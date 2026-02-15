"""
Tool word definitions.

Contains manually defined ToolWord objects representing calculation tools.
Tools perform business calculations with required input parameters.

Available only in APP context (cd app/).
"""

from typing import List

from ...enums.core import ContextLevel
from ...models.words import ToolWord

TOOL_WORDS_LIST: List[ToolWord] = [
    ToolWord(
        id="dcf",
        description="Discounted Cash Flow valuation model",
        aliases=["discounted-cash-flow", "valuation"],
        context=ContextLevel.APP,
        parameters=["revenue", "growth_rate", "discount_rate", "terminal_multiple"],
    ),
    ToolWord(
        id="captable",
        description="Cap Table calculator - ownership and dilution",
        aliases=["cap", "equity"],
        context=ContextLevel.APP,
        parameters=["shares_outstanding", "option_pool", "new_investment"],
    ),
    ToolWord(
        id="forecast",
        description="Revenue forecast model",
        aliases=["rev-forecast", "projection"],
        context=ContextLevel.APP,
        parameters=["base_revenue", "growth_rate", "periods"],
    ),
]
