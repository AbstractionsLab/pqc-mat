/* main.js — VECTOR Web Interface shared utilities */

function showToast(msg, type /* ok | warn | fail */, duration) {
  duration = duration || 3500;
  const host = document.getElementById('global-toast-host');
  if (!host) return;

  const el = document.createElement('div');
  el.className = `toast toast--${type}`;
  el.textContent = msg;
  host.appendChild(el);

  setTimeout(() => {
    el.classList.add('toast--out');
    setTimeout(() => el.remove(), 400);
  }, duration);
}
