# File: src/vlmx_sh2/storage/database.py
"""
Data persistence layer.

Handles JSON file-based storage for entities with context-aware paths.
Provides CRUD operations for companies and other business entities,
managing file creation, updates, and retrieval operations.
"""

import json
import os
import shutil
from datetime import datetime, date
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..models.context import Context, ContextLevel
from vlmx_sh2.enums import Cardinality
from ..models.results import StorageResult
from .mappings import get_entity_json_filename, _entity_class_to_json_filename


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
    if context.level == ContextLevel.SYS:
        # Use current directory or a default system path
        base_path = context.sys_path or Path.cwd()
        return base_path / "data"
    else:
        # For ORG/APP level, use org-specific storage
        if context.org_db_path:
            # org_db_path points to company.json, so parent is the company folder
            # We want the data directory that contains company folders
            return context.org_db_path.parent.parent
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


# ==================== STORAGE INTERFACE ====================

class StorageInterface:
    """
    Single point of access for all storage operations.
    
    All other code must use this interface - no direct JSON file operations allowed.
    Standardizes return types and centralizes error handling.
    """
    
    @staticmethod
    def create_entity(entity_type: str, data: Dict[str, Any], context: Context) -> StorageResult:
        """Create a new entity with standardized error handling."""
        try:
            result = create_entity(entity_type, data, context)
            
            if result is None:
                return StorageResult(
                    success=False,
                    error=f"Failed to create {entity_type}: Unknown error"
                )
            
            if not isinstance(result, dict):
                return StorageResult(
                    success=False,
                    error=f"Invalid storage result format for {entity_type}"
                )
                
            if result.get("success"):
                return StorageResult(
                    success=True,
                    data=result,
                    message=result.get("message", f"Successfully created {entity_type}")
                )
            else:
                return StorageResult(
                    success=False,
                    error=result.get("error", f"Failed to create {entity_type}"),
                    message=result.get("message")
                )
                
        except Exception as e:
            return StorageResult(
                success=False,
                error=f"Exception during create {entity_type}: {str(e)}"
            )
    
    @staticmethod
    def load_entity(entity_type: str, company_name: str, context: Context) -> StorageResult:
        """Load an entity with standardized error handling."""
        try:
            result = load_entity(entity_type, company_name, context)
            
            if result is None:
                return StorageResult(
                    success=False,
                    error=f"{entity_type.title()} not found for company '{company_name}'"
                )
            
            return StorageResult(
                success=True,
                data=result,
                message=f"Successfully loaded {entity_type}"
            )
            
        except Exception as e:
            return StorageResult(
                success=False,
                error=f"Exception during load {entity_type}: {str(e)}"
            )
    
    @staticmethod  
    def save_entity(entity_type: str, data: Dict[str, Any], company_name: str, context: Context) -> StorageResult:
        """Save an entity with standardized error handling."""
        try:
            result = save_entity(entity_type, data, company_name, context)
            
            if result is None:
                return StorageResult(
                    success=False,
                    error=f"Failed to save {entity_type}: Unknown error"
                )
            
            if not isinstance(result, dict):
                return StorageResult(
                    success=False,
                    error=f"Invalid storage result format for {entity_type}"
                )
                
            if result.get("success"):
                return StorageResult(
                    success=True,
                    data=result,
                    message=result.get("message", f"Successfully saved {entity_type}")
                )
            else:
                return StorageResult(
                    success=False,
                    error=result.get("error", f"Failed to save {entity_type}"),
                    message=result.get("message")
                )
                
        except Exception as e:
            return StorageResult(
                success=False,
                error=f"Exception during save {entity_type}: {str(e)}"
            )
    
    @staticmethod
    def delete_entity(entity_type: str, company_name: str, context: Context) -> StorageResult:
        """Delete an entity with standardized error handling."""
        try:
            result = delete_entity(entity_type, company_name, context)
            
            if result is None:
                return StorageResult(
                    success=False,
                    error=f"Failed to delete {entity_type}: Unknown error"
                )
            
            if not isinstance(result, dict):
                return StorageResult(
                    success=False,
                    error=f"Invalid storage result format for {entity_type}"
                )
                
            if result.get("success"):
                return StorageResult(
                    success=True,
                    data=result,
                    message=result.get("message", f"Successfully deleted {entity_type}")
                )
            else:
                return StorageResult(
                    success=False,
                    error=result.get("error", f"Failed to delete {entity_type}"),
                    message=result.get("message")
                )
                
        except Exception as e:
            return StorageResult(
                success=False,
                error=f"Exception during delete {entity_type}: {str(e)}"
            )
    
    @staticmethod
    def list_entities(entity_type: str, company_name: str, context: Context) -> StorageResult:
        """List entities with standardized error handling."""
        try:
            if entity_type == 'company':
                result = list_companies(context)
            else:
                result = load_all_entities(entity_type, company_name, context)
                # Convert list result to standard format
                if isinstance(result, list):
                    result = {
                        "success": True,
                        "data": result,
                        "count": len(result)
                    }
            
            if result is None:
                return StorageResult(
                    success=False,
                    error=f"Failed to list {entity_type}: Unknown error"
                )
            
            if isinstance(result, list):
                return StorageResult(
                    success=True,
                    data={"entities": result, "count": len(result)},
                    message=f"Successfully listed {len(result)} {entity_type} entities"
                )
            
            if not isinstance(result, dict):
                return StorageResult(
                    success=False,
                    error=f"Invalid storage result format for list {entity_type}"
                )
                
            if result.get("success", True):  # Some list functions don't have success field
                return StorageResult(
                    success=True,
                    data=result,
                    message=result.get("message", f"Successfully listed {entity_type} entities")
                )
            else:
                return StorageResult(
                    success=False,
                    error=result.get("error", f"Failed to list {entity_type}"),
                    message=result.get("message")
                )
                
        except Exception as e:
            return StorageResult(
                success=False,
                error=f"Exception during list {entity_type}: {str(e)}"
            )


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


