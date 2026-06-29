# Readline Character Support Matrix

A complete catalogue of every readline-relevant input the component can receive,
evaluated against the normative contract (`docs/tui_architecture_spec.md` §5,
§5.1) and the current implementation (`mapping_resolution_tui/loop.py` →
`key_to_action`, dispatched through `mapping_resolution_tui/reducer.py`).

## Scope note

The component implemented today is **BROWSING-mode only** (Epic 2 filter input).
`EDITING` and `CONFIRMING` modes do not exist yet, so every "Edit input" and
confirmation behavior in spec §5.1 is necessarily **planned / future epic**. The
"Current" column below therefore evaluates each key against its **filter-input**
contract, which is what `key_to_action` + the reducer cover now.

Any key that `key_to_action` does not recognise returns `None`; the loop then
skips dispatch (FR30), leaving root state and rendered output unchanged. This is
how the spec's mandated **no-op families** are satisfied today — by default.

## Bang-autocomplete reconciliation (spec §3.2/§3.3/§5.1)

The filter contract was reworked so that `filter.raw` is the single editable
buffer and the source of truth; `collisionOnly` (raw begins with `!`) and `text`
(raw minus a single leading `!`) are **derived** after every mutation. This
changes the rows below relative to the original toggle model:

- **`Tab` / `ctrl+i`** no longer toggles a metafilter. It now *autocompletes a
  leading `!`* into `filter.raw` (cursor → 1) **only** when the `Tab to view
  collisions` ghost is visible, and is a **no-op** otherwise (a second `Tab` must
  not clear the `!`). Implemented in TASK-003 as the `AutocompleteBang` action;
  the old `ToggleCollisionOnly` reducer action was retired.
- **`!`** is an ordinary printable character handled by `InsertCharacter`; it is
  no longer a metafilter toggle. A `!` inserted at index 0 *is* the collision
  metafilter by derivation.
- **`Backspace` / `ctrl+h` / DEL** at `filter.cursor == 0` is a **no-op**; the
  leading `!` deletes like any other character once the cursor sits at index 1.
  The old "clear metafilter at cursor 0" branch is removed, so `DeleteBackward`
  is now **partial** (🟠) until its cursor-0 behavior is verified to no-op.

## Status legend

| Symbol | Meaning |
|---|---|
| ✅ Implemented | Wired in `key_to_action` → reducer; matches the spec's filter-input behavior. |
| 🟡 No-op (compliant) | Spec mandates an explicit no-op; component ignores it (`None`). Behavior is correct. |
| 🔴 Gap (planned) | Spec mandates an **action**, but the component currently ignores the key. Needs a future slice. |
| 🟠 Partial | Implemented but simplified relative to the full spec contract. |
| ⚪ Out of scope | Not named in the spec; ignored, no requirement. Listed for completeness. |

## A. C0 control characters (`ctrl+@` … `ctrl+_`) and DEL

