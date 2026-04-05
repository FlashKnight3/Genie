import { api } from '../api.js';
import { agentChip, countUp, severityBadge, timeAgo } from '../components.js';
import { getSupabase, subscribePostgresInserts } from '../supabase.js';

let dashboardRealtimeCleanup = [];

function clearDashboardRealtime() {
  dashboardRealtimeCleanup.forEach((fn) => fn());
  dashboardRealtimeCleanup = [];
}

const HEATMAP_COLORS = {
  pending:     '#475569',
  matching:    '#3b82f6',
  assigned:    '#6366f1',
  in_progress: '#d97706',
  completed:   '#16a34a',
  at_risk:     '#ea580c',
  rescheduled: '#9333ea',
  cancelled:   '#dc2626',
};

function renderActivityBlock(logs) {
  return `
    <h3 class="text-sm font-semibold text-slate-300 mb-4">Recent Agent Activity</h3>
    ${logs.length === 0
      ? '<p class="text-slate-500 text-sm">No agent activity yet. Run an agent on a job to see activity here.</p>'
      : `<div class="space-y-2">
          ${logs.map(l => `
            <div class="flex items-start gap-3 py-2 border-b border-slate-700/50 last:border-0">
              <div class="mt-0.5 flex-shrink-0">${agentChip(l.agent_name)}</div>
              <div class="flex-1 min-w-0">
                <p class="text-xs text-slate-300 truncate">${l.action}</p>
                ${l.tool_calls && l.tool_calls.length ? `<p class="text-xs text-slate-600 mt-0.5">tools: ${l.tool_calls.map(t => t.tool).join(', ')}</p>` : ''}
              </div>
              <div class="text-xs text-slate-600 flex-shrink-0">${timeAgo(l.timestamp)}</div>
            </div>`).join('')}
        </div>`}`;
}

