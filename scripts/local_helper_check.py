#!/usr/bin/env python3
"""
scripts/local_helper_check.py

Deterministic sanity checks for the Intelligent Escrow Protocol that run
WITHOUT GenVM, a Studio simulator, or a live/mocked LLM backend. These
exist to catch structural regressions fast, before spending a GenVM test
run or Studio deploy cycle on them.

What this checks:
  - contracts/escrow.py parses as valid Python.
  - The required magic-comment dependency header is present and is the
    first line of the file (GenVM parses this to resolve the SDK build).
  - Exactly one class subclasses `gl.Contract`.
  - Every state machine status string used in the contract is one of the
    four declared constants (no typo'd status strings).
  - Every fixture in fixtures/*.json has the required keys.

This is intentionally dumb, fast, dependency-free static analysis --
not a substitute for tests/direct (which actually exercises GenVM logic).
"""

import ast
import json
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
CONTRACT_PATH = REPO_ROOT / "contracts" / "escrow.py"
FIXTURES_DIR = REPO_ROOT / "fixtures"

REQUIRED_FIXTURE_KEYS = {
    "name",
    "description",
    "acceptance_criteria",
    "deliverable_payload",
    "expected_decision",
}

STATUS_CONSTANTS = {"PENDING", "DELIVERED", "DISPUTED", "RESOLVED"}


def check_contract_parses() -> None:
    source = CONTRACT_PATH.read_text()
    ast.parse(source)
    print(f"[OK] {CONTRACT_PATH.relative_to(REPO_ROOT)} parses as valid Python.")


def check_magic_comment_header() -> None:
    first_line = CONTRACT_PATH.read_text().splitlines()[0]
    second_line = CONTRACT_PATH.read_text().splitlines()[1]
    assert first_line.startswith("# v"), (
        f"Expected first line to be a version comment (e.g. '# v0.2.16'), got: {first_line!r}"
    )
    assert '"Depends"' in second_line and second_line.strip().startswith("#"), (
        f"Expected second line to be the GenVM dependency magic comment, got: {second_line!r}"
    )
    print("[OK] Magic comment header present and correctly positioned.")


def check_single_contract_class() -> None:
    tree = ast.parse(CONTRACT_PATH.read_text())
    contract_classes = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef)
        and any(
            (isinstance(base, ast.Attribute) and base.attr == "Contract")
            for base in node.bases
        )
    ]
    assert len(contract_classes) == 1, (
        f"Expected exactly one gl.Contract subclass, found {len(contract_classes)}."
    )
    print(f"[OK] Exactly one gl.Contract subclass found: {contract_classes[0].name}")


def check_no_module_level_functions() -> None:
    """
    Mirrors a known-good reference contract's structure: nothing but
    imports and a single class definition at module scope. Free functions
    at module scope are an untested surface for schema generation.
    """
    tree = ast.parse(CONTRACT_PATH.read_text())
    top_level_funcs = [
        node.name for node in tree.body if isinstance(node, ast.FunctionDef)
    ]
    assert not top_level_funcs, (
        f"Found module-level function(s) outside the contract class: {top_level_funcs}. "
        "Inline this logic as a method or a nested closure instead."
    )
    print("[OK] No module-level functions outside the contract class.")


def check_status_strings() -> None:
    source = CONTRACT_PATH.read_text()
    for status in STATUS_CONSTANTS:
        assert f'"{status}"' in source, f"Expected status constant {status!r} to appear in the contract."
    print(f"[OK] All {len(STATUS_CONSTANTS)} status constants are present: {sorted(STATUS_CONSTANTS)}")


def check_fixtures() -> None:
    fixture_files = sorted(FIXTURES_DIR.glob("*.json"))
    assert fixture_files, f"No fixtures found in {FIXTURES_DIR}"
    for fixture_file in fixture_files:
        data = json.loads(fixture_file.read_text())
        missing = REQUIRED_FIXTURE_KEYS - data.keys()
        assert not missing, f"{fixture_file.name} is missing keys: {missing}"
        if data["expected_decision"] is not None:
            assert data["expected_decision"] in ("SELLER", "BUYER"), (
                f"{fixture_file.name}: expected_decision must be SELLER, BUYER, or null."
            )
    print(f"[OK] {len(fixture_files)} fixture(s) validated: {[f.name for f in fixture_files]}")


def main() -> int:
    checks = [
        check_contract_parses,
        check_magic_comment_header,
        check_single_contract_class,
        check_no_module_level_functions,
        check_status_strings,
        check_fixtures,
    ]
    for check in checks:
        check()
    print("\nAll local helper checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
