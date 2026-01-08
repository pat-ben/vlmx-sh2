"""
Wizard handlers.

Provides form wizard functionality for interactive data collection.
Returns FormWizardRequest models for UI interpretation.
"""

from typing import Optional, List, Type, Dict, Any
from pydantic import BaseModel

from ..models.results import FormWizardRequest, RecordPickerWizardRequest, ErrorResult, HandlerResult
from ..models.context import Context
from ..models.schema.enums import Cardinality
from ..models.parser.parsed_command import ParsedCommand
from ..handlers.utils import get_company_name_from_context
from ..storage.database import StorageInterface, entity_exists, load_all_entities


# Helper functions for fill_handler
def _handle_multiple_cardinality_entity(
    entity_type: str,
    entity_model: Type[BaseModel],
    entity_value: Optional[str],
    company_name: str,
    context: Context
) -> RecordPickerWizardRequest:
    """
    Handle fill request for multiple cardinality entities.
    
    Args:
        entity_type: Entity type name
        entity_model: Entity model class
        entity_value: Optional entity identifier
        company_name: Company name for context
        context: Current context
        
    Returns:
        RecordPickerWizardRequest for entity record selection
    """
    # Load ALL records for this entity type
    all_records = load_all_entities(entity_type, company_name, context)
    
    # Determine display fields for the picker based on entity type
    display_fields = _get_display_fields_for_entity(entity_type, entity_model)
    
    # Return record picker request
    title = f"Select {entity_type.title()} Record"
    entity_name = entity_value or company_name
    
    return RecordPickerWizardRequest(
        entity_id=entity_type,
        entity_name=entity_name,
        records=all_records,
        display_fields=display_fields,
        show_add_new_option=True,
        title=title
    )


def _determine_requested_fields(
    entity_model: Type[BaseModel],
    fields: Dict[str, Any],
    field_words: Optional[List[str]],
    parsed_command: Optional[ParsedCommand]
) -> List[str]:
    """
    Determine which fields should be included in the form wizard.
    
    Args:
        entity_model: Entity model class
        fields: Dictionary of field data
        field_words: Optional list of specific field names
        parsed_command: Optional parsed command object
        
    Returns:
        List of field names to include in the wizard
    """
    # System fields to exclude
    system_fields = {
        'id', 'co_id', 'brand_id', 'created_at', 'updated_at', 
        'source_db', 'last_synced_at'
    }
    
    if fields:
        # Use specific fields from fields parameter
        return list(fields.keys())
    elif field_words:
        # Use specific fields from field words  
        return field_words
    elif parsed_command and hasattr(parsed_command, 'attributes') and parsed_command.attributes:
        # Use specific fields from parsed command
        return list(parsed_command.attributes.keys())
    else:
        # Use all entity model fields except system fields
        return [
            field for field in entity_model.model_fields.keys() 
            if field not in system_fields
        ]


def _create_form_wizard_request(
    entity_type: str,
    entity_value: Optional[str],
    company_name: str,
    requested_fields: List[str],
    entity_data: Dict[str, Any]
) -> FormWizardRequest:
    """
    Create a FormWizardRequest with pre-filled values.
    
    Args:
        entity_type: Entity type name
        entity_value: Optional entity identifier
        company_name: Company name for context
        requested_fields: List of fields to include
        entity_data: Existing entity data for pre-filling
        
    Returns:
        FormWizardRequest with pre-filled values
    """
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


