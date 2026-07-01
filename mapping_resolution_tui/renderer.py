"""
Renderer module: converts AppState into a list of styled terminal lines.
"""

import re
import time
from enum import Enum

from mapping_resolution_tui.state import (
    AppConfig,
    AppState,
    EditState,
    FocusRegion,
    FooterHint,
    Mode,
)

from mapping_resolution_tui.selectors import (
    EditRenderRow,
    EditSourceRow,
    select_body_capacity,
    select_body_rows,
    select_current_target_value,
    select_default_source,
    select_default_source_value,
    select_edit_render_row,
    select_filter_prompt,
    select_footer_content,
    select_match_spans,
    select_ordinal_match_spans,
    select_render_collision_ordinals,
    select_source_display,
    select_unresolved_collision_count,
    select_visible_rows,
)

_BOLD = "\x1b[1m"
_DIM = "\x1b[2m"
_REV = "\x1b[7m"
_RESET = "\x1b[0m"

_FOOTER_HINT_DISPLAY: dict[FooterHint, tuple[str, str]] = {
    FooterHint.PAGE_SCROLL:   ("shift+↑↓", "pageup/dn"),
    FooterHint.EDIT_SELECTED: ("↵",        "edit selected"),
    FooterHint.CLEAR_FILTER:  ("esc",      "clear filter"),
    FooterHint.SCROLL:        ("↑↓",       "scroll"),
    FooterHint.CONFIRM:       ("↵",        "confirm"),
    FooterHint.EDIT_MAPPINGS: ("↵",        "edit mappings"),
    FooterHint.TYPE_TO_EDIT:  ("type",     "to edit"),
    FooterHint.SELECT_SOURCE: ("↑↓",       "select source"),
    FooterHint.SUBMIT:        ("↵",        "submit"),
    FooterHint.CANCEL:        ("esc",      "cancel"),
}

_ORDINAL_GAP = 2       # blank columns between the ordinal field and the collision marker
_SOURCE_GAP = 3        # blank columns between the token field and the source value


def strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def _apply_bold_spans(text: str, spans: tuple[tuple[int, int], ...]) -> str:
    """Wrap each ``(start, end)`` slice of ``text`` in bold SGR codes.

    ANSI codes are zero-width, so the displayed column width is unchanged — the
    highlight metadata only adds the bold attribute to the matched cells (FR11).
    """
    if not spans:
        return text
    out: list[str] = []
    prev = 0
    for start, end in spans:
        out.append(text[prev:start])
        out.append(f"{_BOLD}{text[start:end]}{_RESET}")
        prev = end
    out.append(text[prev:])
    return "".join(out)


def _render_filter_cursor(raw: str, cursor: int) -> str:
    """Render ``raw`` with a reverse-video cursor block at ``cursor``.

    The character under the cursor is shown in reverse video; when the cursor
    sits past the last character a reverse-video space is appended so the block
    is always visible at the correct offset (FR9).
    """
    out: list[str] = []
    for i, ch in enumerate(raw):
        if i == cursor:
            out.append(f"{_REV}{ch}{_RESET}")
        else:
            out.append(ch)
    if cursor >= len(raw):
        out.append(f"{_REV} {_RESET}")
    return "".join(out)


# ── max-length flash: burst / held phases (spec §7.6) ────────────────────────


class _FlashPhase(Enum):
    NONE = "NONE"
    BURST = "BURST"
    HELD = "HELD"


def _max_length_phase(
    edit: EditState | None, config: AppConfig, now: float
) -> _FlashPhase:
    """The current max-length flash phase for the edit buffer (spec §7.6).

    ``BURST`` while a fresh over-limit deadline is still in the future
    (``now < edit.max_length_flash_until``); ``HELD`` once that deadline has
    passed while the buffer remains INVALID at the max token length; ``NONE``
    otherwise. Pure in both state and the injected render-time ``now``.
    """
    if edit is None:
        return _FlashPhase.NONE
    deadline = edit.max_length_flash_until
    if deadline is not None and now < deadline:
        return _FlashPhase.BURST
    if (
        edit.validation.status == "INVALID"
        and len(edit.buffer) == config.target_policy.max_token_length
    ):
        return _FlashPhase.HELD
    return _FlashPhase.NONE


# ── EDITING row rendering (spec §6.3 / §7) ───────────────────────────────────


