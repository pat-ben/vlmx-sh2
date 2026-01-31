"""
CommandExecutor - Single entry point for backend command processing.

This class serves as the main interface between the UI layer and backend logic.
It coordinates parsing and routing while maintaining complete isolation from UI concerns.
"""

from typing import Union, Dict, Any, Optional
from ..models.context import Context
from ..models.responses import HandlerResult, ErrorResult
from ..parser.parser import Parser
from ..parser.builder import Builder
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
    
    @classmethod
    async def execute_from_wizard(
        cls, 
        action_id: str,
        entity_id: str,
        entity_name: Optional[str],
        field_values: Dict[str, Any],
        record_id: Optional[str],
        context: Context
    ) -> HandlerResult:
        """
        Execute a command from wizard form submission data.
        
        This method enables wizard submissions to use the same unified command
        pipeline as standard text commands. It converts wizard data to a 
        ParsedCommand and routes it through the same execution flow.
        
        Args:
            action_id: The action to perform (e.g., "add", "update")
            entity_id: The entity type (e.g., "organization", "brand") 
            entity_name: Optional entity name/target name
            field_values: Form data submitted by user
            record_id: For updates, the ID of record being updated
            context: Current execution context
            
        Returns:
            HandlerResult: Same as execute() - CommandResult, ErrorResult, 
                         FormRequest, or PickerRequest that UI can render
        """
        try:
            # Step 1: Build ParsedCommand from wizard data
            parsed_command = Builder.from_wizard(
                action_id=action_id,
                entity_id=entity_id,
                entity_name=entity_name,
                field_values=field_values,
                record_id=record_id
            )
            
            # Step 2: Check if command building was successful
            if not parsed_command:
                return ErrorResult(
                    errors=[f"Failed to build command from wizard data"],
                    suggestions=[
                        f"Check that action '{action_id}' and entity '{entity_id}' are valid",
                        "Verify form data is properly formatted"
                    ]
                )
            
            # Step 3: Create a ParseResult-like structure for Router
            # We need to create a minimal ParseResult to pass to Router.dispatch
            from ..models.parser.parsing import ParseResult
            parse_result = ParseResult(
                input_text=f"[WIZARD] {action_id} {entity_id}",
                command_tokens=[],
                filter_tokens=[],
                command=parsed_command,
                is_valid=True,
                errors=[],
                suggestions=[]
            )
            
            # Step 4: Route and execute through Router (same as standard flow)
            return await Router.dispatch(parse_result, context)
            
        except Exception as e:
            # Catch ANY unexpected errors and wrap in ErrorResult
            return ErrorResult(
                errors=[f"Unexpected error in wizard execution: {str(e)}"],
                suggestions=[
                    "Please try again or check your form input",
                    "If the problem persists, try using the text command interface"
                ]
            )