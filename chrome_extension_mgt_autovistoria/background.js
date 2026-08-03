const PORTAL_URL = 'https://autovistoria.rio.rj.gov.br/ConsultaPublica.php';

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type === 'MGT_START_QUERY') {
    const job = {...message.payload, createdAt: Date.now(), sourceTabId: sender.tab?.id};
    chrome.storage.local.set({mgtAutovistoriaJob: job}, () => {
      chrome.tabs.create({url: PORTAL_URL}, tab => sendResponse({ok: true, tabId: tab?.id}));
    });
    return true;
  }
  if (message?.type === 'MGT_IMPORT_RESULTS') {
    chrome.storage.local.get('mgtAutovistoriaJob', ({mgtAutovistoriaJob: job}) => {
      if (!job?.sourceTabId) return sendResponse({ok: false, error: 'A aba do MGT não foi localizada.'});
      chrome.tabs.sendMessage(job.sourceTabId, {
        type: 'MGT_POST_RESULTS',
        items: message.items,
        job
      }, response => {
        if (chrome.runtime.lastError) return sendResponse({ok: false, error: chrome.runtime.lastError.message});
        sendResponse(response || {ok: false, error: 'Sem resposta do MGT.'});
      });
    });
    return true;
  }
});
