# D:\Code\vlmx-sh2\src\vlmx_sh2\router\decision.py
"""
Route decision model for VLMX DSL.

Represents the routing decision made by CommandRouter, containing all
information needed to execute the chosen path.
"""

from typing import Optional, Callable, Dict, Any
from .enums import RouteType
from ..models.parser import ParsedCommand


class RouteDecision:
    """
    Represents the routing decision for a command.
    
    Contains all information needed to execute the chosen route,
    including the parsed command, handler reference, and any
    wizard-specific configuration.
    
    Attributes:
        route_type: Type of route (DIRECT, FORM_WIZARD, etc.)
        parsed_command: The parsed command (may be None for error cases)
        handler: Handler function for direct execution
        wizard_config: Configuration dict for wizard screens
        error_context: Context about parse errors (for SUPPORT_WIZARD)
    
    Examples:
        >>> # Direct execution decision
        >>> decision = RouteDecision(
        ...     route_type=RouteType.DIRECT,
        ...     parsed_command=command,
        ...     handler=add_brand_handler
        ... )
        
        >>> # Form wizard decision
        >>> decision = RouteDecision(
        ...     route_type=RouteType.FORM_WIZARD,
        ...     parsed_command=command,
        ...     wizard_config={'fields': ['vision', 'mission']}
        ... )
        
        >>> # Error with support wizard
        >>> decision = RouteDecision(
        ...     route_type=RouteType.SUPPORT_WIZARD,
        ...     error_context={'errors': ['Invalid action']}
        ... )
    """
    
    def __init__(
        self,
        route_type: RouteType,
        parsed_command: Optional[ParsedCommand] = None,
        handler: Optional[Callable] = None,
        wizard_config: Optional[Dict[str, Any]] = None,
        error_context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize route decision.
        
        Args:
            route_type: Type of route to take
            parsed_command: The parsed command (may be None for some wizards)
            handler: Handler function to execute (for DIRECT route)
            wizard_config: Configuration for wizard screens
            error_context: Context about errors (for SUPPORT_WIZARD)
        """
        self.route_type = route_type
        self.parsed_command = parsed_command
        self.handler = handler
        self.wizard_config = wizard_config or {}
        self.error_context = error_context or {}
    
    # ==================== HELPER PROPERTIES ====================
    
    @property
    def is_direct(self) -> bool:
        """Check if this is a direct execution route."""
        return self.route_type == RouteType.DIRECT
    
    @property
    def is_wizard(self) -> bool:
        """Check if this is any kind of wizard route."""
        return self.route_type in [
            RouteType.FORM_WIZARD,
            RouteType.QUERY_WIZARD,
            RouteType.SUPPORT_WIZARD
        ]
    
    @property
    def needs_form(self) -> bool:
        """Check if this route requires form display."""
        return self.route_type == RouteType.FORM_WIZARD
    
    @property
    def needs_query_builder(self) -> bool:
        """Check if this route requires query builder (future)."""
        return self.route_type == RouteType.QUERY_WIZARD
    
    @property
    def needs_support(self) -> bool:
        """Check if this route requires support/error recovery."""
        return self.route_type == RouteType.SUPPORT_WIZARD
    
    @property
    def has_error(self) -> bool:
        """Check if this decision contains error context."""
        return bool(self.error_context)
    
    @property
    def can_execute(self) -> bool:
        """Check if this decision can be executed directly."""
        return self.is_direct and self.handler is not None
    
    # ==================== STRING REPRESENTATION ====================
    
    def __repr__(self) -> str:
        parts = [f"RouteDecision(route_type={self.route_type.value}"]
        
        if self.parsed_command:
            parts.append(f"command={self.parsed_command.action.id}")
        
        if self.handler:
            parts.append(f"handler={self.handler.__name__}")
        
        if self.wizard_config:
            parts.append(f"wizard_config={list(self.wizard_config.keys())}")
        
        if self.error_context:
            parts.append(f"has_errors=True")
        
        return ", ".join(parts) + ")"