(() => {
  const escape = (value) => String(value ?? "—").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
  const status = document.querySelector("#aiInvestigatorStatus");
  const resultNode = document.querySelector("#aiInvestigatorResult");
  const buttons = [...document.querySelectorAll("[data-ai-action]")];
  if (!status || !resultNode || !buttons.length) return;
  const actionLabel = (value) => ({
    INVESTIGATE_OBSERVATION: "INVESTIGATION", CHALLENGE_EXPLANATION: "CHALLENGE",
    MISSING_EVIDENCE: "EVIDENCE GAP REVIEW", NEXT_INSPECTION: "NEXT INSPECTION",
  }[value] || value);
  const readableCheck = (value) => String(value ?? "").replaceAll("_", " ").toLowerCase()
    .replace(/\b(nasa|nisar|qa|asf|hls|sar|gpm|smap|gibs|gcov|rtc)\b/gi, (word) => word.toUpperCase())
    .replace(/^\s*\w/, (first) => first.toUpperCase());
  const cited = (ids) => `<small class="ai-citations">ECHO RECORDS · ${Array.isArray(ids) && ids.length ? ids.map((id) => `<button type="button" class="ai-source-link" data-ai-evidence-id="${escape(id)}">${escape(id)}</button>`).join(" · ") : "No source citation returned"}</small>`;
  const statement = (item) => `<li>${escape(item.text)}${cited(item.evidence_ids)}</li>`;
  function render(record) {
    const result = record.result;
    const ovi = result.observed_vs_inferred;
    const hypotheses = result.hypotheses.map((item) => {
      const retained = item.state_authorship === "ECHO_RETAINED_CASE_ASSESSMENT";
      const unavailable = item.unavailable_evidence.length
        ? `<small>AI-SUGGESTED EVIDENCE GAPS · UNVERIFIED · ${item.unavailable_evidence.map(escape).join(" · ")}</small>`
        : "";
      return `<article><b>${escape(item.hypothesis_id)} · ${escape(retained ? "ECHO RECORDED" : "AI DRAFT")} · ${escape(item.state)} · ${escape(item.label)}</b><p><small>${retained ? "ECHO RETAINED TESTABILITY REASON" : "AI DRAFT EXPLANATION"}</small><br>${escape(item.explanation)}</p><small>RECORDED SUPPORT · ${cited(item.supporting_evidence_ids)}</small><small>RECORDED CONTRADICTION · ${cited(item.contradictory_evidence_ids)}</small><small>DOES NOT DISTINGUISH / LIMITS · ${cited(item.non_discriminating_evidence_ids)}</small>${unavailable}</article>`;
    }).join("");
    const inferred = ovi.inferred.length
      ? `<ul>${ovi.inferred.map(statement).join("")}</ul>${hypotheses}`
      : `<p class="ai-safety-notice">No event interpretation is offered because this case has no accepted pair-change measurement.</p>${hypotheses}`;
    const checks = result.follow_up_checks.map((item) => `<li><b>${escape(readableCheck(item.action))}</b><span>${escape(item.reason)}</span>${cited(item.evidence_ids)}</li>`).join("");
    const safeguardNotes = Array.isArray(record.guardrails_applied) ? [...record.guardrails_applied] : [];
    if (record.citation_method === "AI_RECORD_IDS_VALIDATED_WITH_PRIMARY_CASE_RECORD_FALLBACK") safeguardNotes.push("ECHO attached its retained primary case record where the model returned no citation. The source link identifies context, not proof that the interpretation is correct.");
    const safeguards = safeguardNotes.length ? `<p class="ai-safety-notice">ECHO SAFETY GATE · ${safeguardNotes.map(escape).join(" ")}</p>` : "";
    const observedHeading = record.observations_method === "RETAINED_DETERMINISTIC_CASE_RECORDS" ? "OBSERVED · ECHO RETAINED MEASUREMENTS" : "OBSERVED · AI SUMMARY";
    const nextHeading = record.followup_method === "RETAINED_OPEN_CASE_PLAN" ? "NEXT EVIDENCE · OPEN ECHO CASE PLAN" : "DISCRIMINATING NEXT CHECKS · AI DRAFT";
    resultNode.innerHTML = `<div class="ai-result-meta">AI-GENERATED DRAFT · ${escape(actionLabel(record.action))} · ${escape(record.provider)} / ${escape(record.model)} · ${escape(record.created_at_utc)}</div><p class="ai-result-assessment">${escape(result.assessment.text)}</p>${cited(result.assessment.evidence_ids)}${safeguards}<div class="ai-result-grid"><section><h4>${escape(observedHeading)}</h4><ul>${ovi.observed.map(statement).join("") || "<li>No observation statement returned.</li>"}</ul></section><section><h4>INFERRED · HYPOTHESES</h4>${inferred}</section></div><section><h4>LIMITATIONS</h4><ul>${result.limitations.map(statement).join("") || "<li>None returned.</li>"}</ul></section><section><h4>${escape(nextHeading)}</h4><ul class="ai-followups">${checks || "<li>No follow-up check returned.</li>"}</ul></section><div class="ai-result-footer">${result.insufficient_evidence ? "INSUFFICIENT EVIDENCE · ABSTENTION RECORDED" : "DRAFT INTERPRETATION · NOT A VALIDATED FINDING"}<br>Prompt ${escape(record.prompt_version)} · dossier SHA-256 ${escape(record.dossier_sha256)} · saved locally<br>Local record ID ${escape(record.persistence_id || "not supplied")}<br>${record.limitations.map(escape).join(" ")}</div>`;
    resultNode.hidden = false;
  }
  resultNode.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-ai-evidence-id]");
    if (!button) return;
    button.disabled = true;
    try {
      const sourceUrl = new URL("/api/ai-investigator/source", window.location.origin);
      const selectedCase = new URLSearchParams(window.location.search).get("case_id");
      if (selectedCase) sourceUrl.searchParams.set("case_id", selectedCase);
      sourceUrl.searchParams.set("evidence_id", button.dataset.aiEvidenceId);
      const response = await fetch(sourceUrl, {cache: "no-store"});
      const record = await response.json();
      if (!response.ok) throw new Error(record.error || "Source record could not be opened");
      document.querySelector("#recordJson").textContent = JSON.stringify(record, null, 2);
      document.querySelector("#recordDialog .eyebrow").textContent = `AI CITED SOURCE · ${button.dataset.aiEvidenceId}`;
      document.querySelector("#recordDialog h2").textContent = record.event?.name || record.record_type || record.scene_id || "ECHO evidence record";
      const digest = response.headers.get("X-ECHO-Content-SHA256") || "not supplied";
      const path = response.headers.get("X-ECHO-Source-Path") || "source path not supplied";
      document.querySelector("#recordProvenance").textContent = `SHA-256 ${digest} · ${path}`;
      document.querySelector("#recordScope").innerHTML = "<p class=\"scope-unavailable\">AI citations identify records; they do not prove that the model's interpretation is supported by those records.</p>";
      document.querySelector("#recordDialog").showModal();
    } catch (error) {
      status.textContent = error.message || "Source could not be opened.";
    } finally {
      button.disabled = false;
    }
  });
  buttons.forEach((button) => button.addEventListener("click", async () => {
    if (buttons.some((item) => item.disabled)) return;
    buttons.forEach((item) => { item.disabled = true; });
    resultNode.hidden = true;
    resultNode.replaceChildren();
    status.textContent = "Assembling selected case records and waiting for the local model. No analysis is being sent to an external provider.";
    try {
      const endpoint = new URL("/api/ai-investigator", window.location.origin);
      const selectedCase = new URLSearchParams(window.location.search).get("case_id");
      if (selectedCase) endpoint.searchParams.set("case_id", selectedCase);
      const response = await fetch(endpoint, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({action: button.dataset.aiAction})});
      const record = await response.json();
      if (!response.ok) throw new Error(record.error || `Local investigator failed (${response.status})`);
      render(record);
      status.textContent = `Local model response received · ${record.model}. AI interpretation remains a draft and does not alter case status.`;
    } catch (error) {
      const fetchFailure=error instanceof TypeError&&/fetch|network/i.test(error.message||"");
      status.textContent = fetchFailure
        ? "ECHO's local service could not be reached from this tab. Check that the app is still running at this address, then reload and retry. No AI response was generated."
        : error.message || "No AI response was generated.";
    } finally {
      buttons.forEach((item) => { item.disabled = false; });
    }
  }));
})();
