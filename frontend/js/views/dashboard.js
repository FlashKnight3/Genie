import { api } from '../api.js';
import { agentChip, severityBadge, statusBadge, timeAgo } from '../components.js';

export async function renderDashboard(container) {
  container.innerHTML = `<div class="space-y-6">
    <div id="dash-stats" class="grid grid-cols-4 gap-4"></div>
    <div class="grid grid-cols-2 gap-6">
      <div id="dash-status-chart" class="card p-5"></div>
      <div id="dash-risks" class="card p-5"></div>
    </div>
    <div id="dash-activity" class="card p-5"></div>
  </div>`;

  const [jobsData, subsData, risksData, logsData] = await Promise.all([
    api.jobs.list(),
    api.subcontractors.list({ availability: 'available' }),
    api.orchestrate.risks(),
    api.orchestrate.logs(10),
  ]);

  const jobs = jobsData?.jobs || [];
  const availableSubs = subsData?.count || 0;
  const risks = risksData?.risks || [];
  const logs = logsData?.logs || [];

  const activeRisks = risks.filter(r => !r.resolved);
  const completed = jobs.filter(j => j.status === 'completed').length;
  const atRisk = jobs.filter(j => j.status === 'at_risk').length;

  // Stat cards
  const stats = [
    { label: 'Total Jobs', value: jobs.length, icon: '💼', sub: `${atRisk} at risk`, subColor: atRisk > 0 ? 'text-orange-400' : 'text-slate-500' },
    { label: 'Active Risks', value: activeRisks.length, icon: '⚠️', sub: risks.filter(r => r.severity === 'critical').length + ' critical', subColor: 'text-red-400' },
    { label: 'Available Subs', value: availableSubs, icon: '👷', sub: 'ready to assign', subColor: 'text-slate-500' },
    { label: 'Completed', value: completed, icon: '✅', sub: `of ${jobs.length} jobs`, subColor: 'text-green-400' },
  ];

  document.getElementById('dash-stats').innerHTML = stats.map(s => `
    <div class="card p-5">
      <div class="flex items-start justify-between mb-3">
        <span class="text-2xl">${s.icon}</span>
      </div>
      <div class="text-3xl font-bold text-slate-100 mb-1">${s.value}</div>
      <div class="text-sm text-slate-400 mb-1">${s.label}</div>
      <div class="text-xs ${s.subColor}">${s.sub}</div>
    </div>`).join('');

  // Status breakdown chart
  const statusCounts = {};
  jobs.forEach(j => { statusCounts[j.status] = (statusCounts[j.status] || 0) + 1; });
  const statusColors = { pending:'bg-slate-500', matching:'bg-blue-500', assigned:'bg-indigo-500', in_progress:'bg-yellow-500', completed:'bg-green-500', at_risk:'bg-orange-500', rescheduled:'bg-purple-500', cancelled:'bg-red-500' };

  document.getElementById('dash-status-chart').innerHTML = `
    <h3 class="text-sm font-semibold text-slate-300 mb-4">Jobs by Status</h3>
    <div class="space-y-2.5">
      ${Object.entries(statusCounts).map(([status, count]) => `
        <div>
          <div class="flex justify-between text-xs text-slate-400 mb-1">
            <span>${status.replace(/_/g, ' ')}</span><span>${count}</span>
          </div>
          <div class="h-2 bg-slate-700 rounded-full overflow-hidden">
            <div class="${statusColors[status] || 'bg-slate-500'} h-full rounded-full" style="width:${jobs.length ? (count/jobs.length*100) : 0}%"></div>
          </div>
        </div>`).join('')}
    </div>`;

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
  document.getElementById('dash-activity').innerHTML = `
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
