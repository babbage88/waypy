from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, DirectoryTree
from textual.binding import Binding
from textual.widget import Widget
from textual.reactive import var
from pathlib import Path
import shutil
from waypy_cli.cli import DEFAULT_WAYPY_DIR


class Status(Widget):
    message = var("")

    def render(self):
        return self.message


class WaybarProfilesSelector(App):
    BINDINGS = [
        Binding("d", "deploy_profile", "Deploy selected profile")
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.selected_path: Path | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield DirectoryTree(Path(DEFAULT_WAYPY_DIR) / "profiles" / "waybar")
        yield Footer()
        yield Status()

    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        self.selected_path = event.path
        self.query_one(Status).message = f"Selected file: {self.selected_path}"

    def on_directory_tree_directory_selected(self, event: DirectoryTree.DirectorySelected) -> None:
        self.selected_path = event.path
        self.query_one(Status).message = f"Selected directory: {self.selected_path}"

    def action_deploy_profile(self) -> None:
        if self.selected_path is None:
            self.query_one(Status).message = "⚠️ No profile selected."
            return

        profile_path = self.selected_path
        if profile_path.is_file():
            profile_path = profile_path.parent

        config_file = profile_path / "config"
        style_file = profile_path / "style.css"

        target_dir = Path.home() / ".config" / "waybar"
        target_dir.mkdir(parents=True, exist_ok=True)

        messages = []

        if config_file.exists():
            shutil.copy2(config_file, target_dir / "config")
            messages.append("✅ Config deployed.")
        else:
            messages.append("⚠️ config file missing.")

        if style_file.exists():
            shutil.copy2(style_file, target_dir / "style.css")
            messages.append("✅ style.css deployed.")
        else:
            messages.append("⚠️ style.css file missing.")

        self.query_one(Status).message = "\n".join(messages)


if __name__ == "__main__":
    WaybarProfilesSelector().run()
