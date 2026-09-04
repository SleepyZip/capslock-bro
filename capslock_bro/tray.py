"""The tray icon itself."""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QActionGroup, QColor, QFont, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from . import leds, xkb

ON_COLOR = "#e8542f"      # a genuine Caps Lock
OFF_COLOR = "#8a8a8a"      # dark
FORCED_COLOR = "#7d5bed"   # driven by hand, not a real lock

POLL_MS = 200
GRACE_TICKS = 3            # let sysfs catch up before trusting a disagreement


def make_icon(on, forced=False):
    """An 'A' badge: filled when the LED is lit, outlined when dark.

    Colours are fixed rather than themed, because Plasma does not recolour
    StatusNotifierItem pixmaps — these read on light and dark panels alike.
    """
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
        pen.setWidth(5)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(4, 4, size - 9, size - 9, 13, 13)
        p.setPen(QColor(dark))
    font = QFont()
    font.setPixelSize(38)
    font.setBold(True)
    p.setFont(font)
    p.drawText(pm.rect(), Qt.AlignCenter, "A")
    p.end()
    return QIcon(pm)


class Indicator:
    def __init__(self, app):
        self.app = app
        self.icons = {(on, f): make_icon(on, f)
                      for on in (False, True) for f in (False, True)}
        self.state = False
        self.shown = None
        self.real_state = False
        self.override = None   # None = tracking reality, bool = forced value
        self.grace = 0

        self.can_remap = xkb.backend_available()
        self.can_force = leds.can_drive_leds()

        self.menu = QMenu()
        self.status = self.menu.addAction("Caps Lock: …")
        self.status.setEnabled(False)

        self.menu.addSeparator()
        header = self.menu.addAction("Caps key acts as:")
        header.setEnabled(False)

        group = QActionGroup(self.menu)
        group.setExclusive(True)
        self.mode_actions = []
        for mode in xkb.MODES:
            act = self.menu.addAction("   " + mode.label)
            act.setCheckable(True)
            act.setEnabled(self.can_remap)
            group.addAction(act)
            act.triggered.connect(lambda _=False, o=mode.option: self.set_mode(o))
            self.mode_actions.append((act, mode.option))
        if not self.can_remap:
            note = self.menu.addAction("   (needs KDE Plasma 6 — kwriteconfig6 not found)")
            note.setEnabled(False)

        self.menu.addSeparator()
        self.force_action = self.menu.addAction("Force Caps LED on")
        self.force_action.setCheckable(True)
        self.force_action.setEnabled(self.can_force)
        self.force_action.triggered.connect(self.toggle_force)
        if not self.can_force:
            note = self.menu.addAction("   (needs membership in the 'input' group)")
            note.setEnabled(False)

        self.menu.addSeparator()
        self.menu.addAction("Quit").triggered.connect(app.quit)
        self.menu.aboutToShow.connect(self.refresh_mode)

        self.tray = QSystemTrayIcon()
        self.tray.setContextMenu(self.menu)
        self.refresh_mode()
        self.tick()
        self.tray.show()

        self.timer = QTimer()
        self.timer.timeout.connect(self.tick)
        self.timer.start(POLL_MS)

    # -- mode -------------------------------------------------------------

    def mode_label(self):
        active = xkb.active_mode()
        for mode in xkb.MODES:
            if mode.option == active:
                return mode.short
        return xkb.MODES[-1].short

    def refresh_mode(self):
        active = xkb.active_mode()
        for act, option in self.mode_actions:
            act.setChecked(option == active)
        self.update_text()

    def set_mode(self, option):
        xkb.set_mode(option)
        self.update_text()

    # -- LED --------------------------------------------------------------

    def toggle_force(self, checked):
        if checked:
            self.override = True
            leds.set_caps_led(True)
        else:
            self.override = None
            leds.set_caps_led(self.real_state)
        self.grace = GRACE_TICKS
        self.tick()

    # -- rendering --------------------------------------------------------

    def update_text(self):
        on = "ON" if self.state else "OFF"
        forced = self.override is not None
        label = f"Caps Lock: {on}" + ("  (LED forced)" if forced else "")
        self.status.setText(label)
        tip = [label, f"Caps key acts as: {self.mode_label()}"]
        if forced:
            tip.append("LED is driven manually — not the real lock state.")
        self.tray.setToolTip("\n".join(tip))

    def tick(self):
        on = leds.caps_led_on()
        if self.grace > 0:
            self.grace -= 1
        elif self.override is None:
            self.real_state = on
        elif on != self.override:
            # A real Caps Lock change reclaimed the LED; stop overriding.
            self.override = None
            self.force_action.setChecked(False)
        self.state = on
        key = (on, self.override is not None)
        if key != self.shown:
            self.shown = key
            self.tray.setIcon(self.icons[key])
        self.update_text()
