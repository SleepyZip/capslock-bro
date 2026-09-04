"""Reading and driving the keyboard Caps Lock LED.

Reading goes through sysfs, which is world-readable, so the indicator works
for everyone. Driving the LED writes an EV_LED event to the evdev node, which
needs write access to /dev/input/event* — on most distributions that means
membership in the `input` group. It deliberately does not need root.
"""

import glob
import os
import struct

EV_LED = 0x11
LED_CAPSL = 0x01

_EVENT_FMT = "llHHi"


def led_dirs():
    """sysfs directories for every Caps Lock LED currently present."""
    return glob.glob("/sys/class/leds/*::capslock")


def led_devices():
    """evdev nodes of every keyboard exposing a Caps Lock LED.

    Resolved through sysfs on each call rather than cached, so hotplugging a
    keyboard (and the event-number churn that comes with it) is handled.
    """
    nodes = []
    for led in led_dirs():
        try:
            for entry in os.listdir(os.path.join(led, "device")):
                if entry.startswith("event"):
                    nodes.append("/dev/input/" + entry)
                    break
        except OSError:
            continue
    return nodes


def caps_led_on():
    """True if any keyboard's Caps Lock LED is currently lit."""
    for led in led_dirs():
        try:
            with open(os.path.join(led, "brightness")) as fh:
                if int(fh.read().strip()) > 0:
                    return True
        except (OSError, ValueError):
            continue
    return False


def can_drive_leds():
    """True if we may write to at least one keyboard's evdev node."""
    return any(os.access(node, os.W_OK) for node in led_devices())


def set_caps_led(on):
    """Force every Caps Lock LED on or off. Returns the number driven.

    The kernel owns this light; anything that legitimately updates the lock
    state will overwrite what we write here. That is intentional.
    """
    event = struct.pack(_EVENT_FMT, 0, 0, EV_LED, LED_CAPSL, 1 if on else 0)
    driven = 0
    for node in led_devices():
        try:
            with open(node, "wb", buffering=0) as fh:
                fh.write(event)
            driven += 1
        except OSError:
            continue
    return driven
