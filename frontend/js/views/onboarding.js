import { api } from '../api.js';

/**
 * @param {HTMLElement} root
 * @param {() => void} onComplete
 */
export async function renderOnboarding(root, onComplete) {
  root.innerHTML = `
    <div class="min-h-screen flex items-center justify-center p-6" style="background:#0a1120">
      <div class="card max-w-lg w-full p-8 border-slate-600">
        <h1 class="text-xl font-semibold text-slate-100 mb-1">Welcome to Genie</h1>
        <p class="text-slate-500 text-sm mb-6">Tell us a bit about your workspace to finish setup.</p>
        <div id="onb-error" class="hidden text-red-400 text-sm mb-4 p-3 rounded-lg bg-red-950/40 border border-red-900"></div>
        <form id="onb-form" class="space-y-4">
          <div>
            <label class="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Your name</label>
            <input class="input" name="display_name" type="text" required placeholder="Jane Contractor" autocomplete="name" />
          </div>
          <div>
            <label class="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Company</label>
            <input class="input" name="company_name" type="text" required placeholder="Acme Builders" autocomplete="organization" />
          </div>
          <button type="submit" class="btn-primary w-full mt-2" id="onb-submit">Continue to app</button>
        </form>
      </div>
    </div>`;

  const form = root.querySelector('#onb-form');
  const errEl = root.querySelector('#onb-error');
  const submitBtn = root.querySelector('#onb-submit');

  form?.addEventListener('submit', async (ev) => {
    ev.preventDefault();
    errEl?.classList.add('hidden');
    const fd = new FormData(form);
    const display_name = String(fd.get('display_name') || '').trim();
    const company_name = String(fd.get('company_name') || '').trim();
    if (!display_name || !company_name) return;
    submitBtn.disabled = true;
    try {
      await api.profile.update({
        display_name,
        company_name,
        onboarding_completed: true,
      });
      onComplete();
    } catch (e) {
      errEl.textContent = e.message || 'Could not save profile';
      errEl.classList.remove('hidden');
      submitBtn.disabled = false;
    }
  });
}
