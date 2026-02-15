# File: src/vlmx_sh2/storage/backend.py
"""
Storage backend contract.

Defines the StorageBackend Protocol that both JSON and SQLite backends
must implement, plus a StorageBackendType enum for configuration.

All backend methods return plain dicts (with shape:
{"success": bool, "error": str?, "message": str?, ...data}) or primitives.
The StorageInterface layer is responsible for wrapping these into StorageResult.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, runtime_checkable

from typing import Protocol

from ..core.models.context import Context


class StorageBackendType(str, Enum):
    """Supported storage backend types."""
    JSON = "json"
    SQLITE = "sqlite"


@runtime_checkable
class StorageBackend(Protocol):
    """Contract that every storage backend must satisfy.

    Backends are structural subtypes — they don't need to inherit from this
    class, they just need to implement every method with a matching signature.
    """

    def create_entity(
        self,
        entity_type: str,
        data: Dict[str, Any],
        context: Context,
    ) -> Dict[str, Any]: ...

    def load_entity(
        self,
        entity_type: str,
        company_name: str,
        context: Context,
    ) -> Optional[Dict[str, Any]]: ...

    def save_entity(
        self,
        entity_type: str,
        data: Dict[str, Any],
        company_name: str,
        context: Context,
    ) -> Dict[str, Any]: ...

    def delete_entity(
        self,
        entity_type: str,
        entity_name: str,
        context: Context,
    ) -> Dict[str, Any]: ...

    def load_all_entities(
        self,
        entity_type: str,
        company_name: str,
        context: Context,
    ) -> List[Dict[str, Any]]: ...

    def save_entity_array(
        self,
        entity_type: str,
        entity_array: List[Dict[str, Any]],
        company_name: str,
        context: Context,
    ) -> Dict[str, Any]: ...

    def update_dynamic_entity_record(
        self,
        entity_type: str,
        record_id: str,
        updated_fields: Dict[str, Any],
        company_name: str,
        context: Context,
    ) -> Dict[str, Any]: ...

    def list_companies(
        self,
        context: Context,
    ) -> Dict[str, Any]: ...

    def entity_exists(
        self,
        entity_name: str,
        company_name: str,
        context: Context,
    ) -> bool: ...

    def find_company_by_name(
        self,
        search_name: str,
        context: Context,
    ) -> Optional[str]: ...

    def find_company_candidates(
        self,
        search_name: str,
        context: Context,
    ) -> List[str]: ...
