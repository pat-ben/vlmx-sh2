# File: src/vlmx_sh2/storage/json_backend.py
"""
JSON file-based storage backend.

Implements the StorageBackend protocol using one JSON file per entity
and one folder per company.  This is the original storage strategy
and remains fully functional alongside the newer SQLite backend.
"""

import json
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

from vlmx_sh2.core.enums import Cardinality
from vlmx_sh2.core.models.context import Context
from vlmx_sh2.core.registry import (
    ROOT_ENTITY_ID,
    get_entities_for_schema,
    get_root_entity,
    get_root_json_filename,
    get_storage_mapping,
    is_schema_id,
)
from vlmx_sh2.core.utils.context.helpers import is_sys
from vlmx_sh2.core.utils.entity_defaults import create_default_entity_data_simple
from vlmx_sh2.db.mappings import get_entity_json_filename
from vlmx_sh2.db.paths import get_company_folder_path, get_data_directory_path
from vlmx_sh2.db.result_helpers import error_result, success_result

# ==================== PRIVATE HELPERS ====================

_create_default_entity_data = create_default_entity_data_simple


def _safe_json_load(file_path: Path) -> Optional[Dict[str, Any]]:
    """Safely load JSON file with error handling."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError, FileNotFoundError):
        return None


def _safe_json_save(file_path: Path, data: Any) -> bool:
    """Safely save JSON data with atomic write and error handling."""
    temp_path = None
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write to temporary file first for atomic operation
        temp_path = file_path.with_suffix(".json.tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str, ensure_ascii=False)

        # Atomically replace the target file
        os.replace(temp_path, file_path)
        return True
    except (IOError, OSError, TypeError, ValueError, Exception):
        # Clean up temp file if it was created but operation failed
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        return False


def _create_schema_entities(company_folder: Path, schema_id: str) -> List[str]:
    """Create all entity files for a new organization using registry config."""
    created_files = []

    for entity_class in get_entities_for_schema(schema_id):
        entity_id = entity_class.get_entity_word_id()
        if entity_id == ROOT_ENTITY_ID:
            continue

        mapping = get_storage_mapping(entity_id)
        if mapping is None:
            continue

        entity_file = company_folder / mapping.json_filename

        # Determine data structure based on cardinality
        if (
            hasattr(entity_class, "cardinality")
            and entity_class.cardinality == Cardinality.SINGLE
        ):
            default_data = _create_default_entity_data(entity_class)
        else:
            default_data = []

        if _safe_json_save(entity_file, default_data):
            created_files.append(mapping.json_filename)

    return created_files


# ==================== JSON BACKEND ====================


class JsonBackend:
    """JSON file-based storage backend.

    Satisfies the StorageBackend protocol via structural subtyping —
    no inheritance required.
    """

    # -- CRUD ----------------------------------------------------------

    def create_entity(
        self,
        entity_type: str,
        data: Dict[str, Any],
        context: Context,
    ) -> Dict[str, Any]:
        """Generic entity creation — works for ANY entity type."""
        try:
            # Schema types have special creation flow (folder + entity files)
            if is_schema_id(entity_type):
                company_name = data.get("name")
                if not company_name:
                    return error_result("Organization name is required")

                company_folder = get_company_folder_path(company_name, context)
                if company_folder.exists() and company_folder.is_dir():
                    return error_result(f"Organization '{company_name}' already exists")

                # Parse incorporation date if provided
                if "incorporation" in data and data["incorporation"]:
                    try:
                        incorporation = datetime.strptime(
                            data["incorporation"], "%Y-%m-%d"
                        ).date()
                        data["incorporation"] = incorporation.isoformat()
                    except (ValueError, TypeError):
                        pass

                organization_entity_class = get_root_entity()

                # Create organization data with defaults
                base_data = {
                    "id": None,
                    "name": data.get("name"),
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                }
                base_data.update(data)

                try:
                    company_instance = organization_entity_class(**base_data)
                    organization_data = company_instance.model_dump()
                except Exception as e:
                    return error_result(f"Invalid organization data: {str(e)}")

                # Create organization directory and files
                company_folder.mkdir(parents=True, exist_ok=True)

                org_file = company_folder / get_root_json_filename()
                if not _safe_json_save(org_file, organization_data):
                    return error_result("Failed to save organization data")

                _create_schema_entities(company_folder, entity_type)

                # Register org in system/org/registry.toml.
                import importlib.util as _ilu

                _spec = _ilu.spec_from_file_location(
                    "org_registry",
                    Path(__file__).resolve().parents[4] / "system" / "org" / "org_registry.py",
                )
                _mod = _ilu.module_from_spec(_spec)
                _spec.loader.exec_module(_mod)
                write_org_to_registry = _mod.write_org_to_registry

                if not write_org_to_registry(
                    {
                        "name": organization_data.get("name"),
                        "legal": organization_data.get("legal"),
                        "currency": organization_data.get("currency"),
                    }
                ):
                    logger.warning(
                        "Failed to write org '%s' to registry — org folder was created successfully",
                        company_name,
                    )

                return success_result(
                    f"Successfully created organization '{company_name}'",
                    company=organization_data,
                    folder_path=str(company_folder),
                )
            else:
                # For other entity types, need organization context
                if is_sys(context) or not context.org_name:
                    return error_result(
                        "Must be in organization context to create non-schema entities"
                    )

                return self._save_entity_json(
                    entity_type, data, context.org_name, context
                )

        except Exception as e:
            return error_result(f"Failed to create {entity_type}: {str(e)}")

    def load_entity(
        self,
        entity_type: str,
        company_name: str,
        context: Context,
    ) -> Optional[Dict[str, Any]]:
        """Generic entity loading — works for ANY entity type."""
        try:
            if is_schema_id(entity_type):
                company_folder = get_company_folder_path(company_name, context)
                org_file = company_folder / get_root_json_filename()
                return _safe_json_load(org_file)
            else:
                return self._load_entity_json(entity_type, company_name, context)
        except Exception:
            return None

    def save_entity(
        self,
        entity_type: str,
        data: Dict[str, Any],
        company_name: str,
        context: Context,
    ) -> Dict[str, Any]:
        """Generic entity saving — works for ANY entity type."""
        try:
            if is_schema_id(entity_type):
                company_folder = get_company_folder_path(company_name, context)
                if not (company_folder.exists() and company_folder.is_dir()):
                    return error_result(f"Organization '{company_name}' not found")

                org_file = company_folder / get_root_json_filename()
                organization_data = _safe_json_load(org_file)
                if organization_data is None:
                    return error_result(
                        f"Could not load organization data for '{company_name}'"
                    )

                # Parse incorporation date if being updated
                if "incorporation" in data and data["incorporation"]:
                    try:
                        incorporation = datetime.strptime(
                            data["incorporation"], "%Y-%m-%d"
                        ).date()
                        data["incorporation"] = incorporation.isoformat()
                    except (ValueError, TypeError):
                        pass

                # Update and save data
                organization_data.update(data)
                organization_data["updated_at"] = datetime.now().isoformat()

                if _safe_json_save(org_file, organization_data):
                    return success_result(
                        f"Successfully updated organization '{company_name}'",
                        company=organization_data,
                        folder_path=str(company_folder),
                    )
                else:
                    return error_result("Failed to save organization data")
            else:
                return self._save_entity_json(entity_type, data, company_name, context)
        except Exception as e:
            return error_result(f"Failed to save {entity_type}: {str(e)}")

    def delete_entity(
        self,
        entity_type: str,
        entity_name: str,
        context: Context,
    ) -> Dict[str, Any]:
        """Generic entity deletion — works for ANY entity type."""
        try:
            if is_schema_id(entity_type):
                company_folder = get_company_folder_path(entity_name, context)
                if not (company_folder.exists() and company_folder.is_dir()):
                    return error_result(f"Organization '{entity_name}' not found")

                # Load organization data before deletion
                org_file = company_folder / get_root_json_filename()
                company_data = _safe_json_load(org_file)

                # Remove the entire folder
                shutil.rmtree(company_folder)

                # Count remaining companies
                data_dir = get_data_directory_path(context)
                remaining_count = (
                    sum(1 for item in data_dir.iterdir() if item.is_dir())
                    if data_dir.exists()
                    else 0
                )

                return success_result(
                    f"Successfully deleted company '{entity_name}'",
                    deleted_company=company_data,
                    remaining_companies=remaining_count,
                    folder_path=str(company_folder),
                )
            else:
                json_filename = get_entity_json_filename(entity_type)
                if not json_filename:
                    return error_result(f"Unknown entity type: {entity_type}")

                company_folder = get_company_folder_path(entity_name, context)
                entity_file = company_folder / json_filename

                if entity_file.exists():
                    os.remove(entity_file)
                    return success_result(f"Successfully deleted {entity_type} data")
                else:
                    return error_result(f"Entity '{entity_type}' not found")

        except Exception as e:
            return error_result(f"Failed to delete {entity_type}: {str(e)}")

    # -- Bulk / query operations ---------------------------------------

    def load_all_entities(
        self,
        entity_type: str,
        company_name: str,
        context: Context,
    ) -> List[Dict[str, Any]]:
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
            return (
                data
                if isinstance(data, list)
                else [data]
                if isinstance(data, dict)
                else []
            )
        except Exception:
            return []

    def save_entity_array(
        self,
        entity_type: str,
        entity_array: List[Dict[str, Any]],
        company_name: str,
        context: Context,
    ) -> Dict[str, Any]:
        """Save an array of schemas for multi-record entity types."""
        try:
            json_filename = get_entity_json_filename(entity_type)
            if not json_filename:
                return error_result(f"Unknown entity type: {entity_type}")

            company_folder = get_company_folder_path(company_name, context)
            entity_file = company_folder / json_filename

            if _safe_json_save(entity_file, entity_array):
                return success_result(
                    f"Successfully saved {len(entity_array)} {entity_type} records",
                    file_path=str(entity_file),
                )
            else:
                return error_result(f"Failed to save {entity_type} array")
        except Exception as e:
            return error_result(f"Failed to save {entity_type} array: {str(e)}")

    def update_dynamic_entity_record(
        self,
        entity_type: str,
        record_id: str,
        updated_fields: Dict[str, Any],
        company_name: str,
        context: Context,
    ) -> Dict[str, Any]:
        """Update a specific record within a dynamic entity array."""
        try:
            all_records = self.load_all_entities(entity_type, company_name, context)
            if not all_records:
                return error_result(
                    f"No {entity_type} records found for company '{company_name}'"
                )

            # Find and update the target record
            for i, record in enumerate(all_records):
                if str(record.get("id", "")) == str(record_id):
                    target_record = record.copy()
                    target_record.update(updated_fields)
                    target_record["updated_at"] = datetime.now().isoformat()
                    all_records[i] = target_record

                    # Save updated array
                    json_filename = get_entity_json_filename(entity_type)
                    if not json_filename:
                        return error_result(f"Unknown entity type: {entity_type}")

                    company_folder = get_company_folder_path(company_name, context)
                    entity_file = company_folder / json_filename

                    if _safe_json_save(entity_file, all_records):
                        return success_result(
                            f"Successfully updated {entity_type} record (ID: {record_id})",
                            updated_record=target_record,
                            file_path=str(entity_file),
                        )
                    else:
                        return error_result(f"Failed to save {entity_type} record")

            return error_result(
                f"Record with ID '{record_id}' not found in {entity_type}"
            )
        except Exception as e:
            return error_result(f"Failed to update {entity_type} record: {str(e)}")

    # -- Company listing / search --------------------------------------

    def list_organizations(
        self,
        context: Context,
    ) -> Dict[str, Any]:
        """List all organizations by scanning folders in the data directory."""
        try:
            data_dir = get_data_directory_path(context)
            companies = []

            if data_dir.exists():
                for folder in data_dir.iterdir():
                    if folder.is_dir():
                        org_file = folder / get_root_json_filename()
                        org_data = _safe_json_load(org_file)
                        if org_data:
                            companies.append(org_data)

            return success_result(
                f"Found {len(companies)} companies",
                companies=companies,
                count=len(companies),
                data_directory=str(data_dir),
            )
        except Exception as e:
            return error_result(f"Failed to list companies: {str(e)}")

    def entity_exists(
        self,
        entity_name: str,
        company_name: str,
        context: Context,
    ) -> bool:
        """Check if an entity JSON file exists for a company."""
        json_filename = get_entity_json_filename(entity_name)
        if not json_filename:
            return False

        company_folder = get_company_folder_path(company_name, context)
        entity_file = company_folder / json_filename
        return entity_file.exists()

    def find_organization_by_name(
        self,
        search_name: str,
        context: Context,
    ) -> Optional[str]:
        """Find an organization using intelligent matching."""
        data_dir = get_data_directory_path(context)
        if not data_dir.exists():
            return None

        search_name_lower = search_name.lower().strip()

        # Get all company folders
        try:
            company_folders = [
                item.name for item in data_dir.iterdir() if item.is_dir()
            ]
        except (OSError, PermissionError):
            return None

        if not company_folders:
            return None

        # Try exact match (case insensitive)
        for company_name in company_folders:
            if company_name.lower() == search_name_lower:
                return company_name

        # Try partial match on first word (case insensitive)
        search_first_word = (
            search_name_lower.split()[0] if search_name_lower.split() else ""
        )
        if search_first_word:
            partial_matches = []
            for company_name in company_folders:
                company_first_word = (
                    company_name.lower().split()[0]
                    if company_name.lower().split()
                    else ""
                )
                if company_first_word == search_first_word:
                    partial_matches.append(company_name)

            # Only return a match if there's exactly one
            if len(partial_matches) == 1:
                return partial_matches[0]
            # If multiple matches, return None to let caller handle disambiguation

        return None

    def find_organization_candidates(
        self,
        search_name: str,
        context: Context,
    ) -> List[str]:
        """Find all organizations that partially match the search name."""
        data_dir = get_data_directory_path(context)
        if not data_dir.exists():
            return []

        search_name_lower = search_name.lower().strip()

        # Get all company folders
        try:
            company_folders = [
                item.name for item in data_dir.iterdir() if item.is_dir()
            ]
        except (OSError, PermissionError):
            return []

        if not company_folders:
            return []

        # Find partial matches on first word (case insensitive)
        search_first_word = (
            search_name_lower.split()[0] if search_name_lower.split() else ""
        )
        if not search_first_word:
            return []

        partial_matches = []
        for company_name in company_folders:
            company_first_word = (
                company_name.lower().split()[0] if company_name.lower().split() else ""
            )
            if company_first_word == search_first_word:
                partial_matches.append(company_name)

        return partial_matches

    # -- Internal helpers (not part of the protocol) -------------------

    def _load_entity_json(
        self,
        entity_name: str,
        company_name: str,
        context: Context,
    ) -> Optional[Dict[str, Any]]:
        """Load JSON data for any entity type."""
        json_filename = get_entity_json_filename(entity_name)
        if not json_filename:
            return None

        company_folder = get_company_folder_path(company_name, context)
        entity_file = company_folder / json_filename
        return _safe_json_load(entity_file)

    def _save_entity_json(
        self,
        entity_name: str,
        entity_data: Dict[str, Any],
        company_name: str,
        context: Context,
    ) -> Dict[str, Any]:
        """Save JSON data for any entity type."""
        json_filename = get_entity_json_filename(entity_name)
        if not json_filename:
            return error_result(f"Unknown entity type: {entity_name}")

        company_folder = get_company_folder_path(company_name, context)
        entity_file = company_folder / json_filename

        if _safe_json_save(entity_file, entity_data):
            return success_result(
                f"Successfully saved {entity_name} data", file_path=str(entity_file)
            )
        else:
            return error_result(f"Failed to save {entity_name} data")
