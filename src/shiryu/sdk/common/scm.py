"""scm module."""

from collections.abc import Awaitable, Callable, ItemsView, KeysView, ValuesView
from dataclasses import asdict, dataclass, field, replace
from enum import Enum, StrEnum, unique
from inspect import Parameter, signature
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Any, Final, Self, final

import dagger

from ...utils.case import camel_case_to_snake_case, snake_case_to_dash_case
from ...utils.dagger.directory import directory_with_new_file
from ...utils.template import Mapping, Template, TemplateFile
from .templates import COMMON_JINJA_ENVIRONMENT
from .vcs import VCS_PRIMARY_BRANCH

_PROJECT_DIRECTORY_ANNOTATION: Final = "Project directory path."


@final
@dataclass(frozen=True, slots=True)
class SDKModuleFunctionParameter:
    """GitHubActionFunctionParameter class."""

    name: str
    option: str
    description: str
    default: str | None


SDKModuleFunctionParameters = tuple[SDKModuleFunctionParameter, ...]

SDKModuleFunction = Callable[..., Awaitable[Any]]


def get_sdk_module_function_parameters(
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
    for parameter in signature(sdk_module_function).parameters.values():
        parameter_name = parameter.name
        if parameter_name == "self":
            continue
        parameter_annotation = parameter.annotation
        if parameter_annotation is Parameter.empty:
            exception_message = (
                f"Parameter {parameter_name} of function {sdk_module_function} has no annotations."
            )
            raise Exception(exception_message)
        parameter_type = parameter_annotation.__origin__
        parameter_annotation_metadata = parameter_annotation.__metadata__
        parameter_annotation_metadata_len = len(parameter_annotation_metadata)
        parameter_description: str
        if parameter_annotation_metadata_len < 1:
            exception_message = (
                f"Parameter {parameter_name} of function {sdk_module_function} must contain "
                "annotation metadata description"
            )
            raise Exception(exception_message)
        if not isinstance(parameter_annotation_metadata[0], dagger.Doc):
            exception_message = (
                f"Parameter {parameter_name} of function {sdk_module_function} must contain "
                f"annotation metadata description of type {dagger.Doc}"
            )
            raise Exception(exception_message)
        parameter_description = parameter_annotation_metadata[0].documentation
        parameter_default: str | None
        # TODO: dagger.DefaultPath doesn't work as expected. It defaults to the module directory
        # context where the dagger.json lives. For this reason we set ".", to the specific project
        # directory parameter which means that the current working directory.
        if (
            parameter_type is dagger.Directory
            and parameter_annotation_metadata[0] == _PROJECT_DIRECTORY_ANNOTATION
            # and isinstance(parameter_annotation_metadata[1], dagger.DefaultPath)
        ):
            # The dagger.Directory has a special default value: https://docs.dagger.io/api/default-paths/
            # parameter_default = parameter_annotation_metadata[1].from_context
            parameter_default = "."
        else:
            _parameter_default = parameter.default
            # If default parameter is None the parameter is removed.
            if _parameter_default is None:
                continue
            parameter_default = (
                None if _parameter_default is Parameter.empty else _parameter_default
            )
        sdk_module_function_parameters.add(
            SDKModuleFunctionParameter(
                parameter_name,
                f"--{snake_case_to_dash_case(parameter_name)}",
                parameter_description,
                parameter_default,
            )
        )
    return tuple(sorted(sdk_module_function_parameters, key=lambda param: param.name))


@final
@dataclass(frozen=True, slots=True)
class GitHubAction:
    """GitHubAction class."""

    id: str
    name: str
    template: Template
    function_parameters: SDKModuleFunctionParameters


GitHubActions = frozenset[GitHubAction]


@final
@dataclass(frozen=True, slots=True)
class GitHubWorkflowStepInputParameter:
    """GitHubWorkflowStepInputParameter class."""

    name: str
    value: str


@final
@dataclass(frozen=True, slots=True)
class GitHubWorkflowRunStep:
    """GitHubWorkflowRunStep class."""

    id: str
    name: str
    uses: str
    with_: tuple[GitHubWorkflowStepInputParameter, ...]


@final
@dataclass(frozen=True, slots=True)
class GitHubWorkflowJobStep:
    """GitHubWorkflowJobStep class."""

    id: str
    name: str
    uses: str
    with_: tuple[GitHubWorkflowStepInputParameter, ...]


CHECKOUT_JOB_STEP: Final = GitHubWorkflowJobStep(
    "check_out_code", "Check out code", "actions/checkout@v6", ()
)


@final
@dataclass(frozen=True, slots=True)
class GitHubWorkflowTriggerActionPush:
    """GitHubWorkflowTriggerActionPush class."""

    branches: tuple[str, ...]
    tags: tuple[str, ...]


@final
@dataclass(frozen=True, slots=True)
class GitHubWorkflowTriggerAction:
    """GitHubWorkflowTriggerAction class."""

    push: GitHubWorkflowTriggerActionPush | None


@final
@dataclass(frozen=True, slots=True)
class GitHubWorkflowProperties:
    """GitHubWorkflowProperties class."""

    name: str
    on: GitHubWorkflowTriggerAction


@final
@unique
class GitHubWorkflowId(Enum):
    """GitHubWorkflowId options."""

    DEPLOY = GitHubWorkflowProperties(
        "deploy",
        GitHubWorkflowTriggerAction(
            push=GitHubWorkflowTriggerActionPush(
                branches=(f'"{VCS_PRIMARY_BRANCH}"',), tags=('"v[0-9]+.[0-9]+.[0-9]+"',)
            )
        ),
    )
    QUALITY = GitHubWorkflowProperties("quality", GitHubWorkflowTriggerAction(push=None))


@final
@dataclass(frozen=True, slots=True)
class GitHubJobEnvironment:
    """GitHubJobEnvironment class."""

    name: str
    url: str | None


@final
@dataclass(frozen=True, slots=True)
class GitHubWorkflowJob:
    """GitHubWorkflowJob class."""

    id: str
    name: str
    environment: GitHubJobEnvironment | None
    steps: tuple[GitHubWorkflowJobStep, ...]


@final
@dataclass(frozen=True, slots=True)
class GitHubWorkflows:
    """GitHubWorkflows class with enforced read-only structural immutability."""

    _github_workflows: MappingProxyType[GitHubWorkflowId, frozenset[GitHubWorkflowJob]] = field(
        default_factory=lambda: MappingProxyType({})
    )

    def add(
        self, workflow_id: GitHubWorkflowId, workflow_job: GitHubWorkflowJob
    ) -> "GitHubWorkflows":
        """
        Add a GitHub workflow job to a GitHub workflow identifier.

        Args:
            workflow_id: GitHub workflow identifier.
            workflow_job: GitHub workflow job.

        Returns:
            A new GitHubWorkflows instance containing the updated state.
        """
        current_jobs: frozenset[GitHubWorkflowJob] = self._github_workflows.get(
            workflow_id, frozenset()
        )

        # Unpack the proxy into a temporary flat dict to safely add the data
        updated_dict: dict[GitHubWorkflowId, frozenset[GitHubWorkflowJob]] = dict(
            self._github_workflows
        )
        updated_dict[workflow_id] = current_jobs | frozenset([workflow_job])

        return GitHubWorkflows(MappingProxyType(updated_dict))

    def merge(self, other: "GitHubWorkflows") -> "GitHubWorkflows":
        """
        Merge another GitHubWorkflows instance into a brand new state.

        Args:
            other: Another GitHubWorkflows instance to merge.

        Returns:
            A new GitHubWorkflows instance representing the union of both states.
        """
        merged_dict: dict[GitHubWorkflowId, frozenset[GitHubWorkflowJob]] = dict(
            self._github_workflows
        )
        for wf_id, jobs in other.items():
            merged_dict[wf_id] = merged_dict.get(wf_id, frozenset()) | jobs

        return GitHubWorkflows(MappingProxyType(merged_dict))

    def items(self) -> ItemsView[GitHubWorkflowId, frozenset[GitHubWorkflowJob]]:
        """
        Return the GitHub workflows identifiers and GitHub workflows jobs as key-value pair.

        Returns:
            The GitHub workflows identifiers and GitHub workflows jobs.
        """
        return self._github_workflows.items()

    def keys(self) -> KeysView[GitHubWorkflowId]:
        """
        Return the GitHub workflows identifiers.

        Returns:
            The GitHub workflows identifiers.
        """
        return self._github_workflows.keys()

    def values(self) -> ValuesView[frozenset[GitHubWorkflowJob]]:
        """
        Return the GitHub workflows jobs.

        Returns:
            The GitHub workflows jobs.
        """
        return self._github_workflows.values()

    def evolve(
        self,
        github_workflows: MappingProxyType[GitHubWorkflowId, frozenset[GitHubWorkflowJob]]
        | None = None,
    ) -> "GitHubWorkflows":
        """
        Type-safe evolution for the underlying GitHub workflows.

        Args:
            github_workflows: GitHub workflows.

        Returns:
            A new GitHubWorkflows instance with the modified or current state.
        """
        return replace(
            self,
            _github_workflows=github_workflows
            if github_workflows is not None
            else self._github_workflows,
        )


@final
@dataclass(frozen=True, slots=True)
class GitHubActionsWorkflows:
    """GitHubActionsWorkflows class."""

    actions: GitHubActions
    workflows: GitHubWorkflows

    def evolve(
        self,
        actions: GitHubActions | None = None,
        workflows: GitHubWorkflows | None = None,
    ) -> Self:
        """
        Type-safe evolution for GitHub actions and workflows tracking.

        Args:
            actions: GitHub actions.
            workflows: GitHub workflows.

        Returns:
            A new GitHubActionsWorkflows instance with the modified or current state.
        """
        return replace(
            self,
            actions=actions if actions is not None else self.actions,
            workflows=workflows if workflows is not None else self.workflows,
        )


# https://docs.gitlab.com/ci/inputs/#array-type
GitLabArrayElementType = str
GitLabArrayType = tuple[GitLabArrayElementType, ...]
GitLabScript = GitLabArrayType


@final
@dataclass(frozen=True, slots=True)
class GitLabArtifacts:
    """GitLabArtifacts class."""

    paths: GitLabArrayType


GitLabStageRules = GitLabArrayType

GitLabStageName = str


@final
@dataclass(frozen=True, slots=True)
class GitLabStageJob:
    """GitLabStageJob class."""

    path: str
    name: str
    extends: GitLabArrayType
    stage: GitLabStageName
    needs: GitLabArrayType
    rules: GitLabStageRules


@final
@dataclass(frozen=True, slots=True)
class GitLabStageProperties:
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
@dataclass(frozen=True, slots=True)
class GitLabJob:
    """GitLabJob class."""

    id_: str
    name: str
    template: Template
    function_parameters: SDKModuleFunctionParameters


GitLabJobs = frozenset[GitLabJob]


@final
@dataclass(frozen=True, slots=True)
class GitLabStages:
    """
    GitLabStages class with enforced read-only structural immutability.

    Attributes:
        _gitlab_stages: Internal gitlab-stages mapping
    """

    _gitlab_stages: MappingProxyType[GitLabStageId, frozenset[GitLabStageJob]] = field(
        default_factory=lambda: MappingProxyType({})
    )

    def add(self, stage_id: GitLabStageId, stage_job: GitLabStageJob) -> "GitLabStages":
        """
        Add a collection of GitLab stage jobs to a GitLab stage identifier.

        Args:
            stage_id: GitLab stage identifier.
            stage_job: GitLabStage job to add to the GitLab stage identifier.

        Returns:
            A new GitLabStages instance containing the updated state.
        """
        current_jobs: frozenset[GitLabStageJob] = self._gitlab_stages.get(stage_id, frozenset())
        updated_dict: dict[GitLabStageId, frozenset[GitLabStageJob]] = dict(self._gitlab_stages)
        updated_dict[stage_id] = current_jobs | frozenset([stage_job])
        return GitLabStages(MappingProxyType(updated_dict))

    def merge(self, other: "GitLabStages") -> "GitLabStages":
        """
        Merge another GitLabStages instance into a brand new state.

        Args:
            other: A GitLabStages instance to merge into this one.

        Returns:
            A new GitLabStages instance representing the union of both states.
        """
        merged_dict: dict[GitLabStageId, frozenset[GitLabStageJob]] = dict(self._gitlab_stages)
        for st_id, jobs in other.items():
            merged_dict[st_id] = merged_dict.get(st_id, frozenset()) | jobs
        return GitLabStages(MappingProxyType(merged_dict))

    def items(self) -> ItemsView[GitLabStageId, frozenset[GitLabStageJob]]:
        """
        Return the GitLab stage identifier and the GitLab stage job as key-value pairs.

        Returns:
            The GitLab stage identifier and the GitLab stage job as key-value pairs.
        """
        return self._gitlab_stages.items()

    def evolve(
        self,
        gitlab_stages: MappingProxyType[GitLabStageId, frozenset[GitLabStageJob]] | None = None,
    ) -> "GitLabStages":
        """
        Type-safe evolution for the GitLab stages.

        Args:
            gitlab_stages: GitLab stages.

        Returns:
            Anew GitLabStages instance with the modified or current state.
        """
        return replace(
            self,
            _gitlab_stages=gitlab_stages if gitlab_stages is not None else self._gitlab_stages,
        )


@final
@dataclass(frozen=True, slots=True)
class GitLabJobsStages:
    """GitLabJobsStages class."""

    jobs: GitLabJobs
    stages: GitLabStages

    def evolve(self, jobs: GitLabJobs | None = None, stages: GitLabStages | None = None) -> Self:
        """
        Type-safe evolution for GitLab jobs and stages tracking.

        Args:
            jobs: GitLab jobs.
            stages: GitLab stages.

        Returns:
            A new GitLabJobsStages instance with the modified or current state.
        """
        return replace(
            self,
            jobs=jobs if jobs is not None else self.jobs,
            stages=stages if stages is not None else self.stages,
        )


@dagger.enum_type
@final
@unique
class SCM(StrEnum):
    """SCM options."""

    GITHUB = "github"
    GITLAB = "gitlab"


GITHUB_FOLDER: Final = ".github"


def github_init(
    directory: dagger.Directory, github_actions_workflows: GitHubActionsWorkflows
) -> dagger.Directory:
    """
    Initialize the directory with GitHub files and folders.

    Args:
        directory: A directory to GitHub initialize.
        github_actions_workflows: The GitHub actions and workflows.

    Returns:
        Returns a directory with GitHub initialized.
    """
    # .github/{actions, workflows}/*
    # .github/actions/*/action.yml
    for github_action in github_actions_workflows.actions:
        directory = directory_with_new_file(directory, github_action.template)
    # .github/workflows/*.yml
    for (
        github_workflow,
        github_workflow_jobs,
    ) in github_actions_workflows.workflows.items():
        github_workflow_name = github_workflow.value.name
        workflow_name = f"{github_workflow_name}.yml"
        github_workflow_yml_template_mapping: Mapping = {
            "name": github_workflow_name,
            "on": asdict(github_workflow.value.on),
            "jobs": github_workflow_jobs,
        }
        github_workflow_yml_template = Template(
            COMMON_JINJA_ENVIRONMENT,
            TemplateFile(
                Path("github_workflow.yml"),
                PurePosixPath(GITHUB_FOLDER) / "workflows",
                PurePosixPath(workflow_name),
            ),
            github_workflow_yml_template_mapping,
        )
        directory = directory_with_new_file(directory, github_workflow_yml_template)
    return directory


GITLAB_FOLDER: Final = ".gitlab"


def gitlab_init(
    directory: dagger.Directory, gitlab_jobs_stages: GitLabJobsStages
) -> dagger.Directory:
    """
    Initialize the directory with GitLab files and folders.

    Args:
        directory: A directory to GitLab initialize.
        gitlab_jobs_stages: GitLab jobs and stages.

    Returns:
        Returns a directory with GitLab initialized.
    """
    # .gitlab/{jobs, stages}/*
    # .gitlab/jobs/*.yml
    for gitlab_job in gitlab_jobs_stages.jobs:
        directory = directory_with_new_file(directory, gitlab_job.template)
    # .gitlab/stages/*.yml
    gitlab_ci_stages: dict[str, str] = {}
    for gitlab_stage, gitlab_stage_jobs in gitlab_jobs_stages.stages.items():
        gitlab_stage_name = gitlab_stage.value.name
        gitlab_stage_file_name = f"{gitlab_stage_name}.yml"
        gitlab_stage_yml_template_mapping: Mapping = {"jobs": gitlab_stage_jobs}
        gitlab_stage_yml_template = Template(
            COMMON_JINJA_ENVIRONMENT,
            TemplateFile(
                Path("gitlab_stage.yml"),
                PurePosixPath(GITLAB_FOLDER) / "stages",
                PurePosixPath(gitlab_stage_file_name),
            ),
            gitlab_stage_yml_template_mapping,
        )
        gitlab_ci_stages[gitlab_stage_name] = str(
            gitlab_stage_yml_template.template_file.output_path
        )
        directory = directory_with_new_file(directory, gitlab_stage_yml_template)
    # .gitlab-ci.yml
    _gitlab_ci_yml_template_mapping: Mapping = {
        "stages": [stage_name.lower() for stage_name in gitlab_ci_stages],
        "paths": gitlab_ci_stages.values(),
    }
    _gitlab_ci_yml_template = Template(
        COMMON_JINJA_ENVIRONMENT,
        TemplateFile(Path(".gitlab-ci.yml")),
        _gitlab_ci_yml_template_mapping,
    )
    directory = directory_with_new_file(directory, _gitlab_ci_yml_template)
    return directory


GITLAB_JOBS_FOLDER: Final = "jobs"


def build_github_action(  # noqa: PLR0913
    sdk_language: str,
    sdk_module_name: str,
    sdk_module_function: SDKModuleFunction,
    dagger_version: str,
    shiryu_version: str,
    export_path: PurePosixPath | None,
) -> GitHubAction:
    """
    Build a github action.

    Args:
        sdk_language: SDK language.
        sdk_module_name: SDK module name.
        sdk_module_function: SDK module function.
        dagger_version: Dagger version.
        shiryu_version: Shiryu version.
        export_path: Append export path after dagger call.

    Returns:
        A GitHub action.

    Raises:
        ValueError: If `export_path` argument is provided and `sdk_module_function` return type is
        not `dagger.Directory`.
    """
    sdk_module_name_title = sdk_module_name.title()
    sdk_module_function_name = sdk_module_function.__name__
    id_ = camel_case_to_snake_case(
        f"{sdk_module_name_title}{sdk_module_function_name.title()}",
    )
    name = f"{sdk_module_name_title} {sdk_module_function_name}"
    sdk_module_function_parameters = get_sdk_module_function_parameters(sdk_module_function)
    # .github/actions/<sdk_module_function_name>/action.yml
    export_chain = []
    if export_path is not None:
        sdk_module_function_return_type = signature(sdk_module_function).return_annotation
        if (
            sdk_module_function_return_type is Parameter.empty
            or sdk_module_function_return_type is not dagger.Directory
        ):
            exception_message = (
                f"Invalid `export_path` argument for SDK module function "
                f"{sdk_module_function_name} from module {sdk_module_name} with return type "
                f"{sdk_module_function_return_type}"
            )
            raise ValueError(exception_message)
        # TODO: Check that the return type is of type dagger.
        export_chain.append(f"export --path=./{export_path}")
    action_yml_template_mapping: Mapping = {
        "function": sdk_module_function_name,
        "module": sdk_module_name,
        "shiryu_version": {"default": shiryu_version},
        "sdk_language": {"default": sdk_language},
        "parameters": sdk_module_function_parameters,
        "steps": (
            GitHubWorkflowRunStep(
                f"call_dagger_{id_}",
                f"Call Dagger {name}",
                "dagger/dagger-for-github@v8.4.0",
                (
                    GitHubWorkflowStepInputParameter("version", f'"v{dagger_version}"'),
                    GitHubWorkflowStepInputParameter("verb", "call"),
                    GitHubWorkflowStepInputParameter(
                        "module",
                        "github.com/fvonbergen/shiryu@${{ inputs.shiryu_version }}",
                    ),
                    GitHubWorkflowStepInputParameter(
                        "args",
                        " ".join(
                            [
                                f"${{{{ inputs.sdk_language }}}} {sdk_module_name} "
                                f"{sdk_module_function_name}",
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
        TemplateFile(Path("action.yml"), PurePosixPath(GITHUB_FOLDER) / "actions" / id_),
        action_yml_template_mapping,
    )
    return GitHubAction(id_, name, action_yml_template, sdk_module_function_parameters)


def build_github_workflow_job(
    sdk_language: str,
    github_action: GitHubAction,
    shiryu_version: str,
    job_environment: GitHubJobEnvironment | None,
    post_steps: tuple[GitHubWorkflowJobStep, ...],
) -> GitHubWorkflowJob:
    """
    Build a GitHub workflow job.

    Args:
        sdk_language: SDK language.
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
        f'"./{github_action.template.template_file.output_path.parent}"',
        (
            *(
                GitHubWorkflowStepInputParameter(
                    "dagger_cloud_token", "${{ secrets.DAGGER_CLOUD_TOKEN }}"
                ),
                GitHubWorkflowStepInputParameter("shiryu_version", f'"{shiryu_version}"'),
                GitHubWorkflowStepInputParameter("sdk_language", f'"{sdk_language}"'),
            ),
            *tuple(action_step_input_parameters_generator),
        ),
    )
    return GitHubWorkflowJob(id_, name, job_environment, (*pre_steps, action_step, *post_steps))


def build_gitlab_job(  # noqa: PLR0913
    sdk_language: str,
    sdk_module_name: str,
    sdk_module_function: SDKModuleFunction,
    shiryu_version: str,
    pre_script: GitLabScript,
    export_path: PurePosixPath | None,
    post_script: GitLabScript,
    artifacts: GitLabArtifacts | None,
) -> GitLabJob:
    """
    Build a GitLab job.

    Args:
        sdk_language: SDK language.
        sdk_module_name: SDK module name.
        sdk_module_function: SDK module function.
        shiryu_version: Shiryu version.
        pre_script: GitLab commands to run before dagger module command in script section.
        export_path: Append export path after dagger call.
        post_script: GitLab commands to run after dagger module command in script section.
        artifacts: GitLab artifacts section.

    Returns:
        A GitLab job.

    Raises:
        ValueError: If `export_path` argument is provided and `sdk_module_function` return type is
        not `dagger.Directory`.
    """
    sdk_module_function_name = sdk_module_function.__name__
    id_ = camel_case_to_snake_case(
        f"{sdk_module_name.title()}{sdk_module_function_name.title()}",
    )
    sdk_module_function_parameters = get_sdk_module_function_parameters(sdk_module_function)
    export_chain = []
    if export_path is not None:
        sdk_module_function_return_type = signature(sdk_module_function).return_annotation
        if (
            sdk_module_function_return_type is Parameter.empty
            or sdk_module_function_return_type is not dagger.Directory
        ):
            exception_message = (
                f"Invalid `export_path` argument for SDK module function "
                f"{sdk_module_function_name} from module {sdk_module_name} with return type "
                f"{sdk_module_function_return_type}"
            )
            raise ValueError(exception_message)
        # TODO: Check that the return type is of type dagger.
        export_chain.append(f"export --path=./{export_path}")
    job_name = f".{id_}"
    job_yml_template_mapping: Mapping = {
        "name": job_name,
        "shiryu_version": {"default": shiryu_version},
        "sdk_language": {"default": sdk_language},
        "parameters": sdk_module_function_parameters,
        "scripts": (
            *pre_script,
            " ".join(
                [
                    (
                        "dagger --mod=gitlab.com/fvonbergen1/shiryu@${{SHIRYU_VERSION}} call "
                        "${{SDK_LANGUAGE}} "
                        f"{sdk_module_name} {sdk_module_function_name}"
                    ),
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
            PurePosixPath(GITLAB_FOLDER) / GITLAB_JOBS_FOLDER,
            PurePosixPath(f"{job_name}.yml"),
        ),
        job_yml_template_mapping,
    )
    return GitLabJob(id_, job_name, job_yml_template, sdk_module_function_parameters)


def build_gitlab_stage_job(gitlab_stage_id: GitLabStageId, gitlab_job: GitLabJob) -> GitLabStageJob:
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
        str(gitlab_job.template.template_file.output_path),
        f"{gitlab_stage_name}_{gitlab_job.id_}",
        (gitlab_job.name,),
        gitlab_stage_name,
        (),
        gitlab_stage_id.value.rules,
    )
