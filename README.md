# Caps Lock Bro

A tray indicator that tells you whether Caps Lock is on — and lets you change
what the Caps key actually does, live, without logging out.

If you've remapped Caps Lock to Ctrl, you've traded away the one key that told
you when you were shouting. This puts that back in the tray, and gives you a
switch to change your mind whenever you like.

```
Caps Lock: OFF
──────────────────────────────────────
Caps key acts as:
  ● Ctrl  —  Shift+Caps still locks
  ○ Ctrl  —  locked, Caps Lock disabled
  ○ Normal Caps Lock
──────────────────────────────────────
☐ Force Caps LED on
Light show                           ▸
──────────────────────────────────────
Quit
```

The icon is an `A` badge — solid when the light is on, outlined when it's off.

## The three modes

| Mode | XKB option | `<CAPS>` becomes |
|---|---|---|
| Ctrl, Shift+Caps still locks | `caps:ctrl_shifted_capslock` | `TWO_LEVEL` → `[Control_L, Caps_Lock]` |
| Ctrl, locked | `ctrl:nocaps` | `ONE_LEVEL` → `[Control_L]` |
| Normal Caps Lock | *(none)* | `[Caps_Lock]` |

The middle one is airtight: `ONE_LEVEL` means the key has no second level, so
even Shift+Caps resolves to `Control_L`. Caps Lock becomes unreachable from
that key rather than merely inconvenient.

Switching applies **instantly** and persists across reboots — it writes the same
config KDE reads at login, so it's a real change, not a session override.

## Requirements

- **KDE Plasma 6** (Wayland or X11) for mode switching — it drives `kxkbrc`
- **Python 3.9+** and **PySide6**
- Membership in the **`input` group** for the LED toggle only

Missing pieces degrade rather than crash: without `kwriteconfig6` the mode
switch greys out, without `input` group the LED toggle greys out, and the
indicator itself keeps working either way. Reading Caps Lock state uses sysfs,
which is world-readable, so that part works on any Linux desktop with a tray.

## Install

```bash
pipx install git+https://github.com/SleepyZip/capslock-bro
capslock-bro --install-autostart
capslock-bro &
```

Or from a clone:

```bash
git clone https://github.com/SleepyZip/capslock-bro
cd capslock-bro
pip install --user .
```

`--uninstall-autostart` undoes the login entry.

## How it works

**Mode switching.** Plasma keeps keyboard options in `~/.config/kxkbrc`. KWin
watches that file with a `KConfigWatcher`, which reacts to a **D-Bus change
notification** rather than to the write itself. So:

```bash
kwriteconfig6 --notify --file kxkbrc --group Layout \
  --key Options "caps:ctrl_shifted_capslock"     # applies instantly
```

Drop `--notify` — or edit the file in a text editor — and nothing happens until
your next login, with no error to tell you why. That one flag is most of what
this tool knows.

You can check what's actually live at any time:

```bash
xkbcomp -xkb "$DISPLAY" - | awk '/key <CAPS>/,/};/'
```

**LED state.** Read from `/sys/class/leds/*::capslock/brightness`, OR'd across
every keyboard, so it's correct no matter which one you typed on.

**Driving the LED.** Writes an `EV_LED` event straight to the evdev node. The
node list is re-resolved through sysfs on every write, so hotplugging a keyboard
and the event-number churn that follows are handled.

## About that LED toggle

It's a toy, and it's built so it can't lie to you:

- The icon turns **violet** while forced, so a manual light is never mistaken
  for a real Caps Lock.
- The override **surrenders automatically** if a genuine Caps Lock event
  reclaims the LED, and the checkbox unticks itself.
- Releasing it restores the light to the real lock state, which the app tracks
  separately whenever it isn't overriding.

It's a one-shot write, not a held state — anything that legitimately updates the
LED wins. That's what keeps it honest instead of fighting the kernel.

While a light show is running the icon stays violet and the app infers nothing
from the LEDs, since they belong to the effect rather than to your lock state.

### A note on the `input` group

Adding yourself to `input` (`sudo usermod -aG input $USER`) grants read access
to every input device on the system, which means any process running as you can
read your keystrokes. That's a real trade-off, and it's worth understanding
before you make it for a blinkenlight. The indicator works fine without it.

## Light show

You have three lock LEDs and they are just sitting there.

| Effect | What it does | Cycle |
|---|---|---|
| **Scanner** | Back and forth, KITT-style | 0.4s |
| **Matrix** | One direction, wrapping around | 0.3s |
| **Fill** | Fills up from Num Lock, then drains back | 0.8s |
| **Blink** | All three, together | 0.7s |
| **Laboratory** | Each light gets its own slow beat, then all three, then a long dark pause | 7.7s |

Effects are pure data — a list of frames, each frame being the set of LEDs lit
at that step:

```python
def _chase(names):
    return [frozenset([n]) for n in names]
```

Adding one is a function in `effects.py` and a line in `_BUILDERS`. Effects that
would degenerate on your hardware — a scanner across a single LED — are dropped
automatically, so a laptop with one light gets a shorter menu rather than a
broken one.

Your real lock states are captured when a show starts and restored when it
stops, including on quit. It will not leave someone's keyboard lit up.

## Icons

The icon tells you **what the Caps key does**, because that's the thing you
forget. Sunglasses mean it's acting as Ctrl; a plain keycap means it's an
ordinary Caps Lock. A tint layers the current state on top:

| | standard | amber | violet |
|---|---|---|---|
| **Sunglasses** — Caps is Ctrl | idle | Caps Lock genuinely on | LEDs driven by hand |
| **Plain keycap** — normal Caps Lock | off | Caps Lock on | LEDs driven by hand |

Only two base images ship. The amber and violet variants are composited at
load time, so your own art inherits them for free.

To use your own, drop images into `~/.config/capslock-bro/icons/`:

```
ctrl.png     normal.png            # the two you probably want
ctrl-locked.png     ctrl-forced.png       # optional, override the tint
normal-locked.png   normal-forced.png
```

`.svg`, `.png`, `.svgz` and `.xpm` are accepted. Each state resolves as: your
art for that exact state, else bundled art for it, else the base art tinted,
else a drawn fallback — per state rather than all-or-nothing.

Tray icons render around 22px, so favour bold shapes over detail. The
sunglasses survive that because they change the silhouette rather than adding
detail.

## Why not Fn + Caps Lock?

The obvious design is Caps for Ctrl and **Fn+Caps** for a real Caps Lock. On
most keyboards this is impossible, and it's worth knowing why.

Fn is resolved in keyboard **firmware**. On a Topre Realforce R3, pressing Fn
alone or Fn+Caps sends *nothing at all* over USB — verified by reading the evdev
node directly:

```
Caps Lock alone   →  keycode 58, hid 0x70039   ✓
Fn alone          →  (no events)               ✗
Fn + Caps Lock    →  (no events)               ✗
```

There is no event for the kernel to deliver, so no remapper — xkb, keyd, kanata,
udev hwdb — can ever bind it. Only firmware-level remapping could change that.
Hence Shift+Caps: a modifier the OS can actually see.

## License

MIT
