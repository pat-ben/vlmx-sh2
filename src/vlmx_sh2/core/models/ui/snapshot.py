"""
UI org snapshot model.

Represents the right pane header data when an organization is selected.
"""

from typing import Optional

from pydantic import BaseModel


class OrgSnapshot(BaseModel):
    """Data for the right pane header when an org is selected."""

    name: str
    type: str                    # from TypeOrg enum value
    legal: Optional[str]
    currency: Optional[str]
    unit: Optional[str]
    closing: Optional[int]
    incorporation: Optional[str] # formatted date string or None
    created_at: Optional[str]    # formatted date string or None
    # Metadata fields (from MetadataEntity)
    stage: Optional[str]
    sector: Optional[str]
    # Completion summary
    overall_completion_pct: float
