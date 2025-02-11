"""module package."""

from abc import ABC, abstractmethod
from collections.abc import ItemsView
from dataclasses import dataclass, field
from enum import Enum, unique
from inspect import Parameter, signature
from pathlib import Path
from typing import (
    Annotated,
    Any,
    Awaitable,
    Callable,
    Final,
    NamedTuple,
    TypedDict,
    final,
)

import dagger

from ...utils.case import camel_case_to_snake_case, snake_case_to_dash_case
from ...utils.class_name import ClassName
from ...utils.dagger.container import container_with_file
from ...utils.dagger.function import add_enum_values_as_methods
from ...utils.enum import get_enum_values
from ...utils.template import Mapping, Template, TemplateFile
from .templates import COMMON_JINJA_ENVIRONMENT

DAGGER_VERSION = "0.20.8"


class DaggerModuleMetadata(NamedTuple):
    """DaggerModuleMetadata class."""

    dagger_version: str
    git_tag_or_branch: str


VCS_PRIMARY_BRANCH: Final = "main"
VCS_USER_NAME_DEFAULT: Final = "shiryu"
VCS_USER_EMAIL_DEFAULT: Final = "shiryu@shiryu.com"

PACKAGES = set[str]


@final
class VCSUser(NamedTuple):
    """VCSUser."""

    name: str
    email: str


@final
class ProjectAuthor(NamedTuple):
    """ProjectAuthor."""

    name: str
    email: str


ProjectAuthors = set[ProjectAuthor]


ProjectType = Annotated[
    dagger.Directory, dagger.Doc("Project location"), dagger.DefaultPath(".")
]

# class Platform(Enum):
#     """Platform options."""
#
#     # Reference: https://go.dev/wiki/MinimumRequirements#amd64
#     AMD64 = "linux/amd64"
#     # Reference: https://go.dev/wiki/GoArm
#     ARM32V7 = "linux/arm/v7"
#     ARM64 = "linux/arm64"
PlatformType = Annotated[
    str, dagger.Doc("Platform config OS and architecture in a Container.")
]
PLATFORM_DEFAULT: Final = "linux/amd64"

ProjectNameType = Annotated[str, dagger.Doc("Project name")]

PROJECT_NAME_DEFAULT: Final = "shiryu-project-name-default"

IsUpdateType = Annotated[bool, dagger.Doc("Whether to update project files or not.")]


@dagger.enum_type
@final
@unique
class SCM(str, Enum):
    """SCM options."""

    GITHUB = "github"
    GITLAB = "gitlab"


SCMListType = Annotated[
    list[SCM],
    dagger.Doc(
        "Project Source Code Management (SCM) list to be targeted or configured."
    ),
]
SCM_DEFAULT = [SCM.GITLAB]


@final
class SDKModuleFunctionParameter(NamedTuple):
    """GitHubActionFunctionParameter class."""

    name: str
    option: str
    description: str
    default: str | None


SDKModuleFunctionParameters = tuple[SDKModuleFunctionParameter, ...]


@final
class GitHubAction(NamedTuple):
    """GitHubAction class."""

    id: str
    name: str
    template: Template
    function_parameters: SDKModuleFunctionParameters


GitHubActions = set[GitHubAction]


@final
class GitHubWorkflowStepInputParameter(NamedTuple):
    """GitHubWorkflowStepInputParameter class."""

    name: str
    value: str


@final
class GitHubWorkflowRunStep(NamedTuple):
    """GitHubWorkflowRunStep class."""

    id: str
    name: str
    uses: str
    with_: tuple[GitHubWorkflowStepInputParameter, ...]


@final
class GitHubWorkflowJobStep(NamedTuple):
    """GitHubWorkflowJobStep class."""

    id: str
    name: str
    uses: str
    with_: tuple[GitHubWorkflowStepInputParameter, ...]


CHECKOUT_JOB_STEP: Final = GitHubWorkflowJobStep(
    "check_out_code", "Check out code", "actions/checkout@v6", ()
)


@final
class GitHubWorkflowTriggerActionPush(TypedDict, total=False):
    """GitHubWorkflowTriggerActionPush class."""

    branches: list[str]
    tags: list[str]


@final
class GitHubWorkflowTriggerAction(TypedDict):
    """GitHubWorkflowTriggerAction class."""

    push: GitHubWorkflowTriggerActionPush | None


@final
class GitHubWorkflowProperties(NamedTuple):
    """GitHubWorkflowProperties class."""

    name: str
    on: GitHubWorkflowTriggerAction


@final
@unique
class GitHubWorkflowId(Enum):
    """GitHubWorkflowId options."""

    DEPLOY = GitHubWorkflowProperties(
        "deploy",
        {
            "push": {
                "branches": [f'"{VCS_PRIMARY_BRANCH}"'],
                "tags": ['"v[0-9]+.[0-9]+.[0-9]+"'],
            }
        },
    )
    QUALITY = GitHubWorkflowProperties("quality", {"push": None})


@final
class GitHubJobEnvironment(NamedTuple):
    """GitHubJobEnvironment class."""

    name: str
    url: str | None


