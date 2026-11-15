/* Product-independent rendering for the evidence-and-hypothesis workflow. */
window.renderOperaScopedQualityReview = function renderOperaScopedQualityReview(review) {
  const escape = (value) => String(value ?? "NOT RECORDED").replace(/[&<>\"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[character]));
  const label = (value) => escape(value).replaceAll("_", " ");
  if (review?.record_type !== "ECHO_OPERA_RTC_S1_SCOPED_QUALITY_REVIEW") return "";
  const providerQa = review.provider_qa || {};
  const checks = review.echo_bounded_checks || {};
  const observations = (review.per_observation || []).map((item) => {
    const counts = item.aoi_mask_counts || {};
    const rfi = item.rfi_metadata || {};
    const missing = item.metadata_missing_fields?.length ? item.metadata_missing_fields.join(", ") : "None listed in this review";
    return `<details class="record-quality-observation"><summary>${escape(item.role).toUpperCase()} · ${escape(item.scene_id)}</summary><p>Scene disposition: <b>${label(item.provider_scene_disposition)}</b></p><p>AOI mask counts · clear ${escape(counts.clear_code_0)} · layover ${escape(counts.layover_affected)} · shadow ${escape(counts.shadow_affected)} · invalid ${escape(counts.invalid)}</p><p>RFI metadata · in/out band ratio ${escape(rfi.in_band_out_band_power_ratio)} · mitigation ${escape(rfi.mitigation_performed)} (${escape(rfi.mitigation_domain)}) · residual impact ${label(rfi.residual_impact_status)}</p><small>Missing metadata fields: ${escape(missing)} · sidecar SHA-256 ${escape(item.sidecar_sha256)}</small></details>`;
  }).join("");
  const published = review.provider_product_validation || {};
  return `<section class="record-quality-review" aria-label="OPERA RTC-S1 scoped quality review"><div class="scope-heading"><span>SCOPED PRODUCT QUALITY REVIEW</span><b>${label(review.status)}</b></div><p class="record-quality-boundary">Provider scene-level verdict: <b>${label(providerQa.scene_level_verdict)}</b>. No per-scene PASS/FAIL is provided; published product validation is contextual and does not certify these acquisitions. ECHO’s checks do not override provider QA.</p><p>ECHO checks · ${label(checks.registration_gate)} · resampling ${label(checks.resampling)} · common clear support ${escape(checks.common_clear_support_count)} / ${escape(checks.aoi_pixel_count)} cells.</p><small>Scope: ${escape(checks.check_scope)}. Published validation scope: ${escape(published.validation_scope)}</small><div class="record-quality-observations">${observations || "<p>No per-observation quality details are recorded.</p>"}</div><small>Assessment boundary · ${label(review.assessment_boundary?.disposition)} · RFI residual effect ${label(review.assessment_boundary?.rfi_residual_effect)} · physical cause supported: ${escape(review.assessment_boundary?.physical_cause_supported)} · provider QA overridden: ${escape(review.assessment_boundary?.provider_qa_overridden)}</small><small>Review basis SHA-256 ${escape(review.review_basis_sha256)}</small></section>`;
};

window.renderAcquisitionChronology = function renderAcquisitionChronology(rows, offsetText) {
  const escape = (value) => String(value ?? "—").replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[character]));
  const unavailable = `<section class="investigation-timeline"><b>ACQUISITION CHRONOLOGY UNAVAILABLE</b><p>Linked observation records are missing valid, ordered acquisition timestamps.</p></section>`;
  if (!Array.isArray(rows) || !rows.length) return unavailable;
  const timelineEvents = rows.flatMap((row) => [
    { row, role: "BEFORE", timestamp: row.before },
    { row, role: "AFTER", timestamp: row.after },
  ]).map((event) => ({ ...event, time: Date.parse(event.timestamp) }));
  if (timelineEvents.some((event) => !Number.isFinite(event.time))
      || rows.some((row) => !Number.isFinite(Date.parse(row.before))
        || !Number.isFinite(Date.parse(row.after))
        || Date.parse(row.after) < Date.parse(row.before))) return unavailable;
  const min = Math.min(...timelineEvents.map((event) => event.time));
  const max = Math.max(...timelineEvents.map((event) => event.time));
  const span = Math.max(1, max - min);
  const totalDays = (max - min) / 86400000;
  const tracks = rows.map((row) => {
    const points = timelineEvents.filter((event) => event.row === row);
    const marks = points.map((event) => {
      const position = ((event.time - min) / span) * 100;
      const detail = new Date(event.time).toISOString().replace("T", " ").replace("Z", " UTC");
      return `<span class="investigation-time-point ${String(row.kind || "").replace(/[^a-z0-9_-]/gi, "")} ${event.role.toLowerCase()}" data-time-position="${position.toFixed(3)}"><i></i><small><b>${event.role}</b>${escape(detail)}</small></span>`;
    }).join("");
    const interval = ((points[1].time - points[0].time) / 86400000).toFixed(2);
    const source = typeof row.evidence_id === "string" && row.evidence_id
      ? `<button type="button" class="investigation-source-link" data-evidence-id="${escape(row.evidence_id)}">INSPECT SOURCE</button>`
      : `<small class="investigation-time-source-missing">SOURCE RECORD NOT LINKED</small>`;
    return `<div class="investigation-time-row"><b>${escape(row.label)}</b>${source}<div class="investigation-time-track"><span class="investigation-time-line"></span>${marks}</div><small class="investigation-time-interval">Pair interval · ${interval} days</small></div>`;
  }).join("");
  return `<section class="investigation-timeline" aria-label="Observation acquisition chronology"><div class="investigation-timeline-heading"><b>ACQUISITION CHRONOLOGY</b><span>${totalDays.toFixed(1)} days represented · acquisition times in UTC</span></div>${tracks}<p>${escape(offsetText || "Acquisition offsets are not recorded for this assessment.")}</p><small>Temporal proximity is shown from acquisition timestamps. This view does not establish pixel alignment, observation equivalence, or causation.</small></section>`;
};

