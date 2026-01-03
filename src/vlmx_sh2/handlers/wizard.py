"""
Wizard handlers for VLMX DSL.

Provides form wizard functionality for interactive data collection.
Returns FormWizardRequest models for UI interpretation.
"""

from typing import Dict, List
from ..models.results import FormWizardRequest, ErrorResult


async def fill_handler(
    entity_model=None, entity_value=None, fields=None, context=None, 
    field_words=None, parsed_command=None
):
    """
    Handler for 'fill' command - requests a form wizard for entity data collection.
    
    Extracts fields from parsed_command.fields (if provided) OR from 
    entity_model.model_fields (excluding system fields).
    
    Returns FormWizardRequest for UI to handle.
    """
    if entity_model is None:
        return ErrorResult(
            errors=["entity_model is required for fill command"],
            suggestions=["Try: fill brand vision mission"]
        )
    
    try:
        # Determine entity type and name
        entity_type = entity_model.__name__.replace("Entity", "").lower()
        entity_name = entity_value or entity_type
        
        # Extract fields to fill
        if parsed_command and hasattr(parsed_command, 'fields') and parsed_command.fields:
            # Use specific fields from command fields
            fields = list(parsed_command.fields.keys())
        elif field_words:
            # Use specific fields from field words  
            fields = field_words
        else:
            # Use all entity model fields except system fields
            system_fields = {
                'id', 'co_id', 'brand_id', 'created_at', 'updated_at', 
                'source_db', 'last_synced_at'
            }
            fields = [
                field for field in entity_model.model_fields.keys() 
                if field not in system_fields
            ]
        
        if not fields:
            return ErrorResult(
                errors=["No fields available to fill"],
                suggestions=[f"Check {entity_type} entity model has fillable fields"]
            )
        
        # Get pre-filled values from fields if provided
        pre_filled_values = fields or {}
        
        # Create wizard request
        title = f"Fill {entity_type.title()} Information"
        
        return FormWizardRequest(
            entity_id=entity_type,
            entity_name=entity_name,
            fields=fields,
            pre_filled_values=pre_filled_values,
            title=title
        )
        
    except Exception as e:
        return ErrorResult(
            errors=[f"Failed to create wizard: {str(e)}"],
            suggestions=["Check entity model and field configuration"]
        )