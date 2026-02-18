"""
Core shared utilities.

This package contains helper functions that are safe to use across layers
(engine, storage, UI). Import from `vlmx_sh2.core.utils` as the canonical path.
"""

from .context.helpers import (
    can_execute_direct_command,
    command_requires_schema,
    get_level_name,
    get_missing_requirements,
    is_app,
    is_org,
    is_sys,
    requires_app,
    requires_schema,
    validate_command_requirements,
)
     
from .entity_defaults import (
    create_default_entity_data,
    create_default_entity_data_simple,
)
from .field_specs import (
    build_column_specs,
    build_field_specs,
)

__all__ = [
    "build_column_specs",
    "build_field_specs",
    "can_execute_direct_command",
    "command_requires_schema",
    "create_default_entity_data",
    "create_default_entity_data_simple",
    "get_level_name",
    "get_missing_requirements",
    "is_app",
    "is_org",
    "is_sys",
    "requires_app",
    "requires_schema",
    "validate_command_requirements",
]
