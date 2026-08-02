# Getting Started

In this tutorial, you will create and run your first pipeline in under 5 minutes.

## Prerequisites

Ensure you have Python 3.10+ installed and the package installed:

```bash
pip install my_package
```

Step 1: Initialize the Engine

Create a file named `quickstart.py` and import Engine:
```Python
from my_package.core import Engine

engine = Engine(name="tutorial_runner")
print(f"Engine initialized: {engine.name}")
```

Step 2: Process Data

Pass a dictionary payload to the engine:
Python

```Python
result = engine.process({"input_path": "data.csv"})
print(f"Result status: {result['status']}")
```

Step 3: Run the Script

Execute the script from your terminal:
Bash

```bash
python quickstart.py
```

You've successfully run your first pipeline! Check out the How-To Guides to extend functionality.
