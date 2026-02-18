"""
Passive read interface between the UI and data sources.

The UI must never import from db/ or dsl/ directly — all passive reads
go through UIDataProvider.
"""

from __future__ import annotations

from ..core.models.context import Context
from ..core.models.ui import EntityDisplay, FieldDisplay, ModuleDisplay, OrgDataDisplay, OrgSnapshot
from ..core.models.words import ToolWord, ViewWord
from ..core.schemas.company import OrganizationEntity

# Deterministic module rendering order for the right pane.
_MODULE_ORDER = ["core", "branding", "market"]


class UIDataProvider:
    """Single point of access for all UI data reads."""

    @staticmethod
    def get_organizations(context: Context) -> list[OrganizationEntity]:
        """Return all organizations from the org registry index.

        Reads system/org/registry.toml rather than scanning data/ folders.
        Each entry provides only the left-pane fields (name, legal, currency);
        full org data is loaded separately via get_org_snapshot() when selected.
        """
        try:
            from ..db.org_registry import read_org_registry

            entries = read_org_registry()
            results = []
            for entry in entries:
                try:
                    results.append(
                        OrganizationEntity(
                            name=entry["name"],
                            legal=entry.get("legal"),
                            currency=entry.get("currency"),
                        )
                    )
                except Exception:
                    continue
            return results
        except Exception:
            return []

    @staticmethod
    def get_views(schema_id: str = "company") -> list[ViewWord]:
        """Return ViewWord instances for the given schema_id."""
        try:
            from ..dsl.words.registry import VIEW_WORDS

            return [v for v in VIEW_WORDS.values() if v.schema_id == schema_id]
        except Exception:
            return []

    @staticmethod
    def get_tools() -> list[ToolWord]:
        """Return all ToolWord instances."""
        try:
            from ..dsl.words.registry import TOOL_WORDS

            return list(TOOL_WORDS.values())
        except Exception:
            return []

    @staticmethod
    def get_entity_records(
        entity_type: str, org_name: str, context: Context
    ) -> list[dict]:
        """Load all records for an entity type within an organization."""
        try:
            from ..db.database import StorageInterface

            result = StorageInterface.load_all_entities(entity_type, org_name, context)
            if result.success:
                return result.data
            return []
        except Exception:
            return []

    # ── Right-pane providers ──────────────────────────────────────────────────

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
            if not org_result.success:
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
            overall_pct = UIDataProvider.get_org_data(org_name, context).overall_completion_pct
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

    @staticmethod
    def get_entity_ids_for_view(view_id: str) -> list[str]:
        """Return the entity IDs associated with a view word."""
        try:
            from ..dsl.words.registry import VIEW_WORDS

            view_word = VIEW_WORDS.get(view_id)
            if view_word is None:
                return []
            return view_word.entities
        except Exception:
            return []

    @staticmethod
    def get_entity_ids_for_tool(tool_id: str) -> list[str]:
        """Return the entity IDs associated with a tool word."""
        # TODO: wire tool dependencies when ToolWord exposes them
        return []
