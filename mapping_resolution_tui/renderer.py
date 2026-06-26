"""
Renderer module: converts AppState into a list of styled terminal lines.
"""

import re

from mapping_resolution_tui.state import AppState, FooterHint

from mapping_resolution_tui.selectors import (
    select_body_capacity,
    select_current_target_value,
    select_default_source,
    select_filter_prompt,
    select_footer_content,
    select_match_spans,
    select_ordinal_match_spans,
    select_unresolved_collision_count,
    select_unresolved_collision_ordinals,
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

_TOKEN_START_COL = 9   # cursor(1) + 2sp + ordinal:2 + 2sp + collision(1) = 8 prefix chars
_SOURCE_GAP = 2        # blank columns between the token field and the source value


def strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def _apply_bold_spans(text: str, spans: tuple[tuple[int, int], ...]) -> str:
    """Wrap each ``[start, end)`` span of ``text`` in bold ANSI styling.

    ANSI codes carry no display width, so the rendered cell geometry is
    unchanged. With no spans the text is returned verbatim.
    """
    if not spans:
        return text
    parts: list[str] = []
    cursor = 0
    for start, end in spans:
        parts.append(text[cursor:start])
        parts.append(f"{_BOLD}{text[start:end]}{_RESET}")
        cursor = end
    parts.append(text[cursor:])
    return "".join(parts)


def render_lines(state: AppState) -> list[str]:
    config = state.config
    mappings = state.mappings
    height = state.terminal.height

    unresolved_count = select_unresolved_collision_count(mappings)
    collision_ordinals = select_unresolved_collision_ordinals(mappings)
    total = len(mappings)

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
    raw = prompt_content.filter_raw
    if raw == "!":
        # Metafilter only: the literal `!` followed by the `Type to filter` ghost,
        # only its first character reverse-video and the remainder dim (§6.5).
        first, rest = "T", "ype to filter"
        prompt = f"  Filter: !{_REV}{first}{_RESET}{_DIM}{rest}{_RESET}"
    elif raw:
        # Render filter.raw literally (including any leading `!`) with the
        # reverse-video cursor block at filter.cursor within raw (§3.3 / §6.5).
        cursor = prompt_content.filter_cursor
        if cursor >= len(raw):
            query = f"{raw}{_REV} {_RESET}"
        else:
            query = f"{raw[:cursor]}{_REV}{raw[cursor]}{_RESET}{raw[cursor + 1:]}"
        prompt = f"  Filter: {query}"
    else:
        hint_text = "Tab to view collisions" if prompt_content.collision_hint_visible else "Type to filter"
        first, rest = hint_text[0], hint_text[1:]
        prompt = f"  Filter: {_REV}{first}{_RESET}{_DIM}{rest}{_RESET}"

    # ── table header ──────────────────────────────────────────────────────────
    max_token_length = config.target_policy.max_token_length
    source_col = _TOKEN_START_COL + max_token_length + _SOURCE_GAP
    target_label = config.target_column_label
    source_label = config.source_column_label
    padding = " " * max(1, source_col - 9 - len(target_label))
    table_header = f"    #   {target_label}{padding}{source_label}"

    # ── body rows ─────────────────────────────────────────────────────────────
    capacity = select_body_capacity(height)
    visible = select_visible_rows(state)
    scroll = state.selection.scroll_offset
    shown = visible[scroll : scroll + capacity]

    filter_text = state.filter.text
    body_lines: list[str] = []
    for mapping in shown:
        is_selected = mapping.ordinal == state.selection.selected_ordinal
        collision = "!" if mapping.ordinal in collision_ordinals else " "
        cursor = "▸" if is_selected else " "
        target = select_current_target_value(mapping)
        source = select_default_source(mapping).original_value or ""

        ordinal_display = f"{mapping.ordinal:>2}"
        token_field = f"{target:<{max_token_length}}"
        if filter_text:
            # Bold every non-overlapping filter match in the ordinal and target
            # token cells; source values are never matched or highlighted (§3.3).
            ordinal_cell = _apply_bold_spans(
                ordinal_display,
                select_ordinal_match_spans(mapping.ordinal, filter_text, len(ordinal_display)),
            )
            token_cell = _apply_bold_spans(
                token_field, select_match_spans(target, filter_text)
            )
        else:
            ordinal_cell = ordinal_display
            token_cell = token_field

        row = f"{cursor}  {ordinal_cell}  {collision}{token_cell}  {source}"
        body_lines.append(row)



    # ── footer ────────────────────────────────────────────────────────────────
    footer_content = select_footer_content(state)
    hints = "  ·  ".join(
        f"{key} {label}"
        for hint in footer_content.hints
        for key, label in (_FOOTER_HINT_DISPLAY[hint],)
    )
    footer = f"  {hints}"

    # ── assemble ──────────────────────────────────────────────────────────────
    # The inline frame is variable-height and ends at the footer; it MUST NOT be
    # padded with blank lines to reach the terminal height (§6.1/§6.2). Clearing
    # any stale lines a taller previous frame drew below the footer is the
    # redraw loop's job, not the renderer's.
    lines = [header, prompt, "", table_header, *body_lines, "", footer]
    return lines
