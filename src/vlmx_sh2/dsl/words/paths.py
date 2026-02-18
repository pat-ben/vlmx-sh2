"""
System directory path resolver.

Resolves locations of system directories (views, tools) relative to project root.
"""

from pathlib import Path


def get_system_views_dir() -> Path:
    """
    Get the path to the system/views directory.
    
    Returns:
        Path object pointing to system/views directory
        
    Notes:
        The system/views folder is at the project root, which is 4 levels up
        from this file's location: src/vlmx_sh2/dsl/words/paths.py
    """
    # Navigate from this file to project root: src/vlmx_sh2/dsl/words/paths.py → project root
    project_root = Path(__file__).resolve().parents[4]
    return project_root / "system" / "views"


def get_system_org_dir() -> Path:
    """
    Get the path to the system/org directory.

    Returns:
        Path object pointing to system/org directory
    """
    project_root = Path(__file__).resolve().parents[4]
    return project_root / "system" / "org"


def get_system_tools_dir() -> Path:
    """
    Get the path to the system/tools directory.
    
    Returns:
        Path object pointing to system/tools directory
        
    Notes:
        Consistent with get_system_views_dir() for future tool loader.
    """
    project_root = Path(__file__).resolve().parents[4]
    return project_root / "system" / "tools"