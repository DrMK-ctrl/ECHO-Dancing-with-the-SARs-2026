import json
from pathlib import Path
import shutil
import subprocess

import pytest

from echo.adversarial import build_adversarial_challenge


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


def test_t163_swot_context_renders_as_quality_limited_inspectable_evidence():
    gjs = shutil.which("gjs")
    if gjs is None:
        pytest.skip("GJS is required to exercise the browser renderer")

    repository = Path(__file__).resolve().parents[1]
    assessment = repository / (
        "data/research/opera-rtc-cross-sensor-investigation-"
        "T163-349925-2026-11-09-source-refresh.json"
    )
    script = (
        "const GLib=imports.gi.GLib;const ByteArray=imports.byteArray;"
        "globalThis.window={};const [ok,bytes]=GLib.file_get_contents(ARGV[0]);"
        "if(!ok)throw new Error('renderer source unavailable');"
        "eval(ByteArray.toString(bytes));"
        "const [rok,json]=GLib.file_get_contents(ARGV[1]);"
        "if(!rok)throw new Error('assessment unavailable');"
        "print(window.renderInvestigationReasoning(JSON.parse(ByteArray.toString(json))));"
    )
    rendered = subprocess.run(
        [gjs, "-c", script, "echo/static/investigation.js", str(assessment)],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    ).stdout

    assert 'data-evidence-id="NASA-SWOT-RIVERSP-REACH-SCREEN"' in rendered
    assert "RETRIEVED QUALITY LIMITED" in rendered
    assert "0 quality-good reaches with valid WSE" in rendered
    assert "nearest suspect reach (64110700015) is 5.0 km" in rendered
    assert "No water-level comparison was computed" in rendered
    assert "LIMITS INTERPRETATION" in rendered


