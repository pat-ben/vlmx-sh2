
from enum import Enum
from typing import Optional, Callable
from ..models.parser import ParsedCommand, ParseResult

class RouteType(Enum):
    """Types of routes the command can take."""
    DIRECT = "direct"           # Execute handler immediately
    FORM_WIZARD = "form_wizard" # Show interactive form first
    QUERY_WIZARD = "query_wizard" # Show query builder first (future)

class RouteDecision:
    """Represents the routing decision for a command."""
    
    def __init__(
        self,
        route_type: RouteType,
        parsed_command: ParsedCommand,
        handler: Optional[Callable] = None,
        wizard_config: Optional[dict] = None
    ):
        self.route_type = route_type
        self.parsed_command = parsed_command
        self.handler = handler
        self.wizard_config = wizard_config

class CommandRouter:
    """
    Routes parsed commands to appropriate execution paths.
    
    Determines whether a command should:
    1. Execute directly (normal flow)
    2. Show a form wizard first
    3. Show a query wizard first (future)
    """
    
    def route(self, parse_result: ParseResult) -> RouteDecision:
        """
        Determine the route for a parsed command.
        
        Args:
            parse_result: Result from VLMXParser
            
        Returns:
            RouteDecision indicating what should happen next
        """
        # Implementation to come...