import { api } from '../api.js';
import { formatDateTime, severityBadge } from '../components.js';

export async function renderRisks(container) {
  container.innerHTML = `
    <div class="flex items-center justify-between mb-6">
      <div class="flex items-center gap-3">
        <select id="filter-resolved" class="input w-40 text-sm">
          <option value="">All Risks</option>
          <option value="active">Active Only</option>
          <option value="resolved">Resolved Only</option>
        </select>
        <select id="filter-severity" class="input w-40 text-sm">
          <option value="">All Severities</option>
          <option>low</option><option>medium</option><option>high</option><option>critical</option>
        </select>
      </div>
      <button id="refresh-risks" class="btn-ghost text-sm">↻ Refresh</button>
    </div>
    <div class="card overflow-hidden">
      <div id="risks-table-container"></div>
    </div>`;

  let allRisks = [];
  let jobsMap = {};

  async function load() {
    const [risksData, jobsData] = await Promise.all([
      api.orchestrate.risks(),
      api.jobs.list(),
    ]);
    allRisks = risksData?.risks || [];
    jobsMap = Object.fromEntries((jobsData?.jobs || []).map(j => [j.id, j]));
    renderTable();
  }

  function renderTable() {
    const resolvedFilter = document.getElementById('filter-resolved').value;
    const severityFilter = document.getElementById('filter-severity').value;
    const tc = document.getElementById('risks-table-container');

    let filtered = allRisks;
    if (resolvedFilter === 'active') filtered = filtered.filter(r => !r.resolved);
    if (resolvedFilter === 'resolved') filtered = filtered.filter(r => r.resolved);
    if (severityFilter) filtered = filtered.filter(r => r.severity === severityFilter);

    if (!filtered.length) {
      tc.innerHTML = `<div class="p-12 text-center">
        <div class="text-4xl mb-3">🛡️</div>
        <p class="text-slate-400">No risks match the current filters.</p>
        ${allRisks.length === 0 ? '<p class="text-slate-600 text-sm mt-2">Run an agent on a job to detect risks.</p>' : ''}
      </div>`;
      return;
    }

    tc.innerHTML = `<table>
      <thead><tr>
        <th>Job</th><th>Risk Type</th><th>Severity</th><th>Description</th>
        <th>Triggered</th><th>Status</th>
      </tr></thead>
      <tbody>
        ${filtered.map(r => {
          const job = jobsMap[r.job_id];
          return `<tr>
            <td>
              ${job
                ? `<a href="#job/${r.job_id}" class="text-indigo-400 hover:text-indigo-300 font-medium text-xs">${job.title}</a>`
                : `<span class="text-slate-500 text-xs">${r.job_id.slice(0, 8)}…</span>`}
            </td>
            <td class="text-slate-300">${r.risk_type.replace(/_/g, ' ')}</td>
            <td>${severityBadge(r.severity)}</td>
            <td class="text-slate-400 text-xs max-w-xs">
              <span title="${r.description}">${r.description.length > 80 ? r.description.slice(0, 80) + '…' : r.description}</span>
            </td>
            <td class="text-slate-500 text-xs">${formatDateTime(r.triggered_at)}</td>
            <td>
              ${r.resolved
                ? '<span class="text-green-400 text-xs font-semibold">✓ Resolved</span>'
                : '<span class="text-orange-400 text-xs font-semibold">⚠ Active</span>'}
            </td>
          </tr>`;
        }).join('')}
      </tbody>
    </table>`;

    // Make job links not trigger row click
    tc.querySelectorAll('a').forEach(a => a.addEventListener('click', e => e.stopPropagation()));
  }

  document.getElementById('filter-resolved').addEventListener('change', renderTable);
  document.getElementById('filter-severity').addEventListener('change', renderTable);
  document.getElementById('refresh-risks').addEventListener('click', load);

  await load();
}
