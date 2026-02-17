"""
App handlers for views and tools.

Engine boundary: these handlers accept stable IR directly.
"""

from ...core.models.context import Context
from ...core.models.responses import CommandResult, ErrorResult, HandlerResult
from ...dsl.ir.command import IRCommand, IRTargetKind
from .utils import validate_target_context, validate_target_exists


async def apply_handler(ir_command: IRCommand, context: Context) -> HandlerResult:
    """Apply/activate a view filter."""
    error = validate_target_exists(ir_command)
    if error:
        return error

    context_error = validate_target_context(
        ir_command.target.kind, ir_command.target.id, context
    )
    if context_error:
        return context_error

    if ir_command.target.kind != IRTargetKind.VIEW:
        return ErrorResult(
            errors=["'apply' only works with views"],
            suggestions=["Use 'apply <view_name>' (e.g., 'apply neco')"],
        )

    from ...dsl.words.registry import VIEW_WORDS

    view = VIEW_WORDS.get(ir_command.target.id)
    if not view:
        return ErrorResult(
            errors=[f"View '{ir_command.target.id}' not found"],
            suggestions=[f"Available views: {', '.join(VIEW_WORDS.keys())}"],
        )

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
    error = validate_target_exists(ir_command)
    if error:
        return error

    context_error = validate_target_context(
        ir_command.target.kind, ir_command.target.id, context
    )
    if context_error:
        return context_error

    if ir_command.target.kind != IRTargetKind.TOOL:
        return ErrorResult(
            errors=["'run' only works with tools"],
            suggestions=["Use 'run <tool_name>' (e.g., 'run dcf')"],
        )

    from ...dsl.words.registry import TOOL_WORDS

    tool = TOOL_WORDS.get(ir_command.target.id)
    if not tool:
        return ErrorResult(
            errors=[f"Tool '{ir_command.target.id}' not found"],
            suggestions=[f"Available tools: {', '.join(TOOL_WORDS.keys())}"],
        )

    provided_params = dict(ir_command.assignments)
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
