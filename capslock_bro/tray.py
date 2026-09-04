"""The tray icon itself."""

from PySide6.QtCore import QTimer
from PySide6.QtGui import QActionGroup
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from . import effects, icons, leds, xkb

POLL_MS = 200
GRACE_TICKS = 3            # let sysfs catch up before trusting a disagreement


class Indicator:
    def __init__(self, app):
        self.app = app
        self.icons = icons.load_all()   # {state name: QIcon}
        self.state = False
        self.shown = None
        self.real_state = False
        self.override = None   # None = tracking reality, bool = forced value
        self.grace = 0

        self.show = None       # active Effect, if any
        self.show_idx = 0
        self.show_snapshot = None

        self.can_remap = xkb.backend_available()
        self.can_drive = leds.can_drive()
        self.effects = effects.build(leds.available())

        self._build_menu()

        self.tray = QSystemTrayIcon()
        self.tray.setContextMenu(self.menu)
        self.refresh_mode()
        self.tick()
        self.tray.show()

        self.timer = QTimer()
        self.timer.timeout.connect(self.tick)
        self.timer.start(POLL_MS)

        self.show_timer = QTimer()
        self.show_timer.timeout.connect(self._step_show)

        app.aboutToQuit.connect(self.cleanup)

    # -- menu -------------------------------------------------------------

    def _build_menu(self):
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
        self.force_action.setEnabled(self.can_drive)
        self.force_action.triggered.connect(self.toggle_force)

        self.show_menu = self.menu.addMenu("Light show")
        self.show_menu.setEnabled(self.can_drive and bool(self.effects))
        show_group = QActionGroup(self.show_menu)
        show_group.setExclusive(True)
        self.show_actions = []
        for effect in self.effects:
            act = self.show_menu.addAction(effect.label)
            act.setCheckable(True)
            show_group.addAction(act)
            act.triggered.connect(lambda _=False, e=effect: self.start_show(e))
            self.show_actions.append((act, effect.key))
        self.show_menu.addSeparator()
        self.stop_action = self.show_menu.addAction("Stop")
        self.stop_action.setCheckable(True)
        self.stop_action.setChecked(True)
        show_group.addAction(self.stop_action)
        self.stop_action.triggered.connect(lambda _=False: self.stop_show())

        if not self.can_drive:
            note = self.menu.addAction("   (LED control needs the 'input' group)")
            note.setEnabled(False)

        self.menu.addSeparator()
        self.menu.addAction("Quit").triggered.connect(self.app.quit)
        self.menu.aboutToShow.connect(self.refresh_mode)

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
        self.stop_show()
        if checked:
            self.override = True
            leds.set_led("capslock", True)
        else:
            self.override = None
            leds.set_led("capslock", self.real_state)
        self.grace = GRACE_TICKS
        self.tick()

    # -- light show -------------------------------------------------------

    def start_show(self, effect):
        if self.show is None:
            # Only snapshot on the way in, so switching effects mid-show
            # doesn't capture the effect's own frame as "reality".
            self.show_snapshot = leds.snapshot()
        self.override = None
        self.force_action.setChecked(False)
        self.show = effect
        self.show_idx = 0
        self.show_timer.start(effect.interval)
        self.update_text()

    def _step_show(self):
        if self.show is None:
            return
        frame = self.show.frames[self.show_idx % len(self.show.frames)]
        self.show_idx += 1
        leds.apply_frame(frame)

    def stop_show(self):
        if self.show is None:
            return
        self.show_timer.stop()
        self.show = None
        if self.show_snapshot is not None:
            leds.restore(self.show_snapshot)
            self.show_snapshot = None
        for act, _ in self.show_actions:
            act.setChecked(False)
        self.stop_action.setChecked(True)
        self.grace = GRACE_TICKS
        self.update_text()

    def cleanup(self):
        """Never leave someone's keyboard lit up on exit."""
        self.stop_show()
        if self.override is not None:
            leds.set_led("capslock", self.real_state)

    # -- rendering --------------------------------------------------------

    def update_text(self):
        if self.show is not None:
            label = "Light show: %s" % self.show.label
            tip = [label, "Caps key acts as: %s" % self.mode_label()]
        else:
            on = "ON" if self.state else "OFF"
            forced = self.override is not None
            label = "Caps Lock: %s%s" % (on, "  (LED forced)" if forced else "")
            tip = [label, "Caps key acts as: %s" % self.mode_label()]
            if forced:
                tip.append("LED is driven manually — not the real lock state.")
        self.status.setText(label)
        self.tray.setToolTip("\n".join(tip))

    def _is_ctrl(self):
        """True when the Caps key is acting as Ctrl, in either Ctrl mode."""
        return bool(xkb.active_mode())

    def _set_icon(self, state):
        if state != self.shown:
            self.shown = state
            self.tray.setIcon(self.icons[state])

    def tick(self):
        if self.show is not None:
            # The LEDs are ours right now; infer nothing from them.
            self._set_icon(icons.state_name(self._is_ctrl(), False, True))
            self.update_text()
            return
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
        forced = self.override is not None
        self._set_icon(icons.state_name(self._is_ctrl(), on, forced))
        self.update_text()
