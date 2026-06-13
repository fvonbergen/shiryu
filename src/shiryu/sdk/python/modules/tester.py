"""tester module."""

from configparser import ConfigParser
from pathlib import Path, PurePosixPath
from typing import Annotated, Final, final

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
    GitHubWorkflowId,
    GitLabStageId,
    build_github_action,
    build_github_workflow_job,
    build_gitlab_job,
    build_gitlab_stage_job,
)
from ...common.utils import PROJECT_SOURCE_CODE_FOLDER, PROJECT_TESTS_FOLDER
from ..context import DependencyGroups, PythonModuleInitContextDirectory
from ..module import PythonModule
from ..templates import PYTHON_JINJA_ENVIRONMENT
from .checker import Checker

OptionalKeywordDaggerType = Annotated[
    str | None, dagger.Doc("Run tests that match substring expression")
]
OPTIONAL_KEYWORD_DAGGER_DEFAULT: Final = None
PrivilegedNestingDaggerType = Annotated[
    bool, dagger.Doc("Whether to allow container dagger client to connect to the dagger engine.")
]
PRIVILEGED_NESTING_DAGGER_DEFAULT: Final = False

TESTS_UNIT_FOLDER: Final = "unit"

TESTS_CODE_DEPENDENCIES: Final = {"pytest", "pytest-asyncio"}


