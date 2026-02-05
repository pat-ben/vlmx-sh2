"""
Navigation handler.

Handles context navigation (cd command) between different levels
of the application (SYS, ORG, APP).
"""

from typing import Callable, Awaitable, Dict, Optional
from ..models.context import Context
from ..models.responses import HandlerResult, CommandResult, ErrorResult
from ..models.parser.command import ParsedCommand
from ..enums.core import ContextLevel
from ..storage.database import find_company_by_name


# =============================================================================
# 1. Atomic Navigation Functions
# =============================================================================

def _navigate_to_sys(context: Context) -> HandlerResult:
    """Navigate to SYS (root) level."""
    return CommandResult(
        success=True,
        message="At root",
        data={
            "context_switch": {
                "level": "SYS",
                "org_id": None,
                "org_name": None,
                "org_db_path": None
            }
        }
    )


def _navigate_to_app(context: Context) -> HandlerResult:
    """Navigate to APP context (from ORG or stay in APP)."""
    if context.level == ContextLevel.SYS:
        return ErrorResult(
            errors=["Can only enter APP context from ORG context"],
            suggestions=["First navigate to a company: cd <company>/"]
        )
    
    # From ORG or APP -> APP (with appropriate message)
    if context.level == ContextLevel.APP:
        message = f"Already in APP context for {context.org_name}"
    else:
        message = f"Entered APP context for {context.org_name}"
    
    return CommandResult(
        success=True,
        message=message,
        data={
            "context_switch": {
                "level": "APP",
                "org_id": context.org_id,
                "org_name": context.org_name,
                "org_db_path": context.org_db_path
            }
        }
    )


def _already_at_root(context: Context) -> HandlerResult:
    """Error: already at SYS level."""
    return ErrorResult(
        errors=["Already at root level"],
        suggestions=["Use 'cd <company>/' to enter a company"]
    )


def _navigate_org_to_sys(context: Context) -> HandlerResult:
    """Navigate from ORG to SYS."""
    return CommandResult(
        success=True,
        message="Back to root",
        data={
            "context_switch": {
                "level": "SYS",
                "org_id": None,
                "org_name": None,
                "org_db_path": None
            }
        }
    )


def _navigate_app_to_org(context: Context) -> HandlerResult:
    """Navigate from APP to ORG."""
    return CommandResult(
        success=True,
        message=f"Back to {context.org_name}",
        data={
            "context_switch": {
                "level": "ORG",
                "org_id": context.org_id,
                "org_name": context.org_name,
                "org_db_path": context.org_db_path
            }
        }
    )


async def _navigate_to_org(org_name: str, context: Context) -> HandlerResult:
    """Navigate to a specific organization."""
    # Validate we're at SYS level
    if context.level != ContextLevel.SYS:
        return ErrorResult(
            errors=[f"Cannot navigate to '{org_name}' from {context.level} context"],
            suggestions=["First return to root: cd ~"]
        )
    
    # Check org exists
    company = find_company_by_name(org_name)
    
    if not company:
        return ErrorResult(
            errors=[f"Company '{org_name}' not found"],
            suggestions=["Use 'create company <name>' to create a new company"]
        )
    
    return CommandResult(
        success=True,
        message=f"Entered {org_name}",
        data={
            "context_switch": {
                "level": "ORG",
                "org_id": company.get("id"),
                "org_name": org_name,
                "org_db_path": company.get("db_path")
            }
        }
    )


# =============================================================================
# 2. Dispatch Tables
# =============================================================================

# Special paths: path -> handler (sync functions)
_SPECIAL_PATHS: Dict[str, Callable[[Context], HandlerResult]] = {
    "~": _navigate_to_sys,
    "": _navigate_to_sys,
    "..": None,  # Special case: uses _NAVIGATE_UP table
    "app": _navigate_to_app,
    "app/": _navigate_to_app,
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
    
    Navigation model:
        SYS (root) <-> ORG (company) <-> APP (analytics)
    
    Commands:
        cd ~           -> SYS (root)
        cd ..          -> Up one level
        cd <company>/  -> ORG (enter company)
        cd app/        -> APP (enter analytics mode)
    """
    target_path = (parsed_command.target_name or "").strip()
    
    # Normalize path (remove trailing slash for lookup, except "app/")
    lookup_path = target_path.rstrip("/") if target_path not in ("app/",) else target_path
    
    # Check for special paths
    if lookup_path in _SPECIAL_PATHS or target_path in _SPECIAL_PATHS:
        # Handle ".." specially with context-aware dispatch
        if lookup_path == "..":
            handler_fn = _NAVIGATE_UP.get(context.level)
            if handler_fn:
                return handler_fn(context)
            return ErrorResult(errors=[f"Unknown context level: {context.level}"])
        
        # Other special paths
        handler_fn = _SPECIAL_PATHS.get(lookup_path) or _SPECIAL_PATHS.get(target_path)
        if handler_fn:
            return handler_fn(context)
    
    # Default: navigate to org
    org_name = target_path.rstrip("/")
    return await _navigate_to_org(org_name, context)


# =============================================================================
# 4. Prompt Display Helper
# =============================================================================

def get_prompt_string(context: Context) -> str:
    """
    Generate prompt string for current context.
    
    Returns:
        ~ $              for SYS
        ~/acme $         for ORG
        ~/acme/app $     for APP
    """
    _PROMPT_FORMAT: Dict[ContextLevel, Callable[[Context], str]] = {
        ContextLevel.SYS: lambda c: "~",
        ContextLevel.ORG: lambda c: f"~/{c.org_name}",
        ContextLevel.APP: lambda c: f"~/{c.org_name}/app",
    }
    
    formatter = _PROMPT_FORMAT.get(context.level, lambda c: "?")
    return f"{formatter(context)} $"