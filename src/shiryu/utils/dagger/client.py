"""client module."""

import asyncio
from collections.abc import Set
from pathlib import PurePosixPath
from typing import Final

from dagger_clients.core import CacheSharingMode, Container, Directory, Platform, core
from packaging.version import Version

from .file import TargetFile

WORKDIR_PATH: Final = PurePosixPath("/workspace")

# PINNED: debian codename (2026/11/01)
DEBIAN_VERSION_CODENAME: Final = "trixie"
# PINNED: debian snapshot datetime (2026/11/01)
# https://snapshot.debian.org/
DEBIAN_SNAPSHOT_DATETIME: Final = "20261101T000000Z"
# PINNED: debian manifest digest (2026/11/22)
# Pick the multi-architecture manifest wrapper.
# https://hub.docker.com/layers/library/debian/trixie-slim/images/sha256-a72b4433de1cf7d6bae0c4cee74d0547f58601a643b3375f070c51600d63b6b2
DEBIAN_MANIFEST_DIGEST: Final = (
    "sha256:a72b4433de1cf7d6bae0c4cee74d0547f58601a643b3375f070c51600d63b6b2"
)
IMAGE_REF: Final = "docker.io"
DEBIAN_IMAGE_NAMESPACE: Final = "library/debian"
# IMAGE_REF: Final = "public.ecr.aws/"
# DEBIAN_IMAGE_NAMESPACE: Final = "debian/debian"
FULLY_QUALIFIED_IMAGE_NAME_DEBIAN: Final = (
    f"{IMAGE_REF}/{DEBIAN_IMAGE_NAMESPACE}:{DEBIAN_VERSION_CODENAME}-slim@{DEBIAN_MANIFEST_DIGEST}"
)
# PINNED: uv version (2026/11/22)
UV_VERSION: Final = Version("0.13.8")
# NOTE: trivy version will be pinned ont the dagger.lock file.
FULLY_QUALIFIED_IMAGE_NAME_TRIVY: Final = f"{IMAGE_REF}/aquasec/trivy"

APTPackages = Set[str]


async def __run_trivy(
    platform: Platform, rootfs_audit: Directory, _trivyignore_file: TargetFile
) -> None:
    """Runs a Trivy vulnerability scan on the target root filesystem.

    Args:
        platform: The container platform.
        rootfs_audit: The root filesystem directory to be scanned.
        _trivyignore_file: The trivyignore file.
    """
    rootfs_target = "/mnt/target"
    _trivyignore_file_file = _trivyignore_file.file
    await (
        core()
        .container(platform=platform)
        .from_(FULLY_QUALIFIED_IMAGE_NAME_TRIVY)
        .with_mounted_cache(
            "/root/.cache/trivy",
            core().cache_volume("shiryu-trivy"),
            sharing=CacheSharingMode.LOCKED,
        )
        .with_file(str(_trivyignore_file.output_path), _trivyignore_file_file, permissions=0o644)
        .with_directory(rootfs_target, rootfs_audit)
        .with_exec(
            [
                "trivy",
                "rootfs",
                f"--ignorefile={await _trivyignore_file_file.name()}",
                "--pkg-types=os",
                "--severity=CRITICAL",
                "--exit-code=1",
                rootfs_target,
            ]
        )
        .sync()
    )


