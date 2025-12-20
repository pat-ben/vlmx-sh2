"""Base types for VLMX DSL.

This module contains shared types used across the DSL and interpreter modules.
These are the foundational types that other modules build upon.

Classes:
- Context: Navigation and session context for commands
- CommandModel: Base class for all VLMX commands
"""

from __future__ import annotations


from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import BaseModel, field_validator, model_validator
from pydantic.config import ConfigDict



class Context(BaseModel):
    """Navigation and session context passed into commands.

    The context is treated as immutable/frozen; navigation commands should
    construct new Context instances rather than mutating an existing one.
    """

    # Pydantic v2 configuration
    model_config = ConfigDict(frozen=True)

    # Context level tracking
    level: int = 0  # 0=VLMX, 1=Company, 2=Plugin

    # Platform level (level 0)
    platform_path: Optional[Path] = None

    # Company level (level 1+)
    company_id: Optional[int] = None
    company_name: Optional[str] = None
    company_db_path: Optional[Path] = None

    # Plugin level (level 2)
    plugin_id: Optional[str] = None
    scenario_id: Optional[int] = None

    # Session (Step 2)
    user_id: Optional[int] = None
    user_email: Optional[str] = None

    @field_validator("level")
    @classmethod
    def _validate_level_range(cls, v: int) -> int:
        if v not in (0, 1, 2):
            raise ValueError("level must be 0, 1, or 2")
        return v

    @model_validator(mode="after")
    def _validate_level_consistency(self) -> "Context":
        # Level 0: no company or plugin fields
        if self.level == 0:
            if any((self.company_id, self.company_name, self.plugin_id)):
                raise ValueError(
                    "At level 0, company_id, company_name, and plugin_id must all be None"
                )
        # Level 1: must have company, no plugin
        elif self.level == 1:
            if self.company_id is None or self.company_name is None:
                raise ValueError(
                    "At level 1, company_id and company_name must not be None"
                )
            if self.plugin_id is None is False and self.plugin_id is not None:
                # Defensive, but effectively: plugin_id must be None
                raise ValueError("At level 1, plugin_id must be None")
        # Level 2: must have company and plugin
        elif self.level == 2:
            if self.company_id is None or self.company_name is None or self.plugin_id is None:
                raise ValueError(
                    "At level 2, company_id, company_name, and plugin_id must not be None"
                )
        return self

    # Helper methods
    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def is_at_level(self, level: int) -> bool:
        return self.level == level

    def can_run_command(self, required_level: int) -> bool:
        return self.level >= required_level

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(exclude_none=True)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Context":
        return cls(**data)
