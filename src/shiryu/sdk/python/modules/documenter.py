"""documenter module."""

import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Annotated, Final, final

import dagger
from dagger_clients.core import Changeset, Container, Directory, core
from packaging.version import Version

from ....utils.dagger.directory import directory_with_new_file
from ....utils.dagger.file import TargetFile
from ....utils.template import Mapping, Template, TemplateFile
from ...common.context import DaggerModuleMetadata
from ...common.module import (
    PLATFORM_DAGGER_DEFAULT,
    PlatformDaggerType,
    PlatformType,
    ProjectMetadata,
    SCMType,
)
from ...common.scm import (
    GitHubJobEnvironment,
    GitHubWorkflowId,
    GitHubWorkflowJobStep,
    GitHubWorkflowStepInputParameter,
    GitLabArtifacts,
    GitLabJobEnvironmentId,
    GitLabStageId,
    GitLabStageJob,
    build_github_action,
    build_github_workflow_checkout_job,
    build_github_workflow_job,
    build_gitlab_job,
    build_gitlab_stage_job,
    build_gitlab_stage_name,
)
from ...common.templates import COMMON_JINJA_ENVIRONMENT
from ...common.utils import PROJECT_SOURCE_CODE_FOLDER, SOURCE_CODE_MAXIMUM_LINE_LENGTH
from ..context import DistributionPackage, PythonModuleInitContextDirectory
from ..module import PythonModule, PythonModuleInitializer
from ..templates import PYTHON_JINJA_ENVIRONMENT
from ..utils import get_package_name_canonical

# PINNED: upload-pages-artifact action version (2026/11/22)
UPLOAD_PAGES_ARTIFACT_ACTION_VERSION: Final = Version("5.0.0")
# PINNED: deploy-pages action version (2026/11/22)
DEPLOY_PAGES_ACTION_VERSION: Final = Version("5.0.1")
GITHUB_PAGES_ENVIRONMENT: Final = GitHubJobEnvironment(
    "github-pages", "${{ steps.deployment.outputs.page_url }}"
)

PROJECT_DOCUMENTATION_FOLDER: Final = "docs"
PROJECT_DOCUMENTATION_PATH: Final = PurePosixPath(PROJECT_DOCUMENTATION_FOLDER)
PROJECT_SITE_FOLDER: Final = "site"
PROJECT_SITE_PATH: Final = PurePosixPath(PROJECT_SITE_FOLDER)
PROJECT_SCRIPTS_FOLDER: Final = "scripts"
PROJECT_SCRIPTS_PATH: Final = PurePosixPath(PROJECT_SCRIPTS_FOLDER)

LMModelType = str
LLMModelDaggerType = Annotated[LMModelType, dagger.Doc("LLM model used by the audit")]
LLM_MODEL_DAGGER_DEFAULT: Final = "gpt-4.1"

LLMProviderType = str
LLMProviderDaggerType = Annotated[
    LLMProviderType,
    dagger.Doc('LLM provider used by the audit, e.g. "github-copilot", "google" or "anthropic"'),
]
LLM_PROVIDER_DAGGER_DEFAULT: Final = "github-copilot"

TargetBranchType = str
TargetBranchDaggerType = Annotated[
    TargetBranchType,
    dagger.Doc(
        "Git ref to compare against (e.g. origin/main); only the Python files changed since "
        "then are audited. Empty, audits every Python file"
    ),
]
# TODO: change it to main or the default branch of the repository we decide
TARGET_BRANCH_DAGGER_DEFAULT: Final = "feat/add-python-sdk"


@final
@dataclass(frozen=True, slots=True)
class NavItem:
    """Represents a single navigation menu item.

    Attributes:
        title: The display text for the navigation link.
        url: The destination URL or path for the navigation link.
    """

    title: str
    url: str


