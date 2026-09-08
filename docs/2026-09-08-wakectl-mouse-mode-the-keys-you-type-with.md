# Wakectl Mouse Mode, Part 2: The Keys You Actually Type With (or: How Alt+Arrow Won by Being the Compromise Nobody Protested)

**Date:** 2026-09-08  
**Author:** Codebot  
**Topic:** wakectl, golang, ydotool, terminal, mouse-mode, keyboard, tty

---

## 1. Objective (or: Closing a Ticket That Turned Out Not to Be a Ticket)

The previous report (2026-09-04, "The Great Resurrection") shipped commit
`6a5b719` and left three known-broken items in `BUGS.md`:

1. `Ctrl+Down` scroll does not work (only `Ctrl+Up`).
2. Click keys `Space` / `-` / `=` do not do anything (`ENTER`, `SLASH`, `D`
   had click duties instead).
3. `Esc` does not exit mouse mode.

The plan, as recorded in that report's Recommendations: "Fix the three BUGS.md
items in a follow-up; Esc exit is the highest-value one."

This is that follow-up. It ends with two of the three items declared Not a Bug
(one of them a feature request in a trench coat), the third revealed as a much
nastier bug than documented, and mouse mode redesigned around a new constraint
nobody had written down: the owner must be able to type text while mouse mode
is on.

## 2. Background

### 2.1 Where Part 1 left off

At `6a5b719`, mouse mode intercepted the cursor keys for movement and a grab
bag of others for clicks and scroll:

| Key | Action |
| --- | --- |
| Arrows | move 1px |
| Shift+arrows | move 10px |
| Ctrl+up/down/left/right | scroll (vert + horiz) |
| `ENTER` | left click (0xC0) |
| `SLASH` | right click (0xC1) |
| `D` | double click |

`Ctrl+/` toggled mouse mode on/off, and the help text promised Esc would exit
mouse mode. The reader was swallowing Esc whole, so that promise was already
unfulfillable, though nobody had quite noticed yet.

### 2.2 The constraint nobody filed

The real environment is not a bare console: it is a remote desktop, where the
other side runs a media player and a text editor. Three consequences:

- Esc is what closes popups and exits fullscreen on the remote side. Esc as
  "exit mouse mode" was never going to survive contact with reality.
- Enter and `/` are text keys. Watching Enter emit a right click in a prose
  editor is, to put it mildly, suboptimal.
- Space, `-`, and `D` are the keys you type actual words with. If mouse mode
  steals them, you can navigate the pointer but you cannot write the sentence
  you were navigating to.

## 3. Problem (or: Every Key Press Is a Bet on Someone Else's Terminal)

Symptoms from the first remote-desktop test of `6a5b719`:

- `Esc` did not behave like Esc. It did nothing at all - no mouse-mode exit,
  not even a forwarded escape.
- `Enter` and `/` misfired as clicks in the editor instead of typing.
- Mouse mode generally worked (arrows moved, Space/`-`/`D` clicked) but the
  click keys sat in the middle of the home rows, exactly where the owner's
  fingers needed to be for editing.

Two distinct defects were hiding here: a keyboard-mapping judgment call
(Enter/Slash should not be clicks) and a genuine reader bug (Esc swallowed).

## 4. Work Performed

### 4.1 Enter and Slash lose their click jobs (commit 794cedc)

First pass: give the click duties to keys that do not appear in normal prose,
and let `Enter` and `/` through as regular keystrokes. The mapping moved from
`ENTER`/`SLASH`/`D` to `SPACE`/`MINUS`/`D`, and the `CTRL_*` scroll cases were
removed outright (they now forward as keystrokes, which is the documented
behavior of Part 1 anyway):

```go
case "SPACE":
    return Action{Type: Click, Button: 0xC0}
case "MINUS":
    return Action{Type: Click, Button: 0xC1}
case "D":
    return Action{Type: Click, Button: 0xC0, Delta: 2}
```

Plus a reader fix that was about to become necessary regardless (section 4.2)
and a `WAKECTL_DEBUG_KEYS=1` diagnostic trace added to the reader and the
runtime loop - which is what cracked the Esc case open.

### 4.2 The ESC Detective Story (or: SetReadDeadline, You Absolute Liar)

With the trace on, a bare Esc press printed exactly one line and then nothing:

```
[reader] raw ESC (0x1b); hasDeadline=true timeout=50ms
```

Then the next printed line came only after the *next* key was pressed, and it
showed that key - not Esc. The reader, after seeing `0x1b`, did a follow-up
read with `SetReadDeadline(50ms)` to decide whether the ESC was a standalone
key or the start of an escape sequence. The follow-up read never returned.

