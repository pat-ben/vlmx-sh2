"""
Navigation handler.

Handles context navigation (cd command) between different levels
of the application (SYS, ORG, APP).
"""

from typing import Optional
from ..models.context import Context
from ..models.responses import HandlerResult, CommandResult, ErrorResult
from ..models.parser.parsed_command import ParsedCommand
from ..models.context import Context as NewContext
from ..enums.core import ContextLevel
from ..storage.database import find_company_by_name
from ..utils.context_helpers import is_sys, is_org, get_level_name


# =============================================================================
# 1. Constants & Configuration
# =============================================================================

# Navigation command aliases
ROOT_NAVIGATION_ALIASES = {"~", "root", None}
UP_NAVIGATION_ALIASES = {".."}  # Go up one level in context hierarchy


# =============================================================================
# 2. Public Handler API
# =============================================================================

async def navigate_handler(parsed_command: ParsedCommand, context: Context) -> HandlerResult:
    """
    Handler for 'cd' command - manages context navigation.
    
    Supports:
    - cd ~, cd root  : Navigate to system level
    - cd ..          : Navigate up one level
    - cd <org_name>  : Navigate to organization
    - cd             : Show current location
    """
    try:
        entity_value = parsed_command.target_name
        
        if entity_value in UP_NAVIGATION_ALIASES:
            return _navigate_up(context)
        
        elif entity_value in ROOT_NAVIGATION_ALIASES:
            return _navigate_to_root()
        
        elif entity_value:
            return _navigate_to_org(entity_value, parsed_command.entity_model, context)
        
        else:
            return _show_current_location(context)
    
    except Exception as e:
        return ErrorResult(
            errors=[f"Navigation failed: {str(e)}"],
            suggestions=["Check command format and system status"]
        )


# =============================================================================
# 3. Navigation Operations (Different Types of Navigation)
# =============================================================================

def _navigate_up(context: Context) -> HandlerResult:
    """
    Navigate up one level in hierarchy (APP→ORG→SYS).
    
    Args:
        context: Current context
        
    Returns:
        Navigation result or error if already at SYS level
    """
    if is_sys(context):
        return ErrorResult(
            errors=["Already at system level - cannot navigate up"],
            suggestions=["Try navigating to an organization with: cd company_name"]
        )
    
    if is_org(context):
        new_context = _create_context(ContextLevel.SYS)
        return _create_nav_result(
            new_context,
            "Navigated to system level",
            from_context=f"Organization: {context.org_name}",
            context="System Level"
        )
    
    # From APP level, go back to ORG level
    new_context = _create_context(ContextLevel.ORG, context.org_name, context.org_id)
    return _create_nav_result(
        new_context,
        "Navigated to organization level",
        from_context=f"Application: {context.app_id}",
        organization=context.org_name
    )


def _navigate_to_root() -> CommandResult:
    """
    Navigate to system/root level.
    
    Returns:
        Navigation result for root level
    """
    new_context = _create_context(ContextLevel.SYS)
    return _create_nav_result(
        new_context,
        "Navigated to system level",
        context="System Level"
    )


def _navigate_to_org(entity_value: str, entity_model, context: Context) -> HandlerResult:
    """
    Navigate to specific organization by name.
    
    Args:
        entity_value: Organization name to navigate to
        entity_model: Entity model (for determining org type)
        context: Current context
        
    Returns:
        Navigation result or error if organization not found
    """
    # Determine organization type from entity_model if available
    org_type = "organization"
    if entity_model:
        org_type = entity_model.__name__.replace("Entity", "").lower()
    
    # Use intelligent matching to find the company
    actual_company_name = find_company_by_name(entity_value, context)
    if not actual_company_name:
        return ErrorResult(
            errors=[f"Organization '{entity_value}' does not exist"],
            suggestions=["Check organization name spelling or create it first"]
        )
    
    # Create organization level context
    new_context = _create_context(ContextLevel.ORG, actual_company_name, 1)
    return _create_nav_result(
        new_context,
        f"Navigated to {org_type} {actual_company_name}",
        organization=actual_company_name,
        type=org_type
    )


def _show_current_location(context: Context) -> CommandResult:
    """
    Show current location without navigating.
    
    Args:
        context: Current context
        
    Returns:
        CommandResult with current location information
    """
    level_name = get_level_name(context).upper()
    
    if is_sys(context):
        location = "Root"
    elif is_org(context):
        location = f"Organization: {context.org_name}"
    else:
        location = f"Application: {context.app_id}"
    
    return CommandResult(
        success=True,
        message=f"Current location: {location}",
        data={
            "level": level_name,
            "location": location,
            "operation": "current_location"
        }
    )


# =============================================================================
# 4. Utilities (Helper Functions)
# =============================================================================

def _create_context(level: ContextLevel, org_name: Optional[str] = None, org_id: Optional[int] = None) -> NewContext:
    """
    Create a new navigation context.
    
    Args:
        level: Context level (SYS, ORG, or APP)
        org_name: Organization name (for ORG/APP levels)
        org_id: Organization ID (for ORG/APP levels)
        
    Returns:
        New Context object
    """
    return NewContext(
        level=level,
        org_id=org_id,
        org_name=org_name,
        org_db_path=None
    )


def _create_nav_result(
    new_context: NewContext,
    message: str,
    from_context: Optional[str] = None,
    **extra_data
) -> CommandResult:
    """
    Create navigation result with context switch data.
    
    Args:
        new_context: The new context being navigated to
        message: Success message
        from_context: Optional "from" description (e.g., "Organization: ACME")
        **extra_data: Additional data fields to include
        
    Returns:
        CommandResult with standardized navigation data
    """
    # Convert level to string representation for context_switch
    level_str = "SYS"
    if new_context.level == ContextLevel.ORG:
        level_str = "ORG"
    elif new_context.level == ContextLevel.APP:
        level_str = "APP"
    
    data = {
        "level": get_level_name(new_context).upper(),
        "context_switch": {
            "level": level_str,
            "org_id": new_context.org_id,
            "org_name": new_context.org_name,
            "org_db_path": new_context.org_db_path
        }
    }
    
    if from_context:
        data["from"] = from_context
    
    data.update(extra_data)
    
    return CommandResult(success=True, message=message, data=data)