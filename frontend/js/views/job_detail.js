import { api } from '../api.js';
import { formatDate, formatDateTime, hideAgentOverlay, priorityBadge, ratingStars, severityBadge, showAgentOverlay, skillChips, statusBadge, toast } from '../components.js';

export async function renderJobDetail(container, jobId) {
  container.innerHTML = `<div class="animate-pulse space-y-4">
    <div class="h-8 bg-slate-800 rounded w-1/3"></div>
    <div class="h-40 bg-slate-800 rounded-xl"></div>
  </div>`;

  const job = await api.jobs.get(jobId);

  container.innerHTML = `
    <!-- Breadcrumb -->
    <div class="flex items-center gap-2 text-sm text-slate-500 mb-6">
      <a href="#jobs" class="hover:text-indigo-400 transition-colors">Jobs</a>
      <span>/</span>
      <span class="text-slate-300">${job.title}</span>
    </div>

    <!-- Header -->
    <div class="flex items-start justify-between mb-6">
      <div>
        <div class="flex items-center gap-3 mb-2">
          <h1 class="text-2xl font-bold text-slate-100">${job.title}</h1>
          ${statusBadge(job.status)}
          ${priorityBadge(job.priority)}
        </div>
        <p class="text-slate-400 text-sm">${job.location} &nbsp;·&nbsp; $${job.budget.toLocaleString()} budget</p>
      </div>
      <button id="run-agent-btn" class="btn-primary flex items-center gap-2 text-base px-6 py-3">
        🤖 Run Agent
      </button>
    </div>

    <!-- Info grid -->
    <div class="grid grid-cols-3 gap-4 mb-6">
      <div class="card p-4">
        <div class="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Description</div>
        <p class="text-sm text-slate-300">${job.description}</p>
      </div>
      <div class="card p-4">
        <div class="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Required Skills</div>
        <div class="flex flex-wrap gap-1 mt-1">${skillChips(job.required_skills)}</div>
        <div class="mt-3 text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Dates</div>
        <p class="text-sm text-slate-300">${formatDate(job.start_date)} → ${formatDate(job.end_date)}</p>
      </div>
      <div id="sub-card" class="card p-4">
        <div class="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Assigned Subcontractor</div>
        <p class="text-slate-500 text-sm">Loading…</p>
      </div>
    </div>

    <!-- Tabs -->
    <div class="card overflow-hidden">
      <div class="flex border-b border-slate-700 px-4 pt-1">
        <button class="tab-btn active" data-tab="schedule">Schedule</button>
        <button class="tab-btn" data-tab="messages">Messages</button>
        <button class="tab-btn" data-tab="risks">Risks</button>
      </div>
      <div id="tab-content" class="p-5 min-h-40"></div>
    </div>`;

  // Subcontractor card
  const subCard = document.getElementById('sub-card');
  if (job.assigned_subcontractor_id) {
    try {
      const sub = await api.subcontractors.get(job.assigned_subcontractor_id);
      subCard.innerHTML = `
        <div class="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">Assigned Subcontractor</div>
        <p class="font-semibold text-slate-100 text-sm mb-1">${sub.name}</p>
        <p class="text-xs text-slate-400 mb-0.5">✉ ${sub.email}</p>
        <p class="text-xs text-slate-400 mb-2">📞 ${sub.phone}</p>
        <div class="mb-2">${ratingStars(sub.rating)}</div>
        <div class="flex flex-wrap gap-1">${skillChips(sub.skills)}</div>`;
    } catch {
      subCard.innerHTML = `<div class="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Assigned Subcontractor</div><p class="text-slate-400 text-sm">${job.assigned_subcontractor_id}</p>`;
    }
  } else {
    subCard.innerHTML = `
      <div class="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Assigned Subcontractor</div>
      <div class="text-center py-4">
        <div class="text-3xl mb-2">👷</div>
        <p class="text-slate-500 text-sm">Not yet assigned</p>
        <p class="text-xs text-slate-600 mt-1">Run Agent to match a subcontractor</p>
      </div>`;
  }

  // Tab logic
  async function loadTab(tab) {
    const tc = document.getElementById('tab-content');
    tc.innerHTML = `<div class="text-slate-500 text-sm">Loading…</div>`;

    if (tab === 'schedule') {
      const data = await api.schedule.forJob(jobId);
      const scheds = data?.schedules || [];
      tc.innerHTML = scheds.length === 0
        ? `<div class="text-center py-8 text-slate-500"><div class="text-3xl mb-2">📅</div><p>No schedule entries yet.</p></div>`
        : scheds.map(s => `
          <div class="flex items-start gap-4 p-3 rounded-lg bg-slate-900 mb-2">
            <div class="text-2xl">📅</div>
            <div>
              <p class="text-sm font-semibold text-slate-200">${formatDateTime(s.scheduled_start)} → ${formatDateTime(s.scheduled_end)}</p>
              ${s.notes ? `<p class="text-xs text-slate-400 mt-1">${s.notes}</p>` : ''}
            </div>
          </div>`).join('');

    } else if (tab === 'messages') {
      const data = await api.orchestrate.messages(jobId);
      const msgs = data?.messages || [];
      tc.innerHTML = msgs.length === 0
        ? `<div class="text-center py-8 text-slate-500"><div class="text-3xl mb-2">💬</div><p>No messages yet.</p></div>`
        : `<div class="space-y-3">${msgs.map(m => {
            const isOut = m.direction === 'outbound';
            const chanIcon = { email: '✉', sms: '📱', slack: '💬' }[m.channel] || '📨';
            return `<div class="flex ${isOut ? 'justify-end' : 'justify-start'}">
              <div class="max-w-sm rounded-xl p-3 ${isOut ? 'bg-indigo-900 text-indigo-100' : 'bg-slate-700 text-slate-200'}">
                <div class="text-xs font-semibold mb-1 opacity-70">${chanIcon} ${m.channel} · ${m.direction}</div>
                <p class="text-xs font-semibold mb-1">${m.subject}</p>
                <p class="text-xs opacity-80 whitespace-pre-wrap">${m.body}</p>
                <p class="text-xs opacity-40 mt-1.5 text-right">${formatDateTime(m.sent_at)}</p>
              </div>
            </div>`;
          }).join('')}</div>`;

    } else if (tab === 'risks') {
      const data = await api.orchestrate.risks();
      const risks = (data?.risks || []).filter(r => r.job_id === jobId);
      tc.innerHTML = risks.length === 0
        ? `<div class="text-center py-8 text-slate-500"><div class="text-3xl mb-2">✅</div><p>No risks detected.</p></div>`
        : `<div class="space-y-2">${risks.map(r => `
          <div class="flex items-start gap-3 p-3 rounded-lg bg-slate-900">
            <div class="mt-0.5">${severityBadge(r.severity)}</div>
            <div>
              <p class="text-xs font-semibold text-slate-300">${r.risk_type.replace(/_/g, ' ')}</p>
              <p class="text-xs text-slate-400 mt-0.5">${r.description}</p>
              ${r.resolved ? `<p class="text-xs text-green-500 mt-1">✓ Resolved</p>` : '<p class="text-xs text-orange-400 mt-1">⚠ Active</p>'}
            </div>
          </div>`).join('')}</div>`;
    }
  }

  container.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      container.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      loadTab(btn.dataset.tab);
    });
  });

  loadTab('schedule');

  // Run Agent button
  document.getElementById('run-agent-btn').addEventListener('click', async () => {
    const btn = document.getElementById('run-agent-btn');
    btn.disabled = true;
    const overlay = showAgentOverlay(job.title);
    try {
      const result = await api.orchestrate.run(jobId);
      hideAgentOverlay();
      toast(`✓ Agents completed — ${result?.tool_calls_count || 0} tool calls made`, 'success');

      // Show summary in a nice way
      if (result?.summary) {
        const summaryEl = document.createElement('div');
        summaryEl.className = 'card p-4 mb-4 border-indigo-700';
        summaryEl.style.borderColor = '#4f46e5';
        summaryEl.innerHTML = `
          <div class="flex items-start gap-3">
            <span class="text-xl">🤖</span>
            <div>
              <p class="text-sm font-semibold text-indigo-300 mb-1">Agent Summary</p>
              <p class="text-xs text-slate-400">${result.summary.slice(0, 400)}${result.summary.length > 400 ? '…' : ''}</p>
            </div>
          </div>`;
        container.insertBefore(summaryEl, container.querySelector('.card.overflow-hidden'));
      }

      // Refresh job data
      await renderJobDetail(container, jobId);
    } catch (err) {
      hideAgentOverlay();
      toast(err.message, 'error');
      btn.disabled = false;
    }
  });
}
