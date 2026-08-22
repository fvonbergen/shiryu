---
title: How-To Guides
---

# How-To Guides

> "A **how-to guide** addresses a real-world goal or problem, by providing practical directions to help the user who is in that situation.
> A how-to guide always addresses an already-competent user, who is expected to be able to use the guide to help them get their work done. In contrast to a tutorial, a how-to guide is concerned with work rather than *study*.
> A how-to guide might be: *How to store cellulose nitrate film (in motion picture photography) or How to configure frame profiling (in software). Or even: Troubleshooting deployment problems*."
>
> - Source: [Diátaxis: How-to guides](https://diataxis.fr/start-here/#how-to-guides)

# Standard Structural Components of a Diátaxis How-To Guide Section

```
How-To Guide
├── 1. The Scenario / Purpose Statement
├── 2. Prerequisites & Assumptions
├── 3. Practical Action Steps
├── 4. Verification / Test Step
└── 5. Related Tasks
```

## 1. The Scenario / Purpose Statement
**What it is**: An opening statement describing the exact real-world problem or task this guide solves.

**Rule**: Focus on a practical goal (e.g., "How to format JSON with indentation"). Assume the reader is a competent user in a hurry.

Example:

> This guide shows you how to format compact JSON output into a readable, multi-line string using indentation in Python.

## 2. Prerequisites & Assumptions

**What it is**: A list of prior conditions, existing systems, or setup requirements assumed to be true before starting.

**Rule**: Do not teach basic setup here. State what must already exist so the user can quickly check if this guide applies to them.

Example:

> - A working Python environment.
> - Basic familiarity with Python dictionaries.

## 3. Practical Action Steps

**What it is**: A series of practical steps required to complete the task.

**Rule**: Keep instructions direct and actionable. Unlike tutorials, you can include options, alternative flags, and brief warnings about potential pitfalls here.

Example:

> 1. Pass the indent parameter to `json.dumps()`:
> ```python
> import json
>
> data = {"name": "Alice", "skills": ["Python", "Git"]}
>
> # Pretty-print with 4 spaces of indentation
> pretty_json = json.dumps(data, indent=4)
> print(pretty_json)
> ```
> 2. (Optional) To sort keys alphabetically in the output, add `sort_keys=True`:
> ```python
> pretty_json = json.dumps(data, indent=4, sort_keys=True)
> ```

## 4. Verification / Test Step

**What it is**: An explicit instruction showing how to test or confirm that the problem was successfully solved.

**Rule**: Always provide a way to verify success in a real environment (e.g., checking status codes or response payloads).

Example:

> Run your script. The output string should print across multiple lines with aligned indentation rather than a single compressed line:
>
> ```json
> {
>     "name": "Alice",
>     "skills": [
>         "Python",
>         "Git"
>     ]
> }
> ```

## 5. Related Tasks

**What it is**: Links to adjacent How-To Guides or deeper Reference pages.

**Rule**: Only link to directly related operational tasks.

Example:

> - [How-To: Handle Custom Python Objects in JSON]
> - [How-To: Read Large JSON Files Safely]