"""
Command macros and shortcuts for VLMX DSL.

Provides command abbreviations and expansion functionality to allow
users to use short forms like 'cc' for 'create company' or 'sb' 
for 'show brand'. Helps improve command line efficiency.
"""

from typing import Dict, List


# ==================== SHORTCUTS SYSTEM ====================

SHORTCUTS: Dict[str, List[str]] = {
    "cc": ["create", "company"],
    "cb": ["create", "brand"],
    "cm": ["create", "metadata"],
    "co": ["create", "offering"],
    "ct": ["create", "target"],
    "cv": ["create", "values"],
    "sb": ["show", "brand"],
    "sc": ["show", "company"],
    "sm": ["show", "metadata"],
    "so": ["show", "offering"],
    "st": ["show", "target"],
    "sv": ["show", "values"],
    "ub": ["update", "brand"],
    "uc": ["update", "company"],
    "um": ["update", "metadata"],
    "uo": ["update", "offering"],
    "ut": ["update", "target"],
    "uv": ["update", "values"],
    "ab": ["add", "brand"],
    "ac": ["add", "company"],
    "am": ["add", "metadata"],
    "ao": ["add", "offering"],
    "at": ["add", "target"],
    "av": ["add", "values"],
    "db": ["delete", "brand"],
    "dc": ["delete", "company"],
    "dm": ["delete", "metadata"],
    "do": ["delete", "offering"],
    "dt": ["delete", "target"],
    "dv": ["delete", "values"],
}


def expand_shortcuts(input_text: str) -> str:
    """
    Expand shortcuts in user input before parsing.
    
    Args:
        input_text: Original user input
        
    Returns:
        Input with shortcuts expanded to full words
    """
    tokens = input_text.strip().split()
    if not tokens:
        return input_text
    
    first_token = tokens[0].lower()
    if first_token in SHORTCUTS:
        expanded_words = SHORTCUTS[first_token]
        remaining_tokens = tokens[1:] if len(tokens) > 1 else []
        return " ".join(expanded_words + remaining_tokens)
    
    return input_text