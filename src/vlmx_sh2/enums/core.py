"""
Core entities ENUMs.

Contains ENUMs that are fundamental to the entities architecture
and are shared across multiple entities components.
"""

from enum import Enum


class Cardinality(str, Enum):
    """
    Entity cardinality types.
    
    Defines whether an entity can have single or multiple records
    per company in the database entities.
    """
    SINGLE = "single"      # One record per company (e.g., Company, Brand)
    MULTIPLE = "multiple"  # Multiple records per company (e.g., News, Competitors)