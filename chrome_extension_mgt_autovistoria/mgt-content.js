function pageStatus(message) {
  window.dispatchEvent(new CustomEvent('mgt-autovistoria-status', {detail: {message}}));
}
window.addEventListener('mgt-autovistoria-start', event => {
  chrome.runtime.sendMessage({type: 'MGT_START_QUERY', payload: event.detail}, response => {
    if (chrome.runtime.lastError) return pageStatus(`Erro na extensão: ${chrome.runtime.lastError.message}`);
    pageStatus(response?.ok ? 'Portal aberto. O robô começará o preenchimento.' : (response?.error || 'Não foi possível abrir o portal.'));
  });
});
window.addEventListener('mgt-autovistoria-page-ready', () => {
  window.dispatchEvent(new CustomEvent('mgt-autovistoria-extension-ready'));
});
window.dispatchEvent(new CustomEvent('mgt-autovistoria-extension-ready'));

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
    body: JSON.stringify({items: message.items, source: 'chrome-extension-assisted-v1'})
  }).then(async response => {
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || `Erro HTTP ${response.status}`);
    pageStatus(data.message || 'Comunicados importados com sucesso.');
    window.setTimeout(() => window.location.reload(), 900);
    sendResponse({ok: true, ...data});
  }).catch(error => {
    pageStatus(`Falha ao importar: ${error.message}`);
    sendResponse({ok: false, error: error.message});
  });
  return true;
});
