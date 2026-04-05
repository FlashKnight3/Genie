import { api } from '../api.js';
import { formatDate, priorityBadge, toast } from '../components.js';

const COLUMNS = [
  { key: 'pending',     label: 'Pending',     color: '#475569', bg: 'rgba(71,85,105,0.1)'  },
  { key: 'matching',    label: 'Matching',    color: '#3b82f6', bg: 'rgba(59,130,246,0.1)' },
  { key: 'in_progress', label: 'In Progress', color: '#d97706', bg: 'rgba(217,119,6,0.1)'  },
  { key: 'at_risk',     label: 'At Risk',     color: '#ea580c', bg: 'rgba(234,88,12,0.1)'  },
  { key: 'completed',   label: 'Completed',   color: '#16a34a', bg: 'rgba(22,163,74,0.1)'  },
];

// Which DB statuses map to which column
const STATUS_TO_COL = {
  pending:     'pending',
  matching:    'matching',
  assigned:    'in_progress',
  in_progress: 'in_progress',
  at_risk:     'at_risk',
  rescheduled: 'at_risk',
  completed:   'completed',
  cancelled:   'completed',
};

const PRIORITY_BORDER = {
  critical: '#ef4444',
  high:     '#f97316',
  medium:   '#6366f1',
  low:      '#475569',
};

function daysUntil(dateStr) {
  if (!dateStr) return null;
  const diff = new Date(dateStr) - new Date();
  return Math.ceil(diff / (1000 * 60 * 60 * 24));
}

function deadlineBadge(endDate) {
  const d = daysUntil(endDate);
  if (d === null) return '';
  if (d < 0) return `<span style="font-size:0.65rem;color:#f87171;font-weight:600;">⚠ ${Math.abs(d)}d overdue</span>`;
  if (d <= 7) return `<span style="font-size:0.65rem;color:#fb923c;font-weight:600;">⏰ ${d}d left</span>`;
  return `<span style="font-size:0.65rem;color:#475569;">${formatDate(endDate)}</span>`;
}

function cardHtml(job) {
  const borderColor = PRIORITY_BORDER[job.priority] || '#475569';
  return `
    <div class="kanban-card" draggable="true" data-job-id="${job.id}" data-job-status="${job.status}"
         style="border-left: 4px solid ${borderColor}; margin-bottom: 0.625rem;">
      <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:0.5rem;margin-bottom:0.5rem;">
        <p style="font-size:0.8rem;font-weight:600;color:#e2e8f0;line-height:1.3;flex:1;cursor:pointer;" class="kanban-title">${job.title}</p>
        <div style="flex-shrink:0;">${priorityBadge(job.priority)}</div>
      </div>
      <p style="font-size:0.7rem;color:#64748b;margin-bottom:0.5rem;">${job.location}</p>
      <div style="display:flex;align-items:center;justify-content:space-between;gap:0.5rem;">
        <span style="font-size:0.72rem;color:#94a3b8;">$${(job.budget || 0).toLocaleString()}</span>
        ${deadlineBadge(job.end_date)}
      </div>
      ${job.assigned_subcontractor_id ? `
        <div style="margin-top:0.5rem;display:flex;align-items:center;gap:0.4rem;">
          <span style="width:20px;height:20px;border-radius:50%;background:#334155;display:inline-flex;align-items:center;justify-content:center;font-size:0.6rem;color:#94a3b8;flex-shrink:0;font-weight:700;">👷</span>
          <span style="font-size:0.65rem;color:#64748b;">Assigned</span>
        </div>` : `
        <div style="margin-top:0.5rem;">
          <span style="font-size:0.65rem;color:#334155;font-style:italic;">Unassigned</span>
        </div>`}
    </div>`;
}

function columnStats(jobs) {
  const total = jobs.reduce((s, j) => s + (j.budget || 0), 0);
  return { count: jobs.length, total };
}

