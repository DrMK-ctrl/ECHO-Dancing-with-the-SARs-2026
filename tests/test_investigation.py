import json
from pathlib import Path
import re

import pytest

from echo.investigation import (
    EvidenceAssessment,
    EvidenceRelation,
    NON_DIRECTIONAL_EVIDENCE_ROLES,
    NON_DIRECTIONAL_EVIDENCE_STATUSES,
    evaluate_hypothesis,
    preview_evidence_relationship_change,
    validate_evidence_lineage,
    validate_follow_up_plan,
    validate_hypotheses,
    validate_investigation_contract,
)
from echo.investigation_draft import PRIMARY_SAR_EVIDENCE_ROLES


def assessment(evidence_id, relation, rationale="Test evidence statement."):
    return EvidenceAssessment(evidence_id, EvidenceRelation(relation), rationale)


def test_browser_assessment_guard_matches_authoritative_non_directional_contract():
    app_js = (Path(__file__).parents[1] / "echo" / "static" / "app.js").read_text()
    for frontend_name, backend_values in (
        ("NON_DIRECTIONAL_SOURCE_ROLES", NON_DIRECTIONAL_EVIDENCE_ROLES),
        ("NON_DIRECTIONAL_SOURCE_STATUSES", NON_DIRECTIONAL_EVIDENCE_STATUSES),
    ):
        match = re.search(rf"const {frontend_name} = new Set\((\[[^\n]*\])\);", app_js)
        assert match, f"browser guard {frontend_name} is missing"
        assert set(json.loads(match.group(1))) == backend_values


def test_browser_primary_sar_role_guard_matches_draft_contract_and_ignores_artifact_order():
    app_js = (Path(__file__).parents[1] / "echo" / "static" / "app.js").read_text()
    match = re.search(r"const PRIMARY_SAR_SOURCE_ROLES = new Set\((\[[^\n]*\])\);", app_js)
    assert match, "browser primary SAR role guard is missing"
    assert set(json.loads(match.group(1))) == PRIMARY_SAR_EVIDENCE_ROLES
    assert "function primarySarEvidenceArtifact(artifacts)" in app_js
    assert "primarySarEvidenceArtifact(record.evidence_artifacts)" in app_js
    assert "primarySarEvidenceArtifact(activeCatalogFollowupDraft.evidence_artifacts)" in app_js
    assert "record.evidence_artifacts[0]?.evidence_id!==source?.evidence_id" not in app_js


def test_opera_pair_source_inspector_uses_human_title_and_dark_scrollbar():
    root = Path(__file__).parents[1]
    app_js = (root / "echo" / "static" / "app.js").read_text()
    styles = (root / "echo" / "static" / "styles.css").read_text()
    assert '"SAR-RTC-S1-PAIR":"OPERA RTC-S1 pair measurement and quality review"' in app_js
    assert ".record-dialog{scrollbar-color:#40545d #0b1318;scrollbar-width:thin}" in styles


def test_tablet_layout_keeps_map_and_evidence_panel_within_viewport():
    styles = (Path(__file__).parents[1] / "echo" / "static" / "styles.css").read_text()
    assert "@media (min-width:761px) and (max-width:999px)" in styles
    assert "grid-template-columns:minmax(0,1fr) 280px" in styles
    assert ".left-rail{display:none}" in styles
    assert ".main-column{min-width:0" in styles


def test_revision_ui_marks_inherited_searches_as_historical_and_opens_source_records():
    app_js = (Path(__file__).parents[1] / "echo" / "static" / "app.js").read_text()
    assert "const inheritedFollowupSources=record.revision?.inherited_followup_sources||[];" in app_js
    assert 'class="draft-inherited-followups"' in app_js
    assert "NOT A RESULT FOR THE CURRENT TEST" in app_js
    assert "item.follow_up_link.target_hypothesis_id" in app_js
    assert "item.test_design.expected_observation" in app_js
    assert "item.test_design.would_weaken_if" in app_js
    assert 'class="draft-inspect-source" data-source-id="${escapeHTML(item.evidence_id)}"' in app_js


