from typing import Literal

KeywordLiteral = Literal[
    # Actions
    "create", "delete", "update",
    # Entities
    "company", "milestone", "data",
    # Contexts
    "holding", "operating"    
]