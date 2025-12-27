"""
Navigation handler for VLMX DSL.

Handles context navigation (cd command) between different levels
of the application (SYS, ORG, APP).
"""

from typing import Dict, Any, Optional

async def navigate_handler(entity_model, entity_value, attributes, context, attribute_words=None):
    """
    Dynamic navigation handler for context switching.
    
    Handles commands like:
    - cd ~          (navigate to root/SYS level)
    - cd root       (navigate to root/SYS level) 
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
    from ..models.context import Context as NewContext
    from ..storage.database import company_exists
    
    try:
        # Navigate to root/system level
        if entity_value in ["~", "root", None]:
            new_context = NewContext(
                level=0,
                org_id=None,
                org_name=None,
                org_db_path=None
            )
            
            result = create_success_result(
                operation="navigated",
                entity_name="root",
                attributes={"level": "SYS", "context": "System Level"}
            )
            result.set_context_switch(new_context)
            return result
            
        # Navigate to specific company/organization
        elif entity_value:
            # Check if the company exists
            if not company_exists(entity_value, context):
                return create_error_result([f"Company '{entity_value}' does not exist"])
            
            # Create organization level context
            new_context = NewContext(
                level=1,
                org_id=1,
                org_name=entity_value,
                org_db_path=None
            )
            
            result = create_success_result(
                operation="navigated",
                entity_name=f"company {entity_value}",
                attributes={"level": "ORG", "company": entity_value}
            )
            result.set_context_switch(new_context)
            return result
            
        # Show current location if no target specified
        else:
            level_name = "SYS" if context.level == 0 else "ORG"
            location = "Root" if context.level == 0 else f"Company: {context.org_name}"
            
            return create_success_result(
                operation="current_location",
                entity_name="location",
                attributes={"level": level_name, "location": location}
            )
            
    except Exception as e:
        return create_error_result([f"Navigation failed: {str(e)}"])