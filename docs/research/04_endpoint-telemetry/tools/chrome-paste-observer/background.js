let pending = Promise.resolve();
chrome.runtime.onMessage.addListener((message, sender, respond) => {
  const allowed = sender.id === chrome.runtime.id;
  if (!allowed) return;
  pending = pending.catch(() => {}).then(async () => {
    const state = await chrome.storage.local.get(['run_id', 'rows', 'active']);
    if (message.kind === 'start' && !sender.tab) {
      const run_id = crypto.randomUUID();
      await chrome.storage.local.set({run_id, active: true, rows: [{type: 'experiment_start', run_id, observed_at_utc: new Date().toISOString()}]});
    } else if (message.kind === 'stop' && !sender.tab) {
      const rows = state.rows || [];
      if (state.active) rows.push({type: 'experiment_stop', run_id: state.run_id, observed_at_utc: new Date().toISOString()});
      await chrome.storage.local.set({active: false, rows});
    } else if (message.kind === 'observation' && state.active && sender.tab && sender.origin === 'https://chatgpt.com') {
      const rows = state.rows || [];
      if (rows.length >= 5000) throw new Error('기록 한도 도달: 중지 후 내보내세요.');
      rows.push({...message.row, run_id: state.run_id, tab_id: sender.tab.id, event_id: rows.length + 1});
      await chrome.storage.local.set({rows});
    }
    respond({ok: true});
  }).catch(error => {
    chrome.storage.local.set({last_error: String(error)});
    respond({ok: false, error: String(error)});
  });
  return true;
});
