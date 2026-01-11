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
    "org": ["organization"],
    
    # Operator macros for filtering
    "&": ["and"],
    "|": ["or"]
}


def expand_macros(input_text: str) -> str:
    """
    Expand macros in user input before parsing.
    
    Handles both command macros (cc → create company) and operator macros (& → and, | → or).
    Command macros are only expanded at the beginning of the input.
    Operator macros are expanded throughout the entire input.
    
    Args:
        input_text: Original user input
        
    Returns:
        Input with macros expanded to full words
    """
    if not input_text.strip():
        return input_text
    
    # First, expand operator macros throughout the text
    result = input_text
    for symbol, words in MACROS.items():
        if symbol in ["&", "|"]:  # Only operator macros
            # Replace symbol with word, but preserve spacing
            result = result.replace(symbol, words[0])
    
    # Then, expand command macros at the beginning
    tokens = result.strip().split()
    if tokens:
        first_token = tokens[0].lower()
        if first_token in MACROS and first_token not in ["&", "|"]:  # Exclude operator macros
            expanded_words = MACROS[first_token]
            remaining_tokens = tokens[1:] if len(tokens) > 1 else []
            result = " ".join(expanded_words + remaining_tokens)
    
    return result