# ==================== GENERIC ENTITY OPERATIONS ====================

def create_entity(entity_type: str, data: Dict[str, Any], context: Context) -> Dict[str, Any]:
    """
    Generic entity creation - works for ANY entity type.
    
    Args:
        entity_type: Entity type name (e.g., 'company', 'brand', 'metadata')
        data: Validated entity data
        context: Execution context
        
    Returns:
        Result dictionary with success status and details
    """
    try:
        if entity_type == 'company':
            # Inline company creation logic
            company_name = data.get('name')
            if not company_name:
                return {
                    "success": False,
                    "error": "Company name is required"
                }
            
            # Check if company already exists
            company_folder = get_company_folder_path(company_name, context)
            if company_folder.exists() and company_folder.is_dir():
                return {
                    "success": False,
                    "error": f"Company '{company_name}' already exists"
                }
            
            # Parse incorporation date if provided
            if 'incorporation' in data and data['incorporation']:
                try:
                    incorporation = datetime.strptime(data['incorporation'], "%Y-%m-%d").date()
                    data['incorporation'] = incorporation.isoformat()
                except (ValueError, TypeError):
                    # Keep original value if parsing fails
                    pass
            
            # Import CompanyEntity to get proper defaults
            from ..models.schema.company import CompanyEntity
            
            # Create organization data using CompanyEntity model defaults
            base_data = {
                "id": None,
                "name": data.get('name'),
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }
            
            # Merge user data with base data
            base_data.update(data)
            
            # Use CompanyEntity model to apply defaults and validate
            try:
                company_instance = CompanyEntity(**base_data)
                organization_data = company_instance.model_dump()
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Invalid company data: {str(e)}"
                }
            
            # Create company directory
            company_folder.mkdir(parents=True, exist_ok=True)
            
            # Import CompanyDatabase to get all entity classes  
            from ..models.schema.company import CompanyDatabase
            
            created_files = []
            
            try:
                # CompanyEntity data is stored as "company.json" following standard convention
                org_file = company_folder / "company.json"
                with open(org_file, 'w', encoding='utf-8') as f:
                    json.dump(organization_data, f, indent=2, default=str, ensure_ascii=False)
                created_files.append("company.json")
                
                # Dynamically create JSON files for all other entities in CompanyDatabase.tables
                for entity_class in CompanyDatabase.tables:
                    # Skip CompanyEntity as it's already handled as "company.json"
                    if entity_class.__name__ == 'CompanyEntity':
                        continue
                    
                    # Generate JSON filename from entity class name
                    json_filename = _entity_class_to_json_filename(entity_class.__name__)
                    entity_file = company_folder / json_filename
                    
                    # Determine the default data structure based on cardinality
                    if hasattr(entity_class, 'cardinality') and entity_class.cardinality == Cardinality.SINGLE:
                        # Single record entity - create default record with model defaults
                        try:
                            # Create a default instance to get all field defaults
                            default_instance_data = {
                                "id": None,
                                "co_id": 1,
                                "created_at": datetime.now().isoformat(),
                                "updated_at": datetime.now().isoformat()
                            }
                            
                            # Apply entity model defaults by creating an instance
                            # This handles all the default values defined in the model
                            entity_instance = entity_class(**default_instance_data)
                            default_data = entity_instance.model_dump()
                            
                        except Exception as e:
                            # Fallback to simple default structure if model creation fails
                            default_data = {
                                "id": None,
                                "co_id": 1,
                                "created_at": datetime.now().isoformat(),
                                "updated_at": datetime.now().isoformat()
                            }
                    else:
                        # Multiple records entity - create empty array
                        default_data = []
                    
                    # Write the JSON file
                    with open(entity_file, 'w', encoding='utf-8') as f:
                        json.dump(default_data, f, indent=2, default=str, ensure_ascii=False)
                    
                    created_files.append(json_filename)
                    
            except IOError as e:
                raise RuntimeError(f"Could not save company files to {company_folder}: {e}")
            
            return {
                "success": True,
                "company": organization_data,
                "message": f"Successfully created company '{company_name}'",
                "folder_path": str(company_folder)
            }
            
        else:
            # For other entities, we need a company context
            if context.level == ContextLevel.SYS or not context.org_name:
                return {
                    "success": False,
                    "error": "Must be in organization context to create non-company entities"
                }
            
            # Save the entity data using generic storage
            return save_entity_json(entity_type, data, context.org_name, context)
            
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to create {entity_type}: {str(e)}"
        }


