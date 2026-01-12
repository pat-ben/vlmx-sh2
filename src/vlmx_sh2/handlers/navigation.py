"""
Navigation handler.

Handles context navigation (cd command) between different levels
of the application (SYS, ORG, APP).
"""


from ..models.context import Context
from ..models.responses import HandlerResult
from ..models.parser.parsed_command import ParsedCommand
from ..utils.context_helpers import is_sys, is_org, is_app, get_level_name

# Navigation command aliases
ROOT_NAVIGATION_ALIASES = {"~", "root", None}
UP_NAVIGATION_ALIASES = {".."}  # Go up one level in context hierarchy


async def navigate_handler(parsed_command: ParsedCommand, context: Context) -> HandlerResult:
    """
    Handler for 'cd' command - manages context navigation between system levels.
    
    Provides hierarchical navigation through the system's three-tier context structure:
    SYS (system) → ORG (organization) → APP (application). Supports various navigation
    patterns including relative navigation (..), absolute navigation (~, root), and
    direct organization targeting by name.
    
    Navigation patterns:
    - cd ~          : Navigate to root/SYS level from any context
    - cd root       : Navigate to root/SYS level from any context 
    - cd ..         : Navigate up one level in hierarchy (APP→ORG→SYS)
    - cd company    : Navigate to specific organization by name (with fuzzy matching)
    
    Args:
        parsed_command: Parsed command containing navigation target and parameters
        context: Current execution context defining current position in hierarchy
        
    Returns:
        CommandResult with navigation outcome and new context data, or ErrorResult on failure
        
    Raises:
        Returns ErrorResult for invalid navigation attempts, missing organizations, or system errors
    """
    from ..models.responses import CommandResult, ErrorResult
    from ..models.context import Context as NewContext
    from ..enums.core import ContextLevel
    from ..storage.database import find_company_by_name
    
    try:
        # Extract parameters from parsed_command
        entity_model = parsed_command.entity_model
        entity_value = parsed_command.target_name  # For navigation, this is the target (company name, etc.)
        
        # Navigate up one level in context hierarchy
        if entity_value in UP_NAVIGATION_ALIASES:
            # If already at SYS level, can't go up further
            if is_sys(context):
                return ErrorResult(
                    errors=["Already at system level - cannot navigate up"],
                    suggestions=["Try navigating to an organization with: cd company_name"]
                )
            
            # From ORG level, go back to SYS level
            if is_org(context):
                new_context = NewContext(
                    level=ContextLevel.SYS,
                    org_id=None,
                    org_name=None,
                    org_db_path=None
                )
                
                result = CommandResult(
                    success=True,
                    message="Navigated to system level",
                    data={
                        "level": get_level_name(new_context).upper(),
                        "context": "System Level",
                        "from": f"Organization: {context.org_name}",
                        "context_switch": {
                            "level": "SYS",
                            "org_id": None,
                            "org_name": None,
                            "org_db_path": None
                        }
                    }
                )
                return result
            
            # From APP level, go back to ORG level
            if is_app(context):
                new_context = NewContext(
                    level=ContextLevel.ORG,
                    org_id=context.org_id,
                    org_name=context.org_name,
                    org_db_path=context.org_db_path
                )
                
                result = CommandResult(
                    success=True,
                    message="Navigated to organization level",
                    data={
                        "level": get_level_name(new_context).upper(),
                        "organization": context.org_name,
                        "from": f"Application: {context.app_id}",
                        "context_switch": {
                            "level": "ORG",
                            "org_id": context.org_id,
                            "org_name": context.org_name,
                            "org_db_path": context.org_db_path
                        }
                    }
                )
                return result
        
        # Navigate to root/system level
        elif entity_value in ROOT_NAVIGATION_ALIASES:
            new_context = NewContext(
                level=ContextLevel.SYS,
                org_id=None,
                org_name=None,
                org_db_path=None
            )
            
            result = CommandResult(
                success=True,
                message="Navigated to system level",
                data={
                    "level": get_level_name(new_context).upper(),
                    "context": "System Level",
                    "context_switch": {
                        "level": "SYS",
                        "org_id": None,
                        "org_name": None,
                        "org_db_path": None
                    }
                }
            )
            return result
            
        # Navigate to specific organization
        elif entity_value:
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
            
            # Create organization level context using the actual company name
            new_context = NewContext(
                level=ContextLevel.ORG,
                org_id=1,
                org_name=actual_company_name,
                org_db_path=None
            )
            
            result = CommandResult(
                success=True,
                message=f"Navigated to {org_type} {actual_company_name}",
                data={
                    "level": get_level_name(new_context).upper(),
                    "organization": actual_company_name,
                    "type": org_type,
                    "context_switch": {
                        "level": "ORG",
                        "org_id": 1,
                        "org_name": actual_company_name,
                        "org_db_path": None
                    }
                }
            )
            return result
            
        # Show current location if no target specified
        else:
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
            
    except Exception as e:
        return ErrorResult(
            errors=[f"Navigation failed: {str(e)}"],
            suggestions=["Check command format and system status"]
        )
    
    # Fallback return (should not reach here)
    return ErrorResult(
        errors=["Unknown navigation error"],
        suggestions=["Check command format"]
    )