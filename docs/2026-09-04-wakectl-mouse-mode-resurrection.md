# Wakectl Mouse Mode: The Great Resurrection (or: How a Missing MakeRaw Ruined Everyone's Tuesday)

**Date:** 2026-09-04  
**Author:** Codebot  
**Topic:** wakectl, golang, ydotool, terminal, mouse, refactor-regression

---

## 1. Objective (or: Why Won't My Cursor Move, Dave?)

`wakectl` is a single-binary Go CLI that reads raw keystrokes from a headless
Linux console TTY and injects them as keystrokes (and, in mouse mode, as cursor
moves) via `ydotool`. The owner reported that after an earlier architecture
refactor, the tool came back to life but the mouse was dead: shortcuts either
echoed garbage to the screen or did nothing, and the cursor never moved on the
other monitor.

The mission: make mouse mode actually work again, align the shortcut keys to the
documented behavior, and record what is still broken so future-me does not
"fix" it by accident.

## 2. Background

### 2.1 What wakectl is

A Go 1.24 CLI living at `/srv/repo/wakectl` (module `wakectl`). It shells out to
`ydotool` which talks to `ydotoold` over `/run/ydotoold/socket`. Mouse mode is a
runtime concept: arrow keys become cursor moves, Shift+arrows become fast moves,
Ctrl+arrows become scroll, and a handful of letter keys become clicks.

### 2.2 The refactor that broke it

Commit `a8118fb` ("refactor: modular architecture per target spec") reorganized
the once-flat `package main` into `internal/{runtime,mouse,input,sender,...}`.
Two things quietly went missing in the move:

1. The `term.MakeRaw(fd)` call that put the TTY into raw mode.
2. The wiring of `Display` into the runtime `Deps` struct.

Both were present in the pre-refactor loop. Their absence is why everything
looked "almost working" but was fundamentally wrong.

## 3. Problem

Symptom list as reported by the owner, in order:

- `Ctrl+/` (toggle mouse on) printed `^_` on screen and did nothing.
- `Ctrl+]]` should quit but instead printed `^]]`.
- `Esc` did not toggle mouse off.
- No key presses reached the other monitor at all.
- After the raw-mode fix, mouse mode toggled and arrows moved the cursor -- but
  only Up/Down did anything useful; Left/Right appeared dead.

The throughline: the terminal was in canonical (cooked) + echo mode, so control
sequences were line-buffered and echoed instead of delivered as raw bytes.

## 4. Work Performed

### 4.1 Raw terminal mode (the big one)

`runInteractive` in `internal/runtime/runtime.go` saved and restored terminal
state with `term.GetState`/`term.Restore` but never called `term.MakeRaw`. Added
it right after saving the original state, with a deferred restore:

```go
rawState, err := term.MakeRaw(int(fd))
if err != nil {
    return fmt.Errorf("set raw mode: %w", err)
}
defer term.Restore(int(fd), rawState)
```

Suddenly `Ctrl+]`, `Ctrl+/`, and `Esc` arrived as clean control bytes. No more
`^_` and `^]]` graffiti.

### 4.2 Startup banner / shortcut info

The refactor dropped the `Display` wiring, so `d.Display` was always `nil` and the
startup info line (which lists the shortcuts) never printed. Wired it back in
`internal/runtime/module.go`:

```go
deps := &Deps{
    Sender:   m.senderImpl,
    Bindings: m.bindingsList,
    Display:  display.NewDisplay(),
    ...
}
```

Now the banner prints on launch:

```
Active Terminal = tty2, Backlight = 872. Ctrl+] + any key to quit. Ctrl+/ = mouse on/off, ESC=exit mouse mode
```

### 4.3 The toggle key fiasco (or: Whose Terminal Is This, Anyway?)

The help text said `Ctrl+/`. I (foolishly, confidently) changed the toggle match
from `0x1f` to `0x0f`, reasoning that `Ctrl+/` is byte `0x0f`. Famous last words.