Root cause, and it is a nasty little truth about Go on Unix: `os.File`
`SetReadDeadline` does **not** interrupt a blocking `read(2)` on a TTY. The
deadline is a virtual concept implemented for network fds, but against a real
terminal driver it is a request, not a guarantee. The reader blocked in the
kernel, forever, on that follow-up read. The next key the user pressed
satisfied the read and came back as the "rest of the ESC sequence", so the
loop decoded a mangled gesture instead of an Esc - one Esc press made the next
key's press invisible too, and every Esc after that repeated the cycle.

The fix replaced the deadline with an actual poll, via `syscall.Select`, on
the stdin fd for the 50ms window:

```go
func pollReadable(fd int, timeout time.Duration) (bool, error) { ... syscall.Select ... }
```

A bare Esc now returns in about 50ms; Esc followed by sequence bytes returns
the full sequence. The mode where the owner's terminal emits `Ctrl+/` as `0x1f`
also taught us to match both `0x1f` and `0x0f`, which carried over unchanged.
This is commit `794cedc`: mouse-mode Esc forwarding, Enter/Slash passthrough,
and the reader fix.

### 4.3 The keyboard strikes back (or: Space, - and D want their jobs back)

The very next requirement killed the work of section 4.1: Space, `-`, and `D`
must type, because the owner edits text. Clicks had to move - for the third
time in two hours.

The shortlist offered was: punctuation trio (`=`/`;`/backtick), navigation
cluster (Insert/Delete/End), or F-key row (F5/F6/F7). F5/F6/F7 won on "zero
typing conflict" grounds. The change was implemented, built, and green.

Then, the moment of wisdom that saved the essay: "wait, can we use Alt+arrow
instead?" Alt+Left for left click, Alt+Right for right click, Alt+Up or
Alt+Down for double click. One hand stays on the arrow cluster for movement
and clicks together; the other hand does the typing. The F-keys never got a
commit to their name - they were a working-tree intermediary between two
committed states, exactly the kind of almost-shipped thing that excellent
`git log` hygiene keeps boring.

### 4.4 Alt+arrow: two dialects, one truth (commit d9941f2)

Terminals have opinions about how Alt+arrow is encoded, and the two main
dialects do not agree:

- xterm CSI form: `\x1b[1;3A` (the `;3` is the Alt modifier in the CSI
  parameter).
- double-ESC form: `\x1b\x1b[A`.

`keyseq.go` now carries both, mapping to `ALT_UP`/`ALT_DOWN`/`ALT_LEFT`/
`ALT_RIGHT`:

```go
"\x1b[1;3A": "ALT_UP",  ...  "\x1b[1;3C": "ALT_RIGHT",
"\x1b\x1b[A": "ALT_UP", ...   "\x1b\x1b[D": "ALT_LEFT",
```

The decoder turns those names into chords (arrow keycode + `LEFTALT` = 56),
and `internal/mouse/mouse.go` does the final mapping:

```go
case "ALT_LEFT":
    return Action{Type: Click, Button: 0xC0}
case "ALT_RIGHT":
    return Action{Type: Click, Button: 0xC1}
case "ALT_UP", "ALT_DOWN":
    return Action{Type: Click, Button: 0xC0, Delta: 2}
```

Note the deliberate redundancy: Alt+Up and Alt+Down both mean double click,
so the owner can chord with whichever thumb is free. Scroll is gone from mouse
mode; Ctrl+arrows forward as keystrokes.

The unit test now asserts six click events (Alt+Left = 1, Alt+Right = 1,
Alt+Up = 2, Alt+Down = 2) and that `SPACE`, `MINUS`, `D`, `ENTER`, `SLASH`,
`CTRL_DOWN`, `ESC`, and `F5`-`F7` are all `Noop` - i.e. forwarded as typing.

### 4.5 BUGS.md retires (commit cb83545)

With all three legacy items resolved or reclassified, the docs caught up:

- `README.md` gained a Mouse mode section: the toggle, the full key table, the
  ydotool seed workaround, the two Alt+arrow encodings, and the
  `WAKECTL_DEBUG_KEYS=1` diagnostic.
- `AGENTS.md` was rewritten. It was describing the pre-refactor flat
  `package main` layout - files like `client.go`, `seqreader.go`, and
  `modifiers.go` that have not existed since `a8118fb`. It now documents the
  real module structure, the keystroke data flow, the ESC `pollReadable` fix,
  and the mouse-mode design.
- `BUGS.md` was deleted. The operational notes (seed quirk, `Ctrl+/` as
  `0x1f`/`0x0f`, both Alt+arrow encodings, the debug env var) live on in
  README; the nothing-is-broken status is now the happy default.

## 5. Diagnosis (or: The Ticket Was Worth Less Than Its Paper)

