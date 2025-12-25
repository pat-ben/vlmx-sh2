"""
Data persistence layer for VLMX DSL.

Handles JSON file-based storage for entities with context-aware paths.
Provides CRUD operations for companies and other business entities,
managing file creation, updates, and retrieval operations.
"""

import json
import shutil
from datetime import datetime, date
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..core.context import Context
from ..core.enums import Entity, Currency, Unit, Type
from ..core.mappings import get_entity_json_filename


# ==================== PATH UTILITIES ====================

def get_data_directory_path(context: Context) -> Path:
    """
    Get the path to the data directory based on context.
    
    For SYS level: uses a global data/ directory
    For ORG/APP level: uses context-specific location
    
    Args:
        context: The execution context
        
    Returns:
        Path to the data directory
    """
    if context.level == 0:  # SYS level
        # Use current directory or a default system path
        base_path = context.sys_path or Path.cwd()
        return base_path / "data"
    else:
        # For ORG/APP level, use org-specific storage
        if context.org_db_path:
            return context.org_db_path.parent / "data"
        else:
            # Fallback to current directory
            return Path.cwd() / "data"

def get_company_folder_path(company_name: str, context: Context) -> Path:
    """
    Get the path to a specific company's folder.
    
    Args:
        company_name: Name of the company
        context: The execution context
        
    Returns:
        Path to the company's folder
    """
    data_dir = get_data_directory_path(context)
    return data_dir / company_name.lower()

