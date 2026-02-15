"""
View word definitions.

Contains manually defined ViewWord objects representing report filters.
Views determine which entities are displayed together.

Available only in APP context (cd app/).
"""

from typing import List

from ...enums.core import ContextLevel
from ...models.words import ViewWord

VIEW_WORDS_LIST: List[ViewWord] = [
    ViewWord(
        id="neco",
        description="NECO (Non-Equity Company Overview) - Core company info without financials",
        aliases=["non-equity", "basic"],
        context=ContextLevel.APP,
        entities=["organization", "address", "metadata", "brand", "news"],
    ),
    ViewWord(
        id="investor",
        description="Investor Report - Financial and equity focused",
        aliases=["ir"],
        context=ContextLevel.APP,
        entities=["organization", "metadata", "brand"],
        # Future: add financials, captable when available
    ),
    ViewWord(
        id="duediligence",
        description="Due Diligence - Comprehensive company review",
        aliases=["dd"],
        context=ContextLevel.APP,
        entities=[
            "organization",
            "address",
            "metadata",
            "brand",
            "news",
            "competitors",
        ],
    ),
]