@pytest.mark.parametrize(
    ("items", "expected"),
    [
        ([], "NOT_EVALUATED"),
        ([assessment("E1", "SUPPORTS")], "SUPPORTED_WITHIN_SCOPE"),
        ([assessment("E1", "CONTRADICTS")], "CONTRADICTED_WITHIN_SCOPE"),
        ([assessment("E1", "DOES_NOT_DISTINGUISH")], "UNRESOLVED"),
        ([assessment("E1", "LIMITS_INTERPRETATION")], "UNRESOLVED"),
        ([assessment("E1", "SUPPORTS"), assessment("E2", "CONTRADICTS")], "UNRESOLVED"),
        ([assessment("E1", "SUPPORTS"), assessment("E2", "DOES_NOT_DISTINGUISH")], "UNRESOLVED"),
        ([assessment("E1", "SUPPORTS"), assessment("E2", "LIMITS_INTERPRETATION")], "UNRESOLVED"),
    ],
)
def test_disposition_is_conservative_and_has_no_probability_score(items, expected):
    result = evaluate_hypothesis(items, known_evidence_ids={"E1", "E2"})

    assert result["disposition"] == expected
    assert "probability" not in result
    assert len(result["evidence_assessments"]) == len(items)


def test_unknown_evidence_reference_is_rejected():
    with pytest.raises(ValueError, match="unknown evidence reference"):
        evaluate_hypothesis(
            [assessment("UNREGISTERED", "SUPPORTS")],
            known_evidence_ids={"E1"},
        )


def test_duplicate_reference_is_rejected():
    with pytest.raises(ValueError, match="duplicate evidence assessment"):
        evaluate_hypothesis(
            [assessment("E1", "SUPPORTS"), assessment("E1", "CONTRADICTS")],
            known_evidence_ids={"E1"},
        )


def test_empty_rationale_is_rejected():
    with pytest.raises(ValueError, match="rationale is required"):
        evaluate_hypothesis(
            [assessment("E1", "SUPPORTS", "  ")],
            known_evidence_ids={"E1"},
        )


def _minimal_investigation_record(relationship="DOES_NOT_DISTINGUISH"):
    return {
        "evidence_artifacts": [{
            "evidence_id": "E1",
            "lineage": {"derived_from_evidence_ids": [], "shares_source_observations_with": []},
        }],
        "hypotheses": [{
            "id": "H1",
            "statement": "A stated mechanism explains the measured response.",
            "state": "UNRESOLVED",
            "scope_limit": "This contract does not judge the evidence science.",
            "expected_observation": "A predeclared observation is present.",
            "would_weaken_if": "The predeclared observation is absent.",
            "testability_reason": "One linked source is nondiscriminating.",
            "testability_state": "DESCRIPTIVE_ONLY",
            "required_evidence": ["A measurement suitable for this mechanism."],
            "evidence_refs": ["E1"],
            "evidence_assessments": [{
                "evidence_id": "E1",
                "relationship": relationship,
                "rationale": "The source does not distinguish this mechanism.",
            }],
        }],
        "follow_up_evidence": [],
    }


@pytest.mark.parametrize(
    ("role", "status", "relationship", "directional_state"),
    [
        ("SAR_PAIR_HELD_AT_PROVIDER_QA", "QA_HELD", "SUPPORTS", "SUPPORTED_WITHIN_SCOPE"),
        ("SAR_PAIR_HELD_AT_PROVIDER_QA", "QA_HELD", "CONTRADICTS", "CONTRADICTED_WITHIN_SCOPE"),
        ("CATALOG_DISCOVERY_ONLY", "CATALOG_METADATA_ONLY", "SUPPORTS", "SUPPORTED_WITHIN_SCOPE"),
        ("NASA_INDEPENDENT_HYDROLOGY_CONTEXT_SCREEN", "SCREENED", "SUPPORTS", "SUPPORTED_WITHIN_SCOPE"),
        ("FOLLOWUP_PROVIDER_QA_METADATA_ONLY", "PROVIDER_QA_METADATA_ONLY", "CONTRADICTS", "CONTRADICTED_WITHIN_SCOPE"),
        (
            "NASA_MODEL_DERIVED_SOIL_MOISTURE_CATALOG_SCREEN",
            "NO_GRANULES_IN_TARGET_INTERVAL",
            "SUPPORTS",
            "SUPPORTED_WITHIN_SCOPE",
        ),
        (
            "IN_SITU_STATION_CATALOG_AVAILABILITY_SCREEN",
            "NO_SPATIOTEMPORALLY_SUITABLE_STATION",
            "CONTRADICTS",
            "CONTRADICTED_WITHIN_SCOPE",
        ),
    ],
)
def test_non_directional_qa_and_catalog_evidence_cannot_assess_physical_hypotheses(
    role, status, relationship, directional_state
):
    record = _minimal_investigation_record(relationship)
    record["evidence_artifacts"][0].update(role=role, status=status)
    record["hypotheses"][0]["state"] = directional_state

    with pytest.raises(ValueError, match="cannot directionally assess a hypothesis"):
        validate_investigation_contract(record)


