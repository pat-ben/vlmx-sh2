# File: D:\Code\vlmx-sh2\src\vlmx_sh2\handlers.py

"""
Command handlers for VLMX DSL.

This module contains the actual implementation of commands registered in commands.py.
Uses the storage module for data persistence while leveraging the existing architecture.
"""

from datetime import datetime

from .commands import register_command
from .context import Context
from .entities import CompanyEntity
from .enums import ContextLevel
from .parser import ParseResult
from .storage import create_company, delete_company, list_companies


# ==================== BUSINESS LOGIC UTILITIES ====================

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
        # Extract company name from parse result
        company_name = extract_company_name_from_parse_result(parse_result)
        
        # Extract attributes from parse result
        attributes = extract_company_attributes_from_parse_result(parse_result)
        
        # Create company entity
        company_entity = CompanyEntity(
            name=company_name,
            entity=attributes["entity"],
            currency=attributes["currency"],
            unit=attributes["unit"],
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Convert to dict for JSON storage
        company_dict = company_entity.model_dump()
        company_dict["created_at"] = company_entity.created_at.isoformat()
        company_dict["updated_at"] = company_entity.updated_at.isoformat()
        
        # Use storage module to create company
        result = create_company(company_dict, context)
        result["action"] = "create_company"
        
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