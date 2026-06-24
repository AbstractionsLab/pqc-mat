const SCAN_ID      = window.VECTOR_SCAN_ID;
const _startTime   = new Date(window.VECTOR_SUBMITTED_AT);

const TYPE_LABEL = {
  'code':          'VECTOR-Code',
  'network-tls':   'VECTOR-Network · TLS',
  'network-ssh':   'VECTOR-Network · SSH',
};

let _linesShown   = 0;
let _pollTimer    = null;
let _elapsedTimer = null;
let _finished     = false;
let _redirected   = false;

function fmtElapsed(ms) {
  const s = Math.floor(ms / 1000);
  if (s < 60) return s + 's';
  return Math.floor(s / 60) + 'm ' + (s % 60) + 's';
}

function updateElapsed() {
  if (_finished) return;
  const el = document.getElementById('elapsed');
  if (el) el.textContent = fmtElapsed(Date.now() - _startTime);
}

function appendLines(lines) {
  const inner = document.getElementById('log-inner');
  lines.forEach(line => {
    const div = document.createElement('div');
    div.className = 'log-line';
    if (line.startsWith('✓'))           div.classList.add('log-line--ok');
    else if (line.startsWith('✗') || /\berror\b/i.test(line)) div.classList.add('log-line--err');
    else if (/\bwarning\b/i.test(line)) div.classList.add('log-line--warn');
    div.textContent = line;
    inner.appendChild(div);
  });
  const container = document.getElementById('log-container');
  container.scrollTop = container.scrollHeight;
  const count = document.getElementById('log-lines-count');
  if (count) count.textContent = inner.childElementCount + ' lines';
}

function setStatusStrip(status, error) {
  const strip   = document.getElementById('status-strip');
  const text    = document.getElementById('status-text');
  const spinner = strip.querySelector('.spin');
  strip.className = 'strip';

  if (status === 'pending' || status === 'running') {
    strip.classList.add('strip--blue');
    text.textContent = status === 'pending' ? 'Waiting to start…' : 'Scan in progress…';
    if (spinner) spinner.style.display = '';
  } else if (status === 'done') {
    strip.classList.add('strip--green');
    text.textContent = 'Scan complete — loading results…';
    if (spinner) spinner.style.display = 'none';
    document.getElementById('elapsed').textContent = '';
  } else if (status === 'failed') {
    strip.classList.add('strip--red');
    text.textContent = 'Scan failed.';
    if (spinner) spinner.style.display = 'none';
    if (error) {
      document.getElementById('error-panel').style.display = '';
      document.getElementById('error-msg').textContent = error;
    }
    document.getElementById('elapsed').textContent = '';
  }
}

function setStatusBadge(status) {
  const cls = { pending: 'badge--amber', running: 'badge--blue', done: 'badge--green', failed: 'badge--red' };
  const el  = document.getElementById('dt-status');
  if (el) el.innerHTML = '<span class="badge ' + (cls[status] || 'badge--gray') + '">' + status + '</span>';
}

async function poll() {
  try {
    const r    = await fetch('/api/scan/' + SCAN_ID + '?since=' + _linesShown);
    const data = await r.json();
    if (!data.ok) return;

    const tl = TYPE_LABEL[data.type] || data.type;
    document.getElementById('ph-title').textContent   = tl;
    document.getElementById('ph-sub').textContent     = data.target;
    document.getElementById('dt-type').textContent    = tl;
    document.getElementById('dt-target').textContent  = data.target;
    document.getElementById('dt-appname').textContent = data.app_name;

    appendLines(data.output_lines);
    _linesShown = data.output_total;
    setStatusStrip(data.status, data.error);
    setStatusBadge(data.status);

    if (data.status === 'done' && !_redirected) {
      _finished   = true;
      _redirected = true;
      clearTimeout(_pollTimer);
      clearInterval(_elapsedTimer);
      setTimeout(() => { window.location.href = '/results/' + SCAN_ID; }, 800);
    } else if (data.status === 'failed') {
      _finished = true;
      clearTimeout(_pollTimer);
      clearInterval(_elapsedTimer);
    } else {
      _pollTimer = setTimeout(poll, 1200);
    }
  } catch (e) {
    _pollTimer = setTimeout(poll, 3000);
  }
}

_elapsedTimer = setInterval(updateElapsed, 1000);
poll();