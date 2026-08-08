/* =============================================================================
 * ELDRIA — ui.js
 * 入力 (タッチ仮想スティック / キーボード / マウス) と HUD / メニュー全般
 * ========================================================================== */
'use strict';

/* ======================= 入力 ======================= */
(function () {
  const I = G.Input = {};
  I.moveX = 0; I.moveY = 0;      // 仮想スティック (-1..1) 上=-Y
  I.camDX = 0; I.camDY = 0;      // カメラ回転差分 (フレーム毎に消費)
  I.sprint = false;
  I.wheel = 0;
  const pressQ = [];             // ボタンイベントキュー
  const EMPTY = [];
  I.held = { jump: false, attack: false };
  I.push = a => pressQ.push(a);
  I.poll = function () { return pressQ.length ? pressQ.splice(0, pressQ.length) : EMPTY; };

  const keys = {};
  let joyPtr = null, camPtr = null;
  let joyCX = 0, joyCY = 0;
  let fDownT = 0;

  I.init = function (canvas) {
    /* --- キーボード --- */
    window.addEventListener('keydown', e => {
      if (e.repeat) return;
      keys[e.code] = true;
      switch (e.code) {
        case 'Space': I.push('roll'); e.preventDefault(); break;
        case 'KeyF': I.held.attack = true; fDownT = performance.now(); break;
        case 'KeyR': I.push('heavy'); break;
        case 'KeyE': I.push('interact'); break;
        case 'KeyQ': I.push('lock'); break;
        case 'KeyC': I.push('jump'); I.held.jump = true; break;
        case 'Digit1': I.push('potion'); break;
        case 'KeyI': case 'Tab': I.push('menu'); e.preventDefault(); break;
        case 'KeyM': I.push('map'); break;
        case 'Escape': I.push('back'); break;
      }
    });
    window.addEventListener('keyup', e => {
      keys[e.code] = false;
      if (e.code === 'KeyC') I.held.jump = false;
      if (e.code === 'KeyF' && I.held.attack) {
        I.held.attack = false;
        const dur = (performance.now() - fDownT) / 1000;
        I.push(dur < 0.28 ? 'attack' : dur < 0.8 ? 'heavy' : 'spin');
      }
    });

    /* --- ポインタ (タッチ & マウス) --- */
    const onDown = e => {
      if (e.target !== canvas) return;
      G.Audio.init();
      const w = window.innerWidth;
      if (G.isTouch && e.pointerType !== 'mouse' && e.clientX < w * 0.45) {
        if (joyPtr === null) {
          joyPtr = e.pointerId;
          joyCX = e.clientX; joyCY = e.clientY;
          showJoy(joyCX, joyCY);
        }
      } else {
        if (camPtr === null) {
          camPtr = e.pointerId;
          lastCX = e.clientX; lastCY = e.clientY;
          if (e.pointerType === 'mouse') {
            mouseDownT = performance.now();
            mouseMoved = 0;
          }
          // ウィンドウ外で離しても pointerup を受け取れるように捕捉
          try { canvas.setPointerCapture(e.pointerId); } catch (err) {}
        }
      }
    };
    let lastCX = 0, lastCY = 0, mouseDownT = 0, mouseMoved = 0;
    const onMove = e => {
      if (e.pointerId === joyPtr) {
        const dx = e.clientX - joyCX, dy = e.clientY - joyCY;
        const R = 56;
        const len = Math.hypot(dx, dy);
        const k = len > R ? R / len : 1;
        I.moveX = (dx * k) / R;
        I.moveY = (dy * k) / R;
        moveJoyThumb(dx * k, dy * k);
      } else if (e.pointerId === camPtr) {
        const dx = e.clientX - lastCX, dy = e.clientY - lastCY;
        lastCX = e.clientX; lastCY = e.clientY;
        I.camDX += dx * 0.0042 * G.settings.sens;
        I.camDY += dy * 0.0042 * G.settings.sens * (G.settings.invertY ? -1 : 1);
        mouseMoved += Math.abs(dx) + Math.abs(dy);
      }
    };
    const onUp = e => {
      if (e.pointerId === joyPtr) {
        joyPtr = null;
        I.moveX = 0; I.moveY = 0;
        hideJoy();
      } else if (e.pointerId === camPtr) {
        camPtr = null;
        // マウス: 動かさずクリック → 攻撃
        if (e.pointerType === 'mouse' && mouseMoved < 6) {
          const dur = (performance.now() - mouseDownT) / 1000;
          I.push(dur < 0.28 ? 'attack' : dur < 0.8 ? 'heavy' : 'spin');
        }
      }
    };
    window.addEventListener('pointerdown', onDown);
    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
    window.addEventListener('pointercancel', onUp);
    window.addEventListener('wheel', e => { I.wheel += e.deltaY * 0.01; }, { passive: true });
    window.addEventListener('contextmenu', e => e.preventDefault());
    // フォーカス喪失時は入力状態を全解除 (押しっぱなし・カメラ固着防止)
    window.addEventListener('blur', () => {
      joyPtr = null; camPtr = null;
      I.held.jump = false; I.held.attack = false;
      I.moveX = 0; I.moveY = 0;
      for (const k in keys) keys[k] = false;
      hideJoy();
    });
  };

  I.updateFromKeys = function () {
    if (!G.isTouch || true) {
      const kx = (keys['KeyD'] ? 1 : 0) - (keys['KeyA'] ? 1 : 0);
      const ky = (keys['KeyS'] ? 1 : 0) - (keys['KeyW'] ? 1 : 0);
      if (kx || ky) {
        const l = Math.hypot(kx, ky);
        I.moveX = kx / l; I.moveY = ky / l;
      } else if (joyPtr === null) {
        // ジョイスティック優先
        if (!G.isTouch) { I.moveX = 0; I.moveY = 0; }
      }
      I.sprint = !!keys['ShiftLeft'] || !!keys['ShiftRight'] ||
        (Math.hypot(I.moveX, I.moveY) > 0.94 && G.isTouch);
    }
  };

  /* 仮想スティック表示 */
  let joyEl = null, thumbEl = null;
  function showJoy(x, y) {
    if (!joyEl) return;
    joyEl.style.display = 'block';
    joyEl.style.left = (x - 64) + 'px';
    joyEl.style.top = (y - 64) + 'px';
  }
  function moveJoyThumb(dx, dy) {
    if (thumbEl) thumbEl.style.transform = `translate(${dx}px, ${dy}px)`;
  }
  function hideJoy() {
    if (joyEl) joyEl.style.display = 'none';
    if (thumbEl) thumbEl.style.transform = 'translate(0,0)';
  }
  I.bindJoyEls = (j, t) => { joyEl = j; thumbEl = t; };
})();