def load_entity(entity_type: str, company_name: str, context: Context) -> Optional[Dict[str, Any]]:
    """
    Generic entity loading - works for ANY entity type.
    
    Args:
        entity_type: Entity type name (e.g., 'company', 'brand', 'metadata')
        company_name: Name of the company (for non-company entities)
        context: Execution context
        
    Returns:
        Entity data dictionary or None if not found
    """
    try:
        if entity_type == 'company':
            # Inline company organization loading logic
            company_folder = get_company_folder_path(company_name, context)
            org_file = company_folder / "company.json"
            
            if not org_file.exists():
                return None
            
            try:
                with open(org_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load organization from {org_file}: {e}")
                return None
        else:
            return load_entity_json(entity_type, company_name, context)
    except Exception as e:
        print(f"Warning: Failed to load {entity_type}: {e}")
        return None


def save_entity(entity_type: str, data: Dict[str, Any], company_name: str, context: Context) -> Dict[str, Any]:
    """
    Generic entity saving - works for ANY entity type.
    
    Args:
        entity_type: Entity type name (e.g., 'company', 'brand', 'metadata')
        data: Entity data to save
        company_name: Name of the company (for non-company entities)
        context: Execution context
        
    Returns:
        Result dictionary with success status and details
    """
    try:
        if entity_type == 'company':
            # Inline company update logic
            company_folder = get_company_folder_path(company_name, context)
            if not (company_folder.exists() and company_folder.is_dir()):
                return {
                    "success": False,
                    "error": f"Company '{company_name}' not found"
                }
            
            # Load current organization data
            org_file = company_folder / "company.json"
            if not org_file.exists():
                return {
                    "success": False,
                    "error": f"Could not load organization data for '{company_name}'"
                }
                
            try:
                with open(org_file, 'r', encoding='utf-8') as f:
                    organization_data = json.load(f)
            except (json.JSONDecodeError, IOError):
                return {
                    "success": False,
                    "error": f"Could not load organization data for '{company_name}'"
                }
            
            # Parse incorporation date if being updated
            if 'incorporation' in data and data['incorporation']:
                try:
                    incorporation = datetime.strptime(data['incorporation'], "%Y-%m-%d").date()
                    data['incorporation'] = incorporation.isoformat()
                except (ValueError, TypeError):
                    # Keep original value if parsing fails
                    pass
            
            # Update the data
            organization_data.update(data)
            organization_data['updated_at'] = datetime.now().isoformat()
            
            # Save updated organization data
            try:
                with open(org_file, 'w', encoding='utf-8') as f:
                    json.dump(organization_data, f, indent=2, default=str, ensure_ascii=False)
            except IOError as e:
                return {
                    "success": False,
                    "error": f"Failed to save company data: {str(e)}"
                }
            
            return {
                "success": True,
                "company": organization_data,
                "message": f"Successfully updated company '{company_name}'",
                "folder_path": str(company_folder)
            }
        else:
            return save_entity_json(entity_type, data, company_name, context)
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to save {entity_type}: {str(e)}"
        }