@pytest.mark.parametrize(
    ("role", "status", "relationship"),
    [
        ("NASA_MODEL_DERIVED_SOIL_MOISTURE_CATALOG_SCREEN", "NO_GRANULES_IN_TARGET_INTERVAL", "DOES_NOT_DISTINGUISH"),
        ("NASA_MODEL_DERIVED_SOIL_MOISTURE_CATALOG_SCREEN", "NO_GRANULES_IN_TARGET_INTERVAL", "LIMITS_INTERPRETATION"),
        ("IN_SITU_STATION_CATALOG_AVAILABILITY_SCREEN", "NO_SPATIOTEMPORALLY_SUITABLE_STATION", "DOES_NOT_DISTINGUISH"),
        ("IN_SITU_STATION_CATALOG_AVAILABILITY_SCREEN", "NO_SPATIOTEMPORALLY_SUITABLE_STATION", "LIMITS_INTERPRETATION"),
    ],
)
def test_unavailable_source_screens_can_still_mark_gaps_or_limit_interpretation(
    role, status, relationship
):
    record = _minimal_investigation_record(relationship)
    record["evidence_artifacts"][0].update(role=role, status=status)

    result = validate_investigation_contract(record)

    assert result["hypotheses"][0]["state"] == "UNRESOLVED"


def test_optical_context_role_can_support_a_scoped_descriptive_hypothesis():
    record = _minimal_investigation_record("SUPPORTS")
    record["evidence_artifacts"][0].update(
        role="OPTICAL_PRODUCT_CONTEXT",
        status="NASA_OPTICAL_CONTEXT_ONLY_NOT_SAR_VALIDATION",
    )
    record["hypotheses"][0]["state"] = "SUPPORTED_WITHIN_SCOPE"

    result = validate_investigation_contract(record)

    assert result["hypotheses"][0]["state"] == "SUPPORTED_WITHIN_SCOPE"


def test_reusable_investigation_contract_accepts_explicit_unresolved_case():
    result = validate_investigation_contract(_minimal_investigation_record())

    assert result["evidence_ids"] == {"E1"}
    assert result["hypotheses"][0]["state"] == "UNRESOLVED"


def test_reusable_investigation_contract_rejects_directional_claim_from_nondistinguishing_evidence():
    record = _minimal_investigation_record()
    record["hypotheses"][0]["state"] = "SUPPORTED_WITHIN_SCOPE"

    with pytest.raises(ValueError, match="disposition does not match evidence relationships"):
        validate_investigation_contract(record)


def test_counterfactual_relationship_preview_is_separate_and_does_not_mutate_hypothesis():
    hypothesis = {
        "id": "H1",
        "evidence_assessments": [{
            "evidence_id": "E1",
            "relationship": "SUPPORTS",
            "rationale": "The cited measurement matches the predeclared pattern.",
        }],
    }

    preview = preview_evidence_relationship_change(
        hypothesis,
        evidence_id="E1",
        proposed_relationship="CONTRADICTS",
        known_evidence_ids={"E1"},
    )

    assert preview["current_disposition"] == "SUPPORTED_WITHIN_SCOPE"
    assert preview["counterfactual_disposition"] == "CONTRADICTED_WITHIN_SCOPE"
    assert preview["disposition_would_change"] is True
    assert preview["previous_relationship"] == "SUPPORTS"
    assert hypothesis["evidence_assessments"][0]["relationship"] == "SUPPORTS"
    assert "does not verify" in preview["interpretation_limit"]


