"""
SQL-inspired CRUD handlers with clean, simple routing.

Refactored handlers using parsed command structure to eliminate all hardcoded
entity-specific logic and complex nested conditionals. Uses SQL-inspired
semantics with create/drop for structure and add/delete/reset for content.

Engine boundary:
- Public handlers in this module accept stable IR (`IRCommand`).
- During migration, we adapt IR -> legacy `ParsedCommand` internally so the bulk
  of existing CRUD logic remains unchanged.
"""

# =============================================================================
# 1. Public Handler API (Main CRUD Entry Points)
# =============================================================================
# Dispatch Tables (Replace if/elif chains)
# =============================================================================
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any, Optional, cast

from pydantic import BaseModel

from vlmx_sh2.core.enums import Cardinality
from vlmx_sh2.dsl.ast.filters import FilterExpression

from ...core.constants import SYSTEM_FIELDS
from ...core.models.context import Context
from ...core.models.parser.command import ParsedCommand
from ...core.models.responses import CommandResult, ErrorResult, HandlerResult
from ...core.models.words import (
    EntityWord,
    FieldWord,
    ModuleWord,
    SchemaWord,
    TargetWord,
    TargetWordUnion,
    ToolWord,
    ViewWord,
    WordType,
)
from ...core.utils.context_helpers import is_sys
from ...core.utils.entity_defaults import create_default_entity_data
from ...db.database import StorageInterface
from ...db.filters import apply_filters
from ...dsl.ir.command import IRCommand
from ..legacy_adapter import to_legacy_parsed_command
from .utils import (
    format_entity_data_for_display,
    get_entity_type_string,
    get_target_id,
    handle_storage_result,
    validate_field_values_present,
    validate_org_context,
    validate_target_context,
    validate_target_exists,
)

# NOTE: We intentionally do NOT maintain multiple dispatch-table systems here.
# The only dispatch tables are defined near the bottom of this file under
# "Dispatch Tables (Replace if/elif chains)" and are async-typed.


# =============================================================================
# 1. Public Handler API (Main CRUD Entry Points)
# =============================================================================


async def create_handler(ir_command: IRCommand, context: Context) -> HandlerResult:
    """Create schema or entity structure."""
    parsed_command: ParsedCommand = to_legacy_parsed_command(ir_command)

    error = validate_target_exists(parsed_command)
    if error:
        return error

    assert parsed_command.target is not None  # Validated by validate_target_exists
    target = cast(TargetWordUnion, parsed_command.target)

    # Validate target is allowed in current context
    context_error = validate_target_context(target, context)
    if context_error:
        return context_error

    target_id = get_target_id(cast(Any, target))
    target_name = parsed_command.target_name
    field_values = parsed_command.field_values

    target_type = type(parsed_command.target)
    handler = _CREATE_TARGET_HANDLERS.get(target_type)
    if handler:
        return await handler(target_id, target_name, field_values, context)

    return _not_yet_supported_error(
        "Entity structure creation",
        "Entity structures are currently defined in code",
    )


async def drop_handler(ir_command: IRCommand, context: Context) -> HandlerResult:
    """Drop schema or entity structure."""
    parsed_command: ParsedCommand = to_legacy_parsed_command(ir_command)

    error = validate_target_exists(parsed_command)
    if error:
        return error

    assert parsed_command.target is not None  # Validated by validate_target_exists
    target = cast(TargetWordUnion, parsed_command.target)

    # Validate target is allowed in current context
    context_error = validate_target_context(target, context)
    if context_error:
        return context_error

    target_id = get_target_id(cast(Any, target))
    target_name = parsed_command.target_name

    target_type = type(parsed_command.target)
    handler = _DROP_TARGET_HANDLERS.get(target_type)
    if handler:
        return await handler(target_id, target_name, context)

    return _not_yet_supported_error(
        "Entity structure deletion",
        "Entity structures are currently defined in code",
    )


