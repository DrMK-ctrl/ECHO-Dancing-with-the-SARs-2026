const $ = (selector) => document.querySelector(selector);
const svg = $("#footprintMap");
let catalog;
let review;
let qaReports = {records:[]};
let pair;
let selectedScene = "before";
let zoom = 1;
let toastTimer;

const escapeHTML = (value) => String(value ?? "—").replace(/[&<>"']/g, (char) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[char]));

function selectedPair() {
  const candidate = review?.candidate_pair;
  if (candidate?.before?.scene_id && candidate?.after?.scene_id) {
    return {before_scene:candidate.before.scene_id,after_scene:candidate.after.scene_id};
  }
  return catalog.metadata_candidate_pairs?.[0] || null;
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

function trustedQAReportURI(report) {
  try {
    const url=new URL(report.artifact_uri);
    const match=url.pathname.match(/^\/NISAR\/NISAR_L2_GCOV_(?:BETA_V1|PROVISIONAL_V1|V1)\/([^/]+)\/([^/]+)_QA_REPORT\.pdf$/);
    return url.protocol==="https:" && url.hostname==="nisar.asf.earthdatacloud.nasa.gov" && !url.search && !url.hash && match?.[1]===report.scene_id && match?.[2]===report.scene_id ? url.href : null;
  } catch { return null; }
}

function displayedFeatures() {
  if (!catalog?.features?.length) return [];
  if (pair) {
    return [pair.before_scene,pair.after_scene]
      .map((id)=>catalog.features.find((feature)=>feature.properties.fileID===id))
      .filter(Boolean);
  }
  return [...catalog.features]
    .sort((a,b)=>Date.parse(a.properties.startTime)-Date.parse(b.properties.startTime))
    .slice(0,2);
}

function getBounds(features, point) {
  const xs = [point[0]], ys = [point[1]];
  const visit = (coordinates) => {
    if (typeof coordinates[0] === "number") { xs.push(coordinates[0]); ys.push(coordinates[1]); return; }
    coordinates.forEach(visit);
  };
  features.forEach((feature) => visit(feature.geometry.coordinates));
  const padX = Math.max((Math.max(...xs) - Math.min(...xs)) * 0.15, 0.06);
  const padY = Math.max((Math.max(...ys) - Math.min(...ys)) * 0.15, 0.06);
  return {minX:Math.min(...xs)-padX,maxX:Math.max(...xs)+padX,minY:Math.min(...ys)-padY,maxY:Math.max(...ys)+padY};
}

function drawMap() {
  const {query} = catalog;
  const displayed = displayedFeatures();
  const features = pair ? displayed : catalog.features.slice(0,60);
  const width = 1000, height = 600, pad = {l:78,r:32,t:35,b:43};
  const bounds = getBounds(features, [query.longitude, query.latitude]);
  const centerX = (bounds.minX + bounds.maxX) / 2, centerY = (bounds.minY + bounds.maxY) / 2;
  const spanX = (bounds.maxX - bounds.minX) / zoom, spanY = (bounds.maxY - bounds.minY) / zoom;
  const view = {minX:centerX-spanX/2,maxX:centerX+spanX/2,minY:centerY-spanY/2,maxY:centerY+spanY/2};
  const x = (lon) => pad.l + ((lon-view.minX)/(view.maxX-view.minX))*(width-pad.l-pad.r);
  const y = (lat) => pad.t + ((view.maxY-lat)/(view.maxY-view.minY))*(height-pad.t-pad.b);
  const grid = [];
  for (let i=0;i<=4;i++) {
    const gx=pad.l+i*(width-pad.l-pad.r)/4, lon=view.minX+i*(view.maxX-view.minX)/4;
    const gy=pad.t+i*(height-pad.t-pad.b)/4, lat=view.maxY-i*(view.maxY-view.minY)/4;
    grid.push(`<line class="grid-line" x1="${gx}" y1="${pad.t}" x2="${gx}" y2="${height-pad.b}"/><text class="grid-label" x="${gx}" y="${height-15}" text-anchor="middle">${Math.abs(lon).toFixed(2)}°${lon<0?'W':'E'}</text>`);
    grid.push(`<line class="grid-line" x1="${pad.l}" y1="${gy}" x2="${width-pad.r}" y2="${gy}"/><text class="grid-label" x="${pad.l-12}" y="${gy+3}" text-anchor="end">${Math.abs(lat).toFixed(2)}°${lat<0?'S':'N'}</text>`);
  }
  const shapes = features.map((feature,index) => {
    const rings = feature.geometry.type === "Polygon" ? feature.geometry.coordinates : feature.geometry.coordinates.flat();
    const css = pair ? (index === 0 ? "footprint-before" : "footprint-after") : "footprint-catalog";
    return rings.map((ring) => `<polygon class="${css}" points="${ring.map(([lon,lat])=>`${x(lon)},${y(lat)}`).join(" ")}"/>`).join("");
  }).join("");
  const px=x(query.longitude), py=y(query.latitude);
  svg.innerHTML = `${grid.join("")}<g>${shapes}</g><line class="point-leader" x1="${px+10}" y1="${py-8}" x2="${px+75}" y2="${py-43}"/><text class="point-label" x="${px+80}" y="${py-46}">SEARCH POINT</text><circle class="search-ring" cx="${px}" cy="${py}" r="10"/><circle class="search-dot" cx="${px}" cy="${py}" r="3.5"/>`;
}

function renderDetails(scene) {
  const displayed = displayedFeatures();
  const index = scene === "before" ? 0 : 1;
  const feature = displayed[index];
  if (!feature) {
    $("#sceneDetails").innerHTML = `<div class="full"><dt>OBSERVATION</dt><dd>${catalog.feature_count ? "Select a returned scene to inspect its record." : "No catalog observations were returned."}</dd></div>`;
    $("#beforeSelect").hidden = true;
    $("#afterSelect").hidden = true;
    selectedScene=scene;
    return;
  }
  const p = feature.properties;
  const qa = reviewProducts().find((item) => item.scene_id === p.fileID);
  const report = qaReports.records.find((item) => item.scene_id === p.fileID);
  const bytes = Object.values(p.bytes || {}).find((file) => file.format === "HDF5")?.bytes;
  const size = bytes ? `${(bytes/1e9).toFixed(2)} GB` : "HDF5";
  const time = new Date(p.startTime).toISOString().replace("T"," ").replace(".000Z"," UTC");
  const qaStatus = qa?.qa_summary?.identification_group || (qa?.hdf5_identification_metadata ? "REVIEWED · IDENTIFICATION MISMATCH" : "NOT REVIEWED");
  $("#sceneDetails").innerHTML = [
    ["ACQUISITION",time], ["MATURITY",catalog.query.data_maturity], ["PRODUCT","GCOV · L2"], ["QA SUMMARY",qaStatus], ["QA REPORT",report?`v${report.qa_software_version} · METADATA RECORDED`:"NOT RETAINED"], ["POLARIZATION",(p.mainBandPolarization||[]).join(" / ")], ["ORBIT",`${p.flightDirection} · PATH ${p.pathNumber}`], ["FRAME",`${p.frameNumber} · ${p.frameCoverage||"UNKNOWN"}`], ["FILE SIZE",size], ["SCENE ID",p.fileID,true]
  ].map(([label,value,full])=>`<div class="${full?'full':''}"><dt>${escapeHTML(label)}</dt><dd title="${escapeHTML(value)}">${escapeHTML(value)}</dd></div>`).join("");

  const labels = pair ? ["BEFORE","AFTER"] : ["SCENE 01","SCENE 02"];
  ["before","after"].forEach((key,sceneIndex)=>{
    const observed=displayed[sceneIndex];
    const button=$(`#${key}Select`);
    button.hidden=!observed;
    button.querySelector(".observation-tag").textContent=labels[sceneIndex];
    if (!observed) return;
    const date=new Date(observed.properties.startTime);
    button.querySelector(".observation-date").textContent=date.toLocaleDateString("en-GB",{day:"2-digit",month:"short",year:"numeric",timeZone:"UTC"}).toUpperCase();
    button.querySelector(".observation-time").textContent=date.toISOString().slice(11,19)+" UTC";
    $(`.legend-item.${key}`).innerHTML=`<i class="legend-swatch ${key}"></i> ${labels[sceneIndex]} · ${date.toLocaleDateString("en-GB",{day:"2-digit",month:"short",timeZone:"UTC"}).toUpperCase()}`;
  });
  $("#beforeSelect").classList.toggle("selected",scene==="before");
  $("#afterSelect").classList.toggle("selected",scene==="after");
  selectedScene=scene;
}

function showToast(message) {
  const node=$("#toast"); node.textContent=message; node.classList.add("show");
  clearTimeout(toastTimer); toastTimer=setTimeout(()=>node.classList.remove("show"),3200);
}

function renderWorkspace() {
  const displayed=displayedFeatures();
  if (pair && displayed.length !== 2) pair=null;
  const gap=pair ? Math.round((Date.parse(displayed[1].properties.startTime)-Date.parse(displayed[0].properties.startTime))/86400000) : null;
  const event=review?.event?.name || (review?.case_id || "ASF catalog search").replace(/[-_]/g," ");
  const status=review?.candidate_pair?.qa_status || review?.status || review?.review_status || (pair ? "METADATA_MATCH_ONLY" : catalog.feature_count ? "OBSERVATIONS FOUND" : "NO OBSERVATIONS");
  $(".top-context").innerHTML=`<span class="live-dot"></span> INVESTIGATION WORKSPACE <span class="slash">/</span> ${escapeHTML(review?.case_id || "CATALOG SEARCH")}`;
  $(".case-chip b").textContent=event;
  $(".case-chip small").textContent=displayed[0]?`Path ${displayed[0].properties.pathNumber} · frame ${displayed[0].properties.frameNumber}`:"No selected acquisition";
  $(".case-heading h1").textContent=event;
  $(".case-heading .subtitle").textContent=review?.candidate_question || (pair ? `Two metadata-compatible acquisitions are ${gap} days apart. Their pixels have not been compared.` : catalog.feature_count ? `${catalog.feature_count} ASF catalog records. No metadata-compatible temporal pair was found.` : "No NISAR GCOV observations match this point and time range.");
  const statusNode=$(".case-status");
  statusNode.classList.toggle("qa-hold",String(status).includes("QA_HOLD") || String(status).includes("REVIEW_REQUIRED"));
  $(".case-status b").textContent=status.replaceAll("_"," ");
  $(".case-status small").textContent=review?.candidate_pair?.crid?`PROCESSING RELEASE ${review.candidate_pair.crid}`:pair?`METADATA PAIR · ${catalog.query.data_maturity}`:"CATALOG ONLY · QA NOT REVIEWED";
  const identifiers=displayed.map((item)=>reviewProducts().find((record)=>record.scene_id===item.properties.fileID)?.qa_summary?.identification_group).filter(Boolean);
  $(".finding-card p").textContent=review ? `ASF lists two ${catalog.query.data_maturity} NISAR GCOV acquisitions ${gap} days apart. ${identifiers.length===2?`Both QA summaries report identification-group ${identifiers[0]===identifiers[1]?identifiers[0].toLowerCase():"review findings"}.`:"Product QA evidence is recorded for this pair."}` : pair ? `ASF metadata matched two ${catalog.query.data_maturity} NISAR GCOV observations ${gap} days apart. This is a catalog candidate only; product QA, grid alignment, and common valid pixels are not verified.` : `${catalog.feature_count} NISAR GCOV metadata records returned. ECHO found no orbit-separated, non-overlapping temporal pair that meets its catalog matching rules.`;
  $(".finding-meta b").textContent=status.replaceAll("_"," ");
  $(".coordinate-readout").innerHTML=`${Math.abs(catalog.query.longitude).toFixed(4)}° ${catalog.query.longitude<0?"W":"E"}&nbsp;&nbsp; ${Math.abs(catalog.query.latitude).toFixed(4)}° ${catalog.query.latitude<0?"S":"N"} <span>SEARCH POINT</span>`;
  $(".map-caption").textContent=pair ? `Catalog footprints · ${gap}-day metadata candidate` : `Catalog footprints · ${catalog.feature_count} records`;
  $(".timeline-head #intervalLabel").textContent=pair ? `${gap} DAY INTERVAL · ${catalog.query.data_maturity} DATA` : `${catalog.feature_count} RECORDS · NO MATCHED PAIR`;
  $(".timeline-note").textContent=pair ? "Select an acquisition to inspect its catalog record" : "Individual observations are not a change pair";
  $(".evidence-title .eyebrow").innerHTML=`${escapeHTML(review?.case_id || "ASF CATALOG")} <span>·</span> EVIDENCE`;
  $(".evidence-count").innerHTML=`${String(displayed.length).padStart(2,"0")} <i>/</i> ${String(catalog.feature_count || 0).padStart(2,"0")}`;
  $(".confidence-block .readiness-value").innerHTML=review?`1 <small>OF 4 GATES · QA HOLD</small>`:`0 <small>OF 4 GATES · CATALOG ONLY</small>`;
  document.querySelectorAll(".confidence-block .readiness-track i").forEach((item,index)=>item.style.background=review&&index===0?"var(--cyan)":"#293940");
  $(".confidence-block p").textContent=review?"Catalog pairing is complete. Product QA reports an identification failure; alignment and valid-pixel overlap remain unchecked.":pair?"Catalog pairing is complete. Product QA, pixel-grid alignment, and common valid coverage remain unreviewed.":"Catalog discovery is complete. No temporal pair passed ECHO's metadata screening; no change claim is available.";
  $(".finding-meta b").textContent=status.replaceAll("_"," ");
  if (!review) {
    $(".gate-count").textContent=pair?"1 CANDIDATE · 2 OPEN":"NO PAIR · QA NOT REVIEWED";
    $(".gate-list").innerHTML=`<li><span class="gate-icon ${pair?'review':'open'}">${pair?'!':'○'}</span><span><b>Catalog pair screening</b><small>${pair?'Metadata match only; pixels not compared':'No distinct-orbit temporal pair found'}</small></span><span class="gate-state">${pair?'CANDIDATE':'OPEN'}</span></li><li><span class="gate-icon open">○</span><span><b>Product QA</b><small>Per-product checks have not been retrieved for this search</small></span><span class="gate-state">OPEN</span></li><li><span class="gate-icon open">○</span><span><b>Grid and interpretation</b><small>Registration and physical explanation not assessed</small></span><span class="gate-state">OPEN</span></li>`;
  }
  drawMap();
  renderDetails("before");
}

async function init() {
  try {
    const response=await fetch("/api/case",{cache:"no-store"});
    if(!response.ok) throw new Error("Catalog metadata could not be loaded");
    catalog=await response.json();
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
  $("#queryLongitude").value=query.longitude ?? 0;
  $("#queryLatitude").value=query.latitude ?? 0;
  $("#queryStart").value=query.start_date ?? "2026-01-01";
  $("#queryEnd").value=query.end_date ?? "2026-01-31";
  $("#queryMaturity").value=query.data_maturity ?? "PROVISIONAL";
  $("#catalogDialog").showModal();
}

async function runCatalogSearch(event) {
  event.preventDefault();
  const submit=$("#runCatalogSearch");
  submit.disabled=true;
  submit.textContent="SEARCHING…";
  const payload={
    longitude:Number($("#queryLongitude").value),
    latitude:Number($("#queryLatitude").value),
    start_date:$("#queryStart").value,
    end_date:$("#queryEnd").value,
    maturity:$("#queryMaturity").value,
  };
  try {
    const response=await fetch("/api/catalog",{
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify(payload),
    });
    const record=await response.json();
    if(!response.ok) throw new Error(record.error || "ASF catalog search failed");
    catalog=record;
    review=null;
    pair=selectedPair();
    selectedScene="before";
    zoom=1;
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

$("#zoomIn").addEventListener("click",()=>{zoom=Math.min(zoom*1.35,5);if(catalog)drawMap()});
$("#zoomOut").addEventListener("click",()=>{zoom=Math.max(zoom/1.35,0.7);if(catalog)drawMap()});
$("#resetView").addEventListener("click",()=>{zoom=1;if(catalog)drawMap()});
$("#beforeSelect").addEventListener("click",()=>catalog&&renderDetails("before"));
$("#afterSelect").addEventListener("click",()=>catalog&&renderDetails("after"));
$("#recordToggle").addEventListener("click",()=>{
  if(!catalog)return;
  const feature=displayedFeatures()[selectedScene==="before"?0:1];
  if(!feature){showToast("No observation is selected.");return;}
  $("#recordJson").textContent=JSON.stringify(feature,null,2);
  $("#recordDialog").showModal();
});
$("#qaRecordToggle").addEventListener("click",()=>{
  if(!review){showToast("Product QA has not been reviewed for this catalog search.");return;}
  const sceneIds=new Set(displayedFeatures().map((item)=>item.properties.fileID));
  const reports=qaReports.records.filter((item)=>sceneIds.has(item.scene_id));
  const qaReview=reviewProducts();
  $("#qaSummary").innerHTML=reports.length?reports.map((report)=>{
    const metadata=report.product_metadata||{};
    const qa=qaReview.find((item)=>item.scene_id===report.scene_id);
    const checks=report.catalog_crosschecks||{};
    const matching=Object.values(checks).filter((value)=>value===true).length;
    const checkTotal=Object.values(checks).filter((value)=>value!==null).length;
    const sourceDiagnostic=report.identification_crosscheck?.status||"NOT AVAILABLE";
    const reportURI=trustedQAReportURI(report);
    const sourceLink=reportURI?`<a href="${escapeHTML(reportURI)}" target="_blank" rel="noopener noreferrer">Open original ASF report ↗</a>`:`<span>ASF report link unavailable · source URI did not validate</span>`;
    return `<article class="qa-report-card"><div class="qa-report-heading"><span>ASF QA REPORT · ${escapeHTML(report.qa_software_version)}</span><b>${escapeHTML(qa?.qa_summary?.identification_group||"CSV DISPOSITION IN REVIEW RECORD")}</b></div><h3>${escapeHTML(report.scene_id)}</h3><dl><div><dt>REPORT PROCESSED</dt><dd>${escapeHTML(report.report_processing_time_utc)}</dd></div><div><dt>RETRIEVED</dt><dd>${escapeHTML(report.retrieved_at_utc)}</dd></div><div><dt>PRODUCT FORMAT</dt><dd>Spec ${escapeHTML(metadata.productSpecificationVersion)} · product ${escapeHTML(metadata.productVersion)}</dd></div><div><dt>IDENTIFICATION</dt><dd>${escapeHTML(metadata.instrumentName)} · ${(metadata.listOfObservationModes||[]).map(escapeHTML).join(", ")}</dd></div><div><dt>CATALOG CROSS-CHECK</dt><dd>${matching}/${checkTotal} reported orbit, track, and frame matches</dd></div><div><dt>LIMITED SOURCE DIAGNOSTIC</dt><dd>${escapeHTML(sourceDiagnostic)} · not provider failure attribution</dd></div></dl><p>${sourceLink}<span class="qa-checksum">SHA-256 ${escapeHTML(report.artifact_sha256)}</span></p></article>`;
  }).join(""):`<p class="qa-empty">No parsed QA report metadata is retained for these scenes. The case review and provider QA summaries remain available in the machine-readable record.</p>`;
  $("#qaJson").textContent=JSON.stringify({qa_review:review,provider_qa_report_records:reports,report_record_scope:"PDF metadata and provenance only; provider QA disposition comes from the separate CSV and is not overridden."},null,2);
  $("#qaDialog").showModal();
});
$("#challengeButton").addEventListener("click",()=>$("#challengeDialog").showModal());
$("#aboutButton").addEventListener("click",()=>$("#aboutDialog").showModal());
$("#searchCatalog").addEventListener("click",openCatalogSearch);
$("#closeCatalogDialog").addEventListener("click",()=>$("#catalogDialog").close());
$("#catalogQueryForm").addEventListener("submit",runCatalogSearch);
$("#sourcesNav").addEventListener("click",()=>showToast("Source records are available from the observation details panel."));
init();
