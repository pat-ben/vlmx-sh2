"""
Utility functions for generic command handlers.

Provides common functionality for extracting entities, fields, and context
information from parse results. Used by generic field handlers to work
with any entity-field combination dynamically.
"""

from typing import Dict, Any, Optional, Type, Union, Tuple
from pydantic import BaseModel

from ..models.context import Context
from ..enums.core import ContextLevel
from ..models.responses import ErrorResult, CommandResult, HandlerResult, StorageResult
from ..models.parser.parsed_command import ParsedCommand
from ..models.words import SchemaWord, EntityWord, FieldWord

def get_company_name_from_context(context: Context) -> Optional[str]:
    """
    Get the current company name from context.
    
    Args:
        context: The execution context
        
    Returns:
        Company name if in ORG context, None if in SYS context
    """
    if context.level >= ContextLevel.ORG and context.org_name:
        return context.org_name
    return None

def format_entity_data_for_display(entity_data: Dict[str, Any], 
                                 specific_fields: list[str] | None = None) -> str:
    """
    Format entity data for user display.
    
    Args:
        entity_data: The entity data dictionary
        specific_fields: Specific fields to show, or None for all
        
    Returns:
        Formatted string for display
    """
    if not entity_data:
        return "No data found"
    
    lines = []
    
    # Filter to specific fields if requested
    if specific_fields:
        data_to_show = {field: entity_data.get(field) for field in specific_fields}
    else:
        data_to_show = entity_data
    
    # Format each field
    for key, value in data_to_show.items():
        if value is not None:
            if isinstance(value, str) and len(value) > 50:
                # Truncate long values
                formatted_value = value[:50] + "..."
            else:
                formatted_value = str(value)
            lines.append(f"{key}: {formatted_value}")
        else:
            lines.append(f"{key}: (not set)")
    
    return "\n".join(lines) if lines else "No fields to display"


# ==================== TYPE CONVERSION UTILITIES ====================

def get_entity_type_string(target_model: Type[BaseModel]) -> str:
    """
    Convert entity model to storage string identifier.
    
    Extracts entity type string from model class name by removing 'Entity' suffix.
    This is the ONLY place this conversion should happen.
    
    Args:
        target_model: Entity model class (e.g., BrandEntity, OrganizationEntity)
    
    Returns:
        Storage identifier string (e.g., "brand", "organization")
    
    Examples:
        >>> get_entity_type_string(BrandEntity)
        "brand"
        >>> get_entity_type_string(OrganizationEntity)
        "organization"
    """
    return target_model.__name__.replace("Entity", "").lower()


def get_target_id(target: Union[SchemaWord, EntityWord, FieldWord]) -> str:
    """
    Get storage identifier from any target word.
    
    Uses direct property access to word.id (all word types have this property).
    
    Args:
        target: Any word type (SchemaWord, EntityWord, FieldWord)
    
    Returns:
        Storage identifier string from word.id
    
    Examples:
        >>> get_target_id(SchemaWord(id="company", ...))
        "company"
        >>> get_target_id(EntityWord(id="brand", ...))
        "brand"
    """
    return target.id


# ==================== VALIDATION UTILITIES ====================

def validate_target_exists(parsed_command: ParsedCommand) -> Optional[ErrorResult]:
    """
    Validate that parsed command has a target.
    
    Returns:
        ErrorResult if validation fails, None if validation passes
    """
    if not parsed_command.target:
        return ErrorResult(errors=["No target specified"])
    return None


def validate_org_context(context: Context) -> Tuple[Optional[str], Optional[ErrorResult]]:
    """
    Validate that we're in organization context and get company name.
    
    Returns:
        Tuple of (company_name, error_result)
        - If valid: (company_name, None)
        - If invalid: (None, ErrorResult)
    
    Usage:
        company_name, error = validate_org_context(context)
        if error:
            return error
        # Continue with company_name
    """
    company_name = get_company_name_from_context(context)
    if not company_name:
        return None, ErrorResult(errors=["Must be in organization context"])
    return company_name, None


def validate_field_values_present(parsed_command: ParsedCommand) -> Optional[ErrorResult]:
    """
    Validate that parsed command has field values.
    
    Returns:
        ErrorResult if validation fails, None if validation passes
    """
    if not parsed_command.field_values:
        return ErrorResult(errors=["No fields specified"])
    return None


# ==================== RESULT HANDLING UTILITIES ====================

def handle_storage_result(
    storage_result: StorageResult,
    success_message: str,
    entity_type: str,
    operation_data: Optional[Dict[str, Any]] = None
) -> HandlerResult:
    """
    Convert StorageResult to HandlerResult.
    
    Centralizes the pattern of checking storage result and building appropriate response.
    
    Args:
        storage_result: Result from storage operation
        success_message: Message to return on success
        entity_type: Entity type string for error messages
        operation_data: Additional data to include in success response
    
    Returns:
        CommandResult on success, ErrorResult on failure
    """
    if storage_result.success:
        data = {
            "entity_type": entity_type,
            **(operation_data or {})
        }
        return CommandResult(
            success=True,
            message=success_message,
            data=data
        )
    else:
        return ErrorResult(
            errors=[storage_result.error or f"Operation failed for {entity_type}"],
            suggestions=["Check database permissions and system status"]
        )

