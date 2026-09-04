"""Tray icons.

A drawn default, overridable per state by dropping image files into
~/.config/capslock-bro/icons/ — see README. Colours in the drawn icons are
fixed rather than themed, because Plasma does not recolour
StatusNotifierItem pixmaps; these read on light and dark panels alike.
"""

import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPen, QPixmap

ON_COLOR = "#e8542f"      # a genuine Caps Lock
OFF_COLOR = "#8a8a8a"      # dark
FORCED_COLOR = "#7d5bed"   # driven by hand, not a real lock

USER_DIR = os.path.expanduser("~/.config/capslock-bro/icons")
SUFFIXES = (".svg", ".png", ".svgz", ".xpm")

STATES = ("off", "on", "forced-off", "forced-on")


def _user_icon(state):
    for suffix in SUFFIXES:
        path = os.path.join(USER_DIR, state + suffix)
        if os.path.isfile(path):
            icon = QIcon(path)
            if not icon.isNull():
                return icon
    return None


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
    """{(on, forced): QIcon}, preferring user-supplied art where present."""
    icons = {}
    for on in (False, True):
        for forced in (False, True):
            state = ("forced-" if forced else "") + ("on" if on else "off")
            icons[(on, forced)] = _user_icon(state) or draw(on, forced)
    return icons
