"""
Field specification utilities.

Provides functions for building FieldSpec and ColumnSpec from Pydantic models.
Used by both handlers and UI components to maintain proper backend/UI separation.
"""

from typing import Type, List, Dict, Any, Optional
from pydantic import BaseModel

from ..models.responses import FieldSpec, ColumnSpec


def build_field_specs(
    entity_model: Type[BaseModel], 
    field_names: List[str], 
    pre_filled: Dict[str, Any]
) -> List[FieldSpec]:
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


def build_column_specs(
    entity_type: str,
    entity_model: Type[BaseModel], 
    display_fields: List[str]
) -> List[ColumnSpec]:
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


# =============================================================================
# Private helper functions
# =============================================================================

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