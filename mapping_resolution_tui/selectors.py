"""
Pure selectors for derived mapping state.
"""

from mapping_resolution_tui.state import AppConfig, Mapping, Source


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
