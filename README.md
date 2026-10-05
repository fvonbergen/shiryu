# Shiryu

Shiryu is a cross-language SDK built as a [dagger.io](https://dagger.io/)
module. Its goal is to standardize software repository structures and provide
local-first developer commands that mirror your CI/CD pipeline exactly.

Source code:
- [Shiryu (GitHub)](https://github.com/fvonbergen/shiryu)
- [Shiryu (GitLab)](https://gitlab.com/fvonbergen1/shiryu)

Documentation:
- [Shiryu Pages (GitHub)](https://fvonbergen.github.io/shiryu)
- [Shiryu Pages (GitLab)](https://shiryu-1fe986.gitlab.io/)

## For users

### Prerequisites

> [!IMPORTANT]
> **VCS Requirement:** Shiryu projects must use `git`. Shiryu executes version
control commands internally and depends on the `.git/` directory and `.gitignore` configuration.

To install the Dagger CLI, follow the official instructions at
[https://docs.dagger.io/install/](https://docs.dagger.io/install/).

### Installation & Execution

Install Shiryu directly into your workspace using `dagger module install`:

```bash
dagger module install https://github.com/fvonbergen/shiryu.git
```

Once installed, invoke functions directly via the Dagger CLI:

```bash
DO_NOT_TRACK=1 dagger api                                 \
  call                                                    \
  --verbose=4                                             \
  shiryu                                                  \
  <shiryu_function>
```

Alternatively, you can run functions directly from the remote reference without prior installation:

```bash
DO_NOT_TRACK=1 dagger api                                 \
  call                                                    \
  --verbose=4                                             \
  --load-module=https://github.com/fvonbergen/shiryu.git  \
  <shiryu_function>
```

### Python SDK

This SDK provides a Dagger-based module to initialize, manage, and update Python
project structures.

> [!IMPORTANT]
> Prerequisites: Shiryu projects must use `uv` as the package manager. The
underlying automation executes `uv` commands internally and relies on the
presence of a `uv.lock` file to manage deterministic environments.

List commands:

```bash
DO_NOT_TRACK=1 dagger api                                 \
  call                                                    \
  --verbose=4                                             \
  --load-module=https://github.com/fvonbergen/shiryu.git  \
  python --help
```

Initialize a new project:

```bash
DO_NOT_TRACK=1 dagger api                                 \
  call                                                    \
  --verbose=4                                             \
  --load-module=https://github.com/fvonbergen/shiryu.git  \
  python                                                  \
  init                                                    \
    --project-directory=<project_directory_path>          \
    --project-name=<project_name>                         \
```

Update a project:

```bash
DO_NOT_TRACK=1 dagger api                                 \
  call                                                    \
  --verbose=4                                             \
  --load-module=https://github.com/fvonbergen/shiryu.git  \
  python                                                  \
  init                                                    \
    --project-directory=<project_directory_path>          \
    --project-name=<project_name>                         \
    --is-update                                           \
```

### With GitHub

Assumes the Dagger Cloud token is in a repository secret named
`DAGGER_CLOUD_TOKEN` set via the GitHub UI/CLI.

### With GitLab

Assumes the Dagger Cloud token is in a repository CI/CD variable named
`DAGGER_CLOUD_TOKEN` set via the GitLab UI.

## For developers

### Local Execution & Testing

To run Shiryu locally when cloned from source:

```bash
git clone https://github.com/fvonbergen/shiryu.git
cd shiryu
DO_NOT_TRACK=1 dagger api \
  call                    \
  --verbose=4             \
  --load-module=.         \
  <shiryu_function>
```

To run Shiryu directly from the remote repository:

```bash
DO_NOT_TRACK=1 dagger api                                 \
  call                                                    \
  --verbose=4                                             \
  --load-module=https://github.com/fvonbergen/shiryu.git  \
  <shiryu_function>
```

### Local virtual environment

Because Dagger reads the `uv.lock` file behind the scenes, `uv` is the default
package manager for Shiryu.

#### Set up a local virtual environment

To bootstrap and populate your local development environment, run:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install uv

# Install base project dependencies exactly as locked
UV_MALWARE_CHECK=1 uv sync --locked --no-install-project
# Install ALL extras
UV_MALWARE_CHECK=1 uv sync --locked --no-install-project --all-groups
# Install a specific extra
UV_MALWARE_CHECK=1 uv sync --locked --no-install-project --group=<group_section>
```

#### Update lockfile

`uv.lock` is the standard lockfile format generated by `uv`. It is a
prerequisite for both Shiryu and the Python Dagger SDK client.

To regenerate or update the lockfile after modifying dependencies:
```bash
UV_MALWARE_CHECK=1 uv lock --upgrade
```

To synchronize your local `.venv` exactly with the existing `uv.lock` file:
```bash
UV_MALWARE_CHECK=1 uv sync --no-install-project
```
