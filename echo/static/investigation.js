/* Product-independent rendering for the evidence-and-hypothesis workflow. */
window.renderInvestigationReasoning = function renderInvestigationReasoning(record) {
  const escape = (value) => String(value ?? "—").replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[character]));
  const hypotheses = Array.isArray(record.hypotheses) ? record.hypotheses : [];
  const artifacts = Array.isArray(record.evidence_artifacts) ? record.evidence_artifacts : [];
  const followUps = Array.isArray(record.follow_up_evidence) ? record.follow_up_evidence : [];
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
      return `<li><button type="button" class="investigation-source-link" data-evidence-id="${escape(assessment.evidence_id)}">${escape(assessment.evidence_id)}</button><b> · ${escape((assessment.relationship || "").replaceAll("_", " "))}</b><small class="investigation-relation-source">ANALYST-DECLARED FIT · ${escape((assessment.evidence_fit || "UNKNOWN").replaceAll("_", " "))}</small><small class="investigation-relation-source">${escape(sourceRole.replaceAll("_", " "))} · ${sourceStatusLabel}: ${escape(sourceStatus.replaceAll("_", " "))}</small>${caseTrace?`<small>CASE PROVENANCE · ${escape(caseTrace.case_id)} · ${escape(caseTrace.source_evidence_id)} · ${escape(caseTrace.source_relative_path)}</small>`:""}<span>${escape(assessment.rationale)}</span>${assessment.review_basis?`<small>INSPECTION BASIS · ${escape(assessment.review_basis)}</small>`:""}${assessment.limitations?`<small>STATED LIMITS · ${escape(assessment.limitations)}</small>`:""}</li>`;
    }).join("");
    const dependencyMarkup = dependencyLinks.length ? `<details class="hypothesis-evidence-dependencies"><summary>DEPENDENT EVIDENCE · ${dependencyLinks.length} LINK${dependencyLinks.length === 1 ? "" : "S"}</summary><p>These cited records have explicit shared or derived lineage. Their relationships are not independent corroboration. Missing lineage metadata does not prove that other records are independent.</p><ul>${dependencyLinks.map((link) => {
      const reason = link.reason === "SHARED_SOURCE_OBSERVATIONS" ? "Share source observations" : link.reason === "DERIVED_FROM_CITED_EVIDENCE" ? "One record is derived from the other" : `Share recorded derivation input${link.commonInputs.length === 1 ? "" : "s"}: ${link.commonInputs.join(" · ")}`;
      return `<li><button type="button" class="investigation-source-link" data-evidence-id="${escape(link.leftId)}">${escape(link.leftId)}</button><span>↔</span><button type="button" class="investigation-source-link" data-evidence-id="${escape(link.rightId)}">${escape(link.rightId)}</button><small>${escape(reason)}</small></li>`;
    }).join("")}</ul></details>` : "";
    const requirements = (item.required_evidence || []).map((requirement) => `<li>${escape(requirement)}</li>`).join("");
    const challenge = record.record_type === "ECHO_INVESTIGATION_DRAFT" || record.status === "DRAFT_NOT_ASSESSED" ? "" : `<button type="button" class="challenge-hypothesis" data-hypothesis-id="${escape(item.id)}">CHALLENGE THIS EXPLANATION</button>`;
    return `<article class="investigation-hypothesis"><div><b>${escape(item.statement)}</b><span class="investigation-state state-${escape((item.state || "").toLowerCase().replaceAll("_", "-"))}">${escape((item.state || "").replaceAll("_", " "))}</span></div><small class="hypothesis-testability">TESTABILITY · ${escape((item.testability_state || "").replaceAll("_", " "))}</small><p class="hypothesis-reasoning">${escape(explanation)}</p>${dependencyMarkup}${relations ? `<ul class="investigation-relations">${relations}</ul>` : "<p>No relevant evidence is recorded for this explanation.</p>"}<details class="hypothesis-test"><summary>TEST CONDITIONS</summary><div><b>EXPECTED OBSERVATION</b><p>${escape(item.expected_observation)}</p><b>WOULD WEAKEN IF</b><p>${escape(item.would_weaken_if)}</p><b>WHY THIS TESTABILITY STATE</b><p>${escape(item.testability_reason)}</p><b>REQUIRED EVIDENCE</b><ul>${requirements}</ul></div></details><small>SCOPE · ${escape(item.scope_limit || "Not specified")}</small>${challenge}</article>`;
  }).join("");

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
    const actionTrack = item.action_track || (
      item.purpose === "QUALITY_GATE" && ["NOT_SEARCHED", "PROVIDER_RESPONSE_REQUIRED"].includes(item.availability_state)
        ? "QUALITY_PREREQUISITE"
        : item.purpose === "DISCRIMINATING_OBSERVATION" && ["NOT_SEARCHED", "SEARCH_IN_PROGRESS_NO_SUITABLE_SOURCE"].includes(item.availability_state)
          ? "NEW_EVIDENCE_SEARCH"
          : "REVIEWED_RESULT"
    );
    const design = item.test_design;
    const designMarkup = design ? `<details class="followup-test-design"><summary>PRE-REGISTERED TEST DESIGN</summary><div><b>MECHANISM BRANCH</b><p>${escape(design.mechanism_branch)}</p><b>EXPECTED IF PRESENT</b><p>${escape(design.expected_observation)}</p><b>WOULD WEAKEN IF</b><p>${escape(design.would_weaken_if)}</p><b>REMAINS INCONCLUSIVE IF</b><p>${escape(design.inconclusive_if)}</p><b>DATA ACCEPTANCE GATES</b><ul>${(design.acceptance_gates || []).map((gate) => `<li>${escape(gate)}</li>`).join("")}</ul><b>DOES NOT TEST</b><ul>${(design.does_not_test_hypothesis_ids || []).map((id) => `<li>${escape(hypotheses.find((entry) => entry.id === id)?.statement || id)}</li>`).join("")}</ul><b>INTERPRETATION LIMIT</b><p>${escape(design.interpretation_limit)}</p></div></details>` : "";
    const screen = item.screening_review;
    const screenMarkup = screen ? `<details class="followup-screen-record"><summary>ANALYST SCREEN · UNVERIFIED · ${escape(item.availability_state.replaceAll("_", " "))}</summary><p>Gate results were entered by an unauthenticated analyst. They do not independently validate source quality, independence, or hypothesis relevance.</p><button type="button" class="investigation-source-link" data-evidence-id="${escape(screen.source_evidence_id)}">INSPECT ${escape(screen.source_evidence_id)}</button><ul>${screen.gate_results.map((gate) => `<li>${escape(gate.gate)} · ${escape(gate.result)}</li>`).join("")}</ul><b>INSPECTION BASIS</b><p>${escape(screen.review_basis)}</p><b>LIMITATIONS</b><p>${escape(screen.limitations)}</p><small>SCREENED ${escape(screen.screened_at_utc)} · SOURCE SHA-256 ${escape(screen.source_sha256)} · SCREEN RECORD SHA-256 ${escape(screen.sha256)}</small></details>` : "";
    return `<article class="investigation-followup"><div><b>${escape((item.purpose || "").replaceAll("_", " "))}</b><span class="followup-availability">${escape((item.availability_state || "").replaceAll("_", " "))}</span></div><small class="followup-track">WORKSTREAM · ${escape(actionTrack.replaceAll("_", " "))}</small><p>${escape(item.action)}</p><small>TEST · ${escape(item.discriminating_question)}</small><small>IF OBSERVED · ${escape(item.possible_interpretation)}</small><small>TARGET · ${escape(targets)}</small><div class="followup-evidence-records"><small>EVIDENCE RECORDS</small>${refs}</div>${designMarkup}${screenMarkup}<small>WHY NOW · ${escape(item.priority_reason)}</small></article>`;
  }).join("");

  return `<section class="investigation-reasoning"><div class="investigation-hypotheses">${hypothesisMarkup}</div>${sharedMarkup}${lineageMarkup}<div class="investigation-next"><b>NEXT INVESTIGATION WORKSTREAMS</b><p>Quality prerequisites and unresolved evidence searches are shown as separate tracks. The order is not a confidence or value ranking; searching for scientific context can continue while a measurement QA response is pending.</p><div class="investigation-followups">${followUpMarkup}</div></div></section>`;
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
