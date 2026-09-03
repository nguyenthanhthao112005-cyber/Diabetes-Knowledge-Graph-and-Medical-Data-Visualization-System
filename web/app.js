/* GlucoGraph — dependency-free interactive dashboard. */

const DEFAULT_TYPES = {
  Disease: { name: 'Bệnh', plural: 'Bệnh lý', color: '#0D9488' },
  Drug: { name: 'Thuốc', plural: 'Thuốc', color: '#2563EB' },
  Symptom: { name: 'Triệu chứng', plural: 'Triệu chứng', color: '#F59E0B' },
  LabTest: { name: 'Xét nghiệm', plural: 'Xét nghiệm', color: '#8B5CF6' },
  Complication: { name: 'Biến chứng', plural: 'Biến chứng', color: '#EF4444' },
  RiskFactor: { name: 'Yếu tố nguy cơ', plural: 'Yếu tố nguy cơ', color: '#F97316' },
  SideEffect: { name: 'Tác dụng phụ', plural: 'Tác dụng phụ', color: '#EC4899' },
  DrugCategory: { name: 'Nhóm thuốc', plural: 'Nhóm thuốc', color: '#14B8A6' },
};

const state = {
  nodeTypes: DEFAULT_TYPES,
  relationNames: {},
  stats: null,
  graphLabel: '',
  graphQuery: '',
  lookupLabel: '',
  lookupQuery: '',
  lookupPage: 1,
  lookupLimit: 18,
  graphRequest: 0,
  lookupRequest: 0,
};

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const fmt = (value) => new Intl.NumberFormat('vi-VN').format(Number(value || 0));
const escapeHTML = (value) => String(value ?? '')
  .replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')
  .replaceAll('"', '&quot;').replaceAll("'", '&#039;');

function typeMeta(label) {
  return state.nodeTypes[label] || { name: label || 'Thực thể', plural: label || 'Khác', color: '#64748B' };
}

function glyph(label) {
  return ({ Disease: 'ĐTĐ', Drug: 'Rx', Symptom: 'TC', LabTest: 'XN', Complication: 'BC', RiskFactor: 'NC', SideEffect: 'ADR', DrugCategory: 'NH' })[label] || 'KG';
}

function relationName(type) {
  return state.relationNames[type] || String(type || 'liên quan').toLowerCase().replaceAll('_', ' ');
}

async function fetchJSON(url) {
  const response = await fetch(url, { headers: { Accept: 'application/json' } });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
  return data;
}

let toastTimer;
function toast(message) {
  const el = $('#toast');
  el.textContent = message;
  el.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove('show'), 2800);
}

function setConnection(online, message) {
  const pill = $('#connectionPill');
  const dot = $('.status-dot', pill);
  const sideDot = $('#sideStatusDot');
  pill.classList.remove('checking');
  dot.className = `status-dot ${online ? 'online' : 'offline'}`;
  sideDot.className = `status-dot ${online ? 'online' : 'offline'}`;
  $('#connectionText').textContent = online ? 'Neo4j trực tuyến' : 'Dữ liệu snapshot';
  $('#sideStatusText').textContent = online ? 'Neo4j trực tuyến' : 'Snapshot sẵn sàng';
  pill.title = message || '';
}

function applySourceMeta(meta) {
  if (!meta) return;
  setConnection(Boolean(meta.database_online), meta.message || '');
}

