const $ = (selector) => document.querySelector(selector);
const svg = $("#footprintMap");
let catalog;
let review;
let qaReports = {records:[]};
const qaSummaryByScene = new Map();
const qaFeatureByScene = new Map();
let pair;
let selectedSceneId = null;
let zoom = 1;
let toastTimer;
let basemapEnabled = true;
let areaBounds = null;
let areaPreview = null;
let drawingArea = false;
let areaStart = null;
let mapTransform = null;

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

function providerQAStatus(sceneId) {
  const live=qaSummaryByScene.get(sceneId)?.evidence?.status;
  if(live)return live;
  const reviewed=reviewProducts().find((item)=>item.scene_id===sceneId);
  return reviewed?.qa_summary?.identification_group || (reviewed?.hdf5_identification_metadata ? "REVIEWED · IDENTIFICATION MISMATCH" : "NOT REVIEWED");
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

function getBounds(features, point, area = null) {
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
  const padX = Math.max((Math.max(...xs) - Math.min(...xs)) * 0.15, 0.06);
  const padY = Math.max((Math.max(...ys) - Math.min(...ys)) * 0.15, 0.06);
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

function drawMap() {
  const {query} = catalog;
  const displayed = displayedFeatures();
  const features = (catalog.features||[]).slice(0,60);
  const selectedFeature=chronologicalFeatures().find((feature)=>feature.properties.fileID===selectedSceneId);
  if(selectedFeature&&!features.some((item)=>item.properties.fileID===selectedFeature.properties.fileID))features.push(selectedFeature);
  displayed.forEach((feature)=>{
    if(feature&&!features.some((item)=>item.properties.fileID===feature.properties.fileID))features.push(feature);
  });
  if(pair)features.sort((a,b)=>{
    const rank=(feature)=>feature.properties.fileID===selectedSceneId?3:feature.properties.fileID===pair.before_scene?1:feature.properties.fileID===pair.after_scene?2:0;
    return rank(a)-rank(b);
  });
  const width = 1000, height = 600, pad = {l:78,r:32,t:35,b:43};
  const center=geographicCenter(query);
  const bounds = getBounds(features, center, areaBounds || query.bounds_wgs84);
  const centerX = (bounds.minX + bounds.maxX) / 2, centerY = (bounds.minY + bounds.maxY) / 2;
  const spanX = (bounds.maxX - bounds.minX) / zoom, spanY = (bounds.maxY - bounds.minY) / zoom;
  const view = {minX:centerX-spanX/2,maxX:centerX+spanX/2,minY:centerY-spanY/2,maxY:centerY+spanY/2};
  const x = (lon) => pad.l + ((lon-view.minX)/(view.maxX-view.minX))*(width-pad.l-pad.r);
  const y = (lat) => pad.t + ((view.maxY-lat)/(view.maxY-view.minY))*(height-pad.t-pad.b);
  const plotWidth=width-pad.l-pad.r, plotHeight=height-pad.t-pad.b;
  mapTransform={view,pad,width,height,plotWidth,plotHeight};
  const imageDate=basemapDate(displayed);
  const imageURL=basemapEnabled && imageDate ? gibsImageURL(view,plotWidth,plotHeight,imageDate) : null;
  const imageMarkup=imageURL ? `<image class="gibs-basemap" x="${pad.l}" y="${pad.t}" width="${plotWidth}" height="${plotHeight}" preserveAspectRatio="none" href="${escapeHTML(imageURL)}"/>` : "";
  const grid = [];
  for (let i=0;i<=4;i++) {
    const gx=pad.l+i*(width-pad.l-pad.r)/4, lon=view.minX+i*(view.maxX-view.minX)/4;
    const gy=pad.t+i*(height-pad.t-pad.b)/4, lat=view.maxY-i*(view.maxY-view.minY)/4;
    grid.push(`<line class="grid-line" x1="${gx}" y1="${pad.t}" x2="${gx}" y2="${height-pad.b}"/><text class="grid-label" x="${gx}" y="${height-15}" text-anchor="middle">${Math.abs(lon).toFixed(2)}°${lon<0?'W':'E'}</text>`);
    grid.push(`<line class="grid-line" x1="${pad.l}" y1="${gy}" x2="${width-pad.r}" y2="${gy}"/><text class="grid-label" x="${pad.l-12}" y="${gy+3}" text-anchor="end">${Math.abs(lat).toFixed(2)}°${lat<0?'S':'N'}</text>`);
  }
  const shapes = features.map((feature) => {
    const rings = feature.geometry.type === "Polygon" ? feature.geometry.coordinates : feature.geometry.coordinates.flat();
    const sceneId=feature.properties.fileID;
    const css = pair&&sceneId===pair.before_scene?"footprint-before":pair&&sceneId===pair.after_scene?"footprint-after":"footprint-catalog";
    const selected=sceneId===selectedSceneId?" footprint-selected":"";
    return rings.map((ring) => `<polygon class="${css}${selected}" data-scene-id="${escapeHTML(sceneId)}" points="${ring.map(([lon,lat])=>`${x(lon)},${y(lat)}`).join(" ")}"><title>ASF footprint · ${escapeHTML(sceneId)}</title></polygon>`).join("");
  }).join("");
  const px=x(center[0]), py=y(center[1]);
  const area=areaPreview||areaBounds;
  const selection=area?`<rect class="aoi-selection" x="${x(area[0])}" y="${y(area[3])}" width="${Math.max(1,x(area[2])-x(area[0]))}" height="${Math.max(1,y(area[1])-y(area[3]))}"/>`:"";
  svg.classList.toggle("area-draw-mode",drawingArea);
  svg.innerHTML = `${imageMarkup}${grid.join("")}<g>${shapes}</g>${selection}<line class="point-leader" x1="${px+10}" y1="${py-8}" x2="${px+75}" y2="${py-43}"/><text class="point-label" x="${px+80}" y="${py-46}">${area?"AREA CENTER":"SEARCH POINT"}</text><circle class="search-ring" cx="${px}" cy="${py}" r="10"/><circle class="search-dot" cx="${px}" cy="${py}" r="3.5"/>`;
  const basemapLabel=$("#mapDataAttribution");
  const toggle=$("#toggleBasemap");
  toggle.setAttribute("aria-pressed",String(basemapEnabled));
  toggle.textContent=basemapEnabled ? "NASA CONTEXT ON" : "NASA CONTEXT OFF";
  basemapLabel.textContent=imageURL ? `NASA GIBS · MODIS TERRA TRUE COLOR · ${imageDate} · CONTEXT ONLY` : basemapEnabled ? "NASA GIBS DATE UNAVAILABLE · GRID SHOWN" : "BASEMAP OFF · COORDINATE GRID";
  const image=svg.querySelector(".gibs-basemap");
  image?.addEventListener("error",()=>{
    image.remove();
    basemapLabel.textContent=`NASA GIBS UNAVAILABLE · ${imageDate} · GRID SHOWN`;
  },{once:true});
  syncAreaButton();
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
  if (pair && displayed.length !== 2) pair=null;
  if(!ordered.some((feature)=>feature.properties.fileID===selectedSceneId)){
    selectedSceneId=ordered.find((feature)=>feature.properties.fileID===pair?.before_scene)?.properties.fileID||ordered[0]?.properties.fileID||null;
  }
  renderTimeline();
  renderPairLegend();
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
  const mapCenter=geographicCenter(catalog.query);
  $(".coordinate-readout").innerHTML=`${Math.abs(mapCenter[0]).toFixed(4)}° ${mapCenter[0]<0?"W":"E"}&nbsp;&nbsp; ${Math.abs(mapCenter[1]).toFixed(4)}° ${mapCenter[1]<0?"S":"N"} <span>${areaBounds?"AREA CENTER":"SEARCH POINT"}</span>`;
  const plottedIds=new Set((catalog.features||[]).slice(0,60).map((feature)=>feature.properties.fileID));
  if(selectedSceneId)plottedIds.add(selectedSceneId);
  displayed.forEach((feature)=>plottedIds.add(feature.properties.fileID));
  const plottedCount=plottedIds.size;
  $(".map-caption").textContent=`${plottedCount} ASF footprints shown${catalog.feature_count>plottedCount?` of ${catalog.feature_count}`:""}${pair?` · ${gap}-day metadata candidate`:""}`;
  $("#otherObservationLegend").hidden=(catalog.features?.length||0)<=2;
  $(".timeline-head #intervalLabel").textContent=pair ? `${ordered.length} ACQUISITIONS · ${gap} DAY METADATA CANDIDATE` : `${ordered.length} ACQUISITIONS · ${catalog.query.data_maturity} DATA`;
  $(".timeline-note").textContent=ordered.length>1?"Select any acquisition to update the map and source details · gaps show elapsed acquisition time":"Select the acquisition to inspect its source details";
  $(".evidence-title .eyebrow").innerHTML=`${escapeHTML(review?.case_id || "ASF CATALOG")} <span>·</span> EVIDENCE`;
  $(".confidence-block .readiness-value").innerHTML=review?`1 <small>OF 4 GATES · QA HOLD</small>`:`0 <small>OF 4 GATES · CATALOG ONLY</small>`;
  document.querySelectorAll(".confidence-block .readiness-track i").forEach((item,index)=>item.style.background=review&&index===0?"var(--cyan)":"#293940");
  $(".confidence-block p").textContent=review?"Catalog pairing is complete. Product QA reports an identification failure; alignment and valid-pixel overlap remain unchecked.":pair?"Catalog pairing is complete. Product QA, pixel-grid alignment, and common valid coverage remain unreviewed.":"Catalog discovery is complete. No temporal pair passed ECHO's metadata screening; no change claim is available.";
  $(".finding-meta b").textContent=status.replaceAll("_"," ");
  if (!review) {
    $(".gate-count").textContent=pair?"1 CANDIDATE · 2 OPEN":"NO PAIR · QA NOT REVIEWED";
    $(".gate-list").innerHTML=`<li><span class="gate-icon ${pair?'review':'open'}">${pair?'!':'○'}</span><span><b>Catalog pair screening</b><small>${pair?'Metadata match only; pixels not compared':'No distinct-orbit temporal pair found'}</small></span><span class="gate-state">${pair?'CANDIDATE':'OPEN'}</span></li><li><span class="gate-icon open">○</span><span><b>Product QA</b><small>Per-product checks have not been retrieved for this search</small></span><span class="gate-state">OPEN</span></li><li><span class="gate-icon open">○</span><span><b>Grid and interpretation</b><small>Registration and physical explanation not assessed</small></span><span class="gate-state">OPEN</span></li>`;
  }
  renderDetails(selectedSceneId);
  drawMap();
}

async function init() {
  try {
    const response=await fetch("/api/case",{cache:"no-store"});
    if(!response.ok) throw new Error("Catalog metadata could not be loaded");
    catalog=await response.json();
    areaBounds=catalog.query.bounds_wgs84||null;
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
  $("#queryLongitude").value=center[0] ?? 0;
  $("#queryLatitude").value=center[1] ?? 0;
  $("#queryStart").value=query.start_date ?? "2026-01-01";
  $("#queryEnd").value=query.end_date ?? "2026-01-31";
  $("#queryMaturity").value=query.data_maturity ?? "PROVISIONAL";
  const summary=$("#queryAreaSummary");
  summary.hidden=!areaBounds;
  summary.innerHTML=areaBounds?`Selected WGS84 bounds (west, south, east, north): ${areaBounds.map((v)=>v.toFixed(4)).join(", ")} <button type="button" id="clearSearchArea">Use point search</button>`:"";
  $("#runCatalogSearch").textContent=areaBounds?"SEARCH AREA":"SEARCH POINT";
  $("#clearSearchArea")?.addEventListener("click",()=>{
    areaBounds=null; summary.hidden=true; summary.textContent="";
    if(catalog?.query)catalog.query.bounds_wgs84=null;
    $("#runCatalogSearch").textContent="SEARCH POINT"; syncAreaButton();
    if(catalog)renderWorkspace();
  });
  $("#catalogDialog").showModal();
}

async function runCatalogSearch(event) {
  event.preventDefault();
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
    areaBounds=record.query.bounds_wgs84||null;
    review=null;
    pair=selectedPair();
    selectedSceneId=null;
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
$("#toggleBasemap").addEventListener("click",()=>{basemapEnabled=!basemapEnabled;if(catalog)drawMap()});
$("#drawArea").addEventListener("click",()=>{
  if(areaBounds){areaBounds=null;areaPreview=null;drawingArea=false;if(catalog?.query)catalog.query.bounds_wgs84=null;if(catalog)renderWorkspace();return;}
  drawingArea=!drawingArea; areaPreview=null; syncAreaButton();
  svg.classList.toggle("area-draw-mode",drawingArea);
  showToast(drawingArea?"Drag on the map to select a WGS84 rectangle.":"Area selection cancelled.");
});
svg.addEventListener("pointerdown",(event)=>{
  if(!drawingArea||!mapTransform||event.button!==0)return;
  event.preventDefault(); areaStart=mapCoordinate(event); areaPreview=[areaStart[0],areaStart[1],areaStart[0],areaStart[1]];
  svg.setPointerCapture(event.pointerId); drawMap();
});
svg.addEventListener("pointermove",(event)=>{
  if(!drawingArea||!areaStart||!mapTransform)return;
  const [lon,lat]=mapCoordinate(event);
  areaPreview=[Math.min(areaStart[0],lon),Math.min(areaStart[1],lat),Math.max(areaStart[0],lon),Math.max(areaStart[1],lat)];
  drawMap();
});
svg.addEventListener("pointerup",(event)=>{
  if(!areaStart||!areaPreview)return;
  const width=areaPreview[2]-areaPreview[0],height=areaPreview[3]-areaPreview[1];
  if(width>0&&height>0){areaBounds=areaPreview;drawingArea=false;showToast("Area selected. Find observations to query ASF for intersecting footprints.");}
  else showToast("Drag a rectangle with non-zero width and height.");
  areaStart=null; areaPreview=null; syncAreaButton();
  if(areaBounds)renderWorkspace();else drawMap();
  if(svg.hasPointerCapture(event.pointerId))svg.releasePointerCapture(event.pointerId);
});
svg.addEventListener("pointercancel",()=>{areaStart=null;areaPreview=null;drawMap();});
$("#timelineTrack").addEventListener("click",(event)=>{
  const button=event.target.closest(".timeline-observation[data-scene-id]");
  if(button)selectObservation(button.dataset.sceneId);
});
svg.addEventListener("click",(event)=>{
  const polygon=event.target.closest("polygon[data-scene-id]");
  if(polygon)selectObservation(polygon.dataset.sceneId,{scrollTimeline:true});
});
$("#recordToggle").addEventListener("click",()=>{
  if(!catalog)return;
  const feature=chronologicalFeatures().find((item)=>item.properties.fileID===selectedSceneId);
  if(!feature){showToast("No observation is selected.");return;}
  $("#recordJson").textContent=JSON.stringify(feature,null,2);
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
    const sourceDiagnostic=report.identification_crosscheck?.status||"NOT AVAILABLE";
    const reportURI=trustedQAReportURI(report);
    const sourceLink=reportURI?`<a href="${escapeHTML(reportURI)}" target="_blank" rel="noopener noreferrer">Open original ASF report ↗</a>`:`<span>ASF report link unavailable · source URI did not validate</span>`;
    return `<article class="qa-report-card"><div class="qa-report-heading"><span>ASF QA REPORT · ${escapeHTML(report.qa_software_version)}</span><b>${escapeHTML(liveQA?.evidence?.status||qa?.qa_summary?.identification_group||"CSV DISPOSITION IN REVIEW RECORD")}</b></div><h3>${escapeHTML(report.scene_id)}</h3><dl><div><dt>REPORT PROCESSED</dt><dd>${escapeHTML(report.report_processing_time_utc)}</dd></div><div><dt>RETRIEVED</dt><dd>${escapeHTML(report.retrieved_at_utc)}</dd></div><div><dt>PRODUCT FORMAT</dt><dd>Spec ${escapeHTML(metadata.productSpecificationVersion)} · product ${escapeHTML(metadata.productVersion)}</dd></div><div><dt>IDENTIFICATION</dt><dd>${escapeHTML(metadata.instrumentName)} · ${(metadata.listOfObservationModes||[]).map(escapeHTML).join(", ")}</dd></div><div><dt>CATALOG CROSS-CHECK</dt><dd>${matching}/${checkTotal} reported orbit, track, and frame matches</dd></div><div><dt>LIMITED SOURCE DIAGNOSTIC</dt><dd>${escapeHTML(sourceDiagnostic)} · not provider failure attribution</dd></div></dl><p>${sourceLink}<span class="qa-checksum">SHA-256 ${escapeHTML(report.artifact_sha256)}</span></p></article>`;
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
$("#aboutButton").addEventListener("click",()=>$("#aboutDialog").showModal());
$("#searchCatalog").addEventListener("click",openCatalogSearch);
$("#closeCatalogDialog").addEventListener("click",()=>$("#catalogDialog").close());
$("#catalogQueryForm").addEventListener("submit",runCatalogSearch);
$("#sourcesNav").addEventListener("click",()=>showToast("Source records are available from the observation details panel."));
init();