def test_counterfactual_relationship_preview_preserves_unresolved_other_evidence():
    hypothesis = {
        "id": "H1",
        "evidence_assessments": [
            {"evidence_id": "E1", "relationship": "DOES_NOT_DISTINGUISH", "rationale": "No separation."},
            {"evidence_id": "E2", "relationship": "LIMITS_INTERPRETATION", "rationale": "Coverage is limited."},
        ],
    }

    preview = preview_evidence_relationship_change(
        hypothesis,
        evidence_id="E1",
        proposed_relationship="SUPPORTS",
        known_evidence_ids={"E1", "E2"},
    )

    assert preview["counterfactual_disposition"] == "UNRESOLVED"
    assert preview["disposition_would_change"] is False


def test_counterfactual_relationship_preview_requires_cited_source():
    with pytest.raises(ValueError, match="cited exactly once"):
        preview_evidence_relationship_change(
            {"id": "H1", "evidence_assessments": []},
            evidence_id="E1",
            proposed_relationship="SUPPORTS",
            known_evidence_ids={"E1"},
        )


def test_counterfactual_cannot_preview_directional_relabeling_of_qa_held_evidence():
    hypothesis = {
        "id": "H1",
        "evidence_assessments": [{
            "evidence_id": "E1",
            "relationship": "DOES_NOT_DISTINGUISH",
            "rationale": "The QA-held measurement does not establish a mechanism.",
        }],
    }

    with pytest.raises(ValueError, match="non-directional evidence cannot be previewed"):
        preview_evidence_relationship_change(
            hypothesis,
            evidence_id="E1",
            proposed_relationship="SUPPORTS",
            known_evidence_ids={"E1"},
            non_directional_evidence_ids={"E1"},
        )


def _hypothesis(**overrides):
    item = {
        "id": "H1",
        "statement": "A testable explanation.",
        "state": "NOT_EVALUATED",
        "scope_limit": "Only this case.",
        "expected_observation": "An expected observation.",
        "would_weaken_if": "An observation that weakens it.",
        "testability_state": "NOT_TESTED",
        "testability_reason": "Required evidence is absent.",
        "required_evidence": ["A suitable measurement"],
        "evidence_refs": [],
        "evidence_assessments": [],
    }
    item.update(overrides)
    return item


def test_hypothesis_contract_requires_falsifiable_test_conditions():
    item = _hypothesis()

    result = validate_hypotheses([item], known_evidence_ids={"E1"})

    assert result[0]["would_weaken_if"] == "An observation that weakens it."
    assert result[0]["testability_state"] == "NOT_TESTED"


@pytest.mark.parametrize(
    ("item", "known", "message"),
    [
        (_hypothesis(expected_observation=" "), {"E1"}, "expected_observation is required"),
        (_hypothesis(testability_state="LIKELY"), {"E1"}, "unsupported testability state"),
        (_hypothesis(testability_state=[]), {"E1"}, "unsupported testability state"),
        (_hypothesis(required_evidence=[]), {"E1"}, "nonempty list"),
        (_hypothesis(evidence_refs=["UNKNOWN"]), {"E1"}, "unknown evidence reference"),
        (_hypothesis(testability_state="DESCRIPTIVE_ONLY"), {"E1"}, "must cite evidence"),
        (_hypothesis(evidence_refs=["E1"]), {"E1"}, "do not match assessments"),
    ],
)
def test_hypothesis_contract_rejects_missing_or_untraceable_test_conditions(item, known, message):
    with pytest.raises(ValueError, match=message):
        validate_hypotheses([item], known_evidence_ids=known)


def test_hypothesis_contract_rejects_duplicate_ids():
    with pytest.raises(ValueError, match="duplicate hypothesis identifier"):
        validate_hypotheses([_hypothesis(), _hypothesis()], known_evidence_ids=set())


def test_hypothesis_disposition_must_match_its_evidence_relationships():
    item = _hypothesis(
        state="SUPPORTED_WITHIN_SCOPE",
        evidence_refs=["E1", "E2"],
        evidence_assessments=[
            {"evidence_id": "E1", "relationship": "SUPPORTS", "rationale": "Supports the claim."},
            {"evidence_id": "E2", "relationship": "CONTRADICTS", "rationale": "Conflicts with the claim."},
        ],
    )

    with pytest.raises(ValueError, match="does not match evidence relationships"):
        validate_hypotheses([item], known_evidence_ids={"E1", "E2"})


