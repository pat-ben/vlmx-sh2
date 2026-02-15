"""
App handlers for views and tools.

Engine boundary: these handlers accept stable IR and may adapt to legacy ParsedCommand
internals during the migration.
"""

from ...lang.ir.command import IRCommand
from ...models.context import Context
from ...models.responses import CommandResult, ErrorResult, HandlerResult
from ...models.words import ToolWord, ViewWord
from ..legacy_adapter import to_legacy_parsed_command
from .utils import validate_target_context, validate_target_exists


async def apply_handler(ir_command: IRCommand, context: Context) -> HandlerResult:
    """Apply/activate a view filter."""
    parsed_command = to_legacy_parsed_command(ir_command)

    error = validate_target_exists(parsed_command)
    if error:
        return error

    context_error = validate_target_context(parsed_command.target, context)
    if context_error:
        return context_error

    if not isinstance(parsed_command.target, ViewWord):
        return ErrorResult(
            errors=["'apply' only works with views"],
            suggestions=["Use 'apply <view_name>' (e.g., 'apply neco')"],
        )

    view = parsed_command.target
    return CommandResult(
        success=True,
        message=f"Applied view: {view.id}",
        data={
            "view_id": view.id,
            "description": view.description,
            "visible_entities": view.entities,
        },
    )


async def run_handler(ir_command: IRCommand, context: Context) -> HandlerResult:
    """Execute a calculation tool."""
    parsed_command = to_legacy_parsed_command(ir_command)

    error = validate_target_exists(parsed_command)
    if error:
        return error

    context_error = validate_target_context(parsed_command.target, context)
    if context_error:
        return context_error

    if not isinstance(parsed_command.target, ToolWord):
        return ErrorResult(
            errors=["'run' only works with tools"],
            suggestions=["Use 'run <tool_name>' (e.g., 'run dcf')"],
        )

    tool = parsed_command.target
    provided_params = parsed_command.field_values or {}
    missing_params = [p for p in tool.parameters if p not in provided_params]

    if missing_params:
        return CommandResult(
            success=True,
            message=f"Tool '{tool.id}' requires parameters",
            data={
                "tool_id": tool.id,
                "required_parameters": tool.parameters,
                "missing_parameters": missing_params,
                "provided_parameters": provided_params,
                "needs_wizard": True,
            },
        )

    return CommandResult(
        success=True,
        message=f"Running tool: {tool.id}",
        data={
            "tool_id": tool.id,
            "parameters": provided_params,
            "result": "Tool execution not yet implemented",
        },
    )