class _ColumnRow:
    """Left-to-right row builder that tracks the current 0-based display column.

    ANSI styling is zero-width, so styled spans advance the column only by their
    visible width; ``pad_to`` fills spaces up to a target column. This lets the
    edit row place the cursor, validation icon, source pointer, divider, and
    source text at the exact §6.3 columns regardless of inline styling.
    """

    def __init__(self) -> None:
        self._parts: list[str] = []
        self.col = 0

    def pad_to(self, target_col: int) -> None:
        if target_col > self.col:
            self._parts.append(" " * (target_col - self.col))
            self.col = target_col

    def emit(self, text: str, width: int, pre: str = "", post: str = "") -> None:
        self._parts.append(pre + text + post)
        self.col += width

    def build(self) -> str:
        return "".join(self._parts)


def _render_edit_token_row(
    render_row: EditRenderRow,
    ordinal_str: str,
    W: int,
    M: int,
    collision: str,
    burst: bool = False,
) -> str:
    """Render the token-input row of the expanded edit block (spec §6.3 / §7).

    Lays out the row cursor, ordinal, collision marker, the buffer with its
    reverse-video cursor, the derived ghost suffix (dim), the validation icon
    (two columns past the cursor, capped at the token-field end), and the first
    active source after the divider. While ``burst`` (the max-length flash's
    150ms burst phase, §7.6), the capped validation icon renders reverse-video.
    """
    token0 = 5 + W           # token field start
    pointer0 = 6 + W + M     # source pointer / capped-icon column
    div0 = 8 + W + M         # source divider column
    src0 = 10 + W + M        # source text column

    buffer = render_row.buffer
    ghost = render_row.ghost_suffix
    cursor = render_row.cursor
    # A ghost-only/empty buffer carries no concrete value, so no icon renders.
    icon = render_row.validation_icon if buffer != "" else None

    row = _ColumnRow()
    cursor_glyph = "▸" if render_row.focus_region == FocusRegion.TOKEN_INPUT else " "
    row.emit(cursor_glyph, 1)
    row.emit(" ", 1)
    row.emit(ordinal_str.rjust(W), W)
    row.emit(" " * _ORDINAL_GAP, _ORDINAL_GAP)
    row.emit(collision, 1)
    # token field: buffer (reverse-video at cursor) then ghost suffix
    for i, ch in enumerate(buffer):
        if i == cursor:
            row.emit(ch, 1, _REV, _RESET)
        else:
            row.emit(ch, 1)
    if cursor == len(buffer):
        if ghost:
            row.emit(ghost[0], 1, _REV, _RESET)
            if len(ghost) > 1:
                row.emit(ghost[1:], len(ghost) - 1, _DIM, _RESET)
        else:
            row.emit(" ", 1, _REV, _RESET)
    # validation icon: cursor + 2, capped at the token-field end (spec §6.3).
    # During the max-length burst (§7.6) the capped icon renders reverse-video.
    if icon is not None:
        icon_col = min(token0 + cursor + 2, pointer0)
        if icon_col >= row.col:
            row.pad_to(icon_col)
            if burst:
                row.emit(icon, 1, _REV, _RESET)
            else:
                row.emit(icon, 1)
    # first active source shares the token-input display row (spec §8.2)
    if render_row.sources:
        first = render_row.sources[0]
        if first.is_pointer:
            row.pad_to(pointer0)
            row.emit("▸", 1)
        row.pad_to(div0)
        row.emit("┃", 1)
        row.pad_to(src0)
        row.emit(first.display, len(first.display))
    return row.build()


def _render_edit_source_row(source: EditSourceRow, W: int, M: int) -> str:
    """Render an additional source line of the expanded edit block (spec §7.4)."""
    pointer0 = 6 + W + M
    div0 = 8 + W + M
    src0 = 10 + W + M
    row = _ColumnRow()
    if source.is_pointer:
        row.pad_to(pointer0)
        row.emit("▸", 1)
    row.pad_to(div0)
    row.emit("┃", 1)
    row.pad_to(src0)
    row.emit(source.display, len(source.display))
    return row.build()


