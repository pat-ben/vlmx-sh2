"""
Wizard handlers for VLMX DSL.

Provides form wizard functionality for interactive data collection.
Returns FormWizardRequest models for UI interpretation.
"""

from typing import Optional, List
from ..models.results import FormWizardRequest, ErrorResult
from ..models.context import Context
from ..handlers.utils import get_company_name_from_context
from ..storage.database import entity_exists, load_entity


async def fill_handler(
    entity_model=None, 
    entity_value: Optional[str] = None, 
    fields: Optional[List[str]] = None, 
    context: Optional[Context] = None, 
    field_words: Optional[List[str]] = None, 
    parsed_command=None
):
    """
    Handler for 'fill' command - requests a form wizard for entity data collection.
    
    Loads existing entity data from database and creates a FormWizardRequest
    with pre-filled values for the user to edit.
    
    Returns FormWizardRequest if entity exists, ErrorResult otherwise.
    """
    if entity_model is None:
        return ErrorResult(
            errors=["entity_model is required for fill command"],
            suggestions=["Try: fill brand vision mission"]
        )
    
    try:
        # Validate context is provided
        if context is None:
            return ErrorResult(
                errors=["Context is required for fill command"],
                suggestions=["Ensure command is executed within proper context"]
            )
        
        # Determine entity type and name
        entity_type = entity_model.__name__.replace("Entity", "").lower()
        
        # Validate context - must be in organization context
        company_name = get_company_name_from_context(context)
        if not company_name:
            return ErrorResult(
                errors=["Fill command requires organization context"],
                suggestions=[
                    "Navigate to a company first using: cd company_name",
                    "Or create a company using: create company name=YourCompany"
                ]
            )
        
        # Check if entity exists in database
        if not entity_exists(entity_type, company_name, context):
            return ErrorResult(
                errors=[f"{entity_type.title()} does not exist for company '{company_name}'"],
                suggestions=[
                    f"Create the {entity_type} first using: create {entity_type}",
                    f"Or check available entities using: show {entity_type}"
                ]
            )
        
        # Load existing entity data for pre-filling
        entity_data = load_entity(entity_type, company_name, context)
        if not entity_data:
            return ErrorResult(
                errors=[f"Failed to load {entity_type} data for company '{company_name}'"],
                suggestions=[
                    f"Check if {entity_type} data file exists",
                    f"Or recreate the {entity_type} using: create {entity_type}"
                ]
            )
        
        # Determine which fields to display
        system_fields = {
            'id', 'co_id', 'brand_id', 'created_at', 'updated_at', 
            'source_db', 'last_synced_at'
        }
        
        if parsed_command and hasattr(parsed_command, 'fields') and parsed_command.fields:
            # Use specific fields from command fields
            requested_fields = list(parsed_command.fields.keys())
        elif field_words:
            # Use specific fields from field words  
            requested_fields = field_words
        else:
            # Use all entity model fields except system fields
            requested_fields = [
                field for field in entity_model.model_fields.keys() 
                if field not in system_fields
            ]
        
        if not requested_fields:
            return ErrorResult(
                errors=["No fillable fields available"],
                suggestions=[f"Check {entity_type} entity model has user-editable fields"]
            )
        
        # Extract pre-filled values from loaded entity data
        pre_filled_values = {}
        for field in requested_fields:
            if field in entity_data and entity_data[field] is not None:
                pre_filled_values[field] = str(entity_data[field])
        
        # Create wizard request
        title = f"Fill {entity_type.title()} Information"
        entity_name = entity_value or company_name
        
        return FormWizardRequest(
            entity_id=entity_type,
            entity_name=entity_name,
            fields=requested_fields,
            pre_filled_values=pre_filled_values,
            title=title
        )
        
    except Exception as e:
        return ErrorResult(
            errors=[f"Failed to create wizard: {str(e)}"],
            suggestions=["Check entity model and field configuration"]
        )