window.renderInvestigationReasoning = function renderInvestigationReasoning(record, options = {}) {
  const escape = (value) => String(value ?? "—").replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[character]));
  const hypotheses = Array.isArray(record.hypotheses) ? record.hypotheses : [];
  const artifacts = Array.isArray(record.evidence_artifacts) ? record.evidence_artifacts : [];
  const followUps = Array.isArray(record.follow_up_evidence) ? record.follow_up_evidence : [];
  const unresolvedHypotheses = new Map(hypotheses
    .filter((item) => ["UNRESOLVED", "NOT_EVALUATED"].includes(item.state))
    .map((item) => [item.id, item]));
  const followUpTrack = (item) => item.action_track || (
    item.purpose === "QUALITY_GATE" && ["NOT_SEARCHED", "PROVIDER_RESPONSE_REQUIRED"].includes(item.availability_state)
      ? "QUALITY_PREREQUISITE"
      : item.purpose === "DISCRIMINATING_OBSERVATION" && ["NOT_SEARCHED", "SEARCH_IN_PROGRESS_NO_SUITABLE_SOURCE", "ACCESS_REQUIRED"].includes(item.availability_state)
        ? "NEW_EVIDENCE_SEARCH"
        : "REVIEWED_RESULT"
  );
  const touchesUnresolvedHypothesis = (item) =>
    (item.target_hypothesis_ids || []).some((id) => unresolvedHypotheses.has(id));
  const openQualityGates = followUps.filter((item) =>
    followUpTrack(item) === "QUALITY_PREREQUISITE"
    && touchesUnresolvedHypothesis(item)
    && ["NOT_SEARCHED", "PROVIDER_RESPONSE_REQUIRED", "SEARCH_FAILED_RETRYABLE"].includes(item.availability_state)
  );
  const openEvidenceSearches = followUps.filter((item) =>
    followUpTrack(item) === "NEW_EVIDENCE_SEARCH"
    && touchesUnresolvedHypothesis(item)
    && ["NOT_SEARCHED", "SEARCH_FAILED_RETRYABLE", "SEARCH_IN_PROGRESS_NO_SUITABLE_SOURCE", "ACCESS_REQUIRED", "CANDIDATE_RETRIEVED_UNASSESSED"].includes(item.availability_state)
  );
  const targetStatements = (item) => (item.target_hypothesis_ids || [])
    .map((id) => unresolvedHypotheses.get(id)?.statement || id)
    .filter(Boolean)
    .map(escape).join(" · ");
  const decisionItems = (items, label) => items.map((item) =>
    `<article><b>${escape(item.follow_up_id)} · ${escape(item.availability_state.replaceAll("_", " "))}</b><p>${escape(item.action)}</p><small>TARGET · ${targetStatements(item) || "no currently unresolved hypothesis"}</small><small>RATIONALE · ${escape(item.priority_reason)}</small><small>${escape(label)} · This is a workflow dependency, not a probability, confidence, or information-gain score.</small></article>`
  ).join("");
  const decisionMarkup = openQualityGates.length || openEvidenceSearches.length
    ? `<section class="investigation-decision"><b>NEXT INVESTIGATION DECISION</b><p>These steps are selected from unresolved hypotheses and recorded availability states. ECHO does not infer that a source is available or scientifically suitable from this ordering.</p>${openQualityGates.length ? `<div><h4>INTERPRETATION GATE</h4>${decisionItems(openQualityGates, "MUST BE RESOLVED BEFORE CAUSAL INTERPRETATION")}</div>` : ""}${openEvidenceSearches.length ? `<div><h4>OPEN EVIDENCE SEARCH</h4>${decisionItems(openEvidenceSearches, "SEARCH OR SCREEN THIS ROUTE")}</div>` : ""}</section>`
    : `<section class="investigation-decision"><b>NEXT INVESTIGATION DECISION</b><p>No uncompleted quality prerequisite or evidence search is recorded for an unresolved explanation. Review existing inconclusive screens before starting another search; the case does not currently identify a validated next observation.</p></section>`;
  const artifactById = new Map(artifacts.map((artifact) => [artifact.evidence_id, artifact]));
  const derivedAncestors = (evidenceId, seen = new Set()) => {
    if (seen.has(evidenceId)) return seen;
    seen.add(evidenceId);
    const artifact = artifactById.get(evidenceId);
    for (const parent of artifact?.lineage?.derived_from_evidence_ids || []) derivedAncestors(parent, seen);
    return seen;
  };
  const hypothesisMarkup = hypotheses.map((item) => {
    const assessments = Array.isArray(item.evidence_assessments) ? item.evidence_assessments : [];
    const linkedEvidenceIds = new Set(assessments.map((assessment) => assessment.evidence_id));
    const unlinkedArtifacts = artifacts.filter((artifact) => !linkedEvidenceIds.has(artifact.evidence_id));
    const dependencyLinks = [];
    for (let leftIndex = 0; leftIndex < assessments.length; leftIndex += 1) {
      for (let rightIndex = leftIndex + 1; rightIndex < assessments.length; rightIndex += 1) {
        const leftId = assessments[leftIndex].evidence_id;
        const rightId = assessments[rightIndex].evidence_id;
        const left = artifactById.get(leftId);
        const right = artifactById.get(rightId);
        const leftLineage = left?.lineage || {};
        const rightLineage = right?.lineage || {};
        if ((leftLineage.shares_source_observations_with || []).includes(rightId) || (rightLineage.shares_source_observations_with || []).includes(leftId)) {
          dependencyLinks.push({ leftId, rightId, reason: "SHARED_SOURCE_OBSERVATIONS" });
          continue;
        }
        const leftAncestors = derivedAncestors(leftId);
        const rightAncestors = derivedAncestors(rightId);
        if (leftAncestors.has(rightId) || rightAncestors.has(leftId)) {
          dependencyLinks.push({ leftId, rightId, reason: "DERIVED_FROM_CITED_EVIDENCE" });
          continue;
        }
        const commonInputs = [...leftAncestors].filter((id) => rightAncestors.has(id));
        if (commonInputs.length) dependencyLinks.push({ leftId, rightId, reason: "COMMON_DERIVATION_INPUT", commonInputs });
      }
    }
    const relationOrder = [
      ["SUPPORTS", "supporting"],
      ["CONTRADICTS", "contradictory"],
      ["DOES_NOT_DISTINGUISH", "non-distinguishing"],
      ["LIMITS_INTERPRETATION", "interpretation-limiting"],
    ];
    const relationCounts = new Map();
    for (const assessment of assessments) {
      relationCounts.set(assessment.relationship, (relationCounts.get(assessment.relationship) || 0) + 1);
    }
    const relationSummary = relationOrder
      .filter(([relationship]) => relationCounts.has(relationship))
      .map(([relationship, label]) => `${relationCounts.get(relationship)} ${label} ${relationCounts.get(relationship) === 1 ? "link" : "links"}`)
      .join(" · ");
    const explanation = item.state === "SUPPORTED_WITHIN_SCOPE"
      ? "Recorded relationships are supportive within this hypothesis's stated scope. This does not establish causation, source quality, or independent confirmation."
      : item.state === "CONTRADICTED_WITHIN_SCOPE"
        ? "Recorded relationships are contradictory within this hypothesis's stated scope. This does not establish source quality or rule out explanations outside the stated scope."
        : item.state === "UNRESOLVED"
          ? `The recorded relationships do not yield a directional assessment${relationSummary ? ` (${relationSummary})` : ""}. Relationship labels are analyst-assigned, not confidence scores.`
          : "No evidence relationship has been assessed for this explanation; it remains not evaluated.";
    const relations = assessments.map((assessment) => {
      const source = artifactById.get(assessment.evidence_id);
      const sourceRole = source?.role || "ROLE NOT RECORDED";
      const sourceStatus = source?.status || "STATUS NOT RECORDED";
      const sourceStatusLabel = source?.ingest_method === "USER_SUPPLIED_LOCAL_JSON_RECORD" ? "USER-DECLARED STATUS · UNVERIFIED" : source?.ingest_method === "VALIDATED_LOCAL_CASE_ASSESSMENT" ? "CASE-RETAINED STATUS · PROVIDER NOT REVERIFIED" : "EVIDENCE RECORD STATUS";
      const caseTrace = source?.case_provenance;
      const followupScreenTrace = assessment.followup_screen_sha256
        ? `<small>REGISTERED FOLLOW-UP SCREEN SHA-256 · ${escape(assessment.followup_screen_sha256)}</small><button type="button" class="investigation-followup-screen-link" data-screen-source="${escape(assessment.evidence_id)}">INSPECT LINKED GATE SCREEN</button>`
        : "";
      return `<li><button type="button" class="investigation-source-link" data-evidence-id="${escape(assessment.evidence_id)}">${escape(assessment.evidence_id)}</button><b> · ${escape((assessment.relationship || "").replaceAll("_", " "))}</b><small class="investigation-relation-source">ANALYST-DECLARED FIT · ${escape((assessment.evidence_fit || "UNKNOWN").replaceAll("_", " "))}</small><small class="investigation-relation-source">${escape(sourceRole.replaceAll("_", " "))} · ${sourceStatusLabel}: ${escape(sourceStatus.replaceAll("_", " "))}</small>${caseTrace?`<small>CASE PROVENANCE · ${escape(caseTrace.case_id)} · ${escape(caseTrace.source_evidence_id)} · ${escape(caseTrace.source_relative_path)}</small>`:""}${followupScreenTrace}<span>${escape(assessment.rationale)}</span>${assessment.review_basis?`<small>INSPECTION BASIS · ${escape(assessment.review_basis)}</small>`:""}${assessment.limitations?`<small>STATED LIMITS · ${escape(assessment.limitations)}</small>`:""}</li>`;
    }).join("");
    const dependencyMarkup = dependencyLinks.length ? `<details class="hypothesis-evidence-dependencies"><summary>DEPENDENT EVIDENCE · ${dependencyLinks.length} LINK${dependencyLinks.length === 1 ? "" : "S"}</summary><p>These cited records have explicit shared or derived lineage. Their relationships are not independent corroboration. Missing lineage metadata does not prove that other records are independent.</p><ul>${dependencyLinks.map((link) => {
      const reason = link.reason === "SHARED_SOURCE_OBSERVATIONS" ? "Share source observations" : link.reason === "DERIVED_FROM_CITED_EVIDENCE" ? "One record is derived from the other" : `Share recorded derivation input${link.commonInputs.length === 1 ? "" : "s"}: ${link.commonInputs.join(" · ")}`;
      return `<li><button type="button" class="investigation-source-link" data-evidence-id="${escape(link.leftId)}">${escape(link.leftId)}</button><span>↔</span><button type="button" class="investigation-source-link" data-evidence-id="${escape(link.rightId)}">${escape(link.rightId)}</button><small>${escape(reason)}</small></li>`;
    }).join("")}</ul></details>` : "";
    const coverageMarkup = `<details class="hypothesis-evidence-coverage"><summary>EVIDENCE COVERAGE · ${assessments.length} LINKED · ${unlinkedArtifacts.length} OTHER SOURCE${unlinkedArtifacts.length === 1 ? "" : "S"}</summary><p>Other source records in this investigation have no relationship recorded for this hypothesis. Their relevance has not been assessed here; an unlinked record is not negative evidence, proof of irrelevance, or independent corroboration.</p>${unlinkedArtifacts.length ? `<ul>${unlinkedArtifacts.map((artifact) => `<li><button type="button" class="investigation-source-link" data-evidence-id="${escape(artifact.evidence_id)}">${escape(artifact.evidence_id)}</button><small>${escape((artifact.role || "ROLE NOT RECORDED").replaceAll("_", " "))} · ${escape((artifact.status || "STATUS NOT RECORDED").replaceAll("_", " "))}</small></li>`).join("")}</ul>` : "<p class=\"hypothesis-evidence-coverage-complete\">Every source record currently listed in this investigation has a relationship recorded for this hypothesis. This does not establish that the source set is complete.</p>"}</details>`;
    const requirements = (item.required_evidence || []).map((requirement) => `<li>${escape(requirement)}</li>`).join("");
    const isDraft = record.record_type === "ECHO_INVESTIGATION_DRAFT";
    const isAssessedDraft = isDraft && record.status === "DRAFT_ANALYST_ASSESSED_UNVERIFIED";
    const challenge = isDraft
      ? (isAssessedDraft && options.enableDraftChallenge
        ? `<button type="button" class="challenge-hypothesis" data-hypothesis-id="${escape(item.id)}">CHALLENGE THIS FINDING</button>`
        : "")
      : record.status === "DRAFT_NOT_ASSESSED"
        ? ""
        : `<button type="button" class="challenge-hypothesis" data-hypothesis-id="${escape(item.id)}">CHALLENGE THIS FINDING</button>`;
    return `<article class="investigation-hypothesis"><div><b>${escape(item.statement)}</b><span class="investigation-state state-${escape((item.state || "").toLowerCase().replaceAll("_", "-"))}">${escape((item.state || "").replaceAll("_", " "))}</span></div><small class="hypothesis-testability">TESTABILITY · ${escape((item.testability_state || "").replaceAll("_", " "))}</small><p class="hypothesis-reasoning">${escape(explanation)}</p>${coverageMarkup}${dependencyMarkup}${relations ? `<ul class="investigation-relations">${relations}</ul>` : "<p>No relevant evidence is recorded for this explanation.</p>"}<details class="hypothesis-test"><summary>TEST CONDITIONS</summary><div><b>EXPECTED OBSERVATION</b><p>${escape(item.expected_observation)}</p><b>WOULD WEAKEN IF</b><p>${escape(item.would_weaken_if)}</p><b>WHY THIS TESTABILITY STATE</b><p>${escape(item.testability_reason)}</p><b>REQUIRED EVIDENCE</b><ul>${requirements}</ul></div></details><small>SCOPE · ${escape(item.scope_limit || "Not specified")}</small>${challenge}</article>`;
  }).join("");

  const relationshipLabels = {
    SUPPORTS: ["SUP", "supports"],
    CONTRADICTS: ["CON", "contradicts"],
    DOES_NOT_DISTINGUISH: ["N/D", "does not distinguish"],
    LIMITS_INTERPRETATION: ["LIMITS", "limits interpretation"],
  };
  const hypothesisEvidenceMatrix = artifacts.length && hypotheses.length
    ? `<details class="investigation-evidence-matrix"><summary>EVIDENCE / HYPOTHESIS MATRIX · ${artifacts.length} SOURCES × ${hypotheses.length} EXPLANATIONS</summary><p>Cells show only recorded analyst-assigned relationships. “Not assessed” means no relationship is recorded; it does not mean irrelevant, contradictory, or independent evidence.</p><div class="investigation-evidence-matrix-scroll" role="region" aria-label="Evidence and hypothesis relationship matrix" tabindex="0"><table><thead><tr><th scope="col">EVIDENCE SOURCE</th>${hypotheses.map((hypothesis) => `<th scope="col" title="${escape(hypothesis.statement)}"><span>${escape(hypothesis.id)}</span><small>${escape((hypothesis.state || "STATE NOT RECORDED").replaceAll("_", " "))}</small></th>`).join("")}</tr></thead><tbody>${artifacts.map((artifact) => {
      const relationships = new Map(hypotheses.flatMap((hypothesis) => (hypothesis.evidence_assessments || [])
        .filter((assessment) => assessment.evidence_id === artifact.evidence_id)
        .map((assessment) => [hypothesis.id, assessment.relationship])));
      const role = (artifact.role || "ROLE NOT RECORDED").replaceAll("_", " ");
      const sourceStatus = (artifact.status || "STATUS NOT RECORDED").replaceAll("_", " ");
      return `<tr><th scope="row"><button type="button" class="investigation-source-link" data-evidence-id="${escape(artifact.evidence_id)}">${escape(artifact.evidence_id)}</button><small>${escape(role)} · ${escape(sourceStatus)}</small></th>${hypotheses.map((hypothesis) => {
        const relationship = relationships.get(hypothesis.id);
        const [label, description] = relationshipLabels[relationship] || ["—", "not assessed"];
        const missingExplanation = relationship ? "" : "; no relationship recorded, relevance not assessed";
        return `<td><span class="evidence-matrix-cell${relationship ? "" : " unassessed"}" aria-label="${escape(description + missingExplanation)}" title="${escape(description + missingExplanation)}">${label}</span></td>`;
      }).join("")}</tr>`;
    }).join("")}</tbody></table></div><small class="investigation-evidence-matrix-legend">SUP · supports &nbsp; CON · contradicts &nbsp; N/D · does not distinguish &nbsp; LIMITS · limits interpretation &nbsp; — · not assessed. Relationship labels are not independently verified or confidence scores.</small></details>`
    : "";

  const evidenceByHypothesis = new Map();
  for (const hypothesis of hypotheses) {
    for (const assessment of hypothesis.evidence_assessments || []) {
      const entries = evidenceByHypothesis.get(assessment.evidence_id) || [];
      entries.push({ hypothesis, assessment });
      evidenceByHypothesis.set(assessment.evidence_id, entries);
    }
  }
  const sharedEvidence = [...evidenceByHypothesis.entries()].filter(([, entries]) => entries.length > 1);
  const sharedMarkup = sharedEvidence.length ? `<details class="investigation-cross-hypothesis"><summary>EVIDENCE ACROSS EXPLANATIONS · ${sharedEvidence.length} SHARED RECORDS</summary><p>The same source is cited under multiple explanations. Its appearance in multiple rows is not independent corroboration; relationships below are analyst-assigned and remain scoped to each hypothesis.</p><div>${sharedEvidence.map(([evidenceId, entries]) => {
    const artifact = artifactById.get(evidenceId);
    return `<article><div><button type="button" class="investigation-source-link" data-evidence-id="${escape(evidenceId)}">${escape(evidenceId)}</button><small>${escape((artifact?.role || "EVIDENCE").replaceAll("_", " "))}</small></div><ul>${entries.map(({ hypothesis, assessment }) => `<li><span>${escape(hypothesis.statement)}</span><b>${escape((assessment.relationship || "").replaceAll("_", " "))}</b></li>`).join("")}</ul></article>`;
  }).join("")}</div></details>` : "";

  const lineageRows = artifacts.map((artifact) => {
    const lineage = artifact.lineage || {};
    const derived = (lineage.derived_from_evidence_ids || []).map(escape);
    const shared = (lineage.shares_source_observations_with || []).map(escape);
    const relationship = [
      derived.length ? `Derived from ${derived.join(" · ")}` : "",
      shared.length ? `Shares source observations with ${shared.join(" · ")}` : "",
    ].filter(Boolean).join(" · ") || "Primary source record; no upstream evidence link recorded";
    const statusLabel = artifact.role === "USER_SUPPLIED_SOURCE_NOT_REVIEWED" ? "USER-DECLARED STATUS · UNVERIFIED" : "EVIDENCE RECORD STATUS";
    return `<li><button type="button" class="investigation-source-link" data-evidence-id="${escape(artifact.evidence_id)}">${escape(artifact.evidence_id)}</button><b> · ${escape((artifact.role || "EVIDENCE").replaceAll("_", " "))}</b><small class="investigation-relation-source">${statusLabel}: ${escape((artifact.status || "NOT RECORDED").replaceAll("_", " "))}</small><span>${relationship}</span></li>`;
  }).join("");
  const lineageMarkup = `<details class="investigation-lineage"><summary>EVIDENCE DEPENDENCIES · ${artifacts.length} RECORDS</summary><p>Derived analyses and products sharing source acquisitions are identified so related results are not mistaken for independent corroboration.</p><ul>${lineageRows}</ul></details>`;

  const followUpMarkup = followUps.map((item) => {
    const targets = (item.target_hypothesis_ids || []).map((id) => hypotheses.find((hypothesis) => hypothesis.id === id)?.statement || id).join(" · ");
    const refs = (item.evidence_refs || []).map((id) => `<button type="button" class="investigation-source-link" data-evidence-id="${escape(id)}">INSPECT ${escape(id)}</button>`).join(" ") || "No retrieved evidence record";
    const catalogSources = (item.evidence_refs || []).map((id) => {
      const value = record.source_records?.[id];
      if (typeof value === "string") {
        try { return JSON.parse(value); } catch { return null; }
      }
      return value;
    }).filter((source) => source?.record_type === "ECHO_FOLLOWUP_CATALOG_SCREEN" && source.search_window_comparison);
    const searchWindowMarkup = catalogSources.map((source) => {
      const comparison = source.search_window_comparison;
      const planned = comparison.planned_window;
      const executed = comparison.executed_window;
      return `<div class="followup-window-check"><b>CATALOG DATE FILTER · ${escape((comparison.state || "UNKNOWN").replaceAll("_", " "))}</b><small>PLANNED · ${planned ? `${escape(planned.start_date_inclusive)} through ${escape(planned.end_date_inclusive)}` : "no interval registered"}</small><small>EXECUTED · ${escape(executed?.start_date_inclusive)} through ${escape(executed?.end_date_inclusive)} · date-filter comparison only</small></div>`;
    }).join("");
    const actionTrack = followUpTrack(item);
    const design = item.test_design;
    const plannedWindow = design?.catalog_search_window;
    const plannedWindowMarkup = plannedWindow ? `<b>PLANNED CATALOG SEARCH WINDOW</b><p>${escape(plannedWindow.start_date_inclusive)} through ${escape(plannedWindow.end_date_inclusive)} · discovery filter only</p>` : "";
    const designMarkup = design ? `<details class="followup-test-design"><summary>PRE-REGISTERED TEST DESIGN</summary><div><b>MECHANISM BRANCH</b><p>${escape(design.mechanism_branch)}</p><b>EXPECTED IF PRESENT</b><p>${escape(design.expected_observation)}</p><b>WOULD WEAKEN IF</b><p>${escape(design.would_weaken_if)}</p><b>REMAINS INCONCLUSIVE IF</b><p>${escape(design.inconclusive_if)}</p>${plannedWindowMarkup}<b>DATA ACCEPTANCE GATES</b><ul>${(design.acceptance_gates || []).map((gate) => `<li>${escape(gate)}</li>`).join("")}</ul><b>DOES NOT TEST</b><ul>${(design.does_not_test_hypothesis_ids || []).map((id) => `<li>${escape(hypotheses.find((entry) => entry.id === id)?.statement || id)}</li>`).join("")}</ul><b>INTERPRETATION LIMIT</b><p>${escape(design.interpretation_limit)}</p></div></details>` : "";
    const screens = Array.isArray(item.screening_history)
      ? item.screening_history
      : item.screening_review ? [item.screening_review] : [];
    const screeningContext = screens.length > 1
      ? `<p>Each candidate has its own gate screen. The follow-up state reflects whether any one candidate met all analyst-declared gates; results are not transferred between sources.</p>`
      : "";
    const screenMarkup = screens.map((screen, index) => {
      const candidateState = screen.gate_results.every((gate) => gate.result === "MET")
        ? "ALL DECLARED GATES MET · ANALYST ENTERED"
        : "ONE OR MORE GATES NOT MET OR UNKNOWN · ANALYST ENTERED";
      return `<details class="followup-screen-record" data-screen-source="${escape(screen.source_evidence_id)}"><summary>CANDIDATE ${index + 1} · ${escape(candidateState)}</summary><p>Gate results were entered by an unauthenticated analyst. They do not independently validate source quality, independence, or hypothesis relevance.</p><button type="button" class="investigation-source-link" data-evidence-id="${escape(screen.source_evidence_id)}">INSPECT ${escape(screen.source_evidence_id)}</button><ul>${screen.gate_results.map((gate) => `<li>${escape(gate.gate)} · ${escape(gate.result)}</li>`).join("")}</ul><b>INSPECTION BASIS</b><p>${escape(screen.review_basis)}</p><b>LIMITATIONS</b><p>${escape(screen.limitations)}</p><small>SCREENED ${escape(screen.screened_at_utc)} · SOURCE SHA-256 ${escape(screen.source_sha256)} · SCREEN RECORD SHA-256 ${escape(screen.sha256)}</small></details>`;
    }).join("");
    return `<article class="investigation-followup"><div><b>${escape((item.purpose || "").replaceAll("_", " "))}</b><span class="followup-availability">${escape((item.availability_state || "").replaceAll("_", " "))}</span></div><small class="followup-track">WORKSTREAM · ${escape(actionTrack.replaceAll("_", " "))}</small><p>${escape(item.action)}</p><small>TEST · ${escape(item.discriminating_question)}</small><small>IF OBSERVED · ${escape(item.possible_interpretation)}</small><small>TARGET · ${escape(targets)}</small><div class="followup-evidence-records"><small>EVIDENCE RECORDS</small>${refs}</div>${searchWindowMarkup}${designMarkup}${screeningContext}${screenMarkup}<small>WHY NOW · ${escape(item.priority_reason)}</small></article>`;
  }).join("");

  return `<section class="investigation-reasoning">${hypothesisEvidenceMatrix}<div class="investigation-hypotheses">${hypothesisMarkup}</div>${sharedMarkup}${lineageMarkup}${decisionMarkup}<div class="investigation-next"><b>INVESTIGATION WORKSTREAM RECORD</b><p>Completed screens remain visible for audit. The decision summary above separates interpretation gates from searches that may add evidence; neither is a scientific conclusion.</p><div class="investigation-followups">${followUpMarkup}</div></div></section>`;
};