def _get_display_fields_for_entity(entity_type: str, entity_model) -> List[str]:
    """
    Determine which fields to display in the record picker for a dynamic entity.
    
    Args:
        entity_type: The entity type name
        entity_model: The entity model class
        
    Returns:
        List of field names to display in the picker
    """
    # Default system fields to exclude
    system_fields = {
        'id', 'co_id', 'brand_id', 'created_at', 'updated_at', 
        'source_db', 'last_synced_at'
    }
    
    # Get all model fields excluding system fields
    all_fields = [
        field for field in entity_model.model_fields.keys() 
        if field not in system_fields
    ]
    
    # Entity-specific display field priorities
    if entity_type in ['offering', 'target', 'values']:
        # For key-value entities, prioritize id, key, value
        priority_fields = ['id', 'key', 'value']
        display_fields = []
        
        # Add priority fields if they exist
        for field in priority_fields:
            if field in all_fields:
                display_fields.append(field)
        
        # Add any remaining fields (up to 3-4 total for good display)
        for field in all_fields:
            if field not in display_fields and len(display_fields) < 4:
                display_fields.append(field)
        
        return display_fields if display_fields else all_fields[:3]
    
    elif entity_type == 'metadata':
        # For metadata, show key metadata fields
        priority_fields = ['id', 'stage', 'sector', 'model']
        display_fields = []
        
        for field in priority_fields:
            if field in all_fields:
                display_fields.append(field)
        
        return display_fields if display_fields else all_fields[:3]
    
    else:
        # Default: show first few non-system fields
        return all_fields[:3] if all_fields else ['id']


async def fill_handler(
    entity_model: Type[BaseModel],
    entity_value: Optional[str],
    fields: Dict[str, Any],
    context: Context,
    field_words: Optional[List[str]] = None,
    parsed_command: Optional[ParsedCommand] = None
) -> HandlerResult:
    """
    Handler for 'fill' command - initiates interactive form wizards for entity data collection.
    
    Creates appropriate wizard interfaces based on entity cardinality. For single cardinality
    entities (metadata, identity), loads existing data and presents a pre-filled form wizard.
    For multi cardinality entities (offering, target, values), presents a record picker
    to select which record to edit, with an option to create new records.
    
    Workflow:
    1. Validates organization context requirement
    2. Determines entity cardinality from model metadata
    3. For SINGLE cardinality: Loads existing entity data for pre-filling
    4. For MULTIPLE cardinality: Loads all records and presents selection interface
    5. Returns appropriate wizard request (FormWizardRequest or RecordPickerWizardRequest)
    
    Args:
        entity_model: Pydantic model class for the entity type
        entity_value: Optional entity name/identifier (used for record targeting)
        fields: Dictionary of specific fields to include in form (optional)
        context: Current execution context (must be at ORG level)
        field_words: Optional list of specific field names to include in wizard
        parsed_command: Optional parsed command object with field specifications
        
    Returns:
        FormWizardRequest for single cardinality entities with pre-filled data,
        RecordPickerWizardRequest for multi cardinality entities,
        or ErrorResult on validation/loading failures
        
    Raises:
        Returns ErrorResult for context validation errors, missing entities, or storage failures
    """
    try:
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
        
        # Check entity cardinality to determine flow
        if getattr(entity_model, 'cardinality', None) == Cardinality.SINGLE:
            # Static entity flow - single record per company
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
            load_result = StorageInterface.load_entity(entity_type, company_name, context)
            if not load_result.success:
                return ErrorResult(
                    errors=[load_result.error or f"Failed to load {entity_type} data for company '{company_name}'"],
                    suggestions=[
                        f"Check if {entity_type} data file exists",
                        f"Or recreate the {entity_type} using: create {entity_type}"
                    ]
                )
            
            # Determine requested fields and create form wizard
            requested_fields = _determine_requested_fields(entity_model, fields, field_words, parsed_command)
            
            if not requested_fields:
                return ErrorResult(
                    errors=["No fillable fields available"],
                    suggestions=[f"Check {entity_type} entity model has user-editable fields"]
                )
            
            # Ensure we have valid data
            entity_data = load_result.data if load_result.data else {}
            return _create_form_wizard_request(entity_type, entity_value, company_name, requested_fields, entity_data)
        
        else:
            # Dynamic entity flow - multiple records per company
            return _handle_multiple_cardinality_entity(entity_type, entity_model, entity_value, company_name, context)
        
    except Exception as e:
        return ErrorResult(
            errors=[f"Failed to create wizard: {str(e)}"],
            suggestions=["Check entity model and field configuration"]
        )