async function refresh() {
  const s = await chrome.storage.local.get(['active', 'rows', 'last_error']);
  const rows = s.rows || [];
  document.getElementById('status').textContent = `${s.active ? '수집 중' : '중지 상태'} / 페이지 준비 ${rows.filter(r => r.type === 'page_ready').length} / 붙여넣기 ${rows.filter(r => r.type === 'paste_event').length}건${s.last_error ? ' / 오류: ' + s.last_error : ''}`;
}
for (const kind of ['start', 'stop']) document.getElementById(kind).onclick = async () => {
  if (kind === 'start' && !confirm('이전 기록을 대체하고 새 실험을 시작할까요?')) return;
  const result = await chrome.runtime.sendMessage({kind});
  if (!result?.ok) alert(result?.error || '처리 실패');
  await refresh();
};
document.getElementById('export').onclick = async () => {
  const state = await chrome.storage.local.get(['rows', 'run_id']);
  const blob = new Blob([(state.rows || []).map(r => JSON.stringify(r)).join('\n') + '\n'], {type: 'application/x-ndjson'});
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url; link.download = `chrome-paste-${state.run_id || 'empty'}.jsonl`; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 10000);
};
chrome.storage.onChanged.addListener(refresh);
refresh();
