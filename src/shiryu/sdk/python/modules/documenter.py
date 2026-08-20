"""documenter module."""

from pathlib import Path, PurePosixPath
from typing import Final, final

import dagger

from shiryu.sdk.common.utils import PROJECT_SOURCE_CODE_FOLDER

from ....utils.dagger.directory import directory_with_new_file
from ....utils.template import Mapping, Template, TemplateFile
from ...common.context import DaggerModuleMetadata
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
from ...common.templates import COMMON_JINJA_ENVIRONMENT
from ..context import PythonModuleInitContextDirectory
from ..module import PythonModule, PythonModuleInitializer
from ..templates import PYTHON_JINJA_ENVIRONMENT

GITHUB_PAGES_ENVIRONMENT: Final = GitHubJobEnvironment(
    "github-pages", "${{ steps.deployment.outputs.page_url }}"
)

PROJECT_DOCUMENTATION_FOLDER: Final = "docs"
PROJECT_DOCUMENTATION_PATH: Final = PurePosixPath(PROJECT_DOCUMENTATION_FOLDER)
PROJECT_DOCUMENTATION_REFERENCE_FOLDER: Final = "reference"
PROJECT_SITE_FOLDER: Final = "site"
PROJECT_SCRIPTS_FOLDER: Final = "scripts"
PROJECT_SCRIPTS_PATH: Final = PurePosixPath(PROJECT_SCRIPTS_FOLDER)


class DocumenterInitializer(PythonModuleInitializer):
    """DocumenterInitializer class."""

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
        sdk_module_cls = Documenter
        sdk_language = sdk_module_cls._sdk_name()
        sdk_module_name = sdk_module_cls.name()
        sdk_module_function = sdk_module_cls.document
        export_path = PROJECT_DOCUMENTATION_PATH
        github_action = build_github_action(
            sdk_language=sdk_language,
            sdk_module_name=sdk_module_name,
            sdk_module_function=sdk_module_function,
            dagger_version=dagger_version,
            shiryu_version=shiryu_version,
            export_path=export_path,
        )
        gitlab_documentation_folder_output = "public"
        gitlab_job = build_gitlab_job(
            sdk_language=sdk_language,
            sdk_module_name=sdk_module_name,
            sdk_module_function=sdk_module_function,
            shiryu_version=shiryu_version,
            pre_script=(),
            export_path=export_path,
            post_script=(
                f"mkdir {gitlab_documentation_folder_output}",
                f"cp --recursive {PROJECT_SITE_FOLDER}/* {gitlab_documentation_folder_output}/",
            ),
            artifacts=GitLabArtifacts(paths=(gitlab_documentation_folder_output,)),
        )
        documentation_api_reference_path = (
            PROJECT_DOCUMENTATION_PATH / PROJECT_DOCUMENTATION_REFERENCE_FOLDER / "api-reference"
        )
        return init_context_directory.evolve(
            vcs=init_context_directory.vcs.evolve(
                exclude_files_folders=init_context_directory.vcs.exclude_files_folders
                | {f"/{PROJECT_SITE_FOLDER}/", f"/{documentation_api_reference_path}"}
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
                                            "path", f"{PROJECT_SITE_FOLDER}"
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
                sdk_module_name,
                {
                    # All versions supported
                    "mkdocs-autorefs",
                    # https://github.com/mkdocstrings/python/releases/tag/1.11.0
                    # >= 1.11.0: Hook into autorefs to provide context around cross-ref errors
                    "mkdocstrings-python >= 1.11.0",
                    # https://github.com/zensical/zensical/releases/tag/v0.0.22
                    # # >= 0.0.22: Support autorefs plugin
                    "zensical >= 0.0.22",
                },
            ),
        )

    @final
    @classmethod
    def _zensical_toml_template_file(cls) -> TemplateFile:
        """
        zensical.toml template file.

        Returns:
            The zensical.toml template file.
        """
        return TemplateFile(Path("zensical.toml"))

    @final
    @classmethod
    def _gen_ref_pages_py_template_file(cls) -> TemplateFile:
        """
        gen_ref_pages.py template file.

        Returns:
            The gen_ref_pages.py template file.
        """
        return TemplateFile(Path("gen_ref_pages.py"), output_directory=PROJECT_SCRIPTS_PATH)

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
        project_documentation_path = PROJECT_DOCUMENTATION_PATH
        # zensical.toml
        zensical_toml_template_mapping: Mapping = {
            "project_name": project_name,
            "project_authors_names": project_authors_names,
            "project_site_path": PROJECT_SITE_FOLDER,
            "project_docs_path": PROJECT_DOCUMENTATION_FOLDER,
            "project_src_path": PROJECT_SOURCE_CODE_FOLDER,
        }
        zensical_toml_template = Template(
            PYTHON_JINJA_ENVIRONMENT,
            cls._zensical_toml_template_file(),
            zensical_toml_template_mapping,
        )
        init_directory = directory_with_new_file(init_directory, zensical_toml_template)
        # <documentation>/**/index.md
        index_md_file_path = PurePosixPath("index.md")
        # <documentation>/index.md
        documentation_md_template_mapping: Mapping = {}
        documentation_md_template = Template(
            COMMON_JINJA_ENVIRONMENT,
            TemplateFile(
                Path("documentation.md"),
                output_directory=project_documentation_path,
                output_file_name=index_md_file_path,
            ),
            documentation_md_template_mapping,
        )
        init_directory = directory_with_new_file(init_directory, documentation_md_template)
        # <documentation>/explanation/index.md
        explanation_md_template_mapping: Mapping = {}
        explanation_md_template = Template(
            COMMON_JINJA_ENVIRONMENT,
            TemplateFile(
                Path("explanation.md"),
                output_directory=project_documentation_path / PurePosixPath("explanation"),
                output_file_name=index_md_file_path,
            ),
            explanation_md_template_mapping,
        )
        init_directory = directory_with_new_file(init_directory, explanation_md_template)
        # <documentation>/how-to-guides/index.md
        how_to_guides_md_template_mapping: Mapping = {}
        how_to_guides_md_template = Template(
            COMMON_JINJA_ENVIRONMENT,
            TemplateFile(
                Path("how_to_guides.md"),
                output_directory=project_documentation_path / PurePosixPath("how-to-guides"),
                output_file_name=index_md_file_path,
            ),
            how_to_guides_md_template_mapping,
        )
        init_directory = directory_with_new_file(init_directory, how_to_guides_md_template)
        # <documentation>/reference/index.md
        reference_md_template_mapping: Mapping = {}
        reference_md_template = Template(
            COMMON_JINJA_ENVIRONMENT,
            TemplateFile(
                Path("reference.md"),
                output_directory=project_documentation_path
                / PurePosixPath(PROJECT_DOCUMENTATION_REFERENCE_FOLDER),
                output_file_name=index_md_file_path,
            ),
            reference_md_template_mapping,
        )
        init_directory = directory_with_new_file(init_directory, reference_md_template)
        # <documentation>/tutorials/index.md
        tutorials_md_template_mapping: Mapping = {}
        tutorials_md_template = Template(
            COMMON_JINJA_ENVIRONMENT,
            TemplateFile(
                Path("tutorials.md"),
                output_directory=project_documentation_path / PurePosixPath("tutorials"),
                output_file_name=index_md_file_path,
            ),
            tutorials_md_template_mapping,
        )
        init_directory = directory_with_new_file(init_directory, tutorials_md_template)
        # scripts/gen_ref_pages.py
        gen_ref_pages_py_template_mapping: Mapping = {}
        gen_ref_pages_py_template = Template(
            PYTHON_JINJA_ENVIRONMENT,
            cls._gen_ref_pages_py_template_file(),
            gen_ref_pages_py_template_mapping,
        )
        init_directory = directory_with_new_file(init_directory, gen_ref_pages_py_template)
        return init_directory


