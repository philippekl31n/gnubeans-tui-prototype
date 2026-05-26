"""
Pure selectors for derived mapping state.
"""

from dataclasses import dataclass

from mapping_resolution_tui.state import AppConfig, Mapping, Source


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
        f"unknown default source label for mapping {mapping.ordinal}: "
        f"{mapping.default_source_label}"
    )


def select_default_source_value(mapping: Mapping) -> str:
    default_source = select_default_source(mapping)
    effective_value = select_source_effective_value(default_source)
    if effective_value is None:
        raise ValueError(f"missing default source value for mapping {mapping.ordinal}")
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
                mapping.ordinal,
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
