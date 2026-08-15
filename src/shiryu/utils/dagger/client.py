"""client module."""

from collections.abc import Set
from pathlib import PurePosixPath
from typing import Final

import dagger

APT_PACKAGES = Set[str]

WORKDIR_PATH: Final = PurePosixPath("/workspace")


def container_debian(
    dagger_client: dagger.Client,
    platform: dagger.Platform,
    *,
    apt_packages: APT_PACKAGES = frozenset(),
) -> dagger.Container:
    """
    A debian container.

    Args:
        dagger_client: The dagger client.
        platform: The container platform.
        apt_packages: The container APT packages.

    Returns:
        A debian container.
    """
    container = dagger_client.container(platform=platform).from_(
        "public.ecr.aws/debian/debian:trixie-slim"
    )
    if apt_packages:
        apt_install = (
            "apt-get",
            "install",
            "--assume-yes",
            "--no-install-recommends",
            *sorted(apt_packages),
        )
        container = (
            # Prevent hanging scripts due to interactive prompts
            container.with_env_variable(name="DEBIAN_FRONTEND", value="noninteractive")
            # Prevent crashes from special characters/emojis in filenames or logs
            .with_env_variable(name="LC_ALL", value="C.UTF-8")
            .with_mounted_cache(
                "/var/cache/apt/archives",
                dagger.dag.cache_volume("shiryu-apt-archives-debian-trixie-slim"),
            )
            .with_mounted_cache(
                "/var/lib/apt/lists",
                dagger.dag.cache_volume("shiryu-apt-lists-debian-trixie-slim"),
            )
            .with_new_file(
                path="/etc/apt/apt.conf.d/keep-cache",
                contents='Binary::apt::APT::Keep-Downloaded-Packages "true";\n',
                permissions=0o644,
            )
            .with_exec(["apt-get", "update"])
            .with_exec([*apt_install])
        )
    return container.with_workdir(str(WORKDIR_PATH))


def container_git(dagger_client: dagger.Client, platform: dagger.Platform) -> dagger.Container:
    """
    A git container.

    Args:
        dagger_client: The dagger client.
        platform: The container platform.

    Returns:
        A container with git.
    """
    return container_debian(dagger_client, platform, apt_packages={"git"})


def container_uv(
    dagger_client: dagger.Client,
    platform: dagger.Platform,
    *,
    apt_packages: APT_PACKAGES = frozenset(),
) -> dagger.Container:
    """
    A uv container.

    Args:
        dagger_client: The dagger client.
        platform: The container platform.
        apt_packages: The container APT packages.

    Returns:
        A container with uv.
    """
    container = container_debian(dagger_client, platform, apt_packages={"pipx", *apt_packages})
    venv_path_str = "/opt/.venv"
    return (
        container.with_mounted_cache(
            "/root/.cache/pipx",
            dagger.dag.cache_volume("shiryu-pipx-debian-trixie-slim"),
        )
        .with_env_variable(name="PATH", value="/root/.local/bin:${PATH}", expand=True)
        .with_exec(["pipx", "install", "uv"])
        .with_mounted_cache(
            "/root/.cache/uv", dagger.dag.cache_volume("shiryu-uv-debian-trixie-slim")
        )
        .with_env_variable("UV_LINK_MODE", "copy")
        .with_exec(["uv", "venv", venv_path_str])
        .with_env_variable(name="UV_PROJECT_ENVIRONMENT", value=venv_path_str)
        .with_env_variable(name="UV_MALWARE_CHECK", value="1")
    )
