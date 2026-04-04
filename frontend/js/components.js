// ── Status / Priority / Severity Badges ──────────────────────────────────────

const STATUS_COLORS = {
  pending:     'bg-slate-700 text-slate-300',
  matching:    'bg-blue-900 text-blue-300',
  assigned:    'bg-indigo-900 text-indigo-300',
  in_progress: 'bg-yellow-900 text-yellow-300',
  completed:   'bg-green-900 text-green-300',
  at_risk:     'bg-orange-900 text-orange-300',
  rescheduled: 'bg-purple-900 text-purple-300',
  cancelled:   'bg-red-900 text-red-400',
};

const PRIORITY_COLORS = {
  low:      'bg-slate-700 text-slate-400',
  medium:   'bg-blue-900 text-blue-300',
  high:     'bg-orange-900 text-orange-300',
  critical: 'bg-red-900 text-red-400',
};

const SEVERITY_COLORS = {
  low:      'bg-green-900 text-green-300',
  medium:   'bg-yellow-900 text-yellow-300',
  high:     'bg-orange-900 text-orange-300',
  critical: 'bg-red-900 text-red-400',
};

const AVAILABILITY_COLORS = {
  available:   'bg-green-900 text-green-300',
  busy:        'bg-yellow-900 text-yellow-300',
  unavailable: 'bg-red-900 text-red-400',
};

const AGENT_COLORS = {
  project_manager: 'bg-indigo-900 text-indigo-200',
  matching:        'bg-blue-900 text-blue-200',
  communication:   'bg-green-900 text-green-200',
  risk:            'bg-orange-900 text-orange-200',
  rescheduling:    'bg-purple-900 text-purple-200',
  base:            'bg-slate-700 text-slate-300',
};

export function badge(text, colorClass) {
  return `<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${colorClass}">${text}</span>`;
}

export function statusBadge(status) {
  return badge(status.replace(/_/g, ' '), STATUS_COLORS[status] || 'bg-slate-700 text-slate-300');
}

export function priorityBadge(priority) {
  return badge(priority, PRIORITY_COLORS[priority] || 'bg-slate-700 text-slate-300');
}

export function severityBadge(severity) {
  const extra = severity === 'critical' ? ' animate-pulse' : '';
  return `<span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold ${SEVERITY_COLORS[severity] || ''}${extra}">
    ${severity === 'critical' ? '<span class="pulse-dot" style="background:currentColor"></span>' : ''}
    ${severity}
  </span>`;
}

export function availabilityBadge(status) {
  return badge(status, AVAILABILITY_COLORS[status] || 'bg-slate-700 text-slate-300');
}

export function agentChip(name) {
  const label = name.replace(/_/g, ' ');
  return `<span class="agent-chip ${AGENT_COLORS[name] || 'bg-slate-700 text-slate-300'}">${label}</span>`;
}

export function ratingStars(rating) {
  const full = Math.floor(rating);
  const half = rating - full >= 0.5;
  let html = '';
  for (let i = 0; i < 5; i++) {
    if (i < full) html += '<span class="text-yellow-400">★</span>';
    else if (i === full && half) html += '<span class="text-yellow-600">★</span>';
    else html += '<span class="text-slate-600">★</span>';
  }
  return `<span class="text-sm">${html} <span class="text-slate-400 ml-1">${rating.toFixed(1)}</span></span>`;
}

export function skillChips(skills) {
  if (!skills || !skills.length) return '<span class="text-slate-500 text-xs">—</span>';
  return skills.map(s => `<span class="skill-chip">${s}</span>`).join('');
}

export function formatDate(str) {
  if (!str) return '—';
  try {
    return new Date(str).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  } catch { return str; }
}

export function formatDateTime(str) {
  if (!str) return '—';
  try {
    return new Date(str).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' });
  } catch { return str; }
}

export function timeAgo(str) {
  if (!str) return '';
  const diff = Date.now() - new Date(str).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return 'just now';
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

// ── Toast ─────────────────────────────────────────────────────────────────────

export function toast(message, type = 'success') {
  const colors = {
    success: 'bg-green-900 border border-green-700 text-green-100',
    error:   'bg-red-900 border border-red-700 text-red-100',
    info:    'bg-indigo-900 border border-indigo-700 text-indigo-100',
  };
  const icon = { success: '✓', error: '✕', info: 'ℹ' }[type] || '•';
  const el = document.createElement('div');
  el.className = `toast ${colors[type] || colors.info}`;
  el.innerHTML = `<div class="flex items-start gap-3"><span class="text-lg font-bold">${icon}</span><div>${message}</div></div>`;
  document.getElementById('toast-container').appendChild(el);
  setTimeout(() => el.remove(), 5000);
}

// ── Modal ─────────────────────────────────────────────────────────────────────

export function showModal(html, onClose) {
  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.innerHTML = `<div class="modal">${html}</div>`;
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) { overlay.remove(); onClose && onClose(); }
  });
  document.body.appendChild(overlay);
  return overlay;
}

// ── Loading overlay ───────────────────────────────────────────────────────────

export function showAgentOverlay(jobTitle) {
  const el = document.createElement('div');
  el.id = 'agent-overlay';
  el.className = 'modal-overlay';
  el.innerHTML = `
    <div class="card p-8 text-center max-w-sm mx-auto">
      <div class="spinner mx-auto mb-4" style="width:40px;height:40px;border-width:3px"></div>
      <p class="text-lg font-semibold text-slate-100 mb-2">Agents are working…</p>
      <p class="text-sm text-slate-400 mb-4">Running PM Agent on <span class="text-indigo-400">${jobTitle}</span></p>
      <div class="flex flex-wrap gap-2 justify-center text-xs text-slate-500">
        <span>🔍 Matching</span><span>📨 Communicating</span><span>⚠️ Risk Check</span><span>📅 Scheduling</span>
      </div>
      <p class="text-xs text-slate-600 mt-4">This may take 30–60 seconds</p>
    </div>`;
  document.body.appendChild(el);
  return el;
}

export function hideAgentOverlay() {
  document.getElementById('agent-overlay')?.remove();
}

// ── Empty state ───────────────────────────────────────────────────────────────

export function emptyState(message, icon = '📭') {
  return `<div class="empty-state"><div class="text-4xl mb-3">${icon}</div><p class="text-slate-400">${message}</p></div>`;
}

// ── Loading skeleton ──────────────────────────────────────────────────────────

export function loadingSkeleton() {
  return `<div class="space-y-3 p-4">
    ${[1,2,3].map(() => `<div class="h-12 bg-slate-800 rounded-lg animate-pulse"></div>`).join('')}
  </div>`;
}
