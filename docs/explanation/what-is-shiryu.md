---
title: What is Shiryu?
---

Shiryu is a cross-language SDK built as a [Dagger](https://dagger.io/) module. It gives your
repository a standard structure and a standard set of developer commands (lint, type check, test,
audit, build, document, release) that run **the same way on your machine and in CI**.

If you have not used Dagger before, read [What is Dagger?](what-is-dagger.md) first. This page
assumes you know what a Dagger module and a Dagger function are.

## The problem Shiryu solves

Starting a new project usually means repeating the same chores:

- choosing and configuring a linter, a formatter, a type checker and a test runner;
- writing a `pyproject.toml`, a documentation site configuration and a changelog;
- writing CI pipelines for GitHub or GitLab, and keeping them in sync with the local scripts;
- deciding how releases are tagged, how the changelog is generated and how packages are published.

Every project ends up slightly different, and every difference is something a contributor has to
learn. Shiryu makes these decisions once and applies them to any project that uses it:

- **A standard project structure.** `init` generates the configuration files for every tool, the
  documentation skeleton and the CI pipelines.
- **Standard commands.** Each task is a Dagger function with the same name in every project:
  `python linter lint-code`, `python tester unit`, `python releaser release`, and so on.
- **Local runs that mirror CI.** The generated CI pipelines call exactly the same functions you
  run locally.

## Local runs mirror CI

This is the central idea of Shiryu, so it is worth seeing concretely. Locally, you run the unit
tests with:

```bash
DO_NOT_TRACK=1 dagger                                         \
  --progress=plain                                            \
  api                                                         \
    call                                                      \
      --load-module=https://github.com/fvonbergen/shiryu.git  \
      python                                                  \
        tester                                                \
          unit
```

In CI, the pipelines that Shiryu generates for your project run the same function. The files
below are included verbatim from this repository, which Shiryu generated for itself, so they always
show the current versions:

**GitHub Actions**, in `.github/actions/tester_unit/action.yml`:

```yaml
--8<-- ".github/actions/tester_unit/action.yml"
```

**GitLab CI**, in `.gitlab/jobs/.tester_unit.yml`:

```yaml
--8<-- ".gitlab/jobs/.tester_unit.yml"
```

The GitLab job extends `.dagger`, defined in `.gitlab/jobs/.dagger.yml`, which installs the Dagger
CLI:

```yaml
--8<-- ".gitlab/jobs/.dagger.yml"
```

All of them call `python tester unit`. CI adds nothing of its own: it installs Dagger, checks
out the code and calls the function. If the tests pass locally, they pass in CI.

## How Shiryu is organized

Shiryu is organized in three levels, and the command line follows the same structure:

```plaintext
shiryu                     the Dagger module
└── python                 an SDK: one per programming language
    ├── init               initialize or update a project
    ├── linter             a module: a group of related functions
    │   ├── lint-code      a function
    │   ├── fix-code
    │   └── ...
    ├── tester
    │   └── unit
    └── ...
```

1. **The Shiryu module** is the entry point that Dagger loads.
2. **SDKs** group everything for one programming language. Python is the only SDK today; the
   design leaves room for others.
3. **Modules** inside an SDK group functions around one concern: linting, testing, releasing…

You can explore this tree with `--help` at any level. Asking the Python SDK for help lists its
modules:

```console
$ dagger api call --load-module=. python --help
USAGE
  dagger api call python <function>

AVAILABLE COMMANDS
  auditor      Python SDK Security Auditor.
  builder      Python SDK builder.
  checker      Python SDK checker.
  documenter   Python SDK documenter.
  init         Returns a changeset to initialize a project with the SDK module
               directory.
  jupyter      Python SDK jupyter.
  linter       Python SDK linter.
  releaser     Python SDK Releaser.
  tester       Python SDK tester.
```

## The Python SDK at a glance

Each module wraps one or more well-known tools. You do not install any of them: they run inside
containers managed by Dagger, at the versions Shiryu pins.

| Module       | Functions                                    | Tools it runs                     |
|--------------|----------------------------------------------|-----------------------------------|
| `init`       | *(function itself)*                          | Generates the project files       |
| `linter`     | `lint-code`, `fix-code`                      | Ruff (lint and format)            |
| `linter`     | `lint-documentation`, `fix-documentation`    | PyMarkdown                        |
| `linter`     | `lint-vcs`                                   | commit-check                      |
| `checker`    | `check`                                      | ty (type checker)                 |
| `tester`     | `unit`                                       | pytest                            |
| `auditor`    | `audit`                                      | `uv audit` (dependency CVEs)      |
| `builder`    | `build`, `test`, `publish`                   | Hatch, uv, Trivy (image scan)     |
| `documenter` | `document`, `audit`                          | Zensical, an LLM through Dagger   |
| `releaser`   | `release`, `dry-run`                         | Commitizen, the GitHub/GitLab API |
| `jupyter`    | `service`, `changeset`                       | Jupyter                           |

### Checks

Some functions are marked as **checks**. They verify the project without changing it, and
`dagger check` runs all of them at once:

- `linter lint-code`, `linter lint-documentation`, `linter lint-vcs`
- `checker check`
- `auditor audit`
- `builder test`

### Functions that change your project

Functions such as `init`, `linter fix-code` and `linter fix-documentation` return a Dagger
`Changeset`. Dagger shows you the changes before anything is written to your working tree.

## Requirements

Shiryu makes a few assumptions about the projects it manages:

- **Git.** Projects must be Git repositories. Shiryu runs Git commands internally (for example,
  to lint commit messages or create release tags) and honours your `.gitignore`.
- **uv, for Python projects.** The Python SDK uses [uv](https://docs.astral.sh/uv/) as package
  manager and relies on the `uv.lock` file to build reproducible environments.
- **Dagger and a container runtime** to run the Dagger engine, usually Docker.

## Design trade-offs

**Conventions over configuration.** Shiryu chooses the tools and their configuration for you.
That makes every Shiryu project look and behave the same, at the cost of flexibility: if your
project needs a different test runner, Shiryu is not a good fit for that part.

**Generated files are owned by Shiryu.** Running `init` with `--is-update` regenerates the files
that Shiryu manages, so projects pick up new conventions automatically. Local edits to those
files are overwritten, which is why Shiryu keeps its own configuration in clearly separated files
(`ruff.toml`, `ty.toml`, `pytest.unit.ini`, `zensical.toml`, …).

**Containers everywhere.** Every task runs in a container, which costs some time on the first run
but guarantees that results do not depend on the developer's machine.

## Further reading

- [What is Dagger?](what-is-dagger.md)
- [Shiryu on GitHub](https://github.com/fvonbergen/shiryu)
- [Shiryu on GitLab](https://gitlab.com/fvonbergen1/shiryu)