function animateNumber(element, target) {
  const end = Number(target || 0);
  const startTime = performance.now();
  const duration = 650;
  function tick(now) {
    const progress = Math.min(1, (now - startTime) / duration);
    const eased = 1 - Math.pow(1 - progress, 3);
    element.textContent = fmt(Math.round(end * eased));
    if (progress < 1) requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
}

function renderStats(data) {
  state.stats = data;
  applySourceMeta(data.meta);
  animateNumber($('#metricNodes'), data.totals.nodes);
  animateNumber($('#metricEdges'), data.totals.relationships);
  animateNumber($('#metricLabels'), data.labels.length);
  animateNumber($('#metricRelTypes'), data.relationships.length);

  const total = Math.max(1, Number(data.totals.nodes));
  let angle = 0;
  const stops = data.labels.map((row) => {
    const start = angle;
    angle += (Number(row.count) / total) * 100;
    return `${typeMeta(row.label).color} ${start.toFixed(2)}% ${angle.toFixed(2)}%`;
  });
  const donut = $('#entityDonut');
  donut.style.background = `conic-gradient(${stops.join(',')})`;
  donut.innerHTML = `<div><strong>${fmt(data.totals.nodes)}</strong><span>thực thể</span></div>`;
  $('#distributionList').innerHTML = data.labels.slice(0, 8).map((row) => {
    const meta = typeMeta(row.label);
    return `<div class="dist-row"><i style="background:${meta.color}"></i><span>${escapeHTML(meta.plural)}</span><b>${fmt(row.count)}</b></div>`;
  }).join('');

  const maxRel = Math.max(...data.relationships.map((row) => Number(row.count)), 1);
  $('#relationBars').innerHTML = data.relationships.slice(0, 6).map((row, index) => {
    const width = Math.max(5, (Number(row.count) / maxRel) * 100);
    return `<div class="bar-row"><div><div class="bar-label"><span>${escapeHTML(relationName(row.type))}</span></div><div class="bar-track"><div class="bar-fill" style="width:${width}%;filter:hue-rotate(${index * 9}deg)"></div></div></div><b>${fmt(row.count)}</b></div>`;
  }).join('');

  const central = $('#centralList');
  central.innerHTML = data.top_nodes.slice(0, 8).map((node) => {
    const meta = typeMeta(node.label);
    return `<button class="central-item" data-node-id="${escapeHTML(node.id)}"><span class="central-avatar" style="--node-color:${meta.color}">${glyph(node.label)}</span><div><strong>${escapeHTML(node.name)}</strong><small>${escapeHTML(meta.name)}</small></div><span>${fmt(node.degree)} nối</span></button>`;
  }).join('');
  $$('.central-item', central).forEach((el) => el.addEventListener('click', () => openDetail(el.dataset.nodeId)));
  renderFilters();
  renderLookupTabs();
}

function renderFilters() {
  const preferred = ['Disease', 'Drug', 'Symptom', 'LabTest', 'Complication', 'RiskFactor'];
  const counts = new Map((state.stats?.labels || []).map((row) => [row.label, row.count]));
  const entries = preferred.filter((label) => counts.has(label));
  $('#graphFilters').innerHTML = [
    `<button type="button" class="filter-chip ${state.graphLabel === '' ? 'active' : ''}" data-label=""><i></i>Tất cả</button>`,
    ...entries.map((label) => {
      const meta = typeMeta(label);
      return `<button type="button" class="filter-chip ${state.graphLabel === label ? 'active' : ''}" data-label="${label}" style="--chip-color:${meta.color}"><i></i>${escapeHTML(meta.name)}</button>`;
    }),
  ].join('');
  $$('.filter-chip', $('#graphFilters')).forEach((button) => button.addEventListener('click', () => {
    state.graphLabel = button.dataset.label || '';
    renderFilters();
    loadGraph();
  }));
}

function renderLookupTabs() {
  const entries = ['', 'Drug', 'Symptom', 'LabTest', 'Complication', 'RiskFactor'];
  const counts = new Map((state.stats?.labels || []).map((row) => [row.label, row.count]));
  $('#lookupTabs').innerHTML = entries.map((label) => {
    const title = label ? typeMeta(label).plural : 'Tất cả';
    const count = label ? counts.get(label) : state.stats?.totals.nodes;
    return `<button type="button" role="tab" aria-selected="${state.lookupLabel === label}" class="lookup-tab ${state.lookupLabel === label ? 'active' : ''}" data-label="${label}">${escapeHTML(title)}<span>${fmt(count)}</span></button>`;
  }).join('');
  $$('.lookup-tab').forEach((button) => button.addEventListener('click', () => {
    state.lookupLabel = button.dataset.label || '';
    state.lookupPage = 1;
    renderLookupTabs();
    loadLookup();
  }));
}

function lookupCardDescription(node) {
  const p = node.properties || {};
  if (node.label === 'Drug') return [p.generic_name, p.concentration, p.manufacturer].filter(Boolean).join(' · ') || 'Thông tin thuốc điều trị';
  if (node.label === 'LabTest') return [p.normal_range && `Ngưỡng: ${p.normal_range}`, p.unit].filter(Boolean).join(' · ') || p.description || 'Xét nghiệm theo dõi và chẩn đoán';
  return p.description || `${typeMeta(node.label).name} trong Knowledge Graph đái tháo đường`;
}

async function loadLookup() {
  const requestId = ++state.lookupRequest;
  const grid = $('#resultGrid');
  const empty = $('#resultEmpty');
  grid.innerHTML = Array.from({ length: 6 }, () => '<div class="result-skeleton"></div>').join('');
  empty.classList.add('hidden');
  $('#pagination').innerHTML = '';
  const params = new URLSearchParams({
    q: state.lookupQuery,
    label: state.lookupLabel,
    page: state.lookupPage,
    limit: state.lookupLimit,
  });
  try {
    const data = await fetchJSON(`/api/search?${params}`);
    if (requestId !== state.lookupRequest) return;
    applySourceMeta(data.meta);
    const from = data.total ? (data.page - 1) * data.page_size + 1 : 0;
    const to = Math.min(data.total, data.page * data.page_size);
    $('#resultSummary').textContent = data.total ? `Hiển thị ${fmt(from)}–${fmt(to)} trong ${fmt(data.total)} kết quả` : 'Không có kết quả phù hợp';
    $('#resultSource').textContent = data.meta?.source === 'neo4j' ? 'Neo4j live' : 'JSON snapshot';
    if (!data.items.length) {
      grid.innerHTML = '';
      empty.classList.remove('hidden');
      return;
    }
    grid.innerHTML = data.items.map((node) => {
      const meta = typeMeta(node.label);
      return `<article class="result-card" tabindex="0" role="button" data-node-id="${escapeHTML(node.id)}" style="--node-color:${meta.color}"><div class="result-card-top"><span class="result-icon">${glyph(node.label)}</span><span class="result-degree">${fmt(node.degree)} liên kết</span></div><h3>${escapeHTML(node.name)}</h3><p>${escapeHTML(lookupCardDescription(node))}</p><span class="result-label">${escapeHTML(meta.name)}</span></article>`;
    }).join('');
    $$('.result-card', grid).forEach((card) => {
      card.addEventListener('click', () => openDetail(card.dataset.nodeId));
      card.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); openDetail(card.dataset.nodeId); }
      });
    });
    renderPagination(data.total, data.page, data.page_size);
  } catch (error) {
    if (requestId !== state.lookupRequest) return;
    grid.innerHTML = '';
    $('#resultSummary').textContent = 'Không thể tải kết quả';
    toast(error.message);
  }
}