async def container_debian(
    platform: Platform,
    apt_security_audit_file: TargetFile,
    *,
    apt_packages: APTPackages = frozenset(),
) -> Container:
    """A debian container.

    Args:
        platform: The container platform.
        apt_security_audit_file: APT security audit file.
        apt_packages: The container APT packages.

    Returns:
        A debian container.
    """
    container = core().container(platform=platform).from_(FULLY_QUALIFIED_IMAGE_NAME_DEBIAN)

    # Load environment variables from the .env file if it exists in the host directory
    # only .env file name are allowed.
    host_dir = core().host().directory(".", include=[".env"])
    if await host_dir.exists(".env"):
        env_file = host_dir.file(".env").as_env_file()
        container = container.with_env_file_variables(env_file)

    snapshot_sources = (
        f"deb http://snapshot.debian.org/archive/debian/{DEBIAN_SNAPSHOT_DATETIME} "
        f"{DEBIAN_VERSION_CODENAME} main\n"
        f"deb http://snapshot.debian.org/archive/debian-security/{DEBIAN_SNAPSHOT_DATETIME} "
        f"{DEBIAN_VERSION_CODENAME}-security main\n"
    )
    container = (
        # Prevent hanging scripts due to interactive prompts
        container.with_env_variable("DEBIAN_FRONTEND", "noninteractive")
        # Prevent crashes from special characters/emojis in filenames or logs
        .with_env_variable("LC_ALL", "C.UTF-8")
        # Override sources.list with the frozen snapshot archive
        .with_new_file("/etc/apt/sources.list", snapshot_sources, permissions=0o644)
        # Tell APT to ignore validation errors on past dates
        .with_new_file(
            "/etc/apt/apt.conf.d/99snapshot",
            'Acquire::Check-Valid-Until "false";\n',
            permissions=0o644,
        )
        # Scope cache volumes with the snapshot date to prevent stale data conflicts
        # LOCKED serializes concurrent apt run (e.g. asyncio.gather in releaser) that
        # would otherwise lead to race conditions for the apt cache.
        .with_mounted_cache(
            "/var/cache/apt/archives",
            core().cache_volume(
                f"shiryu-apt-archives-debian-{DEBIAN_VERSION_CODENAME}-slim-{DEBIAN_SNAPSHOT_DATETIME}"
            ),
            sharing=CacheSharingMode.LOCKED,
        )
        .with_mounted_cache(
            "/var/lib/apt/lists",
            core().cache_volume(
                f"shiryu-apt-lists-debian-{DEBIAN_VERSION_CODENAME}-slim-{DEBIAN_SNAPSHOT_DATETIME}"
            ),
            sharing=CacheSharingMode.LOCKED,
        )
        .with_new_file(
            "/etc/apt/apt.conf.d/keep-cache",
            'Binary::apt::APT::Keep-Downloaded-Packages "true";\n',
            permissions=0o644,
        )
        .with_exec(["apt-get", "update"])
    )

    if apt_packages:
        apt_install = (
            "apt-get",
            "install",
            "--assume-yes",
            "--no-install-recommends",
            *sorted(apt_packages),
        )
        container = container.with_exec([*apt_install])

    await __run_trivy(platform, container.rootfs(), _trivyignore_file=apt_security_audit_file)

    return container.with_workdir(str(WORKDIR_PATH))


async def container_git(platform: Platform, apt_security_audit_file: TargetFile) -> Container:
    """A git container.

    Args:
        platform: The container platform.
        apt_security_audit_file: APT security audit file.

    Returns:
        A container with git.
    """
    return await container_debian(platform, apt_security_audit_file, apt_packages={"git"})


async def container_uv(
    platform: Platform,
    apt_security_audit_file: TargetFile,
    config_file_file: TargetFile,
    *,
    apt_packages: APTPackages = frozenset(),
) -> Container:
    """A uv container.

    Args:
        platform: The container platform.
        apt_security_audit_file: APT security audit file.
        config_file_file: Uv config file.
        apt_packages: The container APT packages.

    Returns:
        A container with uv.
    """
    _config_file_file = config_file_file.file
    container, config_file_file_name = await asyncio.gather(
        container_debian(platform, apt_security_audit_file, apt_packages={"pipx", *apt_packages}),
        _config_file_file.name(),
    )
    venv_path_str = "/opt/.venv"
    container = (
        container.with_mounted_cache(
            "/root/.cache/pipx", core().cache_volume("shiryu-pipx"), sharing=CacheSharingMode.LOCKED
        )
        .with_env_variable("PATH", "/root/.local/bin:${PATH}", expand=True)
        .with_exec(["pipx", "install", f"uv=={UV_VERSION}"])
        .with_mounted_cache(
            "/root/.cache/uv", core().cache_volume("shiryu-uv"), sharing=CacheSharingMode.LOCKED
        )
        .with_env_variable("UV_LINK_MODE", "copy")
        .with_env_variable("UV_MALWARE_CHECK", "1")
        .with_file(str(config_file_file.output_path), _config_file_file, permissions=0o644)
        .with_exec(["uv", f"--config-file={config_file_file_name}", "venv", venv_path_str])
        .with_env_variable("UV_PROJECT_ENVIRONMENT", venv_path_str)
    )

    return container
