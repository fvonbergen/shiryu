---
title: Reference
---

# Reference

> "**Reference guides contain the technical description** - facts - that a user needs in order to do things correctly: accurate, complete, reliable information, free of distraction and interpretation. They contain *propositional or theoretical knowledge*, not guides to action.
> Like a how-to guide, reference documentation serves the user who is at work, and it’s up to the user to be sufficiently competent to interpret and use it correctly.
> *Reference material is neutral*. It is not concerned with what the user is doing. A marine chart could be used by a ship’s navigator to plot a course, but equally well by an investigating judge.
> Where possible, the architecture of reference documentation should reflect the structure or architecture of the thing it’s describing - just like a map does. If a method is part of a class that belongs to a certain module, then we should expect to see the same relationship in the documentation too."
>
> - Source: [Diátaxis: Reference](https://diataxis.fr/start-here/#reference)

# Standard Structural Components of a Diátaxis Reference Section

```
Reference
├── 1. Short Technical Summary
├── 2. CLI & System Specification       (Handwritten CLI / Config specs)
├── 3. API Overview                     (Auto-generated symbol list & TypeAliases)
├── 4. API Reference                    (Auto-generated function/class details)
└── 5. Code Examples                    (Minimal execution snippets)
```

## 1. Short Technical Summary

**What it is**: A concise, neutral description of the module, package, or system interface being documented.

**Rule**: Keep it strictly factual and neutral. Avoid tutorial language, introductory fluff, or marketing phrases.

Example:

> `json` — Native Python module and command-line utility providing interfaces for encoding, decoding, validating, and formatting JSON data.

## 2. CLI & System Specification

**What it is**: The technical specification for system-level interfaces like CLI commands, .env variables, or configuration files that are written manually.

**Rule**: Use standard bracket/flag notation for commands and provide exhaustive tables for flags or configuration keys.

Example:

> **json.tool** Command-Line Interface
> Syntax Specification:
> ```bash
> python -m json.tool [infile] [outfile] [--sort-keys] [--json-lines]
> ```
>
> Parameters & Flags Table:
>
> |Flag / Parameter |Type |Required |Default    |Description                                          |
> |-----------------|-----|---------|-----------|-----------------------------------------------------|
> |infile           |Path |No       |sys.stdin  |Path to the input JSON file to read.                 |
> |outfile          |Path |No       |sys.stdout |Path to write the formatted output.                  |
> |--sort-keys      |Flag |No       |False      |Sorts output dictionary keys alphabetically.         |
> |--json-lines     |Flag |No       |False      |Parses each line of input as a separate JSON object. |
>
> Minimal Interface Example:
>
> ```bash
> echo '{"b": 2, "a": 1}' | python -m json.tool --sort-keys
> {
>     "a": 1,
>     "b": 2
> }
> ```

## 3. API Overview

**What it is**: The top-level inventory generated automatically from code docstrings and type annotations. It provides an index of all exported symbols alongside custom type definitions.

**Rule**: Place type aliases first so readers understand custom parameter type hints used in the detailed function signatures in Section 4.

Example:

> Module Export Index (\_\_all\_\_):
>
> |Symbol       |Type     |Description                                            |
> |-------------|---------|-------------------------------------------------------|
> |`json.dump()`  |Function |Serializes object as a JSON stream to a file pointer.  |
> |`json.dumps()` |Function |Serializes object to a JSON formatted `str`.             |
> |`json.load()`  |Function |Deserializes a JSON file stream to a Python object.    |
> |`json.loads()` |Function |Deserializes a JSON string or bytes to a Python object.|
>
> Type Aliases & Definitions:
> ```python
> from typing import Union
>
> JSONPrimitive = Union[str, int, float, bool, None]
> JSONStructure = Union[dict[str, "JSONValue"], list["JSONValue"]]
> JSONValue = Union[JSONPrimitive, JSONStructure]
> ```

## 4. API Reference

**What it is**: The detailed technical specifications for every exported function, class, or method. Signatures, arguments, return values, and exceptions are combined under each specific member block.

**Rule**: Group class methods directly under their parent class. Document exact exception types raised under failure conditions.

Example:

> **json.dumps()**
>
> Signature:
> ```python
> json.dumps(
>     obj: JSONValue, 
>     *, 
>     indent: int | str | None = None, 
>     sort_keys: bool = False
> ) -> str
> ```
>
> Parameters Table:
>
> |Parameter|Type         |Required |Default|Description                                          |
> |---------|-------------|---------|-------|-----------------------------------------------------|
> |`obj`      |`JSONValue`    |Yes      |—      |Python data structure to serialize.                  |
> |`indent`   |`int\|str\|None` |No       |`None`   |Spaces or indentation string for pretty-printing.    |
> |`sort_keys`|`bool`         |No       |`False`  |If `True`, sorts output dictionary keys alphabetically.|
>
> Return Values & Exceptions:
>
> - Returns: `str` — UTF-8 encoded valid JSON text string.
> - Raises: `TypeError` — Raised if `obj` contains data types that cannot be serialized.

## 4. Return Values & Errors

**What it is**: Explicit technical specifications on outputs, return types, exceptions thrown, or status codes returned.

**Rule**: Document all edge-case error conditions and exact data structures returned by the call.

Example:

> - Returns: A UTF-8 `str` object containing valid JSON text.
> - Raises: `TypeError` if `obj` contains data types that cannot be serialized (e.g., sets, datetime objects, or functions).

## 5. Minimal Code Examples

**What it is**: A stripped-down code block illustrating direct Python invocation of the API.

**Rule**: Keep it minimal and functional—no complex business logic, narratives, or step-by-step tutorial explanations.

Example:

> ```python
> import json
>
> data: json.JSONValue = {"b": 2, "a": 1}
> output: str = json.dumps(data, indent=2, sort_keys=True)
> print(output)
> ```