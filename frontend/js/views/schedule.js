import { api } from '../api.js';
import { formatDateTime } from '../components.js';

export async function renderSchedule(container) {
  container.innerHTML = `
    <div class="flex items-center justify-between mb-6">
      <p class="text-slate-400 text-sm">All scheduled job assignments</p>
      <button id="refresh-btn" class="btn-ghost text-sm">↻ Refresh</button>
    </div>
    <div id="schedule-content"></div>`;

  async function load() {
    const sc = document.getElementById('schedule-content');
    sc.innerHTML = `<div class="text-slate-500 text-sm p-4">Loading…</div>`;

    const [schedData, jobsData, subsData] = await Promise.all([
      api.schedule.all(),
      api.jobs.list(),
      api.subcontractors.list(),
    ]);

    const schedules = schedData?.schedules || [];
    const jobs = Object.fromEntries((jobsData?.jobs || []).map(j => [j.id, j]));
    const subs = Object.fromEntries((subsData?.subcontractors || []).map(s => [s.id, s]));

    if (!schedules.length) {
      sc.innerHTML = `<div class="card p-12 text-center">
        <div class="text-4xl mb-3">📅</div>
        <p class="text-slate-400">No schedule entries yet.</p>
        <p class="text-slate-600 text-sm mt-2">Run an agent on a job to create schedule entries.</p>
      </div>`;
      return;
    }

    const sorted = [...schedules].sort((a, b) => a.scheduled_start.localeCompare(b.scheduled_start));

    sc.innerHTML = `<div class="grid grid-cols-3 gap-4">
      ${sorted.map(s => {
        const job = jobs[s.job_id];
        const sub = subs[s.subcontractor_id];
        const now = new Date().toISOString();
        const isActive = s.scheduled_start <= now && s.scheduled_end >= now;
        const isPast = s.scheduled_end < now;
        return `
          <div class="card p-5 ${isActive ? 'border-indigo-600' : ''}">
            <div class="flex items-start justify-between mb-3">
              <div class="text-xs font-semibold text-slate-500 uppercase tracking-wide">
                ${isPast ? '✓ Past' : isActive ? '🟢 Active' : '⏳ Upcoming'}
              </div>
            </div>
            <p class="font-semibold text-slate-100 text-sm mb-1 line-clamp-2">${job?.title || s.job_id}</p>
            <div class="flex items-center gap-2 mt-2 mb-3">
              <div class="w-6 h-6 rounded-full bg-indigo-900 flex items-center justify-center text-xs text-indigo-300 font-bold">
                ${sub ? sub.name.charAt(0) : '?'}
              </div>
              <span class="text-xs text-slate-400">${sub?.name || 'Unknown'}</span>
            </div>
            <div class="space-y-1 text-xs text-slate-500">
              <div class="flex items-center gap-2">
                <span>▶</span><span>${formatDateTime(s.scheduled_start)}</span>
              </div>
              <div class="flex items-center gap-2">
                <span>⏹</span><span>${formatDateTime(s.scheduled_end)}</span>
              </div>
            </div>
            ${s.notes ? `<p class="text-xs text-slate-500 mt-3 italic border-t border-slate-700 pt-2">${s.notes}</p>` : ''}
          </div>`;
      }).join('')}
    </div>`;
  }

  document.getElementById('refresh-btn').addEventListener('click', load);
  await load();
}
