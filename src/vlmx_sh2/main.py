"""
Main entry point for the VLMX-SH2 application.

Provides the main() function that initializes and runs the Textual
application, with proper error handling and graceful shutdown.
"""

try:
    from .ui.app import VLMX
except ImportError:
    # Direct execution - add src to path
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from vlmx_sh2.ui.app import VLMX


def main():
    """Main entry point for the VLMX-SH2 application."""
    try:
        app = VLMX()
        app.run()
    except KeyboardInterrupt:
        print("\nApplication interrupted by user.")
    except Exception as e:
        print(f"Error starting VLMX application: {e}")


if __name__ == "__main__":
    main()