"""
Router - Command routing and handler execution.

Routes parsed commands to appropriate handlers and manages execution flow.
Converts parser results into handler results while maintaining error isolation.
"""

from ..models.context import Context
from ..models.responses import HandlerResult, ErrorResult


class Router:
    """
    Routes parsed commands to appropriate handlers and manages execution.
    
    Responsibilities:
    - Validate parse results
    - Check handler availability  
    - Execute handlers safely
    - Convert exceptions to ErrorResult
    - Return pure data contracts
    """
    
    @classmethod
    async def dispatch_command(cls, parsed_command, context: Context) -> HandlerResult:
        """
        Dispatch a ParsedCommand directly to its handler without ParseResult wrapper.
        
        Args:
            parsed_command: ParsedCommand instance
            context: Current execution context
            
        Returns:
            HandlerResult: Data contract from handler or ErrorResult if failed
        """
        # Step 1: Check if action handler exists
        if not hasattr(parsed_command, 'action') or not parsed_command.action:
            return ErrorResult(
                errors=["No action specified"],
                suggestions=["Specify an action like 'show', 'create', 'fill', etc."]
            )
        
        # Step 2: Get the handler function
        handler_func = cls._get_handler_function(parsed_command.action)
        if not handler_func:
            action_name = getattr(parsed_command.action, 'id', str(parsed_command.action))
            return ErrorResult(
                errors=[f"No handler found for action '{action_name}'"],
                suggestions=["Check if the action is implemented"]
            )
        
        # Step 3: Execute handler safely
        try:
            result = await handler_func(parsed_command, context)
            return result
            
        except Exception as e:
            return ErrorResult(
                errors=[f"Handler execution failed: {str(e)}"],
                suggestions=["Please try again or check your input"]
            )
    
    @classmethod
    def _get_handler_function(cls, action_word):
        """
        Get the handler function from the action word.
        
        ActionWord objects already contain their handler function,
        so we just return it directly. This eliminates the need for
        duplicated handler mappings.
        """
        return getattr(action_word, 'handler', None)