@dagger.object_type
class Tester(PythonModule):
    """Python SDK tester."""

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
    def __tests_unit_path(cls) -> PurePosixPath:
        """
        Get the tests unit path.

        Returns:
            The tests unit path.
        """
        return PurePosixPath(PROJECT_TESTS_FOLDER) / TESTS_UNIT_FOLDER

    # @final
    # @classmethod
    # def _coverage_badge_file_path(cls) -> Path:
    #     """
    #     Get the container project coverage badge file path.

    #     Returns:
    #         The container project coverage badge file path.
    #     """
    #     return PurePosixPath() / cls._coverage_badge_file_name()

    @final
    @classmethod
    def _pytest_unit_ini_template_file(cls) -> TemplateFile:
        """
        pytest.ini template file.

        Returns:
            The pytest.ini template file.
        """
        return TemplateFile(Path("pytest.ini"), None, PurePosixPath("pytest.unit.ini"))

    @final
    @classmethod
    def _coveragerc_template_file(cls) -> TemplateFile:
        """
        .coveragerc template file.

        Returns:
            The .coveragerc template file.
        """
        return TemplateFile(Path(".coveragerc"))

    #     @classmethod
    #     def _sdk_source_code_python_packages(cls) -> set[str]:
    #         """
    #         Python packages used in modules source code.
    #
    #         Returns:
    #             Python packages used in modules source code.
    #         """
    #         python_packages = super()._sdk_source_code_python_packages()
    #         return {*python_packages, "pytest", "pytest-asyncio"}

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
        sdk_module_function = cls.unit
        github_action = build_github_action(
            sdk_language=sdk_language,
            sdk_module_name=sdk_module_name,
            sdk_module_function=sdk_module_function,  # pyright: ignore [reportArgumentType]
            dagger_version=dagger_version,
            shiryu_version=shiryu_version,
            export_path=None,
        )
        gitlab_job = build_gitlab_job(
            sdk_language=sdk_language,
            sdk_module_name=sdk_module_name,
            sdk_module_function=sdk_module_function,  # pyright: ignore [reportArgumentType]
            shiryu_version=shiryu_version,
            pre_script=(),
            export_path=None,
            post_script=(),
            artifacts=None,
        )
        return init_context_directory.evolve(
            scm=init_context_directory.scm.evolve(
                github_actions_workflows=init_context_directory.scm.github_actions_workflows.evolve(
                    actions=init_context_directory.scm.github_actions_workflows.actions
                    | {github_action},
                    workflows=init_context_directory.scm.github_actions_workflows.workflows.add(
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
                        GitLabStageId.QUALITY,
                        build_gitlab_stage_job(
                            gitlab_stage_id=GitLabStageId.QUALITY, gitlab_job=gitlab_job
                        ),
                    ),
                ),
            ),
            dependency_groups=init_context_directory.dependency_groups.add(
                sdk_module_name,
                TESTS_CODE_DEPENDENCIES | {"pytest-cov", "pytest-xdist[psutil]"},
            ).merge(DependencyGroups({Checker.name(): TESTS_CODE_DEPENDENCIES})),
            source_code_files_folders=init_context_directory.source_code_files_folders
            | {PROJECT_TESTS_FOLDER},
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
        tests_unit_path_str = str(cls.__tests_unit_path())
        # pytest.unit.ini
        pytest_unit_init_template_mapping: Mapping = {
            "project_coveragerc_path": str(cls._coveragerc_template_file().output_file_name),
            "project_source_path": PROJECT_SOURCE_CODE_FOLDER,
            "project_tests_path": tests_unit_path_str,
        }
        pytest_unit_ini_template = Template(
            PYTHON_JINJA_ENVIRONMENT,
            cls._pytest_unit_ini_template_file(),
            pytest_unit_init_template_mapping,
        )
        init_directory = directory_with_new_file(init_directory, pytest_unit_ini_template)
        # .coveragerc
        _coveragerc_template_mapping: Mapping = {
            "project_source_path": PROJECT_SOURCE_CODE_FOLDER,
            "coverage_file_path": cls._coverage_file_name(),
        }
        _coveragerc_template = Template(
            PYTHON_JINJA_ENVIRONMENT, cls._coveragerc_template_file(), _coveragerc_template_mapping
        )
        init_directory = directory_with_new_file(init_directory, _coveragerc_template)
        # <tests>/<tests unit>/
        init_directory = init_directory.with_directory(tests_unit_path_str, dagger.dag.directory())
        return init_directory

    @final
    @classmethod
    async def __unit(
        cls,
        container: dagger.Container,
        keyword: OptionalKeywordDaggerType,
        privileged_nesting: PrivilegedNestingDaggerType,
    ) -> dagger.Container:
        """
        Unit test pipeline.

        Args:
            container: Project container.
            keyword: Run tests that match substring expression.
            privileged_nesting: Whether to allow dagger container connect to the dagger engine.

        Returns:
            A container with the project test command executed.
        """
        # Check that there is at last one test file.
        config = ConfigParser()
        pytest_unit_ini_output_path = cls._pytest_unit_ini_template_file().output_path
        pytest_unit_ini_file_contents = await container.file(
            str(pytest_unit_ini_output_path)
        ).contents()
        config.read_string(pytest_unit_ini_file_contents)
        tests_unit_extension = config["pytest"]["python_files"]
        tests_unit_files = await container.directory(str(cls.__tests_unit_path())).glob(
            tests_unit_extension
        )
        is_tests_unit_files = len(tests_unit_files) != 0
        expect = dagger.ReturnType.SUCCESS if is_tests_unit_files else dagger.ReturnType.FAILURE
        pytest_command = cls._build_uv_run_command(
            ["pytest", f"--config-file={pytest_unit_ini_output_path}"]
        )
        if keyword:
            pytest_command.extend([f"-k={keyword}", "--cov-fail-under=0"])
        return container.with_exec(
            pytest_command, expect=expect, experimental_privileged_nesting=privileged_nesting
        )

    @final
    @dagger.function
    async def unit(
        self,
        project_directory: ProjectDirectoryDaggerType,
        keyword: OptionalKeywordDaggerType = OPTIONAL_KEYWORD_DAGGER_DEFAULT,
        platform: PlatformDaggerType = PLATFORM_DAGGER_DEFAULT,
        privileged_nesting: PrivilegedNestingDaggerType = PRIVILEGED_NESTING_DAGGER_DEFAULT,
    ) -> str:
        """Run unit tests in the project of the provided source Directory."""
        container = await self._exec_container(project_directory, platform)
        container = await self.__unit(container, keyword, privileged_nesting)
        return await container.stdout()

    # @final
    # @dagger.function
    # async def coverage(
    #     self, project_directory: ProjectDirectoryType, platform: PlatformType = PLATFORM_DEFAULT
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
    #                 f"--input-file={self._coverage_file_name()}",
    #                 f"--output-file={self._coverage_badge_file_path()}",
    #             ]
    #         )
    #         .directory(".")
    #         .filter(include=[str(self._coverage_file_path())])
    #     )


sdk_module: Final = Tester