@pytest.mark.parametrize(
    ("assessment_item", "message"),
    [
        ({"evidence_id": "E1", "relationship": "LIKELY", "rationale": "Unsupported label."}, "unsupported evidence relationship"),
        ({"evidence_id": "E1", "relationship": "SUPPORTS", "rationale": "  "}, "evidence rationale is required"),
    ],
)
def test_hypothesis_contract_rejects_uninterpretable_evidence_assessments(assessment_item, message):
    item = _hypothesis(
        state="SUPPORTED_WITHIN_SCOPE",
        evidence_refs=["E1"],
        evidence_assessments=[assessment_item],
    )

    with pytest.raises(ValueError, match=message):
        validate_hypotheses([item], known_evidence_ids={"E1"})


def _follow_up(**overrides):
    item = {
        "follow_up_id": "F1",
        "target_hypothesis_ids": ["H1"],
        "purpose": "DISCRIMINATING_OBSERVATION",
        "availability_state": "NOT_SEARCHED",
        "action": "Search for compatible observations.",
        "discriminating_question": "Do observations distinguish the explanations?",
        "possible_interpretation": "A match could support; a mismatch could weaken.",
        "priority_reason": "The hypothesis is unresolved.",
    }
    item.update(overrides)
    return item


def _follow_up_test_design(non_targets=("H2", "H3")):
    return {
        "mechanism_branch": "Select one driver before retrieval.",
        "hypothesis_under_test_id": "H1",
        "expected_observation": "The selected variable changes with the measured response.",
        "would_weaken_if": "Adequate observations show no predicted association.",
        "inconclusive_if": "Quality, timing, or coverage is inadequate.",
        "acceptance_gates": ["Independent source", "Acceptable provider QA"],
        "does_not_test_hypothesis_ids": list(non_targets),
        "interpretation_limit": "Association does not establish cause.",
    }


def test_follow_up_plan_links_a_search_candidate_without_claiming_availability():
    result = validate_follow_up_plan(
        [_follow_up(test_design=_follow_up_test_design())],
        known_hypothesis_ids={"H1", "H2", "H3"},
    )

    assert result[0]["availability_state"] == "NOT_SEARCHED"
    assert result[0]["action_track"] == "NEW_EVIDENCE_SEARCH"
    assert result[0]["target_hypothesis_ids"] == ["H1"]


def test_follow_up_plan_keeps_partially_screened_search_open():
    result = validate_follow_up_plan(
        [_follow_up(
            availability_state="SEARCH_IN_PROGRESS_NO_SUITABLE_SOURCE",
            evidence_refs=["SCREEN"],
            test_design=_follow_up_test_design(),
        )],
        known_hypothesis_ids={"H1", "H2", "H3"},
        known_evidence_ids={"SCREEN"},
    )

    assert result[0]["availability_state"] == "SEARCH_IN_PROGRESS_NO_SUITABLE_SOURCE"
    assert result[0]["action_track"] == "NEW_EVIDENCE_SEARCH"


def test_open_discriminating_search_requires_test_design():
    with pytest.raises(ValueError, match="open evidence search requires a falsifiable test design"):
        validate_follow_up_plan(
            [_follow_up(test_design=None)],
            known_hypothesis_ids={"H1"},
        )


def test_follow_up_test_design_records_a_narrow_falsifiable_branch_and_non_targets():
    item = _follow_up(test_design=_follow_up_test_design())

    result = validate_follow_up_plan(
        [item],
        known_hypothesis_ids={"H1", "H2", "H3"},
    )

    assert result[0]["test_design"]["does_not_test_hypothesis_ids"] == ["H2", "H3"]


def test_discriminating_test_design_must_target_exactly_one_hypothesis():
    item = _follow_up(
        target_hypothesis_ids=["H1", "H2"],
        test_design=_follow_up_test_design(non_targets=("H3",)),
    )

    with pytest.raises(ValueError, match="must target exactly its one hypothesis under test"):
        validate_follow_up_plan(
            [item],
            known_hypothesis_ids={"H1", "H2", "H3"},
        )


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"expected_observation": " "}, "test design expected_observation is required"),
        ({"does_not_test_hypothesis_ids": ["MISSING"]}, "test design must identify other hypotheses"),
        ({"acceptance_gates": []}, "acceptance gates must be a nonempty text list"),
        ({"hypothesis_under_test_id": "H2"}, "must be a follow-up target"),
        ({"does_not_test_hypothesis_ids": ["H2", "H3"]}, "non-target hypotheses cannot be follow-up targets"),
    ],
)
def test_follow_up_test_design_rejects_incomplete_or_misaligned_contracts(change, message):
    design = {
        "mechanism_branch": "Select one driver before retrieval.",
        "hypothesis_under_test_id": "H1",
        "expected_observation": "The selected variable changes with the measured response.",
        "would_weaken_if": "Adequate observations show no predicted association.",
        "inconclusive_if": "Quality, timing, or coverage is inadequate.",
        "acceptance_gates": ["Independent source"],
        "does_not_test_hypothesis_ids": ["H2", "H3"],
        "interpretation_limit": "Association does not establish cause.",
    }
    design.update(change)
    item = _follow_up(
        target_hypothesis_ids=(
            ["H1", "H2"]
            if "does_not_test_hypothesis_ids" in change
            else ["H1"]
        ),
        test_design=design,
    )

    with pytest.raises(ValueError, match=message):
        validate_follow_up_plan(
            [item],
            known_hypothesis_ids={"H1", "H2", "H3"},
        )


