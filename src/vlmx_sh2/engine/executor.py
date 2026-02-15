"""
CommandExecutor - Single entry point for backend command processing.

This class serves as the main interface between the UI layer and backend logic.
It coordinates parsing, lowering to stable IR, and engine dispatch while maintaining
complete isolation from UI concerns.
"""

from typing import Any, Dict, Optional

from ..lang.ir.lowering import lower_from_tokens_result, lower_from_wizard
from ..lang.parser.parser import Parser
from ..models.context import Context
from ..models.responses import ErrorResult, HandlerResult
from .router import Router


class CommandExecutor:
    """
    Single entry point for command execution that isolates backend from UI.

    The UI layer should only interact with the backend through this class.
    The execution pipeline is:

        raw input / wizard -> parser (stages 0-6) -> AST (filters) -> IR -> engine

    The engine boundary accepts ONLY IR.
    """

    @classmethod
    async def execute(cls, input_text: str, context: Context) -> HandlerResult:
        """
        Execute a command from raw text input.

        This is the ONLY method the UI should call for command processing.
        It handles the entire pipeline: parsing -> lowering (IR) -> routing -> execution.
        """
        try:
            # Step 1: Parse the input text (stages 0-6)
            tokens_result = Parser.parse(input_text, context)

            # Step 2: Check for parsing errors
            if not tokens_result.is_valid:
                return ErrorResult(
                    errors=tokens_result.errors, suggestions=tokens_result.suggestions
                )

            # Step 3: Lower to stable IR (Intermediate Layer)
            ir_command = lower_from_tokens_result(tokens_result, raw_input=input_text)
            if not ir_command:
                return ErrorResult(
                    errors=["Failed to lower command into IR"],
                    suggestions=["Check command syntax"],
                )

            # Step 4: Route and execute through engine
            return await Router.dispatch_command(ir_command, context)

        except Exception as e:
            # Catch ANY unexpected errors and wrap in ErrorResult
            return ErrorResult(
                errors=[f"Unexpected error: {str(e)}"],
                suggestions=["Please try again or check command syntax"],
            )

    @classmethod
    async def execute_from_wizard(
        cls,
        action_id: str,
        entity_id: str,
        entity_name: Optional[str],
        field_values: Dict[str, Any],
        record_id: Optional[str],
        context: Context,
    ) -> HandlerResult:
        """
        Execute a command from wizard form submission data.

        Wizard submissions are lowered directly into IR so they use the exact same
        engine interface as text commands.
        """
        try:
            # Step 1: Lower wizard submission into stable IR
            ir_command = lower_from_wizard(
                action_id=action_id,
                entity_id=entity_id,
                entity_name=entity_name,
                field_values=field_values,
                record_id=record_id,
            )

            # Step 2: Check if lowering was successful
            if not ir_command:
                return ErrorResult(
                    errors=["Failed to lower wizard submission into IR"],
                    suggestions=[
                        f"Check that action '{action_id}' and entity '{entity_id}' are valid",
                        "Verify form data is properly formatted",
                    ],
                )

            # Step 3: Route and execute through engine
            return await Router.dispatch_command(ir_command, context)

        except Exception as e:
            # Catch ANY unexpected errors and wrap in ErrorResult
            return ErrorResult(
                errors=[f"Unexpected error in wizard execution: {str(e)}"],
                suggestions=[
                    "Please try again or check your form input",
                    "If the problem persists, try using the text command interface",
                ],
            )
