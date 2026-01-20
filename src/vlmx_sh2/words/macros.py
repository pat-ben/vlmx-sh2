"""
Command macros and shortcuts.

Provides command abbreviations and expansion functionality to allow
users to use short forms like 'cc' for 'create company' or 'sb' 
for 'show brand'. Helps improve command line efficiency.
"""

from typing import Dict, List


# ==================== SHORTCUTS SYSTEM ====================

MACROS: Dict[str, List[str]] = {
    "cc": ["create", "company"],
    "dc": ["delete", "company"],
    "org": ["organization"]
}


def expand_macros(input_text: str) -> str:
    """
    Expand command macros in user input before parsing.
    
    Handles multi-word command macros (cc → create company, dc → delete company).
    Command macros are only expanded at the beginning of the input.
    
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