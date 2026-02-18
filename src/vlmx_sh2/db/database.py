from __future__ import annotations

from typing import Any, cast

from ..core.models.context import Context
from ..core.models.responses import StorageResult
from ..core.registry import ROOT_ENTITY_ID, get_root_json_filename, is_schema_id
from .backends.json import JsonBackend
from .base import StorageBackend, StorageBackendType
from .paths import (  # noqa: F401 — re-exported
    get_company_folder_path,
    get_data_directory_path,
)
from .result_helpers import success_result

# File: src/vlmx_sh2/storage/database.py
"""
Data persistence layer — public facade.

StorageInterface delegates every call to the active backend (JSON by
default).  Call ``set_backend(StorageBackendType.SQLITE)`` to switch.

The import path ``from ..db.database import StorageInterface`` is
the stable public API that handler modules depend on.
"""

# Public API — only these should be imported by consumers
__all__ = [
    "StorageInterface",
    "get_company_folder_path",
    "find_organization_candidates",
]

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
        return
    if backend_type == StorageBackendType.SQLITE:
        from .backends.sql import SqliteBackend

        _backend = SqliteBackend()
        return

    raise ValueError(f"Unknown backend type: {backend_type!r}")


def get_backend() -> StorageBackend:
    """Return the currently active backend instance."""
    return _backend


# ==================== RESULT WRAPPER ====================


class BackendResult(dict[str, Any]):
    """
    Best-effort typing for backend result dicts.

    Backends are currently dynamically typed; this alias exists to prevent
    cascaded "unknown/Any" warnings in consumers without enforcing a strict
    TypedDict contract here.
    """


class StorageRecord(dict[str, Any]):
    """
    Best-effort typing for persisted records.

    Records are dict-shaped and backend-dependent; keep this broad and let
    higher layers narrow/validate as needed.
    """


def _wrap_storage_result(
    result: BackendResult, entity_type: str, operation: str
) -> StorageResult:
    """Convert a standardized backend dict to a ``StorageResult``."""
    if bool(result.get("success")):
        return StorageResult(
            success=True,
            data=result,
            message=cast(str, result.get("message", "")),
        )
    return StorageResult(
        success=False,
        error=cast(str, result.get("error", "Unknown error")),
    )


# ==================== CONVENIENCE FREE FUNCTIONS ====================
# Re-exported so existing ``from ..db.database import …`` lines
# in handler modules keep working without modification.


def find_organization_candidates(search_name: str, context: Context) -> list[str]:
    """Find all organizations that partially match the search name."""
    return _backend.find_organization_candidates(search_name, context)


# ==================== STORAGE INTERFACE ====================


class StorageInterface:
    """Single point of access for all storage operations.

    Every method delegates to ``_backend`` (the active StorageBackend)
    and wraps the raw dict result into a ``StorageResult``.
    """

    @staticmethod
    def create_entity(
        entity_type: str, data: StorageRecord, context: Context
    ) -> StorageResult:
        """Create a new entity with standardized error handling."""
        try:
            result = _backend.create_entity(entity_type, data, context)
            return _wrap_storage_result(
                cast(BackendResult, result), entity_type, "create"
            )
        except Exception as e:
            return StorageResult(
                success=False, error=f"Exception during create {entity_type}: {str(e)}"
            )

    @staticmethod
    def load_entity(
        entity_type: str, company_name: str, context: Context
    ) -> StorageResult:
        """Load an entity with standardized error handling."""
        try:
            result = _backend.load_entity(entity_type, company_name, context)
            if result is None:
                return StorageResult(
                    success=False,
                    error=f"{entity_type.title()} not found for company '{company_name}'",
                )
            return StorageResult(
                success=True,
                data=result,
                message=f"Successfully loaded {entity_type}",
            )
        except Exception as e:
            return StorageResult(
                success=False, error=f"Exception during load {entity_type}: {str(e)}"
            )

    @staticmethod
    def save_entity(
        entity_type: str, data: StorageRecord, company_name: str, context: Context
    ) -> StorageResult:
        """Save an entity with standardized error handling."""
        try:
            result = _backend.save_entity(entity_type, data, company_name, context)
            return _wrap_storage_result(
                cast(BackendResult, result), entity_type, "save"
            )
        except Exception as e:
            return StorageResult(
                success=False, error=f"Exception during save {entity_type}: {str(e)}"
            )

    @staticmethod
    def delete_entity(
        entity_type: str, company_name: str, context: Context
    ) -> StorageResult:
        """Delete an entity with standardized error handling."""
        try:
            result = _backend.delete_entity(entity_type, company_name, context)
            return _wrap_storage_result(
                cast(BackendResult, result), entity_type, "delete"
            )
        except Exception as e:
            return StorageResult(
                success=False, error=f"Exception during delete {entity_type}: {str(e)}"
            )

    @staticmethod
    def list_entities(
        entity_type: str, company_name: str, context: Context
    ) -> StorageResult:
        """List entities with standardized error handling."""
        try:
            if is_schema_id(entity_type):
                result = _backend.list_organizations(context)
            else:
                records = _backend.load_all_entities(entity_type, company_name, context)
                result = success_result(
                    f"Found {len(records)} {entity_type} records",
                    data=records,
                    count=len(records),
                )
            return _wrap_storage_result(
                cast(BackendResult, result), entity_type, "list"
            )
        except Exception as e:
            return StorageResult(
                success=False, error=f"Exception during list {entity_type}: {str(e)}"
            )

    @staticmethod
    def entity_exists(entity_type: str, company_name: str, context: Context) -> bool:
        """Check if an entity exists with standardized error handling."""
        try:
            return _backend.entity_exists(entity_type, company_name, context)
        except Exception:
            return False

    @staticmethod
    def load_all_entities(
        entity_type: str, company_name: str, context: Context
    ) -> StorageResult:
        """Load all entities with standardized error handling."""
        try:
            records = _backend.load_all_entities(entity_type, company_name, context)
            return StorageResult(
                success=True,
                data=records,
                message=f"Successfully loaded {len(records)} {entity_type} records",
            )
        except Exception as e:
            return StorageResult(
                success=False,
                error=f"Exception during load all {entity_type}: {str(e)}",
            )

    @staticmethod
    def find_organization_by_name(search_name: str, context: Context) -> StorageResult:
        """Find organization by name with standardized error handling."""
        try:
            company_name = _backend.find_organization_by_name(search_name, context)
            if company_name is None:
                # Check if there are partial matches for disambiguation
                candidates = _backend.find_organization_candidates(search_name, context)
                if candidates:
                    candidates_str = ", ".join(f"'{name}'" for name in candidates)
                    return StorageResult(
                        success=False,
                        error=f"Company '{search_name}' not found or ambiguous",
                        data={
                            "suggestions": candidates,
                            "message": f"Multiple matches found: {candidates_str}",
                        },
                    )
                else:
                    return StorageResult(
                        success=False, error=f"Company '{search_name}' not found"
                    )

            # Load organization data via the active backend
            org_data = _backend.load_entity(ROOT_ENTITY_ID, company_name, context)
            company_folder = get_company_folder_path(company_name, context)

            # Determine db_path based on active backend
            if isinstance(_backend, JsonBackend):
                db_path = str(company_folder / get_root_json_filename())
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
                message=f"Found company: {company_name}",
            )
        except Exception as e:
            return StorageResult(
                success=False, error=f"Exception during find company: {str(e)}"
            )