def parse_incorporation_date(date_string: str) -> Optional[date]:
    """
    Parse incorporation date from ISO format (YYYY-MM-DD).
    
    Args:
        date_string: Date string in ISO format
        
    Returns:
        Parsed date object or None if invalid
    """
    try:
        return datetime.strptime(date_string, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


# ==================== JSON STORAGE OPERATIONS ====================

def load_company_organization(company_name: str, context: Context) -> Optional[Dict[str, Any]]:
    """
    Load organization data for a specific company.
    
    Args:
        company_name: Name of the company
        context: The execution context
        
    Returns:
        Organization dictionary or None if not found
    """
    company_folder = get_company_folder_path(company_name, context)
    org_file = company_folder / "organization.json"
    
    if not org_file.exists():
        return None
    
    try:
        with open(org_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Warning: Could not load organization from {org_file}: {e}")
        return None

def save_company_files(company_name: str, organization_data: Dict[str, Any], 
                      metadata_data: List[Dict[str, Any]] = None, 
                      brand_data: Dict[str, Any] = None, 
                      context: Context = None) -> None:
    """
    Save company files to the folder structure.
    
    Args:
        company_name: Name of the company
        organization_data: Organization data to save
        metadata_data: Metadata array (defaults to empty array)
        brand_data: Brand data (defaults to empty object with null values)
        context: The execution context
        
    Raises:
        RuntimeError: If files cannot be written
    """
    company_folder = get_company_folder_path(company_name, context)
    
    # Create company directory
    company_folder.mkdir(parents=True, exist_ok=True)
    
    # Default values
    if metadata_data is None:
        metadata_data = []
    
    if brand_data is None:
        brand_data = {
            "id": None,
            "org_id": 1,
            "vision": None,
            "mission": None,
            "personality": None,
            "promise": None,
            "brand": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
    
    try:
        # Save organization.json
        org_file = company_folder / "organization.json"
        with open(org_file, 'w', encoding='utf-8') as f:
            json.dump(organization_data, f, indent=2, default=str, ensure_ascii=False)
        
        # Save metadata.json
        metadata_file = company_folder / "metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata_data, f, indent=2, ensure_ascii=False)
        
        # Save brand.json
        brand_file = company_folder / "brand.json"
        with open(brand_file, 'w', encoding='utf-8') as f:
            json.dump(brand_data, f, indent=2, default=str, ensure_ascii=False)
            
    except IOError as e:
        raise RuntimeError(f"Could not save company files to {company_folder}: {e}")


# ==================== COMPANY CRUD OPERATIONS ====================

def company_folder_exists(company_name: str, context: Context) -> bool:
    """
    Check if a company folder exists.
    
    Args:
        company_name: Name of the company
        context: The execution context
        
    Returns:
        True if company folder exists, False otherwise
    """
    company_folder = get_company_folder_path(company_name, context)
    return company_folder.exists() and company_folder.is_dir()


def create_company(company_data: Dict[str, Any], context: Context) -> Dict[str, Any]:
    """
    Create a new company with folder structure.
    
    Creates a folder for the company with three JSON files:
    - organization.json: Company data matching OrganizationEntity schema
    - metadata.json: Empty array for future metadata
    - brand.json: Empty BrandEntity with null values
    
    Args:
        company_data: Company data dictionary
        context: The execution context
        
    Returns:
        Result dictionary with success status and details
    """
    try:
        company_name = company_data.get('name')
        if not company_name:
            return {
                "success": False,
                "error": "Company name is required"
            }
        
        # Check if company already exists
        if company_folder_exists(company_name, context):
            return {
                "success": False,
                "error": f"Company '{company_name}' already exists"
            }
        
        # Parse incorporation date if provided
        incorporation = None
        if 'incorporation' in company_data and company_data['incorporation']:
            incorporation = parse_incorporation_date(company_data['incorporation'])
            if incorporation:
                company_data['incorporation'] = incorporation.isoformat()
        
        # Create organization data matching OrganizationEntity schema
        organization_data = {
            "id": None,  # Will be set by database
            "name": company_data.get('name'),
            "entity": company_data.get('entity', 'SA'),  # Default to SA
            "type": company_data.get('type', 'company'),  # Default to company
            "currency": company_data.get('currency', 'EUR'),  # Default to EUR
            "unit": company_data.get('unit', 'THOUSANDS'),  # Default to THOUSANDS
            "closing": int(company_data.get('closing', 12)),  # Default to 12
            "incorporation": company_data.get('incorporation'),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "source_db": None,
            "last_synced_at": None
        }
        
        # Save company files
        save_company_files(company_name, organization_data, context=context)
        
        company_folder = get_company_folder_path(company_name, context)
        return {
            "success": True,
            "company": organization_data,
            "message": f"Successfully created company '{company_name}'",
            "folder_path": str(company_folder)
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to create company: {str(e)}"
        }


def delete_company(company_name: str, context: Context) -> Dict[str, Any]:
    """
    Delete a company by removing its entire folder.
    
    Args:
        company_name: Name of the company to delete
        context: The execution context
        
    Returns:
        Result dictionary with success status and details
    """
    try:
        # Check if company exists
        if not company_folder_exists(company_name, context):
            return {
                "success": False,
                "error": f"Company '{company_name}' not found"
            }
        
        # Load company data before deletion
        company_data = load_company_organization(company_name, context)
        company_folder = get_company_folder_path(company_name, context)
        
        # Remove the entire folder
        shutil.rmtree(company_folder)
        
        # Count remaining companies
        data_dir = get_data_directory_path(context)
        remaining_count = 0
        if data_dir.exists():
            remaining_count = sum(1 for item in data_dir.iterdir() if item.is_dir())
        
        return {
            "success": True,
            "deleted_company": company_data,
            "message": f"Successfully deleted company '{company_name}'",
            "remaining_companies": remaining_count,
            "folder_path": str(company_folder)
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to delete company: {str(e)}"
        }


def update_company(company_name: str, updates: Dict[str, Any], context: Context) -> Dict[str, Any]:
    """
    Update a company's organization data.
    
    Args:
        company_name: Name of the company to update
        updates: Dictionary of fields to update
        context: The execution context
        
    Returns:
        Result dictionary with success status and details
    """
    try:
        # Check if company exists
        if not company_folder_exists(company_name, context):
            return {
                "success": False,
                "error": f"Company '{company_name}' not found"
            }
        
        # Load current organization data
        organization_data = load_company_organization(company_name, context)
        if not organization_data:
            return {
                "success": False,
                "error": f"Could not load organization data for '{company_name}'"
            }
        
        # Parse incorporation date if being updated
        if 'incorporation' in updates and updates['incorporation']:
            incorporation = parse_incorporation_date(updates['incorporation'])
            if incorporation:
                updates['incorporation'] = incorporation.isoformat()
        
        # Update the data
        organization_data.update(updates)
        organization_data['updated_at'] = datetime.now().isoformat()
        
        # Save updated organization data
        save_company_files(company_name, organization_data, context=context)
        
        company_folder = get_company_folder_path(company_name, context)
        return {
            "success": True,
            "company": organization_data,
            "message": f"Successfully updated company '{company_name}'",
            "folder_path": str(company_folder)
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to update company: {str(e)}"
        }


# ==================== QUERY OPERATIONS ====================

def list_companies(context: Context) -> Dict[str, Any]:
    """
    List all companies by scanning folders in the data directory.
    
    Args:
        context: The execution context
        
    Returns:
        Result dictionary with companies list and metadata
    """
    try:
        data_dir = get_data_directory_path(context)
        companies = []
        
        if data_dir.exists():
            # Scan all directories in data folder
            for folder in data_dir.iterdir():
                if folder.is_dir():
                    # Try to load organization data for each folder
                    org_data = load_company_organization(folder.name, context)
                    if org_data:
                        companies.append(org_data)
        
        return {
            "success": True,
            "companies": companies,
            "count": len(companies),
            "data_directory": str(data_dir)
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to list companies: {str(e)}"
        }


def get_company_by_name(company_name: str, context: Context) -> Optional[Dict[str, Any]]:
    """
    Get a specific company by reading from its organization.json file.
    
    Args:
        company_name: Name of the company to retrieve
        context: The execution context
        
    Returns:
        Company dictionary if found, None otherwise
    """
    try:
        return load_company_organization(company_name, context)
    except Exception as e:
        print(f"Warning: Failed to get company '{company_name}': {e}")
        return None


def company_exists(company_name: str, context: Context) -> bool:
    """
    Check if a company exists by checking for its folder.
    
    Args:
        company_name: Name of the company to check
        context: The execution context
        
    Returns:
        True if company exists, False otherwise
    """
    return company_folder_exists(company_name, context)


# ==================== STORAGE INFO ====================

def get_storage_info(context: Context) -> Dict[str, Any]:
    """
    Get information about the folder-based storage system and current data.
    
    Args:
        context: The execution context
        
    Returns:
        Dictionary with storage metadata
    """
    data_dir = get_data_directory_path(context)
    companies_result = list_companies(context)
    company_count = companies_result.get('count', 0) if companies_result.get('success') else 0
    
    return {
        "storage_type": "JSON Folder-Based",
        "data_directory": str(data_dir),
        "directory_exists": data_dir.exists(),
        "company_count": company_count,
        "context_level": context.level,
        "context_name": context.level_name
    }


# ==================== GENERIC ENTITY STORAGE ====================

def load_entity_json(entity_name: str, company_name: str, context: Context) -> Optional[Dict[str, Any]]:
    """
    Load JSON data for any entity type.
    
    Args:
        entity_name: The entity word ID (e.g., "brand", "organization", "metadata")
        company_name: Name of the company
        context: The execution context
        
    Returns:
        Entity data dictionary or None if not found
    """
    # Get the JSON filename for this entity
    json_filename = get_entity_json_filename(entity_name)
    if not json_filename:
        return None
    
    # Get the company folder path
    company_folder = get_company_folder_path(company_name, context)
    entity_file = company_folder / json_filename
    
    if not entity_file.exists():
        return None
    
    try:
        with open(entity_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Warning: Could not load {entity_name} from {entity_file}: {e}")
        return None

def save_entity_json(entity_name: str, entity_data: Dict[str, Any], 
                    company_name: str, context: Context) -> Dict[str, Any]:
    """
    Save JSON data for any entity type.
    
    Args:
        entity_name: The entity word ID (e.g., "brand", "organization", "metadata")
        entity_data: The entity data to save
        company_name: Name of the company
        context: The execution context
        
    Returns:
        Result dictionary with success status and details
    """
    try:
        # Get the JSON filename for this entity
        json_filename = get_entity_json_filename(entity_name)
        if not json_filename:
            return {
                "success": False,
                "error": f"Unknown entity type: {entity_name}"
            }
        
        # Get the company folder path
        company_folder = get_company_folder_path(company_name, context)
        
        # Create folder if it doesn't exist
        company_folder.mkdir(parents=True, exist_ok=True)
        
        # Save the entity data
        entity_file = company_folder / json_filename
        with open(entity_file, 'w', encoding='utf-8') as f:
            json.dump(entity_data, f, indent=2, default=str, ensure_ascii=False)
        
        return {
            "success": True,
            "message": f"Successfully saved {entity_name} data",
            "file_path": str(entity_file)
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to save {entity_name} data: {str(e)}"
        }

def entity_exists(entity_name: str, company_name: str, context: Context) -> bool:
    """
    Check if an entity JSON file exists for a company.
    
    Args:
        entity_name: The entity word ID
        company_name: Name of the company
        context: The execution context
        
    Returns:
        True if the entity file exists, False otherwise
    """
    # Get the JSON filename for this entity
    json_filename = get_entity_json_filename(entity_name)
    if not json_filename:
        return False
    
    # Check if the file exists
    company_folder = get_company_folder_path(company_name, context)
    entity_file = company_folder / json_filename
    return entity_file.exists()

def create_default_entity_data(entity_name: str) -> Dict[str, Any]:
    """
    Create default entity data structure for a given entity type.
    
    Args:
        entity_name: The entity word ID
        
    Returns:
        Default entity data dictionary
    """
    from datetime import datetime
    
    # Base structure with timestamps
    base_data = {
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    # Entity-specific defaults
    if entity_name in ["organization", "company", "org"]:
        return {
            **base_data,
            "id": None,
            "name": None,
            "entity": None,
            "type": None,
            "currency": None,
            "unit": None,
            "closing": 12,
            "incorporation": None,
            "source_db": None,
            "last_synced_at": None
        }
    elif entity_name in ["brand", "branding", "identity"]:
        return {
            **base_data,
            "id": None,
            "org_id": 1,
            "vision": None,
            "mission": None,
            "personality": None,
            "promise": None,
            "brand": None
        }
    elif entity_name in ["metadata", "meta", "info"]:
        return []  # Metadata is stored as an array of key-value objects
    else:
        # Generic entity structure
        return {
            **base_data,
            "id": None,
            "name": None
        }