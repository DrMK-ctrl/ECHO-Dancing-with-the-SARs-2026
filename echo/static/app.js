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

function rasterPixelAt(localX,localY) {
  let nearest=null,distance=Infinity;
  for(const cell of previewScreenCells){
    const current=Math.hypot(cell.centerX-localX,cell.centerY-localY);
    if(current<distance){distance=current;nearest=cell;}
  }
  return distance<=14?nearest:null;
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
  const bounds = areaBounds||areaFocusBounds
    ? getBounds([], center, areaBounds||areaFocusBounds)
    : getBounds(features, center, areaPreview || query.bounds_wgs84);
  const centerX = (bounds.minX + bounds.maxX) / 2 + mapPan[0], centerY = (bounds.minY + bounds.maxY) / 2 + mapPan[1];
  const spanX = (bounds.maxX - bounds.minX) / zoom, spanY = (bounds.maxY - bounds.minY) / zoom;
  const view = {minX:centerX-spanX/2,maxX:centerX+spanX/2,minY:centerY-spanY/2,maxY:centerY+spanY/2};
  const x = (lon) => pad.l + ((lon-view.minX)/(view.maxX-view.minX))*(width-pad.l-pad.r);
  const y = (lat) => pad.t + ((view.maxY-lat)/(view.maxY-view.minY))*(height-pad.t-pad.b);
  const plotWidth=width-pad.l-pad.r, plotHeight=height-pad.t-pad.b;
  mapTransform={view,pad,width,height,plotWidth,plotHeight};
  svg.setAttribute("viewBox","0 0 1000 600");
  const imageDate=basemapDate(displayed);
  const imageURL=basemapEnabled && imageDate ? gibsImageURL(view,plotWidth,plotHeight,imageDate) : null;
  const imageMarkup=imageURL ? `<image class="gibs-basemap" x="${pad.l}" y="${pad.t}" width="${plotWidth}" height="${plotHeight}" preserveAspectRatio="none" href="${escapeHTML(imageURL)}"/>` : "";
  const pairRaster=pairAnalysisImage(x,y);
  const rasterURL=pairRaster||rasterPreviewImage(x,y);
  const rasterMarkup=rasterURL?`<image class="gcov-raster-preview" x="0" y="0" width="1000" height="600" preserveAspectRatio="none" href="${rasterURL}"/>`:"";
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
  const pairMeasured=gcovPairAnalysis?.status==="MEASURED_DESCRIPTIVE_ONLY";
  svg.classList.toggle("gcov-raster-active",Boolean(gcovPreview)||pairMeasured);
  svg.innerHTML = `${imageMarkup}${rasterMarkup}${grid.join("")}<g>${shapes}</g>${selection}<line class="point-leader" x1="${px+10}" y1="${py-8}" x2="${px+75}" y2="${py-43}"/><text class="point-label" x="${px+80}" y="${py-46}">${area?"AREA CENTER":"SEARCH POINT"}</text><circle class="search-ring" cx="${px}" cy="${py}" r="10"/><circle class="search-dot" cx="${px}" cy="${py}" r="3.5"/>`;
  const warning=$("#mapWarning");
  const watermark=$(".map-watermark");
  const ramp=$("#previewRamp");
  ramp.hidden=!gcovPreview&&!pairMeasured;
  if(pairMeasured){
    const scale=pairChangeScale();
    ramp.classList.add("pair-ramp");
    $("#previewRampRange").textContent=`−${scale.toFixed(2)} to +${scale.toFixed(2)} dB`;
    warning.classList.add("qa-preview");
    warning.innerHTML='<span class="warning-glyph">Δ</span><span><b>DESCRIPTIVE SAR CHANGE</b><small>Provider QA PASS · no event or cause inferred</small></span>';
    watermark.classList.add("raster-preview");
    watermark.innerHTML="ECHO <span>·</span> NISAR GCOV LOG RATIO";
    $("#mapDataAttribution").textContent=`NISAR GCOV · ${gcovPairAnalysis.measurement.layer} · Δγ⁰ dB · QA PASS · NASA GIBS IS CONTEXT ONLY`;
  }else if(gcovPairAnalysis?.status==="QA_HELD"){
    ramp.classList.remove("pair-ramp");
    warning.classList.add("qa-preview");
    warning.innerHTML='<span class="warning-glyph">△</span><span><b>PAIR ANALYSIS HELD</b><small>Provider QA did not pass · no change pixels read</small></span>';
    watermark.classList.remove("raster-preview");
    watermark.innerHTML="ECHO <span>·</span> QA GATE · NO CHANGE LAYER";
    $("#mapDataAttribution").textContent="PAIR QA HOLD · NO MEASUREMENT LAYER · NASA GIBS IS CONTEXT ONLY";
  }else if(gcovPreview){
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
    ramp.classList.remove("pair-ramp");
    warning.classList.remove("qa-preview");
    warning.innerHTML='<span class="warning-glyph">△</span><span><b>NO RADAR PIXELS LOADED</b><small>Footprints show ASF metadata coverage only</small></span>';
    watermark.classList.remove("raster-preview");
    watermark.innerHTML="ECHO <span>·</span> CATALOG VIEW";
    $("#mapDataAttribution").textContent=imageURL?`NASA GIBS · MODIS TERRA TRUE COLOR · ${imageDate} · CONTEXT ONLY`:basemapEnabled?"NASA GIBS DATE UNAVAILABLE · GRID SHOWN":"BASEMAP OFF · COORDINATE GRID";
  }
  const basemapLabel=$("#mapDataAttribution");
  const toggle=$("#toggleBasemap");
  toggle.setAttribute("aria-pressed",String(basemapEnabled));
  toggle.textContent=basemapEnabled ? "NASA CONTEXT ON" : "NASA CONTEXT OFF";
  if(!gcovPreview&&!gcovPairAnalysis)basemapLabel.textContent=imageURL ? `NASA GIBS · MODIS TERRA TRUE COLOR · ${imageDate} · CONTEXT ONLY` : basemapEnabled ? "NASA GIBS DATE UNAVAILABLE · GRID SHOWN" : "BASEMAP OFF · COORDINATE GRID";
  const image=svg.querySelector(".gibs-basemap");
  image?.addEventListener("error",()=>{
    image.remove();
    basemapLabel.textContent=`NASA GIBS UNAVAILABLE · ${imageDate} · GRID SHOWN`;
  },{once:true});
  syncAreaButton();
  renderGcovPreviewDetails();
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
    if(record.status==="QA_HELD"){
      const gates=record.analysis_gates||{};
      const gateRows=Object.entries(gates).map(([name,status])=>`<div><dt>${escapeHTML(name.replaceAll("_"," "))}</dt><dd>${escapeHTML(status)}</dd></div>`).join("");
      const nextEvidence=(record.next_evidence||[]).map(item=>`<li>${escapeHTML(item)}</li>`).join("");
      resultDetails=`<h3>PAIR HELD AT PROVIDER QA GATE</h3><p>No product metadata or radar measurement arrays were read for this pair. QA status is preserved as reported by ASF; no comparison result exists.</p><dl>${cards}<div class="full"><dt>ANALYSIS GATES</dt><dd><div class="pair-gate-grid">${gateRows}</div></dd></div><div class="full"><dt>NEXT EVIDENCE REQUIRED</dt><dd><ul class="pair-next-evidence">${nextEvidence}</ul></dd></div><div class="full"><dt>DISPOSITION</dt><dd>Held roles: ${escapeHTML((record.held_roles||[]).join(", ")||"unknown")} · Measurement: none · Analysis manifest: none</dd></div></dl>`;
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
  const qualityNote=quality.display_eligible_pixel_count===0?`<p class="preview-quality-note"><b>NO PIXELS SHOWN</b> · ${quality.aoi_pixel_center_count.toLocaleString()} AOI centers were read, but none met ECHO's current display-quality screen. Input-data exception values: ${exceptionCodes}. ECHO does not interpret unrecognized codes; flagged samples remain excluded and are retained in the source record.</p>`:"";
  const selected=selectedPreviewPixel;
  const pixelDetails=selected?`<p class="preview-pixel-readout"><b>Selected pixel</b> · row ${selected.row+window.row_start}, column ${selected.column+window.column_start} · γ⁰ ${selected.raw.toPrecision(6)} linear · ${selected.db.toFixed(2)} dB · mask ${selected.mask} · ${escapeHTML(selected.looks)} looks · exception ${selected.exception}</p>`:"<p>Click a rendered pixel to inspect its product value and quality codes.</p>";
  section.hidden=false;
  const qaLink=trustedQASummaryURI(qa);
  section.innerHTML=`<h3>REAL NISAR GCOV · ${status==="PASS"?"SINGLE-OBSERVATION PREVIEW":"QA-HELD DIAGNOSTIC PREVIEW"}</h3><p>This is one acquisition. It shows gamma-zero backscatter; it is not a change measurement or an event interpretation.</p><dl><div><dt>PROVIDER / PRODUCT</dt><dd>${escapeHTML(source.provider)} · ${escapeHTML(source.product)}<br>${escapeHTML(source.scene_id)}</dd></div><div><dt>ACQUISITION UTC</dt><dd>${escapeHTML(source.catalog_metadata.startTime)} · ${escapeHTML(source.catalog_metadata.stopTime)}</dd></div><div><dt>MEASUREMENT</dt><dd>${escapeHTML(record.measurement.dataset)}<br>${escapeHTML(record.measurement.units)} · Frequency ${escapeHTML(record.measurement.frequency)}</dd></div><div><dt>PROVIDER QA</dt><dd class="${status==="FAIL"?"qa-fail":""}">${escapeHTML(status)} · ${escapeHTML(qa.artifact_size_bytes)} B · retrieved ${escapeHTML(qa.retrieved_at_utc)}${qaLink?`<br><a href="${escapeHTML(qaLink)}" target="_blank" rel="noopener noreferrer">Open original ASF QA summary ↗</a>`:""}</dd></div><div><dt>WINDOW / GRID</dt><dd>${window.shape[1]} × ${window.shape[0]} pixels · EPSG:${record.grid.epsg_code}<br>${quality.aoi_pixel_center_count.toLocaleString()} AOI centers</dd></div><div><dt>DISPLAY MASK</dt><dd>${quality.display_eligible_pixel_count.toLocaleString()} shown · ${quality.excluded_nonvalid_mask_count} nonvalid · ${quality.excluded_exception_count} exception · ${quality.excluded_nonfinite_or_nonpositive_count} nonfinite/nonpositive</dd></div><div><dt>DISPLAY SCALE</dt><dd>10 log₁₀(linear γ⁰) · ${escapeHTML(stretchLabel)}<br>2nd–98th percentile stretch</dd></div><div><dt>ACCESS</dt><dd>${escapeHTML(record.provenance.window_access_method)} · ${Number(record.provenance.fsspec_range_bytes_requested).toLocaleString()} range bytes</dd></div><div class="full"><dt>QA SUMMARY SHA-256</dt><dd>${escapeHTML(record.provenance.provider_qa_artifact_sha256)}</dd></div></dl>${qualityNote}${pixelDetails}<div class="preview-actions"><button type="button" id="previewRecordButton">INSPECT FULL RECORD</button><button type="button" id="downloadPreviewButton">DOWNLOAD REPRODUCTION RECORD</button></div>`;
  $("#previewRecordButton").addEventListener("click",()=>{
    $("#recordJson").textContent=JSON.stringify(record,null,2);
    $("#recordDialog").showModal();
  });
  $("#downloadPreviewButton").addEventListener("click",downloadPreviewRecord);
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
  $(".coordinate-readout").innerHTML=`${Math.abs(mapCenter[0]).toFixed(4)}° ${mapCenter[0]<0?"W":"E"}&nbsp;&nbsp; ${Math.abs(mapCenter[1]).toFixed(4)}° ${mapCenter[1]<0?"S":"N"} <span>${areaBounds?"AREA CENTER":areaFocusBounds?"AREA FOCUS":"SEARCH POINT"}</span>`;
  const plottedIds=new Set((catalog.features||[]).slice(0,60).map((feature)=>feature.properties.fileID));
  if(selectedSceneId)plottedIds.add(selectedSceneId);
  displayed.forEach((feature)=>plottedIds.add(feature.properties.fileID));
  const plottedCount=plottedIds.size;
  $(".map-caption").textContent=gcovPairAnalysis?.status==="QA_HELD"?"Selected pair · QA held · no comparison pixels read":gcovPairAnalysis?.status==="MEASURED_DESCRIPTIVE_ONLY"?`NISAR ${gcovPairAnalysis.measurement.layer} descriptive comparison · QA PASS`:gcovPreview?`NISAR ${gcovPreview.measurement.layer} backscatter preview · product QA ${gcovPreview.source.provider_qa_status}`:`${plottedCount} ASF footprints shown${catalog.feature_count>plottedCount?` of ${catalog.feature_count}`:""}${pair?` · ${gap}-day metadata candidate`:""}`;
  $("#otherObservationLegend").hidden=(catalog.features?.length||0)<=2;
  $(".timeline-head #intervalLabel").textContent=pair ? `${ordered.length} ACQUISITIONS · ${candidateCount} METADATA ${candidateCount===1?"PAIR":"PAIRS"}` : `${ordered.length} ACQUISITIONS · ${catalog.query.data_maturity} DATA`;
  $(".timeline-note").textContent=catalog.source.potentially_truncated?`Catalog cap reached at ${catalog.source.result_limit} records across ${catalog.source.pages_retrieved} pages; narrow dates or area to reduce this incomplete result set.`:ordered.length>1?"Choose a metadata pair, then select acquisitions to inspect source details · gaps show elapsed time":"Select the acquisition to inspect its source details";
  $(".evidence-title .eyebrow").innerHTML=`${escapeHTML(review?.case_id || "ASF CATALOG")} <span>·</span> EVIDENCE`;
  $(".confidence-block .readiness-value").innerHTML=review?`1 <small>OF 4 GATES · QA HOLD</small>`:`0 <small>OF 4 GATES · CATALOG ONLY</small>`;
  document.querySelectorAll(".confidence-block .readiness-track i").forEach((item,index)=>item.style.background=review&&index===0?"var(--cyan)":"#293940");
  $(".confidence-block p").textContent=review?"Catalog pairing is complete. Product QA reports an identification failure; alignment and valid-pixel overlap remain unchecked.":pair?"Catalog pairing is complete. Product QA, pixel-grid alignment, and common valid coverage remain unreviewed.":"Catalog discovery is complete. No temporal pair passed ECHO's metadata screening; no change claim is available.";
  $(".finding-meta b").textContent=status.replaceAll("_"," ");
  if (!review) {
    $(".gate-count").textContent=pair?`${candidateCount} CANDIDATE${candidateCount===1?"":"S"} · 2 OPEN`:"NO PAIR · QA NOT REVIEWED";
    $(".gate-list").innerHTML=`<li><span class="gate-icon ${pair?'review':'open'}">${pair?'!':'○'}</span><span><b>Catalog pair screening</b><small>${pair?'Metadata match only; pixels not compared':'No distinct-orbit temporal pair found'}</small></span><span class="gate-state">${pair?'CANDIDATE':'OPEN'}</span></li><li><span class="gate-icon open">○</span><span><b>Product QA</b><small>Per-product checks have not been retrieved for this search</small></span><span class="gate-state">OPEN</span></li><li><span class="gate-icon open">○</span><span><b>Grid and interpretation</b><small>Registration and physical explanation not assessed</small></span><span class="gate-state">OPEN</span></li>`;
  }
  renderDetails(selectedSceneId);
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
    if(!["QA_HELD","MEASURED_DESCRIPTIVE_ONLY"].includes(record.status))throw new Error("GCOV pair response has an unsupported disposition");
    gcovPairAnalysis=record;
    if(record.status==="MEASURED_DESCRIPTIVE_ONLY")pairAnalysisDisplayScale=pairDisplayScale(record);
    renderDetails(selectedSceneId);drawMap();
    const count=record.status==="QA_HELD"?0:record.measurement.common_valid_mask.flat().filter(Boolean).length;
    showToast(record.status==="QA_HELD"?"Pair held: ASF provider QA did not pass. No measurement arrays were read.":"Rendered "+count.toLocaleString()+" common valid NISAR measurement pixels · descriptive only.");
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
    if(width>0&&height>0){areaBounds=areaPreview;areaFocusBounds=areaBounds;gcovPreview=null;selectedPreviewPixel=null;gcovPairAnalysis=null;selectedPairPixel=null;pairAnalysisDisplayScale=null;drawingArea=false;showToast("Area selected. Find observations to query ASF for intersecting footprints.");}
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
  const polygon=event.target.closest("polygon[data-scene-id]");
  if(polygon&&!gcovPreview&&(!gcovPairAnalysis||gcovPairAnalysis.status==="QA_HELD")){selectObservation(polygon.dataset.sceneId,{scrollTimeline:true});return;}
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
$("#loadGcovPreview").addEventListener("click",loadGcovPreview);
$("#runPairAnalysis").addEventListener("click",runGcovPairAnalysis);
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
