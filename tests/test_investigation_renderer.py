import json
from pathlib import Path
import shutil
import subprocess

import pytest

from echo.adversarial import build_adversarial_challenge


def test_opera_scoped_quality_review_renders_provider_boundary_and_per_scene_limits():
    gjs = shutil.which("gjs")
    if gjs is None:
        pytest.skip("GJS is required to exercise the browser renderer")
    repository = Path(__file__).resolve().parents[1]
    review = {
        "record_type": "ECHO_OPERA_RTC_S1_SCOPED_QUALITY_REVIEW",
        "status": "REVIEW_RECORDED_WITH_UNRESOLVED_SCENE_QUALITY_LIMITS",
        "provider_qa": {"scene_level_verdict": "NOT_PROVIDED"},
        "provider_product_validation": {"validation_scope": "Published results are not per-scene certification."},
        "echo_bounded_checks": {
            "registration_gate": "EXACT_GRID_MATCH",
            "resampling": "NONE",
            "common_clear_support_count": 1199,
            "aoi_pixel_count": 1199,
            "check_scope": "Input and mask checks only.",
        },
        "per_observation": [{
            "role": "before", "scene_id": "SCENE-<A>",
            "provider_scene_disposition": "NOT_PROVIDED_IN_RETRIEVED_SIDECAR",
            "sidecar_sha256": "abc123",
            "aoi_mask_counts": {"clear_code_0": 1199, "layover_affected": 0, "shadow_affected": 0, "invalid": 0},
            "rfi_metadata": {"in_band_out_band_power_ratio": 13.35, "mitigation_performed": "BasedOnNoiseMeas", "mitigation_domain": "TimeAndFrequency", "residual_impact_status": "UNRESOLVED"},
            "metadata_missing_fields": [],
        }],
        "assessment_boundary": {"disposition": "DESCRIPTIVE_MEASUREMENT_REMAINS_DIAGNOSTIC", "rfi_residual_effect": "UNRESOLVED", "physical_cause_supported": False, "provider_qa_overridden": False},
        "review_basis_sha256": "review-hash",
    }
    script = (
        "const GLib=imports.gi.GLib;const ByteArray=imports.byteArray;globalThis.window={};"
        "const [ok,bytes]=GLib.file_get_contents(ARGV[0]);if(!ok)throw new Error('renderer source unavailable');"
        "eval(ByteArray.toString(bytes));print(window.renderOperaScopedQualityReview(JSON.parse(ARGV[1])));"
    )
    rendered = subprocess.run(
        [gjs, "-c", script, "echo/static/investigation.js", json.dumps(review)],
        cwd=repository, check=True, capture_output=True, text=True,
    ).stdout
    assert "SCOPED PRODUCT QUALITY REVIEW" in rendered
    assert "Provider scene-level verdict" in rendered
    assert "NOT PROVIDED" in rendered
    assert "does not certify these acquisitions" in rendered
    assert "provider QA." in rendered
    assert "1199 / 1199 cells" in rendered
    assert "SCENE-&lt;A&gt;" in rendered
    assert "physical cause supported: false" in rendered
    assert "provider QA overridden: false" in rendered
    assert "<script>" not in rendered


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


