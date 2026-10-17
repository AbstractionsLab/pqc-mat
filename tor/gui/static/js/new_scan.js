let _selectedProtocol = 'tls';
let _sourceMode = 'local';
let _selectedFiles = [];

const SOURCE_SKIP_SEGMENTS = new Set(['.git', 'node_modules', '__pycache__', '.venv', 'venv', '.tox', '.mypy_cache']);

function _skipUploadPath(relPath) {
  return relPath.split('/').some(seg => SOURCE_SKIP_SEGMENTS.has(seg));
}

function switchSourceMode(mode) {
  _sourceMode = mode;
  document.getElementById('source-mode-local').classList.toggle('proto-btn--active', mode === 'local');
  document.getElementById('source-mode-github').classList.toggle('proto-btn--active', mode === 'github');
  document.getElementById('source-panel-local').style.display  = mode === 'local'  ? '' : 'none';
  document.getElementById('source-panel-github').style.display = mode === 'github' ? '' : 'none';
  document.getElementById('code-error').textContent = '';
}

document.getElementById('code-source-files').addEventListener('change', (e) => {
  _selectedFiles = Array.from(e.target.files).filter(f => !_skipUploadPath(f.webkitRelativePath || f.name));
  const summary = document.getElementById('code-folder-summary');
  if (_selectedFiles.length === 0) {
    summary.textContent = 'No folder selected';
  } else {
    const root = (_selectedFiles[0].webkitRelativePath || '').split('/')[0] || 'folder';
    summary.textContent = root + ' — ' + _selectedFiles.length + ' file' + (_selectedFiles.length === 1 ? '' : 's') + ' selected';
  }
});

function switchScanType(type) {
  document.querySelectorAll('.scan-type-btn').forEach(b => b.classList.remove('scan-type-btn--active'));
  document.querySelector('[data-type="' + type + '"]').classList.add('scan-type-btn--active');
  document.getElementById('form-code').style.display = type === 'code'    ? '' : 'none';
  document.getElementById('form-network').style.display = type === 'network' ? '' : 'none';
}

function selectProtocol(proto) {
  _selectedProtocol = proto;
  document.getElementById('proto-tls').classList.toggle('proto-btn--active', proto === 'tls');
  document.getElementById('proto-ssh').classList.toggle('proto-btn--active', proto === 'ssh');
  document.getElementById('net-port').value = proto === 'tls' ? '443' : '22';
}

async function submitCodeScan() {
  const appName = document.getElementById('code-appname').value.trim();
  const errEl = document.getElementById('code-error');
  const btn = document.getElementById('code-submit-btn');

  errEl.textContent = '';

  let fetchOptions;
  if (_sourceMode === 'local') {
    if (_selectedFiles.length === 0) { errEl.textContent = 'Choose a folder to scan.'; return; }
    const formData = new FormData();
    formData.append('app_name', appName || 'application');
    _selectedFiles.forEach(f => formData.append('files', f, f.webkitRelativePath || f.name));
    fetchOptions = { method: 'POST', body: formData };
  } else {
    const source = document.getElementById('code-source').value.trim();
    if (!source) { errEl.textContent = 'GitHub URL is required.'; return; }
    fetchOptions = {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ source, app_name: appName || 'application' }),
    };
  }

  btn.disabled = true;
  btn.textContent = 'Submitting…';

  try {
    const r = await fetch('/api/scan/code', fetchOptions);
    const data = await r.json();
    if (data.ok) {
      window.location.href = '/scan/' + data.scan_id;
    } else {
      errEl.textContent = data.error || 'Submission failed.';
      btn.disabled = false;
      btn.textContent = 'Start scan';
    }
  } catch (e) {
    errEl.textContent = 'Network error — is the server running?';
    btn.disabled = false;
    btn.textContent = 'Start scan';
  }
}

async function submitNetworkScan() {
  const target = document.getElementById('net-target').value.trim();
  const port = parseInt(document.getElementById('net-port').value, 10);
  const errEl = document.getElementById('net-error');
  const btn = document.getElementById('net-submit-btn');

  errEl.textContent = '';
  if (!target) { errEl.textContent = 'Target is required.'; return; }
  if (!port || port < 1 || port > 65535) { errEl.textContent = 'Port must be between 1 and 65535.'; return; }

  btn.disabled    = true;
  btn.textContent = 'Submitting…';

  try {
    const r = await fetch('/api/scan/network', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ protocol: _selectedProtocol, target, port }),
    });
    const data = await r.json();
    if (data.ok) {
      window.location.href = '/scan/' + data.scan_id;
    } else {
      errEl.textContent = data.error || 'Submission failed.';
      btn.disabled = false;
      btn.textContent = 'Start scan';
    }
  } catch (e) {
    errEl.textContent = 'Network error — is the server running?';
    btn.disabled = false;
    btn.textContent = 'Start scan';
  }
}