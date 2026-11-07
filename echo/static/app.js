const $ = (selector) => document.querySelector(selector);
const svg = $("#footprintMap");
let catalog;
let selectedScene = "before";
let zoom = 1;
let toastTimer;

const escapeHTML = (value) => String(value ?? "—").replace(/[&<>"']/g, (char) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[char]));
const sceneLabel = (scene) => scene === "before" ? "JAN 05 · BEFORE" : "JAN 17 · AFTER";

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
  const {features, query} = catalog;
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
    const css = index === 0 ? "footprint-after" : "footprint-before";
    return rings.map((ring) => `<polygon class="${css}" points="${ring.map(([lon,lat])=>`${x(lon)},${y(lat)}`).join(" ")}"/>`).join("");
  }).join("");
  const px=x(query.longitude), py=y(query.latitude);
  svg.innerHTML = `${grid.join("")}<g>${shapes}</g><line class="point-leader" x1="${px+10}" y1="${py-8}" x2="${px+75}" y2="${py-43}"/><text class="point-label" x="${px+80}" y="${py-46}">SEARCH POINT</text><circle class="search-ring" cx="${px}" cy="${py}" r="10"/><circle class="search-dot" cx="${px}" cy="${py}" r="3.5"/>`;
}

function renderDetails(scene) {
  const feature = catalog.features.find((item) => item.properties.startTime.startsWith(scene === "before" ? "2026-01-05" : "2026-01-17")) || catalog.features[0];
  const p = feature.properties;
  const bytes = Object.values(p.bytes || {}).find((file) => file.format === "HDF5")?.bytes;
  const size = bytes ? `${(bytes/1e9).toFixed(2)} GB` : "HDF5";
  const time = new Date(p.startTime).toISOString().replace("T"," ").replace(".000Z"," UTC");
  $("#sceneDetails").innerHTML = [
    ["ACQUISITION",time], ["MATURITY",catalog.query.data_maturity], ["PRODUCT","GCOV · L2"], ["POLARIZATION",(p.mainBandPolarization||[]).join(" / ")], ["ORBIT",`${p.flightDirection} · PATH ${p.pathNumber}`], ["FRAME",`${p.frameNumber} · ${p.frameCoverage||"UNKNOWN"}`], ["FILE SIZE",size], ["SCENE ID",p.fileID,true]
  ].map(([label,value,full])=>`<div class="${full?'full':''}"><dt>${escapeHTML(label)}</dt><dd title="${escapeHTML(value)}">${escapeHTML(value)}</dd></div>`).join("");
  $("#beforeSelect").classList.toggle("selected",scene==="before");
  $("#afterSelect").classList.toggle("selected",scene==="after");
  selectedScene=scene;
}

function showToast(message) {
  const node=$("#toast"); node.textContent=message; node.classList.add("show");
  clearTimeout(toastTimer); toastTimer=setTimeout(()=>node.classList.remove("show"),2600);
}

async function init() {
  try {
    const response=await fetch("/api/case",{cache:"no-store"});
    if(!response.ok) throw new Error("Catalog metadata could not be loaded");
    catalog=await response.json();
    if(!catalog.features?.length) throw new Error("The selected catalog contains no observations");
    const dates=catalog.features.map((f)=>Date.parse(f.properties.startTime)).sort((a,b)=>a-b);
    $("#intervalLabel").textContent=`${Math.round((dates.at(-1)-dates[0])/86400000)} DAY INTERVAL`;
    drawMap(); renderDetails("before");
  } catch(error) {
    $("#sceneDetails").innerHTML=`<div class="full"><dt>CATALOG</dt><dd>${escapeHTML(error.message)}</dd></div>`;
    showToast(error.message);
  }
}

$("#zoomIn").addEventListener("click",()=>{zoom=Math.min(zoom*1.35,5);if(catalog)drawMap()});
$("#zoomOut").addEventListener("click",()=>{zoom=Math.max(zoom/1.35,0.7);if(catalog)drawMap()});
$("#resetView").addEventListener("click",()=>{zoom=1;if(catalog)drawMap()});
$("#beforeSelect").addEventListener("click",()=>catalog&&renderDetails("before"));
$("#afterSelect").addEventListener("click",()=>catalog&&renderDetails("after"));
$("#recordToggle").addEventListener("click",()=>{if(!catalog)return;const feature=catalog.features.find((f)=>f.properties.startTime.startsWith(selectedScene==="before"?"2026-01-05":"2026-01-17"))||catalog.features[0];$("#recordJson").textContent=JSON.stringify(feature,null,2);$("#recordDialog").showModal()});
$("#challengeButton").addEventListener("click",()=>$("#challengeDialog").showModal());
$("#aboutButton").addEventListener("click",()=>$("#aboutDialog").showModal());
$("#sourcesNav").addEventListener("click",()=>showToast("Source records are available from the observation details panel."));
init();
