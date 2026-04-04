const BASE = 'http://localhost:8000';

async function apiFetch(path, options = {}) {
  const res = await fetch(BASE + path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  const json = await res.json();
  if (!res.ok) throw new Error(json.detail || json.message || 'Request failed');
  return json.data;
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
    run: (jobId, task) =>
      apiFetch('/orchestrate', { method: 'POST', body: JSON.stringify({ job_id: jobId, task: task || null }) }),
    logs: (limit = 50) => apiFetch(`/orchestrate/logs?limit=${limit}`),
    risks: () => apiFetch('/orchestrate/risks'),
    messages: (jobId) => apiFetch(`/orchestrate/messages/${jobId}`),
  },
};
