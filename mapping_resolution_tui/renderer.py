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
    if prompt_content.filter_text:
        prompt = f"  Filter: {prompt_content.filter_text}"
    else:
        prefix = "!" if prompt_content.collision_only else ""
        hint_text = "Tab to view collisions" if prompt_content.collision_hint_visible else "Type to filter"
        first, rest = hint_text[0], hint_text[1:]
        prompt = f"  Filter: {prefix}{_REV}{first}{_RESET}{_DIM}{rest}{_RESET}"

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

    body_lines: list[str] = []
    for mapping in shown:
        is_selected = mapping.ordinal == state.selection.selected_ordinal
        collision = "!" if mapping.ordinal in collision_ordinals else " "
        cursor = "▸" if is_selected else " "
        target = select_current_target_value(mapping)
        source = select_default_source(mapping).original_value or ""
        ordinal_str = f"{mapping.ordinal:>2}"
        row = f"{cursor}  {ordinal_str}  {collision}{target:<{max_token_length}}  {source}"
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
    lines = [header, prompt, "", table_header, *body_lines, "", footer]
    return lines
