import argparse
import time
from typing import List
import argcomplete
import subprocess
import sys
import logging
from logging import StreamHandler, Formatter
from colorama import Fore, Style, init as colorama_init
import os
import threading
import yaml
from pathlib import Path
from typing_extensions import Optional
from datetime import datetime
import shutil

DEFAULT_WAYPY_DIR = Path.home() / ".config" / "waypy"
DEFAULT_CONFIG_PATH = Path.home() / ".config" / "waypy" / "config.yaml"
WAYBAR_ACTIVE_CONFIG_PATH = Path.home() / ".config" / "waybar"
WAYBAR_ACTIVE_CONFIG_FILE = Path(WAYBAR_ACTIVE_CONFIG_PATH, "config").absolute()
WAYBAR_ACTIVE_CSS_FILE = Path(WAYBAR_ACTIVE_CONFIG_PATH, "style.css").absolute()
HYPRLAND_CONFIG_FILE_PATH = Path.home() / ".config" / "hypr" / "hyprland.conf"
HYPRPAPER_CONFIG_FILE_PATH = Path.home() / ".config" / "hypr" / "hyprpaper.conf"

class WaybarProfile:
    def __init__(self, name, config_path, css_path) -> None:
        self.name = name
        self.config_path = config_path
        self.css_path = css_path

    def backup_existing(self):
        now = datetime.now()
        bkup_name = str(now.strftime("%Y-%m-%d_%H%M%S") + '_bak')
        backup_path = Path(DEFAULT_WAYPY_DIR, "backups", bkup_name).absolute().mkdir(mode=775, parents=True, exist_ok=True)
        for item in WAYBAR_ACTIVE_CONFIG_PATH.iterdir():
            if item.is_file():
                logger.info(f"Backing up: {str(item)} to {str(backup_path)}")
                shutil.copyfile(str(item.absolute()), str(backup_path))

    def deploy_profile(self):
        logger.info("Starting waybar config backup")
        self.backup_existing()
        logger.info(f"deploying config {self.config_path}")
        shutil.copyfile(self.config_path, WAYBAR_ACTIVE_CONFIG_FILE)
        logger.info(f"deploying stying {self.css_path}")
        shutil.copyfile(self.css_path, WAYBAR_ACTIVE_CSS_FILE)
        self.reload_waybar()

    def reload_waybar(self, timeout: float=float(9.0)):
        logger.info("Attempting to reload Waybar...")
        threads: List[threading.Thread] = []
        notify_event: threading.Event = threading.Event()
        kill_thread: threading.Thread = threading.Thread(target=kill_waybar, kwargs={"notify_event": notify_event})
        threads.append(kill_thread)
        start_thread: threading.Thread = threading.Thread(target=start_waybar, kwargs={"notify_event": notify_event, "timeout":timeout})
        threads.append(start_thread)

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join(timeout=timeout)

class WaypyConfig:
    def __init__(self, path):
        self.path: Path = path
        self.waybar_configs_dir: Optional[str] = None
        self.hyprland_configs_dir: Optional[str] = None
        self._load()

    def _load(self):
        if not self.path.exists():
            logger.warning(
                f"Config file {self.path} does not exist. Using defaults if available."
            )
            self.waybar_configs_dir = str(Path(DEFAULT_WAYPY_DIR, "profiles", "waybar").absolute())
            self.hyprland_configs_dir = str(Path(DEFAULT_WAYPY_DIR, "profiles", "hyprland").absolute())
            self.backups_path = str(Path(DEFAULT_WAYPY_DIR, "backups").absolute())
            return

        try:
            with self.path.open() as f:
                data = yaml.safe_load(f) or {}

            self.waybar_configs_dir = data.get("waybar_configs_dir")
            self.hyprland_configs_dir = data.get("hyprland_configs_dir")
            self.backups_path = data.get("backups_path")
            wb_path = Path(str(self.waybar_configs_dir))
            hl_path = Path(str(self.hyprland_configs_dir))
            wb_path.mkdir(parents=True, exist_ok=True)
            hl_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to load config file: {e}")
            sys.exit(1)

    def __repr__(self):
        return f"<WaypyConfig waybar_configs_dir={self.waybar_configs_dir} hyprland_configs_dir={self.hyprland_configs_dir}>"


colorama_init(autoreset=True)


class ColorFormatter(Formatter):
    LEVEL_COLORS = {
        "DEBUG": Fore.LIGHTCYAN_EX,
        "INFO": Fore.LIGHTGREEN_EX,
        "WARNING": Fore.LIGHTYELLOW_EX,
        "ERROR": Fore.LIGHTRED_EX,
        "CRITICAL": Fore.RED,
    }

    def format(self, record):
        level_color = self.LEVEL_COLORS.get(record.levelname, "")
        message = super().format(record)
        return f"{level_color}{message}{Style.RESET_ALL}"


def setup_logging():
    handler = StreamHandler()
    formatter = ColorFormatter(
        fmt="[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%H:%M:%S"
    )
    handler.setFormatter(formatter)

    logger = logging.getLogger("waypy")
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    logger.propagate = False
    return logger