| Byte | Key | Readline function | Spec filter-input behavior (§5.1 / §5) | Current | Status |
|---|---|---|---|---|---|
| `\x00` | ctrl+@ | `set-mark` | — (not named) | `None` | ⚪ |
| `\x01` | ctrl+a | `beginning-of-line` | Set `filter.cursor = 0` | `MoveCursorHome` | ✅ |
| `\x02` | ctrl+b | `backward-char` | Cursor left, clamp at 0 | `MoveCursorLeft` | ✅ |
| `\x03` | ctrl+c | *(app)* interrupt | Enter EXIT confirmation; arm 2nd-ctrl+c SIGINT | Quits loop cleanly via `is_quit_key` | 🟠 |
| `\x04` | ctrl+d | `delete-char` | Delete char **at** cursor; no-op at end | `DeleteForward` | ✅ |
| `\x05` | ctrl+e | `end-of-line` | Set `filter.cursor = len(filter.raw)` | `MoveCursorEnd` | ✅ |
| `\x06` | ctrl+f | `forward-char` | Cursor right, clamp at `len(filter.raw)` | `MoveCursorRight` | ✅ |
| `\x07` | ctrl+g | `abort` | No-op (must NOT act like Esc/ctrl+c) | `None` | 🟡 |
| `\x08` | ctrl+h | `backward-delete-char` | Delete before cursor in `filter.raw`; no-op at cursor 0 (leading `!` deletes as ordinary char) | `DeleteBackward` (no-op at cursor 0) | ✅ |
| `\x09` | ctrl+i / Tab | `complete` → *(app)* | Autocomplete a leading `!` into `filter.raw` (cursor → 1) only when the `Tab to view collisions` ghost is visible; else no-op | `AutocompleteBang` (reducer no-ops unless ghost visible) | ✅ |
| `\x0a` | ctrl+j | `accept-line` (Enter) | Dispatch as Enter (edit selected row) | `None` | 🔴 |
| `\x0b` | ctrl+k | `kill-line` | Delete from cursor through end of `filter.raw` | `KillToEnd` | ✅ |
| `\x0c` | ctrl+l | `clear-screen` / `redraw-current-line` | Re-render only; MUST NOT mutate state | `None` (no forced redraw) | 🟠 |
| `\x0d` | ctrl+m | `accept-line` (Enter) | Dispatch as Enter (edit selected row) | `None` | 🔴 |
| `\x0e` | ctrl+n | `next-history` → *(app)* | Move selection down | `MoveSelectionDown` | ✅ |
| `\x0f` | ctrl+o | `operate-and-get-next` | — (not named) | `None` | ⚪ |
| `\x10` | ctrl+p | `previous-history` → *(app)* | Move selection up | `MoveSelectionUp` | ✅ |
| `\x11` | ctrl+q | `quoted-insert` | No-op (quoted insertion unsupported) | `None` | 🟡 |
| `\x12` | ctrl+r | `reverse-search-history` | No-op | `None` | 🟡 |
| `\x13` | ctrl+s | *(app)* submit / `forward-search-history` | Open accept confirmation if 0 collisions | `None` | 🔴 |
| `\x14` | ctrl+t | `transpose-chars` | No-op (text transform unsupported) | `None` | 🟡 |
| `\x15` | ctrl+u | `unix-line-discard` | Delete start…cursor; set cursor 0 | `KillToStart` | ✅ |
| `\x16` | ctrl+v | `quoted-insert` | No-op | `None` | 🟡 |
| `\x17` | ctrl+w | `unix-word-rubout` / `backward-kill-word` | Delete previous word run before cursor | `DeleteWordBackward` | ✅ |
| `\x18` | ctrl+x | command prefix (`ctrl+x ctrl+?` = `backward-kill-line`, `ctrl+x ctrl+u` = `undo`) | `backward-kill-line` = `unix-line-discard`; `undo` = no-op | `None` | 🔴 / 🟡 |
| `\x19` | ctrl+y | `yank` | No-op (paste arrives as printable text) | `None` | 🟡 |
| `\x1a` | ctrl+z | *(terminal suspend)* | — (not named) | `None` | ⚪ |
| `\x1b` | ctrl+[ / Esc | *(app)* + meta prefix | Clear `filter.raw` (clears derived metafilter + text); cursor 0 | `ClearFilter` | ✅ |
| `\x1c` | ctrl+\ | *(terminal SIGQUIT)* | — (not named) | `None` | ⚪ |
| `\x1d` | ctrl+] | — | — (not named) | `None` | ⚪ |
| `\x1e` | ctrl+^ | — | — (not named) | `None` | ⚪ |
| `\x1f` | ctrl+_ | `undo` / `revert-line` | No-op (undo out of scope) | `None` | 🟡 |
| `\x7f` | ctrl+? / DEL | `backward-delete-char` | Delete before cursor in `filter.raw`; no-op at cursor 0 (leading `!` deletes as ordinary char) | `DeleteBackward` (no-op at cursor 0) | ✅ |

## B. Meta / Alt functions named by the spec

Meta combos arrive as an ESC prefix (`\x1b` + key) or a distinct sequence.
`key_to_action` recognises `meta+d` and `meta+backspace` (the word kills); the
remaining meta functions are no-ops.

