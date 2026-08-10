// ============================================================================
//  main.js — boot, title screen, character creation and the frame loop.
// ============================================================================

import { Game } from './game/game.js';
import { UI } from './ui/ui.js';
import { CLASSES } from './game/player.js';
import { listSaves, loadGameData, deleteSave, formatPlaytime, saveSettings } from './core/save.js';
import { clamp, MAX_DT } from './core/math.js';

const $ = (id) => document.getElementById(id);

let game = null;
let ui = null;
let running = false;
let lastTime = 0;
let pausedForVisibility = false;
let frameRequest = 0;
let contextLost = false;

const LOAD_TIPS = [
  '左側をドラッグして移動。右側をスワイプして視点を動かせます。',
  '回避は短押し、ダッシュは回避を押したまま移動します。',
  '黄色い◇と画面上部の使命表示が、次の目的地を示します。',
  '篝火・使命更新・王の撃破・60秒ごとに自動保存されます。',
  '敵の攻撃直前にパリィすると、致命の一撃の機会が生まれます。',
];
let loadTipIndex = -1;

// ---------------------------------------------------------------------------
//  Loading
// ---------------------------------------------------------------------------

function setLoading(p, label) {
  $('load-bar').style.width = `${Math.round(p * 100)}%`;
  $('load-label').textContent = label || '';
  $('load-percent').textContent = `${Math.round(p * 100)}%`;
  const nextTip = Math.min(LOAD_TIPS.length - 1, Math.floor(p * LOAD_TIPS.length));
  if (nextTip !== loadTipIndex && $('load-tip')) {
    loadTipIndex = nextTip;
    $('load-tip').textContent = LOAD_TIPS[nextTip];
  }
}

function showLoading(show) {
  $('loading').classList.toggle('hidden', !show);
}

