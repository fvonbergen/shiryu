# Shiryu

Shiryu is a SDK for programming languages built in the form of a
[dagger.io](https://dagger.io/) module. Its goal is to standardize the structure
of software repositories and provide updated commands for developer to interact
with source code. These commands execute the same code that runs in the CI/CD
pipeline.

Source code documentation can be found in [Shiryu](https://fvonbergen.github.io/shiryu)

## For users

Shiryu can be used by cloning the repository and running it with the dagger
python SDK or by installing it with Dagger.

To install Dagger follow the instructions in [https://docs.dagger.io/install/](https://docs.dagger.io/install/).

To use Shiryu with a cloned repository run:

```bash
git clone https://github.com/fvonbergen/shiryu.git
cd shiryu
DO_NOT_TRACK=1 dagger call \
    <shiryu_function>
```

To run Shiryu using with dagger run:

```bash
DO_NOT_TRACK=1 dagger --mod=https://github.com/fvonbergen/shiryu.git call \
  <shiryu_function>
```

### Python SDK

List commands:

```bash
DO_NOT_TRACK=1 dagger call \
  python --help
```

Initialize a new project:

```bash
DO_NOT_TRACK=1 dagger call        \
  python                          \
  init                            \
    --project=<project_path>      \
    --project-name=<project_name> \
  export                          \
    --path=<output_directory_path>
```

Update a project:

```bash
DO_NOT_TRACK=1 dagger call        \
  python                          \
  init                            \
    --project=<project_path>      \
    --project-name=<project_name> \
    --is-update                   \
  export                          \
    --path=<output_directory_path>
```

### With GitHub

Assumes the Dagger Cloud token is in a repository secret named
`DAGGER_CLOUD_TOKEN` set via the GitHub UI/CLI.

### With GitLab

Assumes the Dagger Cloud token is in a repository CI/CD variable named
`DAGGER_CLOUD_TOKEN` set via the GitLab UI.

## For developers

The [Dagger Python SDK](https://github.com/dagger/dagger/tree/main/sdk/python)
loads/installs the Shiryu module inside the dagger engine using a container that
runs in it. The container has a default base-image, but can be configured to
pull it from a local container registry.

Shiryu's version is generated dynamically using [git](https://git-scm.com/) and
[hatch-vcs](https://github.com/ofek/hatch-vcs). If [git](https://git-scm.com/)
is not installed it will fall back to `0.0.0+unknown`.

Shiryu relies on its version for generating template files. For this reason it
is useful for development to have Shiryu installed with its correct version.

In order to accomplish it, we need to provide to the
[Dagger Python SDK](https://github.com/dagger/dagger/tree/main/sdk/python)
access to a container registry with a container image with [git](https://git-scm.com/).

```bash
git clone https://github.com/fvonbergen/shiryu.git
./local_registry.sh
```

In the [pyproject.toml](pyproject.toml) file:

- Uncomment the lines inside the "XML" tag `<develop>` comment.
- Comment the lines inside the "XML" tag `<release>` comment.

### Local virtual environment

To build a local virtual environment run:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install uv
uv pip install --requirement pyproject.toml --no-sources --upgrade
uv pip install --requirement pyproject.toml --no-sources --upgrade --extra=<extra_section>
```
