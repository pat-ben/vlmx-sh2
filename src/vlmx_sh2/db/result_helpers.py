# File: src/vlmx_sh2/storage/result_helpers.py
"""
Shared result-dict constructors used by all storage backends.

Every backend method that returns a dict MUST use these helpers so
that ``_wrap_storage_result()`` in ``database.py`` can rely on a
consistent shape:

  success → ``{"success": True,  "message": str, …extra}``
  failure → ``{"success": False, "error": str}``
"""

from typing import Any, Dict


def success_result(message: str, **data: Any) -> Dict[str, Any]:
    """Create a success result dictionary."""
    return {"success": True, "message": message, **data}


def error_result(error: str) -> Dict[str, Any]:
    """Create an error result dictionary."""
    return {"success": False, "error": error}