| Keys | Readline function | Spec filter-input behavior | Current | Status |
|---|---|---|---|---|
| `meta+d` | `kill-word` | Delete cursor → end of next word | `DeleteWordForward` | ✅ |
| `meta+backspace` | `backward-kill-word` | Delete previous word run | `DeleteWordBackward` | ✅ |
| `meta+r` | `revert-line` | No-op | `None` | 🟡 |
| `meta+t` | `transpose-words` | No-op | `None` | 🟡 |
| `meta+c` / `meta+l` / `meta+u` | case transforms | No-op | `None` | 🟡 |
| `meta+?` `meta+=` `meta+!` `meta+/` `meta+~` `meta+$` `meta+@` | completion variants | No-op | `None` | 🟡 |
| `meta+n` `meta+p` `meta+<` `meta+>` | history variants | No-op | `None` | 🟡 |
| `meta+y` `meta+.` `meta+_` `meta+ctrl+y` | yank / kill-ring variants | No-op | `None` | 🟡 |
| `ctrl+x…` / `meta+…` / vi-mode names | macro, shell-expand, glob, alias, dump, vi | No-op unless mapped elsewhere | `None` | 🟡 |

## C. Named escape sequences (blessed `Keystroke.name`)

| `name` | Key | Readline / app function | Spec filter-input behavior | Current | Status |
|---|---|---|---|---|---|
| `KEY_LEFT` | ← | `backward-char` | Cursor left | `MoveCursorLeft` | ✅ |
| `KEY_RIGHT` | → | `forward-char` | Cursor right | `MoveCursorRight` | ✅ |
| `KEY_BACKSPACE` | Backspace | `backward-delete-char` | Delete before cursor in `filter.raw`; no-op at cursor 0 | `DeleteBackward` (no-op at cursor 0) | ✅ |
| `KEY_ESCAPE` | Esc | *(app)* | Clear `filter.raw` (clears derived metafilter + text) | `ClearFilter` | ✅ |
| `KEY_TAB` | Tab | `complete` → *(app)* | Autocomplete leading `!` when `Tab to view collisions` ghost visible; else no-op | `AutocompleteBang` (reducer no-ops unless ghost visible) | ✅ |
| `KEY_ENTER` | Enter | `accept-line` | Edit selected row | `None` | 🔴 |
| `KEY_UP` | ↑ | *(app)* | Move selection up | `MoveSelectionUp` | ✅ |
| `KEY_DOWN` | ↓ | *(app)* | Move selection down | `MoveSelectionDown` | ✅ |
| `KEY_HOME` | Home | `beginning-of-line` | Set cursor 0 | `MoveCursorHome` | ✅ |
| `KEY_END` | End | `end-of-line` | Set cursor `len(filter.raw)` | `MoveCursorEnd` | ✅ |
| `KEY_DELETE` | Delete | `delete-char` | Delete at cursor | `DeleteForward` | ✅ |
| `KEY_SUP` / `KEY_PGUP` | Shift+↑ / PgUp | *(app)* | Page up; select first visible | `PageUp` | ✅ |
| `KEY_SDOWN` / `KEY_PGDOWN` | Shift+↓ / PgDn | *(app)* | Page down; select first visible | `PageDown` | ✅ |
| `KEY_INSERT` | Insert | — | — (not named) | `None` | ⚪ |

## Summary

| Status | Count (approx.) | Meaning |
|---|---|---|
| ✅ Implemented | 14 control + 2 meta + 12 named = **~28 bindings** | Printable insert (incl. literal `!`), Tab/ctrl+i bang autocomplete, cursor move (left/right/home/end), backspace/forward-delete with cursor-0 no-op, kill-line, unix-line-discard, word kills (back/forward), Esc clear, selection navigation (↑↓/ctrl+p/ctrl+n), page movement (Shift+↑↓/PgUp/PgDn). |
| 🟡 No-op (compliant) | **~14 families** | abort, quoted-insert, undo, transpose, yank, search/history, completion variants, case transforms, macro/shell/vi. |
| 🔴 Gap (planned) | **~4 bindings** | accept-line (Enter/ctrl+j/ctrl+m), submit (ctrl+s), `ctrl+x` prefix. |
| 🟠 Partial | **2** | `ctrl+c` (simple quit vs EXIT confirmation), `ctrl+l` (no forced redraw). |
| ⚪ Out of scope | **~7** | Control bytes the spec never names. |