function renderPagination(total, page, pageSize) {
  const pages = Math.ceil(total / pageSize);
  if (pages <= 1) return;
  const wanted = new Set([1, pages, page - 1, page, page + 1].filter((n) => n >= 1 && n <= pages));
  const buttons = [];
  buttons.push(`<button data-page="${page - 1}" ${page === 1 ? 'disabled' : ''}>Trước</button>`);
  let previous = 0;
  [...wanted].sort((a, b) => a - b).forEach((n) => {
    if (previous && n - previous > 1) buttons.push('<button disabled>…</button>');
    buttons.push(`<button data-page="${n}" class="${n === page ? 'active' : ''}">${n}</button>`);
    previous = n;
  });
  buttons.push(`<button data-page="${page + 1}" ${page === pages ? 'disabled' : ''}>Sau</button>`);
  const root = $('#pagination');
  root.innerHTML = buttons.join('');
  $$('button[data-page]', root).forEach((button) => button.addEventListener('click', () => {
    state.lookupPage = Number(button.dataset.page);
    loadLookup();
    $('#lookup').scrollIntoView({ behavior: 'smooth', block: 'start' });
  }));
}

class GraphRenderer {
  constructor(canvas, tooltip, onSelect) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.tooltip = tooltip;
    this.onSelect = onSelect;
    this.nodes = [];
    this.edges = [];
    this.nodeMap = new Map();
    this.neighbours = new Map();
    this.hovered = null;
    this.selected = null;
    this.scale = 1;
    this.offsetX = 0;
    this.offsetY = 0;
    this.alpha = 0;
    this.drag = null;
    this.animationFrame = null;
    this.dpr = Math.min(2, window.devicePixelRatio || 1);
    this.resizeObserver = new ResizeObserver(() => this.resize());
    this.resizeObserver.observe(canvas.parentElement);
    this.bindEvents();
    this.resize();
  }

  resize() {
    const rect = this.canvas.parentElement.getBoundingClientRect();
    this.width = Math.max(1, rect.width);
    this.height = Math.max(1, rect.height);
    this.canvas.width = Math.round(this.width * this.dpr);
    this.canvas.height = Math.round(this.height * this.dpr);
    this.canvas.style.width = `${this.width}px`;
    this.canvas.style.height = `${this.height}px`;
    if (!this.offsetX && !this.offsetY) { this.offsetX = this.width / 2; this.offsetY = this.height / 2; }
    this.draw();
  }

  hash(text) {
    let value = 2166136261;
    for (let i = 0; i < text.length; i += 1) value = Math.imul(value ^ text.charCodeAt(i), 16777619);
    return (value >>> 0) / 4294967295;
  }

  setData(nodes, edges) {
    const labels = [...new Set(nodes.map((n) => n.label))];
    const clusterCenters = new Map(labels.map((label, index) => {
      const angle = (index / Math.max(1, labels.length)) * Math.PI * 2 - Math.PI / 2;
      return [label, { x: Math.cos(angle) * 160, y: Math.sin(angle) * 125 }];
    }));
    this.nodes = nodes.map((raw, index) => {
      const center = clusterCenters.get(raw.label) || { x: 0, y: 0 };
      const angle = this.hash(raw.id) * Math.PI * 2;
      const distance = 20 + this.hash(`${raw.id}:r`) * 100;
      return {
        ...raw,
        x: center.x + Math.cos(angle) * distance,
        y: center.y + Math.sin(angle) * distance,
        vx: 0,
        vy: 0,
        radius: 4.2 + Math.min(7, Math.sqrt(Math.max(1, raw.degree)) * .52) + (raw.label === 'Disease' ? 2 : 0),
      };
    });
    this.nodeMap = new Map(this.nodes.map((node) => [node.id, node]));
    this.edges = edges.filter((edge) => this.nodeMap.has(edge.source) && this.nodeMap.has(edge.target));
    this.neighbours = new Map(this.nodes.map((node) => [node.id, new Set()]));
    this.edges.forEach((edge) => {
      this.neighbours.get(edge.source)?.add(edge.target);
      this.neighbours.get(edge.target)?.add(edge.source);
    });
    this.labelled = new Set([...this.nodes].sort((a, b) => b.degree - a.degree).slice(0, 22).map((n) => n.id));
    this.hovered = null;
    this.selected = null;
    this.alpha = 1;
    this.start();
    setTimeout(() => this.fit(), 360);
  }

  start() {
    if (this.animationFrame) return;
    const frame = () => {
      if (this.alpha > .006) this.simulate();
      this.draw();
      if (this.alpha > .006 || this.drag) this.animationFrame = requestAnimationFrame(frame);
      else this.animationFrame = null;
    };
    this.animationFrame = requestAnimationFrame(frame);
  }

  simulate() {
    const nodes = this.nodes;
    const alpha = this.alpha;
    const repulsion = nodes.length > 180 ? 1800 : 3000;
    for (let i = 0; i < nodes.length; i += 1) {
      const a = nodes[i];
      for (let j = i + 1; j < nodes.length; j += 1) {
        const b = nodes[j];
        let dx = b.x - a.x;
        let dy = b.y - a.y;
        let d2 = dx * dx + dy * dy;
        if (d2 < 1) { dx = .5; dy = .5; d2 = .5; }
        if (d2 > 28000) continue;
        const distance = Math.sqrt(d2);
        const force = Math.min(2.2, repulsion / d2) * alpha;
        const fx = (dx / distance) * force;
        const fy = (dy / distance) * force;
        a.vx -= fx; a.vy -= fy; b.vx += fx; b.vy += fy;
      }
    }
    for (const edge of this.edges) {
      const a = this.nodeMap.get(edge.source);
      const b = this.nodeMap.get(edge.target);
      const dx = b.x - a.x;
      const dy = b.y - a.y;
      const distance = Math.max(1, Math.sqrt(dx * dx + dy * dy));
      const desired = edge.type === 'CONTRAINDICATED_WITH' ? 78 : 63;
      const force = (distance - desired) * .0065 * alpha;
      const fx = (dx / distance) * force;
      const fy = (dy / distance) * force;
      a.vx += fx; a.vy += fy; b.vx -= fx; b.vy -= fy;
    }
    for (const node of nodes) {
      if (node.fx != null) { node.x = node.fx; node.y = node.fy; node.vx = 0; node.vy = 0; continue; }
      node.vx += -node.x * .0009 * alpha;
      node.vy += -node.y * .0009 * alpha;
      node.vx *= .84; node.vy *= .84;
      const speed = Math.sqrt(node.vx * node.vx + node.vy * node.vy);
      if (speed > 8) { node.vx = (node.vx / speed) * 8; node.vy = (node.vy / speed) * 8; }
      node.x += node.vx; node.y += node.vy;
    }
    this.alpha *= .973;
  }

  screen(node) { return { x: node.x * this.scale + this.offsetX, y: node.y * this.scale + this.offsetY }; }
  world(x, y) { return { x: (x - this.offsetX) / this.scale, y: (y - this.offsetY) / this.scale }; }

  drawArrow(ctx, from, to, radius, color) {
    const angle = Math.atan2(to.y - from.y, to.x - from.x);
    const x = to.x - Math.cos(angle) * (radius * this.scale + 2);
    const y = to.y - Math.sin(angle) * (radius * this.scale + 2);
    const size = 4.2;
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.lineTo(x - Math.cos(angle - .52) * size, y - Math.sin(angle - .52) * size);
    ctx.lineTo(x - Math.cos(angle + .52) * size, y - Math.sin(angle + .52) * size);
    ctx.closePath(); ctx.fillStyle = color; ctx.fill();
  }

  roundRect(ctx, x, y, width, height, radius) {
    const r = Math.min(radius, width / 2, height / 2);
    ctx.beginPath();
    ctx.moveTo(x + r, y); ctx.arcTo(x + width, y, x + width, y + height, r);
    ctx.arcTo(x + width, y + height, x, y + height, r); ctx.arcTo(x, y + height, x, y, r);
    ctx.arcTo(x, y, x + width, y, r); ctx.closePath();
  }

  draw() {
    const ctx = this.ctx;
    ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
    ctx.clearRect(0, 0, this.width, this.height);
    const focus = this.hovered || this.selected;
    const related = focus ? this.neighbours.get(focus.id) || new Set() : null;

    ctx.lineWidth = .7;
    for (const edge of this.edges) {
      const a = this.nodeMap.get(edge.source);
      const b = this.nodeMap.get(edge.target);
      if (!a || !b) continue;
      const sa = this.screen(a); const sb = this.screen(b);
      const connected = !focus || a.id === focus.id || b.id === focus.id;
      ctx.strokeStyle = connected ? (focus ? 'rgba(44,105,97,.43)' : 'rgba(70,117,110,.15)') : 'rgba(92,123,117,.035)';
      ctx.lineWidth = connected && focus ? 1.25 : .65;
      ctx.beginPath(); ctx.moveTo(sa.x, sa.y); ctx.lineTo(sb.x, sb.y); ctx.stroke();
      if (focus && connected) this.drawArrow(ctx, sa, sb, b.radius, 'rgba(41,103,94,.62)');
    }

    const ordered = [...this.nodes].sort((a, b) => (a === focus) - (b === focus));
    for (const node of ordered) {
      const p = this.screen(node);
      if (p.x < -35 || p.y < -35 || p.x > this.width + 35 || p.y > this.height + 35) continue;
      const meta = typeMeta(node.label);
      const radius = Math.max(2.7, node.radius * this.scale);
      const dimmed = focus && node.id !== focus.id && !related.has(node.id);
      ctx.globalAlpha = dimmed ? .19 : 1;
      if (node === focus) {
        ctx.beginPath(); ctx.arc(p.x, p.y, radius + 8, 0, Math.PI * 2);
        ctx.fillStyle = `${meta.color}1F`; ctx.fill();
        ctx.beginPath(); ctx.arc(p.x, p.y, radius + 3, 0, Math.PI * 2);
        ctx.strokeStyle = `${meta.color}80`; ctx.lineWidth = 1.4; ctx.stroke();
      }
      ctx.beginPath(); ctx.arc(p.x, p.y, radius, 0, Math.PI * 2);
      ctx.fillStyle = meta.color; ctx.shadowColor = `${meta.color}55`; ctx.shadowBlur = node === focus ? 12 : 4; ctx.fill();
      ctx.shadowBlur = 0; ctx.strokeStyle = 'rgba(255,255,255,.9)'; ctx.lineWidth = Math.max(1, this.scale * 1.2); ctx.stroke();
      if (radius > 7.2) {
        ctx.fillStyle = 'rgba(255,255,255,.95)'; ctx.font = `800 ${Math.min(7.5, radius * .58)}px Manrope, sans-serif`;
        ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText(glyph(node.label), p.x, p.y + .3);
      }
      const showLabel = node === focus || (this.scale > .72 && this.labelled.has(node.id));
      if (showLabel) {
        const name = node.name.length > 30 ? `${node.name.slice(0, 29)}…` : node.name;
        ctx.font = `${node === focus ? 700 : 600} ${node === focus ? 9 : 8}px Manrope, sans-serif`;
        const textWidth = ctx.measureText(name).width;
        const lx = p.x - textWidth / 2 - 5; const ly = p.y + radius + 5;
        this.roundRect(ctx, lx, ly, textWidth + 10, 17, 5);
        ctx.fillStyle = node === focus ? 'rgba(16,52,49,.94)' : 'rgba(255,255,255,.88)'; ctx.fill();
        ctx.fillStyle = node === focus ? '#fff' : '#365852'; ctx.textBaseline = 'middle'; ctx.fillText(name, p.x, ly + 8.7);
      }
      ctx.globalAlpha = 1;
    }
  }

  point(event) {
    const rect = this.canvas.getBoundingClientRect();
    return { x: event.clientX - rect.left, y: event.clientY - rect.top };
  }

  pick(x, y) {
    let best = null; let bestDistance = Infinity;
    for (const node of this.nodes) {
      const p = this.screen(node);
      const distance = Math.hypot(p.x - x, p.y - y);
      if (distance < node.radius * this.scale + 9 && distance < bestDistance) { best = node; bestDistance = distance; }
    }
    return best;
  }

  bindEvents() {
    this.canvas.addEventListener('pointerdown', (event) => {
      const p = this.point(event);
      const node = this.pick(p.x, p.y);
      this.canvas.setPointerCapture?.(event.pointerId);
      this.drag = { node, startX: p.x, startY: p.y, x: p.x, y: p.y, offsetX: this.offsetX, offsetY: this.offsetY, moved: false };
      if (node) { node.fx = node.x; node.fy = node.y; this.alpha = Math.max(this.alpha, .14); this.start(); }
    });
    this.canvas.addEventListener('pointermove', (event) => {
      const p = this.point(event);
      if (this.drag) {
        if (Math.hypot(p.x - this.drag.startX, p.y - this.drag.startY) > 4) this.drag.moved = true;
        if (this.drag.node) {
          const w = this.world(p.x, p.y); this.drag.node.fx = w.x; this.drag.node.fy = w.y;
        } else {
          this.offsetX = this.drag.offsetX + p.x - this.drag.startX;
          this.offsetY = this.drag.offsetY + p.y - this.drag.startY;
        }
        this.draw(); return;
      }
      const node = this.pick(p.x, p.y);
      if (node !== this.hovered) { this.hovered = node; this.canvas.style.cursor = node ? 'pointer' : 'grab'; this.draw(); }
      if (node) {
        const meta = typeMeta(node.label);
        this.tooltip.innerHTML = `<strong>${escapeHTML(node.name)}</strong><span>${escapeHTML(meta.name)} · ${fmt(node.degree)} liên kết</span>`;
        this.tooltip.style.left = `${Math.min(p.x, this.width - 245)}px`;
        this.tooltip.style.top = `${Math.min(p.y, this.height - 70)}px`;
        this.tooltip.classList.remove('hidden');
      } else this.tooltip.classList.add('hidden');
    });
    const release = () => {
      if (!this.drag) return;
      if (this.drag.node) {
        const node = this.drag.node;
        node.x = node.fx; node.y = node.fy; node.fx = null; node.fy = null;
        if (!this.drag.moved) { this.selected = node; this.onSelect(node); }
      }
      this.drag = null; this.draw();
    };
    this.canvas.addEventListener('pointerup', release);
    this.canvas.addEventListener('pointercancel', release);
    this.canvas.addEventListener('pointerleave', () => { if (!this.drag) { this.hovered = null; this.tooltip.classList.add('hidden'); this.draw(); } });
    this.canvas.addEventListener('wheel', (event) => {
      event.preventDefault();
      const p = this.point(event);
      this.zoomAt(event.deltaY < 0 ? 1.12 : .89, p.x, p.y);
    }, { passive: false });
  }

  zoomAt(factor, x = this.width / 2, y = this.height / 2) {
    const oldScale = this.scale;
    const newScale = Math.max(.2, Math.min(3.2, oldScale * factor));
    this.offsetX = x - ((x - this.offsetX) / oldScale) * newScale;
    this.offsetY = y - ((y - this.offsetY) / oldScale) * newScale;
    this.scale = newScale; this.draw();
  }

  fit() {
    if (!this.nodes.length) return;
    const xs = this.nodes.map((n) => n.x); const ys = this.nodes.map((n) => n.y);
    const minX = Math.min(...xs); const maxX = Math.max(...xs); const minY = Math.min(...ys); const maxY = Math.max(...ys);
    this.scale = Math.max(.28, Math.min(1.55, Math.min((this.width - 100) / Math.max(120, maxX - minX), (this.height - 100) / Math.max(120, maxY - minY))));
    this.offsetX = this.width / 2 - ((minX + maxX) / 2) * this.scale;
    this.offsetY = this.height / 2 - ((minY + maxY) / 2) * this.scale;
    this.draw();
  }
}

