"""
Navigation handler.

Handles context navigation (cd command) between different levels:
- SYS (root) <-> ORG (company) <-> APP (specific view or tool)

Navigation commands:
    cd ~              -> SYS (root)
    cd ..             -> Up one level
    cd <company>/     -> ORG (enter company)
    cd <app_name>/    -> APP (enter specific view or tool from ORG)
"""

from typing import Callable, Dict, Optional
from ..models.context import Context
from ..models.responses import HandlerResult, CommandResult, ErrorResult
from ..models.parser.command import ParsedCommand
from ..enums.core import ContextLevel
from ..storage.database import StorageInterface


# =============================================================================
# 1. Atomic Navigation Functions
# =============================================================================

async def _navigate_to_sys(context: Context) -> HandlerResult:
    """Navigate to SYS (root) level."""
    return CommandResult(
        success=True,
        message="At root",
        data={
            "context_switch": {
                "level": ContextLevel.SYS,
                "org_id": None,
                "org_name": None,
                "org_db_path": None,
                "app_id": None,
                "app_name": None,
                "app_type": None,
            }
        }
    )


async def _navigate_to_app(app_name: str, context: Context) -> HandlerResult:
    """Navigate to a specific app (view or tool) from ORG level."""
    if context.level == ContextLevel.SYS:
        return ErrorResult(
            errors=["Cannot enter APP context from SYS level"],
            suggestions=["First navigate to a company: cd <company>/"]
        )
    
    # Import here to avoid circular imports
    from ..dsl.registry import VIEW_WORDS, TOOL_WORDS
    
    # Look up app in VIEW_WORDS and TOOL_WORDS
    app_word = VIEW_WORDS.get(app_name) or TOOL_WORDS.get(app_name)
    
    if not app_word:
        # List available apps for suggestion
        available_views = list(VIEW_WORDS.keys())
        available_tools = list(TOOL_WORDS.keys())
        return ErrorResult(
            errors=[f"App '{app_name}' not found"],
            suggestions=[
                f"Available views: {', '.join(available_views)}",
                f"Available tools: {', '.join(available_tools)}",
            ]
        )
    
    # Determine app type
    app_type = app_word.app_type  # "view" or "tool"
    
    return CommandResult(
        success=True,
        message=f"Entered {app_name} ({app_type}) for {context.org_name}",
        data={
            "context_switch": {
                "level": ContextLevel.APP,
                "org_id": context.org_id,
                "org_name": context.org_name,
                "org_db_path": context.org_db_path,
                "app_id": app_word.id,
                "app_name": app_name,
                "app_type": app_type,
            }
        }
    )


async def _already_at_root(context: Context) -> HandlerResult:
    """Error: already at SYS level."""
    return ErrorResult(
        errors=["Already at root level"],
        suggestions=["Use 'cd <company>/' to enter a company"]
    )


async def _navigate_org_to_sys(context: Context) -> HandlerResult:
    """Navigate from ORG to SYS."""
    return CommandResult(
        success=True,
        message="Back to root",
        data={
            "context_switch": {
                "level": ContextLevel.SYS,
                "org_id": None,
                "org_name": None,
                "org_db_path": None,
                "app_id": None,
                "app_name": None,
                "app_type": None,
            }
        }
    )


async def _navigate_app_to_org(context: Context) -> HandlerResult:
    """Navigate from APP to ORG."""
    return CommandResult(
        success=True,
        message=f"Back to {context.org_name}",
        data={
            "context_switch": {
                "level": ContextLevel.ORG,
                "org_id": context.org_id,
                "org_name": context.org_name,
                "org_db_path": context.org_db_path,
                "app_id": None,
                "app_name": None,
                "app_type": None,
            }
        }
    )


async def _navigate_to_org(org_name: str, context: Context) -> HandlerResult:
    """Navigate to a specific organization."""
    if context.level != ContextLevel.SYS:
        return ErrorResult(
            errors=[f"Cannot navigate to company '{org_name}' from current context"],
            suggestions=["First return to root: cd ~"]
        )
    
    company_result = StorageInterface.find_company_by_name(org_name, context)
    if not company_result.success:
        suggestions = ["Use 'create company <name>' to create a new company"]
        
        # Add disambiguation suggestions if available
        if company_result.data and company_result.data.get("suggestions"):
            candidate_suggestions = [f"cd {name}/" for name in company_result.data["suggestions"]]
            suggestions = candidate_suggestions + suggestions
        
        return ErrorResult(
            errors=[company_result.error],
            suggestions=suggestions
        )
    
    return CommandResult(
        success=True,
        message=f"Entered {org_name}",
        data={
            "context_switch": {
                "level": ContextLevel.ORG,
                "org_id": company_result.data.get("id"),
                "org_name": org_name,
                "org_db_path": company_result.data.get("db_path"),
                "app_id": None,
                "app_name": None,
                "app_type": None,
            }
        }
    )


# =============================================================================
# 2. Dispatch Tables
# =============================================================================

# Special paths (no trailing slash needed in lookup)
_SPECIAL_PATHS: Dict[str, Callable[[Context], HandlerResult]] = {
    "~": _navigate_to_sys,
    "": _navigate_to_sys,
    "..": None,  # Special case: uses _NAVIGATE_UP table
}

# Navigate up dispatch: current_level -> handler
_NAVIGATE_UP: Dict[ContextLevel, Callable[[Context], HandlerResult]] = {
    ContextLevel.SYS: _already_at_root,
    ContextLevel.ORG: _navigate_org_to_sys,
    ContextLevel.APP: _navigate_app_to_org,
}


# =============================================================================
# 3. Main Handler
# =============================================================================

async def navigate_handler(parsed_command: ParsedCommand, context: Context) -> HandlerResult:
    """
    Navigate between contexts.
    
    Navigation model (cumulative):
        SYS (root) <-> ORG (company) <-> APP (specific view/tool)
    
    Commands:
        cd ~              -> SYS (root)
        cd ..             -> Up one level
        cd <company>/     -> ORG (enter company) - from SYS only
        cd <app_name>/    -> APP (enter view/tool) - from ORG or APP
    """
    target_path = (parsed_command.target_name or "").strip()
    lookup_path = target_path.rstrip("/")
    
    # Handle special paths
    if lookup_path in _SPECIAL_PATHS:
        if lookup_path == "..":
            handler_fn = _NAVIGATE_UP.get(context.level)
            if handler_fn:
                return await handler_fn(context)
            return ErrorResult(errors=[f"Unknown context level: {context.level}"])
        
        handler_fn = _SPECIAL_PATHS.get(lookup_path)
        if handler_fn:
            return await handler_fn(context)
    
    # From SYS: navigate to company
    if context.level == ContextLevel.SYS:
        return await _navigate_to_org(lookup_path, context)
    
    # From ORG or APP: navigate to app (or switch app)
    return await _navigate_to_app(lookup_path, context)


# =============================================================================
# 4. Prompt Display Helper
# =============================================================================

def get_prompt_string(context: Context) -> str:
    """
    Generate prompt string for current context.
    
    Returns:
        ~ $              for SYS
        ~/acme $         for ORG
        ~/acme/neco $    for APP (with app name)
    """
    _PROMPT_FORMAT: Dict[ContextLevel, Callable[[Context], str]] = {
        ContextLevel.SYS: lambda c: "~",
        ContextLevel.ORG: lambda c: f"~/{c.org_name}",
        ContextLevel.APP: lambda c: f"~/{c.org_name}/{c.app_name}",
    }
    
    formatter = _PROMPT_FORMAT.get(context.level, lambda c: "?")
    return f"{formatter(context)} $"