"""tester module."""

from configparser import ConfigParser
from pathlib import Path
from typing import Annotated, Final, final

import dagger

from ....utils.dagger.container import container_with_file
from ....utils.template import Mapping, Template, TemplateFile
from ...common.module import (
    PLATFORM_DEFAULT,
    GitHubActionsWorkflows,
    GitHubWorkflowId,
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

OptionalKeywordType = Annotated[
    str | None, dagger.Doc("Run tests that match substring expression")
]


class TesterInit(PythonModuleInit):
    """Python SDK tester initializer."""

    @final
    @staticmethod
    def _tests_folder() -> str:
        """
        Get the tests folder name.

        Returns:
            The tests folder name.
        """
        return "tests"

    @final
    @staticmethod
    def _unit_folder() -> str:
        """
        Get the unit folder name.

        Returns:
            The unit folder name.
        """
        return "unit"

    @final
    @staticmethod
    def _coverage_file_name() -> str:
        """
        Get the coverage file name.

        Returns:
            The coverage file name.
        """
        return "coverage.xml"

    # @final
    # @staticmethod
    # def _coverage_badge_file_name() -> str:
    #     """
    #     Get the coverage badge file name.

    #     Returns:
    #         The coverage badge file name.
    #     """
    #     return "coverage-badge.svg"

    @final
    @classmethod
    def _container_project_tests_path(cls) -> Path:
        """
        Get the container project tests path.

        Returns:
            The container project tests path.
        """
        return cls._container_project_path() / cls._tests_folder()

    @final
    @classmethod
    def _container_project_tests_unit_path(cls) -> Path:
        """
        Get the container project tests unit path.

        Returns:
            The container project tests unit path.
        """
        return cls._container_project_path() / cls._tests_folder() / cls._unit_folder()

    @final
    @classmethod
    def _container_project_coverage_file_path(cls) -> Path:
        """
        Get the container project coverage file path.

        Returns:
            The container project coverage file path.
        """
        return cls._container_project_path() / cls._coverage_file_name()

    # @final
    # @classmethod
    # def _container_project_coverage_badge_file_path(cls) -> Path:
    #     """
    #     Get the container project coverage badge file path.

    #     Returns:
    #         The container project coverage badge file path.
    #     """
    #     return cls._container_project_path() / cls._coverage_badge_file_name()

    @classmethod
    def _sdk_source_code_files_folders(cls) -> set[str]:
        """
        Files and folders that contains SDK language source code.

        Returns:
            Set of files and folders with SDK language source code.
        """
        source_code_files_folders = super(
            TesterInit, cls
        )._sdk_source_code_files_folders()
        source_code_files_folders.add(
            f"{cls._container_project_tests_unit_path().relative_to(cls._container_project_path())}"
        )
        return source_code_files_folders

    @final
    @classmethod
    def _pytest_unit_ini_template_file(cls) -> TemplateFile:
        """
        pytest.ini template file.

        Returns:
            The pytest.ini template file.
        """
        return TemplateFile(
            Path("pytest.ini"), cls._container_project_path(), Path("pytest.unit.ini")
        )

    @final
    @classmethod
    def _coveragerc_template_file(cls) -> TemplateFile:
        """
        .coveragerc template file.

        Returns:
            The .coveragerc template file.
        """
        return TemplateFile(Path(".coveragerc"), cls._container_project_path())

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
        _sdk_env = await super(TesterInit, cls)._module_init(sdk_env, is_overwrite, scm)
        container = _sdk_env.container
        project_properties = _sdk_env.project_properties
        # tests/unit
        container = container.with_exec(
            [
                "mkdir",
                "--parents",
                str(cls._container_project_tests_unit_path()),
            ]
        )
        # pytest.unit.ini
        project_source_path_str = str(
            cls._container_project_source_path().relative_to(
                cls._container_project_path()
            )
        )
        pytest_unit_init_template_mapping: Mapping = {
            "project_coveragerc_path": str(
                cls._coveragerc_template_file().output_file_name
            ),
            "project_source_path": project_source_path_str,
            "project_tests_path": str(
                cls._container_project_tests_unit_path().relative_to(
                    cls._container_project_path()
                )
            ),
        }
        pytest_unit_ini_template = Template(
            PYTHON_JINJA_ENVIRONMENT,
            cls._pytest_unit_ini_template_file(),
            pytest_unit_init_template_mapping,
        )
        container = await container_with_file(
            container, pytest_unit_ini_template, is_overwrite
        )
        # .coveragerc
        _coveragerc_template_mapping: Mapping = {
            "project_source_path": project_source_path_str,
            "coverage_file_path": str(
                cls._container_project_coverage_file_path().relative_to(
                    cls._container_project_path()
                )
            ),
        }
        _coveragerc_template = Template(
            PYTHON_JINJA_ENVIRONMENT,
            cls._coveragerc_template_file(),
            _coveragerc_template_mapping,
        )
        container = await container_with_file(
            container, _coveragerc_template, is_overwrite
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
        github_actions_workflows = super(TesterInit, cls)._github_actions_workflows(
            dagger_version, shiryu_version
        )
        github_actions = github_actions_workflows["actions"]
        github_workflows = github_actions_workflows["workflows"]
        github_action = cls._build_github_action(
            Tester,
            Tester.unit,  # pyright: ignore [reportArgumentType]
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
    def _sdk_source_code_python_packages(cls) -> set[str]:
        """
        Python packages used in modules source code.

        Returns:
            Python packages used in modules source code.
        """
        return {"pytest", "pytest-asyncio"}

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
        gitlab_jobs_stages = super(TesterInit, cls)._gitlab_jobs_stages(
            dagger_version, shiryu_version
        )
        gitlab_jobs = gitlab_jobs_stages["jobs"]
        gitlab_stages = gitlab_jobs_stages["stages"]
        gitlab_job = cls._build_gitlab_job(
            Tester,
            Tester.unit,  # pyright: ignore [reportArgumentType]
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
class Tester(PythonModule, TesterInit):
    """Python SDK tester."""

    @classmethod
    def _base_container_modules_python_packages(cls) -> ModulesPythonPackages:
        """
        Base container modules python packages.

        Returns:
            Base container modules python packages.
        """
        base_container_modules_python_packages = super(
            Tester, cls
        )._base_container_modules_python_packages()
        base_container_modules_python_packages[Tester.name()] = {
            *cls._sdk_source_code_python_packages(),
            "pytest-cov",
        }
        return base_container_modules_python_packages

    @final
    @classmethod
    async def __pipeline(
        cls, project: ProjectType, platform: PlatformType, keyword: OptionalKeywordType
    ) -> dagger.Container:
        """
        Test pipeline.

        Args:
            project: Project directory.
            platform: The container platform.
            keyword: Run tests that match substring expression.

        Returns:
            A container with the project test command executed.
        """
        container, _ = await cls.sdk_module_env(project, platform)
        # Check that there is at last one test file.
        config = ConfigParser()
        pytest_unit_ini_output_path = cls._pytest_unit_ini_template_file().output_path
        pytest_unit_ini_file_contents = await container.file(
            str(pytest_unit_ini_output_path)
        ).contents()
        config.read_string(pytest_unit_ini_file_contents)
        tests_unit_extension = config["pytest"]["python_files"]
        tests_unit_files = await container.directory(
            str(cls._container_project_tests_unit_path())
        ).glob(tests_unit_extension)
        is_tests_unit_files = len(tests_unit_files) != 0
        expect = (
            dagger.ReturnType.SUCCESS
            if is_tests_unit_files
            else dagger.ReturnType.FAILURE
        )
        pytest_command = [
            "uv",
            "run",
            "--no-project",
            "--module",
            "pytest",
            f"--config-file={pytest_unit_ini_output_path}",
        ]
        if keyword:
            pytest_command.append(f"-k={keyword}")
        return await container.with_exec(pytest_command, expect=expect).sync()

    @final
    @dagger.function
    async def unit(
        self,
        project: ProjectType,
        keyword: OptionalKeywordType = None,
        platform: PlatformType = PLATFORM_DEFAULT,
    ) -> str:
        """Run unit tests in the project of the provided source Directory."""
        container = await self.__pipeline(project, platform, keyword)
        return await container.stdout()

    # @final
    # @dagger.function
    # async def coverage(
    #     self, project: ProjectType, platform: PlatformType = PLATFORM_DEFAULT
    # ) -> dagger.Directory:
    #     """Run unit tests in the project of the provided source Directory."""
    #     # TODO: add genbadge[coverage] to cls._base_container_python_packages()
    #     container = await self.__pipeline(project, platform, None)
    #     return (
    #         container.with_exec(
    #             [
    #                 "uv",
    #                 "run",
    #                 "--no-project",
    #                 "genbadge",
    #                 "coverage",
    #                 f"--input-file={self._container_project_coverage_file_path()}",
    #                 f"--output-file={self._container_project_coverage_badge_file_path()}",
    #             ]
    #         )
    #         .directory(str(self._container_project_path()))
    #         .filter(
    #             include=[
    #                 str(
    #                     self._container_project_coverage_file_path().relative_to(
    #                         self._container_project_path()
    #                     )
    #                 ),
    #                 str(
    #                     self._container_project_coverage_badge_file_path().relative_to(
    #                         self._container_project_path()
    #                     )
    #                 ),
    #             ]
    #         )
    #     )


sdk_module: Final = SDKModuleModule(init=TesterInit, module=Tester)