export async function renderKanban(container) {
  container.innerHTML = `
    <div class="flex items-center justify-between mb-6">
      <div>
        <h2 class="text-lg font-bold text-slate-100">Kanban Board</h2>
        <p class="text-xs text-slate-500 mt-0.5">Drag cards to update job status</p>
      </div>
      <button id="kanban-refresh" class="btn-ghost text-sm py-2 px-3">↺ Refresh</button>
    </div>
    <div id="kanban-board" style="display:flex;gap:1rem;overflow-x:auto;padding-bottom:1rem;min-height:60vh;align-items:flex-start;"></div>`;

  async function loadBoard() {
    const data = await api.jobs.list();
    const jobs = data?.jobs || [];

    // Group jobs into columns
    const grouped = {};
    COLUMNS.forEach(c => { grouped[c.key] = []; });
    jobs.forEach(j => {
      const col = STATUS_TO_COL[j.status];
      if (col && grouped[col]) grouped[col].push(j);
    });

    const board = document.getElementById('kanban-board');
    board.innerHTML = COLUMNS.map(col => {
      const colJobs = grouped[col.key] || [];
      const stats = columnStats(colJobs);
      return `
        <div class="kanban-col" data-col="${col.key}" style="background:${col.bg};border:1px solid ${col.color}30;border-radius:0.75rem;padding:0.875rem;">
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:0.875rem;">
            <div style="display:flex;align-items:center;gap:0.5rem;">
              <span style="width:10px;height:10px;border-radius:50%;background:${col.color};flex-shrink:0;"></span>
              <span style="font-size:0.8rem;font-weight:700;color:#e2e8f0;">${col.label}</span>
              <span style="font-size:0.7rem;color:${col.color};background:${col.bg};border:1px solid ${col.color}40;border-radius:9999px;padding:0.05rem 0.5rem;font-weight:600;">${stats.count}</span>
            </div>
            ${stats.total > 0 ? `<span style="font-size:0.65rem;color:#475569;">$${(stats.total/1000).toFixed(0)}k</span>` : ''}
          </div>
          <div class="kanban-drop-zone" data-col="${col.key}" style="min-height:60px;">
            ${colJobs.map(j => cardHtml(j)).join('')}
          </div>
        </div>`;
    }).join('');

    // Click cards to navigate
    board.querySelectorAll('.kanban-title').forEach(el => {
      el.addEventListener('click', (e) => {
        const card = e.target.closest('[data-job-id]');
        if (card) window.location.hash = `#job/${card.dataset.jobId}`;
      });
    });

    // Drag-and-drop
    let dragJobId = null;
    let dragSourceStatus = null;

    board.querySelectorAll('.kanban-card').forEach(card => {
      card.addEventListener('dragstart', (e) => {
        dragJobId = card.dataset.jobId;
        dragSourceStatus = card.dataset.jobStatus;
        card.classList.add('dragging');
        e.dataTransfer.effectAllowed = 'move';
      });
      card.addEventListener('dragend', () => {
        card.classList.remove('dragging');
        board.querySelectorAll('.kanban-drop-zone').forEach(z => z.classList.remove('kanban-drop-target'));
      });
    });

    board.querySelectorAll('.kanban-drop-zone').forEach(zone => {
      zone.addEventListener('dragover', (e) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        zone.classList.add('kanban-drop-target');
      });
      zone.addEventListener('dragleave', () => {
        zone.classList.remove('kanban-drop-target');
      });
      zone.addEventListener('drop', async (e) => {
        e.preventDefault();
        zone.classList.remove('kanban-drop-target');
        if (!dragJobId) return;

        const targetColKey = zone.dataset.col;
        const col = COLUMNS.find(c => c.key === targetColKey);
        if (!col) return;

        // Map column key to actual status
        const statusMap = {
          pending:     'pending',
          matching:    'matching',
          in_progress: 'in_progress',
          at_risk:     'at_risk',
          completed:   'completed',
        };
        const newStatus = statusMap[targetColKey];
        if (!newStatus || newStatus === dragSourceStatus) return;

        // Find the card and show inline spinner
        const card = board.querySelector(`[data-job-id="${dragJobId}"]`);
        if (card) {
          const orig = card.innerHTML;
          card.innerHTML = `<div style="text-align:center;padding:1rem;"><div class="spinner mx-auto"></div></div>`;
          card.style.opacity = '0.7';

          try {
            await api.jobs.updateStatus(dragJobId, newStatus);
            toast(`Moved to ${col.label}`, 'success');
            await loadBoard();
          } catch (err) {
            card.innerHTML = orig;
            card.style.opacity = '';
            toast(err.message, 'error');
          }
        }
      });
    });
  }

  document.getElementById('kanban-refresh').addEventListener('click', loadBoard);

  await loadBoard();
}
