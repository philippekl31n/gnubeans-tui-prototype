import argparse
import importlib
import sys

from mapping_resolution_tui import loop


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Demo the mapping resolution TUI component with mock datasets."
    )
    parser.add_argument(
        "dataset",
        help="The name of the mock dataset module in tests.fixtures to load (e.g. storyboard).",
    )
    args = parser.parse_args()

    module_name = f"tests.fixtures.{args.dataset}"
    try:
        fixture_module = importlib.import_module(module_name)
        config = fixture_module.make_config()
        mappings = fixture_module.make_mappings()
    except ImportError:
        print(f"Unknown dataset: {args.dataset} (could not import {module_name})")
        sys.exit(1)
    except AttributeError as e:
        print(f"Dataset '{args.dataset}' is missing standard factory methods: {e}")
        sys.exit(1)

    result = loop.run(config, mappings)
    if result is None:
        print("\nDemo cancelled by user.")
    else:
        print(f"\nDemo completed. Resolved {len(result)} mappings.")


if __name__ == "__main__":
    main()
