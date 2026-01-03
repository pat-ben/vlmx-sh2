"""
Navigation handler for VLMX DSL.

Handles context navigation (cd command) between different levels
of the application (SYS, ORG, APP).
"""

# Navigation command aliases
ROOT_NAVIGATION_ALIASES = {"~", "root", None}
UP_NAVIGATION_ALIASES = {".."}  # Go up one level in context hierarchy


async def navigate_handler(entity_model, entity_value, fields, context, field_words=None, parsed_command=None):
    """
    Dynamic navigation handler for context switching.
    
    Handles commands like:
    - cd ~          (navigate to root/SYS level)
    - cd root       (navigate to root/SYS level) 
    - cd ..         (navigate up one level in hierarchy)
    - cd company    (navigate to company if specified)
    
    Args:
        entity_model: Not used for navigation
        entity_value: Navigation target (company name, ~, root, etc.)
        fields: Additional navigation parameters
        context: Current execution context
        field_words: Not used for navigation
        
    Returns:
        Result dictionary with navigation outcome
    """
    from ..models.results import CommandResult, ErrorResult
    from ..models.context import Context as NewContext, ContextLevel
    from ..storage.database import find_company_by_name
    
    try:
        # Navigate up one level in context hierarchy
        if entity_value in UP_NAVIGATION_ALIASES:
            # If already at SYS level, can't go up further
            if context.level == ContextLevel.SYS:
                return ErrorResult(
                    errors=["Already at system level - cannot navigate up"],
                    suggestions=["Try navigating to an organization with: cd company_name"]
                )
            
            # From ORG level, go back to SYS level
            if context.level == ContextLevel.ORG:
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
                        "level": new_context.level_name.upper(),
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
            if context.level == ContextLevel.APP:
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
                        "level": new_context.level_name.upper(),
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
                    "level": new_context.level_name.upper(),
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
                    "level": new_context.level_name.upper(),
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
            level_name = context.level_name.upper()
            if context.level == ContextLevel.SYS:
                location = "Root"
            elif context.level == ContextLevel.ORG:
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