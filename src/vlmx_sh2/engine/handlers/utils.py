"""
Utility functions for generic command handlers.

Provides common functionality for extracting schemas, fields, and context
information from parse results.
"""

from typing import Any, Dict, List, Optional, Tuple, Type, Union

from pydantic import BaseModel

from ...core.enums.context_rules import (
    get_allowed_target_names_for_context,
    is_target_allowed_in_context,
)
from ...core.enums.core import ContextLevel
from ...core.models.context import Context
from ...core.models.parser.command import ParsedCommand
from ...core.models.responses import CommandResult, ErrorResult, HandlerResult, StorageResult
from ...core.models.words import EntityWord, FieldWord, SchemaWord, TargetWord, WordType

# =============================================================================
# 1. Context & Data Utilities (Basic Context & Data Processing)
# =============================================================================


def get_company_name_from_context(context: Context) -> Optional[str]:
    """Get the current company name from context."""
    return context.org_name if context.level >= ContextLevel.ORG else None


def format_entity_data_for_display(
    entity_data: Dict[str, Any], specific_fields: Optional[List[str]] = None
) -> str:
    """Format entity data for user display."""
    if not entity_data:
        return "No data found"

    data_to_show = (
        {f: entity_data.get(f) for f in specific_fields}
        if specific_fields
        else entity_data
    )

    lines = []
    for key, value in data_to_show.items():
        if value is not None:
            formatted_value = (
                f"{str(value)[:50]}..."
                if isinstance(value, str) and len(value) > 50
                else str(value)
            )
            lines.append(f"{key}: {formatted_value}")
        else:
            lines.append(f"{key}: (not set)")

    return "\n".join(lines) if lines else "No fields to display"


# =============================================================================
# 2. Type Conversion Utilities (Type & Identifier Conversion)
# =============================================================================


def get_entity_type_string(target_model: Type[BaseModel]) -> str:
    """Convert entity model to storage string identifier."""
    return target_model.__name__.replace("Entity", "").lower()


def get_target_id(target: Union[SchemaWord, EntityWord, FieldWord]) -> str:
    """Get storage identifier from any target word."""
    return target.id


# =============================================================================
# 3. Common Error Helpers (Shared Error Creation Functions)
# =============================================================================


def _validation_error(
    message: str, suggestions: Optional[List[str]] = None
) -> ErrorResult:
    """Create standardized validation error."""
    return ErrorResult(errors=[message], suggestions=suggestions or [])


# =============================================================================
# 4. Validation Utilities (Input Validation & Error Checking)
# =============================================================================


def validate_target_exists(parsed_command: ParsedCommand) -> Optional[ErrorResult]:
    """Validate that parsed command has a target."""
    return (
        _validation_error("No target specified") if not parsed_command.target else None
    )


def validate_target_context(
    target: TargetWord, context: Context
) -> Optional[ErrorResult]:
    """
    Validate that target is allowed in current context.

    Cumulative Context Model:
    - SYS: Schema only
    - ORG: Schema + Module + Entity + Field
    - APP: All (Schema + Module + Entity + Field + View + Tool)

    Returns ErrorResult if invalid, None if valid.
    """
    if is_target_allowed_in_context(target.word_type.value, context.level):
        return None

    # Build helpful error message
    allowed_names = get_allowed_target_names_for_context(context.level)

    # Suggest correct context for APP targets
    if target.word_type.value == "app":
        suggestion = f"Navigate to an app: cd {target.id}/"
    else:
        suggestion = "This should not happen in cumulative model"

    level_names = {
        ContextLevel.SYS: "SYS",
        ContextLevel.ORG: "ORG",
        ContextLevel.APP: "APP",
    }
    level_name = level_names.get(context.level, f"level {context.level}")

    return ErrorResult(
        errors=[
            f"'{target.id}' ({target.word_type.value}) is not available in {level_name} context"
        ],
        suggestions=[
            f"Allowed in {level_name}: {', '.join(allowed_names)}",
            suggestion,
        ],
    )


def validate_org_context(
    context: Context,
) -> Tuple[Optional[str], Optional[ErrorResult]]:
    """Validate organization context and get company name."""
    company_name = get_company_name_from_context(context)
    return (
        (company_name, None)
        if company_name
        else (None, _validation_error("Must be in organization context"))
    )


def validate_field_values_present(
    parsed_command: ParsedCommand,
) -> Optional[ErrorResult]:
    """Validate that parsed command has field values."""
    return (
        _validation_error("No fields specified")
        if not parsed_command.field_values
        else None
    )


# =============================================================================
# 5. Result Handling Utilities (Result Processing & Conversion)
# =============================================================================


def handle_storage_result(
    storage_result: StorageResult,
    success_message: str,
    entity_type: str,
    operation_data: Optional[Dict[str, Any]] = None,
) -> HandlerResult:
    """Convert StorageResult to HandlerResult."""
    if storage_result.success:
        return CommandResult(
            success=True,
            message=success_message,
            data={"entity_type": entity_type, **(operation_data or {})},
        )
    else:
        return _validation_error(
            storage_result.error or f"Operation failed for {entity_type}",
            ["Check database permissions and system status"],
        )
