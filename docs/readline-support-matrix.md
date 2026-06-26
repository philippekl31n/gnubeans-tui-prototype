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
| `\x01` | ctrl+a | `beginning-of-line` | Set `filter.cursor = 0` | `None` | 🔴 |
| `\x02` | ctrl+b | `backward-char` | Cursor left, clamp at 0 | `MoveCursorLeft` | ✅ |
| `\x03` | ctrl+c | *(app)* interrupt | Enter EXIT confirmation; arm 2nd-ctrl+c SIGINT | Quits loop cleanly via `is_quit_key` | 🟠 |
| `\x04` | ctrl+d | `delete-char` | Delete char **at** cursor; no-op at end | `None` | 🔴 |
| `\x05` | ctrl+e | `end-of-line` | Set `filter.cursor = len(text)` | `None` | 🔴 |
| `\x06` | ctrl+f | `forward-char` | Cursor right, clamp at `len(text)` | `MoveCursorRight` | ✅ |
| `\x07` | ctrl+g | `abort` | No-op (must NOT act like Esc/ctrl+c) | `None` | 🟡 |
| `\x08` | ctrl+h | `backward-delete-char` | Delete before cursor / clear metafilter | `DeleteBackward` | ✅ |
| `\x09` | ctrl+i / Tab | `complete` → *(app)* | Toggle `filter.collision_only` | `ToggleCollisionOnly` | ✅ |
| `\x0a` | ctrl+j | `accept-line` (Enter) | Dispatch as Enter (edit selected row) | `None` | 🔴 |
| `\x0b` | ctrl+k | `kill-line` | Delete from cursor through end of text | `None` | 🔴 |
| `\x0c` | ctrl+l | `clear-screen` / `redraw-current-line` | Re-render only; MUST NOT mutate state | `None` (no forced redraw) | 🟠 |
| `\x0d` | ctrl+m | `accept-line` (Enter) | Dispatch as Enter (edit selected row) | `None` | 🔴 |
| `\x0e` | ctrl+n | `next-history` → *(app)* | Move selection down | `None` | 🔴 |
| `\x0f` | ctrl+o | `operate-and-get-next` | — (not named) | `None` | ⚪ |
| `\x10` | ctrl+p | `previous-history` → *(app)* | Move selection up | `None` | 🔴 |
| `\x11` | ctrl+q | `quoted-insert` | No-op (quoted insertion unsupported) | `None` | 🟡 |
| `\x12` | ctrl+r | `reverse-search-history` | No-op | `None` | 🟡 |
| `\x13` | ctrl+s | *(app)* submit / `forward-search-history` | Open accept confirmation if 0 collisions | `None` | 🔴 |
| `\x14` | ctrl+t | `transpose-chars` | No-op (text transform unsupported) | `None` | 🟡 |
| `\x15` | ctrl+u | `unix-line-discard` | Delete start…cursor; set cursor 0 | `None` | 🔴 |
| `\x16` | ctrl+v | `quoted-insert` | No-op | `None` | 🟡 |
| `\x17` | ctrl+w | `unix-word-rubout` / `backward-kill-word` | Delete previous word run before cursor | `None` | 🔴 |
| `\x18` | ctrl+x | command prefix (`ctrl+x ctrl+?` = `backward-kill-line`, `ctrl+x ctrl+u` = `undo`) | `backward-kill-line` = `unix-line-discard`; `undo` = no-op | `None` | 🔴 / 🟡 |
| `\x19` | ctrl+y | `yank` | No-op (paste arrives as printable text) | `None` | 🟡 |
| `\x1a` | ctrl+z | *(terminal suspend)* | — (not named) | `None` | ⚪ |
| `\x1b` | ctrl+[ / Esc | *(app)* + meta prefix | Clear active filter + metafilter; cursor 0 | `ClearFilter` | ✅ |
| `\x1c` | ctrl+\ | *(terminal SIGQUIT)* | — (not named) | `None` | ⚪ |
| `\x1d` | ctrl+] | — | — (not named) | `None` | ⚪ |
| `\x1e` | ctrl+^ | — | — (not named) | `None` | ⚪ |
| `\x1f` | ctrl+_ | `undo` / `revert-line` | No-op (undo out of scope) | `None` | 🟡 |
| `\x7f` | ctrl+? / DEL | `backward-delete-char` | Delete before cursor / clear metafilter | `DeleteBackward` | ✅ |

## B. Meta / Alt functions named by the spec

Meta combos arrive as an ESC prefix (`\x1b` + key) or a distinct sequence. None
are recognised by `key_to_action` today, so all return `None`.

