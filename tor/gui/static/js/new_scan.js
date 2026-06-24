let _selectedProtocol = 'tls';

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
  const source = document.getElementById('code-source').value.trim();
  const appName = document.getElementById('code-appname').value.trim();
  const errEl = document.getElementById('code-error');
  const btn = document.getElementById('code-submit-btn');

  errEl.textContent = '';
  if (!source) { errEl.textContent = 'Source path or GitHub URL is required.'; return; }

  btn.disabled = true;
  btn.textContent = 'Submitting…';

  try {
    const r = await fetch('/api/scan/code', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ source, app_name: appName || 'application' }),
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