def delete_entity(entity_type: str, entity_name: str, context: Context) -> Dict[str, Any]:
    """
    Generic entity deletion - works for ANY entity type.
    
    Args:
        entity_type: Entity type name (e.g., 'company', 'brand', 'metadata')
        entity_name: Name of the entity to delete
        context: Execution context
        
    Returns:
        Result dictionary with success status and details
    """
    try:
        if entity_type == 'company':
            # Inline company deletion logic
            company_folder = get_company_folder_path(entity_name, context)
            if not (company_folder.exists() and company_folder.is_dir()):
                return {
                    "success": False,
                    "error": f"Company '{entity_name}' not found"
                }
            
            # Load company data before deletion
            org_file = company_folder / "company.json"
            company_data = None
            if org_file.exists():
                try:
                    with open(org_file, 'r', encoding='utf-8') as f:
                        company_data = json.load(f)
                except (json.JSONDecodeError, IOError):
                    pass
            
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
                "message": f"Successfully deleted company '{entity_name}'",
                "remaining_companies": remaining_count,
                "folder_path": str(company_folder)
            }
        else:
            # For other entities, remove the JSON file
            
            json_filename = get_entity_json_filename(entity_type)
            if not json_filename:
                return {
                    "success": False,
                    "error": f"Unknown entity type: {entity_type}"
                }
            
            company_folder = get_company_folder_path(entity_name, context)
            entity_file = company_folder / json_filename
            
            if entity_file.exists():
                os.remove(entity_file)
                return {
                    "success": True,
                    "message": f"Successfully deleted {entity_type} data"
                }
            else:
                return {
                    "success": False,
                    "error": f"Entity '{entity_type}' not found"
                }
                
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to delete {entity_type}: {str(e)}"
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
                    org_file = folder / "company.json"
                    if org_file.exists():
                        try:
                            with open(org_file, 'r', encoding='utf-8') as f:
                                org_data = json.load(f)
                                companies.append(org_data)
                        except (json.JSONDecodeError, IOError):
                            # Skip folders that don't contain valid organization data
                            continue
        
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