export async function renderDashboard(container) {
  clearDashboardRealtime();
  container.innerHTML = `<div class="space-y-6">
    <div id="dash-stats" class="grid grid-cols-4 gap-4"></div>
    <div id="dash-heatmap" class="card p-5"></div>
    <div id="dash-alerts" class="space-y-3"></div>
    <div class="grid grid-cols-2 gap-6">
      <div id="dash-risks" class="card p-5"></div>
      <div id="dash-activity" class="card p-5"></div>
    </div>
  </div>`;

  const [jobsData, subsData, risksData, logsData, delaysData, leadsData] = await Promise.all([
    api.jobs.list(),
    api.subcontractors.list({ availability: 'available' }),
    api.orchestrate.risks(),
    api.orchestrate.logs(8),
    api.delays.list().catch(() => ({ alerts: [] })),
    api.leads.list().catch(() => ({ leads: [] })),
  ]);

  const jobs = jobsData?.jobs || [];
  const availableSubs = subsData?.count || 0;
  const risks = risksData?.risks || [];
  const logs = logsData?.logs || [];
  const alerts = delaysData?.alerts || [];
  const leads = leadsData?.leads || [];

  const activeRisks = risks.filter(r => !r.resolved);
  const activeJobs = jobs.filter(j => !['completed', 'cancelled'].includes(j.status));
  const atRisk = jobs.filter(j => j.status === 'at_risk' || j.status === 'rescheduled').length;
  const newLeads = leads.filter(l => l.status === 'new').length;

  // Glass metric cards
  const metrics = [
    {
      label: 'Active Jobs', value: activeJobs.length, icon: '💼',
      sub: `${atRisk} at risk`, subColor: atRisk > 0 ? '#f97316' : '#475569',
      borderColor: '#6366f1', iconBg: 'rgba(99,102,241,0.15)',
    },
    {
      label: 'Overdue Alerts', value: alerts.length, icon: '⚠️',
      sub: 'need follow-up', subColor: alerts.length > 0 ? '#f87171' : '#475569',
      borderColor: '#ef4444', iconBg: 'rgba(239,68,68,0.15)',
      dataAttr: '',
    },
    {
      label: 'New Leads', value: newLeads, icon: '📥',
      sub: 'awaiting response', subColor: newLeads > 0 ? '#818cf8' : '#475569',
      borderColor: '#6366f1', iconBg: 'rgba(99,102,241,0.15)',
      dataAttr: 'data-dash-stat="new-leads"',
    },
    {
      label: 'Available Subs', value: availableSubs, icon: '👷',
      sub: 'ready to assign', subColor: '#475569',
      borderColor: '#22c55e', iconBg: 'rgba(34,197,94,0.15)',
    },
  ];

  document.getElementById('dash-stats').innerHTML = metrics.map((m, i) => `
    <div class="glass-card p-5 relative overflow-hidden" ${m.dataAttr || ''} style="border-bottom: 3px solid ${m.borderColor}20; border-bottom-width: 3px;">
      <div style="position:absolute;top:1rem;right:1rem;width:2.2rem;height:2.2rem;border-radius:50%;background:${m.iconBg};display:flex;align-items:center;justify-content:center;font-size:1.1rem;">${m.icon}</div>
      <div class="text-3xl font-bold text-slate-100 mb-1 mt-1" id="metric-val-${i}" ${i === 2 ? 'data-dash-field="value"' : ''}>0</div>
      <div class="text-sm font-medium text-slate-400 mb-1">${m.label}</div>
      <div class="text-xs" style="color:${m.subColor}">${m.sub}</div>
      <div style="position:absolute;bottom:0;left:0;right:0;height:3px;background:${m.borderColor};opacity:0.6;border-radius:0 0 0.75rem 0.75rem;"></div>
    </div>`).join('');

  // Animate metric counts
  metrics.forEach((m, i) => {
    const el = document.getElementById(`metric-val-${i}`);
    if (el) countUp(el, m.value);
  });

  // Job Health Heatmap
  const heatmapEl = document.getElementById('dash-heatmap');
  if (jobs.length === 0) {
    heatmapEl.innerHTML = `<h3 class="text-sm font-semibold text-slate-300 mb-3">Portfolio Health</h3><p class="text-slate-500 text-sm">No jobs yet. <a href="#jobs" class="text-indigo-400 hover:underline">Create your first job →</a></p>`;
  } else {
    heatmapEl.innerHTML = `
      <div class="flex items-center justify-between mb-4">
        <h3 class="text-sm font-semibold text-slate-300">Portfolio Health</h3>
        <div class="flex items-center gap-3 text-xs text-slate-500">
          <span style="display:inline-flex;align-items:center;gap:0.25rem;"><span style="width:10px;height:10px;background:#16a34a;border-radius:2px;display:inline-block;"></span>Done</span>
          <span style="display:inline-flex;align-items:center;gap:0.25rem;"><span style="width:10px;height:10px;background:#d97706;border-radius:2px;display:inline-block;"></span>Active</span>
          <span style="display:inline-flex;align-items:center;gap:0.25rem;"><span style="width:10px;height:10px;background:#ea580c;border-radius:2px;display:inline-block;"></span>At Risk</span>
          <span style="display:inline-flex;align-items:center;gap:0.25rem;"><span style="width:10px;height:10px;background:#475569;border-radius:2px;display:inline-block;"></span>Pending</span>
          <span class="text-slate-600">${jobs.length} total</span>
        </div>
      </div>
      <div style="display:flex;flex-wrap:wrap;gap:6px;">
        ${jobs.map(j => `
          <div class="heatmap-cell"
               style="background:${HEATMAP_COLORS[j.status] || '#475569'};"
               title="${j.title} — ${j.status.replace(/_/g, ' ')}"
               data-job-id="${j.id}"></div>`).join('')}
      </div>`;

    heatmapEl.querySelectorAll('.heatmap-cell').forEach(cell => {
      cell.addEventListener('click', () => {
        window.location.hash = `#job/${cell.dataset.jobId}`;
      });
    });
  }

  // Delay alert cards
  const alertsEl = document.getElementById('dash-alerts');
  if (alerts.length === 0) {
    alertsEl.innerHTML = `
      <div class="card p-4 flex items-center gap-3" style="border-color:#166534;">
        <span class="text-green-400 text-lg">✓</span>
        <span class="text-sm text-green-400 font-medium">All jobs on track — no overdue alerts.</span>
      </div>`;
  } else {
    alertsEl.innerHTML = `
      <div class="flex items-center gap-2 mb-1">
        <span class="text-red-400 font-semibold text-sm">🚨 ${alerts.length} Overdue Job${alerts.length > 1 ? 's' : ''} — AI has pre-drafted follow-ups</span>
      </div>
      ${alerts.map(a => renderAlertCard(a)).join('')}`;
  }

  // Active risks
  document.getElementById('dash-risks').innerHTML = `
    <h3 class="text-sm font-semibold text-slate-300 mb-4">Active Risks</h3>
    ${activeRisks.length === 0
      ? '<p class="text-slate-500 text-sm">No active risks — all clear ✓</p>'
      : `<div class="space-y-2">
          ${activeRisks.slice(0, 5).map(r => `
            <div class="flex items-start gap-3 p-2.5 rounded-lg bg-slate-900">
              <div class="mt-0.5">${severityBadge(r.severity)}</div>
              <div>
                <div class="text-xs font-semibold text-slate-300">${r.risk_type.replace(/_/g, ' ')}</div>
                <div class="text-xs text-slate-500 mt-0.5 line-clamp-2">${r.description}</div>
              </div>
            </div>`).join('')}
        </div>`}`;

  // Agent activity
  document.getElementById('dash-activity').innerHTML = renderActivityBlock(logs);

  if (getSupabase()) {
    dashboardRealtimeCleanup.push(
      subscribePostgresInserts('agent_logs', async () => {
        try {
          const logsData = await api.orchestrate.logs(8);
          const box = document.getElementById('dash-activity');
          if (box) box.innerHTML = renderActivityBlock(logsData?.logs || []);
        } catch { /* ignore */ }
      })
    );
    dashboardRealtimeCleanup.push(
      subscribePostgresInserts('leads', async () => {
        try {
          const leadsData = await api.leads.list();
          const leads = leadsData?.leads || [];
          const n = leads.filter((l) => l.status === 'new').length;
          const val = document.querySelector('[data-dash-field="value"]');
          if (val) { val.textContent = String(n); }
        } catch { /* ignore */ }
      })
    );
  }
}

