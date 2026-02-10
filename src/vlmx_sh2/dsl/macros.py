"""
Command macros and shortcuts.

Provides command abbreviations and expansion functionality to allow
users to use short forms like 'cc' for 'create company' or 'sb' 
for 'show brand'. Helps improve command line efficiency.

Macro Design Guidelines:
- Length: Macros must be 2 characters
- Structure: Must expand to ActionWord + SchemaWord OR ActionWord + EntityWord (2 words)
- Position: Only expands at the very beginning of input (position 0)
- Case: Case-insensitive matching

These are guidelines for developers adding new macros, not runtime validation.
"""

from typing import Dict, List


# ==================== SHORTCUTS SYSTEM ====================

MACROS: Dict[str, List[str]] = {
    "cc": ["create", "company"],   # ActionWord + SchemaWord
    "dc": ["delete", "company"],   # ActionWord + SchemaWord
    # Add new macros following the pattern: 2 chars → [ActionWord, SchemaWord/EntityWord]
}


def expand_macros(input_text: str) -> str:
    """
    Expand command macros in user input before parsing.
    
    Handles multi-word command macros (cc → create company, dc → delete company).
    Only the first token is checked for macro expansion. Macros appearing
    elsewhere in input are ignored and treated as regular text.
    
    Args:
        input_text: Original user input
        
    Returns:
        Input with command macros expanded to full words
    """
    if not input_text.strip():
        return input_text
    
    # Expand command macros at the beginning
    tokens = input_text.strip().split()
    if tokens:
        first_token = tokens[0].lower()
        if first_token in MACROS:
            expanded_words = MACROS[first_token]
            remaining_tokens = tokens[1:] if len(tokens) > 1 else []
            return " ".join(expanded_words + remaining_tokens)
    
    return input_text