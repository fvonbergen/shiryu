"""client module."""

from collections.abc import Set
from pathlib import PurePosixPath
from typing import Final

from dagger_clients.core import CacheSharingMode, Container, Directory, Platform, core

from .function import SecurityAudit, SecurityAuditType

WORKDIR_PATH: Final = PurePosixPath("/workspace")

DEBIAN_CODENAME: Final = "trixie"
# https://snapshot.debian.org/
DEBIAN_SNAPSHOT_DATETIME: Final = "20261101T000000Z"
# Pick the multi-architecture manifest wrapper.
# https://hub.docker.com/layers/library/debian/trixie-slim/images/sha256-918311b7b6c4c6f68b232ba516584925f6c78ad82b6fd534b98979df6438e483
DEBIAN_MANIFEST_DIGEST: Final = (
    "sha256:a29215f6a35e51e22adffa17f89e9d2ef06214e64a2bad10d765c46aea49f11f"
)
IMAGE_REF: Final = "docker.io"
DEBIAN_IMAGE_NAMESPACE: Final = "library/debian"
# IMAGE_REF: Final = "public.ecr.aws/"
# DEBIAN_IMAGE_NAMESPACE: Final = "debian/debian"
FULLY_QUALIFIED_IMAGE_NAME_DEBIAN: Final = (
    f"{IMAGE_REF}/{DEBIAN_IMAGE_NAMESPACE}:{DEBIAN_CODENAME}-slim@{DEBIAN_MANIFEST_DIGEST}"
)
UV_VERSION: Final = "0.13.6"
FULLY_QUALIFIED_IMAGE_NAME_TRIVY: Final = f"{IMAGE_REF}/aquasec/trivy"

APTPackages = Set[str]


async def __run_trivy(platform: Platform, rootfs_audit: Directory) -> None:
    """Runs a Trivy vulnerability scan on the target root filesystem.

    Args:
        platform: The container platform.
        rootfs_audit: The root filesystem directory to be scanned.
    """
    rootfs_target = "/mnt/target"
    await (
        core()
        .container(platform=platform)
        .from_(FULLY_QUALIFIED_IMAGE_NAME_TRIVY)
        .with_mounted_cache("/root/.cache/trivy", core().cache_volume("shiryu-trivy"))
        .with_directory(rootfs_target, rootfs_audit)
        .with_exec(
            [
                "trivy",
                "rootfs",
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
    security_audit: SecurityAuditType,
    *,
    apt_packages: APTPackages = frozenset(),
) -> Container:
    """A debian container.

    Args:
        platform: The container platform.
        security_audit: Security audit checks that can be enabled in the pipeline.
        apt_packages: The container APT packages.

    Returns:
        A debian container.
    """
    container = core().container(platform=platform).from_(FULLY_QUALIFIED_IMAGE_NAME_DEBIAN)
    if apt_packages:
        snapshot_sources = (
            f"deb http://snapshot.debian.org/archive/debian/{DEBIAN_SNAPSHOT_DATETIME} "
            f"{DEBIAN_CODENAME} main\n"
            f"deb http://snapshot.debian.org/archive/debian-security/{DEBIAN_SNAPSHOT_DATETIME} "
            f"{DEBIAN_CODENAME}-security main\n"
        )
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
            # Override sources.list with the frozen snapshot archive
            .with_new_file(
                path="/etc/apt/sources.list",
                contents=snapshot_sources,
                permissions=0o644,
            )
            # Tell APT to ignore validation errors on past dates
            .with_new_file(
                path="/etc/apt/apt.conf.d/99snapshot",
                contents='Acquire::Check-Valid-Until "false";\n',
                permissions=0o644,
            )
            # Scope cache volumes with the snapshot date to prevent stale data conflicts
            # LOCKED serializes concurrent apt run (e.g. aynscio.gather in releaser) that
            # would otherwise lead to race conditions for the apt cache.
            .with_mounted_cache(
                "/var/cache/apt/archives",
                core().cache_volume(
                    f"shiryu-apt-archives-debian-{DEBIAN_CODENAME}-slim-{DEBIAN_SNAPSHOT_DATETIME}"
                ),
                sharing=CacheSharingMode.LOCKED,
            )
            .with_mounted_cache(
                "/var/lib/apt/lists",
                core().cache_volume(
                    f"shiryu-apt-lists-debian-{DEBIAN_CODENAME}-slim-{DEBIAN_SNAPSHOT_DATETIME}"
                ),
                sharing=CacheSharingMode.LOCKED,
            )
            .with_new_file(
                path="/etc/apt/apt.conf.d/keep-cache",
                contents='Binary::apt::APT::Keep-Downloaded-Packages "true";\n',
                permissions=0o644,
            )
            .with_exec(["apt-get", "update"])
            .with_exec([*apt_install])
        )
    if SecurityAudit.CONTAINER in security_audit:
        await __run_trivy(platform, container.rootfs())
    return container.with_workdir(str(WORKDIR_PATH))


async def container_git(platform: Platform, security_audit: SecurityAuditType) -> Container:
    """A git container.

    Args:
        platform: The container platform.
        security_audit: Security audit checks that can be enabled in the pipeline.

    Returns:
        A container with git.
    """
    return await container_debian(platform, security_audit, apt_packages={"git"})


async def container_uv(
    platform: Platform,
    security_audit: SecurityAuditType,
    *,
    apt_packages: APTPackages = frozenset(),
) -> Container:
    """A uv container.

    Args:
        platform: The container platform.
        security_audit: Security audit checks that can be enabled in the pipeline.
        apt_packages: The container APT packages.

    Returns:
        A container with uv.
    """
    container = await container_debian(
        platform, security_audit, apt_packages={"pipx", *apt_packages}
    )
    venv_path_str = "/opt/.venv"
    container = (
        container.with_mounted_cache("/root/.cache/pipx", core().cache_volume("shiryu-pipx"))
        .with_env_variable(name="PATH", value="/root/.local/bin:${PATH}", expand=True)
        .with_exec(["pipx", "install", f"uv=={UV_VERSION}"])
        .with_mounted_cache("/root/.cache/uv", core().cache_volume("shiryu-uv"))
        .with_env_variable("UV_LINK_MODE", "copy")
        .with_exec(["uv", "venv", venv_path_str])
        .with_env_variable(name="UV_PROJECT_ENVIRONMENT", value=venv_path_str)
    )
    if SecurityAudit.DEPENDENCIES in security_audit:
        container = container.with_env_variable(name="UV_MALWARE_CHECK", value="1")

    return container
