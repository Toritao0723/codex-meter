// Shared account switch: a single identity label, not a second card or reserved slot.
(() => {
  let selected, available = [];
  const post = body => window.webkit?.messageHandlers?.meter?.postMessage(body);
  const buttons = [...document.querySelectorAll('.provider-switch')];
  for (const button of buttons) {
    button.addEventListener('pointerdown', e => { e.stopPropagation(); post({type:'nodrag'}); });
    button.addEventListener('click', e => {
      e.stopPropagation();
      if (available.length < 2) return;
      post({type:'provider', value:available[(available.indexOf(selected) + 1) % available.length]});
    });
  }
  window.updateProviderSwitch = data => {
    selected = data.provider || document.documentElement.dataset.provider;
    available = (data.providers || [selected]).filter(p => p === 'codex' || p === 'claude');
    const name = selected === 'claude' ? 'Claude' : 'Codex';
    const english = (data.language || data.lang) === 'en';
    const next = selected === 'claude' ? 'Codex' : 'Claude';
    for (const button of buttons) {
      button.disabled = available.length < 2;
      button.textContent = name + (available.length > 1 ? ' ⇄' : '');
      button.title = available.length > 1 ? (english ? `Switch to ${next}` : `切换到 ${next}`) : name;
      button.setAttribute('aria-label', button.title);
    }
    const sticker = document.querySelector('.sticker');
    if (sticker) sticker.textContent = name.toUpperCase();
    document.title = name + ' Meter';
  };
})();
