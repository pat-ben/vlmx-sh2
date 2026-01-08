"""
Form and UI ENUMs package.

Contains all ENUMs that are visible to users in forms, dropdowns,
and other UI components. These ENUMs represent user choices and
business domain values that users directly interact with.

Usage:
    from vlmx_sh2.enums import Legal, Currency, Country
    from vlmx_sh2.enums.forms import NewsCategory
"""

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

__all__ = [
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
]