import {
  getSupabase,
  lastPublicConfig,
  signInWithEnterpriseSSO,
  signInWithOAuthProvider,
} from '../supabase.js';

const LABELS = {
  google: 'Google',
  github: 'GitHub',
  azure: 'Microsoft',
  gitlab: 'GitLab',
  bitbucket: 'Bitbucket',
};

function labelFor(provider) {
  return LABELS[provider] || provider.charAt(0).toUpperCase() + provider.slice(1);
}

/**
 * @param {HTMLElement} root
 */
export async function renderAuthLogin(root) {
  const cfg = lastPublicConfig || {};
  const providers = Array.isArray(cfg.oauth_providers) ? cfg.oauth_providers : ['google', 'github'];
  const ssoDomain = typeof cfg.sso_domain === 'string' && cfg.sso_domain ? cfg.sso_domain : '';

  root.innerHTML = `
    <div class="min-h-screen flex items-center justify-center p-6" style="background:#0a1120">
      <div class="card max-w-md w-full p-8 border-slate-600">
        <div class="text-center mb-8">
          <div class="text-3xl mb-2">⚡</div>
          <h1 class="text-2xl font-bold text-indigo-400">Genie</h1>
          <p class="text-slate-500 text-sm mt-1">Sign in to continue</p>
        </div>
        <div id="login-error" class="hidden text-red-400 text-sm mb-4 p-3 rounded-lg bg-red-950/40 border border-red-900"></div>
        <div class="space-y-3" id="oauth-buttons"></div>
        ${
          ssoDomain
            ? `<div class="mt-6 pt-6 border-t border-slate-700">
            <p class="text-xs text-slate-500 uppercase tracking-wider mb-3">Enterprise SSO</p>
            <button type="button" id="btn-sso" class="btn-primary w-full">Sign in with SSO</button>
            <p class="text-xs text-slate-600 mt-2">Domain: ${escapeHtml(ssoDomain)}</p>
          </div>`
            : ''
        }
        <p class="text-xs text-slate-600 mt-8 text-center">
          Configure providers in Supabase Dashboard → Authentication → Providers.
          Redirect URL: <code class="text-slate-400">http://localhost:8000/app/</code>
        </p>
      </div>
    </div>`;

  const errEl = root.querySelector('#login-error');
  const oauthHost = root.querySelector('#oauth-buttons');

  function showError(msg) {
    errEl.textContent = msg;
    errEl.classList.remove('hidden');
  }

  for (const p of providers) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'btn-primary w-full';
    btn.textContent = `Continue with ${labelFor(p)}`;
    btn.addEventListener('click', async () => {
      errEl.classList.add('hidden');
      btn.disabled = true;
      try {
        await signInWithOAuthProvider(p);
      } catch (e) {
        showError(e.message || 'Sign-in failed');
        btn.disabled = false;
      }
    });
    oauthHost?.appendChild(btn);
  }

  const ssoBtn = root.querySelector('#btn-sso');
  if (ssoBtn && ssoDomain) {
    ssoBtn.addEventListener('click', async () => {
      errEl.classList.add('hidden');
      ssoBtn.disabled = true;
      try {
        await signInWithEnterpriseSSO(ssoDomain);
      } catch (e) {
        showError(e.message || 'SSO sign-in failed');
        ssoBtn.disabled = false;
      }
    });
  }

  if (!getSupabase()) {
    showError('Supabase URL or anon key is missing. Set SUPABASE_URL and SUPABASE_ANON_KEY on the server.');
  }
}

function escapeHtml(s) {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}
