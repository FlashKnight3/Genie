const BASE = 'http://localhost:8000';

let client = null;
let initPromise = null;

/** @type {Record<string, unknown> | null} */
export let lastPublicConfig = null;

function oauthRedirectUrl() {
  const { origin, pathname } = window.location;
  if (pathname.startsWith('/app')) return `${origin}/app/`;
  return `${origin}/`;
}

export async function initSupabase() {
  if (initPromise) return initPromise;
  initPromise = (async () => {
    try {
      const res = await fetch(`${BASE}/api/config`);
      if (!res.ok) {
        lastPublicConfig = null;
        return null;
      }
      const cfg = await res.json();
      lastPublicConfig = cfg;
      if (!cfg.supabase_url || !cfg.supabase_anon_key) {
        client = null;
        return null;
      }
      const { createClient } = await import('https://esm.sh/@supabase/supabase-js@2');
      client = createClient(cfg.supabase_url, cfg.supabase_anon_key, {
        auth: {
          flowType: 'pkce',
          detectSessionInUrl: true,
          persistSession: true,
          autoRefreshToken: true,
        },
      });
    } catch (e) {
      console.warn('Supabase client not initialized', e);
      lastPublicConfig = null;
    }
    return client;
  })();
  return initPromise;
}

export function getSupabase() {
  return client;
}

/**
 * @param {string} provider e.g. google, github, azure
 */
export async function signInWithOAuthProvider(provider) {
  const sb = client;
  if (!sb) throw new Error('Supabase is not configured');
  const { error } = await sb.auth.signInWithOAuth({
    provider,
    options: { redirectTo: oauthRedirectUrl() },
  });
  if (error) throw error;
}

/**
 * Enterprise SAML / OIDC via Supabase SSO (requires project SSO + domain registered).
 * @param {string} domain e.g. acme.com
 */
export async function signInWithEnterpriseSSO(domain) {
  const sb = client;
  if (!sb) throw new Error('Supabase is not configured');
  const { error } = await sb.auth.signInWithSSO({ domain: domain.trim() });
  if (error) throw error;
}

export async function signOut() {
  const sb = client;
  if (!sb) return;
  await sb.auth.signOut();
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
