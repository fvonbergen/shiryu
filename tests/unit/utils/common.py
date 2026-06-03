"""common module."""

import json
from typing import Any, NamedTuple, final

import dagger

Paths = tuple[str, ...]


@final
class DirectoryOutput(NamedTuple):
    """DirectoryOutput class."""

    paths: Paths


def ignore_pytest[T: type](cls: T) -> T:
    """
    Mark a class to be ignored by pytest's test collection.

    Args:
        cls: The class to shield from pytest.

    Returns:
        The input class with `__test__ = False` dynamically applied.
    """
    target: Any = cls
    target.__test__ = False
    return cls


async def get_all_paths(dir_: dagger.Directory) -> Paths:
    """
    Takes a dagger.Directory object and returns every single file and folder path recursively.

    Args:
        dir_: The target Dagger Directory.

    Returns:
        The sorted list of all paths within the provided directory.
    """
    # Inline python script utilizing optimized, low-level os.scandir traversal
    python_script = """
# This script recursively crawls a workspace to return a JSON array of all file and folder paths.
import os
import json

from pathlib import PurePosixPath, Path

files_list = []
all_directories = set()
parent_directories = set()

root_abs = PurePosixPath(Path.cwd().resolve())

def crawl(current_dir_str: str) -> None:
    current_dir = PurePosixPath(current_dir_str)
    is_root = (current_dir == root_abs)

    current_dir_rel = current_dir.relative_to(root_abs)

    try:
        with os.scandir(current_dir_str) as entries:
            for entry in entries:
                rel_path_str = str(
                    PurePosixPath(entry.name)
                    if is_root
                    else current_dir_rel / entry.name
                )

                if entry.is_dir(follow_symlinks=False):
                    all_directories.add(f"{rel_path_str}/")

                    if not is_root:
                        parent_directories.add(f"{current_dir_rel}/")

                    crawl(entry.path)
                else:
                    files_list.append(rel_path_str)

                    if not is_root:
                        parent_directories.add(f"{current_dir_rel}/")
    except PermissionError:
        pass

crawl(str(root_abs))

empty_directories = all_directories - parent_directories
final_paths = files_list + list(empty_directories)

print(json.dumps(final_paths))
"""
    container_project_path_str = "/project"
    output_json = await (
        dagger.dag.container(platform=dagger.Platform("linux/amd64"))
        .from_("public.ecr.aws/debian/debian:trixie-slim")
        .with_env_variable(name="LC_ALL", value="C.UTF-8")
        # Prevent hanging scripts due to interactive prompts
        .with_env_variable(name="DEBIAN_FRONTEND", value="noninteractive")
        # Prevent crashes from special characters/emojis in filenames or logs
        .with_env_variable(name="LC_ALL", value="C.UTF-8")
        # Prevent logs from being lost or delayed in memory buffers
        .with_env_variable(name="PYTHONUNBUFFERED", value="1")
        .with_mounted_cache(
            "/var/cache/apt/archives",
            dagger.dag.cache_volume("pytest-apt-archives-debian-trixie-slim"),
        )
        .with_mounted_cache(
            "/var/lib/apt/lists",
            dagger.dag.cache_volume("pytest-apt-lists-debian-trixie-slim"),
        )
        .with_new_file(
            path="/etc/apt/apt.conf.d/keep-cache",
            contents='Binary::apt::APT::Keep-Downloaded-Packages "true";\n',
            permissions=0o644,
        )
        .with_exec(["apt-get", "update"])
        .with_exec(["apt-get", "install", "--assume-yes", "--no-install-recommends", "python3"])
        .with_mounted_directory(container_project_path_str, dir_)
        .with_workdir(container_project_path_str)
        .with_exec(["python3", "-c", python_script])
        .stdout()
    )

    paths_list = json.loads(output_json.strip())
    return tuple(sorted(paths_list))
