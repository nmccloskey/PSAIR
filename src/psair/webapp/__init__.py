"""
Streamlit-based viewing utilities for PSAIR manuals.
"""

__all__ = ["render_manual_ui"]


def __getattr__(name: str):
    if name == "render_manual_ui":
        from .manual_viewer import render_manual_ui

        return render_manual_ui
    raise AttributeError(name)
