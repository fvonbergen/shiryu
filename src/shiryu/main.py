"""main module."""

import asyncio

import dagger

from .sdk import SDKInterface, get_sdk_languages
from .sdk.common import (
    LANGUAGE_DEFAULT,
    PLATFORM_DEFAULT,
    SDK,
    LanguageType,
    PlatformType,
    ProjectNameType,
    ProjectType,
)

# class Platform(Enum):
#     """Platform options."""
#
#     # Reference: https://go.dev/wiki/MinimumRequirements#amd64
#     AMD64 = "linux/amd64"
#     # Reference: https://go.dev/wiki/GoArm
#     ARM32V7 = "linux/arm/v7"
#     ARM64 = "linux/arm64"


@dagger.object_type
class DaggerSDKInterface:
    """SDKInterface class."""

    sdk_language: LanguageType = dagger.field()

    def get_sdk(self) -> type[SDKInterface]:
        """
        Get SDK.

        Args:
            sdk: SDK enum.

        Returns:
            SDK class.
        """
        return get_sdk_languages()[self.sdk_language]

    @dagger.function
    async def build(
        self, project: ProjectType, platform: PlatformType = PLATFORM_DEFAULT
    ) -> dagger.Directory:
        """Run build in the project of the provided source Directory."""
        return await self.get_sdk().build(project, platform)

    @dagger.function
    async def check(
        self, project: ProjectType, platform: PlatformType = PLATFORM_DEFAULT
    ) -> str:
        """Run type checks in the project of the provided source Directory."""
        return await self.get_sdk().check(project, platform)

    @dagger.function
    async def lint(
        self, project: ProjectType, platform: PlatformType = PLATFORM_DEFAULT
    ) -> str:
        """Run lint checks in the project of the provided source Directory."""
        return await self.get_sdk().lint(project, platform)

    @dagger.function
    async def lint_fix(
        self, project: ProjectType, platform: PlatformType = PLATFORM_DEFAULT
    ) -> dagger.Directory:
        """Run lint fixes in the project of the provided source Directory."""
        return await self.get_sdk().lint_fix(project, platform)

    @dagger.function
    async def quality(
        self, project: ProjectType, platform: PlatformType = PLATFORM_DEFAULT
    ) -> str:
        """Run quality checks in the project of the provided source Directory."""
        sdk = self.get_sdk()
        return "\n".join(
            await asyncio.gather(
                sdk.lint(project, platform), sdk.check(project, platform)
            )
        )

    @dagger.function
    async def test_install(
        self, project: ProjectType, platform: PlatformType = PLATFORM_DEFAULT
    ) -> str:
        """Test the project installation process."""
        return await self.get_sdk().test_install(project, platform)

    @dagger.function
    async def init(
        self, project_name: ProjectNameType, platform: PlatformType = PLATFORM_DEFAULT
    ) -> dagger.Directory:
        """Returns a directory with a new project initialized."""
        return await self.get_sdk().init(project_name, platform)


@dagger.object_type
class Shiryu:
    """Shiryu class."""

    @dagger.function
    def sdk(self, language: LanguageType = LANGUAGE_DEFAULT) -> DaggerSDKInterface:
        """Shiryu SDK."""
        return DaggerSDKInterface(sdk_language=SDK(language))  # type: ignore[call-arg]
