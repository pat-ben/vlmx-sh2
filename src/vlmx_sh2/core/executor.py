"""
CommandExecutor - Single entry point for backend command processing.

This class serves as the main interface between the UI layer and backend logic.
It coordinates parsing and routing while maintaining complete isolation from UI concerns.
"""

from typing import Union
from ..models.context import Context
from ..models.responses import HandlerResult, ErrorResult
from ..parser.parser import Parser
from .router import Router


class CommandExecutor:
    """
    Single entry point for command execution that isolates backend from UI.
    
    The UI layer should only interact with the backend through this class.
    All parsing, validation, routing, and execution happens here, returning
    pure data contracts that the UI can render without business logic knowledge.
    """
    
    @classmethod
    async def execute(cls, input_text: str, context: Context) -> HandlerResult:
        """
        Execute a command from raw text input.
        
        This is the ONLY method the UI should call for command processing.
        It handles the entire pipeline: parsing -> validation -> routing -> execution.
        
        Args:
            input_text: Raw command text from user
            context: Current execution context (org, system level, etc.)
            
        Returns:
            HandlerResult: Pure data contract (CommandResult, ErrorResult, 
                         FormRequest, PickerRequest) that UI can render
        """
        try:
            # Step 1: Parse the input text
            parse_result = Parser.parse(input_text)
            
            # Step 2: Route and execute through Router
            return await Router.dispatch(parse_result, context)
            
        except Exception as e:
            # Catch ANY unexpected errors and wrap in ErrorResult
            return ErrorResult(
                errors=[f"Unexpected error: {str(e)}"],
                suggestions=["Please try again or check command syntax"]
            )