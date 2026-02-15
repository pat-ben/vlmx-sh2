"""
Main entry point for the VLMX-SH2 application.

Provides the main() function that initializes and runs the Textual
application, with proper error handling and graceful shutdown.
"""

# Importing engine handlers performs action_id -> handler registration for the IR router.
# This keeps runtime wiring out of IR and ensures the engine can dispatch commands.
from .engine import handlers  # noqa: F401
from .ui.app import VLMX


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