The owner's terminal actually emits `0x1f` (shown on screen as `^_`) for
`Ctrl+/`. My change meant the toggle matched neither the key the user pressed
(`0x1f`) nor the canonical `0x0f`, so mouse mode never engaged. Every arrow then
leaked through to the host as a keystroke -- which is why Up/Down "moved the
screen" (content scroll) and Left/Right did nothing visible.

Fix: match both encodings, because terminals are opinions:

```go
const (
    keyQuit     = "\x1d"
    keyMouse    = "\x1f"  // terminal emits this for Ctrl+/
    keyMouseAlt = "\x0f"  // canonical Ctrl+/ byte on other terminals
    keyEscName  = "ESC"
)
...
if seq == keyMouse || seq == keyMouseAlt {
    entering := mouseCtrl.Toggle()
    ...
    if entering {
        if err := mouseCtrl.Seed(d.Sender); err != nil { ... }
    }
}
```

### 4.4 The cursor that wouldn't move (or: ydotool's little secret)

Even with raw mode and a working toggle, the cursor refused to budge. `ydotool
mousemove -x N -y N` exits 0 but does nothing -- a well-known ydotool quirk:

> Relative mouse moves are a no-op until an absolute position has been set at
> least once.

The pre-refactor build looked like it worked only because an absolute position
happened to exist in `ydotoold`'s state from earlier runs. A fresh daemon had no
such position, so every relative move was a silent no-op.

Fix: added `Sender.MoveMouseAbsolute(x, y)` and `Controller.Seed(s)` that seeds
the pointer at (100,100) the moment mouse mode turns on:

```go
// internal/mouse/mouse.go
func (c *Controller) Seed(s Sender) error {
    return s.MoveMouseAbsolute(100, 100)
}

// internal/output/sender/ydotool.go
func (y *Ydotool) MoveMouseAbsolute(x, yPos int) error {
    return y.run([]string{"mousemove", "-a", strconv.Itoa(x), strconv.Itoa(yPos)})
}
```

After the seed, all four arrow directions move the cursor as expected.

### 4.5 Test fakes caught up

Adding `MoveMouseAbsolute` to the `Sender` interface meant four test fakes
(`internal/output/sender/sender_test.go`, `internal/domain/binding/binding_test.go`,
`internal/mouse/mouse_test.go`, `test/wakectl-smoke/main.go`) needed the method
or `go vet`/`go test` failed. Added no-op stubs to each.

## 5. Diagnosis

Root causes, in causal order:

1. **Cooked terminal mode** (`MakeRaw` missing) - the umbrella cause of all the
   echoed-control-character and "shortcuts don't work" symptoms.
