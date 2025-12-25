"""
Data persistence layer for VLMX DSL.

Handles JSON file-based storage for entities with context-aware paths.
Provides CRUD operations for companies and other business entities,
managing file creation, updates, and retrieval operations.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..core.context import Context


# ==================== PATH UTILITIES ====================

def get_companies_file_path(context: Context) -> Path:
    """
    Get the path to the companies JSON file based on context.
    
    For SYS level: stores in a global companies.json
    For ORG/APP level: stores in context-specific location
    
    Args:
        context: The execution context
        
    Returns:
        Path to the companies JSON file
    """
    if context.level == 0:  # SYS level
        # Use current directory or a default system path
        base_path = context.sys_path or Path.cwd()
        return base_path / "companies.json"
    else:
        # For ORG/APP level, use org-specific storage
        if context.org_db_path:
            return context.org_db_path.parent / "companies.json"
        else:
            # Fallback to current directory
            return Path.cwd() / f"companies_{context.org_id or 'default'}.json"


# ==================== JSON STORAGE OPERATIONS ====================

def load_companies(context: Context) -> List[Dict[str, Any]]:
    """
    Load companies from JSON file.
    
    Args:
        context: The execution context
        
    Returns:
        List of company dictionaries
    """
    file_path = get_companies_file_path(context)
    
    if not file_path.exists():
        return []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Warning: Could not load companies from {file_path}: {e}")
        return []


def save_companies(companies: List[Dict[str, Any]], context: Context) -> None:
    """
    Save companies to JSON file.
    
    Args:
        companies: List of company dictionaries to save
        context: The execution context
        
    Raises:
        RuntimeError: If file cannot be written
    """
    file_path = get_companies_file_path(context)
    
    # Create directory if it doesn't exist
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(companies, f, indent=2, default=str, ensure_ascii=False)
    except IOError as e:
        raise RuntimeError(f"Could not save companies to {file_path}: {e}")


# ==================== COMPANY CRUD OPERATIONS ====================

def find_company_by_name(companies: List[Dict[str, Any]], name: str) -> Optional[Dict[str, Any]]:
    """
    Find a company by name (case-insensitive).
    
    Args:
        companies: List of company dictionaries
        name: Company name to search for
        
    Returns:
        Company dictionary if found, None otherwise
    """
    name_lower = name.lower()
    for company in companies:
        if company.get('name', '').lower() == name_lower:
            return company
    return None


def create_company(company_data: Dict[str, Any], context: Context) -> Dict[str, Any]:
    """
    Create a new company in storage.
    
    Args:
        company_data: Company data dictionary
        context: The execution context
        
    Returns:
        Result dictionary with success status and details
    """
    try:
        # Load existing companies
        companies = load_companies(context)
        
        # Check if company already exists
        company_name = company_data.get('name')
        if company_name and find_company_by_name(companies, company_name):
            return {
                "success": False,
                "error": f"Company '{company_name}' already exists"
            }
        
        # Add to companies list
        companies.append(company_data)
        
        # Save to file
        save_companies(companies, context)
        
        return {
            "success": True,
            "company": company_data,
            "message": f"Successfully created company '{company_name}'",
            "file_path": str(get_companies_file_path(context))
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to create company: {str(e)}"
        }


def delete_company(company_name: str, context: Context) -> Dict[str, Any]:
    """
    Delete a company from storage by name.
    
    Args:
        company_name: Name of the company to delete
        context: The execution context
        
    Returns:
        Result dictionary with success status and details
    """
    try:
        # Load existing companies
        companies = load_companies(context)
        
        if not companies:
            return {
                "success": False,
                "error": "No companies found to delete"
            }
        
        # Find and remove the company
        company_to_delete = find_company_by_name(companies, company_name)
        if not company_to_delete:
            return {
                "success": False,
                "error": f"Company '{company_name}' not found"
            }
        
        # Remove the company from the list
        companies = [c for c in companies if c.get('name', '').lower() != company_name.lower()]
        
        # Save updated list
        save_companies(companies, context)
        
        return {
            "success": True,
            "deleted_company": company_to_delete,
            "message": f"Successfully deleted company '{company_name}'",
            "remaining_companies": len(companies),
            "file_path": str(get_companies_file_path(context))
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to delete company: {str(e)}"
        }


def update_company(company_name: str, updates: Dict[str, Any], context: Context) -> Dict[str, Any]:
    """
    Update a company in storage.
    
    Args:
        company_name: Name of the company to update
        updates: Dictionary of fields to update
        context: The execution context
        
    Returns:
        Result dictionary with success status and details
    """
    try:
        # Load existing companies
        companies = load_companies(context)
        
        # Find the company
        company_index = None
        for i, company in enumerate(companies):
            if company.get('name', '').lower() == company_name.lower():
                company_index = i
                break
        
        if company_index is None:
            return {
                "success": False,
                "error": f"Company '{company_name}' not found"
            }
        
        # Update the company
        companies[company_index].update(updates)
        
        # Save to file
        save_companies(companies, context)
        
        return {
            "success": True,
            "company": companies[company_index],
            "message": f"Successfully updated company '{company_name}'",
            "file_path": str(get_companies_file_path(context))
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to update company: {str(e)}"
        }


# ==================== QUERY OPERATIONS ====================

def list_companies(context: Context) -> Dict[str, Any]:
    """
    List all companies in storage.
    
    Args:
        context: The execution context
        
    Returns:
        Result dictionary with companies list and metadata
    """
    try:
        companies = load_companies(context)
        return {
            "success": True,
            "companies": companies,
            "count": len(companies),
            "file_path": str(get_companies_file_path(context))
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to list companies: {str(e)}"
        }


def get_company_by_name(company_name: str, context: Context) -> Optional[Dict[str, Any]]:
    """
    Get a specific company by name.
    
    Args:
        company_name: Name of the company to retrieve
        context: The execution context
        
    Returns:
        Company dictionary if found, None otherwise
    """
    try:
        companies = load_companies(context)
        return find_company_by_name(companies, company_name)
    except Exception as e:
        print(f"Warning: Failed to get company '{company_name}': {e}")
        return None


def company_exists(company_name: str, context: Context) -> bool:
    """
    Check if a company exists in storage.
    
    Args:
        company_name: Name of the company to check
        context: The execution context
        
    Returns:
        True if company exists, False otherwise
    """
    return get_company_by_name(company_name, context) is not None


# ==================== STORAGE INFO ====================

def get_storage_info(context: Context) -> Dict[str, Any]:
    """
    Get information about the storage system and current data.
    
    Args:
        context: The execution context
        
    Returns:
        Dictionary with storage metadata
    """
    file_path = get_companies_file_path(context)
    companies = load_companies(context)
    
    return {
        "storage_type": "JSON",
        "file_path": str(file_path),
        "file_exists": file_path.exists(),
        "company_count": len(companies),
        "context_level": context.level,
        "context_name": context.level_name
    }