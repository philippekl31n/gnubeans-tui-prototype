Below are the exact visual states the TUI must accurately render across its lifecycle stitched together in a sequential narrative of a user interacting with a sample dataset in a terminal session 15 lines high and 75 columns wide.

> Mockups presented in bash code blocks include the following multimarkdown markup to indicate ANSI formatting:
- **bold**
- *"reverse-video"* used to indicate current cursor position on an input line ala ncurses or htop
- __dim__

> The component renders inline without an alternate screen buffer — it appears as an interactive pause within a larger migration script, allowing users to scroll back to preceding command output. Lines are rendered without wrapping; content extending beyond the right edge of the terminal viewport is accessible via the terminal emulator's native horizontal scrolling.

1a. Initial State (BROWSING, collisions > 0)
```bash
❯ Reviewing 11 commodity mappings. 1 unresolved collision. __ctrl+c cancel__
  Filter: *T*__ab to view collisions__

   #   Beancount Token            GnuCash Source
▸  1   APPLE                      user_symbol: "APPLE"
   2  !AT-T                       cmdty_id: "AT&T" → "AT-T"
   3  !AT-T                       cmdty_id: "AT-T"
   4   C100-F                     cmdty_id: "100-F" → "C100-F"
   5   GOOGL                      cmdty_id: "GOOGL"
   6   MSFT                       cmdty_id: "MSFT"
   7   NVDA                       cmdty_id: "NVDA"
   8   SPY                        cmdty_id: "SPY"
   9   QQQ                        cmdty_id: "QQQ"

   shift+↑↓ pageup/dn  ·  ↵ edit selected
```
- Table rows are sorted first by sanitized version of gnucash source; then by ASCII order of original version (e.g. "AT&T" before "AT-T" in the case of the collision above); This prevents having to dynamically reorder the table when Beancount Token values change
- The ordinal column is two digits wide (matching the width of the table size) and right-aligned

> TRANSITION: User types `ctrl`+`c`

1b. Exit Signal Recieved (BROWSING, collisions > 0)
```bash
❯ Reviewing 11 commodity mappings. 1 unresolved collision. __ctrl+c exit__
  Filter: *T*__ab to view collisions__

   #   Beancount Token            GnuCash Source
▸  1   APPLE                      user_symbol: "APPLE"
   2  !AT-T                       cmdty_id: "AT&T" → "AT-T"
   3  !AT-T                       cmdty_id: "AT-T"
   4   C100-F                     cmdty_id: "100-F" → "C100-F"
   5   GOOGL                      cmdty_id: "GOOGL"
   6   MSFT                       cmdty_id: "MSFT"
   7   NVDA                       cmdty_id: "NVDA"
   8   SPY                        cmdty_id: "SPY"
   9   QQQ                        cmdty_id: "QQQ"

   shift+↑↓ pageup/dn  ·  ↵ edit selected
```
- Pressing `ctrl`+`c` again sends SIGINT

> TRANSITION: User types either `↵` or `esc`, then either `tab` or `!`

2. Active Metafilter (BROWSING, collisions > 0)
```bash
❯ Reviewing 11 commodity mappings. 1 unresolved collision. __ctrl+c cancel__
  Filter: !*T*__ype to filter__

   #   Beancount Token            GnuCash Source
▸  2  !AT-T                       cmdty_id: "AT&T" → "AT-T"
   3  !AT-T                       cmdty_id: "AT-T"

  shift+↑↓ pageup/dn  ·  ↵ edit selected  ·  esc clear filter







```
- Shortcuts line moves up to remain just two lines below the table

> TRANSITION: User types `3`

3. Active Metafilter + String (BROWSING, collisions > 0)
```bash
❯ Reviewing 11 commodity mappings. 1 unresolved collision. __ctrl+c cancel__
  Filter: !3* *

   #   Beancount Token            GnuCash Source
▸  **3**  !AT-T                       cmdty_id: "AT-T"

  shift+↑↓ pageup/dn  ·  ↵ edit selected  ·  esc clear filter








```
- String matches on values in the ordinal and Beancount Token columns bolded for visual feedback

> TRANSITION: User types `backspace` or `ctrl`+`h`, then `↓`, `↵`

4. 
```bash
❯ Reviewing 11 commodity mappings. 1 unresolved collision. __ctrl+c cancel__
  Editing mapping for "AT-T":

   #   Beancount Token            GnuCash Source
   __2  !AT-T                       cmdty_id: "AT&T" → "AT-T"__
▸  3  !*A*__T-T__                       ┃ cmdty_id: "AT-T"
                                  ┃ user_symbol: (not set)

  type to edit  ·  ↑↓ select source  ·  esc cancel






```
- All characters in row 2 appear super dim while row 3 is expanded (as will be true for all rows surrounding the selected mapping while in edit mode)
- When the value of the Beancount Token field matches the sanitized value (or original value if not sanitized) of one of its source values, the input follows a model of streaming overwrite with ghost-text deviation detection: Characters that match the ghost prefix advance the cursor through it (A→A, T→T); A character that **doesn't match** discards the remaining ghost text and appends normally

