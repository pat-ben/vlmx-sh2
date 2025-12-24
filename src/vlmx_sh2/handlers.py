# File: D:\Code\vlmx-sh2\src\vlmx_sh2\handlers.py

"""
Command handlers for VLMX DSL.

This module contains the actual implementation of commands registered in commands.py.
Uses the storage module for data persistence while leveraging the existing architecture.
"""

from datetime import datetime

from .commands import register_command
from .context import Context
from .words import get_word, EntityWord
from .enums import ContextLevel
from .parser import ParseResult
from .storage import create_company, delete_company, list_companies


# ==================== BUSINESS LOGIC UTILITIES ====================

def validate_attribute_for_entity(attribute_id: str, entity_id: str) -> bool:
    """
    Validate if an attribute exists on an entity using the Words Registry.
    
    Args:
        attribute_id: ID of the attribute word
        entity_id: ID of the entity word
        
    Returns:
        True if the attribute exists on the entity, False otherwise
    """
    from .words import AttributeWord
    
    # Get the attribute word
    attribute_word = get_word(attribute_id)
    if not attribute_word or not isinstance(attribute_word, AttributeWord):
        return False
    
    # Get the entity word
    entity_word = get_word(entity_id)
    if not entity_word or not isinstance(entity_word, EntityWord):
        return False
    
    # Check if the entity model is in the attribute's entity_models list
    return entity_word.entity_model in attribute_word.entity_models


def get_entity_model_from_registry(entity_id: str):
    """
    Get entity model from Words Registry with validation.
    
    Args:
        entity_id: ID of the entity word
        
    Returns:
        Entity model class or None if not found
    """
    entity_word = get_word(entity_id)
    if entity_word and isinstance(entity_word, EntityWord):
        return entity_word.entity_model
    return None

def extract_company_name_from_parse_result(parse_result: ParseResult) -> str:
    """Extract company name from parse result with fallback logic."""
    company_name = parse_result.entity_values.get('company_name')
    
    if company_name:
        return company_name
    
    # Fallback: generate timestamp-based name for demo purposes
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"Company_{timestamp}"


def extract_company_attributes_from_parse_result(parse_result: ParseResult) -> dict:
    """Extract company attributes from parse result with defaults and validation."""
    from .enums import Currency, Entity, Unit
    
    attributes = {}
    
    # Extract entity from attributes (entity=SA)
    entity_str = parse_result.attribute_values.get('entity', 'SA')
    try:
        attributes['entity'] = Entity(entity_str.upper())
    except ValueError:
        attributes['entity'] = Entity.SA  # Default fallback
    
    # Extract currency from attributes (currency=EUR)  
    currency_str = parse_result.attribute_values.get('currency', 'EUR')
    try:
        attributes['currency'] = Currency(currency_str.upper())
    except ValueError:
        attributes['currency'] = Currency.EUR  # Default fallback
    
    # Set default unit
    attributes['unit'] = Unit.THOUSANDS
    
    return attributes


# ==================== COMMAND HANDLERS ====================

@register_command(
    command_id="create_company",
    description="Create a new company entity with specified attributes",
    context=ContextLevel.SYS,
    required_words={"create", "company"},
    optional_words={"entity", "currency"},
    examples=[
        "create company ACME-SA --entity=SA --currency=EUR",
        "create company HoldCo --entity=HOLDING --currency=USD"
    ]
)
async def create_company_handler(parse_result: ParseResult, context: Context) -> dict:
    """
    Handler for creating companies.
    
    Command: create company [company_name] --entity=[entity] --currency=[currency]
    """
    try:
        # Infer entity type from parsed words
        entity_words = [word for word in parse_result.recognized_words 
                       if hasattr(word, 'word_type') and word.word_type.value == 'entity']
        
        if not entity_words:
            return {
                "success": False,
                "error": "No entity word found in command",
                "action": "create_entity"
            }
        
        entity_word = entity_words[0]  # Take the first entity word
        EntityModel = get_entity_model_from_registry(entity_word.id)
        
        if not EntityModel:
            return {
                "success": False,
                "error": f"Entity '{entity_word.id}' not found in Words Registry",
                "action": "create_entity"
            }
        
        # Extract entity name from parse result
        entity_name = extract_company_name_from_parse_result(parse_result)
        
        # Extract attributes from parse result
        attributes = extract_company_attributes_from_parse_result(parse_result)
        
        # Create entity dynamically using inferred model from Words Registry
        entity_instance = EntityModel(
            name=entity_name,
            entity=attributes["entity"],
            currency=attributes["currency"],
            unit=attributes["unit"],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            source_db=None,  # Optional field for portfolio tracking
            last_synced_at=None  # Optional field for portfolio sync tracking
        )
        
        # Convert to dict for JSON storage with datetime serialization
        entity_dict = entity_instance.model_dump(mode='json')
        
        # Ensure datetime fields are properly serialized as ISO strings
        for field_name in ['created_at', 'updated_at']:
            if field_name in entity_dict and hasattr(entity_instance, field_name):
                field_value = getattr(entity_instance, field_name)
                if field_value and hasattr(field_value, 'isoformat'):
                    entity_dict[field_name] = field_value.isoformat()
        
        # Use storage module to create entity
        result = create_company(entity_dict, context)  # TODO: Make this dynamic too
        result["action"] = f"create_{entity_word.id}"
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to create company: {str(e)}",
            "action": "create_company"
        }


@register_command(
    command_id="delete_company",
    description="Delete an existing company entity",
    context=ContextLevel.SYS,
    required_words={"delete", "company"},
    examples=[
        "delete company ACME-SA",
        "delete company HoldCo"
    ]
)
async def delete_company_handler(parse_result: ParseResult, context: Context) -> dict:
    """
    Handler for deleting companies.
    
    Command: delete company [company_name]
    """
    try:
        # Extract company name from parse result
        company_name = extract_company_name_from_parse_result(parse_result)
        
        # If no specific company name was provided, try to delete the first available company
        if company_name.startswith("Company_"):  # This is our generated fallback name
            companies_info = list_companies(context)
            if not companies_info["success"] or companies_info["count"] == 0:
                return {
                    "success": False,
                    "error": "No companies found to delete",
                    "action": "delete_company"
                }
            
            # Use the first company if no specific name was provided
            companies = companies_info["companies"]
            if companies:
                first_company = companies[0]
                company_name = first_company.get("name", "Unknown")
            else:
                return {
                    "success": False,
                    "error": "No companies found to delete",
                    "action": "delete_company"
                }
        
        # Use storage module to delete company
        result = delete_company(company_name, context)
        result["action"] = "delete_company"
        
        return result
            
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to delete company: {str(e)}",
            "action": "delete_company"
        }


# ==================== UTILITY FUNCTIONS ====================
# Note: list_companies and get_company_by_name are imported from storage module


# ==================== DEBUG INFO ====================

def get_handler_info() -> dict:
    """Get information about registered handlers."""
    return {
        "handlers": [
            {
                "command_id": "create_company",
                "description": "Create a new company entity",
                "required_words": ["create", "company"],
                "optional_words": ["entity", "currency"],
                "context_level": "SYS"
            },
            {
                "command_id": "delete_company", 
                "description": "Delete an existing company entity",
                "required_words": ["delete", "company"],
                "optional_words": [],
                "context_level": "SYS"
            }
        ],
        "storage": "JSON files",
        "utilities": ["list_companies", "get_company_by_name"]
    }