"""Switching what the Caps Lock key does, live, via KDE's XKB options.

Plasma stores keyboard options in ~/.config/kxkbrc. KWin watches that file
with a KConfigWatcher, which reacts to a D-Bus change notification rather than
to the write itself — so `kwriteconfig6 --notify` applies instantly, while a
plain write (or an editor) appears to do nothing until the next login.
"""

import collections
import os
import shutil
import subprocess

KXKBRC = os.path.expanduser("~/.config/kxkbrc")

CTRL_SHIFTED = "caps:ctrl_shifted_capslock"
CTRL_NOCAPS = "ctrl:nocaps"

Mode = collections.namedtuple("Mode", "label option short")

MODES = [
    Mode("Ctrl  —  Shift+Caps still locks", CTRL_SHIFTED, "Ctrl (Shift+Caps locks)"),
    Mode("Ctrl  —  locked, Caps Lock disabled", CTRL_NOCAPS, "Ctrl (locked)"),
    Mode("Normal Caps Lock", "", "Caps Lock"),
]

# Options this tool owns; anything else in kxkbrc is preserved untouched.
_OWNED_PREFIXES = ("caps:",)
_OWNED_EXACT = (CTRL_NOCAPS,)


def backend_available():
    """True if we can actually change the mapping on this system."""
    return shutil.which("kwriteconfig6") is not None


def current_options():
    """The raw Options= value from [Layout] in kxkbrc."""
    try:
        with open(KXKBRC) as fh:
            in_layout = False
            for line in fh:
                line = line.strip()
                if line.startswith("["):
                    in_layout = line == "[Layout]"
                elif in_layout and line.startswith("Options="):
                    return line.split("=", 1)[1]
    except OSError:
        pass
    return ""


def active_mode():
    """The XKB option currently in effect, or "" for a plain Caps Lock key."""
    options = {o for o in current_options().split(",") if o}
    for mode in MODES:
        if mode.option and mode.option in options:
            return mode.option
    return ""


def set_mode(option):
    """Apply a mode, preserving unrelated XKB options the user may have set."""
    keep = [
        o for o in current_options().split(",")
        if o and not o.startswith(_OWNED_PREFIXES) and o not in _OWNED_EXACT
    ]
    if option:
        keep.append(option)
    _write("Options", ",".join(keep))
    # Without this, options removed from the list linger until the next login.
    _write("ResetOldOptions", "true", "bool")


def _write(key, value, type_=None):
    cmd = ["kwriteconfig6", "--notify", "--file", "kxkbrc", "--group", "Layout", "--key", key]
    if type_:
        cmd += ["--type", type_]
    cmd.append(value)
    try:
        subprocess.run(cmd, check=False)
    except OSError:
        pass
