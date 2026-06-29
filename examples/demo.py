import argparse
import importlib
import sys
from dataclasses import replace

from mapping_resolution_tui import loop
from mapping_resolution_tui.state import AppConfig, Mapping, Source

# Defaults match the storyboard fixture's token field width (M=24) and a modest
# row count, so `--items` / `--token-length` can each be supplied on their own.
_DEFAULT_ITEMS = 24
_DEFAULT_TOKEN_LENGTH = 24


def _make_synthetic_config(token_length: int) -> AppConfig:
    """Reuse the storyboard config (labels + validator) at an arbitrary M.

    Only the token field width changes: ``max_token_length`` drives M in the
    §6.3 grid, so overriding it is enough to demo any column geometry.
    """
    from tests.fixtures.storyboard import make_config

    base = make_config()
    return replace(
        base,
        target_policy=replace(base.target_policy, max_token_length=token_length),
    )


_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _synthetic_token(index: int, token_length: int) -> str:
    """A unique token whose length cycles from ``len("SYM<index>")`` up to M.

    The ``SYM<index>`` prefix keeps every token distinct (so the demo shows no
    spurious collisions); a cycling letter suffix fills toward the M-wide field
    so the token-field padding and the source column at col 9+W+M stay visible.
    Tokens are clamped to M; if the index alone overflows M (tiny M) it is
    truncated.
    """
    body = f"SYM{index}"
    if len(body) >= token_length:
        return body[:token_length]
    fill = index % (token_length - len(body) + 1)  # 0..(M - len(body))
    return body + _ALPHABET[:fill]


def _make_synthetic_mappings(items: int, token_length: int) -> list[Mapping]:
    """Generate ``items`` mappings with cycling token lengths.

    Every 4th row carries a differing ``sanitized_value`` so the
    ``select_source_display`` arrow form ("orig" → "sanitized") is exercised
    alongside the plain form. Ordinals are left unset; ``make_initial_state``
    assigns 1..N after its bootstrap sort.
    """
    mappings: list[Mapping] = []
    for i in range(1, items + 1):
        original = f"SYM{i}"
        sanitized = f"SYM-{i}" if i % 4 == 0 else None
        mappings.append(
            Mapping(
                sources=[
                    Source(
                        label="cmdty_id",
                        original_value=original,
                        sanitized_value=sanitized,
                    )
                ],
                default_source_label="cmdty_id",
                target_value=_synthetic_token(i, token_length),
            )
        )
    return mappings


def _run_fixture(dataset: str) -> list[Mapping] | None:
    module_name = f"tests.fixtures.{dataset}"
    try:
        fixture_module = importlib.import_module(module_name)
        config = fixture_module.make_config()
        mappings = fixture_module.make_mappings()
    except ImportError:
        print(f"Unknown dataset: {dataset} (could not import {module_name})")
        sys.exit(1)
    except AttributeError as e:
        print(f"Dataset '{dataset}' is missing standard factory methods: {e}")
        sys.exit(1)
    return loop.run(config, mappings)


def _run_synthetic(items: int, token_length: int) -> list[Mapping] | None:
    if items < 1:
        print(f"--items must be >= 1 (got {items})")
        sys.exit(1)
    if token_length < 1:
        print(f"--token-length must be >= 1 (got {token_length})")
        sys.exit(1)
    config = _make_synthetic_config(token_length)
    mappings = _make_synthetic_mappings(items, token_length)
    return loop.run(config, mappings)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Demo the mapping resolution TUI component with mock datasets."
    )
    parser.add_argument(
        "dataset",
        nargs="?",
        default=None,
        help="Name of a mock dataset module in tests.fixtures (e.g. storyboard). "
        "Omit to generate a synthetic dataset from --items / --token-length.",
    )
    parser.add_argument(
        "--items",
        type=int,
        default=_DEFAULT_ITEMS,
        help=f"Number of mappings to generate (drives W = ordinal width). "
        f"Default {_DEFAULT_ITEMS}.",
    )
    parser.add_argument(
        "--token-length",
        type=int,
        default=_DEFAULT_TOKEN_LENGTH,
        help=f"Token field width M = max_token_length. Default {_DEFAULT_TOKEN_LENGTH}.",
    )
    args = parser.parse_args()

    if args.dataset is not None:
        result = _run_fixture(args.dataset)
    else:
        result = _run_synthetic(args.items, args.token_length)

    if result is None:
        print("\nDemo cancelled by user.")
    else:
        print(f"\nDemo completed. Resolved {len(result)} mappings.")


if __name__ == "__main__":
    main()
