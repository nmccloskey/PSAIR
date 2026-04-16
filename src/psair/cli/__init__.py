"""
CLI entry points and argument definitions for PSAIR.
"""

__all__ = ["main"]


def __getattr__(name: str):
    if name == "main":
        from .main import main

        return main
    raise AttributeError(name)
