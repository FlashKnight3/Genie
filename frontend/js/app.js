import { api } from './api.js';
import { renderDashboard } from './views/dashboard.js';
import { renderJobs } from './views/jobs.js';
import { renderJobDetail } from './views/job_detail.js';
import { renderSubcontractors } from './views/subcontractors.js';
import { renderSchedule } from './views/schedule.js';
import { renderRisks } from './views/risks.js';
import { renderLogs } from './views/logs.js';

const PAGE_TITLES = {
  dashboard: 'Dashboard',
  jobs: 'Jobs',
  subcontractors: 'Subcontractors',
  schedule: 'Schedule',
  risks: 'Risks',
  logs: 'Agent Logs',
};

function getRoute() {
  const hash = window.location.hash.slice(1) || 'dashboard';
  if (hash.startsWith('job/')) return { page: 'job_detail', id: hash.slice(4) };
  return { page: hash };
}

async function route() {
  const { page, id } = getRoute();
  const content = document.getElementById('main-content');
  const titleEl = document.getElementById('page-title');

  // Update nav active state
  document.querySelectorAll('.nav-item').forEach(el => {
    el.classList.remove('active');
    const href = el.getAttribute('href')?.slice(1);
    if (href === page || (page === 'job_detail' && href === 'jobs')) {
      el.classList.add('active');
    }
  });

  // Set page title
  titleEl.textContent = PAGE_TITLES[page] || 'Genie';

  // Render view
  try {
    switch (page) {
      case 'dashboard':       await renderDashboard(content); break;
      case 'jobs':            await renderJobs(content); break;
      case 'job_detail':      await renderJobDetail(content, id); break;
      case 'subcontractors':  await renderSubcontractors(content); break;
      case 'schedule':        await renderSchedule(content); break;
      case 'risks':           await renderRisks(content); break;
      case 'logs':            await renderLogs(content); break;
      default:                await renderDashboard(content);
    }
  } catch (err) {
    content.innerHTML = `
      <div class="card p-8 text-center">
        <p class="text-red-400 text-lg font-semibold mb-2">Failed to load page</p>
        <p class="text-slate-400 text-sm">${err.message}</p>
        <p class="text-slate-600 text-xs mt-3">Make sure the server is running: <code>python3 -m uvicorn main:app --reload</code></p>
      </div>`;
  }
}

async function checkServerHealth() {
  const statusEl = document.getElementById('server-status');
  try {
    await api.health();
    statusEl.innerHTML = '<span class="w-2 h-2 rounded-full bg-green-400"></span> Connected';
    statusEl.className = 'flex items-center gap-2 text-xs text-green-400';
  } catch {
    statusEl.innerHTML = '<span class="w-2 h-2 rounded-full bg-red-400"></span> Server offline';
    statusEl.className = 'flex items-center gap-2 text-xs text-red-400';
  }
}

export function initApp() {
  window.addEventListener('hashchange', route);
  checkServerHealth();
  setInterval(checkServerHealth, 15000);

  // Default to dashboard
  if (!window.location.hash) window.location.hash = '#dashboard';
  route();
}