@final
class GitHubWorkflowJob(NamedTuple):
    """GitHubWorkflowJob class."""

    id: str
    name: str
    environment: GitHubJobEnvironment | None
    steps: tuple[GitHubWorkflowJobStep, ...]


@dataclass
class GitHubWorkflows:
    """GitHubWorkflows class."""

    _github_workflows: dict[GitHubWorkflowId, set[GitHubWorkflowJob]] = field(
        default_factory=lambda: {}
    )

    def add(
        self, workflow_id: GitHubWorkflowId, workflow_job: GitHubWorkflowJob
    ) -> None:
        """
        Add a GitHub workflow job to a GitHub workflow identifier.

        Args:
            workflow_id: GitHub workflow identifier.
            workflow_job: GitHub workflow job.
        """
        if workflow_id in self._github_workflows:
            self._github_workflows[workflow_id].add(workflow_job)
        else:
            self._github_workflows[workflow_id] = {workflow_job}

    def items(self) -> ItemsView[GitHubWorkflowId, set[GitHubWorkflowJob]]:
        """
        Return the GitHub workflows identifiers and GitHub workflows jobs as key value pair.

        Returns:
            The GitHub workflows identifiers and GitHub workflows jobs as key value pair.
        """
        return self._github_workflows.items()


SDKModuleFunction = Callable[[Any], Awaitable[Any]]


@final
class GitHubActionsWorkflows(TypedDict):
    """GitHubActionsWorkflows class."""

    actions: GitHubActions
    workflows: GitHubWorkflows


# https://docs.gitlab.com/ci/inputs/#array-type
GitLabArrayElementType = str
GitLabArrayType = tuple[GitLabArrayElementType, ...]
GitLabScript = GitLabArrayType


@final
class GitLabArtifacts(NamedTuple):
    """GitLabArtifacts class."""

    paths: GitLabArrayType


GitLabStageRules = GitLabArrayType

GitLabStageName = str


@final
class GitLabStageJob(NamedTuple):
    """GitLabStageJob class."""

    path: str
    name: str
    extends: GitLabArrayType
    stage: GitLabStageName
    needs: GitLabArrayType
    rules: GitLabStageRules


@final
class GitLabStageProperties(NamedTuple):
    """GitLabStageProperties class."""

    name: GitLabStageName
    rules: GitLabStageRules


@final
@unique
class GitLabStageId(Enum):
    """GitLabStageId options."""

    DEPLOY = GitLabStageProperties(
        "deploy",
        (
            f'$CI_COMMIT_BRANCH == "{VCS_PRIMARY_BRANCH}"',
            r"$CI_COMMIT_TAG =~ /^v[0-9]+\.[0-9]+\.[0-9]+$/",
        ),
    )
    QUALITY = GitLabStageProperties("quality", ())


@final
class GitLabJob(NamedTuple):
    """GitLabJob class."""

    id_: str
    name: str
    template: Template
    function_parameters: SDKModuleFunctionParameters


GitLabJobs = set[GitLabJob]


@dataclass
class GitLabStages:
    """GitLabStages class."""

    _gitlab_stages: dict[GitLabStageId, set[GitLabStageJob]] = field(
        default_factory=lambda: {}
    )

    def add(self, stage_id: GitLabStageId, stage_job: GitLabStageJob) -> None:
        """
        Add a GitLab stage job to a GitLab stage identifier.

        Args:
            stage_id: GitLab stage identifier.
            stage_job: GitLab stage job.
        """
        if stage_id in self._gitlab_stages:
            self._gitlab_stages[stage_id].add(stage_job)
        else:
            self._gitlab_stages[stage_id] = {stage_job}

    def items(self) -> ItemsView[GitLabStageId, set[GitLabStageJob]]:
        """
        Return the GitLab stages identifiers and GitLab stages jobs as key value pair.

        Returns:
            The GitLab stages identifiers and GitLab stages jobs as key value pair.
        """
        return self._gitlab_stages.items()


@final
class GitLabJobsStages(TypedDict):
    """GitLabJobsStages class."""

    jobs: GitLabJobs
    stages: GitLabStages


@final
class ProjectProperties(NamedTuple):
    """ProjectProperties class."""

    name: ProjectNameType
    authors: ProjectAuthors
    version: str


@final
class SDKEnv(NamedTuple):
    """SDKEnv class."""

    container: dagger.Container
    project_properties: ProjectProperties