/* ======================= UI 本体 ======================= */
(function () {
  const UI = G.UI = {};
  let root;

  function el(tag, cls, parent, html) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html !== undefined) e.innerHTML = html;
    (parent || root).appendChild(e);
    return e;
  }
  UI.el = el;

  /* タッチボタン生成 */
  function actionBtn(cls, label, action, opts) {
    opts = opts || {};
    const b = el('div', 'abtn ' + cls, hudEl, label);
    let downT = 0;
    b.addEventListener('pointerdown', e => {
      e.stopPropagation();
      G.Audio.init();
      downT = performance.now();
      b.classList.add('pressed');
      if (opts.heldKey) G.Input.held[opts.heldKey] = true;
      if (opts.fireOnPress) G.Input.push(action);
    });
    const fire = e => {
      e.stopPropagation();
      b.classList.remove('pressed');
      if (opts.heldKey) G.Input.held[opts.heldKey] = false;
      if (opts.fireOnPress) return;
      if (opts.holdable) {
        const dur = (performance.now() - downT) / 1000;
        G.Input.push(dur < 0.3 ? action : dur < 0.8 ? opts.holdAction : (opts.spinAction || opts.holdAction));
      } else {
        G.Input.push(action);
      }
    };
    b.addEventListener('pointerup', fire);
    b.addEventListener('pointercancel', e => {
      e.stopPropagation(); b.classList.remove('pressed');
      if (opts.heldKey) G.Input.held[opts.heldKey] = false;
    });
    return b;
  }

  /* ---------- 生成 ---------- */
  let hudEl, hpBar, hpFill, hpChip, staFill, xpFill, lvlEl, goldEl, clockEl, weatherEl;
  let hpChipW = 100, hpChipHold = 0;
  let miniCanvas, miniCtx, mapCanvas = null;
  let bigMapCanvas = null;
  let trackerEl, toastWrap, promptEl, bossWrap, bossFill, bossName, bossChip;
  let bossChipW = 100;
  let dlgWrap, dlgName, dlgText, dlgOpts;
  let menuWrap, menuTabs, menuBody;
  let deathEl, endEl, titleEl, introEl;
  let dmgLayer;
  let joyBase, joyThumb;
  let potBtn;

  UI.init = function () {
    root = document.getElementById('ui');

    /* HUD */
    hudEl = el('div', 'hud');
    // 左上: バー類
    const bars = el('div', 'bars', hudEl);
    lvlEl = el('div', 'lvl', bars, '1');
    const barCol = el('div', 'barcol', bars);
    hpBar = el('div', 'bar hp', barCol);
    hpChip = el('div', 'chip', hpBar);
    hpFill = el('div', 'fill', hpBar);
    const staBar = el('div', 'bar sta', barCol); staFill = el('div', 'fill', staBar);
    const xpBar = el('div', 'bar xp', barCol); xpFill = el('div', 'fill', xpBar);
    goldEl = el('div', 'gold', barCol, '<span class="gicon">G</span> 0');

    // 右上: ミニマップ + 時計
    const mmWrap = el('div', 'mmwrap', hudEl);
    miniCanvas = el('canvas', 'minimap', mmWrap);
    miniCanvas.width = 110; miniCanvas.height = 110;
    miniCtx = miniCanvas.getContext('2d');
    const under = el('div', 'mm-under', mmWrap);
    clockEl = el('div', 'clock', under, '9:30');
    weatherEl = el('div', 'weather', under, '☀');

    // クエストトラッカー
    trackerEl = el('div', 'tracker', hudEl);

    // トースト
    toastWrap = el('div', 'toasts', hudEl);

    // インタラクトプロンプト
    promptEl = el('div', 'prompt', hudEl);
    promptEl.style.display = 'none';
    promptEl.addEventListener('pointerdown', e => {
      e.stopPropagation();
      G.Input.push('interact');
    });

    // ボスバー
    bossWrap = el('div', 'bosswrap', hudEl);
    bossName = el('div', 'bossname', bossWrap, '');
    const bb = el('div', 'bossbar', bossWrap);
    bossChip = el('div', 'chip', bb);
    bossFill = el('div', 'fill', bb);
    bossWrap.style.display = 'none';

    // ダメージ数字レイヤ
    dmgLayer = el('div', 'dmglayer', hudEl);

    // 仮想スティック
    joyBase = el('div', 'joy', hudEl);
    joyThumb = el('div', 'joythumb', joyBase);
    joyBase.style.display = 'none';
    G.Input.bindJoyEls(joyBase, joyThumb);

    // タッチボタン
    if (G.isTouch) {
      actionBtn('b-attack', '<b>攻</b>', 'attack', { holdable: true, holdAction: 'heavy', spinAction: 'spin', heldKey: 'attack' });
      actionBtn('b-roll', '回避', 'roll');
      actionBtn('b-jump', '跳', 'jump', { fireOnPress: true, heldKey: 'jump' });
      actionBtn('b-lock', '◎<span class="blabel">注視</span>', 'lock');
      potBtn = actionBtn('b-potion', '薬', 'potion');
      actionBtn('b-menu', '≡', 'menu');
      actionBtn('b-map', '地図', 'map');
    } else {
      const help = el('div', 'keyhelp', hudEl,
        'WASD:移動 F/クリック:攻撃(長押し:強/回転) Space:回避 C:跳躍(空中長押し:滑空) E:調べる Q:ロックオン 1:薬 I:メニュー M:地図 Shift:走る');
      potBtn = null;
    }

    /* 会話 */
    dlgWrap = el('div', 'dialogue', root);
    dlgName = el('div', 'dlgname', dlgWrap);
    dlgText = el('div', 'dlgtext', dlgWrap);
    dlgOpts = el('div', 'dlgopts', dlgWrap);
    dlgWrap.style.display = 'none';

    /* メニュー */
    menuWrap = el('div', 'menu', root);
    const mHead = el('div', 'mhead', menuWrap);
    el('div', 'mtitle', mHead, 'ELDRIA');
    const closeB = el('div', 'mclose', mHead, '✕');
    closeB.addEventListener('pointerdown', e => { e.stopPropagation(); UI.closeMenu(); });
    menuTabs = el('div', 'mtabs', menuWrap);
    menuBody = el('div', 'mbody', menuWrap);
    menuWrap.style.display = 'none';
    const tabs = [['equip', '装備'], ['items', '持ち物'], ['map', '地図'], ['quests', '任務'], ['settings', '設定']];
    for (const [id, label] of tabs) {
      const t = el('div', 'mtab', menuTabs, label);
      t.dataset.tab = id;
      t.addEventListener('pointerdown', e => { e.stopPropagation(); G.Audio.sfx('ui'); UI.showTab(id); });
    }

    /* 死亡画面 */
    deathEl = el('div', 'death', root, '<div class="dtext">力尽きた…</div>');
    const respawnB = el('div', 'bigbtn', deathEl, '祠から再開');
    respawnB.addEventListener('pointerdown', e => { e.stopPropagation(); G.Game.respawn(); });
    deathEl.style.display = 'none';

    /* クリア画面 */
    endEl = el('div', 'ending', root);
    endEl.style.display = 'none';

    hudEl.style.display = 'none';   // タイトル中は隠す

    UI.refreshTracker();
    G.events.on('questChange', UI.refreshTracker);
    G.events.on('invChange', () => { UI.refreshHUDStatic(); if (menuOpen) UI.showTab(curTab); });
    G.events.on('bossEngage', b => UI.showBoss(b));
    G.events.on('bossDisengage', () => UI.hideBoss());
    G.events.on('bossKilled', () => UI.hideBoss());
    G.events.on('playerDead', () => { setTimeout(() => { deathEl.style.display = 'flex'; }, 900); });
    G.events.on('gameClear', () => setTimeout(UI.showEnding, 2200));
  };

  UI.setHudVisible = function (v) { hudEl.style.display = v ? '' : 'none'; };

  /* ---------- タイトル ---------- */
  UI.showTitle = function (onStart) {
    titleEl = el('div', 'title', root);
    el('div', 'tbg', titleEl);
    const inner = el('div', 'tinner', titleEl);
    el('div', 'tname', inner, 'ELDRIA');
    el('div', 'tsub', inner, '風と遺跡の大地');
    const btns = el('div', 'tbtns', inner);
    if (G.Save.exists()) {
      const c = el('div', 'bigbtn', btns, 'つづきから');
      c.addEventListener('pointerdown', e => { e.stopPropagation(); G.Audio.init(); G.Audio.sfx('uiOpen'); close(); onStart(false); });
    }
    const n = el('div', 'bigbtn' + (G.Save.exists() ? ' sub' : ''), btns, 'はじめから');
    n.addEventListener('pointerdown', e => {
      e.stopPropagation(); G.Audio.init();
      if (G.Save.exists() && !confirm('セーブデータを消して最初から始めますか?')) return;
      G.Audio.sfx('uiOpen'); close(); onStart(true);
    });
    el('div', 'tfoot', inner, G.isTouch ? '左半分: 移動スティック / 右半分: カメラ / ボタン: 攻撃・回避' : 'WASD移動 / マウスでカメラ / クリック攻撃');
    function close() { titleEl.remove(); titleEl = null; }
  };

  UI.showIntro = function () {
    UI.setHudVisible(false);
    introEl = el('div', 'intro', root,
      '<div class="imist"></div><div class="imist m2"></div>' +
      '<div class="iname">E L D R I A</div>' +
      '<div class="itext">霧深き大地エルドリア。<br><br>北の頂に黒竜ヴァルドレクが目覚めしとき、<br>大地は魔物で溢れ、人々は小さな村に身を寄せた。<br><br>――旅人よ。風がお前を呼んでいる。</div>');
    const skip = el('div', 'bigbtn', introEl, '旅を始める');
    skip.addEventListener('pointerdown', e => {
      e.stopPropagation();
      introEl.remove(); introEl = null;
      UI.setHudVisible(true);
      G.Audio.sfx('uiOpen');
    });
  };

  /* ---------- HUD 更新 ---------- */
  let hudT = 0, promptT = 0, curInteract = null;
  UI.refreshHUDStatic = function () {
    goldEl.innerHTML = '<span class="gicon">G</span> ' + G.Inv.gold;
    if (potBtn) {
      const n = G.Inv.count('potion') + G.Inv.count('hipotion');
      potBtn.innerHTML = '薬<span class="pcount">' + n + '</span>';
    }
  };

  UI.update = function (dt) {
    const p = G.Player;
    // バー
    const hpPctP = 100 * p.hp / p.maxHp();
    hpFill.style.width = hpPctP + '%';
    // 自機HPも遅延チップで被弾量を見せる (敵/ボスバーと同じUI言語)
    if (hpChipW < hpPctP) hpChipW = hpPctP;
    else if (hpChipW > hpPctP + 0.01) {
      if (hpChipHold <= 0) hpChipHold = 0.35;
    }
    if (hpChipHold > 0) hpChipHold -= dt;
    else hpChipW += (hpPctP - hpChipW) * G.damp(5.5, dt);
    hpChip.style.width = hpChipW + '%';
    staFill.style.width = (100 * p.stamina / p.maxSta()) + '%';
    xpFill.style.width = (100 * G.Stats.xp / G.Stats.xpNeed()) + '%';
    lvlEl.textContent = G.Stats.level;
    hpFill.classList.toggle('low', p.hp < p.maxHp() * 0.3);

    updateTrackerDist(dt);

    // 時計
    const tod = G.State.tod;
    const hh = Math.floor(tod), mm = Math.floor((tod - hh) * 60);
    clockEl.textContent = `${G.State.day}日目 ${hh}:${mm < 10 ? '0' : ''}${mm}`;
    weatherEl.textContent = G.State.weather > 0.5 ? '☂' : (tod > 19 || tod < 5 ? '☾' : '☀');

    // ボスバー (黄色の削り残像つき)
    if (curBoss) {
      const w = 100 * Math.max(0, curBoss.hp) / curBoss.maxHp;
      bossFill.style.width = w + '%';
      bossChipW += (w - bossChipW) * G.damp(2.2, dt);
      if (bossChipW < w) bossChipW = w;
      bossChip.style.width = bossChipW + '%';
    }

    // インタラクトプロンプト (0.15秒間隔で再探索)
    promptT -= dt;
    if (promptT <= 0) {
      promptT = 0.15;
      curInteract = G.findInteractable();
      if (curInteract && p.alive && !G.paused) {
        promptEl.style.display = 'block';
        promptEl.innerHTML = (G.isTouch ? '' : '<span class="pkey">E</span> ') + curInteract.label;
        UI.promptShowing = true;
      } else {
        promptEl.style.display = 'none';
        UI.promptShowing = false;
      }
    }

    // ミニマップは 0.1 秒間隔で再描画 (毎フレームは無駄、メニュー中は不要)
    mmT -= dt;
    if (mmT <= 0 && !menuOpen) { mmT = 0.1; updateMinimap(); }
    updateDmgNums(dt);
    updateEnemyBars(dt);
    updateToasts(dt);
  };
  let mmT = 0;

  /* ---------- ミニマップ ---------- */
  const MAP_R = 1000;       // ワールド範囲 ±1000
  let mapReady = false;
  UI.buildMap = function () {
    mapCanvas = document.createElement('canvas');
    mapCanvas.width = mapCanvas.height = 256;
    const ctx = mapCanvas.getContext('2d');
    const img = ctx.createImageData(256, 256);
    for (let j = 0; j < 256; j++) {
      for (let i = 0; i < 256; i++) {
        const x = (i / 256) * MAP_R * 2 - MAP_R;
        const z = (j / 256) * MAP_R * 2 - MAP_R;
        const c = G.World.minimapColor(x, z);
        const o = (j * 256 + i) * 4;
        img.data[o] = Math.min(255, c.r * 255);
        img.data[o + 1] = Math.min(255, c.g * 255);
        img.data[o + 2] = Math.min(255, c.b * 255);
        img.data[o + 3] = 255;
      }
    }
    ctx.putImageData(img, 0, 0);
    mapReady = true;
  };

  function worldToMap(x, z, size) {
    return [(x + MAP_R) / (MAP_R * 2) * size, (z + MAP_R) / (MAP_R * 2) * size];
  }

  function updateMinimap() {
    if (!mapReady) return;
    const p = G.Player;
    const ctx = miniCtx;
    const S = 110;
    const view = 340;   // 表示範囲 (m)
    ctx.clearRect(0, 0, S, S);
    ctx.save();
    ctx.beginPath();
    ctx.arc(S / 2, S / 2, S / 2 - 1, 0, Math.PI * 2);
    ctx.clip();
    if (G.inCave) {
      // 洞窟は島の地図の範囲外 — 洞窟床色で塗って可読性を保つ
      ctx.fillStyle = '#2a3044';
      ctx.fillRect(0, 0, S, S);
    } else {
      const scale = (256 / (MAP_R * 2));
      const sw = view * scale;
      const [mx, mz] = worldToMap(p.pos.x, p.pos.z, 256);
      ctx.drawImage(mapCanvas, mx - sw / 2, mz - sw / 2, sw, sw, 0, 0, S, S);
    }
    // 祠
    for (const s of G.World.shrines) {
      if (!G.State.shrines[s.id]) continue;
      const dx = (s.x - p.pos.x) / view * S + S / 2;
      const dz = (s.z - p.pos.z) / view * S + S / 2;
      if (dx < 0 || dx > S || dz < 0 || dz > S) continue;
      ctx.fillStyle = '#6fe3ff';
      ctx.beginPath(); ctx.arc(dx, dz, 3, 0, Math.PI * 2); ctx.fill();
    }
    // クエストマーカー
    ctx.fillStyle = '#ffd35a';
    for (const m of G.Quests.marks()) {
      const dx = (m.x - p.pos.x) / view * S + S / 2;
      const dz = (m.z - p.pos.z) / view * S + S / 2;
      const cx = G.clamp(dx, 6, S - 6), cz = G.clamp(dz, 6, S - 6);
      ctx.beginPath();
      ctx.moveTo(cx, cz - 4); ctx.lineTo(cx + 4, cz); ctx.lineTo(cx, cz + 4); ctx.lineTo(cx - 4, cz);
      ctx.closePath(); ctx.fill();
    }
    // 敵 (配列生成を避けるため list と bosses を別々に描く)
    ctx.fillStyle = '#ff5a5a';
    const drawEnemy = e => {
      if (!e.alive) return;
      const dx = (e.pos.x - p.pos.x) / view * S + S / 2;
      const dz = (e.pos.z - p.pos.z) / view * S + S / 2;
      if (dx < 4 || dx > S - 4 || dz < 4 || dz > S - 4) return;
      ctx.beginPath(); ctx.arc(dx, dz, 1.6, 0, Math.PI * 2); ctx.fill();
    };
    // 村人など友好NPCは緑 (赤=敵の誤認を防ぐ)
    ctx.fillStyle = '#7fe37f';
    for (const n of G.NPCs.list) {
      const dx = (n.pos.x - p.pos.x) / view * S + S / 2;
      const dz = (n.pos.z - p.pos.z) / view * S + S / 2;
      if (dx < 4 || dx > S - 4 || dz < 4 || dz > S - 4) continue;
      ctx.beginPath(); ctx.arc(dx, dz, 1.8, 0, Math.PI * 2); ctx.fill();
    }
    ctx.fillStyle = '#ff5a5a';
    for (const e of G.Enemies.list) drawEnemy(e);
    // ボスは白縁の大きな菱形で明示
    for (const b of G.Enemies.bosses) {
      if (!b.alive) continue;
      const dx = (b.pos.x - p.pos.x) / view * S + S / 2;
      const dz = (b.pos.z - p.pos.z) / view * S + S / 2;
      if (dx < 5 || dx > S - 5 || dz < 5 || dz > S - 5) continue;
      ctx.fillStyle = '#ff3030';
      ctx.strokeStyle = '#fff';
      ctx.lineWidth = 1.2;
      ctx.beginPath();
      ctx.moveTo(dx, dz - 5); ctx.lineTo(dx + 5, dz); ctx.lineTo(dx, dz + 5); ctx.lineTo(dx - 5, dz);
      ctx.closePath(); ctx.fill(); ctx.stroke();
      ctx.fillStyle = '#ff5a5a';
    }
    // プレイヤー矢印
    ctx.save();
    ctx.translate(S / 2, S / 2);
    ctx.rotate(-p.yaw + Math.PI);
    ctx.fillStyle = '#fff';
    ctx.beginPath();
    ctx.moveTo(0, -6); ctx.lineTo(4, 5); ctx.lineTo(0, 2.5); ctx.lineTo(-4, 5);
    ctx.closePath(); ctx.fill();
    ctx.restore();
    ctx.restore();
    // 枠 (ボス交戦中は赤く脈動して戦闘状態を示す)
    let bossOn = false;
    for (const b of G.Enemies.bosses) { if (b.alive && b.engaged) { bossOn = true; break; } }
    if (bossOn) {
      ctx.strokeStyle = `rgba(255,70,60,${0.5 + Math.sin(G.time * 5) * 0.3})`;
      ctx.lineWidth = 3;
    } else {
      ctx.strokeStyle = 'rgba(255,255,255,0.5)';
      ctx.lineWidth = 1.5;
    }
    ctx.beginPath(); ctx.arc(S / 2, S / 2, S / 2 - 1, 0, Math.PI * 2); ctx.stroke();
  }

  /* ---------- ダメージ数字 ---------- */
  const dmgPool = [];
  UI.dmgNum = function (x, y, z, n, opts) {
    if (!G.settings.showDmg) return;
    opts = opts || {};
    // 同一対象への連続ヒットは合算表示 (画面が数字で埋まるのを防ぐ)
    if (opts.tgt) {
      const now = performance.now();
      const ex = dmgPool.find(d => d.active && d.tgt === opts.tgt &&
        now - d.born < 420 && !d.crit === !opts.crit &&
        now - (d.firstBorn || d.born) < 1200);   // 1.2秒で合算を確定し新規へ
      if (ex) {
        ex.val += n;
        ex.eln.textContent = ex.val;
        // 合算中はフェードをリセット (合計値を読み切れる寿命を保証)
        ex.born = Math.max(ex.born, now - 300);
        // 対象が動いた場合は現在位置へ緩やかに寄せる
        ex.x += (x - ex.x) * 0.4; ex.z += (z - ex.z) * 0.4;
        return;
      }
    }
    let d = dmgPool.find(d => !d.active);
    if (!d) {
      if (dmgPool.length >= 40) {
        // プール上限: 最も古い表示を再利用
        d = dmgPool.reduce((a, c) => (c.born < a.born ? c : a), dmgPool[0]);
      } else {
        d = { eln: el('div', 'dmgnum', dmgLayer), active: false };
        dmgPool.push(d);
      }
    }
    d.active = true; d.t = 0; d.born = performance.now();
    d.firstBorn = d.born; d.riseBorn = d.born;
    d.val = n; d.tgt = opts.tgt || null; d.crit = !!opts.crit;
    // ▼ロックオンマーカー/HPバーと重ならないよう、頭上さらに上へ
    d.x = x + (Math.random() - 0.5) * 1.6; d.y = y + 0.7 + Math.random() * 0.5; d.z = z;
    d.eln.textContent = n;
    d.eln.className = 'dmgnum' + (opts.crit ? ' crit' : '') + (opts.player ? ' onplayer' : '');
    d.eln.style.display = 'block';
  };
  function updateDmgNums(dt) {
    // 実時間で寿命管理 (低FPS環境でゲームdtが縮んでも数分残留させない)
    const now = performance.now();
    for (const d of dmgPool) {
      if (!d.active) continue;
      d.t = (now - (d.born || now)) / 1000;
      if (d.t > 0.9) { d.active = false; d.eln.style.display = 'none'; continue; }
      // 上昇は合算でリセットされない専用タイマーで (数字が下に跳ねない)
      const riseT = (now - (d.riseBorn || d.born)) / 1000;
      const pr = UI.project(d.x, d.y + Math.min(riseT, 1.2) * 1.2, d.z);
      if (!pr.visible) { d.eln.style.display = 'none'; continue; }
      d.eln.style.display = 'block';
      d.eln.style.left = pr.x + 'px';
      d.eln.style.top = pr.y + 'px';
      d.eln.style.opacity = d.t > 0.6 ? String(1 - (d.t - 0.6) / 0.3) : '1';
    }
  }

  /* ---------- 敵HPバー ---------- */
  const ebarPool = [];
  function updateEnemyBars(dt) {
    let used = 0;
    const p = G.Player;
    const placedBars = [];
    for (const e of G.Enemies.list) {
      if (!e.alive || !e.aggro) continue;
      if (G.dist2(p.pos.x, p.pos.z, e.pos.x, e.pos.z) > 40 * 40) continue;
      const pr = UI.project(e.pos.x, e.pos.y + (e.T.barH || 1.9), e.pos.z);
      if (!pr.visible) continue;
      // 密集時はスクリーン空間で縦にずらして重なりを避ける
      for (let k = 0; k < placedBars.length; k++) {
        const q = placedBars[k];
        if (Math.abs(pr.x - q.x) < 58 && Math.abs(pr.y - q.y) < 10) pr.y = q.y - 11;
      }
      placedBars.push({ x: pr.x, y: pr.y });
      let b = ebarPool[used];
      if (!b) {
        const wrap = el('div', 'ebar', dmgLayer);
        const chip = el('div', 'chip', wrap);
        const fill = el('div', 'fill', wrap);
        b = { wrap, fill, chip };
        ebarPool.push(b);
      }
      used++;
      b.wrap.style.display = 'block';
      b.wrap.style.left = pr.x + 'px';
      b.wrap.style.top = pr.y + 'px';
      const hpPct = 100 * Math.max(0, e.hp) / e.maxHp;
      b.fill.style.width = hpPct + '%';
      // 遅延チップ: 0.35秒保持してから dt 基準で追従 (リフレッシュレート非依存)
      if (e._chipW === undefined || e._chipW < hpPct) e._chipW = hpPct;
      if (e._chipW > hpPct + 0.01 && e._chipPrev !== hpPct) { e._chipHold = 0.35; e._chipPrev = hpPct; }
      if (e._chipHold > 0) e._chipHold -= dt;
      else e._chipW += (hpPct - e._chipW) * G.damp(5.5, dt);
      b.chip.style.width = e._chipW + '%';
      // ロックオン対象マーク
      b.wrap.classList.toggle('locked', G.Player.target === e);
      if (used >= 12) break;
    }
    for (let i = used; i < ebarPool.length; i++) ebarPool[i].wrap.style.display = 'none';
  }

  /* ---------- 投影 ---------- */
  const _v = new THREE.Vector3();
  UI.project = function (x, y, z) {
    const cam = G.Camera.cam;
    _v.set(x, y, z).project(cam);
    if (_v.z > 1 || _v.z < -1) return { x: 0, y: 0, visible: false };
    return {
      x: (_v.x * 0.5 + 0.5) * window.innerWidth,
      y: (-_v.y * 0.5 + 0.5) * window.innerHeight,
      visible: true
    };
  };

  /* ---------- トースト ---------- */
  const toasts = [];
  UI.toast = function (msg, kind) {
    const t = el('div', 'toast ' + (kind || ''), toastWrap, msg);
    toasts.push({ eln: t, born: performance.now() });
    if (toasts.length > 3) {
      const old = toasts.shift();
      old.eln.remove();
    }
  };
  UI.clearToasts = function () {
    for (const t of toasts) t.eln.remove();
    toasts.length = 0;
  };
  function updateToasts() {
    // 実時間で寿命管理 (低FPS環境でゲームdtが縮んでも残留させない)
    const now = performance.now();
    for (let i = toasts.length - 1; i >= 0; i--) {
      const age = (now - toasts[i].born) / 1000;
      if (age > 2.6) { toasts[i].eln.classList.add('fade'); }
      if (age > 3.4) { toasts[i].eln.remove(); toasts.splice(i, 1); }
    }
  }

  /* ---------- 段階式チュートリアルチップ ---------- */
  let tutEl = null;
  let khWanted = true;   // チュートリアル中などは false (会話後の復元先)
  UI.showTutChip = function (html) {
    if (!tutEl) tutEl = el('div', 'tutchip', hudEl);
    tutEl.innerHTML = html;
    tutEl.style.display = 'block';
    tutEl.classList.remove('pop'); void tutEl.offsetWidth; tutEl.classList.add('pop');
  };
  UI.hideTutChip = function () { if (tutEl) tutEl.style.display = 'none'; };
  UI.setKeyhelpVisible = function (v) {
    khWanted = v;
    const kh = hudEl.querySelector('.keyhelp');
    if (kh) kh.style.display = (v && !G.isTouch) ? '' : 'none';
  };

  /* ---------- クエストトラッカー ---------- */
  let trackerMark = null;
  UI.refreshTracker = function () {
    const lines = G.Quests.trackerLines().slice(0, 3);
    trackerMark = null;
    trackerEl.innerHTML = lines.map((l, i) => {
      // 先頭 (メイン優先) のクエストには目標距離を添える
      let dist = '';
      if (i === 0 && l.mx !== null) {
        trackerMark = { x: l.mx, z: l.mz };
        dist = ' <span class="tdist"></span>';
      }
      return `<div class="tline ${l.main ? 'main' : ''} ${l.ready ? 'ready' : ''}">${l.line}${dist}</div>`;
    }).join('');
  };
  let tdistT = 0;
  function updateTrackerDist(dt) {
    tdistT -= dt;
    if (tdistT > 0 || !trackerMark) return;
    tdistT = 0.5;
    const eln = trackerEl.querySelector('.tdist');
    if (!eln) return;
    const d = G.dist(G.Player.pos.x, G.Player.pos.z, trackerMark.x, trackerMark.z);
    eln.textContent = d > 12 ? Math.round(d) + 'm' : '';
  }

  /* ---------- ボスバー ---------- */
  let curBoss = null;
  UI.showBoss = function (b) {
    const isNew = curBoss !== b;
    curBoss = b;
    bossChipW = 100 * Math.max(0, b.hp) / b.maxHp;
    bossName.textContent = b.name;
    bossWrap.style.display = 'block';
    if (isNew) {
      // 登場演出: 通常トースト/クエストトラッカーを消し、中央に大きく名前
      UI.clearToasts();
      trackerEl.style.opacity = '0';
      const intro = el('div', 'bossintro', root, b.name);
      setTimeout(() => { intro.classList.add('out'); }, 5600);
      setTimeout(() => { intro.remove(); }, 7000);
      // ボス戦中は操作ヘルプを隠して緊張感を保つ
      const kh = hudEl.querySelector('.keyhelp');
      if (kh) kh.style.display = 'none';
    }
  };
  UI.hideBoss = function () {
    curBoss = null;
    bossWrap.style.display = 'none';
    trackerEl.style.opacity = '';
    const kh = hudEl.querySelector('.keyhelp');
    if (kh && !G.isTouch) kh.style.display = '';
  };

  /* ---------- 会話 ---------- */
  UI.showDialogue = function (name, node) {
    G.paused = true;
    UI.hideTutChip();
    hudEl.classList.add('dlgmode');
    const kh = hudEl.querySelector('.keyhelp');
    if (kh) kh.style.display = 'none';
    dlgWrap.style.display = 'block';
    dlgName.textContent = name;
    renderNode(node);
    function renderNode(nd) {
      dlgOpts.innerHTML = '';
      typeText(nd.text, () => {
        for (const op of nd.options) {
          const b = el('div', 'dlgopt', dlgOpts, op.label);
          b.addEventListener('pointerdown', ev => {
            ev.stopPropagation();
            G.Audio.sfx('ui');
            if (op.closeText) {
              if (op.action) op.action();
              dlgOpts.innerHTML = '';
              typeText(op.closeText, () => {
                const c = el('div', 'dlgopt', dlgOpts, '（会話を終える）');
                c.addEventListener('pointerdown', e2 => { e2.stopPropagation(); UI.closeDialogue(); });
              });
            } else if (op.next) {
              if (op.action) op.action();
              renderNode(op.next);
            } else {
              // 会話を閉じてからアクション (商店などが paused を管理できるように)
              UI.closeDialogue();
              if (op.action) op.action();
            }
          });
        }
      });
    }
  };
  /* ゲームループ (dt) 駆動のタイプライター — タイマースロットルの影響を受けない */
  let typing = null;   // {text, i, done}
  function typeText(text, done) {
    typing = { text, i: 0, done };
    dlgText.textContent = '';
    // タップで全文表示スキップ
    dlgText.onpointerdown = e => { e.stopPropagation(); finishTyping(); };
  }
  function finishTyping() {
    if (!typing) return;
    const t = typing; typing = null;
    dlgText.textContent = t.text;
    if (t.done) t.done();
  }
  UI.updateTyping = function (dt) {
    if (!typing) return;
    typing.i += dt * 110;                      // 110文字/秒
    if (typing.i >= typing.text.length) { finishTyping(); return; }
    dlgText.textContent = typing.text.slice(0, typing.i | 0);
  };
  UI.closeDialogue = function () {
    dlgWrap.style.display = 'none';
    G.paused = false;
    typing = null;
    hudEl.classList.remove('dlgmode');
    // チュートリアル中に非表示化されている場合は復元しない
    const kh = hudEl.querySelector('.keyhelp');
    if (kh && khWanted && !G.isTouch) kh.style.display = '';
    G.events.emit('dialogueClosed');
  };

  /* ---------- 祠メニュー ---------- */
  UI.shrineMenu = function (shrine) {
    G.paused = true;
    dlgWrap.style.display = 'block';
    dlgName.textContent = shrine.name;
    dlgText.textContent = '祠の温かな光が体を包む。どうする?';
    dlgOpts.innerHTML = '';
    const mk = (label, fn) => {
      const b = el('div', 'dlgopt', dlgOpts, label);
      b.addEventListener('pointerdown', e => { e.stopPropagation(); G.Audio.sfx('ui'); fn(); });
    };
    mk('休む (全回復・再開地点に設定)', () => {
      G.Player.heal(9999);
      G.Player.stamina = G.Stats.maxSta();
      G.State.respawn = shrine.id;
      G.Save.save();
      UI.toast('体力が回復し、記録した', 'gold');
      G.Audio.sfx('shrine');
      UI.closeDialogue();
    });
    mk('時を送る (朝/夜へ)', () => {
      const tod = G.State.tod;
      if (tod > 5 && tod < 19) { G.State.tod = 20.5; }
      else { G.State.tod = 6.5; G.State.day++; }
      UI.toast('時が流れた…');
      UI.closeDialogue();
    });
    mk('ファストトラベル', () => {
      UI.closeDialogue();
      UI.openMenu('map');
    });
    mk('立ち去る', () => UI.closeDialogue());
  };

  /* ---------- メニュー ---------- */
  let menuOpen = false, curTab = 'equip';
  UI.isMenuOpen = () => menuOpen;
  UI.openMenu = function (tab) {
    menuOpen = true;
    G.paused = true;
    hudEl.style.visibility = 'hidden';
    menuTabs.style.display = '';
    menuWrap.style.display = 'flex';
    G.Audio.sfx('uiOpen');
    UI.showTab(tab || 'equip');
  };
  UI.closeMenu = function () {
    menuOpen = false;
    G.paused = false;
    hudEl.style.visibility = '';
    menuWrap.style.display = 'none';
    G.Audio.sfx('ui');
  };
  UI.toggleMenu = function (tab) {
    if (menuOpen) UI.closeMenu(); else UI.openMenu(tab);
  };

  UI.showTab = function (tab) {
    curTab = tab;
    for (const t of menuTabs.children) t.classList.toggle('on', t.dataset.tab === tab);
    menuBody.innerHTML = '';
    if (tab === 'equip') renderEquip();
    else if (tab === 'items') renderItems();
    else if (tab === 'map') renderMap();
    else if (tab === 'quests') renderQuests();
    else if (tab === 'settings') renderSettings();
  };

  function renderEquip() {
    const s = el('div', 'stats', menuBody);
    s.innerHTML = `
      <div>Lv <b>${G.Stats.level}</b></div>
      <div>HP <b>${Math.round(G.Player.hp)}/${G.Stats.maxHp()}</b></div>
      <div>攻撃 <b>${G.Stats.atk()}</b></div>
      <div>防御 <b>${G.Stats.def()}</b></div>
      <div>次のLvまで <b>${G.Stats.xpNeed() - G.Stats.xp}</b></div>`;
    const list = el('div', 'ilist', menuBody);
    const ids = Object.keys(G.Inv.items);
    let has = false;
    for (const id of ids) {
      const it = G.Items.get(id);
      if (!it || (it.type !== 'weapon' && it.type !== 'armor')) continue;
      has = true;
      const equipped = G.Inv.equip.weapon === id || G.Inv.equip.armor === id;
      const row = el('div', 'irow' + (equipped ? ' equipped' : ''), list);
      const ul = G.Inv.upgLevel(id);
      const st = it.type === 'weapon' ? `攻 ${it.atk + ul * 2}` : `防 ${it.def + ul}`;
      const glyph = it.type === 'weapon' ? '⚔️' : '🛡️';
      row.innerHTML = `<div class="iname"><span class="rowicon">${glyph}</span>${it.name}${ul ? ' +' + ul : ''} <span class="istat">${st}</span></div><div class="idesc">${it.desc}</div>`;
      if (!equipped) {
        const b = el('div', 'ibtn', row, '装備');
        b.addEventListener('pointerdown', e => { e.stopPropagation(); G.Inv.equipItem(id); });
      } else {
        el('div', 'itag', row, '装備中');
      }
    }
    // 初期装備は所持数に現れないため必ず出す
    for (const id of [G.Inv.equip.weapon, G.Inv.equip.armor]) {
      if (ids.includes(id)) continue;
      const it = G.Items.get(id);
      if (!it) continue;
      has = true;
      const ul = G.Inv.upgLevel(id);
      const row = el('div', 'irow equipped', list);
      const st = it.type === 'weapon' ? `攻 ${it.atk + ul * 2}` : `防 ${it.def + ul}`;
      const glyph = it.type === 'weapon' ? '⚔️' : '🛡️';
      row.innerHTML = `<div class="iname"><span class="rowicon">${glyph}</span>${it.name}${ul ? ' +' + ul : ''} <span class="istat">${st}</span></div><div class="idesc">${it.desc}</div>`;
      el('div', 'itag', row, '装備中');
    }
    if (!has) el('div', 'mnote', menuBody, '装備品は宝箱や店、ボス討伐で手に入る。');
  }

  /* アイテム種別ごとの絵文字アイコンとタイル色 */
  const ITEM_ICONS = {
    potion: ['🧪', '#7a2e3e'], hipotion: ['🧪', '#8e2438'], herb: ['🌿', '#2e5a38'],
    pelt: ['🟤', '#5a4430'], bone: ['🦴', '#565a62'], magicstone: ['💠', '#2e4a72'],
  };
  function itemIcon(id, it) {
    if (ITEM_ICONS[id]) return ITEM_ICONS[id];
    if (it.type === 'weapon') return ['⚔️', '#4e4258'];
    if (it.type === 'armor') return ['🛡️', '#3e4a58'];
    return ['📦', '#4a4438'];
  }

  function renderItems() {
    const ids = Object.keys(G.Inv.items);
    if (!ids.length) { el('div', 'mnote', menuBody, '何も持っていない。'); return; }
    // アイコン付きグリッド + 下に選択中アイテムの詳細
    const grid = el('div', 'igrid', menuBody);
    const detail = el('div', 'idetail', menuBody);
    let selected = null;
    const select = (id, it, tile) => {
      selected = id;
      grid.querySelectorAll('.itile.on').forEach(t => t.classList.remove('on'));
      tile.classList.add('on');
      detail.innerHTML = `<div class="iname">${it.name} ×${G.Inv.count(id)}</div><div class="idesc">${it.desc}</div>`;
      if (it.type === 'consumable') {
        const b = el('div', 'ibtn', detail, '使う');
        b.addEventListener('pointerdown', e => {
          e.stopPropagation();
          if (id === 'potion' || id === 'hipotion') { G.Player.potionCd = 0; G.Player.usePotion(id); }
          else if (id === 'herb') {
            if (G.Inv.remove('herb', 1)) { G.Player.heal(Math.round(G.Player.maxHp() * 0.12)); G.Audio.sfx('potion'); }
          }
          UI.showTab('items');
        });
      }
    };
    let first = null;
    for (const id of ids) {
      const it = G.Items.get(id);
      if (!it) continue;
      const [glyph, tint] = itemIcon(id, it);
      const tile = el('div', 'itile', grid);
      tile.style.background = tint;
      tile.innerHTML = `<div class="iglyph">${glyph}</div><div class="icount">×${G.Inv.count(id)}</div><div class="itname">${it.name}</div>`;
      tile.addEventListener('pointerdown', e => { e.stopPropagation(); G.Audio.sfx('ui'); select(id, it, tile); });
      if (!first) first = [id, it, tile];
    }
    if (first) select(first[0], first[1], first[2]);
  }

  function renderMap() {
    const wrap = el('div', 'mapwrap', menuBody);
    if (!bigMapCanvas) {
      bigMapCanvas = document.createElement('canvas');
      bigMapCanvas.width = bigMapCanvas.height = 512;
    }
    wrap.appendChild(bigMapCanvas);
    drawBigMap();
    // 凡例は横に並べて地図を大きく取る
    el('div', 'maplegend', wrap,
      '<div>◆ 任務</div><div>● 祠<br><span class="mlsub">タップで<br>ファストトラベル</span></div><div>▲ 現在地</div>');
    // 祠タップでファストトラベル
    bigMapCanvas.onpointerdown = e => {
      e.stopPropagation();
      const rect = bigMapCanvas.getBoundingClientRect();
      const mx = (e.clientX - rect.left) / rect.width * 512;
      const mz = (e.clientY - rect.top) / rect.height * 512;
      for (const s of G.World.shrines) {
        if (!G.State.shrines[s.id]) continue;
        const [sx, sz] = worldToMap(s.x, s.z, 512);
        if (Math.hypot(mx - sx, mz - sz) < 18) {
          if (confirm(s.name + ' へ移動しますか?')) {
            UI.closeMenu();
            G.Game.travelTo(s);
          }
          return;
        }
      }
    };
  }

  function drawBigMap() {
    const ctx = bigMapCanvas.getContext('2d');
    ctx.drawImage(mapCanvas, 0, 0, 512, 512);
    // 祠
    for (const s of G.World.shrines) {
      if (!G.State.shrines[s.id]) continue;
      const [x, z] = worldToMap(s.x, s.z, 512);
      ctx.fillStyle = '#6fe3ff';
      ctx.beginPath(); ctx.arc(x, z, 7, 0, Math.PI * 2); ctx.fill();
      ctx.strokeStyle = '#fff'; ctx.lineWidth = 2; ctx.stroke();
      ctx.fillStyle = '#eaf6ff';
      ctx.font = '12px sans-serif';
      ctx.fillText(s.name, x + 10, z + 4);
    }
    // クエストマーカー
    for (const m of G.Quests.marks()) {
      const [x, z] = worldToMap(m.x, m.z, 512);
      ctx.fillStyle = '#ffd35a';
      ctx.beginPath();
      ctx.moveTo(x, z - 9); ctx.lineTo(x + 9, z); ctx.lineTo(x, z + 9); ctx.lineTo(x - 9, z);
      ctx.closePath(); ctx.fill();
      ctx.strokeStyle = '#7a5a00'; ctx.lineWidth = 1.5; ctx.stroke();
    }
    // 村
    {
      const [x, z] = worldToMap(0, 0, 512);
      ctx.fillStyle = '#ffe9b0';
      ctx.font = 'bold 13px sans-serif';
      ctx.fillText('ミストヴェイル村', x - 44, z - 10);
    }
    // プレイヤー
    const p = G.Player;
    const [px, pz] = worldToMap(p.pos.x, p.pos.z, 512);
    ctx.save();
    ctx.translate(px, pz);
    ctx.rotate(-p.yaw + Math.PI);
    ctx.fillStyle = '#fff';
    ctx.strokeStyle = '#222';
    ctx.beginPath();
    ctx.moveTo(0, -10); ctx.lineTo(7, 8); ctx.lineTo(0, 4); ctx.lineTo(-7, 8);
    ctx.closePath(); ctx.fill(); ctx.stroke();
    ctx.restore();
  }

  function renderQuests() {
    const list = el('div', 'qlist', menuBody);
    const ids = Object.keys(G.Quests.state);
    if (!ids.length) el('div', 'mnote', menuBody, 'まだ任務はない。');
    const order = ids.sort((a, b) => {
      const da = G.Quests.DEFS[a], db = G.Quests.DEFS[b];
      const sa = G.Quests.state[a].status === 'done' ? 1 : 0;
      const sb = G.Quests.state[b].status === 'done' ? 1 : 0;
      if (sa !== sb) return sa - sb;
      return (db.main ? 1 : 0) - (da.main ? 1 : 0);
    });
    for (const id of order) {
      const D = G.Quests.DEFS[id], st = G.Quests.state[id];
      const row = el('div', 'qrow ' + st.status, list);
      let prog = '';
      if (D.kill) prog = ` (${Math.min(st.progress, D.count)}/${D.count})`;
      if (D.collect) prog = ` (${Math.min(G.Inv.count(D.collect), D.count)}/${D.count})`;
      row.innerHTML = `<div class="qname">${D.main ? '【主】' : '【副】'}${D.name}${prog}</div>
        <div class="qdesc">${st.status === 'done' ? '達成済み' : st.status === 'ready' ? '条件達成 — 報告しよう' : D.desc}</div>`;
    }
    // 称号
    el('div', 'shophead', menuBody, '― 称号 ―');
    const tl = el('div', 'qlist', menuBody);
    let any = false;
    for (const id in G.Achieve.DEFS) {
      const got = G.State.titles && G.State.titles[id];
      if (!got) continue;
      any = true;
      const D = G.Achieve.DEFS[id];
      const row = el('div', 'qrow ready', tl);
      row.innerHTML = `<div class="qname">「${D.name}」</div><div class="qdesc">${D.desc}</div>`;
    }
    if (!any) el('div', 'mnote', menuBody, '称号はまだない。討伐や探索で手に入る。');
    el('div', 'mnote', menuBody, `討伐数: ${G.State.killCount || 0}`);
  }

  function renderSettings() {
    const wrap = el('div', 'setlist', menuBody);
    const mkSlider = (label, get, set) => {
      const row = el('div', 'srow', wrap);
      el('div', 'slabel', row, label);
      const input = document.createElement('input');
      input.type = 'range'; input.min = 0; input.max = 100;
      input.value = Math.round(get() * 100);
      const val = el('div', 'sval', null, input.value + '%');
      const paint = () => {
        input.style.setProperty('--fill', input.value + '%');
        val.textContent = input.value + '%';
      };
      paint();
      input.addEventListener('input', () => { set(input.value / 100); paint(); });
      input.addEventListener('pointerdown', e => e.stopPropagation());
      row.appendChild(input);
      row.appendChild(val);
    };
    mkSlider('音楽', () => G.settings.music, v => { G.settings.music = v; G.Audio.setMusicVol(v); G.settings.save(); });
    mkSlider('効果音', () => G.settings.sfx, v => { G.settings.sfx = v; G.Audio.setSfxVol(v); G.settings.save(); });
    mkSlider('カメラ感度', () => G.settings.sens / 2, v => { G.settings.sens = v * 2; G.settings.save(); });

    const qrow = el('div', 'srow', wrap);
    el('div', 'slabel', qrow, '描画品質 (要リロード)');
    const sel = document.createElement('select');
    for (const [v, l] of [['auto', '自動'], ['low', '低'], ['mid', '中'], ['high', '高']]) {
      const o = document.createElement('option');
      o.value = v; o.textContent = l;
      if (G.settings.quality === v) o.selected = true;
      sel.appendChild(o);
    }
    sel.addEventListener('change', () => { G.settings.quality = sel.value; G.settings.save(); UI.toast('リロードで反映されます'); });
    sel.addEventListener('pointerdown', e => e.stopPropagation());
    qrow.appendChild(sel);

    const save = el('div', 'bigbtn sub', wrap, '手動セーブ');
    save.addEventListener('pointerdown', e => {
      e.stopPropagation();
      if (G.Save.save()) UI.toast('セーブした', 'gold');
    });
    el('div', 'dangergap', wrap);
    const reset = el('div', 'bigbtn danger small', wrap, 'データを消して最初から');
    reset.addEventListener('pointerdown', e => {
      e.stopPropagation();
      if (confirm('本当にセーブデータを削除しますか?') &&
          confirm('全ての進行が失われます。最終確認: 削除しますか?')) {
        G.Save.reset();
        location.reload();
      }
    });
    el('div', 'mnote', wrap, 'ELDRIA v1.0 — 完全プロシージャル・オープンワールドARPG。データは端末内に保存されます。');
  }

  /* ---------- 商店 ---------- */
  UI.openShop = function () {
    G.paused = true;
    menuOpen = true;
    hudEl.style.visibility = 'hidden';
    menuWrap.style.display = 'flex';
    menuTabs.style.display = 'none';
    menuBody.innerHTML = '';
    el('div', 'shoptitle', menuBody, '🛒 モーガンの店');
    el('div', 'mnote', menuBody, `所持金: ${G.Inv.gold} G`);
    el('div', 'shophead', menuBody, '― 購入 ―');
    const buy = el('div', 'ilist', menuBody);
    for (const id of G.Shop.stock) {
      const it = G.Items.get(id);
      const row = el('div', 'irow', buy);
      // 装備中との比較差分を添える (+4 / -2)
      let st = '';
      if (it.type === 'weapon' || it.type === 'armor') {
        const curId = G.Inv.equip[it.type];
        const cur = G.Items.get(curId);
        const lvl = curId ? G.Inv.upgLevel(curId) : 0;
        const curV = cur ? (it.type === 'weapon' ? cur.atk + lvl * 2 : cur.def + lvl) : 0;
        const v = it.type === 'weapon' ? it.atk : it.def;
        const diff = v - curV;
        const dTxt = diff === 0 ? '' :
          ` <span class="${diff > 0 ? 'diffup' : 'diffdown'}">(${diff > 0 ? '+' : ''}${diff})</span>`;
        st = ` / ${it.type === 'weapon' ? '攻' : '防'} ${v}${dTxt}`;
      }
      row.innerHTML = `<div class="iname">${it.name} <span class="istat">${it.price}G${st}</span></div><div class="idesc">${it.desc}</div>`;
      if (G.Inv.gold >= it.price) {
        const b = el('div', 'ibtn', row, '買う');
        b.addEventListener('pointerdown', e => { e.stopPropagation(); if (G.Shop.buy(id)) UI.openShop(); });
      } else {
        el('div', 'ibtn off', row, 'G不足');
      }
    }
    el('div', 'shophead', menuBody, '― 売却 ―');
    const sell = el('div', 'ilist', menuBody);
    let any = false;
    for (const id of Object.keys(G.Inv.items)) {
      const it = G.Items.get(id);
      if (!it || !it.sell) continue;
      any = true;
      const row = el('div', 'irow', sell);
      row.innerHTML = `<div class="iname">${it.name} ×${G.Inv.count(id)} <span class="istat">${it.sell}G</span></div>`;
      const b = el('div', 'ibtn', row, '売る');
      b.addEventListener('pointerdown', e => { e.stopPropagation(); if (G.Shop.sell(id)) UI.openShop(); });
    }
    if (!any) el('div', 'mnote', sell, '売れる物がない。');
  };

  /* ---------- 鍛冶 ---------- */
  UI.openForge = function () {
    G.paused = true;
    menuOpen = true;
    hudEl.style.visibility = 'hidden';
    menuWrap.style.display = 'flex';
    menuTabs.style.display = 'none';
    menuBody.innerHTML = '';
    el('div', 'shoptitle', menuBody, '⚒ ドヴァンの鍛冶場');
    el('div', 'mnote', menuBody, `所持金: ${G.Inv.gold} G / 魔石×${G.Inv.count('magicstone')} 骨×${G.Inv.count('bone')} 毛皮×${G.Inv.count('pelt')}`);
    el('div', 'shophead', menuBody, '― 装備強化 ―');
    const list = el('div', 'ilist', menuBody);
    for (const id of [G.Inv.equip.weapon, G.Inv.equip.armor]) {
      const it = G.Items.get(id);
      if (!it) continue;
      const lvl = G.Inv.upgLevel(id);
      const row = el('div', 'irow', list);
      const stat = it.type === 'weapon'
        ? `攻 ${it.atk + lvl * 2}` : `防 ${it.def + lvl}`;
      let costTxt = '最大強化済み';
      let can = false;
      if (lvl < 5) {
        const c = G.Forge.cost(lvl);
        // 不足している素材/所持金を赤字で強調
        const mats = Object.keys(c.mats).map(m => {
          const lack = G.Inv.count(m) < c.mats[m];
          const t = `${G.Items.get(m).name}×${c.mats[m]}`;
          return lack ? `<span class="lack">${t}</span>` : t;
        }).join(' ');
        // 強化後の数値を予告して費用対効果を判断できるように
        const next = it.type === 'weapon' ? `攻 ${it.atk + lvl * 2} → ${it.atk + (lvl + 1) * 2}`
                                          : `防 ${it.def + lvl} → ${it.def + lvl + 1}`;
        const goldTxt = G.Inv.gold < c.gold ? `<span class="lack">${c.gold}G</span>` : `${c.gold}G`;
        costTxt = `${next} / ${goldTxt} + ${mats}`;
        can = G.Inv.gold >= c.gold &&
              Object.keys(c.mats).every(m => G.Inv.count(m) >= c.mats[m]);
      }
      row.innerHTML = `<div class="iname">${it.name}${lvl ? ' +' + lvl : ''} <span class="istat">${stat}</span></div>
        <div class="idesc">${lvl < 5 ? '次の強化: ' + costTxt : costTxt}</div>`;
      if (lvl < 5) {
        if (can) {
          const b = el('div', 'ibtn', row, '強化');
          b.addEventListener('pointerdown', e => {
            e.stopPropagation();
            if (G.Forge.upgrade(id)) UI.openForge();
          });
        } else {
          el('div', 'ibtn off', row, '素材不足');
        }
      }
    }
    el('div', 'mnote', menuBody, '強化は装備中の武器・防具に施される。素材は敵のドロップや売店で。');
  };

  /* ---------- 死亡/クリア ---------- */
  UI.hideDeath = function () { deathEl.style.display = 'none'; };

  UI.showEnding = function () {
    endEl.style.display = 'flex';
    endEl.innerHTML = `
      <div class="etext">
        <div class="etitle">黒竜討伐</div>
        <div class="ebody">黒竜ヴァルドレクは崩れ落ち、エルドリアに風が戻った。<br><br>
        討伐 Lv.${G.Stats.level} / ${G.State.day}日目<br>
        あなたは伝説となった。<br><br>
        ―― 旅はまだ続く。世界は自由だ。</div>
      </div>`;
    const b = el('div', 'bigbtn', endEl, '旅を続ける');
    b.addEventListener('pointerdown', e => {
      e.stopPropagation();
      endEl.style.display = 'none';
      G.Save.save();
    });
  };
})();
