"""LED light shows.

An effect is just a list of frames, each frame being the set of LEDs lit at
that step. The tray steps through them on a timer and writes each frame with
`leds.apply_frame`, so effects stay pure data and are trivial to add.
"""

import collections

Effect = collections.namedtuple("Effect", "key label interval frames")


def _scanner(names):
    """Back and forth, without pausing twice on the end lights."""
    forward = [frozenset([n]) for n in names]
    if len(names) < 3:
        return forward
    return forward + forward[-2:0:-1]


def _chase(names):
    """One direction, wrapping around."""
    return [frozenset([n]) for n in names]


def _fill(names):
    """Fill up from one end, then drain back."""
    up = [frozenset(names[:i]) for i in range(len(names) + 1)]
    if len(up) < 3:
        return up
    return up + up[-2:0:-1]


def _blink(names):
    return [frozenset(names), frozenset()]


_BUILDERS = [
    ("scanner", "Scanner", 110, _scanner),
    ("chase", "Chase", 110, _chase),
    ("fill", "Fill", 130, _fill),
    ("blink", "Blink", 350, _blink),
]


def build(names):
    """Effects for the LEDs this machine actually has, skipping degenerate ones."""
    names = tuple(names)
    out = []
    for key, label, interval, builder in _BUILDERS:
        frames = builder(names)
        if len(frames) > 1:
            out.append(Effect(key, label, interval, frames))
    return out
