# File: src/vlmx_sh2/storage/database.py
"""
Data persistence layer — public facade.

StorageInterface delegates every call to the active backend (JSON by
default).  Call ``set_backend(StorageBackendType.SQLITE)`` to switch.

The import path ``from ..storage.database import StorageInterface`` is
the stable public API that handler modules depend on.
"""

# Public API — only these should be imported by consumers
__all__ = ["StorageInterface", "get_company_folder_path", "find_company_candidates"]

from typing import Any, Dict, List

from ..core.models.context import Context
from ..core.models.responses import StorageResult
from .backend import StorageBackend, StorageBackendType
from .json_backend import JsonBackend
from .paths import get_company_folder_path, get_data_directory_path  # noqa: F401 — re-exported
from .result_helpers import success_result


# ==================== ACTIVE BACKEND ====================

_backend: StorageBackend = JsonBackend()


def set_backend(backend_type: StorageBackendType) -> None:
    """Switch the active storage backend.

    Importing and instantiating the SQLite backend is deferred so that
    SQLModel is only required when actually selected.
    """
    global _backend
    if backend_type == StorageBackendType.JSON:
        _backend = JsonBackend()
    elif backend_type == StorageBackendType.SQLITE:
        from .sqlite_backend import SqliteBackend
        _backend = SqliteBackend()
    else:
        raise ValueError(f"Unknown backend type: {backend_type!r}")


def get_backend() -> StorageBackend:
    """Return the currently active backend instance."""
    return _backend


# ==================== RESULT WRAPPER ====================

def _wrap_storage_result(result: Dict[str, Any], entity_type: str,
                        operation: str) -> StorageResult:
    """Convert a standardized backend dict to a ``StorageResult``.

    Both backends use ``success_result()`` / ``error_result()`` from
    ``result_helpers``, so we can rely on the dict always having a
    ``"success"`` key plus either ``"message"`` (on success) or
    ``"error"`` (on failure).
    """
    if result["success"]:
        return StorageResult(
            success=True,
            data=result,
            message=result["message"],
        )
    return StorageResult(
        success=False,
        error=result["error"],
    )


# ==================== CONVENIENCE FREE FUNCTIONS ====================
# Re-exported so existing ``from ..storage.database import …`` lines
# in handler modules keep working without modification.

def find_company_candidates(search_name: str, context: Context) -> List[str]:
    """Find all companies that partially match the search name."""
    return _backend.find_company_candidates(search_name, context)


# ==================== STORAGE INTERFACE ====================

class StorageInterface:
    """Single point of access for all storage operations.

    Every method delegates to ``_backend`` (the active StorageBackend)
    and wraps the raw dict result into a ``StorageResult``.
    """

    @staticmethod
    def create_entity(entity_type: str, data: Dict[str, Any], context: Context) -> StorageResult:
        """Create a new entity with standardized error handling."""
        try:
            result = _backend.create_entity(entity_type, data, context)
            return _wrap_storage_result(result, entity_type, "create")
        except Exception as e:
            return StorageResult(success=False, error=f"Exception during create {entity_type}: {str(e)}")

    @staticmethod
    def load_entity(entity_type: str, company_name: str, context: Context) -> StorageResult:
        """Load an entity with standardized error handling."""
        try:
            result = _backend.load_entity(entity_type, company_name, context)
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
            result = _backend.save_entity(entity_type, data, company_name, context)
            return _wrap_storage_result(result, entity_type, "save")
        except Exception as e:
            return StorageResult(success=False, error=f"Exception during save {entity_type}: {str(e)}")

    @staticmethod
    def delete_entity(entity_type: str, company_name: str, context: Context) -> StorageResult:
        """Delete an entity with standardized error handling."""
        try:
            result = _backend.delete_entity(entity_type, company_name, context)
            return _wrap_storage_result(result, entity_type, "delete")
        except Exception as e:
            return StorageResult(success=False, error=f"Exception during delete {entity_type}: {str(e)}")

    @staticmethod
    def list_entities(entity_type: str, company_name: str, context: Context) -> StorageResult:
        """List entities with standardized error handling."""
        try:
            if entity_type == 'company':
                result = _backend.list_companies(context)
            else:
                records = _backend.load_all_entities(entity_type, company_name, context)
                result = success_result(
                    f"Found {len(records)} {entity_type} records",
                    data=records,
                    count=len(records),
                )
            return _wrap_storage_result(result, entity_type, "list")
        except Exception as e:
            return StorageResult(success=False, error=f"Exception during list {entity_type}: {str(e)}")

    @staticmethod
    def entity_exists(entity_type: str, company_name: str, context: Context) -> bool:
        """Check if an entity exists with standardized error handling."""
        try:
            return _backend.entity_exists(entity_type, company_name, context)
        except Exception:
            return False

    @staticmethod
    def load_all_entities(entity_type: str, company_name: str, context: Context) -> StorageResult:
        """Load all entities with standardized error handling."""
        try:
            records = _backend.load_all_entities(entity_type, company_name, context)
            return StorageResult(
                success=True,
                data=records,
                message=f"Successfully loaded {len(records)} {entity_type} records"
            )
        except Exception as e:
            return StorageResult(success=False, error=f"Exception during load all {entity_type}: {str(e)}")

    @staticmethod
    def find_company_by_name(search_name: str, context: Context) -> StorageResult:
        """Find company by name with standardized error handling."""
        try:
            company_name = _backend.find_company_by_name(search_name, context)
            if company_name is None:
                # Check if there are partial matches for disambiguation
                candidates = _backend.find_company_candidates(search_name, context)
                if candidates:
                    candidates_str = ', '.join(f"'{name}'" for name in candidates)
                    return StorageResult(
                        success=False,
                        error=f"Company '{search_name}' not found or ambiguous",
                        data={"suggestions": candidates, "message": f"Multiple matches found: {candidates_str}"}
                    )
                else:
                    return StorageResult(
                        success=False,
                        error=f"Company '{search_name}' not found"
                    )

            # Load company data via the active backend
            org_data = _backend.load_entity('company', company_name, context)
            company_folder = get_company_folder_path(company_name, context)

            # Determine db_path based on active backend
            if isinstance(_backend, JsonBackend):
                db_path = str(company_folder / "company.json")
            else:
                from .engine import get_company_db_path
                db_path = str(get_company_db_path(company_name, context))

            company_data = {
                "name": company_name,
                "id": org_data.get("id") if org_data else None,
                "db_path": db_path,
            }

            return StorageResult(
                success=True,
                data=company_data,
                message=f"Found company: {company_name}"
            )
        except Exception as e:
            return StorageResult(success=False, error=f"Exception during find company: {str(e)}")