function renderAlertCard(alert) {
  const cardId = `alert-card-${alert.job_id}`;
  const btnId = `alert-btn-${alert.job_id}`;

  setTimeout(() => {
    const btn = document.getElementById(btnId);
    if (btn) {
      btn.addEventListener('click', async () => {
        btn.disabled = true;
        btn.textContent = 'Sending…';
        try {
          const res = await api.delays.send(alert.job_id);
          const card = document.getElementById(cardId);
          if (card) {
            card.innerHTML = `
              <div class="flex items-center gap-3 p-4">
                <span class="text-green-400 text-xl">✓</span>
                <div>
                  <p class="text-sm font-semibold text-green-400">Follow-up sent to ${alert.sub_name}</p>
                  <p class="text-xs text-slate-500 mt-0.5">Message logged • Delivery: ${res?.delivery_status || 'sent'}</p>
                </div>
              </div>`;
          }
        } catch (err) {
          btn.disabled = false;
          btn.textContent = '✓ Approve & Send SMS';
          alert(`Error: ${err.message}`);
        }
      });
    }
  }, 50);

  return `
    <div id="${cardId}" class="card p-4" style="border-color:#7f1d1d;">
      <div class="flex items-start justify-between gap-4">
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2 mb-1">
            <span class="text-xs font-bold text-red-400 uppercase tracking-wide">Overdue ${alert.days_overdue}d</span>
            <span class="text-xs text-slate-500">•</span>
            <span class="text-xs text-slate-400">${alert.sub_name}</span>
          </div>
          <p class="text-sm font-semibold text-slate-200 mb-2">${alert.job_title}</p>
          <div class="bg-slate-900 rounded-lg p-3 mb-3">
            <p class="text-xs text-slate-500 mb-1 font-semibold uppercase tracking-wide">AI-drafted SMS</p>
            <p class="text-sm text-slate-300 italic">"${alert.draft_sms}"</p>
          </div>
        </div>
      </div>
      <div class="flex items-center gap-2">
        <button id="${btnId}" class="btn-primary text-sm py-2 px-4">✓ Approve &amp; Send SMS</button>
        <span class="text-xs text-slate-500">→ ${alert.sub_name} · ${alert.sub_phone || alert.sub_email}</span>
      </div>
    </div>`;
}