def test_draft_challenge_action_is_available_only_after_assessment_and_snapshot_save():
    gjs = shutil.which("gjs")
    if gjs is None:
        pytest.skip("GJS is required to exercise the browser renderer")
    repository = Path(__file__).resolve().parents[1]
    record = {
        "record_type": "ECHO_INVESTIGATION_DRAFT",
        "status": "DRAFT_ANALYST_ASSESSED_UNVERIFIED",
        "question": "Which explanation best fits the recorded response?",
        "hypotheses": [{
            "id": "H1", "statement": "Water change contributed to the response.",
            "state": "UNRESOLVED", "testability_state": "TESTABLE",
            "evidence_assessments": [{
                "evidence_id": "SAR-ONE", "relationship": "DOES_NOT_DISTINGUISH",
                "rationale": "The held observation does not identify the physical driver.",
                "evidence_fit": "UNKNOWN", "review_basis": "Inspected the QA-held record.",
                "limitations": "Provider QA is unresolved.",
            }],
            "required_evidence": [], "scope_limit": "The selected area only.",
            "expected_observation": "An independently measured water transition.",
            "would_weaken_if": "Suitable evidence shows no transition.",
            "testability_reason": "Independent evidence is not yet linked.",
        }],
        "evidence_artifacts": [{"evidence_id": "SAR-ONE", "role": "SAR_MEASUREMENT", "status": "QA_HELD"}],
        "follow_up_evidence": [],
    }
    script = (
        "const GLib=imports.gi.GLib;const ByteArray=imports.byteArray;globalThis.window={};"
        "const [ok,bytes]=GLib.file_get_contents(ARGV[0]);if(!ok)throw new Error('renderer source unavailable');"
        "eval(ByteArray.toString(bytes));const record=JSON.parse(ARGV[1]);"
        "print(JSON.stringify([window.renderInvestigationReasoning(record),"
        "window.renderInvestigationReasoning(record,{enableDraftChallenge:true})]));"
    )
    rendered = subprocess.run(
        [gjs, "-c", script, "echo/static/investigation.js", json.dumps(record)],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    before_save, after_save = json.loads(rendered)
    assert "CHALLENGE THIS FINDING" not in before_save
    assert 'data-hypothesis-id="H1"' in after_save
    assert "CHALLENGE THIS FINDING" in after_save


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
    assert "GRID-OFFSET STRESS TEST · UNAVAILABLE" in rendered
    assert "No linked pair measurement was available for numerical reproduction" in rendered


def test_adversarial_renderer_displays_retained_t163_sensitivity_summaries(tmp_path):
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
    record_path = tmp_path / "challenge.json"
    record_path.write_text(json.dumps(record))
    script = (
        "const GLib=imports.gi.GLib;const ByteArray=imports.byteArray;globalThis.window={};"
        "const [ok,bytes]=GLib.file_get_contents(ARGV[0]);if(!ok)throw new Error('renderer source unavailable');"
        "const [recordOk,recordBytes]=GLib.file_get_contents(ARGV[1]);if(!recordOk)throw new Error('challenge record unavailable');"
        "eval(ByteArray.toString(bytes));print(window.renderAdversarialChallenge(JSON.parse(ByteArray.toString(recordBytes))));"
    )
    rendered = subprocess.run(
        [gjs, "-c", script, "echo/static/investigation.js", str(record_path)],
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
    assert "SPATIAL VIEW · SAR RESPONSE AND OPTICAL CONTEXT" in rendered
    assert 'data-spatial-threshold type="range" min="50" max="95" step="5" value="50"' in rendered
    assert rendered.count('class="challenge-spatial-cell"') == 1254
    assert "TEMPORAL BASELINE CHECK · UNAVAILABLE" in rendered
    assert "data-show-temporal-series" not in rendered
    assert "A pair alone cannot test whether its measured response changes under another temporal baseline." in rendered


def test_adversarial_renderer_exposes_reproduced_t024_temporal_baseline_sensitivity(tmp_path):
    gjs = shutil.which("gjs")
    if gjs is None:
        pytest.skip("GJS is required to exercise the browser renderer")
    repository = Path(__file__).resolve().parents[1]
    case = json.loads((repository / "data/cases/rio-grande-do-sul-t024-2024/investigation.json").read_text())
    assessment = json.loads((repository / case["evidence_records"]["cross_sensor_assessment"]).read_text())
    record = build_adversarial_challenge(
        assessment,
        hypothesis_id="H2_WATER_CHANGE_EXPLAINS_SAR_RESPONSE",
        assessment_sha256="d" * 64,
        evidence_root=repository,
    )
    record_path = tmp_path / "t024-challenge.json"
    record_path.write_text(json.dumps(record))
    script = (
        "const GLib=imports.gi.GLib;const ByteArray=imports.byteArray;globalThis.window={};"
        "const [ok,bytes]=GLib.file_get_contents(ARGV[0]);if(!ok)throw new Error('renderer source unavailable');"
        "const [recordOk,recordBytes]=GLib.file_get_contents(ARGV[1]);if(!recordOk)throw new Error('challenge record unavailable');"
        "eval(ByteArray.toString(bytes));print(window.renderAdversarialChallenge(JSON.parse(ByteArray.toString(recordBytes))));"
    )
    rendered = subprocess.run(
        [gjs, "-c", script, "echo/static/investigation.js", str(record_path)],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    ).stdout

    assert "TEMPORAL BASELINE CHECK · DIAGNOSTIC" in rendered
    assert "3 acquisitions · 1034 of 1199 AOI cells" in rendered
    assert "ADJACENT ACQUISITION STEP" in rendered
    assert "FIRST-ACQUISITION BASELINE" in rendered
    assert "-2.344 dB / -1.408 dB" in rendered
    assert "0.188 dB / 0.177 dB" in rendered
    assert "ONE-CELL GRID-OFFSET STRESS TEST · DIAGNOSTIC" in rendered
    assert "median sign 8/8 offsets" in rendered
    assert "0.046 to 0.227 dB" in rendered
    assert "Positive / negative / zero cells" in rendered
    assert "not measured registration errors" in rendered
    assert "-2.156 dB / -1.252 dB" in rendered
    assert 'data-evidence-id="NASA-OPERA-RTC-S1-TEMPORAL-SERIES"' in rendered
    assert rendered.count("data-show-temporal-series") == 3
    assert 'data-comparison-key="adjacent:0"' in rendered
    assert 'data-comparison-key="adjacent:1"' in rendered
    assert 'data-comparison-key="baseline:0"' in rendered
    assert "data-series-sha256=" in rendered
    assert "not NISAR" in rendered
    assert "not independent or event-equivalent tests" in rendered
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
