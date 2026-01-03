# D:\Code\vlmx-sh2\src\vlmx_sh2\router\config.py
"""
Router configuration for VLMX DSL.

Provides configurable behavior for command routing and wizard features.
"""


class RouterConfig:
    """
    Configuration for command router behavior.
    
    Controls how the router handles different scenarios:
    - Support wizard on/off
    - Auto-suggestions
    - Form validation strictness
    
    Attributes:
        support_wizard_enabled: Enable interactive error recovery wizard
        auto_suggest_on_error: Show suggestions when parsing fails
        form_validation_strict: Require all form fields to be valid before submission
    
    Examples:
        >>> # Default config (no support wizard)
        >>> config = RouterConfig()
        >>> config.support_wizard_enabled
        False
        
        >>> # Enable all features
        >>> config = RouterConfig(
        ...     support_wizard_enabled=True,
        ...     auto_suggest_on_error=True,
        ...     form_validation_strict=True
        ... )
    """
    
    def __init__(
        self,
        support_wizard_enabled: bool = False,
        auto_suggest_on_error: bool = True,
        form_validation_strict: bool = True
    ):
        """
        Initialize router configuration.
        
        Args:
            support_wizard_enabled: Enable support wizard for failed commands
                Default: False (show error message directly)
            auto_suggest_on_error: Provide suggestions when parsing fails
                Default: True
            form_validation_strict: Require all form fields to be valid
                Default: True (reject invalid forms)
        """
        self.support_wizard_enabled = support_wizard_enabled
        self.auto_suggest_on_error = auto_suggest_on_error
        self.form_validation_strict = form_validation_strict
    
    def enable_support_wizard(self) -> None:
        """Enable support wizard for error recovery."""
        self.support_wizard_enabled = True
    
    def disable_support_wizard(self) -> None:
        """Disable support wizard (show errors directly)."""
        self.support_wizard_enabled = False
    
    def __repr__(self) -> str:
        return (
            f"RouterConfig("
            f"support_wizard_enabled={self.support_wizard_enabled}, "
            f"auto_suggest_on_error={self.auto_suggest_on_error}, "
            f"form_validation_strict={self.form_validation_strict}"
            f")"
        )