async def add_handler(ir_command: IRCommand, context: Context) -> HandlerResult:
    """Add or set field values."""
    parsed_command: ParsedCommand = to_legacy_parsed_command(ir_command)

    # Validate target exists
    error = validate_target_exists(parsed_command)
    if error:
        return error

    assert parsed_command.target is not None  # Validated by validate_target_exists
    target = cast(TargetWordUnion, parsed_command.target)

    # Validate target is allowed in current context
    context_error = validate_target_context(target, context)
    if context_error:
        return context_error

    error = validate_field_values_present(parsed_command)
    if error:
        return error

    company_name, error = validate_org_context(context)
    if error:
        return error

    assert company_name is not None  # Validated by validate_org_context
    assert parsed_command.target_model is not None  # Required for add operations
    entity_type = get_entity_type_string(parsed_command.target_model)
    fields = parsed_command.field_values
    filters = parsed_command.filters

    return await _add_field_values(
        entity_type=entity_type,
        fields=fields,
        filters=filters,
        company_name=company_name,
        context=context,
        entity_model=parsed_command.target_model,
    )


async def delete_handler(ir_command: IRCommand, context: Context) -> HandlerResult:
    """Delete data (content, not structure)."""
    parsed_command: ParsedCommand = to_legacy_parsed_command(ir_command)

    # Validate target exists
    error = validate_target_exists(parsed_command)
    if error:
        return error

    assert parsed_command.target is not None  # Validated by validate_target_exists
    target = cast(TargetWordUnion, parsed_command.target)

    # Validate target is allowed in current context
    context_error = validate_target_context(target, context)
    if context_error:
        return context_error

    # Check if word type supports delete
    # TODO: This could be refactored to dispatch tables in the future
    target = parsed_command.target
    if target.word_type not in [WordType.SCHEMA, WordType.ENTITY, WordType.FIELD]:
        supported_types = ["schema", "entity", "field"]
        return ErrorResult(
            errors=[f"'delete' does not support {target.word_type.value}"],
            suggestions=[f"'delete' works with: {', '.join(supported_types)}"],
        )

    company_name, error = validate_org_context(context)
    if error:
        return error

    assert company_name is not None  # Validated by validate_org_context
    assert parsed_command.target_model is not None  # Required for delete operations
    entity_type = get_entity_type_string(parsed_command.target_model)
    field_names = parsed_command.field_names
    filters = parsed_command.filters

    if field_names:
        return await _delete_field_values(
            entity_type=entity_type,
            field_names=field_names,
            filters=filters,
            company_name=company_name,
            context=context,
        )

    elif filters:
        cardinality = (
            getattr(parsed_command.target_model, "cardinality", Cardinality.SINGLE)
            if parsed_command.target_model
            else Cardinality.SINGLE
        )
        if cardinality == Cardinality.SINGLE:
            return ErrorResult(errors=["Cannot delete rows from single-record entity"])

        return await _delete_rows(
            entity_type=entity_type,
            filters=filters,
            company_name=company_name,
            context=context,
        )

    else:
        return await _delete_entity_content(
            entity_type=entity_type, company_name=company_name, context=context
        )


async def reset_handler(ir_command: IRCommand, context: Context) -> HandlerResult:
    """Reset entity or fields to default values."""
    parsed_command: ParsedCommand = to_legacy_parsed_command(ir_command)

    # Validate target exists
    error = validate_target_exists(parsed_command)
    if error:
        return error

    assert parsed_command.target is not None  # Validated by validate_target_exists
    target = cast(TargetWordUnion, parsed_command.target)

    # Validate target is allowed in current context
    context_error = validate_target_context(target, context)
    if context_error:
        return context_error

    company_name, error = validate_org_context(context)
    if error:
        return error

    assert company_name is not None  # Validated by validate_org_context
    assert parsed_command.target_model is not None  # Required for reset operations
    entity_type = get_entity_type_string(parsed_command.target_model)
    field_names = parsed_command.field_names
    filters = parsed_command.filters

    if field_names:
        return await _reset_field_values(
            entity_type=entity_type,
            field_names=field_names,
            filters=filters,
            company_name=company_name,
            context=context,
            entity_model=parsed_command.target_model,
        )
    else:
        return await _reset_entity_content(
            entity_type=entity_type,
            company_name=company_name,
            context=context,
            entity_model=parsed_command.target_model,
        )


