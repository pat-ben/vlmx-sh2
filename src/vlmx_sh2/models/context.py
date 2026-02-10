"""
Context and session management.

Provides navigation context and session state for command execution.
Manages hierarchical contexts (system, organization, application) and
tracks current company and plugin state during command sessions.
"""

from __future__ import annotations


from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import BaseModel, field_validator, model_validator
from pydantic.config import ConfigDict

from ..enums.core import ContextLevel



class Context(BaseModel):
    """Navigation and session context passed into commands.

    The context is treated as immutable/frozen; navigation commands should
    construct new Context instances rather than mutating an existing one.
    """

    # Pydantic v2 configuration
    model_config = ConfigDict(frozen=True)

    # Context level tracking
    level: ContextLevel = ContextLevel.SYS  # SYS=System, ORG=Organization, APP=Application

    # System level (level 0)
    sys_path: Optional[Path] = None

    # Organization level (level 1+)
    org_id: Optional[int] = None
    org_name: Optional[str] = None
    org_db_path: Optional[Path] = None

    # Application level (level 2)
    app_id: Optional[str] = None
    app_name: Optional[str] = None      # NEW: Human-readable app name
    app_type: Optional[str] = None      # NEW: "view" or "tool"

    # Session (Step 2)
    user_id: Optional[int] = None
    user_email: Optional[str] = None

    @field_validator("level")
    @classmethod
    def _validate_level_range(cls, v: ContextLevel) -> ContextLevel:
        return v

    @model_validator(mode="after")
    def _validate_level_consistency(self) -> "Context":
        # SYS level: no organization or application fields
        if self.level == ContextLevel.SYS:
            if any((self.org_id, self.org_name, self.app_id, self.app_name)):
                raise ValueError(
                    "At SYS level, org and app fields must all be None"
                )
        # ORG level: must have organization, no application
        elif self.level == ContextLevel.ORG:
            if self.org_id is None or self.org_name is None:
                raise ValueError(
                    "At ORG level, org_id and org_name must not be None"
                )
            if self.app_id is not None or self.app_name is not None:
                raise ValueError("At ORG level, app fields must be None")
        # APP level: must have organization AND application
        elif self.level == ContextLevel.APP:
            if self.org_id is None or self.org_name is None:
                raise ValueError(
                    "At APP level, org_id and org_name must not be None"
                )
            if self.app_id is None or self.app_name is None:
                raise ValueError(
                    "At APP level, app_id and app_name must not be None"
                )
        return self


    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(exclude_none=True)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Context":
        return cls(**data)
