from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static


class BruceApp(App):
    CSS = """
    Screen { background: #080604; }
    Static { color: #ff8800; }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Bruce Laptop — TUI mode\n\nRun without --tui for the full GTK4 GUI.")
        yield Footer()
