"""
Core module for backend/UI isolation.

Provides the single entry point (CommandExecutor), command building logic (CommandBuilder),
and routing logic (Router) to isolate backend business logic from UI presentation layer.
"""

from .executor import CommandExecutor
from .router import Router
from .builder import CommandBuilder

__all__ = ['CommandExecutor', 'Router', 'CommandBuilder']