def load_all_entities(entity_type: str, company_name: str, context: Context) -> List[Dict[str, Any]]:
    """
    Load ALL records for a dynamic entity type (multiple records per company).
    
    Args:
        entity_type: Entity type name (e.g., 'metadata', 'offering', 'target', 'values')
        company_name: Name of the company 
        context: Execution context
        
    Returns:
        List of entity dictionaries (empty list if none found)
    """
    try:
        # Get the JSON filename for this entity
        json_filename = get_entity_json_filename(entity_type)
        if not json_filename:
            return []
        
        # Get the company folder path
        company_folder = get_company_folder_path(company_name, context)
        entity_file = company_folder / json_filename
        
        if not entity_file.exists():
            return []
        
        try:
            with open(entity_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # With our new dynamic system, files are either:
            # 1. Arrays for dynamic entities (multiple records)
            # 2. Objects for static entities (single record)
            if isinstance(data, list):
                return data  # Dynamic entity - return array as-is
            elif isinstance(data, dict):
                return [data]  # Static entity - wrap in array for consistency  
            else:
                return []  # Invalid format
                
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not load {entity_type} from {entity_file}: {e}")
            return []
            
    except Exception as e:
        print(f"Warning: Failed to load all {entity_type} entities: {e}")
        return []


def update_dynamic_entity_record(entity_type: str, record_id: str, updated_fields: Dict[str, Any], company_name: str, context: Context) -> Dict[str, Any]:
    """
    Update a specific record within a dynamic entity array.
    
    Args:
        entity_type: Entity type name (e.g., 'news', 'offering', 'target')
        record_id: ID of the record to update
        updated_fields: Fields to update in the record
        company_name: Name of the company
        context: Execution context
        
    Returns:
        Result dictionary with success status and details
    """
    try:
        # Load all records for this entity type
        all_records = load_all_entities(entity_type, company_name, context)
        
        if not all_records:
            return {
                "success": False,
                "error": f"No {entity_type} records found for company '{company_name}'"
            }
        
        # Find the record with matching ID
        target_record_index = None
        for i, record in enumerate(all_records):
            if str(record.get('id', '')) == str(record_id):
                target_record_index = i
                break
        
        if target_record_index is None:
            return {
                "success": False,
                "error": f"Record with ID '{record_id}' not found in {entity_type}"
            }
        
        # Update the target record
        target_record = all_records[target_record_index].copy()
        target_record.update(updated_fields)
        target_record['updated_at'] = datetime.now().isoformat()
        
        # Replace the record in the array
        all_records[target_record_index] = target_record
        
        # Get the JSON filename and save the updated array
        json_filename = get_entity_json_filename(entity_type)
        if not json_filename:
            return {
                "success": False,
                "error": f"Unknown entity type: {entity_type}"
            }
        
        company_folder = get_company_folder_path(company_name, context)
        entity_file = company_folder / json_filename
        
        with open(entity_file, 'w', encoding='utf-8') as f:
            json.dump(all_records, f, indent=2, default=str, ensure_ascii=False)
        
        return {
            "success": True,
            "message": f"Successfully updated {entity_type} record (ID: {record_id})",
            "updated_record": target_record,
            "file_path": str(entity_file)
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to update {entity_type} record: {str(e)}"
        }


def save_entity_array(entity_type: str, entity_array: List[Dict[str, Any]], company_name: str, context: Context) -> Dict[str, Any]:
    """
    Save an array of entities for multi-record entity types.
    
    Args:
        entity_type: Entity type name (e.g., 'metadata', 'offering', 'target', 'values')
        entity_array: List of entity records to save
        company_name: Name of the company 
        context: Execution context
        
    Returns:
        Result dictionary with success status and details
    """
    try:
        # Get the JSON filename for this entity
        json_filename = get_entity_json_filename(entity_type)
        if not json_filename:
            return {
                "success": False,
                "error": f"Unknown entity type: {entity_type}"
            }
        
        company_folder = get_company_folder_path(company_name, context)
        entity_file = company_folder / json_filename
        
        # Save the entity array
        with open(entity_file, 'w', encoding='utf-8') as f:
            json.dump(entity_array, f, indent=2, default=str, ensure_ascii=False)
        
        return {
            "success": True,
            "message": f"Successfully saved {len(entity_array)} {entity_type} records",
            "file_path": str(entity_file)
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to save {entity_type} array: {str(e)}"
        }


def find_company_by_name(search_name: str, context: Context) -> Optional[str]:
    """
    Find a company using intelligent matching with tolerance for:
    1. Case insensitivity 
    2. Partial matching (first word)
    3. Exact matching
    
    Args:
        search_name: Name to search for (can be partial or full)
        context: The execution context
        
    Returns:
        The actual company name if found, None otherwise
    """
    data_dir = get_data_directory_path(context)
    if not data_dir.exists():
        return None
    
    search_name_lower = search_name.lower().strip()
    
    # Get all company folders
    company_folders = []
    try:
        for item in data_dir.iterdir():
            if item.is_dir():
                company_folders.append(item.name)
    except (OSError, PermissionError):
        return None
    
    if not company_folders:
        return None
    
    # 1. Try exact match (case insensitive)
    for company_name in company_folders:
        if company_name.lower() == search_name_lower:
            return company_name
    
    # 2. Try partial match on first word (case insensitive)
    search_first_word = search_name_lower.split()[0] if search_name_lower.split() else ""
    if search_first_word:
        for company_name in company_folders:
            company_first_word = company_name.lower().split()[0] if company_name.lower().split() else ""
            if company_first_word == search_first_word:
                return company_name
    
    # 3. No match found
    return None