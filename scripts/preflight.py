#!/usr/bin/env python3
"""
scripts/preflight.py

Submission invariant checks -- run this before zipping/pushing a
submission to catch missing deliverables, not contract logic bugs
(see local_helper_check.py for that).

Checks:
  - Every file the README/SUBMISSION.md promise actually exists.
  - README.md contains the required architectural-pattern sections
    (Equivalence Design, Greybox Sanitization) so reviewers can find them.
  - LICENSE is present.
  - No stray debug artifacts (__pycache__, .pyc, .DS_Store) are staged.
"""

import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

REQUIRED_FILES = [
    "README.md",
    "SUBMISSION.md",
    "LICENSE",
    "gltest.config.yaml",
    "requirements-test.txt",
    "contracts/escrow.py",
    "docs/ARCHITECTURE.md",
    "docs/CONSENSUS.md",
    "tests/direct/test_escrow.py",
    "scripts/local_helper_check.py",
    "scripts/deploy_studionet.sh",
]

REQUIRED_README_SECTIONS = [
    "consensus actually does",
    "greybox-sanitized",
    "Repository layout",
]

DISALLOWED_PATTERNS = ["__pycache__", ".pyc", ".DS_Store"]


def check_required_files() -> list[str]:
    problems = []
    for rel_path in REQUIRED_FILES:
        if not (REPO_ROOT / rel_path).exists():
            problems.append(f"Missing required file: {rel_path}")
    return problems


def check_readme_sections() -> list[str]:
    problems = []
    readme = (REPO_ROOT / "README.md").read_text()
    for section in REQUIRED_README_SECTIONS:
        if section not in readme:
            problems.append(f"README.md is missing expected section/heading: {section!r}")
    return problems


def check_no_debug_artifacts() -> list[str]:
    problems = []
    for pattern in DISALLOWED_PATTERNS:
        matches = list(REPO_ROOT.rglob(f"*{pattern}*"))
        if matches:
            problems.append(
                f"Found disallowed artifact(s) matching '{pattern}': "
                + ", ".join(str(m.relative_to(REPO_ROOT)) for m in matches)
            )
    return problems


def main() -> int:
    all_problems: list[str] = []
    all_problems += check_required_files()
    all_problems += check_readme_sections()
    all_problems += check_no_debug_artifacts()

    if all_problems:
        print("Preflight FAILED:\n")
        for problem in all_problems:
            print(f"  - {problem}")
        return 1

    print("Preflight OK -- all required submission files and sections are present.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
