"""Entry point, single-instance guard, and autostart management."""

import argparse
import fcntl
import os
import shutil
import sys

from . import __version__

AUTOSTART_DIR = os.path.expanduser("~/.config/autostart")
AUTOSTART_FILE = os.path.join(AUTOSTART_DIR, "capslock-bro.desktop")

DESKTOP_ENTRY = """\
[Desktop Entry]
Type=Application
Name=Caps Lock Bro
Comment=Tray indicator for Caps Lock and what the Caps key does
Exec={exec_path}
Icon=input-keyboard
Terminal=false
Categories=Utility;
X-GNOME-Autostart-enabled=true
"""


def install_autostart():
    exec_path = shutil.which("capslock-bro") or os.path.abspath(sys.argv[0])
    os.makedirs(AUTOSTART_DIR, exist_ok=True)
    with open(AUTOSTART_FILE, "w") as fh:
        fh.write(DESKTOP_ENTRY.format(exec_path=exec_path))
    print(f"autostart installed: {AUTOSTART_FILE}")
    return 0


def uninstall_autostart():
    try:
        os.remove(AUTOSTART_FILE)
        print(f"autostart removed: {AUTOSTART_FILE}")
    except FileNotFoundError:
        print("autostart was not installed")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="capslock-bro",
        description="Tray indicator for Caps Lock, with a live switch for "
                    "what the Caps key does.",
    )
    parser.add_argument("--version", action="version",
                        version=f"capslock-bro {__version__}")
    parser.add_argument("--install-autostart", action="store_true",
                        help="start Caps Lock Bro automatically on login")
    parser.add_argument("--uninstall-autostart", action="store_true",
                        help="stop starting automatically on login")
    args = parser.parse_args(argv)

    if args.install_autostart:
        return install_autostart()
    if args.uninstall_autostart:
        return uninstall_autostart()

    # Single instance: hold an exclusive lock for the life of the process, so
    # autostart plus a manual launch cannot produce two tray icons.
    runtime = os.environ.get("XDG_RUNTIME_DIR", "/tmp")
    lock = open(os.path.join(runtime, "capslock-bro.lock"), "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print("Caps Lock Bro is already running", file=sys.stderr)
        return 0

    from PySide6.QtWidgets import QApplication, QSystemTrayIcon
    from .tray import Indicator

    app = QApplication(sys.argv)
    app.setApplicationName("Caps Lock Bro")
    app.setApplicationDisplayName("Caps Lock Bro")
    app.setDesktopFileName("capslock-bro")
    app.setQuitOnLastWindowClosed(False)

    if not QSystemTrayIcon.isSystemTrayAvailable():
        print("No system tray available on this desktop.", file=sys.stderr)
        return 1

    Indicator(app)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