async def show_handler(ir_command: IRCommand, context: Context) -> HandlerResult:
    """Display data with optional field selection and filtering."""
    parsed_command: ParsedCommand = to_legacy_parsed_command(ir_command)

    # Validate target exists
    error = validate_target_exists(parsed_command)
    if error:
        return error

    assert parsed_command.target is not None  # Validated by validate_target_exists
    target = cast(TargetWordUnion, parsed_command.target)

    # Validate target is allowed in current context
    context_error = validate_target_context(target, context)
    if context_error:
        return context_error

    # Handle by target type using dispatch table
    target = parsed_command.target

    # Get handler based on target type
    handler = _SHOW_TARGET_HANDLERS.get(type(target))
    if handler:
        return await handler(parsed_command, context)

    supported_types = ["schema", "entity", "field", "module", "app"]
    return ErrorResult(
        errors=[f"'show' does not support {target.word_type.value}"],
        suggestions=[f"Supported types: {', '.join(supported_types)}"],
    )


# =============================================================================
# 2. Validation & Utilities (Common Helper Functions)
# =============================================================================


def _not_yet_supported_error(
    feature: str, suggestion: Optional[str] = None
) -> ErrorResult:
    """Return standardized 'not yet supported' error."""
    return ErrorResult(
        errors=[f"{feature} not yet supported"],
        suggestions=[
            suggestion or f"{feature} may be available in future implementation"
        ],
    )


def _entity_not_found_error(entity_type: str, company_name: str) -> ErrorResult:
    """Return standardized entity not found error."""
    return ErrorResult(
        errors=[f"Entity '{entity_type}' does not exist for company '{company_name}'"],
        suggestions=[f"Create the {entity_type} first or check the entity name"],
    )


def _validate_entity_exists(
    entity_type: str, company_name: str, context: Context
) -> Optional[ErrorResult]:
    """
    Validate entity exists, return error if not.

    Returns:
        ErrorResult if entity doesn't exist, None if valid
    """
    if not StorageInterface.entity_exists(entity_type, company_name, context):
        return _entity_not_found_error(entity_type, company_name)
    return None


def _resolve_organization_name(
    name: Optional[str], context: Context
) -> tuple[Optional[str], Optional[ErrorResult]]:
    """
    Resolve company name with intelligent matching.

    Returns:
        Tuple of (actual_company_name, error). If error is not None, operation failed.
    """
    if not name:
        return None, ErrorResult(
            errors=["Company name required"], suggestions=["Specify company name"]
        )

    result = StorageInterface.find_organization_by_name(name, context)
    if not result.success:
        return None, ErrorResult(
            errors=[result.error] if result.error is not None else ["Unknown error"],
            suggestions=["Check company name spelling or list existing companies"],
        )
    data = cast(dict[str, object], result.data or {})
    actual_name = cast(Optional[str], data.get("name"))
    if not actual_name:
        return None, ErrorResult(
            errors=["Company name could not be resolved"],
            suggestions=["Check company name spelling or list existing companies"],
        )

    return actual_name, None


# =============================================================================
# 3. Schema Operations (Structure-Level Operations)
# =============================================================================


