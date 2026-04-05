import { api } from '../api.js';
import { countUp, formatDate, formatDateTime, hideAgentOverlay, hideMissionControlOverlay, priorityBadge, ratingStars, severityBadge, showAgentOverlay, showMissionControlOverlay, showModal, skillChips, statusBadge, toast } from '../components.js';

const SPECIALIST_OPTIONS = [0, 1, 2, 3, 4, 5, 6, 7, 8];

function buildOrchestrateLimits() {
  const maxSpecEl = document.getElementById('run-max-specialists');
  const raw = maxSpecEl ? parseInt(maxSpecEl.value, 10) : 1;
  const max_specialist_agents = Number.isNaN(raw) ? 3 : raw;
  const limits = { max_specialist_agents };

  const pmEl = document.getElementById('run-pm-rounds');
  const specEl = document.getElementById('run-spec-rounds');
  if (pmEl?.value !== '' && pmEl?.value != null) {
    const n = parseInt(pmEl.value, 10);
    if (!Number.isNaN(n) && n >= 1) limits.max_llm_rounds = n;
  }
  if (specEl?.value !== '' && specEl?.value != null) {
    const n = parseInt(specEl.value, 10);
    if (!Number.isNaN(n) && n >= 1) limits.max_rounds_per_specialist = n;
  }
  return limits;
}

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
      <div class="flex flex-col items-end gap-2 max-w-sm">
        <div class="flex flex-wrap items-end justify-end gap-2">
          <button id="predict-btn" class="btn-ghost flex items-center gap-1.5 text-sm px-3 py-2" title="AI success probability prediction">
            🔮 Predict
          </button>
          <div class="flex flex-col items-end gap-0.5">
            <label for="run-max-specialists" class="text-xs font-medium text-slate-400">Specialist agents</label>
            <select id="run-max-specialists" class="input text-sm py-2 min-w-[10.5rem]" title="How many delegated specialist runs (matching, risk, etc.) the project manager may start">
              ${SPECIALIST_OPTIONS.map(
                (n) =>
                  `<option value="${n}" ${n === 3 ? 'selected' : ''}>${n === 0 ? '0 — PM only' : n}</option>`
              ).join('')}
            </select>
          </div>
          <div class="flex items-stretch gap-0">
            <button id="run-agent-btn" class="btn-primary flex items-center gap-2 text-base px-5 py-3" style="border-radius:0.5rem 0 0 0.5rem;">
              🤖 Run Agent
            </button>
            <button id="live-mode-btn" title="Live mode: stream agent activity in real-time" class="btn-ghost text-xs px-2.5 py-3 flex items-center gap-1" style="border-radius:0 0.5rem 0.5rem 0; border-left:none; background:#1e293b;">
              <span id="live-mode-indicator" style="width:7px;height:7px;border-radius:50%;background:#475569;flex-shrink:0;transition:background 0.2s;"></span>
              Live
            </button>
          </div>
        </div>
        <details class="text-xs text-slate-500 w-full">
          <summary class="cursor-pointer text-slate-500 hover:text-slate-400 select-none text-right">Advanced — prompt rounds</summary>
          <div class="mt-2 flex flex-wrap gap-3 justify-end items-end">
            <div class="flex flex-col items-end gap-0.5">
              <label for="run-pm-rounds" class="text-slate-500">PM max rounds</label>
              <input id="run-pm-rounds" type="number" min="1" max="15" placeholder="server default" class="input text-sm py-1.5 w-28 text-right" title="Leave empty for server default" />
            </div>
            <div class="flex flex-col items-end gap-0.5">
              <label for="run-spec-rounds" class="text-slate-500">Per specialist</label>
              <input id="run-spec-rounds" type="number" min="1" max="15" placeholder="server default" class="input text-sm py-1.5 w-28 text-right" title="Leave empty for server default" />
            </div>
          </div>
        </details>
        <p class="text-xs text-slate-600 text-right leading-snug">Each specialist is a separate AI agent. Use <strong class="text-slate-400">0</strong> for project manager only (no delegation).</p>
      </div>
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

  // Live mode toggle
  let liveMode = false;
  document.getElementById('live-mode-btn').addEventListener('click', () => {
    liveMode = !liveMode;
    const indicator = document.getElementById('live-mode-indicator');
    if (indicator) indicator.style.background = liveMode ? '#4ade80' : '#475569';
    const liveBtn = document.getElementById('live-mode-btn');
    if (liveBtn) liveBtn.style.color = liveMode ? '#4ade80' : '#94a3b8';
    toast(liveMode ? '📡 Live mode on — next run will stream in real-time' : 'Live mode off', 'info');
  });

  // Crystal Ball predict button
  document.getElementById('predict-btn').addEventListener('click', async () => {
    const btn = document.getElementById('predict-btn');
    btn.disabled = true;
    btn.textContent = '⏳ Gazing…';
    try {
      const data = await api.predict.run(jobId);
      const pred = data?.prediction || {};
      const prob = pred.success_probability ?? 50;
      const barColor = prob >= 70 ? '#22c55e' : prob >= 40 ? '#f59e0b' : '#ef4444';
      const tlIcon = { on_track: '✅', at_risk: '⚠️', overdue: '🔴' }[pred.timeline_assessment] || '📍';

      const modal = showModal(`
        <div class="flex items-center justify-between mb-5">
          <h2 class="text-lg font-bold text-slate-100">🔮 Crystal Ball</h2>
          <button id="close-predict-modal" class="text-slate-500 hover:text-slate-300 text-2xl leading-none">&times;</button>
        </div>
        <p class="text-xs text-slate-500 mb-5 text-center">${data?.job_title || job.title}</p>

        <!-- Crystal ball visualization -->
        <div style="display:flex;align-items:center;justify-content:center;margin-bottom:1.5rem;">
          <div style="position:relative;width:140px;height:140px;flex-shrink:0;">
            <svg width="140" height="140" viewBox="0 0 140 140">
              <defs>
                <radialGradient id="ballGrad" cx="38%" cy="35%" r="60%">
                  <stop offset="0%" stop-color="#818cf8" stop-opacity="0.9"/>
                  <stop offset="40%" stop-color="#6366f1" stop-opacity="0.7"/>
                  <stop offset="100%" stop-color="#1e1b4b" stop-opacity="0.95"/>
                </radialGradient>
                <radialGradient id="glowGrad" cx="50%" cy="50%" r="50%">
                  <stop offset="0%" stop-color="#818cf8" stop-opacity="0.25"/>
                  <stop offset="100%" stop-color="#818cf8" stop-opacity="0"/>
                </radialGradient>
              </defs>
              <circle cx="70" cy="70" r="68" fill="url(#glowGrad)" style="animation:crystalPulse 2s ease-in-out infinite;"/>
              <circle cx="70" cy="70" r="58" fill="url(#ballGrad)" stroke="#6366f1" stroke-width="1" stroke-opacity="0.4"/>
              <ellipse cx="52" cy="50" rx="12" ry="7" fill="white" fill-opacity="0.12" transform="rotate(-30 52 50)"/>
            </svg>
            <div style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;flex-direction:column;">
              <div id="prob-num" style="font-size:2rem;font-weight:800;color:#e0e7ff;line-height:1;text-shadow:0 0 20px rgba(99,102,241,0.8);">0%</div>
              <div style="font-size:0.6rem;color:#818cf8;letter-spacing:0.1em;margin-top:2px;text-transform:uppercase;">${pred.confidence || 'medium'}</div>
            </div>
          </div>
        </div>

        <!-- Probability bar -->
        <div style="margin-bottom:1.25rem;">
          <div style="background:#1e293b;border-radius:9999px;height:8px;overflow:hidden;">
            <div id="prob-bar" style="height:100%;width:0%;background:${barColor};border-radius:9999px;transition:width 1.2s cubic-bezier(0.34,1.56,0.64,1);"></div>
          </div>
          <div style="display:flex;justify-content:space-between;margin-top:0.4rem;">
            <span style="font-size:0.7rem;color:#475569;">Low</span>
            <span style="font-size:0.7rem;color:${barColor};font-weight:600;">${prob}% success probability</span>
            <span style="font-size:0.7rem;color:#475569;">High</span>
          </div>
        </div>

        <!-- Timeline assessment -->
        <div style="display:flex;justify-content:center;margin-bottom:1.25rem;">
          <span style="background:#1e293b;border:1px solid #334155;border-radius:9999px;padding:0.25rem 0.875rem;font-size:0.75rem;color:#cbd5e1;">${tlIcon} ${(pred.timeline_assessment || 'on_track').replace(/_/g, ' ')}</span>
        </div>

        <!-- Risk factors -->
        ${(pred.risk_factors || []).length ? `
        <div style="margin-bottom:1rem;">
          <h4 style="font-size:0.75rem;font-weight:700;color:#f87171;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:0.5rem;">Risk Factors</h4>
          <div class="space-y-1.5">
            ${pred.risk_factors.map(f => {
              const ic = { low: '#22c55e', medium: '#f59e0b', high: '#ef4444' }[f.impact] || '#94a3b8';
              return `<div style="display:flex;gap:0.75rem;align-items:flex-start;border-left:3px solid ${ic};padding-left:0.75rem;background:rgba(15,23,42,0.4);padding:0.5rem 0.75rem;border-radius:0 0.375rem 0.375rem 0;">
                <div>
                  <span style="font-size:0.75rem;font-weight:600;color:#e2e8f0;">${f.factor}</span>
                  <span style="font-size:0.65rem;color:${ic};margin-left:0.5rem;text-transform:uppercase;">${f.impact}</span>
                  <p style="font-size:0.7rem;color:#64748b;margin-top:0.15rem;">${f.detail}</p>
                </div>
              </div>`;
            }).join('')}
          </div>
        </div>` : ''}

        <!-- Positive factors -->
        ${(pred.positive_factors || []).length ? `
        <div style="margin-bottom:1rem;">
          <h4 style="font-size:0.75rem;font-weight:700;color:#4ade80;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:0.5rem;">Positive Factors</h4>
          <div class="space-y-1">
            ${pred.positive_factors.map(f => `
              <div style="font-size:0.75rem;color:#86efac;padding:0.35rem 0.75rem;background:rgba(34,197,94,0.07);border-radius:0.375rem;border:1px solid rgba(34,197,94,0.15);">
                ✓ <strong>${f.factor}</strong> — ${f.detail}
              </div>`).join('')}
          </div>
        </div>` : ''}

        <!-- Recommendation -->
        ${pred.recommendation ? `
        <div style="background:rgba(217,119,6,0.08);border:1px solid rgba(217,119,6,0.25);border-radius:0.5rem;padding:0.75rem 1rem;">
          <span style="font-size:0.7rem;font-weight:700;color:#fbbf24;text-transform:uppercase;letter-spacing:0.05em;display:block;margin-bottom:0.3rem;">Recommendation</span>
          <p style="font-size:0.8rem;color:#fde68a;">${pred.recommendation}</p>
        </div>` : ''}`);

      modal.querySelector('#close-predict-modal')?.addEventListener('click', () => modal.remove());

      // Animate the ball count-up and probability bar
      setTimeout(() => {
        const probNum = document.getElementById('prob-num');
        const probBar = document.getElementById('prob-bar');
        if (probNum) {
          const start = performance.now();
          requestAnimationFrame(function step(now) {
            const t = Math.min((now - start) / 1400, 1);
            const eased = 1 - Math.pow(1 - t, 3);
            probNum.textContent = Math.round(eased * prob) + '%';
            if (t < 1) requestAnimationFrame(step);
          });
        }
        if (probBar) setTimeout(() => { probBar.style.width = prob + '%'; }, 100);
      }, 50);

    } catch (err) {
      toast(err.message, 'error');
    } finally {
      btn.disabled = false;
      btn.textContent = '🔮 Predict';
    }
  });

  // Run Agent button
  document.getElementById('run-agent-btn').addEventListener('click', async () => {
    const btn = document.getElementById('run-agent-btn');
    btn.disabled = true;

    const limits = buildOrchestrateLimits();

    if (liveMode) {
      // Live mode: SSE stream
      const mc = showMissionControlOverlay(job.title);
      const baseUrl = api.getBaseUrl();
      const params = new URLSearchParams({ max_specialist_agents: limits.max_specialist_agents || 3 });
      if (limits.max_llm_rounds) params.set('max_llm_rounds', limits.max_llm_rounds);
      const es = new EventSource(`${baseUrl}/orchestrate/stream/${jobId}?${params}`);

      es.onmessage = (e) => {
        try {
          const event = JSON.parse(e.data);
          mc.appendLog(event);
          if (event.type === 'done') {
            es.close();
            mc.complete(event.success, event.summary);
            setTimeout(async () => {
              hideMissionControlOverlay();
              if (event.success) {
                toast(`✓ Agents completed — ${event.tool_calls_count || 0} tool calls`, 'success');
                await renderJobDetail(container, jobId);
              } else {
                toast(event.error || 'Agent failed', 'error');
                btn.disabled = false;
              }
            }, 2000);
          }
        } catch { /* ignore parse errors */ }
      };

      es.onerror = () => {
        es.close();
        mc.complete(false);
        setTimeout(() => {
          hideMissionControlOverlay();
          toast('Connection lost or agent error', 'error');
          btn.disabled = false;
        }, 1500);
      };
    } else {
      // Standard mode: blocking call with spinner
      const overlay = showAgentOverlay(job.title);
      try {
        const result = await api.orchestrate.run(jobId, null, limits);
        hideAgentOverlay();
        toast(`✓ Agents completed — ${result?.tool_calls_count || 0} tool calls made`, 'success');

        if (result?.summary) {
          const summaryEl = document.createElement('div');
          summaryEl.className = 'card p-4 mb-4';
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

        await renderJobDetail(container, jobId);
      } catch (err) {
        hideAgentOverlay();
        toast(err.message, 'error');
        btn.disabled = false;
      }
    }
  });
}
