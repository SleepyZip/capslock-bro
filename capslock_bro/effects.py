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


def _matrix(names):
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


def _laboratory(names):
    """Slow and deliberate: idle equipment ticking over in an empty lab.

    Each light gets its own beat with a dark gap after it, then all three
    together, then a long pause before it comes round again.
    """
    frames = []
    for n in names:
        frames.append(frozenset([n]))
        frames.append(frozenset())
    frames.append(frozenset(names))
    frames.append(frozenset())
    frames.append(frozenset())
    return frames


_BUILDERS = [
    ("scanner", "Scanner", 110, _scanner),
    ("matrix", "Matrix", 110, _matrix),
    ("fill", "Fill", 130, _fill),
    ("blink", "Blink", 350, _blink),
    ("laboratory", "Laboratory", 850, _laboratory),
]


def build(names):
    """Effects for the LEDs this machine actually has, skipping degenerate ones."""
    names = tuple(names)
    if not names:
        return []
    out = []
    for key, label, interval, builder in _BUILDERS:
        frames = builder(names)
        if len(frames) > 1:
            out.append(Effect(key, label, interval, frames))
    return out
