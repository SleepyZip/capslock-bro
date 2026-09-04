"""Tray icons.

Art ships in assets/ and is overridable per state by dropping image files
into ~/.config/capslock-bro/icons/ — see README. The drawn fallback exists
for states with no art at all; its colours are fixed rather than themed,
because Plasma does not recolour StatusNotifierItem pixmaps, and these read
on light and dark panels alike.
"""

import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPen, QPixmap

ON_COLOR = "#e8542f"      # a genuine Caps Lock
OFF_COLOR = "#8a8a8a"      # dark
FORCED_COLOR = "#7d5bed"   # driven by hand, not a real lock

USER_DIR = os.path.expanduser("~/.config/capslock-bro/icons")
ASSET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
SUFFIXES = (".svg", ".png", ".svgz", ".xpm")

STATES = ("off", "on", "forced-off", "forced-on")


def _icon_from(directory, state):
    for suffix in SUFFIXES:
        path = os.path.join(directory, state + suffix)
        if os.path.isfile(path):
            icon = QIcon(path)
            if not icon.isNull():
                return icon
    return None


def _user_icon(state):
    return _icon_from(USER_DIR, state)


def _bundled_icon(state):
    return _icon_from(ASSET_DIR, state)


def draw(on, forced=False):
    """An 'A' badge: filled when the LED is lit, outlined when dark."""
    size = 64
    lit = FORCED_COLOR if forced else ON_COLOR
    dark = FORCED_COLOR if forced else OFF_COLOR
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    if on:
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(lit))
        p.drawRoundedRect(2, 2, size - 4, size - 4, 14, 14)
        p.setPen(QColor("#ffffff"))
    else:
        pen = QPen(QColor(dark))
        pen.setWidth(6)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(5, 5, size - 10, size - 10, 13, 13)
        p.setPen(QColor(dark))
    font = QFont()
    font.setPixelSize(40)
    font.setBold(True)
    p.setFont(font)
    p.drawText(pm.rect(), Qt.AlignCenter, "A")
    p.end()
    return QIcon(pm)


def load_all():
    """{(on, forced): QIcon} — user art, else bundled art, else drawn.

    Resolution is per state rather than all-or-nothing, so replacing a single
    icon does not oblige you to supply the other three.
    """
    icons = {}
    for on in (False, True):
        for forced in (False, True):
            state = ("forced-" if forced else "") + ("on" if on else "off")
            icons[(on, forced)] = (_user_icon(state)
                                   or _bundled_icon(state)
                                   or draw(on, forced))
    return icons