const graph = new GraphRenderer($('#graphCanvas'), $('#graphTooltip'), (node) => openDetail(node.id));

function renderLegend(nodes) {
  const labels = [...new Set(nodes.map((node) => node.label))];
  $('#graphLegend').innerHTML = labels.map((label) => `<span class="legend-item"><i style="background:${typeMeta(label).color}"></i>${escapeHTML(typeMeta(label).name)}</span>`).join('');
}

async function loadGraph() {
  const requestId = ++state.graphRequest;
  const loading = $('#graphLoading');
  const empty = $('#graphEmpty');
  loading.classList.remove('hidden'); empty.classList.add('hidden');
  const params = new URLSearchParams({ q: state.graphQuery, label: state.graphLabel, limit: 160, edge_limit: 750 });
  try {
    const data = await fetchJSON(`/api/graph?${params}`);
    if (requestId !== state.graphRequest) return;
    applySourceMeta(data.meta);
    graph.setData(data.nodes, data.edges);
    renderLegend(data.nodes);
    $('#graphCount').textContent = `${fmt(data.nodes.length)} node · ${fmt(data.edges.length)} cạnh`;
    empty.classList.toggle('hidden', data.nodes.length > 0);
  } catch (error) {
    if (requestId !== state.graphRequest) return;
    graph.setData([], []); renderLegend([]);
    $('#graphCount').textContent = 'Không có dữ liệu';
    empty.classList.remove('hidden');
    toast(error.message);
  } finally {
    if (requestId === state.graphRequest) loading.classList.add('hidden');
  }
}

