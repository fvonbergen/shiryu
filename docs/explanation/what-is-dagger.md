---
title: What is Dagger?
---

Shiryu is built on top of [Dagger](https://dagger.io/). You do not need to be a Dagger expert to
use Shiryu, but knowing a handful of Dagger concepts makes everything else in this documentation
easier to follow. This page explains those concepts and why they matter.

## The problem Dagger solves

Most projects describe their automation twice:

- once for developers, as shell scripts, `Makefile` targets or README instructions;
- once for CI, as YAML files that only run on GitHub Actions or GitLab CI.

The two versions drift apart. A check that passes on your laptop fails in CI because of a different
tool version, a missing system package or an environment variable nobody documented. Debugging it
means pushing commits and waiting for the pipeline.

Dagger removes the duplication. Automation is written **once, as code**, and it always runs
**inside containers** managed by the Dagger engine. Your laptop and the CI runner execute exactly
the same steps, with the same images and the same tool versions, so a green run locally means a
green run in CI.

## How Dagger works

```plaintext
 ┌──────────────┐   API calls    ┌──────────────────────────────────────────┐
 │  dagger CLI  │ ─────────────▶ │              Dagger engine               │
 │ (your shell  │                │  (runs as a container on Docker/Podman)  │
 │  or CI job)  │ ◀───────────── │                                          │
 └──────────────┘   results      │  ┌────────────┐  ┌────────────┐          │
                                 │  │ container  │  │ container  │  ...     │
        loads                    │  │ ruff check │  │ pytest     │          │
          │                      │  └────────────┘  └────────────┘          │
          ▼                      │          shared build cache              │
 ┌──────────────┐                └──────────────────────────────────────────┘
 │ Dagger module│
 │  (e.g.       │
 │   Shiryu)    │
 └──────────────┘
```

### The engine

The **Dagger engine** does the actual work. The first time you run a `dagger` command, the CLI
starts the engine as a container on your container runtime (usually Docker) and talks to it
through an API. Every step of a workflow (installing dependencies, running a linter, building a
package) runs in a container created by the engine.

You can see which engine your CLI uses with `dagger version`:

```console
$ dagger version
Version:     v1.x.y
commit:      ...
dirty:       no
platform:    linux/amd64
runner-host: image://registry.dagger.io/engine:v1.x.y
```

The `runner-host` line shows the engine image that was started for you. Use the same Dagger
version that Shiryu uses in its CI pipelines; you can find it in the `version` input of the
generated GitHub actions, as shown in [What is Shiryu?](what-is-shiryu.md#local-runs-mirror-ci).

### Modules and functions

A **module** is a package of automation code. A module exposes **functions**, and each function is
a typed operation such as "lint the code" or "run the unit tests". Modules can be written in Python,
Go, TypeScript and other languages through Dagger SDKs.

Shiryu is a Dagger module written in Python. Inside Shiryu, a function looks like a regular Python
method with a decorator. This is the real definition of the type checker function, from
`src/shiryu/sdk/python/modules/checker.py`:

```python
@dagger.function(doc="Run tests in the project of the provided source Directory.")
@dagger.check
async def unit(
    self, *, platform: PlatformDaggerType = PLATFORM_DAGGER_DEFAULT
) -> None:
    ...
```

Dagger turns that method into a command you can call from the CLI. Function names and arguments
are converted to kebab case. Run from a clone of the Shiryu repository (`--load-module=.`
loads the module in the current directory):

```bash
dagger api call --load-module=. python tester unit
```

The function's `doc` and its typed arguments become the command's help text:

```console
$ dagger api call --load-module=. python checker check --help
Run type checks in the project of the provided source Directory.

USAGE
  dagger api call python checker check [arguments] <function>

...

ARGUMENTS
      --platform Platform   Platform config OS and architecture in a
                            Container (default linux/amd64)
```

Functions can return other objects, and you chain calls by writing them one after the other. In
the command above, `python` returns the Python SDK object, `checker` returns the checker module and
`check` runs the check. This chaining is how you navigate Shiryu from the command line.

### Core types

Dagger functions pass a few core types between each other. You will see these names in Shiryu's
help output and in its API reference:

| Type        | What it represents                                                        |
|-------------|---------------------------------------------------------------------------|
| `Container` | A container image plus the commands run in it.                            |
| `Directory` | A directory tree, such as your project source or a build output.          |
| `File`      | A single file.                                                            |
| `Secret`    | A sensitive value (token, password) that is never written to logs.        |
| `Service`   | A long-running container with open ports, such as a Jupyter server.       |
| `Changeset` | The difference between two directories: files added, modified, removed.   |

`Changeset` deserves a special mention. Functions that *change* your project, for example
Shiryu's code formatter or project initializer, do not write to your disk directly. They return a
`Changeset`, and the CLI shows you the changes and lets you apply them. Nothing in your working
tree is modified without you seeing it first.

### Caching

The engine caches every step. When you run the same function twice and its inputs did not change,
the engine reuses the previous result instead of executing it again. Shiryu also uses **cache
volumes** to keep package manager and scanner caches (for example, the `uv` cache and the Trivy
vulnerability database) between runs. The first run of a function is slow; the following runs are
much faster.

### The workspace

When you run a `dagger` command inside a project, that project directory is the **workspace**.
Shiryu reads your project from the workspace, honouring your `.gitignore`, so ignored files such as
`.venv/` or build outputs are never sent to the engine.

## The commands you will use

Shiryu's documentation uses a small set of `dagger` commands:

| Command           | Purpose                                                                       |
|-------------------|-------------------------------------------------------------------------------|
| `dagger api call` | Call any function of a module, e.g. `dagger api call python tester unit`.     |
| `dagger check`    | Run every function marked as a *check* (linters, type checks, tests, audits). |
| `dagger generate` | Run the module's generators. Shiryu uses it to initialize a project.          |
| `dagger version`  | Print the CLI and engine versions.                                            |

Two options and one environment variable appear in almost every example:

| Option or variable   | Effect                                                                     |
|----------------------|----------------------------------------------------------------------------|
| `--progress=plain`   | Prints the log as plain text instead of the interactive terminal view.     |
| `--load-module=<ref>`| Selects the module: a local path (`.`) or a Git URL.                       |
| `DO_NOT_TRACK=1`     | Disables Dagger's anonymous usage telemetry.                               |

Use `--progress=plain` in CI, when piping output, or whenever you want to read the full log.
Shiryu sets `DO_NOT_TRACK=1` in every CI pipeline it generates, and the examples in this
documentation use it too.

### A complete example

Putting it together, this command runs Shiryu's type checker on the project in the current
directory, loading Shiryu straight from GitHub:

```bash
DO_NOT_TRACK=1 dagger                                         \
  --progress=plain                                            \
  api                                                         \
    call                                                      \
      --load-module=https://github.com/fvonbergen/shiryu.git  \
      python                                                  \
        checker                                               \
          check
```

Read it from top to bottom:

1. `DO_NOT_TRACK=1` turns telemetry off for this command.
2. `--progress=plain` asks for a plain text log.
3. `api call` calls a function.
4. `--load-module=…` loads Shiryu from its Git repository.
5. `python checker check` navigates to the Python SDK, then the checker module, then the `check`
   function.

## Dagger Cloud

[Dagger Cloud](https://dagger.io/cloud) is an optional web service that stores the traces of your
runs, so you can inspect every step of a pipeline in a browser. Dagger reads its token from the
`DAGGER_CLOUD_TOKEN` environment variable. The CI pipelines generated by Shiryu expect a secret
with that name; locally it is not required.

## Why Shiryu builds on Dagger

**One definition, every environment.** Shiryu defines each step (lint, test, build, release) once
as a Dagger function. The GitHub Actions and GitLab CI files that Shiryu generates are thin
wrappers that call those same functions, so local runs and CI runs cannot drift apart.

**Isolation over convenience.** Every step runs in a container instead of your local Python
environment. The cost is a slower first run, while images and caches are downloaded. The benefit
is that results do not depend on what happens to be installed on your machine or on the CI runner.

**Typed interfaces over shell scripts.** Because functions have typed arguments and documented
flags, `--help` always tells you what a step accepts, and wrong arguments fail before anything
runs.

## Further reading

- [What is Shiryu?](what-is-shiryu.md)
- [Dagger documentation](https://docs.dagger.io/)
- [Dagger Python SDK reference](https://dagger-io.readthedocs.io/)
