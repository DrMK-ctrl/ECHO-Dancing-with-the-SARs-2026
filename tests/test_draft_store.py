import hashlib
import json
import os
from datetime import datetime, timezone

import pytest

from echo.draft_store import DraftStoreError, LocalDraftStore
from echo.investigation_draft import build_investigation_draft


def _draft():
    source = {
        "record_type": "ECHO_GCOV_PAIR_ANALYSIS",
        "schema_version": 1,
        "status": "QA_HELD",
        "source_products": {"before": {"scene_id": "A"}, "after": {"scene_id": "B"}},
        "provider_qa": {"before": {"evidence": {"status": "FAIL"}}, "after": {"evidence": {"status": "FAIL"}}},
        "analysis_gates": {"provider_qa": "HELD_NON_PASS", "measurement_arrays": "NOT_READ", "change_calculation": "NOT_PERFORMED"},
        "measurement": None,
        "manifest": None,
    }
    hypotheses = [
        {"statement": f"Mechanism {index}", "scope_limit": "selected AOI", "expected_observation": f"expected signal {index}", "would_weaken_if": f"signal {index} is absent", "required_evidence": f"independent source {index}"}
        for index in (1, 2)
    ]
    next_observation = {
        "target_hypothesis_id": "H1",
        "action": "Retrieve independent observations across both acquisition dates.",
        "discriminating_question": "Does the observation distinguish the selected explanation?",
        "possible_interpretation": "A matching pattern is consistent with the explanation within scope.",
        "priority_reason": "It tests one named alternative with an independent source.",
        "expected_observation": "Quality-accepted observations show the registered pattern.",
        "would_weaken_if": "Suitable observations show no registered pattern.",
        "inconclusive_if": "Timing, quality, or spatial coverage is insufficient.",
        "acceptance_gates": "Independent source\nSuitable timing\nAdequate coverage",
        "interpretation_limit": "This does not validate the held SAR pair or establish cause.",
    }
    return build_investigation_draft(
        source,
        question="Which explanation is consistent with this radar response?",
        hypotheses=hypotheses,
        next_observation=next_observation,
        created_at_utc=datetime(2026, 11, 8, tzinfo=timezone.utc),
    )


def test_content_addressed_local_draft_round_trip_and_permissions(tmp_path):
    store = LocalDraftStore(tmp_path / "echo" / "drafts")
    draft = _draft()

    saved = store.save(draft)
    listed = store.list()
    restored = store.load(saved["draft_id"])

    assert saved["draft_id"] == hashlib.sha256(
        json.dumps(draft, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
    ).hexdigest()
    assert saved["already_saved"] is False
    assert store.save(draft)["already_saved"] is True
    assert listed[0]["integrity"] == "VALID"
    assert listed[0]["draft_id"] == saved["draft_id"]
    assert restored == draft
    if os.name == "posix":
        assert (tmp_path / "echo" / "drafts").stat().st_mode & 0o777 == 0o700
        assert next((tmp_path / "echo" / "drafts").glob("*.json")).stat().st_mode & 0o777 == 0o600


def test_local_draft_store_detects_changed_bytes_and_invalid_ids(tmp_path):
    store = LocalDraftStore(tmp_path / "drafts")
    draft_id = store.save(_draft())["draft_id"]
    path = tmp_path / "drafts" / f"{draft_id}.json"
    path.write_bytes(path.read_bytes() + b" ")

    with pytest.raises(DraftStoreError, match="checksum"):
        store.load(draft_id)
    assert store.list()[0]["integrity"] == "INVALID"
    with pytest.raises(DraftStoreError, match="draft_id"):
        store.load("../draft.json")


def test_local_draft_store_rejects_invalid_draft(tmp_path):
    store = LocalDraftStore(tmp_path / "drafts")
    with pytest.raises(DraftStoreError, match="validation failed"):
        store.save({"status": "DRAFT_NOT_ASSESSED"})
    assert not (tmp_path / "drafts").exists()
