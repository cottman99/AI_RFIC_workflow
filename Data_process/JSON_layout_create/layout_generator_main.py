#!/usr/bin/env python3
"""Launch the current primary JSON layout generator GUI."""

from pathlib import Path
import runpy


def resolve_primary_gui(base_dir: Path) -> Path:
    """Pick the most feature-complete GUI script without hard-coding a localized filename."""
    candidates = [
        path
        for path in base_dir.glob("RFIC*.py")
        if path.name != Path(__file__).name and not path.name.startswith("test_")
    ]
    if not candidates:
        raise FileNotFoundError("No RFIC layout generator GUI script was found.")

    # The current primary implementation is the largest GUI script in this directory.
    return max(candidates, key=lambda path: path.stat().st_size)


def main() -> None:
    script_path = resolve_primary_gui(Path(__file__).parent)
    runpy.run_path(str(script_path), run_name="__main__")


if __name__ == "__main__":
    main()
