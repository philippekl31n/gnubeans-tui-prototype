"""
Pure selectors for derived mapping state.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from mapping_resolution_tui.state import (
    AppConfig,
    ConfirmationChoice,
    FilterPromptContent,
    FooterContent,
    FooterHint,
    Mapping,
    Mode,
    Source,
)

if TYPE_CHECKING:
    from mapping_resolution_tui.state import AppState


@dataclass(frozen=True)
class RowCollisionMetadata:
    ordinal: int
    is_unresolved: bool


def select_source_effective_value(source: Source) -> str | None:
    return source.sanitized_value if source.sanitized_value is not None else source.original_value


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
    return [
        source
        for source in mapping.sources
        if select_source_effective_value(source) is not None
    ]


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


def select_collision_groups(mappings: list[Mapping]) -> tuple[tuple[str, tuple[int, ...]], ...]:
    ordinals_by_target: dict[str, list[int]] = {}
    for mapping in mappings:
        target_value = select_current_target_value(mapping)
        ordinals_by_target.setdefault(target_value, []).append(mapping.ordinal)

    return tuple(
        (target_value, tuple(sorted(ordinals)))
        for target_value, ordinals in sorted(ordinals_by_target.items())
        if len(ordinals) > 1
    )


def select_unresolved_collision_count(mappings: list[Mapping]) -> int:
    return len(select_collision_groups(mappings))


def select_unresolved_collision_ordinals(mappings: list[Mapping]) -> frozenset[int]:
    return frozenset(
        ordinal
        for _, ordinals in select_collision_groups(mappings)
        for ordinal in ordinals
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


def select_match_spans(needle: str, haystack: str) -> tuple[tuple[int, int], ...]:
    """Non-overlapping ASCII case-insensitive match spans of ``needle`` in ``haystack``.

    Returns ``(start, end)`` half-open index pairs into ``haystack`` (left to
    right, non-overlapping). An empty ``needle`` matches nothing. The spans are
    the bold-highlight metadata the renderer applies to the ordinal display and
    target token cell (FR11).
    """
    if not needle:
        return ()
    lowered_needle = needle.lower()
    lowered_haystack = haystack.lower()
    spans: list[tuple[int, int]] = []
    start = 0
    while True:
        idx = lowered_haystack.find(lowered_needle, start)
        if idx == -1:
            break
        spans.append((idx, idx + len(lowered_needle)))
        start = idx + len(lowered_needle)
    return tuple(spans)


def select_filter_prompt(state: "AppState", unresolved_count: int) -> FilterPromptContent:
    return FilterPromptContent(
        filter_raw=state.filter.raw,
        filter_text=state.filter.text,
        filter_cursor=state.filter.cursor,
        collision_only=state.filter.collision_only,
        collision_hint_visible=unresolved_count > 0,
    )


def select_footer_content(state: "AppState") -> FooterContent:
    if state.mode == Mode.BROWSING:
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
    return FooterContent(hints=(
        FooterHint.TYPE_TO_EDIT,
        FooterHint.SELECT_SOURCE,
        FooterHint.SUBMIT,
        FooterHint.CANCEL,
    ))


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
