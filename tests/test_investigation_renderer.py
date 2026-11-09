import json
from pathlib import Path
import shutil
import subprocess

import pytest


def test_evidence_hypothesis_matrix_renders_recorded_and_unassessed_cells():
    gjs = shutil.which("gjs")
    if gjs is None:
        pytest.skip("GJS is required to exercise the browser renderer")

    repository = Path(__file__).resolve().parents[1]
    record = {
        "record_type": "ECHO_INVESTIGATION_DRAFT",
        "hypotheses": [
            {
                "id": "H1",
                "statement": "Could <water> explain the response?",
                "state": "UNRESOLVED",
                "testability_state": "TESTABLE",
                "evidence_assessments": [
                    {
                        "evidence_id": "SAR-ONE",
                        "relationship": "CONTRADICTS",
                        "rationale": "The recorded observation is contrary to this test.",
                    }
                ],
                "required_evidence": [],
            }
        ],
        "evidence_artifacts": [
            {"evidence_id": "SAR-ONE", "role": "SAR_MEASUREMENT", "status": "DIAGNOSTIC"},
            {"evidence_id": "OPTICAL-TWO", "role": "OPTICAL_CONTEXT", "status": "UNASSESSED"},
        ],
        "follow_up_evidence": [],
    }
    script = (
        "const GLib=imports.gi.GLib;const ByteArray=imports.byteArray;"
        "globalThis.window={};const [ok,bytes]=GLib.file_get_contents(ARGV[0]);"
        "if(!ok)throw new Error('renderer source unavailable');"
        "eval(ByteArray.toString(bytes));"
        "print(window.renderInvestigationReasoning(JSON.parse(ARGV[1])));"
    )
    rendered = subprocess.run(
        [gjs, "-c", script, "echo/static/investigation.js", json.dumps(record)],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    ).stdout

    matrix = rendered.split(
        '<details class="investigation-evidence-matrix"', 1
    )[1].split("</details>", 1)[0]
    assert "2 SOURCES × 1 EXPLANATIONS" in matrix
    assert 'aria-label="contradicts"' in matrix
    assert 'aria-label="not assessed; no relationship recorded, relevance not assessed"' in matrix
    assert "CONTRADICTS" not in matrix  # The matrix uses the visible, accessible short label.
    assert ">CON</span>" in matrix
    assert "Could &lt;water&gt;" in rendered
    assert "not negative evidence" in rendered
