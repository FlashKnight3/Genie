import { api } from '../api.js';

export async function renderQuote(container) {
  container.innerHTML = `
    <div class="max-w-3xl space-y-6">
      <div>
        <h2 class="text-lg font-semibold text-slate-100">Quote Builder</h2>
        <p class="text-sm text-slate-500 mt-0.5">Describe a job in plain English — AI drafts a full line-item quote in seconds.</p>
      </div>

      <div class="card p-5 space-y-4">
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1.5 uppercase tracking-wide">Job Description</label>
          <textarea id="quote-desc" class="input" rows="3" placeholder="e.g. Interior paint, 1200 sq ft, 3 rooms, 2 coats, ceilings and walls included"></textarea>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-xs font-semibold text-slate-400 mb-1.5 uppercase tracking-wide">Location (optional)</label>
            <input id="quote-location" class="input" placeholder="Austin, TX" value="Austin, TX" />
          </div>
          <div>
            <label class="block text-xs font-semibold text-slate-400 mb-1.5 uppercase tracking-wide">Budget Hint (optional)</label>
            <input id="quote-budget" class="input" type="number" placeholder="5000" />
          </div>
        </div>
        <button id="quote-btn" class="btn-primary py-2.5 w-full">Generate Quote Draft</button>
      </div>

      <div id="quote-result"></div>
    </div>`;

  // Quick-fill examples
  const exampleJobs = [
    'Interior paint, 1200 sq ft, 3 rooms, ceilings and walls, 2 coats',
    'Master bathroom tile install — floor and shower walls, ~80 sq ft, subway tile',
    'Electrical panel upgrade from 100A to 200A, add 4 new circuits',
    'HVAC replacement, 2000 sq ft home, 3-ton unit, ductwork inspection included',
    'Kitchen cabinet install — 20 linear feet of uppers and lowers, no countertops',
  ];

  // Add example chips
  const exampleHtml = exampleJobs.map((ex, i) =>
    `<button class="example-chip text-xs bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-200 rounded-full px-3 py-1 border border-slate-700 transition-colors" data-idx="${i}">${ex.slice(0, 55)}…</button>`
  ).join('');

  const resultEl = document.getElementById('quote-result');
  resultEl.insertAdjacentHTML('beforebegin', `
    <div class="space-y-2">
      <p class="text-xs text-slate-500 font-semibold uppercase tracking-wide">Quick examples</p>
      <div class="flex flex-wrap gap-2">${exampleHtml}</div>
    </div>`);

  container.querySelectorAll('.example-chip').forEach(btn => {
    btn.addEventListener('click', () => {
      document.getElementById('quote-desc').value = exampleJobs[parseInt(btn.dataset.idx)];
    });
  });

  document.getElementById('quote-btn').addEventListener('click', async () => {
    const btn = document.getElementById('quote-btn');
    const desc = document.getElementById('quote-desc').value.trim();
    const location = document.getElementById('quote-location').value.trim();
    const budgetVal = document.getElementById('quote-budget').value.trim();

    if (!desc) {
      resultEl.innerHTML = `<div class="card p-4 text-red-400 text-sm">Please enter a job description.</div>`;
      return;
    }

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner mr-2"></span>Drafting quote…';
    resultEl.innerHTML = '';

    try {
      const data = await api.quote.draft({
        description: desc,
        location: location || undefined,
        budget_hint: budgetVal ? parseFloat(budgetVal) : undefined,
      });

      const quote = data?.quote;
      if (!quote || quote.parse_error) {
        resultEl.innerHTML = `
          <div class="card p-6 border border-slate-700 text-center">
            <div class="text-3xl mb-3 text-orange-400">⚠️</div>
            <h3 class="text-lg font-bold text-slate-100 mb-2">Quote Generation Interrupted</h3>
            <p class="text-sm text-slate-400 mb-4">The AI provider returned an incomplete or loosely formatted result. Please click "Generate" again to retry.</p>
            <details class="text-xs text-slate-600 text-left">
              <summary class="cursor-pointer mb-2 hover:text-slate-400 transition-colors">Show raw output</summary>
              <pre class="bg-slate-900 p-3 rounded-lg overflow-x-auto whitespace-pre-wrap text-slate-500">${quote?.raw || 'No output'}</pre>
            </details>
          </div>
        `;
      } else {
        resultEl.innerHTML = renderQuoteCard(quote);
      }
    } catch (err) {
      resultEl.innerHTML = `<div class="card p-4 text-red-400 text-sm">Error: ${err.message}</div>`;
    }

    btn.disabled = false;
    btn.textContent = 'Generate Quote Draft';
  });
}

function renderQuoteCard(q) {
  const items = (q.line_items || []).map(item => `
    <tr>
      <td class="text-slate-300">${item.item}</td>
      <td class="text-slate-500 text-xs">${item.description || ''}</td>
      <td class="text-right text-slate-400">${item.qty} ${item.unit}</td>
      <td class="text-right text-slate-400">$${(item.unit_price || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}</td>
      <td class="text-right font-semibold text-slate-200">$${(item.total || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}</td>
    </tr>`).join('');

  return `
    <div class="card p-6 space-y-5">
      <div>
        <h3 class="text-lg font-bold text-slate-100 mb-1">${q.title || 'Quote'}</h3>
        <p class="text-sm text-slate-400">${q.summary || ''}</p>
      </div>

      <table>
        <thead>
          <tr>
            <th>Item</th>
            <th>Detail</th>
            <th class="text-right">Qty/Unit</th>
            <th class="text-right">Unit Price</th>
            <th class="text-right">Total</th>
          </tr>
        </thead>
        <tbody>
          ${items}
        </tbody>
      </table>

      <div class="border-t border-slate-700 pt-4 space-y-1">
        <div class="flex justify-between text-sm text-slate-400">
          <span>Subtotal</span>
          <span>$${(q.subtotal || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}</span>
        </div>
        <div class="flex justify-between text-sm text-slate-400">
          <span>Tax (${((q.tax_rate || 0) * 100).toFixed(1)}%)</span>
          <span>$${(q.tax || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}</span>
        </div>
        <div class="flex justify-between text-base font-bold text-slate-100 pt-1">
          <span>Total</span>
          <span>$${(q.total || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}</span>
        </div>
      </div>

      ${q.notes ? `
        <div class="bg-slate-900 rounded-lg p-3">
          <p class="text-xs text-slate-500 font-semibold uppercase tracking-wide mb-1">Notes & Assumptions</p>
          <p class="text-sm text-slate-400">${q.notes}</p>
        </div>` : ''}

      <p class="text-xs text-slate-600">AI-generated draft · Review before sending to client</p>
    </div>`;
}
