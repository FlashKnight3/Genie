import { api } from '../api.js';
import { timeAgo } from '../components.js';
import { getSupabase, subscribePostgresInserts } from '../supabase.js';

let leadsRealtimeCleanup = null;

export async function renderLeads(container) {
  if (leadsRealtimeCleanup) {
    leadsRealtimeCleanup();
    leadsRealtimeCleanup = null;
  }
  container.innerHTML = `
    <div class="space-y-6">
      <div class="flex items-center justify-between">
        <div>
          <h2 class="text-lg font-semibold text-slate-100">Leads</h2>
          <p class="text-sm text-slate-500 mt-0.5">AI responds within 60 seconds, owner sees summary cards</p>
        </div>
        <button id="new-lead-btn" class="btn-primary text-sm">+ Submit Test Lead</button>
      </div>
      <div id="leads-list" class="space-y-4">
        <div class="text-slate-500 text-sm">Loading…</div>
      </div>
    </div>`;

  document.getElementById('new-lead-btn').addEventListener('click', () => showLeadForm());

  await loadLeads();

  if (getSupabase()) {
    leadsRealtimeCleanup = subscribePostgresInserts('leads', () => {
      loadLeads();
    });
  }
}

async function loadLeads() {
  const el = document.getElementById('leads-list');
  try {
    const data = await api.leads.list();
    const leads = data?.leads || [];

    if (leads.length === 0) {
      el.innerHTML = `
        <div class="card p-10 text-center">
          <p class="text-4xl mb-3">📥</p>
          <p class="text-slate-400 font-semibold mb-1">No leads yet</p>
          <p class="text-slate-500 text-sm">Submit a test lead above to see AI auto-response in action.</p>
        </div>`;
      return;
    }

    el.innerHTML = leads.map(renderLeadCard).join('');
  } catch (err) {
    el.innerHTML = `<div class="card p-6 text-red-400 text-sm">Failed to load leads: ${err.message}</div>`;
  }
}

function renderLeadCard(lead) {
  const statusColors = {
    new: 'bg-yellow-900 text-yellow-300',
    responded: 'bg-blue-900 text-blue-300',
    qualified: 'bg-indigo-900 text-indigo-300',
    booked: 'bg-green-900 text-green-300',
    lost: 'bg-red-900 text-red-300',
  };
  const statusColor = statusColors[lead.status] || 'bg-slate-700 text-slate-300';

  return `
    <div class="card p-5">
      <div class="flex items-start justify-between gap-4 mb-3">
        <div>
          <div class="flex items-center gap-2 mb-1">
            <span class="font-semibold text-slate-100">${lead.name}</span>
            <span class="text-xs px-2 py-0.5 rounded-full font-semibold ${statusColor}">${lead.status}</span>
            ${lead.auto_reply_sent ? '<span class="text-xs text-green-400">✓ Auto-replied</span>' : ''}
          </div>
          <p class="text-xs text-slate-500">${lead.email}${lead.phone ? ' · ' + lead.phone : ''} · ${timeAgo(lead.received_at)}</p>
        </div>
      </div>

      <div class="bg-slate-900 rounded-lg p-3 mb-3">
        <p class="text-xs text-slate-500 font-semibold uppercase tracking-wide mb-1">Their message</p>
        <p class="text-sm text-slate-300">${lead.message}</p>
      </div>

      ${lead.ai_summary ? `
        <div class="bg-indigo-950 border border-indigo-800 rounded-lg p-3">
          <p class="text-xs text-indigo-400 font-semibold uppercase tracking-wide mb-1">AI Summary</p>
          <p class="text-sm text-slate-300">${lead.ai_summary}</p>
        </div>
      ` : ''}
    </div>`;
}

function showLeadForm() {
  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.innerHTML = `
    <div class="modal">
      <div class="flex items-center justify-between mb-5">
        <h3 class="text-lg font-semibold text-slate-100">Submit Test Lead</h3>
        <button id="close-modal" class="text-slate-500 hover:text-slate-300 text-xl leading-none">×</button>
      </div>
      <div class="space-y-4">
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1.5 uppercase tracking-wide">Name</label>
          <input id="lead-name" class="input" placeholder="Jane Smith" value="Rachel Torres" />
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1.5 uppercase tracking-wide">Email</label>
          <input id="lead-email" class="input" type="email" placeholder="jane@email.com" value="rachel.t@gmail.com" />
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1.5 uppercase tracking-wide">Phone (optional)</label>
          <input id="lead-phone" class="input" placeholder="408-722-1995" value="408-722-1995" />
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1.5 uppercase tracking-wide">Message</label>
          <textarea id="lead-message" class="input" rows="4" placeholder="Tell us about your project…">Hi, I'm looking to renovate my kitchen — new cabinets, countertops, and tile backsplash. My house is in South Austin, about 180 sq ft kitchen. Would love to get a quote this week if possible. Budget is around $25k.</textarea>
        </div>
        <div id="lead-result" class="hidden"></div>
        <button id="submit-lead-btn" class="btn-primary w-full py-2.5">Submit Lead — Watch AI Respond</button>
      </div>
    </div>`;

  document.body.appendChild(overlay);

  overlay.querySelector('#close-modal').addEventListener('click', () => overlay.remove());
  overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.remove(); });

  overlay.querySelector('#submit-lead-btn').addEventListener('click', async () => {
    const btn = overlay.querySelector('#submit-lead-btn');
    const resultEl = overlay.querySelector('#lead-result');

    const name = overlay.querySelector('#lead-name').value.trim();
    const email = overlay.querySelector('#lead-email').value.trim();
    const phone = overlay.querySelector('#lead-phone').value.trim();
    const message = overlay.querySelector('#lead-message').value.trim();

    if (!name || !email || !message) {
      resultEl.className = 'block bg-red-900 text-red-300 text-sm rounded-lg p-3';
      resultEl.textContent = 'Name, email, and message are required.';
      return;
    }

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner mr-2"></span>AI processing…';
    resultEl.className = 'hidden';

    try {
      const res = await api.leads.submit({ name, email, phone: phone || undefined, message });

      resultEl.className = 'block space-y-3';
      resultEl.innerHTML = `
        <div class="bg-green-900 border border-green-700 rounded-lg p-3">
          <p class="text-xs font-semibold text-green-400 uppercase tracking-wide mb-1">✓ Auto-reply sent</p>
          <p class="text-sm text-slate-300 italic">"${res?.auto_reply || ''}"</p>
        </div>
        ${res?.ai_summary ? `
          <div class="bg-indigo-950 border border-indigo-800 rounded-lg p-3">
            <p class="text-xs font-semibold text-indigo-400 uppercase tracking-wide mb-1">Owner summary</p>
            <p class="text-sm text-slate-300">${res.ai_summary}</p>
          </div>
        ` : ''}`;

      btn.textContent = '✓ Done';
      // Reload leads list in background
      setTimeout(() => loadLeads(), 500);
    } catch (err) {
      resultEl.className = 'block bg-red-900 text-red-300 text-sm rounded-lg p-3';
      resultEl.textContent = `Error: ${err.message}`;
      btn.disabled = false;
      btn.textContent = 'Submit Lead — Watch AI Respond';
    }
  });
}
