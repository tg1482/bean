"""HTML renderer for Bean visualizations.

Takes enriched data dict + D3.js source and produces a self-contained HTML file.
"""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path
from typing import Any

D3_URL = "https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js"


def download_d3(cache_dir: Path) -> str:
    """Download D3.js and cache locally."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    cached = cache_dir / "d3.v7.min.js"
    if cached.exists():
        return cached.read_text(encoding="utf-8")
    print(f"  Downloading {D3_URL} ...")
    resp = urllib.request.urlopen(D3_URL, timeout=30)
    text = resp.read().decode("utf-8")
    cached.write_text(text, encoding="utf-8")
    return text


def render_html(data: dict[str, Any], d3_js: str) -> str:
    """Render the full HTML page with inlined JS and data."""
    payload = json.dumps(data, ensure_ascii=True, separators=(",", ":"))

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Bean — Codebase Visualizer</title>
<style>
{CSS}
</style>
</head>
<body>
<div id="app">
  <header id="header">
    <div class="header-left">
      <span class="logo">&#9733; Bean</span>
      <nav class="view-tabs" id="viewTabs">
        <button class="tab active" data-view="radial">Radial</button>
        <button class="tab" data-view="data">Data</button>
        <button class="tab" data-view="trace">Trace</button>
        <button class="tab" data-view="quality">Quality</button>
      </nav>
    </div>
    <div class="header-right">
      <input type="text" id="searchInput" placeholder="Search modules, functions..." autocomplete="off"/>
      <div class="stats-badges" id="statsBadges"></div>
    </div>
  </header>
  <div id="mainLayout">
    <aside id="sidebar">
      <div class="sidebar-section" id="layerLegend"></div>
      <div class="sidebar-section" id="filterControls"></div>
      <div class="sidebar-section" id="inspector"></div>
    </aside>
    <main id="canvas-area">
      <canvas id="particleCanvas"></canvas>
      <svg id="mainSvg"></svg>
      <div id="uiOverlay">
        <div id="breadcrumbs"></div>
        <div id="tooltip" class="tooltip hidden"></div>
      </div>
      <div id="searchResults" class="search-results hidden"></div>
    </main>
  </div>
</div>
<script>
{d3_js}
</script>
<script>
const BEAN_DATA = {payload};
{APP_JS}
</script>
</body>
</html>"""


CSS = r"""
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#0a0e17;--bg2:#0f1523;--bg3:#151d2e;
  --text:#e2e8f0;--text2:#94a3b8;--text3:#64748b;
  --accent:#3b82f6;--border:rgba(148,163,184,0.12);
  --gold:#fbbf24;--panel-bg:rgba(15,21,35,0.92);
}
html,body{height:100%;overflow:hidden;background:var(--bg);color:var(--text);
  font-family:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;font-size:13px}
#app{display:flex;flex-direction:column;height:100vh}

/* Header */
#header{display:flex;align-items:center;justify-content:space-between;
  height:48px;padding:0 16px;background:var(--bg2);border-bottom:1px solid var(--border);
  flex-shrink:0;z-index:100}
.header-left{display:flex;align-items:center;gap:16px}
.header-right{display:flex;align-items:center;gap:12px}
.logo{font-size:18px;font-weight:700;color:var(--gold);letter-spacing:-0.5px}
.view-tabs{display:flex;gap:2px}
.tab{background:transparent;border:1px solid transparent;color:var(--text2);
  padding:6px 14px;border-radius:6px;cursor:pointer;font-size:12px;font-weight:500;
  transition:all 0.2s}
.tab:hover{color:var(--text);background:var(--bg3)}
.tab.active{color:var(--gold);background:var(--bg3);border-color:var(--gold)}
#searchInput{background:var(--bg3);border:1px solid var(--border);color:var(--text);
  padding:6px 12px;border-radius:6px;width:220px;font-size:12px;outline:none}
#searchInput:focus{border-color:var(--accent)}
.stats-badges{display:flex;gap:8px}
.badge{background:var(--bg3);border:1px solid var(--border);border-radius:12px;
  padding:2px 8px;font-size:11px;color:var(--text2)}
.badge strong{color:var(--text)}

/* Layout */
#mainLayout{display:flex;flex:1;overflow:hidden;position:relative}
#sidebar{width:260px;background:var(--bg2);border-right:1px solid var(--border);
  overflow-y:auto;flex-shrink:0;padding:12px;display:flex;flex-direction:column;gap:12px}
.sidebar-section{background:var(--bg3);border:1px solid var(--border);border-radius:8px;padding:10px}
.sidebar-section h3{font-size:11px;text-transform:uppercase;letter-spacing:0.05em;
  color:var(--text3);margin-bottom:8px;font-weight:600}

/* Legend */
.legend-item{display:flex;align-items:center;gap:8px;padding:3px 0;font-size:12px;cursor:pointer}
.legend-item:hover{color:var(--text)}
.legend-dot{width:10px;height:10px;border-radius:50%;flex-shrink:0}
.legend-label{color:var(--text2)}
.legend-count{margin-left:auto;color:var(--text3);font-size:11px}

/* Inspector */
.inspector-title{font-size:14px;font-weight:600;color:var(--text);margin-bottom:6px}
.inspector-row{display:flex;justify-content:space-between;padding:3px 0;font-size:12px;
  border-bottom:1px solid var(--border)}
.inspector-row .label{color:var(--text3)}
.inspector-row .value{color:var(--text);font-weight:500}

/* Canvas area */
#canvas-area{flex:1;position:relative;overflow:hidden;background:
  radial-gradient(ellipse at 30% 20%,rgba(59,130,246,0.06),transparent 60%),
  radial-gradient(ellipse at 70% 80%,rgba(139,92,246,0.04),transparent 50%),
  var(--bg)}
#particleCanvas{position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:0}
#mainSvg{position:absolute;top:0;left:0;width:100%;height:100%;z-index:1}
#uiOverlay{position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:2}
#breadcrumbs{position:absolute;top:12px;left:12px;pointer-events:auto}
.breadcrumb{display:inline-block;background:var(--panel-bg);border:1px solid var(--border);
  border-radius:4px;padding:3px 8px;font-size:11px;color:var(--text2);cursor:pointer;margin-right:4px}
.breadcrumb:hover{color:var(--text);border-color:var(--accent)}
.breadcrumb.current{color:var(--gold);border-color:var(--gold)}

/* Tooltip */
.tooltip{position:absolute;pointer-events:none;background:var(--panel-bg);
  border:1px solid var(--border);border-radius:8px;padding:10px 14px;
  font-size:12px;max-width:320px;backdrop-filter:blur(8px);
  box-shadow:0 8px 32px rgba(0,0,0,0.4);z-index:200}
.tooltip.hidden{display:none}
.tooltip .tt-title{font-weight:600;color:var(--text);margin-bottom:4px;font-size:13px}
.tooltip .tt-row{color:var(--text2);line-height:1.5}

/* Search */
.search-results{position:absolute;top:8px;right:8px;width:300px;max-height:400px;
  overflow-y:auto;background:var(--panel-bg);border:1px solid var(--border);
  border-radius:8px;backdrop-filter:blur(8px);z-index:150;pointer-events:auto}
.search-results.hidden{display:none}
.search-item{padding:8px 12px;cursor:pointer;border-bottom:1px solid var(--border);font-size:12px}
.search-item:hover{background:var(--bg3)}
.search-item .si-name{color:var(--text);font-weight:500}
.search-item .si-meta{color:var(--text3);font-size:11px}

/* Filter controls */
.filter-group{margin-bottom:8px}
.filter-group label{font-size:11px;color:var(--text3);display:block;margin-bottom:3px}
.filter-toggle{display:flex;align-items:center;gap:6px;padding:3px 0;font-size:12px;
  color:var(--text2);cursor:pointer}
.filter-toggle input[type=checkbox]{accent-color:var(--accent)}

/* Quality dashboard */
.quality-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;padding:12px}
.gauge-card{background:var(--bg3);border:1px solid var(--border);border-radius:8px;
  padding:16px;text-align:center}
.gauge-card .gauge-value{font-size:28px;font-weight:700;margin:8px 0}
.gauge-card .gauge-label{font-size:11px;color:var(--text3);text-transform:uppercase;letter-spacing:0.05em}
.gauge-card.full-width{grid-column:1/-1}
.bar-row{display:flex;align-items:center;gap:8px;padding:4px 0;font-size:12px}
.bar-label{width:80px;text-align:right;color:var(--text2);font-size:11px;flex-shrink:0}
.bar-track{flex:1;height:16px;background:var(--bg);border-radius:3px;overflow:hidden;position:relative}
.bar-fill{height:100%;border-radius:3px;transition:width 0.6s ease}
.bar-val{width:40px;font-size:11px;color:var(--text3);text-align:right;flex-shrink:0}

/* Heatmap */
.heatmap-grid{display:grid;gap:2px;margin-top:8px}
.heatmap-cell{border-radius:3px;display:flex;align-items:center;justify-content:center;
  font-size:10px;font-weight:600;min-height:28px}
.heatmap-label{font-size:10px;color:var(--text3);text-align:center;padding:2px}

/* Entrypoint explorer */
.ep-list{max-height:calc(100vh - 200px);overflow-y:auto}
.ep-group-header{font-size:11px;text-transform:uppercase;color:var(--text3);
  padding:8px 0 4px;letter-spacing:0.05em;font-weight:600;
  border-bottom:1px solid var(--border);margin-top:8px}
.ep-item{padding:6px 8px;cursor:pointer;border-radius:4px;font-size:12px;color:var(--text2)}
.ep-item:hover{background:var(--bg3);color:var(--text)}
.ep-item.active{background:var(--accent);color:white}
.ep-controls{display:flex;gap:6px;padding:8px 0;align-items:center}
.ep-btn{background:var(--bg3);border:1px solid var(--border);color:var(--text2);
  padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px}
.ep-btn:hover{color:var(--text);border-color:var(--accent)}
.ep-btn.active{background:var(--accent);color:white;border-color:var(--accent)}
.speed-label{font-size:11px;color:var(--text3)}

/* Animations */
@keyframes pulseBeacon{
  0%{r:0;opacity:0.8}
  100%{r:24;opacity:0}
}
@keyframes nodePopIn{
  0%{transform:scale(0);opacity:0}
  60%{transform:scale(1.15);opacity:1}
  100%{transform:scale(1);opacity:1}
}
@keyframes marchingAnts{
  to{stroke-dashoffset:-16}
}
.marching-ants{animation:marchingAnts 0.6s linear infinite}
.node-pop{animation:nodePopIn 0.5s ease-out forwards}

/* SVG filter styles via defs */
.glow-node{filter:url(#glowFilter)}
.hotspot-node{filter:url(#hotspotGlow)}

/* Scrollbar */
::-webkit-scrollbar{width:6px}
::-webkit-scrollbar-track{background:var(--bg2)}
::-webkit-scrollbar-thumb{background:var(--bg3);border-radius:3px}
::-webkit-scrollbar-thumb:hover{background:rgba(148,163,184,0.3)}

/* Data flow view */
.type-card{cursor:pointer;transition:filter 0.2s}
.type-card:hover{filter:brightness(1.3)}
.type-field-row{font-size:10px;fill:var(--text2)}
.type-field-type{fill:var(--text3);font-style:italic}
.type-kind-badge{font-size:8px;text-transform:uppercase;letter-spacing:0.05em}
"""


