import { api } from '../api.js';
import { formatDate, priorityBadge, showModal, statusBadge, toast } from '../components.js';

export async function renderJobs(container) {
  container.innerHTML = `
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
      <button id="new-job-btn" class="btn-primary flex items-center gap-2">
        <span class="text-lg leading-none">+</span> New Job
      </button>
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

  await loadJobs();
}
