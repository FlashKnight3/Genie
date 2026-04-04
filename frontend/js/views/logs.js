import { api } from '../api.js';
import { agentChip, formatDateTime, timeAgo } from '../components.js';

export async function renderLogs(container) {
  container.innerHTML = `
    <div class="flex items-center justify-between mb-6">
      <div class="flex items-center gap-3">
        <select id="filter-agent" class="input w-48 text-sm">
          <option value="">All Agents</option>
          <option value="project_manager">Project Manager</option>
          <option value="matching">Matching</option>
          <option value="communication">Communication</option>
          <option value="risk">Risk</option>
          <option value="rescheduling">Rescheduling</option>
        </select>
        <select id="filter-limit" class="input w-32 text-sm">
          <option value="25">Last 25</option>
          <option value="50" selected>Last 50</option>
          <option value="100">Last 100</option>
        </select>
      </div>
      <div class="flex items-center gap-3">
        <label class="flex items-center gap-2 text-sm text-slate-400 cursor-pointer">
          <input type="checkbox" id="auto-refresh" class="accent-indigo-500" />
          Auto-refresh
        </label>
        <button id="refresh-logs" class="btn-ghost text-sm">↻ Refresh</button>
      </div>
    </div>
    <div id="logs-feed" class="card p-5"></div>`;

  let refreshTimer = null;
  let allLogs = [];

  async function load() {
    const limit = parseInt(document.getElementById('filter-limit').value);
    const data = await api.orchestrate.logs(limit);
    allLogs = data?.logs || [];
    renderFeed();
  }

  function renderFeed() {
    const agentFilter = document.getElementById('filter-agent').value;
    const feed = document.getElementById('logs-feed');

    const filtered = agentFilter
      ? allLogs.filter(l => l.agent_name === agentFilter)
      : allLogs;

    if (!filtered.length) {
      feed.innerHTML = `<div class="text-center py-12">
        <div class="text-4xl mb-3">📊</div>
        <p class="text-slate-400">No agent activity yet.</p>
        <p class="text-slate-600 text-sm mt-2">Run an agent on a job to see logs here.</p>
      </div>`;
      return;
    }

    feed.innerHTML = `<div class="space-y-0">
      ${filtered.map((l, i) => {
        const tools = l.tool_calls || [];
        return `
          <div class="flex items-start gap-4 py-3.5 ${i < filtered.length - 1 ? 'border-b border-slate-700' : ''}">
            <!-- Timeline dot -->
            <div class="flex flex-col items-center mt-1">
              <div class="w-2 h-2 rounded-full bg-indigo-500 flex-shrink-0"></div>
              ${i < filtered.length - 1 ? '<div class="w-px flex-1 bg-slate-700 mt-1" style="min-height:20px"></div>' : ''}
            </div>

            <!-- Content -->
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 flex-wrap mb-1">
                ${agentChip(l.agent_name)}
                ${l.job_id ? `<a href="#job/${l.job_id}" class="text-xs text-indigo-400 hover:text-indigo-300">job ↗</a>` : ''}
              </div>
              <p class="text-sm text-slate-200 mb-1.5">${l.action}</p>
              ${tools.length ? `
                <div class="flex flex-wrap gap-1">
                  ${tools.map(t => `<span class="text-xs bg-slate-800 text-slate-400 px-2 py-0.5 rounded-md font-mono">${t.tool || t}</span>`).join('')}
                </div>` : ''}
            </div>

            <!-- Timestamp -->
            <div class="flex-shrink-0 text-right">
              <p class="text-xs text-slate-500">${timeAgo(l.timestamp)}</p>
              <p class="text-xs text-slate-700 mt-0.5">${formatDateTime(l.timestamp)}</p>
            </div>
          </div>`;
      }).join('')}
    </div>`;

    feed.querySelectorAll('a').forEach(a => a.addEventListener('click', e => e.stopPropagation()));
  }

  // Auto-refresh
  document.getElementById('auto-refresh').addEventListener('change', (e) => {
    if (e.target.checked) {
      refreshTimer = setInterval(load, 10000);
    } else {
      clearInterval(refreshTimer);
    }
  });

  document.getElementById('refresh-logs').addEventListener('click', load);
  document.getElementById('filter-agent').addEventListener('change', renderFeed);
  document.getElementById('filter-limit').addEventListener('change', load);

  await load();
}
