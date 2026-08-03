const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
const normalize = value => (value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/\s+/g, ' ').trim().toUpperCase();
const STATE = {
  NEW: 'NEW',
  FILLING: 'FILLING',
  WAITING_CAPTCHA: 'WAITING_CAPTCHA',
  WAITING_RESULTS: 'WAITING_RESULTS',
  IMPORTING: 'IMPORTING',
  DONE: 'DONE',
  ERROR: 'ERROR'
};
let resultObserver = null;
let importInProgress = false;

function panel() {
  let box = document.getElementById('mgt-robot-panel');
  if (box) return box;
  box = document.createElement('aside');
  box.id = 'mgt-robot-panel';
  box.innerHTML = '<strong>🤖 MGT Autovistoria</strong><p id="mgt-robot-status">Preparando...</p><small>O robô não lê nem resolve o CAPTCHA.</small>';
  document.body.appendChild(box);
  return box;
}
function status(text) { panel().querySelector('#mgt-robot-status').textContent = text; }
function updateJob(patch) {
  return new Promise(resolve => chrome.storage.local.get('mgtAutovistoriaJob', ({mgtAutovistoriaJob: job}) => {
    const updated = {...(job || {}), ...patch, updatedAt: Date.now()};
    chrome.storage.local.set({mgtAutovistoriaJob: updated}, () => resolve(updated));
  }));
}
function setNativeValue(element, value) {
  const proto = element.tagName === 'SELECT' ? HTMLSelectElement.prototype : HTMLInputElement.prototype;
  const descriptor = Object.getOwnPropertyDescriptor(proto, 'value');
  descriptor?.set?.call(element, value);
  element.dispatchEvent(new Event('input', {bubbles: true}));
  element.dispatchEvent(new Event('change', {bubbles: true}));
}
async function typeLikePerson(input, text) {
  input.focus();
  setNativeValue(input, '');
  for (const char of text || '') {
    setNativeValue(input, input.value + char);
    input.dispatchEvent(new KeyboardEvent('keydown', {key: char, bubbles: true}));
    input.dispatchEvent(new KeyboardEvent('keyup', {key: char, bubbles: true}));
    await sleep(55 + Math.floor(Math.random() * 60));
  }
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
function visibleAutocompleteOptions() {
  const selectors = ['.ui-autocomplete li','.autocomplete-suggestions .autocomplete-suggestion','.autocomplete li','[role="listbox"] [role="option"]','ul[id*="autocomplete"] li','div[id*="autocomplete"] li','ul[class*="suggest"] li','div[class*="suggest"]'];
  const found = [];
  for (const selector of selectors) {
    for (const el of document.querySelectorAll(selector)) {
      const style = getComputedStyle(el);
      if (el.offsetParent !== null && style.visibility !== 'hidden' && style.display !== 'none' && normalize(el.textContent)) found.push(el);
    }
  }
  return [...new Set(found)];
}
function streetHasInternalCode(input) {
  if (/\(\s*CL\s*\d+\s*\)/i.test((input?.value || '').trim())) return true;
  const form = input?.form || input?.closest('form') || document;
  return [...form.querySelectorAll('input[type="hidden"]')].some(el => {
    const key = normalize(`${el.name || ''} ${el.id || ''}`);
    return (key.includes('LOGRAD') || key.includes('ENDERE') || key.includes('COD')) && String(el.value || '').trim();
  });
}
async function chooseAutocomplete(streetInput, streetText) {
  status('Aguardando as opções de logradouro da Prefeitura...');
  const started = Date.now();
  while (Date.now() - started < 10000) {
    const options = visibleAutocompleteOptions();
    if (options.length) {
      const wanted = normalize(streetText);
      const target = options.find(el => normalize(el.textContent).includes(wanted)) || options[0];
      target.scrollIntoView({block: 'nearest'});
      target.dispatchEvent(new MouseEvent('mousedown', {bubbles: true, cancelable: true, view: window}));
      target.click();
      await sleep(1000);
      if (streetHasInternalCode(streetInput)) return true;
      break;
    }
    await sleep(250);
  }
  status('Selecione uma opção na lista de logradouros. O robô continuará automaticamente.');
  streetInput.focus();
  const manualStarted = Date.now();
  while (Date.now() - manualStarted < 120000) {
    if (streetHasInternalCode(streetInput)) return true;
    await sleep(300);
  }
  return false;
}
function chooseNeighborhood(select, neighborhood) {
  if (!select || !neighborhood) return;
  const wanted = normalize(neighborhood);
  const option = [...select.options].find(o => normalize(o.textContent) === wanted) || [...select.options].find(o => normalize(o.textContent).includes(wanted));
  if (option) setNativeValue(select, option.value);
}
function parseResults() {
  const tables = [...document.querySelectorAll('table')];
  const table = tables.find(t => {
    const text = normalize(t.textContent);
    return text.includes('COMUNICADO') && text.includes('TIPO DE COMUNICADO') && text.includes('DATA DO COMUNICADO');
  });
  if (!table) return [];
  return [...table.querySelectorAll('tr')].map(row => {
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
async function importResults(items) {
  if (!items.length || importInProgress) return;
  importInProgress = true;
  await updateJob({state: STATE.IMPORTING, resultCount: items.length});
  status(`Importando ${items.length} comunicado(s) para o MGT...`);
  chrome.runtime.sendMessage({type: 'MGT_IMPORT_RESULTS', items}, async response => {
    importInProgress = false;
    if (chrome.runtime.lastError) {
      await updateJob({state: STATE.ERROR, error: chrome.runtime.lastError.message});
      status(`Falha na importação: ${chrome.runtime.lastError.message}`);
      return;
    }
    if (!response?.ok) {
      await updateJob({state: STATE.ERROR, error: response?.error || 'erro desconhecido'});
      status(`Falha na importação: ${response?.error || 'erro desconhecido'}`);
      return;
    }
    await updateJob({state: STATE.DONE, importedAt: Date.now(), resultCount: items.length});
    status(response.message || `${items.length} comunicado(s) importado(s) com sucesso. Volte ao MGT.`);
  });
}
function observeResults() {
  if (resultObserver) return;
  const check = async () => {
    const items = parseResults();
    if (!items.length) return;
    resultObserver?.disconnect();
    resultObserver = null;
    await importResults(items);
  };
  check();
  resultObserver = new MutationObserver(check);
  resultObserver.observe(document.documentElement, {childList: true, subtree: true, characterData: true});
  status('Aguardando você informar o CAPTCHA e clicar em Consultar. Depois, a importação será automática.');
}
async function fill(job) {
  await updateJob({state: STATE.FILLING});
  panel(); status('Localizando os campos do portal...');
  const fields = locateFields();
  if (!fields.street || !fields.number || !fields.neighborhood) throw new Error('Não foi possível localizar todos os campos. O portal pode ter mudado.');
  status('Digitando o logradouro...');
  await typeLikePerson(fields.street, job.street);
  if (!await chooseAutocomplete(fields.street, job.street)) throw new Error('O logradouro não foi selecionado na lista da Prefeitura.');
  status('Logradouro confirmado. Digitando o número...');
  await typeLikePerson(fields.number, job.number);
  if (fields.complement && job.complement) { status('Digitando o complemento...'); await typeLikePerson(fields.complement, job.complement); }
  status('Selecionando o bairro...');
  chooseNeighborhood(fields.neighborhood, job.neighborhood);
  if (fields.communication && job.communication) { status('Digitando o número do comunicado...'); await typeLikePerson(fields.communication, job.communication); }
  await updateJob({state: STATE.WAITING_CAPTCHA, filledAt: Date.now()});
  observeResults();
}

chrome.storage.local.get('mgtAutovistoriaJob', async ({mgtAutovistoriaJob: job}) => {
  panel();
  if (!job || Date.now() - job.createdAt > 30 * 60 * 1000) {
    status('Nenhuma consulta recente foi iniciada no MGT.');
    return;
  }
  const existingItems = parseResults();
  if (existingItems.length && job.state !== STATE.DONE) {
    await importResults(existingItems);
    return;
  }
  if ([STATE.WAITING_CAPTCHA, STATE.WAITING_RESULTS, STATE.IMPORTING].includes(job.state)) {
    await updateJob({state: STATE.WAITING_RESULTS});
    observeResults();
    return;
  }
  if (job.state === STATE.DONE) {
    status(`${job.resultCount || 0} comunicado(s) já foram importados. Inicie uma nova consulta no MGT para consultar outro condomínio.`);
    return;
  }
  try {
    await fill(job);
  } catch (error) {
    await updateJob({state: STATE.ERROR, error: error.message});
    status(`Atenção: ${error.message}`);
  }
});
