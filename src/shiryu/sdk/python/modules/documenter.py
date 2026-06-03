"""documenter module."""

from pathlib import Path, PurePosixPath
from typing import Final, final

import dagger

from ....utils.dagger.directory import directory_with_new_file
from ....utils.template import Mapping, Template, TemplateFile
from ...common.context import DaggerModuleMetadata, SDKModuleInitContextContainer
from ...common.module import (
    PLATFORM_DAGGER_DEFAULT,
    PlatformDaggerType,
    PlatformType,
    ProjectDirectoryDaggerType,
    ProjectMetadata,
    SCMType,
)
from ...common.scm import (
    GitHubJobEnvironment,
    GitHubWorkflowId,
    GitHubWorkflowJobStep,
    GitHubWorkflowStepInputParameter,
    GitLabArtifacts,
    GitLabStageId,
    build_github_action,
    build_github_workflow_job,
    build_gitlab_job,
    build_gitlab_stage_job,
)
from ...common.utils import PROJECT_SOURCE_CODE_FOLDER
from ..context import PythonModuleInitContextDirectory
from ..module import ExecutionMode, PythonModule
from ..templates import PYTHON_JINJA_ENVIRONMENT
from ..utils import get_package_name_canonical

GITHUB_PAGES_ENVIRONMENT: Final = GitHubJobEnvironment(
    "github-pages", "${{ steps.deployment.outputs.page_url }}"
)

PROJECT_DOCUMENTATION_FOLDER: Final = "docs"


