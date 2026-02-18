from __future__ import annotations

from typing import Any, cast

from ..core.models.context import Context
from ..core.models.responses import StorageResult
from ..core.registry import ROOT_ENTITY_ID, get_root_json_filename, is_schema_id
from .backends.json import JsonBackend
from .base import StorageBackend, StorageBackendType
from ..core.schemas.company import OrganizationEntity
from ..core.models.ui import EntityDisplay, FieldDisplay, ModuleDisplay, OrgDataDisplay, OrgSnapshot
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

# Deterministic module rendering order for the right pane.
_MODULE_ORDER = ["core", "branding", "market"]


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

    @staticmethod
    def get_entity_records(
        entity_type: str, org_name: str, context: Context
    ) -> list[dict]:
        """Load all records for an entity type within an organization."""
        try:
            from ..db.database import StorageInterface
    
            result = StorageInterface.load_all_entities(entity_type, org_name, context)
            if result.success and result.data is not None:
                return result.data
            return []
        except Exception:
            return []
    
    @staticmethod
    def get_org_snapshot(org_name: str, context: Context) -> OrgSnapshot | None:
        """
        Return header data for the selected organization.
    
        Loads OrganizationEntity and MetadataEntity. Returns None only when
        the org itself cannot be loaded. Metadata failures degrade gracefully
        (stage/sector remain None).
        """
        try:
            from ..db.database import StorageInterface
            from ..core.schemas.company import MetadataEntity
    
            org_result = StorageInterface.load_entity("organization", org_name, context)
            if not org_result.success or not org_result.data:
                return None
            org = OrganizationEntity(**org_result.data)
        except Exception:
            return None
    
        stage: str | None = None
        sector: str | None = None
        try:
            from ..db.database import StorageInterface
            from ..core.schemas.company import MetadataEntity
    
            meta_result = StorageInterface.load_entity("metadata", org_name, context)
            if meta_result.success and meta_result.data:
                meta = MetadataEntity(**meta_result.data)
                stage = str(meta.stage) if meta.stage is not None else None
                sector = str(meta.sector) if meta.sector is not None else None
        except Exception:
            pass
    
        overall_pct = 0.0
        try:
            overall_pct = StorageInterface.get_org_data(org_name, context).overall_completion_pct
        except Exception:
            pass
    
        # Format optional date/datetime fields defensively.
        def _fmt(value: object) -> str | None:
            if value is None:
                return None
            if hasattr(value, "isoformat"):
                return value.isoformat()  # type: ignore[union-attr]
            return str(value)
    
        return OrgSnapshot(
            name=org.name,
            type=str(org.type) if org.type is not None else "",
            legal=str(org.legal) if org.legal is not None else None,
            currency=str(org.currency) if org.currency is not None else None,
            unit=str(org.unit) if org.unit is not None else None,
            closing=org.closing,
            incorporation=_fmt(org.incorporation),
            created_at=_fmt(org.created_at),
            stage=stage,
            sector=sector,
            overall_completion_pct=overall_pct,
        )
    
    @staticmethod
    def get_org_data(org_name: str, context: Context) -> OrgDataDisplay:
        """
        Return the full right-pane data payload for the selected organization.
    
        Iterates every entity registered for the "company" schema. SINGLE
        entities produce a field list with completion stats; MULTIPLE entities
        produce a record count and title list. Results are grouped into
        ModuleDisplay objects in deterministic order: core → branding → market.
    
        Never raises — returns an empty OrgDataDisplay on any failure.
        """
        try:
            from ..core.enums import Cardinality
            from ..core.registry import get_entities_for_schema
            from ..db.database import StorageInterface
    
            entity_classes = get_entities_for_schema("company")
    
            # Buckets keyed by module, preserving declaration order within each.
            module_buckets: dict[str, list[EntityDisplay]] = {m: [] for m in _MODULE_ORDER}
    
            total_filled = 0
            total_fields = 0
    
            for entity_cls in entity_classes:
                entity_id = entity_cls.get_entity_word_id()
                entity_name = entity_cls.__name__.replace("Entity", "")
                module = getattr(entity_cls, "module", "core")
                cardinality = entity_cls.cardinality
                system_fields = entity_cls.get_all_system_fields()
                user_field_names = [
                    fname
                    for fname in entity_cls.model_fields
                    if fname not in system_fields
                ]
    
                if cardinality == Cardinality.SINGLE:
                    result = StorageInterface.load_entity(entity_id, org_name, context)
                    record: dict = result.data if result.success and result.data else {}
    
                    field_displays: list[FieldDisplay] = []
                    for fname in user_field_names:
                        raw = record.get(fname)
                        is_set = raw is not None and raw != ""
                        field_displays.append(
                            FieldDisplay(
                                name=fname,
                                value=raw,
                                is_set=is_set,
                                display_value=str(raw) if is_set else "—",
                            )
                        )
    
                    filled = sum(1 for f in field_displays if f.is_set)
                    total = len(field_displays)
                    pct = (filled / total * 100) if total > 0 else 0.0
    
                    total_filled += filled
                    total_fields += total
    
                    entity_display = EntityDisplay(
                        entity_id=entity_id,
                        entity_name=entity_name,
                        cardinality=cardinality,
                        fields=field_displays,
                        filled_count=filled,
                        total_count=total,
                        completion_pct=pct,
                        record_count=0,
                        record_titles=[],
                    )
    
                else:  # Cardinality.MULTIPLE
                    result = StorageInterface.load_all_entities(entity_id, org_name, context)
                    records: list[dict] = (
                        result.data
                        if result.success and isinstance(result.data, list)
                        else []
                    )
    
                    record_titles: list[str] = []
                    for rec in records:
                        title: str | None = None
                        for fname in user_field_names:
                            val = rec.get(fname)
                            if val is not None and val != "":
                                title = str(val)
                                break
                        record_titles.append(title if title is not None else str(rec.get("id", "?")))
    
                    entity_display = EntityDisplay(
                        entity_id=entity_id,
                        entity_name=entity_name,
                        cardinality=cardinality,
                        fields=[],
                        filled_count=0,
                        total_count=0,
                        completion_pct=0.0,
                        record_count=len(records),
                        record_titles=record_titles,
                    )
    
                bucket = module_buckets.setdefault(module, [])
                bucket.append(entity_display)
    
            modules: list[ModuleDisplay] = []
            for mod_id in _MODULE_ORDER:
                ents = module_buckets.get(mod_id, [])
                if not ents:
                    continue
                modules.append(
                    ModuleDisplay(
                        module_id=mod_id,
                        module_name=mod_id.capitalize(),
                        entities=ents,
                        entity_count=len(ents),
                    )
                )
    
            overall_pct = (total_filled / total_fields * 100) if total_fields > 0 else 0.0
    
            return OrgDataDisplay(
                org_name=org_name,
                modules=modules,
                total_filled=total_filled,
                total_fields=total_fields,
                overall_completion_pct=overall_pct,
                active_entity_ids=[],
            )
    
        except Exception:
            return OrgDataDisplay(
                org_name=org_name,
                modules=[],
                total_filled=0,
                total_fields=0,
                overall_completion_pct=0.0,
                active_entity_ids=[],
            )
