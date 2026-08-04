const EXTENSION_VERSION = chrome.runtime.getManifest().version;

function pageStatus(message, level = 'info') {
  window.dispatchEvent(new CustomEvent('mgt-autovistoria-status', {detail: {message, level}}));
}

function announceReady(nonce = null) {
  const detail = {version: EXTENSION_VERSION};
  if (nonce) detail.nonce = nonce;
  window.dispatchEvent(new CustomEvent('mgt-autovistoria-extension-ready', {detail}));
  window.dispatchEvent(new CustomEvent('mgt-autovistoria-health-response', {detail}));
}

window.addEventListener('mgt-autovistoria-healthcheck', event => {
  const nonce = event.detail?.nonce || null;
  chrome.runtime.sendMessage({type: 'MGT_HEALTHCHECK'}, response => {
    if (chrome.runtime.lastError) {
      pageStatus(`Erro ao verificar a extensão: ${chrome.runtime.lastError.message}`, 'error');
      return;
    }
    if (!response?.ok) {
      pageStatus(response?.error || 'O serviço da extensão não respondeu.', 'error');
      return;
    }
    announceReady(nonce);
  });
});

window.addEventListener('mgt-autovistoria-start', event => {
  const nonce = event.detail?.requestNonce || null;
  chrome.runtime.sendMessage({type: 'MGT_START_QUERY', payload: event.detail}, response => {
    if (chrome.runtime.lastError) {
      const error = `Erro na extensão: ${chrome.runtime.lastError.message}`;
      pageStatus(error, 'error');
      window.dispatchEvent(new CustomEvent('mgt-autovistoria-start-response', {detail: {ok: false, error, nonce}}));
      return;
    }
    const detail = response?.ok
      ? {ok: true, nonce, message: 'Portal aberto. O robô começará o preenchimento.'}
      : {ok: false, nonce, error: response?.error || 'Não foi possível abrir o portal.'};
    window.dispatchEvent(new CustomEvent('mgt-autovistoria-start-response', {detail}));
    pageStatus(detail.message || detail.error, detail.ok ? 'info' : 'error');
  });
});

announceReady();

function cookie(name) {
  const value = document.cookie.split('; ').find(row => row.startsWith(`${name}=`));
  return value ? decodeURIComponent(value.split('=').slice(1).join('=')) : '';
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type !== 'MGT_POST_RESULTS') return;
  const url = message.job?.importUrl;
  if (!url) { sendResponse({ok: false, error: 'URL de importação ausente.'}); return; }
  fetch(url, {
    method: 'POST',
    credentials: 'same-origin',
    headers: {'Content-Type': 'application/json', 'X-CSRFToken': cookie('csrftoken')},
    body: JSON.stringify({items: message.items, source: 'chrome-extension-assisted-v1.0.3'})
  }).then(async response => {
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || `Erro HTTP ${response.status}`);
    pageStatus(data.message || 'Comunicados importados com sucesso.');
    window.setTimeout(() => window.location.reload(), 900);
    sendResponse({ok: true, ...data});
  }).catch(error => {
    pageStatus(`Falha ao importar: ${error.message}`, 'error');
    sendResponse({ok: false, error: error.message});
  });
  return true;
});
