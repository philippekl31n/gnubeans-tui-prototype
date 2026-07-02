"""
Pure selectors for derived mapping state.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from mapping_resolution_tui.state import (
    AppConfig,
    ConfirmationChoice,
    ConfirmationKind,
    ConfirmationPromptContent,
    FilterPromptContent,
    FooterContent,
    FooterHint,
    Mapping,
    Mode,
    Source,
    FocusRegion,
)

if TYPE_CHECKING:
    from mapping_resolution_tui.state import AppState, EditState


@dataclass(frozen=True)
class RowCollisionMetadata:
    ordinal: int
    is_unresolved: bool


@dataclass(frozen=True)
class EditSourceRow:
    display: str
    is_pointer: bool


@dataclass(frozen=True)
class EditRowContent:
    buffer_text: str
    ghost_suffix: str
    cursor_offset: int
    validation_icon: str | None
    validation_error: str | None
    focus_region: FocusRegion
    sources: tuple[EditSourceRow, ...]


def select_source_effective_value(source: Source) -> str | None:
    return source.sanitized_value if source.sanitized_value is not None else source.original_value


def select_source_display(source: Source) -> str:
    """Render a source cell per the storyboard source-column format.

    ``label: "original"`` for a plain value, ``label: "original" → "sanitized"``
    when sanitization occurred (sanitized value present and differing), and
    ``label: (not set)`` when the source has no value.
    """
    original = source.original_value
    if original is None:
        return f"{source.label}: (not set)"
    display = f'{source.label}: "{original}"'
    if source.sanitized_value is not None and source.sanitized_value != original:
        display += f' → "{source.sanitized_value}"'
    return display


def select_default_source(mapping: Mapping) -> Source:
    for source in mapping.sources:
        if source.label == mapping.default_source_label:
            return source
    raise ValueError(
        f"unknown default source label for mapping: "
        f"{mapping.default_source_label}"
    )


def select_default_source_value(mapping: Mapping) -> str:
    default_source = select_default_source(mapping)
    effective_value = select_source_effective_value(default_source)
    if effective_value is None:
        raise ValueError(f"missing default source value for mapping")
    return effective_value


def select_current_target_value(mapping: Mapping) -> str:
    if mapping.target_value is not None:
        return mapping.target_value
    return select_default_source_value(mapping)


def select_active_sources(mapping: Mapping) -> list[Source]:
    """Return all sources with non-empty effective values."""
    return [s for s in mapping.sources if select_source_effective_value(s)]


def select_ghost_suffix(state: "AppState", mapping: Mapping) -> str:
    """Return the remaining suffix of the default source value when editing.
    
    Returns the suffix when: mapping.target_value is None, 
    edit.cursor == len(edit.buffer), and edit.buffer is a case-sensitive 
    prefix of the default source effective value; returns '' otherwise.
    """
    if mapping.target_value is not None:
        return ""
    if state.edit is None:
        return ""
    if state.edit.cursor != len(state.edit.buffer):
        return ""
    
    default_value = select_default_source_value(mapping)
    if default_value.startswith(state.edit.buffer):
        return default_value[len(state.edit.buffer):]
    return ""


def select_concrete_value(state: "AppState", mapping: Mapping) -> str:
    """Return edit.buffer if non-empty, else the default source effective value."""
    if state.edit is not None and state.edit.buffer:
        return state.edit.buffer
    return select_default_source_value(mapping)


def select_source_pointer_value(state: "AppState", mapping: Mapping) -> str | None:
    """Return the effective value of the source at edit.source_pointer_index."""
    if (edit := state.edit) is None or edit.source_pointer_index is None:
        return None
    active_sources = select_active_sources(mapping)
    index = edit.source_pointer_index
    return select_source_effective_value(active_sources[index]) if 0 <= index < len(active_sources) else None


def select_edit_render_row(state: "AppState", mapping: Mapping) -> EditRowContent:
    """Return everything the renderer needs for the expanded edit row."""
    if state.edit is None:
        raise ValueError("Cannot select edit render row when not editing")

    active_sources = select_active_sources(mapping)
    pointer_index = state.edit.source_pointer_index
    pointer_source = (
        active_sources[pointer_index]
        if pointer_index is not None and 0 <= pointer_index < len(active_sources)
        else None
    )
    sources = tuple(
        EditSourceRow(
            display=select_source_display(src),
            is_pointer=src is pointer_source,
        )
        for src in mapping.sources
    )

    return EditRowContent(
        buffer_text=state.edit.buffer,
        ghost_suffix=select_ghost_suffix(state, mapping),
        cursor_offset=state.edit.cursor,
        validation_icon=state.edit.validation.icon,
        validation_error=state.edit.validation.error_message,
        focus_region=state.edit.focus_region,
        sources=sources,
    )


def sort_mappings_for_initial_display(mappings: list[Mapping]) -> tuple[Mapping, ...]:
    return tuple(
        sorted(
            mappings,
            key=lambda mapping: (
                select_default_source_value(mapping),
                select_default_source(mapping).original_value or "",
            ),
        )
    )


def select_collision_groups(
    mappings: list[Mapping],
    *,
    override_ordinal: int | None = None,
    override_value: str | None = None,
) -> tuple[tuple[str, tuple[int, ...]], ...]:
    """Group mapping ordinals by their current target value.

    ``override_ordinal``/``override_value`` substitute a single mapping's value
    in the grouping pass without copying the mapping list — used by
    :func:`select_render_collision_ordinals` to preview a live edit buffer's
    collisions before it's committed.
    """
    ordinals_by_target: dict[str, list[int]] = {}
    for mapping in mappings:
        target_value = (
            override_value if mapping.ordinal == override_ordinal
            else select_current_target_value(mapping)
        )
        ordinals_by_target.setdefault(target_value, []).append(mapping.ordinal)

    return tuple(
        (target_value, tuple(sorted(ordinals)))
        for target_value, ordinals in sorted(ordinals_by_target.items())
        if len(ordinals) > 1
    )


def select_unresolved_collision_count(
    mappings: list[Mapping],
    *,
    override_ordinal: int | None = None,
    override_value: str | None = None,
) -> int:
    return len(select_collision_groups(mappings, override_ordinal=override_ordinal, override_value=override_value))


def select_unresolved_collision_ordinals(
    mappings: list[Mapping],
    *,
    override_ordinal: int | None = None,
    override_value: str | None = None,
) -> frozenset[int]:
    return frozenset(
        ordinal
        for _, ordinals in select_collision_groups(
            mappings, override_ordinal=override_ordinal, override_value=override_value
        )
        for ordinal in ordinals
    )


def select_render_collision_ordinals(state: "AppState") -> frozenset[int]:
    """Unresolved-collision ordinals for the rendered row markers.

    Identical to :func:`select_unresolved_collision_ordinals` outside of
    EDITING. While EDITING with a non-empty buffer, substitutes the edited
    mapping's live buffer for its committed target so the ``!`` markers react
    on every keystroke instead of only after submit.

    An empty buffer substitutes nothing: the edited mapping keeps its committed
    :func:`select_current_target_value`, so clearing the buffer never resolves
    a conflict (FR8). Falling back to the default source value here would
    falsely drop the markers of a committed literal-target collision.
    """
    if state.mode is not Mode.EDITING or state.edit is None or not state.edit.buffer:
        return select_unresolved_collision_ordinals(state.mappings)

    return select_unresolved_collision_ordinals(
        state.mappings,
        override_ordinal=state.edit.mapping_ordinal,
        override_value=state.edit.buffer,
    )


def select_row_collision_metadata(
    mappings: list[Mapping],
    ordinal: int,
) -> RowCollisionMetadata:
    return RowCollisionMetadata(
        ordinal=ordinal,
        is_unresolved=ordinal in select_unresolved_collision_ordinals(mappings),
    )


def select_body_capacity(height: int) -> int:
    """body_capacity = height - 4 fixed rows - 1 separator - 1 footer"""
    return max(0, height - 6)


def select_collision_ghost_visible(state: "AppState") -> bool:
    """Return True when the ``Tab to view collisions`` ghost is visible.

    The ghost — and therefore the ``Tab`` / ``ctrl+i`` bang autocomplete it gates
    (spec §3.3 / §6.6) — renders only when ``filter.raw`` is empty and at least
    one unresolved collision exists.
    """
    return (
        state.filter.raw == ""
        and select_unresolved_collision_count(state.mappings) > 0
    )


def select_visible_rows(state: "AppState") -> list[Mapping]:
    rows: list[Mapping] = list(state.mappings)

    if state.filter.collision_only:
        collision_ordinals = select_unresolved_collision_ordinals(state.mappings)
        rows = [m for m in rows if m.ordinal in collision_ordinals]

    if state.filter.text:
        text_lower = state.filter.text.lower()

        def _matches(m: Mapping) -> bool:
            if text_lower in str(m.ordinal):
                return True
            return text_lower in select_current_target_value(m).lower()

        rows = [m for m in rows if _matches(m)]

    return rows


def parse_filter(raw: str) -> tuple[bool, str]:
    """Derive ``(collision_only, text)`` from the editable ``filter.raw`` buffer.

    ``collision_only`` is True when ``raw`` begins with ``!``; ``text`` is ``raw``
    with a single leading ``!`` removed — the search portion used by matching
    (spec §3.3). A non-leading ``!`` is ordinary search text. This is the single
    source of truth for the derivation; the reducer and renderer both use it.
    """
    collision_only = raw.startswith("!")
    text = raw[1:] if collision_only else raw
    return collision_only, text


def select_match_spans(text: str, query: str) -> tuple[tuple[int, int], ...]:
    """Non-overlapping ASCII case-insensitive spans of ``query`` within ``text``.

    Returns ``(start, end)`` half-open index pairs into ``text`` (left to right,
    non-overlapping). An empty ``query`` matches nothing. The spans are the
    bold-highlight metadata the renderer applies to the ordinal display and
    target token cell (FR11).
    """
    if not query:
        return ()
    haystack = text.lower()
    needle = query.lower()
    spans: list[tuple[int, int]] = []
    start = 0
    while True:
        idx = haystack.find(needle, start)
        if idx == -1:
            break
        spans.append((idx, idx + len(needle)))
        start = idx + len(needle)
    return tuple(spans)


def select_ordinal_match_spans(
    ordinal: int, query: str, display_width: int
) -> tuple[tuple[int, int], ...]:
    """Bold spans for an ordinal rendered right-aligned to ``display_width``.

    Matching is on the bare decimal ordinal string (no left padding), so the
    alignment spaces never match; each span is then shifted by the pad width to
    address the right-aligned display cell (spec §3.3).
    """
    ordinal_str = str(ordinal)
    pad = display_width - len(ordinal_str)
    return tuple(
        (start + pad, end + pad)
        for start, end in select_match_spans(ordinal_str, query)
    )


def select_body_rows(state: "AppState") -> list[Mapping]:
    """Return the mappings to render in the table body (spec §8.2)."""
    visible = select_visible_rows(state)
    capacity = select_body_capacity(state.terminal.height)
    if capacity <= 0 or not visible:
        return []
    scroll = state.selection.scroll_offset
    return visible[scroll : scroll + capacity]


def select_filter_prompt(state: "AppState", unresolved_count: int) -> FilterPromptContent:
    return FilterPromptContent(
        filter_raw=state.filter.raw,
        filter_text=state.filter.text,
        filter_cursor=state.filter.cursor,
        collision_only=state.filter.collision_only,
        collision_hint_visible=unresolved_count > 0,
    )


def select_confirmation_prompt(state: "AppState") -> ConfirmationPromptContent:
    """Derive the confirmation prompt content for CONFIRMING mode (spec §6.5).

    The prompt text comes from ``config.acceptPrompt``/``config.exitPrompt`` per
    ``confirmation.kind``; the ``[y/N]``/``[Y/n]`` indicators are cased so the
    active choice is upper-case, and ``yes_active`` tells the renderer which
    indicator to render reverse-video. Rendering is driven entirely from this
    output so the renderer never branches on ``ConfirmationKind``/``choice``.
    """
    config = state.config
    prompt = (
        config.exit_prompt
        if state.confirmation.kind is ConfirmationKind.EXIT
        else config.accept_prompt
    )
    yes_active = state.confirmation.choice is ConfirmationChoice.YES
    return ConfirmationPromptContent(
        prompt=prompt,
        yes_indicator="Y" if yes_active else "y",
        no_indicator="n" if yes_active else "N",
        yes_active=yes_active,
    )


def select_confirmation_header(state: "AppState") -> str:
    """Header line text for CONFIRMING mode (spec §6.4).

    Always opens with the ``❯ Reviewing …`` review clause and appends the
    unresolved-collision clause only when collisions remain (frame 1b keeps its
    count, while an accept confirmation — entered only at zero collisions —
    omits it). The trailing shortcut is ``ctrl+c exit`` for an exit confirmation
    and ``ctrl+c cancel`` otherwise. Returned as plain text; the renderer
    applies the bold glyph and dim shortcut styling.
    """
    config = state.config
    header = (
        f"❯ Reviewing {len(state.mappings)} {config.entity_name_singular} "
        f"{config.mapping_noun_plural}."
    )
    count = select_unresolved_collision_count(state.mappings)
    if count > 0:
        plural = "" if count == 1 else "s"
        header += f" {count} unresolved collision{plural}."
    shortcut = (
        "ctrl+c exit"
        if state.confirmation.kind is ConfirmationKind.EXIT
        else "ctrl+c cancel"
    )
    return f"{header} {shortcut}"


def select_edit_is_submittable(state: "AppState", edit: "EditState") -> bool:
    """SUBMIT is offered only for a valid, non-colliding, actually-changed edit.

    ``target_policy.validate`` only checks token format, so the collision and
    no-op-edit checks below are the only enforcement of those two rules.
    """
    if edit.validation.status != "VALID":
        return False
    mapping = next(m for m in state.mappings if m.ordinal == edit.mapping_ordinal)
    if mapping.ordinal in select_render_collision_ordinals(state):
        return False
    return select_concrete_value(state, mapping) != mapping.target_value


def select_footer_content(state: "AppState") -> FooterContent:
    if state.mode == Mode.BROWSING:
        if not select_visible_rows(state):
            return FooterContent(
                hints=(FooterHint.CLEAR_FILTER,),
                error="no matching rows",
            )

        hints: list[FooterHint] = [FooterHint.PAGE_SCROLL, FooterHint.EDIT_SELECTED]
        if state.filter.text or state.filter.collision_only:
            hints.append(FooterHint.CLEAR_FILTER)
        return FooterContent(hints=tuple(hints))
    if state.mode == Mode.CONFIRMING:
        action = (
            FooterHint.CONFIRM
            if state.confirmation.choice == ConfirmationChoice.YES
            else FooterHint.EDIT_MAPPINGS
        )
        return FooterContent(hints=(FooterHint.SCROLL, FooterHint.PAGE_SCROLL, action))

    if state.edit is None:
        raise ValueError("Cannot select footer content when not editing")
    edit = state.edit

    if edit.validation.status == "INVALID":
        return FooterContent(
            hints=(FooterHint.SELECT_SOURCE, FooterHint.CANCEL),
            error=edit.validation.error_message,
        )

    hints = [FooterHint.TYPE_TO_EDIT, FooterHint.SELECT_SOURCE]
    if select_edit_is_submittable(state, edit):
        hints.append(FooterHint.SUBMIT)
    hints.append(FooterHint.CANCEL)
    return FooterContent(hints=tuple(hints))


def validate_mapping_invariants(config: AppConfig, mapping: Mapping) -> None:
    labels_seen: set[str] = set()
    configured_labels = set(config.source_labels)

    for source in mapping.sources:
        if source.label in labels_seen:
            raise ValueError(
                f"duplicate source label for mapping {mapping.ordinal}: {source.label}"
            )
        labels_seen.add(source.label)

        if source.label not in configured_labels:
            raise ValueError(
                f"unknown source label for mapping {mapping.ordinal}: {source.label}"
            )

        if source.original_value is None and source.sanitized_value is not None:
            raise ValueError(
                f"sanitized value without original value for mapping {mapping.ordinal}: "
                f"{source.label}"
            )

    if mapping.default_source_label not in configured_labels:
        raise ValueError(
            f"unknown default source label for mapping {mapping.ordinal}: "
            f"{mapping.default_source_label}"
        )

    default_source = select_default_source(mapping)
    if select_source_effective_value(default_source) is None:
        raise ValueError(f"missing default source value for mapping {mapping.ordinal}")
