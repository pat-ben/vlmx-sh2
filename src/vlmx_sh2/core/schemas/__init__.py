"""
Core SQLModel schemas.

This package contains shared SQLModel schema definitions and entities.
Import these from `vlmx_sh2.core.schemas`.
"""

from .base import EntityModel, SchemaModel
from .company import (
    AddressEntity,
    BrandEntity,
    CompanyDatabase,
    CompetitorsEntity,
    MetadataEntity,
    NewsEntity,
    OfferingEntity,
    OrganizationEntity,
    TargetEntity,
    ValuesEntity,
)

__all__ = [
    "EntityModel",
    "SchemaModel",
    "CompanyDatabase",
    "OrganizationEntity",
    "AddressEntity",
    "MetadataEntity",
    "BrandEntity",
    "OfferingEntity",
    "TargetEntity",
    "ValuesEntity",
    "NewsEntity",
    "CompetitorsEntity",
]
