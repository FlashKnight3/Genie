const BASE = 'http://localhost:8000';

async function authHeaders() {
  try {
    const { getSupabase } = await import('./supabase.js');
    const supabase = getSupabase();
    if (!supabase) return {};
    const {
      data: { session },
    } = await supabase.auth.getSession();
    if (!session?.access_token) return {};
    return { Authorization: `Bearer ${session.access_token}` };
  } catch {
    return {};
  }
}

async function apiFetch(path, options = {}) {
  const auth = await authHeaders();
  const res = await fetch(BASE + path, {
    headers: { 'Content-Type': 'application/json', ...auth, ...options.headers },
    ...options,
  });
  const json = await res.json();
  if (!res.ok) throw new Error(json.detail || json.message || 'Request failed');
  // SuccessResponse wraps payloads in `data`; some routes (e.g. POST /orchestrate) return a flat body
  if (json && typeof json === 'object' && 'data' in json && 'message' in json) return json.data;
  return json;
}

function qs(params) {
  const p = Object.fromEntries(Object.entries(params).filter(([, v]) => v != null && v !== ''));
  return Object.keys(p).length ? '?' + new URLSearchParams(p) : '';
}

export const api = {
  health: () => fetch(BASE + '/health').then(r => r.json()),

  jobs: {
    list: (params = {}) => apiFetch('/jobs' + qs(params)),
    get: (id) => apiFetch(`/jobs/${id}`),
    create: (body) => apiFetch('/jobs', { method: 'POST', body: JSON.stringify(body) }),
    updateStatus: (id, status, notes) =>
      apiFetch(`/jobs/${id}/status`, { method: 'PATCH', body: JSON.stringify({ status, notes }) }),
  },

  subcontractors: {
    list: (params = {}) => apiFetch('/subcontractors' + qs(params)),
    get: (id) => apiFetch(`/subcontractors/${id}`),
    create: (body) => apiFetch('/subcontractors', { method: 'POST', body: JSON.stringify(body) }),
  },

  schedule: {
    all: () => apiFetch('/schedule'),
    forJob: (jobId) => apiFetch(`/schedule/${jobId}`),
  },

  orchestrate: {
    /** @param {Record<string, number | null | undefined>} [limits] max_llm_rounds, max_specialist_agents, max_rounds_per_specialist */
    run: (jobId, task, limits = {}) => {
      const body = { job_id: jobId, task: task || null, ...limits };
      Object.keys(body).forEach((k) => body[k] == null && delete body[k]);
      return apiFetch('/orchestrate', { method: 'POST', body: JSON.stringify(body) });
    },
    logs: (limit = 50) => apiFetch(`/orchestrate/logs?limit=${limit}`),
    risks: () => apiFetch('/orchestrate/risks'),
    messages: (jobId) => apiFetch(`/orchestrate/messages/${jobId}`),
  },

  delays: {
    list: () => apiFetch('/delays'),
    send: (jobId) => apiFetch(`/delays/${jobId}/send`, { method: 'POST' }),
  },

  leads: {
    list: () => apiFetch('/leads'),
    get: (id) => apiFetch(`/leads/${id}`),
    submit: (body) => apiFetch('/leads', { method: 'POST', body: JSON.stringify(body) }),
  },

  quote: {
    draft: (body) => apiFetch('/quote', { method: 'POST', body: JSON.stringify(body) }),
  },
};
