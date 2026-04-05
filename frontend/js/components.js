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
  predictor:       'bg-cyan-900 text-cyan-200',
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

// ── Count-up animation ────────────────────────────────────────────────────────

export function countUp(el, target, duration = 1200) {
  if (!el) return;
  const start = performance.now();
  requestAnimationFrame(function step(now) {
    const t = Math.min((now - start) / duration, 1);
    const eased = 1 - Math.pow(1 - t, 3);
    el.textContent = Math.round(eased * target);
    if (t < 1) requestAnimationFrame(step);
  });
}

// ── Mission Control Overlay (SSE live stream) ─────────────────────────────────

export function showMissionControlOverlay(jobTitle) {
  const el = document.createElement('div');
  el.id = 'mission-control-overlay';
  el.className = 'modal-overlay';
  el.style.cssText = 'align-items: flex-start; padding-top: 5vh;';
  el.innerHTML = `
    <div id="mc-modal" style="background:#0f172a; border:1px solid #334155; border-radius:1rem; width:100%; max-width:720px; max-height:82vh; display:flex; flex-direction:column; overflow:hidden; margin:0 1rem;">
      <div id="mc-header" style="padding:1.25rem 1.5rem; border-bottom:1px solid #334155; display:flex; align-items:center; justify-content:space-between; flex-shrink:0;">
        <div style="display:flex; align-items:center; gap:0.75rem;">
          <div class="spinner" style="width:18px;height:18px;border-width:2px;flex-shrink:0;"></div>
          <div>
            <p style="font-weight:700; color:#e2e8f0; font-size:0.95rem;">🤖 Mission Control</p>
            <p style="font-size:0.75rem; color:#64748b; margin-top:0.15rem;">${jobTitle}</p>
          </div>
        </div>
        <span id="mc-elapsed" style="font-size:0.7rem; color:#475569; font-family:monospace;">0.0s</span>
      </div>
      <div id="mc-log" style="flex:1; overflow-y:auto; padding:0.75rem 1rem; font-family:monospace; font-size:0.75rem; line-height:1.6; background:#0a1120;"></div>
      <div id="mc-footer" style="padding:0.75rem 1.5rem; border-top:1px solid #1e293b; display:flex; align-items:center; gap:0.5rem; background:#0f172a; flex-shrink:0;">
        <span id="mc-cursor" style="width:8px;height:14px;background:#6366f1;display:inline-block;animation:mcBlink 1s step-end infinite;border-radius:1px;"></span>
        <span id="mc-status" style="font-size:0.72rem; color:#475569;">Connecting…</span>
      </div>
    </div>`;
  document.body.appendChild(el);

  const startTime = Date.now();
  const elapsedEl = document.getElementById('mc-elapsed');
  const elapsedTimer = setInterval(() => {
    if (elapsedEl) elapsedEl.textContent = ((Date.now() - startTime) / 1000).toFixed(1) + 's';
  }, 100);

  return {
    el,
    elapsedTimer,
    appendLog(event) {
      const log = document.getElementById('mc-log');
      if (!log) return;
      const status = document.getElementById('mc-status');
      const line = document.createElement('div');
      line.style.cssText = 'padding:0.15rem 0; border-bottom:1px solid #0f172a; display:flex; gap:0.6rem; align-items:flex-start;';

      const agentColors = {
        project_manager: '#818cf8', matching: '#60a5fa', communication: '#34d399',
        risk: '#fb923c', rescheduling: '#a78bfa', predictor: '#22d3ee', base: '#94a3b8',
      };
      const agentColor = agentColors[event.agent] || '#94a3b8';
      const agentLabel = (event.agent || 'system').replace(/_/g, ' ');

      let icon = '';
      let textStyle = 'color:#94a3b8;';
      let text = '';

      if (event.type === 'agent_start') {
        icon = '▶';
        textStyle = 'color:#818cf8; font-weight:600;';
        text = `Starting ${agentLabel}: ${event.task || ''}`;
      } else if (event.type === 'tool_call') {
        icon = '⚙';
        textStyle = 'color:#64748b;';
        text = `${event.tool}(${(event.input_keys || []).join(', ')})`;
      } else if (event.type === 'tool_result') {
        icon = '✓';
        textStyle = 'color:#475569;';
        text = event.summary || '';
      } else if (event.type === 'thinking') {
        icon = '◈';
        textStyle = 'color:#e2e8f0;';
        text = event.text || '';
      } else if (event.type === 'agent_done') {
        icon = '■';
        textStyle = 'color:#4ade80; font-weight:600;';
        text = `${agentLabel} done — ${event.summary || ''}`;
      } else if (event.type === 'done') {
        icon = '★';
        textStyle = event.success ? 'color:#4ade80; font-weight:700;' : 'color:#f87171; font-weight:700;';
        text = event.success ? `Completed! ${event.tool_calls_count || 0} tool calls` : `Error: ${event.error || 'unknown'}`;
      }

      line.innerHTML = `
        <span style="color:${agentColor}; flex-shrink:0; min-width:90px; font-size:0.68rem; font-weight:700; text-transform:uppercase; letter-spacing:0.04em; padding-top:1px;">${agentLabel}</span>
        <span style="color:#475569; flex-shrink:0; padding-top:1px;">${icon}</span>
        <span style="${textStyle} flex:1; word-break:break-word;">${text}</span>`;

      log.appendChild(line);
      log.scrollTop = log.scrollHeight;
      if (status) status.textContent = text.slice(0, 60);
    },
    complete(success, summary) {
      clearInterval(elapsedTimer);
      const header = document.getElementById('mc-header');
      if (header) {
        const spinner = header.querySelector('.spinner');
        if (spinner) {
          spinner.style.cssText = `width:18px;height:18px;border-radius:50%;background:${success ? '#4ade80' : '#f87171'};animation:none;border:none;`;
        }
        const title = header.querySelector('p');
        if (title) title.textContent = success ? '✓ Mission Complete' : '✗ Mission Failed';
        if (title) title.style.color = success ? '#4ade80' : '#f87171';
      }
      const cursor = document.getElementById('mc-cursor');
      if (cursor) cursor.style.display = 'none';
      const statusEl = document.getElementById('mc-status');
      if (statusEl) statusEl.textContent = success ? 'All agents completed successfully' : 'Agent encountered an error';
    },
  };
}

export function hideMissionControlOverlay() {
  document.getElementById('mission-control-overlay')?.remove();
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
