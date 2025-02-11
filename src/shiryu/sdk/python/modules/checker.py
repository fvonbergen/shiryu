"""check module."""

from configparser import ConfigParser
from pathlib import Path
from typing import Final, final

import dagger

from ....utils.dagger.container import container_with_files
from ....utils.template import Mapping, Template, TemplateFile
from ...common.module import (
    PLATFORM_DEFAULT,
    GitHubActionsWorkflows,
    GitHubWorkflowId,
    GitLabJobsStages,
    GitLabStageId,
    PlatformType,
    ProjectDirectoryType,
    SCMListType,
    SDKEnv,
    SDKModuleModule,
)
from ..module import ModulesPythonPackages, PythonModule, PythonModuleInit
from ..templates import PYTHON_JINJA_ENVIRONMENT


class CheckerInit(PythonModuleInit):
    """Python SDK checker initializer."""

    @final
    @classmethod
    def _mypy_ini_template_file(cls) -> TemplateFile:
        """
        Get the mypy.ini template file.

        Returns:
            The mypy.ini template file.
        """
        return TemplateFile(Path("mypy.ini"), cls._container_project_path())

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
        _sdk_env = await super()._module_init(sdk_env, is_overwrite, scm)
        container = _sdk_env.container
        project_properties = _sdk_env.project_properties
        # mypy.ini
        mypy_init_template_mapping: Mapping = {
            "project_source_path": str(
                cls._container_project_source_path().relative_to(
                    cls._container_project_path()
                )
            ),
            "source_code_files_and_folders": cls._sdk_source_code_files_folders(),
        }
        mypy_ini_template = Template(
            PYTHON_JINJA_ENVIRONMENT,
            cls._mypy_ini_template_file(),
            mypy_init_template_mapping,
        )
        # mypy.ini
        container = await container_with_files(
            container, (mypy_ini_template,), is_overwrite
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
        github_actions_workflows = super()._github_actions_workflows(
            dagger_version, shiryu_version
        )
        github_actions = github_actions_workflows["actions"]
        github_workflows = github_actions_workflows["workflows"]
        github_action = cls._build_github_action(
            Checker,
            Checker.check,  # pyright: ignore [reportArgumentType]
            dagger_version,
            shiryu_version,
            None,
        )
        github_actions.add(github_action)
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
        gitlab_jobs_stages = super()._gitlab_jobs_stages(dagger_version, shiryu_version)
        gitlab_jobs = gitlab_jobs_stages["jobs"]
        gitlab_stages = gitlab_jobs_stages["stages"]
        gitlab_job = cls._build_gitlab_job(
            Checker,
            Checker.check,  # pyright: ignore [reportArgumentType]
            shiryu_version,
            (),
            None,
            (),
            None,
        )
        gitlab_jobs.update({gitlab_job})
        gitlab_stages.add(
            GitLabStageId.QUALITY,
            cls._build_gitlab_stage_job(GitLabStageId.QUALITY, gitlab_job),
        )
        return {"jobs": gitlab_jobs, "stages": gitlab_stages}


@final
@dagger.object_type
class Checker(PythonModule, CheckerInit):
    """Python SDK checker."""

    @classmethod
    def _base_container_modules_python_packages(cls) -> ModulesPythonPackages:
        """
        Base container modules python packages.

        Returns:
            Base container modules python packages.
        """
        base_container_modules_python_packages = (
            super()._base_container_modules_python_packages()
        )
        base_container_modules_python_packages[Checker.name()] = {
            *cls._sdk_source_code_python_packages(),
            "mypy",
        }
        return base_container_modules_python_packages

    @final
    @classmethod
    async def __pipeline(
        cls, project_directory: ProjectDirectoryType, platform: PlatformType
    ) -> dagger.Container:
        """
        Check pipeline.

        Args:
            project_directory: Project directory.
            platform: The container platform.

        Returns:
            A container with the project check command executed.
        """
        container, _ = await cls.sdk_module_env(project_directory, platform)
        # mypy needs files inside the source code folder.
        config = ConfigParser()
        mypy_ini_file_contents = await container.file(
            str(cls._mypy_ini_template_file().output_path)
        ).contents()
        config.read_string(mypy_ini_file_contents)
        source_code_files_folders = {
            source_code_file_folder.strip()
            for source_code_file_folder in config["mypy"]["files"].split(",")
        }
        # <source_code_folder>/mypy_dummy.py
        for source_code_folder in source_code_files_folders:
            mypy_dummy_py_output_path = (
                cls._container_project_path() / source_code_folder
            )
            source_code_files = sorted(
                await container.directory(str(mypy_dummy_py_output_path)).glob(
                    "**/*.py"
                )
            )
            if len(source_code_files) == 0:
                mypy_dummy_py_template_file = TemplateFile(
                    Path("mypy_dummy.py"), mypy_dummy_py_output_path
                )
                mypy_dummy_py_template_mapping: Mapping = {}
                mypy_dummy_py_template = Template(
                    PYTHON_JINJA_ENVIRONMENT,
                    mypy_dummy_py_template_file,
                    mypy_dummy_py_template_mapping,
                )
                # <source_code_folder>/dummy.py
                container = await container_with_files(
                    container, (mypy_dummy_py_template,), False
                )
        # MYPYPATH={PROJECT_SOURCE_CODE_FOLDER} mypy --config-file={mypy_ini_file.file_name} {' '.join(params)}
        mypy_command = [
            "uv",
            "run",
            "--no-project",
            "--module",
            "mypy",
            f"--config-file={cls._mypy_ini_template_file().file_name}",
        ]
        return container.with_exec(mypy_command)

    @dagger.function
    async def check(
        self,
        project_directory: ProjectDirectoryType,
        platform: PlatformType = PLATFORM_DEFAULT,
    ) -> str:
        """Run type checks in the project of the provided source Directory."""
        await (await self.__pipeline(project_directory, platform)).sync()
        return "Check successfull"


sdk_module: Final = SDKModuleModule(init=CheckerInit, module=Checker)
