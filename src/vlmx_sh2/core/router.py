"""
Router - Command routing and handler execution.

Routes parsed commands to appropriate handlers and manages execution flow.
Converts parser results into handler results while maintaining error isolation.
"""

from ..models.context import Context
from ..models.parser import ParseResult
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
    async def dispatch(cls, parse_result: ParseResult, context: Context) -> HandlerResult:
        """
        Dispatch a parsed command to its handler.
        
        Args:
            parse_result: Result from Parser.parse()
            context: Current execution context
            
        Returns:
            HandlerResult: Data contract from handler or ErrorResult if failed
        """
        # Step 1: Check for parse errors
        if not parse_result.is_valid or parse_result.errors:
            return ErrorResult(
                errors=parse_result.errors or ["Invalid command"],
                suggestions=parse_result.suggestions or []
            )
        
        # Step 2: Ensure we have a parsed command
        if not parse_result.command:
            return ErrorResult(
                errors=["No valid command found"],
                suggestions=parse_result.suggestions or ["Check command syntax"]
            )
        
        # Step 3: Check if action handler exists
        if not hasattr(parse_result.command, 'action') or not parse_result.command.action:
            return ErrorResult(
                errors=["No action specified"],
                suggestions=["Specify an action like 'show', 'create', 'fill', etc."]
            )
        
        # Step 4: Get the handler function
        handler_func = cls._get_handler_function(parse_result.command.action)
        if not handler_func:
            action_name = getattr(parse_result.command.action, 'id', str(parse_result.command.action))
            return ErrorResult(
                errors=[f"No handler found for action '{action_name}'"],
                suggestions=["Check if the action is implemented"]
            )
        
        # Step 5: Execute handler safely
        try:
            result = await handler_func(parse_result.command, context)
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