"""
Context helper functions.

Utility functions for working with Context instances. These functions
were extracted from the Context class to separate data structure from
business logic and provide a cleaner functional interface.
"""

from typing import List, Optional, Tuple

from ..models.context import Context
from ..enums.core import ContextLevel


def is_sys(context: Context) -> bool:
    """
    Check if context is at system level.
    
    Args:
        context: The context to check
        
    Returns:
        True if at system level, False otherwise
    """
    return context.level == ContextLevel.SYS


def is_org(context: Context) -> bool:
    """
    Check if context is at organization level.
    
    Args:
        context: The context to check
        
    Returns:
        True if at organization level, False otherwise
    """
    return context.level == ContextLevel.ORG


def is_app(context: Context) -> bool:
    """
    Check if context is at application level.
    
    Args:
        context: The context to check
        
    Returns:
        True if at application level, False otherwise
    """
    return context.level == ContextLevel.APP


def get_level_name(context: Context) -> str:
    """
    Get human-readable level name.
    
    Args:
        context: The context to get level name for
        
    Returns:
        Level name: "sys", "org", "app", or "unknown(N)"
    """
    if context.level == ContextLevel.SYS:
        return "sys"
    elif context.level == ContextLevel.ORG:
        return "org"
    elif context.level == ContextLevel.APP:
        return "app"
    else:
        return f"unknown({context.level})"


def requires_schema(context: Context) -> bool:
    """
    Check if commands must explicitly specify a schema/company.
    
    Args:
        context: The context to check
        
    Returns:
        True if at SYS level (user must explicitly specify schema/company)
        False if at ORG or APP level (schema already known from context)
    """
    return context.level == ContextLevel.SYS


def requires_app(context: Context) -> bool:
    """
    Check if commands must explicitly specify an app.
    
    Args:
        context: The context to check
        
    Returns:
        True if at SYS or ORG level (user must explicitly specify app)
        False if at APP level (app already known from context)
    """
    return context.level != ContextLevel.APP


def get_missing_requirements(context: Context) -> List[str]:
    """
    Get list of what needs to be specified for commands at current context level.
    
    Args:
        context: The context to check
        
    Returns:
        List of what needs to be specified: ["schema"], ["app"], ["schema", "app"], or []
        Based on current context level
    """
    requirements = []
    
    if requires_schema(context):
        requirements.append("schema")
    
    if requires_app(context):
        requirements.append("app")
        
    return requirements


def can_execute_direct_command(context: Context) -> bool:
    """
    Check if commands can run without prefixes.
    
    Args:
        context: The context to check
        
    Returns:
        True only at APP level (commands can run without prefixes)
        False at SYS/ORG levels
    """
    return context.level == ContextLevel.APP


def validate_command_requirements(context: Context, has_schema: bool = False, has_app: bool = False) -> Tuple[bool, Optional[str]]:
    """
    Validate if a command has all required parameters for the current context level.
    
    Args:
        context: The context to validate against
        has_schema: Was schema/company provided?
        has_app: Was app provided?
        
    Returns:
        Tuple of (is_valid: bool, error_message: Optional[str])
        Error messages are user-friendly
    """
    missing = []
    
    if requires_schema(context) and not has_schema:
        missing.append("schema")
        
    if requires_app(context) and not has_app:
        missing.append("app")
        
    if not missing:
        return True, None
        
    # Generate user-friendly error message
    if len(missing) == 1:
        if missing[0] == "schema":
            return False, f"At {get_level_name(context).upper()} level, you must specify the schema: command [company_name] ..."
        else:  # app
            return False, f"At {get_level_name(context).upper()} level, you must specify the app: command ... [app_name]"
    else:  # both missing
        return False, f"At {get_level_name(context).upper()} level, you must specify both schema and app: command [company_name] ... [app_name]"