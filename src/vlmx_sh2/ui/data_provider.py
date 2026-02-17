"""
Passive read interface between the UI and data sources.

The UI must never import from db/ or dsl/ directly — all passive reads
go through UIDataProvider.
"""

from __future__ import annotations

from ..core.models.context import Context
from ..core.schemas.company import OrganizationEntity


class UIDataProvider:
    """Single point of access for all UI data reads."""

    @staticmethod
    def get_organizations(context: Context) -> list[OrganizationEntity]:
        """Return all organizations as OrganizationEntity instances."""
        try:
            from ..db.database import StorageInterface

            storage_result = StorageInterface.list_entities("company", "", context)
            companies = storage_result.data.get("companies", [])
            results = []
            for record in companies:
                try:
                    results.append(OrganizationEntity(**record))
                except Exception:
                    continue
            return results
        except Exception:
            return []

    @staticmethod
    def get_views(schema_id: str = "company") -> list:
        """Return ViewWord instances for the given schema_id."""
        try:
            from ..dsl.words.registry import VIEW_WORDS

            return [v for v in VIEW_WORDS.values() if v.schema_id == schema_id]
        except Exception:
            return []

    @staticmethod
    def get_tools() -> list:
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
