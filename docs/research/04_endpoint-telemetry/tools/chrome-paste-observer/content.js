(() => {
  const documentId = crypto.randomUUID();
  const emit = (type, extra = {}) => {
    chrome.runtime.sendMessage({kind: 'observation', row: {
      schema_version: 1, document_id: documentId, type,
      observed_at_utc: new Date().toISOString(),
      document_monotonic_ms: performance.now(), origin: location.origin, ...extra
    }}).catch(() => {});
  };
  emit('page_ready');
  document.addEventListener('paste', event => {
    const target = event.composedPath().find(n => n instanceof Element);
    emit('paste_event', {
      trusted: event.isTrusted,
      target_tag: target?.tagName ?? null,
      target_editable: !!target && (target.isContentEditable ||
        (target.tagName === 'TEXTAREA') ||
        (target.tagName === 'INPUT' && !target.disabled && !target.readOnly)),
      payload_collected: false,
      semantics: 'Paste event observed; does not prove content insertion, composer identity, or transmission.'
    });
  }, true);
})();
