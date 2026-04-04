const BASE = 'http://localhost:8000';

let client = null;
let initPromise = null;

export async function initSupabase() {
  if (initPromise) return initPromise;
  initPromise = (async () => {
    try {
      const res = await fetch(`${BASE}/api/config`);
      if (!res.ok) return null;
      const cfg = await res.json();
      if (!cfg.supabase_url || !cfg.supabase_anon_key) return null;
      const { createClient } = await import('https://esm.sh/@supabase/supabase-js@2');
      client = createClient(cfg.supabase_url, cfg.supabase_anon_key);
    } catch (e) {
      console.warn('Supabase client not initialized', e);
    }
    return client;
  })();
  return initPromise;
}

export function getSupabase() {
  return client;
}

/**
 * @param {string} table
 * @param {(row: Record<string, unknown>) => void} handler
 * @returns {() => void}
 */
export function subscribePostgresInserts(table, handler) {
  const sb = client;
  if (!sb) return () => {};

  const channel = sb
    .channel(`public:${table}:${Math.random().toString(36).slice(2)}`)
    .on(
      'postgres_changes',
      { event: 'INSERT', schema: 'public', table },
      (payload) => handler(payload.new)
    )
    .subscribe();

  return () => {
    sb.removeChannel(channel);
  };
}
