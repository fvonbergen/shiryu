"""documenter module."""

import tomllib
from pathlib import Path
from typing import Final, final

import dagger

from ....utils.dagger.container import container_with_file, is_container_with_file
from ....utils.template import Mapping, Template, TemplateFile
from ...common.module import (
    PLATFORM_DEFAULT,
    GitHubActionsWorkflows,
    GitHubJobEnvironment,
    GitHubWorkflowId,
    GitHubWorkflowJobStep,
    GitHubWorkflowStepInputParameter,
    GitLabArtifacts,
    GitLabJobsStages,
    GitLabStageId,
    PlatformType,
    ProjectType,
    SCMListType,
    SDKEnv,
    SDKModuleModule,
)
from ..module import ModulesPythonPackages, PythonModule, PythonModuleInit
from ..templates import PYTHON_JINJA_ENVIRONMENT

GITHUB_PAGES_ENVIRONMENT: Final = GitHubJobEnvironment(
    "github-pages", "${{ steps.deployment.outputs.page_url }}"
)

SPHINX_PACKAGE_NAME: Final = "sphinx"


class DocumenterInit(PythonModuleInit):
    """Python SDK documenter initializer."""

    @final
    @staticmethod
    def __project_documentation_folder() -> str:
        """
        Get the project documentation folder.

        Returns:
            Project documentation folder.
        """
        return "docs"

    @final
    @staticmethod
    def __project_shiryu_templates_folder() -> str:
        """
        Get the project documentation folder.

        Returns:
            Project documentation folder.
        """
        return "shiryu-templates"

    @classmethod
    def _vcs_exclude_files_folders(cls) -> set[str]:
        """
        Files and folders to exclude from vcs.

        Returns:
            A list of files and folders to exclude from vcs.
        """
        vcs_exclude_files_folders = super(
            DocumenterInit, cls
        )._vcs_exclude_files_folders()
        vcs_exclude_files_folders.update(
            {
                f"/{cls.__project_documentation_folder()}/build/",
                rf"/{cls.__project_documentation_folder()}/source/*\.rst",
                rf"!/{cls.__project_documentation_folder()}/source/index\.rst",
            }
        )
        return vcs_exclude_files_folders

    @final
    @classmethod
    def _container_project_documentation_path(cls) -> Path:
        """
        Get the container project documentation path.

        Returns:
            Container project documentation path.
        """
        return cls._container_project_path() / cls.__project_documentation_folder()

    @final
    @classmethod
    def _container_project_documentation_shiryu_templates_path(cls) -> Path:
        """
        Get the container project documentation path.

        Returns:
            Container project documentation path.
        """
        return (
            cls._container_project_path()
            / cls.__project_documentation_folder()
            / cls.__project_shiryu_templates_folder()
        )

    @classmethod
    async def _module_init(
        cls, sdk_env: SDKEnv, is_overwrite: bool, scm: SCMListType
    ) -> SDKEnv:
        """
        Initialize the SDK module environment.

        Args:
            sdk_env: SDK environment.
            is_overwrite: Whether to overwrite files or not.
            scm: Project Source Code Management (SCM) list to be targeted or configured.

        Returns:
            Returns an SDK module environment.
        """
        _sdk_env = await super(DocumenterInit, cls)._module_init(
            sdk_env, is_overwrite, scm
        )
        container = _sdk_env.container
        project_properties = _sdk_env.project_properties
        pyproject_toml_template_file = cls._pyproject_toml_template_file()
        pyproject_toml_file_contents = await container.file(
            str(pyproject_toml_template_file.output_path)
        ).contents()
        pyproject_toml_data = tomllib.loads(pyproject_toml_file_contents)
        pyproject_toml_data_project = pyproject_toml_data["project"]
        project_name = pyproject_toml_data_project["name"]
        project_authors_names = ", ".join(
            [
                project_author["name"]
                for project_author in pyproject_toml_data_project["authors"]
            ]
        )
        project_documentation_path_str = str(
            cls._container_project_documentation_path()
        )
        conf_py_jinja_template_mapping: Mapping = {}
        project_documentation_shiryu_templates_path = (
            cls._container_project_documentation_shiryu_templates_path()
        )
        project_documentation_shiryu_templates_path_str = str(
            project_documentation_shiryu_templates_path
        )
        conf_py_jinja_template_file = TemplateFile(
            Path("conf.py.jinja"), project_documentation_shiryu_templates_path
        )
        if not await is_container_with_file(container, conf_py_jinja_template_file):
            conf_py_jinja_template = Template(
                PYTHON_JINJA_ENVIRONMENT,
                conf_py_jinja_template_file,
                conf_py_jinja_template_mapping,
            )
            container = await container_with_file(
                container, conf_py_jinja_template, is_overwrite
            )
            container = (
                container.with_exec(
                    ["mkdir", "--parents", project_documentation_path_str]
                )
                .with_exec(["uv", "pip", "install", SPHINX_PACKAGE_NAME])
                .with_exec(
                    [
                        "uv",
                        "run",
                        "--no-project",
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
                        f"--templatedir={project_documentation_shiryu_templates_path_str}",
                        # "-d=append_syspath=true",
                        # f"-d=module_path=os.path.abspath('../../{cls._source_folder()}')",
                        project_documentation_path_str,
                    ]
                )
                .with_exec(
                    [
                        "sed",
                        "--in-place",
                        "--regexp-extended",
                        r"--expression=s/^   sphinx-quickstart on [a-zA-Z]{3} [a-zA-Z]{3} [0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2} [0-9]{4}\.$/   sphinx-quickstart on --- --- -- --:--:-- ----./",
                        r"--expression=/^Add your content using ``reStructuredText`` syntax\. See the$/d",
                        r"--expression=\|^`reStructuredText <https://www\.sphinx-doc\.org/en/master/usage/restructuredtext/index\.html>`_$|d",
                        r"--expression=/^documentation for details\.$/d",
                        r"--expression=/^   :caption: Contents:$/a\ \n   modules\n\n\nIndices and tables\n==================\n\n* :ref:`genindex`\n* :ref:`modindex`\n* :ref:`search`",
                        f"{cls._container_project_documentation_path() / 'source' / 'index.rst'}",
                    ]
                )
            )
        return SDKEnv(container, project_properties)

    @classmethod
    def _github_actions_workflows(
        cls, dagger_version: str, shiryu_version: str
    ) -> GitHubActionsWorkflows:
        """
        Get the GitHub actions and workflows.

        Args:
            dagger_version: Dagger version.
            shiryu_version: Shiryu version.

        Returns:
            GitHub actions and workflows.
        """
        github_actions_workflows = super(DocumenterInit, cls)._github_actions_workflows(
            dagger_version, shiryu_version
        )
        github_actions = github_actions_workflows["actions"]
        github_workflows = github_actions_workflows["workflows"]
        github_action = cls._build_github_action(
            Documenter,
            Documenter.document,  # pyright: ignore [reportArgumentType]
            dagger_version,
            shiryu_version,
            Path(cls.__project_documentation_folder()),
        )
        github_actions.add(github_action)
        github_workflows.add(
            GitHubWorkflowId.DEPLOY,
            cls._build_github_workflow_job(
                github_action,
                shiryu_version,
                GITHUB_PAGES_ENVIRONMENT,
                (
                    GitHubWorkflowJobStep(
                        "upload_artifact",
                        "Upload artifact",
                        "actions/upload-pages-artifact@v5",
                        (
                            GitHubWorkflowStepInputParameter(
                                "path",
                                f"{cls.__project_documentation_folder()}/build/html",
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
        )
        github_workflows.add(
            GitHubWorkflowId.QUALITY,
            cls._build_github_workflow_job(
                github_action, shiryu_version, None, tuple()
            ),
        )
        return {"actions": github_actions, "workflows": github_workflows}

    @classmethod
    def _gitlab_jobs_stages(
        cls, dagger_version: str, shiryu_version: str
    ) -> GitLabJobsStages:
        """
        Get the GitLab jobs and stages.

        Args:
            dagger_version: Dagger version.
            shiryu_version: Shiryu version.

        Returns:
            GitLab jobs and stages.
        """
        gitlab_jobs_stages = super(DocumenterInit, cls)._gitlab_jobs_stages(
            dagger_version, shiryu_version
        )
        gitlab_jobs = gitlab_jobs_stages["jobs"]
        gitlab_stages = gitlab_jobs_stages["stages"]
        gitlab_documentation_folder_output = "public"
        gitlab_job = cls._build_gitlab_job(
            Documenter,
            Documenter.document,  # pyright: ignore [reportArgumentType]
            shiryu_version,
            (),
            Path(cls.__project_documentation_folder()),
            (
                f"mkdir {gitlab_documentation_folder_output}",
                f"cp --recursive {cls.__project_documentation_folder()}/build/html/* {gitlab_documentation_folder_output}/",
            ),
            GitLabArtifacts(paths=(gitlab_documentation_folder_output,)),
        )
        gitlab_jobs.update({gitlab_job})
        gitlab_stages.add(
            GitLabStageId.DEPLOY,
            cls._build_gitlab_stage_job(GitLabStageId.DEPLOY, gitlab_job),
        )
        gitlab_stages.add(
            GitLabStageId.QUALITY,
            cls._build_gitlab_stage_job(GitLabStageId.QUALITY, gitlab_job),
        )
        return {"jobs": gitlab_jobs, "stages": gitlab_stages}


@final
@dagger.object_type
class Documenter(PythonModule, DocumenterInit):
    """Python SDK documenter."""

    @classmethod
    def _base_container_base_packages(cls) -> set[str]:
        """
        Base container base packages.

        Returns:
            Base container base packages.
        """
        base_container_base_packages = super(
            Documenter, cls
        )._base_container_base_packages()
        base_container_base_packages.update({"make"})
        return base_container_base_packages

    @classmethod
    def _base_container_modules_python_packages(cls) -> ModulesPythonPackages:
        """
        Base container modules python packages.

        Returns:
            Base container modules python packages.
        """
        base_container_modules_python_packages = super(
            Documenter, cls
        )._base_container_modules_python_packages()
        base_container_modules_python_packages[Documenter.name()] = {
            SPHINX_PACKAGE_NAME,
            "sphinx-autodoc-typehints",
            "sphinx_rtd_theme",
        }
        return base_container_modules_python_packages

    @final
    @classmethod
    async def __pipeline(
        cls, project: ProjectType, platform: PlatformType
    ) -> dagger.Container:
        """
        Document pipeline.

        Args:
            project: Project directory.
            platform: The container platform.

        Returns:
            A container with the project document command executed.
        """
        container, sdk_env = await cls.sdk_module_env(project, platform)
        project_install = [
            "uv",
            "pip",
            "install",
            "--no-sources",
            str(cls._container_project_path()),
        ]
        sphinx_command = [
            "uv",
            "run",
            "--no-project",
            "sphinx-apidoc",
            "--implicit-namespaces",
            f"-o={cls._container_project_documentation_path() / 'source'}",
            str(cls._container_project_source_path() / sdk_env.name),
        ]
        make_command = [
            "uv",
            "run",
            "--no-project",
            "make",
            f"--directory={cls._container_project_documentation_path()}",
            "html",
        ]
        return await (
            container.with_exec(project_install)
            .with_exec(sphinx_command)
            .with_exec(make_command)
            .sync()
        )

    @final
    @dagger.function
    async def document(
        self, project: ProjectType, platform: PlatformType = PLATFORM_DEFAULT
    ) -> dagger.Directory:
        """Run documenter document in the project of the provided source Directory."""
        container = await self.__pipeline(project, platform)
        return await container.directory(
            str(self._container_project_documentation_path())
        )


sdk_module: Final = SDKModuleModule(init=DocumenterInit, module=Documenter)
