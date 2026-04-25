"""python-pptx renderers.

Each renderer maps one ``ContentBlock.kind`` to slide shapes. Add new kinds by:
1. extending ``ContentBlockKind`` in ``state.py``,
2. registering a renderer in ``RENDERERS`` in ``render.py``,
3. covering it with a test in ``tests/pptx/``.
"""

from .render import render_deck

__all__ = ["render_deck"]
