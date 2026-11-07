"""Shared provider-QA schema requirements for parsing and analysis gates."""

from __future__ import annotations

REQUIRED_PROVIDER_QA_CHECKS = frozenset(
    {
        "Able to open input NISAR file?",
        "Coordinate grid metadata cubes are valid?",
        "Calibration information LUTs are valid?",
        "Passes all `identification` group checks?",
        "QA completed with no exceptions?",
    }
)

PROVIDER_QA_RESULT_NORMALIZATION = {
    "PASS": "PASS",
    "FAIL": "FAIL",
    "SKIP": "SKIPPED",
    "SKIPPED": "SKIPPED",
    "WARNING": "WARNING",
    "NOT_RUN": "NOT_RUN",
}


def provider_qa_check_name(key: str) -> str:
    """Return the check label from ECHO's ordered ``index:label`` map key."""
    prefix, separator, label = key.partition(":")
    if separator and prefix.isdigit():
        return label
    return key
