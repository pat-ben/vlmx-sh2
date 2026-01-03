# D:\Code\vlmx-sh2\src\vlmx_sh2\router\command_router.py
"""
Command router for VLMX DSL.

Routes parsed commands to appropriate execution paths based on:
- Parse success/failure
- Action word requirements (form, query)
- Router configuration (support wizard)
"""

from typing import Optional, List
from .enums import RouteType
from .config import RouterConfig
from .decision import RouteDecision
from ..models.parser import ParsedCommand, ParseResult


class CommandRouter:
    """
    Routes parsed commands to appropriate execution paths.
    
    Decision tree:
    1. Parse failed? 
       → Support Wizard (if enabled) or Direct with error
    2. Action requires form? 
       → Form Wizard
    3. Action requires query builder? 
       → Query Wizard (future)
    4. Otherwise 
       → Direct execution
    
    Examples:
        >>> # Basic usage with default config
        >>> router = CommandRouter()
        >>> decision = router.route(parse_result)
        
        >>> # With support wizard enabled
        >>> config = RouterConfig(support_wizard_enabled=True)
        >>> router = CommandRouter(config)
        >>> decision = router.route(parse_result)
        >>> if decision.needs_support:
        ...     show_support_wizard(decision.error_context)
    """
    
    def __init__(self, config: Optional[RouterConfig] = None):
        """
        Initialize command router.
        
        Args:
            config: Router configuration (uses defaults if None)
        """
        self.config = config or RouterConfig()
    
    def route(self, parse_result: ParseResult) -> RouteDecision:
        """
        Determine the route for a parsed command.
        
        Args:
            parse_result: Result from VLMXParser
            
        Returns:
            RouteDecision indicating what should happen next
            
        Examples:
            >>> # Valid command with form action
            >>> result = parser.parse("fill brand vision mission")
            >>> decision = router.route(result)
            >>> decision.route_type
            RouteType.FORM_WIZARD
            
            >>> # Valid standard command
            >>> result = parser.parse("add brand vision='Test'")
            >>> decision = router.route(result)
            >>> decision.route_type
            RouteType.DIRECT
            
            >>> # Invalid command with support wizard enabled
            >>> result = parser.parse("invalid command")
            >>> decision = router.route(result)
            >>> decision.route_type  # If support_wizard_enabled=True
            RouteType.SUPPORT_WIZARD
        """
        # ROUTE 1: Check if parse failed
        if not parse_result.is_valid:
            return self._route_failed_parse(parse_result)
        
        # At this point, we have a valid ParsedCommand
        command = parse_result.command
        
        # ROUTE 2: Check if action requires a form wizard
        if self._requires_form_wizard(command):
            return self._route_to_form_wizard(command, parse_result)
        
        # ROUTE 3: Check if action requires query wizard (future)
        if self._requires_query_wizard(command):
            return self._route_to_query_wizard(command, parse_result)
        
        # ROUTE 4: Default - direct execution
        return self._route_to_direct_execution(command, parse_result)
    
    # ==================== ROUTE DECISION METHODS ====================
    
    def _route_failed_parse(self, parse_result: ParseResult) -> RouteDecision:
        """
        Route a failed parse result.
        
        If support wizard is enabled, route to support wizard.
        Otherwise, route to direct execution with error display.
        
        Args:
            parse_result: Failed parse result
            
        Returns:
            RouteDecision for handling the failure
        """
        error_context = {
            'errors': parse_result.errors,
            'suggestions': parse_result.suggestions,
            'input_text': parse_result.input_text,
            'tokens': parse_result.tokens
        }
        
        if self.config.support_wizard_enabled:
            # Route to support wizard for interactive error recovery
            return RouteDecision(
                route_type=RouteType.SUPPORT_WIZARD,
                parsed_command=None,
                error_context=error_context,
                wizard_config={
                    'show_suggestions': self.config.auto_suggest_on_error,
                    'error_messages': parse_result.errors,
                    'suggested_fixes': parse_result.suggestions
                }
            )
        else:
            # Direct route - will display error message
            return RouteDecision(
                route_type=RouteType.DIRECT,
                parsed_command=None,
                error_context=error_context
            )
    
    def _route_to_form_wizard(
        self,
        command: ParsedCommand,
        parse_result: ParseResult
    ) -> RouteDecision:
        """
        Route to form wizard.
        
        Prepares wizard configuration with:
        - Entity information
        - Fields to display
        - Pre-filled values (if any)
        - Validation rules
        
        Args:
            command: Parsed command
            parse_result: Full parse result
            
        Returns:
            RouteDecision for form wizard
        """
        form_fields = self._extract_form_fields(command)
        
        wizard_config = {
            'entity': command.entity,
            'entity_name': command.entity_name,
            'fields': form_fields,
            'pre_filled_values': command.attributes,
            'validation_strict': self.config.form_validation_strict,
            'title': f"Fill {command.entity.id.title()} Information"
        }
        
        return RouteDecision(
            route_type=RouteType.FORM_WIZARD,
            parsed_command=command,
            wizard_config=wizard_config
        )
    
    def _route_to_query_wizard(
        self,
        command: ParsedCommand,
        parse_result: ParseResult
    ) -> RouteDecision:
        """
        Route to query wizard (future implementation).
        
        Args:
            command: Parsed command
            parse_result: Full parse result
            
        Returns:
            RouteDecision for query wizard
        """
        wizard_config = {
            'entity': command.entity,
            'query_type': 'select',  # select, filter, aggregate, etc.
        }
        
        return RouteDecision(
            route_type=RouteType.QUERY_WIZARD,
            parsed_command=command,
            wizard_config=wizard_config
        )
    
    def _route_to_direct_execution(
        self,
        command: ParsedCommand,
        parse_result: ParseResult
    ) -> RouteDecision:
        """
        Route to direct execution.
        
        For standard commands that don't need wizards,
        prepare for immediate handler execution.
        
        Args:
            command: Parsed command
            parse_result: Full parse result
            
        Returns:
            RouteDecision for direct execution
        """
        # Get handler from action (assuming action has handler reference)
        handler = getattr(command.action, 'handler', None)
        
        return RouteDecision(
            route_type=RouteType.DIRECT,
            parsed_command=command,
            handler=handler
        )
    
    # ==================== REQUIREMENT CHECK METHODS ====================
    
    def _requires_form_wizard(self, command: ParsedCommand) -> bool:
        """
        Check if command requires a form wizard.
        
        A command requires a form wizard if:
        1. The action word has requires_form=True (e.g., "fill")
        2. The entity has defined form fields
        
        Args:
            command: Parsed command to check
            
        Returns:
            True if form wizard is required
        """
        if not hasattr(command.action, 'requires_form'):
            return False
        
        return command.action.requires_form
    
    def _requires_query_wizard(self, command: ParsedCommand) -> bool:
        """
        Check if command requires a query wizard.
        
        A command requires a query wizard if:
        1. The action word is related to querying (e.g., "query", "search", "find")
        2. Complex query building would benefit from interactive UI
        
        Args:
            command: Parsed command to check
            
        Returns:
            True if query wizard is required
            
        Note:
            This is a placeholder for future implementation.
            Currently always returns False.
        """
        # Future implementation
        # Check for query-related actions like: query, search, find, filter
        return False
    
    # ==================== HELPER METHODS ====================
    
    def _extract_form_fields(self, command: ParsedCommand) -> List[str]:
        """
        Extract form fields from command or entity definition.
        
        Strategy:
        1. If command has explicit attributes (e.g., "fill brand vision mission"),
           use those as field list
        2. Otherwise, get all fields from entity's form definition
        
        Args:
            command: Parsed command
            
        Returns:
            List of field names to display in form
            
        Examples:
            >>> # Command: "fill brand vision mission"
            >>> _extract_form_fields(command)
            ['vision', 'mission']
        """
        # If command has attributes with empty values, those are the requested fields
        if command.attributes:
            return list(command.attributes.keys())
        
        # Otherwise, get default form fields from entity definition
        if hasattr(command.entity, 'form_fields'):
            return [field['name'] for field in command.entity.form_fields]
        
        return []
    
    # ==================== CONFIGURATION METHODS ====================
    
    def set_config(self, **kwargs) -> None:
        """
        Update router configuration dynamically.
        
        Args:
            **kwargs: Configuration parameters to update
            
        Examples:
            >>> router.set_config(support_wizard_enabled=True)
            >>> router.set_config(auto_suggest_on_error=False)
        """
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)