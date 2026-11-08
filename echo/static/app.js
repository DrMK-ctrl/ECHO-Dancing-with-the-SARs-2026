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
let operaDisplayScale = null;
let previewScreenCells = [];

const escapeHTML = (value) => String(value ?? "—").replace(/[&<>"']/g, (char) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[char]));

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
  if(!crossSensorAssessmentVisible||!crossSensorAssessment){section.hidden=true;section.innerHTML="";return;}
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
  const hypotheses=record.hypotheses.map((item)=>{const relations=(item.evidence_assessments||[]).map((assessment)=>`<li><b>${escapeHTML(assessment.evidence_id)} · ${escapeHTML(assessment.relationship.replaceAll("_"," "))}</b><span>${escapeHTML(assessment.rationale)}</span></li>`).join("");const requirements=item.required_evidence.map((requirement)=>`<li>${escapeHTML(requirement)}</li>`).join("");return `<article class="investigation-hypothesis"><div><b>${escapeHTML(item.statement)}</b><span class="investigation-state state-${escapeHTML(item.state.toLowerCase().replaceAll("_","-"))}">${escapeHTML(item.state.replaceAll("_"," "))}</span></div><small class="hypothesis-testability">TESTABILITY · ${escapeHTML(item.testability_state.replaceAll("_"," "))}</small>${relations?`<ul class="investigation-relations">${relations}</ul>`:"<p>No relevant evidence is recorded for this explanation.</p>"}<details class="hypothesis-test"><summary>TEST CONDITIONS</summary><div><b>EXPECTED OBSERVATION</b><p>${escapeHTML(item.expected_observation)}</p><b>WOULD WEAKEN IF</b><p>${escapeHTML(item.would_weaken_if)}</p><b>WHY THIS TESTABILITY STATE</b><p>${escapeHTML(item.testability_reason)}</p><b>REQUIRED EVIDENCE</b><ul>${requirements}</ul></div></details><small>SCOPE · ${escapeHTML(item.scope_limit||"Not specified")}</small><button type="button" class="challenge-hypothesis" data-hypothesis-id="${escapeHTML(item.id)}">CHALLENGE THIS EXPLANATION</button></article>`;}).join("");
  const lineageRows=(record.evidence_artifacts||[]).map((artifact)=>{
    const lineage=artifact.lineage||{};
    const derived=(lineage.derived_from_evidence_ids||[]).map(escapeHTML);
    const shared=(lineage.shares_source_observations_with||[]).map(escapeHTML);
    const relationship=[
      derived.length?`Derived from ${derived.join(" · ")}`:"",
      shared.length?`Shares source observations with ${shared.join(" · ")}`:"",
    ].filter(Boolean).join(" · ")||"Primary source record; no upstream evidence link recorded";
    return `<li><b>${escapeHTML(artifact.evidence_id)} · ${escapeHTML((artifact.role||"EVIDENCE").replaceAll("_"," "))}</b><span>${relationship}</span></li>`;
  }).join("");
  const lineagePanel=`<details class="investigation-lineage"><summary>EVIDENCE DEPENDENCIES · ${record.evidence_artifacts?.length||0} RECORDS</summary><p>Derived analyses and products sharing source acquisitions are identified so related results are not mistaken for independent corroboration.</p><ul>${lineageRows}</ul></details>`;
  const followups=record.follow_up_evidence.map((item)=>{
    const targets=item.target_hypothesis_ids.map((id)=>record.hypotheses.find((hypothesis)=>hypothesis.id===id)?.statement||id).join(" · ");
    const refs=(item.evidence_refs||[]).join(" · ")||"No retrieved evidence record";
    const actionTrack=item.action_track||(
      item.purpose==="QUALITY_GATE"&&["NOT_SEARCHED","PROVIDER_RESPONSE_REQUIRED"].includes(item.availability_state)
        ?"QUALITY_PREREQUISITE"
        :item.purpose==="DISCRIMINATING_OBSERVATION"&&item.availability_state==="NOT_SEARCHED"
          ?"NEW_EVIDENCE_SEARCH"
          :"REVIEWED_RESULT"
    );
    const design=item.test_design;
    const designMarkup=design?`<details class="followup-test-design"><summary>PRE-SEARCH TEST DESIGN</summary><div><b>MECHANISM BRANCH</b><p>${escapeHTML(design.mechanism_branch)}</p><b>EXPECTED IF PRESENT</b><p>${escapeHTML(design.expected_observation)}</p><b>WOULD WEAKEN IF</b><p>${escapeHTML(design.would_weaken_if)}</p><b>REMAINS INCONCLUSIVE IF</b><p>${escapeHTML(design.inconclusive_if)}</p><b>DATA ACCEPTANCE GATES</b><ul>${design.acceptance_gates.map((gate)=>`<li>${escapeHTML(gate)}</li>`).join("")}</ul><b>DOES NOT TEST</b><ul>${design.does_not_test_hypothesis_ids.map((id)=>{const hypothesis=record.hypotheses.find((entry)=>entry.id===id);return `<li>${escapeHTML(hypothesis?.statement||id)}</li>`;}).join("")}</ul><b>INTERPRETATION LIMIT</b><p>${escapeHTML(design.interpretation_limit)}</p></div></details>`:"";
    return `<article class="investigation-followup"><div><b>${escapeHTML(item.purpose.replaceAll("_"," "))}</b><span class="followup-availability">${escapeHTML(item.availability_state.replaceAll("_"," "))}</span></div><small class="followup-track">WORKSTREAM · ${escapeHTML(actionTrack.replaceAll("_"," "))}</small><p>${escapeHTML(item.action)}</p><small>TEST · ${escapeHTML(item.discriminating_question)}</small><small>IF OBSERVED · ${escapeHTML(item.possible_interpretation)}</small><small>TARGET · ${escapeHTML(targets)}</small><small>EVIDENCE RECORDS · ${escapeHTML(refs)}</small>${designMarkup}<small>WHY NOW · ${escapeHTML(item.priority_reason)}</small></article>`;
  }).join("");
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
  const currentChallenges=investigationChallengeNotes.filter((note)=>note.source_assessment.case_id===record.case_id&&note.source_assessment.sha256===crossSensorAssessmentSha256);
  const challengesMarkup=currentChallenges.length?currentChallenges.map((note)=>`<article class="challenge-note"><div><b>${escapeHTML(note.challenge_type.replaceAll("_"," "))}</b><small>${escapeHTML(note.created_at_utc.replace("T"," ").replace("Z"," UTC"))}</small></div><p><b>EXPLANATION</b> · ${escapeHTML(note.hypothesis.statement)}</p><p>${escapeHTML(note.challenge_statement)}</p><small>RELATED SOURCE · ${escapeHTML(note.related_evidence?.evidence_id||"No retrieved source · information gap")}</small><p><b>PROPOSED TEST</b> · ${escapeHTML(note.proposed_test)}</p><small>UNASSESSED HUMAN REVIEW · does not alter the source assessment</small></article>`).join(""):"<p class=\"challenge-empty\">No challenge notes recorded for this assessment in this page session.</p>";
  section.hidden=false;
  section.innerHTML=`<h3>INVESTIGATION ASSESSMENT · ${escapeHTML(record.status.replaceAll("_"," "))}</h3><p>${escapeHTML(record.assessment.summary)}</p><div class="investigation-observations"><article><b>DIAGNOSTIC SAR · SENTINEL-1 / OPERA RTC-S1</b><span>${sar.common_clear_pixel_count.toLocaleString()} / ${sar.aoi_pixel_count.toLocaleString()} common-clear cells · mean ${sar.mean_db.toFixed(2)} dB · median ${sar.median_db.toFixed(2)} dB</span><small>QA: ${escapeHTML(sar.provider_qa_state)} · not NISAR</small></article><article><b>NASA OPTICAL CONTEXT · OPERA DSWx-HLS</b><span>WTR ${optical.wtr_water_class_counts_before_after[0]} → ${optical.wtr_water_class_counts_before_after[1]} · WTR-2 ${optical.wtr2_water_class_counts_before_after[0]} → ${optical.wtr2_water_class_counts_before_after[1]} water-class cells</span><small>${spatial?"Native grids joined by exact area-weighted cell intersections; no resampling. Optical classifications remain context, not ground truth.":"Same AOI, different grids · no pixel-wise cross-sensor comparison"}</small></article>${nearerCard}${spatialCard}${polarizationCard}${gpmCard}${gpmInteracquisitionCard}${hydrologicCard}${smapScreenCard}${smapRadiometerCard}${hlsCard}</div>${timeline}<div class="investigation-hypotheses">${hypotheses}</div>${lineagePanel}<section class="investigation-challenges"><div><b>CHALLENGE / HUMAN REVIEW</b><button type="button" id="exportChallengeNotes" ${currentChallenges.length?"":"hidden"}>EXPORT NOTES</button></div><p>Review notes are unassessed analyst input. They are linked to this assessment and never change its disposition automatically.</p><div class="challenge-notes">${challengesMarkup}</div></section><div class="investigation-next"><b>NEXT INVESTIGATION WORKSTREAMS</b><p>Quality prerequisites and unresolved evidence searches are shown as separate tracks. The order is not a confidence or value ranking; searching for scientific context can continue while a measurement QA response is pending.</p><div class="investigation-followups">${followups}</div></div><p class="investigation-boundary">This assessment uses a retained diagnostic Sentinel-1 pair and optical product classifications. It does not establish causal attribution, a validated flood extent, or a NISAR result.</p><div class="preview-actions"><button type="button" id="assessmentRecordButton">INSPECT LINKED EVIDENCE RECORD</button><button type="button" id="closeAssessmentButton">CLOSE ASSESSMENT</button></div>`;
  section.querySelectorAll(".investigation-time-point[data-time-position]").forEach((point)=>{
    point.style.left=`${point.dataset.timePosition}%`;
  });
  $("#assessmentRecordButton").addEventListener("click",()=>{$("#recordJson").textContent=JSON.stringify(record,null,2);$("#recordDialog .eyebrow").textContent="EVIDENCE RECORD · CROSS-SENSOR ASSESSMENT";$("#recordDialog h2").textContent="Investigation and evidence links";$("#recordDialog").showModal();});
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
  section.querySelectorAll(".challenge-hypothesis").forEach((button)=>button.addEventListener("click",()=>openInvestigationChallenge(button.dataset.hypothesisId)));
  if(currentChallenges.length)$("#exportChallengeNotes").addEventListener("click",exportInvestigationChallengeNotes);
  $("#closeAssessmentButton").addEventListener("click",()=>{crossSensorAssessmentVisible=false;renderCrossSensorAssessment();});
}

async function openInvestigationEvidenceRecord(evidenceId) {
  try{
    const response=await fetch(`/api/investigation-evidence?evidence_id=${encodeURIComponent(evidenceId)}`,{cache:"no-store"});
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
  hypothesisSelect.value=hypothesisId;
  const evidenceSelect=$("#challengeEvidence");
  evidenceSelect.innerHTML='<option value="MISSING_EVIDENCE">No retrieved source · information gap</option>'+crossSensorAssessment.evidence_artifacts.map((item)=>`<option value="${escapeHTML(item.evidence_id)}">${escapeHTML(item.evidence_id)} · ${escapeHTML(item.role)}</option>`).join("");
  $("#investigationChallengeDialog").showModal();
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

async function sha256Hex(text) {
  if(!globalThis.crypto?.subtle)return null;
  const digest=await crypto.subtle.digest("SHA-256",new TextEncoder().encode(text));
  return Array.from(new Uint8Array(digest),(byte)=>byte.toString(16).padStart(2,"0")).join("");
}

async function openCrossSensorAssessment() {
  if(!crossSensorAssessmentMatchesCurrentPair()){
    showToast("This assessment is linked to a different RTC-S1 pair. Select its case-preferred pair to inspect it.");
    return;
  }
  const button=$("#assessDswxEvidence");button.disabled=true;button.textContent="LOADING LINKED EVIDENCE…";
  try{
    if(!crossSensorAssessment){
      const response=await fetch("/api/cross-sensor-assessment",{cache:"no-store"});
      const responseText=await response.text();
      const record=JSON.parse(responseText);
      if(!response.ok)throw new Error(record.error||"Investigation assessment could not be loaded");
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
    crossSensorAssessmentVisible=true;renderCrossSensorAssessment();
  }catch(error){showToast(error.message);}
  finally{button.disabled=false;button.textContent="OPEN EVIDENCE ASSESSMENT";}
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
        ? `NISAR ${gcovPairAnalysis.measurement.layer} descriptive comparison · QA PASS`
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
  const area=contextMode?dswxContext.aoi.bounds_west_south_east_north:areaPreview||areaBounds;
  const selection=area?`<rect class="aoi-selection" x="${x(area[0])}" y="${y(area[3])}" width="${Math.max(1,x(area[2])-x(area[0]))}" height="${Math.max(1,y(area[1])-y(area[3]))}"/>`:"";
  svg.classList.toggle("area-draw-mode",drawingArea);
  const pairMeasured=gcovPairAnalysis?.status==="MEASURED_DESCRIPTIVE_ONLY";
  svg.classList.toggle("gcov-raster-active",contextMode||Boolean(gcovPreview)||pairMeasured||Boolean(operaPairAnalysis));
  svg.innerHTML = `${imageMarkup}${rasterMarkup}${dswxMarkup}${grid.join("")}<g>${shapes}</g>${selection}<line class="point-leader" x1="${px+10}" y1="${py-8}" x2="${px+75}" y2="${py-43}"/><text class="point-label" x="${px+80}" y="${py-46}">${area?"AREA CENTER":"SEARCH POINT"}</text><circle class="search-ring" cx="${px}" cy="${py}" r="10"/><circle class="search-dot" cx="${px}" cy="${py}" r="3.5"/>`;
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
    warning.innerHTML='<span class="warning-glyph">Δ</span><span><b>DESCRIPTIVE SAR CHANGE</b><small>Provider QA PASS · no event or cause inferred</small></span>';
    watermark.classList.add("raster-preview");
    watermark.innerHTML="ECHO <span>·</span> NISAR GCOV LOG RATIO";
    $("#mapDataAttribution").textContent=`NISAR GCOV · ${gcovPairAnalysis.measurement.layer} · Δγ⁰ dB · QA PASS · NASA GIBS IS CONTEXT ONLY`;
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
      "<div class=\"preview-actions\"><button type=\"button\" id=\"operaRecordButton\">INSPECT FULL RECORD</button><button type=\"button\" id=\"downloadOperaRecordButton\">DOWNLOAD REPRODUCTION RECORD</button></div>";
    $("#operaRecordButton").addEventListener("click",()=>{$("#recordJson").textContent=JSON.stringify(record,null,2);$("#recordDialog .eyebrow").textContent="SOURCE RECORD · OPERA RTC-S1";$("#recordDialog h2").textContent="Diagnostic pair analysis";$("#recordDialog").showModal();});
    $("#downloadOperaRecordButton").addEventListener("click",()=>downloadJSON(record,"echo-opera-rtc-s1-"+record.status.toLowerCase()+".json"));
    return;
  }
  if(gcovPairAnalysis){
    const record=gcovPairAnalysis;
    const sourceProducts=record.source_products||{};
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
      resultDetails=`<h3>DESCRIPTIVE NISAR GCOV COMPARISON · QA PASS</h3><p>Mapped quantity: 10 log₁₀(after γ⁰ / before γ⁰). This is a measured backscatter difference; it does not identify an event or physical cause.</p><dl><div><dt>MEASUREMENT</dt><dd>${escapeHTML(measurement.layer)} · frequency ${escapeHTML(measurement.frequency)} · ${escapeHTML(measurement.units)}<br>${windowShape[1]} × ${windowShape[0]} pixels · EPSG:${escapeHTML(grid.epsg_code)}</dd></div><div><dt>COMMON VALID PIXELS</dt><dd>${measurement.common_valid_mask.flat().filter(Boolean).length.toLocaleString()} of ${measurement.valid_mask.flat().length.toLocaleString()} grid cells</dd></div><div><dt>DISPLAY STRETCH</dt><dd>±${pairChangeScale().toFixed(2)} dB · 98th percentile of absolute valid values<br>Display-only scaling; not an analysis threshold</dd></div><div class="full"><dt>ANALYSIS MANIFEST</dt><dd>${escapeHTML(manifest.analysis?.method||"Reproducible analysis record available")} · alignment ${escapeHTML(manifest.grid_alignment?.status||"recorded")}<br>Created ${escapeHTML(record.created_at_utc)}</dd></div>${cards}</dl>${pixel}`;
    }
    section.hidden=false;
    section.innerHTML=`${resultDetails}<div class="preview-actions"><button type="button" id="pairRecordButton">INSPECT FULL RECORD</button><button type="button" id="downloadPairRecordButton">DOWNLOAD REPRODUCTION RECORD</button></div>`;
    $("#pairRecordButton").addEventListener("click",()=>{$("#recordJson").textContent=JSON.stringify(record,null,2);$("#recordDialog").showModal();});
    $("#downloadPairRecordButton").addEventListener("click",()=>downloadJSON(record,`echo-gcov-pair-${record.status.toLowerCase()}.json`));
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
    const response=await fetch("/api/opera-catalog",{
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
    const response=await fetch("/api/opera-pair-analysis",{
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
  const response=await fetch("/api/qa-summary",{
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
    const response=await fetch("/api/case",{cache:"no-store"});
    if(!response.ok) throw new Error("Catalog metadata could not be loaded");
    catalog=await response.json();
    areaBounds=catalog.query.bounds_wgs84||null;
    areaFocusBounds=areaBounds;
    const reviewResponse=await fetch("/api/review",{cache:"no-store"});
    if(reviewResponse.ok) review=await reviewResponse.json();
    const reportResponse=await fetch("/api/qa-reports",{cache:"no-store"});
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
    const response=await fetch("/api/catalog",{
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
    const response=await fetch("/api/gcov-preview",{
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
    const response=await fetch("/api/gcov-pair-analysis",{
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
      const response=await fetch("/api/dswx-context",{cache:"no-store"});
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
    interpretation_limit:"This human review note is not verified evidence and does not alter the assessment disposition.",
  });
  $("#investigationChallengeForm").reset();
  $("#investigationChallengeDialog").close();
  renderCrossSensorAssessment();
  showToast("Challenge note added to this page session. Export it to keep a copy.");
});
$("#aboutButton").addEventListener("click",()=>$("#aboutDialog").showModal());
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
