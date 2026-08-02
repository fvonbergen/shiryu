"""documenter module."""

from pathlib import Path, PurePosixPath
from typing import Final, final

import dagger

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
from ..context import PythonModuleInitContextDirectory
from ..module import PythonModule, PythonModuleInitializer
from ..templates import PYTHON_JINJA_ENVIRONMENT

GITHUB_PAGES_ENVIRONMENT: Final = GitHubJobEnvironment(
    "github-pages", "${{ steps.deployment.outputs.page_url }}"
)

PROJECT_DOCUMENTATION_FOLDER: Final = "docs"
PROJECT_DOCUMENTATION_PATH: Final = PurePosixPath(PROJECT_DOCUMENTATION_FOLDER)
PROJECT_SITE_FOLDER: Final = "site"


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
        return init_context_directory.evolve(
            vcs=init_context_directory.vcs.evolve(
                exclude_files_folders=init_context_directory.vcs.exclude_files_folders
                | {f"/{PROJECT_SITE_FOLDER}/"}
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
                sdk_module_name, {"mkdocs-autorefs", "mkdocstrings[python]", "zensical"}
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
        }
        zensical_toml_template = Template(
            PYTHON_JINJA_ENVIRONMENT,
            cls._zensical_toml_template_file(),
            zensical_toml_template_mapping,
        )
        init_directory = directory_with_new_file(init_directory, zensical_toml_template)
        # <documentation>/{explanation/, how_to/, reference/, tutorials/,}
        # TODO: add docs/index.md
        # docs/{explanation, how_to, reference, tutorials}/index.rst
        empty_directory = dagger.dag.directory()
        init_directory = (
            init_directory.with_directory(
                str(project_documentation_path / "explanation"), empty_directory
            )
            .with_directory(str(project_documentation_path / "how_to"), empty_directory)
            .with_directory(str(project_documentation_path / "reference"), empty_directory)
            .with_directory(str(project_documentation_path / "tutorials"), empty_directory)
        )
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
            container.with_exec(["python3", "scripts/gen_ref_pages.py"])
            .with_exec(zensical_command)
            .directory(PROJECT_SITE_FOLDER)
        )

    @final
    @dagger.function
    async def document(
        self,
        project_directory: ProjectDirectoryDaggerType,
        platform: PlatformDaggerType = PLATFORM_DAGGER_DEFAULT,
    ) -> dagger.Directory:
        """Run documenter document in the project of the provided source Directory."""
        container = await self._exec_container(project_directory, platform)
        return self.__document(container)


sdk_module: Final = Documenter
