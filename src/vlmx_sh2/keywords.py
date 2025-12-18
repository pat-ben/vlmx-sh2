

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




""" 
TO DO LIST:
    1. Create keywords Type (VERB, NOUN, ADJECTIVE)
    2. Create keywords Usage (ACTION, ENTITY, MODIFIER, PROPERTY)
    2. Add metadata to each keyword: category (Action, Entity, Modifier or a mixt), description (str), aliases (Optional List), abbreviations (Optional List), deprecated (boolean)
    2. Corresponding arguments to each keyword and their value type. This should apply to Entity keywords.
    3. Add IDE support for autocompletion, syntax highlighting, and keyword information. This IDE support will be used when composing commands with keywords.
    4. Make it easy to parse and validate commands using these keywords.
    

"""