def test_follow_up_plan_separates_qa_prerequisites_from_open_scientific_searches():
    quality_gate = _follow_up(
        follow_up_id="F_QA",
        purpose="QUALITY_GATE",
        availability_state="PROVIDER_RESPONSE_REQUIRED",
    )
    open_search = _follow_up(follow_up_id="F_SEARCH")
    open_search["test_design"] = _follow_up_test_design()
    reviewed_context = _follow_up(
        follow_up_id="F_CONTEXT",
        availability_state="RETRIEVED_QUALITY_LIMITED",
    )

    result = validate_follow_up_plan(
        [quality_gate, open_search, reviewed_context],
        known_hypothesis_ids={"H1", "H2", "H3"},
    )

    assert [item["action_track"] for item in result] == [
        "QUALITY_PREREQUISITE",
        "NEW_EVIDENCE_SEARCH",
        "REVIEWED_RESULT",
    ]


def test_evidence_lineage_distinguishes_derivation_from_shared_observations():
    records = [
        {"evidence_id": "VV", "lineage": {}},
        {"evidence_id": "VH", "lineage": {"shares_source_observations_with": ["VV"]}},
        {"evidence_id": "OVERLAY", "lineage": {"derived_from_evidence_ids": ["VV", "VH"]}},
    ]

    result = validate_evidence_lineage(records)

    assert result[1]["lineage"]["shares_source_observations_with"] == ["VV"]
    assert result[2]["lineage"]["derived_from_evidence_ids"] == ["VV", "VH"]


@pytest.mark.parametrize(
    ("records", "message"),
    [
        ([{"evidence_id": "A", "lineage": {"derived_from_evidence_ids": ["MISSING"]}}], "unknown derived_from"),
        ([{"evidence_id": "A", "lineage": {"derived_from_evidence_ids": ["A"]}}], "self-referential"),
        ([
            {"evidence_id": "A", "lineage": {"derived_from_evidence_ids": ["B"]}},
            {"evidence_id": "B", "lineage": {"derived_from_evidence_ids": ["A"]}},
        ], "contain a cycle"),
    ],
)
def test_evidence_lineage_rejects_invalid_or_cyclic_links(records, message):
    with pytest.raises(ValueError, match=message):
        validate_evidence_lineage(records)


@pytest.mark.parametrize(
    ("items", "known_ids", "message"),
    [
            ([_follow_up(test_design=_follow_up_test_design()), _follow_up(test_design=_follow_up_test_design())], {"H1", "H2", "H3"}, "duplicate follow-up identifier"),
        ([_follow_up(target_hypothesis_ids=["H2"])], {"H1"}, "unknown hypothesis target"),
        ([_follow_up(target_hypothesis_ids=[])], {"H1"}, "at least one hypothesis"),
        ([_follow_up(availability_state="AVAILABLE", test_design=_follow_up_test_design())], {"H1", "H2", "H3"}, "unsupported purpose or availability"),
        ([_follow_up(action_track="QUALITY_PREREQUISITE", test_design=_follow_up_test_design())], {"H1", "H2", "H3"}, "action track does not match"),
        ([_follow_up(action=" ")], {"H1"}, "action is required"),
    ],
)
def test_follow_up_plan_rejects_untraceable_or_unsupported_entries(items, known_ids, message):
    with pytest.raises(ValueError, match=message):
        validate_follow_up_plan(items, known_hypothesis_ids=known_ids)
