"""
Context and session management for VLMX DSL.

Provides navigation context and session state for command execution.
Manages hierarchical contexts (system, organization, application) and
tracks current company and plugin state during command sessions.
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
    level: int = 0  # 0=System (sys), 1=Organization (org), 2=Application (app)

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
        if v not in (0, 1, 2):
            raise ValueError("level must be 0, 1, or 2")
        return v

    @model_validator(mode="after")
    def _validate_level_consistency(self) -> "Context":
        # Level 0 (sys): no organization or application fields
        if self.level == 0:
            if any((self.org_id, self.org_name, self.app_id)):
                raise ValueError(
                    "At level 0 (sys), org_id, org_name, and app_id must all be None"
                )
        # Level 1 (org): must have organization, no application
        elif self.level == 1:
            if self.org_id is None or self.org_name is None:
                raise ValueError(
                    "At level 1 (org), org_id and org_name must not be None"
                )
            if self.app_id is None is False and self.app_id is not None:
                # Defensive, but effectively: app_id must be None
                raise ValueError("At level 1 (org), app_id must be None")
        # Level 2 (app): must have organization and application
        elif self.level == 2:
            if self.org_id is None or self.org_name is None or self.app_id is None:
                raise ValueError(
                    "At level 2 (app), org_id, org_name, and app_id must not be None"
                )
        return self

    # Convenience properties for new terminology
    @property
    def is_sys(self) -> bool:
        """True if at system level (0)"""
        return self.level == 0
    
    @property
    def is_org(self) -> bool:
        """True if at organization level (1)"""
        return self.level == 1
    
    @property
    def is_app(self) -> bool:
        """True if at application level (2)"""
        return self.level == 2

    @property
    def level_name(self) -> str:
        """Human-readable level name"""
        level_names = {0: "sys", 1: "org", 2: "app"}
        return level_names.get(self.level, f"unknown({self.level})")

    # Legacy compatibility properties
    @property
    def company_id(self) -> Optional[int]:
        """Legacy property for org_id"""
        return self.org_id
    
    @property
    def company_name(self) -> Optional[str]:
        """Legacy property for org_name"""
        return self.org_name
    
    @property
    def company_db_path(self) -> Optional[Path]:
        """Legacy property for org_db_path"""
        return self.org_db_path
    
    @property
    def platform_path(self) -> Optional[Path]:
        """Legacy property for sys_path"""
        return self.sys_path
    
    @property
    def plugin_id(self) -> Optional[str]:
        """Legacy property for app_id"""
        return self.app_id

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