> TRANSITION: User types `A` , `T` , `T`

5.
```bash
❯ Reviewing 11 commodity mappings. 1 unresolved collision. __ctrl+c cancel__
  Editing mapping for "AT-T":

   #   Beancount Token            GnuCash Source
   __2   AT-T                       cmdty_id: "AT&T" → "AT-T"__
▸  3   ATT* * ✓                     ┃ cmdty_id: "AT-T"
                                  ┃ user_symbol: (not set)

  type to edit  ·  ↑↓ select source  ·  ↵ submit  ·  esc cancel






```
- The Collision icon (`!`) disappears from rows 2 and 3 when the second `T` is typed, i.e. as soon as the value of the Beancount Token deviates from the original (or sanitized, when present) version of the default GnuCash Source value

> TRANSITION: User types `↵`

6. (CONFIRMING, collisions = 0)
```bash
❯ Reviewing 11 commodity mappings. __ctrl+c cancel__
  Accept all? [*Y*/n]

   #   Beancount Token            GnuCash Source
   1   APPLE                      user_symbol: "APPLE"
   2   AT-T                       cmdty_id: "AT&T" → "AT-T"
   3   ATT                        cmdty_id: "AT-T"
   4   C100-F                     cmdty_id: "100-F" → "C100-F"
   5   GOOGL                      cmdty_id: "GOOGL"
   6   MSFT                       cmdty_id: "MSFT"
   7   NVDA                       cmdty_id: "NVDA"
   8   SPY                        cmdty_id: "SPY"
   9   QQQ                        cmdty_id: "QQQ"

  ↑↓ pageup/dn  ·  ↵ confirm
```
- CONFIRMING mode is triggered upon submit of a Beancount Token that results in there being 0 unresolved collisions; the “Accept all” prompt is set to 'Y' 

> TRANSITION: User types `n` or `→`, then `↓` (or vice-versa)

7a. (CONFIRMING, collisions = 0)
```bash
❯ Reviewing 11 commodity mappings. __ctrl+c cancel__
  Accept all? [y/*N*]

   #   Beancount Token            GnuCash Source
  10   VTSAX                      cmdty_id: "VTSAX"
  11   VWUSX                      cmdty_id: "VWUSX"

  ↑↓ pageup/dn  ·  ↵ edit mappings







```

> TRANSITION: User types `↵`

7b. (BROWSING, collisions = 0)
```bash
❯ Reviewing 11 commodity mappings. __ctrl+s submit  · ctrl+c cancel__
  Filter: *T*__ype to filter__

   #   Beancount Token            GnuCash Source
▸ 10   VTSAX                      cmdty_id: "VTSAX"
  11   VWUSX                      cmdty_id: "VWUSX"

  shift+↑↓ pageup/dn  ·  ↵ edit selected







```

> TRANSITION: User types `1`

8.
```bash
❯ Reviewing 11 commodity mappings. __ctrl+s submit  ·  ctrl+c cancel__
  Filter: 1* *

   #   Beancount Token            GnuCash Source
▸  **1**   APPLE                      user_symbol: "APPLE"
   4   C**1**00-F                     cmdty_id: "100-F" → "C100-F"
  **1**0   VTSAX                      cmdty_id: "VTSAX"
  **1**1   VWUSX                      cmdty_id: "VWUSX"

  shift+↑↓ pageup/dn  ·  ↵ edit selected  ·  esc clear filter





```
- Row 4 is included in filter results on the basis of matching the “1” in the token string “C100-F”; values in the GnuCash Source column are not exposed to filter matching

> TRANSITION: User types `↵`:

9.
```bash
❯ Reviewing 11 commodity mappings. __ctrl+s submit  ·  ctrl+c cancel__
  Editing mapping for "APPLE":

   #   Beancount Token            GnuCash Source
▸  1   *A*__PPLE__                      ┃ cmdty_id: "AAPL"
                                  ┃ user_symbol: "APPLE"
   __4   C100-F                     cmdty_id: "100-F" → "C100-F"__
  __10   VTSAX                      cmdty_id: "VTSAX"__
  __11   VWUSX                      cmdty_id: "VWUSX"__

  type to edit  ·  ↑↓ select source  ·  ↵ submit  ·  esc cancel





```

> TRANSITION: User types `4`, `4`, `P` , `L`