def test_adversarial_challenge_renderer_reveals_evidence_progressively_and_labels_analyst_links():
    gjs = shutil.which("gjs")
    if gjs is None:
        pytest.skip("GJS is required to exercise the browser renderer")
    repository = Path(__file__).resolve().parents[1]
    record = {
        "record_type": "ECHO_ADVERSARIAL_EVIDENCE_CHALLENGE",
        "status": "REVIEWABLE_WITH_RECORDED_LIMITS",
        "assessment_sha256": "a" * 64,
        "hypothesis": {
            "hypothesis_id": "H1",
            "statement": "Water explains the radar response.",
            "recorded_state": "UNRESOLVED",
            "testability_state": "NOT_TESTABLE_WITH_RETAINED_EVIDENCE",
            "testability_reason": "Provider QA remains unresolved.",
            "would_weaken_if": "Independent water observations do not match the prediction.",
            "required_evidence": ["Independent, quality-valid water observations"],
        },
        "observation": {"provider_qa_state": "PRODUCT_QA_UNRESOLVED", "qa_gate": "PROVIDER_QA_UNRESOLVED"},
        "evidence_review": {
            "recorded_relationships": [{
                "evidence_id": "E1",
                "relationship": "DOES_NOT_DISTINGUISH",
                "rationale": "The context does not resolve cause.",
                "relationship_basis": "RECORDED_ANALYST_ASSESSMENT",
                "role": "CONTEXT",
                "source_status": "RETRIEVED",
                "record_type": "SOURCE",
                "sha256": "b" * 64,
            }],
            "unassessed_referenced_evidence_ids": [],
            "relationship_limit": "Analyst labels are not independently verified.",
        },
        "sensitivity_review": {
            "state": "NO_LINKED_SENSITIVITY_RECORD",
            "linked_sources": [],
            "interpretation_limit": "No common score is computed.",
        },
        "comparability_review": {
            "state": "DESCRIPTIVE_METADATA_REVIEW_NOT_CAUSAL_OR_QA_CLEARANCE",
            "evidence_id": "PAIR-COMPARABILITY",
            "source_status": "DIAGNOSTIC",
            "sha256": "c" * 64,
            "scope": "CASE_WIDE_NOT_LINKED_TO_SELECTED_HYPOTHESIS",
            "summary": {"causal_disposition": "UNRESOLVED"},
            "comparisons": [{"field": "rfi_burst_report", "comparison": "DIFFERS", "before": 0.1, "after": 0.2}],
            "interpretation": "The metadata do not distinguish the cause.",
            "limitations": ["No spatial association was computed."],
        },
        "alternatives": [],
        "next_observations": [],
        "interpretation_limit": "This is not a new scientific analysis.",
    }
    script = (
        "const GLib=imports.gi.GLib;const ByteArray=imports.byteArray;globalThis.window={};"
        "const [ok,bytes]=GLib.file_get_contents(ARGV[0]);if(!ok)throw new Error('renderer source unavailable');"
        "eval(ByteArray.toString(bytes));print(window.renderAdversarialChallenge(JSON.parse(ARGV[1])));"
    )
    rendered = subprocess.run(
        [gjs, "-c", script, "echo/static/investigation.js", json.dumps(record)],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert "OBSERVATION, INFERENCE, AND QUALITY GATE" in rendered
    assert "EVIDENCE RECORDED AGAINST OR LIMITING IT" in rendered
    assert "COMPARABILITY AND SENSITIVITY" in rendered
    assert "CASE WIDE NOT LINKED TO SELECTED HYPOTHESIS" in rendered
    assert 'data-evidence-id="PAIR-COMPARABILITY"' in rendered
    assert "rfi burst report · DIFFERS" in rendered
    assert "RECORDED_ANALYST_ASSESSMENT" not in rendered
    assert "Recorded analyst assessment; not independently verified here" in rendered
    assert "No sensitivity source is linked" in rendered
    assert "No linked pair measurement was available for numerical reproduction" in rendered


def test_adversarial_renderer_displays_retained_t163_sensitivity_summaries():
    gjs = shutil.which("gjs")
    if gjs is None:
        pytest.skip("GJS is required to exercise the browser renderer")
    repository = Path(__file__).resolve().parents[1]
    case = json.loads((repository / "data/cases/rio-grande-do-sul-t163-349925-2024/investigation.json").read_text())
    assessment = json.loads((repository / case["evidence_records"]["cross_sensor_assessment"]).read_text())
    record = build_adversarial_challenge(
        assessment,
        hypothesis_id="H2_WATER_CHANGE_EXPLAINS_SAR_RESPONSE",
        assessment_sha256="a" * 64,
        evidence_root=repository,
    )
    script = (
        "const GLib=imports.gi.GLib;const ByteArray=imports.byteArray;globalThis.window={};"
        "const [ok,bytes]=GLib.file_get_contents(ARGV[0]);if(!ok)throw new Error('renderer source unavailable');"
        "eval(ByteArray.toString(bytes));print(window.renderAdversarialChallenge(JSON.parse(ARGV[1])));"
    )
    rendered = subprocess.run(
        [gjs, "-c", script, "echo/static/investigation.js", json.dumps(record)],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    ).stdout

    assert "RECORDED POLARIZATION COMPARISON" in rendered
    assert "-2.047 / -1.215 dB" in rendered
    assert "-1.716 / -1.144 dB" in rendered
    assert "50%" in rendered and "95%" in rendered
    assert "826" in rendered and "738" in rendered
    assert "RECOMPUTED FROM CHECKSUM VALIDATED VV VH PER CELL RECORDS" in rendered
    assert "RECORDED VARIANTS REPRODUCED AND FIXED SWEEP COMPUTED FROM CHECKSUM VALIDATED CELLS" in rendered
    assert "Exploratory threshold sweep" in rendered
    assert "No cutoff is preferred" in rendered
    assert "stability score" in rendered


def test_iraq_qa_held_challenge_renderer_never_displays_a_change_finding():
    gjs = shutil.which("gjs")
    if gjs is None:
        pytest.skip("GJS is required to exercise the browser renderer")
    repository = Path(__file__).resolve().parents[1]
    record = {
        "record_type": "ECHO_ADVERSARIAL_EVIDENCE_CHALLENGE",
        "status": "QA_HELD_NO_CHANGE_FINDING",
        "candidate_pair": {
            "interval_days": 12,
            "status": "METADATA_MATCH_ONLY",
            "qa_status": "QA_HOLD",
            "products": [
                {"scene_id": "before", "acquisition_time_utc": "2026-10-08T16:07:23Z", "provider_qa_state": "FAIL", "qa_summary_uri": "https://nisar.asf.earthdatacloud.nasa.gov/NISAR/collection/before/before_QA_SUMMARY.csv", "qa_summary_sha256": "a" * 64, "qa_summary_size_bytes": 1441, "qa_summary_retrieved_at_utc": "2026-11-08T20:57:15Z", "qa_report_uri": "https://nisar.asf.earthdatacloud.nasa.gov/NISAR/collection/before/before_QA_REPORT.pdf", "qa_report_sha256": "c" * 64},
                {"scene_id": "after", "acquisition_time_utc": "2026-10-20T16:07:23Z", "provider_qa_state": "FAIL", "qa_summary_uri": "https://nisar.asf.earthdatacloud.nasa.gov/NISAR/collection/after/after_QA_SUMMARY.csv", "qa_summary_sha256": "a" * 64, "qa_summary_size_bytes": 1441, "qa_summary_retrieved_at_utc": "2026-11-08T20:57:40Z", "qa_report_uri": "https://nisar.asf.earthdatacloud.nasa.gov/NISAR/collection/after/after_QA_REPORT.pdf", "qa_report_sha256": "d" * 64},
            ],
        },
        "observation": {
            "measurement": "/science/LSAR/GCOV/grids/frequencyA/HHHH",
            "units": "linear gamma-zero power",
            "selected_pixel_center_count": 9918,
            "acquired_at_utc": "2026-10-20T16:07:23Z",
            "source_record_sha256": "c" * 64,
            "scientific_disposition": "QA_HELD_DIAGNOSTIC_PREVIEW",
        },
        "challenge_result": {"reason": "No change finding exists to challenge.", "next_step": "Resolve provider QA first.", "change_conclusion": None},
        "interpretation_limit": "A single scene is not a temporal measurement.",
    }
    script = (
        "const GLib=imports.gi.GLib;const ByteArray=imports.byteArray;globalThis.window={};"
        "const [ok,bytes]=GLib.file_get_contents(ARGV[0]);if(!ok)throw new Error('renderer source unavailable');"
        "eval(ByteArray.toString(bytes));print(window.renderAdversarialChallenge(JSON.parse(ARGV[1])));"
    )
    rendered = subprocess.run(
        [gjs, "-c", script, "echo/static/investigation.js", json.dumps(record)],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert "No change finding exists to challenge" in rendered
    assert "provider QA FAIL" in rendered
    assert "No temporal change was computed" in rendered
    assert "change conclusion" not in rendered.lower()
    assert "Each acquisition has its own ASF QA CSV URL" in rendered
    assert "OPEN PROVIDER QA CSV" in rendered
    assert "OPEN PRODUCT QA REPORT" in rendered
    assert "before_QA_SUMMARY.csv" in rendered
    assert "after_QA_SUMMARY.csv" in rendered
    assert 'rel="noopener noreferrer"' in rendered