/** Drive the boot coroutine across frames so the bar actually animates. */
function runBoot(seed, onDone) {
  showLoading(true);
  loadTipIndex = -1;
  setLoading(0, '目を覚ましている');
  const gen = game.boot(seed);
  const step = () => {
    const t0 = performance.now();
    let res;
    // Spend up to ~24ms per frame generating, then yield to the browser.
    do {
      res = gen.next();
      if (res.done) break;
    } while (performance.now() - t0 < 24);
    if (res.done) {
      setLoading(1, '完了');
      setTimeout(() => { showLoading(false); onDone(); }, 220);
      return;
    }
    setLoading(res.value.p, res.value.label);
    requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

// ---------------------------------------------------------------------------
//  Title
// ---------------------------------------------------------------------------

function showTitle() {
  const saves = listSaves();
  const hasSave = saves.some(Boolean);
  const latest = saves.filter(Boolean).sort((a, b) => b.savedAt - a.savedAt)[0] || null;
  const overlay = $('overlay');
  overlay.className = 'overlay open screen-title';
  overlay.innerHTML = `
    <div class="title-screen">
      <div class="title-sigil" aria-hidden="true"></div>
      <div class="title-mark">
        <h1>黒鉄の刻印</h1>
        <p class="sub">KUROGANE — Mark of Black Iron</p>
      </div>
      <p class="tagline">残り火の王冠は砕けた。<br>刻印を負う者だけが、まだ歩いている。</p>
      ${latest ? `<div class="save-preview"><b>${escapeHtml(latest.name)} — Lv.${latest.level} ${escapeHtml(latest.className)}</b><span>${escapeHtml(latest.region || '名もなき地')} / ${formatPlaytime(latest.playtime)} / 王 ${latest.bosses}体</span></div>` : ''}
      <div class="title-menu">
        ${hasSave ? '<button class="btn primary" data-t="load">続きから</button>' : ''}
        <button class="btn${hasSave ? '' : ' primary'}" data-t="new">新しい旅</button>
        <button class="btn" data-t="settings">設定</button>
      </div>
      <p class="title-foot">端末を横向きにすると広く表示されます。ヘッドホン推奨。</p>
      <span class="title-version">QUALITY REFORGED 2026.08</span>
    </div>`;
  document.body.classList.add('menu-open');

  overlay.onclick = (e) => {
    const b = e.target.closest('[data-t]');
    if (!b) return;
    if (b.dataset.t === 'new') {
      const empty = saves.findIndex((save) => !save);
      creation.slot = empty >= 0 ? empty : 0;
      showClassSelect();
    }
    else if (b.dataset.t === 'load') showLoadMenu();
    else if (b.dataset.t === 'settings') showTitleSettings();
  };
}

function showTitleSettings() {
  const overlay = $('overlay');
  const s = game.settings;
  overlay.innerHTML = `
    <div class="panel">
      <div class="panel-head"><h2>設定</h2><button class="icon-btn" data-t="back">戻る</button></div>
      <div class="panel-body scroll">
        <h3>グラフィック品質</h3>
        <div class="chips">
          ${['low', 'medium', 'high'].map((q) => `<button class="chip${s.quality === q ? ' active' : ''}" data-q="${q}">${{ low: '低', medium: '中', high: '高' }[q]}</button>`).join('')}
        </div>
        <div class="hint">迷ったら「中」。動作が重ければ「低」に。</div>
        <h3>音量</h3>
        <label class="range">全体<input type="range" min="0" max="1" step="0.05" value="${s.master}" data-k="master"><span class="range-value">${s.master.toFixed(2)}</span></label>
        <label class="range">音楽<input type="range" min="0" max="1" step="0.05" value="${s.music}" data-k="music"><span class="range-value">${s.music.toFixed(2)}</span></label>
        <label class="range">効果音<input type="range" min="0" max="1" step="0.05" value="${s.sfx}" data-k="sfx"><span class="range-value">${s.sfx.toFixed(2)}</span></label>
      </div>
    </div>`;
  overlay.onclick = (e) => {
    const b = e.target.closest('[data-t],[data-q]');
    if (!b) return;
    if (b.dataset.t === 'back') { showTitle(); return; }
    if (b.dataset.q) {
      game.settings.quality = b.dataset.q;
      game.renderer.setQuality(b.dataset.q);
      showTitleSettings();
    }
  };
  overlay.oninput = (e) => {
    const k = e.target.dataset.k;
    if (!k) return;
    const v = parseFloat(e.target.value);
    game.settings[k] = v;
    game.audio.setVolumes({ [k]: v });
    saveSettings(game.settings);
    const out = e.target.parentElement.querySelector('.range-value');
    if (out) out.textContent = v.toFixed(2);
  };
}

function showLoadMenu() {
  const saves = listSaves();
  const overlay = $('overlay');
  overlay.innerHTML = `
    <div class="panel">
      <div class="panel-head"><h2>続きから</h2><button class="icon-btn" data-t="back">戻る</button></div>
      <div class="panel-body scroll">
        ${saves.map((s, i) => s ? `
          <div class="save-row big">
            <button class="item-row" data-slot="${i}">
              <span class="name">${escapeHtml(s.name)} — Lv.${s.level} ${escapeHtml(s.className)}</span>
              <span class="meta">${escapeHtml(s.region || '')} / ${formatPlaytime(s.playtime)} / 王 ${s.bosses}体</span>
            </button>
            <button class="mini-btn danger" data-del="${i}">削除</button>
          </div>` : `<div class="save-row"><span>スロット${i + 1}：空</span></div>`).join('')}
      </div>
    </div>`;
  overlay.onclick = (e) => {
    const back = e.target.closest('[data-t="back"]');
    if (back) { showTitle(); return; }
    const del = e.target.closest('[data-del]');
    if (del) {
      deleteSave(parseInt(del.dataset.del, 10));
      showLoadMenu();
      return;
    }
    const b = e.target.closest('[data-slot]');
    if (!b) return;
    const data = loadGameData(parseInt(b.dataset.slot, 10));
    if (!data) return;
    startGame({ load: data, slot: parseInt(b.dataset.slot, 10) });
  };
}

// ---------------------------------------------------------------------------
//  Character creation
// ---------------------------------------------------------------------------

let creation = { classId: 'knight', skin: 0, hair: 0, cape: 0, name: '刻印者', slot: 0 };

const CAPE_COLORS = [
  [0.30, 0.09, 0.09], [0.11, 0.14, 0.28], [0.14, 0.22, 0.13],
  [0.24, 0.21, 0.16], [0.20, 0.13, 0.24], [0.42, 0.34, 0.13],
];

function showClassSelect() {
  const overlay = $('overlay');
  const cls = CLASSES.find((c) => c.id === creation.classId) || CLASSES[0];
  const saves = listSaves();
  overlay.className = 'overlay open screen-create';
  overlay.innerHTML = `
    <div class="panel wide">
      <div class="panel-head"><h2>刻印を選ぶ</h2><button class="icon-btn" data-t="back">戻る</button></div>
      <div class="panel-body cols">
        <div class="col scroll">
          ${CLASSES.map((c) => `
            <button class="item-row${c.id === creation.classId ? ' equipped' : ''}" data-cls="${c.id}">
              <span class="name">${c.name}${c.id === 'knight' ? '　<small>初心者向け</small>' : ''}</span>
              <span class="meta">Lv.${c.level}</span>
              <span class="desc">${c.blurb}</span>
            </button>`).join('')}
        </div>
        <div class="col">
          <h3>セーブ先</h3>
          <div class="chips">
            ${saves.map((save, i) => `<button class="chip${creation.slot === i ? ' active' : ''}" data-new-slot="${i}">スロット${i + 1}${save ? `：${escapeHtml(save.name)}` : '：空き'}</button>`).join('')}
          </div>
          <h3>${cls.name}</h3>
          <div class="stat-grid small">
            ${Object.entries(cls.stats).map(([k, v]) => `<div class="stat-row"><span>${statLabel(k)}</span><b>${v}</b></div>`).join('')}
          </div>
          <h3>外見</h3>
          <div class="chips">
            <span class="chip-label">肌</span>
            ${[0, 1, 2, 3].map((i) => `<button class="chip swatch${creation.skin === i ? ' active' : ''}" data-skin="${i}" style="background:${skinCss(i)}"></button>`).join('')}
          </div>
          <div class="chips">
            <span class="chip-label">髪</span>
            ${[0, 1, 2, 3].map((i) => `<button class="chip swatch${creation.hair === i ? ' active' : ''}" data-hair="${i}" style="background:${hairCss(i)}"></button>`).join('')}
          </div>
          <div class="chips">
            <span class="chip-label">外套</span>
            ${CAPE_COLORS.map((c, i) => `<button class="chip swatch${creation.cape === i ? ' active' : ''}" data-cape="${i}" style="background:${rgbCss(c)}"></button>`).join('')}
          </div>
          <h3>名前</h3>
          <input class="text-input" id="create-name" maxlength="12" value="${escapeHtml(creation.name)}">
          <button class="btn primary wide-btn" data-t="start">この者として目覚める</button>
        </div>
      </div>
    </div>`;

  overlay.oninput = (e) => {
    if (e.target.id === 'create-name') creation.name = e.target.value.slice(0, 12) || '刻印者';
  };
  overlay.onclick = (e) => {
    const b = e.target.closest('[data-cls],[data-skin],[data-hair],[data-cape],[data-new-slot],[data-t]');
    if (!b) return;
    if (b.dataset.t === 'back') { showTitle(); return; }
    if (b.dataset.t === 'start') {
      const existing = listSaves()[creation.slot];
      if (existing) showOverwriteConfirm(existing);
      else beginNewGame();
      return;
    }
    if (b.dataset.newSlot !== undefined) creation.slot = parseInt(b.dataset.newSlot, 10);
    if (b.dataset.cls) creation.classId = b.dataset.cls;
    if (b.dataset.skin) creation.skin = parseInt(b.dataset.skin, 10);
    if (b.dataset.hair) creation.hair = parseInt(b.dataset.hair, 10);
    if (b.dataset.cape) creation.cape = parseInt(b.dataset.cape, 10);
    showClassSelect();
  };
}

function beginNewGame() {
  startGame({
    slot: creation.slot,
    create: {
      classId: creation.classId,
      appearance: { skin: creation.skin, hair: creation.hair, cape: CAPE_COLORS[creation.cape] },
      name: creation.name,
    },
  });
}

function showOverwriteConfirm(existing) {
  const overlay = $('overlay');
  overlay.innerHTML = `
    <div class="panel">
      <div class="panel-head"><h2>スロット${creation.slot + 1}を上書き</h2></div>
      <div class="panel-body center">
        <p class="flavor">${escapeHtml(existing.name)}（Lv.${existing.level} / ${formatPlaytime(existing.playtime)}）の記録を、新しい旅で上書きします。</p>
        <button class="btn danger" data-t="confirm-overwrite">上書きして始める</button>
        <button class="btn" data-t="cancel-overwrite">戻る</button>
      </div>
    </div>`;
  overlay.onclick = (e) => {
    const button = e.target.closest('[data-t]');
    if (!button) return;
    if (button.dataset.t === 'confirm-overwrite') beginNewGame();
    else showClassSelect();
  };
}

// ---------------------------------------------------------------------------
//  Start
// ---------------------------------------------------------------------------

function startGame(opts) {
  const overlay = $('overlay');
  overlay.className = 'overlay';
  overlay.innerHTML = '';
  document.body.classList.remove('menu-open');
  game.audio.init();
  game.activeSaveSlot = Number.isFinite(opts.slot) ? opts.slot : 0;
  const persistenceRequest = navigator.storage?.persist?.();
  persistenceRequest?.catch(() => {});

  const seed = opts.load?.meta?.seed || 'aldrath';
  runBoot(seed, () => {
    ui.attach(game);
    if (opts.load) game.loadFromData(opts.load);
    else game.startNewGame(opts.create.classId, opts.create.appearance, opts.create.name);
    document.body.classList.add('playing');
    game.paused = false;
    game.input.enabled = true;
    if (!running && !contextLost) {
      running = true;
      lastTime = performance.now();
      frameRequest = requestAnimationFrame(frame);
    }
  });
}

// ---------------------------------------------------------------------------
//  Loop
// ---------------------------------------------------------------------------

function frame(now) {
  if (!running || contextLost) return;
  let dt = (now - lastTime) / 1000;
  lastTime = now;
  // A long stall (tab switch, GC pause) must not teleport the world.
  dt = clamp(dt, 0.0005, MAX_DT);

  try {
    game.update(dt);
    game.render(dt);
    if (game.started) ui.update(dt);
  } catch (err) {
    console.error(err);
    running = false;
    frameRequest = 0;
    showFatal(err);
    return;
  }
  frameRequest = requestAnimationFrame(frame);
}

function showFatal(err) {
  const overlay = $('overlay');
  overlay.className = 'overlay open';
  overlay.innerHTML = `
    <div class="panel">
      <div class="panel-head"><h2>エラー</h2></div>
      <div class="panel-body">
        <p>予期しない問題が発生しました。</p>
        <pre class="errbox">${escapeHtml(err && err.stack ? err.stack : String(err))}</pre>
        <button class="btn primary" onclick="location.reload()">再読み込み</button>
      </div>
    </div>`;
}

// ---------------------------------------------------------------------------
//  Bootstrap
// ---------------------------------------------------------------------------

function init() {
  const canvas = $('gl');
  try {
    ui = new UI();
    game = new Game(canvas, ui);
    // Exposed for tooling and for anyone who wants to poke at the world from
    // the console; the game never reads these back.
    window.__g = game;
    window.__ui = ui;
  } catch (e) {
    $('loading').innerHTML = `<div class="load-fail">
      <h2>WebGL を利用できません</h2>
      <p>${escapeHtml(e.message)}</p>
      <p>ブラウザの設定でハードウェアアクセラレーションを有効にしてください。</p></div>`;
    return;
  }

  window.addEventListener('resize', () => {
    if (game) game.resize();
    if (ui && ui.screen === 'map') ui._drawWorldMap();
  });
  window.addEventListener('orientationchange', () => setTimeout(() => game && game.resize(), 250));

  // iOS may reclaim the GPU context when memory is tight or the app is sent
  // to the background. Rebuilding every renderer resource in-place is more
  // fragile than restoring from the small autosave, so save first and reload
  // once the browser confirms that a context is available again.
  canvas.addEventListener('webglcontextlost', (event) => {
    event.preventDefault();
    contextLost = true;
    game?.autosave('描画復旧前', true);
    game && (game.paused = true);
    running = false;
    if (frameRequest) cancelAnimationFrame(frameRequest);
    frameRequest = 0;
    const overlay = $('overlay');
    overlay.className = 'overlay open';
    overlay.innerHTML = `
      <div class="panel">
        <div class="panel-head"><h2>描画を復旧しています</h2></div>
        <div class="panel-body center">
          <p>進行状況は保存済みです。数秒で安全に再開します。</p>
          <button class="btn primary" onclick="location.reload()">今すぐ再開</button>
        </div>
      </div>`;
  });
  canvas.addEventListener('webglcontextrestored', () => {
    setTimeout(() => location.reload(), 80);
  });

  // Any first touch unlocks audio on mobile.
  const unlock = () => { game.audio.init(); game.audio.resume(); };
  window.addEventListener('touchstart', unlock, { once: true });
  window.addEventListener('mousedown', unlock, { once: true });
  window.addEventListener('keydown', unlock, { once: true });

  document.addEventListener('visibilitychange', () => {
    if (!game || !game.started) return;
    if (document.hidden) {
      game.autosave('画面終了前', true);
      if (!game.paused) {
        pausedForVisibility = true;
        game.paused = true;
      }
    } else if (pausedForVisibility && !ui.isOpen) {
      pausedForVisibility = false;
      game.paused = false;
      game.audio.resume();
      lastTime = performance.now();
    }
  });
  window.addEventListener('pagehide', () => game?.autosave('画面終了前', true));
  window.addEventListener('kurogane-update-ready', () => {
    if (game?.started) game.notify('最新版を取得しました。次の起動時に反映されます。', 'good');
  });

  // Escape / menu button toggles the pause screen during play.
  window.addEventListener('keydown', (e) => {
    if (!game || !game.started) return;
    if (e.code === 'Escape' || e.code === 'Tab') {
      e.preventDefault();
      if (ui.isOpen) ui.closeAll();
      else ui.openPause();
    }
  });

  showLoading(false);
  showTitle();
  game.resize();

  // Keep the atmosphere ticking behind the title screen for a live backdrop.
  if (!running) {
    running = true;
    lastTime = performance.now();
    frameRequest = requestAnimationFrame(titleFrame);
  }
}

/** Before a world exists there is nothing to draw; just keep the clock alive. */
function titleFrame(now) {
  if (!running || contextLost) return;
  if (game && game.started) { lastTime = now; frameRequest = requestAnimationFrame(frame); return; }
  frameRequest = requestAnimationFrame(titleFrame);
  lastTime = now;
}

function statLabel(k) {
  return { vig: '生命力', mnd: '精神力', end: '持久力', str: '筋力', dex: '技量', int: '理力', fth: '信仰' }[k] || k;
}
function skinCss(i) {
  return ['#c79e80', '#997056', '#704f3d', '#dbb89e'][i];
}
function hairCss(i) {
  return ['#241c17', '#5c3d1f', '#9e9580', '#852a1f'][i];
}
function rgbCss(c) {
  return `rgb(${Math.round(c[0] * 255)},${Math.round(c[1] * 255)},${Math.round(c[2] * 255)})`;
}
function escapeHtml(s) {
  return String(s === undefined || s === null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}

window.__errors = [];
window.addEventListener('error', (e) => {
  const msg = (e.error && e.error.stack) || e.message;
  window.__errors.push(String(msg));
  console.error('uncaught', msg);
});
window.addEventListener('unhandledrejection', (e) => {
  window.__errors.push(`unhandled rejection: ${e.reason}`);
});