@dagger.object_type
class Documenter(PythonModule):
    """Python SDK documenter."""

    @staticmethod
    def _initializer_cls() -> type[DocumenterInitializer]:
        """
        Initializer class.

        Returns:
            The initializer class.
        """
        return DocumenterInitializer

    @final
    @classmethod
    def __document(cls, container: dagger.Container) -> dagger.Directory:
        """
        Document pipeline.

        Args:
            container: Project container.

        Returns:
            The directory with the documentation files.
        """
        initializer = cls._initializer_cls()
        zensical_toml_file_name = initializer._zensical_toml_template_file().file_name
        zensical_command = cls._build_uv_run_command(
            ["zensical", "build", f"--config-file={zensical_toml_file_name}"]
        )
        return (
            container.with_exec(
                ["python3", str(initializer._gen_ref_pages_py_template_file().output_path)]
            )
            .with_exec(zensical_command)
            .directory(PROJECT_SITE_FOLDER)
        )

    @final
    @dagger.function
    async def document(
        self,
        project_directory: ProjectDirectoryDaggerType,
        *,
        platform: PlatformDaggerType = PLATFORM_DAGGER_DEFAULT,
    ) -> dagger.Directory:
        """Run documenter document in the project of the provided source Directory."""
        container = await self._exec_container(project_directory, platform)
        return self.__document(container)

    @final
    @dagger.function
    async def audit(
        self,
        project_directory: ProjectDirectoryDaggerType,
        *,
        platform: PlatformDaggerType = PLATFORM_DAGGER_DEFAULT,
    ) -> str | None:
        """Audit source code docstrings."""
        workspace = await self._exec_container(project_directory, platform)

        # 1. Extract source code context before calling LLM (0 LLM requests)
        source_code_dump = await workspace.with_exec(
            [
                "sh",
                "-c",
                f"find {PROJECT_SOURCE_CODE_FOLDER} -name '*.py' -exec echo '=== FILE: {{}} ===' \\; -exec cat {{}} \\;",  # noqa: E501
            ]
        ).stdout()

        # 2. Define environment with string output target
        environment = dagger.dag.env().with_string_output(
            "audit_report",
            "Strictly raw JSON audit report matching the required schema.",
        )
        documenter_audit_propmpt_txt_template_mapping: Mapping = {
            "source_code_dump": source_code_dump,
            "project_src_path": PROJECT_SOURCE_CODE_FOLDER,
        }
        documenter_audit_prompt_txt_template = Template(
            PYTHON_JINJA_ENVIRONMENT,
            TemplateFile(Path("documenter_audit_prompt.txt")),
            documenter_audit_propmpt_txt_template_mapping,
        )
        # 4. Execute single-pass LLM job (No .loop() means exactly 1 request)
        # llm providers: https://docs.dagger.io/reference/configuration/llm
        audit_job = (
            dagger.dag.llm(model="gemini-3.6-flash")
            .with_env(environment)
            .with_prompt(documenter_audit_prompt_txt_template.contents)
        )

        # 5. Retrieve output string
        report = await audit_job.env().output("audit_report").as_string()
        return report


sdk_module: Final = Documenter
