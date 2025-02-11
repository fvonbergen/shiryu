"""class_name module."""

from typing import final

from .case import camel_case_to_snake_case


class ClassName:
    """Class with defined name."""

    @final
    @classmethod
    def name(cls) -> str:
        """
        Get class name.

        Returns:
            Class name.
        """
        class_name = cls.__qualname__
        return camel_case_to_snake_case(class_name)