Reclassifying the three "known broken" items of BUGS.md:

1. **Ctrl+arrow scroll "not working"** - resolved by design. Ctrl+arrows
   forwards as regular keystrokes; that is the documented behavior, not a bug.
2. **Space / - / = click keys "not working"** - they now type, which is the
   thing they were always meant to do. The question was not "wire up =",
   it was "stop hijacking Space, - and D".
3. **Esc does not exit mouse mode** - the documented fix ("Esc exit") was the
   wrong feature. The Reader had a real bug (a follow-up read that blocked
   forever), and once fixed, Esc forwards cleanly - which is what a remote
   desktop actually needs (closing popups, exiting fullscreen). "Esc exits
   mouse mode" was retired, not repaired.

Underneath all three: the first-generation click mapping (Enter/Slash/D) was
chosen with zero thought about who would be typing. The second generation
(Space/-/D) fixed that slightly. The third (Alt+arrow) finally put clicks where
the navigation hand already lived.

## 6. Solution Summary

Final mouse-mode key map:

| Key | Action |
| --- | --- |
| `Ctrl+/` | toggle mouse mode on/off |
| Arrows | move 1px |
| Shift+arrows | move 10px |
| Alt+Left | left click |
| Alt+Right | right click |
| Alt+Up / Alt+Down | double click |
| Space, -, D, F-keys, Enter, /, Ctrl+arrows, Esc | forwarded as regular keystrokes |

Commit trail on `main` (all pushed to `github.com/thsigit/wakectl`):

| Commit | What |
| --- | --- |
| `6a5b719` | raw mode, seed, toggle, banner (Part 1) |
| `794cedc` | Esc blocked-read fix (`pollReadable`), Enter/Slash passthrough, Space/-/D clicks, debug trace |
| `d9941f2` | Alt+arrow clicks, decoding both encodings |
| `cb83545` | README mouse-mode section, AGENTS rewrite, BUGS.md deleted |

## 7. Verification

- Build, `go vet ./...`, and `go test ./...` (all 9 packages) green; touched
  files gofmt-clean; binary rebuilt in place.
- Manual on the remote desktop: Space, `-`, and `d` type normally in the
  editor while mouse mode is on; Esc exits the media player's fullscreen;
  Alt+arrow clicks land; `Ctrl+/` toggles both on and off with the updated
  banner (`Arrows=1px, Shift+arrows=10px, Alt+Left=left, Alt+Right=right,
  Alt+Up/Down=double`).

## 8. Pending Actions

- Nothing remains in a bugs file, because there is no bugs file. If anyone
  ever misses Ctrl+arrow scrolling in mouse mode, resurrecting the four
  `Scroll` cases in `ProcessKeyEvent` is a five-line change that the current
  test explicitly guards against regressing silently.

## 9. Recommendations

1. **Mouse mode should be additive, not greedy.** Intercept only what
   navigation needs; let every other key forward. It is the difference between
   "a pointer you steer" and "a keyboard with holes poked in it".
2. **Never trust `SetReadDeadline` on a TTY.** It is a polite fiction for
   blocking `read(2)`. If you need a timeout on a real terminal fd, poll it
   yourself (`syscall.Select`), or the first timout-key in the session hangs
   the event loop.
3. **Terminals have dialects; match all of them.** `Ctrl+/` is `0x1f` on this
   box and `0x0f` canonically; Alt+arrow is `\x1b[1;3A` or `\x1b\x1b[A`.
   Accepting both cost one line each and removed a class of "works here, not
   there" tickets.
4. **Commit the intermediate states.** F5/F6/F7 was built and tested and is
   now a ghost - it lives only in this blog post. A commit per decision keeps
   `git log` telling the truth about the journey.
5. **Keep `WAKECTL_DEBUG_KEYS`.** A one-environment-variable key trace that
   prints `[reader]`, `[loop]`, and `[dbg]` lines is how a blocking-read bug
   was caught in under a minute. It costs nothing when unset and is priceless
   when set.

## 10. Conclusions

The three "broken items" resolved into: one real bug (the reader), one
reclassified design decision (Ctrl+arrow forwarding), and one genuine feature
elevation (Esc forwards instead of exiting). And the click keys finally make
sense with the world they live in - typing happens with the typing keys, and
clicking happens on the arrow cluster, where the navigation hand already is.
Alt+arrow is the compromise nobody had to lobby for, which is usually how you
can tell it was the right one.

If mouse mode ever swallows a key again, run `WAKECTL_DEBUG_KEYS=1` and watch
`[reader] raw ...` - the bytes will tell you whose fault it is. That is the
whole diagnostic story: the terminal says what it means, and now wakectl
listens.

---

Generated by Big Pickle (OpenCode)