window.renderInvestigationIntegrityImpact = function renderInvestigationIntegrityImpact(impact) {
  const escape = (value) => String(value ?? "—").replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[character]));
  const affectedEvidence = new Set(impact.affected_evidence_ids || []);
  const changed = (impact.changed_evidence || []).map((item) =>
    `<article><b>${escape(item.evidence_id)}</b><small>${escape(item.role || "SOURCE")} · ${escape(item.integrity_state)}</small>${item.asset_path ? `<small>FILE · ${escape(item.asset_path)}</small>` : ""}<code>Expected ${escape(item.expected_sha256 || "unknown")}<br>Observed ${escape(item.observed_sha256 || "unavailable")}</code></article>`
  ).join("");
  const hypotheses = (impact.affected_hypotheses || []).map((item) =>
    `<li><b>${escape(item.hypothesis_id)}</b> · ${escape(item.state || "state unavailable")}<span>${escape(item.statement || "")}</span></li>`
  ).join("");
  const followUps = (impact.affected_follow_ups || []).map((item) =>
    `<li><b>${escape(item.follow_up_id)}</b><span>${escape(item.action || "")}</span></li>`
  ).join("");
  return `<section class="investigation-integrity-impact"><div class="eyebrow">EVIDENCE INTEGRITY <span>·</span> REASSESSMENT REQUIRED</div><h2>Linked source evidence changed</h2><p>${escape(impact.interpretation_limit || "The retained assessment cannot be treated as current until its evidence is reviewed.")}</p><small>Assessment SHA-256 · ${escape(impact.assessment_sha256 || "unavailable")}</small><h3>CHANGED OR UNAVAILABLE SOURCE RECORDS</h3><div class="integrity-impact-sources">${changed}</div><h3>DEPENDENT FINDINGS · ${hypotheses ? "HYPOTHESES SHOWN" : "NONE DIRECTLY IDENTIFIED"}</h3>${hypotheses ? `<ul>${hypotheses}</ul>` : `<p>No hypothesis directly references the affected evidence IDs: ${escape([...affectedEvidence].join(" · ") || "none resolved")}. Re-review the full assessment.</p>`}<h3>DEPENDENT FOLLOW-UP PLANS</h3>${followUps ? `<ul>${followUps}</ul>` : "<p>No linked follow-up plan was identified.</p>"}<p class="investigation-boundary">ECHO did not accept the changed source as evidence or display the prior assessment as current. Restore the expected source or rebuild and review the linked assessment.</p></section>`;
};

