import { api } from '../api.js';
import { availabilityBadge, ratingStars, skillChips, showModal, toast } from '../components.js';

export async function renderSubcontractors(container) {
  container.innerHTML = `
    <div class="flex items-center justify-between mb-6">
      <div class="flex items-center gap-3">
        <select id="filter-avail" class="input w-44 text-sm">
          <option value="">All Availability</option>
          <option value="available">Available</option>
          <option value="busy">Busy</option>
          <option value="unavailable">Unavailable</option>
        </select>
        <input id="filter-skill" class="input w-52 text-sm" placeholder="Filter by skill…" />
      </div>
      <button id="add-sub-btn" class="btn-primary flex items-center gap-2">
        <span class="text-lg leading-none">+</span> Add Subcontractor
      </button>
    </div>
    <div class="card overflow-hidden">
      <div id="sub-table-container"></div>
    </div>`;

  async function loadSubs() {
    const avail = document.getElementById('filter-avail').value;
    const skill = document.getElementById('filter-skill').value;
    const data = await api.subcontractors.list({
      availability: avail || null,
      skills: skill || null,
    });
    renderTable(data?.subcontractors || []);
  }

  function renderTable(subs) {
    const tc = document.getElementById('sub-table-container');
    if (!subs.length) {
      tc.innerHTML = `<div class="p-12 text-center text-slate-500"><div class="text-3xl mb-3">👷</div><p>No subcontractors found.</p></div>`;
      return;
    }
    tc.innerHTML = `<table>
      <thead><tr>
        <th>Name</th><th>Location</th><th>Skills</th><th>Rating</th>
        <th>Rate/hr</th><th>Availability</th><th>Jobs Done</th>
      </tr></thead>
      <tbody>
        ${subs.map(s => `
          <tr data-id="${s.id}">
            <td>
              <div class="font-medium text-slate-100">${s.name}</div>
              <div class="text-xs text-slate-500">${s.email}</div>
            </td>
            <td>${s.location}</td>
            <td><div class="flex flex-wrap gap-0.5">${skillChips(s.skills)}</div></td>
            <td>${ratingStars(s.rating)}</td>
            <td class="text-slate-300">$${s.hourly_rate}/hr</td>
            <td>${availabilityBadge(s.availability_status)}</td>
            <td class="text-slate-400">${s.completed_jobs}</td>
          </tr>`).join('')}
      </tbody>
    </table>`;

    tc.querySelectorAll('tbody tr').forEach(row => {
      row.addEventListener('click', async () => {
        const id = row.dataset.id;
        const sub = subs.find(s => s.id === id);
        if (!sub) return;
        showModal(`
          <div class="flex items-center justify-between mb-5">
            <h2 class="text-lg font-bold text-slate-100">${sub.name}</h2>
            <button id="close-sub-modal" class="text-slate-500 hover:text-slate-300 text-2xl leading-none">&times;</button>
          </div>
          <div class="space-y-4">
            <div class="grid grid-cols-2 gap-4">
              <div>
                <p class="text-xs text-slate-500 mb-1">Email</p>
                <p class="text-sm text-slate-200">${sub.email}</p>
              </div>
              <div>
                <p class="text-xs text-slate-500 mb-1">Phone</p>
                <p class="text-sm text-slate-200">${sub.phone}</p>
              </div>
              <div>
                <p class="text-xs text-slate-500 mb-1">Location</p>
                <p class="text-sm text-slate-200">${sub.location}</p>
              </div>
              <div>
                <p class="text-xs text-slate-500 mb-1">Hourly Rate</p>
                <p class="text-sm text-slate-200">$${sub.hourly_rate}/hr</p>
              </div>
            </div>
            <div>
              <p class="text-xs text-slate-500 mb-2">Skills</p>
              <div class="flex flex-wrap gap-1">${skillChips(sub.skills)}</div>
            </div>
            <div class="grid grid-cols-3 gap-4 p-4 rounded-lg bg-slate-900">
              <div class="text-center">
                <p class="text-2xl font-bold text-slate-100">${sub.rating.toFixed(1)}</p>
                <p class="text-xs text-slate-500">Rating</p>
              </div>
              <div class="text-center">
                <p class="text-2xl font-bold text-slate-100">${sub.completed_jobs}</p>
                <p class="text-xs text-slate-500">Jobs Done</p>
              </div>
              <div class="text-center">
                <div class="mt-1">${availabilityBadge(sub.availability_status)}</div>
                <p class="text-xs text-slate-500 mt-1">Status</p>
              </div>
            </div>
          </div>`);
        document.getElementById('close-sub-modal')?.addEventListener('click', () =>
          document.querySelector('.modal-overlay')?.remove()
        );
      });
    });
  }

  // Filters
  document.getElementById('filter-avail').addEventListener('change', loadSubs);
  document.getElementById('filter-skill').addEventListener('input', loadSubs);

  // Add subcontractor modal
  document.getElementById('add-sub-btn').addEventListener('click', () => {
    const overlay = showModal(`
      <div class="flex items-center justify-between mb-5">
        <h2 class="text-lg font-bold text-slate-100">Add Subcontractor</h2>
        <button id="close-modal" class="text-slate-500 hover:text-slate-300 text-2xl leading-none">&times;</button>
      </div>
      <form id="add-sub-form" class="space-y-4">
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-xs font-semibold text-slate-400 mb-1.5">Full Name *</label>
            <input name="name" class="input" required />
          </div>
          <div>
            <label class="block text-xs font-semibold text-slate-400 mb-1.5">Email *</label>
            <input name="email" type="email" class="input" required />
          </div>
          <div>
            <label class="block text-xs font-semibold text-slate-400 mb-1.5">Phone *</label>
            <input name="phone" class="input" placeholder="512-555-0100" required />
          </div>
          <div>
            <label class="block text-xs font-semibold text-slate-400 mb-1.5">Location *</label>
            <input name="location" class="input" placeholder="Austin, TX" required />
          </div>
          <div>
            <label class="block text-xs font-semibold text-slate-400 mb-1.5">Hourly Rate ($) *</label>
            <input name="hourly_rate" type="number" class="input" placeholder="75" required />
          </div>
          <div>
            <label class="block text-xs font-semibold text-slate-400 mb-1.5">Initial Rating</label>
            <input name="rating" type="number" step="0.1" min="0" max="5" class="input" placeholder="4.0" />
          </div>
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1.5">Skills (comma-separated) *</label>
          <input name="skills" class="input" placeholder="electrical, wiring, panel upgrades" required />
        </div>
        <div class="flex gap-3 pt-2">
          <button type="submit" class="btn-primary flex-1">Add Subcontractor</button>
          <button type="button" id="cancel-btn" class="btn-ghost flex-1">Cancel</button>
        </div>
      </form>`);

    overlay.querySelector('#close-modal').addEventListener('click', () => overlay.remove());
    overlay.querySelector('#cancel-btn').addEventListener('click', () => overlay.remove());

    overlay.querySelector('#add-sub-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      const fd = new FormData(e.target);
      try {
        await api.subcontractors.create({
          name: fd.get('name'),
          email: fd.get('email'),
          phone: fd.get('phone'),
          location: fd.get('location'),
          hourly_rate: parseFloat(fd.get('hourly_rate')),
          rating: parseFloat(fd.get('rating') || '4.0'),
          skills: fd.get('skills').split(',').map(s => s.trim()).filter(Boolean),
        });
        overlay.remove();
        toast('Subcontractor added!');
        await loadSubs();
      } catch (err) {
        toast(err.message, 'error');
      }
    });
  });

  await loadSubs();
}
