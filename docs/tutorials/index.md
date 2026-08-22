---
title: Tutorials
---

# Tutorials

> "A **tutorial is a lesson**, that takes a student by the hand through a learning experience. A tutorial is always *practical*: the user *does* something, under the guidance of an instructor. A tutorial is designed around an encounter that the learner can make sense of, in which the instructor is responsible for the learner’s safety and success.
> A driving lesson is a good example of a tutorial. The purpose of the lesson is to develop skills and confidence in the student, not to get from A to B. A software example could be: *Let’s create a simple game in Python*.
> *The user will learn through what they do* - not because someone has tried to teach them.
> In documentation, the special difficulty is that the instructor is condemned to be absent, and is not there to monitor the learner and correct their mistakes. The instructor must somehow find a way to be present through written instruction alone."
>
> - Source: [Diátaxis: Tutorials](https://diataxis.fr/start-here/#tutorials)

# Standard Structural Components of a Diátaxis Tutorial Section

```
Getting Started (Tutorial Document)
├── 1. Destination Statement (The Goal)
├── 2. Prerequisites
├── 3. Step-by-Step Execution Sequence
└── 4. Immediate Next Steps
```

## 1. Destination Statement (The Goal)

**What it is**: A single intro paragraph setting expectations about the outcome of the lesson.

**Rule**: State what the learner will build or achieve, not abstract concepts they will "understand." Avoid options or ambiguous outcomes.

Example:

> In this tutorial, you will write your first Python script using the built-in `json` module to convert a Python dictionary into a JSON file on your computer.

## 2. Prerequisites

**What it is**: The absolute baseline software, environment, or access required to run the steps.

**Rule**: Keep it strictly minimal. Pick one environment or path and stick to it (specify the exact setup used in the guide).

Example:

> - Python 3 installed on your system.
> - Terminal / Command Line access.

## 3. Step-by-Step Execution Sequence

**What it is**: The main hands-on body of the tutorial, broken into small sequential steps. Each step includes an Action, Expected Output, and an Observation Prompt.

**Rule**: Every step must be guaranteed to work 100% of the time. Never offer choices, branches, or troubleshooting alternatives. Always show the exact output so the user can verify success.

Example:

> **Step 1: Write data to a JSON file**
>
> Create a file named `save_user.py` and add the following code:
>
> ```python
> import json
>
> user_data = {"name": "Alice", "age": 30, "is_active": True}
>
> with open("user.json", "w") as file:
>   json.dump(user_data, file)
>
> print("File created successfully!")
> ```
>
> Run the script in your terminal:
>
> ```bash
> python save_user.py
> ```
>
> Expected Output:
> ```
> File created successfully!
> ```
>
> *Notice how `user.json` was created in your folder containing `{"name": "Alice", "age": 30, "is_active": true}`—the Python `True` was automatically converted to the JSON `true`.

## 4. Immediate Next Steps

**What it is**: A brief closing section linking to other documentation pages once the tutorial is completed.

**Rule**: Point the user away from the tutorial toward How-To Guides (to solve real tasks) or Explanations (to study theory). Do not extend the tutorial further.

Example:

> Congratulations! You created your first JSON file using Python.
>
> - To learn how to read and update existing files, see our [How-To: Parse and Modify Local JSON Files].
> - To understand how Python maps types like dictionaries to JSON, read [Explanation: Python to JSON Type Conversions].