def _render_dim_context_row(
    mapping, W: int, M: int, collision_ordinals: frozenset[int]
) -> str:
    """Render a non-edited context row, super-dimmed, with no row cursor (frame 9).

    Surrounding rows render in the browsing grid but fully dim while a row is
    expanded for editing; the collision marker uses the live edit-aware ordinals.
    """
    collision = "!" if mapping.ordinal in collision_ordinals else " "
    ordinal_display = str(mapping.ordinal).rjust(W)
    target = select_current_target_value(mapping)
    token_cell = target + " " * max(0, M - len(target))
    source = select_source_display(select_default_source(mapping))
    row = (
        f"  {ordinal_display}{' ' * _ORDINAL_GAP}"
        f"{collision}{token_cell}{' ' * _SOURCE_GAP}{source}"
    )
    return f"{_DIM}{row}{_RESET}"


def _render_editing_body(
    state: AppState,
    W: int,
    M: int,
    collision_ordinals: frozenset[int],
    burst: bool = False,
) -> list[str]:
    """Allocate and render the EDITING table body (spec §8.2 anchored block).

    The expanded edit block for the selected mapping is kept visible; following
    context rows fill the remaining capacity first, then preceding context rows
    fill what is left (closest rows first), all rendered super-dim. The storyboard
    keeps surrounding rows visible around the edit — frame 4 shows the preceding
    AT-T collision row above the expanded row. ``burst`` forwards the max-length
    flash burst phase (§7.6) to the token row's capped validation icon.
    """
    visible = select_visible_rows(state)
    edited_ordinal = state.edit.mapping_ordinal
    anchor_index = next(
        (i for i, m in enumerate(visible) if m.ordinal == edited_ordinal), None
    )
    if anchor_index is None:
        return [""]

    edited = visible[anchor_index]
    render_row = select_edit_render_row(state, edited)
    anchor_block_len = max(1, len(render_row.sources))
    capacity = select_body_capacity(state.terminal.height)
    context_capacity = max(0, capacity - anchor_block_len)

    after = visible[anchor_index + 1 : anchor_index + 1 + context_capacity]
    remaining = context_capacity - len(after)
    before = visible[max(0, anchor_index - remaining) : anchor_index]

    collision = "!" if edited_ordinal in collision_ordinals else " "
    lines = [
        _render_dim_context_row(mapping, W, M, collision_ordinals) for mapping in before
    ]
    lines.append(_render_edit_token_row(render_row, str(edited.ordinal), W, M, collision, burst))
    for source in render_row.sources[1:]:
        lines.append(_render_edit_source_row(source, W, M))
    for mapping in after:
        lines.append(_render_dim_context_row(mapping, W, M, collision_ordinals))
    return lines


