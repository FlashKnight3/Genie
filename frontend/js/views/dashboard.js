import { api } from '../api.js';
import { agentChip, severityBadge, timeAgo } from '../components.js';
import { getSupabase, subscribePostgresInserts } from '../supabase.js';

let dashboardRealtimeCleanup = [];

function clearDashboardRealtime() {
  dashboardRealtimeCleanup.forEach((fn) => fn());
  dashboardRealtimeCleanup = [];
}

function renderActivityBlock(logs) {
  return `
    <h3 class="text-sm font-semibold text-slate-300 mb-4">Recent Agent Activity</h3>
    ${logs.length === 0
      ? '<p class="text-slate-500 text-sm">No agent activity yet. Run an agent on a job to see activity here.</p>'
      : `<div class="space-y-2">
          ${logs.map(l => `
            <div class="flex items-start gap-3 py-2 border-b border-slate-700 last:border-0">
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
  const completed = jobs.filter(j => j.status === 'completed').length;
  const atRisk = jobs.filter(j => j.status === 'at_risk' || j.status === 'rescheduled').length;
  const newLeads = leads.filter(l => l.status === 'new').length;

  // Stat cards
  const stats = [
    { label: 'Active Jobs', value: jobs.filter(j => !['completed','cancelled'].includes(j.status)).length, icon: '💼', sub: `${atRisk} at risk`, subColor: atRisk > 0 ? 'text-orange-400' : 'text-slate-500' },
    { label: 'Overdue Alerts', value: alerts.length, icon: '⚠️', sub: 'need follow-up', subColor: alerts.length > 0 ? 'text-red-400' : 'text-slate-500' },
    { label: 'New Leads', value: newLeads, icon: '📥', sub: 'awaiting response', subColor: newLeads > 0 ? 'text-indigo-400' : 'text-slate-500' },
    { label: 'Available Subs', value: availableSubs, icon: '👷', sub: 'ready to assign', subColor: 'text-slate-500' },
  ];

  document.getElementById('dash-stats').innerHTML = stats.map((s, i) => `
    <div class="card p-5" ${i === 2 ? 'data-dash-stat="new-leads"' : ''}>
      <div class="flex items-start justify-between mb-3">
        <span class="text-2xl">${s.icon}</span>
      </div>
      <div class="text-3xl font-bold text-slate-100 mb-1" ${i === 2 ? 'data-dash-field="value"' : ''}>${s.value}</div>
      <div class="text-sm text-slate-400 mb-1">${s.label}</div>
      <div class="text-xs ${s.subColor}">${s.sub}</div>
    </div>`).join('');

  // Delay alert cards — the money moment
  const alertsEl = document.getElementById('dash-alerts');
  if (alerts.length === 0) {
    alertsEl.innerHTML = `
      <div class="card p-4 border-green-800 flex items-center gap-3">
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
        } catch {
          /* ignore */
        }
      })
    );
    dashboardRealtimeCleanup.push(
      subscribePostgresInserts('leads', async () => {
        try {
          const leadsData = await api.leads.list();
          const leads = leadsData?.leads || [];
          const n = leads.filter((l) => l.status === 'new').length;
          const card = document.querySelector('[data-dash-stat="new-leads"]');
          const val = card?.querySelector('[data-dash-field="value"]');
          if (val) val.textContent = String(n);
        } catch {
          /* ignore */
        }
      })
    );
  }
}

function renderAlertCard(alert) {
  const cardId = `alert-card-${alert.job_id}`;
  const btnId = `alert-btn-${alert.job_id}`;

  // Wire up the send button after rendering
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
    <div id="${cardId}" class="card border border-red-900 p-4">
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
