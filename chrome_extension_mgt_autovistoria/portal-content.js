const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
const normalize = value => (value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/\s+/g, ' ').trim().toUpperCase();

function panel() {
  let box = document.getElementById('mgt-robot-panel');
  if (box) return box;
  box = document.createElement('aside');
  box.id = 'mgt-robot-panel';
  box.innerHTML = '<strong>🤖 MGT Autovistoria</strong><p id="mgt-robot-status">Preparando...</p><button id="mgt-import-results" type="button" hidden>Importar comunicados para o MGT</button><small>O robô não lê nem resolve o CAPTCHA.</small>';
  document.body.appendChild(box);
  return box;
}
function status(text) { panel().querySelector('#mgt-robot-status').textContent = text; }
function setNativeValue(element, value) {
  const descriptor = Object.getOwnPropertyDescriptor(element.tagName === 'SELECT' ? HTMLSelectElement.prototype : HTMLInputElement.prototype, 'value');
  descriptor?.set?.call(element, value);
  element.dispatchEvent(new Event('input', {bubbles: true}));
  element.dispatchEvent(new Event('change', {bubbles: true}));
}
async function typeLikePerson(input, text) {
  input.focus(); setNativeValue(input, '');
  for (const char of text || '') {
    setNativeValue(input, input.value + char);
    input.dispatchEvent(new KeyboardEvent('keyup', {key: char, bubbles: true}));
    await sleep(45 + Math.floor(Math.random() * 55));
  }
  input.dispatchEvent(new Event('blur', {bubbles: true}));
}
function labelControl(labelPart, tag = 'input') {
  const wanted = normalize(labelPart);
  const labels = [...document.querySelectorAll('label, td, th, span, div')].filter(el => normalize(el.textContent).replace(/:$/, '') === wanted);
  for (const label of labels) {
    if (label.htmlFor) { const linked = document.getElementById(label.htmlFor); if (linked?.matches(tag)) return linked; }
    const parent = label.closest('tr, .form-group, div') || label.parentElement;
    const candidate = parent?.querySelector(tag);
    if (candidate) return candidate;
    let sibling = label.nextElementSibling;
    while (sibling) { const found = sibling.matches?.(tag) ? sibling : sibling.querySelector?.(tag); if (found) return found; sibling = sibling.nextElementSibling; }
  }
  return null;
}
function visibleInputs() { return [...document.querySelectorAll('input:not([type=hidden]):not([type=button]):not([type=submit])')].filter(el => el.offsetParent !== null); }
function locateFields() {
  const inputs = visibleInputs();
  return {
    street: labelControl('Logradouro') || inputs[0],
    number: labelControl('Nº') || labelControl('N°') || inputs[1],
    complement: labelControl('Complemento') || inputs[2],
    neighborhood: labelControl('Bairro', 'select') || document.querySelector('select'),
    communication: labelControl('Número do comunicado') || inputs[3]
  };
}
async function chooseAutocomplete(street) {
  await sleep(1200);
  const candidates = [...document.querySelectorAll('.ui-autocomplete li, .autocomplete li, [role=listbox] [role=option], option')].filter(el => el.offsetParent !== null || el.tagName === 'OPTION');
  const target = candidates.find(el => normalize(el.textContent).includes(normalize(street))) || candidates[0];
  if (target && target.tagName !== 'OPTION') { target.dispatchEvent(new MouseEvent('mousedown', {bubbles: true})); target.click(); await sleep(500); }
}
function chooseNeighborhood(select, neighborhood) {
  if (!select || !neighborhood) return;
  const wanted = normalize(neighborhood);
  const option = [...select.options].find(o => normalize(o.textContent) === wanted) || [...select.options].find(o => normalize(o.textContent).includes(wanted));
  if (option) setNativeValue(select, option.value);
}
async function fill(job) {
  panel(); status('Localizando os campos do portal...');
  const fields = locateFields();
  if (!fields.street || !fields.number || !fields.neighborhood) throw new Error('Não foi possível localizar todos os campos. O portal pode ter mudado.');
  status('Digitando o logradouro...'); await typeLikePerson(fields.street, job.street); await chooseAutocomplete(job.street);
  status('Digitando o número...'); await typeLikePerson(fields.number, job.number);
  if (fields.complement && job.complement) { status('Digitando o complemento...'); await typeLikePerson(fields.complement, job.complement); }
  status('Selecionando o bairro...'); chooseNeighborhood(fields.neighborhood, job.neighborhood);
  if (fields.communication && job.communication) { status('Digitando o número do comunicado...'); await typeLikePerson(fields.communication, job.communication); }
  status('Preenchimento concluído. Digite o CAPTCHA e clique em Consultar.');
  observeResults();
}
function parseResults() {
  const tables = [...document.querySelectorAll('table')];
  const table = tables.find(t => normalize(t.textContent).includes('COMUNICADO') && normalize(t.textContent).includes('TIPO DE COMUNICADO'));
  if (!table) return [];
  const rows = [...table.querySelectorAll('tbody tr, tr')];
  return rows.map(row => {
    const cells = [...row.querySelectorAll('td')];
    if (cells.length < 4) return null;
    const communication = (cells[1]?.innerText || cells[1]?.textContent || '').trim();
    if (!communication || normalize(communication) === 'COMUNICADO') return null;
    return {
      complement: (cells[0]?.innerText || '').trim(),
      communication_number: communication,
      infraction_number: communication,
      infraction_type: (cells[2]?.innerText || '').trim(),
      infraction_date: (cells[3]?.innerText || '').trim(),
      notes: (cells[4]?.innerText || '').trim()
    };
  }).filter(Boolean);
}
function activateImport(items) {
  const button = panel().querySelector('#mgt-import-results');
  button.hidden = false;
  button.textContent = `Importar ${items.length} comunicado(s) para o MGT`;
  button.onclick = () => {
    button.disabled = true; status('Enviando comunicados para o MGT...');
    chrome.runtime.sendMessage({type: 'MGT_IMPORT_RESULTS', items}, response => {
      button.disabled = false;
      if (chrome.runtime.lastError) return status(`Erro: ${chrome.runtime.lastError.message}`);
      status(response?.ok ? (response.message || 'Importação concluída. Volte ao MGT.') : `Falha: ${response?.error || 'erro desconhecido'}`);
    });
  };
  status(`${items.length} comunicado(s) encontrado(s). Confira a tabela e importe para o MGT.`);
}
function observeResults() {
  const check = () => { const items = parseResults(); if (items.length) activateImport(items); };
  check();
  new MutationObserver(check).observe(document.body, {childList: true, subtree: true});
}
chrome.storage.local.get('mgtAutovistoriaJob', ({mgtAutovistoriaJob: job}) => {
  if (!job || Date.now() - job.createdAt > 30 * 60 * 1000) { panel(); status('Nenhuma consulta recente foi iniciada no MGT.'); observeResults(); return; }
  fill(job).catch(error => { panel(); status(`Atenção: ${error.message}`); observeResults(); });
});
