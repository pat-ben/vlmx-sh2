"""
Wizard handlers.

Provides form wizard functionality for interactive data collection.
Returns FormRequest/PickerRequest models for UI interpretation.

Engine boundary:
- Public handlers accept stable IR (`IRCommand`).
- During migration, we adapt IR -> legacy `ParsedCommand` internally so existing
  wizard logic can remain mostly unchanged.
"""

from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, Field

from vlmx_sh2.enums import Cardinality

from ...constants import SYSTEM_FIELDS
from ...lang.ir.command import IRCommand
from ...models.context import Context
from ...models.parser.command import ParsedCommand
from ...models.responses import (
    ColumnSpec,
    ErrorResult,
    FieldSpec,
    FormRequest,
    HandlerResult,
    PickerRequest,
)
from ...storage.database import StorageInterface
from ...utils.field_specs import build_column_specs, build_field_specs
from ..legacy_adapter import to_legacy_parsed_command
from .utils import _validation_error, get_company_name_from_context

# =============================================================================
# 1. Public Handler API
# =============================================================================


async def fill_handler(ir_command: IRCommand, context: Context) -> HandlerResult:
    """
    Handler for 'fill' command - initiates interactive form wizards.

    Creates form wizards for single cardinality schemas or record pickers
    for multiple cardinality schemas.
    """
    parsed_command: ParsedCommand = to_legacy_parsed_command(ir_command)

    try:
        entity_model = parsed_command.entity_model
        if not entity_model:
            return _validation_error(
                "No entity specified for fill command",
                ["Specify an entity to fill, e.g.: fill news"],
            )

        entity_type = _get_entity_type(entity_model)
        entity_value = parsed_command.target.id if parsed_command.target else None

        # Validate organization context
        company_name = get_company_name_from_context(context)
        if not company_name:
            return _validation_error(
                "Fill command requires organization context",
                [
                    "Navigate to a company first: cd company_name",
                    "Or create a company: create company name=YourCompany",
                ],
            )

        # Handle based on cardinality
        if getattr(entity_model, "cardinality", None) == Cardinality.SINGLE:
            # Single cardinality: form wizard with existing data
            if not StorageInterface.entity_exists(entity_type, company_name, context):
                return _validation_error(
                    f"{entity_type.title()} does not exist for company '{company_name}'",
                    [
                        f"Create the {entity_type} first: create {entity_type}",
                        f"Or check available schemas: show {entity_type}",
                    ],
                )

            # Load existing data
            load_result = StorageInterface.load_entity(
                entity_type, company_name, context
            )
            if not load_result.success:
                return _validation_error(
                    load_result.error or f"Failed to load {entity_type} data",
                    [
                        f"Check if {entity_type} data exists",
                        f"Or recreate: create {entity_type}",
                    ],
                )

            # Create form with requested fields
            requested_fields = _get_requested_fields(entity_model, parsed_command)
            if not requested_fields:
                return _validation_error(
                    "No fillable fields available",
                    [f"Check {entity_type} entity model has user-editable fields"],
                )

            entity_data = load_result.data or {}
            return _create_form_request(
                entity_type,
                entity_value,
                company_name,
                requested_fields,
                entity_data,
                entity_model,
            )
        else:
            # Multiple cardinality: record picker
            return _create_picker_request(
                entity_type, entity_value, company_name, entity_model, context
            )

    except Exception as e:
        return _validation_error(
            f"Failed to create wizard: {str(e)}",
            ["Check entity model and field configuration"],
        )


# =============================================================================
# 2. Field & Data Extraction (Entity Data Processing)
# =============================================================================


def _get_entity_type(entity_model: Type[BaseModel]) -> str:
    """Extract entity type from model class name."""
    return entity_model.__name__.replace("Entity", "").lower()


def _get_display_fields(entity_type: str, entity_model: Type[BaseModel]) -> List[str]:
    """Get display fields for entity picker based on type."""
    all_fields = [f for f in entity_model.model_fields.keys() if f not in SYSTEM_FIELDS]

    # Entity-specific priorities
    priorities = {
        ("offering", "target", "values"): ["id", "key", "value"],
        ("metadata",): ["id", "stage", "sector", "model"],
    }

    for entities, fields in priorities.items():
        if entity_type in entities:
            display_fields = [f for f in fields if f in all_fields]
            # Add remaining fields up to 4 total
            display_fields.extend(
                [f for f in all_fields if f not in display_fields][
                    : 4 - len(display_fields)
                ]
            )
            return display_fields or all_fields[:3]

    return all_fields[:3] or ["id"]


def _get_requested_fields(
    entity_model: Type[BaseModel], parsed_command: ParsedCommand
) -> List[str]:
    """Determine which fields to include in the form."""
    # Priority: field_values > field_names > all model fields
    if parsed_command.field_values:
        return list(parsed_command.field_values.keys())
    if parsed_command.field_names:
        return parsed_command.field_names

    return [f for f in entity_model.model_fields.keys() if f not in SYSTEM_FIELDS]


# =============================================================================
# 4. UI Request Creation (Form & Picker Generation)
# =============================================================================


def _create_picker_request(
    entity_type: str,
    entity_value: Optional[str],
    company_name: str,
    entity_model: Type[BaseModel],
    context: Context,
) -> PickerRequest:
    """Create picker request for multiple cardinality schemas."""
    records_result = StorageInterface.load_all_entities(
        entity_type, company_name, context
    )
    if not records_result.success:
        return ErrorResult(
            errors=[records_result.error],
            suggestions=["Check entity type and database connection"],
        )
    records = records_result.data
    display_fields = _get_display_fields(entity_type, entity_model)
    column_specs = build_column_specs(entity_type, entity_model, display_fields)

    return PickerRequest(
        entity_id=entity_type,
        entity_name=entity_value or company_name,
        records=records,
        columns=column_specs,
        show_add_new_option=True,
        multi_select=False,
        title=f"Select {entity_type.title()} Record",
    )


def _create_form_request(
    entity_type: str,
    entity_value: Optional[str],
    company_name: str,
    requested_fields: List[str],
    entity_data: Dict[str, Any],
    entity_model: Type[BaseModel],
) -> FormRequest:
    """Create form request with FieldSpec and pre-filled values."""
    # Build field specifications with metadata
    field_specs = build_field_specs(entity_model, requested_fields, entity_data)

    # Pre-filled values as they are (no conversion to string)
    pre_filled = {
        f: v for f, v in entity_data.items() if f in requested_fields and v is not None
    }

    return FormRequest(
        entity_id=entity_type,
        entity_name=entity_value or company_name,
        fields=field_specs,
        pre_filled_values=pre_filled,
        title=f"Fill {entity_type.title()} Information",
        submit_label="Save",
        cancel_label="Cancel",
    )


# =============================================================================
# 5. Validation & Utilities (Error Handling & Helpers)
# =============================================================================
