import argparse
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

DEFAULT_CONFIG_PATH = Path.home() / ".config" / "waypy" / "config.yaml"


class WaypyConfig:
    def __init__(self, path):
        self.path = path
        self.waybar_configs_dir = None
        self.hyprland_configs_dir = None
        self._load()

    def _load(self):
        if not self.path.exists():
            logger.warning(
                f"Config file {self.path} does not exist. Using defaults if available."
            )
            return

        try:
            with self.path.open() as f:
                data = yaml.safe_load(f) or {}

            self.waybar_configs_dir = data.get("waybar_configs_dir")
            self.hyprland_configs_dir = data.get("hyprland_configs_dir")

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
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    logger.propagate = False
    return logger


logger = setup_logging()


def waybar_reload(args):
    logger.info("Attempting to reload Waybar...")

    try:
        result_kill = subprocess.run(
            ["pkill", "-x", "waybar"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        if result_kill.returncode == 0:
            logger.info("Killed existing Waybar process(es).")
        else:
            logger.warning(
                "No Waybar process found to kill (or pkill returned non-zero)."
            )

    except Exception as e:
        logger.error(f"Error attempting to kill Waybar: {e}")
        sys.exit(1)

    try:
        result_start = subprocess.Popen(
            ["waybar"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        logger.info(f"Waybar started with PID {result_start.pid}.")
    except Exception as e:
        logger.error(f"Failed to start Waybar: {e}")
        sys.exit(1)


def completion_install(args):
    shell_path = os.environ.get("SHELL", "")
    detected_shell = os.path.basename(shell_path)

    logger.info(f"Detected shell: {detected_shell}")

    if detected_shell not in ["bash", "zsh"]:
        logger.warning(
            "Your shell is not explicitly supported by this helper. Supported: bash, zsh"
        )

    logger.info("To enable completion temporarily, run:")
    logger.info(Fore.CYAN + '  eval "$(register-python-argcomplete waypy)"')

    logger.info("To enable completion permanently:")

    if detected_shell == "bash":
        logger.info("  Add this to your ~/.bashrc or ~/.bash_profile:")
        logger.info(Fore.CYAN + '  eval "$(register-python-argcomplete waypy)"')
    elif detected_shell == "zsh":
        logger.info("  Add this to your ~/.zshrc:")
        logger.info(Fore.CYAN + '  eval "$(register-python-argcomplete waypy)"')
    else:
        logger.info("  Add eval line to your shell's rc file.")


def build_parser():
    parser = argparse.ArgumentParser(
        prog="waypy",
        description="CLI + TUI tool for managing Waybar and Hyprland configuration.",
    )

    subparsers = parser.add_subparsers(
        dest="component", required=True, help="Component to manage"
    )

    waybar_parser = subparsers.add_parser("waybar", help="Manage Waybar")
    waybar_subparsers = waybar_parser.add_subparsers(
        dest="waybar_command", required=True, help="Waybar commands"
    )

    waybar_reload_parser = waybar_subparsers.add_parser(
        "reload", help="Hot reload Waybar"
    )
    waybar_reload_parser.set_defaults(func=waybar_reload)

    hyprland_parser = subparsers.add_parser("hyprland", help="Manage Hyprland")
    hyprland_subparsers = hyprland_parser.add_subparsers(
        dest="hyprland_command", help="Hyprland commands"
    )

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

    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()