window.renderAdversarialChallenge = function renderAdversarialChallenge(record) {
  const escape = (value) => String(value ?? "—").replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[character]));
  const sourceButton = (item, label = item.evidence_id) => item.evidence_id
    ? `<button type="button" class="investigation-source-link" data-evidence-id="${escape(item.evidence_id)}">${escape(label)}</button>`
    : escape(label);
  if (record.status === "QA_HELD_NO_CHANGE_FINDING") {
    const candidateProducts = record.candidate_pair?.products || [];
    const summaryHashes = new Set(candidateProducts.map((item) => item.qa_summary_sha256).filter(Boolean));
    const identicalSummaryNotice = candidateProducts.length > 1 && summaryHashes.size === 1
      ? `<p>Each acquisition has its own ASF QA CSV URL. The retrieved CSV content is byte-identical across these products (matching SHA-256), while the linked product QA reports remain product-specific.</p>`
      : "";
    const products = candidateProducts.map((item) => {
      const summarySize = Number.isFinite(item.qa_summary_size_bytes)
        ? `${escape(item.qa_summary_size_bytes)} bytes`
        : "size not recorded";
      const summaryLink = item.qa_summary_uri
        ? `<a href="${escape(item.qa_summary_uri)}" target="_blank" rel="noopener noreferrer">OPEN PROVIDER QA CSV ↗</a>`
        : "Provider QA CSV URL unavailable";
      const reportLink = item.qa_report_uri
        ? `<a href="${escape(item.qa_report_uri)}" target="_blank" rel="noopener noreferrer">OPEN PRODUCT QA REPORT ↗</a>`
        : "Product QA report URL unavailable";
      const reportSize = Number.isFinite(item.qa_report_size_bytes)
        ? `${escape(item.qa_report_size_bytes)} bytes`
        : "size not recorded";
      return `<li><b>${escape(item.scene_id)}</b><span>${escape(item.acquisition_time_utc)} · provider QA ${escape(item.provider_qa_state)}</span><small>QA summary CSV · ${summarySize} · SHA-256 ${escape(item.qa_summary_sha256)} · retrieved ${escape(item.qa_summary_retrieved_at_utc)}</small><span class="qa-artifact-links">${summaryLink} · ${reportLink}</span><small>QA report PDF · ${reportSize} · SHA-256 ${escape(item.qa_report_sha256)} · retrieved ${escape(item.qa_report_retrieved_at_utc)}</small></li>`;
    }).join("");
    const observation = record.observation || {};
    return `<section class="adversarial-challenge qa-held-challenge"><div class="eyebrow">CHALLENGE REVIEW <span>·</span> ${escape(record.status.replaceAll("_", " "))}</div><h2>No change finding exists to challenge</h2><p>${escape(record.challenge_result?.reason)}</p><section><h3>OBSERVATION AVAILABLE</h3><p>${escape(observation.measurement)} · ${escape(observation.units)} · ${escape(observation.selected_pixel_center_count)} selected pixel centers · acquired ${escape(observation.acquired_at_utc)}</p><small>One QA-held diagnostic NISAR observation · source record SHA-256 ${escape(observation.source_record_sha256)}</small></section><section><h3>PAIR QA GATE</h3><p>Candidate interval ${escape(record.candidate_pair?.interval_days)} days · ${escape(record.candidate_pair?.status)} · ${escape(record.candidate_pair?.qa_status)}</p>${identicalSummaryNotice}<ul>${products}</ul></section><section class="adversarial-result"><b>ASSESSMENT</b><p>No temporal change was computed, and ECHO does not infer an event or physical explanation from the single-scene preview.</p><p><b>NEXT:</b> ${escape(record.challenge_result?.next_step)}</p></section><small>${escape(record.interpretation_limit)}</small></section>`;
  }
  const finding = record.hypothesis || {};
  const evidence = record.evidence_review?.recorded_relationships || [];
  const relationGroup = (items, relationship, title, note) => {
    const selected = items.filter((item) => item.relationship === relationship);
    if (!selected.length) return `<p class="adversarial-empty">No ${escape(title.toLowerCase())} relationship is recorded. Absence of a relationship is not evidence against the explanation.</p>`;
    return `<ul>${selected.map((item) => `<li>${sourceButton(item)} <b>${escape(item.source_status)} · ${escape(item.role.replaceAll("_", " "))}</b><span>${escape(item.rationale)}</span><small>Recorded analyst assessment; not independently verified here. ${escape(note)} · source SHA-256 ${escape(item.sha256)}</small></li>`).join("")}</ul>`;
  };
  const sources = record.sensitivity_review?.linked_sources || [];
  const recordedSensitivityResults = record.sensitivity_review?.recorded_results || [];
  const comparability = record.comparability_review;
  const compactValue = (value) => {
    if (value === null || value === undefined) return "not reported";
    const text = typeof value === "string" ? value : JSON.stringify(value);
    return text.length > 120 ? `${text.slice(0, 117)}…` : text;
  };
  const comparisonRows = (comparability?.comparisons || []).map((item) =>
    `<li><b>${escape(item.field.replaceAll("_", " "))} · ${escape(item.comparison)}</b><span>${escape(compactValue(item.before))} → ${escape(compactValue(item.after))}</span></li>`
  ).join("");
  const comparabilityMarkup = comparability
    ? `<section class="challenge-comparability"><b>ACQUISITION COMPARABILITY · ${escape(comparability.scope.replaceAll("_", " "))}</b><p>Documented platform, product, and processing fields are summarized from the retained pair metadata. This comparison does not establish raster alignment or clear provider QA.</p><p>${escape(comparability.interpretation)}</p>${sourceButton({evidence_id: comparability.evidence_id}, "INSPECT CHECKSUM-LINKED COMPARABILITY REVIEW")}<details><summary>FIELD-BY-FIELD METADATA AND LIMITS</summary><ul class="challenge-comparison-rows">${comparisonRows}</ul><ul>${(comparability.limitations || []).map((item) => `<li>${escape(item)}</li>`).join("")}</ul><small>Review SHA-256 · ${escape(comparability.sha256)}</small></details></section>`
    : `<p>No checksum-linked acquisition comparability review is available for this case.</p>`;
  const sensitivityResultMarkup = recordedSensitivityResults.map((item) => {
    const summary = item.summary || {};
    let metrics = "<p>This linked record is checksum-verified, but this challenge view has no validated metric adapter for its contents.</p>";
    if (item.result_kind === "RECORDED_POLARIZATION_COMPARISON") {
      metrics = `<dl class="challenge-sensitivity-metrics"><dt>Common cells</dt><dd>${escape(summary.common_cells)}</dd><dt>VV mean / median log ratio</dt><dd>${escape(Number(summary.vv_mean_log_ratio_db).toFixed(3))} / ${escape(Number(summary.vv_median_log_ratio_db).toFixed(3))} dB</dd><dt>VH mean / median log ratio</dt><dd>${escape(Number(summary.vh_mean_log_ratio_db).toFixed(3))} / ${escape(Number(summary.vh_median_log_ratio_db).toFixed(3))} dB</dd><dt>VV–VH descriptive correlation</dt><dd>${escape(Number(summary.vv_vh_pearson_r_log_ratio).toFixed(3))}</dd><dt>Water-change association, VV / VH</dt><dd>${escape(Number(summary.vv_pearson_r_water_change_vs_log_ratio).toFixed(3))} / ${escape(Number(summary.vh_pearson_r_water_change_vs_log_ratio).toFixed(3))}</dd></dl>`;
    } else if (item.result_kind === "RECORDED_OPTICAL_SUPPORT_THRESHOLD_VARIANTS") {
      const metric = (value) => Number.isFinite(value) ? Number(value).toFixed(3) : "—";
      const variants = (summary.exploratory_threshold_sweep || []).map((variant) =>
        `<tr><td>${escape((variant.minimum_common_valid_wtr_area_fraction * 100).toFixed(0))}%</td><td>${escape(variant.sar_cells)}</td><td>${metric(variant.mean_signed_sar_log_ratio_db)} / ${metric(variant.median_signed_sar_log_ratio_db)} dB</td><td>${metric(variant.descriptive_pearson_r_water_fraction_change_vs_sar_log_ratio_db)}</td></tr>`
      ).join("");
      metrics = `<p>Exploratory threshold sweep, calculated from the checksum-verified per-cell record in 5 percentage-point steps. No cutoff is preferred. Values are descriptive and do not establish flood extent, causation, or provider QA clearance.</p><div class="table-scroll"><table><thead><tr><th>Minimum common WTR support</th><th>SAR cells</th><th>Mean / median signed log ratio</th><th>Descriptive r</th></tr></thead><tbody>${variants}</tbody></table></div>`;
    }
    let spatialMarkup = "";
    if (item.spatial_map) {
      const map = item.spatial_map;
      const [west, south, east, north] = map.bounds_wgs84;
      const width = 760, height = 430, padding = 18;
      const latitudeScale = Math.cos(((south + north) / 2) * Math.PI / 180);
      const geographicWidth = (east - west) * latitudeScale;
      const geographicHeight = north - south;
      const scale = Math.min((width - padding * 2) / geographicWidth, (height - padding * 2) / geographicHeight);
      const xOffset = (width - geographicWidth * scale) / 2;
      const yOffset = (height - geographicHeight * scale) / 2;
      const project = ([longitude, latitude]) => [
        xOffset + (longitude - west) * latitudeScale * scale,
        height - yOffset - (latitude - south) * scale,
      ];
      const cells = (map.cells || []).map((cell) => {
        const corners = map.pixel_corners_wgs84;
        const ring = [
          corners[cell.row][cell.column],
          corners[cell.row][cell.column + 1],
          corners[cell.row + 1][cell.column + 1],
          corners[cell.row + 1][cell.column],
        ];
        const points = ring.map(project).map(([x, y]) => `${x.toFixed(3)},${y.toFixed(3)}`).join(" ");
        const sar = Number.isFinite(cell.sar_log_ratio_db) ? cell.sar_log_ratio_db : "";
        const water = Number.isFinite(cell.water_fraction_change_after_minus_before)
          ? cell.water_fraction_change_after_minus_before : "";
        const title = `SAR cell ${cell.row}, ${cell.column} · common WTR support ${Number(cell.common_valid_wtr_area_fraction * 100).toFixed(1)}% · Δγ⁰ ${sar === "" ? "unavailable" : `${Number(sar).toFixed(3)} dB`} · DSWx water-fraction change ${water === "" ? "unavailable" : Number(water).toFixed(3)}`;
        return `<polygon class="challenge-spatial-cell" points="${points}" data-row="${cell.row}" data-column="${cell.column}" data-valid="${cell.sar_measurement_valid}" data-support="${cell.common_valid_wtr_area_fraction}" data-sar="${sar}" data-water="${water}"><title>${escape(title)}</title></polygon>`;
      }).join("");
      spatialMarkup = `<details class="challenge-spatial-visualization"><summary>SPATIAL VIEW · SAR RESPONSE AND OPTICAL CONTEXT</summary><p>Native WGS84 cell corners from the linked pair record. Both views use cells with a valid SAR response, common optical support at or above the selected cutoff, and a measured water-fraction difference. The Sentinel-1-derived OPERA response and NASA OPERA DSWx-HLS context are descriptive; their spatial association does not establish cause or a flood boundary.</p><div class="challenge-spatial-controls"><label>Displayed measurement<select data-spatial-layer><option value="sar">SAR signed γ⁰ log ratio · dB</option><option value="water">DSWx-HLS water-fraction change</option></select></label><label>Minimum common WTR support <output data-spatial-threshold-value>50%</output><input data-spatial-threshold type="range" min="50" max="95" step="5" value="50"></label></div><small>WGS84 raster-grid extent · longitude ${west.toFixed(5)}° to ${east.toFixed(5)}° · latitude ${south.toFixed(5)}° to ${north.toFixed(5)}°</small><div class="challenge-spatial-frame"><svg data-spatial-map viewBox="0 0 760 430" role="img" aria-label="Geolocated SAR response and optical water-fraction changes on common spatial support">${cells}</svg></div><div class="challenge-spatial-readout" data-spatial-readout role="status" aria-live="polite"></div><div class="challenge-spatial-legend"><span class="negative">NEGATIVE CHANGE</span><span class="neutral">ZERO</span><span class="positive">POSITIVE CHANGE</span><small data-spatial-legend-note>Display stretch is visual only.</small></div><button type="button" class="challenge-open-workspace-map" data-show-challenge-map>SHOW THIS DIAGNOSTIC LAYER ON THE GEOGRAPHIC WORKSPACE</button><small>Pair record SHA-256 · ${escape(map.pair_record_sha256)}<br>Optical context SHA-256 · ${escape(map.optical_context_record_sha256)}<br>${escape(map.interpretation_limit)}</small></details>`;
    }
    const limits = (item.interpretation_limits || []).map((limit) => `<li>${escape(limit)}</li>`).join("");
    return `<details class="challenge-sensitivity-result"><summary>${escape(item.result_kind.replaceAll("_", " "))}</summary><p><b>Source status</b> · ${escape(item.source_status)} · <b>Scope</b> · ${escape(item.scope)}</p>${sourceButton(item, "INSPECT RETAINED SOURCE RECORD")}${metrics}${spatialMarkup}<small>${escape(item.summary_basis.replaceAll("_", " "))} · record SHA-256 ${escape(item.sha256)}</small>${limits ? `<h4>Interpretation limits</h4><ul>${limits}</ul>` : ""}</details>`;
  }).join("");
  const sensitivityMarkup = sources.length
    ? `<p>Linked records are checksum and lineage checked. Recorded summaries are reproduced where supported; the optical-support sweep is calculated from retained per-cell measurements. Metrics remain separate and are not combined into a common score.</p><ul>${sources.map((item) => `<li>${sourceButton(item)} <b>${escape(item.role.replaceAll("_", " "))} · ${escape(item.source_status.replaceAll("_", " "))}</b><small>${escape(item.record_type)} · SHA-256 ${escape(item.sha256)}</small></li>`).join("")}</ul>${sensitivityResultMarkup}`
    : `<p>No sensitivity source is linked to this explanation. The requested variation cannot be evaluated from the retained assessment.</p>`;
  const temporalBaseline = record.temporal_baseline_review || {};
  const temporalComparisons = [
    ...(temporalBaseline.adjacent_intervals || []).map((item, index) => ({ ...item, comparison_type: "ADJACENT ACQUISITION STEP", comparison_key: `adjacent:${index}` })),
    ...(temporalBaseline.reference_baseline?.comparisons || []).map((item, index) => ({ ...item, comparison_type: "FIRST-ACQUISITION BASELINE", comparison_key: `baseline:${index}` })),
  ];
  const temporalRows = temporalComparisons.map((item) => {
    const summary = item.summary_db || {};
    const median = Number.isFinite(summary.median) ? `${summary.median.toFixed(3)} dB` : "unavailable";
    const mean = Number.isFinite(summary.mean) ? `${summary.mean.toFixed(3)} dB` : "unavailable";
    const mapAction = temporalBaseline.status === "REPRODUCED_DIAGNOSTIC_BASELINE_SENSITIVITY"
      ? `<button type="button" data-show-temporal-series data-comparison-key="${escape(item.comparison_key)}" data-series-sha256="${escape(temporalBaseline.sha256)}" data-before-utc="${escape(item.before_acquisition_start_utc)}" data-after-utc="${escape(item.after_acquisition_start_utc)}">SHOW ON MAP</button>`
      : "—";
    return `<tr><td>${escape(item.comparison_type)}</td><td>${escape(item.before_acquisition_start_utc)} → ${escape(item.after_acquisition_start_utc)}</td><td>${escape(Number(item.interval_days).toFixed(1))} d</td><td>${escape(item.measured_pixel_count)}</td><td>${escape(mean)} / ${escape(median)}</td><td>${mapAction}</td></tr>`;
  }).join("");
  const gridOffset = temporalBaseline.grid_offset_sensitivity || {};
  const gridOffsetComparisons = (gridOffset.comparisons || []).map((item) => {
    const range = item.shifted_median_range_db;
    const support = item.matched_support_pixel_count_range;
    const variants = (item.variants || []).map((variant) => `<tr><td>${escape(variant.row_offset_cells)}, ${escape(variant.column_offset_cells)}</td><td>${escape(variant.east_offset_m.toFixed(1))}, ${escape(variant.north_offset_m.toFixed(1))} m</td><td>${escape(variant.matched_pixel_count)}</td><td>${Number.isFinite(variant.unshifted_control_median_db) ? `${variant.unshifted_control_median_db.toFixed(3)} dB` : "—"}</td><td>${Number.isFinite(variant.shifted_median_db) ? `${variant.shifted_median_db.toFixed(3)} dB` : "—"}</td><td>${escape(variant.positive_pixel_count ?? "—")} / ${escape(variant.negative_pixel_count ?? "—")} / ${escape(variant.zero_pixel_count ?? "—")}</td><td>${Number.isFinite(variant.median_difference_from_matched_control_db) ? `${variant.median_difference_from_matched_control_db.toFixed(3)} dB` : "—"}</td></tr>`).join("");
    return `<details class="challenge-grid-offset-comparison"><summary>${escape(item.comparison_kind.replaceAll("_", " "))} · ${escape(Number(item.interval_days).toFixed(1))} d · nominal median ${escape(Number(item.nominal_median_db).toFixed(3))} dB · offset medians ${range ? `${escape(range[0].toFixed(3))} to ${escape(range[1].toFixed(3))} dB` : "unavailable"} · median sign ${escape(item.same_median_sign_as_nominal_count)}/${escape(item.evaluable_offset_count)} offsets · support ${support ? `${escape(support[0])}–${escape(support[1])}` : "unavailable"}</summary><div class="table-scroll"><table><thead><tr><th>Row, column offset</th><th>East, north displacement</th><th>Matched cells</th><th>Unshifted control median</th><th>Offset median</th><th>Positive / negative / zero cells</th><th>Offset minus matched control</th></tr></thead><tbody>${variants}</tbody></table></div></details>`;
  }).join("");
  const gridOffsetMarkup = gridOffset.status === "REPRODUCED_DIAGNOSTIC_ONE_CELL_RELATIVE_OFFSET_STRESS_TEST"
    ? `<details class="challenge-grid-offset-sensitivity"><summary>ONE-CELL GRID-OFFSET STRESS TEST · DIAGNOSTIC</summary><p>ECHO shifted each after observation by one native grid cell in eight directions, without resampling or wraparound. Each offset is compared with its unshifted control on that same matched valid support. This reveals sensitivity to this specified perturbation only.</p>${gridOffsetComparisons}<p>${escape(gridOffset.interpretation_limit)}</p></details>`
    : `<details class="challenge-grid-offset-sensitivity"><summary>GRID-OFFSET STRESS TEST · UNAVAILABLE</summary><p>${escape(gridOffset.interpretation_limit || "No compatible retained series supports this calculation.")}</p></details>`;
  const temporalBaselineMarkup = temporalBaseline.status === "REPRODUCED_DIAGNOSTIC_BASELINE_SENSITIVITY"
    ? `<section class="challenge-temporal-baseline"><b>TEMPORAL BASELINE CHECK · DIAGNOSTIC</b><p>${escape(temporalBaseline.observation_count)} acquisitions · ${escape(temporalBaseline.common_support_count)} of ${escape(temporalBaseline.aoi_pixel_count)} AOI cells marked valid by every acquisition's retained product mask. Each comparison below was recomputed from the linked observations and masks.</p><div class="table-scroll"><table><thead><tr><th>COMPARISON</th><th>ACQUISITIONS</th><th>INTERVAL</th><th>COMMON CELLS</th><th>MEAN / MEDIAN</th><th>MAP</th></tr></thead><tbody>${temporalRows}</tbody></table></div>${gridOffsetMarkup}${sourceButton({ evidence_id: temporalBaseline.evidence_id }, "INSPECT CHECKSUM-LINKED TEMPORAL SERIES")}<small>SHA-256 ${escape(temporalBaseline.sha256)} · ${escape(temporalBaseline.method)}</small><p>${escape(temporalBaseline.interpretation_limit)}</p></section>`
    : `<section class="challenge-temporal-baseline"><b>TEMPORAL BASELINE CHECK · UNAVAILABLE</b><p>${escape(temporalBaseline.reason || "No validated multi-acquisition series is linked to this assessment.")}</p><small>${escape(temporalBaseline.interpretation_limit || "No alternative baseline was calculated or inferred.")}</small>${gridOffsetMarkup}</section>`;
  const alternatives = (record.alternatives || []).map((item) =>
    `<details><summary>${escape(item.recorded_state)} · ${escape(item.statement)}</summary><p>TESTABILITY · ${escape(item.testability_state)}</p><p>WOULD WEAKEN IF · ${escape(item.would_weaken_if)}</p><p>REQUIRED · ${escape((item.required_evidence || []).join(" · "))}</p></details>`
  ).join("") || "<p>No competing hypothesis is recorded in this assessment.</p>";
  const missing = (finding.required_evidence || []).map((item) => `<li>${escape(item)}</li>`).join("");
  const unassessed = record.evidence_review?.unassessed_referenced_evidence_ids || [];
  const followUps = (record.next_observations || []).map((item) =>
    `<article><b>${escape(item.follow_up_id)} · ${escape(item.availability_state.replaceAll("_", " "))}</b>${item.action_track ? `<small>ACTION TRACK · ${escape(item.action_track.replaceAll("_", " "))}</small>` : ""}${item.purpose ? `<small>PURPOSE · ${escape(item.purpose.replaceAll("_", " "))}</small>` : ""}<p>${escape(item.action)}</p>${item.priority_reason ? `<p class="follow-up-priority-reason"><b>WHY THIS NEXT STEP</b> · ${escape(item.priority_reason)}</p>` : ""}<small>QUESTION · ${escape(item.discriminating_question)}</small><div class="adversarial-followup-sources"><b>LINKED RECORDS</b>${(item.evidence_refs || []).map((id) => sourceButton({evidence_id:id}, `INSPECT ${id}`)).join("") || `<small>No linked evidence records are listed for this follow-up.</small>`}</div>${item.test_design ? `<details><summary>PRE-REGISTERED TEST AND GATES</summary><p>EXPECTED · ${escape(item.test_design.expected_observation)}</p><p>WOULD WEAKEN · ${escape(item.test_design.would_weaken_if)}</p><p>INCONCLUSIVE IF · ${escape(item.test_design.inconclusive_if)}</p><ul>${(item.test_design.acceptance_gates || []).map((gate) => `<li>${escape(gate)}</li>`).join("")}</ul></details>` : ""}</article>`
  ).join("") || "<p>No hypothesis-targeted follow-up is recorded.</p>";
  const qa = record.observation || {};
  const measurement = qa.measurement || {};
  const measuredSummary = measurement.quantity
    ? `${measurement.sensor || "SAR observation"} · ${measurement.polarization || "polarization not recorded"} · ${measurement.acquisition_before_utc || "before time not recorded"} → ${measurement.acquisition_after_utc || "after time not recorded"} · mean ${Number.isFinite(measurement.mean_db) ? `${measurement.mean_db.toFixed(3)} dB` : "not recorded"} · median ${Number.isFinite(measurement.median_db) ? `${measurement.median_db.toFixed(3)} dB` : "not recorded"} · common support ${measurement.common_clear_pixel_count ?? "not recorded"}/${measurement.aoi_pixel_count ?? "not recorded"} cells`
    : "No two-acquisition measurement is recorded for this assessment.";
  const reproduction = record.observation?.measurement_reproduction;
  const reproductionMarkup = reproduction
    ? `<p class="measurement-reproduction"><b>SAR MEASUREMENT REPRODUCTION</b> · ${escape(reproduction.status.replaceAll("_", " "))} · ${escape(reproduction.valid_sample_count)} valid cells · recomputed mean ${Number.isFinite(reproduction.mean_db) ? `${reproduction.mean_db.toFixed(3)} dB` : "not recorded"} · median ${Number.isFinite(reproduction.median_db) ? `${reproduction.median_db.toFixed(3)} dB` : "not recorded"}</p>`
    : `<p class="measurement-reproduction">No linked pair measurement was available for numerical reproduction.</p>`;
  return `<section class="adversarial-challenge"><div class="eyebrow">CHALLENGE REVIEW <span>·</span> ${escape(record.status.replaceAll("_", " "))}</div><h2>${escape(finding.statement)}</h2><div class="adversarial-verdict"><b>RECORDED STATE · ${escape(finding.recorded_state.replaceAll("_", " "))}</b><span>Testability · ${escape(finding.testability_state.replaceAll("_", " "))}</span><p>${escape(finding.testability_reason)}</p></div><details open><summary>1 · LINKED MEASUREMENT, INFERENCE, AND QUALITY GATE</summary><p><b>CASE SAR MEASUREMENT</b> · ${escape(measuredSummary)}</p>${reproductionMarkup}${qa.measurement_evidence_id ? sourceButton({evidence_id:qa.measurement_evidence_id}, "INSPECT LINKED SAR MEASUREMENT") : ""}<p><b>INFERENCE UNDER REVIEW</b> · ${escape(finding.statement)}</p><p><b>WHAT COULD WEAKEN IT</b> · ${escape(finding.would_weaken_if)}</p><p><b>MEASUREMENT QA</b> · ${escape(qa.provider_qa_state.replaceAll("_", " "))} · ${escape(qa.qa_gate.replaceAll("_", " "))}</p><p>${escape(qa.interpretation_limit)}</p><small>Assessment SHA-256 · ${escape(record.assessment_sha256)}</small></details><details><summary>2 · EVIDENCE RECORDED AGAINST OR LIMITING IT</summary><h3>CONTRADICTORY</h3>${relationGroup(evidence, "CONTRADICTS", "contradictory", "Analyst-assessed relationship; not independently verified here")}<h3>LIMITS INTERPRETATION</h3>${relationGroup(evidence, "LIMITS_INTERPRETATION", "interpretation-limiting", "Source limitation recorded in the assessment")}<h3>DOES NOT DISTINGUISH</h3>${relationGroup(evidence, "DOES_NOT_DISTINGUISH", "non-distinguishing", "Does not discriminate between this and competing explanations")}</details><details><summary>3 · COMPARABILITY AND SENSITIVITY</summary>${comparabilityMarkup}<section class="challenge-sensitivity"><b>SENSITIVITY STATUS · ${escape(record.sensitivity_review?.state.replaceAll("_", " "))}</b>${sensitivityMarkup}${temporalBaselineMarkup}<p>${escape(record.sensitivity_review?.interpretation_limit)}</p></section></details><details><summary>4 · OTHER RECORDED EXPLANATIONS · ${record.alternatives?.length || 0}</summary>${alternatives}</details><details><summary>5 · MISSING EVIDENCE AND NEXT OBSERVATIONS</summary><b>REQUIRED BY THIS HYPOTHESIS</b><ul>${missing || "<li>No requirements recorded.</li>"}</ul><b>REFERENCED BUT NOT RELATIONSHIP-ASSESSED</b><ul>${unassessed.map((id) => `<li>${sourceButton({evidence_id:id})}</li>`).join("") || "<li>None recorded; this does not establish that the evidence set is complete.</li>"}</ul><div class="adversarial-followups">${followUps}</div></details><p class="adversarial-limit">${escape(record.evidence_review?.relationship_limit)} ${escape(record.interpretation_limit)}</p></section>`;
};

