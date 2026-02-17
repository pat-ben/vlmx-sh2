"""
Schema Registry — single source of truth for entity pools and schema configs.

This module centralises all knowledge about which entities exist, which schemas
(org types) group them, and how entities map to storage names.  Every other
module that needs this information should import from here instead of
re-deriving it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Type

from vlmx_sh2.core.enums import TypeOrg
from vlmx_sh2.core.schemas.base import EntityModel, SchemaModel
from vlmx_sh2.core.schemas.company import (
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

# ============================================
# 1. Global entity pool
# ============================================

ENTITY_POOL: Dict[str, Type[EntityModel]] = {
    cls.get_entity_word_id(): cls
    for cls in [
        OrganizationEntity,
        AddressEntity,
        MetadataEntity,
        BrandEntity,
        OfferingEntity,
        TargetEntity,
        ValuesEntity,
        NewsEntity,
        CompetitorsEntity,
    ]
}

# ============================================
# 2. Schema definitions
# ============================================


@dataclass
class SchemaConfig:
    """Configuration for an org-type schema."""

    schema_id: str
    org_type: TypeOrg
    description: str
    aliases: list[str]
    entity_ids: list[str]
    schema_class: Type[SchemaModel]


SCHEMAS: Dict[str, SchemaConfig] = {
    "company": SchemaConfig(
        schema_id="company",
        org_type=TypeOrg.COMPANY,
        description="Company organization type",
        aliases=["co"],
        entity_ids=[
            "organization",
            "address",
            "metadata",
            "brand",
            "offering",
            "target",
            "values",
            "news",
            "competitors",
        ],
        schema_class=CompanyDatabase,
    ),
}

# ============================================
# 3. Root entity accessor
# ============================================

ROOT_ENTITY_ID = "organization"


def get_root_entity() -> Type[EntityModel]:
    """Return the root entity class (OrganizationEntity)."""
    return ENTITY_POOL[ROOT_ENTITY_ID]


def is_root_entity(entity_id: str) -> bool:
    """True if entity_id is (or resolves to) the root entity.

    Accepts both 'organization' (entity_id) and 'company' (table_name).
    """
    if entity_id == ROOT_ENTITY_ID:
        return True
    # Check if it matches any schema_id whose root is ROOT_ENTITY_ID
    return entity_id in SCHEMAS


def is_schema_id(name: str) -> bool:
    """True if name is a registered schema_id (e.g. 'company')."""
    return name in SCHEMAS


def get_root_json_filename() -> str:
    """Return the JSON filename for the root org entity ('company.json').

    This is the on-disk filename for the root organization record,
    derived from the root entity's table_name.
    """
    mapping = _STORAGE_MAPPINGS.get(ROOT_ENTITY_ID)
    if mapping is None:
        raise RuntimeError(f"No storage mapping for root entity '{ROOT_ENTITY_ID}'")
    return mapping.json_filename


# ============================================
# 4. Storage-name mapping
# ============================================


@dataclass
class StorageMapping:
    """Maps an entity_id to its on-disk / in-DB storage names."""

    entity_id: str
    json_filename: str
    table_name: str
    aliases: list[str] = field(default_factory=list)


def _build_storage_mappings() -> Dict[str, StorageMapping]:
    mappings: Dict[str, StorageMapping] = {}
    for entity_id, entity_cls in ENTITY_POOL.items():
        tname = entity_cls.table_name()
        mappings[entity_id] = StorageMapping(
            entity_id=entity_id,
            json_filename=f"{tname}.json",
            table_name=tname,
            aliases=entity_cls.get_entity_aliases(),
        )
    return mappings


_STORAGE_MAPPINGS = _build_storage_mappings()

# Build a reverse lookup: alias → entity_id
_ALIAS_TO_ENTITY: Dict[str, str] = {}
for _eid, _mapping in _STORAGE_MAPPINGS.items():
    for _alias in _mapping.aliases:
        _ALIAS_TO_ENTITY[_alias] = _eid

# ============================================
# 5. Query functions (public API)
# ============================================


def get_entity_class(entity_id: str) -> Type[EntityModel] | None:
    """Look up an entity class by its word id."""
    return ENTITY_POOL.get(entity_id)


def get_entities_for_schema(schema_id: str) -> list[Type[EntityModel]]:
    """Return the ordered list of entity classes for a given schema."""
    config = SCHEMAS.get(schema_id)
    if config is None:
        return []
    return [ENTITY_POOL[eid] for eid in config.entity_ids]


def get_schema_config(schema_id: str) -> SchemaConfig | None:
    """Return the SchemaConfig for *schema_id*, or None."""
    return SCHEMAS.get(schema_id)


def get_all_schema_configs() -> list[SchemaConfig]:
    """Return every registered SchemaConfig."""
    return list(SCHEMAS.values())


def get_storage_mapping(entity_id: str) -> StorageMapping | None:
    """Return the StorageMapping for *entity_id*, or None."""
    return _STORAGE_MAPPINGS.get(entity_id)


def get_all_storage_mappings() -> Dict[str, StorageMapping]:
    """Return all storage mappings keyed by entity_id."""
    return dict(_STORAGE_MAPPINGS)


def resolve_entity_alias(alias: str) -> str | None:
    """Resolve an entity alias to its canonical entity_id.

    Returns None if *alias* is not a known entity alias (schema aliases
    like "co" are *not* resolved here).
    """
    return _ALIAS_TO_ENTITY.get(alias)
