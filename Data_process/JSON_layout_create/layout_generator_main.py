#!/usr/bin/env python3
"""Launch the current primary JSON layout generator GUI."""

from pathlib import Path
import runpy


def resolve_primary_gui(base_dir: Path) -> Path:
    """Pick the current primary GUI script from the ASCII entry modules."""
    candidates = [
        base_dir / "layout_generator_gui_super_enhanced.py",
        base_dir / "layout_generator_gui_enhanced.py",
        base_dir / "layout_generator_gui.py",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError("No layout generator GUI script was found.")


def main() -> None:
    script_path = resolve_primary_gui(Path(__file__).parent)
    runpy.run_path(str(script_path), run_name="__main__")


if __name__ == "__main__":
    main()
