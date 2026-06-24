const CBOM_DATA = window.VECTOR_CBOM;

const RISK_COLORS = {
  'quantum-vulnerable':    '#dc2626',
  'classically-deprecated':'#f97316',
  'non-hybrid':            '#d97706',
  'quantum-safe':          '#16a34a',
  'hybrid':                '#2563eb',
  'unknown':               '#94a3b8',
};

const RISK_DISPLAY = {
  'quantum-vulnerable':    'Quantum vulnerable',
  'classically-deprecated':'Classically deprecated',
  'non-hybrid':            'Non-hybrid',
  'quantum-safe':          'Quantum safe',
  'hybrid':                'Hybrid',
  'unknown':               'Unknown',
};

function switchTab(name) {
  document.querySelectorAll('.subnav__item').forEach(el => {
    el.classList.toggle('subnav__item--active', el.dataset.tab === name);
  });
  document.querySelectorAll('.tab-panel').forEach(el => {
    el.style.display = el.id === 'tab-' + name ? '' : 'none';
  });
}

function filterCbom(classification, btn) {
  document.querySelectorAll('.filter-bar .pill').forEach(b => b.classList.remove('pill--active'));
  btn.classList.add('pill--active');
  document.querySelectorAll('#cbom-grid .cbom-card').forEach(card => {
    card.style.display = (classification === 'all' || card.dataset.classification === classification) ? '' : 'none';
  });
}

function buildPieChart(cbom) {
  const canvas = document.getElementById('risk-pie');
  const legend = document.getElementById('risk-legend');
  if (!canvas || !legend) return;

  const components = (cbom.components || []).filter(c =>
    c.cryptoProperties && c.cryptoProperties.assetType === 'algorithm'
  );
  if (components.length === 0) {
    canvas.parentElement.style.display = 'none';
    return;
  }

  const counts = {};
  components.forEach(comp => {
    const props = comp.properties || [];
    const p = props.find(x => x.name === 'pqcmat:risk-classification');
    const cls = p ? p.value : 'unknown';
    counts[cls] = (counts[cls] || 0) + 1;
  });

  const order = ['quantum-vulnerable', 'classically-deprecated', 'non-hybrid', 'unknown', 'quantum-safe', 'hybrid'];
  const slices = order.filter(k => counts[k] > 0).map(k => ({
    label: k, count: counts[k], color: RISK_COLORS[k] || '#94a3b8',
    _startAngle: 0, _endAngle: 0,
  }));
  const total = slices.reduce((s, x) => s + x.count, 0);

  const ctx = canvas.getContext('2d');
  const cx = canvas.width  / 2;
  const cy = canvas.height / 2;
  const r = 78;
  const ri = 44;
  let hovered = -1;

  function computeAngles() {
    let a = -Math.PI / 2;
    slices.forEach(sl => {
      sl._startAngle = a;
      sl._endAngle   = a + (sl.count / total) * 2 * Math.PI;
      a = sl._endAngle;
    });
  }

  function draw(hovIdx) {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    computeAngles();
    slices.forEach((sl, i) => {
      const sweep = sl._endAngle - sl._startAngle;
      const push  = i === hovIdx ? 6 : 0;
      const mid   = sl._startAngle + sweep / 2;
      ctx.beginPath();
      ctx.moveTo(cx + Math.cos(mid) * push, cy + Math.sin(mid) * push);
      ctx.arc(cx + Math.cos(mid) * push, cy + Math.sin(mid) * push, r,  sl._startAngle, sl._endAngle);
      ctx.arc(cx + Math.cos(mid) * push, cy + Math.sin(mid) * push, ri, sl._endAngle,   sl._startAngle, true);
      ctx.closePath();
      ctx.fillStyle = sl.color;
      ctx.fill();
      if (i === hovIdx) { ctx.strokeStyle = '#fff'; ctx.lineWidth = 2; ctx.stroke(); }
    });
    ctx.fillStyle = '#0f172a'; ctx.font = 'bold 22px Inter, system-ui, sans-serif';
    ctx.textAlign = 'center';  ctx.textBaseline = 'middle';
    ctx.fillText(total, cx, cy - 8);
    ctx.font = '11px Inter, system-ui, sans-serif'; ctx.fillStyle = '#94a3b8';
    ctx.fillText('algorithms', cx, cy + 12);
  }

  computeAngles();
  draw(-1);

  canvas.addEventListener('mousemove', e => {
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left - cx;
    const my = e.clientY - rect.top  - cy;
    const dist = Math.sqrt(mx * mx + my * my);
    if (dist < ri || dist > r + 6) { if (hovered !== -1) { hovered = -1; draw(-1); } return; }
    let ang = Math.atan2(my, mx);
    if (ang < -Math.PI / 2) ang += 2 * Math.PI;
    const idx = slices.findIndex(sl => ang >= sl._startAngle + Math.PI / 2 && ang < sl._endAngle + Math.PI / 2);
    if (idx !== hovered) { hovered = idx; draw(idx); }
  });
  canvas.addEventListener('mouseleave', () => { hovered = -1; draw(-1); });

  slices.forEach(sl => {
    const pct  = Math.round((sl.count / total) * 100);
    const item = document.createElement('div');
    item.className = 'legend-item';
    item.innerHTML =
      '<span class="legend-dot" style="background:' + sl.color + '"></span>' +
      '<span class="legend-label">' + (RISK_DISPLAY[sl.label] || sl.label) + '</span>' +
      '<span class="legend-count">' + sl.count + '</span>' +
      '<span class="legend-pct">' + pct + '%</span>';
    legend.appendChild(item);
  });
}

if (CBOM_DATA) {
  buildPieChart(CBOM_DATA);
}