"""
UI field display model.

Represents a single entity field prepared for rendering in the right pane.
"""

from typing import Any, Optional

from pydantic import BaseModel


class FieldDisplay(BaseModel):
    """A single entity field ready for UI rendering."""

    name: str                 # field name e.g. "legal"
    value: Optional[Any]      # actual stored value, None if not set
    is_set: bool              # True if value is not None and not empty string
    display_value: str        # human-readable value or "—" if not set
