const PORTAL_URL = 'https://autovistoria.rio.rj.gov.br/ConsultaPublica.php';

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type === 'MGT_HEALTHCHECK') {
    sendResponse({ok: true, version: chrome.runtime.getManifest().version});
    return;
  }
  if (message?.type === 'MGT_START_QUERY') {
    const job = {
      ...message.payload,
      jobId: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
      createdAt: Date.now(),
      updatedAt: Date.now(),
      state: 'NEW',
      sourceTabId: sender.tab?.id
    };
    chrome.storage.local.set({mgtAutovistoriaJob: job}, () => {
      chrome.tabs.create({url: PORTAL_URL, active: true}, tab => sendResponse({ok: true, tabId: tab?.id, jobId: job.jobId}));
    });
    return true;
  }
  if (message?.type === 'MGT_IMPORT_RESULTS') {
    chrome.storage.local.get('mgtAutovistoriaJob', ({mgtAutovistoriaJob: job}) => {
      if (!job?.sourceTabId) return sendResponse({ok: false, error: 'A aba do MGT não foi localizada.'});
      chrome.tabs.sendMessage(job.sourceTabId, {type: 'MGT_POST_RESULTS', items: message.items, job}, response => {
        if (chrome.runtime.lastError) return sendResponse({ok: false, error: chrome.runtime.lastError.message});
        if (response?.ok) chrome.tabs.update(job.sourceTabId, {active: true});
        sendResponse(response || {ok: false, error: 'Sem resposta do MGT.'});
      });
    });
    return true;
  }
});
