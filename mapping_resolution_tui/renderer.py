"""
Renderer module: converts AppState into a list of styled terminal lines.
"""

import re

from mapping_resolution_tui.state import AppState, FooterHint, Mode

from mapping_resolution_tui.selectors import (
    select_body_capacity,
    select_body_rows,
    select_current_target_value,
    select_default_source,
    select_filter_prompt,
    select_footer_content,
    select_match_spans,
    select_ordinal_match_spans,
    select_source_display,
    select_unresolved_collision_count,
    select_unresolved_collision_ordinals,
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


def render_lines(state: AppState) -> list[str]:
    config = state.config
    mappings = state.mappings
    height = state.terminal.height

    unresolved_count = select_unresolved_collision_count(mappings)
    collision_ordinals = select_unresolved_collision_ordinals(mappings)
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
    if state.mode == Mode.EDITING:
        mapping = next(m for m in state.mappings if m.ordinal == state.edit.mapping_ordinal)
        from mapping_resolution_tui.selectors import select_default_source_value
        default_val = select_default_source_value(mapping)
        prompt = f'  Editing mapping for "{default_val}":'
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
    shown = select_body_rows(state)

    filter_text = state.filter.text
    body_lines: list[str] = []
    for mapping in shown:
        is_selected = mapping.ordinal == state.selection.selected_ordinal
        collision = "!" if mapping.ordinal in collision_ordinals else " "
        cursor = "▸" if is_selected else " "
        
        if state.mode == Mode.EDITING and is_selected:
            edit_content = select_edit_render_row(state, mapping)
            buffer = edit_content.buffer_text
            ghost = edit_content.ghost_suffix
            cursor_idx = edit_content.cursor_offset
            
            ordinal_display = str(mapping.ordinal).rjust(ordinal_width)
            
            # Combine buffer and ghost, apply cursor reverse-video
            token_display_list = []
            full_text = buffer + ghost
            
            visual_cursor = cursor_idx
            if cursor_idx == len(full_text) and len(buffer) == max_token_length and not ghost:
                visual_cursor = max_token_length - 1

            for i, ch in enumerate(full_text):
                if i == visual_cursor:
                    token_display_list.append(f"{_REV}{ch}{_RESET}")
                elif i >= len(buffer):
                    token_display_list.append(f"{_DIM}{ch}{_RESET}")
                else:
                    token_display_list.append(ch)
            if cursor_idx >= len(full_text) and visual_cursor == cursor_idx:
                token_display_list.append(f"{_REV} {_RESET}")
            
            token_display = "".join(token_display_list)
            
            # Calculate lengths
            unformatted_len = len(full_text)
            if cursor_idx >= len(full_text) and visual_cursor == cursor_idx:
                unformatted_len += 1
                
            val_icon = edit_content.validation_icon or ""
            
            first_src = edit_content.visible_sources[0] if edit_content.visible_sources else None
            first_source_str = select_source_display(first_src.source) if first_src else ""
            ptr_0 = "▸" if (first_src and first_src.is_pointed) else " "
            gap_str_0 = f"{ptr_0} " if ptr_0 != " " else "  "
            
            # The fixed width area before ┃ is exactly max_token_length + 3
            # It consists of:
            # 1. token_display (ANSI formatted, unformatted length is `unformatted_len`)
            # 2. Spaces up to max_token_length + 1
            # 3. gap_str_0 (2 chars)
            # 4. val_icon overwrites a character at `unformatted_len + 1` (capped at max_token_length + 1)
            
            area_len = max_token_length + 3
            icon_idx = min(unformatted_len + 1, max_token_length + 1)
            
            # Build the unformatted remainder (everything after token_display)
            remainder = [" "] * (area_len - unformatted_len)
            
            # Place gap_str_0 at the end of the remainder
            remainder[-2] = gap_str_0[0]
            remainder[-1] = gap_str_0[1]
            
            # Place val_icon
            if val_icon:
                rem_idx = icon_idx - unformatted_len
                if 0 <= rem_idx < len(remainder):
                    remainder[rem_idx] = val_icon
                    
            token_cell_with_gap = token_display + "".join(remainder)
            
            row = (
                f"{cursor} {ordinal_display}{' ' * _ORDINAL_GAP}"
                f"{collision}{token_cell_with_gap}┃ {first_source_str}"
            )
            body_lines.append(row)
            
            # Subsequent lines for other sources
            # padding must equal: cursor(1) + space(1) + ordinal(4) + gap(3) + collision(1) + token(24) + space(1) = 35
            padding_len = 1 + 1 + ordinal_width + _ORDINAL_GAP + 1 + max_token_length + 1
            padding = " " * padding_len
            for src in edit_content.visible_sources[1:]:
                ptr = "▸" if src.is_pointed else " "
                gap_str = f"{ptr} " if ptr != " " else "  "
                body_lines.append(f"{padding}{gap_str}┃ {select_source_display(src.source)}")
                
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