@dagger.object_type
class Documenter(PythonModule):
    """Python SDK documenter."""

    @classmethod
    def _init_context_directory(
        cls,
        init_context_directory: PythonModuleInitContextDirectory,
        shiryu_metadata: DaggerModuleMetadata,
        project_metadata: ProjectMetadata,
    ) -> PythonModuleInitContextDirectory:
        """
        Initialization directory context used in the SDK module directory initialization.

        Args:
            init_context_directory: SDK module initialization directory context.
            shiryu_metadata: Shiryu metadata.
            project_metadata: Project metadata.

        Returns:
            The updated SDK module initialization directory context.
        """
        init_context_directory = super()._init_context_directory(
            init_context_directory, shiryu_metadata, project_metadata
        )
        dagger_version = shiryu_metadata.dagger_version
        shiryu_version = shiryu_metadata.git_tag_or_branch
        sdk_language = cls._sdk_name()
        sdk_module_name = cls.name()
        github_action = build_github_action(
            sdk_language=sdk_language,
            sdk_module_name=sdk_module_name,
            sdk_module_function=cls.document,  # pyright: ignore [reportArgumentType]
            dagger_version=dagger_version,
            shiryu_version=shiryu_version,
            export_path=PurePosixPath(PROJECT_DOCUMENTATION_FOLDER),
        )
        gitlab_documentation_folder_output = "public"
        gitlab_job = build_gitlab_job(
            sdk_language=sdk_language,
            sdk_module_name=sdk_module_name,
            sdk_module_function=cls.document,  # pyright: ignore [reportArgumentType]
            shiryu_version=shiryu_version,
            pre_script=(),
            export_path=PurePosixPath(PROJECT_DOCUMENTATION_FOLDER),
            post_script=(
                f"mkdir {gitlab_documentation_folder_output}",
                f"cp --recursive {PROJECT_DOCUMENTATION_FOLDER}/build/html/* {gitlab_documentation_folder_output}/",  # noqa: E501
            ),
            artifacts=GitLabArtifacts(paths=(gitlab_documentation_folder_output,)),
        )
        return init_context_directory.evolve(
            vcs=init_context_directory.vcs.evolve(
                exclude_files_folders=init_context_directory.vcs.exclude_files_folders
                | {
                    f"/{PROJECT_DOCUMENTATION_FOLDER}/build/",
                    rf"/{PROJECT_DOCUMENTATION_FOLDER}/source/reference/modules\.rst",
                    rf"/{PROJECT_DOCUMENTATION_FOLDER}/source/reference/{project_metadata.name}\.*\.rst",
                }
            ),
            scm=init_context_directory.scm.evolve(
                github_actions_workflows=init_context_directory.scm.github_actions_workflows.evolve(
                    actions=init_context_directory.scm.github_actions_workflows.actions
                    | {github_action},
                    workflows=init_context_directory.scm.github_actions_workflows.workflows.add(
                        GitHubWorkflowId.DEPLOY,
                        build_github_workflow_job(
                            sdk_language=sdk_language,
                            github_action=github_action,
                            shiryu_version=shiryu_version,
                            job_environment=GITHUB_PAGES_ENVIRONMENT,
                            post_steps=(
                                GitHubWorkflowJobStep(
                                    "upload_artifact",
                                    "Upload artifact",
                                    "actions/upload-pages-artifact@v5",
                                    (
                                        GitHubWorkflowStepInputParameter(
                                            "path", f"{PROJECT_DOCUMENTATION_FOLDER}/build/html"
                                        ),
                                    ),
                                ),
                                GitHubWorkflowJobStep(
                                    "deploy_to_github_pages",
                                    "Deploy to GitHub pages",
                                    "actions/deploy-pages@v5",
                                    (),
                                ),
                            ),
                        ),
                    ).add(
                        GitHubWorkflowId.QUALITY,
                        build_github_workflow_job(
                            sdk_language=sdk_language,
                            github_action=github_action,
                            shiryu_version=shiryu_version,
                            job_environment=None,
                            post_steps=(),
                        ),
                    ),
                ),
                gitlab_jobs_stages=init_context_directory.scm.gitlab_jobs_stages.evolve(
                    jobs=init_context_directory.scm.gitlab_jobs_stages.jobs | {gitlab_job},
                    stages=init_context_directory.scm.gitlab_jobs_stages.stages.add(
                        GitLabStageId.DEPLOY,
                        build_gitlab_stage_job(
                            gitlab_stage_id=GitLabStageId.DEPLOY, gitlab_job=gitlab_job
                        ),
                    ).add(
                        GitLabStageId.QUALITY,
                        build_gitlab_stage_job(
                            gitlab_stage_id=GitLabStageId.QUALITY, gitlab_job=gitlab_job
                        ),
                    ),
                ),
            ),
            dependency_groups=init_context_directory.dependency_groups.add(
                sdk_module_name, {"sphinx", "sphinx-autodoc-typehints", "sphinx_rtd_theme"}
            ),
        )

    @classmethod
    async def _init_directory(
        cls,
        init_directory: dagger.Directory,
        init_context_directory: PythonModuleInitContextDirectory,
        project_metadata: ProjectMetadata,
        scm: SCMType,
        platform: PlatformType,
    ) -> dagger.Directory:
        """
        Build the initialization directory.

        Args:
            init_directory: The dagger directory to initialize.
            init_context_directory: SDK module initialization directory context.
            project_metadata: Project metadata.
            scm: Project Source Code Management (SCM) list to be targeted or configured.
            platform: The container platform used for initialization.

        Returns:
            The initialization directory.
        """
        init_directory = await super()._init_directory(
            init_directory, init_context_directory, project_metadata, scm, platform
        )
        project_name = project_metadata.name
        project_authors_names = ", ".join([author.name for author in project_metadata.authors])
        project_documentation_path = PurePosixPath(PROJECT_DOCUMENTATION_FOLDER)
        # <documentation>/
        conf_py_jinja_template_mapping: Mapping = {}
        project_documentation_shiryu_templates_path = (
            project_documentation_path / "shiryu-templates"
        )
        # <documentation>/shiryu-templates/conf.py.jinja
        conf_py_jinja_template_file = TemplateFile(
            Path("conf.py.jinja"), project_documentation_shiryu_templates_path
        )
        conf_py_jinja_template = Template(
            PYTHON_JINJA_ENVIRONMENT, conf_py_jinja_template_file, conf_py_jinja_template_mapping
        )
        init_directory = directory_with_new_file(init_directory, conf_py_jinja_template)
        # <documentation>/source/{explanation/, how_to/, reference/, tutorials/,}
        # TODO: add docs/source/index.rst file
        # TODO: add diátaxis index.rst files:
        # docs/source/{explanation, how_to, reference, tutorials}/index.rst
        empty_directory = dagger.dag.directory()
        init_directory = (
            init_directory.with_directory(
                str(project_documentation_path / "source" / "explanation"), empty_directory
            )
            .with_directory(str(project_documentation_path / "source" / "how_to"), empty_directory)
            .with_directory(
                str(project_documentation_path / "source" / "reference"), empty_directory
            )
            .with_directory(
                str(project_documentation_path / "source" / "tutorials"), empty_directory
            )
        )
        # <documentation>/{Makefile, build/, source/_static/, source/_templates/, source/conf.py,
        # source/index.rst}
        init_directory = (
            cls._base_container(
                cls._init_context_container(SDKModuleInitContextContainer.create_default()),
                platform,
            )
            .with_directory(".", init_directory)
            .with_exec(
                [
                    "uvx",
                    "--from",
                    "sphinx",
                    "sphinx-quickstart",
                    "--sep",
                    f"--project={project_name}",
                    f"--author='{project_authors_names}'",
                    "--language=en",
                    "--release=",
                    "--ext-autodoc",
                    "--ext-doctest",
                    "--ext-intersphinx",
                    "--ext-todo",
                    "--ext-coverage",
                    "--ext-imgmath",
                    "--ext-mathjax",
                    "--ext-ifconfig",
                    "--ext-viewcode",
                    "--ext-githubpages",
                    "--extensions=sphinx.ext.napoleon,sphinx_autodoc_typehints",
                    "--no-batchfile",
                    f"--templatedir={project_documentation_shiryu_templates_path}",
                    # "-d=append_syspath=true",
                    # f"-d=module_path=os.path.abspath('../../{cls._source_folder()}')",
                    str(project_documentation_path),
                ]
            )
            .with_exec(
                [
                    "sed",
                    "--in-place",
                    "--regexp-extended",
                    r"--expression=s/^   sphinx-quickstart on [a-zA-Z]{3} [a-zA-Z]{3} [0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2} [0-9]{4}\.$/   sphinx-quickstart on --- --- -- --:--:-- ----./",  # noqa: E501
                    r"--expression=/^Add your content using ``reStructuredText`` syntax\. See the$/d",  # noqa: E501
                    r"--expression=\|^`reStructuredText <https://www\.sphinx-doc\.org/en/master/usage/restructuredtext/index\.html>`_$|d",
                    r"--expression=/^documentation for details\.$/d",
                    r"--expression=/^   :caption: Contents:$/a\ \n   modules\n\n\nIndices and tables\n==================\n\n* :ref:`genindex`\n* :ref:`modindex`\n* :ref:`search`",  # noqa: E501
                    f"{project_documentation_path / 'source' / 'index.rst'}",
                ]
            )
            .directory(".")
        )
        return init_directory

    @classmethod
    def _init_context_container(
        cls, init_context_container: SDKModuleInitContextContainer
    ) -> SDKModuleInitContextContainer:
        """
        Initialization container context used in the SDK module container initialization.

        Args:
            init_context_container: SDK module initialization container context.

        Returns:
            The updated SDK module initialization container context.
        """
        return init_context_container.evolve(
            apt_packages=init_context_container.apt_packages | {"make"}
        )

    @final
    @classmethod
    def __document(
        cls, container: dagger.Container, project_metadata: ProjectMetadata
    ) -> dagger.Directory:
        """
        Document pipeline.

        Args:
            container: Project container.
            project_metadata: Project metadata.

        Returns:
            The directory with the documentation files.
        """
        package_name_canonical = get_package_name_canonical(project_metadata.name)
        sphinx_command = cls._build_uv_run_command(
            [
                "sphinx-apidoc",
                "--implicit-namespaces",
                f"-o={PurePosixPath(PROJECT_DOCUMENTATION_FOLDER) / 'source' / 'reference'}",
                str(PurePosixPath(PROJECT_SOURCE_CODE_FOLDER) / package_name_canonical),
            ],
            ExecutionMode.SCRIPT,
        )
        make_command = cls._build_uv_run_command(
            ["make", f"--directory={PROJECT_DOCUMENTATION_FOLDER}", "html"], ExecutionMode.SCRIPT
        )
        return (
            container.with_exec(sphinx_command)
            .with_exec(make_command)
            .directory(PROJECT_DOCUMENTATION_FOLDER)
        )

    @final
    @dagger.function
    async def document(
        self,
        project_directory: ProjectDirectoryDaggerType,
        platform: PlatformDaggerType = PLATFORM_DAGGER_DEFAULT,
    ) -> dagger.Directory:
        """Run documenter document in the project of the provided source Directory."""
        project_metadata = await self._get_project_metadata(project_directory, platform)
        container = await self._exec_container(project_directory, platform)
        return self.__document(container, project_metadata)


sdk_module: Final = Documenter
