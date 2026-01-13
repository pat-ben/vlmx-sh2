# File: src/vlmx_sh2/storage/database.py
"""
Data persistence layer.

Handles JSON file-based storage for schemas with context-aware paths.
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..models.context import Context
from vlmx_sh2.enums import Cardinality
from ..models.responses import StorageResult
from .mappings import get_entity_json_filename
from ..utils.context_helpers import is_sys


# ==================== PATH UTILITIES ====================

def get_data_directory_path(context: Context) -> Path:
    """Get the path to the data directory based on context."""
    if is_sys(context):
        base_path = context.sys_path or Path.cwd()
        return base_path / "data"
    else:
        return context.org_db_path.parent.parent if context.org_db_path else Path.cwd() / "data"


def get_company_folder_path(company_name: str, context: Context) -> Path:
    """Get the path to a specific company's folder."""
    return get_data_directory_path(context) / company_name.lower()


# ==================== HELPER FUNCTIONS ====================

def _safe_json_load(file_path: Path) -> Optional[Dict[str, Any]]:
    """Safely load JSON file with error handling."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError, FileNotFoundError):
        return None


def _safe_json_save(file_path: Path, data: Any) -> bool:
    """Safely save JSON data with error handling."""
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str, ensure_ascii=False)
        return True
    except (IOError, OSError):
        return False


def _success_result(message: str, **data) -> Dict[str, Any]:
    """Create success result dictionary."""
    return {"success": True, "message": message, **data}


def _error_result(error: str) -> Dict[str, Any]:
    """Create error result dictionary."""
    return {"success": False, "error": error}


def _wrap_storage_result(func_result: Optional[Dict[str, Any]], entity_type: str, 
                        operation: str) -> StorageResult:
    """Convert function result to StorageResult with standardized error handling."""
    if func_result is None:
        return StorageResult(
            success=False,
            error=f"Failed to {operation} {entity_type}: Unknown error"
        )
    
    if not isinstance(func_result, dict):
        return StorageResult(
            success=False,
            error=f"Invalid storage result format for {entity_type}"
        )
    
    if func_result.get("success"):
        return StorageResult(
            success=True,
            data=func_result,
            message=func_result.get("message", f"Successfully {operation}d {entity_type}")
        )
    else:
        return StorageResult(
            success=False,
            error=func_result.get("error", f"Failed to {operation} {entity_type}"),
            message=func_result.get("message")
        )


# ==================== STORAGE INTERFACE ====================

class StorageInterface:
    """Single point of access for all storage operations."""
    
    @staticmethod
    def create_entity(entity_type: str, data: Dict[str, Any], context: Context) -> StorageResult:
        """Create a new entity with standardized error handling."""
        try:
            result = create_entity(entity_type, data, context)
            return _wrap_storage_result(result, entity_type, "create")
        except Exception as e:
            return StorageResult(success=False, error=f"Exception during create {entity_type}: {str(e)}")
    
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
            return StorageResult(success=True, data=result, message=f"Successfully loaded {entity_type}")
        except Exception as e:
            return StorageResult(success=False, error=f"Exception during load {entity_type}: {str(e)}")
    
    @staticmethod  
    def save_entity(entity_type: str, data: Dict[str, Any], company_name: str, context: Context) -> StorageResult:
        """Save an entity with standardized error handling."""
        try:
            result = save_entity(entity_type, data, company_name, context)
            return _wrap_storage_result(result, entity_type, "save")
        except Exception as e:
            return StorageResult(success=False, error=f"Exception during save {entity_type}: {str(e)}")
    
    @staticmethod
    def delete_entity(entity_type: str, company_name: str, context: Context) -> StorageResult:
        """Delete an entity with standardized error handling."""
        try:
            result = delete_entity(entity_type, company_name, context)
            return _wrap_storage_result(result, entity_type, "delete")
        except Exception as e:
            return StorageResult(success=False, error=f"Exception during delete {entity_type}: {str(e)}")
    
    @staticmethod
    def list_entities(entity_type: str, company_name: str, context: Context) -> StorageResult:
        """List schemas with standardized error handling."""
        try:
            if entity_type == 'company':
                result = list_companies(context)
            else:
                result = load_all_entities(entity_type, company_name, context)
                if isinstance(result, list):
                    result = {"success": True, "data": result, "count": len(result)}
            
            if result is None:
                return StorageResult(success=False, error=f"Failed to list {entity_type}: Unknown error")
            
            if isinstance(result, list):
                return StorageResult(
                    success=True,
                    data={"schemas": result, "count": len(result)},
                    message=f"Successfully listed {len(result)} {entity_type} schemas"
                )
            
            if not isinstance(result, dict):
                return StorageResult(success=False, error=f"Invalid storage result format for list {entity_type}")
                
            if result.get("success", True):
                return StorageResult(
                    success=True,
                    data=result,
                    message=result.get("message", f"Successfully listed {entity_type} schemas")
                )
            else:
                return StorageResult(
                    success=False,
                    error=result.get("error", f"Failed to list {entity_type}"),
                    message=result.get("message")
                )
        except Exception as e:
            return StorageResult(success=False, error=f"Exception during list {entity_type}: {str(e)}")


# ==================== ENTITY OPERATIONS ====================

def load_entity_json(entity_name: str, company_name: str, context: Context) -> Optional[Dict[str, Any]]:
    """Load JSON data for any entity type."""
    json_filename = get_entity_json_filename(entity_name)
    if not json_filename:
        return None
    
    company_folder = get_company_folder_path(company_name, context)
    entity_file = company_folder / json_filename
    return _safe_json_load(entity_file)


def save_entity_json(entity_name: str, entity_data: Dict[str, Any], 
                    company_name: str, context: Context) -> Dict[str, Any]:
    """Save JSON data for any entity type."""
    json_filename = get_entity_json_filename(entity_name)
    if not json_filename:
        return _error_result(f"Unknown entity type: {entity_name}")
    
    company_folder = get_company_folder_path(company_name, context)
    entity_file = company_folder / json_filename
    
    if _safe_json_save(entity_file, entity_data):
        return _success_result(f"Successfully saved {entity_name} data", file_path=str(entity_file))
    else:
        return _error_result(f"Failed to save {entity_name} data")


def entity_exists(entity_name: str, company_name: str, context: Context) -> bool:
    """Check if an entity JSON file exists for a company."""
    json_filename = get_entity_json_filename(entity_name)
    if not json_filename:
        return False
    
    company_folder = get_company_folder_path(company_name, context)
    entity_file = company_folder / json_filename
    return entity_file.exists()


def _create_default_entity_data(entity_class) -> Dict[str, Any]:
    """Create default entity data from entity class."""
    default_data = {
        "id": None,
        "co_id": 1,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    try:
        entity_instance = entity_class(**default_data)
        return entity_instance.model_dump()
    except Exception:
        return default_data


def _create_company_entities(company_folder: Path) -> List[str]:
    """Create all entity files for a new company."""
    from ..models.schemas.company import CompanyDatabase
    
    created_files = []
    
    for entity_class in CompanyDatabase.tables:
        if entity_class.__name__ == 'OrganizationEntity':
            continue
        
        entity_word_id = entity_class.get_entity_word_id()
        json_filename = f"{entity_word_id}.json"
        entity_file = company_folder / json_filename
        
        # Determine data structure based on cardinality
        if hasattr(entity_class, 'cardinality') and entity_class.cardinality == Cardinality.SINGLE:
            default_data = _create_default_entity_data(entity_class)
        else:
            default_data = []
        
        if _safe_json_save(entity_file, default_data):
            created_files.append(json_filename)
    
    return created_files


def create_entity(entity_type: str, data: Dict[str, Any], context: Context) -> Dict[str, Any]:
    """Generic entity creation - works for ANY entity type."""
    try:
        if entity_type == 'company':
            company_name = data.get('name')
            if not company_name:
                return _error_result("Company name is required")
            
            company_folder = get_company_folder_path(company_name, context)
            if company_folder.exists() and company_folder.is_dir():
                return _error_result(f"Company '{company_name}' already exists")
            
            # Parse incorporation date if provided
            if 'incorporation' in data and data['incorporation']:
                try:
                    incorporation = datetime.strptime(data['incorporation'], "%Y-%m-%d").date()
                    data['incorporation'] = incorporation.isoformat()
                except (ValueError, TypeError):
                    pass
            
            # Create organization data with defaults
            from ..models.schemas.company import OrganizationEntity
            
            base_data = {
                "id": None,
                "name": data.get('name'),
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }
            base_data.update(data)
            
            try:
                company_instance = OrganizationEntity(**base_data)
                organization_data = company_instance.model_dump()
            except Exception as e:
                return _error_result(f"Invalid company data: {str(e)}")
            
            # Create company directory and files
            company_folder.mkdir(parents=True, exist_ok=True)
            
            org_file = company_folder / "company.json"
            if not _safe_json_save(org_file, organization_data):
                return _error_result("Failed to save company data")
            
            created_files = ["company.json"] + _create_company_entities(company_folder)
            
            return _success_result(
                f"Successfully created company '{company_name}'",
                company=organization_data,
                folder_path=str(company_folder)
            )
        else:
            # For other schemas, need company context
            if is_sys(context) or not context.org_name:
                return _error_result("Must be in organization context to create non-company schemas")
            
            return save_entity_json(entity_type, data, context.org_name, context)
            
    except Exception as e:
        return _error_result(f"Failed to create {entity_type}: {str(e)}")


def load_entity(entity_type: str, company_name: str, context: Context) -> Optional[Dict[str, Any]]:
    """Generic entity loading - works for ANY entity type."""
    try:
        if entity_type == 'company':
            company_folder = get_company_folder_path(company_name, context)
            org_file = company_folder / "company.json"
            return _safe_json_load(org_file)
        else:
            return load_entity_json(entity_type, company_name, context)
    except Exception:
        return None


def save_entity(entity_type: str, data: Dict[str, Any], company_name: str, context: Context) -> Dict[str, Any]:
    """Generic entity saving - works for ANY entity type."""
    try:
        if entity_type == 'company':
            company_folder = get_company_folder_path(company_name, context)
            if not (company_folder.exists() and company_folder.is_dir()):
                return _error_result(f"Company '{company_name}' not found")
            
            org_file = company_folder / "company.json"
            organization_data = _safe_json_load(org_file)
            if organization_data is None:
                return _error_result(f"Could not load organization data for '{company_name}'")
            
            # Parse incorporation date if being updated
            if 'incorporation' in data and data['incorporation']:
                try:
                    incorporation = datetime.strptime(data['incorporation'], "%Y-%m-%d").date()
                    data['incorporation'] = incorporation.isoformat()
                except (ValueError, TypeError):
                    pass
            
            # Update and save data
            organization_data.update(data)
            organization_data['updated_at'] = datetime.now().isoformat()
            
            if _safe_json_save(org_file, organization_data):
                return _success_result(
                    f"Successfully updated company '{company_name}'",
                    company=organization_data,
                    folder_path=str(company_folder)
                )
            else:
                return _error_result("Failed to save company data")
        else:
            return save_entity_json(entity_type, data, company_name, context)
    except Exception as e:
        return _error_result(f"Failed to save {entity_type}: {str(e)}")


def delete_entity(entity_type: str, entity_name: str, context: Context) -> Dict[str, Any]:
    """Generic entity deletion - works for ANY entity type."""
    try:
        if entity_type == 'company':
            company_folder = get_company_folder_path(entity_name, context)
            if not (company_folder.exists() and company_folder.is_dir()):
                return _error_result(f"Company '{entity_name}' not found")
            
            # Load company data before deletion
            org_file = company_folder / "company.json"
            company_data = _safe_json_load(org_file)
            
            # Remove the entire folder
            shutil.rmtree(company_folder)
            
            # Count remaining companies
            data_dir = get_data_directory_path(context)
            remaining_count = sum(1 for item in data_dir.iterdir() if item.is_dir()) if data_dir.exists() else 0
            
            return _success_result(
                f"Successfully deleted company '{entity_name}'",
                deleted_company=company_data,
                remaining_companies=remaining_count,
                folder_path=str(company_folder)
            )
        else:
            json_filename = get_entity_json_filename(entity_type)
            if not json_filename:
                return _error_result(f"Unknown entity type: {entity_type}")
            
            company_folder = get_company_folder_path(entity_name, context)
            entity_file = company_folder / json_filename
            
            if entity_file.exists():
                os.remove(entity_file)
                return _success_result(f"Successfully deleted {entity_type} data")
            else:
                return _error_result(f"Entity '{entity_type}' not found")
                
    except Exception as e:
        return _error_result(f"Failed to delete {entity_type}: {str(e)}")


# ==================== QUERY OPERATIONS ====================

def list_companies(context: Context) -> Dict[str, Any]:
    """List all companies by scanning folders in the data directory."""
    try:
        data_dir = get_data_directory_path(context)
        companies = []
        
        if data_dir.exists():
            for folder in data_dir.iterdir():
                if folder.is_dir():
                    org_file = folder / "company.json"
                    org_data = _safe_json_load(org_file)
                    if org_data:
                        companies.append(org_data)
        
        return _success_result(
            f"Found {len(companies)} companies",
            companies=companies,
            count=len(companies),
            data_directory=str(data_dir)
        )
    except Exception as e:
        return _error_result(f"Failed to list companies: {str(e)}")


def load_all_entities(entity_type: str, company_name: str, context: Context) -> List[Dict[str, Any]]:
    """Load ALL records for a dynamic entity type."""
    try:
        json_filename = get_entity_json_filename(entity_type)
        if not json_filename:
            return []
        
        company_folder = get_company_folder_path(company_name, context)
        entity_file = company_folder / json_filename
        
        data = _safe_json_load(entity_file)
        if data is None:
            return []
        
        # Return list for arrays, wrap dict in list for consistency
        return data if isinstance(data, list) else [data] if isinstance(data, dict) else []
    except Exception:
        return []


def update_dynamic_entity_record(entity_type: str, record_id: str, updated_fields: Dict[str, Any], 
                                company_name: str, context: Context) -> Dict[str, Any]:
    """Update a specific record within a dynamic entity array."""
    try:
        all_records = load_all_entities(entity_type, company_name, context)
        if not all_records:
            return _error_result(f"No {entity_type} records found for company '{company_name}'")
        
        # Find and update the target record
        for i, record in enumerate(all_records):
            if str(record.get('id', '')) == str(record_id):
                target_record = record.copy()
                target_record.update(updated_fields)
                target_record['updated_at'] = datetime.now().isoformat()
                all_records[i] = target_record
                
                # Save updated array
                json_filename = get_entity_json_filename(entity_type)
                if not json_filename:
                    return _error_result(f"Unknown entity type: {entity_type}")
                
                company_folder = get_company_folder_path(company_name, context)
                entity_file = company_folder / json_filename
                
                if _safe_json_save(entity_file, all_records):
                    return _success_result(
                        f"Successfully updated {entity_type} record (ID: {record_id})",
                        updated_record=target_record,
                        file_path=str(entity_file)
                    )
                else:
                    return _error_result(f"Failed to save {entity_type} record")
        
        return _error_result(f"Record with ID '{record_id}' not found in {entity_type}")
    except Exception as e:
        return _error_result(f"Failed to update {entity_type} record: {str(e)}")


def save_entity_array(entity_type: str, entity_array: List[Dict[str, Any]], 
                     company_name: str, context: Context) -> Dict[str, Any]:
    """Save an array of schemas for multi-record entity types."""
    try:
        json_filename = get_entity_json_filename(entity_type)
        if not json_filename:
            return _error_result(f"Unknown entity type: {entity_type}")
        
        company_folder = get_company_folder_path(company_name, context)
        entity_file = company_folder / json_filename
        
        if _safe_json_save(entity_file, entity_array):
            return _success_result(
                f"Successfully saved {len(entity_array)} {entity_type} records",
                file_path=str(entity_file)
            )
        else:
            return _error_result(f"Failed to save {entity_type} array")
    except Exception as e:
        return _error_result(f"Failed to save {entity_type} array: {str(e)}")


def find_company_by_name(search_name: str, context: Context) -> Optional[str]:
    """Find a company using intelligent matching."""
    data_dir = get_data_directory_path(context)
    if not data_dir.exists():
        return None
    
    search_name_lower = search_name.lower().strip()
    
    # Get all company folders
    try:
        company_folders = [item.name for item in data_dir.iterdir() if item.is_dir()]
    except (OSError, PermissionError):
        return None
    
    if not company_folders:
        return None
    
    # Try exact match (case insensitive)
    for company_name in company_folders:
        if company_name.lower() == search_name_lower:
            return company_name
    
    # Try partial match on first word (case insensitive)
    search_first_word = search_name_lower.split()[0] if search_name_lower.split() else ""
    if search_first_word:
        for company_name in company_folders:
            company_first_word = company_name.lower().split()[0] if company_name.lower().split() else ""
            if company_first_word == search_first_word:
                return company_name
    
    return None