"""
Context and session management.

Provides navigation context and session state for command execution.
Manages hierarchical contexts (system, organization, application) and
tracks current company and plugin state during command sessions.
"""

from __future__ import annotations


from pathlib import Path
from typing import Any, Dict, Optional
from enum import IntEnum

from pydantic import BaseModel, field_validator, model_validator
from pydantic.config import ConfigDict


class ContextLevel(IntEnum):
    SYS = 0  # system / root level
    ORG = 1  # organization level (most of the time company)
    APP = 2  # application level (could be plugin)



class Context(BaseModel):
    """Navigation and session context passed into commands.

    The context is treated as immutable/frozen; navigation commands should
    construct new Context instances rather than mutating an existing one.
    """

    # Pydantic v2 configuration
    model_config = ConfigDict(frozen=True)

    # Context level tracking
    level: int = ContextLevel.SYS  # SYS=System, ORG=Organization, APP=Application

    # System level (level 0)
    sys_path: Optional[Path] = None

    # Organization level (level 1+)
    org_id: Optional[int] = None
    org_name: Optional[str] = None
    org_db_path: Optional[Path] = None

    # Application level (level 2) - plugin_id kept for developer compatibility
    app_id: Optional[str] = None

    # Session (Step 2)
    user_id: Optional[int] = None
    user_email: Optional[str] = None

    @field_validator("level")
    @classmethod
    def _validate_level_range(cls, v: int) -> int:
        if v not in (ContextLevel.SYS, ContextLevel.ORG, ContextLevel.APP):
            raise ValueError("level must be SYS (0), ORG (1), or APP (2)")
        return v

    @model_validator(mode="after")
    def _validate_level_consistency(self) -> "Context":
        # SYS level: no organization or application fields
        if self.level == ContextLevel.SYS:
            if any((self.org_id, self.org_name, self.app_id)):
                raise ValueError(
                    "At SYS level, org_id, org_name, and app_id must all be None"
                )
        # ORG level: must have organization, no application
        elif self.level == ContextLevel.ORG:
            if self.org_id is None or self.org_name is None:
                raise ValueError(
                    "At ORG level, org_id and org_name must not be None"
                )
            if self.app_id is None is False and self.app_id is not None:
                # Defensive, but effectively: app_id must be None
                raise ValueError("At ORG level, app_id must be None")
        # APP level: must have organization and application
        elif self.level == ContextLevel.APP:
            if self.org_id is None or self.org_name is None or self.app_id is None:
                raise ValueError(
                    "At APP level, org_id, org_name, and app_id must not be None"
                )
        return self

    # Convenience properties for new terminology
    @property
    def is_sys(self) -> bool:
        """True if at system level"""
        return self.level == ContextLevel.SYS
    
    @property
    def is_org(self) -> bool:
        """True if at organization level"""
        return self.level == ContextLevel.ORG
    
    @property
    def is_app(self) -> bool:
        """True if at application level"""
        return self.level == ContextLevel.APP

    @property
    def level_name(self) -> str:
        """Human-readable level name"""
        if self.level == ContextLevel.SYS:
            return "sys"
        elif self.level == ContextLevel.ORG:
            return "org"
        elif self.level == ContextLevel.APP:
            return "app"
        else:
            return f"unknown({self.level})"


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