10.
```bash
❯ Reviewing 11 commodity mappings. __ctrl+s submit  ·  ctrl+c cancel__
  Editing mapping for "APPLE":

   #   Beancount Token            GnuCash Source
▸  1   44PL* * ✗                    ┃ cmdty_id: "AAPL"
                                  ┃ user_symbol: "APPLE"
  __10   VTSAX                      cmdty_id: "VTSAX"__
  __11   VWUSX                      cmdty_id: "VWUSX"__

  Error: must start with A–Z  ·  ↑↓ select source ·  esc cancel




                  
```
- The Error message and Invalid-input icon (`✗`) appear immediately after the first `4` is typed
- The icon appears two spaces to the right of the reverse-video cursor (represented by `* *`)

> TRANSITION: User types 21 digits

11.
```bash
❯ Reviewing 11 commodity mappings. __ctrl+s submit  ·  ctrl+c cancel__
  Editing mapping for "APPLE":

   #   Beancount Token            GnuCash Source
▸  1   44PL56789012345678901234* *✗ ┃ cmdty_id: "AAPL"
                                  ┃ user_symbol: "APPLE"
  __10   VTSAX                      cmdty_id: "VTSAX"__
  __11   VWUSX                      cmdty_id: "VWUSX"__

  Error: 24 chars max  ·  ↑↓ select source  ·  esc cancel





```
- When the user types the 24th character in a Beancount Token input buffer, the cursor advances to column 32 of the display, but the input status icon (`✗` above) stops at column 33, breaking the ‘two spaces to the right of the cursor’ rule
- When the user types the 25th character in a Beancount Token input buffer, the character is discarded, the Invalid-input icon (`✗`) flashes in column 33, and the error message "Error: 24 chars max" appears briefly before fading out/fading to the last error message pushed to the stack

> TRANSITION to 12a: User types `↓`, moving `▸` to first source and auto-filling token-input field with that source's Beancount-safe value
> TRANSITION to 12b: User types either
  - `↓` , `↓`
  - `↑`
  - or any combination of `backspace` and/or readline keybindings to erase the current Beancount Token value (e.g. `Ctrl`+`A` then `Ctrl`+`K`), then `Tab`

12a.
```bash
❯ Reviewing 11 commodity mappings. __ctrl+s submit  ·  ctrl+c cancel__
  Editing mapping for "APPLE":

   #   Beancount Token            GnuCash Source
   1   AAPL* * ✓                  ▸ ┃ cmdty_id: "AAPL"
                                  ┃ user_symbol: "APPLE"
  __10   VTSAX                      cmdty_id: "VTSAX"__
  __11   VWUSX                      cmdty_id: "VWUSX"__

  type to edit  ·  ↑↓ select source  ·  ↵ submit  ·  esc cancel





```

> TRANSITION: User types `↓`

12b.
```bash
❯ Reviewing 11 commodity mappings. __ctrl+s submit  ·  ctrl+c cancel__
  Editing mapping for "APPLE":

   #   Beancount Token            GnuCash Source
   1   APPLE* * ✓                   ┃ cmdty_id: "AAPL"
                                ▸ ┃ user_symbol: "APPLE"
  __10   VTSAX                      cmdty_id: "VTSAX"__
  __11   VWUSX                      cmdty_id: "VWUSX"__

  type to edit  ·  ↑↓ select source  ·  ↵ submit  ·  esc cancel





```

> TRANSITION: User types either `↵` or `esc`, then `2`

13.
```bash
❯ Reviewing 11 commodity mappings. __ctrl+s submit  ·  ctrl+c cancel__
  Filter: 12* *

   #   Beancount Token            GnuCash Source


  Error: no matching rows  ·  esc back








```
- An empty row is displayed under the table headers when no results match the current filter
- The "esc back" shortcut is always visible in BROWSING mode when collisions = 0, replacing the conditional "esc clear filter" shortcut


> TRANSITION: User types `esc`:

14. Back to Accept All (CONFIRMING, collisions = 0)
```bash
❯ Reviewing 11 commodity mappings. __ctrl+c cancel__
  Accept all? [y/*N*]

   #   Beancount Token            GnuCash Source
   1   APPLE                      user_symbol: "APPLE"
   2   AT-T                       cmdty_id: "AT&T" → "AT-T"
   3   ATT                        cmdty_id: "AT-T"
   4   C100-F                     cmdty_id: "100-F" → "C100-F"
   5   GOOGL                      cmdty_id: "GOOGL"
   6   MSFT                       cmdty_id: "MSFT"
   7   NVDA                       cmdty_id: "NVDA"
   8   SPY                        cmdty_id: "SPY"
   9   QQQ                        cmdty_id: "QQQ"

  ↑↓ prev/next page  ·  ↵ edit mappings
```
- Boolean retains previous 'no' selection