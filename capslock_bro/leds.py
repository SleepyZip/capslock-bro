"""Reading and driving keyboard lock LEDs.

Reading goes through sysfs, which is world-readable, so the indicator works
for everyone. Driving a LED writes an EV_LED event to the evdev node, which
needs write access to /dev/input/event* — on most distributions that means
membership in the `input` group. It deliberately does not need root.
"""

import glob
import os
import struct

EV_LED = 0x11

# evdev LED codes, by their sysfs name.
CODES = {
    "numlock": 0x00,
    "capslock": 0x01,
    "scrolllock": 0x02,
}

# Physical left-to-right order on a conventional keyboard, which is what a
# scrolling effect needs to look right.
STRIP = ("numlock", "capslock", "scrolllock")

_EVENT_FMT = "llHHi"


def _led_dirs(name):
    return glob.glob("/sys/class/leds/*::%s" % name)


def available():
    """Lock LEDs present on at least one keyboard, in physical order."""
    return tuple(n for n in STRIP if _led_dirs(n))


def devices_for(name):
    """evdev nodes of every keyboard exposing this LED.

    Resolved through sysfs on each call rather than cached, so hotplugging a
    keyboard — and the event-number churn that follows — is handled.
    """
    nodes = []
    for led in _led_dirs(name):
        try:
            for entry in os.listdir(os.path.join(led, "device")):
                if entry.startswith("event"):
                    nodes.append("/dev/input/" + entry)
                    break
        except OSError:
            continue
    return nodes


def is_on(name):
    """True if this LED is lit on any keyboard."""
    for led in _led_dirs(name):
        try:
            with open(os.path.join(led, "brightness")) as fh:
                if int(fh.read().strip()) > 0:
                    return True
        except (OSError, ValueError):
            continue
    return False


def caps_led_on():
    return is_on("capslock")


def can_drive():
    """True if we may write to at least one keyboard's evdev node."""
    for name in available():
        if any(os.access(node, os.W_OK) for node in devices_for(name)):
            return True
    return False


def set_led(name, on):
    """Force one LED on or off across every keyboard that has it.

    The kernel owns these lights; anything that legitimately updates a lock
    state will overwrite what we write here. That is intentional.
    """
    code = CODES.get(name)
    if code is None:
        return 0
    event = struct.pack(_EVENT_FMT, 0, 0, EV_LED, code, 1 if on else 0)
    driven = 0
    for node in devices_for(name):
        try:
            with open(node, "wb", buffering=0) as fh:
                fh.write(event)
            driven += 1
        except OSError:
            continue
    return driven


def apply_frame(lit, names=None):
    """Light exactly the LEDs in `lit`, darkening the rest of `names`."""
    for name in (names if names is not None else available()):
        set_led(name, name in lit)


def snapshot():
    """Current state of every available LED, for restoring after an effect."""
    return {name: is_on(name) for name in available()}


def restore(snap):
    for name, on in snap.items():
        set_led(name, on)