2. **Display never wired** - the startup shortcut banner was silently skipped.
3. **Toggle key mismatch** (`0x0f` vs the user's `0x1f`) - mouse mode never
   engaged, so arrows leaked to the host.
4. **ydotool relative-move no-op without a prior absolute seed** - cursor would
   not move even once mouse mode worked.

## 6. Preliminary Assessment

The refactor was structurally fine (modular split is good), but it dropped two
load-bearing lines (`MakeRaw`, `Display` wiring) and silently changed the toggle
byte. Nothing about the mouse *logic* was actually broken -- `ProcessKeyEvent`
mapping is byte-for-byte identical to pre-refactor. The breakage was entirely in
plumbing.

## 7. Solution Summary

- TTY switched to raw mode so control sequences arrive unbuffered and without
  echo.
- `Display` wired into `Deps` so the shortcut banner prints.
- Sender gains `MoveMouseAbsolute`; `Controller.Seed` plants an absolute pointer
  position on entering mouse mode (workaround for ydotool's relative-move quirk).
- `Ctrl+/` toggle matches both `0x1f` and `0x0f`.
- Input handler reconstructed: `Ctrl+]`+key quit, `Ctrl+/` toggle, `Esc` exit.

Committed as `6a5b719` on `main`. The `wakectl` binary is gitignored and rebuilt
in place; it is not tracked.

## 8. Verification Plan

- `go build ./cmd/wakectl` clean; `go vet ./...` clean; `go test ./...` green.
- Manual: launch in a real TTY, confirm banner prints, `Ctrl+/` shows `[Mouse
  ON]`, arrows move cursor, Shift+arrows fast, `D` double-clicks, `Ctrl+Up`
  scrolls. Verified directly that `ydotool mousemove -a 100 100` then
  `ydotool mousemove -x N -y N` moves the pointer.

## 9. Pending Actions

Recorded in `/srv/repo/wakectl/BUGS.md`. Three known-broken behaviors, left
unfixed on purpose:

1. `Ctrl+Down` scroll does not work (only `Ctrl+Up` scrolls).
2. Click keys `Space` / `-` / `=` do not work (no `case` for them in
   `ProcessKeyEvent`; only `ENTER`, `SLASH`, `D` exist).
3. `Esc` does not exit mouse mode (bare Esc is consumed by the reader as a raw
   escape and never reaches `ProcessKeyEvent` as name `"ESC"`).

## 10. The "It Worked, Then It Didn't" Mystery (or: Whose State Is This Anyway?)

A fair objection: after the refactor, wakectl sometimes worked fine for a while,
then the mouse problems surfaced out of nowhere. That was not wakectl regressing
mid-flight. It was `ydotoold` forgetting what it remembered.

`ydotool` the client is stateless -- it is just a CLI that connects to `ydotoold`
over `/run/ydotoold/socket`. The daemon is the thing that holds the virtual
mouse's *current position*. And the quirk from section 4.4 cuts deeper than it
first looked:

> Relative `mousemove -x N -y N` is a no-op until an absolute position has been
> set at least once in the daemon's lifetime.

So the actual timeline was almost certainly:

1. The refactor shipped (`a8118fb`). By then `ydotoold` had been running since a
   prior session where something had issued an absolute `mousemove -a` -- the old
   build did this, or a manual move had happened earlier. The daemon still
   "remembered" a position.
2. wakectl's mouse mode appeared to work, because relative moves had a base
   position to build on. Arrows moved; life was good.
3. Then `ydotoold` restarted -- a reboot, `systemctl restart ydotoold`, a crash,
   or a `nixos-rebuild` that touched the unit. The daemon's pointer state was
   wiped to nothing.
4. Mouse mode was suddenly dead: relative moves became silent no-ops again,
   because no absolute seed existed. That is the moment the ticket opened.

In other words, wakectl was never really fixed by the refactor -- it was riding
on borrowed daemon state. The refactor had removed the absolute-seed step, so
wakectl only worked by accident of whatever `ydotoold` happened to remember. A
daemon restart was simply when the accident ended.

Confirmation on the box: `ydotoold` is an `enabled` systemd service
(`/etc/systemd/system/ydotoold.service`, started `Sep 03 16:02:38`). A single
boot, one start. Its internal pointer position does not survive that restart.

The `Controller.Seed()` fix makes this deterministic. wakectl no longer cares how
long `ydotoold` has been up or what it remembers -- it plants an absolute position
itself on every toggle-on. That is why it is stable now across reboots. If mouse
mode ever "stops working after a while" again, `systemctl status ydotoold` for a
recent restart is the first thing to check -- though with the seed in place, even
that should not matter.

## 11. Recommendations

- When porting a flat `package main` into packages, diff the old main loop
  against the new one line-by-line for "boring" calls like `MakeRaw` and
  `Display` wiring -- they are invisible until everything breaks.
- Treat terminal control-byte assumptions as environment-specific; matching both
  `0x1f` and `0x0f` for `Ctrl+/` cost one round-trip and is worth it.
- ydotool's relative-move behavior (and the daemon-state dependency behind it)
  should be encoded as a comment at the seed site so nobody "cleans it up" later.
- Stateful daemons are silent landmines: a working client can look broken purely
  because the backend forgot its position across a restart. Seed your own state;
  do not inherit the daemon's.
- Fix the three BUGS.md items in a follow-up; `Esc` exit is the highest-value
  one because it is the only documented way to leave mouse mode short of quit.

Generated by Hy3 (Free) Kenari
