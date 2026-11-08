/* Product-independent rendering for the evidence-and-hypothesis workflow. */
window.renderInvestigationReasoning = function renderInvestigationReasoning(record) {
  const escape = (value) => String(value ?? "—").replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[character]));
  const hypotheses = Array.isArray(record.hypotheses) ? record.hypotheses : [];
  const artifacts = Array.isArray(record.evidence_artifacts) ? record.evidence_artifacts : [];
  const followUps = Array.isArray(record.follow_up_evidence) ? record.follow_up_evidence : [];
  const hypothesisMarkup = hypotheses.map((item) => {
    const assessments = Array.isArray(item.evidence_assessments) ? item.evidence_assessments : [];
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
    const relations = assessments.map((assessment) =>
      `<li><button type="button" class="investigation-source-link" data-evidence-id="${escape(assessment.evidence_id)}">${escape(assessment.evidence_id)}</button><b> · ${escape((assessment.relationship || "").replaceAll("_", " "))}</b><span>${escape(assessment.rationale)}</span></li>`
    ).join("");
    const requirements = (item.required_evidence || []).map((requirement) => `<li>${escape(requirement)}</li>`).join("");
    return `<article class="investigation-hypothesis"><div><b>${escape(item.statement)}</b><span class="investigation-state state-${escape((item.state || "").toLowerCase().replaceAll("_", "-"))}">${escape((item.state || "").replaceAll("_", " "))}</span></div><small class="hypothesis-testability">TESTABILITY · ${escape((item.testability_state || "").replaceAll("_", " "))}</small><p class="hypothesis-reasoning">${escape(explanation)}</p>${relations ? `<ul class="investigation-relations">${relations}</ul>` : "<p>No relevant evidence is recorded for this explanation.</p>"}<details class="hypothesis-test"><summary>TEST CONDITIONS</summary><div><b>EXPECTED OBSERVATION</b><p>${escape(item.expected_observation)}</p><b>WOULD WEAKEN IF</b><p>${escape(item.would_weaken_if)}</p><b>WHY THIS TESTABILITY STATE</b><p>${escape(item.testability_reason)}</p><b>REQUIRED EVIDENCE</b><ul>${requirements}</ul></div></details><small>SCOPE · ${escape(item.scope_limit || "Not specified")}</small><button type="button" class="challenge-hypothesis" data-hypothesis-id="${escape(item.id)}">CHALLENGE THIS EXPLANATION</button></article>`;
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
  const artifactById = new Map(artifacts.map((artifact) => [artifact.evidence_id, artifact]));
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
    return `<li><button type="button" class="investigation-source-link" data-evidence-id="${escape(artifact.evidence_id)}">${escape(artifact.evidence_id)}</button><b> · ${escape((artifact.role || "EVIDENCE").replaceAll("_", " "))}</b><span>${relationship}</span></li>`;
  }).join("");
  const lineageMarkup = `<details class="investigation-lineage"><summary>EVIDENCE DEPENDENCIES · ${artifacts.length} RECORDS</summary><p>Derived analyses and products sharing source acquisitions are identified so related results are not mistaken for independent corroboration.</p><ul>${lineageRows}</ul></details>`;

  const followUpMarkup = followUps.map((item) => {
    const targets = (item.target_hypothesis_ids || []).map((id) => hypotheses.find((hypothesis) => hypothesis.id === id)?.statement || id).join(" · ");
    const refs = (item.evidence_refs || []).join(" · ") || "No retrieved evidence record";
    const actionTrack = item.action_track || (
      item.purpose === "QUALITY_GATE" && ["NOT_SEARCHED", "PROVIDER_RESPONSE_REQUIRED"].includes(item.availability_state)
        ? "QUALITY_PREREQUISITE"
        : item.purpose === "DISCRIMINATING_OBSERVATION" && item.availability_state === "NOT_SEARCHED"
          ? "NEW_EVIDENCE_SEARCH"
          : "REVIEWED_RESULT"
    );
    const design = item.test_design;
    const designMarkup = design ? `<details class="followup-test-design"><summary>PRE-REGISTERED TEST DESIGN</summary><div><b>MECHANISM BRANCH</b><p>${escape(design.mechanism_branch)}</p><b>EXPECTED IF PRESENT</b><p>${escape(design.expected_observation)}</p><b>WOULD WEAKEN IF</b><p>${escape(design.would_weaken_if)}</p><b>REMAINS INCONCLUSIVE IF</b><p>${escape(design.inconclusive_if)}</p><b>DATA ACCEPTANCE GATES</b><ul>${(design.acceptance_gates || []).map((gate) => `<li>${escape(gate)}</li>`).join("")}</ul><b>DOES NOT TEST</b><ul>${(design.does_not_test_hypothesis_ids || []).map((id) => `<li>${escape(hypotheses.find((entry) => entry.id === id)?.statement || id)}</li>`).join("")}</ul><b>INTERPRETATION LIMIT</b><p>${escape(design.interpretation_limit)}</p></div></details>` : "";
    return `<article class="investigation-followup"><div><b>${escape((item.purpose || "").replaceAll("_", " "))}</b><span class="followup-availability">${escape((item.availability_state || "").replaceAll("_", " "))}</span></div><small class="followup-track">WORKSTREAM · ${escape(actionTrack.replaceAll("_", " "))}</small><p>${escape(item.action)}</p><small>TEST · ${escape(item.discriminating_question)}</small><small>IF OBSERVED · ${escape(item.possible_interpretation)}</small><small>TARGET · ${escape(targets)}</small><small>EVIDENCE RECORDS · ${escape(refs)}</small>${designMarkup}<small>WHY NOW · ${escape(item.priority_reason)}</small></article>`;
  }).join("");

  return `<section class="investigation-reasoning"><div class="investigation-hypotheses">${hypothesisMarkup}</div>${sharedMarkup}${lineageMarkup}<div class="investigation-next"><b>NEXT INVESTIGATION WORKSTREAMS</b><p>Quality prerequisites and unresolved evidence searches are shown as separate tracks. The order is not a confidence or value ranking; searching for scientific context can continue while a measurement QA response is pending.</p><div class="investigation-followups">${followUpMarkup}</div></div></section>`;
};