APP_JS = r"""
(function() {
'use strict';

const D = BEAN_DATA;

// Dynamically discover layers from the data
const _layerSet = new Set();
D.galaxyNodes.forEach(n => _layerSet.add(n.layer));
const LAYERS = [..._layerSet].sort();

// Generate distinct colors for layers using a broad palette
const _PALETTE = [
  '#8b5cf6','#f77f00','#3b82f6','#10b981','#ef4444',
  '#e879f9','#06b6d4','#84cc16','#f43f5e','#a78bfa',
  '#fb923c','#22d3ee','#facc15','#4ade80','#f472b6',
];
const LAYER_COLORS = {};
LAYERS.forEach((l, i) => { LAYER_COLORS[l] = _PALETTE[i % _PALETTE.length]; });
// Keep a fallback for "other"
LAYER_COLORS.other = '#6b7280';

const LAYER_LABELS = {};
LAYERS.forEach(l => { LAYER_LABELS[l] = l.charAt(0).toUpperCase() + l.slice(1); });

/* ── State ── */
let currentView = 'radial';
let particleCtx = null;
let particles = [];
let animFrame = null;
let searchOpen = false;

/* ── Helpers ── */
function layerColor(l) { return LAYER_COLORS[l] || LAYER_COLORS.other; }
function clamp(v,lo,hi) { return Math.max(lo,Math.min(hi,v)); }
function shortLabel(s) { const p=s.split('.'); return p.length>2 ? p.slice(-2).join('.') : s; }

/* ── Init ── */
function init() {
  renderStatsBadges();
  setupTabs();
  setupSearch();
  setupParticles();
  switchView('radial');
  // Load-in reveal
  document.getElementById('app').style.opacity = '0';
  requestAnimationFrame(() => {
    document.getElementById('app').style.transition = 'opacity 1.2s ease';
    document.getElementById('app').style.opacity = '1';
  });
}

function renderStatsBadges() {
  const m = D.quality.meta || {};
  const el = document.getElementById('statsBadges');
  el.innerHTML = `
    <span class="badge"><strong>${m.module_count||0}</strong> modules</span>
    <span class="badge"><strong>${m.function_count||0}</strong> functions</span>
    <span class="badge"><strong>${m.class_count||0}</strong> classes</span>
    <span class="badge"><strong>${m.total_lines||0}</strong> lines</span>
  `;
}

/* ── Tabs ── */
function setupTabs() {
  document.querySelectorAll('.tab').forEach(t => {
    t.addEventListener('click', () => switchView(t.dataset.view));
  });
}

function switchView(view) {
  currentView = view;
  document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.dataset.view === view));
  // Reset
  const svg = d3.select('#mainSvg');
  svg.selectAll('*').remove();
  document.getElementById('breadcrumbs').innerHTML = '';
  document.getElementById('tooltip').classList.add('hidden');
  document.getElementById('searchResults').classList.add('hidden');
  cancelAnimationFrame(animFrame);

  // Add SVG defs
  addSvgDefs(svg);

  switch(view) {
    case 'radial': renderRadial(); break;
    case 'data': renderDataFlow(); break;
    case 'trace': renderTrace(); break;
    case 'quality': renderQuality(); break;
  }
}

function addSvgDefs(svg) {
  const defs = svg.append('defs');
  // Glow filter
  const glow = defs.append('filter').attr('id','glowFilter').attr('x','-50%').attr('y','-50%').attr('width','200%').attr('height','200%');
  glow.append('feGaussianBlur').attr('stdDeviation','3').attr('result','blur');
  const merge = glow.append('feMerge');
  merge.append('feMergeNode').attr('in','blur');
  merge.append('feMergeNode').attr('in','SourceGraphic');
  // Hotspot glow
  const hg = defs.append('filter').attr('id','hotspotGlow').attr('x','-80%').attr('y','-80%').attr('width','260%').attr('height','260%');
  hg.append('feGaussianBlur').attr('stdDeviation','5').attr('result','blur');
  const hm = hg.append('feMerge');
  hm.append('feMergeNode').attr('in','blur');
  hm.append('feMergeNode').attr('in','SourceGraphic');
  // Gradient for edges
  const edgeGrad = defs.append('linearGradient').attr('id','edgeGrad').attr('gradientUnits','userSpaceOnUse');
  edgeGrad.append('stop').attr('offset','0%').attr('stop-color','rgba(148,163,184,0.3)');
  edgeGrad.append('stop').attr('offset','100%').attr('stop-color','rgba(148,163,184,0.1)');
  // Radial gradients for each layer
  LAYERS.forEach(l => {
    const rg = defs.append('radialGradient').attr('id','grad-'+l).attr('cx','35%').attr('cy','35%');
    rg.append('stop').attr('offset','0%').attr('stop-color',d3.color(layerColor(l)).brighter(1));
    rg.append('stop').attr('offset','100%').attr('stop-color',layerColor(l));
  });
}

/* ── Particles ── */
function setupParticles() {
  const canvas = document.getElementById('particleCanvas');
  const rect = canvas.parentElement.getBoundingClientRect();
  canvas.width = rect.width;
  canvas.height = rect.height;
  particleCtx = canvas.getContext('2d');
  particles = [];
  for (let i = 0; i < 150; i++) {
    particles.push({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      r: Math.random() * 1.5 + 0.3,
      vx: (Math.random() - 0.5) * 0.15,
      vy: (Math.random() - 0.5) * 0.1,
      alpha: Math.random() * 0.4 + 0.1,
    });
  }
  animateParticles();
  window.addEventListener('resize', () => {
    const r2 = canvas.parentElement.getBoundingClientRect();
    canvas.width = r2.width;
    canvas.height = r2.height;
  });
}

function animateParticles() {
  if (!particleCtx) return;
  const c = particleCtx;
  const w = c.canvas.width, h = c.canvas.height;
  c.clearRect(0,0,w,h);
  for (const p of particles) {
    p.x += p.vx; p.y += p.vy;
    if (p.x < 0) p.x = w;
    if (p.x > w) p.x = 0;
    if (p.y < 0) p.y = h;
    if (p.y > h) p.y = 0;
    c.beginPath();
    c.arc(p.x, p.y, p.r, 0, Math.PI*2);
    c.fillStyle = `rgba(148,163,184,${p.alpha})`;
    c.fill();
  }
  animFrame = requestAnimationFrame(animateParticles);
}

/* ── Search ── */
function setupSearch() {
  const input = document.getElementById('searchInput');
  const results = document.getElementById('searchResults');
  input.addEventListener('input', () => {
    const q = input.value.trim().toLowerCase();
    if (q.length < 2) { results.classList.add('hidden'); return; }
    const matches = [];
    D.galaxyNodes.forEach(n => {
      if (n.label.toLowerCase().includes(q)) matches.push({type:'module',label:n.label,layer:n.layer,id:n.id});
    });
    D.epNodes.forEach(n => {
      if ((n.label||n.id).toLowerCase().includes(q)) matches.push({type:'function',label:n.label||n.id,layer:n.layer,id:n.id});
    });
    if (!matches.length) { results.classList.add('hidden'); return; }
    results.classList.remove('hidden');
    results.innerHTML = matches.slice(0,20).map(m =>
      `<div class="search-item" data-id="${m.id}" data-type="${m.type}">
        <div class="si-name">${m.label}</div>
        <div class="si-meta">${m.type} · ${m.layer}</div>
      </div>`
    ).join('');
    results.querySelectorAll('.search-item').forEach(el => {
      el.addEventListener('click', () => {
        const id = el.dataset.id;
        results.classList.add('hidden');
        input.value = '';
      });
    });
  });
  input.addEventListener('blur', () => setTimeout(() => results.classList.add('hidden'), 200));
}

/* ── Sidebar ── */
function renderLayerLegend() {
  const el = document.getElementById('layerLegend');
  const counts = {};
  D.galaxyNodes.forEach(n => { counts[n.layer] = (counts[n.layer]||0)+1; });
  el.innerHTML = `<h3>Layers</h3>` + LAYERS.map(l =>
    `<div class="legend-item" data-layer="${l}">
      <div class="legend-dot" style="background:${layerColor(l)}"></div>
      <span class="legend-label">${LAYER_LABELS[l]||l}</span>
      <span class="legend-count">${counts[l]||0}</span>
    </div>`
  ).join('');
}

/* ══════════════════════════════════════════════════════════
   VIEW: Radial Architecture Graph
   ══════════════════════════════════════════════════════════ */
function renderRadial() {
  const sidebar = document.getElementById('sidebar');
  const filters = sidebar.querySelector('#filterControls');
  const inspector = sidebar.querySelector('#inspector');
  const tooltip = document.getElementById('tooltip');

  renderLayerLegend();

  filters.innerHTML = `
    <h3>Display</h3>
    <div class="filter-toggle"><input type="checkbox" id="radLabels" checked/><label for="radLabels">Labels</label></div>
    <div class="filter-toggle"><input type="checkbox" id="radEdges" checked/><label for="radEdges">Dependencies</label></div>
    <div class="filter-toggle"><input type="checkbox" id="radRings" checked/><label for="radRings">Depth rings</label></div>
    <h3 style="margin-top:8px">Layers</h3>
    ${LAYERS.map(l => `<div class="filter-toggle"><input type="checkbox" class="layer-filter" data-layer="${l}" checked/><label>${LAYER_LABELS[l]||l}</label></div>`).join('')}
  `;

  const nodes = D.galaxyNodes;
  const edges = D.galaxyEdges;

  if (!nodes.length) {
    inspector.innerHTML = '<h3>Radial</h3><div style="color:var(--text3);font-size:12px">No modules found</div>';
    return;
  }

  const epCount = nodes.filter(n => n.isEntryPoint).length;
  inspector.innerHTML = `
    <h3>Architecture</h3>
    <div class="inspector-row"><span class="label">Modules</span><span class="value">${nodes.length}</span></div>
    <div class="inspector-row"><span class="label">Dependencies</span><span class="value">${edges.length}</span></div>
    <div class="inspector-row"><span class="label">Entry points</span><span class="value">${epCount}</span></div>
    <div class="inspector-row"><span class="label">Layers</span><span class="value">${LAYERS.length}</span></div>
    <div style="margin-top:6px;font-size:11px;color:var(--text3)">Inner ring = core modules. Outer ring = entry points. Hover for details, click to inspect.</div>
  `;

  const svg = d3.select('#mainSvg');
  const width = svg.node().clientWidth;
  const height = svg.node().clientHeight;
  const g = svg.append('g').attr('class','radial-root');

  const zoomBehavior = d3.zoom().scaleExtent([0.1, 5]).on('zoom', e => g.attr('transform', e.transform));
  svg.call(zoomBehavior);

  const cx = width / 2;
  const cy = height / 2;

  /* ── Build import graph ── */
  const nodeById = new Map();
  nodes.forEach(n => nodeById.set(n.id, n));
  const nodeIdSet = new Set(nodes.map(n => n.id));

  const importsOf = new Map();
  edges.forEach(e => {
    if (!importsOf.has(e.source)) importsOf.set(e.source, new Set());
    importsOf.get(e.source).add(e.target);
  });

  /* ── Compute dependency depth ──
     depth(m) = 0 if m has no internal imports (core)
     depth(m) = max(depth(dep)) + 1 otherwise
     Inner ring (0) = core, outer = entry points */
  const depthOf = new Map();
  const inProgress = new Set();

  function calcDepth(id) {
    if (depthOf.has(id)) return depthOf.get(id);
    if (inProgress.has(id)) return 0;
    inProgress.add(id);
    const deps = importsOf.get(id) || new Set();
    let maxDep = -1;
    for (const dep of deps) {
      if (nodeIdSet.has(dep)) maxDep = Math.max(maxDep, calcDepth(dep));
    }
    const d = maxDep + 1;
    depthOf.set(id, d);
    inProgress.delete(id);
    return d;
  }
  nodes.forEach(n => calcDepth(n.id));

  // Force entry-point modules to the outermost ring
  const naturalMax = Math.max(0, ...depthOf.values());
  const epRing = naturalMax + 1;
  nodes.forEach(n => { if (n.isEntryPoint) depthOf.set(n.id, epRing); });

  const maxDepth = Math.max(0, ...depthOf.values());
  const displayMax = Math.min(maxDepth, 12);

  /* ── Sector layout: divide circle into layer wedges ── */
  const layerBuckets = {};
  LAYERS.forEach(l => { layerBuckets[l] = []; });
  nodes.forEach(n => {
    const l = n.layer || 'other';
    if (!layerBuckets[l]) layerBuckets[l] = [];
    layerBuckets[l].push(n);
  });
  const activeLayers = LAYERS.filter(l => (layerBuckets[l]||[]).length > 0);

  const sectorGap = activeLayers.length > 1 ? 0.06 : 0;
  const totalGap = sectorGap * activeLayers.length;
  const availAngle = 2 * Math.PI - totalGap;
  const totalN = nodes.length;

  const sectors = {};
  let curAngle = -Math.PI / 2;
  activeLayers.forEach(l => {
    const cnt = layerBuckets[l].length;
    const sweep = (cnt / totalN) * availAngle;
    sectors[l] = { start: curAngle, end: curAngle + sweep };
    curAngle += sweep + sectorGap;
  });

  /* ── Position each node on its ring within its sector ── */
  const minR = Math.max(40, Math.min(cx, cy) * 0.1);
  const maxR = Math.min(cx, cy) - 60;
  const ringStep = displayMax > 0 ? (maxR - minR) / displayMax : 0;
  const positions = new Map();

  activeLayers.forEach(layer => {
    const sec = sectors[layer];
    const mods = layerBuckets[layer];
    const byDepth = {};
    mods.forEach(n => {
      const d = Math.min(depthOf.get(n.id)||0, displayMax);
      (byDepth[d] = byDepth[d] || []).push(n);
    });

    Object.entries(byDepth).forEach(([dStr, arr]) => {
      const d = parseInt(dStr);
      const r = minR + d * ringStep;
      arr.sort((a, b) => a.label.localeCompare(b.label));
      const sweep = sec.end - sec.start;
      arr.forEach((n, i) => {
        const t = arr.length > 1 ? (i + 0.5) / arr.length : 0.5;
        const a = sec.start + t * sweep;
        positions.set(n.id, { x: cx + r * Math.cos(a), y: cy + r * Math.sin(a), angle: a, r, depth: d });
      });
    });
  });

  /* ── Drawing layers ── */
  const ringsG = g.append('g').attr('class','rad-rings');
  const sectorG = g.append('g').attr('class','rad-sectors');
  const edgeG = g.append('g').attr('class','rad-edges');
  const nodeG = g.append('g').attr('class','rad-nodes');
  const labelG = g.append('g').attr('class','rad-labels');

  /* Concentric ring guides */
  for (let d = 0; d <= displayMax; d++) {
    const r = minR + d * ringStep;
    ringsG.append('circle')
      .attr('cx', cx).attr('cy', cy).attr('r', r)
      .attr('fill','none')
      .attr('stroke','var(--border)')
      .attr('stroke-width', d === 0 || d === displayMax ? 0.7 : 0.3)
      .attr('stroke-dasharray','4 8')
      .attr('opacity', 0);
  }

  /* Center label */
  ringsG.append('text')
    .attr('x', cx).attr('y', cy + 4)
    .attr('text-anchor','middle')
    .attr('font-size', 10).attr('font-weight',700)
    .attr('fill','var(--text3)')
    .attr('letter-spacing','0.1em')
    .attr('opacity', 0)
    .text('CORE');

  /* Depth ring annotations (right side) */
  for (let d = 0; d <= displayMax; d++) {
    const r = minR + d * ringStep;
    const label = d === 0 ? 'core' : d === displayMax ? 'entry' : '';
    if (!label) continue;
    ringsG.append('text')
      .attr('x', cx + r).attr('y', cy - 8)
      .attr('text-anchor','middle')
      .attr('font-size', 8).attr('fill','var(--text3)')
      .attr('opacity', 0)
      .text(label);
  }

  /* Sector backgrounds & labels */
  activeLayers.forEach(layer => {
    const sec = sectors[layer];
    const mid = (sec.start + sec.end) / 2;

    // Background arc (d3.arc uses clockwise from 12 o'clock)
    const arc = d3.arc()
      .innerRadius(minR - 8)
      .outerRadius(maxR + 8)
      .startAngle(sec.start + Math.PI / 2)
      .endAngle(sec.end + Math.PI / 2);

    sectorG.append('path')
      .attr('d', arc())
      .attr('transform', `translate(${cx},${cy})`)
      .attr('fill', layerColor(layer))
      .attr('fill-opacity', 0.025)
      .attr('stroke','none');

    // Divider line at sector start
    if (activeLayers.length > 1) {
      sectorG.append('line')
        .attr('x1', cx + (minR - 12) * Math.cos(sec.start))
        .attr('y1', cy + (minR - 12) * Math.sin(sec.start))
        .attr('x2', cx + (maxR + 12) * Math.cos(sec.start))
        .attr('y2', cy + (maxR + 12) * Math.sin(sec.start))
        .attr('stroke', layerColor(layer))
        .attr('stroke-width', 0.4)
        .attr('stroke-opacity', 0.25);
    }

    // Sector label at outer edge
    const lR = maxR + 32;
    const lx = cx + lR * Math.cos(mid);
    const ly = cy + lR * Math.sin(mid);
    sectorG.append('text')
      .attr('x', lx).attr('y', ly + 3)
      .attr('text-anchor','middle')
      .attr('dominant-baseline','middle')
      .attr('font-size', 11).attr('font-weight',600)
      .attr('fill', layerColor(layer))
      .attr('opacity', 0.8)
      .text(LAYER_LABELS[layer] || layer);
  });

  /* ── Edges (bundled toward center) ── */
  edges.forEach(e => {
    const sp = positions.get(e.source);
    const tp = positions.get(e.target);
    if (!sp || !tp) return;

    const bundle = 0.55;
    const mx = (sp.x + tp.x) / 2;
    const my = (sp.y + tp.y) / 2;
    const qx = mx + (cx - mx) * bundle;
    const qy = my + (cy - my) * bundle;

    edgeG.append('path')
      .attr('d', `M${sp.x},${sp.y} Q${qx},${qy} ${tp.x},${tp.y}`)
      .attr('fill','none')
      .attr('stroke','rgba(148,163,184,0.08)')
      .attr('stroke-width', clamp(0.4 + (e.count||1) * 0.25, 0.4, 3))
      .attr('data-source', e.source)
      .attr('data-target', e.target)
      .attr('opacity', 0);
  });

  /* ── Nodes ── */
  nodes.forEach(n => {
    const pos = positions.get(n.id);
    if (!pos) return;
    const sz = clamp(2.5 + Math.sqrt(n.symbolCount||1) * 1.8, 3, 14);

    const ng = nodeG.append('g')
      .attr('transform', `translate(${pos.x},${pos.y})`)
      .attr('class','rad-node')
      .attr('data-id', n.id)
      .attr('data-layer', n.layer)
      .attr('data-depth', pos.depth)
      .style('cursor','pointer')
      .attr('opacity', 0);

    // Ambient glow
    ng.append('circle').attr('r', sz + 3)
      .attr('fill', layerColor(n.layer)).attr('fill-opacity', 0.08);

    // Main dot
    ng.append('circle').attr('r', sz)
      .attr('fill', `url(#grad-${n.layer})`)
      .attr('stroke', d3.color(layerColor(n.layer)).brighter(0.5))
      .attr('stroke-width', n.isEntryPoint ? 1.5 : 0.5);

    // Entry point ring
    if (n.isEntryPoint) {
      ng.append('circle').attr('r', sz + 5)
        .attr('fill','none')
        .attr('stroke', layerColor(n.layer))
        .attr('stroke-width', 0.7)
        .attr('stroke-dasharray','3 3')
        .attr('opacity', 0.5);
    }

    // Hotspot ring
    if (n.isHotspot) {
      ng.append('circle').attr('r', sz + 2)
        .attr('fill','none')
        .attr('stroke','#ef4444')
        .attr('stroke-width', 0.5)
        .attr('opacity', 0.5);
    }
  });

  /* ── Labels ── */
  nodes.forEach(n => {
    const pos = positions.get(n.id);
    if (!pos) return;
    const sz = clamp(2.5 + Math.sqrt(n.symbolCount||1) * 1.8, 3, 14);
    const dx = pos.x - cx;
    const dy = pos.y - cy;
    const dist = Math.sqrt(dx*dx + dy*dy) || 1;
    const nx = dx / dist;
    const ny = dy / dist;
    const off = sz + 5;
    const lx = pos.x + nx * off;
    const ly = pos.y + ny * off;
    let anchor = 'start';
    if (nx < -0.3) anchor = 'end';
    else if (Math.abs(nx) <= 0.3) anchor = 'middle';

    labelG.append('text')
      .attr('x', lx).attr('y', ly + 3)
      .attr('text-anchor', anchor)
      .attr('font-size', 9)
      .attr('fill','var(--text3)')
      .attr('paint-order','stroke')
      .attr('stroke','var(--bg)')
      .attr('stroke-width', 2)
      .attr('stroke-linejoin','round')
      .attr('pointer-events','none')
      .attr('data-id', n.id)
      .attr('data-depth', pos.depth)
      .attr('opacity', 0)
      .text(shortLabel(n.label));
  });

  /* ── Interactions ── */
  nodeG.selectAll('.rad-node')
    .on('mouseenter', function(e) {
      const id = d3.select(this).attr('data-id');
      const n = nodeById.get(id);
      if (!n) return;
      const pos = positions.get(id);

      // Find connected modules
      const connected = new Set([id]);
      edges.forEach(ed => {
        if (ed.source === id) connected.add(ed.target);
        if (ed.target === id) connected.add(ed.source);
      });

      // Dim non-connected
      nodeG.selectAll('.rad-node')
        .transition().duration(120)
        .attr('opacity', function() { return connected.has(d3.select(this).attr('data-id')) ? 1 : 0.1; });

      labelG.selectAll('text')
        .transition().duration(120)
        .attr('opacity', function() { return connected.has(d3.select(this).attr('data-id')) ? 1 : 0.05; });

      // Highlight connected edges
      edgeG.selectAll('path')
        .transition().duration(120)
        .attr('stroke', function() {
          const s = d3.select(this).attr('data-source');
          const t = d3.select(this).attr('data-target');
          return (s === id || t === id) ? layerColor(n.layer) : 'rgba(148,163,184,0.04)';
        })
        .attr('stroke-width', function() {
          const s = d3.select(this).attr('data-source');
          const t = d3.select(this).attr('data-target');
          return (s === id || t === id) ? 2.2 : 0.4;
        });

      // Tooltip
      tooltip.classList.remove('hidden');
      tooltip.innerHTML = `
        <div class="tt-title" style="color:${layerColor(n.layer)}">${n.label}</div>
        <div class="tt-row">Layer: ${LAYER_LABELS[n.layer]||n.layer} · Depth: ${pos?.depth??'?'}</div>
        <div class="tt-row">${n.nFunctions||0} functions · ${n.nClasses||0} classes · Complexity: ${n.complexity}</div>
        ${n.isEntryPoint ? '<div class="tt-row" style="color:var(--gold)">★ Entry point module</div>' : ''}
        ${n.isHotspot ? '<div class="tt-row" style="color:#ef4444">● Complexity hotspot</div>' : ''}
      `;
      tooltip.style.left = (e.clientX + 16) + 'px';
      tooltip.style.top = (e.clientY - 10) + 'px';
    })
    .on('mousemove', e => {
      tooltip.style.left = (e.clientX + 16) + 'px';
      tooltip.style.top = (e.clientY - 10) + 'px';
    })
    .on('mouseleave', function() {
      tooltip.classList.add('hidden');
      nodeG.selectAll('.rad-node').transition().duration(200).attr('opacity', 1);
      labelG.selectAll('text').transition().duration(200).attr('opacity', 1);
      edgeG.selectAll('path').transition().duration(200)
        .attr('stroke','rgba(148,163,184,0.08)')
        .attr('stroke-width', function() {
          const s = d3.select(this).attr('data-source');
          const t = d3.select(this).attr('data-target');
          const ed = edges.find(e => e.source === s && e.target === t);
          return clamp(0.4 + ((ed?.count)||1) * 0.25, 0.4, 3);
        });
    })
    .on('click', function(e) {
      const id = d3.select(this).attr('data-id');
      const n = nodeById.get(id);
      if (!n) return;
      const pos = positions.get(id);
      const inDeps = edges.filter(ed => ed.target === id);
      const outDeps = edges.filter(ed => ed.source === id);
      inspector.innerHTML = `
        <h3>Module</h3>
        <div class="inspector-title" style="color:${layerColor(n.layer)}">${n.label}</div>
        <div class="inspector-row"><span class="label">Layer</span><span class="value">${LAYER_LABELS[n.layer]||n.layer}</span></div>
        <div class="inspector-row"><span class="label">Depth</span><span class="value">${pos?.depth??'?'}</span></div>
        <div class="inspector-row"><span class="label">Functions</span><span class="value">${n.nFunctions||0}</span></div>
        <div class="inspector-row"><span class="label">Classes</span><span class="value">${n.nClasses||0}</span></div>
        <div class="inspector-row"><span class="label">Complexity</span><span class="value">${n.complexity||0}</span></div>
        ${n.isEntryPoint ? '<div class="inspector-row"><span class="label">Entry point</span><span class="value" style="color:var(--gold)">★</span></div>' : ''}
        ${outDeps.length ? `<div style="margin-top:6px;font-size:11px;color:var(--text3)">Depends on (${outDeps.length}):</div>` +
          outDeps.slice(0,10).map(ed => { const t = nodeById.get(ed.target); return `<div class="inspector-row"><span class="label" style="font-size:10px;color:${layerColor(t?.layer||'other')}">${t?shortLabel(t.label):ed.target}</span><span class="value" style="font-size:9px">${ed.count}</span></div>`; }).join('') : ''}
        ${inDeps.length ? `<div style="margin-top:6px;font-size:11px;color:var(--text3)">Imported by (${inDeps.length}):</div>` +
          inDeps.slice(0,10).map(ed => { const s = nodeById.get(ed.source); return `<div class="inspector-row"><span class="label" style="font-size:10px;color:${layerColor(s?.layer||'other')}">${s?shortLabel(s.label):ed.source}</span><span class="value" style="font-size:9px">${ed.count}</span></div>`; }).join('') : ''}
      `;
    });

  /* ── Animated reveal: center outward ── */
  const revealMs = 70;

  // Rings
  ringsG.selectAll('circle').each(function(d, i) {
    d3.select(this).transition().delay(i * revealMs).duration(400).attr('opacity', 1);
  });
  ringsG.selectAll('text').transition().delay(100).duration(500).attr('opacity', 0.5);

  // Nodes by depth
  for (let d = 0; d <= displayMax; d++) {
    const delay = d * revealMs + 80;
    nodeG.selectAll(`.rad-node[data-depth="${d}"]`)
      .transition().delay(delay).duration(300).ease(d3.easeBackOut)
      .attr('opacity', 1);
    labelG.selectAll(`text[data-depth="${d}"]`)
      .transition().delay(delay + 50).duration(250)
      .attr('opacity', 1);
  }

  // Edges last
  edgeG.selectAll('path')
    .transition().delay(displayMax * revealMs + 200).duration(500)
    .attr('opacity', 1);

  /* ── Auto-fit ── */
  const pad = 80;
  const allPos = [...positions.values()];
  if (allPos.length) {
    const xs = allPos.map(p => p.x);
    const ys = allPos.map(p => p.y);
    const bx = Math.min(...xs) - pad, bX = Math.max(...xs) + pad;
    const by = Math.min(...ys) - pad, bY = Math.max(...ys) + pad;
    const bw = bX - bx, bh = bY - by;
    const s = Math.min(width / bw, height / bh, 1.3);
    const tx = (width - bw * s) / 2 - bx * s;
    const ty = (height - bh * s) / 2 - by * s;
    svg.call(zoomBehavior.transform, d3.zoomIdentity.translate(tx, ty).scale(s));
  }

  /* ── Filter listeners ── */
  document.getElementById('radLabels')?.addEventListener('change', function() {
    labelG.style('display', this.checked ? null : 'none');
  });
  document.getElementById('radEdges')?.addEventListener('change', function() {
    edgeG.style('display', this.checked ? null : 'none');
  });
  document.getElementById('radRings')?.addEventListener('change', function() {
    ringsG.style('display', this.checked ? null : 'none');
  });
  filters.querySelectorAll('.layer-filter').forEach(cb => {
    cb.addEventListener('change', () => {
      const hidden = new Set();
      filters.querySelectorAll('.layer-filter').forEach(el => {
        if (!el.checked) hidden.add(el.dataset.layer);
      });
      nodeG.selectAll('.rad-node').style('display', function() {
        return hidden.has(d3.select(this).attr('data-layer')) ? 'none' : null;
      });
      labelG.selectAll('text').style('display', function() {
        const id = d3.select(this).attr('data-id');
        const n = nodeById.get(id);
        return (n && hidden.has(n.layer)) ? 'none' : null;
      });
      edgeG.selectAll('path').style('display', function() {
        const s = nodeById.get(d3.select(this).attr('data-source'));
        const t = nodeById.get(d3.select(this).attr('data-target'));
        return (s && hidden.has(s.layer)) || (t && hidden.has(t.layer)) ? 'none' : null;
      });
    });
  });
}

/* ══════════════════════════════════════════════════════════
   VIEW 4: Entrypoint Explorer — Linear left-to-right trace
   ══════════════════════════════════════════════════════════ */
function renderTrace() {
  const sidebar = document.getElementById('sidebar');
  const legend = sidebar.querySelector('#layerLegend');
  const filters = sidebar.querySelector('#filterControls');
  const inspector = sidebar.querySelector('#inspector');

  // Group entrypoints by kind
  const epByKind = {};
  D.entrypoints.forEach(ep => {
    const k = ep.kind || 'other';
    (epByKind[k] = epByKind[k] || []).push(ep);
  });

  legend.innerHTML = '<h3>Entry Points</h3>';
  filters.innerHTML = `
    <div class="ep-controls">
      <button class="ep-btn" id="epPlay">Play</button>
      <button class="ep-btn" id="epPause">Pause</button>
      <button class="ep-btn" id="epReset">Reset</button>
      <span class="speed-label">Speed:</span>
      <button class="ep-btn" data-speed="0.5">0.5x</button>
      <button class="ep-btn active" data-speed="1">1x</button>
      <button class="ep-btn" data-speed="2">2x</button>
    </div>
  `;

  let epListHtml = '<div class="ep-list">';
  const kindOrder = ['route','main_guard','script','cli','task','worker_handler','other'];
  const sortedKinds = Object.keys(epByKind).sort((a,b) => {
    const ai = kindOrder.indexOf(a), bi = kindOrder.indexOf(b);
    return (ai===-1?99:ai) - (bi===-1?99:bi);
  });
  for (const kind of sortedKinds) {
    const eps = epByKind[kind];
    epListHtml += `<div class="ep-group-header">${kind} (${eps.length})</div>`;
    eps.forEach(ep => {
      const label = ep.target || ep.id;
      epListHtml += `<div class="ep-item" data-target="${ep.target}" data-id="${ep.id}">${label}</div>`;
    });
  }
  epListHtml += '</div>';
  legend.innerHTML += epListHtml;

  inspector.innerHTML = '<h3>Trace</h3><div style="color:var(--text3);font-size:12px">Select an entry point to trace its call chain</div>';

  const svg = d3.select('#mainSvg');
  const width = svg.node().clientWidth;
  const height = svg.node().clientHeight;
  const g = svg.append('g').attr('class','trace-root');

  const zoom = d3.zoom().scaleExtent([0.15,4]).on('zoom', e => g.attr('transform', e.transform));
  svg.call(zoom);

  // Build adjacency
  const adj = new Map();
  const epNodeMap = new Map();
  D.epNodes.forEach(n => epNodeMap.set(n.id, n));
  D.epEdges.forEach(e => {
    if (!adj.has(e.source)) adj.set(e.source, []);
    adj.get(e.source).push(e.target);
  });

  let animTimer = null;
  let speed = 1;
  let playing = true;

  filters.querySelectorAll('[data-speed]').forEach(btn => {
    btn.addEventListener('click', () => {
      speed = parseFloat(btn.dataset.speed);
      filters.querySelectorAll('[data-speed]').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
    });
  });

  function traceEntry(targetFn) {
    g.selectAll('*').remove();
    if (animTimer) { clearInterval(animTimer); animTimer = null; }
    playing = true;

    // BFS
    const visited = new Set();
    const levels = [];
    const parentOf = new Map(); // child -> parent (for tree edges)
    let frontier = [targetFn];
    visited.add(targetFn);

    while (frontier.length > 0 && levels.length < 12) {
      levels.push([...frontier]);
      const next = [];
      for (const fn of frontier) {
        for (const child of (adj.get(fn) || [])) {
          if (!visited.has(child)) {
            visited.add(child);
            next.push(child);
            parentOf.set(child, fn);
          }
        }
      }
      frontier = next;
    }

    // Linear left-to-right layout
    const colSpacing = 180;
    const rowSpacing = 38;
    const startX = 60;
    const startY = 50;

    const allNodes = [];
    const nodePositions = new Map();

    levels.forEach((level, li) => {
      // Sort by layer for visual grouping within each column
      const sorted = level.slice().sort((a, b) => {
        const aInfo = epNodeMap.get(a);
        const bInfo = epNodeMap.get(b);
        const aLayer = aInfo?.layer || 'other';
        const bLayer = bInfo?.layer || 'other';
        const aIdx = LAYERS.indexOf(aLayer);
        const bIdx = LAYERS.indexOf(bLayer);
        return (aIdx===-1?99:aIdx) - (bIdx===-1?99:bIdx);
      });

      sorted.forEach((nodeId, ni) => {
        const x = startX + li * colSpacing;
        const y = startY + ni * rowSpacing;
        nodePositions.set(nodeId, {x, y, level: li});
        allNodes.push({id: nodeId, x, y, level: li, info: epNodeMap.get(nodeId)});
      });
    });

    // Compute total bounds for auto-fit
    const maxX = startX + (levels.length - 1) * colSpacing + 80;
    const maxY = startY + (Math.max(...levels.map(l=>l.length)) - 1) * rowSpacing + 40;

    // Auto-fit zoom
    const scaleX = width / (maxX + 60);
    const scaleY = height / (maxY + 60);
    const autoScale = Math.min(scaleX, scaleY, 1.5);
    const tx = (width - maxX * autoScale) / 2;
    const ty = Math.max(10, (height - maxY * autoScale) / 2);
    svg.call(zoom.transform, d3.zoomIdentity.translate(tx, ty).scale(autoScale));

    // Column depth labels
    levels.forEach((level, li) => {
      g.append('text')
        .attr('x', startX + li * colSpacing)
        .attr('y', startY - 20)
        .attr('text-anchor','middle')
        .attr('font-size', 10)
        .attr('fill','var(--text3)')
        .text(`depth ${li}`);
    });

    // Build tree edges (parent -> child)
    const treeEdges = [];
    for (const [child, parent] of parentOf.entries()) {
      if (nodePositions.has(parent) && nodePositions.has(child)) {
        treeEdges.push({source: parent, target: child});
      }
    }

    // Draw edges — smooth horizontal bezier curves
    const edgeEls = g.append('g').selectAll('path').data(treeEdges).join('path')
      .attr('d', d => {
        const s = nodePositions.get(d.source);
        const t = nodePositions.get(d.target);
        if (!s || !t) return '';
        const midX = (s.x + t.x) / 2;
        return `M${s.x + 8},${s.y} C${midX},${s.y} ${midX},${t.y} ${t.x - 8},${t.y}`;
      })
      .attr('fill','none')
      .attr('stroke','rgba(148,163,184,0.06)')
      .attr('stroke-width', 1.5)
      .attr('marker-end', null);

    // Nodes
    const nodeEls = g.append('g').selectAll('circle').data(allNodes).join('circle')
      .attr('cx', d => d.x)
      .attr('cy', d => d.y)
      .attr('r', 7)
      .attr('fill', d => layerColor(d.info?.layer || 'other'))
      .attr('stroke', d => d3.color(layerColor(d.info?.layer||'other')).brighter(0.5))
      .attr('stroke-width', 0.8)
      .attr('opacity', 0.12)
      .attr('class','glow-node')
      .attr('cursor','pointer');

    // Labels — function name, right of node
    const labelEls = g.append('g').selectAll('text').data(allNodes).join('text')
      .attr('x', d => d.x + 12)
      .attr('y', d => d.y + 4)
      .text(d => {
        const l = d.info?.label || d.id;
        const parts = l.split(':');
        return parts[parts.length - 1];
      })
      .attr('font-size', 10)
      .attr('fill','var(--text3)')
      .attr('pointer-events','none')
      .attr('paint-order','stroke')
      .attr('stroke','var(--bg)')
      .attr('stroke-width', 2)
      .attr('stroke-linejoin','round')
      .attr('opacity', 0.12);

    // Layer color pills next to labels
    const pillEls = g.append('g').selectAll('rect').data(allNodes).join('rect')
      .attr('x', d => d.x - 12)
      .attr('y', d => d.y - 4)
      .attr('width', 3)
      .attr('height', 8)
      .attr('rx', 1)
      .attr('fill', d => layerColor(d.info?.layer || 'other'))
      .attr('opacity', 0.12);

    // Tooltip
    const tooltip = document.getElementById('tooltip');
    nodeEls.on('mouseenter', (e, d) => {
      tooltip.classList.remove('hidden');
      const info = d.info || {};
      tooltip.innerHTML = `
        <div class="tt-title" style="color:${layerColor(info.layer||'other')}">${info.label || d.id}</div>
        <div class="tt-row">Module: ${info.module || '-'}</div>
        <div class="tt-row">Layer: ${info.layer || '-'} · Depth: ${d.level}</div>
      `;
      tooltip.style.left = (e.clientX+16)+'px';
      tooltip.style.top = (e.clientY-10)+'px';
      // Highlight path from root to this node
      const pathNodes = new Set([d.id]);
      let cur = d.id;
      while (parentOf.has(cur)) { cur = parentOf.get(cur); pathNodes.add(cur); }
      nodeEls.attr('opacity', n => pathNodes.has(n.id) ? 1 : 0.15);
      labelEls.attr('opacity', n => pathNodes.has(n.id) ? 1 : 0.1);
      edgeEls.attr('stroke', ed => pathNodes.has(ed.source) && pathNodes.has(ed.target) ? layerColor(info.layer||'other') : 'rgba(148,163,184,0.06)')
        .attr('stroke-width', ed => pathNodes.has(ed.source) && pathNodes.has(ed.target) ? 2.5 : 1);
    })
    .on('mousemove', e => { tooltip.style.left=(e.clientX+16)+'px'; tooltip.style.top=(e.clientY-10)+'px'; })
    .on('mouseleave', () => {
      tooltip.classList.add('hidden');
    });

    // Animated BFS reveal — left to right, column by column
    let currentLevel = 0;

    function revealLevel(li) {
      if (li >= levels.length) return;
      const ids = new Set(levels[li]);
      nodeEls.filter(d => ids.has(d.id))
        .transition().duration(350 / speed).ease(d3.easeBackOut)
        .attr('opacity', 1)
        .attr('r', 8);
      labelEls.filter(d => ids.has(d.id))
        .transition().duration(250 / speed)
        .attr('opacity', 1)
        .attr('fill','var(--text2)');
      pillEls.filter(d => ids.has(d.id))
        .transition().duration(250 / speed)
        .attr('opacity', 0.9);
      // Reveal edges TO this level's nodes
      edgeEls.filter(d => ids.has(d.target))
        .transition().duration(300 / speed)
        .attr('stroke', d => {
          const tInfo = epNodeMap.get(d.target);
          return layerColor(tInfo?.layer || 'other');
        })
        .attr('stroke-opacity', 0.5)
        .attr('stroke-width', 1.8);
    }

    revealLevel(0);
    currentLevel = 1;

    animTimer = setInterval(() => {
      if (!playing) return;
      if (currentLevel >= levels.length) { clearInterval(animTimer); return; }
      revealLevel(currentLevel);
      currentLevel++;
    }, 500 / speed);

    document.getElementById('epPlay').onclick = () => { playing = true; };
    document.getElementById('epPause').onclick = () => { playing = false; };
    document.getElementById('epReset').onclick = () => { traceEntry(targetFn); };

    // Layer transitions summary
    const layerSeq = [];
    levels.forEach(level => {
      const layersInLevel = new Set(level.map(id => epNodeMap.get(id)?.layer || '?'));
      layerSeq.push([...layersInLevel]);
    });

    inspector.innerHTML = `
      <h3>Trace</h3>
      <div class="inspector-title">${targetFn.split(':').pop()}</div>
      <div class="inspector-row"><span class="label">Call depth</span><span class="value">${levels.length}</span></div>
      <div class="inspector-row"><span class="label">Functions reached</span><span class="value">${allNodes.length}</span></div>
      <div style="margin-top:8px;font-size:11px;color:var(--text3)">Layer flow:</div>
      <div style="display:flex;flex-wrap:wrap;gap:3px;margin-top:4px">
        ${layerSeq.map((ls, i) => ls.map(l =>
          `<span style="display:inline-block;background:${layerColor(l)};color:white;font-size:9px;padding:1px 5px;border-radius:3px">${l}</span>`
        ).join('')).join('<span style="color:var(--text3);font-size:10px;padding:0 1px">→</span>')}
      </div>
    `;
  }

  // EP item click handlers
  legend.querySelectorAll('.ep-item').forEach(el => {
    el.addEventListener('click', () => {
      legend.querySelectorAll('.ep-item').forEach(e => e.classList.remove('active'));
      el.classList.add('active');
      traceEntry(el.dataset.target);
    });
  });
}

/* ══════════════════════════════════════════════════════════
   VIEW 5: Quality — SVG scatter plot, module bars, heatmap
   ══════════════════════════════════════════════════════════ */
function renderQuality() {
  const sidebar = document.getElementById('sidebar');
  const legend = sidebar.querySelector('#layerLegend');
  const filters = sidebar.querySelector('#filterControls');
  const inspector = sidebar.querySelector('#inspector');

  renderLayerLegend();
  filters.innerHTML = `
    <h3>View</h3>
    <div class="filter-toggle"><input type="checkbox" id="qScatter" checked/><label for="qScatter">Complexity scatter</label></div>
    <div class="filter-toggle"><input type="checkbox" id="qModules" checked/><label for="qModules">Module breakdown</label></div>
    <div class="filter-toggle"><input type="checkbox" id="qHeatmap" checked/><label for="qHeatmap">Layer heatmap</label></div>
  `;

  const q = D.quality;
  const funcs = q.functions || [];
  const mods = q.moduleBreakdown || [];

  // Show key stats in inspector
  inspector.innerHTML = `
    <h3>Codebase Profile</h3>
    <div class="inspector-row"><span class="label">Modules</span><span class="value">${q.meta?.module_count||0}</span></div>
    <div class="inspector-row"><span class="label">Functions</span><span class="value">${q.meta?.function_count||0}</span></div>
    <div class="inspector-row"><span class="label">Classes</span><span class="value">${q.meta?.class_count||0}</span></div>
    <div class="inspector-row"><span class="label">Total lines</span><span class="value">${q.meta?.total_lines||0}</span></div>
    <div class="inspector-row"><span class="label">Type coverage</span><span class="value">${Math.round(q.typeCoverage||0)}%</span></div>
    <div class="inspector-row"><span class="label">Return coverage</span><span class="value">${Math.round(q.returnTypeCoverage||0)}%</span></div>
    <div class="inspector-row"><span class="label">Cross-layer edges</span><span class="value">${q.crossLayerEdges||0}</span></div>
  `;

  const svg = d3.select('#mainSvg');
  const width = svg.node().clientWidth;
  const height = svg.node().clientHeight;
  const g = svg.append('g').attr('class','quality-root');

  // Zoom/pan for quality view
  const zoom = d3.zoom().scaleExtent([0.2, 4]).on('zoom', e => g.attr('transform', e.transform));
  svg.call(zoom);

  // Three panels: scatter (top-left), modules (top-right), heatmap (bottom)
  const scatterW = width * 0.55;
  const scatterH = height * 0.55;
  const modW = width * 0.4;
  const modH = height * 0.55;
  const heatW = width * 0.92;
  const heatH = height * 0.38;
  const pad = 20;

  // ── Scatter: Complexity vs Span ──
  const sg = g.append('g').attr('class','scatter-panel').attr('transform',`translate(${pad+10},${pad})`);
  const sInnerW = scatterW - 70;
  const sInnerH = scatterH - 60;

  sg.append('text').attr('x', sInnerW/2).attr('y', 12).attr('text-anchor','middle')
    .attr('font-size',13).attr('font-weight',600).attr('fill','var(--text)')
    .text('Function Complexity vs Size');

  const sOffX = 45, sOffY = 30;
  const maxComp = Math.max(1, ...funcs.map(f => f.complexity));
  const maxSpan = Math.max(1, ...funcs.map(f => f.span));

  const xScale = d3.scaleLinear().domain([0, maxSpan * 1.05]).range([0, sInnerW]);
  const yScale = d3.scaleLinear().domain([0, maxComp * 1.05]).range([sInnerH, 0]);

  const scatterG = sg.append('g').attr('transform',`translate(${sOffX},${sOffY})`);

  // Grid lines
  const xTicks = xScale.ticks(6);
  const yTicks = yScale.ticks(6);
  xTicks.forEach(t => {
    scatterG.append('line').attr('x1',xScale(t)).attr('x2',xScale(t)).attr('y1',0).attr('y2',sInnerH)
      .attr('stroke','var(--border)').attr('stroke-dasharray','2 4');
  });
  yTicks.forEach(t => {
    scatterG.append('line').attr('x1',0).attr('x2',sInnerW).attr('y1',yScale(t)).attr('y2',yScale(t))
      .attr('stroke','var(--border)').attr('stroke-dasharray','2 4');
  });

  // Axes
  scatterG.append('g').attr('transform',`translate(0,${sInnerH})`)
    .call(d3.axisBottom(xScale).ticks(6).tickSize(4))
    .call(g => g.select('.domain').attr('stroke','var(--text3)'))
    .call(g => g.selectAll('.tick text').attr('fill','var(--text3)').attr('font-size',9))
    .call(g => g.selectAll('.tick line').attr('stroke','var(--text3)'));
  scatterG.append('g')
    .call(d3.axisLeft(yScale).ticks(6).tickSize(4))
    .call(g => g.select('.domain').attr('stroke','var(--text3)'))
    .call(g => g.selectAll('.tick text').attr('fill','var(--text3)').attr('font-size',9))
    .call(g => g.selectAll('.tick line').attr('stroke','var(--text3)'));

  // Axis labels
  sg.append('text').attr('x', sOffX + sInnerW/2).attr('y', sOffY + sInnerH + 38)
    .attr('text-anchor','middle').attr('font-size',10).attr('fill','var(--text3)').text('Lines of code');
  sg.append('text').attr('transform',`translate(12,${sOffY + sInnerH/2}) rotate(-90)`)
    .attr('text-anchor','middle').attr('font-size',10).attr('fill','var(--text3)').text('Cyclomatic complexity');

  // Dots
  const tooltip = document.getElementById('tooltip');
  const dots = scatterG.selectAll('circle').data(funcs).join('circle')
    .attr('cx', d => xScale(d.span))
    .attr('cy', d => yScale(d.complexity))
    .attr('r', d => clamp(2 + Math.sqrt(d.calls || 0) * 0.6, 2, 10))
    .attr('fill', d => layerColor(d.layer))
    .attr('fill-opacity', 0.55)
    .attr('stroke', d => layerColor(d.layer))
    .attr('stroke-opacity', 0.3)
    .attr('stroke-width', 0.5)
    .attr('cursor','pointer')
    .style('opacity', 0);

  dots.transition().delay((d,i) => Math.min(i * 1, 600)).duration(300).style('opacity', 1);

  dots.on('mouseenter', (e, d) => {
    d3.select(e.target).attr('r', clamp(4 + Math.sqrt(d.calls||0)*0.8, 4, 14)).attr('fill-opacity',0.9);
    tooltip.classList.remove('hidden');
    tooltip.innerHTML = `
      <div class="tt-title" style="color:${layerColor(d.layer)}">${d.id}</div>
      <div class="tt-row">Complexity: ${d.complexity} · Span: ${d.span} lines</div>
      <div class="tt-row">Calls: ${d.calls} · Module: ${d.module}</div>
    `;
    tooltip.style.left = (e.clientX+16)+'px';
    tooltip.style.top = (e.clientY-10)+'px';
  })
  .on('mousemove', e => { tooltip.style.left=(e.clientX+16)+'px'; tooltip.style.top=(e.clientY-10)+'px'; })
  .on('mouseleave', (e, d) => {
    d3.select(e.target).attr('r', clamp(2 + Math.sqrt(d.calls||0)*0.6, 2, 10)).attr('fill-opacity',0.55);
    tooltip.classList.add('hidden');
  });

  // Danger zone — highlight high complexity region
  if (maxComp > 15) {
    scatterG.append('rect')
      .attr('x', 0).attr('y', 0)
      .attr('width', sInnerW).attr('height', yScale(15))
      .attr('fill','rgba(239,68,68,0.04)')
      .attr('pointer-events','none');
    scatterG.append('text')
      .attr('x', sInnerW - 4).attr('y', yScale(15) + 12)
      .attr('text-anchor','end').attr('font-size',9).attr('fill','rgba(239,68,68,0.4)')
      .text('high complexity zone');
  }

  // ── Module breakdown: horizontal bars ──
  const mg = g.append('g').attr('class','module-panel')
    .attr('transform',`translate(${scatterW + 30},${pad})`);

  mg.append('text').attr('x', 0).attr('y', 12)
    .attr('font-size',13).attr('font-weight',600).attr('fill','var(--text)')
    .text('Module Complexity (top 20)');

  const topMods = mods.slice(0, 20);
  const mMaxComp = Math.max(1, ...topMods.map(m => m.totalComplexity));
  const mBarH = 16;
  const mGap = 3;
  const mLabelW = 110;
  const mBarW = modW - mLabelW - 60;
  const mStartY = 28;

  topMods.forEach((mod, i) => {
    const y = mStartY + i * (mBarH + mGap);
    const barW = (mod.totalComplexity / mMaxComp) * mBarW;
    const shortName = mod.module.split('.').slice(-2).join('.');

    // Module label
    mg.append('text')
      .attr('x', mLabelW - 4).attr('y', y + mBarH/2 + 3)
      .attr('text-anchor','end').attr('font-size',10)
      .attr('fill', layerColor(mod.layer))
      .text(shortName);

    // Bar background
    mg.append('rect')
      .attr('x', mLabelW).attr('y', y)
      .attr('width', mBarW).attr('height', mBarH)
      .attr('rx', 2)
      .attr('fill','var(--bg)');

    // Filled bar
    mg.append('rect')
      .attr('x', mLabelW).attr('y', y)
      .attr('width', 0).attr('height', mBarH)
      .attr('rx', 2)
      .attr('fill', layerColor(mod.layer))
      .attr('fill-opacity', 0.6)
      .attr('cursor','pointer')
      .transition().duration(600).delay(i * 30)
      .attr('width', barW);

    // Max complexity indicator — small bright segment
    if (mod.maxComplexity > 10) {
      const maxW = (mod.maxComplexity / mod.totalComplexity) * barW;
      mg.append('rect')
        .attr('x', mLabelW + barW - maxW).attr('y', y)
        .attr('width', 0).attr('height', mBarH)
        .attr('rx', 2)
        .attr('fill', mod.maxComplexity > 20 ? '#ef4444' : '#fbbf24')
        .attr('fill-opacity', 0.4)
        .transition().duration(600).delay(i * 30 + 200)
        .attr('width', maxW);
    }

    // Value
    mg.append('text')
      .attr('x', mLabelW + mBarW + 6).attr('y', y + mBarH/2 + 3)
      .attr('font-size', 10).attr('fill','var(--text3)')
      .text(`${mod.totalComplexity} (${mod.functionCount}fn)`);
  });

  // ── Layer Dependency Heatmap (bottom) ──
  const hg = g.append('g').attr('class','heatmap-panel')
    .attr('transform',`translate(${pad + 10},${scatterH + 20})`);

  hg.append('text').attr('x', 0).attr('y', 12)
    .attr('font-size',13).attr('font-weight',600).attr('fill','var(--text)')
    .text('Layer Dependency Matrix');

  const layers = LAYERS;
  const matrixMap = {};
  (q.layerMatrix||[]).forEach(m => { matrixMap[m.source_layer+'_'+m.target_layer] = m; });
  const maxCount = Math.max(1, ...(q.layerMatrix||[]).map(m => m.count||0));

  const cellSize = Math.min(52, (heatW - 100) / Math.max(layers.length, 1));
  const hLabelW = 70;
  const hStartX = hLabelW;
  const hStartY = 40;

  // Column headers
  layers.forEach((l, i) => {
    hg.append('text')
      .attr('x', hStartX + i * cellSize + cellSize/2)
      .attr('y', hStartY - 6)
      .attr('text-anchor','middle')
      .attr('font-size', 11).attr('font-weight',600)
      .attr('fill', layerColor(l))
      .text(LAYER_LABELS[l]||l);
  });

  // Rows
  layers.forEach((sl, si) => {
    const y = hStartY + si * cellSize;

    // Row label
    hg.append('text')
      .attr('x', hLabelW - 8).attr('y', y + cellSize/2 + 3)
      .attr('text-anchor','end')
      .attr('font-size', 11).attr('font-weight',600)
      .attr('fill', layerColor(sl))
      .text(LAYER_LABELS[sl]||sl);

    layers.forEach((tl, ti) => {
      const x = hStartX + ti * cellSize;
      const m = matrixMap[sl+'_'+tl];
      const cnt = m ? m.count : 0;
      const intensity = cnt / maxCount;

      const isDiag = sl === tl;
      let fillColor;
      if (cnt === 0) fillColor = 'rgba(148,163,184,0.04)';
      else if (isDiag) fillColor = `rgba(148,163,184,${0.08 + intensity * 0.3})`;
      else fillColor = `rgba(59,130,246,${0.1 + intensity * 0.5})`;

      hg.append('rect')
        .attr('x', x + 1).attr('y', y + 1)
        .attr('width', cellSize - 2).attr('height', cellSize - 2)
        .attr('rx', 4)
        .attr('fill', fillColor)
        .attr('stroke', 'var(--border)')
        .attr('stroke-width', 0.5)
        .attr('cursor','pointer')
        .on('mouseenter', function(e) {
          d3.select(this).attr('stroke-width', 2).attr('stroke', layerColor(sl));
          tooltip.classList.remove('hidden');
          tooltip.innerHTML = `
            <div class="tt-title">${LAYER_LABELS[sl]||sl} → ${LAYER_LABELS[tl]||tl}</div>
            <div class="tt-row">${cnt} dependency edges</div>
            ${isDiag ? '<div class="tt-row" style="color:var(--text3)">Intra-layer</div>' : ''}
          `;
          tooltip.style.left = (e.clientX+16)+'px';
          tooltip.style.top = (e.clientY-10)+'px';
        })
        .on('mousemove', e => { tooltip.style.left=(e.clientX+16)+'px'; tooltip.style.top=(e.clientY-10)+'px'; })
        .on('mouseleave', function() {
          d3.select(this).attr('stroke-width', 0.5).attr('stroke', 'var(--border)');
          tooltip.classList.add('hidden');
        });

      // Count text
      hg.append('text')
        .attr('x', x + cellSize/2).attr('y', y + cellSize/2 + 4)
        .attr('text-anchor','middle')
        .attr('font-size', cnt > 0 ? 14 : 11)
        .attr('font-weight', cnt > 0 ? 700 : 400)
        .attr('fill', cnt > 0 ? 'var(--text)' : 'var(--text3)')
        .attr('pointer-events','none')
        .text(cnt > 0 ? cnt : '·');
    });
  });

  // Hotspot sparkline — right side of heatmap area
  const hsX = hStartX + layers.length * cellSize + 60;
  const hsY = hStartY;

  hg.append('text').attr('x', hsX).attr('y', hsY - 6)
    .attr('font-size',12).attr('font-weight',600).attr('fill','var(--text)')
    .text('Top Hotspots');

  const spots = q.hotspots || [];
  const maxHs = Math.max(1, ...spots.map(s => s.complexity||0));
  const hsBarW = 160;

  spots.slice(0,12).forEach((s, i) => {
    const y = hsY + i * 20;
    const pct = (s.complexity||0) / maxHs;
    const shortName = (s.id||'').split('.').slice(-2).join('.');

    hg.append('rect')
      .attr('x', hsX + 90).attr('y', y)
      .attr('width', 0).attr('height', 14)
      .attr('rx', 2)
      .attr('fill', pct > 0.6 ? '#ef4444' : pct > 0.3 ? '#fbbf24' : '#10b981')
      .attr('fill-opacity', 0.5)
      .transition().duration(500).delay(i*40)
      .attr('width', pct * hsBarW);

    hg.append('text')
      .attr('x', hsX + 86).attr('y', y + 11)
      .attr('text-anchor','end').attr('font-size',9)
      .attr('fill','var(--text2)')
      .text(shortName);

    hg.append('text')
      .attr('x', hsX + 94 + pct * hsBarW).attr('y', y + 11)
      .attr('font-size',9).attr('fill','var(--text3)')
      .text(s.complexity);
  });

  // Toggle visibility
  ['qScatter','qModules','qHeatmap'].forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;
    el.addEventListener('change', () => {
      const map = {qScatter:'.scatter-panel', qModules:'.module-panel', qHeatmap:'.heatmap-panel'};
      g.select(map[id]).style('display', el.checked ? null : 'none');
    });
  });
}

/* ══════════════════════════════════════════════════════════
   VIEW 6: Data Flow — module clusters with drill-down
   ══════════════════════════════════════════════════════════ */
function renderDataFlow() {
  const sidebar = document.getElementById('sidebar');
  const filters = sidebar.querySelector('#filterControls');
  const inspector = sidebar.querySelector('#inspector');
  const tooltip = document.getElementById('tooltip');

  renderLayerLegend();

  const dataTypes = D.dataTypes || [];
  const transforms = D.typeTransformations || [];

  if (!dataTypes.length) {
    inspector.innerHTML = '<h3>Data</h3><div style="color:var(--text3);font-size:12px">No data types found (dataclasses, Pydantic models, etc.)</div>';
    filters.innerHTML = '';
    return;
  }

  // Build lookups
  const typeByName = new Map();
  dataTypes.forEach(dt => typeByName.set(dt.name, dt));

  // Group types by module
  const modMap = {};
  dataTypes.forEach(dt => {
    const m = dt.module;
    if (!modMap[m]) modMap[m] = { module: m, layer: dt.layer, types: [], kinds: new Set() };
    modMap[m].types.push(dt);
    modMap[m].kinds.add(dt.kind);
  });
  const modules = Object.values(modMap);
  modules.forEach(m => {
    m.kinds = [...m.kinds].sort();
    m.types.sort((a, b) => a.name.localeCompare(b.name));
    m.shortName = m.module.split('.').slice(-2).join('.');
  });

  // Aggregate module-to-module transform counts
  const modEdgeMap = {};
  transforms.forEach(t => {
    const src = typeByName.get(t.sourceType);
    const tgt = typeByName.get(t.targetType);
    if (!src || !tgt) return;
    const key = src.module + '|' + tgt.module;
    if (!modEdgeMap[key]) modEdgeMap[key] = { source: src.module, target: tgt.module, count: 0, transforms: [] };
    modEdgeMap[key].count++;
    modEdgeMap[key].transforms.push(t);
  });
  const modEdges = Object.values(modEdgeMap);

  // Kind colors
  const kindColors = {
    dataclass: '#8b5cf6', pydantic: '#3b82f6', sqlalchemy: '#10b981',
    typeddict: '#f77f00', namedtuple: '#e879f9', class: '#94a3b8',
  };

  // Filters
  const kinds = [...new Set(dataTypes.map(dt => dt.kind))].sort();
  filters.innerHTML = `
    <h3>Type Kind</h3>
    ${kinds.map(k => `<div class="filter-toggle"><input type="checkbox" id="dtk-${k}" checked/><label for="dtk-${k}">${k}</label></div>`).join('')}
    <h3 style="margin-top:8px">Display</h3>
    <div class="filter-toggle"><input type="checkbox" id="dtShowEdges" checked/><label for="dtShowEdges">Show transforms</label></div>
  `;

  const modCount = modules.length;
  inspector.innerHTML = `
    <h3>Data Types</h3>
    <div class="inspector-row"><span class="label">Modules</span><span class="value">${modCount}</span></div>
    <div class="inspector-row"><span class="label">Types</span><span class="value">${dataTypes.length}</span></div>
    <div class="inspector-row"><span class="label">Transforms</span><span class="value">${transforms.length}</span></div>
    <div style="margin-top:6px;font-size:11px;color:var(--text3)">Click a module to expand its types. Click a type for detail.</div>
  `;

  const svg = d3.select('#mainSvg');
  const width = svg.node().clientWidth;
  const height = svg.node().clientHeight;
  const g = svg.append('g').attr('class','dataflow-root');

  const zoom = d3.zoom().scaleExtent([0.1, 6]).on('zoom', e => g.attr('transform', e.transform));
  svg.call(zoom);

  // Arrowhead marker
  const defs = svg.select('defs');
  defs.append('marker').attr('id','dataArrow')
    .attr('viewBox','0 -3 6 6').attr('refX',6).attr('refY',0)
    .attr('markerWidth',6).attr('markerHeight',6).attr('orient','auto')
    .append('path').attr('d','M0,-3L6,0L0,3').attr('fill','rgba(148,163,184,0.4)');
  defs.append('marker').attr('id','dataArrowGold')
    .attr('viewBox','0 -3 6 6').attr('refX',6).attr('refY',0)
    .attr('markerWidth',6).attr('markerHeight',6).attr('orient','auto')
    .append('path').attr('d','M0,-3L6,0L0,3').attr('fill','var(--gold)');

  // Layout constants
  const clusterW = 220;
  const clusterHeaderH = 28;
  const typeRowH = 18;
  const kindPillH = 16;
  const clusterPad = 6;
  const colSpacing = clusterW + 80;
  const rowSpacing = 14;
  const startX = 40;
  const startY = 50;

  // Expanded state
  const expanded = new Set();
  let selectedType = null;

  // Cluster height based on expanded state
  function clusterH(mod) {
    const base = clusterHeaderH + kindPillH + clusterPad;
    if (!expanded.has(mod.module)) {
      return base + mod.types.length * typeRowH + clusterPad;
    }
    // Expanded: show type cards with fields
    let h = base;
    mod.types.forEach(dt => {
      h += 26 + dt.fields.length * 15 + 10;
    });
    return h + clusterPad;
  }

  // Group modules by layer
  const layerModules = {};
  modules.forEach(m => {
    const l = m.layer || 'other';
    (layerModules[l] = layerModules[l] || []).push(m);
  });
  Object.values(layerModules).forEach(arr => arr.sort((a, b) => a.module.localeCompare(b.module)));

  const layerOrder = LAYERS.filter(l => layerModules[l]);
  Object.keys(layerModules).forEach(l => { if (!layerOrder.includes(l)) layerOrder.push(l); });

  const edgeG = g.append('g').attr('class','mod-edges');
  const clusterG = g.append('g').attr('class','mod-clusters');

  function layout() {
    const positions = new Map(); // module name → {x, y, h}

    layerOrder.forEach((layer, li) => {
      const mods = layerModules[layer] || [];
      let y = startY;
      mods.forEach(mod => {
        const h = clusterH(mod);
        positions.set(mod.module, { x: startX + li * colSpacing, y, h, layer });
        y += h + rowSpacing;
      });
    });
    return positions;
  }

  function render() {
    clusterG.selectAll('*').remove();
    edgeG.selectAll('*').remove();

    const positions = layout();

    // Column headers
    layerOrder.forEach((layer, li) => {
      clusterG.append('text')
        .attr('x', startX + li * colSpacing + clusterW / 2)
        .attr('y', startY - 18)
        .attr('text-anchor', 'middle')
        .attr('font-size', 13).attr('font-weight', 700)
        .attr('fill', layerColor(layer))
        .text(LAYER_LABELS[layer] || layer);
    });

    // Draw module-to-module edges
    const showEdges = document.getElementById('dtShowEdges')?.checked ?? true;
    if (showEdges) {
      modEdges.forEach(me => {
        const sp = positions.get(me.source);
        const tp = positions.get(me.target);
        if (!sp || !tp) return;

        const isSelf = me.source === me.target;
        const hasEndpoint = me.transforms.some(t => t.kind === 'endpoint');
        const strokeColor = hasEndpoint ? 'var(--gold)' : 'rgba(148,163,184,0.3)';
        const strokeW = Math.min(1 + me.count * 0.5, 5);

        if (isSelf) {
          // Self-loop arc
          const cx = sp.x + clusterW + 20;
          const cy = sp.y + sp.h / 2;
          const r = Math.min(sp.h / 3, 30);
          edgeG.append('path')
            .attr('d', `M${sp.x + clusterW},${cy - r/2} A${r},${r} 0 1,1 ${sp.x + clusterW},${cy + r/2}`)
            .attr('fill', 'none').attr('stroke', strokeColor)
            .attr('stroke-width', strokeW).attr('stroke-opacity', 0.6)
            .attr('marker-end', hasEndpoint ? 'url(#dataArrowGold)' : 'url(#dataArrow)')
            .attr('data-src', me.source).attr('data-tgt', me.target);
          edgeG.append('text')
            .attr('x', cx + r + 4).attr('y', cy + 3)
            .attr('font-size', 9).attr('fill', strokeColor)
            .text(me.count);
        } else {
          const sx = sp.x + clusterW;
          const sy = sp.y + sp.h / 2;
          const tx = tp.x;
          const ty = tp.y + tp.h / 2;
          const sameCol = Math.abs(sp.x - tp.x) < 10;
          let d;
          if (sameCol) {
            const off = 30;
            d = `M${sx},${sy} C${sx+off},${sy} ${tx+off},${ty} ${tx + clusterW},${ty}`;
          } else {
            const midX = (sx + tx) / 2;
            d = `M${sx},${sy} C${midX},${sy} ${midX},${ty} ${tx},${ty}`;
          }
          edgeG.append('path')
            .attr('d', d).attr('fill', 'none')
            .attr('stroke', strokeColor).attr('stroke-width', strokeW)
            .attr('stroke-opacity', 0.6)
            .attr('marker-end', hasEndpoint ? 'url(#dataArrowGold)' : 'url(#dataArrow)')
            .attr('data-src', me.source).attr('data-tgt', me.target);
          // Count label at midpoint
          const mx = sameCol ? sx + 30 : (sx + tx) / 2;
          const my = (sy + ty) / 2 - 5;
          edgeG.append('text')
            .attr('x', mx).attr('y', my)
            .attr('text-anchor', 'middle').attr('font-size', 9)
            .attr('fill', strokeColor)
            .text(me.count);
        }
      });
    }

    // Draw module clusters
    modules.forEach(mod => {
      const pos = positions.get(mod.module);
      if (!pos) return;
      const h = clusterH(mod);
      const isExpanded = expanded.has(mod.module);
      const cg = clusterG.append('g')
        .attr('class', 'mod-cluster')
        .attr('data-mod', mod.module)
        .attr('transform', `translate(${pos.x},${pos.y})`);

      // Background
      cg.append('rect')
        .attr('width', clusterW).attr('height', h).attr('rx', 8)
        .attr('fill', 'var(--bg2)')
        .attr('stroke', layerColor(mod.layer))
        .attr('stroke-width', isExpanded ? 1.5 : 0.8)
        .attr('stroke-opacity', isExpanded ? 0.7 : 0.3);

      // Header background
      cg.append('rect')
        .attr('width', clusterW).attr('height', clusterHeaderH).attr('rx', 8)
        .attr('fill', layerColor(mod.layer)).attr('fill-opacity', 0.12);
      cg.append('rect')
        .attr('y', clusterHeaderH - 8).attr('width', clusterW).attr('height', 8)
        .attr('fill', layerColor(mod.layer)).attr('fill-opacity', 0.12);

      // Module name
      cg.append('text')
        .attr('x', clusterPad + 14).attr('y', 18)
        .attr('font-size', 11).attr('font-weight', 600)
        .attr('fill', layerColor(mod.layer))
        .text(mod.shortName);

      // Expand/collapse chevron
      cg.append('text')
        .attr('x', clusterPad).attr('y', 18)
        .attr('font-size', 10).attr('fill', 'var(--text3)')
        .text(isExpanded ? '▾' : '▸');

      // Type count badge
      cg.append('text')
        .attr('x', clusterW - clusterPad).attr('y', 18)
        .attr('text-anchor', 'end').attr('font-size', 10)
        .attr('fill', 'var(--text3)')
        .text(mod.types.length + ' types');

      // Kind pills
      let pillX = clusterPad;
      mod.kinds.forEach(k => {
        const count = mod.types.filter(t => t.kind === k).length;
        const label = k.slice(0, 3).toUpperCase() + ' ' + count;
        const tw = label.length * 6 + 8;
        cg.append('rect')
          .attr('x', pillX).attr('y', clusterHeaderH + 2)
          .attr('width', tw).attr('height', kindPillH - 2).attr('rx', 3)
          .attr('fill', kindColors[k] || '#666').attr('fill-opacity', 0.15);
        cg.append('text')
          .attr('x', pillX + tw/2).attr('y', clusterHeaderH + kindPillH - 4)
          .attr('text-anchor', 'middle').attr('font-size', 8)
          .attr('fill', kindColors[k] || '#999')
          .text(label);
        pillX += tw + 4;
      });

      const contentY = clusterHeaderH + kindPillH + clusterPad;

      if (!isExpanded) {
        // Collapsed: show type names as compact list
        mod.types.forEach((dt, i) => {
          cg.append('text')
            .attr('x', clusterPad + 2)
            .attr('y', contentY + i * typeRowH + 13)
            .attr('font-size', 10)
            .attr('fill', selectedType === dt.name ? layerColor(mod.layer) : 'var(--text2)')
            .attr('font-weight', selectedType === dt.name ? 600 : 400)
            .attr('class', 'type-name-row')
            .attr('data-name', dt.name)
            .text(dt.name)
            .style('cursor', 'pointer');

          // Field count on right
          cg.append('text')
            .attr('x', clusterW - clusterPad)
            .attr('y', contentY + i * typeRowH + 13)
            .attr('text-anchor', 'end').attr('font-size', 9)
            .attr('fill', 'var(--text3)')
            .text(dt.fields.length + 'f');
        });
      } else {
        // Expanded: show type cards with fields
        let yOff = contentY;
        mod.types.forEach(dt => {
          const isSelected = selectedType === dt.name;

          // Type header
          cg.append('rect')
            .attr('x', 4).attr('y', yOff)
            .attr('width', clusterW - 8).attr('height', 22).attr('rx', 4)
            .attr('fill', isSelected ? layerColor(mod.layer) : 'rgba(148,163,184,0.06)')
            .attr('fill-opacity', isSelected ? 0.2 : 1);

          cg.append('text')
            .attr('x', clusterPad + 2).attr('y', yOff + 15)
            .attr('font-size', 11).attr('font-weight', 600)
            .attr('fill', isSelected ? layerColor(mod.layer) : 'var(--text1)')
            .attr('class', 'type-name-row')
            .attr('data-name', dt.name)
            .text(dt.name)
            .style('cursor', 'pointer');

          // Kind badge
          cg.append('text')
            .attr('x', clusterW - clusterPad - 2).attr('y', yOff + 14)
            .attr('text-anchor', 'end').attr('font-size', 8)
            .attr('fill', kindColors[dt.kind] || 'var(--text3)')
            .text(dt.kind);

          yOff += 24;

          // Fields
          dt.fields.forEach((f, fi) => {
            if (fi % 2 === 0) {
              cg.append('rect')
                .attr('x', 6).attr('y', yOff)
                .attr('width', clusterW - 12).attr('height', 15).attr('rx', 2)
                .attr('fill', 'rgba(148,163,184,0.03)');
            }
            cg.append('text')
              .attr('x', clusterPad + 6).attr('y', yOff + 11)
              .attr('font-size', 9.5)
              .attr('fill', f.hasDefault ? 'var(--text3)' : 'var(--text2)')
              .text(f.name);
            const ts = f.type.length > 16 ? f.type.slice(0,14)+'..' : f.type;
            cg.append('text')
              .attr('x', clusterW - clusterPad - 2).attr('y', yOff + 11)
              .attr('text-anchor', 'end').attr('font-size', 8.5)
              .attr('fill', 'var(--text3)').attr('font-style', 'italic')
              .text(ts);
            yOff += 15;
          });
          yOff += 10;
        });
      }

      // Click header to expand/collapse
      cg.on('click', (e) => {
        // Check if they clicked a type name row
        const target = d3.select(e.target);
        if (target.classed('type-name-row')) {
          const name = target.attr('data-name');
          selectType(name);
          e.stopPropagation();
          return;
        }
        // Toggle expand
        if (expanded.has(mod.module)) expanded.delete(mod.module);
        else expanded.add(mod.module);
        render();
      });

      // Hover tooltip
      cg.on('mouseenter', (e) => {
        tooltip.classList.remove('hidden');
        tooltip.innerHTML = `
          <div class="tt-title" style="color:${layerColor(mod.layer)}">${mod.module}</div>
          <div class="tt-row">${mod.types.length} types · ${mod.kinds.join(', ')}</div>
          <div class="tt-row">Click to ${isExpanded ? 'collapse' : 'expand fields'}</div>
        `;
        tooltip.style.left = (e.clientX + 16) + 'px';
        tooltip.style.top = (e.clientY - 10) + 'px';
      })
      .on('mousemove', e => {
        tooltip.style.left = (e.clientX + 16) + 'px';
        tooltip.style.top = (e.clientY - 10) + 'px';
      })
      .on('mouseleave', () => tooltip.classList.add('hidden'));
    });

    // Auto-fit
    const allPos = [...layout().values()];
    if (allPos.length) {
      const maxX = Math.max(...allPos.map(p => p.x)) + clusterW + 40;
      const maxY = Math.max(...allPos.map(p => p.y + p.h)) + 40;
      const scaleX = width / maxX;
      const scaleY = height / maxY;
      const s = Math.min(scaleX, scaleY, 1);
      const tx = Math.max(10, (width - maxX * s) / 2);
      svg.call(zoom.transform, d3.zoomIdentity.translate(tx, 10).scale(s));
    }
  }

  function selectType(name) {
    selectedType = name;
    const dt = typeByName.get(name);
    if (!dt) return;

    // Inspector detail
    const related = transforms.filter(t => t.sourceType === name || t.targetType === name);
    inspector.innerHTML = `
      <h3>Type Detail</h3>
      <div class="inspector-title" style="color:${layerColor(dt.layer)}">${dt.name}</div>
      <div class="inspector-row"><span class="label">Kind</span><span class="value">${dt.kind}</span></div>
      <div class="inspector-row"><span class="label">Module</span><span class="value" style="font-size:10px">${dt.module}</span></div>
      <div class="inspector-row"><span class="label">Fields</span><span class="value">${dt.fields.length}</span></div>
      <div class="inspector-row"><span class="label">Bases</span><span class="value">${dt.bases.join(', ') || '-'}</span></div>
      ${dt.fields.length ? '<div style="margin-top:6px;font-size:11px;color:var(--text3)">Fields:</div>' : ''}
      ${dt.fields.map(f => `<div class="inspector-row"><span class="label">${f.name}</span><span class="value" style="font-size:10px">${f.type}</span></div>`).join('')}
      ${related.length ? '<div style="margin-top:6px;font-size:11px;color:var(--text3)">Transforms:</div>' : ''}
      ${related.map(t => {
        const fn = t.functionId.split(':').pop();
        return `<div class="inspector-row"><span class="label" style="font-size:10px">${t.sourceType} → ${t.targetType}</span><span class="value" style="font-size:9px">${fn}</span></div>`;
      }).join('')}
    `;

    // Highlight connected modules
    const connectedMods = new Set([dt.module]);
    related.forEach(t => {
      const src = typeByName.get(t.sourceType);
      const tgt = typeByName.get(t.targetType);
      if (src) connectedMods.add(src.module);
      if (tgt) connectedMods.add(tgt.module);
    });

    clusterG.selectAll('.mod-cluster').style('opacity', function() {
      return connectedMods.has(d3.select(this).attr('data-mod')) ? 1 : 0.2;
    });
    edgeG.selectAll('path').attr('stroke-opacity', function() {
      const s = d3.select(this).attr('data-src');
      const t = d3.select(this).attr('data-tgt');
      return (connectedMods.has(s) && connectedMods.has(t)) ? 0.8 : 0.05;
    });

    render();
  }

  // Double-click to reset selection
  svg.on('dblclick.reset', () => {
    selectedType = null;
    clusterG.selectAll('.mod-cluster').style('opacity', 1);
    edgeG.selectAll('path').attr('stroke-opacity', 0.6);
    inspector.innerHTML = `
      <h3>Data Types</h3>
      <div class="inspector-row"><span class="label">Modules</span><span class="value">${modCount}</span></div>
      <div class="inspector-row"><span class="label">Types</span><span class="value">${dataTypes.length}</span></div>
      <div class="inspector-row"><span class="label">Transforms</span><span class="value">${transforms.length}</span></div>
      <div style="margin-top:6px;font-size:11px;color:var(--text3)">Click a module to expand its types. Click a type for detail.</div>
    `;
    render();
  });

  // Filter listeners
  kinds.forEach(k => {
    const el = document.getElementById('dtk-' + k);
    if (el) el.addEventListener('change', render);
  });
  const showEdgesEl = document.getElementById('dtShowEdges');
  if (showEdgesEl) showEdgesEl.addEventListener('change', render);

  render();
}

/* ── Boot ── */
init();
})();
"""
