"""
Business domain schemas.

Contains entity definitions for business objects like companies,
funds, and their related data. This package is the extension point
for plugins to add custom entity types.
"""

from .base import EntityModel, SchemaModel
from .company import (
    CompanyDatabase,
    OrganizationEntity,
    AddressEntity,
    MetadataEntity,
    BrandEntity,
    OfferingEntity,
    TargetEntity,
    ValuesEntity,
    NewsEntity,
    CompetitorsEntity,
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