#!/usr/bin/env python3
"""Historical smoke tests for the enhanced layout generator variant."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import numpy as np


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
MODULE_NAME = "layout_generator_gui_enhanced"


def load_module():
    return importlib.import_module(MODULE_NAME)


def test_fill_ratio_behavior() -> bool:
    module = load_module()
    layers = ["metal1", "metal2"]
    target_ratio = 0.3
    matrices = module.generate_random_matrices(layers, fill_ratio=target_ratio)
    for layer, matrix in matrices.items():
        actual_ratio = float(np.sum(matrix)) / float(matrix.size)
        print(f"{layer}: expected~{target_ratio:.2f}, actual={actual_ratio:.3f}")
        if abs(actual_ratio - target_ratio) > 0.2:
            print("fill ratio deviates too much from the requested target")
            return False
    return True


def test_design_metadata() -> bool:
    module = load_module()
    design = module.create_new_design_object()
    metadata = design.get("metadata", {})
    if metadata.get("fill_ratio") != 0.5:
        print(f"unexpected default fill ratio: {metadata.get('fill_ratio')}")
        return False
    return True


def test_backward_compatibility() -> bool:
    module = load_module()
    module.generate_random_matrices(["metal1"])
    module.generate_random_matrices(["metal1"], fill_ratio=0.4)
    return True


def main() -> int:
    tests = [
        test_fill_ratio_behavior,
        test_design_metadata,
        test_backward_compatibility,
    ]
    passed = 0
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                print(f"FAILED: {test.__name__}")
        except Exception as exc:  # pragma: no cover - historical helper
            print(f"ERROR in {test.__name__}: {exc}")
    print(f"passed {passed}/{len(tests)} tests")
    return 0 if passed == len(tests) else 1


if __name__ == "__main__":
    raise SystemExit(main())
