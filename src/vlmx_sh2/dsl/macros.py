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
    "am": ["add", "metadata"],
    "um": ["update", "metadata"],
    "dm": ["delete", "metadata"],
    "ab": ["add", "brand"],
    "ub": ["update", "brand"],
    "db": ["delete", "brand"],
    "av": ["add", "value"],
    "uv": ["update", "value"],
    "dv": ["delete", "value"],
    "at": ["add", "target"],
    "ut": ["update", "target"],
    "dt": ["delete", "target"],
    "ao": ["add", "offering"],
    "uo": ["update", "offering"],
    "do": ["delete", "offering"]    

}


def expand_macros(input_text: str) -> str:
    """
    Expand macros in user input before parsing.
    
    Args:
        input_text: Original user input
        
    Returns:
        Input with macros expanded to full words
    """
    tokens = input_text.strip().split()
    if not tokens:
        return input_text
    
    first_token = tokens[0].lower()
    if first_token in MACROS:
        expanded_words = MACROS[first_token]
        remaining_tokens = tokens[1:] if len(tokens) > 1 else []
        return " ".join(expanded_words + remaining_tokens)
    
    return input_text