window.renderDraftAdversarialChallenge = function renderDraftAdversarialChallenge(record) {
  const escape = (value) => String(value ?? "—").replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[character]));
  const sourceButton = (item) => `<button type="button" class="investigation-source-link" data-evidence-id="${escape(item.evidence_id)}">${escape(item.evidence_id)}</button>`;
  const finding = record.hypothesis || {};
  const observation = record.observation || {};
  const relationships = record.evidence_review?.recorded_relationships || [];
  const group = (relationship, label) => {
    const rows = relationships.filter((item) => item.relationship === relationship);
    return `<section><h3>${escape(label)} · ${rows.length}</h3>${rows.length
      ? `<ul>${rows.map((item) => `<li>${sourceButton(item)} <b>${escape(item.source_status)} · ${escape(item.role.replaceAll("_", " "))}</b><span>${escape(item.rationale)}</span><small>Unauthenticated analyst relationship · ${escape(item.record_type)} · SHA-256 ${escape(item.sha256)}</small><p>Review basis · ${escape(item.review_basis)}</p><small>Limitation · ${escape(item.limitations)}</small></li>`).join("")}</ul>`
      : `<p>No ${escape(label.toLowerCase())} relationship is recorded. Missing relationships are unassessed, not evidence against the explanation.</p>`}</section>`;
  };
  const unassessed = record.evidence_review?.unassessed_sources || [];
  const alternatives = (record.alternatives || []).map((item) => `<details><summary>${escape(item.hypothesis_id)} · ${escape(item.recorded_state.replaceAll("_", " "))}</summary><p>${escape(item.statement)}</p><p>Expected · ${escape(item.expected_observation)}</p><p>Would weaken if · ${escape(item.would_weaken_if)}</p><p>Required · ${escape((item.required_evidence || []).join(" · "))}</p></details>`).join("");
  const followups = (record.next_observations || []).map((item) => `<article><b>${escape(item.follow_up_id)} · ${escape(item.availability_state.replaceAll("_", " "))}</b><p>${escape(item.action)}</p><p>Question · ${escape(item.discriminating_question)}</p><details><summary>REGISTERED TEST AND ACCEPTANCE GATES</summary><p>Expected · ${escape(item.test_design?.expected_observation)}</p><p>Would weaken if · ${escape(item.test_design?.would_weaken_if)}</p><p>Inconclusive if · ${escape(item.test_design?.inconclusive_if)}</p><ul>${(item.test_design?.acceptance_gates || []).map((gate) => `<li>${escape(gate)}</li>`).join("")}</ul></details></article>`).join("");
  return `<section class="adversarial-challenge draft-adversarial-challenge"><div class="eyebrow">CHALLENGE REVIEW · UNVERIFIED DRAFT</div><h2>${escape(finding.statement)}</h2><section><h3>1 · SOURCE OBSERVATION</h3><p>${sourceButton(observation)} · ${escape(observation.record_type)} · ${escape(observation.role.replaceAll("_", " "))} · ${escape(observation.source_status)}</p><p>Measurement fields recorded · ${escape((observation.measurement_fields_recorded || []).join(" · ") || "none identified in the source record")}</p><small>Source SHA-256 ${escape(observation.sha256)} · measurement values not recomputed in this challenge view</small><p>The source's status and provider QA are not upgraded by this review. Inspect the exact source record for its measurements, acquisition details, QA, and processing context.</p></section><section><h3>2 · INFERENCE UNDER REVIEW</h3><p>${escape(finding.statement)}</p><p>Recorded disposition · ${escape(finding.recorded_state.replaceAll("_", " "))} · testability ${escape(finding.testability_state.replaceAll("_", " "))}</p><p>Scope · ${escape(finding.scope_limit)}</p><p>Expected · ${escape(finding.expected_observation)}</p><p>Would weaken if · ${escape(finding.would_weaken_if)}</p><ul>${(finding.required_evidence || []).map((item) => `<li>${escape(item)}</li>`).join("")}</ul></section><details open><summary>3 · EVIDENCE RELATIONSHIPS</summary>${group("CONTRADICTS", "Contradictory")}${group("LIMITS_INTERPRETATION", "Limits interpretation")}${group("DOES_NOT_DISTINGUISH", "Does not distinguish")}${group("SUPPORTS", "Supportive")}</details><details><summary>4 · SOURCES WITHOUT A RECORDED RELATIONSHIP · ${unassessed.length}</summary><p>These records have no relationship recorded for the selected explanation. Their relevance has not been assessed.</p><ul>${unassessed.map((item) => `<li>${sourceButton(item)} · ${escape(item.role.replaceAll("_", " "))} · ${escape(item.source_status)} · ${escape(item.record_type)} · SHA-256 ${escape(item.sha256)}</li>`).join("") || "<li>None in this draft; this does not establish that the source set is complete.</li>"}</ul></details><details><summary>5 · COMPETING EXPLANATIONS · ${record.alternatives?.length || 0}</summary>${alternatives || "<p>No competing explanation is recorded.</p>"}</details><details><summary>6 · REGISTERED NEXT OBSERVATIONS · ${record.next_observations?.length || 0}</summary>${followups || "<p>No follow-up targets this explanation.</p>"}</details><section><h3>SENSITIVITY AND REPRODUCTION</h3><p>${escape(record.sensitivity_review?.interpretation_limit)}</p></section><p class="adversarial-limit">${escape(record.evidence_review?.relationship_limit)} ${escape(record.interpretation_limit)}</p><small>Draft SHA-256 · ${escape(record.draft_sha256)}</small></section>`;
};