| Keys | Readline function | Spec filter-input behavior | Current | Status |
|---|---|---|---|---|
| `meta+d` | `kill-word` | Delete cursor → end of next word | `None` | 🔴 |
| `meta+backspace` | `backward-kill-word` | Delete previous word run | `None` | 🔴 |
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
| `KEY_BACKSPACE` | Backspace | `backward-delete-char` | Delete before cursor / clear metafilter | `DeleteBackward` | ✅ |
| `KEY_ESCAPE` | Esc | *(app)* | Clear active filter | `ClearFilter` | ✅ |
| `KEY_TAB` | Tab | `complete` → *(app)* | Toggle metafilter | `ToggleCollisionOnly` | ✅ |
| `KEY_ENTER` | Enter | `accept-line` | Edit selected row | `None` | 🔴 |
| `KEY_UP` | ↑ | *(app)* | Move selection up | `None` | 🔴 |
| `KEY_DOWN` | ↓ | *(app)* | Move selection down | `None` | 🔴 |
| `KEY_HOME` | Home | `beginning-of-line` | Set cursor 0 | `None` | 🔴 |
| `KEY_END` | End | `end-of-line` | Set cursor `len(text)` | `None` | 🔴 |
| `KEY_DELETE` | Delete | `delete-char` | Delete at cursor | `None` | 🔴 |
| `KEY_SUP` / `KEY_PGUP` | Shift+↑ / PgUp | *(app)* | Page up; select first visible | `None` | 🔴 |
| `KEY_SDOWN` / `KEY_PGDOWN` | Shift+↓ / PgDn | *(app)* | Page down; select first visible | `None` | 🔴 |
| `KEY_INSERT` | Insert | — | — (not named) | `None` | ⚪ |

## Summary

| Status | Count (approx.) | Meaning |
|---|---|---|
| ✅ Implemented | 7 control + 5 named = **12 bindings** | Filter cursor move, delete, metafilter toggle, clear, insert. |
| 🟡 No-op (compliant) | **~14 families** | abort, quoted-insert, undo, transpose, yank, search/history, completion variants, case transforms, macro/shell/vi. |
| 🔴 Gap (planned) | **~16 bindings** | Line-edit aliases, accept-line, navigation, page, submit. |
| 🟠 Partial | **2** | `ctrl+c` (simple quit vs EXIT confirmation), `ctrl+l` (no forced redraw). |
| ⚪ Out of scope | **~7** | Control bytes the spec never names. |

### Spec-mandated "supported aliases" coverage (§5.1)

The spec requires tests for these 14 aliases. Current state:

| Alias | Function | Status |
|---|---|---|
| ctrl+i | complete → toggle | ✅ |
| ctrl+? | backward-delete-char | ✅ |
| ctrl+b | backward-char | ✅ |
| ctrl+f | forward-char | ✅ |
| ctrl+j | accept-line | 🔴 |
| ctrl+m | accept-line | 🔴 |
| ctrl+p | up | 🔴 |
| ctrl+n | down | 🔴 |
| ctrl+a | beginning-of-line | 🔴 |
| ctrl+e | end-of-line | 🔴 |
| ctrl+d | delete-char | 🔴 |
| ctrl+k | kill-line | 🔴 |
| ctrl+u | unix-line-discard | 🔴 |
| ctrl+w | backward-kill-word | 🔴 |

**4 of 14** supported today. (`ctrl+h` and `DEL`, also supported, are
`backward-delete-char` aliases not on the spec's must-test list.)

## Closing the gaps — what needs to be built

The existing reducer has six actions: `InsertCharacter`, `MoveCursorLeft`,
`MoveCursorRight`, `ToggleCollisionOnly`, `DeleteBackward`, `ClearFilter`. Full
readline coverage for the **filter input** needs new actions + reducer handlers
plus `key_to_action` normalisation (each followed by the §5.1 post-mutation
sequence: clamp cursor → sync `filter.raw` → re-filter → clamp selection):

1. **Cursor jumps** — `MoveCursorHome` (ctrl+a, Home), `MoveCursorEnd` (ctrl+e, End).
2. **Forward delete** — `DeleteForward` (ctrl+d, Delete); no-op at end.
3. **Line kills** — `KillLine` (ctrl+k), `KillToLineStart` (ctrl+u, plus `ctrl+x ctrl+?`).
4. **Word kills** — `KillWordForward` (meta+d), `KillWordBackward` (ctrl+w, meta+backspace),
   using `wordChar = [A-Za-z0-9_-]` boundaries (§5.1).
5. **Navigation** — up/down (↑/↓, ctrl+p/ctrl+n) and page (Shift+↑↓, PgUp/PgDn)
   for selection movement.
6. **accept-line** — Enter / ctrl+j / ctrl+m → enter `EDITING` (depends on the editing epic).
7. **submit** — ctrl+s → accept confirmation when collisions are zero (depends on the confirmation epic).
8. **ctrl+c** — upgrade the current clean-quit into the EXIT-confirmation contract
   (with second-ctrl+c SIGINT) once `CONFIRMING` exists.
9. **clear-screen** — ctrl+l → trigger a redraw without mutating state.

The active no-op families (🟡) require no new behavior — only explicit tests
asserting state and render are unchanged, per §5.1's testing mandate.
