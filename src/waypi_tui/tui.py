from typing import Type
from textual.driver import Driver
import waypy_cli
from textual.app import App, ComposeResult
from textual.widgets import DirectoryTree, Header, Footer
from typing import List
from pathlib import Path, PurePath
from waypy_cli.cli import DEFAULT_WAYPY_DIR 


class WaybarProfilesSelector(App):
    def __init__(self, driver_class: type[Driver] | None = None, css_path: str | PurePath | List[str | PurePath] | None = None, watch_css: bool = False, ansi_color: bool = False):
        self.configs_path = Path(DEFAULT_WAYPY_DIR, "profiles", "waybar").absolute().__str__()
        super().__init__(driver_class, css_path, watch_css, ansi_color)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True, name="Waypy Profiles", id="waypy_wb_configs")
        yield DirectoryTree(self.configs_path)
        yield Footer()
    
    def set_configs_path(self, value: str):
        self.configs_path = value

if __name__ == "__main__":
    app = WaybarProfilesSelector()
    app.run()