# File: src/vlmx_sh2/storage/paths.py
"""
Shared path utilities for storage backends.

Both JSON and SQLite backends need to resolve data directories and
company folder paths.  These helpers live here so neither backend
owns them.
"""

from pathlib import Path

from ..models.context import Context
from ..utils.context_helpers import is_sys


def get_data_directory_path(context: Context) -> Path:
    """Get the path to the data directory based on context."""
    if is_sys(context):
        base_path = context.sys_path or Path.cwd()
        return base_path / "data"
    else:
        return context.org_db_path.parent.parent if context.org_db_path else Path.cwd() / "data"


def get_company_folder_path(company_name: str, context: Context) -> Path:
    """Get the path to a specific company's folder."""
    return get_data_directory_path(context) / company_name.lower()
