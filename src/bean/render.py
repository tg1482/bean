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
        <button class="tab active" data-view="data">Data</button>
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
let currentView = 'data';
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
  switchView('data');
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
   VIEW 6: Data Flow — types, fields, transformations
   ══════════════════════════════════════════════════════════ */
function renderDataFlow() {
  const sidebar = document.getElementById('sidebar');
  const legend = sidebar.querySelector('#layerLegend');
  const filters = sidebar.querySelector('#filterControls');
  const inspector = sidebar.querySelector('#inspector');

  renderLayerLegend();

  const dataTypes = D.dataTypes || [];
  const transforms = D.typeTransformations || [];

  if (!dataTypes.length) {
    inspector.innerHTML = '<h3>Data</h3><div style="color:var(--text3);font-size:12px">No data types found (dataclasses, Pydantic models, etc.)</div>';
    filters.innerHTML = '';
    return;
  }

  // Kind filter
  const kinds = [...new Set(dataTypes.map(dt => dt.kind))].sort();
  filters.innerHTML = `
    <h3>Type Kind</h3>
    ${kinds.map(k => `<div class="filter-toggle"><input type="checkbox" id="dtk-${k}" checked/><label for="dtk-${k}">${k}</label></div>`).join('')}
    <h3 style="margin-top:8px">Display</h3>
    <div class="filter-toggle"><input type="checkbox" id="dtShowFields" checked/><label for="dtShowFields">Show fields</label></div>
    <div class="filter-toggle"><input type="checkbox" id="dtShowEdges" checked/><label for="dtShowEdges">Show transformations</label></div>
  `;

  inspector.innerHTML = `
    <h3>Data Types</h3>
    <div class="inspector-row"><span class="label">Types</span><span class="value">${dataTypes.length}</span></div>
    <div class="inspector-row"><span class="label">Transformations</span><span class="value">${transforms.length}</span></div>
    <div style="margin-top:6px;font-size:11px;color:var(--text3)">Click a type to inspect</div>
  `;

  const svg = d3.select('#mainSvg');
  const width = svg.node().clientWidth;
  const height = svg.node().clientHeight;
  const g = svg.append('g').attr('class','dataflow-root');

  const zoom = d3.zoom().scaleExtent([0.1, 4]).on('zoom', e => g.attr('transform', e.transform));
  svg.call(zoom);

  // Card dimensions
  const cardW = 200;
  const fieldH = 16;
  const headerH = 32;
  const kindBadgeH = 14;
  const cardPadding = 8;

  function cardHeight(dt) {
    return headerH + kindBadgeH + dt.fields.length * fieldH + cardPadding * 2;
  }

  // Build type name → data type lookup
  const typeByName = new Map();
  dataTypes.forEach(dt => typeByName.set(dt.name, dt));

  // Layout: group by layer, arrange in columns
  const layerGroups = {};
  dataTypes.forEach(dt => {
    const l = dt.layer || 'other';
    (layerGroups[l] = layerGroups[l] || []).push(dt);
  });

  const layerOrder = LAYERS.filter(l => layerGroups[l]);
  // Add any layers not in LAYERS
  Object.keys(layerGroups).forEach(l => {
    if (!layerOrder.includes(l)) layerOrder.push(l);
  });

  const colSpacing = cardW + 60;
  const rowSpacing = 20;
  const startX = 40;
  const startY = 40;

  const positions = new Map(); // dt.id → {x, y, h}

  layerOrder.forEach((layer, li) => {
    const types = layerGroups[layer] || [];
    // Sort by kind then name
    types.sort((a, b) => a.kind.localeCompare(b.kind) || a.name.localeCompare(b.name));
    let y = startY;
    types.forEach(dt => {
      const h = cardHeight(dt);
      positions.set(dt.id, { x: startX + li * colSpacing, y: y, h: h, layer: layer });
      y += h + rowSpacing;
    });
  });

  // Auto-fit
  const maxX = startX + layerOrder.length * colSpacing;
  const maxY = Math.max(...[...positions.values()].map(p => p.y + p.h), height);
  const scaleX = width / (maxX + 40);
  const scaleY = height / (maxY + 40);
  const autoScale = Math.min(scaleX, scaleY, 1);
  const tx = Math.max(10, (width - maxX * autoScale) / 2);
  svg.call(zoom.transform, d3.zoomIdentity.translate(tx, 10).scale(autoScale));

  // Column headers (layer names)
  layerOrder.forEach((layer, li) => {
    g.append('text')
      .attr('x', startX + li * colSpacing + cardW / 2)
      .attr('y', startY - 16)
      .attr('text-anchor', 'middle')
      .attr('font-size', 13)
      .attr('font-weight', 700)
      .attr('fill', layerColor(layer))
      .text(LAYER_LABELS[layer] || layer);
  });

  // Draw transformation edges
  const edgeG = g.append('g').attr('class', 'transform-edges');
  const edgeData = transforms.filter(t => typeByName.has(t.sourceType) && typeByName.has(t.targetType));

  const edgeEls = edgeG.selectAll('path').data(edgeData).join('path')
    .attr('d', d => {
      const src = typeByName.get(d.sourceType);
      const tgt = typeByName.get(d.targetType);
      if (!src || !tgt) return '';
      const sp = positions.get(src.id);
      const tp = positions.get(tgt.id);
      if (!sp || !tp) return '';
      const sx = sp.x + cardW;
      const sy = sp.y + sp.h / 2;
      const tx = tp.x;
      const ty = tp.y + tp.h / 2;
      // If same column or going backwards, curve more
      const midX = (sx + tx) / 2;
      return `M${sx},${sy} C${midX},${sy} ${midX},${ty} ${tx},${ty}`;
    })
    .attr('fill', 'none')
    .attr('stroke', d => {
      if (d.kind === 'endpoint') return 'var(--gold)';
      return 'rgba(148,163,184,0.25)';
    })
    .attr('stroke-width', d => d.kind === 'endpoint' ? 2 : 1.2)
    .attr('stroke-dasharray', d => d.kind === 'method' ? '4 3' : null)
    .attr('marker-end', null);

  // Draw arrowheads
  const defs = svg.select('defs');
  const arrowId = 'dataArrow';
  defs.append('marker')
    .attr('id', arrowId)
    .attr('viewBox', '0 -3 6 6')
    .attr('refX', 6).attr('refY', 0)
    .attr('markerWidth', 6).attr('markerHeight', 6)
    .attr('orient', 'auto')
    .append('path').attr('d', 'M0,-3L6,0L0,3').attr('fill', 'rgba(148,163,184,0.4)');

  edgeEls.attr('marker-end', `url(#${arrowId})`);

  // Edge labels (function name)
  edgeG.selectAll('text').data(edgeData).join('text')
    .attr('x', d => {
      const src = typeByName.get(d.sourceType);
      const tgt = typeByName.get(d.targetType);
      if (!src || !tgt) return 0;
      const sp = positions.get(src.id);
      const tp = positions.get(tgt.id);
      if (!sp || !tp) return 0;
      return (sp.x + cardW + tp.x) / 2;
    })
    .attr('y', d => {
      const src = typeByName.get(d.sourceType);
      const tgt = typeByName.get(d.targetType);
      if (!src || !tgt) return 0;
      const sp = positions.get(src.id);
      const tp = positions.get(tgt.id);
      if (!sp || !tp) return 0;
      return (sp.y + sp.h / 2 + tp.y + tp.h / 2) / 2 - 4;
    })
    .attr('text-anchor', 'middle')
    .attr('font-size', 8)
    .attr('fill', d => d.kind === 'endpoint' ? 'var(--gold)' : 'var(--text3)')
    .text(d => {
      const parts = d.functionId.split(':');
      const fn = parts[parts.length - 1];
      return fn.length > 25 ? fn.slice(0, 23) + '..' : fn;
    });

  // Draw type cards
  const cardG = g.append('g').attr('class', 'type-cards');
  const tooltip = document.getElementById('tooltip');

  dataTypes.forEach(dt => {
    const pos = positions.get(dt.id);
    if (!pos) return;
    const h = cardHeight(dt);
    const cg = cardG.append('g')
      .attr('class', 'type-card')
      .attr('transform', `translate(${pos.x},${pos.y})`);

    // Card background
    cg.append('rect')
      .attr('width', cardW)
      .attr('height', h)
      .attr('rx', 6)
      .attr('fill', 'var(--bg2)')
      .attr('stroke', layerColor(dt.layer))
      .attr('stroke-width', 1.2)
      .attr('stroke-opacity', 0.5);

    // Header bar
    cg.append('rect')
      .attr('width', cardW)
      .attr('height', headerH)
      .attr('rx', 6)
      .attr('fill', layerColor(dt.layer))
      .attr('fill-opacity', 0.15);
    // Clip bottom corners of header
    cg.append('rect')
      .attr('y', headerH - 6)
      .attr('width', cardW)
      .attr('height', 6)
      .attr('fill', layerColor(dt.layer))
      .attr('fill-opacity', 0.15);

    // Type name
    cg.append('text')
      .attr('x', cardPadding)
      .attr('y', 20)
      .attr('font-size', 13)
      .attr('font-weight', 700)
      .attr('fill', layerColor(dt.layer))
      .text(dt.name);

    // Kind badge
    const kindColors = {
      dataclass: '#8b5cf6', pydantic: '#3b82f6', sqlalchemy: '#10b981',
      typeddict: '#f77f00', namedtuple: '#e879f9',
    };
    cg.append('text')
      .attr('x', cardPadding)
      .attr('y', headerH + kindBadgeH - 2)
      .attr('font-size', 9)
      .attr('fill', kindColors[dt.kind] || 'var(--text3)')
      .attr('letter-spacing', '0.05em')
      .text(dt.kind.toUpperCase());

    // Fields
    const fieldsG = cg.append('g')
      .attr('class', 'fields-group')
      .attr('transform', `translate(0,${headerH + kindBadgeH + 4})`);

    dt.fields.forEach((field, fi) => {
      const fy = fi * fieldH;

      // Alternating row background
      if (fi % 2 === 0) {
        fieldsG.append('rect')
          .attr('x', 2).attr('y', fy)
          .attr('width', cardW - 4).attr('height', fieldH)
          .attr('fill', 'rgba(148,163,184,0.03)')
          .attr('rx', 2);
      }

      // Field name
      fieldsG.append('text')
        .attr('x', cardPadding)
        .attr('y', fy + 12)
        .attr('font-size', 10)
        .attr('fill', field.hasDefault ? 'var(--text3)' : 'var(--text2)')
        .text(field.name);

      // Field type (right-aligned, truncated)
      const typeStr = field.type.length > 18 ? field.type.slice(0, 16) + '..' : field.type;
      fieldsG.append('text')
        .attr('x', cardW - cardPadding)
        .attr('y', fy + 12)
        .attr('text-anchor', 'end')
        .attr('font-size', 9)
        .attr('fill', 'var(--text3)')
        .attr('font-style', 'italic')
        .text(typeStr);
    });

    // Hover / click
    cg.on('mouseenter', (e) => {
      tooltip.classList.remove('hidden');
      tooltip.innerHTML = `
        <div class="tt-title" style="color:${layerColor(dt.layer)}">${dt.name}</div>
        <div class="tt-row">${dt.kind} · ${dt.fields.length} fields · ${dt.module}</div>
        <div class="tt-row">Bases: ${dt.bases.join(', ') || 'none'}</div>
        <div class="tt-row">Methods: ${dt.methods.join(', ') || 'none'}</div>
      `;
      tooltip.style.left = (e.clientX + 16) + 'px';
      tooltip.style.top = (e.clientY - 10) + 'px';
    })
    .on('mousemove', e => {
      tooltip.style.left = (e.clientX + 16) + 'px';
      tooltip.style.top = (e.clientY - 10) + 'px';
    })
    .on('mouseleave', () => tooltip.classList.add('hidden'))
    .on('click', () => {
      // Show detail in inspector
      inspector.innerHTML = `
        <h3>Data Type</h3>
        <div class="inspector-title" style="color:${layerColor(dt.layer)}">${dt.name}</div>
        <div class="inspector-row"><span class="label">Kind</span><span class="value">${dt.kind}</span></div>
        <div class="inspector-row"><span class="label">Module</span><span class="value">${dt.module}</span></div>
        <div class="inspector-row"><span class="label">Fields</span><span class="value">${dt.fields.length}</span></div>
        <div class="inspector-row"><span class="label">Methods</span><span class="value">${dt.methods.length}</span></div>
        <div class="inspector-row"><span class="label">Bases</span><span class="value">${dt.bases.join(', ') || '-'}</span></div>
        <div style="margin-top:8px;font-size:11px;color:var(--text3)">Fields:</div>
        ${dt.fields.map(f => `<div class="inspector-row"><span class="label">${f.name}</span><span class="value" style="font-size:10px">${f.type}</span></div>`).join('')}
        <div style="margin-top:8px;font-size:11px;color:var(--text3)">Transforms:</div>
        ${transforms.filter(t => t.sourceType === dt.name || t.targetType === dt.name)
          .map(t => `<div class="inspector-row"><span class="label" style="font-size:10px">${t.sourceType} → ${t.targetType}</span><span class="value" style="font-size:9px">${t.kind}</span></div>`)
          .join('') || '<div style="font-size:11px;color:var(--text3)">none</div>'}
      `;

      // Highlight connected edges
      const connected = new Set();
      transforms.forEach(t => {
        if (t.sourceType === dt.name) connected.add(t.targetType);
        if (t.targetType === dt.name) connected.add(t.sourceType);
      });
      connected.add(dt.name);

      cardG.selectAll('.type-card').style('opacity', function() {
        const name = d3.select(this).select('text').text();
        return connected.has(name) ? 1 : 0.2;
      });

      edgeEls.attr('stroke-opacity', d => {
        return (d.sourceType === dt.name || d.targetType === dt.name) ? 0.8 : 0.08;
      }).attr('stroke-width', d => {
        return (d.sourceType === dt.name || d.targetType === dt.name) ? 2.5 : 0.8;
      });
    });
  });

  // Double-click background to reset
  svg.on('dblclick.reset', () => {
    cardG.selectAll('.type-card').style('opacity', 1);
    edgeEls.attr('stroke-opacity', null).attr('stroke-width', d => d.kind === 'endpoint' ? 2 : 1.2);
  });

  // Filter controls
  kinds.forEach(k => {
    const el = document.getElementById('dtk-' + k);
    if (el) el.addEventListener('change', applyFilters);
  });
  const showFieldsEl = document.getElementById('dtShowFields');
  const showEdgesEl = document.getElementById('dtShowEdges');
  if (showFieldsEl) showFieldsEl.addEventListener('change', applyFilters);
  if (showEdgesEl) showEdgesEl.addEventListener('change', applyFilters);

  function applyFilters() {
    const activeKinds = new Set(kinds.filter(k => document.getElementById('dtk-' + k)?.checked));
    const showFields = showFieldsEl?.checked ?? true;
    const showEdges = showEdgesEl?.checked ?? true;

    cardG.selectAll('.type-card').each(function() {
      const name = d3.select(this).select('text').text();
      const dt = typeByName.get(name);
      const visible = dt && activeKinds.has(dt.kind);
      d3.select(this).style('display', visible ? null : 'none');
      d3.select(this).selectAll('.fields-group').style('display', showFields ? null : 'none');
    });
    edgeG.style('display', showEdges ? null : 'none');
  }
}

/* ── Boot ── */
init();
})();
"""
