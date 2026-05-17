"""main module."""

from typing import final

import dagger

from .sdk import SDKOptions
from .utils.dagger.function import add_enum_values_as_methods


@final
@dagger.object_type
@add_enum_values_as_methods(SDKOptions)
class Shiryu:
    """Shiryu class."""

    @dagger.function
    async def get_module_version(self) -> str:
        """Get module version."""
        module_source = dagger.dag.current_module().source()
        apt_install = ("apt-get", "install", "--assume-yes", "--no-install-recommends")
        container = (
            dagger.dag.container()
            .from_("debian:trixie-slim")
            .with_exec(["mkdir", "--parents", "/project"])
            .with_workdir("/project")
            .with_directory("/project", module_source)
            .with_exec(["apt-get", "update"])
            .with_exec([*apt_install, *sorted(["git"])])
            .with_exec(["apt-get", "autoremove"])
            .with_exec(["apt-get", "clean"])
        )
        container = container.with_exec(
            [
                "git",
                "init",
                "--initial-branch",
                "main",
                "/project",
            ]
        )

        try:
            module_tag = await container.with_exec(
                ["git", "describe", "--tags", "--exact-match"]
            ).stdout()
            return module_tag
        except dagger.QueryError:
            module_branch = await container.with_exec(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"]
            ).stdout()
            return module_branch
