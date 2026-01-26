"""
Wizard handlers.

Provides form wizard functionality for interactive data collection.
Returns FormRequest/PickerRequest models for UI interpretation.
"""

from typing import Optional, List, Type, Dict, Any
from pydantic import BaseModel, Field

from ..models.responses import FormRequest, PickerRequest, ErrorResult, HandlerResult, FieldSpec, ColumnSpec
from ..models.context import Context
from vlmx_sh2.enums import Cardinality
from ..models.parser.command import ParsedCommand
from ..handlers.utils import get_company_name_from_context
from ..constants import SYSTEM_FIELDS
from ..storage.database import StorageInterface, entity_exists, load_all_entities


# =============================================================================
# 1. Public Handler API
# =============================================================================

async def fill_handler(parsed_command: ParsedCommand, context: Context) -> HandlerResult:
    """
    Handler for 'fill' command - initiates interactive form wizards.
    
    Creates form wizards for single cardinality schemas or record pickers
    for multiple cardinality schemas.
    """
    try:
        entity_model = parsed_command.entity_model
        if not entity_model:
            return _validation_error(
                "No entity specified for fill command",
                ["Specify an entity to fill, e.g.: fill news"]
            )
        
        entity_type = _get_entity_type(entity_model)
        entity_value = parsed_command.target.id if parsed_command.target else None
        
        # Validate organization context
        company_name = get_company_name_from_context(context)
        if not company_name:
            return _validation_error(
                "Fill command requires organization context",
                ["Navigate to a company first: cd company_name", 
                 "Or create a company: create company name=YourCompany"]
            )
        
        # Handle based on cardinality
        if getattr(entity_model, 'cardinality', None) == Cardinality.SINGLE:
            # Single cardinality: form wizard with existing data
            if not entity_exists(entity_type, company_name, context):
                return _validation_error(
                    f"{entity_type.title()} does not exist for company '{company_name}'",
                    [f"Create the {entity_type} first: create {entity_type}",
                     f"Or check available schemas: show {entity_type}"]
                )
            
            # Load existing data
            load_result = StorageInterface.load_entity(entity_type, company_name, context)
            if not load_result.success:
                return _validation_error(
                    load_result.error or f"Failed to load {entity_type} data",
                    [f"Check if {entity_type} data exists",
                     f"Or recreate: create {entity_type}"]
                )
            
            # Create form with requested fields
            requested_fields = _get_requested_fields(entity_model, parsed_command)
            if not requested_fields:
                return _validation_error(
                    "No fillable fields available",
                    [f"Check {entity_type} entity model has user-editable fields"]
                )
            
            entity_data = load_result.data or {}
            return _create_form_request(entity_type, entity_value, company_name, 
                                      requested_fields, entity_data, entity_model)
        else:
            # Multiple cardinality: record picker
            return _create_picker_request(entity_type, entity_value, company_name, 
                                        entity_model, context)
        
    except Exception as e:
        return _validation_error(
            f"Failed to create wizard: {str(e)}",
            ["Check entity model and field configuration"]
        )


# =============================================================================
# 2. Field Specification Building (Entity Model Analysis)
# =============================================================================

def _build_field_specs(entity_model: Type[BaseModel], field_names: List[str], pre_filled: Dict[str, Any]) -> List[FieldSpec]:
    """
    Convert field names to FieldSpec with metadata from entity model.
    
    Uses Pydantic model introspection to generate proper field specifications
    with type information, validation rules, and help text.
    """
    field_specs = []
    model_fields = entity_model.model_fields
    
    for field_name in field_names:
        if field_name not in model_fields:
            continue  # Skip unknown fields
            
        field_info = model_fields[field_name]
        field_type = _infer_field_type(field_info)
        
        # Build FieldSpec with metadata
        field_spec = FieldSpec(
            name=field_name,
            label=_generate_field_label(field_name),
            field_type=field_type,
            required=_is_field_required(field_info),
            default_value=pre_filled.get(field_name) or _get_field_default(field_info),
            placeholder=_generate_placeholder(field_name, field_type),
            help_text=_extract_field_description(field_info),
            options=_extract_field_options(field_info) if field_type == 'select' else None,
            validation_pattern=_extract_validation_pattern(field_info),
            min_length=_extract_min_length(field_info),
            max_length=_extract_max_length(field_info)
        )
        
        field_specs.append(field_spec)
    
    return field_specs


def _build_column_specs(entity_type: str, entity_model: Type[BaseModel], display_fields: List[str]) -> List[ColumnSpec]:
    """
    Convert display fields to ColumnSpec with metadata for table/picker display.
    """
    column_specs = []
    
    for field_name in display_fields:
        if field_name in entity_model.model_fields:
            column_spec = ColumnSpec(
                name=field_name,
                label=_generate_field_label(field_name),
                width=_get_column_width(field_name),
                sortable=_is_field_sortable(field_name)
            )
            column_specs.append(column_spec)
    
    return column_specs


def _infer_field_type(field_info) -> str:
    """Infer UI field type from Pydantic field annotation."""
    annotation = field_info.annotation
    
    # Handle common types
    if annotation == str:
        return 'text'
    elif annotation == int or annotation == float:
        return 'number'
    elif annotation == bool:
        return 'boolean'
    elif hasattr(annotation, '__origin__') and annotation.__origin__ is list:
        return 'select'  # Assume list fields are select options
    else:
        # Check for specific field names that suggest types
        return 'text'  # Default fallback


def _generate_field_label(field_name: str) -> str:
    """Generate human-readable label from field name."""
    return field_name.replace('_', ' ').title()


