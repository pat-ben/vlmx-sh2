"""
Core module for backend/UI isolation.

Provides the single entry point (CommandExecutor) and routing logic (Router)
to isolate backend business logic from UI presentation layer.
"""

from .executor import CommandExecutor
from .router import Router

__all__ = ['CommandExecutor', 'Router']