"""
ENUMs package - Single Export Hub.

Contains all ENUMs used throughout the VLMX DSL system.
This is the single source of truth for all ENUM imports.

Usage:
    from vlmx_sh2.enums import Legal, Currency, Cardinality, Operator
    from vlmx_sh2.enums import TokenType, ValueContext
"""

# Form/UI ENUMs (user-facing business domain values)
from .forms import (
    Legal,
    Currency, 
    Country,
    Stage,
    Phase,
    NewsCategory,
    CompetitorSize,
    Sector,
    Model,
    Round,
    Unit,
    TypeOrg,
)

# Core schemas ENUMs (fundamental schemas architecture)
from .core import (
    Cardinality,
    ContextLevel,
)

# Parser ENUMs (parsing pipeline)
from .parser import (
    Operator,
    QueryKeyword,
    Bracket,
    TokenClass,
    TokenType,
    ValueContext,
)

# Validation ENUMs (diagnostics pipeline)
from .validation import (
    IssueSeverity,
    IssueStage,
)

__all__ = [
    # Form/UI ENUMs
    'Legal',
    'Currency',
    'Country', 
    'Stage',
    'Phase',
    'NewsCategory',
    'CompetitorSize',
    'Sector',
    'Model',
    'Round',
    'Unit',
    'TypeOrg',
    
    # Core schemas ENUMs
    'Cardinality',
    'ContextLevel',
    
    # Parser ENUMs
    'Operator',
    'QueryKeyword',
    'Bracket',
    'TokenClass',
    'TokenType',
    'ValueContext',
    
    # Validation ENUMs
    'IssueSeverity',
    'IssueStage',
]