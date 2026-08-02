# How to Register Custom Plugins

This guide shows you how to extend `my_package` by writing a custom data plugin.

## Solution

Inherit from `BasePlugin` and register your class with the central engine.

1. **Define your plugin:**

    ```python
    from my_package.plugins import BasePlugin


    class UppercasePlugin(BasePlugin):
        def transform(self, payload: dict) -> dict:
            return {k: v.upper() if isinstance(v, str) else v for k, v in payload.items()}
    ```

2. **Register and run:**

    ```python
    from my_package.core import Engine

    engine = Engine(name="plugin_demo")
    engine.register_plugin("uppercase", UppercasePlugin())

    output = engine.process({"message": "hello world"}, plugin="uppercase")
    print(output["message"])  # HELLO WORLD
    ```

!!! note "State Notice"
    Plugins are instantiated once. Avoid storing request state on `self` to maintain thread safety.
