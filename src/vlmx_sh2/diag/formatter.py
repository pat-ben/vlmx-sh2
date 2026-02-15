"""
DiagnosticFormatter for rich error reporting.

Transforms ValidationIssue objects into rich, formatted output for terminal display.
Integrates with PositionResolver and SuggestionEngine to provide Nushell-quality
error messages with position arrows and actionable suggestions.
"""

from typing import List, Optional, Tuple, Union
from enum import Enum

from ..core.models.validation import ValidationIssue, ValidationContext
from ..core.enums import IssueSeverity, IssueStage
from .resolver import PositionResolver
from .suggestions import SuggestionEngine


class OutputFormat(Enum):
    """Output format options for diagnostic formatting."""
    PLAIN = "plain"           # Simple text for basic terminals
    RICH = "rich"            # Rich markup for Textual's Rich rendering
    STRUCTURED = "structured" # Return structured data for UI rendering


class DiagnosticFormatter:
    """
    Formatter for rich diagnostic output from validation issues.
    
    Transforms ValidationIssue objects and ValidationContext into formatted
    error messages with position information, suggestions, and documentation links.
    
    Features:
    - Multiple output formats (plain, rich markup, structured)
    - Position arrows pointing to problematic tokens
    - Integration with PositionResolver for lazy position calculation
    - Integration with SuggestionEngine for additional context-aware suggestions
    - Nushell-quality error formatting
    
    Example usage:
        >>> formatter = DiagnosticFormatter()
        >>> context = ValidationContext(input_text="crate company ACME")
        >>> # ... add issues to context ...
        >>> formatted = formatter.format_context(context)
        >>> print(formatted)
        Error [vlmx::parser::unknown_word]: Unknown word 'crate'
          → Position: column 1-5  
          → Suggestion: Did you mean 'create'?
          → Help: https://docs.vlmx.io/commands/create
    """
    
    def __init__(
        self, 
        output_format: OutputFormat = OutputFormat.PLAIN,
        show_position_arrows: bool = True,
        show_suggestions: bool = True,
        show_doc_links: bool = True,
        context_chars: int = 20
    ):
        """
        Initialize the diagnostic formatter.
        
        Args:
            output_format: Output format (plain, rich, structured)
            show_position_arrows: Whether to show position arrows in output
            show_suggestions: Whether to include suggestions
            show_doc_links: Whether to include documentation links
            context_chars: Number of context characters around error position
        """
        self.output_format = output_format
        self.show_position_arrows = show_position_arrows
        self.show_suggestions = show_suggestions
        self.show_doc_links = show_doc_links
        self.context_chars = context_chars
    
    def format_issue(
        self, 
        issue: ValidationIssue, 
        original_text: str = "",
        resolver: Optional[PositionResolver] = None
    ) -> str:
        """
        Format a single ValidationIssue into a rich error message.
        
        Args:
            issue: The validation issue to format
            original_text: Original user input for position resolution
            resolver: Optional PositionResolver (created if not provided)
            
        Returns:
            Formatted error message string
        """
        if not resolver and original_text:
            resolver = PositionResolver(original_text)
        
        # Build the main error line
        severity_label = self._format_severity(issue.severity)
        error_code_part = f"[{issue.error_code}]" if issue.error_code else ""
        main_line = f"{severity_label} {error_code_part}: {issue.message}".strip(": ")
        
        parts = [main_line]
        
        # Add position information if available
        if resolver and issue.token_text and self.show_position_arrows:
            position_info = self._format_position(issue, resolver)
            if position_info:
                parts.extend(position_info)
        
        # Add suggestion if available
        if issue.suggestion and self.show_suggestions:
            suggestion_line = self._format_suggestion(issue.suggestion)
            parts.append(suggestion_line)
        
        # Add documentation link if available
        if issue.doc_link and self.show_doc_links:
            doc_line = self._format_doc_link(issue.doc_link)
            parts.append(doc_line)
        
        return "\n".join(parts)
    
    def format_context(self, context: ValidationContext) -> str:
        """
        Format an entire ValidationContext into a comprehensive error report.
        
        Args:
            context: ValidationContext containing all issues
            
        Returns:
            Formatted error report string
        """
        if not context.has_issues():
            return ""
        
        resolver = PositionResolver(context.input_text) if context.input_text else None
        formatted_issues = []
        
        # Format each issue
        for issue in context.issues:
            formatted = self.format_issue(issue, context.input_text, resolver)
            formatted_issues.append(formatted)
        
        # Add summary if multiple issues
        result = "\n\n".join(formatted_issues)
        
        if len(context.issues) > 1:
            summary = self._format_summary(context)
            result = f"{result}\n\n{summary}"
        
        return result
    
    def format_errors_only(self, context: ValidationContext) -> str:
        """
        Format only error-level issues from ValidationContext.
        
        Args:
            context: ValidationContext containing issues
            
        Returns:
            Formatted error messages (warnings and info excluded)
        """
        if not context.has_errors():
            return ""
        
        resolver = PositionResolver(context.input_text) if context.input_text else None
        formatted_errors = []
        
        # Format only error-level issues
        for issue in context.errors:
            formatted = self.format_issue(issue, context.input_text, resolver)
            formatted_errors.append(formatted)
        
        return "\n\n".join(formatted_errors)
    
    def get_formatted_suggestions(self, context: ValidationContext) -> List[str]:
        """
        Extract formatted suggestions from all issues in context.
        
        Args:
            context: ValidationContext containing issues
            
        Returns:
            List of formatted suggestion strings
        """
        suggestions = []
        
        for issue in context.issues:
            if issue.suggestion:
                formatted = self._format_suggestion(issue.suggestion)
                suggestions.append(formatted)
        
        return suggestions
    
    def _format_severity(self, severity: IssueSeverity) -> str:
        """Format severity level based on output format."""
        if self.output_format == OutputFormat.RICH:
            colors = {
                IssueSeverity.ERROR: "[bold red]Error[/]",
                IssueSeverity.WARNING: "[bold yellow]Warning[/]",
                IssueSeverity.INFO: "[bold blue]Info[/]"
            }
            return colors.get(severity, str(severity.value))
        else:
            return severity.value.capitalize()
    
    def _format_position(
        self, 
        issue: ValidationIssue, 
        resolver: PositionResolver
    ) -> Optional[List[str]]:
        """
        Format position information with context and arrow pointing to token.
        
        Returns list of strings for position display, or None if position
        cannot be resolved.
        """
        if not issue.token_text:
            return None
        
        # Try to find position using smart resolution
        position = resolver.find_smart_position(issue.token_text)
        if not position:
            return None
        
        start, end = position
        
        # Simple position line
        position_line = f"  -> Position: column {start + 1}-{end}"
        
        # If we want to show context with arrows (like Nushell)
        if self.context_chars > 0:
            context_text, token_pos_in_context = resolver.get_context_around_position(
                start, end, self.context_chars
            )
            
            if context_text and token_pos_in_context >= 0:
                # Create arrow pointing to the token (ASCII-only version)
                arrow_line = "  |  " + context_text
                pointer_line = "  |  " + " " * token_pos_in_context + "-" * (end - start) + "^"
                pointer_label = "  |  " + " " * token_pos_in_context + " " * ((end - start) // 2) + "here"
                
                return [position_line, arrow_line, pointer_line, pointer_label]
        
        return [position_line]
    
    def _format_suggestion(self, suggestion: str) -> str:
        """Format suggestion text based on output format."""
        if self.output_format == OutputFormat.RICH:
            return f"  -> [dim]Suggestion:[/] {suggestion}"
        else:
            return f"  -> Suggestion: {suggestion}"
    
    def _format_doc_link(self, doc_link: str) -> str:
        """Format documentation link based on output format."""
        if self.output_format == OutputFormat.RICH:
            return f"  -> [dim]Help:[/] [link={doc_link}]{doc_link}[/link]"
        else:
            return f"  -> Help: {doc_link}"
    
    def _format_summary(self, context: ValidationContext) -> str:
        """Format summary of all issues in context."""
        total = context.total_count
        errors = context.error_count
        warnings = context.warning_count
        infos = context.info_count
        
        parts = []
        if errors > 0:
            parts.append(f"{errors} error{'s' if errors != 1 else ''}")
        if warnings > 0:
            parts.append(f"{warnings} warning{'s' if warnings != 1 else ''}")
        if infos > 0:
            parts.append(f"{infos} info message{'s' if infos != 1 else ''}")
        
        summary_text = f"Found {', '.join(parts)}"
        
        if self.output_format == OutputFormat.RICH:
            return f"[dim]-- {summary_text} --[/]"
        else:
            return f"-- {summary_text} --"
    
    # ==================== STRUCTURED OUTPUT ====================
    
    def format_issue_structured(
        self, 
        issue: ValidationIssue, 
        original_text: str = ""
    ) -> dict:
        """
        Format issue as structured data for UI rendering.
        
        Returns dictionary with all diagnostic information that UI
        components can render however they want.
        """
        resolver = PositionResolver(original_text) if original_text else None
        position = None
        
        if resolver and issue.token_text:
            pos = resolver.find_smart_position(issue.token_text)
            if pos:
                start, end = pos
                context_text, token_pos = resolver.get_context_around_position(
                    start, end, self.context_chars
                )
                position = {
                    "start": start,
                    "end": end,
                    "context": context_text,
                    "token_position_in_context": token_pos
                }
        
        return {
            "stage": issue.stage.value,
            "severity": issue.severity.value,
            "message": issue.message,
            "error_code": issue.error_code,
            "doc_link": issue.doc_link,
            "suggestion": issue.suggestion,
            "token_text": issue.token_text,
            "position": position
        }
    
    def format_context_structured(self, context: ValidationContext) -> dict:
        """Format ValidationContext as structured data."""
        return {
            "input_text": context.input_text,
            "normalized_text": context.normalized_text,
            "total_issues": context.total_count,
            "error_count": context.error_count,
            "warning_count": context.warning_count,
            "info_count": context.info_count,
            "is_valid": context.is_valid(),
            "issues": [
                self.format_issue_structured(issue, context.input_text)
                for issue in context.issues
            ]
        }