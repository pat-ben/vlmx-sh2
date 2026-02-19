"""AppSelector widget for browsing views and tools within an org."""

from textual.app import ComposeResult
from textual.message import Message
from textual.widget import Widget
from textual.widgets import OptionList, TabbedContent, TabPane
from textual.widgets.option_list import Option

from ...dsl.words.registry import get_tools, get_views


class AppSelector(Widget):
    """Shows views and tools. Always visible; items are disabled until an org is selected."""

    DEFAULT_CSS = """
    AppSelector {
        height: auto;
    }
    """

    class AppSelected(Message):
        """Posted when the user selects a view or tool."""

        def __init__(self, app_id: str, app_type: str) -> None:
            super().__init__()
            self.app_id = app_id
            self.app_type = app_type

    def compose(self) -> ComposeResult:
        with TabbedContent():
            with TabPane("◧ Views", id="tab-views"):
                yield OptionList(id="views-option-list")
            with TabPane("◈ Tools", id="tab-tools"):
                yield OptionList(id="tools-option-list")

    def on_mount(self) -> None:
        self._populate_lists(enabled=False)

    def _populate_lists(self, schema_id: str = "company", enabled: bool = True) -> None:
        """Clear and repopulate both lists. Items are disabled when enabled=False."""
        views_list = self.query_one("#views-option-list", OptionList)
        tools_list = self.query_one("#tools-option-list", OptionList)

        views_list.clear_options()
        tools_list.clear_options()

        views = get_views(schema_id)
        if views:
            for word in views:
                views_list.add_option(
                    Option(word.id.upper(), id=word.id, disabled=not enabled)
                )
        else:
            views_list.add_option(Option("No items available", id="__empty__", disabled=True))

        tools = get_tools()
        if tools:
            for word in tools:
                tools_list.add_option(
                    Option(word.id.upper(), id=word.id, disabled=not enabled)
                )
        else:
            tools_list.add_option(Option("No items available", id="__empty__", disabled=True))

    def show_for_org(self, schema_id: str = "company") -> None:
        """Repopulate lists with enabled items for the given org schema."""
        self._populate_lists(schema_id=schema_id, enabled=True)

    def hide(self) -> None:
        """Repopulate lists with disabled items (no org selected)."""
        self._populate_lists(enabled=False)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Handle selection from either inner OptionList."""
        event.stop()

        if event.option.id == "__empty__":
            return

        list_id = event.option_list.id
        app_type = "view" if list_id == "views-option-list" else "tool"

        self.post_message(self.AppSelected(app_id=event.option.id, app_type=app_type))
