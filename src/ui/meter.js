// Codex Meter activity companion. Original pixel character © 2026 Bon Yeung.
(() => {
  const $ = id => document.getElementById(id);
  const root = document.documentElement;
  const card = $('card'), lane = $('lane'), laneBox = $('laneBox');
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const native = window.webkit && window.webkit.messageHandlers && window.webkit.messageHandlers.meter;
  const post = msg => native && native.postMessage(msg);

  const words = {"每周 Opus 额度":"Weekly Opus limit", "每周 Sonnet 额度":"Weekly Sonnet limit","展开完整面板": "Expand panel", "紧凑模式": "Compact mode", "点击小螃蟹恢复面板；拖动可移动": "Click to expand; drag to move", "进行中每 16 秒换一个忙碌场景，也可以点击切换。等待时听歌，完成时撒花。": "Scenes change every 16 seconds while working. Click to change scenes.", "进行中": "Working", "待回复": "Needs you", "已完成": "Done", "出错": "Error", "已中断": "Interrupted", "额度提醒": "Quota alert", "任务": "Task", "，打开任务": ", open task", "额度未提供": "Quota unavailable", "额度明细": "Quota details", "重置时间未提供": "Reset time unavailable", "已用 --": "Used --", "等待账户数据": "Waiting for account data", "时间未提供": "Time unavailable", "实时": "Live", "待同步": "Not live", "点击刷新": "Click refresh", "任务进行中": "Working", "等待你回复": "Waiting for you", "休息中": "Resting", "本轮已完成": "Turn complete", "任务出错": "Task error", "状态待确认": "Status unknown", "展开额度与任务面板": "Expand quota and tasks", "剩余": "left", "重置倒计时": "Resets in", "立即刷新": "Refresh now", "最小化，只留小螃蟹": "Pet only", "上一个任务": "Previous task", "下一个任务": "Next task", "每周额度": "Weekly quota", "5 小时额度": "5-hour quota", "账户额度": "Account quota", "小螃蟹在打电脑": "Typing away", "小螃蟹在做饭": "Cooking ideas", "小螃蟹在打网球": "Playing tennis", "小螃蟹举起相机拍照": "Taking photos", "小螃蟹开飞机": "Flying high", "听听歌，等你回来": "Music while waiting", "完成啦，撒花！": "Time for confetti!", "小螃蟹休息一下": "Taking a break", "稍候片刻": "One moment"};
  let language = "zh";
  const t = text => language === "en" ? (words[text] || text.replace(/^(\d+) 分钟额度$/, "$1-minute quota")) : text;
  const locale = () => language === "en" ? "en-US" : "zh-CN";
  const TICK = 150;
  const S = { d: null, colors: {}, sized: false, sceneOffset: 0 };
  const tasks = new window.TaskNavigation();

  // ---------- data in ----------

  function update(d) {
    language = d.language === "en" ? "en" : "zh";
    root.lang = language === "en" ? "en" : "zh-Hans";
    $("remainingLabel").textContent = t("剩余");
    $("resetLabel").textContent = t("重置倒计时");
    $("languageBtn").textContent = language === "en" ? "中" : "EN";
    $("languageBtn").setAttribute("aria-label", language === "en" ? "切换到中文" : "Switch to English");
    $("languageBtn").title = language === "en" ? "切换到中文" : "Switch to English";
    for (const [id, label] of [["syncBtn","立即刷新"],["minimizeBtn","最小化，只留小螃蟹"],["prevTask","上一个任务"],["nextTask","下一个任务"]]) { $(id).title = t(label); $(id).setAttribute("aria-label", t(label)); }
    document.querySelector(".week").setAttribute("aria-label", t("额度明细"));
    const windows = d.windows || [];
    d.session = windows[0] || { known: false, idle: true, percentUsed: 0 };
    d.weekly = windows[1] || windows[0] || { known: false };
    S.d = d;
    window.updateProviderSwitch?.(d);
    S.sceneOffset = d.sceneOffset ?? S.sceneOffset;
    applyTheme(d.theme || 'dark');
    root.classList.toggle('mini', !!d.mini);
    root.classList.toggle('minimized', !!d.minimized);
    tasks.update(d.taskNav?.items || []);
    renderNavigation();
    $('sizeBtn').setAttribute('aria-label', d.mini ? t('展开完整面板') : t('紧凑模式'));
    $('sizeBtn').title = d.mini ? t('展开完整面板') : t('紧凑模式');
    $('sizeBtn').innerHTML = d.mini
      ? '<svg viewBox="0 0 8 8" aria-hidden="true"><path d="M1 1h6v6H1zM2 3v3h4V3z" fill-rule="evenodd"/></svg>'
      : '<svg viewBox="0 0 8 8" aria-hidden="true"><path d="M1 1h6v6H1zM2 2v4h4V2zM2 4h4v1H2z" fill-rule="evenodd"/></svg>';

    laneBox.title = d.minimized ? t('点击小螃蟹恢复面板；拖动可移动') : t('进行中每 16 秒换一个忙碌场景，也可以点击切换。等待时听歌，完成时撒花。');
    renderText();
    draw();                     // paint the lane straight away, not on the next tick
    reportSize();
  }

  function renderNavigation() {
    const item = tasks.current(), nav = $('taskNav');
    nav.hidden = !item;
    card.classList.toggle('has-tasks', !!item);
    if (!item) return;
    const state = tasks.needsReply(item) ? 'waiting' : item.state;
    const labels = { working:t('进行中'), waiting:t('待回复'), done:t('已完成'), error:t('出错'), interrupted:t('已中断'), warning:t('额度提醒') };
    nav.dataset.state = state;
    $('taskState').textContent = labels[state] || t('任务');
    $('taskTitle').textContent = item.title;
    $('taskTitle').title = item.title;
    $('taskTitle').disabled = !item.id;
    $('taskTitle').setAttribute('aria-label', `${labels[state] || t('任务')}：${item.title}${item.id ? t('，打开任务') : ''}`);
    $('taskPages').hidden = tasks.items.length < 2;
    $('taskIndex').textContent = `${tasks.index() + 1}/${tasks.items.length}`;
    nav.setAttribute('aria-label', `${language === "en" ? "Tasks" : "任务导航"}, ${tasks.index() + 1}/${tasks.items.length}`);
  }

  function applyTheme(t) {
    const resolved = t === 'auto' ? (matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark') : t;
    if (root.dataset.theme !== resolved) { root.dataset.theme = resolved; S.colors = {}; }
  }

  // ---------- words and numbers ----------

  const pad = n => String(n).padStart(2, '0');
  function countdown(msLeft) {
    if (msLeft <= 0) return '0m';
    const m = Math.floor(msLeft / 60000), h = Math.floor(m / 60), d = Math.floor(h / 24);
    if (d >= 1) return `${d}d ${h % 24}h`;
    if (h >= 1) return `${h}h ${pad(m % 60)}m`;
    return `${m}m ${pad(Math.floor(msLeft / 1000) % 60)}s`;
  }
  function clock(ms, withDay) {
    const t = new Date(ms);
    const time = t.toLocaleTimeString(locale(), { hour: 'numeric', minute: '2-digit' });
    const sameDay = t.toDateString() === new Date().toDateString();
    return withDay || !sameDay ? `${t.toLocaleDateString(locale(), { weekday: 'short' })} ${time}` : time;
  }
  function mood() {
    const s = S.d.session || {};
    if (!s.known) return 'idle';
    if (s.percentUsed >= 100) return 'out';
    if (s.percentUsed >= 90) return 'warn';
    if (s.percentUsed >= 80) return 'close';
    return 'ok';
  }

  function renderText() {
    const d = S.d, s = d.session || {};
    const used = s.idle ? 0 : s.percentUsed;
    // Round "left" down so it never claims more than you really have.
    $('left').textContent = s.known ? Math.max(0, Math.floor(100 - used)) : '--';
    $('plan').textContent = t(s.label || '额度未提供');

    card.dataset.mood = mood();

    // Weekly: fill = used, right end = the limit, which resets at the time shown under it.
    const w = d.weekly || {};
    $('wLabel').textContent = t(w.label || '额度明细');
    if (w.known && !w.idle) {
      const wUsed = Math.min(100, Math.ceil(w.percentUsed));
      $('wFill').style.width = `${wUsed}%`;
      $('wLeft').textContent = `${t("剩余")} ${100 - wUsed}%`;
      $('wUsed').textContent = `${language === "en" ? "Used" : "已用"} ${wUsed}%`;
      $('wReset').textContent = w.resetsAt ? `${language === "en" ? "Resets" : "重置"} ${clock(w.resetsAt, true)}` : '重置时间未提供';
    } else {
      $('wFill').style.width = '0%';
      $('wLeft').textContent = '--';
      $('wUsed').textContent = t('已用 --');
      $('wReset').textContent = t('等待账户数据');
    }

    $('syncBtn').classList.remove('spinning');
    secondTick();
  }

  // Runs every second so the countdown is live between data updates.
  function secondTick() {
    if (!S.d) return;
    const s = S.d.session || {};
    if (s.idle || !s.resetsAt) {
      $('count').textContent = '--';
      $('resetAt').textContent = t('时间未提供');
    } else {
      $('count').textContent = countdown(s.resetsAt - Date.now());
      $('resetAt').textContent = `${language === "en" ? "At" : "于"} ${clock(s.resetsAt)}`;
    }
    liveStatus();
  }

  // "● LIVE · updated 20s ago" when the numbers come straight from your account (refreshed every minute).
  // Anything else is shown in pink as NOT LIVE, so a stale number can never pass for a real one.
  const since = ms => {
    const s = Math.max(0, Math.round((Date.now() - ms) / 1000));
    if (s < 60) return language === "en" ? `${s}s` : `${s} 秒`;
    const m = Math.round(s / 60);
    if (language === "en") return m < 60 ? `${m}m` : `${Math.round(m / 60)}h`;
    return m < 60 ? `${m} 分钟` : `${Math.round(m / 60)} 小时`;
  };
  function liveStatus() {
    const d = S.d;
    const live = d.live && d.liveAt && Date.now() - d.liveAt < 180000;
    const last = d.liveAt || d.syncedAt;
    const foot = $('foot'), mini = $('miniLive');
    card.dataset.stale = String(!live);
    const ago = ms => language === 'en' ? `${since(ms)} ago` : `${since(ms)}前`;
    const status = t(live ? '实时' : '待同步');
    $('quota').title = `${$('left').textContent}% ${t('剩余')} · ${status}${last ? ` · ${ago(last)}` : ''}`;
    for (const el of [foot, mini]) { el.classList.toggle('live', !!live); el.classList.toggle('stale', !live); }
    const detail = last ? ago(last) : t('点击刷新');
    foot.innerHTML = `${live ? '<i class="dot"></i>' : ''}<b>${status}</b> · ${detail}`;
    mini.innerHTML = `${live ? '<i class="dot"></i>' : ''}${status}${last ? ` · ${ago(last)}` : ''}`;
    // Keep the compact layout; expose the actual failure on hover instead of hiding it.
    const problem = !live ? (d.liveProblem || t('点击刷新')) : '';
    foot.title = mini.title = problem;
    if (problem) $('quota').title += ` · ${problem}`;
  }

  function reportSize() {
    requestAnimationFrame(() => {
      S.sized = true;
      // macOS draws the soft window shadow outside the native glass surface.
      post({ type: 'size', w: Math.ceil(card.offsetWidth), h: Math.ceil(card.offsetHeight) });
    });
  }

  // Task activity owns the character; quota remains a separate, factual meter.
  function activity() {
    if (S.d?.activity) return S.d.activity;
    if (S.d?.taskProblem) return { state:'unknown' };
    const tasks = S.d?.tasks || [];
    return { state:tasks.some(t=>t.state==='waiting')?'waiting':tasks.some(t=>t.state==='working')?'working':'idle' };
  }
  function draw() {
    if (!S.d) return;
    const state = activity().state;
    const scene = window.CrabPet.draw(lane, { scene:native ? undefined : S.d.previewScene, state, time:Date.now(), theme:root.dataset.theme, reduced:reduce, offset:S.sceneOffset });
    const statuses = { working:t('任务进行中'), waiting:t('等待你回复'), idle:t('休息中'), done:t('本轮已完成'), error:t('任务出错'), interrupted:t('已中断'), warning:t('额度提醒'), unknown:t('状态待确认') };
    $('petTitle').textContent = t(window.CrabPet.titles[scene] || '');
    $('petStatus').textContent = statuses[state] || t('状态待确认');
    laneBox.setAttribute('aria-label', S.d.minimized ? t('展开额度与任务面板') : `${$('petTitle').textContent}，${$('petStatus').textContent}${language === "en" ? ", click to change scene" : "，点击切换忙碌动作"}`);
  }

  // ---------- interaction ----------
  $('languageBtn').addEventListener('click', () => {
    const value = language === 'en' ? 'zh' : 'en';
    if (native) post({ type:'language', value });
    else update({ ...S.d, language:value });
  });

  for (const button of document.querySelectorAll('button')) button.addEventListener('pointerdown', () => post({ type:'nodrag' }));
  $('taskTitle').addEventListener('click', () => { if (tasks.current()?.id) post({ type:'openTask', id:tasks.current().id }); });
  for (const [id, delta] of [['prevTask', -1], ['nextTask', 1]]) $(id).addEventListener('click', () => { tasks.move(delta); renderNavigation(); });
  $('syncBtn').addEventListener('click', () => {
    $('syncBtn').classList.add('spinning');          // spins until the fresh numbers arrive
    if (native) post({ type: 'sync' });
    else setTimeout(() => update({ ...S.d, live: true, liveAt: Date.now() }), 900);
  });
  $('sizeBtn').addEventListener('click', () => {
    const next = !root.classList.contains('mini');
    if (native) post({ type: 'mini', value: next });
    else update({ ...S.d, mini: next });
  });
  function setMinimized(value) {
    if (native) post({ type:'minimized', value });
    else update({ ...S.d, minimized:value });
  }
  $('minimizeBtn').addEventListener('click', () => setMinimized(true));
  function nextScene() {
    if (S.d?.minimized) { setMinimized(false); return; }
    S.sceneOffset = (S.sceneOffset + 1) % window.CrabPet.busy.length;
    if (native) post({ type:'petScene', offset:S.sceneOffset });
    draw();
  }
  laneBox.addEventListener('click', nextScene);
  laneBox.addEventListener('keydown', event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); nextScene(); } });

  setInterval(draw, TICK);
  setInterval(secondTick, 1000);
  // Recalculate the mood and sentences each minute even if no new data arrives.
  setInterval(() => S.d && update(S.d), 60000);

  window.meter = { update };
  const scheme = matchMedia('(prefers-color-scheme: dark)');
  scheme.addEventListener('change',()=>{ if(S.d?.theme==='auto') update(S.d); });

  // ---------- demo data for a plain browser ----------
  if (!native) {
    const q = new URLSearchParams(location.search);
    const now = Date.now(), H = 3600e3;
    const states = {
      ok:    { percentUsed: 23, startsAt: now - 2.5 * H, resetsAt: now + 2.5 * H },
      close: { percentUsed: 46, startsAt: now - 2.5 * H, resetsAt: now + 2.5 * H },
      warn:  { percentUsed: 71, startsAt: now - 2.5 * H, resetsAt: now + 2.5 * H, emptyAt: now + 1.2 * H },
      out:   { percentUsed: 100, startsAt: now - 4 * H, resetsAt: now + 1 * H },
      idle:  { idle: true, percentUsed: 0 },
    };
    const session = { kind: 'session', known: true, idle: false, ...states[q.get('state') || 'ok'] };
    update({
      now, plan: 'Pro', syncedAt: now - 12 * 60e3, live: q.get('live') !== '0', liveAt: now - 20e3,
      theme: q.get('theme') || 'dark', mini: q.get('mini') === '1', minimized:q.get('minimized') === '1',
      taskNav:{ items:q.get('activity') === 'idle' ? [] : [
        { id:'00000000-0000-0000-0000-000000000001', title:'演示 · 优化小螃蟹桌面伴侣', state:q.get('activity') || 'working' },
        { id:'00000000-0000-0000-0000-000000000002', title:'演示 · 制定项目计划', state:'working' },
      ] },
      activity: { state:q.get('activity') || 'working' }, previewScene:q.get('scene'),
      windows: [{...session, label:'演示 · 5 小时额度'}],
      session,
      weekly: { kind: 'weekly', known: true, percentUsed: 40, startsAt: now - 5 * 24 * H, resetsAt: now + 2 * 24 * H },
    });
  }
})();
