"""
Navigation handler for VLMX DSL.

Handles context navigation (cd command) between different levels
of the application (SYS, ORG, APP).
"""

# Navigation command aliases
ROOT_NAVIGATION_ALIASES = {"~", "root", None}
UP_NAVIGATION_ALIASES = {".."}  # Go up one level in context hierarchy


async def navigate_handler(entity_model, entity_value, attributes, context, attribute_words=None):
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
        attributes: Additional navigation parameters
        context: Current execution context
        attribute_words: Not used for navigation
        
    Returns:
        Result dictionary with navigation outcome
    """
    from ..ui.results import create_success_result, create_error_result
    from ..models.context import Context as NewContext, ContextLevel
    from ..storage.database import company_exists, find_company_by_name
    
    try:
        # Navigate up one level in context hierarchy
        if entity_value in UP_NAVIGATION_ALIASES:
            # If already at SYS level, can't go up further
            if context.level == ContextLevel.SYS:
                return create_error_result([f"Already at system level - cannot navigate up"])
            
            # From ORG level, go back to SYS level
            if context.level == ContextLevel.ORG:
                new_context = NewContext(
                    level=ContextLevel.SYS,
                    org_id=None,
                    org_name=None,
                    org_db_path=None
                )
                
                result = create_success_result(
                    operation="navigated",
                    entity_name="up",
                    attributes={"level": new_context.level_name.upper(), "context": "System Level", "from": f"Organization: {context.org_name}"}
                )
                result.set_context_switch(new_context)
                return result
            
            # From APP level, go back to ORG level
            if context.level == ContextLevel.APP:
                new_context = NewContext(
                    level=ContextLevel.ORG,
                    org_id=context.org_id,
                    org_name=context.org_name,
                    org_db_path=context.org_db_path
                )
                
                result = create_success_result(
                    operation="navigated",
                    entity_name="up",
                    attributes={"level": new_context.level_name.upper(), "organization": context.org_name, "from": f"Application: {context.app_id}"}
                )
                result.set_context_switch(new_context)
                return result
        
        # Navigate to root/system level
        elif entity_value in ROOT_NAVIGATION_ALIASES:
            new_context = NewContext(
                level=ContextLevel.SYS,
                org_id=None,
                org_name=None,
                org_db_path=None
            )
            
            result = create_success_result(
                operation="navigated",
                entity_name="root",
                attributes={"level": new_context.level_name.upper(), "context": "System Level"}
            )
            result.set_context_switch(new_context)
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
                return create_error_result([f"Organization '{entity_value}' does not exist"])
            
            # Create organization level context using the actual company name
            new_context = NewContext(
                level=ContextLevel.ORG,
                org_id=1,
                org_name=actual_company_name,
                org_db_path=None
            )
            
            result = create_success_result(
                operation="navigated",
                entity_name=f"{org_type} {actual_company_name}",
                attributes={"level": new_context.level_name.upper(), "organization": actual_company_name, "type": org_type}
            )
            result.set_context_switch(new_context)
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
            
            return create_success_result(
                operation="current_location",
                entity_name="location",
                attributes={"level": level_name, "location": location}
            )
            
    except Exception as e:
        return create_error_result([f"Navigation failed: {str(e)}"])