def _is_field_required(field_info) -> bool:
    """Check if field is required based on Pydantic field info."""
    return field_info.is_required() if hasattr(field_info, 'is_required') else False


def _get_field_default(field_info) -> Optional[Any]:
    """Extract default value from Pydantic field info."""
    return getattr(field_info, 'default', None) if hasattr(field_info, 'default') else None


def _generate_placeholder(field_name: str, field_type: str) -> Optional[str]:
    """Generate helpful placeholder text based on field name and type."""
    placeholders = {
        'email': 'user@example.com',
        'phone': '+1 (555) 123-4567',
        'website': 'https://example.com',
        'url': 'https://example.com',
        'date': 'YYYY-MM-DD',
        'currency': 'USD',
        'amount': '0.00',
        'price': '0.00',
    }
    
    return placeholders.get(field_name.lower())


def _extract_field_description(field_info) -> Optional[str]:
    """Extract help text from field description."""
    return getattr(field_info, 'description', None) if hasattr(field_info, 'description') else None


def _extract_field_options(field_info) -> Optional[List[str]]:
    """Extract select options from field annotation or constraints."""
    # This would need entity-specific logic based on field definitions
    return None


def _extract_validation_pattern(field_info) -> Optional[str]:
    """Extract regex validation pattern from field constraints."""
    # This would need to inspect Pydantic validators
    return None


def _extract_min_length(field_info) -> Optional[int]:
    """Extract minimum length constraint."""
    return None


def _extract_max_length(field_info) -> Optional[int]:
    """Extract maximum length constraint."""
    return None


def _get_column_width(field_name: str) -> Optional[int]:
    """Get appropriate column width for display field."""
    width_map = {
        'id': 80,
        'key': 120,
        'name': 200,
        'title': 200,
        'value': 150,
        'amount': 100,
        'date': 120,
        'status': 100,
    }
    return width_map.get(field_name.lower())


def _is_field_sortable(field_name: str) -> bool:
    """Determine if field should be sortable in table display."""
    non_sortable = ['description', 'notes', 'comments', 'details']
    return field_name.lower() not in non_sortable


# =============================================================================
# 3. Field & Data Extraction (Entity Data Processing)
# =============================================================================

def _get_entity_type(entity_model: Type[BaseModel]) -> str:
    """Extract entity type from model class name."""
    return entity_model.__name__.replace("Entity", "").lower()


def _get_display_fields(entity_type: str, entity_model: Type[BaseModel]) -> List[str]:
    """Get display fields for entity picker based on type."""
    all_fields = [f for f in entity_model.model_fields.keys() if f not in SYSTEM_FIELDS]
    
    # Entity-specific priorities
    priorities = {
        ('offering', 'target', 'values'): ['id', 'key', 'value'],
        ('metadata',): ['id', 'stage', 'sector', 'model']
    }
    
    for entities, fields in priorities.items():
        if entity_type in entities:
            display_fields = [f for f in fields if f in all_fields]
            # Add remaining fields up to 4 total
            display_fields.extend([f for f in all_fields if f not in display_fields][:4-len(display_fields)])
            return display_fields or all_fields[:3]
    
    return all_fields[:3] or ['id']


def _get_requested_fields(entity_model: Type[BaseModel], parsed_command: ParsedCommand) -> List[str]:
    """Determine which fields to include in the form."""
    # Priority: field_values > field_words > all model fields
    if parsed_command.field_values:
        return list(parsed_command.field_values.keys())
    if parsed_command.field_words:
        return parsed_command.field_words
    
    return [f for f in entity_model.model_fields.keys() if f not in SYSTEM_FIELDS]


# =============================================================================
# 4. UI Request Creation (Form & Picker Generation)  
# =============================================================================

def _create_picker_request(entity_type: str, entity_value: Optional[str], company_name: str, 
                         entity_model: Type[BaseModel], context: Context) -> PickerRequest:
    """Create picker request for multiple cardinality schemas."""
    records = load_all_entities(entity_type, company_name, context)
    display_fields = _get_display_fields(entity_type, entity_model)
    column_specs = _build_column_specs(entity_type, entity_model, display_fields)
    
    return PickerRequest(
        entity_id=entity_type,
        entity_name=entity_value or company_name,
        records=records,
        columns=column_specs,
        show_add_new_option=True,
        multi_select=False,
        title=f"Select {entity_type.title()} Record"
    )


def _create_form_request(entity_type: str, entity_value: Optional[str], company_name: str,
                        requested_fields: List[str], entity_data: Dict[str, Any], 
                        entity_model: Type[BaseModel]) -> FormRequest:
    """Create form request with FieldSpec and pre-filled values."""
    # Build field specifications with metadata
    field_specs = _build_field_specs(entity_model, requested_fields, entity_data)
    
    # Pre-filled values as they are (no conversion to string)
    pre_filled = {f: v for f, v in entity_data.items() 
                 if f in requested_fields and v is not None}
    
    return FormRequest(
        entity_id=entity_type,
        entity_name=entity_value or company_name,
        fields=field_specs,
        pre_filled_values=pre_filled,
        title=f"Fill {entity_type.title()} Information",
        submit_label="Save",
        cancel_label="Cancel"
    )


# =============================================================================
# 5. Validation & Utilities (Error Handling & Helpers)
# =============================================================================

def _validation_error(message: str, suggestions: List[str]) -> ErrorResult:
    """Create standardized validation error."""
    return ErrorResult(errors=[message], suggestions=suggestions)