logger = setup_logging()


def kill_waybar(notify_event: threading.Event) -> int:
    try:
        result_kill = subprocess.run(
            ["pkill", "-x", "waybar"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        if result_kill.returncode == 0:
            logger.info("Killed existing Waybar process(es)")
            notify_event.set()
            return result_kill.returncode
        else:
            logger.warning("No Waybar process found to kill, attempting to start....")
            notify_event.set()
            return result_kill.returncode
    except Exception as e:
        logger.error(f"Error attempting to kill Waybar: {e}")
        return int(1)


def start_waybar(
    notify_event: threading.Event,
    complete_event: threading.Event,
    timeout: float = float(9.0),
):
    logger.info(f"Waiting for waybar process to terminate - Timeout: {str(timeout)}")
    notify_event.wait(timeout=timeout)
    try:
        result_start = subprocess.Popen(["hyprctl", "dispatch", "exec", "waybar"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        logger.info(f"Waybar started with PID {result_start.pid}.")
        complete_event.set()
    except Exception as e:
        logger.error(f"Failed to start Waybar: {e}")
        sys.exit(1)

def waybar_reload(args: argparse.Namespace, config: WaypyConfig):
    logger.info("Attempting to reload Waybar...")
    timeout = float(10.0)
    threads = []
    complete_event: threading.Event = threading.Event()
    notify_event: threading.Event = threading.Event()
    kill_thread: threading.Thread = threading.Thread(
        target=kill_waybar, kwargs={"notify_event": notify_event}
    )
    threads.append(kill_thread)
    waybar_start_thread: threading.Thread = threading.Thread(
        target=start_waybar,
        kwargs={
            "notify_event": notify_event,
            "complete_event": complete_event,
            "timeout": timeout,
        },
    )
    threads.append(waybar_start_thread)

    logger.info("Starting threads")
    for thread in threads:
        thread.start()

    logger.info("Joining threads")
    for thread in threads:
        thread.join(timeout=timeout)

    complete_event.wait(timeout=float(timeout * 2))
    logger.info("Waybar reload completed...")

def completion_install(args, config):
    shell_path = os.environ.get("SHELL", "")
    detected_shell = os.path.basename(shell_path)

    logger.info(f"Detected shell: {detected_shell}")

    eval_line = 'eval "$(register-python-argcomplete waypy)"'

    rc_file = None
    if detected_shell == "bash":
        rc_file = Path.home() / ".bashrc"
    elif detected_shell == "zsh":
        rc_file = Path.home() / ".zshrc"
    else:
        logger.warning("Your shell is not explicitly supported. Supported: bash, zsh")
        logger.info(
            f"Please add the following line manually to your shell rc file:\n{eval_line}"
        )
        return

    # Ensure rc file exists
    if not rc_file.exists():
        logger.info(f"{rc_file} does not exist, creating it.")
        rc_file.touch()

    # Check if line is already present
    with rc_file.open("r") as f:
        lines = f.read().splitlines()

    if any(eval_line in line for line in lines):
        logger.info(f"Autocompletion already configured in {rc_file}. No changes made.")
    else:
        with rc_file.open("a") as f:
            f.write(f"\n# Waypy autocompletion\n{eval_line}\n")
        logger.info(f"Autocompletion added to {rc_file}.")
        logger.info("You may need to restart your shell or source the rc file:")
        logger.info(Fore.CYAN + f"  source {rc_file}")


def build_parser():
    parser = argparse.ArgumentParser(
        prog="waypy",
        description="CLI + TUI tool for managing Waybar and Hyprland configuration.",
    )

    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help=f"Path to config YAML file (default: {DEFAULT_CONFIG_PATH})",
    )

    subparsers = parser.add_subparsers(
        dest="component", required=True, help="Component to manage"
    )

    # Waybar
    waybar_parser = subparsers.add_parser("waybar", help="Manage Waybar")
    waybar_subparsers = waybar_parser.add_subparsers(
        dest="waybar_command", required=True, help="Waybar commands"
    )

    waybar_reload_parser = waybar_subparsers.add_parser(
        "reload", help="Hot reload Waybar"
    )
    waybar_reload_parser.set_defaults(func=waybar_reload)

    # Hyprland placeholder
    hyprland_parser = subparsers.add_parser("hyprland", help="Manage Hyprland")
    hyprland_subparsers = hyprland_parser.add_subparsers(
        dest="hyprland_command", help="Hyprland commands"
    )

    # Completion
    completion_parser = subparsers.add_parser(
        "completion", help="Install autocompletion support"
    )
    completion_subparsers = completion_parser.add_subparsers(
        dest="completion_command", required=True
    )
    install_parser = completion_subparsers.add_parser(
        "install", help="Show instructions or install autocompletion"
    )
    install_parser.set_defaults(func=completion_install)

    return parser


def main():
    parser = build_parser()
    argcomplete.autocomplete(parser)
    args = parser.parse_args()

    # Load config
    config = WaypyConfig(args.config)
    logger.debug(f"Loaded config: {config}")

    if hasattr(args, "func"):
        args.func(args, config)
    else:
        parser.print_help()
