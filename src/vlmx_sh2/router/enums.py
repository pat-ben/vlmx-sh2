# D:\Code\vlmx-sh2\src\vlmx_sh2\router\enums.py
"""
Router enums for VLMX DSL.

Defines the types of routes a command can take through the system.
"""

from enum import Enum


class RouteType(Enum):
    """
    Types of routes a command can take.
    
    Determines the execution path after parsing:
    - DIRECT: Execute handler immediately (standard commands)
    - FORM_WIZARD: Show interactive form before execution
    - QUERY_WIZARD: Show interactive query builder (future feature)
    - SUPPORT_WIZARD: Show error recovery/help wizard
    
    Examples:
        >>> RouteType.DIRECT
        <RouteType.DIRECT: 'direct'>
        >>> RouteType.FORM_WIZARD.value
        'form_wizard'
    """
    DIRECT = "direct"                   # Execute handler immediately
    FORM_WIZARD = "form_wizard"         # Show interactive form first
    QUERY_WIZARD = "query_wizard"       # Show query builder first (future)
    SUPPORT_WIZARD = "support_wizard"   # Show error recovery wizard