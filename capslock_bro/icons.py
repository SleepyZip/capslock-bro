"""Tray icons.

Two pieces of art carry the meaning: sunglasses when the Caps key is acting
as Ctrl, a plain keycap when it is an ordinary Caps Lock. Tints layer state on
top of that — amber when Caps Lock is actually on, violet when the LEDs are
being driven by hand. Tints are composited at load time, so custom art gets
them for free.
"""

import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPen, QPixmap

LOCKED_COLOR = "#e8542f"   # Caps Lock genuinely on
FORCED_COLOR = "#7d5bed"   # LEDs driven by hand, not by a lock
NEUTRAL_COLOR = "#8a8a8a"  # only used by the drawn fallback

TINT_STRENGTH = 0.55

USER_DIR = os.path.expanduser("~/.config/capslock-bro/icons")
ASSET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
SUFFIXES = (".svg", ".png", ".svgz", ".xpm")

BASES = ("ctrl", "normal")
VARIANTS = ("", "-locked", "-forced")
STATES = tuple(b + v for b in BASES for v in VARIANTS)

_TINTS = {"": None, "-locked": LOCKED_COLOR, "-forced": FORCED_COLOR}


def state_name(is_ctrl, locked, forced):
    """The icon state for a given situation. Forced outranks locked."""
    base = "ctrl" if is_ctrl else "normal"
    if forced:
        return base + "-forced"
    if locked:
        return base + "-locked"
    return base


def _pixmap_from(directory, name):
    for suffix in SUFFIXES:
        path = os.path.join(directory, name + suffix)
        if os.path.isfile(path):
            pm = QPixmap(path)
            if not pm.isNull():
                return pm
    return None


def _tint(pm, color):
    """Colourise while preserving the alpha channel."""
    out = QPixmap(pm)
    p = QPainter(out)
    p.setCompositionMode(QPainter.CompositionMode_SourceAtop)
    c = QColor(color)
    c.setAlphaF(TINT_STRENGTH)
    p.fillRect(out.rect(), c)
    p.end()
    return out


def draw(is_ctrl, color):
    """Fallback for when no art is available at all."""
    size = 64
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(color))
    pen.setWidth(6)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    p.drawRoundedRect(5, 5, size - 10, size - 10, 13, 13)
    p.setPen(QColor(color))
    font = QFont()
    font.setPixelSize(40)
    font.setBold(True)
    p.setFont(font)
    p.drawText(pm.rect(), Qt.AlignCenter, "^" if is_ctrl else "A")
    p.end()
    return pm


def load_all():
    """{state: QIcon} for every state.

    Each state resolves as: user art for that exact state, else the bundled
    art for that exact state, else the base art tinted for the variant, else
    a drawn fallback. Per state rather than all-or-nothing, so replacing one
    icon does not oblige you to supply the rest.
    """
    icons = {}
    for base in BASES:
        for variant in VARIANTS:
            state = base + variant
            pm = _pixmap_from(USER_DIR, state) or _pixmap_from(ASSET_DIR, state)
            if pm is None:
                root = _pixmap_from(USER_DIR, base) or _pixmap_from(ASSET_DIR, base)
                tint = _TINTS[variant]
                if root is not None:
                    pm = _tint(root, tint) if tint else root
                else:
                    pm = draw(base == "ctrl", tint or NEUTRAL_COLOR)
            icons[state] = QIcon(pm)
    return icons
