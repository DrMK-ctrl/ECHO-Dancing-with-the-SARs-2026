from pathlib import Path

from echo.cli import _parser


def test_default_serve_opens_the_retained_t163_worked_case():
    args = _parser().parse_args(["serve"])

    assert args.case_file == Path(
        "data/cases/rio-grande-do-sul-t163-349925-2024/catalog.json"
    )