window.bindAdversarialChallengeInteractions = function bindAdversarialChallengeInteractions(container) {
  for (const panel of container.querySelectorAll(".challenge-spatial-visualization")) {
    const slider = panel.querySelector("[data-spatial-threshold]");
    const output = panel.querySelector("[data-spatial-threshold-value]");
    const layer = panel.querySelector("[data-spatial-layer]");
    const readout = panel.querySelector("[data-spatial-readout]");
    const legend = panel.querySelector("[data-spatial-legend-note]");
    const cells = [...panel.querySelectorAll(".challenge-spatial-cell")];
    const mix = (from, to, amount) => from.map((channel, index) => Math.round(channel + (to[index] - channel) * amount));
    const color = (value, scale) => {
      if (!Number.isFinite(value)) return "#7b8586";
      const strength = Math.min(1, Math.abs(value) / Math.max(scale, 1e-9));
      const base = value < 0 ? [81, 139, 190] : [210, 120, 76];
      return `rgb(${mix([177, 184, 181], base, strength).join(",")})`;
    };
    const update = () => {
      const threshold = Number(slider.value) / 100;
      const measurement = layer.value;
      output.textContent = `${slider.value}%`;
      const eligible = cells.filter((cell) => cell.dataset.valid === "true"
        && Number(cell.dataset.support) >= threshold && cell.dataset.water !== "");
      const values = eligible.map((cell) => Number(cell.dataset[measurement]))
        .filter(Number.isFinite);
      const absoluteValues = values.map(Math.abs).sort((a, b) => a - b);
      const scale = measurement === "water" ? 1
        : Math.max(0.1, absoluteValues[Math.min(absoluteValues.length - 1, Math.floor((absoluteValues.length - 1) * 0.98))] || 0.1);
      for (const cell of cells) {
        const value = cell.dataset[measurement] === "" ? NaN : Number(cell.dataset[measurement]);
        const visible = cell.dataset.valid === "true" && Number(cell.dataset.support) >= threshold
          && cell.dataset.water !== "" && Number.isFinite(value);
        cell.style.display = visible ? "" : "none";
        if (visible) cell.setAttribute("fill", color(value, scale));
      }
      panel.querySelector("[data-spatial-map]").setAttribute(
        "aria-label",
        `${measurement === "sar" ? "Signed SAR gamma-zero log-ratio" : "NASA OPERA DSWx-HLS water-fraction change"}; ${eligible.length} cells at ${slider.value}% minimum common optical support. WGS84 cell grid; diagnostic only.`,
      );
      readout.textContent = `${eligible.length.toLocaleString()} common-support SAR cells shown · ${cells.length.toLocaleString()} cells in retained window · ${measurement === "sar" ? "signed SAR log-ratio" : "optical water-fraction change"}`;
      legend.textContent = measurement === "sar"
        ? `Color stretch ±${scale.toFixed(2)} dB · display only; blue = lower response, orange = higher response.`
        : "Fixed water-fraction scale −1 to +1 · blue = lower classified water fraction, orange = higher fraction.";
    };
    slider.addEventListener("input", update);
    layer.addEventListener("change", update);
    update();
  }
};
