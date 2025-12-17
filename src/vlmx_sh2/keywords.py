""" Basic list of keywords.
TO DO NEXT:
    1. Each keyword should have metadata: eg. category, description, aliases, abbreviations, deprecated
    2. Add IDE support for autocompletion, syntax highlighting, and keyword information.
    

"""

from typing import Literal

ActionKeyword = Literal[
    "create", "delete", "update"
]

EntityKeyword = Literal[
    "company", "milestone", "data",    
]

ModifierKeyword = Literal[
    "holding", "operating"    
]

