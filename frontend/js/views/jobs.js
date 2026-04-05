import { api } from '../api.js';
import { formatDate, priorityBadge, showModal, skillChips, statusBadge, toast } from '../components.js';

export async function renderJobs(container) {
  container.innerHTML = `
    <!-- Make a Wish panel (collapsible) -->
    <div id="wish-panel" class="hidden mb-6">
      <div id="wish-container" class="card p-6" style="border-color:rgba(217,119,6,0.4); background:rgba(15,23,42,0.8);">
        <div class="flex items-start gap-4">
          <div style="font-size:2.5rem;line-height:1;flex-shrink:0;filter:drop-shadow(0 0 8px rgba(217,119,6,0.6));">🪄</div>
          <div class="flex-1">
            <h3 class="text-base font-bold mb-1" style="background:linear-gradient(135deg,#fbbf24,#d97706);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;">Make a Wish</h3>
            <p class="text-xs text-slate-500 mb-3">Describe any job in plain English and Genie will create it for you.</p>
            <textarea id="wish-input" class="input text-sm" rows="3"
              placeholder="e.g. I need a plumber in Austin to fix a leaking pipe under the sink, budget around $400, need it done this week"
              style="border-color:rgba(217,119,6,0.3);resize:none;"></textarea>
            <div class="flex items-center gap-3 mt-3">
              <button id="wish-submit-btn" class="flex items-center gap-2 px-5 py-2 rounded-lg text-sm font-semibold cursor-pointer" style="background:linear-gradient(135deg,#d97706,#b45309);color:#fff;border:none;transition:opacity 0.15s;">
                ✨ Grant My Wish
              </button>
              <button id="wish-cancel-btn" class="btn-ghost text-sm py-2">Cancel</button>
            </div>
            <div id="wish-result" class="hidden mt-4 p-4 rounded-lg" style="background:#0f172a;border:1px solid rgba(34,197,94,0.3);"></div>
          </div>
        </div>
      </div>
    </div>

    <div class="flex items-center justify-between mb-6">
      <div class="flex items-center gap-3">
        <select id="filter-status" class="input w-40 text-sm">
          <option value="">All Statuses</option>
          <option>pending</option><option>matching</option><option>assigned</option>
          <option>in_progress</option><option>completed</option><option>at_risk</option>
          <option>rescheduled</option><option>cancelled</option>
        </select>
        <select id="filter-priority" class="input w-36 text-sm">
          <option value="">All Priorities</option>
          <option>low</option><option>medium</option><option>high</option><option>critical</option>
        </select>
        <input id="filter-search" class="input w-52 text-sm" placeholder="Search jobs…" />
      </div>
      <div class="flex items-center gap-2">
        <button id="wish-toggle-btn" class="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold cursor-pointer" style="background:linear-gradient(135deg,rgba(217,119,6,0.2),rgba(180,83,9,0.2));color:#fbbf24;border:1px solid rgba(217,119,6,0.35);transition:all 0.15s;">
          🪄 Make a Wish
        </button>
        <button id="new-job-btn" class="btn-primary flex items-center gap-2">
          <span class="text-lg leading-none">+</span> New Job
        </button>
      </div>
    </div>
    <div class="card overflow-hidden">
      <div id="jobs-table-container"></div>
    </div>`;

  let allJobs = [];

  async function loadJobs() {
    const status = document.getElementById('filter-status').value;
    const priority = document.getElementById('filter-priority').value;
    const data = await api.jobs.list({ status, priority });
    allJobs = data?.jobs || [];
    renderTable(allJobs);
  }

  function renderTable(jobs) {
    const search = document.getElementById('filter-search')?.value?.toLowerCase() || '';
    const filtered = search ? jobs.filter(j =>
      j.title.toLowerCase().includes(search) || j.location.toLowerCase().includes(search)
    ) : jobs;

    const tc = document.getElementById('jobs-table-container');
    if (!filtered.length) {
      tc.innerHTML = `<div class="p-12 text-center text-slate-500">
        <div class="text-3xl mb-3">📋</div>
        <p>No jobs found. Adjust filters or create a new job.</p>
      </div>`;
      return;
    }

    tc.innerHTML = `<table>
      <thead><tr>
        <th>Title</th><th>Location</th><th>Priority</th><th>Status</th>
        <th>Budget</th><th>Start Date</th><th>End Date</th>
      </tr></thead>
      <tbody>
        ${filtered.map(j => `
          <tr data-id="${j.id}" class="cursor-pointer">
            <td class="font-medium text-slate-100">${j.title}</td>
            <td>${j.location}</td>
            <td>${priorityBadge(j.priority)}</td>
            <td>${statusBadge(j.status)}</td>
            <td>$${j.budget.toLocaleString()}</td>
            <td>${formatDate(j.start_date)}</td>
            <td>${formatDate(j.end_date)}</td>
          </tr>`).join('')}
      </tbody>
    </table>`;

    tc.querySelectorAll('tbody tr').forEach(row => {
      row.addEventListener('click', () => {
        window.location.hash = `#job/${row.dataset.id}`;
      });
    });
  }

  // Filters
  ['filter-status', 'filter-priority'].forEach(id =>
    document.getElementById(id)?.addEventListener('change', loadJobs)
  );
  document.getElementById('filter-search')?.addEventListener('input', () => renderTable(allJobs));

  // New job modal
  document.getElementById('new-job-btn').addEventListener('click', () => {
    const overlay = showModal(`
      <div class="flex items-center justify-between mb-5">
        <h2 class="text-lg font-bold text-slate-100">Create New Job</h2>
        <button id="close-modal" class="text-slate-500 hover:text-slate-300 text-2xl leading-none">&times;</button>
      </div>
      <form id="new-job-form" class="space-y-4">
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1.5">Job Title *</label>
          <input name="title" class="input" placeholder="e.g. Electrical Panel Upgrade" required />
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1.5">Description *</label>
          <textarea name="description" class="input" rows="3" placeholder="Describe the work to be done…" required></textarea>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-xs font-semibold text-slate-400 mb-1.5">Location *</label>
            <input name="location" class="input" placeholder="e.g. Austin, TX" required />
          </div>
          <div>
            <label class="block text-xs font-semibold text-slate-400 mb-1.5">Budget ($) *</label>
            <input name="budget" type="number" class="input" placeholder="5000" required />
          </div>
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1.5">Required Skills (comma-separated)</label>
          <input name="skills" class="input" placeholder="electrical, wiring, panel upgrades" />
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-xs font-semibold text-slate-400 mb-1.5">Start Date</label>
            <input name="start_date" type="date" class="input" />
          </div>
          <div>
            <label class="block text-xs font-semibold text-slate-400 mb-1.5">End Date</label>
            <input name="end_date" type="date" class="input" />
          </div>
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1.5">Priority</label>
          <select name="priority" class="input">
            <option value="low">Low</option>
            <option value="medium" selected>Medium</option>
            <option value="high">High</option>
            <option value="critical">Critical</option>
          </select>
        </div>
        <div class="flex gap-3 pt-2">
          <button type="submit" class="btn-primary flex-1">Create Job</button>
          <button type="button" id="cancel-btn" class="btn-ghost flex-1">Cancel</button>
        </div>
      </form>`);

    overlay.querySelector('#close-modal').addEventListener('click', () => overlay.remove());
    overlay.querySelector('#cancel-btn').addEventListener('click', () => overlay.remove());

    overlay.querySelector('#new-job-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      const fd = new FormData(e.target);
      const skills = fd.get('skills').split(',').map(s => s.trim()).filter(Boolean);
      try {
        await api.jobs.create({
          title: fd.get('title'),
          description: fd.get('description'),
          location: fd.get('location'),
          budget: parseFloat(fd.get('budget')),
          required_skills: skills,
          start_date: fd.get('start_date') || null,
          end_date: fd.get('end_date') || null,
          priority: fd.get('priority'),
        });
        overlay.remove();
        toast('Job created successfully!');
        await loadJobs();
      } catch (err) {
        toast(err.message, 'error');
      }
    });
  });

  // Make a Wish toggle
  document.getElementById('wish-toggle-btn').addEventListener('click', () => {
    const panel = document.getElementById('wish-panel');
    panel.classList.toggle('hidden');
    if (!panel.classList.contains('hidden')) {
      document.getElementById('wish-input').focus();
    }
  });

  document.getElementById('wish-cancel-btn').addEventListener('click', () => {
    document.getElementById('wish-panel').classList.add('hidden');
    document.getElementById('wish-input').value = '';
    document.getElementById('wish-result').classList.add('hidden');
  });

  document.getElementById('wish-submit-btn').addEventListener('click', async () => {
    const input = document.getElementById('wish-input');
    const wish = input.value.trim();
    if (!wish) { toast('Please describe your job first.', 'error'); return; }

    const btn = document.getElementById('wish-submit-btn');
    const container = document.getElementById('wish-container');
    const resultEl = document.getElementById('wish-result');

    btn.disabled = true;
    btn.textContent = '⏳ Summoning Genie…';
    resultEl.classList.add('hidden');

    try {
      const data = await api.wishes.make(wish);
      const p = data?.parsed || {};
      const job = data?.job || {};

      // Wish granted animation
      container.classList.add('wish-granted');
      setTimeout(() => container.classList.remove('wish-granted'), 800);

      resultEl.classList.remove('hidden');
      resultEl.innerHTML = `
        <div class="flex items-center gap-2 mb-3">
          <span class="text-green-400 font-semibold text-sm">✓ Wish Granted!</span>
        </div>
        <div class="grid grid-cols-2 gap-3 text-xs">
          <div><span class="text-slate-500">Title:</span> <span class="text-slate-200 font-medium">${p.title || job.title || '—'}</span></div>
          <div><span class="text-slate-500">Location:</span> <span class="text-slate-200">${p.location || '—'}</span></div>
          <div><span class="text-slate-500">Budget:</span> <span class="text-slate-200">$${(p.budget || 0).toLocaleString()}</span></div>
          <div><span class="text-slate-500">Priority:</span> <span class="text-slate-200">${p.priority || 'medium'}</span></div>
          <div><span class="text-slate-500">Start:</span> <span class="text-slate-200">${p.start_date || '—'}</span></div>
          <div><span class="text-slate-500">End:</span> <span class="text-slate-200">${p.end_date || '—'}</span></div>
        </div>
        <div class="mt-2 flex flex-wrap gap-1">${(p.required_skills || []).map(s => `<span class="skill-chip">${s}</span>`).join('')}</div>
        <div class="mt-3 flex gap-2">
          <a href="#job/${job.id}" class="btn-primary text-xs py-1.5 px-3">View Job →</a>
          <button id="wish-another-btn" class="btn-ghost text-xs py-1.5 px-3">Make Another</button>
        </div>`;

      document.getElementById('wish-another-btn')?.addEventListener('click', () => {
        input.value = '';
        resultEl.classList.add('hidden');
        input.focus();
      });

      toast(`✨ Job "${p.title || 'New job'}" created!`, 'success');
      await loadJobs();
    } catch (err) {
      toast(err.message, 'error');
    } finally {
      btn.disabled = false;
      btn.textContent = '✨ Grant My Wish';
    }
  });

  await loadJobs();
}