class SDKModuleInit(ABC):
    """SDKModuleInit class."""

    @staticmethod
    @abstractmethod
    def _sdk_name() -> str:
        """
        Get the SDK name.

        Returns the SDK name.
        """
        ...

    @final
    @staticmethod
    def _container_project_path() -> Path:
        """
        Get the container project path.

        Returns:
            The container project path.
        """
        return Path("/project")

    @classmethod
    def _container_template(
        cls, platform: PlatformType, packages: PACKAGES
    ) -> dagger.Container:
        """
        Container template.

        Args:
            platform: The container platform.
            packages: The container packages.

        Returns:
            A container template.
        """
        container_project_path_str = str(cls._container_project_path())
        apt_install = ("apt-get", "install", "--assume-yes", "--no-install-recommends")
        return (
            dagger.dag.container(platform=dagger.Platform(platform))
            .from_("debian:trixie-slim")
            .with_exec(["mkdir", "--parents", container_project_path_str])
            # .with_env_variable(name="DEBIAN_FRONTEND", value="noninteractive")
            .with_exec(["apt-get", "update"])
            .with_exec([*apt_install, *sorted(packages)])
            .with_exec(["apt-get", "autoremove"])
            .with_exec(["apt-get", "clean"])
        )

    @final
    @staticmethod
    def _source_folder() -> str:
        """
        Get the source folder name.

        Returns:
            The source folder name.
        """
        return "src"

    @final
    @classmethod
    def _container_project_source_path(cls) -> Path:
        """
        Get the container project source path.

        Returns:
            The container project source path.
        """
        return cls._container_project_path() / cls._source_folder()

    @classmethod
    def _sdk_source_code_files_folders(cls) -> set[str]:
        """
        Files and folders that contains SDK language source code.

        Returns:
            Set of files and folders with SDK language source code.
        """
        return {
            f"{cls._container_project_source_path().relative_to(cls._container_project_path())}"
        }

    @final
    @classmethod
    def _readme_md_template_file(cls) -> TemplateFile:
        """
        README.md template file.

        Returns:
            The README.md template file.
        """
        return TemplateFile(Path("README.md"), cls._container_project_path())

    @final
    @classmethod
    def _readme_md_template(cls, project_name: ProjectNameType) -> Template:
        """
        README.md template.

        Returns:
            The README.md template.
        """
        readme_md_template_mapping: Mapping = {
            "project_name": project_name.capitalize()
        }
        return Template(
            COMMON_JINJA_ENVIRONMENT,
            cls._readme_md_template_file(),
            readme_md_template_mapping,
        )

    @classmethod
    def _vcs_exclude_files_folders(cls) -> set[str]:
        """
        Files and folders to exclude from vcs.

        Returns:
            A list of files and folders to exclude from vcs.
        """
        return set()

    @classmethod
    def _base_container_base_packages(cls) -> PACKAGES:
        """
        Base container base packages.

        Returns:
            Base container base packages.
        """
        return set()

    @final
    @staticmethod
    def __get_sdk_module_function_parameters(
        sdk_module_function: SDKModuleFunction,
    ) -> SDKModuleFunctionParameters:
        """
        Get SDK module function parameters.

        Args:
            sdk_module_function: SDK module function.

        Returns:
            The SDK module function parameters.
        """
        sdk_module_function_parameters = set()
        for _, parameter in signature(sdk_module_function).parameters.items():
            parameter_name = parameter.name
            if parameter_name == "self":
                continue
            parameter_annotation = parameter.annotation
            if parameter_annotation is Parameter.empty:
                exception_message = f"Parameter {parameter_name} of function {sdk_module_function} has no annotations."
                raise Exception(exception_message)
            parameter_type = parameter_annotation.__origin__
            parameter_annotation_metadata = parameter_annotation.__metadata__
            parameter_annotation_metadata_len = len(parameter_annotation_metadata)
            parameter_description: str
            if parameter_annotation_metadata_len < 1:
                exception_message = f"Parameter {parameter_name} of function {sdk_module_function} must contain annotation metadata description"
                raise Exception(exception_message)
            if not isinstance(parameter_annotation_metadata[0], dagger.Doc):
                exception_message = f"Parameter {parameter_name} of function {sdk_module_function} must contain annotation metadata description of type {dagger.Doc}"
                raise Exception(exception_message)
            parameter_description = parameter_annotation_metadata[0].documentation
            parameter_default: str | None
            if (
                parameter_annotation_metadata_len > 1
                and parameter_type is dagger.Directory
                and isinstance(parameter_annotation_metadata[1], dagger.DefaultPath)
            ):
                # The dagger.Directory has a special default value: https://docs.dagger.io/api/default-paths/
                parameter_default = parameter_annotation_metadata[1].from_context
            else:
                _parameter_default = parameter.default
                # If default parameter is None the parameter is removed.
                if _parameter_default is None:
                    continue
                parameter_default = (
                    None
                    if _parameter_default is Parameter.empty
                    else _parameter_default
                )
            sdk_module_function_parameters.add(
                SDKModuleFunctionParameter(
                    parameter_name,
                    f"--{snake_case_to_dash_case(parameter_name)}",
                    parameter_description,
                    parameter_default if parameter_default else None,
                )
            )
        return tuple(sorted(sdk_module_function_parameters))

    @final
    @staticmethod
    def _github_folder() -> str:
        """
        Get the .github folder name.

        Returns:
            The .github folder name.
        """
        return ".github"

    @final
    @staticmethod
    def _gitlab_folder() -> str:
        """
        Get the .gitlab folder name.

        Returns:
            The .gitlab folder name.
        """
        return ".gitlab"

    @final
    @staticmethod
    def _jobs_folder() -> str:
        """
        Get the jobs folder name.

        Returns:
            The jobs folder name.
        """
        return "jobs"

    @final
    @classmethod
    def _build_github_action(
        cls,
        sdk_module: type["SDKModule"],
        sdk_module_function: SDKModuleFunction,
        dagger_version: str,
        shiryu_version: str,
        export_path: Path | None,
    ) -> GitHubAction:
        """
        Build a github action.

        Args:
            sdk_module: SDK module.
            sdk_module_function: SDK module function.
            dagger_version: Dagger version.
            shiryu_version: Shiryu version.
            export_path: Append export path after dagger call.

        Returns:
            A GitHub action.

        Raises:
            ValueError: If `export_path` argument is provided and `sdk_module_function` return type is not `dagger.Directory`.
        """
        sdk_module_name = sdk_module.name()
        sdk_module_name_title = sdk_module_name.title()
        sdk_module_function_name = sdk_module_function.__name__
        id_ = camel_case_to_snake_case(
            f"{sdk_module_name_title}{sdk_module_function_name.title()}",
        )
        name = f"{sdk_module_name_title} {sdk_module_function_name}"
        sdk_module_function_parameters = cls.__get_sdk_module_function_parameters(
            sdk_module_function
        )
        # .github/actions/<sdk_module_function_name>/action.yml
        export_chain = []
        if export_path is not None:
            sdk_module_function_return_type = signature(
                sdk_module_function
            ).return_annotation
            if (
                sdk_module_function_return_type is Parameter.empty
                or sdk_module_function_return_type is not dagger.Directory
            ):
                exception_message = f"Invalid `export_path` argument for SDK module function {sdk_module_function_name} from module {sdk_module_name} with return type {sdk_module_function_return_type}"
                raise ValueError(exception_message)
            # TODO: Check that the return type is of type dagger.
            export_chain.append(f"export --path=./{export_path}")
        action_yml_template_mapping: Mapping = {
            "function": sdk_module_function_name,
            "module": sdk_module_name,
            "shiryu_version": {"default": shiryu_version},
            "sdk_language": {"default": cls._sdk_name()},
            "parameters": sdk_module_function_parameters,
            "steps": (
                GitHubWorkflowRunStep(
                    f"call_dagger_{id_}",
                    f"Call Dagger {name}",
                    "dagger/dagger-for-github@v8.4.0",
                    (
                        GitHubWorkflowStepInputParameter(
                            "version", f'"v{dagger_version}"'
                        ),
                        GitHubWorkflowStepInputParameter("verb", "call"),
                        GitHubWorkflowStepInputParameter(
                            "module",
                            "github.com/fvonbergen/shiryu@${{ inputs.shiryu_version }}",
                        ),
                        GitHubWorkflowStepInputParameter(
                            "args",
                            " ".join(
                                [
                                    f"${{{{ inputs.sdk_language }}}} {sdk_module_name} {sdk_module_function_name}",
                                    *[
                                        f'{parameter.option}="${{{{ inputs.{parameter.name} }}}}"'
                                        for parameter in sdk_module_function_parameters
                                    ],
                                    *export_chain,
                                ]
                            ),
                        ),
                        GitHubWorkflowStepInputParameter(
                            "cloud-token", "${{ inputs.dagger_cloud_token }}"
                        ),
                    ),
                ),
            ),
        }
        action_yml_template = Template(
            COMMON_JINJA_ENVIRONMENT,
            TemplateFile(
                Path("action.yml"),
                cls._container_project_path() / cls._github_folder() / "actions" / id_,
            ),
            action_yml_template_mapping,
        )
        return GitHubAction(
            id_, name, action_yml_template, sdk_module_function_parameters
        )

    @final
    @classmethod
    def _build_github_workflow_job(
        cls,
        github_action: GitHubAction,
        shiryu_version: str,
        job_environment: GitHubJobEnvironment | None,
        post_steps: tuple[GitHubWorkflowJobStep, ...],
    ) -> GitHubWorkflowJob:
        """
        Build a GitHub workflow job.

        Args:
            github_action: The GitHub action.
            shiryu_version: Shiryu version.
            job_environment: GitHub job environment.
            post_steps: GitHub workflow job post action job steps.

        Returns:
            A GitHub workflow job.
        """
        pre_steps = (CHECKOUT_JOB_STEP,)
        action_step_input_parameters_generator = (
            GitHubWorkflowStepInputParameter(parameter.name, f'"{parameter.default}"')
            if parameter.default is not None
            else GitHubWorkflowStepInputParameter(
                parameter.name, f"${{{{ secrets.{parameter.name.upper()} }}}}"
            )
            for parameter in github_action.function_parameters
        )
        id_ = github_action.id
        name = github_action.name
        action_step = GitHubWorkflowJobStep(
            id_,
            name,
            f'"./{github_action.template.template_file.output_path.parent.relative_to(cls._container_project_path())}"',
            (
                *(
                    GitHubWorkflowStepInputParameter(
                        "dagger_cloud_token", "${{ secrets.DAGGER_CLOUD_TOKEN }}"
                    ),
                    GitHubWorkflowStepInputParameter(
                        "shiryu_version", f'"{shiryu_version}"'
                    ),
                    GitHubWorkflowStepInputParameter(
                        "sdk_language", f'"{cls._sdk_name()}"'
                    ),
                ),
                *tuple(action_step_input_parameters_generator),
            ),
        )
        return GitHubWorkflowJob(
            id_, name, job_environment, (*pre_steps, action_step, *post_steps)
        )

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
        return {"actions": set(), "workflows": GitHubWorkflows()}

    @final
    @classmethod
    def _build_gitlab_job(
        cls,
        sdk_module: type["SDKModule"],
        sdk_module_function: SDKModuleFunction,
        shiryu_version: str,
        pre_script: GitLabScript,
        export_path: Path | None,
        post_script: GitLabScript,
        artifacts: GitLabArtifacts | None,
    ) -> GitLabJob:
        """
        Build a GitLab job.

        Args:
            sdk_module: SDK module.
            sdk_module_function: SDK module function.
            shiryu_version: Shiryu version.
            pre_script: GitLab commands to run before dagger module command in script section.
            export_path: Append export path after dagger call.
            post_script: GitLab commands to run after dagger module command in script section.
            artifacts: GitLab artifacts section.

        Returns:
            A GitLab job.

        Raises:
            ValueError: If `export_path` argument is provided and `sdk_module_function` return type is not `dagger.Directory`.
        """
        sdk_module_name = sdk_module.name()
        sdk_module_function_name = sdk_module_function.__name__
        id_ = camel_case_to_snake_case(
            f"{sdk_module_name.title()}{sdk_module_function_name.title()}",
        )
        sdk_module_function_parameters = cls.__get_sdk_module_function_parameters(
            sdk_module_function
        )
        export_chain = []
        if export_path is not None:
            sdk_module_function_return_type = signature(
                sdk_module_function
            ).return_annotation
            if (
                sdk_module_function_return_type is Parameter.empty
                or sdk_module_function_return_type is not dagger.Directory
            ):
                exception_message = f"Invalid `export_path` argument for SDK module function {sdk_module_function_name} from module {sdk_module_name} with return type {sdk_module_function_return_type}"
                raise ValueError(exception_message)
            # TODO: Check that the return type is of type dagger.
            export_chain.append(f"export --path=./{export_path}")
        job_name = f".{id_}"
        job_yml_template_mapping: Mapping = {
            "name": job_name,
            "shiryu_version": {"default": shiryu_version},
            "sdk_language": {"default": cls._sdk_name()},
            "parameters": sdk_module_function_parameters,
            "scripts": (
                *pre_script,
                " ".join(
                    [
                        f"dagger --mod=gitlab.com/fvonbergen1/shiryu@${{SHIRYU_VERSION}} call ${{SDK_LANGUAGE}} {sdk_module_name} {sdk_module_function_name}",
                        *[
                            f'{parameter.option}="${{{parameter.name.upper()}}}"'
                            for parameter in sdk_module_function_parameters
                        ],
                        *export_chain,
                    ],
                ),
                *post_script,
            ),
            "artifacts": artifacts,
        }
        job_yml_template = Template(
            COMMON_JINJA_ENVIRONMENT,
            TemplateFile(
                Path("gitlab_job.yml"),
                cls._container_project_path()
                / cls._gitlab_folder()
                / cls._jobs_folder(),
                Path(f"{job_name}.yml"),
            ),
            job_yml_template_mapping,
        )
        return GitLabJob(
            id_, job_name, job_yml_template, sdk_module_function_parameters
        )

    @final
    @classmethod
    def _build_gitlab_stage_job(
        cls, gitlab_stage_id: GitLabStageId, gitlab_job: GitLabJob
    ) -> GitLabStageJob:
        """
        Build a GitLab stage job.

        Args:
            gitlab_stage_id: The GitLab stage id.
            gitlab_job: The GitLab job.

        Returns:
            A GitLab stage job.
        """
        gitlab_stage_name = gitlab_stage_id.name.lower()
        return GitLabStageJob(
            str(
                gitlab_job.template.template_file.output_path.relative_to(
                    cls._container_project_path()
                )
            ),
            f"{gitlab_stage_name}_{gitlab_job.id_}",
            (gitlab_job.name,),
            gitlab_stage_name,
            (),
            gitlab_stage_id.value.rules,
        )

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
        dagger_name = "dagger"
        job_name = f".{dagger_name}"
        dagger_yml_template_mapping: Mapping = {"dagger_version": dagger_version}
        dagger_yml_template = Template(
            COMMON_JINJA_ENVIRONMENT,
            TemplateFile(
                Path(f"{job_name}.yml"),
                cls._container_project_path()
                / cls._gitlab_folder()
                / cls._jobs_folder(),
            ),
            dagger_yml_template_mapping,
        )
        dagger_job = GitLabJob(dagger_name, job_name, dagger_yml_template, ())
        return {"jobs": {dagger_job}, "stages": GitLabStages()}

    @classmethod
    async def _get_dagger_module_metadata(cls) -> DaggerModuleMetadata:
        """
        Returns the module metadata.

        Return:
            The module metadata.
        """
        module_source = dagger.dag.current_module().source()
        # Get locked dagger version.
        # Alternative 1
        # pylock.toml file: actually it is the dagger python sdk version not the dagger engine.
        # py_lock_file_contents = module_source.file("pylock.toml").contents()
        # py_lock_file = tomllib.loads(py_lock_file_contents)
        # dagger_pkg = next(
        #     (
        #         package
        #         for package in py_lock_file.get("packages", [])
        #         if package.get("name") == "dagger-io"
        #     ),
        #     None,
        # )
        # if dagger_pkg is None:
        #     exception_message = "dagger-io not found in py.lock"
        #     raise Exception(exception_message)
        # dagger_version = dagger_pkg.get("version")
        # Alternative 2
        # Read it from the dagger.json. It is the minimal dagger engine requirement. Not useful.
        # Alternative 3
        # Read it from the running engine
        # dagger_version = await dagger.dag.version()
        # Alternative 4
        # Use lockfile mechanism from next versions:
        # - https://github.com/dagger/dagger/pull/11995
        # - https://github.com/dagger/dagger/pull/12046
        # Alternative 5
        # Use a hard coded version
        dagger_version = DAGGER_VERSION
        # Get module exact git tag. Falls back to the branch name if the commit is not tagged.
        container_project_path_str = str(cls._container_project_path())
        container = (
            cls._container_template(PLATFORM_DEFAULT, {"git"})
            .with_workdir(container_project_path_str)
            .with_directory(container_project_path_str, module_source)
        )
        try:
            module_tag = await container.with_exec(
                ["git", "describe", "--tags", "--exact-match"]
            ).stdout()
            return DaggerModuleMetadata(
                dagger_version=dagger_version, git_tag_or_branch=module_tag.strip()
            )
        except dagger.QueryError:
            module_branch = await container.with_exec(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"]
            ).stdout()
            return DaggerModuleMetadata(
                dagger_version=dagger_version, git_tag_or_branch=module_branch.strip()
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
        container = sdk_env.container
        project_properties = sdk_env.project_properties
        # README.md
        readme_md_template = cls._readme_md_template(project_properties.name)
        container = await container_with_file(
            container, readme_md_template, is_overwrite
        )
        # CHANGELOG.md
        changelog_md_template_mapping: Mapping = {}
        changelog_md_template = Template(
            COMMON_JINJA_ENVIRONMENT,
            TemplateFile(Path("CHANGELOG.md"), cls._container_project_path()),
            changelog_md_template_mapping,
        )
        container = await container_with_file(
            container, changelog_md_template, is_overwrite
        )
        # .gitignore
        project_source_path_str = str(cls._container_project_source_path())
        _gitignore_template_mapping: Mapping = {
            "exclude": sorted(cls._vcs_exclude_files_folders())
        }
        _gitignore_template = Template(
            COMMON_JINJA_ENVIRONMENT,
            TemplateFile(Path(".gitignore"), cls._container_project_path()),
            _gitignore_template_mapping,
        )
        container = await container_with_file(
            container, _gitignore_template, is_overwrite
        )
        # src
        if not await container.exists(
            project_source_path_str, expected_type=dagger.ExistsType.DIRECTORY_TYPE
        ):
            container = container.with_exec(
                ["mkdir", "--parents", project_source_path_str]
            )
        if len(scm):
            shiryu_metadata = await cls._get_dagger_module_metadata()
            dagger_version = shiryu_metadata.dagger_version
            shiryu_version = shiryu_metadata.git_tag_or_branch
            if SCM.GITHUB in scm:
                # .github/{actions, workflows}/*
                github_actions_workflows = cls._github_actions_workflows(
                    dagger_version, shiryu_version
                )
                # .github/actions/*/action.yml
                github_actions = github_actions_workflows["actions"]
                # TODO: parallelize
                for github_action in github_actions:
                    container = await container_with_file(
                        container, github_action.template, is_overwrite
                    )
                # .github/workflows/*.yml
                github_workflows = github_actions_workflows["workflows"]
                # TODO: parallelize
                for github_workflow, github_workflow_jobs in github_workflows.items():
                    github_workflow_name = github_workflow.value.name
                    workflow_name = f"{github_workflow_name}.yml"
                    github_workflow_yml_template_mapping: Mapping = {
                        "name": github_workflow_name,
                        "on": github_workflow.value.on,
                        "jobs": github_workflow_jobs,
                    }
                    github_workflow_yml_template = Template(
                        COMMON_JINJA_ENVIRONMENT,
                        TemplateFile(
                            Path("github_workflow.yml"),
                            cls._container_project_path()
                            / cls._github_folder()
                            / "workflows",
                            Path(workflow_name),
                        ),
                        github_workflow_yml_template_mapping,
                    )
                    container = await container_with_file(
                        container, github_workflow_yml_template, is_overwrite
                    )
            if SCM.GITLAB in scm:
                # .gitlab/{jobs, stages}/*
                gitlab_jobs_stages = cls._gitlab_jobs_stages(
                    dagger_version, shiryu_version
                )
                # .gitlab/jobs/*.yml
                gitlab_jobs = gitlab_jobs_stages["jobs"]
                # TODO: parallelize
                for gitlab_job in gitlab_jobs:
                    container = await container_with_file(
                        container, gitlab_job.template, is_overwrite
                    )
                # .gitlab/stages/*.yml
                gitlab_ci_stages: dict[str, str] = {}
                gitlab_stages = gitlab_jobs_stages["stages"]
                # TODO: parallelize
                for gitlab_stage, gitlab_stage_jobs in gitlab_stages.items():
                    gitlab_stage_name = gitlab_stage.value.name
                    gitlab_stage_file_name = f"{gitlab_stage_name}.yml"
                    gitlab_stage_yml_template_mapping: Mapping = {
                        "jobs": gitlab_stage_jobs
                    }
                    gitlab_stage_yml_template = Template(
                        COMMON_JINJA_ENVIRONMENT,
                        TemplateFile(
                            Path("gitlab_stage.yml"),
                            cls._container_project_path()
                            / cls._gitlab_folder()
                            / "stages",
                            Path(gitlab_stage_file_name),
                        ),
                        gitlab_stage_yml_template_mapping,
                    )
                    container = await container_with_file(
                        container, gitlab_stage_yml_template, is_overwrite
                    )
                    gitlab_ci_stages[gitlab_stage_name] = str(
                        gitlab_stage_yml_template.template_file.output_path.relative_to(
                            cls._container_project_path()
                        )
                    )
                # .gitlab-ci.yml
                # .mapping added in Python 3.10; Mypy stubs don't yet expose it on ItemsView
                stages = [
                    stage_name.lower()
                    for stage_name in gitlab_ci_stages.items().mapping.keys()  # type: ignore[attr-defined]
                ]
                paths = gitlab_ci_stages.items().mapping.values()  # type: ignore[attr-defined]
                _gitlab_ci_yml_template_mapping: Mapping = {
                    "stages": stages,
                    "paths": paths,
                }
                _gitlab_ci_yml_template = Template(
                    COMMON_JINJA_ENVIRONMENT,
                    TemplateFile(
                        Path(".gitlab-ci.yml"),
                        cls._container_project_path(),
                    ),
                    _gitlab_ci_yml_template_mapping,
                )
                container = await container_with_file(
                    container, _gitlab_ci_yml_template, is_overwrite
                )
            else:
                # TODO: no scm selected?
                ...

        return SDKEnv(container, project_properties)


@dagger.object_type
class SDKModule(ClassName, SDKModuleInit):
    """SDKModule class."""

    @classmethod
    def _base_container_base_packages(cls) -> PACKAGES:
        """
        Base container base packages.

        Returns:
            Base container base packages.
        """
        return {"git"}

    @classmethod
    def _base_container(cls, platform: PlatformType) -> dagger.Container:
        """
        Base container.

        Args:
            platform: The container platform.

        Returns:
            A base container.
        """
        return cls._container_template(platform, cls._base_container_base_packages())

    @final
    @classmethod
    async def __vcs_init(
        cls, container: dagger.Container
    ) -> tuple[dagger.Container, VCSUser]:
        """
        Initialize the container with the VCS.

        Args:
            container: SDK container to initialize.

        Returns:
            Returns an SDK container with the VCS initialized and the VCS user.
        """
        # TODO: We should check if project is already initialized or not.
        container = container.with_exec(
            [
                "git",
                "init",
                "--initial-branch",
                VCS_PRIMARY_BRANCH,
                str(cls._container_project_path()),
            ]
        )
        try:
            vcs_user_name_stdout = await container.with_exec(
                ["git", "config", "user.name"]
            ).stdout()
            vcs_user_name = vcs_user_name_stdout.strip()
        except dagger.QueryError:
            vcs_user_name = VCS_USER_NAME_DEFAULT
            container = container.with_exec(
                ["git", "config", "user.name", vcs_user_name]
            )
        try:
            vcs_user_email_stdout = await container.with_exec(
                ["git", "config", "user.email"]
            ).stdout()
            vcs_user_email = vcs_user_email_stdout.strip()
        except dagger.QueryError:
            vcs_user_email = VCS_USER_EMAIL_DEFAULT
            container = container.with_exec(
                ["git", "config", "user.email", vcs_user_email]
            )
        return (container, VCSUser(vcs_user_name, vcs_user_email))

    @final
    @classmethod
    async def __base_container_project(
        cls, project: ProjectType | None, platform: PlatformType
    ) -> tuple[dagger.Container, VCSUser]:
        """
        Base container with initialized project.

        Args:
            project: Project directory.
            platform: The container platform.

        Returns:
            A base container with initialized project and the VCS user.
        """
        container_project_path_str = str(cls._container_project_path())
        container = cls._base_container(platform).with_workdir(
            container_project_path_str
        )
        if project is not None:
            container = container.with_directory(container_project_path_str, project)
        return await cls.__vcs_init(container)

    @classmethod
    @abstractmethod
    async def _sdk_module_init(
        cls,
        container: dagger.Container,
        project_name: ProjectNameType | None,
        vcs_user: VCSUser,
        is_overwrite: bool,
        scm: SCMListType,
    ) -> SDKEnv:
        """
        Initialize the SDK module environment.

        Args:
            container: SDK container to initialize.
            project_name: Project name.
            vcs_user: VCS user.
            is_overwrite: Whether to overwrite files or not.
            scm: Project Source Code Management (SCM) list to be targeted or configured.

        Returns:
            Returns an SDK module environment.
        """
        ...

    @final
    @classmethod
    async def sdk_module_env(
        cls, project: ProjectType, platform: PlatformType
    ) -> SDKEnv:
        """
        Build the SDK environment.

        Args:
            project: Project directory.
            platform: The container platform.

        Returns:
            Returns an SDK module environment.
        """
        scm: SCMListType = []
        is_overwrite = False
        container, vcs_user = await cls.__base_container_project(project, platform)
        sdk_env = await cls._sdk_module_init(
            container, None, vcs_user, is_overwrite, scm
        )
        return await cls._module_init(sdk_env, is_overwrite, scm)

    @final
    @dagger.function
    async def init(
        self,
        project_name: ProjectNameType,
        project: ProjectType,
        is_update: IsUpdateType = False,
        scm: SCMListType = SCM_DEFAULT,
        platform: PlatformType = PLATFORM_DEFAULT,
    ) -> dagger.Directory:
        """Returns an initialized directory for the SDK module."""
        is_overwrite = is_update
        # We want the container without the project directory mounted in it
        container, vcs_user = await self.__base_container_project(
            project if is_update else None, platform
        )
        sdk_env = await self._sdk_module_init(
            container, project_name, vcs_user, is_overwrite, scm
        )
        container, _ = await self._module_init(sdk_env, is_overwrite, scm)
        directory = container.directory(str(self._container_project_path()))
        if is_update:
            directory = directory.filter(
                exclude=[str(self._container_project_path() / ".git/")]
            )
        return directory


@final
class SDKModuleModule(NamedTuple):
    """SDKModuleModule class."""

    init: type[SDKModuleInit]
    module: type[SDKModule]


@dagger.object_type
class SDK(ClassName):
    """SDK class."""

    ...


def get_sdk_language(
    sdk_name: str, sdk_module: type[SDKModule], sdk_modules: set[SDKModuleModule]
) -> type[SDK]:
    """
    Get SDK language.

    Args:
        sdk_name: SDK name.
        sdk_module: SDK module.
        sdk_modules: SDK modules.

    Returns:
        A SDK Language class.
    """
    sdk_module_init_base_dict: dict[str, type[SDKModuleInit]] = {}
    sdk_module_options_dict: dict[str, type[SDKModule]] = {}
    for sdk_module_init, sdk_module in sdk_modules:
        sdk_module_name = sdk_module.name()
        sdk_module_init_base_dict[sdk_module_name] = sdk_module_init
        sdk_module_options_dict[sdk_module_name.upper()] = sdk_module

    SDKModuleInitBaseOptions = final(  # noqa: N806
        unique(
            Enum(  # type: ignore[type-var]
                "SDKModuleInitBaseOptions",
                {key.upper(): key for key in sdk_module_init_base_dict.keys()},
            )
        )
    )
    SDKModuleInitBaseOptions.__doc__ = """SDKModuleInitBase options."""

    SDK_MODULE_INIT_BASE_DEFAULT: Final = None  # noqa: N806
    SDKModuleInitBaseType = Annotated[  # noqa: N806
        list[str] | None,
        dagger.Doc(
            f"{sdk_name} SDK modules to initialize (options {', '.join(get_enum_values(SDKModuleInitBaseOptions))}). (default {SDK_MODULE_INIT_BASE_DEFAULT})"
        ),
    ]

    @dagger.function
    async def init(
        self,
        project_name: ProjectNameType,
        project: ProjectType,
        is_update: IsUpdateType = False,
        scm: SCMListType = SCM_DEFAULT,
        platform: PlatformType = PLATFORM_DEFAULT,
        modules: SDKModuleInitBaseType = SDK_MODULE_INIT_BASE_DEFAULT,  # pyright: ignore [reportInvalidTypeForm]
    ) -> dagger.Directory:
        """Python SDK initializer."""
        sdk_module_init_base_set: set[type[SDKModuleInit]]
        if modules is None:
            sdk_module_init_base_set = set(sdk_module_init_base_dict.values())
        else:
            sdk_module_init_base_set = set(
                {
                    module: sdk_module_init_base_dict[module] for module in modules
                }.values()
            )
        Init = final(  # noqa: N806
            dagger.object_type(
                type("Init", (sdk_module, *sdk_module_init_base_set), {})
            )
        )
        Init.__doc__ = f"{sdk_name} SDK initializer."
        return await Init().init(project_name, project, is_update, scm, platform)

    SDKModuleOptions = final(  # noqa: N806
        unique(Enum("SDKModuleOptions", sdk_module_options_dict))  # type: ignore[type-var]
    )
    SDKModuleOptions.__doc__ = """SDKModule options."""
    sdk_language = final(
        dagger.object_type(
            # mypy bug: https://github.com/python/mypy/issues/17147
            add_enum_values_as_methods(SDKModuleOptions)(  # type: ignore[arg-type]
                type(sdk_name, (SDK,), {"init": final(init)})
            )
        )
    )
    sdk_language.__doc__ = f"""{sdk_name} SDK."""
    return sdk_language
