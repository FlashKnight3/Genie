import { api } from './api.js';
import {
  getSupabase,
  initSupabase,
  lastPublicConfig,
  signOut,
} from './supabase.js';
import { renderAuthLogin } from './views/auth_login.js';
import { renderOnboarding } from './views/onboarding.js';
import { renderDashboard } from './views/dashboard.js';
import { renderJobs } from './views/jobs.js';
import { renderJobDetail } from './views/job_detail.js';
import { renderSubcontractors } from './views/subcontractors.js';
import { renderSchedule } from './views/schedule.js';
import { renderRisks } from './views/risks.js';
import { renderLogs } from './views/logs.js';
import { renderLeads } from './views/leads.js';
import { renderQuote } from './views/quote.js';
import { renderKanban } from './views/kanban.js';

const PAGE_TITLES = {
  dashboard: 'Mission Control',
  jobs: 'Jobs',
  subcontractors: 'Subcontractors',
  schedule: 'Schedule',
  risks: 'Risks',
  logs: 'Agent Logs',
  leads: 'Leads',
  quote: 'Quote Builder',
  kanban: 'Kanban Board',
};

function escapeHtml(s) {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

async function mountAuthHeader() {
  const slot = document.getElementById('auth-header-slot');
  if (!slot) return;
  const cfg = lastPublicConfig || {};
  if (!cfg.auth_required) {
    slot.innerHTML = '';
    return;
  }
  const sb = getSupabase();
  if (!sb) return;
  const {
    data: { session },
  } = await sb.auth.getSession();
  if (!session) return;
  const email = session.user?.email || 'Signed in';
  slot.innerHTML = `<span class="text-xs text-slate-400 truncate max-w-[200px]" title="${escapeHtml(email)}">${escapeHtml(email)}</span>
    <button type="button" class="btn-ghost text-xs py-1 px-2" id="hdr-signout">Sign out</button>`;
  document.getElementById('hdr-signout')?.addEventListener('click', async () => {
    await signOut();
    window.location.reload();
  });
}

/**
 * @returns {Promise<boolean>} true if main app should load
 */
async function runAuthGate() {
  await initSupabase();
  const cfg = lastPublicConfig || {};
  const main = document.getElementById('main-app');
  const authView = document.getElementById('auth-view');

  if (cfg.auth_required) {
    const sb = getSupabase();
    if (!sb) {
      main?.classList.add('hidden');
      authView?.classList.remove('hidden');
      await renderAuthLogin(authView);
      return false;
    }

    const {
      data: { session },
    } = await sb.auth.getSession();
    if (!session) {
      main?.classList.add('hidden');
      authView?.classList.remove('hidden');
      await renderAuthLogin(authView);
      sb.auth.onAuthStateChange((event, sess) => {
        if (event === 'SIGNED_IN' && sess) window.location.reload();
      });
      return false;
    }

    let profile;
    try {
      profile = await api.profile.get();
    } catch (e) {
      main?.classList.add('hidden');
      authView?.classList.remove('hidden');
      authView.innerHTML = `
        <div class="min-h-screen flex items-center justify-center p-6">
          <div class="card max-w-md w-full p-8 border-red-900/50 text-center">
            <p class="text-red-400 font-semibold mb-2">Could not load your profile</p>
            <p class="text-slate-400 text-sm">${escapeHtml(e.message || 'Unknown error')}</p>
            <p class="text-slate-600 text-xs mt-4">Check SUPABASE_JWT_SECRET matches your project and that you are signed in.</p>
          </div>
        </div>`;
      return false;
    }

    if (!profile.onboarding_completed) {
      main?.classList.add('hidden');
      authView?.classList.remove('hidden');
      await renderOnboarding(authView, () => window.location.reload());
      return false;
    }
  }

  main?.classList.remove('hidden');
  authView?.classList.add('hidden');
  return true;
}

function getRoute() {
  const hash = window.location.hash.slice(1) || 'dashboard';
  if (hash.startsWith('job/')) return { page: 'job_detail', id: hash.slice(4) };
  return { page: hash };
}

async function route() {
  const { page, id } = getRoute();
  const content = document.getElementById('main-content');
  const titleEl = document.getElementById('page-title');

  document.querySelectorAll('.nav-item').forEach((el) => {
    el.classList.remove('active');
    const href = el.getAttribute('href')?.slice(1);
    if (href === page || (page === 'job_detail' && href === 'jobs')) {
      el.classList.add('active');
    }
  });

  titleEl.textContent = PAGE_TITLES[page] || 'Genie';

  try {
    switch (page) {
      case 'dashboard':
        await renderDashboard(content);
        break;
      case 'jobs':
        await renderJobs(content);
        break;
      case 'job_detail':
        await renderJobDetail(content, id);
        break;
      case 'subcontractors':
        await renderSubcontractors(content);
        break;
      case 'schedule':
        await renderSchedule(content);
        break;
      case 'risks':
        await renderRisks(content);
        break;
      case 'logs':
        await renderLogs(content);
        break;
      case 'leads':
        await renderLeads(content);
        break;
      case 'quote':
        await renderQuote(content);
        break;
      case 'kanban':
        await renderKanban(content);
        break;
      default:
        await renderDashboard(content);
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

export async function initApp() {
  const ok = await runAuthGate();
  if (!ok) return;

  await mountAuthHeader();

  window.addEventListener('hashchange', route);
  checkServerHealth();
  setInterval(checkServerHealth, 15000);

  if (!window.location.hash) window.location.hash = '#dashboard';
  route();
}
