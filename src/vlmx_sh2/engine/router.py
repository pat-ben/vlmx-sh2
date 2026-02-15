"""
Router - Command routing and handler execution.

Engine boundary: the Router accepts ONLY stable, serializable IR types and routes
to handlers using an internal registry (not ActionWord.handler).
"""

from __future__ import annotations

from typing import Awaitable, Callable, Dict, Optional

from ..lang.ir.command import IRCommand
from ..core.models.context import Context
from ..core.models.responses import ErrorResult, HandlerResult

# -----------------------------------------------------------------------------
# Handler registry (engine-side)
# -----------------------------------------------------------------------------
# Keep this mapping here (engine layer) so IR stays stable and free of runtime objects.
HandlerFunc = Callable[[IRCommand, Context], Awaitable[HandlerResult]]

_ACTION_HANDLERS: Dict[str, HandlerFunc] = {}


def register_action_handler(action_id: str, handler: HandlerFunc) -> None:
    """Register a handler for an action_id (e.g., 'create', 'show', 'fill')."""
    _ACTION_HANDLERS[action_id] = handler


class Router:
    """
    Routes IR commands to appropriate handlers and manages execution.

    Responsibilities:
    - Validate IR
    - Check handler availability
    - Execute handlers safely
    - Convert exceptions to ErrorResult
    - Return pure data contracts
    """

    @classmethod
    async def dispatch_command(
        cls, ir_command: IRCommand, context: Context
    ) -> HandlerResult:
        """
        Dispatch an IRCommand to its handler.

        Args:
            ir_command: Stable, serializable command IR
            context: Current execution context

        Returns:
            HandlerResult: Data contract from handler or ErrorResult if failed
        """
        # Step 1: Validate action
        if not getattr(ir_command, "action_id", None):
            return ErrorResult(
                errors=["No action specified"],
                suggestions=["Specify an action like 'show', 'create', 'fill', etc."],
            )

        # Step 2: Find handler
        handler_func = cls._get_handler_function(ir_command.action_id)
        if not handler_func:
            return ErrorResult(
                errors=[f"No handler found for action '{ir_command.action_id}'"],
                suggestions=["Check if the action is implemented"],
            )

        # Step 3: Execute handler safely
        try:
            return await handler_func(ir_command, context)
        except Exception as e:
            return ErrorResult(
                errors=[f"Handler execution failed: {str(e)}"],
                suggestions=["Please try again or check your input"],
            )

    @classmethod
    def _get_handler_function(cls, action_id: str) -> Optional[HandlerFunc]:
        """Return the handler registered for this action_id, if any."""
        return _ACTION_HANDLERS.get(action_id)