def render_lines(state: AppState, *, now: float | None = None) -> list[str]:
    config = state.config
    mappings = state.mappings
    height = state.terminal.height

    # Render-time clock for the max-length flash burst phase (spec §7.6 / §12.1);
    # defaults to wall-clock so non-editing callers are unaffected.
    if now is None:
        now = time.time()
    editing = state.mode == Mode.EDITING and state.edit is not None
    burst = editing and _max_length_phase(state.edit, config, now) is _FlashPhase.BURST

    unresolved_count = select_unresolved_collision_count(mappings)
    collision_ordinals = select_render_collision_ordinals(state)
    total = len(mappings)

    # Variable-width table grid (spec §6.3), driven by two parameters: the
    # ordinal width W = digit count of the mapping count (left edge fixed at
    # column 3), and M = the token field width. Every column after the ordinal
    # follows it, and every column after the token follows it, so a wider ordinal
    # or token shifts everything to its right by the same amount.
    # W = 1 for ≤9, 2 for 10–99, 3 for 100–999.
    ordinal_width = len(str(total)) if total else 1
    max_token_length = config.target_policy.max_token_length
    hash_col = 2 + ordinal_width       # 1-based column of the `#` heading (units digit)
    token_start = 6 + ordinal_width    # 1-based column where the token field begins
    source_col = token_start + max_token_length + _SOURCE_GAP  # 1-based: 9 + W + M

    # ── header ────────────────────────────────────────────────────────────────
    noun = config.mapping_noun_plural
    entity = config.entity_name_singular
    if unresolved_count > 0:
        plural = "" if unresolved_count == 1 else "s"
        header = (
            f"{_BOLD}❯{_RESET} Reviewing {total} {entity} {noun}. "
            f"{unresolved_count} unresolved collision{plural}. "
            f"{_DIM}ctrl+c cancel{_RESET}"
        )
    else:
        header = (
            f"{_BOLD}❯{_RESET} Reviewing {total} {entity} {noun}. "
            f"{_DIM}ctrl+s submit  ·  ctrl+c cancel{_RESET}"
        )

    # ── prompt ────────────────────────────────────────────────────────────────
    prompt_content = select_filter_prompt(state, unresolved_count)
    if state.mode == Mode.EDITING and state.edit is not None:
        # Editing prompt (spec §6.5): the default source value of the edited row.
        edited = next(m for m in mappings if m.ordinal == state.edit.mapping_ordinal)
        prompt = f'  Editing mapping for "{select_default_source_value(edited)}":'
    elif prompt_content.filter_raw == "!":
        # Metafilter only (spec §6.5): the literal ! is followed by the dim
        # "Type to filter" ghost, the caret shown as its reverse-video first
        # character — never a trailing cursor block after the ! itself.
        first, rest = "T", "ype to filter"
        prompt = f"  Filter: !{_REV}{first}{_RESET}{_DIM}{rest}{_RESET}"
    elif prompt_content.filter_raw:
        body = _render_filter_cursor(prompt_content.filter_raw, prompt_content.filter_cursor)
        prompt = f"  Filter: {body}"
    else:
        hint_text = "Tab to view collisions" if prompt_content.collision_hint_visible else "Type to filter"
        first, rest = hint_text[0], hint_text[1:]
        prompt = f"  Filter: {_REV}{first}{_RESET}{_DIM}{rest}{_RESET}"

    # ── table header ──────────────────────────────────────────────────────────
    source_label = config.source_column_label
    # `#` right-aligns over the ordinal units digit; the target label begins at
    # the token column. A label longer than M is truncated with a trailing
    # ellipsis so it stays within the M-wide token field and the source column
    # remains at 9+W+M, aligned with the body source values (spec §6.3).
    target_label = config.target_column_label
    if len(target_label) > max_token_length:
        target_label = target_label[: max_token_length - 1] + "…"
    header_prefix = " " * (hash_col - 1) + "#" + " " * (token_start - hash_col - 1)
    padding = " " * max(1, source_col - token_start - len(target_label))
    table_header = f"{header_prefix}{target_label}{padding}{source_label}"

    # ── body rows ─────────────────────────────────────────────────────────────
    body_lines: list[str] = []
    if state.mode == Mode.EDITING and state.edit is not None:
        # EDITING renders an anchored expanded edit block plus dim context rows
        # (spec §8.2); the browsing scroll-offset window does not apply.
        body_lines = _render_editing_body(
            state, ordinal_width, max_token_length, collision_ordinals, burst
        )
    else:
        shown = select_body_rows(state)
        filter_text = state.filter.text
        for mapping in shown:
            is_selected = mapping.ordinal == state.selection.selected_ordinal
            collision = "!" if mapping.ordinal in collision_ordinals else " "
            cursor = "▸" if is_selected else " "
            target = select_current_target_value(mapping)
            source = select_source_display(select_default_source(mapping))

            # Bold the matched spans in the ordinal display and target token cell.
            # Both span computations live in selectors; the ordinal spans are
            # already shifted into the right-aligned field, so they apply to the
            # padded cell.
            ordinal_display = str(mapping.ordinal).rjust(ordinal_width)
            ordinal_cell = _apply_bold_spans(
                ordinal_display,
                select_ordinal_match_spans(mapping.ordinal, filter_text, ordinal_width),
            )
            token_pad = " " * max(0, max_token_length - len(target))
            token_cell = _apply_bold_spans(
                target, select_match_spans(target, filter_text)
            ) + token_pad

            row = (
                f"{cursor} {ordinal_cell}{' ' * _ORDINAL_GAP}"
                f"{collision}{token_cell}{' ' * _SOURCE_GAP}{source}"
            )
            body_lines.append(row)

        if not shown:
            body_lines.append("")



    # ── footer ────────────────────────────────────────────────────────────────
    footer_content = select_footer_content(state)
    hints_list = []
    if footer_content.error:
        error_text = f"Error: {footer_content.error}"
        # The max-length error leads the footer reverse-video during its burst
        # phase, matching the capped icon (spec §7.6).
        if burst:
            error_text = f"{_REV}{error_text}{_RESET}"
        hints_list.append(error_text)
    
    for hint in footer_content.hints:
        key, label = _FOOTER_HINT_DISPLAY[hint]
        hints_list.append(f"{key} {label}")
        
    hints = "  ·  ".join(hints_list)
    footer = f"  {hints}"

    # ── assemble ──────────────────────────────────────────────────────────────
    lines = [header, prompt, "", table_header, *body_lines, "", footer]
    return lines
