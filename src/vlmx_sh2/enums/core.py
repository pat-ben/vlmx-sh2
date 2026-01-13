"""
Core schemas ENUMs.

Contains ENUMs that are fundamental to the schemas architecture
and are shared across multiple schemas components.
"""

from enum import Enum, IntEnum


class Cardinality(str, Enum):
    """
    Entity cardinality types.
    
    Defines whether an entity can have single or multiple records
    per company in the database schemas.
    """
    SINGLE = "single"      # One record per company (e.g., Company, Brand)
    MULTIPLE = "multiple"  # Multiple records per company (e.g., News, Competitors)


class ContextLevel(IntEnum):
    """Context hierarchy levels for navigation and command execution."""
    
    SYS = 0  # system / root level
    ORG = 1  # organization level (most of the time company)
    APP = 2  # application level (could be plugin)