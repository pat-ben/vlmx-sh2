# File: D:\Code\vlmx-sh2\src\vlmx_sh2\handlers.py

"""
Command handlers for VLMX DSL.

This module contains the actual implementation of commands registered in commands.py.
Uses the storage module for data persistence while leveraging the existing architecture.
"""

from datetime import datetime
from typing import Any, List, Optional

from .commands import register_command
from .context import Context
from .entities import CompanyEntity
from .enums import ContextLevel, Currency, Entity, Unit
from .storage import create_company, delete_company, list_companies, get_company_by_name
from .words import Word


def extract_company_name_from_words(words: List[Word]) -> Optional[str]:
    """
    Extract company name from words.
    
    In our DSL, the company name is the first value that's not a keyword.
    This is a simple implementation - in a full parser you'd use proper value extraction.
    """
    # For now, we'll assume the company name is provided as a simple string
    # In a real implementation, this would come from the parser
    # For demo purposes, we'll return a placeholder
    return "EXAMPLE-COMPANY"


def extract_attributes_from_words(words: List[Word]) -> dict:
    """
    Extract attribute values from words.
    
    In our DSL: --entity=SA --currency=EUR
    This is a simplified implementation.
    """
    # For demo purposes, return default values
    # In a real implementation, this would parse the actual command arguments
    return {
        "entity": Entity.SA,
        "currency": Currency.EUR,
        "unit": Unit.THOUSANDS
    }


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
async def create_company_handler(words: List[Word], context: Context) -> dict:
    """
    Handler for creating companies.
    
    Command: create company [company_name] --entity=[entity] --currency=[currency]
    """
    try:
        # Extract company name from command
        # NOTE: In a real implementation, this would come from the parser
        # For demo purposes, we'll use a timestamp-based name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        company_name = f"Company_{timestamp}"
        
        # Extract attributes from words
        attributes = extract_attributes_from_words(words)
        
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
async def delete_company_handler(words: List[Word], context: Context) -> dict:
    """
    Handler for deleting companies.
    
    Command: delete company [company_name]
    """
    try:
        # Get current companies list to find a company to delete
        companies_info = list_companies(context)
        if not companies_info["success"] or companies_info["count"] == 0:
            return {
                "success": False,
                "error": "No companies found to delete",
                "action": "delete_company"
            }
        
        # Extract company name from command
        # NOTE: In a real implementation, this would come from the parser
        # For demo purposes, we'll delete the first company if any exist
        companies = companies_info["companies"]
        if companies:
            first_company = companies[0]
            company_name = first_company.get("name", "Unknown")
            
            # Use storage module to delete company
            result = delete_company(company_name, context)
            result["action"] = "delete_company"
            
            return result
        else:
            return {
                "success": False,
                "error": "No companies found to delete",
                "action": "delete_company"
            }
            
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