> **TASK-004 status:** browsing navigation is implemented via the
> `MoveSelectionUp` / `MoveSelectionDown` actions (↑/↓ and the readline aliases
> `ctrl+p` / `ctrl+n`, one visible row per press, clamped at the list ends) and
> the `PageUp` / `PageDown` actions (`Shift+↑↓` and the portable `PgUp` / `PgDn`,
> one body capacity per press, clamped to `[0, maxOffset]`, re-anchoring the
> selection on the new first visible row). The reducer's post-mutation sequence
> now also clamps `scrollOffset`, and the renderer draws the empty-result blank
> body row plus the `Error: no matching rows` footer. This builds on TASK-003's
> Tab/ctrl+i bang autocomplete and the Phase 1 (TASK-002) `filter.raw`-as-source
> migration. accept-line/submit follow in the editing/confirmation epics.

### Spec-mandated "supported aliases" coverage (§5.1)

The spec requires tests for these 14 aliases. Current state:

| Alias | Function | Status |
|---|---|---|
| ctrl+i | complete → autocomplete `!` | ✅ |
| ctrl+? | backward-delete-char | ✅ |
| ctrl+b | backward-char | ✅ |
| ctrl+f | forward-char | ✅ |
| ctrl+j | accept-line | 🔴 |
| ctrl+m | accept-line | 🔴 |
| ctrl+p | up | ✅ |
| ctrl+n | down | ✅ |
| ctrl+a | beginning-of-line | ✅ |
| ctrl+e | end-of-line | ✅ |
| ctrl+d | delete-char | ✅ |
| ctrl+k | kill-line | ✅ |
| ctrl+u | unix-line-discard | ✅ |
| ctrl+w | backward-kill-word | ✅ |

**12 of 14** supported. The remaining two are `ctrl+j`/`ctrl+m` (accept-line →
editing epic); `ctrl+p`/`ctrl+n` (selection navigation) landed in TASK-004.
(`ctrl+h` and `DEL`, also implemented, are `backward-delete-char` aliases not on
the must-test list.)

## Closing the gaps — what needs to be built

Phase 1 (TASK-002) landed the `filter.raw`-as-source model and the browsing
line-editing aliases; TASK-003 added the Tab/ctrl+i `AutocompleteBang`; TASK-004
added browsing navigation. The reducer's actions are now `InsertCharacter`,
`MoveCursorLeft`, `MoveCursorRight`, `MoveCursorHome`, `MoveCursorEnd`,
`DeleteBackward`, `DeleteForward`, `KillToEnd`, `KillToStart`,
`DeleteWordBackward`, `DeleteWordForward`, `ClearFilter`, `AutocompleteBang`,
`MoveSelectionUp`, `MoveSelectionDown`, `PageUp`, and `PageDown`. Filter actions
run the §5.1 post-mutation sequence (clamp cursor → derive `collisionOnly`/`text`
from `filter.raw` → re-filter → clamp selection → clamp scroll).
`ToggleCollisionOnly` was removed.

Remaining work, by owning task:

1. **accept-line** — Enter / ctrl+j / ctrl+m → enter `EDITING` (editing epic).
2. **submit** — ctrl+s → accept confirmation when collisions are zero (confirmation epic).
3. **ctrl+c** — upgrade the clean-quit into the EXIT-confirmation contract
   (with second-ctrl+c SIGINT) once `CONFIRMING` exists.
4. **clear-screen** — ctrl+l → trigger a redraw without mutating state.

The active no-op families (🟡) require no new behavior — only explicit tests
asserting state and render are unchanged, per §5.1's testing mandate (Phase 1
added these for `ctrl+g`, `ctrl+q`, `ctrl+v`, `ctrl+r`, `ctrl+t`, `ctrl+y`,
`ctrl+_`, and `ctrl+l`).