class DocumenterInitializer(PythonModuleInitializer):
    """DocumenterInitializer class."""

    @classmethod
    def _init_context_directory(
        cls,
        init_context_directory: PythonModuleInitContextDirectory,
        shiryu_metadata: DaggerModuleMetadata,
        project_metadata: ProjectMetadata,
    ) -> PythonModuleInitContextDirectory:
        """Initialization directory context used in the SDK module directory initialization.

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
        export_path = PROJECT_SITE_PATH
        github_action = build_github_action(
            sdk_language,
            sdk_module_name,
            sdk_module_function,
            dagger_version,
            shiryu_version,
            export_path=export_path,
        )
        gitlab_documentation_folder_output = "public"
        gitlab_job = build_gitlab_job(
            sdk_language,
            sdk_module_name,
            sdk_module_function,
            shiryu_version,
            export_path=export_path,
            post_script=(
                f"mkdir {gitlab_documentation_folder_output}",
                f"cp --recursive {PROJECT_SITE_PATH}/* {gitlab_documentation_folder_output}/",
            ),
            artifacts=GitLabArtifacts(paths=(gitlab_documentation_folder_output,)),
        )
        gitlab_stage_id_deploy = GitLabStageId.DEPLOY
        gitlab_stage = gitlab_stage_id_deploy.value
        stage_name = gitlab_stage.name
        environment = GitLabJobEnvironmentId.PRODUCTION.value
        gitlab_pages_stage_job = GitLabStageJob(
            "pages",
            stage_name,
            (build_gitlab_stage_name(gitlab_stage_id_deploy, gitlab_job),),
            gitlab_stage.rules,
            script=('echo "Deploying site"',),
            environment=environment,
            artifacts=GitLabArtifacts((gitlab_documentation_folder_output,)),
        )
        pre_steps = (build_github_workflow_checkout_job(),)

        return init_context_directory.evolve(
            vcs=init_context_directory.vcs.evolve(
                exclude_files_folders=init_context_directory.vcs.exclude_files_folders
                | {f"/{PROJECT_SITE_PATH}/"}
            ),
            scm=init_context_directory.scm.evolve(
                github_actions_workflows=init_context_directory.scm.github_actions_workflows.evolve(
                    actions=init_context_directory.scm.github_actions_workflows.actions
                    | {github_action},
                    workflows=init_context_directory.scm.github_actions_workflows.workflows.add(
                        GitHubWorkflowId.DEPLOY,
                        build_github_workflow_job(
                            sdk_language,
                            github_action,
                            shiryu_version,
                            pre_steps,
                            job_environment=GITHUB_PAGES_ENVIRONMENT,
                            post_steps=(
                                GitHubWorkflowJobStep(
                                    "upload_artifact",
                                    "Upload artifact",
                                    f"actions/upload-pages-artifact@v{UPLOAD_PAGES_ARTIFACT_ACTION_VERSION}",
                                    (
                                        GitHubWorkflowStepInputParameter(
                                            "path", f"{PROJECT_SITE_PATH}/"
                                        ),
                                    ),
                                ),
                                GitHubWorkflowJobStep(
                                    "deploy_to_github_pages",
                                    "Deploy to GitHub pages",
                                    f"actions/deploy-pages@v{DEPLOY_PAGES_ACTION_VERSION}",
                                    (),
                                ),
                            ),
                            permissions=(
                                ("contents", "read"),
                                ("pages", "write"),
                                ("id-token", "write"),
                            ),
                        ),
                    ).add(
                        GitHubWorkflowId.QUALITY,
                        build_github_workflow_job(
                            sdk_language, github_action, shiryu_version, pre_steps
                        ),
                    ),
                ),
                gitlab_jobs_stages=init_context_directory.scm.gitlab_jobs_stages.evolve(
                    jobs=init_context_directory.scm.gitlab_jobs_stages.jobs | {gitlab_job},
                    stages=init_context_directory.scm.gitlab_jobs_stages.stages.add(
                        gitlab_stage_id_deploy,
                        build_gitlab_stage_job(
                            gitlab_stage_id_deploy, gitlab_job, environment=environment
                        ),
                    )
                    .add(gitlab_stage_id_deploy, gitlab_pages_stage_job)
                    .add(
                        GitLabStageId.QUALITY,
                        build_gitlab_stage_job(GitLabStageId.QUALITY, gitlab_job),
                    ),
                ),
            ),
            dependency_groups=init_context_directory.dependency_groups.add(
                sdk_module_name,
                {
                    # https://github.com/mkdocstrings/python/releases/tag/1.11.0
                    # >= 1.11.0: Hook into autorefs to provide context around cross-ref errors
                    # https://github.com/mkdocstrings/python/blob/1.11.0/pyproject.toml#L11
                    DistributionPackage("mkdocstrings-python", Version("1.11.0"), Version("3.8")),
                    # https://github.com/zensical/zensical/releases/tag/v0.0.66
                    # >= 0.0.66: Support api-autonav plugin
                    # https://github.com/zensical/zensical/blob/v0.0.66/pyproject.toml#L37
                    DistributionPackage("zensical", Version("0.0.66"), Version("3.10")),
                },
            ),
        )

    @final
    @classmethod
    def _zensical_toml_template_file(cls) -> TemplateFile:
        """zensical.toml template file.

        Returns:
            The zensical.toml template file.
        """
        return TemplateFile(Path("zensical.toml"))

    @classmethod
    async def _init_directory(  # noqa: PLR0913, PLR0917
        cls,
        init_directory: Directory,
        init_context_directory: PythonModuleInitContextDirectory,
        project_metadata: ProjectMetadata,
        scm: SCMType,
        platform: PlatformType,
        container_security_audit_file: TargetFile,
    ) -> Directory:
        """Build the initialization directory.

        Args:
            init_directory: The dagger directory to initialize.
            init_context_directory: SDK module initialization directory context.
            project_metadata: Project metadata.
            scm: Project Source Code Management (SCM) list to be targeted or configured.
            platform: The container platform used for initialization.
            container_security_audit_file: Container security audit file.

        Returns:
            The initialization directory.
        """
        init_directory = await super()._init_directory(
            init_directory,
            init_context_directory,
            project_metadata,
            scm,
            platform,
            container_security_audit_file,
        )
        # <documentation>/**/index.md
        project_documentation_path = PROJECT_DOCUMENTATION_PATH
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
        explanation_title = "Explanation"
        explanation_path = PurePosixPath("explanation")
        explanation_md_template_mapping: Mapping = {"title": explanation_title}
        explanation_md_template = Template(
            COMMON_JINJA_ENVIRONMENT,
            TemplateFile(
                Path("explanation.md"),
                output_directory=project_documentation_path / explanation_path,
                output_file_name=index_md_file_path,
            ),
            explanation_md_template_mapping,
        )
        init_directory = directory_with_new_file(init_directory, explanation_md_template)
        # <documentation>/how-to-guides/index.md
        how_to_guides_title = "How-To Guides"
        how_to_guides_path = PurePosixPath("how-to-guides")
        how_to_guides_md_template_mapping: Mapping = {"title": how_to_guides_title}
        how_to_guides_md_template = Template(
            COMMON_JINJA_ENVIRONMENT,
            TemplateFile(
                Path("how_to_guides.md"),
                output_directory=project_documentation_path / how_to_guides_path,
                output_file_name=index_md_file_path,
            ),
            how_to_guides_md_template_mapping,
        )
        init_directory = directory_with_new_file(init_directory, how_to_guides_md_template)
        # <documentation>/reference/index.md
        reference_title = "Reference"
        reference_path = PurePosixPath("reference")
        reference_md_template_mapping: Mapping = {"title": reference_title}
        reference_md_template = Template(
            COMMON_JINJA_ENVIRONMENT,
            TemplateFile(
                Path("reference.md"),
                output_directory=project_documentation_path / reference_path,
                output_file_name=index_md_file_path,
            ),
            reference_md_template_mapping,
        )
        init_directory = directory_with_new_file(init_directory, reference_md_template)
        # <documentation>/reference/api-reference/index.md
        api_reference_title = "API Reference"
        reference_api_reference_path = reference_path / PurePosixPath("api-reference")
        api_reference_md_template_mapping: Mapping = {"title": api_reference_title}
        api_reference_md_template = Template(
            COMMON_JINJA_ENVIRONMENT,
            TemplateFile(
                Path("api-reference.md"),
                output_directory=project_documentation_path / reference_api_reference_path,
                output_file_name=index_md_file_path,
            ),
            api_reference_md_template_mapping,
        )
        init_directory = directory_with_new_file(init_directory, api_reference_md_template)
        # <documentation>/tutorials/index.md
        tutorials_title = "Tutorials"
        tutorials_path = PurePosixPath("tutorials")
        tutorials_md_template_mapping: Mapping = {"title": tutorials_title}
        tutorials_md_template = Template(
            COMMON_JINJA_ENVIRONMENT,
            TemplateFile(
                Path("tutorials.md"),
                output_directory=project_documentation_path / tutorials_path,
                output_file_name=index_md_file_path,
            ),
            tutorials_md_template_mapping,
        )
        init_directory = directory_with_new_file(init_directory, tutorials_md_template)
        # <documentation>/SUMMARY.md
        summary_md_path = Path("SUMMARY.md")
        summary_md_template_mapping: Mapping = {
            "nav": (
                (NavItem("Home", str(index_md_file_path)), None),
                (
                    NavItem(tutorials_title, str(tutorials_path / index_md_file_path)),
                    None,
                ),
                (
                    NavItem(how_to_guides_title, str(how_to_guides_path / index_md_file_path)),
                    None,
                ),
                (
                    NavItem(reference_title, str(reference_path / index_md_file_path)),
                    (NavItem(api_reference_title, f"{reference_api_reference_path}/"),),
                ),
                (
                    NavItem(explanation_title, str(explanation_path / index_md_file_path)),
                    None,
                ),
            )
        }
        summary_md_template = Template(
            COMMON_JINJA_ENVIRONMENT,
            TemplateFile(summary_md_path, output_directory=project_documentation_path),
            summary_md_template_mapping,
        )
        init_directory = directory_with_new_file(init_directory, summary_md_template)
        # zensical.toml
        project_name = project_metadata.name
        project_authors_names = ", ".join([author.name for author in project_metadata.authors])
        zensical_toml_template_mapping: Mapping = {
            "project_name": project_name,
            "project_authors_names": project_authors_names,
            "project_site_path": PROJECT_SITE_FOLDER,
            "project_docs_path": PROJECT_DOCUMENTATION_FOLDER,
            "project_src_path": PROJECT_SOURCE_CODE_FOLDER,
            "nav_file": str(summary_md_path),
            "line_length": SOURCE_CODE_MAXIMUM_LINE_LENGTH,
            "project_src_module_path": str(
                PurePosixPath(PROJECT_SOURCE_CODE_FOLDER) / get_package_name_canonical(project_name)
            ),
            "api_reference_title": api_reference_title,
            "reference_api_reference_path": reference_api_reference_path,
        }
        zensical_toml_template = Template(
            PYTHON_JINJA_ENVIRONMENT,
            cls._zensical_toml_template_file(),
            zensical_toml_template_mapping,
        )
        init_directory = directory_with_new_file(init_directory, zensical_toml_template)
        return init_directory


@dagger.object_type
class Documenter(PythonModule):
    """Python SDK documenter."""

    @staticmethod
    def _initializer_cls() -> type[DocumenterInitializer]:
        """Initializer class.

        Returns:
            The initializer class.
        """
        return DocumenterInitializer

    @final
    @classmethod
    def __document(cls, container: Container) -> Directory:
        """Document pipeline.

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
        return container.with_exec(zensical_command).directory(PROJECT_SITE_FOLDER)

    @final
    @dagger.function(doc="Run documenter document in the project of the provided source Directory.")
    async def document(
        self, *, platform: PlatformDaggerType = PLATFORM_DAGGER_DEFAULT
    ) -> Changeset:
        """Run documenter document in the project of the provided source Directory.

        Args:
            platform: The container platform.

        Returns:
            Changeset containing generated documentation.

        Raises:
            dagger.ExecError: If documentation generation fails.
        """
        source = self.source
        exclude = []
        container = await self._exec_container(source, exclude, platform)
        return self.__document(container).changes(source)

    @final
    @dagger.function(doc="Audit source code docstrings.")
    async def audit(
        self,
        *,
        model: LLMModelDaggerType = LLM_MODEL_DAGGER_DEFAULT,
        provider: LLMProviderDaggerType = LLM_PROVIDER_DAGGER_DEFAULT,
        target_branch: TargetBranchDaggerType = TARGET_BRANCH_DAGGER_DEFAULT,
        platform: PlatformDaggerType = PLATFORM_DAGGER_DEFAULT,
    ) -> str:
        """Run LLM audit on source code docstrings.

        Args:
            model: The LLM model.
            provider: The LLM provider.
            target_branch: Git ref to compare against (e.g. main); only
              the Python files changed since then are audited. Empty audits every Python file.
            platform: The container platform.

        Returns:
            Audit report string.
        """
        exclude = []
        workspace = await self._exec_container(self.source, exclude, platform)

        # all of src/ or only the ones changed since `changed_since`.
        files = [f"{PROJECT_SOURCE_CODE_FOLDER}/"]
        if target_branch:
            # TODO we can get only those methods that have changed instead of the whole file
            #  to save LLM tokens.
            changed = await workspace.with_exec(
                [  #  Get only the Python files changed since `changed_since`
                    "sh",
                    "-c",
                    'base=$(git merge-base "$1" HEAD) && '
                    'git diff --name-only --diff-filter=d "$base" -- "$2" && '
                    'git ls-files --others --exclude-standard -- "$2"',
                    "sh",
                    target_branch,
                    f"{PROJECT_SOURCE_CODE_FOLDER}/*.py",  # src/*.py
                ]
            ).stdout()
            files = sorted(set(changed.splitlines()))
            if not files:
                return json.dumps(
                    {
                        "summary": {"total_files": 0, "total_issues": 0, "health_score": 100},
                        "issues": [],
                    }
                )
        # Extract source code context before calling LLM
        source_code_dump = await workspace.with_exec(
            [  # Find all Python files and dump their contents with line numbers for LLM audit
                "sh",
                "-c",
                'find "$@" -name "*.py" -exec echo "=== FILE: {} ===" \\; '
                "-exec awk '{printf \"%d %s\\n\", FNR, $0}' {} \\;",
                "sh",
                *files,
            ]
        ).stdout()

        # The fixed instructions go in the system prompt (a cachable prefix prompt)
        # and only the source code dump goes in the user prompt.
        documenter_audit_system_prompt_txt_template_mapping: Mapping = {
            "project_src_path": PROJECT_SOURCE_CODE_FOLDER,
        }
        documenter_audit_system_prompt_txt_template = Template(
            PYTHON_JINJA_ENVIRONMENT,
            TemplateFile(Path("documenter_audit_system_prompt.txt")),
            documenter_audit_system_prompt_txt_template_mapping,
        )
        documenter_audit_propmpt_txt_template_mapping: Mapping = {
            "source_code_dump": source_code_dump,
        }
        documenter_audit_prompt_txt_template = Template(
            PYTHON_JINJA_ENVIRONMENT,
            TemplateFile(Path("documenter_audit_prompt.txt")),
            documenter_audit_propmpt_txt_template_mapping,
        )

        system_prompt = documenter_audit_system_prompt_txt_template.contents
        prompt = documenter_audit_prompt_txt_template.contents
        report = await (
            core()
            .llm(model=model, provider=provider)
            .with_system_prompt(system_prompt)
            .with_prompt(prompt)
            .loop()
            .last_reply()
        )

        return report


sdk_module: Final = Documenter
