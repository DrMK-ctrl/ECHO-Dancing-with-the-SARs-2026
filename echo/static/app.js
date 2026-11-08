const $ = (selector) => document.querySelector(selector);
const svg = $("#footprintMap");
const diagonalLayerByPolarization={HH:"HHHH",HV:"HVHV",VV:"VVVV",VH:"VHVH",RH:"RHRH",RV:"RVRV"};
let catalog;
let review;
let qaReports = {records:[]};
const qaSummaryByScene = new Map();
const qaFeatureByScene = new Map();
let pair;
let selectedSceneId = null;
let zoom = 1;
let mapPan = [0,0];
let toastTimer;
let basemapEnabled = true;
let areaBounds = null;
let areaFocusBounds = null;
let areaPreview = null;
let drawingArea = false;
let areaStart = null;
let mapTransform = null;
let panStart = null;
let suppressMapClick = false;
let gcovPreview = null;
let selectedPreviewPixel = null;
let gcovPairAnalysis = null;
let selectedPairPixel = null;
let pairAnalysisDisplayScale = null;
let operaCatalog = null;
let operaPairAnalysis = null;
let selectedOperaPixel = null;
let dswxContext = null;
let dswxContextVisible = false;
let dswxContextLayer = "WTR";
let dswxContextDate = "before";
let selectedDswxSample = null;
let crossSensorAssessment = null;
let crossSensorAssessmentVisible = false;
let crossSensorAssessmentSha256 = null;
let investigationChallengeNotes = [];
let counterfactualChallengePreview = null;
let counterfactualPreviewGeneration = 0;
let operaDisplayScale = null;
let previewScreenCells = [];
let investigationDraftSource = null;
let investigationDraftRecord = null;