const propertyLabels = {
  generic_name: 'Hoạt chất', dosage_form: 'Dạng bào chế', concentration: 'Hàm lượng',
  manufacturer: 'Nhà sản xuất', prescription: 'Kê đơn', specification: 'Quy cách', sku: 'Mã sản phẩm',
  normal_range: 'Ngưỡng tham chiếu', unit: 'Đơn vị', severity: 'Mức độ', icd_code: 'Mã ICD', price: 'Giá',
};

function closeDrawer() {
  $('#detailDrawer').classList.remove('open');
  $('#drawerBackdrop').classList.remove('open');
  $('#detailDrawer').setAttribute('aria-hidden', 'true');
}

async function openDetail(nodeId) {
  const drawer = $('#detailDrawer');
  drawer.classList.add('open'); $('#drawerBackdrop').classList.add('open'); drawer.setAttribute('aria-hidden', 'false');
  $('#drawerType').textContent = 'Đang tải';
  $('#drawerContent').innerHTML = '<div class="drawer-loading"><span></span><span></span><span></span><span></span></div>';
  try {
    const data = await fetchJSON(`/api/nodes/${encodeURIComponent(nodeId)}`);
    applySourceMeta(data.meta);
    const node = data.node; const props = node.properties || {}; const meta = typeMeta(node.label);
    drawer.style.setProperty('--detail-color', meta.color);
    $('#drawerType').textContent = meta.name;
    const description = props.description || lookupCardDescription(node);
    const omitted = new Set(['name', 'description', 'source_url']);
    const properties = Object.entries(props).filter(([key, value]) => !omitted.has(key) && value !== '' && value != null);
    const source = typeof props.source_url === 'string' && /^https?:\/\//.test(props.source_url) ? props.source_url : '';
    $('#drawerContent').innerHTML = `
      <div class="drawer-hero"><span class="drawer-avatar" style="--node-color:${meta.color}">${glyph(node.label)}</span><h2>${escapeHTML(node.name)}</h2><p>${escapeHTML(description)}</p></div>
      ${properties.length ? `<section class="drawer-section"><h3>Thông tin chi tiết</h3><div class="property-grid">${properties.map(([key, value]) => `<div class="property-row"><span>${escapeHTML(propertyLabels[key] || key.replaceAll('_', ' '))}</span><strong>${escapeHTML(Array.isArray(value) ? value.join(', ') : value)}</strong></div>`).join('')}</div>${source ? `<a class="source-link" href="${escapeHTML(source)}" target="_blank" rel="noopener noreferrer"><span>Xem nguồn dữ liệu</span><svg><use href="#i-external"/></svg></a>` : ''}</section>` : (source ? `<a class="source-link" href="${escapeHTML(source)}" target="_blank" rel="noopener noreferrer"><span>Xem nguồn dữ liệu</span><svg><use href="#i-external"/></svg></a>` : '')}
      <section class="drawer-section"><h3>Liên kết (${fmt(data.related.length)})</h3><div class="related-list">${data.related.length ? data.related.slice(0, 35).map((item) => { const relatedMeta = typeMeta(item.node.label); return `<button class="related-item" data-node-id="${escapeHTML(item.node.id)}" style="border-color:#e5ece9;width:100%;text-align:left"><span class="related-avatar" style="--node-color:${relatedMeta.color}">${glyph(item.node.label)}</span><div><strong>${escapeHTML(item.node.name)}</strong><small>${item.direction === 'in' ? '←' : '→'} ${escapeHTML(relationName(item.edge.type))}</small></div><svg><use href="#i-chevron"/></svg></button>`; }).join('') : '<p style="color:#879b97;font-size:9px">Chưa có liên kết trực tiếp.</p>'}</div></section>`;
    $$('.related-item', $('#drawerContent')).forEach((item) => item.addEventListener('click', () => openDetail(item.dataset.nodeId)));
  } catch (error) {
    $('#drawerType').textContent = 'Có lỗi';
    $('#drawerContent').innerHTML = `<div class="result-empty"><span>!</span><h3>Không tải được chi tiết</h3><p>${escapeHTML(error.message)}</p></div>`;
  }
}

