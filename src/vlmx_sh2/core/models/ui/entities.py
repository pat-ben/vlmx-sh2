"""
UI entity and module display models.

Represents one entity and a full module group prepared for rendering
in the right pane of the UI.
"""

from pydantic import BaseModel

from ...enums import Cardinality
from .fields import FieldDisplay


class EntityDisplay(BaseModel):
    """One entity ready for UI rendering in the right pane."""

    entity_id: str               # e.g. "organization"
    entity_name: str             # e.g. "Organization"
    cardinality: Cardinality     # SINGLE or MULTIPLE
    # For SINGLE entities:
    fields: list[FieldDisplay]   # field rows with value + is_set
    filled_count: int            # number of fields with a value
    total_count: int             # total number of user fields
    completion_pct: float        # filled / total * 100, 0.0 if total == 0
    # For MULTIPLE entities:
    record_count: int            # number of records
    record_titles: list[str]     # display titles for each record (best available field)


class ModuleDisplay(BaseModel):
    """One module group (core, branding, market) for the right pane."""

    module_id: str               # e.g. "core"
    module_name: str             # capitalized, e.g. "Core"
    entities: list[EntityDisplay]
    entity_count: int            # len(entities)


class OrgDataDisplay(BaseModel):
    """Complete right-pane data payload for a selected organization."""

    org_name: str
    modules: list[ModuleDisplay]
    total_filled: int            # sum across all single entities
    total_fields: int            # sum across all single entities
    overall_completion_pct: float
    active_entity_ids: list[str] # empty = show all; populated when view/tool filters
