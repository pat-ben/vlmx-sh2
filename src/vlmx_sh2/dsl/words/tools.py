"""
Tool word definitions — replaced by tool_loader.py.

Tool words are now loaded dynamically from TOML files in shell/tools/
via load_tools_from_directory() in tool_loader.py.

This file is retained as a safe import fallback. TOOL_WORDS_LIST is kept
as an empty list so any existing imports do not break.
"""

from typing import List

from ...core.models.words import ToolWord

TOOL_WORDS_LIST: List[ToolWord] = []
