"""
Context helper functions.

Utility functions for working with Context instances. These functions
were extracted from the Context class to separate data structure from
business logic and provide a cleaner functional interface.

The module provides two types of validation functions:

1. **Context State Functions** (requires_schema, requires_app, etc.)
   - Answer: "What does my current context lack?"
   - Used for general context analysis
   
2. **Command Validation Functions** (command_requires_schema, validate_command_context_requirements, etc.)
   - Answer: "What does this specific command need?"
   - Consider command standalone flags and special cases
   - Used for pre-execution validation
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


# ==================== COMMAND-LEVEL VALIDATION ====================

def command_requires_schema(action_word, context: Context, entity_value: Optional[str] = None) -> bool:
    """
    Check if a specific command requires schema context.
    
    This function considers both the command's standalone flag and the specific
    parameters (like entity_value for navigation commands).
    
    Args:
        action_word: The ActionWord being executed
        context: The current context
        entity_value: Optional entity value (for commands like 'cd company_name')
        
    Returns:
        True if this command needs schema to be explicitly specified
        False if this command can run without schema context
    """
    # Special case for navigation (cd command)
    if action_word.id == "cd":
        # Relative navigation is always standalone
        if entity_value in ["..", "~", "root", None]:
            return False
        # Absolute navigation (cd company_name) requires schema validation at SYS level
        return context.level == ContextLevel.SYS
    
    # If command is marked as standalone, it never needs schema
    if action_word.standalone:
        return False
    
    # Non-standalone commands need schema at SYS level
    if context.level == ContextLevel.SYS:
        return True
    
    # At ORG/APP level, schema is provided by context
    return False


def command_requires_app(action_word, context: Context) -> bool:
    """
    Check if a specific command requires app context.
    
    Args:
        action_word: The ActionWord being executed  
        context: The current context
        
    Returns:
        True if this command needs app to be explicitly specified
        False if this command can run without app context
    """
    # If command is marked as standalone, it never needs app
    if action_word.standalone:
        return False
    
    # Non-standalone commands need app at SYS/ORG levels
    if context.level in (ContextLevel.SYS, ContextLevel.ORG):
        return True
    
    # At APP level, app is provided by context
    return False


def validate_command_context_requirements(action_word, context: Context, entity_value: Optional[str] = None, has_schema: bool = False, has_app: bool = False) -> Tuple[bool, Optional[str]]:
    """
    Validate if a specific command has all required context for the current level.
    
    This is the main validation function that should be used by command handlers
    to check if they can execute in the current context.
    
    Args:
        action_word: The ActionWord being executed
        context: The current context  
        entity_value: Optional entity value (for navigation commands)
        has_schema: Was schema/company provided in the command?
        has_app: Was app provided in the command?
        
    Returns:
        Tuple of (is_valid: bool, error_message: Optional[str])
        Error messages are user-friendly and command-specific
    """
    missing = []
    
    if command_requires_schema(action_word, context, entity_value) and not has_schema:
        missing.append("schema")
        
    if command_requires_app(action_word, context) and not has_app:
        missing.append("app")
        
    if not missing:
        return True, None
        
    # Generate command-specific error messages
    command_name = action_word.id
    level_name = get_level_name(context).upper()
    
    if len(missing) == 1:
        if missing[0] == "schema":
            if action_word.id == "cd":
                return False, f"At {level_name} level, you must specify the company: cd [company_name]"
            else:
                return False, f"At {level_name} level, you must specify the schema: {command_name} [company_name] ..."
        else:  # app
            return False, f"At {level_name} level, you must specify the app: {command_name} ... [app_name]"
    else:  # both missing
        return False, f"At {level_name} level, you must specify both schema and app: {command_name} [company_name] ... [app_name]"


def get_app_name(context: Context) -> Optional[str]:
    """
    Get the current app name from context.
    
    Args:
        context: The context to check
        
    Returns:
        App name if at APP level, None otherwise
    """
    return context.app_name if context.level == ContextLevel.APP else None


def get_app_type(context: Context) -> Optional[str]:
    """
    Get the current app type from context.
    
    Args:
        context: The context to check
        
    Returns:
        "view" or "tool" if at APP level, None otherwise
    """
    return context.app_type if context.level == ContextLevel.APP else None


def is_view_context(context: Context) -> bool:
    """
    Check if context is in a view app.
    
    Args:
        context: The context to check
        
    Returns:
        True if at APP level with app_type="view", False otherwise
    """
    return context.level == ContextLevel.APP and context.app_type == "view"


def is_tool_context(context: Context) -> bool:
    """
    Check if context is in a tool app.
    
    Args:
        context: The context to check
        
    Returns:
        True if at APP level with app_type="tool", False otherwise
    """
    return context.level == ContextLevel.APP and context.app_type == "tool"