async function loadHealth() {
  try {
    const data = await fetchJSON('/api/health');
    setConnection(Boolean(data.database.online), data.database.message);
  } catch (_error) {
    setConnection(false, 'Không thể kết nối máy chủ ứng dụng');
  }
}

async function loadStats() {
  try { renderStats(await fetchJSON('/api/stats')); }
  catch (error) { toast(`Không tải được thống kê: ${error.message}`); }
}

async function refreshAll() {
  $$('#refreshAll svg, #mobileRefresh svg, #reloadGraph svg').forEach((icon) => { icon.style.animation = 'rotate .8s linear infinite'; });
  await loadHealth();
  await Promise.allSettled([loadStats(), loadGraph(), loadLookup()]);
  $$('#refreshAll svg, #mobileRefresh svg, #reloadGraph svg').forEach((icon) => { icon.style.animation = ''; });
  toast('Dữ liệu đã được làm mới');
}

function bindUI() {
  $('#graphSearchForm').addEventListener('submit', (event) => {
    event.preventDefault(); state.graphQuery = $('#graphSearch').value.trim(); loadGraph();
  });
  $('#lookupForm').addEventListener('submit', (event) => {
    event.preventDefault(); state.lookupQuery = $('#lookupInput').value.trim(); state.lookupPage = 1; loadLookup();
  });
  let lookupTimer;
  $('#lookupInput').addEventListener('input', () => {
    clearTimeout(lookupTimer);
    lookupTimer = setTimeout(() => { state.lookupQuery = $('#lookupInput').value.trim(); state.lookupPage = 1; loadLookup(); }, 380);
  });
  $('#fitGraph').addEventListener('click', () => graph.fit());
  $('#zoomIn').addEventListener('click', () => graph.zoomAt(1.2));
  $('#zoomOut').addEventListener('click', () => graph.zoomAt(.82));
  $('#reloadGraph').addEventListener('click', loadGraph);
  $('#refreshAll').addEventListener('click', refreshAll);
  $('#mobileRefresh').addEventListener('click', refreshAll);
  $('#closeDrawer').addEventListener('click', closeDrawer);
  $('#drawerBackdrop').addEventListener('click', closeDrawer);
  document.addEventListener('keydown', (event) => { if (event.key === 'Escape') closeDrawer(); });

  const navLinks = $$('.nav-link, .mobile-nav a');
  navLinks.forEach((link) => link.addEventListener('click', () => {
    navLinks.forEach((item) => item.classList.toggle('active', item.getAttribute('href') === link.getAttribute('href')));
  }));
  const sections = ['overview', 'explore', 'lookup', 'insights'].map((id) => document.getElementById(id)).filter(Boolean);
  const observer = new IntersectionObserver((entries) => {
    const visible = entries.filter((entry) => entry.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
    if (!visible) return;
    const href = `#${visible.target.id}`;
    navLinks.forEach((link) => link.classList.toggle('active', link.getAttribute('href') === href));
  }, { rootMargin: '-20% 0px -55%', threshold: [0, .2, .5] });
  sections.forEach((section) => observer.observe(section));
}

async function init() {
  bindUI();
  try {
    const config = await fetchJSON('/api/config');
    state.nodeTypes = config.node_types || DEFAULT_TYPES;
    state.relationNames = config.relation_names || {};
  } catch (_error) { /* Defaults keep the interface usable. */ }
  await loadHealth();
  await Promise.allSettled([loadStats(), loadGraph(), loadLookup()]);
}

init();
