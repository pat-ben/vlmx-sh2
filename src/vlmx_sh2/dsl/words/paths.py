"""
System directory path resolver.

Resolves locations of shell directories (views, tools) relative to project root.
"""

from pathlib import Path


def get_system_views_dir() -> Path:
    """
    Get the path to the shell/views directory.
    
    Returns:
        Path object pointing to shell/views directory
        
    Notes:
        The shell/ folder is inside src/vlmx_sh2/, which is 2 levels up
        from this file's location: src/vlmx_sh2/dsl/words/paths.py
    """
    # Navigate from this file to src/vlmx_sh2/: src/vlmx_sh2/dsl/words/paths.py → parents[2]
    pkg_root = Path(__file__).resolve().parents[2]
    return pkg_root / "shell" / "views"


def get_system_org_dir() -> Path:
    """
    Get the path to the shell/org directory.

    Returns:
        Path object pointing to shell/org directory
    """
    pkg_root = Path(__file__).resolve().parents[2]
    return pkg_root / "shell" / "org"


def get_system_tools_dir() -> Path:
    """
    Get the path to the shell/tools directory.
    
    Returns:
        Path object pointing to shell/tools directory
        
    Notes:
        Consistent with get_system_views_dir() for future tool loader.
    """
    pkg_root = Path(__file__).resolve().parents[2]
    return pkg_root / "shell" / "tools"