async def _create_schema(
    target_id: str, name: Optional[str], fields: dict[str, Any], context: Context
) -> HandlerResult:
    """Create schema (organization database)."""

    entity_type = target_id

    try:
        # Prepare entity data with user-provided fields
        entity_data = {
            "name": name or f"{entity_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        entity_data.update(fields)

        # Use generic storage - simplified validation
        storage_result = StorageInterface.create_entity(
            entity_type=entity_type, data=entity_data, context=context
        )

        # All schema creation returns context_switch payload
        return handle_storage_result(
            storage_result,
            storage_result.message or f"Created {entity_type} {entity_data['name']}",
            entity_type,
            {
                "entity_name": entity_data["name"],
                "fields": entity_data,
                "storage_result": storage_result.data,
                "context_switch": {
                    "level": "ORG",
                    "org_id": 1,
                    "org_name": entity_data["name"],
                    "org_db_path": None,
                },
            },
        )

    except Exception as e:
        return ErrorResult(
            errors=[f"Failed to create entity: {str(e)}"],
            suggestions=["Check input values and system status"],
        )


async def _drop_schema(
    target_id: str, name: Optional[str], context: Context
) -> HandlerResult:
    """Drop schema (organization database)."""

    if not is_sys(context):
        return ErrorResult(
            errors=["Can only drop schemas from system level"],
            suggestions=["Use 'cd' to navigate to system level first"],
        )

    actual_company_name, error = _resolve_organization_name(name, context)
    if error:
        return error

    assert (
        actual_company_name is not None
    )  # Guaranteed by _resolve_organization_name success
    # Delete the entire entity
    delete_result = StorageInterface.delete_entity(
        target_id, actual_company_name, context
    )

    return handle_storage_result(
        delete_result,
        f"Dropped schema {actual_company_name}",
        target_id,
        {
            "deleted_entity": actual_company_name,
            "delete_message": delete_result.message or "Successfully deleted",
        },
    )


async def _show_schema_info(
    target_id: str, name: Optional[str], context: Context
) -> HandlerResult:
    """Show schema information."""

    actual_company_name, error = _resolve_organization_name(name, context)
    if error:
        return error

    assert (
        actual_company_name is not None
    )  # Guaranteed by _resolve_organization_name success
    # Load schema data
    load_result = StorageInterface.load_entity(target_id, actual_company_name, context)
    if not load_result.success or not load_result.data:
        return ErrorResult(
            errors=[f"Failed to load {target_id} data"],
            suggestions=["Check if schema exists and database connection"],
        )

    return CommandResult(
        success=True,
        message=f"Schema information for {actual_company_name}",
        data={
            "entity_type": target_id,
            "entity_name": actual_company_name,
            "schema_info": load_result.data,
            "formatted_data": format_entity_data_for_display(load_result.data),
        },
    )


async def _create_entity_structure(
    entity_word: EntityWord, context: Context
) -> HandlerResult:
    """Create entity structure (future implementation)."""
    return _not_yet_supported_error(
        "Entity structure creation",
        "Use existing entity types or wait for future implementation",
    )


async def _drop_entity_structure(
    entity_word: EntityWord, context: Context
) -> HandlerResult:
    """Drop entity structure (future implementation)."""
    return _not_yet_supported_error(
        "Entity structure deletion",
        "Use existing entity types or wait for future implementation",
    )


# =============================================================================
# 4. Entity Content Operations (Data-Level Operations)
# =============================================================================

# --- Add/Update Operations ---


async def _add_field_values(
    entity_type: str,
    fields: dict[str, str],
    filters: FilterExpression | None,
    company_name: str,
    context: Context,
    entity_model: type[BaseModel] | None = None,
) -> HandlerResult:
    """Add/update field values, optionally filtered."""

    try:
        # Create entity if it doesn't exist using Pydantic model defaults
        if not StorageInterface.entity_exists(entity_type, company_name, context):
            try:
                if entity_model is None:
                    return ErrorResult(
                        errors=["Entity model is required for default creation"],
                        suggestions=["Check entity model configuration"],
                    )

                default_data = create_default_entity_data(entity_model, entity_type)
            except Exception as e:
                return ErrorResult(
                    errors=[f"Failed to create default entity: {str(e)}"],
                    suggestions=["Check entity model configuration"],
                )

            StorageInterface.save_entity(
                entity_type, default_data, company_name, context
            )

        # Load current entity data
        load_result = StorageInterface.load_entity(entity_type, company_name, context)
        current_data = (
            load_result.data if (load_result.success and load_result.data) else {}
        )

        # Validate field names before storage
        if entity_model is not None:
            valid_fields = set(entity_model.model_fields.keys())
            invalid_fields = [f for f in fields if f not in valid_fields]
            system_fields = [f for f in fields if f in SYSTEM_FIELDS]

            if invalid_fields or system_fields:
                error_parts = []
                if invalid_fields:
                    valid_field_names = ", ".join(sorted(valid_fields - SYSTEM_FIELDS))
                    error_parts.append(
                        f"Unknown fields: {', '.join(invalid_fields)}. Valid fields for {entity_type}: {valid_field_names}"
                    )
                if system_fields:
                    error_parts.append(
                        f"System-managed fields cannot be set manually: {', '.join(system_fields)}"
                    )

                return ErrorResult(
                    errors=error_parts,
                    suggestions=[
                        f"Check field names for {entity_type}",
                        "Use only user-editable fields",
                    ],
                )

        # Create updated data with validated fields
        updated_data = current_data.copy()
        updated_data.update(fields)
        updated_data["updated_at"] = datetime.now().isoformat()

        # Save the updated entity
        save_result = StorageInterface.save_entity(
            entity_type, updated_data, company_name, context
        )

        return handle_storage_result(
            save_result,
            f"Added fields to {entity_type}",
            entity_type,
            {"added_fields": fields},
        )

    except Exception as e:
        return ErrorResult(
            errors=[f"Failed to add fields: {str(e)}"],
            suggestions=["Check input format and system status"],
        )


# --- Delete Operations ---


async def _delete_field_values(
    entity_type: str,
    field_names: list[str],
    filters: FilterExpression | None,
    company_name: str,
    context: Context,
) -> HandlerResult:
    """Delete specific field values, optionally filtered."""

    error = _validate_entity_exists(entity_type, company_name, context)
    if error:
        return error

    # Load current entity data
    load_result = StorageInterface.load_entity(entity_type, company_name, context)
    current_data = (
        load_result.data if (load_result.success and load_result.data) else {}
    )
    if not current_data:
        return ErrorResult(
            errors=[f"No data found for {entity_type}"],
            suggestions=["Check entity exists and database connection"],
        )

    # Remove the specified fields
    updated_data = current_data.copy()
    removed_fields = [field for field in field_names if field in updated_data]

    if not removed_fields:
        return ErrorResult(
            errors=[
                f"None of the specified fields exist in {entity_type}: {', '.join(field_names)}"
            ],
            suggestions=[
                "Check field names or show the entity to see available fields"
            ],
        )

    for field_name in removed_fields:
        updated_data[field_name] = None

    # Update timestamp
    if "updated_at" in updated_data:
        updated_data["updated_at"] = datetime.now().isoformat()

    # Save the updated entity
    save_result = StorageInterface.save_entity(
        entity_type, updated_data, company_name, context
    )

    return handle_storage_result(
        save_result,
        f"Deleted fields from {entity_type}",
        entity_type,
        {"removed_fields": removed_fields},
    )


async def _delete_rows(
    entity_type: str, filters: Any, company_name: str, context: Context
) -> HandlerResult:
    """Delete rows matching filters."""

    return _not_yet_supported_error(
        "Row deletion with filters", "Use field deletion or reset entity for now"
    )


async def _delete_entity_content(
    entity_type: str, company_name: str, context: Context
) -> HandlerResult:
    """Delete all entity content."""

    # Delete all entity content
    delete_result = StorageInterface.delete_entity(entity_type, company_name, context)

    return handle_storage_result(
        delete_result,
        f"Deleted all {entity_type} data",
        entity_type,
        {"operation": "delete_all"},
    )


# --- Reset Operations ---


async def _reset_entity_content(
    entity_type: str, company_name: str, context: Context, entity_model: type[BaseModel]
) -> HandlerResult:
    """Reset entity to defaults."""

    try:
        default_data = create_default_entity_data(entity_model, entity_type)
    except Exception as e:
        return ErrorResult(
            errors=[f"Failed to generate defaults: {str(e)}"],
            suggestions=["Check entity model configuration"],
        )

    # Save the default entity
    save_result = StorageInterface.save_entity(
        entity_type, default_data, company_name, context
    )

    return handle_storage_result(
        save_result,
        f"Reset {entity_type} to defaults",
        entity_type,
        {"operation": "reset_to_defaults"},
    )


async def _reset_field_values(
    entity_type: str,
    field_names: list[str],
    filters: FilterExpression | None,
    company_name: str,
    context: Context,
    entity_model: type[BaseModel],
) -> HandlerResult:
    """Reset specific fields to defaults."""

    # Get default values for the fields from the model
    try:
        default_instance = entity_model()
        default_data = default_instance.model_dump()
    except Exception as e:
        return ErrorResult(
            errors=[f"Failed to get default values: {str(e)}"],
            suggestions=["Check entity model configuration"],
        )

    # Load current entity data
    load_result = StorageInterface.load_entity(entity_type, company_name, context)
    current_data = (
        load_result.data if (load_result.success and load_result.data) else {}
    )

    # Reset specified fields to defaults
    updated_data = current_data.copy()
    reset_fields = [field for field in field_names if field in default_data]

    if not reset_fields:
        return ErrorResult(
            errors=[
                f"None of the specified fields have default values: {', '.join(field_names)}"
            ],
            suggestions=["Check field names or use delete to clear fields"],
        )

    updated_data.update({field: default_data[field] for field in reset_fields})

    # Update timestamp
    updated_data["updated_at"] = datetime.now().isoformat()

    # Save the updated entity
    save_result = StorageInterface.save_entity(
        entity_type, updated_data, company_name, context
    )

    return handle_storage_result(
        save_result,
        f"Reset fields in {entity_type} to defaults",
        entity_type,
        {"reset_fields": reset_fields},
    )


# --- Show Operations ---


async def _show_entity(
    entity_type: str,
    field_names: list[str] | None,
    filters: FilterExpression | None,
    company_name: str,
    context: Context,
    entity_model: type[BaseModel] | None = None,
) -> HandlerResult:
    """Show entity data with optional field/row filtering."""

    try:
        error = _validate_entity_exists(entity_type, company_name, context)
        if error:
            return error

        # Load entity data
        load_result = StorageInterface.load_entity(entity_type, company_name, context)
        entity_data = load_result.data if load_result.success else None
        if entity_data is None:
            return ErrorResult(
                errors=[f"No data found for {entity_type}"],
                suggestions=["Check entity exists and database connection"],
            )

        # For multi-cardinality schemas, we might want to show multiple records
        cardinality = (
            getattr(entity_model, "cardinality", Cardinality.SINGLE)
            if entity_model
            else Cardinality.SINGLE
        )
        if cardinality == Cardinality.MULTIPLE:
            # Load all records and apply filtering
            all_records_result = StorageInterface.load_all_entities(
                entity_type, company_name, context
            )
            if not all_records_result.success:
                return ErrorResult(
                    errors=[
                        all_records_result.error
                        if all_records_result.error is not None
                        else "Failed to load records"
                    ],
                    suggestions=["Check entity exists and database connection"],
                )
            all_records = cast(list[dict[str, object]], all_records_result.data or [])

            # Apply filters if present
            if filters:
                try:
                    filtered_records = apply_filters(all_records, filters)
                except Exception as filter_error:
                    return ErrorResult(
                        errors=[f"Filter application failed: {str(filter_error)}"],
                        suggestions=["Check filter syntax and field names"],
                    )
            else:
                filtered_records = all_records

            # Format multiple records
            count = len(filtered_records)
            total_count = len(all_records)

            message = (
                f"Found {count} of {total_count} {entity_type} records"
                if filters
                else f"Found {count} {entity_type} records"
            )

            return CommandResult(
                success=True,
                message=message,
                data={
                    "entity_type": entity_type,
                    "records": filtered_records,
                    "count": count,
                    "total_count": total_count,
                    "filtered": bool(filters),
                },
            )
        else:
            # Single record - format data for display
            specific_fields = field_names if field_names else None
            formatted_data = format_entity_data_for_display(
                entity_data, specific_fields
            )

            return CommandResult(
                success=True,
                message=f"Displaying {entity_type} data",
                data={
                    "entity_type": entity_type,
                    "formatted_data": formatted_data,
                    "raw_data": entity_data,
                },
            )

    except Exception as e:
        return ErrorResult(
            errors=[f"Failed to show entity data: {str(e)}"],
            suggestions=["Check entity exists and database connection"],
        )


# =============================================================================
# 3. New Word Type Handlers (Module, View, Tool)
# =============================================================================


async def _show_module(target: ModuleWord, context: Context) -> HandlerResult:
    """Show module information and its entities."""
    return CommandResult(
        success=True,
        message=f"Module: {target.id}",
        data={
            "module_id": target.id,
            "description": target.description,
            "entities": target.entities,
            "entity_count": len(target.entities),
        },
    )


async def _show_view(target: ViewWord, context: Context) -> HandlerResult:
    """Show view configuration."""
    return CommandResult(
        success=True,
        message=f"View: {target.id}",
        data={
            "view_id": target.id,
            "description": target.description,
            "entities": target.entities,
            "aliases": target.aliases,
        },
    )


async def _show_tool(target: ToolWord, context: Context) -> HandlerResult:
    """Show tool configuration and parameters."""
    return CommandResult(
        success=True,
        message=f"Tool: {target.id}",
        data={
            "tool_id": target.id,
            "description": target.description,
            "parameters": target.parameters,
            "aliases": target.aliases,
        },
    )


async def _show_app(target: TargetWord, context: Context) -> HandlerResult:
    """Route APP word type to view or tool handler."""
    if isinstance(target, ViewWord):
        return await _show_view(target, context)
    elif isinstance(target, ToolWord):
        return await _show_tool(target, context)
    else:
        return ErrorResult(errors=[f"Unknown APP type: {type(target).__name__}"])


# =============================================================================
# Dispatch Tables (Replace if/elif chains)
# =============================================================================

# (no-op) typing imports are already handled at the top of the file

_GenericHandler = Callable[..., Awaitable[HandlerResult]]

# Target-type dispatch tables (async)
_CREATE_TARGET_HANDLERS: dict[type[Any], _GenericHandler] = {
    SchemaWord: _create_schema,
}

_DROP_TARGET_HANDLERS: dict[type[Any], _GenericHandler] = {
    SchemaWord: _drop_schema,
}

_SHOW_TARGET_HANDLERS: dict[type[Any], _GenericHandler] = {}


def _register_show_handler(word_type: type[Any]):
    """Decorator to register show handlers by word type."""

    def decorator(func: _GenericHandler):
        _SHOW_TARGET_HANDLERS[word_type] = func
        return func

    return decorator


@_register_show_handler(ModuleWord)
async def _handle_show_module(
    parsed_command: ParsedCommand, context: Context
) -> HandlerResult:
    target = parsed_command.target
    assert isinstance(target, ModuleWord)
    return await _show_module(target, context)


@_register_show_handler(ViewWord)
@_register_show_handler(ToolWord)
async def _handle_show_app(
    parsed_command: ParsedCommand, context: Context
) -> HandlerResult:
    target = parsed_command.target
    assert isinstance(target, (ViewWord, ToolWord))
    return await _show_app(target, context)


@_register_show_handler(SchemaWord)
async def _handle_show_schema(
    parsed_command: ParsedCommand, context: Context
) -> HandlerResult:
    target = parsed_command.target
    assert isinstance(target, SchemaWord)
    target_id = get_target_id(target)
    target_name = parsed_command.target_name
    return await _show_schema_info(target_id, target_name, context)


@_register_show_handler(EntityWord)
@_register_show_handler(FieldWord)
async def _handle_show_entity(
    parsed_command: ParsedCommand, context: Context
) -> HandlerResult:
    company_name, error = validate_org_context(context)
    if error:
        return error

    assert company_name is not None
    assert parsed_command.target_model is not None
    entity_type = get_entity_type_string(parsed_command.target_model)
    field_names = parsed_command.field_names
    filters = parsed_command.filters

    return await _show_entity(
        entity_type=entity_type,
        field_names=field_names,
        filters=filters,
        company_name=company_name,
        context=context,
        entity_model=parsed_command.target_model,
    )
