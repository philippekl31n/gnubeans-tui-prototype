"""
Renderer module: converts AppState into a list of styled terminal lines.
"""

import re

from mapping_resolution_tui.state import AppState, FocusRegion, FooterHint, Mapping, Mode

from mapping_resolution_tui.selectors import (
    EditRowContent,
    EditSourceRow,
    select_body_capacity,
    select_body_rows,
    select_confirmation_header,
    select_confirmation_prompt,
    select_current_target_value,
    select_default_source,
    select_default_source_value,
    select_filter_prompt,
    select_footer_content,
    select_match_spans,
    select_ordinal_match_spans,
    select_source_display,
    select_unresolved_collision_count,
    select_render_collision_ordinals,
    select_visible_rows,
    select_edit_render_row,
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


def _style_confirmation_header(plain: str) -> str:
    """Apply header styling to a plain CONFIRMING header line (spec §6.4).

    The leading ``❯`` glyph is bold and the trailing keyboard shortcut — always
    starting at the first ``ctrl+`` — is dim, matching the styling the browsing
    header builds inline.
    """
    idx = plain.index("ctrl+")
    return f"{_BOLD}❯{_RESET}{plain[1:idx]}{_DIM}{plain[idx:]}{_RESET}"


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


# ── EDITING row rendering (spec §6.3 / §7) ───────────────────────────────────


class _ColumnRow:
    """Left-to-right row builder that tracks the current 0-based display column.

    ANSI codes are zero-width, so styled spans advance the column only by their
    visible width; ``pad_to`` fills spaces up to a target column. This lets the
    edit row place the cursor, validation icon, source pointer, divider, and
    source text at their fixed §6.3 columns regardless of inline styling,
    without separately tracking an "unformatted length" alongside the string.
    """

    def __init__(self) -> None:
        self._parts: list[str] = []
        self.col = 0

    def pad_to(self, target_col: int) -> None:
        if target_col > self.col:
            self._parts.append(" " * (target_col - self.col))
            self.col = target_col

    def emit(self, text: str, width: int, pre: str = "", post: str = "") -> None:
        self._parts.append(f"{pre}{text}{post}")
        self.col += width

    def build(self) -> str:
        return "".join(self._parts)


def _render_edit_token_row(
    edit_content: EditRowContent,
    ordinal: int,
    ordinal_width: int,
    collision: str,
    max_token_length: int,
) -> str:
    """Render the token-input row of the expanded edit block (spec §6.3 / §7).

    Lays out the row cursor (shown only while focus is on the token input, not
    while navigating sources), ordinal, collision marker, the buffer with its
    reverse-video cursor, the derived ghost suffix (dim), the validation icon —
    shown once the buffer holds a concrete value, one column past the end of
    the displayed text and capped at the source-pointer column so it never
    overflows the M-wide token field — and the first source after the divider.
    When the buffer is exactly ``max_token_length`` long with no ghost, the
    cursor pins to the last character instead of appending an overflow column,
    matching the max-length flash frame (spec §7.6).
    """
    W, M = ordinal_width, max_token_length
    pointer0 = 6 + W + M    # source pointer / capped-icon column
    div0 = 8 + W + M        # source divider column
    src0 = 10 + W + M       # source text column

    buffer = edit_content.buffer_text
    ghost = edit_content.ghost_suffix
    cursor = edit_content.cursor_offset
    full_text = buffer + ghost
    visual_cursor = cursor
    if cursor == len(full_text) and len(buffer) == max_token_length and not ghost:
        visual_cursor = max_token_length - 1

    cursor_glyph = "▸" if edit_content.focus_region == FocusRegion.TOKEN_INPUT else " "

    row = _ColumnRow()
    row.emit(cursor_glyph, 1)
    row.emit(" ", 1)
    row.emit(str(ordinal).rjust(W), W)
    row.emit(" " * _ORDINAL_GAP, _ORDINAL_GAP)
    row.emit(collision, 1)
    for i, ch in enumerate(full_text):
        if i == visual_cursor:
            row.emit(ch, 1, _REV, _RESET)
        elif i >= len(buffer):
            row.emit(ch, 1, _DIM, _RESET)
        else:
            row.emit(ch, 1)
    if cursor >= len(full_text) and visual_cursor == cursor:
        row.emit(" ", 1, _REV, _RESET)

    # A ghost-only/empty buffer carries no concrete value, so no icon renders.
    icon = edit_content.validation_icon if buffer else None
    icon_col = None
    if icon:
        icon_col = min(row.col + 1, pointer0)
        row.pad_to(icon_col)
        row.emit(icon, 1)

    sources = edit_content.sources
    first = sources[0] if sources else None
    if first is not None:
        # The icon wins the pointer column when capped there (the pointer
        # arrow is suppressed); otherwise both render at their own columns.
        if first.is_pointer and icon_col != pointer0:
            row.pad_to(pointer0)
            row.emit("▸", 1)
        row.pad_to(div0)
        row.emit("┃", 1)
        row.emit(" ", 1)
        row.pad_to(src0)
        row.emit(first.display, len(first.display))
    return row.build()


def _render_edit_source_row(
    source: EditSourceRow, ordinal_width: int, max_token_length: int
) -> str:
    """Render an additional source line of the expanded edit block (spec §7.4)."""
    W, M = ordinal_width, max_token_length
    pointer0 = 6 + W + M
    div0 = 8 + W + M
    src0 = 10 + W + M
    row = _ColumnRow()
    if source.is_pointer:
        row.pad_to(pointer0)
        row.emit("▸", 1)
    row.pad_to(div0)
    row.emit("┃", 1)
    row.emit(" ", 1)
    row.pad_to(src0)
    row.emit(source.display, len(source.display))
    return row.build()


def _editing_body_rows(
    state: AppState,
) -> tuple[list[Mapping], EditRowContent | None]:
    """Allocate the EDITING table body (spec §8.2 anchored block).

    The expanded edit block for the selected mapping is always kept visible —
    unlike BROWSING, the scroll-offset window does not apply. Whatever body
    capacity is left over after the block's own rows fills with following
    context rows first, then preceding rows (closest first), all rendered
    super-dim.
    """
    visible = select_visible_rows(state)
    edited_ordinal = state.edit.mapping_ordinal
    anchor_index = next(
        (i for i, m in enumerate(visible) if m.ordinal == edited_ordinal), None
    )
    if anchor_index is None:
        return [], None

    edited = visible[anchor_index]
    edit_content = select_edit_render_row(state, edited)
    capacity = select_body_capacity(state.terminal.height)
    anchor_block_len = max(1, len(edit_content.sources))
    context_capacity = max(0, capacity - anchor_block_len)

    after = visible[anchor_index + 1 : anchor_index + 1 + context_capacity]
    remaining = context_capacity - len(after)
    before = visible[max(0, anchor_index - remaining) : anchor_index]

    return before + [edited] + after, edit_content


def render_lines(state: AppState) -> list[str]:
    config = state.config
    mappings = state.mappings
    height = state.terminal.height

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
    if state.mode == Mode.CONFIRMING:
        header = _style_confirmation_header(select_confirmation_header(state))
    elif unresolved_count > 0:
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
    if state.mode == Mode.EDITING:
        mapping = next(m for m in state.mappings if m.ordinal == state.edit.mapping_ordinal)
        default_val = select_default_source_value(mapping)
        prompt = f'  Editing mapping for "{default_val}":'
    elif state.mode == Mode.CONFIRMING:
        # Driven entirely by select_confirmation_prompt (spec §6.5): the active
        # y/n choice renders reverse-video and bold; the renderer never
        # branches on confirmation.kind or choice.
        prompt_content = select_confirmation_prompt(state)
        if prompt_content.yes_active:
            yes = f"{_REV}{_BOLD}{prompt_content.yes_indicator}{_RESET}"
            no = prompt_content.no_indicator
        else:
            yes = prompt_content.yes_indicator
            no = f"{_REV}{_BOLD}{prompt_content.no_indicator}{_RESET}"
        prompt = f"  {prompt_content.prompt} [{yes}/{no}]"
    else:
        prompt_content = select_filter_prompt(state, unresolved_count)
        if prompt_content.filter_raw == "!":
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
    editing = state.mode == Mode.EDITING and state.edit is not None
    if editing:
        shown, anchor_edit_content = _editing_body_rows(state)
    else:
        shown = select_body_rows(state)
        anchor_edit_content = None

    filter_text = state.filter.text
    body_lines: list[str] = []
    for mapping in shown:
        is_selected = mapping.ordinal == state.selection.selected_ordinal
        collision = "!" if mapping.ordinal in collision_ordinals else " "
        # The row cursor is a BROWSING affordance: CONFIRMING renders no
        # selectedOrdinal cursor (spec §8.4) even though a selection persists.
        cursor = "▸" if is_selected and state.mode != Mode.CONFIRMING else " "

        if editing and is_selected:
            body_lines.append(
                _render_edit_token_row(
                    anchor_edit_content,
                    mapping.ordinal,
                    ordinal_width,
                    collision,
                    max_token_length,
                )
            )
            for src in anchor_edit_content.sources[1:]:
                body_lines.append(
                    _render_edit_source_row(src, ordinal_width, max_token_length)
                )
        else:
            target = select_current_target_value(mapping)
            source = select_source_display(select_default_source(mapping))

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
            if state.mode == Mode.EDITING:
                row = f"{_DIM}{row}{_RESET}"
            body_lines.append(row)

    if not shown:
        body_lines.append("")



    # ── footer ────────────────────────────────────────────────────────────────
    footer_content = select_footer_content(state)
    hints_list = []
    if footer_content.error:
        hints_list.append(f"Error: {footer_content.error}")
    
    for hint in footer_content.hints:
        key, label = _FOOTER_HINT_DISPLAY[hint]
        hints_list.append(f"{key} {label}")
        
    hints = "  ·  ".join(hints_list)
    footer = f"  {hints}"

    # ── assemble ──────────────────────────────────────────────────────────────
    lines = [header, prompt, "", table_header, *body_lines, "", footer]
    return lines
