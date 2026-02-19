"""
TOML tool loader.

Loads ToolWord definitions from TOML files in the shell/tools/ directory.
This replaces the hardcoded tool definitions in tools.py with dynamic configuration.
"""

import logging
from pathlib import Path
from typing import List

import tomllib

from ...core.enums.core import ContextLevel
from ...core.models.words import ToolWord


logger = logging.getLogger(__name__)


def load_tools_from_directory(tools_dir: Path) -> List[ToolWord]:
    """
    Load ToolWord objects from TOML files in a directory.

    Args:
        tools_dir: Path to directory containing .toml files

    Returns:
        List of ToolWord objects loaded from valid TOML files

    Notes:
        - Skips files that fail to parse (logs warning)
        - Returns empty list if directory doesn't exist
        - Reads parameter names from [parameters] section keys
    """
    tools = []

    if not tools_dir.exists():
        logger.debug(f"Tools directory does not exist: {tools_dir}")
        return tools

    toml_files = list(tools_dir.glob("*.toml"))

    if not toml_files:
        logger.debug(f"No TOML files found in tools directory: {tools_dir}")
        return tools

    for toml_file in toml_files:
        try:
            with open(toml_file, "rb") as f:
                data = tomllib.load(f)

            tool_data = data.get("tool", {})
            if not tool_data:
                logger.warning(f"TOML file missing [tool] section: {toml_file}")
                continue

            tool_id = tool_data.get("id")
            if not tool_id:
                logger.warning(f"TOML file missing 'id' in [tool] section: {toml_file}")
                continue

            parameters = list(data.get("parameters", {}).keys())

            tool_word = ToolWord(
                id=tool_id,
                name=tool_data.get("name", ""),
                description=tool_data.get("description", ""),
                aliases=tool_data.get("aliases", []),
                context=ContextLevel.APP,
                parameters=parameters,
            )

            tools.append(tool_word)
            logger.debug(f"Loaded tool '{tool_id}' from {toml_file}")

        except tomllib.TOMLDecodeError as e:
            logger.warning(f"Failed to parse TOML file {toml_file}: {e}")
            continue
        except Exception as e:
            logger.warning(f"Error loading tool from {toml_file}: {e}")
            continue

    return tools