const escapeHTML = (value) => String(value ?? "—").replace(/[&<>"']/g, (char) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[char]));

function openInvestigationDraft(sourceRecord) {
  investigationDraftSource=sourceRecord;
  investigationDraftRecord=null;
  const dialog=$("#investigationDraftDialog"),form=$("#investigationDraftForm");
  form.reset();
  $("#investigationDraftResult").hidden=true;
  $("#investigationDraftResult").innerHTML="";
  $("#draftStatus").textContent=`Source: ${sourceRecord.record_type} · ${sourceRecord.status}. No conclusion will be generated.`;
  $("#createInvestigationDraft").disabled=false;
  $("#createInvestigationDraft").hidden=false;
  $("#createInvestigationDraft").textContent="CREATE UNASSESSED DRAFT";
  form.querySelectorAll("label, fieldset, .dialog-actions, .draft-hypothesis-fields").forEach((item)=>item.hidden=false);
  updateDraftTargetOptions();
  if(!dialog.open)dialog.showModal();
}

function updateDraftTargetOptions() {
  const selector=$("#draftFollowupTarget");
  const prior=selector.value||"H1";
  selector.replaceChildren(...[...document.querySelectorAll(".draft-hypothesis-fields fieldset")].map((fieldset,index)=>{
    const statement=fieldset.querySelector('[data-hypothesis="statement"]').value.trim();
    const option=document.createElement("option");
    option.value=`H${index+1}`;
    option.textContent=`H${index+1} · ${statement||"enter explanation above"}`;
    return option;
  }));
  selector.value=[...selector.options].some((option)=>option.value===prior)?prior:"H1";
}

document.querySelectorAll('.draft-hypothesis-fields [data-hypothesis="statement"]').forEach((field)=>field.addEventListener("input",updateDraftTargetOptions));

function closeInvestigationDraft() {
  const dialog=$("#investigationDraftDialog");
  if(dialog.open)dialog.close();
  investigationDraftSource=null;
}

$("#closeInvestigationDraft").addEventListener("click",closeInvestigationDraft);
$("#openSavedInvestigationDraft").addEventListener("click",()=>$("#draftRestoreFile").click());
$("#draftRestoreFile").addEventListener("change",async(event)=>{
  const file=event.currentTarget.files?.[0];
  if(!file)return;
  const status=$("#draftStatus"),button=$("#openSavedInvestigationDraft");
  button.disabled=true;status.textContent="Checking draft structure, source checksums, and current case links.";
  try{
    const saved=JSON.parse(await file.text());
    const response=await fetch(caseApiURL("/api/investigation-draft/restore"),{
      method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({draft:saved}),
    });
    const record=await response.json();
    if(!response.ok)throw new Error(record.error||"Saved investigation draft could not be restored");
    investigationDraftRecord=record;investigationDraftSource=null;
    const form=$("#investigationDraftForm");form.reset();
    renderInvestigationDraftRecord(record);
    form.querySelectorAll("#draftQuestionLabel, .draft-hypothesis-fields, .draft-next-observation").forEach((item)=>item.hidden=true);
    $("#createInvestigationDraft").hidden=true;
    $("#draftStatus").textContent="Saved draft structure and checksums validated. Case-linked sources were rechecked against the active case. Analyst-authored relationships remain unverified.";
    const dialog=$("#investigationDraftDialog");if(!dialog.open)dialog.showModal();
  }catch(error){status.textContent=error.message;}
  finally{button.disabled=false;event.currentTarget.value="";}
});
$("#investigationDraftForm").addEventListener("submit",async(event)=>{
  event.preventDefault();
  if(!investigationDraftSource)return;
  const fieldsets=[...event.currentTarget.querySelectorAll(".draft-hypothesis-fields fieldset")];
  const hypotheses=fieldsets.map((fieldset)=>Object.fromEntries(
    [...fieldset.querySelectorAll("[data-hypothesis]")].map((field)=>[field.dataset.hypothesis,field.value.trim()]),
  ));
  const nextObservation=Object.fromEntries(
    [...event.currentTarget.querySelectorAll("[data-next]")].map((field)=>[field.dataset.next,field.value.trim()]),
  );
  nextObservation.target_hypothesis_id=$("#draftFollowupTarget").value;
  const button=$("#createInvestigationDraft");
  button.disabled=true;button.textContent="VALIDATING DRAFT…";
  $("#draftStatus").textContent="Checking source status and investigation contract.";
  try{
    const response=await fetch(caseApiURL("/api/investigation-draft"),{
      method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({source_record:investigationDraftSource,source_record_json:JSON.stringify(investigationDraftSource),question:$("#draftQuestion").value,hypotheses,next_observation:nextObservation}),
    });
    const record=await response.json();
    if(!response.ok)throw new Error(record.error||"Investigation draft could not be created");
    investigationDraftRecord=record;
    renderInvestigationDraftRecord(record);
    $("#draftStatus").textContent="Draft created. Hypotheses remain not evaluated and have no evidence relationships.";
    fieldsets.forEach((item)=>item.hidden=true);
    $(".draft-next-observation").hidden=true;
    $("#draftQuestionLabel").hidden=true;
    button.hidden=true;
  }catch(error){
    $("#draftStatus").textContent=error.message;
    button.disabled=false;
  }finally{button.textContent=investigationDraftRecord?"DRAFT CREATED":"CREATE UNASSESSED DRAFT";}
});

function inspectDraftSource(evidenceId) {
  const stored=investigationDraftRecord?.source_records?.[evidenceId];
  if(!stored)return;
  const source=typeof stored==="string"?JSON.parse(stored):stored;
  $("#recordJson").textContent=JSON.stringify(source,null,2);
  $("#recordDialog .eyebrow").textContent=`SOURCE RECORD · ${evidenceId}`;
  $("#recordDialog h2").textContent=`${source.record_type} · ${source.status||"STATUS NOT RECORDED"}`;
  $("#recordDialog").showModal();
}

function renderInvestigationDraftRecord(record) {
  investigationDraftRecord=record;
  const result=$("#investigationDraftResult");
  const sourceCount=Math.max(0,record.evidence_artifacts.length-1);
  const followupScreened=Boolean(record.follow_up_evidence?.[0]?.screening_review);
  const sourceRows=record.evidence_artifacts.map((artifact)=>{const userSource=artifact.ingest_method==="USER_SUPPLIED_LOCAL_JSON_RECORD",caseSource=artifact.ingest_method==="VALIDATED_LOCAL_CASE_ASSESSMENT",caseTrace=artifact.case_provenance;return `<li class="${artifact.source_review_state?"draft-source-unreviewed":""}"><button type="button" class="draft-inspect-source" data-source-id="${escapeHTML(artifact.evidence_id)}">${escapeHTML(artifact.evidence_id)} · INSPECT</button><span>${escapeHTML(artifact.role.replaceAll("_"," "))}</span><small>${escapeHTML(artifact.record_type)} · ${userSource?"USER-DECLARED STATUS · UNVERIFIED":caseSource?"CASE-RETAINED STATUS · PROVIDER NOT REVERIFIED":"RECORD STATUS"} ${escapeHTML(artifact.status)}</small><small>${userSource?`USER SOURCE · UNREVIEWED · INDEPENDENCE ${escapeHTML(artifact.independence_state)}`:caseSource?`ECHO CASE RECORD ${escapeHTML(artifact.source_review_state)} · INDEPENDENCE ${escapeHTML(artifact.independence_state)}`:"Primary SAR pair record"}</small>${caseSource?`<small>CASE ${escapeHTML(caseTrace?.case_id)} · ${escapeHTML(caseTrace?.source_evidence_id)} · ${escapeHTML(caseTrace?.source_relative_path)}</small>`:""}<small>SHA-256 ${escapeHTML(artifact.sha256)}</small></li>`;}).join("");
  const isAssessed=record.status==="DRAFT_ANALYST_ASSESSED_UNVERIFIED";
  const assessmentForm=isAssessed?`<section class="draft-assessment-complete"><h4>ANALYST ASSESSMENT · UNVERIFIED</h4><p>${escapeHTML(record.analyst_assessment?.interpretation_limit||"Analyst-entered relationships are not independently verified.")}</p><small>RECORDED ${escapeHTML(record.analyst_assessment?.reviewed_at_utc||"time unavailable")} · ${record.analyst_assessment?.records?.length||0} RELATIONSHIPS</small></section>`:`<section id="draftAssessmentForm" class="draft-assessment-form"><h4>ASSESS SOURCE RELATIONSHIPS</h4><p>Inspect each cited source first. Record why its content bears on an explanation and what limits that interpretation. ECHO only summarizes your entries; it does not verify the source or claim.</p><div id="draftAssessmentRows"></div><div class="preview-actions"><button type="button" id="addDraftAssessment">ADD RELATIONSHIP</button></div><label class="draft-review-confirm"><input type="checkbox" id="draftReviewedConfirmation" required> I inspected each source I cite and considered its stated quality and limits.</label><button class="primary-button" type="button" id="submitDraftAssessment">RECORD ANALYST ASSESSMENT</button></section>`;
  result.innerHTML=`<h3>${isAssessed?"ANALYST-ASSESSED · UNVERIFIED":"UNASSESSED DRAFT"} · ${escapeHTML(record.status)}</h3><p>${escapeHTML(record.question)}</p><p>${isAssessed?"This provisional record summarizes unauthenticated analyst-entered relationships. It is not a scientifically validated finding.":"Additional source records are staged without hypothesis relationships. Importing a case source verifies its link and integrity against the active case assessment, not the source's fitness for this question."}</p><section class="draft-source-list"><h4>SOURCE RECORDS · ${record.evidence_artifacts.length} TRACEABLE ITEMS</h4><ul>${sourceRows}</ul></section>${window.renderInvestigationReasoning(record)}${assessmentForm}<div class="preview-actions">${!isAssessed?'<button type="button" id="attachDraftSource">STAGE SOURCE JSON</button><button type="button" id="importCaseEvidence">IMPORT CASE EVIDENCE</button>':""}${!isAssessed&&!followupScreened?`<button type="button" id="screenDraftFollowup" ${sourceCount?"":"disabled"}>SCREEN NEXT-OBSERVATION SOURCE</button>`:""}<button type="button" id="downloadDraftRecord">DOWNLOAD DRAFT JSON</button></div><small>${sourceCount} additional source record${sourceCount===1?"":"s"} staged · source fit and independence remain analyst-declared or unassessed</small>`;
  result.hidden=false;
  $("#attachDraftSource")?.addEventListener("click",()=>$("#draftSourceFile").click());
  $("#screenDraftFollowup")?.addEventListener("click",()=>{
    const followup=record.follow_up_evidence[0],gates=followup.test_design.acceptance_gates;
    const sourceOptions=record.evidence_artifacts.slice(1).map(item=>`<option value="${escapeHTML(item.evidence_id)}">${escapeHTML(item.evidence_id)} · ${escapeHTML(item.role.replaceAll("_"," "))} · ${escapeHTML(item.status)}</option>`).join("");
    const gateFields=gates.map((gate,index)=>`<label>${escapeHTML(gate)}<select data-followup-gate="${index}"><option value="UNKNOWN">Unknown</option><option value="MET">Met</option><option value="NOT_MET">Not met</option></select></label>`).join("");
    const panel=document.createElement("section");panel.className="draft-followup-screen";panel.innerHTML=`<h4>SCREEN AGAINST THE PRE-REGISTERED TEST</h4><p>This records an analyst-declared screen of a staged source. It does not independently validate the source or make a hypothesis finding.</p><label>Source record<select id="draftFollowupSource">${sourceOptions}</select></label><div class="draft-followup-gates">${gateFields}</div><label>What source content did you inspect?<textarea id="draftFollowupReviewBasis" rows="2" minlength="12" required></textarea></label><label>What limits this screen?<textarea id="draftFollowupLimitations" rows="2" minlength="12" required></textarea></label><button type="button" id="submitDraftFollowupScreen">RECORD SCREEN · UNVERIFIED</button>`;
    result.insertBefore(panel,result.querySelector(".draft-assessment-form"));
    $("#submitDraftFollowupScreen").addEventListener("click",async(event)=>{
      const submit=event.currentTarget;submit.disabled=true;submit.textContent="VALIDATING GATES…";
      const gate_results=[...panel.querySelectorAll("[data-followup-gate]")].map(field=>({gate:gates[Number(field.dataset.followupGate)],result:field.value}));
      try{
        const response=await fetch(caseApiURL("/api/investigation-draft/screen-followup"),{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({draft:investigationDraftRecord,evidence_id:$("#draftFollowupSource").value,gate_results,review_basis:$("#draftFollowupReviewBasis").value.trim(),limitations:$("#draftFollowupLimitations").value.trim()})});
        const updated=await response.json();if(!response.ok)throw new Error(updated.error||"Follow-up screening could not be recorded");
        renderInvestigationDraftRecord(updated);$("#draftStatus").textContent=`Follow-up screen recorded as ${updated.follow_up_evidence[0].availability_state}. This is analyst-declared; hypothesis states remain unchanged.`;
      }catch(error){$("#draftStatus").textContent=error.message;submit.disabled=false;submit.textContent="RECORD SCREEN · UNVERIFIED";}
    });
  });
  $("#importCaseEvidence")?.addEventListener("click",async()=>{
    const button=$("#importCaseEvidence");button.disabled=true;button.textContent="CHECKING CASE EVIDENCE…";
    try{
      const response=await fetch(caseApiURL("/api/investigation-draft/import-case-evidence"),{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({draft:investigationDraftRecord})});
      const payload=await response.json();if(!response.ok)throw new Error(payload.error||"Case evidence is unavailable");
      if(!payload.options?.length)throw new Error("The validated case has no eligible direct source records. Source independence is not assessed.");
      const options=payload.options.map(item=>`<option value="${escapeHTML(item.evidence_id)}">${escapeHTML(item.evidence_id)} · ${escapeHTML(item.role)} · ${escapeHTML(item.record_type)} · ${escapeHTML(item.status)}</option>`).join("");
      const panel=document.createElement("section");panel.className="draft-case-evidence-options";panel.innerHTML=`<h4>CASE-LINKED SOURCE OPTIONS · ${escapeHTML(payload.case_id)}</h4><p>${escapeHTML(payload.interpretation_limit)}</p><label>Evidence record<select id="draftCaseEvidenceChoice">${options}</select></label><button type="button" id="confirmCaseEvidenceImport">IMPORT SELECTED RECORD</button>`;result.insertBefore(panel,result.querySelector(".draft-assessment-form"));
      $("#confirmCaseEvidenceImport").addEventListener("click",async()=>{
        const importButton=$("#confirmCaseEvidenceImport");importButton.disabled=true;importButton.textContent="VERIFYING AND IMPORTING…";
        try{const imported=await fetch(caseApiURL("/api/investigation-draft/import-case-evidence"),{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({draft:investigationDraftRecord,evidence_id:$("#draftCaseEvidenceChoice").value})});const updated=await imported.json();if(!imported.ok)throw new Error(updated.error||"Evidence import failed");renderInvestigationDraftRecord(updated);$("#draftStatus").textContent="Case source record, case link, and checksums validated. Provider authenticity, source fit, and independence remain unverified.";}
        catch(error){$("#draftStatus").textContent=error.message;importButton.disabled=false;importButton.textContent="IMPORT SELECTED RECORD";}
      });
      button.textContent="CASE RECORDS READY";button.disabled=true;$("#draftStatus").textContent="Case-linked options passed ECHO's assessment and artifact validation and match the exact SAR scenes in this draft.";
    }catch(error){$("#draftStatus").textContent=error.message;button.disabled=false;button.textContent="IMPORT CASE EVIDENCE";}
  });
  $("#downloadDraftRecord").addEventListener("click",()=>downloadJSON(record,"echo-investigation-draft.json"));
  result.querySelectorAll(".draft-inspect-source").forEach((button)=>button.addEventListener("click",()=>inspectDraftSource(button.dataset.sourceId)));
  result.querySelectorAll(".investigation-source-link").forEach((link)=>link.addEventListener("click",()=>inspectDraftSource(link.dataset.evidenceId)));
  if(!isAssessed){
    const rows=$("#draftAssessmentRows");
    const relationOptions=[["SUPPORTS","Supports within stated scope"],["CONTRADICTS","Contradicts within stated scope"],["DOES_NOT_DISTINGUISH","Does not distinguish"],["LIMITS_INTERPRETATION","Limits interpretation"]];
    const addRow=()=>{
      if(rows.children.length>=78){$("#draftStatus").textContent="A single assessment can contain at most 78 relationships.";return;}
      const row=document.createElement("fieldset");row.className="draft-assessment-row";
      row.innerHTML=`<legend>ANALYST RELATIONSHIP ${rows.children.length+1}</legend><label>Hypothesis<select data-assessment="hypothesis_id" required>${record.hypotheses.map(item=>`<option value="${escapeHTML(item.id)}">${escapeHTML(item.id)} · ${escapeHTML(item.statement)}</option>`).join("")}</select></label><label>Inspected source<select data-assessment="evidence_id" required>${record.evidence_artifacts.map(item=>`<option value="${escapeHTML(item.evidence_id)}">${escapeHTML(item.evidence_id)} · ${escapeHTML(item.role.replaceAll("_"," "))} · ${escapeHTML(item.status)}</option>`).join("")}</select></label><label>Analyst-declared fit for this hypothesis<select data-assessment="evidence_fit" required><option value="UNKNOWN">Unknown · do not use directionally</option><option value="SUITABLE_FOR_STATED_SCOPE">Suitable for the stated scope</option><option value="CONTEXT_ONLY">Context only</option><option value="UNSUITABLE">Unsuitable</option></select></label><label>Relationship<select data-assessment="relationship" required>${relationOptions.map(([value,label])=>`<option value="${value}">${label}</option>`).join("")}</select></label><label>Why does this source bear on this hypothesis?<textarea data-assessment="rationale" rows="2" minlength="12" required></textarea></label><label>What did you inspect in the source record?<textarea data-assessment="review_basis" rows="2" minlength="12" required></textarea></label><label>What limits the inference?<textarea data-assessment="limitations" rows="2" minlength="12" required></textarea></label><button type="button" class="text-button remove-draft-assessment">REMOVE RELATIONSHIP</button>`;
      const sourceSelect=row.querySelector('[data-assessment="evidence_id"]'),fitSelect=row.querySelector('[data-assessment="evidence_fit"]'),relationSelect=row.querySelector('[data-assessment="relationship"]');
      const updateAllowedRelations=()=>{const source=record.evidence_artifacts.find(item=>item.evidence_id===sourceSelect.value);const directionalHeld=["SAR_PAIR_HELD_AT_PROVIDER_QA","SAR_PAIR_HELD_AT_PRODUCT_MATURITY","DESCRIPTIVE_NISAR_SAR_MEASUREMENT","DIAGNOSTIC_SENTINEL_1_DERIVED_OPERA_MEASUREMENT","OPERA_PAIR_WITH_NO_COMMON_CLEAR_MEASUREMENT"].includes(source?.role);const directionalAllowed=!directionalHeld&&fitSelect.value==="SUITABLE_FOR_STATED_SCOPE";[...relationSelect.options].forEach(option=>{option.disabled=!directionalAllowed&&["SUPPORTS","CONTRADICTS"].includes(option.value);});if(relationSelect.selectedOptions[0]?.disabled)relationSelect.value="LIMITS_INTERPRETATION";};
      sourceSelect.addEventListener("change",updateAllowedRelations);fitSelect.addEventListener("change",updateAllowedRelations);updateAllowedRelations();
      rows.append(row);row.querySelector(".remove-draft-assessment").addEventListener("click",()=>{row.remove();[...rows.children].forEach((entry,index)=>entry.querySelector("legend").textContent=`ANALYST RELATIONSHIP ${index+1}`);});
    };
    addRow();
    $("#addDraftAssessment").addEventListener("click",addRow);
    $("#submitDraftAssessment").addEventListener("click",async()=>{
      const requiredFields=[...rows.querySelectorAll("[required]"),$("#draftReviewedConfirmation")];
      const invalid=requiredFields.find(field=>!field.checkValidity());if(invalid){invalid.reportValidity();return;}
      const assessments=[...rows.querySelectorAll(".draft-assessment-row")].map((row)=>Object.fromEntries([...row.querySelectorAll("[data-assessment]")].map(field=>[field.dataset.assessment,field.value.trim()])));
      const button=$("#submitDraftAssessment");button.disabled=true;button.textContent="RECORDING…";
      $("#draftStatus").textContent="Validating source references and recording analyst-entered relationships.";
      try{
        const response=await fetch(caseApiURL("/api/investigation-draft/assess"),{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({draft:investigationDraftRecord,assessments})});
        const updated=await response.json();if(!response.ok)throw new Error(updated.error||"Assessment could not be recorded");
        renderInvestigationDraftRecord(updated);$("#draftStatus").textContent="Analyst relationships recorded. Source validation and scientific interpretation remain unverified.";
      }catch(error){$("#draftStatus").textContent=error.message;button.disabled=false;button.textContent="RECORD ANALYST ASSESSMENT";}
    });
  }
}

$("#draftSourceFile").addEventListener("change",async(event)=>{
  const file=event.currentTarget.files?.[0];
  if(!file||!investigationDraftRecord)return;
  event.currentTarget.value="";
  if(file.size>16*1024*1024){$("#draftStatus").textContent="Source JSON exceeds the 16 MiB file limit.";return;}
  $("#draftStatus").textContent="Reading and staging source record without assigning it to a hypothesis.";
  try{
    const sourceRecord=JSON.parse(await file.text());
    const response=await fetch(caseApiURL("/api/investigation-draft/attach-source"),{
      method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({draft:investigationDraftRecord,source_record:sourceRecord}),
    });
    const updated=await response.json();
    if(!response.ok)throw new Error(updated.error||"Source record could not be staged");
    renderInvestigationDraftRecord(updated);
    $("#draftStatus").textContent="Source staged and checksummed. It remains unreviewed, unlinked, and unassessed for independence.";
  }catch(error){$("#draftStatus").textContent=error instanceof SyntaxError?"Selected file is not valid JSON.":error.message;}
});
let activeCaseId = new URLSearchParams(window.location.search).get("case_id") || "";

function caseApiURL(path) {
  const url = new URL(path, window.location.origin);
  if (activeCaseId) url.searchParams.set("case_id", activeCaseId);
  return `${url.pathname}${url.search}`;
}

function populateCaseSelector(registry) {
  const selector = $("#caseSelector");
  const available = Array.isArray(registry.cases) ? registry.cases : [];
  const selected = available.some((item) => item.case_id === activeCaseId)
    ? activeCaseId
    : registry.default_case_id;
  if (!available.some((item) => item.case_id === selected)) {
    throw new Error("No selectable investigation cases are available");
  }
  const selectedCase = available.find((item) => item.case_id === selected);
  $("#openCaseInvestigation").hidden = selectedCase.has_investigation_assessment !== true;
  activeCaseId = selected;
  selector.replaceChildren(...available.map((item) => {
    const option = document.createElement("option");
    option.value = item.case_id;
    option.textContent = `${item.name} · ${item.case_id} · ${item.status_label}`;
    option.selected = item.case_id === selected;
    return option;
  }));
  selector.addEventListener("change", () => {
    const url = new URL(window.location.href);
    url.search = "";
    url.searchParams.set("case_id", selector.value);
    window.location.assign(url.toString());
  });
  if (new URLSearchParams(window.location.search).get("case_id") !== selected) {
    const url = new URL(window.location.href);
    url.searchParams.set("case_id", selected);
    window.history.replaceState(null, "", url.toString());
  }
}

function availablePairs() {
  const candidate = review?.candidate_pair;
  if (candidate?.before?.scene_id && candidate?.after?.scene_id) {
    return [{
      before_scene:candidate.before.scene_id,
      after_scene:candidate.after.scene_id,
      interval_days:candidate.interval_days,
      maturity:catalog?.query?.data_maturity,
      path:candidate.path,
      frame:candidate.frame,
    }];
  }
  return catalog?.metadata_candidate_pairs || [];
}

function selectedPair() {
  return availablePairs()[0] || null;
}

function renderPairSelector() {
  const selector=$("#comparisonPair");
  const choices=availablePairs();
  if(!choices.length){
    selector.innerHTML='<option value="">No metadata-compatible pair</option>';
    selector.disabled=true;
    return;
  }
  selector.disabled=false;
  selector.innerHTML=choices.map((choice,index)=>{
    const before=catalog.features.find((feature)=>feature.properties.fileID===choice.before_scene)?.properties;
    const after=catalog.features.find((feature)=>feature.properties.fileID===choice.after_scene)?.properties;
    const beforeDate=before?.startTime?.slice(0,10)||"date unknown";
    const afterDate=after?.startTime?.slice(0,10)||"date unknown";
    const gap=choice.interval_days ?? (before&&after
      ? (Date.parse(after.startTime)-Date.parse(before.startTime))/86400000
      : null);
    const label=`${beforeDate} → ${afterDate} · ${Number.isFinite(gap)?`${gap.toFixed(1)} d`:`interval unknown`} · path ${choice.path??"?"} / frame ${choice.frame??"?"}`;
    const selected=pair?.before_scene===choice.before_scene&&pair?.after_scene===choice.after_scene;
    return `<option value="${index}"${selected?" selected":""}>${escapeHTML(label)}</option>`;
  }).join("");
}

function reviewProducts() {
  if (Array.isArray(review?.products)) return review.products;
  const candidate = review?.candidate_pair;
  return [candidate?.before,candidate?.after].filter(Boolean).map((scene)=>({
    scene_id:scene.scene_id,
    qa_summary:scene.qa_summary,
    hdf5_identification_metadata:scene.hdf5_identification_metadata,
  }));
}

function providerQAStatus(sceneId) {
  const live=qaSummaryByScene.get(sceneId)?.evidence?.status;
  if(live)return live;
  const reviewed=reviewProducts().find((item)=>item.scene_id===sceneId);
  return reviewed?.qa_summary?.identification_group || (reviewed?.hdf5_identification_metadata ? "REVIEWED · IDENTIFICATION MISMATCH" : "NOT REVIEWED");
}

function investigationGateRecords() {
  const sceneIds=pair?[pair.before_scene,pair.after_scene]:[];
  const qaStatuses=sceneIds.map((sceneId)=>providerQAStatus(sceneId));
  const knownQA=qaStatuses.filter((status)=>status!=="NOT REVIEWED");
  const qaState=!pair||!knownQA.length?"OPEN":
    qaStatuses.every((status)=>status==="PASS")?"PASS":"HOLD";
  const qaDescription=!pair
    ?"No metadata pair is selected"
    :qaStatuses.map((status,index)=>`${index===0?"Before":"After"}: ${status}`).join(" · ");
  const pairAnalysis=gcovPairAnalysis?.status;
  const pairHeld=["QA_HELD","MATURITY_HELD"].includes(pairAnalysis);
  const alignmentState=pairHeld?"BLOCKED":
    pairAnalysis==="MEASURED_DESCRIPTIVE_ONLY"?"MEASURED":"OPEN";
  const alignmentDescription=pairAnalysis==="QA_HELD"
    ?"Provider QA gate stopped execution before pixel windows were read"
    :pairAnalysis==="MATURITY_HELD"
      ?"Product maturity gate stopped execution before pixel windows were read"
      :pairAnalysis==="MEASURED_DESCRIPTIVE_ONLY"
        ?"Pair windows passed the implemented grid and common-validity checks"
        :"No paired pixel comparison has been run";
  const independentCount=Array.isArray(review?.independent_observations)
    ?review.independent_observations.length:0;
  const independentDescription=independentCount
    ?`${independentCount} contextual/reference record${independentCount===1?"":"s"} listed; no independent validation assessment is recorded`
    :"No independent reference assessment is recorded";
  return [
    {name:"Catalog pair",state:pair?"CANDIDATE":"OPEN",description:pair
      ?"Metadata match only; temporal pixel compatibility is not established"
      :"No orbit-separated temporal candidate is selected"},
    {name:"Provider QA",state:qaState,description:qaDescription},
    {name:"Pixel grid and validity",state:alignmentState,description:alignmentDescription},
    {name:"Independent interpretation",state:"NOT EVALUATED",description:independentDescription},
  ];
}

function renderInvestigationGates() {
  const gates=investigationGateRecords();
  const qaGate=gates[1];
  const completed=(pair?1:0)+(qaGate.state==="PASS"?1:0)+(gates[2].state==="MEASURED"?1:0);
  const readinessLabel=qaGate.state==="HOLD"?"QA HOLD":
    qaGate.state==="OPEN"&&pair?"QA NOT REVIEWED":
      gates[2].state==="MEASURED"?"MEASUREMENT RECORDED":"INVESTIGATION INCOMPLETE";
  $(".confidence-block .readiness-value").innerHTML=`${completed} <small>OF 4 GATES · ${readinessLabel}</small>`;
  document.querySelectorAll(".confidence-block .readiness-track i").forEach((item,index)=>{
    item.style.background=index<completed?"var(--cyan)":"#293940";
  });
  $(".confidence-block p").textContent=pair
    ?qaGate.state==="HOLD"
      ?`A metadata candidate exists, but provider QA is not PASS (${qaGate.description}). Pixel alignment and common valid coverage were not evaluated.`
      :qaGate.state==="OPEN"
        ?"A metadata candidate exists. Retrieve provider QA before reading or comparing raster windows."
        :gates[2].state==="MEASURED"
          ?"A descriptive pixel comparison was measured. Independent evidence and physical interpretation remain unevaluated."
          :"The selected pair passed provider QA. Spatial pixel alignment and common valid coverage have not been evaluated."
    :"Catalog discovery is not a scientific comparison. Select a metadata candidate, then inspect its provider QA and pixels.";
  const holdStates=new Set(["HOLD","BLOCKED"]);
  $(".gate-count").textContent=gates.filter((gate)=>holdStates.has(gate.state)).length
    ?`${gates.filter((gate)=>holdStates.has(gate.state)).length} HOLD · ${gates.filter((gate)=>gate.state==="OPEN"||gate.state==="NOT EVALUATED").length} OPEN`
    :`${gates.filter((gate)=>gate.state==="OPEN"||gate.state==="NOT EVALUATED").length} OPEN · ${gates.filter((gate)=>gate.state==="CANDIDATE").length} CANDIDATE`;
  $(".gate-list").innerHTML=gates.map((gate)=>{
    const held=holdStates.has(gate.state);
    const passed=gate.state==="PASS"||gate.state==="MEASURED";
    const icon=held?"!":passed?"✓":gate.state==="CANDIDATE"?"◌":"○";
    const iconClass=held?"review":passed?"pass":"open";
    const stateClass=held?"review":passed?"pass":gate.state==="OPEN"?"open":"candidate";
    return `<li><span class="gate-icon ${iconClass}">${icon}</span><span><b>${escapeHTML(gate.name)}</b><small>${escapeHTML(gate.description)}</small></span><span class="gate-state ${stateClass}">${escapeHTML(gate.state)}</span></li>`;
  }).join("");
}

function renderNextEvidence() {
  const caseItems=Array.isArray(review?.next_evidence_gates)
    ?review.next_evidence_gates.filter((item)=>typeof item==="string"&&item.trim())
    :[];
  let items=caseItems;
  let origin="CASE REVIEW RECORD";
  if(!items.length){
    origin="DERIVED FROM CURRENT GATES";
    const gates=investigationGateRecords();
    const qa=gates[1];
    items=[];
    if(!pair)items.push("Search the selected area and date interval for distinct-orbit observations that match the investigation question.");
    else if(qa.state==="HOLD")items.push("Do not compare this pair while either product QA disposition is not PASS. Seek a provider correction or another QA-cleared pair.");
    else if(qa.state==="OPEN")items.push("Retrieve canonical provider QA summaries for both exact products before reading raster windows.");
    else if(gates[2].state==="OPEN")items.push("Check exact pixel-grid registration, product masks, and common valid coverage before measuring change.");
    if(gates[3].state==="NOT EVALUATED")items.push("Define independent reference evidence and competing explanations before interpreting a measured radar difference.");
  }
  const list=$("#nextEvidenceList");
  list.innerHTML=items.length
    ?items.map((item,index)=>`<li><span>${index+1}</span><p>${escapeHTML(item)}</p></li>`).join("")
    :"<li class=\"empty-evidence\"><p>No additional evidence checks are recorded.</p></li>";
  $("#nextEvidenceOrigin").textContent=origin;
  $("#reviewRecordToggle").hidden=!review;
}

function renderContextSources() {
  const records=Array.isArray(review?.independent_observations)
    ?review.independent_observations.filter((item)=>item&&typeof item==="object"&&!Array.isArray(item))
    :[];
  const panel=$("#contextEvidence");
  if(!records.length){
    panel.innerHTML='<p class="context-empty">No independent or contextual source records are attached to this case review.</p>';
    return;
  }
  panel.innerHTML=records.map((record)=>{
    let sourceLink="";
    try{
      const url=new URL(record.source_url);
      if(url.protocol==="https:"&&url.hostname&&!url.username&&!url.password){
        sourceLink=`<a href="${escapeHTML(url.href)}" target="_blank" rel="noopener noreferrer">Open source ↗</a>`;
      }
    }catch{}
    const details=[
      ["PRODUCT",record.product],
      ["SENSOR",record.sensor],
      ["OBSERVATION DATE",record.observation_date],
      ["ROLE AS RECORDED",record.role],
    ].filter(([,value])=>typeof value==="string"&&value.trim());
    const metadata=details.map(([label,value])=>`<div><dt>${escapeHTML(label)}</dt><dd>${escapeHTML(value)}</dd></div>`).join("");
    return `<article class="context-source"><div class="context-source-head"><b>${escapeHTML(record.provider||"Unspecified provider")}</b><span>CONTEXT · NOT VALIDATION</span></div><dl>${metadata}</dl>${typeof record.limitations==="string"&&record.limitations.trim()?`<p class="context-limitation"><b>LIMITATION</b> · ${escapeHTML(record.limitations)}</p>`:""}${sourceLink}</article>`;
  }).join("");
}

function dswxCodeColor(layer, code) {
  if(layer==="CONF"){
    const colors={0:"#263139",1:"#1767ff",2:"#328dff",3:"#76b2ff",4:"#b5d9ff",10:"#777f84",11:"#2865dd",12:"#5386ed",13:"#7e9df2",14:"#9b8ce2",20:"#48c6cc",21:"#315fd7",22:"#5578e1",23:"#7a8ce8",24:"#8a70cf",254:"#583e75"};
    return colors[code]||"#858585";
  }
  const colors={0:"#34434a",1:"#2588f5",2:"#a6d5f2",252:"#43c8d0",253:"#8e969b",254:"#263f65",255:"transparent"};
  return colors[code]||"#8b8b8b";
}

function dswxCodeLabel(layer, code) {
  if(layer==="CONF"){
    const labels={0:"Not water",1:"Open water · high confidence",2:"Open water · moderate confidence",3:"Partial water · conservative",4:"Partial water · aggressive",10:"Not water · cloud flag",11:"Open water · high confidence · cloud flag",12:"Open water · moderate confidence · cloud flag",13:"Partial water · conservative · cloud flag",14:"Partial water · aggressive · cloud flag",20:"Not water · snow/ice flag",21:"Open water · high confidence · snow/ice flag",22:"Open water · moderate confidence · snow/ice flag",23:"Partial water · conservative · snow/ice flag",24:"Partial water · aggressive · snow/ice flag",254:"Ocean masked"};
    return labels[code]||"Unlisted CONF code";
  }
  const labels={0:"Not water",1:"Open water",2:"Partial surface water",252:"Snow / ice / sediment-rich water",253:"Cloud / cloud shadow",254:"Ocean masked",255:"No data"};
  return labels[code]||"Unlisted class code";
}

function crossSensorAssessmentMatchesCurrentPair() {
  let expected=review?.primary_opera_pair;
  const linkedScenes=crossSensorAssessment?.observations?.sar_diagnostic_measurement?.scene_ids;
  if(crossSensorAssessment){
    if(!Array.isArray(linkedScenes)||linkedScenes.length!==2||linkedScenes.some((sceneId)=>typeof sceneId!=="string"||!sceneId))return false;
    expected={before_scene_id:linkedScenes[0],after_scene_id:linkedScenes[1]};
  }
  if(!expected||!operaPairAnalysis)return true;
  const sources=operaPairAnalysis.source_products||{};
  return sources.before?.scene_id===expected.before_scene_id&&sources.after?.scene_id===expected.after_scene_id;
}

function renderDswxContextInspector() {
  const section=$("#dswxContextInspector");
  if(!dswxContextVisible||!dswxContext){section.hidden=true;section.innerHTML="";return;}
  const role=dswxContextDate;
  const product=dswxContext.source_products[role];
  const sample=selectedDswxSample===null?null:dswxContext.map_samples[selectedDswxSample];
  const sampleDetails=sample
    ?`<p class="preview-pixel-readout"><b>Selected native cell</b> · row ${sample.row}, column ${sample.column} · center ${sample.center_wgs84[0].toFixed(6)}°, ${sample.center_wgs84[1].toFixed(6)}° · ${dswxContextLayer} code ${sample[role][dswxContextLayer]} · ${escapeHTML(dswxCodeLabel(dswxContextLayer,sample[role][dswxContextLayer]))}</p>`
    :"<p>Click a mapped optical cell to inspect its native class code and location.</p>";
  const layerNote=dswxContextLayer==="CONF"
    ?"CONF is NASA's confidence and quality-context layer. Its codes are not a second independent water classification."
    :"This is an OPERA Level-3 optical classification derived from HLS observations; it is not a SAR measurement or field validation.";
  const assessmentMatches=crossSensorAssessmentMatchesCurrentPair();
  const assessmentControl=assessmentMatches
    ?'<button type="button" id="assessDswxEvidence">OPEN EVIDENCE ASSESSMENT</button>'
    :'<button type="button" id="assessDswxEvidence" disabled>ASSESSMENT IS FOR A DIFFERENT SAR PAIR</button>';
  section.hidden=false;
  section.innerHTML=`<h3>NASA OPERA DSWx-HLS · OPTICAL CONTEXT ONLY</h3><p>${escapeHTML(layerNote)} The current acquisition is ${escapeHTML(product.acquisition_time_utc)} UTC (${escapeHTML(product.granule_id)}).</p><dl><div><dt>PROVIDER / PRODUCT</dt><dd>${escapeHTML(product.provider)} · ${escapeHTML(product.mission_product)}<br>${escapeHTML(product.collection_concept_id)} · ${escapeHTML(product.cmr_concept_id||"CMR reference recorded")}</dd></div><div><dt>MAP LAYER</dt><dd>${escapeHTML(dswxContextLayer)} · ${escapeHTML(dswxDateLabel(role))} · native ${escapeHTML(product.assets[dswxContextLayer].grid.crs)}</dd></div><div><dt>PIXEL COUNTS</dt><dd>${product.assets[dswxContextLayer].grid.selected_pixel_center_count.toLocaleString()} AOI centers · ${Object.entries(product.assets[dswxContextLayer].aoi_class_histogram).map(([code,count])=>`${code}: ${count}`).join(" · ")}</dd></div><div class="full"><dt>RETRIEVAL / CHECKSUM</dt><dd>${product.assets[dswxContextLayer].access.bytes.toLocaleString()} bytes · HTTP ${product.assets[dswxContextLayer].access.http_status} · CMR MD5 verified<br>SHA-256 ${escapeHTML(product.assets[dswxContextLayer].access.sha256)}</dd></div><div class="full"><dt>BOUNDARY</dt><dd>Optical context does not validate the OPERA RTC-S1 measurement or establish event extent, cause, or damage.</dd></div></dl>${sampleDetails}<div class="preview-actions">${assessmentControl}<button type="button" id="dswxRecordButton">INSPECT FULL SOURCE RECORD</button><button type="button" id="downloadDswxRecordButton">DOWNLOAD REPRODUCTION RECORD</button></div>`;
  if(assessmentMatches)$("#assessDswxEvidence").addEventListener("click",openCrossSensorAssessment);
  $("#dswxRecordButton").addEventListener("click",()=>{$("#recordJson").textContent=JSON.stringify(dswxContext,null,2);$("#recordDialog .eyebrow").textContent="SOURCE RECORD · NASA OPERA DSWX-HLS";$("#recordDialog h2").textContent="Optical context and processing record";$("#recordDialog").showModal();});
  $("#downloadDswxRecordButton").addEventListener("click",()=>downloadJSON(dswxContext,"echo-nasa-opera-dswx-hls-context.json"));
}

function renderCrossSensorAssessment() {
  const section=$("#investigationAssessment");
  const dialog=$("#investigationDialog");
  if(!crossSensorAssessmentVisible||!crossSensorAssessment){
    if(dialog.open)dialog.close();
    section.innerHTML="";
    return;
  }
  const record=crossSensorAssessment;
  const observations=record.observations;
  const sar=observations.sar_diagnostic_measurement;
  const optical=observations.optical_product_classifications;
  const nearer=observations.nearer_optical_quality_context;
  const spatial=observations.spatial_support_diagnostic;
  const polarization=observations.polarization_sensitivity_diagnostic;
  const gpm=observations.gpm_precipitation_context;
  const timelineRows=[
    {label:"SAR · Sentinel-1 / OPERA RTC-S1",before:sar.acquisition_before_utc,after:sar.acquisition_after_utc,kind:"sar"},
    {label:"NASA optical · OPERA DSWx-HLS",before:optical.before_acquisition_utc,after:optical.after_acquisition_utc,kind:"optical"},
    ...(nearer?[{label:"Nearest optical follow-up · DSWx-HLS",before:nearer.before_acquisition_utc,after:nearer.after_acquisition_utc,kind:"followup"}]:[]),
    ...(observations.hls_l30_vegetation_context?[{label:"NASA/USGS optical · HLS Landsat L30",before:observations.hls_l30_vegetation_context.before_acquisition_utc,after:observations.hls_l30_vegetation_context.after_acquisition_utc,kind:"landsat"}]:[]),
    ...(observations.hls_s30_vegetation_context?[{label:"NASA/USGS optical · HLS Sentinel-2 S30",before:observations.hls_s30_vegetation_context.before_acquisition_utc,after:observations.hls_s30_vegetation_context.after_acquisition_utc,kind:"sentinel2"}]:[]),
  ];
  const timelineEvents=timelineRows.flatMap((row)=>[
    {row,role:"BEFORE",timestamp:row.before},
    {row,role:"AFTER",timestamp:row.after},
  ]).map((event)=>({...event,time:Date.parse(event.timestamp)}));
  const validTimeline=timelineEvents.every((event)=>Number.isFinite(event.time));
  const timeline=validTimeline?(()=>{
    const min=Math.min(...timelineEvents.map((event)=>event.time));
    const max=Math.max(...timelineEvents.map((event)=>event.time));
    const span=Math.max(1,max-min);
    const totalDays=(max-min)/86400000;
    const tracks=timelineRows.map((row)=>{
      const points=timelineEvents.filter((event)=>event.row===row);
      const marks=points.map((event)=>{
        const position=((event.time-min)/span)*100;
        const detail=new Date(event.time).toISOString().replace("T"," ").replace("Z"," UTC");
        return `<span class="investigation-time-point ${row.kind} ${event.role.toLowerCase()}" data-time-position="${position.toFixed(3)}"><i></i><small><b>${event.role}</b>${escapeHTML(detail)}</small></span>`;
      }).join("");
      const interval=((points[1].time-points[0].time)/86400000).toFixed(2);
      return `<div class="investigation-time-row"><b>${escapeHTML(row.label)}</b><div class="investigation-time-track"><span class="investigation-time-line"></span>${marks}</div><small class="investigation-time-interval">Pair interval · ${interval} days</small></div>`;
    }).join("");
    const offsets=observations.relative_acquisition_offsets_days||{};
    const offsetText=Number.isFinite(offsets.optical_before_minus_sar_before)&&Number.isFinite(offsets.optical_after_minus_sar_after)
      ?`Optical minus corresponding SAR acquisition · ${offsets.optical_before_minus_sar_before>=0?"+":""}${offsets.optical_before_minus_sar_before.toFixed(2)} days at the earlier date · ${offsets.optical_after_minus_sar_after>=0?"+":""}${offsets.optical_after_minus_sar_after.toFixed(2)} days at the later date`
      :"Optical-to-SAR offsets are not recorded for this assessment.";
    return `<section class="investigation-timeline" aria-label="Observation acquisition chronology"><div class="investigation-timeline-heading"><b>ACQUISITION CHRONOLOGY</b><span>${totalDays.toFixed(1)} days represented · acquisition times in UTC</span></div>${tracks}<p>${escapeHTML(offsetText)}</p><small>Temporal proximity is shown from acquisition timestamps. This view does not establish pixel alignment, observation equivalence, or causation.</small></section>`;
  })():`<section class="investigation-timeline"><b>ACQUISITION CHRONOLOGY UNAVAILABLE</b><p>One or more linked observation records lack a valid acquisition timestamp.</p></section>`;
  const reasoningMarkup=window.renderInvestigationReasoning(record);
  const nearerCard=nearer?`<article class="investigation-quality-context"><b>NEAREST NASA OPTICAL PAIR · QUALITY LIMITED</b><span>WTR shared valid pixels: ${nearer.wtr_common_valid_count.toLocaleString()} · WTR-2 water classes: ${nearer.wtr2_water_class_counts_before_after[0]} → ${nearer.wtr2_water_class_counts_before_after[1]}</span><small>${nearer.wtr2_cloud_or_snow_flagged_water_before_after[0]} of ${nearer.wtr2_water_class_counts_before_after[0]} earlier WTR-2 water-coded cells have cloud/snow flags · offsets ${nearer.offset_from_rtc_before_days.toFixed(2)} d / ${nearer.offset_from_rtc_after_days.toFixed(2)} d</small></article>`:"";
  const spatial75=spatial?.coverage_sensitivity?.find((item)=>item.minimum_common_valid_wtr_area_fraction===0.75);
  const spatialCard=spatial75?`<article class="investigation-quality-context"><b>NATIVE-GRID COMMON SUPPORT · DIAGNOSTIC</b><span>${spatial75.sar_cells.toLocaleString()} SAR cells with ≥75% common-valid WTR area · ${spatial75.water_fraction_increased_by_more_than_0_05+spatial75.water_fraction_decreased_by_more_than_0_05} cells show >0.05 water-fraction change</span><small>Median water-fraction change ${spatial75.median_water_fraction_change.toFixed(2)} · descriptive Pearson r ${spatial75.descriptive_pearson_r_water_fraction_change_vs_sar_log_ratio_db.toFixed(3)} · no inferential statistic</small><button type="button" id="inspectSpatialSupportRecord">INSPECT CELL-LEVEL EVIDENCE</button></article>`:"";
  const polarizationSummary=polarization?.summary;
  const polarizationCard=polarizationSummary?`<article class="investigation-quality-context"><b>POLARIZATION SENSITIVITY · SAME ACQUISITIONS · DIAGNOSTIC</b><span>${polarizationSummary.common_cells.toLocaleString()} shared cells · water-context correlation VV ${polarizationSummary.vv_pearson_r_water_change_vs_log_ratio.toFixed(3)} · VH ${polarizationSummary.vh_pearson_r_water_change_vs_log_ratio.toFixed(3)}</span><small>VV and VH are related measurements from the same acquisitions and processor, not independent validation. This check does not distinguish the water explanation.</small><button type="button" id="inspectPolarizationRecord">INSPECT SENSITIVITY ANALYSIS</button><button type="button" id="inspectVhPairRecord">INSPECT VH MEASUREMENT RECORD</button><button type="button" id="inspectVhSpatialRecord">INSPECT VH CELL-LEVEL SUPPORT</button></article>`:"";
  const gpmPeriods=gpm?[gpm.before,gpm.after,...(gpm.interacquisition?[gpm.interacquisition]:[])]:[];
  const gpmMaximum=Math.max(1,...gpmPeriods.flatMap((period)=>period.daily_mm_per_day));
  const gpmBars=(period)=>period.daily_mm_per_day.map((value,index)=>{
    const day=new Date(`${period.start_date_utc}T00:00:00Z`);day.setUTCDate(day.getUTCDate()+index);
    const label=day.toISOString().slice(0,10);
    const height=Math.max(2,Math.round((value/gpmMaximum)*38));
    return `<span title="${label}: ${value.toFixed(2)} mm/day · 48/48 samples" aria-label="${label}: ${value.toFixed(2)} millimeters per day" style="height:${height}px"><i></i><small>${label.slice(8)}</small></span>`;
  }).join("");
  const gpmCard=gpm?.before&&gpm?.after?`<article class="investigation-quality-context gpm-context-card"><b>NASA GPM IMERG · REGIONAL PRECIPITATION CONTEXT</b><span>Seven-day estimate at nearest native cell · ${gpm.before.complete_day_sum_mm.toFixed(1)} mm through ${escapeHTML(gpm.before.end_date_utc)} · ${gpm.after.complete_day_sum_mm.toFixed(1)} mm through ${escapeHTML(gpm.after.end_date_utc)}</span><div class="gpm-context-series"><div><small>${escapeHTML(gpm.before.start_date_utc)} — ${escapeHTML(gpm.before.end_date_utc)}</small><div>${gpmBars(gpm.before)}</div></div><div><small>${escapeHTML(gpm.after.start_date_utc)} — ${escapeHTML(gpm.after.end_date_utc)}</small><div>${gpmBars(gpm.after)}</div></div></div><small>Daily mean precipitation estimates · all nearest-cell days have 48/48 samples · native 0.1° grid. This documents regional rainfall context; it does not measure soil moisture or explain the SAR response.</small><button type="button" id="inspectGpmContextRecord">INSPECT GPM SOURCES AND DAILY VALUES</button></article>`:"";
  const gpmInteracquisitionCard=gpm?.interacquisition?`<article class="investigation-quality-context gpm-context-card"><b>BETWEEN ACQUISITIONS · DAILY RAINFALL CHRONOLOGY</b><span>${gpm.interacquisition.complete_days} complete days · ${gpm.interacquisition.complete_day_sum_mm.toFixed(1)} mm total · peak ${gpm.interacquisition.peak_daily_precipitation_mm.toFixed(2)} mm/day on ${escapeHTML(gpm.interacquisition.peak_date_utc)}</span><div class="gpm-context-series"><div><small>${escapeHTML(gpm.interacquisition.start_date_utc)} — ${escapeHTML(gpm.interacquisition.end_date_utc)}</small><div>${gpmBars(gpm.interacquisition)}</div></div></div><small>NASA GPM IMERG Final Daily · nearest native ~0.1° cell · all days have 48/48 samples. Regional rainfall timing can guide follow-up questions; it does not measure AOI soil moisture, validate flood extent, or explain the SAR response.</small><button type="button" id="inspectGpmInteracquisitionRecord">INSPECT INTER-ACQUISITION CHRONOLOGY</button></article>`:"";
  const hydrologic=record.observations.official_hydrologic_event_context;
  const hydrologicCard=hydrologic?`<article class="investigation-quality-context"><b>ANA · GUAÍBA FLOOD-STAGE CHRONOLOGY · NARRATIVE CONTEXT</b><span>${escapeHTML(hydrologic.station_name)} (${escapeHTML(hydrologic.station_code)}) · above flood stage ${escapeHTML(hydrologic.period_local_dates.start_date)} — ${escapeHTML(hydrologic.period_local_dates.end_date)}</span><small>Official agency summary only; no timestamped gauge readings were retrieved. A nearby point gauge does not measure AOI water extent, validate the SAR response, or resolve its cause.</small><button type="button" id="inspectGuaibaHydrologyRecord">INSPECT ANA SOURCE RECORD</button></article>`:"";
  const smapScreen=record.observations.smap_sentinel_soil_moisture_screen;
  const smapScreenCard=smapScreen?`<article class="investigation-quality-context"><b>NASA NSIDC · SMAP / SENTINEL-1 SOIL-MOISTURE CANDIDATE · QA LIMITED</b><span>${smapScreen.paired_quality_eligible_cells} paired 3 km cells passed the declared QA screen · ${escapeHTML(smapScreen.before_granule)} → ${escapeHTML(smapScreen.after_granule)}</span><small>The bounded exact-AOI candidate failed retrieval quality checks. It blends SMAP and Sentinel-1 inputs, so it is not independent SAR validation and is excluded from interpretation.</small><button type="button" id="inspectSmapScreenRecord">INSPECT CANDIDATE AND QA RECORD</button></article>`:"";
  const smapRadiometer=record.observations.smap_radiometer_spatial_suitability_screen;
  const smapRadiometerCard=smapRadiometer?`<article class="investigation-quality-context"><b>NASA SMAP RADIOMETER · INDEPENDENT SOURCE · SCALE SCREEN</b><span>${smapRadiometer.selected_daily_granule_dates.join(" / ")} daily records · AOI ${smapRadiometer.aoi_width_km_approx.toFixed(2)} × ${smapRadiometer.aoi_height_km_approx.toFixed(2)} km · grid posting ${smapRadiometer.grid_posting_km} km</span><small>Radiometer footprint ≈${smapRadiometer.native_radiometer_footprint_km_approx} km; the independent product is too coarse to resolve within-AOI patterns. Metadata only: no soil-moisture pixels were retrieved or tested.</small><button type="button" id="inspectSmapRadiometerRecord">INSPECT CMR COVERAGE AND SCALE SCREEN</button></article>`:"";
  const hls=record.observations.hls_l30_vegetation_context;
  const hlsAssociation=hls?.association_at_75_percent_common_support;
  const hlsCard=hls&&hlsAssociation?`<article class="investigation-quality-context"><b>NASA/USGS HLS LANDSAT · VEGETATION CONTEXT · DESCRIPTIVE</b><span>Common clear-land support ${((hls.common_clear_land_aoi_fraction||0)*100).toFixed(1)}% · median NDVI change ${hls.median_ndvi_change_after_minus_before>=0?"+":""}${hls.median_ndvi_change_after_minus_before.toFixed(3)} · ${hlsAssociation.sar_cells.toLocaleString()} SAR cells at ≥75% optical support</span><small>${escapeHTML(hls.before_platform)} → ${escapeHTML(hls.after_platform)} · Landsat minus SAR offsets ${hls.optical_minus_sar_offsets_hours.map((hours)=>`${hours.toFixed(2)} h`).join(" / ")} · native-grid descriptive Pearson r ${hlsAssociation.descriptive_pearson_r_ndvi_change_vs_sar_log_ratio_db.toFixed(3)}. Limited clear support, spatial dependence, and unresolved RTC-S1 QA mean this association does not distinguish vegetation causality or validate SAR.</small><button type="button" id="inspectHlsScreenRecord">INSPECT LANDSAT OBSERVATION AND PIXEL QA</button><button type="button" id="inspectHlsAssociationRecord">INSPECT SPATIAL ASSOCIATION AND SOURCE LINKS</button></article>`:"";
  const hlsS30=record.observations.hls_s30_vegetation_context;
  const hlsS30Association=hlsS30?.association_at_75_percent_common_support;
  const hlsS30Card=hlsS30&&hlsS30Association?`<article class="investigation-quality-context"><b>NASA/USGS HLS SENTINEL-2 · VEGETATION CONTEXT · INSUFFICIENT SHARED COVERAGE</b><span>${hlsS30.common_clear_land_pixel_count.toLocaleString()} / ${hlsS30.aoi_center_pixel_count.toLocaleString()} common clear-land pixels (${(hlsS30.common_clear_land_aoi_fraction*100).toFixed(2)}%) · ${hlsS30Association.sar_cells.toLocaleString()} SAR cells at ≥75% optical support</span><small>${escapeHTML(hlsS30.before_platform)} → ${escapeHTML(hlsS30.after_platform)} · optical minus SAR offsets ${hlsS30.optical_minus_sar_offsets_hours.map((hours)=>`${hours.toFixed(2)} h`).join(" / ")} · median NDVI change ${hlsS30.median_ndvi_change_after_minus_before>=0?"+":""}${hlsS30.median_ndvi_change_after_minus_before.toFixed(3)} · descriptive r ${hlsS30Association.descriptive_pearson_r_ndvi_change_vs_sar_log_ratio_db.toFixed(3)}. The small, spatially dependent shared sample is nondiscriminating; this optical context does not validate SAR or establish vegetation causality.</small><button type="button" id="inspectHlsS30ScreenRecord">INSPECT SENTINEL-2 OBSERVATIONS AND PIXEL QA</button><button type="button" id="inspectHlsS30AssociationRecord">INSPECT ASSOCIATION AND SOURCE LINKS</button></article>`:"";
  const acquisitionReview=record.observations.acquisition_conditions_metadata_review;
  const acquisitionConditionsCard=acquisitionReview?`<article class="investigation-quality-context"><b>OPERA RTC-S1 ACQUISITION METADATA · NONDISCRIMINATING</b><span>Platform, documented product, processing, and reported geometric-accuracy fields match · RFI burst ratio ${acquisitionReview.rfi_power_ratio_before.toFixed(2)} → ${acquisitionReview.rfi_power_ratio_after.toFixed(2)}</span><small>The burst ratios are not spatially matched to the AOI response; incidence-angle fields are absent, and geometric accuracy values do not establish co-registration. This review does not resolve the acquisition-condition explanation or clear product QA.</small><button type="button" id="inspectAcquisitionConditionsRecord">INSPECT ACQUISITION METADATA COMPARISON</button></article>`:"";
  const modisScreen=record.observations.mod13q1_vegetation_candidate_screen;
  const modisVegetationCard=modisScreen?`<article class="investigation-quality-context"><b>NASA TERRA / MODIS MOD13Q1 · VEGETATION CANDIDATE · INSUFFICIENT ACCEPTED SUPPORT</b><span>${modisScreen.aoi_pixel_center_count} native 250 m AOI pixel centers · ${modisScreen.before_good_summary_qa_count} / ${modisScreen.after_good_summary_qa_count} good-reliability pixels · ${modisScreen.common_strictly_accepted_pixel_count} common pixels pass paired QA and land gates</span><small>Selected per-pixel composite dates ${modisScreen.composite_observation_dates_before.join(", ")} → ${modisScreen.composite_observation_dates_after.join(", ")} · offsets from SAR dates ${modisScreen.composite_observation_offsets_days_min_max[0]} to ${modisScreen.composite_observation_offsets_days_min_max[1]} days. No NDVI change or SAR association is computed; this candidate does not test vegetation causality.</small><button type="button" id="inspectModisVegetationRecord">INSPECT MODIS QA AND COMPOSITE DATES</button></article>`:"";
  const currentChallenges=investigationChallengeNotes.filter((note)=>note.source_assessment.case_id===record.case_id&&note.source_assessment.sha256===crossSensorAssessmentSha256);
  const challengesMarkup=currentChallenges.length?currentChallenges.map((note)=>{
    const preview=note.counterfactual_preview;
    const previewMarkup=preview?`<div class="challenge-counterfactual"><b>COUNTERFACTUAL ONLY · ANALYST-ENTERED RECLASSIFICATION</b><span>${escapeHTML(preview.current_disposition.replaceAll("_"," "))} → ${escapeHTML(preview.counterfactual_disposition.replaceAll("_"," "))}</span><small>${escapeHTML(preview.evidence_id)} · ${escapeHTML(preview.previous_relationship.replaceAll("_"," "))} → ${escapeHTML(preview.proposed_relationship.replaceAll("_"," "))}</small><small>Assessment SHA-256 ${escapeHTML(preview.assessment_sha256)}</small><small>${escapeHTML(preview.interpretation_limit)}</small></div>`:"";
    return `<article class="challenge-note"><div><b>${escapeHTML(note.challenge_type.replaceAll("_"," "))}</b><small>${escapeHTML(note.created_at_utc.replace("T"," ").replace("Z"," UTC"))}</small></div><p><b>EXPLANATION</b> · ${escapeHTML(note.hypothesis.statement)}</p><p>${escapeHTML(note.challenge_statement)}</p><small>RELATED SOURCE · ${escapeHTML(note.related_evidence?.evidence_id||"No retrieved source · information gap")}</small><p><b>PROPOSED TEST</b> · ${escapeHTML(note.proposed_test)}</p>${previewMarkup}<small>UNASSESSED HUMAN REVIEW · does not alter the retained assessment</small></article>`;
  }).join(""):"<p class=\"challenge-empty\">No challenge notes recorded for this assessment in this page session.</p>";
  section.innerHTML=`<h3>INVESTIGATION ASSESSMENT · ${escapeHTML(record.status.replaceAll("_"," "))}</h3><p>${escapeHTML(record.assessment.summary)}</p><div class="investigation-observations"><article><b>DIAGNOSTIC SAR · SENTINEL-1 / OPERA RTC-S1</b><span>${sar.common_clear_pixel_count.toLocaleString()} / ${sar.aoi_pixel_count.toLocaleString()} common-clear cells · mean ${sar.mean_db.toFixed(2)} dB · median ${sar.median_db.toFixed(2)} dB</span><small>QA: ${escapeHTML(sar.provider_qa_state)} · not NISAR</small></article><article><b>NASA OPTICAL CONTEXT · OPERA DSWx-HLS</b><span>WTR ${optical.wtr_water_class_counts_before_after[0]} → ${optical.wtr_water_class_counts_before_after[1]} · WTR-2 ${optical.wtr2_water_class_counts_before_after[0]} → ${optical.wtr2_water_class_counts_before_after[1]} water-class cells</span><small>${spatial?"Native grids joined by exact area-weighted cell intersections; no resampling. Optical classifications remain context, not ground truth.":"Same AOI, different grids · no pixel-wise cross-sensor comparison"}</small></article>${nearerCard}${spatialCard}${polarizationCard}${gpmCard}${gpmInteracquisitionCard}${hydrologicCard}${acquisitionConditionsCard}${modisVegetationCard}${smapScreenCard}${smapRadiometerCard}${hlsCard}${hlsS30Card}</div>${timeline}${reasoningMarkup}<section class="investigation-challenges"><div><b>CHALLENGE / HUMAN REVIEW</b><button type="button" id="exportChallengeNotes" ${currentChallenges.length?"":"hidden"}>EXPORT NOTES</button><button type="button" id="importChallengeNotes">IMPORT REVIEW NOTES</button></div><p>Review notes are unassessed analyst input. They are linked to this assessment and never change its disposition automatically.</p><div class="challenge-notes">${challengesMarkup}</div></section><p class="investigation-boundary">This assessment uses a retained diagnostic Sentinel-1 pair and optical product classifications. It does not establish causal attribution, a validated flood extent, or a NISAR result.</p><div class="preview-actions"><button type="button" id="assessmentRecordButton">INSPECT LINKED EVIDENCE RECORD</button><button type="button" id="closeAssessmentButton">CLOSE ASSESSMENT</button></div>`;
  section.querySelectorAll(".investigation-time-point[data-time-position]").forEach((point)=>{
    point.style.left=`${point.dataset.timePosition}%`;
  });
  $("#assessmentRecordButton").addEventListener("click",()=>{$("#recordJson").textContent=JSON.stringify(record,null,2);$("#recordDialog .eyebrow").textContent="EVIDENCE RECORD · CROSS-SENSOR ASSESSMENT";$("#recordDialog h2").textContent="Investigation and evidence links";$("#recordDialog").showModal();});
  section.querySelectorAll(".investigation-source-link").forEach((button)=>button.addEventListener("click",()=>openInvestigationEvidenceRecord(button.dataset.evidenceId)));
  if(spatial75)$("#inspectSpatialSupportRecord").addEventListener("click",()=>openInvestigationEvidenceRecord("NASA-OPERA-RTC-DSWX-SPATIAL-SUPPORT"));
  if(polarizationSummary){
    $("#inspectPolarizationRecord").addEventListener("click",()=>openInvestigationEvidenceRecord("NASA-OPERA-RTC-POLARIZATION-SENSITIVITY"));
    $("#inspectVhPairRecord").addEventListener("click",()=>openInvestigationEvidenceRecord("NASA-OPERA-RTC-S1-VH-PAIR"));
    $("#inspectVhSpatialRecord").addEventListener("click",()=>openInvestigationEvidenceRecord("NASA-OPERA-RTC-VH-DSWX-SPATIAL-SUPPORT"));
  }
  if(gpm)$("#inspectGpmContextRecord").addEventListener("click",()=>openInvestigationEvidenceRecord("NASA-GPM-IMERG-BEFORE-PRE-SAR"));
  if(gpm?.interacquisition)$("#inspectGpmInteracquisitionRecord").addEventListener("click",()=>openInvestigationEvidenceRecord("NASA-GPM-IMERG-INTERACQUISITION-CHRONOLOGY"));
  if(hydrologic)$("#inspectGuaibaHydrologyRecord").addEventListener("click",()=>openInvestigationEvidenceRecord("ANA-GUAIBA-FLOOD-STAGE-CHRONOLOGY"));
  if(smapScreen)$("#inspectSmapScreenRecord").addEventListener("click",()=>openInvestigationEvidenceRecord("NASA-SPL2SMAP-S-CANDIDATE-SCREEN"));
  if(smapRadiometer)$("#inspectSmapRadiometerRecord").addEventListener("click",()=>openInvestigationEvidenceRecord("NASA-SMAP-SPL3SMP-E-RESOLUTION-SCREEN"));
  if(hls){
    $("#inspectHlsScreenRecord").addEventListener("click",()=>openInvestigationEvidenceRecord("NASA-HLS-L30-VEGETATION-SCREEN"));
    $("#inspectHlsAssociationRecord").addEventListener("click",()=>openInvestigationEvidenceRecord("NASA-HLS-L30-NDVI-SAR-ASSOCIATION"));
  }
  if(hlsS30){
    $("#inspectHlsS30ScreenRecord").addEventListener("click",()=>openInvestigationEvidenceRecord("NASA-HLS-S30-VEGETATION-SCREEN"));
    $("#inspectHlsS30AssociationRecord").addEventListener("click",()=>openInvestigationEvidenceRecord("NASA-HLS-S30-NDVI-SAR-ASSOCIATION"));
  }
  if(acquisitionReview)$("#inspectAcquisitionConditionsRecord").addEventListener("click",()=>openInvestigationEvidenceRecord("NASA-OPERA-RTC-S1-ACQUISITION-CONDITIONS-REVIEW"));
  if(modisScreen)$("#inspectModisVegetationRecord").addEventListener("click",()=>openInvestigationEvidenceRecord("NASA-MOD13Q1-VEGETATION-CANDIDATE-SCREEN"));
  section.querySelectorAll(".challenge-hypothesis").forEach((button)=>button.addEventListener("click",()=>openInvestigationChallenge(button.dataset.hypothesisId)));
  if(currentChallenges.length)$("#exportChallengeNotes").addEventListener("click",exportInvestigationChallengeNotes);
  $("#importChallengeNotes").addEventListener("click",()=>$("#challengeNotesFile").click());
  $("#closeAssessmentButton").addEventListener("click",()=>{crossSensorAssessmentVisible=false;renderCrossSensorAssessment();});
  if(!dialog.open)dialog.showModal();
}

function closeInvestigationDialog() {
  crossSensorAssessmentVisible=false;
  renderCrossSensorAssessment();
}

async function openInvestigationEvidenceRecord(evidenceId) {
  try{
    const response=await fetch(caseApiURL(`/api/investigation-evidence?evidence_id=${encodeURIComponent(evidenceId)}`),{cache:"no-store"});
    const record=await response.json();
    if(!response.ok)throw new Error(record.error||"Linked evidence could not be loaded");
    $("#recordJson").textContent=JSON.stringify(record,null,2);
    $("#recordDialog .eyebrow").textContent=`SOURCE RECORD · ${evidenceId}`;
    $("#recordDialog h2").textContent=evidenceId==="ANA-GUAIBA-FLOOD-STAGE-CHRONOLOGY"?"ANA official hydrologic event context":evidenceId.startsWith("NASA-GPM-IMERG-")?"NASA precipitation context and source subsets":evidenceId==="NASA-OPERA-RTC-S1-VH-PAIR"?"Bounded VH measurement and provenance":evidenceId==="NASA-OPERA-RTC-POLARIZATION-SENSITIVITY"?"VV/VH sensitivity and evidence relationships":evidenceId==="NASA-OPERA-RTC-VH-DSWX-SPATIAL-SUPPORT"?"VH native-grid spatial support diagnostic":"Native-grid spatial support diagnostic";
    $("#recordDialog").showModal();
  }catch(error){showToast(error.message);}
}

function openInvestigationChallenge(hypothesisId) {
  if(!crossSensorAssessment)return;
  const hypothesisSelect=$("#challengeHypothesis");
  hypothesisSelect.innerHTML=crossSensorAssessment.hypotheses.map((item)=>`<option value="${escapeHTML(item.id)}">${escapeHTML(item.statement)}</option>`).join("");
  clearCounterfactualChallengePreview();
  $("#previewChallengeImpact").disabled=true;
  $("#investigationChallengeForm").reset();
  hypothesisSelect.value=hypothesisId;
  populateChallengeEvidence(hypothesisId);
  $("#investigationChallengeDialog").showModal();
}

function populateChallengeEvidence(hypothesisId) {
  const hypothesis=crossSensorAssessment?.hypotheses.find((item)=>item.id===hypothesisId);
  const referenced=new Set(hypothesis?.evidence_refs||[]);
  const evidenceSelect=$("#challengeEvidence");
  const options=crossSensorAssessment.evidence_artifacts
    .filter((item)=>referenced.has(item.evidence_id))
    .map((item)=>`<option value="${escapeHTML(item.evidence_id)}">${escapeHTML(item.evidence_id)} · ${escapeHTML(item.role)}</option>`);
  evidenceSelect.innerHTML='<option value="MISSING_EVIDENCE">No retrieved source · information gap</option>'+options.join("");
  evidenceSelect.value="MISSING_EVIDENCE";
}

function clearCounterfactualChallengePreview() {
  counterfactualPreviewGeneration+=1;
  counterfactualChallengePreview=null;
  const panel=$("#challengeImpactPreview");
  panel.hidden=true;
  panel.textContent="";
  const button=$("#previewChallengeImpact");
  button.textContent="PREVIEW COUNTERFACTUAL DISPOSITION";
  button.disabled=$("#challengeEvidence").value==="MISSING_EVIDENCE";
}

async function previewCounterfactualChallengeImpact() {
  if(!crossSensorAssessment||!crossSensorAssessmentSha256){showToast("Assessment checksum unavailable; reload the linked assessment before previewing.");return;}
  const evidenceId=$("#challengeEvidence").value;
  if(evidenceId==="MISSING_EVIDENCE")return;
  const generation=++counterfactualPreviewGeneration;
  const button=$("#previewChallengeImpact");
  button.disabled=true;
  button.textContent="COMPUTING COUNTERFACTUAL…";
  try{
    const response=await fetch(caseApiURL("/api/investigation-counterfactual-preview"),{
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({
        case_id:crossSensorAssessment.case_id,
        assessment_sha256:crossSensorAssessmentSha256,
        hypothesis_id:$("#challengeHypothesis").value,
        evidence_id:evidenceId,
        proposed_relationship:$("#challengeRelationship").value,
      }),
    });
    const result=await response.json();
    if(generation!==counterfactualPreviewGeneration)return;
    if(!response.ok)throw new Error(result.error||"Counterfactual preview could not be computed");
    if(result.record_type!=="ECHO_COUNTERFACTUAL_EVIDENCE_RECLASSIFICATION_PREVIEW"||result.status!=="COUNTERFACTUAL_ONLY")throw new Error("Counterfactual preview returned an unsupported record");
    counterfactualChallengePreview=result;
    const panel=$("#challengeImpactPreview");
    panel.innerHTML=`<b>COUNTERFACTUAL ONLY · NO SOURCE OR FINDING CHANGED</b><span>${escapeHTML(result.current_disposition.replaceAll("_"," "))} → ${escapeHTML(result.counterfactual_disposition.replaceAll("_"," "))}</span><small>${result.disposition_would_change?"The derived disposition changes under this analyst-entered relationship.":"The derived disposition stays the same under this analyst-entered relationship."} Source ${escapeHTML(result.evidence_id)} · ${escapeHTML(result.previous_relationship.replaceAll("_"," "))} → ${escapeHTML(result.proposed_relationship.replaceAll("_"," "))}</small><small>${escapeHTML(result.interpretation_limit)}</small>`;
    panel.hidden=false;
  }catch(error){if(generation===counterfactualPreviewGeneration){showToast(error.message);clearCounterfactualChallengePreview();}}
  finally{
    if(generation===counterfactualPreviewGeneration){
      button.disabled=$("#challengeEvidence").value==="MISSING_EVIDENCE";
      button.textContent="PREVIEW COUNTERFACTUAL DISPOSITION";
    }
  }
}

function exportInvestigationChallengeNotes() {
  downloadJSON({
    record_type:"ECHO_SESSION_INVESTIGATION_CHALLENGE_NOTES",
    schema_version:1,
    exported_at_utc:new Date().toISOString(),
    notes:investigationChallengeNotes,
    interpretation_limit:"Human review notes are unassessed input, not scientific evidence or a change to the linked assessment.",
  },"echo-investigation-challenge-notes.json");
}

async function importInvestigationChallengeNotes(file) {
  if(!crossSensorAssessment||!crossSensorAssessmentSha256)throw new Error("Open the linked assessment before importing review notes.");
  if(file.size>1024*1024)throw new Error("Review-note file exceeds the 1 MiB limit.");
  let record;
  try{record=JSON.parse(await file.text());}catch{throw new Error("Review-note file is not valid JSON.");}
  if(record?.record_type!=="ECHO_SESSION_INVESTIGATION_CHALLENGE_NOTES"||record.schema_version!==1||!Array.isArray(record.notes)||record.notes.length>100){
    throw new Error("File is not a supported ECHO review-note export.");
  }
  const evidenceById=new Map(crossSensorAssessment.evidence_artifacts.map((item)=>[item.evidence_id,item]));
  const allowedChallenges=new Set(["POSSIBLE_CONTRADICTION","ALTERNATIVE_EXPLANATION","MISSING_EVIDENCE","ASSUMPTION_OR_LIMITATION"]);
  const allowedRelations=new Set(["SUPPORTS","CONTRADICTS","DOES_NOT_DISTINGUISH","LIMITS_INTERPRETATION"]);
  const imported=[];
  for(const note of record.notes){
    if(note?.record_type!=="ECHO_INVESTIGATION_CHALLENGE_NOTE"||note.schema_version!==1||note.status!=="UNASSESSED_HUMAN_INPUT"||note.role!=="ANALYST_CHALLENGE_NOTE"){
      throw new Error("Review-note record header or status is invalid.");
    }
    if(!Number.isFinite(Date.parse(note.created_at_utc))||!allowedChallenges.has(note.challenge_type)||typeof note.challenge_statement!=="string"||note.challenge_statement.trim().length<12||note.challenge_statement.length>4000||typeof note.proposed_test!=="string"||note.proposed_test.trim().length<12||note.proposed_test.length>4000){
      throw new Error("Review-note content or timestamp is invalid.");
    }
    const parent=note.source_assessment;
    if(parent?.case_id!==crossSensorAssessment.case_id||parent.sha256!==crossSensorAssessmentSha256||parent.disposition!==crossSensorAssessment.status){
      throw new Error("Review note belongs to a different or changed assessment.");
    }
    const priorArtifacts=parent.evidence_artifacts;
    if(!Array.isArray(priorArtifacts)||priorArtifacts.length!==evidenceById.size||priorArtifacts.some((item)=>{
      const current=evidenceById.get(item?.evidence_id);
      return !current||current.role!==item.role||current.sha256!==item.sha256;
    }))throw new Error("Review note evidence checksums do not match the current assessment.");
    const hypothesis=crossSensorAssessment.hypotheses.find((item)=>item.id===note.hypothesis?.id);
    if(!hypothesis||hypothesis.statement!==note.hypothesis.statement||hypothesis.state!==note.hypothesis.recorded_state){
      throw new Error("Review note hypothesis does not match the current assessment.");
    }
    let citedSource=null;
    if(note.related_evidence!==null){
      citedSource=evidenceById.get(note.related_evidence?.evidence_id);
      if(!citedSource||!hypothesis.evidence_refs.includes(citedSource.evidence_id)||citedSource.role!==note.related_evidence.role||citedSource.sha256!==note.related_evidence.sha256){
        throw new Error("Review note source is absent, uncited, or has changed.");
      }
    }
    const preview=note.counterfactual_preview;
    if(preview!==undefined&&preview!==null){
      if(!citedSource||preview.record_type!=="ECHO_COUNTERFACTUAL_EVIDENCE_RECLASSIFICATION_PREVIEW"||preview.status!=="COUNTERFACTUAL_ONLY"||preview.case_id!==parent.case_id||preview.assessment_sha256!==parent.sha256||preview.hypothesis_id!==hypothesis.id||preview.evidence_id!==citedSource.evidence_id||!allowedRelations.has(preview.proposed_relationship)){
        throw new Error("Counterfactual preview is not linked to the cited assessment and evidence.");
      }
      const response=await fetch(caseApiURL("/api/investigation-counterfactual-preview"),{
        method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({case_id:parent.case_id,assessment_sha256:parent.sha256,hypothesis_id:hypothesis.id,evidence_id:citedSource.evidence_id,proposed_relationship:preview.proposed_relationship}),
      });
      const fresh=await response.json();
      if(!response.ok||fresh.record_type!==preview.record_type||fresh.status!==preview.status||fresh.case_id!==preview.case_id||fresh.assessment_sha256!==preview.assessment_sha256||fresh.hypothesis_id!==preview.hypothesis_id||fresh.evidence_id!==preview.evidence_id||fresh.previous_relationship!==preview.previous_relationship||fresh.proposed_relationship!==preview.proposed_relationship||fresh.current_disposition!==preview.current_disposition||fresh.counterfactual_disposition!==preview.counterfactual_disposition||fresh.disposition_would_change!==preview.disposition_would_change||fresh.interpretation_limit!==preview.interpretation_limit){
        throw new Error("Counterfactual no longer reproduces against the current assessment.");
      }
    }
    imported.push(note);
  }
  const signature=(note)=>[note.source_assessment.sha256,note.created_at_utc,note.hypothesis.id,note.challenge_type,note.challenge_statement,note.proposed_test].join("\u001f");
  const existing=new Set(investigationChallengeNotes.map(signature));
  const additions=imported.filter((note)=>{
    const key=signature(note);
    if(existing.has(key))return false;
    existing.add(key);
    return true;
  });
  investigationChallengeNotes.push(...additions);
  renderCrossSensorAssessment();
  showToast(`${additions.length} review note${additions.length===1?"":"s"} imported and revalidated.`);
}

async function sha256Hex(text) {
  if(!globalThis.crypto?.subtle)return null;
  const digest=await crypto.subtle.digest("SHA-256",new TextEncoder().encode(text));
  return Array.from(new Uint8Array(digest),(byte)=>byte.toString(16).padStart(2,"0")).join("");
}

function validateLinkedDiagnosticPair(record, expectedSceneIds) {
  const measurement=record?.measurement;
  const grid=record?.grid;
  const values=measurement?.values_db;
  const valid=measurement?.valid_mask;
  const corners=grid?.pixel_corners_wgs84;
  const bounds=grid?.window?.bounds_wgs84;
  const sources=record?.source_products;
  if(record?.record_type!=="ECHO_OPERA_RTC_S1_PAIR_ANALYSIS"||record.status!=="DIAGNOSTIC_PRODUCT_MASKED_COMPARISON")throw new Error("Linked SAR record is not a measured diagnostic RTC-S1 comparison");
  if(measurement.quantity!=="signed_gamma0_log_ratio_db"||measurement.units!=="dB"||!Array.isArray(values)||!values.length||!Array.isArray(valid)||valid.length!==values.length)throw new Error("Linked SAR measurement has an unsupported quantity or mask");
  const columns=values[0]?.length;
  if(!Number.isInteger(columns)||columns<1||values.length*columns>65536||valid.some((row)=>!Array.isArray(row)||row.length!==columns)||values.some((row)=>!Array.isArray(row)||row.length!==columns))throw new Error("Linked SAR measurement exceeds the supported map grid or has inconsistent dimensions");
  if(!Array.isArray(corners)||corners.length!==values.length+1||corners.some((row)=>!Array.isArray(row)||row.length!==columns+1))throw new Error("Linked SAR geographic cell corners do not match the measurement grid");
  if(!Array.isArray(bounds)||bounds.length!==4||!bounds.every(Number.isFinite)||bounds[0]>=bounds[2]||bounds[1]>=bounds[3]||bounds[0]<-180||bounds[2]>180||bounds[1]<-90||bounds[3]>90)throw new Error("Linked SAR geographic bounds are invalid");
  const actualSceneIds=[sources?.before?.scene_id,sources?.after?.scene_id];
  if(actualSceneIds.some((sceneId,index)=>typeof sceneId!=="string"||sceneId!==expectedSceneIds[index]))throw new Error("Linked SAR measurements do not match the assessment's acquisition IDs");
  for(const row of corners)for(const point of row){
    if(!Array.isArray(point)||point.length!==2||!Number.isFinite(point[0])||!Number.isFinite(point[1])||point[0]<-180||point[0]>180||point[1]<-90||point[1]>90)throw new Error("Linked SAR grid contains invalid geographic coordinates");
  }
  return record;
}

async function fetchLinkedDiagnosticPair(assessment) {
  const sar=assessment.observations?.sar_diagnostic_measurement;
  const artifact=assessment.evidence_artifacts?.find((item)=>item.evidence_id==="SAR-RTC-S1-PAIR");
  if(!Array.isArray(sar?.scene_ids)||sar.scene_ids.length!==2||!artifact||artifact.record_type!=="ECHO_OPERA_RTC_S1_PAIR_ANALYSIS")throw new Error("Assessment does not link a supported diagnostic SAR measurement record");
  const response=await fetch(caseApiURL("/api/investigation-evidence?evidence_id=SAR-RTC-S1-PAIR"),{cache:"no-store"});
  const payload=await response.text();
  if(!response.ok)throw new Error("Linked SAR measurement could not be loaded");
  const checksum=await sha256Hex(payload);
  if(!checksum||checksum!==artifact.sha256)throw new Error("Linked SAR measurement checksum does not match its assessment manifest");
  let record;
  try{record=JSON.parse(payload);}catch{throw new Error("Linked SAR measurement is not valid JSON");}
  return validateLinkedDiagnosticPair(record,sar.scene_ids);
}

function showRetainedDiagnosticPair(record) {
  operaPairAnalysis=record;
  operaCatalog={features:[]};
  selectedOperaPixel=null;
  operaDisplayScale=pairDisplayScale(record);
  gcovPreview=null;selectedPreviewPixel=null;gcovPairAnalysis=null;selectedPairPixel=null;pairAnalysisDisplayScale=null;
  dswxContextVisible=false;selectedDswxSample=null;
  $("#dswxContextControls").hidden=true;
  $(".preview-options:not(.context-options)").hidden=true;
  document.querySelector(".timeline-panel").hidden=true;
  $("#loadGcovPreview").hidden=true;
  $("#challengeButton").hidden=true;
  $("#clearOperaView").hidden=false;
  $("#clearOperaView").textContent=review?.primary_opera_pair?"RETURN TO CASE":"RETURN TO NISAR";
  $(".top-context").innerHTML='<span class="live-dot"></span> INVESTIGATION WORKSPACE <span class="slash">/</span> RETAINED OPERA RTC-S1 MEASUREMENT';
  $(".case-heading h1").textContent="Diagnostic SAR measurement";
  $(".case-heading .subtitle").textContent="Sentinel-1-derived OPERA RTC-S1 · retained bounded comparison · no consolidated provider QA verdict";
  $(".case-status").classList.remove("qa-hold");
  $(".case-status b").textContent="Diagnostic comparison";
  $(".case-status small").textContent="OPERA RTC-S1 · NOT NISAR";
  $(".case-chip b").textContent="OPERA RTC-S1 · retained AOI";
  $(".case-chip small").textContent=record.source_products.before.scene_id;
  const bounds=record.grid.window.bounds_wgs84;
  const center=[(bounds[0]+bounds[2])/2,(bounds[1]+bounds[3])/2];
  $(".coordinate-readout").innerHTML=`${Math.abs(center[0]).toFixed(4)}° ${center[0]<0?"W":"E"}&nbsp;&nbsp; ${Math.abs(center[1]).toFixed(4)}° ${center[1]<0?"S":"N"} <span>MEASUREMENT AOI CENTER</span>`;
  $("#searchCenterLegend").innerHTML='<i class="legend-point"></i> MEASUREMENT CENTER';
  const before=record.source_products.before;
  const after=record.source_products.after;
  $("#sceneDetails").innerHTML=`<div><dt>BEFORE</dt><dd>${escapeHTML(before.acquisition_start_utc)} UTC</dd></div><div><dt>AFTER</dt><dd>${escapeHTML(after.acquisition_start_utc)} UTC</dd></div><div><dt>PRODUCT</dt><dd>NASA OPERA RTC-S1 · Sentinel-1 derived</dd></div><div><dt>POLARIZATION</dt><dd>${escapeHTML(record.measurement.polarization)}</dd></div><div><dt>PROVIDER QA</dt><dd>Product metadata retrieved · no consolidated PASS/FAIL</dd></div><div class="full"><dt>SCENE IDS</dt><dd>${escapeHTML(before.scene_id)}<br>${escapeHTML(after.scene_id)}</dd></div>`;
  $(".evidence-count").innerHTML='OPERA <i>/</i> PAIR';
  $(".finding-card p").textContent="This retained map shows the measured Sentinel-1-derived OPERA RTC-S1 gamma-zero log-ratio for the selected AOI. Product QA metadata were retrieved, but no consolidated PASS/FAIL verdict exists; this diagnostic measurement does not establish an event or cause.";
  $(".finding-meta b").textContent=record.status.replaceAll("_"," ");
  $(".confidence-block .readiness-value").innerHTML="DIAGNOSTIC <small>NO CONSOLIDATED QA VERDICT</small>";
  $(".confidence-block p").textContent="Retained measurement displayed from its checksum-linked source record. Provider disposition and causal interpretation remain unresolved.";
  $(".gate-count").textContent="1 HOLD · 2 OPEN";
  $(".gate-list").innerHTML='<li><span class="gate-icon review">!</span><span><b>Product QA</b><small>Per-product metadata retrieved; no consolidated PASS/FAIL disposition.</small></span><span class="gate-state review">OPEN</span></li><li><span class="gate-icon pass">✓</span><span><b>Raster grid and mask</b><small>Retained dimensions and geographic cell corners checked against the assessment record.</small></span><span class="gate-state pass">MEASURED</span></li><li><span class="gate-icon open">○</span><span><b>Independent interpretation</b><small>No causal finding or validated event boundary.</small></span><span class="gate-state open">OPEN</span></li>';
  renderDswxContextInspector();
  drawMap();
}

function showInvestigationIntegrityImpact(impact) {
  const section=$("#investigationAssessment");
  section.innerHTML=window.renderInvestigationIntegrityImpact(impact);
  $("#investigationDialog").showModal();
}

async function openCrossSensorAssessment(button = $("#assessDswxEvidence")) {
  if(!crossSensorAssessmentMatchesCurrentPair()){
    showToast("This assessment is linked to a different RTC-S1 pair. Select its case-preferred pair to inspect it.");
    return;
  }
  if(button){button.disabled=true;button.textContent="LOADING LINKED EVIDENCE…";}
  try{
    if(!crossSensorAssessment){
      const response=await fetch(caseApiURL("/api/cross-sensor-assessment"),{cache:"no-store"});
      const responseText=await response.text();
      const record=JSON.parse(responseText);
      if(!response.ok){
        const error=new Error(record.error||"Investigation assessment could not be loaded");
        error.integrityImpact=record.integrity_impact;
        throw error;
      }
      if(record.record_type!=="ECHO_CROSS_SENSOR_INVESTIGATION_ASSESSMENT"||record.status!=="CAUSAL_INTERPRETATION_UNRESOLVED"||!Array.isArray(record.hypotheses))throw new Error("Assessment record has an unsupported schema or disposition");
      const linkedScenes=record.observations?.sar_diagnostic_measurement?.scene_ids;
      if(!Array.isArray(linkedScenes)||linkedScenes.length!==2||linkedScenes.some((sceneId)=>typeof sceneId!=="string"||!sceneId)||linkedScenes[0]===linkedScenes[1])throw new Error("Assessment record does not identify its two source SAR scenes");
      crossSensorAssessment=record;
      try{crossSensorAssessmentSha256=await sha256Hex(responseText);}catch{crossSensorAssessmentSha256=null;}
      if(!crossSensorAssessmentMatchesCurrentPair()){
        crossSensorAssessment=null;
        crossSensorAssessmentSha256=null;
        throw new Error("Assessment source scenes do not match this case's nominated RTC-S1 pair.");
      }
    }
    if(!operaPairAnalysis){
      const linkedPair=await fetchLinkedDiagnosticPair(crossSensorAssessment);
      showRetainedDiagnosticPair(linkedPair);
    }
    crossSensorAssessmentVisible=true;renderCrossSensorAssessment();
  }catch(error){
    if(error.integrityImpact)showInvestigationIntegrityImpact(error.integrityImpact);
    else showToast(error.message);
  }
  finally{
    if(button){button.disabled=false;button.textContent=button.id==="openCaseInvestigation"?"OPEN CASE INVESTIGATION":"OPEN EVIDENCE ASSESSMENT";}
  }
}

function dswxDateLabel(role) {
  return role==="before"?"2024-05-08 · Sentinel-2A":"2024-06-02 · Sentinel-2B";
}

function trustedQAReportURI(report) {
  try {
    const url=new URL(report.artifact_uri);
    const match=url.pathname.match(/^\/NISAR\/NISAR_L2_GCOV_(?:BETA_V1|PROVISIONAL_V1|V1)\/([^/]+)\/([^/]+)_QA_REPORT\.pdf$/);
    return url.protocol==="https:" && url.hostname==="nisar.asf.earthdatacloud.nasa.gov" && !url.search && !url.hash && match?.[1]===report.scene_id && match?.[2]===report.scene_id ? url.href : null;
  } catch { return null; }
}

function trustedQASummaryURI(record) {
  try {
    const url=new URL(record.artifact_uri);
    const match=url.pathname.match(/^\/NISAR\/(NISAR_L2_GCOV_(?:BETA_V1|PROVISIONAL_V1|V1))\/([^/]+)\/([^/]+)_QA_SUMMARY\.csv$/);
    return url.protocol==="https:" && url.hostname==="nisar.asf.earthdatacloud.nasa.gov" && !url.search && !url.hash && match?.[2]===record.scene_id && match?.[3]===record.scene_id ? url.href : null;
  } catch { return null; }
}

function renderProviderQASummary(record) {
  const evidence=record.evidence||{};
  const sourceURI=trustedQASummaryURI(record);
  const sourceLink=sourceURI?`<a href="${escapeHTML(sourceURI)}" target="_blank" rel="noopener noreferrer">Open original ASF QA summary ↗</a>`:"ASF summary link unavailable · source URI did not validate";
  const checks=(evidence.check_details||[]).map((check)=>`<article class="qa-report-card"><div class="qa-report-heading"><span>${escapeHTML(check.check)}</span><b class="qa-result-${escapeHTML((check.result||"unknown").toLowerCase())}">${escapeHTML(check.result||"UNKNOWN")}</b></div><dl><div><dt>THRESHOLD</dt><dd>${escapeHTML(check.threshold||"Not reported")}</dd></div><div><dt>ACTUAL</dt><dd>${escapeHTML(check.actual||"Not reported")}</dd></div><div class="qa-full"><dt>PROVIDER NOTE</dt><dd>${escapeHTML(check.notes||"No note")}</dd></div></dl></article>`).join("");
  const retrieval=record.retrieval||{};
  return `<article class="qa-report-card"><div class="qa-report-heading"><span>ASF PROVIDER QA · ${escapeHTML(evidence.status||"UNKNOWN")}</span><b>${escapeHTML(record.scene_id)}</b></div><dl><div><dt>RETRIEVED UTC</dt><dd>${escapeHTML(record.retrieved_at_utc)}</dd></div><div><dt>ARTIFACT SIZE</dt><dd>${escapeHTML(record.artifact_size_bytes)} bytes</dd></div><div><dt>PROVIDER / METHOD</dt><dd>${escapeHTML(retrieval.provider)} · ${escapeHTML(retrieval.method)}</dd></div><div><dt>RANGE BYTES</dt><dd>${escapeHTML(retrieval.fsspec_range_bytes_requested)}</dd></div></dl><p>${sourceLink}<span class="qa-checksum">SHA-256 ${escapeHTML(record.artifact_sha256)}</span></p><p class="qa-empty">This is the provider CSV disposition. ECHO did not re-read product HDF5 identification metadata or radar arrays for this request.</p></article>${checks||'<p class="qa-empty">The provider summary contains no check rows.</p>'}`;
}

function configureProviderQAEvidenceExport(sceneId) {
  const summary=qaSummaryByScene.get(sceneId);
  const feature=qaFeatureByScene.get(sceneId);
  const button=$("#qaEvidenceExport");
  if(!summary||!feature||!catalog){button.hidden=true;return;}
  const record={
    record_type:"ECHO_PROVIDER_QA_INSPECTION",
    record_version:1,
    exported_at_utc:new Date().toISOString(),
    source_catalog:{provider:"Alaska Satellite Facility DAAC",query:catalog.query,feature},
    provider_qa_summary:summary,
    interpretation_limits:[
      "Provider QA disposition is not an ECHO scientific suitability determination.",
      "This inspection did not re-read product HDF5 identification metadata or radar measurement arrays.",
      "The provider CSV does not establish valid study-area coverage, cross-date alignment, or event cause.",
    ],
  };
  $("#qaEvidenceRecord").value=JSON.stringify(record);
  button.hidden=false;
}

function displayedFeatures() {
  if (!catalog?.features?.length) return [];
  if (pair) {
    return [pair.before_scene,pair.after_scene]
      .map((id)=>catalog.features.find((feature)=>feature.properties.fileID===id))
      .filter(Boolean);
  }
  return chronologicalFeatures().slice(0,2);
}

function chronologicalFeatures() {
  return [...(catalog?.features||[])].sort((a,b)=>{
    const first=Date.parse(a.properties.startTime),second=Date.parse(b.properties.startTime);
    if(!Number.isFinite(first))return Number.isFinite(second)?1:0;
    if(!Number.isFinite(second))return -1;
    return first-second;
  });
}

function availableDiagonalLayers(properties) {
  const polarizations=[...(properties.mainBandPolarization||[]),...(properties.sideBandPolarization||[])];
  return [...new Set(polarizations.map((value)=>diagonalLayerByPolarization[value]).filter(Boolean))];
}

function sceneRole(sceneId) {
  if(pair?.before_scene===sceneId)return "PAIR · BEFORE";
  if(pair?.after_scene===sceneId)return "PAIR · AFTER";
  return "OBSERVATION";
}

function elapsedLabel(seconds) {
  if(!Number.isFinite(seconds))return "time unknown";
  if(seconds===0)return "same time";
  if(seconds<60)return `${Math.round(seconds)} s`;
  if(seconds<3600)return `${Math.round(seconds/60)} min`;
  if(seconds<86400)return `${(seconds/3600).toFixed(1)} h`;
  return `${(seconds/86400).toFixed(1)} d`;
}

function renderTimeline() {
  const scenes=chronologicalFeatures();
  const track=$("#timelineTrack");
  if(!scenes.length){track.innerHTML='<p class="timeline-empty">No acquisitions in this catalog query.</p>';return;}
  const items=[];
  scenes.forEach((feature,index)=>{
    const p=feature.properties;
    if(index){
      const previous=Date.parse(scenes[index-1].properties.startTime);
      const current=Date.parse(p.startTime);
      items.push(`<span class="timeline-gap" aria-label="${elapsedLabel((current-previous)/1000)} between acquisitions">${elapsedLabel((current-previous)/1000)}</span>`);
    }
    const sceneId=p.fileID;
    const timestamp=Date.parse(p.startTime);
    const date=Number.isFinite(timestamp)?new Date(timestamp):null;
    const dateLabel=date?date.toLocaleDateString("en-GB",{day:"2-digit",month:"short",year:"numeric",timeZone:"UTC"}).toUpperCase():"TIME UNKNOWN";
    const timeLabel=date?`${date.toISOString().slice(11,19)} UTC`:"— UTC";
    const role=sceneRole(sceneId);
    items.push(`<button class="timeline-observation${sceneId===selectedSceneId?" selected":""}${role!=="OBSERVATION"?" paired":""}" type="button" data-scene-id="${escapeHTML(sceneId)}" aria-pressed="${sceneId===selectedSceneId}"><span class="timeline-dot"></span><time class="timeline-date"${date?` datetime="${escapeHTML(p.startTime)}"`:""}>${dateLabel}</time><span class="timeline-time">${timeLabel}</span><span class="timeline-meta">${escapeHTML(p.flightDirection||"ORBIT")} · ${escapeHTML(p.orbit??"UNKNOWN")}</span><span class="timeline-role">${role}</span></button>`);
  });
  track.innerHTML=items.join("");
  track.querySelector(".timeline-observation.selected")?.scrollIntoView({block:"nearest",inline:"center"});
}

function getBounds(features, point, area = null, minimumPadding = 0.06) {
  const xs = [point[0]], ys = [point[1]];
  if (area) {
    xs.push(area[0], area[2]);
    ys.push(area[1], area[3]);
  }
  const visit = (coordinates) => {
    if (typeof coordinates[0] === "number") { xs.push(coordinates[0]); ys.push(coordinates[1]); return; }
    coordinates.forEach(visit);
  };
  features.forEach((feature) => visit(feature.geometry.coordinates));
  const padX = Math.max((Math.max(...xs) - Math.min(...xs)) * 0.15, minimumPadding);
  const padY = Math.max((Math.max(...ys) - Math.min(...ys)) * 0.15, minimumPadding);
  return {minX:Math.min(...xs)-padX,maxX:Math.max(...xs)+padX,minY:Math.min(...ys)-padY,maxY:Math.max(...ys)+padY};
}

function basemapDate(displayed) {
  const feature = chronologicalFeatures().find((item)=>item.properties.fileID===selectedSceneId) || displayed[0];
  const acquired = feature?.properties?.startTime;
  return acquired && Number.isFinite(Date.parse(acquired)) ? new Date(acquired).toISOString().slice(0,10) : null;
}

function geographicCenter(query) {
  const bounds=areaBounds||query.bounds_wgs84;
  return bounds?[(bounds[0]+bounds[2])/2,(bounds[1]+bounds[3])/2]:[query.longitude,query.latitude];
}

function gcovPairMaturityLabel(record=gcovPairAnalysis) {
  const sourceProducts=record?.source_products||{};
  const maturityLevels=Object.values(sourceProducts).map(source=>source.product_maturity||"UNKNOWN");
  if(maturityLevels.length!==2||maturityLevels.some(level=>!['BETA','PROVISIONAL','VALIDATED'].includes(level)))return "MATURITY UNSPECIFIED";
  return new Set(maturityLevels).size===1?maturityLevels[0]:"MIXED MATURITY";
}

function gibsImageURL(view, width, height, date) {
  const url = new URL("https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi");
  Object.entries({
    SERVICE:"WMS", VERSION:"1.1.1", REQUEST:"GetMap",
    LAYERS:"MODIS_Terra_CorrectedReflectance_TrueColor", STYLES:"",
    SRS:"EPSG:4326", BBOX:`${view.minX},${view.minY},${view.maxX},${view.maxY}`,
    WIDTH:String(Math.round(width)), HEIGHT:String(Math.round(height)), FORMAT:"image/jpeg", TIME:date,
  }).forEach(([key,value])=>url.searchParams.set(key,value));
  return url.href;
}

function renderMapCaption() {
  if(!catalog)return;
  if(dswxContextVisible){
    $(".map-caption").textContent=`NASA OPERA DSWx-HLS ${dswxContextLayer} · ${dswxDateLabel(dswxContextDate)} · optical class context`;
    return;
  }
  if(operaPairAnalysis){
    $(".map-caption").textContent=operaPairAnalysis.status==="DIAGNOSTIC_PRODUCT_MASKED_COMPARISON"
      ?"OPERA RTC-S1 descriptive comparison · provider QA not retrieved · diagnostic only"
      :"OPERA RTC-S1 pair · no common clear valid pixels in selected area";
    return;
  }
  const displayed=displayedFeatures();
  const plottedIds=new Set((catalog.features||[]).slice(0,60).map((feature)=>feature.properties.fileID));
  if(selectedSceneId)plottedIds.add(selectedSceneId);
  displayed.forEach((feature)=>plottedIds.add(feature.properties.fileID));
  const plottedCount=plottedIds.size;
  const elapsedDays=pair&&displayed.length===2
    ? (Date.parse(displayed[1].properties.startTime)-Date.parse(displayed[0].properties.startTime))/86400000
    : NaN;
  const gap=Number.isFinite(elapsedDays)?Math.round(elapsedDays):pair?.interval_days;
  const caption=gcovPairAnalysis?.status==="QA_HELD"
    ? "Selected pair · provider QA held · no comparison pixels read"
    : gcovPairAnalysis?.status==="MATURITY_HELD"
      ? "Selected pair · product maturity held · no comparison pixels read"
      : gcovPairAnalysis?.status==="MEASURED_DESCRIPTIVE_ONLY"
        ? `NISAR ${gcovPairMaturityLabel()} ${gcovPairAnalysis.measurement.layer} descriptive comparison · provider QA PASS`
        : gcovPreview
          ? `NISAR ${gcovPreview.measurement.layer} backscatter preview · product QA ${gcovPreview.source.provider_qa_status}`
          : `${plottedCount} ASF footprints shown${catalog.feature_count>plottedCount?` of ${catalog.feature_count}`:""}${pair?` · ${gap}-day metadata candidate`:""}`;
  $(".map-caption").textContent=caption;
}

function previewColor(fraction) {
  const stops=[
    {at:0,color:[27,51,98]},
    {at:.35,color:[40,130,155]},
    {at:.7,color:[116,202,173]},
    {at:1,color:[251,220,115]},
  ];
  const value=Math.max(0,Math.min(1,fraction));
  const upper=stops.findIndex((stop)=>stop.at>=value);
  const left=stops[Math.max(0,upper-1)],right=stops[Math.max(0,upper)];
  const t=right.at===left.at?0:(value-left.at)/(right.at-left.at);
  return "rgb("+left.color.map((channel,index)=>Math.round(channel+(right.color[index]-channel)*t)).join(",")+")";
}

function pairChangeScale() {
  return pairAnalysisDisplayScale||0;
}

function rasterPreviewImage(x,y) {
  previewScreenCells=[];
  if(!gcovPreview)return "";
  const record=gcovPreview;
  const values=record.measurement.values;
  const quality=record.measurement.quality;
  const corners=record.grid.pixel_corners_wgs84;
  const [lowDb,rawHighDb]=record.display_transform.stretch_range_db||[-30,0];
  const highDb=Math.max(rawHighDb,lowDb+1e-6);
  const rows=values.length,columns=values[0]?.length||0;
  const canvas=document.createElement("canvas");
  canvas.width=1000;canvas.height=600;
  const context=canvas.getContext("2d");
  context.globalAlpha=.88;
  for(let row=0;row<rows;row++)for(let column=0;column<columns;column++){
    const raw=values[row][column];
    const code=quality.mask[row][column];
    const exception=quality.input_data_exception_mask[row][column];
    const selected=quality.exact_aoi_pixel_center_selection[row][column]===1;
    if(!selected||code<1||code>5||exception!==0||!Number.isFinite(raw)||raw<=0)continue;
    const db=10*Math.log10(raw);
    const points=[
      corners[row][column],corners[row][column+1],
      corners[row+1][column+1],corners[row+1][column],
    ].map(([longitude,latitude])=>[x(longitude),y(latitude)]);
    context.beginPath();
    context.moveTo(points[0][0],points[0][1]);
    for(let index=1;index<points.length;index++)context.lineTo(points[index][0],points[index][1]);
    context.closePath();
    context.fillStyle=previewColor((db-lowDb)/(highDb-lowDb));
    context.fill();
    const centerX=points.reduce((sum,point)=>sum+point[0],0)/4;
    const centerY=points.reduce((sum,point)=>sum+point[1],0)/4;
    previewScreenCells.push({row,column,centerX,centerY,raw,db,mask:code,looks:quality.number_of_looks[row][column],exception});
  }
  if(selectedPreviewPixel){
    const cell=previewScreenCells.find((item)=>item.row===selectedPreviewPixel.row&&item.column===selectedPreviewPixel.column);
    if(cell){
      context.beginPath();context.arc(cell.centerX,cell.centerY,5,0,2*Math.PI);
      context.strokeStyle="#fff4d5";context.lineWidth=2;context.stroke();
      selectedPreviewPixel={...selectedPreviewPixel,...cell};
    }else selectedPreviewPixel=null;
  }
  return canvas.toDataURL("image/png");
}

function pairAnalysisImage(x,y) {
  previewScreenCells=[];
  if(gcovPairAnalysis?.status!=="MEASURED_DESCRIPTIVE_ONLY")return "";
  const values=gcovPairAnalysis.measurement.values_db;
  const valid=gcovPairAnalysis.measurement.valid_mask;
  const corners=gcovPairAnalysis.grid.pixel_corners_wgs84;
  const scale=pairChangeScale();
  if(!scale)return "";
  const rows=values.length,columns=values[0]?.length||0;
  const canvas=document.createElement("canvas");canvas.width=1000;canvas.height=600;
  const context=canvas.getContext("2d");context.globalAlpha=.91;
  for(let row=0;row<rows;row++)for(let column=0;column<columns;column++){
    const db=values[row][column];if(!valid[row][column]||!Number.isFinite(db))continue;
    const points=[corners[row][column],corners[row][column+1],corners[row+1][column+1],corners[row+1][column]].map(([longitude,latitude])=>[x(longitude),y(latitude)]);
    context.beginPath();context.moveTo(points[0][0],points[0][1]);
    for(let index=1;index<points.length;index++)context.lineTo(points[index][0],points[index][1]);
    context.closePath();
    const fraction=Math.max(-1,Math.min(1,db/scale));
    const strength=Math.abs(fraction),base=fraction<0?[77,120,196]:[212,91,86],neutral=[233,231,219];
    context.fillStyle="rgb("+neutral.map((channel,index)=>Math.round(channel+(base[index]-channel)*strength)).join(",")+")";context.fill();
    const centerX=points.reduce((sum,point)=>sum+point[0],0)/4,centerY=points.reduce((sum,point)=>sum+point[1],0)/4;
    previewScreenCells.push({row,column,centerX,centerY,db});
  }
  if(selectedPairPixel){
    const cell=previewScreenCells.find((item)=>item.row===selectedPairPixel.row&&item.column===selectedPairPixel.column);
    if(cell){context.beginPath();context.arc(cell.centerX,cell.centerY,5,0,2*Math.PI);context.strokeStyle="#fff4d5";context.lineWidth=2;context.stroke();selectedPairPixel={...selectedPairPixel,...cell};}
    else selectedPairPixel=null;
  }
  return canvas.toDataURL("image/png");
}

function pairDisplayScale(record) {
  const samples=[];
  const {values_db:values,valid_mask:valid}=record.measurement;
  for(let row=0;row<values.length;row++)for(let column=0;column<values[row].length;column++){
    const value=values[row][column];
    if(valid[row][column]&&Number.isFinite(value))samples.push(Math.abs(value));
  }
  samples.sort((a,b)=>a-b);
  return samples.length?Math.max(samples[Math.min(samples.length-1,Math.floor((samples.length-1)*.98))],.1):0;
}

function operaAnalysisImage(x,y) {
  previewScreenCells=[];
  if(operaPairAnalysis?.status!=="DIAGNOSTIC_PRODUCT_MASKED_COMPARISON")return "";
  const values=operaPairAnalysis.measurement.values_db;
  const valid=operaPairAnalysis.measurement.valid_mask;
  const corners=operaPairAnalysis.grid.pixel_corners_wgs84;
  const scale=operaDisplayScale||0;
  if(!scale||!corners)return "";
  const canvas=document.createElement("canvas");canvas.width=1000;canvas.height=600;
  const context=canvas.getContext("2d");context.globalAlpha=.91;
  for(let row=0;row<values.length;row++)for(let column=0;column<(values[row]?.length||0);column++){
    const db=values[row][column];
    if(!valid[row][column]||!Number.isFinite(db))continue;
    const points=[corners[row][column],corners[row][column+1],corners[row+1][column+1],corners[row+1][column]].map(([longitude,latitude])=>[x(longitude),y(latitude)]);
    context.beginPath();context.moveTo(points[0][0],points[0][1]);
    for(let index=1;index<points.length;index++)context.lineTo(points[index][0],points[index][1]);
    context.closePath();
    const fraction=Math.max(-1,Math.min(1,db/scale));
    const strength=Math.abs(fraction),base=fraction<0?[77,120,196]:[212,91,86],neutral=[233,231,219];
    context.fillStyle="rgb("+neutral.map((channel,index)=>Math.round(channel+(base[index]-channel)*strength)).join(",")+")";context.fill();
    const centerX=points.reduce((sum,point)=>sum+point[0],0)/4,centerY=points.reduce((sum,point)=>sum+point[1],0)/4;
    previewScreenCells.push({row,column,centerX,centerY,db});
  }
  if(selectedOperaPixel){
    const cell=previewScreenCells.find((item)=>item.row===selectedOperaPixel.row&&item.column===selectedOperaPixel.column);
    if(cell){context.beginPath();context.arc(cell.centerX,cell.centerY,5,0,2*Math.PI);context.strokeStyle="#fff4d5";context.lineWidth=2;context.stroke();selectedOperaPixel={...selectedOperaPixel,...cell};}
    else selectedOperaPixel=null;
  }
  return canvas.toDataURL("image/png");
}

function rasterPixelAt(localX,localY) {
  let nearest=null,distance=Infinity;
  for(const cell of previewScreenCells){
    const current=Math.hypot(cell.centerX-localX,cell.centerY-localY);
    if(current<distance){distance=current;nearest=cell;}
  }
  return distance<=14?nearest:null;
}

function drawMap() {
  const contextMode=Boolean(dswxContextVisible&&dswxContext);
  document.body.classList.toggle("dswx-context-mode",contextMode);
  const {query} = catalog;
  const displayed = displayedFeatures();
  const activeFeatures=operaPairAnalysis&&operaCatalog?operaCatalog.features:catalog.features;
  const features = contextMode?[]:(activeFeatures||[]).slice(0,60);
  const selectedFeature=contextMode?null:chronologicalFeatures().find((feature)=>feature.properties.fileID===selectedSceneId);
  if(!contextMode&&!operaPairAnalysis&&selectedFeature&&!features.some((item)=>item.properties.fileID===selectedFeature.properties.fileID))features.push(selectedFeature);
  if(!contextMode&&!operaPairAnalysis)displayed.forEach((feature)=>{
    if(feature&&!features.some((item)=>item.properties.fileID===feature.properties.fileID))features.push(feature);
  });
  if(!contextMode&&pair&&!operaPairAnalysis)features.sort((a,b)=>{
    const rank=(feature)=>feature.properties.fileID===selectedSceneId?3:feature.properties.fileID===pair.before_scene?1:feature.properties.fileID===pair.after_scene?2:0;
    return rank(a)-rank(b);
  });
  const width = 1000, height = 600, pad = {l:78,r:32,t:35,b:43};
  const focusArea=contextMode?dswxContext.aoi.bounds_west_south_east_north:operaPairAnalysis?.grid?.window?.bounds_wgs84||areaBounds||areaFocusBounds;
  const center=focusArea
    ? [(focusArea[0]+focusArea[2])/2,(focusArea[1]+focusArea[3])/2]
    : geographicCenter(query);
  const focusPadding=focusArea
    ? Math.max(Math.max(focusArea[2]-focusArea[0],focusArea[3]-focusArea[1])*0.15,0.00001)
    : 0.06;
  const bounds = focusArea
    ? getBounds([], center, focusArea, focusPadding)
    : getBounds(features, center, areaPreview || query.bounds_wgs84);
  const centerX = (bounds.minX + bounds.maxX) / 2 + mapPan[0], centerY = (bounds.minY + bounds.maxY) / 2 + mapPan[1];
  const spanX = (bounds.maxX - bounds.minX) / zoom, spanY = (bounds.maxY - bounds.minY) / zoom;
  const view = {minX:centerX-spanX/2,maxX:centerX+spanX/2,minY:centerY-spanY/2,maxY:centerY+spanY/2};
  const x = (lon) => pad.l + ((lon-view.minX)/(view.maxX-view.minX))*(width-pad.l-pad.r);
  const y = (lat) => pad.t + ((view.maxY-lat)/(view.maxY-view.minY))*(height-pad.t-pad.b);
  const plotWidth=width-pad.l-pad.r, plotHeight=height-pad.t-pad.b;
  mapTransform={view,pad,width,height,plotWidth,plotHeight};
  svg.setAttribute("viewBox","0 0 1000 600");
  const operaAfterTime=operaPairAnalysis?.source_products?.after?.acquisition_start_utc;
  const imageDate=contextMode?dswxContext.source_products[dswxContextDate].acquisition_time_utc.slice(0,10):operaPairAnalysis&&operaAfterTime?operaAfterTime.slice(0,10):basemapDate(displayed);
  const imageURL=!contextMode&&basemapEnabled && imageDate ? gibsImageURL(view,plotWidth,plotHeight,imageDate) : null;
  const imageMarkup=imageURL ? `<image class="gibs-basemap" x="${pad.l}" y="${pad.t}" width="${plotWidth}" height="${plotHeight}" preserveAspectRatio="none" href="${escapeHTML(imageURL)}"/>` : "";
  const pairRaster=contextMode?null:operaAnalysisImage(x,y)||pairAnalysisImage(x,y);
  const rasterURL=pairRaster||(contextMode?null:rasterPreviewImage(x,y));
  const rasterMarkup=rasterURL?`<image class="gcov-raster-preview" x="0" y="0" width="1000" height="600" preserveAspectRatio="none" href="${rasterURL}"/>`:"";
  const dswxMarkup=contextMode?dswxContext.map_samples.map((sample,index)=>{
    const code=sample[dswxContextDate][dswxContextLayer];
    const points=sample.corners_wgs84.map(([lon,lat])=>`${x(lon)},${y(lat)}`).join(" ");
    return `<polygon class="dswx-context-cell${selectedDswxSample===index?" selected":""}" data-dswx-index="${index}" fill="${dswxCodeColor(dswxContextLayer,code)}" points="${points}"><title>${escapeHTML(dswxContextLayer)} ${code} · ${escapeHTML(dswxCodeLabel(dswxContextLayer,code))}</title></polygon>`;
  }).join(""):"";
  const grid = [];
  for (let i=0;i<=4;i++) {
    const gx=pad.l+i*(width-pad.l-pad.r)/4, lon=view.minX+i*(view.maxX-view.minX)/4;
    const gy=pad.t+i*(height-pad.t-pad.b)/4, lat=view.maxY-i*(view.maxY-view.minY)/4;
    grid.push(`<line class="grid-line" x1="${gx}" y1="${pad.t}" x2="${gx}" y2="${height-pad.b}"/><text class="grid-label" x="${gx}" y="${height-15}" text-anchor="middle">${Math.abs(lon).toFixed(2)}°${lon<0?'W':'E'}</text>`);
    grid.push(`<line class="grid-line" x1="${pad.l}" y1="${gy}" x2="${width-pad.r}" y2="${gy}"/><text class="grid-label" x="${pad.l-12}" y="${gy+3}" text-anchor="end">${Math.abs(lat).toFixed(2)}°${lat<0?'S':'N'}</text>`);
  }
  const shapes = features.map((feature) => {
    if(!feature.geometry)return "";
    const rings = feature.geometry.type === "Polygon" ? feature.geometry.coordinates : feature.geometry.coordinates.flat();
    const sceneId=feature.properties.fileID;
    const operaBefore=operaPairAnalysis?.source_products?.before?.scene_id;
    const operaAfter=operaPairAnalysis?.source_products?.after?.scene_id;
    const css = operaPairAnalysis&&sceneId===operaBefore?"footprint-before":operaPairAnalysis&&sceneId===operaAfter?"footprint-after":pair&&!operaPairAnalysis&&sceneId===pair.before_scene?"footprint-before":pair&&!operaPairAnalysis&&sceneId===pair.after_scene?"footprint-after":"footprint-catalog";
    const selected=sceneId===selectedSceneId?" footprint-selected":"";
    return rings.map((ring) => `<polygon class="${css}${selected}" data-scene-id="${escapeHTML(sceneId)}" points="${ring.map(([lon,lat])=>`${x(lon)},${y(lat)}`).join(" ")}"><title>ASF footprint · ${escapeHTML(sceneId)}</title></polygon>`).join("");
  }).join("");
  const px=x(center[0]), py=y(center[1]);
  if(contextMode){
    $(".case-chip b").textContent="NASA OPERA DSWx-HLS";
    $(".case-chip small").textContent="HLS optical classification context";
    $(".coordinate-readout").innerHTML=`${Math.abs(center[0]).toFixed(4)}° ${center[0]<0?"W":"E"}&nbsp;&nbsp; ${Math.abs(center[1]).toFixed(4)}° ${center[1]<0?"S":"N"} <span>CONTEXT AOI CENTER</span>`;
    $(".top-context").innerHTML='<span class="live-dot"></span> NASA OPTICAL CONTEXT <span class="slash">/</span> OPERA DSWX-HLS';
  }
  const area=contextMode?dswxContext.aoi.bounds_west_south_east_north:operaPairAnalysis?.grid?.window?.bounds_wgs84||areaPreview||areaBounds;
  const selection=area?`<rect class="aoi-selection" x="${x(area[0])}" y="${y(area[3])}" width="${Math.max(1,x(area[2])-x(area[0]))}" height="${Math.max(1,y(area[1])-y(area[3]))}"/>`:"";
  svg.classList.toggle("area-draw-mode",drawingArea);
  const pairMeasured=gcovPairAnalysis?.status==="MEASURED_DESCRIPTIVE_ONLY";
  svg.classList.toggle("gcov-raster-active",contextMode||Boolean(gcovPreview)||pairMeasured||Boolean(operaPairAnalysis));
  const pointLabel=operaPairAnalysis?"MEASUREMENT AOI CENTER":area?"AREA CENTER":"SEARCH POINT";
  svg.innerHTML = `${imageMarkup}${rasterMarkup}${dswxMarkup}${grid.join("")}<g>${shapes}</g>${selection}<line class="point-leader" x1="${px+10}" y1="${py-8}" x2="${px+75}" y2="${py-43}"/><text class="point-label" x="${px+80}" y="${py-46}">${pointLabel}</text><circle class="search-ring" cx="${px}" cy="${py}" r="10"/><circle class="search-dot" cx="${px}" cy="${py}" r="3.5"/>`;
  const warning=$("#mapWarning");
  const watermark=$(".map-watermark");
  const ramp=$("#previewRamp");
  ramp.hidden=!gcovPreview&&!pairMeasured&&!operaPairAnalysis;
  if(contextMode){
    ramp.hidden=true;
    warning.classList.remove("qa-preview");
    warning.innerHTML='<span class="warning-glyph">i</span><span><b>NASA OPTICAL CONTEXT</b><small>DSWx-HLS classification · not SAR · not ground truth</small></span>';
    watermark.classList.add("raster-preview");
    watermark.innerHTML="ECHO <span>·</span> NASA OPERA DSWX-HLS CONTEXT";
    $("#mapDataAttribution").textContent=`NASA OPERA DSWx-HLS · ${dswxContextLayer} · ${dswxDateLabel(dswxContextDate)} · OPTICAL CONTEXT ONLY`;
    const histogram=dswxContext.source_products[dswxContextDate].assets[dswxContextLayer].aoi_class_histogram;
    const classes=Object.entries(histogram).sort((a,b)=>Number(b[1])-Number(a[1])).slice(0,4);
    $("#dswxMapLegend").hidden=false;
    $("#dswxMapLegend").innerHTML=classes.map(([code])=>`<span><i data-layer="${escapeHTML(dswxContextLayer)}" data-code="${escapeHTML(code)}"></i>${escapeHTML(code)}</span>`).join("")+(Object.keys(histogram).length>4?"<span>+ classes</span>":"");
  }else if(operaPairAnalysis){
    $("#dswxMapLegend").hidden=true;
    const measured=operaPairAnalysis.status==="DIAGNOSTIC_PRODUCT_MASKED_COMPARISON";
    ramp.classList.add("pair-ramp");
    if(measured){
      const scale=operaDisplayScale||0;
      $("#previewRampRange").textContent="−"+scale.toFixed(2)+" to +"+scale.toFixed(2)+" dB";
      warning.classList.add("qa-preview");
      warning.innerHTML='<span class="warning-glyph">△</span><span><b>OPERA RTC-S1 DIAGNOSTIC COMPARISON</b><small>Product QA metadata available · no consolidated verdict · not validated</small></span>';
      watermark.classList.add("raster-preview");
      watermark.innerHTML="ECHO <span>·</span> SENTINEL-1 RTC-S1 LOG RATIO";
      $("#mapDataAttribution").textContent="NASA OPERA RTC-S1 · Sentinel-1 · "+operaPairAnalysis.measurement.polarization+" Δγ⁰ dB · QA METADATA / NO PASS-FAIL · NASA GIBS CONTEXT";
    }else{
      warning.classList.add("qa-preview");
      warning.innerHTML='<span class="warning-glyph">△</span><span><b>NO COMMON CLEAR VALID PIXELS</b><small>OPERA RTC-S1 masks leave no measured comparison in this AOI</small></span>';
      watermark.classList.remove("raster-preview");
      watermark.innerHTML="ECHO <span>·</span> OPERA PAIR · NO MEASUREMENT";
      $("#mapDataAttribution").textContent="NASA OPERA RTC-S1 · NO COMMON CLEAR PIXELS · QA METADATA / NO PASS-FAIL";
    }
  }else if(pairMeasured){
    $("#dswxMapLegend").hidden=true;
    const scale=pairChangeScale();
    ramp.classList.add("pair-ramp");
    $("#previewRampRange").textContent=`−${scale.toFixed(2)} to +${scale.toFixed(2)} dB`;
    warning.classList.add("qa-preview");
    warning.innerHTML=`<span class="warning-glyph">Δ</span><span><b>DESCRIPTIVE SAR CHANGE</b><small>${escapeHTML(gcovPairMaturityLabel())} · provider QA PASS · no event or cause inferred</small></span>`;
    watermark.classList.add("raster-preview");
    watermark.innerHTML="ECHO <span>·</span> NISAR GCOV LOG RATIO";
    $("#mapDataAttribution").textContent=`NISAR GCOV ${gcovPairMaturityLabel()} · ${gcovPairAnalysis.measurement.layer} · Δγ⁰ dB · PROVIDER QA PASS · NASA GIBS IS CONTEXT ONLY`;
  }else if(["QA_HELD","MATURITY_HELD"].includes(gcovPairAnalysis?.status)){
    $("#dswxMapLegend").hidden=true;
    ramp.classList.remove("pair-ramp");
    warning.classList.add("qa-preview");
    const maturityHeld=gcovPairAnalysis.status==="MATURITY_HELD";
    warning.innerHTML=`<span class="warning-glyph">△</span><span><b>PAIR ANALYSIS HELD</b><small>${maturityHeld?"Product maturity is unsupported":"Provider QA did not pass"} · no change pixels read</small></span>`;
    watermark.classList.remove("raster-preview");
    watermark.innerHTML=`ECHO <span>·</span> ${maturityHeld?"MATURITY":"QA"} GATE · NO CHANGE LAYER`;
    $("#mapDataAttribution").textContent=`PAIR ${maturityHeld?"MATURITY":"QA"} HOLD · NO MEASUREMENT LAYER · NASA GIBS IS CONTEXT ONLY`;
  }else if(gcovPreview){
    $("#dswxMapLegend").hidden=true;
    ramp.classList.remove("pair-ramp");
    const qaStatus=gcovPreview.source.provider_qa_status;
    const [lowDb,highDb]=gcovPreview.display_transform.stretch_range_db||[null,null];
    $("#previewRampRange").textContent=Number.isFinite(lowDb)&&Number.isFinite(highDb)?`${lowDb.toFixed(1)} to ${highDb.toFixed(1)} dB`:"no eligible pixels";
    warning.classList.add("qa-preview");
    warning.innerHTML=`<span class="warning-glyph">△</span><span><b>${qaStatus==="PASS"?"SINGLE-OBSERVATION SAR PREVIEW":"QA-HELD REAL SAR PREVIEW"}</b><small>Provider QA ${escapeHTML(qaStatus)} · no change result</small></span>`;
    watermark.classList.add("raster-preview");
    watermark.innerHTML="ECHO <span>·</span> NISAR GCOV PIXELS";
    $("#mapDataAttribution").textContent=`NISAR GCOV · ${gcovPreview.measurement.layer} · 10log₁₀ γ⁰ · PROVIDER QA ${qaStatus} · NASA GIBS IS CONTEXT ONLY`;
  }else{
    $("#dswxMapLegend").hidden=true;
    ramp.classList.remove("pair-ramp");
    warning.classList.remove("qa-preview");
    warning.innerHTML='<span class="warning-glyph">△</span><span><b>NO RADAR PIXELS LOADED</b><small>Footprints show ASF metadata coverage only</small></span>';
    watermark.classList.remove("raster-preview");
    watermark.innerHTML="ECHO <span>·</span> CATALOG VIEW";
    $("#mapDataAttribution").textContent=imageURL?`NASA GIBS · MODIS TERRA TRUE COLOR · ${imageDate} · CONTEXT ONLY`:basemapEnabled?"NASA GIBS DATE UNAVAILABLE · GRID SHOWN":"BASEMAP OFF · COORDINATE GRID";
  }
  const basemapLabel=$("#mapDataAttribution");
  const toggle=$("#toggleBasemap");
  ["#searchCatalog","#drawArea","#loadGcovPreview","#openOpera","#toggleBasemap"].forEach((selector)=>{const control=$(selector);if(control)control.disabled=contextMode;});
  $("#openDswxContext").setAttribute("aria-pressed",String(contextMode));
  $("#openDswxContext").textContent=contextMode?"OPTICAL CONTEXT ACTIVE":"NASA OPTICAL CONTEXT";
  toggle.setAttribute("aria-pressed",String(basemapEnabled));
  toggle.textContent=basemapEnabled ? "NASA CONTEXT ON" : "NASA CONTEXT OFF";
  if(!contextMode&&!gcovPreview&&!gcovPairAnalysis&&!operaPairAnalysis)basemapLabel.textContent=imageURL ? `NASA GIBS · MODIS TERRA TRUE COLOR · ${imageDate} · CONTEXT ONLY` : basemapEnabled ? "NASA GIBS DATE UNAVAILABLE · GRID SHOWN" : "BASEMAP OFF · COORDINATE GRID";
  const image=svg.querySelector(".gibs-basemap");
  image?.addEventListener("error",()=>{
    image.remove();
    basemapLabel.textContent=`NASA GIBS UNAVAILABLE · ${imageDate} · GRID SHOWN`;
  },{once:true});
  syncAreaButton();
  if(contextMode)$("#previewInspector").hidden=true;else renderGcovPreviewDetails();
  renderMapCaption();
}

function syncAreaButton() {
  const button=$("#drawArea");
  if(!button)return;
  const full=areaBounds?"CLEAR AREA":drawingArea?"CANCEL AREA":"SELECT AREA";
  button.textContent=window.innerWidth<420?(areaBounds?"CLEAR":drawingArea?"CANCEL":"AREA"):full;
  button.setAttribute("aria-label",full);
  button.title=full;
  button.setAttribute("aria-pressed",String(drawingArea));
}

function mapCoordinate(event) {
  const point=svg.createSVGPoint();
  point.x=event.clientX; point.y=event.clientY;
  const local=point.matrixTransform(svg.getScreenCTM().inverse());
  const {view,pad,plotWidth,plotHeight}=mapTransform;
  const plotX=Math.max(pad.l,Math.min(pad.l+plotWidth,local.x));
  const plotY=Math.max(pad.t,Math.min(pad.t+plotHeight,local.y));
  return [
    Math.max(-180,Math.min(180,view.minX+(plotX-pad.l)/plotWidth*(view.maxX-view.minX))),
    Math.max(-90,Math.min(90,view.maxY-(plotY-pad.t)/plotHeight*(view.maxY-view.minY))),
  ];
}

function renderDetails(sceneId=selectedSceneId) {
  const feature=chronologicalFeatures().find((item)=>item.properties.fileID===sceneId);
  if (!feature) {
    selectedSceneId=null;
    $("#sceneDetails").innerHTML='<div class="full"><dt>OBSERVATION</dt><dd>No acquisitions match this catalog query.</dd></div>';
    $(".evidence-count").innerHTML=`00 <i>/</i> ${String(catalog.feature_count||0).padStart(2,"0")}`;
    return;
  }
  selectedSceneId=feature.properties.fileID;
  const p = feature.properties;
  const qaStatus = providerQAStatus(p.fileID);
  const report = qaReports.records.find((item) => item.scene_id === p.fileID);
  const bytes = Object.values(p.bytes || {}).find((file) => file.format === "HDF5")?.bytes;
  const size = bytes ? `${(bytes/1e9).toFixed(2)} GB` : "HDF5";
  const time = Number.isFinite(Date.parse(p.startTime)) ? new Date(p.startTime).toISOString().replace("T"," ").replace(".000Z"," UTC") : "UNKNOWN · PROVIDER TIMESTAMP INVALID OR MISSING";
  $("#sceneDetails").innerHTML = [
    ["ACQUISITION",time], ["TEMPORAL ROLE",sceneRole(p.fileID)], ["MATURITY",catalog.query.data_maturity], ["PRODUCT","GCOV · L2"], ["QA SUMMARY",qaStatus], ["QA REPORT",report?`v${report.qa_software_version} · METADATA RECORDED`:"NOT RETAINED"], ["POLARIZATION",(p.mainBandPolarization||[]).join(" / ")], ["ORBIT",`${p.flightDirection} · PATH ${p.pathNumber}`], ["FRAME",`${p.frameNumber} · ${p.frameCoverage||"UNKNOWN"}`], ["FILE SIZE",size], ["SCENE ID",p.fileID,true]
  ].map(([label,value,full])=>`<div class="${full?'full':''}"><dt>${escapeHTML(label)}</dt><dd title="${escapeHTML(value)}">${escapeHTML(value)}</dd></div>`).join("");
  const ordered=chronologicalFeatures();
  const position=ordered.findIndex((item)=>item.properties.fileID===p.fileID)+1;
  $(".evidence-count").innerHTML=`${String(position).padStart(2,"0")} <i>/</i> ${String(ordered.length).padStart(2,"0")}`;
  document.querySelectorAll(".timeline-observation").forEach((button)=>{
    const selected=button.dataset.sceneId===selectedSceneId;
    button.classList.toggle("selected",selected);
    button.setAttribute("aria-pressed",String(selected));
  });
  const previewButton=$("#loadGcovPreview");
  const layerSelect=$("#previewLayer");
  const priorLayer=layerSelect.value;
  const layers=availableDiagonalLayers(p);
  layerSelect.innerHTML=layers.map((layer)=>`<option value="${layer}">${layer}</option>`).join("");
  if(layers.includes(priorLayer))layerSelect.value=priorLayer;
  layerSelect.disabled=p.processingLevel!=="GCOV"||layers.length===0;
  $("#previewFrequency").disabled=p.processingLevel!=="GCOV";
  previewButton.disabled=!selectedSceneId||!areaBounds||p.processingLevel!=="GCOV"||layers.length===0;
  previewButton.textContent=gcovPreview?.source?.scene_id===selectedSceneId?"HIDE BACKSCATTER":"LOAD BACKSCATTER";
  previewButton.title=!areaBounds?"Select a WGS84 map area first":!layers.length?"The catalog record does not identify a supported real-valued diagonal layer":"Read one bounded GCOV backscatter window with its QA and mask records";
  renderGcovPreviewDetails();
}

function renderGcovPreviewDetails() {
  const section=$("#previewInspector");
  if(operaPairAnalysis){
    const record=operaPairAnalysis;
    const measured=record.status==="DIAGNOSTIC_PRODUCT_MASKED_COMPARISON";
    const products=record.source_products||{};
    const rows=["before","after"].map((role)=>{
      const source=products[role]||{};
      const asset=source.assets?.measurement||{};
      const qa=source.quality_metadata||{};
      const geo=qa.geometric_accuracy||{};
      const rfi=qa.radio_frequency_interference||{};
      const assetLink=typeof asset.url==="string"&&asset.url.startsWith("https://datapool.asf.alaska.edu/RTC/OPERA-S1/")
        ?"<br><a href=\""+escapeHTML(asset.url)+"\" target=\"_blank\" rel=\"noopener noreferrer\">Open ASF RTC-S1 asset ↗</a>":"";
      const metadataAsset=source.assets?.metadata||{};
      const metadataLink=typeof metadataAsset.url==="string"&&metadataAsset.url.startsWith("https://datapool.asf.alaska.edu/RTC/OPERA-S1/")
        ?"<br><a href=\""+escapeHTML(metadataAsset.url)+"\" target=\"_blank\" rel=\"noopener noreferrer\">Open QA metadata sidecar ↗</a>":"";
      const qaSummary="<br>Geometric QA bias x/y: "+escapeHTML(geo.geometric_accuracy_bias_x?.value??"missing")+" / "+escapeHTML(geo.geometric_accuracy_bias_y?.value??"missing")+"; stddev x/y: "+escapeHTML(geo.geometric_accuracy_stddev_x?.value??"missing")+" / "+escapeHTML(geo.geometric_accuracy_stddev_y?.value??"missing")+"<br>RFI info available: "+escapeHTML(rfi.rfi_info_available?.value??"unknown")+" · mitigation: "+escapeHTML(rfi.rfi_mitigation_performed?.value??"not reported")+" · domain: "+escapeHTML(rfi.rfi_mitigation_domain?.value??"not reported")+" · no scene-level clearance verdict";
      return "<div><dt>"+role.toUpperCase()+" · OPERA RTC-S1 / SENTINEL-1</dt><dd>"+escapeHTML(source.acquisition_start_utc)+" UTC · "+escapeHTML(source.scene_id)+"<br>"+escapeHTML(source.product_version)+" · "+escapeHTML(source.sensor)+" · "+escapeHTML(source.burst_id)+qaSummary+assetLink+metadataLink+"</dd></div>";
    }).join("");
    const measurement=record.measurement||{};
    const selected=selectedOperaPixel;
    const pixel=selected
      ?"<p class=\"pair-value-readout\"><b>Selected pixel</b> · row "+selected.row+", column "+selected.column+" · "+selected.db.toFixed(3)+" dB</p>"
      :"<p>Click a valid map cell to inspect its signed gamma-zero log-ratio.</p>";
    const mask=measurement.mask_counts||{};
    section.hidden=false;
    section.innerHTML="<h3>OPERA RTC-S1 · "+(measured?"DIAGNOSTIC MASKED COMPARISON":"INCONCLUSIVE PAIR")+"</h3><p>"+(measured?"Descriptive Sentinel-1-derived gamma-zero log-ratio only. Per-product QA metadata are shown below, but the products provide no consolidated PASS/FAIL verdict; this is not a validated event finding.":"No common clear valid pixels were available in the selected AOI.")+"</p><dl>"+rows+
      "<div><dt>PROVIDER QA</dt><dd>PRODUCT METADATA RETRIEVED · NO CONSOLIDATED PASS/FAIL · diagnostic only</dd></div>"+
      "<div><dt>MEASUREMENT</dt><dd>"+escapeHTML(measurement.quantity||"not computed")+" · "+escapeHTML(measurement.polarization||"")+" · "+escapeHTML(measurement.units||"")+"<br>"+(measurement.measured_pixel_count||0)+" measured of "+(measurement.aoi_pixel_count||0)+" AOI centers · "+escapeHTML(record.grid?.crs||"grid unknown")+"</dd></div>"+
      "<div><dt>MASK COUNTS</dt><dd>"+(mask.before_clear||0)+" before clear · "+(mask.after_clear||0)+" after clear · "+(mask.before_shadow_affected||0)+" / "+(mask.after_shadow_affected||0)+" shadow-affected · "+(mask.before_layover_affected||0)+" / "+(mask.after_layover_affected||0)+" layover-affected</dd></div>"+
      "<div><dt>DISPLAY</dt><dd>Symmetric ±"+(operaDisplayScale||0).toFixed(2)+" dB stretch · display only</dd></div>"+
      "<div class=\"full\"><dt>LIMITS</dt><dd>No flood boundary, damage, event, cause, or independent validation is inferred. OPERA RTC-S1 is distinct from NISAR.</dd></div></dl>"+pixel+
      "<div class=\"preview-actions\"><button type=\"button\" id=\"operaRecordButton\">INSPECT FULL RECORD</button><button type=\"button\" id=\"downloadOperaRecordButton\">DOWNLOAD REPRODUCTION RECORD</button><button type=\"button\" id=\"startPairInvestigationDraft\">START INVESTIGATION DRAFT</button></div>";
    $("#operaRecordButton").addEventListener("click",()=>{$("#recordJson").textContent=JSON.stringify(record,null,2);$("#recordDialog .eyebrow").textContent="SOURCE RECORD · OPERA RTC-S1";$("#recordDialog h2").textContent="Diagnostic pair analysis";$("#recordDialog").showModal();});
    $("#downloadOperaRecordButton").addEventListener("click",()=>downloadJSON(record,"echo-opera-rtc-s1-"+record.status.toLowerCase()+".json"));
    $("#startPairInvestigationDraft").addEventListener("click",()=>openInvestigationDraft(record));
    return;
  }
  if(gcovPairAnalysis){
    const record=gcovPairAnalysis;
    const sourceProducts=record.source_products||{};
    const productMaturity=gcovPairMaturityLabel(record);
    const cards=Object.entries(record.provider_qa||{}).map(([role,qa])=>{
      const evidence=qa.evidence||{};
      const uri=trustedQASummaryURI(qa);
      const link=uri?`<br><a class="pair-evidence-link" href="${escapeHTML(uri)}" target="_blank" rel="noopener noreferrer">Open original ASF QA summary ↗</a>`:"<br>Original ASF summary link unavailable or did not validate";
      const checks=(evidence.check_details||[]).map(check=>{
        const result=String(check.result||"UNKNOWN").toUpperCase();
        const resultClass=["PASS","FAIL","WARNING","SKIPPED","NOT_RUN"].includes(result)?result.toLowerCase():"unknown";
        return `<li><b class="qa-result-${resultClass}">${escapeHTML(result)}</b><span>${escapeHTML(check.check||"Unnamed provider check")}</span>${check.notes?`<small>${escapeHTML(check.notes)}</small>`:""}</li>`;
      }).join("");
      const checkDetails=checks?`<details class="pair-check-details"><summary>INSPECT PROVIDER CHECKS (${(evidence.check_details||[]).length})</summary><ul>${checks}</ul></details>`:"<small class=\"pair-check-missing\">Provider check rows unavailable.</small>";
      const source=sourceProducts[role]||{};
      const productLink=source.product_url?`<br><a class="pair-evidence-link" href="${escapeHTML(source.product_url)}" target="_blank" rel="noopener noreferrer">ASF product record ↗</a>`:"";
      return `<div><dt>${role.toUpperCase()} PRODUCT · ${escapeHTML(source.mission||"NISAR")} ${escapeHTML(source.product||"GCOV")}</dt><dd>${escapeHTML(source.acquisition_start_utc)} – ${escapeHTML(source.acquisition_stop_utc)} UTC<br>${escapeHTML(source.collection)} · ${escapeHTML(source.processing_level)} · orbit ${escapeHTML(source.orbit)}<br>${escapeHTML(source.scene_id)}${productLink}</dd></div><div><dt>${role.toUpperCase()} PROVIDER QA</dt><dd class="${evidence.status==="FAIL"?"qa-fail":""}">${escapeHTML(evidence.status||"UNKNOWN")}<br>Retrieved ${escapeHTML(qa.retrieved_at_utc)} · ${escapeHTML(qa.artifact_size_bytes)} B<br>SHA-256 ${escapeHTML(qa.artifact_sha256)}${link}${checkDetails}</dd></div>`;
    }).join("");
    let resultDetails="";
    if(["QA_HELD","MATURITY_HELD"].includes(record.status)){
      const gates=record.analysis_gates||{};
      const gateRows=Object.entries(gates).map(([name,status])=>`<div><dt>${escapeHTML(name.replaceAll("_"," "))}</dt><dd>${escapeHTML(status)}</dd></div>`).join("");
      const nextEvidence=(record.next_evidence||[]).map(item=>`<li>${escapeHTML(item)}</li>`).join("");
      const maturityHeld=record.status==="MATURITY_HELD";
      resultDetails=`<h3>${maturityHeld?"PAIR HELD AT PRODUCT MATURITY GATE":"PAIR HELD AT PROVIDER QA GATE"}</h3><p>${maturityHeld?"Provider QA passed, but the product maturity and documented limitations prevent comparison.":"Provider QA did not pass for every selected product."} No radar measurement arrays were read and no comparison result exists.</p><dl>${cards}<div class="full"><dt>ANALYSIS GATES</dt><dd><div class="pair-gate-grid">${gateRows}</div></dd></div><div class="full"><dt>NEXT EVIDENCE REQUIRED</dt><dd><ul class="pair-next-evidence">${nextEvidence}</ul></dd></div><div class="full"><dt>DISPOSITION</dt><dd>Held roles: ${escapeHTML((record.held_roles||[]).join(", ")||"unknown")} · Measurement: none · Analysis manifest: none</dd></div></dl>`;
    }else{
      const measurement=record.measurement;
      const grid=record.grid;
      const manifest=record.manifest||{};
      const windowShape=grid.window_shape||[];
      const selected=selectedPairPixel;
      const pixel=selected?`<p class="pair-value-readout"><b>Selected pixel</b> · row ${selected.row}, column ${selected.column} · ${selected.db.toFixed(3)} dB</p>`:"<p>Click a valid map pixel to inspect its signed backscatter log-ratio.</p>";
      resultDetails=`<h3>DESCRIPTIVE NISAR GCOV COMPARISON · ${escapeHTML(productMaturity)} · PROVIDER QA PASS</h3><p>Mapped quantity: 10 log₁₀(after γ⁰ / before γ⁰). This is a measured backscatter difference; it does not identify an event or physical cause. Product maturity and provider QA are separate checks.</p><dl><div><dt>MEASUREMENT</dt><dd>${escapeHTML(measurement.layer)} · frequency ${escapeHTML(measurement.frequency)} · ${escapeHTML(measurement.units)}<br>${windowShape[1]} × ${windowShape[0]} pixels · EPSG:${escapeHTML(grid.epsg_code)}</dd></div><div><dt>COMMON VALID PIXELS</dt><dd>${measurement.common_valid_mask.flat().filter(Boolean).length.toLocaleString()} of ${measurement.valid_mask.flat().length.toLocaleString()} grid cells</dd></div><div><dt>DISPLAY STRETCH</dt><dd>±${pairChangeScale().toFixed(2)} dB · 98th percentile of absolute valid values<br>Display-only scaling; not an analysis threshold</dd></div><div class="full"><dt>ANALYSIS MANIFEST</dt><dd>${escapeHTML(manifest.analysis?.method||"Reproducible analysis record available")} · alignment ${escapeHTML(manifest.grid_alignment?.status||"recorded")}<br>Created ${escapeHTML(record.created_at_utc)}</dd></div>${cards}</dl>${pixel}`;
    }
    section.hidden=false;
    section.innerHTML=`${resultDetails}<div class="preview-actions"><button type="button" id="pairRecordButton">INSPECT FULL RECORD</button><button type="button" id="downloadPairRecordButton">DOWNLOAD REPRODUCTION RECORD</button><button type="button" id="startPairInvestigationDraft">START INVESTIGATION DRAFT</button></div>`;
    $("#pairRecordButton").addEventListener("click",()=>{$("#recordJson").textContent=JSON.stringify(record,null,2);$("#recordDialog").showModal();});
    $("#downloadPairRecordButton").addEventListener("click",()=>downloadJSON(record,`echo-gcov-pair-${record.status.toLowerCase()}.json`));
    $("#startPairInvestigationDraft").addEventListener("click",()=>openInvestigationDraft(record));
    return;
  }
  if(!gcovPreview){section.hidden=true;section.innerHTML="";return;}
  const record=gcovPreview;
  const source=record.source;
  const qa=source.provider_qa_summary;
  const status=source.provider_qa_status||"UNKNOWN";
  const quality=record.measurement.quality;
  const window=record.grid.window;
  const stretch=record.display_transform.stretch_range_db;
  const stretchLabel=stretch?`${stretch[0].toFixed(2)} to ${stretch[1].toFixed(2)} dB`:"No eligible sample values";
  const exceptionCodes=Object.entries(quality.input_data_exception_code_counts||{}).map(([code,count])=>`code ${escapeHTML(code)}: ${Number(count).toLocaleString()}`).join(" · ")||"not reported";
  const qualityNote=quality.display_eligible_pixel_count===0?`<p class="preview-quality-note"><b>NO PIXELS SHOWN</b> · ${quality.aoi_pixel_center_count.toLocaleString()} AOI centers were read, but none met ECHO's current display-quality screen. Input-data exception-mask values: ${exceptionCodes}. ECHO does not interpret unrecognized codes; flagged samples remain excluded and are retained in the source record.</p>`:"";
  const exceptionEncoding=quality.input_data_exception_mask_encoding||"UNRECOGNIZED";
  const exceptionPolarization=quality.input_data_exception_mask_polarization;
  const exceptionFlag=quality.input_data_exception_mask_polarization_flag;
  const exceptionExplanation=exceptionFlag?`${exceptionEncoding} · ${escapeHTML(exceptionPolarization)} focused-data bit ${exceptionFlag}, read from the product attribute`:`${exceptionEncoding} · raw values ${exceptionCodes}`;
  const selected=selectedPreviewPixel;
  const pixelDetails=selected?`<p class="preview-pixel-readout"><b>Selected pixel</b> · row ${selected.row+window.row_start}, column ${selected.column+window.column_start} · γ⁰ ${selected.raw.toPrecision(6)} linear · ${selected.db.toFixed(2)} dB · mask ${selected.mask} · ${escapeHTML(selected.looks)} looks · exception mask ${selected.exception}</p>`:"<p>Click a rendered pixel to inspect its product value and quality codes.</p>";
  section.hidden=false;
  const qaLink=trustedQASummaryURI(qa);
  section.innerHTML=`<h3>REAL NISAR GCOV · ${status==="PASS"?"SINGLE-OBSERVATION PREVIEW":"QA-HELD DIAGNOSTIC PREVIEW"}</h3><p>This is one acquisition. It shows gamma-zero backscatter; it is not a change measurement or an event interpretation.</p><dl><div><dt>PROVIDER / PRODUCT</dt><dd>${escapeHTML(source.provider)} · ${escapeHTML(source.product)}<br>${escapeHTML(source.scene_id)}</dd></div><div><dt>ACQUISITION UTC</dt><dd>${escapeHTML(source.catalog_metadata.startTime)} · ${escapeHTML(source.catalog_metadata.stopTime)}</dd></div><div><dt>MEASUREMENT</dt><dd>${escapeHTML(record.measurement.dataset)}<br>${escapeHTML(record.measurement.units)} · Frequency ${escapeHTML(record.measurement.frequency)}</dd></div><div><dt>PROVIDER QA</dt><dd class="${status==="FAIL"?"qa-fail":""}">${escapeHTML(status)} · ${escapeHTML(qa.artifact_size_bytes)} B · retrieved ${escapeHTML(qa.retrieved_at_utc)}${qaLink?`<br><a href="${escapeHTML(qaLink)}" target="_blank" rel="noopener noreferrer">Open original ASF QA summary ↗</a>`:""}</dd></div><div><dt>WINDOW / GRID</dt><dd>${window.shape[1]} × ${window.shape[0]} pixels · EPSG:${record.grid.epsg_code}<br>${quality.aoi_pixel_center_count.toLocaleString()} AOI centers</dd></div><div><dt>DISPLAY MASK</dt><dd>${quality.display_eligible_pixel_count.toLocaleString()} shown · ${quality.excluded_nonvalid_mask_count} nonvalid · ${quality.excluded_exception_count} exception · ${quality.excluded_unfocused_count||0} unfocused · ${quality.excluded_unknown_exception_count||0} unknown · ${quality.excluded_nonfinite_or_nonpositive_count} nonfinite/nonpositive</dd></div><div><dt>EXCEPTION MASK</dt><dd>${exceptionExplanation}</dd></div><div><dt>DISPLAY SCALE</dt><dd>10 log₁₀(linear γ⁰) · ${escapeHTML(stretchLabel)}<br>2nd–98th percentile stretch</dd></div><div><dt>ACCESS</dt><dd>${escapeHTML(record.provenance.window_access_method)} · ${Number(record.provenance.fsspec_range_bytes_requested).toLocaleString()} range bytes</dd></div><div class="full"><dt>QA SUMMARY SHA-256</dt><dd>${escapeHTML(record.provenance.provider_qa_artifact_sha256)}</dd></div></dl>${qualityNote}${pixelDetails}<div class="preview-actions"><button type="button" id="previewRecordButton">INSPECT FULL RECORD</button><button type="button" id="downloadPreviewButton">DOWNLOAD REPRODUCTION RECORD</button></div>`;
  $("#previewRecordButton").addEventListener("click",()=>{
    $("#recordJson").textContent=JSON.stringify(record,null,2);
    $("#recordDialog").showModal();
  });
  $("#downloadPreviewButton").addEventListener("click",downloadPreviewRecord);
}

function openOperaDialog() {
  $("#operaStart").value=catalog?.query?.start_date||"2024-04-25";
  $("#operaEnd").value=catalog?.query?.end_date||"2024-06-30";
  $("#operaAreaNote").textContent=areaBounds
    ?"AOI · "+areaBounds.map((value)=>value.toFixed(5)).join(", ")+" WGS84"
    :"Select a rectangular AOI on the map before searching.";
  $("#operaDialog").showModal();
}

function operaCandidates() {
  return (operaCatalog?.burst_series||[]).flatMap((series)=>series.adjacent_date_candidates||[]);
}

function selectedOperaCandidate() {
  const index=Number($("#operaPair").value);
  return Number.isInteger(index)?operaCandidates()[index]||null:null;
}

function operaFeatureForScene(sceneId) {
  return operaCatalog?.features?.find((feature)=>feature.properties?.fileID===sceneId)||null;
}

function renderOperaCandidates() {
  const candidates=operaCandidates();
  const selector=$("#operaPair");
  if(!candidates.length){
    selector.innerHTML='<option value="">No repeated-burst date candidates found</option>';
    selector.disabled=true;
    $("#analyzeOperaPair").disabled=true;
    $("#operaCandidateDetails").hidden=true;
    return;
  }
  selector.innerHTML=candidates.map((candidate,index)=>{
    const series=operaCatalog.burst_series.find((item)=>item.adjacent_date_candidates.includes(candidate));
    return '<option value="'+index+'">'+escapeHTML(candidate.before_acquisition_start_utc.slice(0,10))+" → "+escapeHTML(candidate.after_acquisition_start_utc.slice(0,10))+" · "+candidate.interval_days.toFixed(1)+" d · "+escapeHTML(series.burst_id)+" · "+escapeHTML(series.platform)+"</option>";
  }).join("");
  selector.disabled=false;
  selector.value="0";
  const preferred=review?.primary_opera_pair;
  if(preferred?.before_scene_id&&preferred?.after_scene_id){
    const match=candidates.findIndex((candidate)=>candidate.before_scene_id===preferred.before_scene_id&&candidate.after_scene_id===preferred.after_scene_id);
    if(match>=0)selector.value=String(match);
  }
  updateOperaCandidateDetails();
}

function updateOperaCandidateDetails() {
  const candidate=selectedOperaCandidate();
  const details=$("#operaCandidateDetails");
  if(!candidate){details.hidden=true;$("#analyzeOperaPair").disabled=true;return;}
  const before=operaFeatureForScene(candidate.before_scene_id)?.properties||{};
  const after=operaFeatureForScene(candidate.after_scene_id)?.properties||{};
  details.hidden=false;
  details.innerHTML="<p><b>METADATA CANDIDATE ONLY</b> · repeated burst identity does not verify grid registration, provider QA, or common valid coverage.</p><dl><div><dt>BEFORE</dt><dd>"+escapeHTML(before.startTime)+" · "+escapeHTML(candidate.before_scene_id)+"</dd></div><div><dt>AFTER</dt><dd>"+escapeHTML(after.startTime)+" · "+escapeHTML(candidate.after_scene_id)+"</dd></div></dl>";
  $("#analyzeOperaPair").disabled=!areaBounds;
}

async function searchOperaCatalog() {
  if(!areaBounds){$("#operaStatus").textContent="Draw a WGS84 rectangle on the map first.";return;}
  if(operaPairAnalysis)clearOperaView();
  const button=$("#searchOpera");button.disabled=true;button.textContent="SEARCHING ASF…";
  $("#operaStatus").textContent="Searching OPERA RTC-S1 metadata; no raster assets are requested.";
  operaCatalog=null;operaPairAnalysis=null;selectedOperaPixel=null;operaDisplayScale=null;
  $("#operaPair").disabled=true;$("#analyzeOperaPair").disabled=true;
  try{
    const response=await fetch(caseApiURL("/api/opera-catalog"),{
      method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({bounds_wgs84:areaBounds,start_date:$("#operaStart").value,end_date:$("#operaEnd").value}),
    });
    const record=await response.json();
    if(!response.ok)throw new Error(record.error||"OPERA catalog search failed");
    if(record.record_type!=="ASF_OPERA_RTC_S1_CATALOG")throw new Error("Unexpected OPERA catalog response");
    operaCatalog=record;renderOperaCandidates();
    $("#operaStatus").textContent=record.returned_feature_count+" ASF records · "+record.metadata_candidate_count+" repeated-burst candidates · "+record.pagination.pages_retrieved+" pages · "+(record.potentially_truncated?"possibly truncated":"catalog cap not reached");
  }catch(error){$("#operaStatus").textContent=error.message;}
  finally{button.disabled=false;button.textContent="SEARCH OPERA CATALOG";}
}

function minimalOperaFeature(feature) {
  const allowed=["fileID","url","startTime","stopTime","collectionName","bytes","beamModeType","flightDirection","polarization","sensor","sceneName"];
  const properties={};
  for(const key of allowed)if(feature?.properties?.[key]!==undefined)properties[key]=feature.properties[key];
  return {properties};
}

async function analyzeOperaPair() {
  const candidate=selectedOperaCandidate();
  if(!candidate||!areaBounds)return;
  const before=operaFeatureForScene(candidate.before_scene_id),after=operaFeatureForScene(candidate.after_scene_id);
  if(!before||!after){$("#operaStatus").textContent="Selected ASF feature records are unavailable.";return;}
  const button=$("#analyzeOperaPair");button.disabled=true;button.textContent="READING WINDOWS…";
  $("#operaStatus").textContent="Reading the two capped RTC-S1 assets and masks for the selected AOI.";
  try{
    const response=await fetch(caseApiURL("/api/opera-pair-analysis"),{
      method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({before:minimalOperaFeature(before),after:minimalOperaFeature(after),bounds_wgs84:areaBounds,polarization:$("#operaPolarization").value}),
    });
    const record=await response.json();
    if(!response.ok)throw new Error(record.error||"OPERA RTC-S1 pair read failed");
    if(record.record_type!=="ECHO_OPERA_RTC_S1_PAIR_ANALYSIS")throw new Error("Unexpected OPERA pair response");
    operaPairAnalysis=record;selectedOperaPixel=null;
    if(!crossSensorAssessmentMatchesCurrentPair()){
      const wasVisible=crossSensorAssessmentVisible;
      crossSensorAssessmentVisible=false;renderCrossSensorAssessment();
      if(wasVisible)showToast("The linked assessment belongs to a different RTC-S1 pair and was closed.");
    }
    operaDisplayScale=record.status==="DIAGNOSTIC_PRODUCT_MASKED_COMPARISON"?pairDisplayScale(record):0;
    gcovPreview=null;selectedPreviewPixel=null;gcovPairAnalysis=null;selectedPairPixel=null;pairAnalysisDisplayScale=null;
    document.querySelector(".timeline-panel").hidden=true;
    $(".preview-options:not(.context-options)").hidden=true;
    $("#loadGcovPreview").hidden=true;
    $("#challengeButton").hidden=true;
    $(".top-context").innerHTML='<span class="live-dot"></span> INVESTIGATION WORKSPACE <span class="slash">/</span> OPERA RTC-S1 ALTERNATE SOURCE';
    $(".case-heading h1").textContent="OPERA RTC-S1 investigation";
    $(".case-heading .subtitle").textContent="Sentinel-1-derived pair · product QA metadata available, no consolidated verdict · diagnostic only";
    $(".case-status b").textContent="Diagnostic comparison";
    $(".case-status small").textContent="OPERA RTC-S1 · NOT NISAR";
    $(".case-chip b").textContent="OPERA RTC-S1 · selected AOI";
    $(".case-chip small").textContent=candidate.interval_days.toFixed(0)+" day metadata interval · "+candidate.before_scene_id;
    $("#sceneDetails").innerHTML=`<div><dt>BEFORE</dt><dd>${escapeHTML(candidate.before_acquisition_start_utc)} UTC</dd></div><div><dt>AFTER</dt><dd>${escapeHTML(candidate.after_acquisition_start_utc)} UTC</dd></div><div><dt>PRODUCT</dt><dd>NASA OPERA RTC-S1 · Sentinel-1 derived</dd></div><div><dt>POLARIZATION</dt><dd>${escapeHTML(record.measurement.polarization||"not available")}</dd></div><div><dt>PROVIDER QA</dt><dd>Product metadata retrieved · no consolidated PASS/FAIL</dd></div><div class="full"><dt>SCENE IDS</dt><dd>${escapeHTML(candidate.before_scene_id)}<br>${escapeHTML(candidate.after_scene_id)}</dd></div>`;
    $(".evidence-count").innerHTML='OPERA <i>/</i> PAIR';
    $(".finding-card p").textContent="A bounded OPERA RTC-S1 gamma-zero comparison was computed from two Sentinel-1-derived products. Product QA metadata were retrieved, but no consolidated PASS/FAIL verdict is provided; the measured response does not establish an event or cause.";
    $(".finding-meta b").textContent=record.status.replaceAll("_"," ");
    $(".confidence-block .readiness-value").innerHTML="DIAGNOSTIC <small>NO CONSOLIDATED QA VERDICT</small>";
    $(".confidence-block p").textContent="Descriptive raster comparison only. Product QA metadata are available; a consolidated provider disposition, independent evidence, and physical interpretation remain open.";
    $(".gate-count").textContent="1 HOLD · 2 OPEN";
    $(".gate-list").innerHTML='<li><span class="gate-icon review">!</span><span><b>Product QA</b><small>Per-product metadata retrieved; the sidecar has no consolidated PASS/FAIL disposition.</small></span><span class="gate-state review">OPEN</span></li><li><span class="gate-icon pass">✓</span><span><b>Raster grid and mask</b><small>CRS, affine transform, shape, and selected pixel centers checked.</small></span><span class="gate-state pass">MEASURED</span></li><li><span class="gate-icon open">○</span><span><b>Independent interpretation</b><small>No event boundary, cause, or independent reference assessment.</small></span><span class="gate-state open">OPEN</span></li>';
    $("#operaStatus").textContent="Pair record created · product QA metadata retrieved, no consolidated verdict · diagnostic only.";
    $("#clearOperaView").hidden=false;
    $("#clearOperaView").textContent=review?.primary_opera_pair?"RETURN TO CASE":"RETURN TO NISAR";
    renderDswxContextInspector();
    renderGcovPreviewDetails();drawMap();$("#operaDialog").close();
  }catch(error){$("#operaStatus").textContent=error.message;}
  finally{button.disabled=false;button.textContent="READ BOUNDED PAIR";}
}

function clearOperaView() {
  operaCatalog=null;operaPairAnalysis=null;selectedOperaPixel=null;operaDisplayScale=null;
  $("#clearOperaView").hidden=true;
  $(".preview-options:not(.context-options)").hidden=false;
  document.querySelector(".timeline-panel").hidden=false;
  $("#loadGcovPreview").hidden=false;
  $("#challengeButton").hidden=false;
  renderWorkspace();
}

function downloadJSON(record,filename){
  const blob=new Blob([JSON.stringify(record,null,2)],{type:"application/json"});
  const url=URL.createObjectURL(blob);const link=document.createElement("a");
  link.href=url;link.download=filename;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}

function downloadPreviewRecord() {
  if(!gcovPreview)return;
  const blob=new Blob([JSON.stringify(gcovPreview,null,2)],{type:"application/json"});
  const href=URL.createObjectURL(blob);
  const link=document.createElement("a");
  link.href=href;
  link.download=`${gcovPreview.source.scene_id}_echo-gcov-preview.json`;
  link.click();
  setTimeout(()=>URL.revokeObjectURL(href),1000);
}

function renderPairLegend() {
  for(const [key,sceneId] of [["before",pair?.before_scene],["after",pair?.after_scene]]){
    const item=$(`.legend-item.${key}`);
    const feature=chronologicalFeatures().find((entry)=>entry.properties.fileID===sceneId);
    item.hidden=!feature;
    if(feature){
      const timestamp=Date.parse(feature.properties.startTime);
      const label=Number.isFinite(timestamp)?new Date(timestamp).toLocaleDateString("en-GB",{day:"2-digit",month:"short",year:"numeric",timeZone:"UTC"}).toUpperCase():"TIME UNKNOWN";
      item.innerHTML=`<i class="legend-swatch ${key}"></i> ${key.toUpperCase()} · ${label}`;
    }
  }
}

function showToast(message) {
  const node=$("#toast"); node.textContent=message; node.classList.add("show");
  clearTimeout(toastTimer); toastTimer=setTimeout(()=>node.classList.remove("show"),3200);
}

async function fetchProviderQASummary(feature) {
  const p=feature.properties;
  const response=await fetch(caseApiURL("/api/qa-summary"),{
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({feature:{properties:{fileID:p.fileID,url:p.url,processingLevel:p.processingLevel,collectionName:p.collectionName}}}),
  });
  const record=await response.json();
  if(!response.ok)throw new Error(record.error||"Provider QA summary retrieval failed");
  return record;
}

function selectObservation(sceneId,{scrollTimeline=false}={}){
  if(!chronologicalFeatures().some((feature)=>feature.properties.fileID===sceneId))return;
  if(gcovPreview?.source?.scene_id!==sceneId){gcovPreview=null;selectedPreviewPixel=null;}
  renderDetails(sceneId);
  drawMap();
  if(scrollTimeline){
    [...document.querySelectorAll(".timeline-observation")]
      .find((button)=>button.dataset.sceneId===sceneId)
      ?.scrollIntoView({block:"nearest",inline:"center"});
  }
}

function renderWorkspace() {
  const ordered=chronologicalFeatures();
  const displayed=displayedFeatures();
  const candidateCount=availablePairs().length;
  if (pair && displayed.length !== 2) pair=null;
  const pairButton=$("#runPairAnalysis");
  if(pairButton){
    const pairReady=Boolean(pair&&areaBounds&&[pair.before_scene,pair.after_scene].every((sceneId)=>catalog?.features?.some((feature)=>feature.properties.fileID===sceneId)));
    if(!pairButton.hasAttribute("aria-busy"))pairButton.disabled=!pairReady;
    pairButton.title=pairReady?"Retrieve bounded windows after checking provider QA for both products":"Select a metadata pair and WGS84 area first";
  }
  if(!ordered.some((feature)=>feature.properties.fileID===selectedSceneId)){
    selectedSceneId=ordered.find((feature)=>feature.properties.fileID===pair?.before_scene)?.properties.fileID||ordered[0]?.properties.fileID||null;
  }
  renderTimeline();
  renderPairSelector();
  renderPairLegend();
  const gap=pair ? Math.round((Date.parse(displayed[1].properties.startTime)-Date.parse(displayed[0].properties.startTime))/86400000) : null;
  const queryCenter=geographicCenter(catalog.query);
  const event=review?.event?.name || (review?.case_id || `${Math.abs(queryCenter[1]).toFixed(2)}°${queryCenter[1]<0?"S":"N"} · ${Math.abs(queryCenter[0]).toFixed(2)}°${queryCenter[0]<0?"W":"E"} GCOV search`).replace(/[-_]/g," ");
  const status=review?.candidate_pair?.qa_status || review?.status || review?.review_status || (pair ? "METADATA_MATCH_ONLY" : catalog.feature_count ? "OBSERVATIONS FOUND" : "NO OBSERVATIONS");
  $(".top-context").innerHTML=`<span class="live-dot"></span> INVESTIGATION WORKSPACE <span class="slash">/</span> ${escapeHTML(review?.case_id || "CATALOG SEARCH")}`;
  $(".case-chip b").textContent=event;
  $(".case-chip small").textContent=review?.location_label|| (displayed[0]?`Path ${displayed[0].properties.pathNumber} · frame ${displayed[0].properties.frameNumber}`:"No selected acquisition");
  $(".case-heading h1").textContent=event;
  $(".case-heading .subtitle").textContent=review?.candidate_question || (pair ? `Two metadata-compatible acquisitions are ${gap} days apart. Their pixels have not been compared.` : catalog.feature_count ? `${catalog.feature_count} ASF catalog records. No metadata-compatible temporal pair was found.` : "No NISAR GCOV observations match this point and time range.");
  const statusNode=$(".case-status");
  statusNode.classList.toggle("qa-hold",String(status).includes("QA_HOLD") || String(status).includes("REVIEW_REQUIRED"));
  $(".case-status b").textContent=status.replaceAll("_"," ");
  $(".case-status small").textContent=review?.status_label|| (review?.candidate_pair?.crid?`PROCESSING RELEASE ${review.candidate_pair.crid}`:pair?`METADATA PAIR · ${catalog.query.data_maturity}`:"CATALOG ONLY · QA NOT REVIEWED");
  const identifiers=displayed.map((item)=>reviewProducts().find((record)=>record.scene_id===item.properties.fileID)?.qa_summary?.identification_group).filter(Boolean);
  $(".finding-card p").textContent=review?.summary || (review ? `ASF lists two ${catalog.query.data_maturity} NISAR GCOV acquisitions ${gap} days apart. ${identifiers.length===2?`Both QA summaries report identification-group ${identifiers[0]===identifiers[1]?identifiers[0].toLowerCase():"review findings"}.`:"Product QA evidence is recorded for this pair."}` : pair ? `ASF metadata matched two ${catalog.query.data_maturity} NISAR GCOV observations ${gap} days apart. This is a catalog candidate only; product QA, grid alignment, and common valid pixels are not verified.` : `${catalog.feature_count} NISAR GCOV metadata records returned. ECHO found no orbit-separated, non-overlapping temporal pair that meets its catalog matching rules.`);
  $(".finding-meta b").textContent=status.replaceAll("_"," ");
  const mapCenter=geographicCenter(catalog.query);
  $(".coordinate-readout").innerHTML=`${Math.abs(mapCenter[0]).toFixed(4)}° ${mapCenter[0]<0?"W":"E"}&nbsp;&nbsp; ${Math.abs(mapCenter[1]).toFixed(4)}° ${mapCenter[1]<0?"S":"N"} <span>${areaBounds?"AREA CENTER":areaFocusBounds?"AREA FOCUS":"SEARCH POINT"}</span>`;
  $("#searchCenterLegend").innerHTML=`<i class="legend-point"></i> ${operaPairAnalysis?"MEASUREMENT CENTER":"SEARCH CENTER"}`;
  $("#otherObservationLegend").hidden=(catalog.features?.length||0)<=2;
  $(".timeline-head #intervalLabel").textContent=pair ? `${ordered.length} ACQUISITIONS · ${candidateCount} METADATA ${candidateCount===1?"PAIR":"PAIRS"}` : `${ordered.length} ACQUISITIONS · ${catalog.query.data_maturity} DATA`;
  $(".timeline-note").textContent=catalog.source.potentially_truncated?`Catalog cap reached at ${catalog.source.result_limit} records across ${catalog.source.pages_retrieved} pages; narrow dates or area to reduce this incomplete result set.`:ordered.length>1?"Choose a metadata pair, then select acquisitions to inspect source details · gaps show elapsed time":"Select the acquisition to inspect its source details";
  $(".evidence-title .eyebrow").innerHTML=`${escapeHTML(review?.case_id || "ASF CATALOG")} <span>·</span> EVIDENCE`;
  $(".finding-meta b").textContent=status.replaceAll("_"," ");
  renderInvestigationGates();
  renderNextEvidence();
  renderContextSources();
  renderDetails(selectedSceneId);
  renderDswxContextInspector();
  drawMap();
}

$("#comparisonPair").addEventListener("change",(event)=>{
  const choice=availablePairs()[Number(event.target.value)];
  if(!choice)return;
  pair=choice;
  gcovPairAnalysis=null;selectedPairPixel=null;pairAnalysisDisplayScale=null;
  selectedSceneId=choice.before_scene;
  renderWorkspace();
  showToast("Comparison changed · metadata candidate only; product QA and pixel checks still apply.");
});

async function init() {
  try {
    const casesResponse=await fetch("/api/cases",{cache:"no-store"});
    if(!casesResponse.ok)throw new Error("Available investigation cases could not be loaded");
    populateCaseSelector(await casesResponse.json());
    const response=await fetch(caseApiURL("/api/case"),{cache:"no-store"});
    if(!response.ok) throw new Error("Catalog metadata could not be loaded");
    catalog=await response.json();
    areaBounds=catalog.query.bounds_wgs84||null;
    areaFocusBounds=areaBounds;
    const reviewResponse=await fetch(caseApiURL("/api/review"),{cache:"no-store"});
    if(reviewResponse.ok) review=await reviewResponse.json();
    const reportResponse=await fetch(caseApiURL("/api/qa-reports"),{cache:"no-store"});
    if(reportResponse.ok) qaReports=await reportResponse.json();
    pair=selectedPair();
    renderWorkspace();
  } catch(error) {
    $("#sceneDetails").innerHTML=`<div class="full"><dt>CATALOG</dt><dd>${escapeHTML(error.message)}</dd></div>`;
    showToast(error.message);
  }
}

function openCatalogSearch() {
  const query=catalog?.query || {};
  const center=geographicCenter(query);
  const queryEnd=new Date();
  const queryStart=new Date(queryEnd.getTime()-60*86400000);
  $("#queryLongitude").value=center[0] ?? 0;
  $("#queryLatitude").value=center[1] ?? 0;
  $("#queryStart").value=query.start_date ?? queryStart.toISOString().slice(0,10);
  $("#queryEnd").value=query.end_date ?? queryEnd.toISOString().slice(0,10);
  $("#queryMaturity").value=query.data_maturity ?? "PROVISIONAL";
  const summary=$("#queryAreaSummary");
  summary.hidden=!areaBounds;
  summary.innerHTML=areaBounds?`Selected WGS84 bounds (west, south, east, north): ${areaBounds.map((v)=>v.toFixed(4)).join(", ")} <button type="button" id="clearSearchArea">Use point search</button>`:"";
  $("#runCatalogSearch").textContent=areaBounds?"SEARCH AREA":"SEARCH POINT";
  $("#clearSearchArea")?.addEventListener("click",()=>{
    areaBounds=null;gcovPreview=null;selectedPreviewPixel=null;summary.hidden=true; summary.textContent="";
    if(catalog?.query)catalog.query.bounds_wgs84=null;
    $("#runCatalogSearch").textContent="SEARCH POINT"; syncAreaButton();
    if(catalog)renderWorkspace();
  });
  $("#catalogDialog").showModal();
}

async function runCatalogSearch(event) {
  event.preventDefault();
  if(operaPairAnalysis)clearOperaView();
  const submit=$("#runCatalogSearch");
  submit.disabled=true;
  submit.textContent="SEARCHING…";
  const center=areaBounds?[(areaBounds[0]+areaBounds[2])/2,(areaBounds[1]+areaBounds[3])/2]:[
    Number($("#queryLongitude").value),Number($("#queryLatitude").value),
  ];
  const payload={
    longitude:center[0],
    latitude:center[1],
    start_date:$("#queryStart").value,
    end_date:$("#queryEnd").value,
    maturity:$("#queryMaturity").value,
  };
  if(areaBounds) payload.bounds_wgs84=areaBounds;
  try {
    const response=await fetch(caseApiURL("/api/catalog"),{
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify(payload),
    });
    const record=await response.json();
    if(!response.ok) throw new Error(record.error || "ASF catalog search failed");
    catalog=record;
    gcovPreview=null;selectedPreviewPixel=null;gcovPairAnalysis=null;selectedPairPixel=null;pairAnalysisDisplayScale=null;
    areaBounds=record.query.bounds_wgs84||null;
    areaFocusBounds=areaBounds;
    review=null;
    pair=selectedPair();
    selectedSceneId=null;
    zoom=1;
    mapPan=[0,0];
    $("#catalogDialog").close();
    renderWorkspace();
    showToast(pair?`Found ${record.feature_count} records and a metadata pair candidate.`:`Found ${record.feature_count} catalog records; no temporal pair matched.`);
  } catch(error) {
    showToast(error.message);
  } finally {
    submit.disabled=false;
    submit.textContent="SEARCH ASF";
  }
}

async function loadGcovPreview() {
  if(gcovPreview?.source?.scene_id===selectedSceneId){
    gcovPreview=null;selectedPreviewPixel=null;
    renderDetails(selectedSceneId);drawMap();
    showToast("Backscatter preview cleared.");
    return;
  }
  if(!areaBounds){showToast("Select a WGS84 map area before loading a bounded raster window.");return;}
  const feature=chronologicalFeatures().find((item)=>item.properties.fileID===selectedSceneId);
  if(!feature){showToast("Select a GCOV observation first.");return;}
  const p=feature.properties;
  const sourceProperties={};
  for(const key of ["fileID","url","processingLevel","collectionName","startTime","stopTime","crid","orbit","productionConfiguration","pathNumber","frameNumber","frameCoverage","flightDirection","mainBandPolarization","sideBandPolarization","rangeBandwidth"]){
    if(p[key]!==undefined)sourceProperties[key]=p[key];
  }
  const button=$("#loadGcovPreview");
  gcovPairAnalysis=null;selectedPairPixel=null;pairAnalysisDisplayScale=null;
  button.disabled=true;button.setAttribute("aria-busy","true");button.textContent="READING WINDOW…";
  try{
    const response=await fetch(caseApiURL("/api/gcov-preview"),{
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({feature:{properties:sourceProperties},bounds_wgs84:areaBounds,frequency:$("#previewFrequency").value,layer:$("#previewLayer").value}),
    });
    const record=await response.json();
    if(!response.ok)throw new Error(record.error||"GCOV preview could not be loaded");
    gcovPreview=record;selectedPreviewPixel=null;
    renderDetails(selectedSceneId);drawMap();
    const qa=record.source.provider_qa_status;
    showToast(`Loaded ${record.measurement.quality.aoi_pixel_center_count.toLocaleString()} real pixel centers · provider QA ${qa} · no change result.`);
  }catch(error){
    showToast(/window exceeds the .*sample limit/i.test(error.message)?"This AOI is too large for the interactive preview. Zoom in and draw a smaller area; the pixel window was not read.":error.message);
  }finally{
    button.removeAttribute("aria-busy");
    button.disabled=!selectedSceneId||!areaBounds;
    button.textContent=gcovPreview?.source?.scene_id===selectedSceneId?"HIDE BACKSCATTER":"LOAD BACKSCATTER";
  }
}

async function runGcovPairAnalysis(){
  if(!pair||!areaBounds)return;
  const featureFor=(sceneId)=>catalog?.features?.find((feature)=>feature.properties.fileID===sceneId);
  const beforeFeature=featureFor(pair.before_scene),afterFeature=featureFor(pair.after_scene);
  if(!beforeFeature||!afterFeature){showToast("Both exact catalog product records are required for pair analysis.");return;}
  const properties=(feature)=>{
    const output={};
    for(const key of ["fileID","url","processingLevel","collectionName","startTime","stopTime","crid","orbit","productionConfiguration","pathNumber","frameNumber","frameCoverage","flightDirection","mainBandPolarization","sideBandPolarization","rangeBandwidth"]){
      if(feature.properties[key]!==undefined)output[key]=feature.properties[key];
    }
    return {properties:output};
  };
  const button=$("#runPairAnalysis");
  button.disabled=true;button.setAttribute("aria-busy","true");button.textContent="CHECKING PROVIDER QA…";
  gcovPreview=null;selectedPreviewPixel=null;gcovPairAnalysis=null;selectedPairPixel=null;pairAnalysisDisplayScale=null;
  try{
    const response=await fetch(caseApiURL("/api/gcov-pair-analysis"),{
      method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({before:properties(beforeFeature),after:properties(afterFeature),bounds_wgs84:areaBounds,frequency:$("#previewFrequency").value,layer:$("#previewLayer").value}),
    });
    const record=await response.json();
    if(!response.ok)throw new Error(record.error||"GCOV pair analysis could not be completed");
    if(!["QA_HELD","MATURITY_HELD","MEASURED_DESCRIPTIVE_ONLY"].includes(record.status))throw new Error("GCOV pair response has an unsupported disposition");
    gcovPairAnalysis=record;
    if(record.status==="MEASURED_DESCRIPTIVE_ONLY")pairAnalysisDisplayScale=pairDisplayScale(record);
    renderDetails(selectedSceneId);drawMap();
    const count=record.status!=="MEASURED_DESCRIPTIVE_ONLY"?0:record.measurement.common_valid_mask.flat().filter(Boolean).length;
    showToast(record.status==="QA_HELD"?"Pair held: ASF provider QA did not pass. No measurement arrays were read.":record.status==="MATURITY_HELD"?"Pair held: unsupported product maturity. No measurement arrays were read.":"Rendered "+count.toLocaleString()+" common valid NISAR measurement pixels · descriptive only.");
  }catch(error){showToast(error.message);}
  finally{
    button.removeAttribute("aria-busy");button.textContent="ANALYZE PAIR";
    const ready=Boolean(pair&&areaBounds&&[pair.before_scene,pair.after_scene].every((sceneId)=>catalog?.features?.some((feature)=>feature.properties.fileID===sceneId)));
    button.disabled=!ready;
  }
}

$("#zoomIn").addEventListener("click",()=>{zoom=Math.min(zoom*1.35,5);if(catalog)drawMap()});
$("#zoomOut").addEventListener("click",()=>{zoom=Math.max(zoom/1.35,0.7);if(catalog)drawMap()});
$("#resetView").addEventListener("click",()=>{zoom=1;mapPan=[0,0];if(catalog)drawMap()});
$("#toggleBasemap").addEventListener("click",()=>{basemapEnabled=!basemapEnabled;if(catalog)drawMap()});
svg.addEventListener("keydown",(event)=>{
  if(!mapTransform)return;
  const horizontal=(mapTransform.view.maxX-mapTransform.view.minX)*0.15;
  const vertical=(mapTransform.view.maxY-mapTransform.view.minY)*0.15;
  const offsets={ArrowLeft:[-horizontal,0],ArrowRight:[horizontal,0],ArrowUp:[0,vertical],ArrowDown:[0,-vertical]};
  const offset=offsets[event.key];
  if(!offset)return;
  event.preventDefault();
  mapPan=[mapPan[0]+offset[0],mapPan[1]+offset[1]];
  drawMap();
});
$("#drawArea").addEventListener("click",()=>{
  if(areaBounds){areaBounds=null;areaPreview=null;drawingArea=false;gcovPreview=null;selectedPreviewPixel=null;gcovPairAnalysis=null;selectedPairPixel=null;pairAnalysisDisplayScale=null;if(catalog?.query)catalog.query.bounds_wgs84=null;if(catalog)renderWorkspace();return;}
  drawingArea=!drawingArea; areaPreview=null; syncAreaButton();
  svg.classList.toggle("area-draw-mode",drawingArea);
  showToast(drawingArea?"Drag on the map to select a WGS84 rectangle.":"Area selection cancelled.");
});
svg.addEventListener("pointerdown",(event)=>{
  if(!mapTransform||event.button!==0)return;
  event.preventDefault();
  if(drawingArea){
    areaStart=mapCoordinate(event); areaPreview=[areaStart[0],areaStart[1],areaStart[0],areaStart[1]];
    svg.setPointerCapture(event.pointerId); drawMap();
    return;
  }
  const point=svg.createSVGPoint();point.x=event.clientX;point.y=event.clientY;
  const local=point.matrixTransform(svg.getScreenCTM().inverse());
  panStart={x:local.x,y:local.y,longitude:mapPan[0],latitude:mapPan[1],view:{...mapTransform.view}};
  svg.classList.add("map-panning");
  svg.setPointerCapture(event.pointerId);
});
svg.addEventListener("pointermove",(event)=>{
  if(drawingArea&&areaStart&&mapTransform){
    const [lon,lat]=mapCoordinate(event);
    areaPreview=[Math.min(areaStart[0],lon),Math.min(areaStart[1],lat),Math.max(areaStart[0],lon),Math.max(areaStart[1],lat)];
    drawMap();
    return;
  }
  if(!panStart)return;
  const point=svg.createSVGPoint();point.x=event.clientX;point.y=event.clientY;
  const local=point.matrixTransform(svg.getScreenCTM().inverse());
  const dx=local.x-panStart.x,dy=local.y-panStart.y;
  if(Math.hypot(dx,dy)>3)suppressMapClick=true;
  svg.setAttribute("viewBox",`${-dx} ${-dy} 1000 600`);
});
svg.addEventListener("pointerup",(event)=>{
  if(areaStart&&areaPreview){
    const width=areaPreview[2]-areaPreview[0],height=areaPreview[3]-areaPreview[1];
    if(width>0&&height>0){areaBounds=areaPreview;areaFocusBounds=areaBounds;gcovPreview=null;selectedPreviewPixel=null;gcovPairAnalysis=null;selectedPairPixel=null;pairAnalysisDisplayScale=null;operaCatalog=null;operaPairAnalysis=null;selectedOperaPixel=null;operaDisplayScale=null;document.querySelector(".timeline-panel").hidden=false;$("#loadGcovPreview").hidden=false;$("#challengeButton").hidden=false;$("#clearOperaView").hidden=true;drawingArea=false;showToast("Area selected. Find observations to query ASF for intersecting footprints.");}
    else showToast("Drag a rectangle with non-zero width and height.");
    areaStart=null; areaPreview=null; syncAreaButton();
    if(areaBounds)renderWorkspace();else drawMap();
  }else if(panStart){
    const point=svg.createSVGPoint();point.x=event.clientX;point.y=event.clientY;
    const local=point.matrixTransform(svg.getScreenCTM().inverse());
    const dx=local.x-panStart.x,dy=local.y-panStart.y;
    mapPan=[
      panStart.longitude-dx/mapTransform.plotWidth*(panStart.view.maxX-panStart.view.minX),
      panStart.latitude+dy/mapTransform.plotHeight*(panStart.view.maxY-panStart.view.minY),
    ];
    panStart=null;svg.classList.remove("map-panning");drawMap();
    window.setTimeout(()=>{suppressMapClick=false;},0);
  }
  if(svg.hasPointerCapture(event.pointerId))svg.releasePointerCapture(event.pointerId);
});
svg.addEventListener("pointercancel",()=>{areaStart=null;areaPreview=null;panStart=null;svg.classList.remove("map-panning");drawMap();});
$("#timelineTrack").addEventListener("click",(event)=>{
  const button=event.target.closest(".timeline-observation[data-scene-id]");
  if(button)selectObservation(button.dataset.sceneId);
});
svg.addEventListener("click",(event)=>{
  if(suppressMapClick){suppressMapClick=false;return;}
  if(dswxContextVisible){
    const cell=event.target.closest("polygon[data-dswx-index]");
    if(cell){selectedDswxSample=Number(cell.dataset.dswxIndex);renderDswxContextInspector();drawMap();}
    return;
  }
  if(operaPairAnalysis){
    if(operaPairAnalysis.status==="DIAGNOSTIC_PRODUCT_MASKED_COMPARISON"&&mapTransform){
      const point=svg.createSVGPoint();point.x=event.clientX;point.y=event.clientY;
      const local=point.matrixTransform(svg.getScreenCTM().inverse());
      const pixel=rasterPixelAt(local.x,local.y);
      if(pixel){selectedOperaPixel=pixel;renderGcovPreviewDetails();drawMap();}
    }
    return;
  }
  const polygon=event.target.closest("polygon[data-scene-id]");
  if(polygon&&!gcovPreview&&(!gcovPairAnalysis||["QA_HELD","MATURITY_HELD"].includes(gcovPairAnalysis.status))){selectObservation(polygon.dataset.sceneId,{scrollTimeline:true});return;}
  if(gcovPairAnalysis?.status==="MEASURED_DESCRIPTIVE_ONLY"&&mapTransform){
    const point=svg.createSVGPoint();point.x=event.clientX;point.y=event.clientY;
    const local=point.matrixTransform(svg.getScreenCTM().inverse());
    const pixel=rasterPixelAt(local.x,local.y);
    if(pixel){selectedPairPixel=pixel;renderGcovPreviewDetails();drawMap();}
    return;
  }
  if(gcovPreview&&mapTransform){
    const point=svg.createSVGPoint();point.x=event.clientX;point.y=event.clientY;
    const local=point.matrixTransform(svg.getScreenCTM().inverse());
    const pixel=rasterPixelAt(local.x,local.y);
    if(pixel){selectedPreviewPixel=pixel;renderGcovPreviewDetails();drawMap();}
  }
});

async function toggleDswxContext() {
  const button=$("#openDswxContext");
  if(dswxContextVisible){
    dswxContextVisible=false;selectedDswxSample=null;
    crossSensorAssessmentVisible=false;renderCrossSensorAssessment();
    $("#dswxContextControls").hidden=true;
    button.setAttribute("aria-pressed","false");
    renderWorkspace();
    return;
  }
  button.disabled=true;button.textContent="LOADING NASA CONTEXT…";
  try{
    if(!dswxContext){
      const response=await fetch(caseApiURL("/api/dswx-context"),{cache:"no-store"});
      const record=await response.json();
      if(!response.ok)throw new Error(record.error||"NASA optical context could not be loaded");
      if(record.record_type!=="ECHO_DSWX_HLS_AOI_CONTEXT_COMPARISON"||!Array.isArray(record.map_samples)||!record.map_samples.length)throw new Error("NASA optical context record is incomplete");
      dswxContext=record;
    }
    dswxContextLayer=$("#dswxLayer").value;
    dswxContextDate=$("#dswxDate").value;
    dswxContextVisible=true;selectedDswxSample=null;zoom=1;mapPan=[0,0];
    $("#dswxContextControls").hidden=false;
    button.setAttribute("aria-pressed","true");button.textContent="NASA OPTICAL CONTEXT";
    renderDswxContextInspector();drawMap();
  }catch(error){showToast(error.message);button.textContent="NASA OPTICAL CONTEXT";}
  finally{button.disabled=false;}
}

$("#openDswxContext").addEventListener("click",toggleDswxContext);
$("#loadDswxContext").addEventListener("click",toggleDswxContext);
$("#dswxLayer").addEventListener("change",(event)=>{dswxContextLayer=event.target.value;selectedDswxSample=null;renderDswxContextInspector();drawMap();});
$("#dswxDate").addEventListener("change",(event)=>{dswxContextDate=event.target.value;selectedDswxSample=null;renderDswxContextInspector();drawMap();});
$("#recordToggle").addEventListener("click",()=>{
  if(!catalog)return;
  const feature=chronologicalFeatures().find((item)=>item.properties.fileID===selectedSceneId);
  if(!feature){showToast("No observation is selected.");return;}
  $("#recordDialog .eyebrow").textContent="SOURCE RECORD · ASF CATALOG SEARCH";
  $("#recordDialog h2").textContent="Catalog metadata";
  $("#recordJson").textContent=JSON.stringify(feature,null,2);
  $("#recordDialog").showModal();
});
$("#reviewRecordToggle").addEventListener("click",()=>{
  if(!review)return;
  $("#recordDialog .eyebrow").textContent="SOURCE RECORD · CASE REVIEW";
  $("#recordDialog h2").textContent="Case evidence and next checks";
  $("#recordJson").textContent=JSON.stringify(review,null,2);
  $("#recordDialog").showModal();
});
$("#qaRecordToggle").addEventListener("click",async()=>{
  if(!catalog||!selectedSceneId){showToast("No observation is selected.");return;}
  const sceneId=selectedSceneId;
  const feature=chronologicalFeatures().find((item)=>item.properties.fileID===sceneId);
  if(!feature){showToast("The selected catalog record is unavailable.");return;}
  const button=$("#qaRecordToggle");
  let qaError=null;
  if(!qaSummaryByScene.has(sceneId)){
    button.disabled=true;
    button.textContent="FETCHING QA…";
    button.setAttribute("aria-busy","true");
    $("#qaSummary").innerHTML='<p class="qa-empty">Retrieving this product\'s bounded ASF QA summary…</p>';
    $("#qaJson").textContent="Provider QA summary retrieval is in progress.";
    $("#qaDialog").showModal();
    try{
      qaSummaryByScene.set(sceneId,await fetchProviderQASummary(feature));
      qaFeatureByScene.set(sceneId,feature);
      if(selectedSceneId===sceneId)renderDetails(sceneId);
    }catch(error){qaError=error.message;}
    finally{button.disabled=false;button.removeAttribute("aria-busy");button.innerHTML=qaSummaryByScene.has(sceneId)?"VIEW QA <span>↗</span>":"FETCH QA <span>↗</span>";}
  }
  const liveQA=qaSummaryByScene.get(sceneId);
  const sceneIds=new Set([sceneId]);
  const reports=qaReports.records.filter((item)=>sceneIds.has(item.scene_id));
  const qaReview=reviewProducts().filter((item)=>sceneIds.has(item.scene_id));
  const reportCards=reports.map((report)=>{
    const metadata=report.product_metadata||{};
    const qa=qaReview.find((item)=>item.scene_id===report.scene_id);
    const checks=report.catalog_crosschecks||{};
    const matching=Object.values(checks).filter((value)=>value===true).length;
    const checkTotal=Object.values(checks).filter((value)=>value!==null).length;
    const crosscheck=report.identification_crosscheck||{};
    const sourceDiagnostic=crosscheck.status||"NOT AVAILABLE";
    const sourceFindings=Array.isArray(crosscheck.findings)?crosscheck.findings:[];
    const diagnosticDetails=sourceFindings.length?`<ul class="qa-source-findings">${sourceFindings.map((finding)=>{
      const field=`${finding.field||"field"}${Number.isInteger(finding.index)?`[${finding.index}]`:""}`;
      return `<li><code>${escapeHTML(field)} = ${escapeHTML(finding.observed_value)}</code><span>${escapeHTML(finding.rule||finding.result||"Source rule mismatch")}</span></li>`;
    }).join("")}</ul>`:'<p class="qa-diagnostic-note">No matching field-level source rules are recorded.</p>';
    const validatorVersion=crosscheck.validator?.version;
    const diagnosticScope=crosscheck.scope||"partial validator-source cross-check; not provider per-field QA";
    const reportURI=trustedQAReportURI(report);
    const sourceLink=reportURI?`<a href="${escapeHTML(reportURI)}" target="_blank" rel="noopener noreferrer">Open original ASF report ↗</a>`:`<span>ASF report link unavailable · source URI did not validate</span>`;
    return `<article class="qa-report-card"><div class="qa-report-heading"><span>ASF QA REPORT · ${escapeHTML(report.qa_software_version)}</span><b>${escapeHTML(liveQA?.evidence?.status||qa?.qa_summary?.identification_group||"CSV DISPOSITION IN REVIEW RECORD")}</b></div><h3>${escapeHTML(report.scene_id)}</h3><dl><div><dt>REPORT PROCESSED</dt><dd>${escapeHTML(report.report_processing_time_utc)}</dd></div><div><dt>RETRIEVED</dt><dd>${escapeHTML(report.retrieved_at_utc)}</dd></div><div><dt>PRODUCT FORMAT</dt><dd>Spec ${escapeHTML(metadata.productSpecificationVersion)} · product ${escapeHTML(metadata.productVersion)}</dd></div><div><dt>IDENTIFICATION</dt><dd>${escapeHTML(metadata.instrumentName)} · ${(metadata.listOfObservationModes||[]).map(escapeHTML).join(", ")}</dd></div><div><dt>CATALOG CROSS-CHECK</dt><dd>${matching}/${checkTotal} reported orbit, track, and frame matches</dd></div><div><dt>PARTIAL SOURCE CHECK</dt><dd>${escapeHTML(sourceDiagnostic)}${validatorVersion?` · nisarqa ${escapeHTML(validatorVersion)}`:""}</dd></div><div class="qa-full"><dt>MATCHING SOURCE RULES · DIAGNOSTIC ONLY</dt><dd>${diagnosticDetails}<p class="qa-diagnostic-note">${escapeHTML(diagnosticScope)}. These matches help explain the aggregate check but do not identify every provider failure or change ASF's disposition.</p></dd></div></dl><p>${sourceLink}<span class="qa-checksum">SHA-256 ${escapeHTML(report.artifact_sha256)}</span></p></article>`;
  });
  const cards=[];
  if(liveQA)cards.push(renderProviderQASummary(liveQA));
  else if(qaError)cards.push(`<p class="qa-empty">Provider QA summary could not be retrieved: ${escapeHTML(qaError)}</p>`);
  if(reportCards.length)cards.push(...reportCards);
  if(!cards.length)cards.push("<p class=\"qa-empty\">No provider QA summary or parsed QA report is available for this acquisition.</p>");
  $("#qaSummary").innerHTML=cards.join("");
  configureProviderQAEvidenceExport(sceneId);
  $("#qaJson").textContent=JSON.stringify({live_provider_qa_summary:liveQA||null,case_review_qa_records:qaReview,provider_qa_report_records:reports,interpretation_limit:"Provider CSV dispositions remain distinct from ECHO's partial validator-source cross-check. PDF metadata does not override the provider CSV status."},null,2);
  $("#qaDialog").showModal();
});
$("#qaEvidenceExport").addEventListener("click",()=>$("#qaEvidenceExportForm").requestSubmit());
$("#challengeButton").addEventListener("click",()=>$("#challengeDialog").showModal());
$("#closeInvestigationChallenge").addEventListener("click",()=>$("#investigationChallengeDialog").close());
$("#cancelInvestigationChallenge").addEventListener("click",()=>$("#investigationChallengeDialog").close());
$("#previewChallengeImpact").addEventListener("click",previewCounterfactualChallengeImpact);
$("#challengeEvidence").addEventListener("change",()=>{
  clearCounterfactualChallengePreview();
  $("#previewChallengeImpact").disabled=$("#challengeEvidence").value==="MISSING_EVIDENCE";
});
$("#challengeRelationship").addEventListener("change",clearCounterfactualChallengePreview);
$("#challengeHypothesis").addEventListener("change",()=>{
  clearCounterfactualChallengePreview();
  populateChallengeEvidence($("#challengeHypothesis").value);
  $("#previewChallengeImpact").disabled=true;
});
$("#challengeNotesFile").addEventListener("change",async(event)=>{
  const file=event.currentTarget.files?.[0];
  event.currentTarget.value="";
  if(!file)return;
  try{await importInvestigationChallengeNotes(file);}catch(error){showToast(error.message);}
});
$("#investigationChallengeForm").addEventListener("submit",(event)=>{
  event.preventDefault();
  if(!crossSensorAssessment)return;
  const hypothesisId=$("#challengeHypothesis").value;
  const hypothesis=crossSensorAssessment.hypotheses.find((item)=>item.id===hypothesisId);
  if(!hypothesis)return;
  const relatedEvidenceValue=$("#challengeEvidence").value;
  const relatedEvidenceId=relatedEvidenceValue==="MISSING_EVIDENCE"?null:relatedEvidenceValue;
  const sourceArtifact=crossSensorAssessment.evidence_artifacts.find((item)=>item.evidence_id===relatedEvidenceId);
  investigationChallengeNotes.push({
    record_type:"ECHO_INVESTIGATION_CHALLENGE_NOTE",
    schema_version:1,
    created_at_utc:new Date().toISOString(),
    status:"UNASSESSED_HUMAN_INPUT",
    role:"ANALYST_CHALLENGE_NOTE",
    source_assessment:{
      case_id:crossSensorAssessment.case_id,
      sha256:crossSensorAssessmentSha256,
      disposition:crossSensorAssessment.status,
      evidence_artifacts:crossSensorAssessment.evidence_artifacts.map((item)=>({evidence_id:item.evidence_id,role:item.role,sha256:item.sha256})),
    },
    hypothesis:{id:hypothesis.id,statement:hypothesis.statement,recorded_state:hypothesis.state},
    challenge_type:$("#challengeKind").value,
    related_evidence:sourceArtifact?{evidence_id:sourceArtifact.evidence_id,role:sourceArtifact.role,sha256:sourceArtifact.sha256}:null,
    challenge_statement:$("#challengeStatement").value.trim(),
    proposed_test:$("#challengeTest").value.trim(),
    counterfactual_preview:counterfactualChallengePreview,
    interpretation_limit:"This human review note and any attached counterfactual preview are unverified analyst input; neither alters the retained assessment disposition.",
  });
  clearCounterfactualChallengePreview();
  $("#investigationChallengeForm").reset();
  $("#investigationChallengeDialog").close();
  renderCrossSensorAssessment();
  showToast("Challenge note added to this page session. Export it to keep a copy.");
});
$("#aboutButton").addEventListener("click",()=>$("#aboutDialog").showModal());
$("#investigationDialog").addEventListener("close",()=>{crossSensorAssessmentVisible=false;});
$("#closeInvestigationDialog").addEventListener("click",closeInvestigationDialog);
$("#openCaseInvestigation").addEventListener("click",(event)=>openCrossSensorAssessment(event.currentTarget));
$("#searchCatalog").addEventListener("click",openCatalogSearch);
$("#loadGcovPreview").addEventListener("click",loadGcovPreview);
$("#runPairAnalysis").addEventListener("click",runGcovPairAnalysis);
$("#openOpera").addEventListener("click",openOperaDialog);
$("#closeOperaDialog").addEventListener("click",()=>$("#operaDialog").close());
$("#searchOpera").addEventListener("click",searchOperaCatalog);
$("#operaPair").addEventListener("change",updateOperaCandidateDetails);
$("#analyzeOperaPair").addEventListener("click",analyzeOperaPair);
$("#clearOperaView").addEventListener("click",clearOperaView);
$("#clearOperaView").hidden=true;
for(const selector of ["#previewFrequency","#previewLayer"]){
  $(selector).addEventListener("change",()=>{
    if(gcovPreview){gcovPreview=null;selectedPreviewPixel=null;drawMap();}
    if(gcovPairAnalysis){gcovPairAnalysis=null;selectedPairPixel=null;pairAnalysisDisplayScale=null;drawMap();}
    renderDetails(selectedSceneId);
  });
}
$("#closeCatalogDialog").addEventListener("click",()=>$("#catalogDialog").close());
$("#catalogQueryForm").addEventListener("submit",runCatalogSearch);
$("#sourcesNav").addEventListener("click",()=>showToast("Source records are available from the observation details panel."));
init();
