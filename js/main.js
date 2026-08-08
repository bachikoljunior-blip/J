/* =============================================================================
 * ELDRIA — main.js
 * 起動 / メインループ / カメラ / 時間・天候 / インタラクト / セーブ統合
 * ========================================================================== */
'use strict';
(function () {
  const Game = G.Game = {};
  let renderer, scene, camera;
  let running = false;
  let prevT = 0;
  let hitstop = 0, trauma = 0;
  let autosaveT = 30;
  let musicT = 0;
  let prevHp = null;
  let flashEl = null;

  G.paused = false;
  G.Camera = { yaw: Math.PI, pitch: 0.42, dist: 7.5, cam: null };

  /* ---------------- 起動 ---------------- */
  Game.boot = function () {
    const canvas = document.getElementById('game');
    renderer = new THREE.WebGLRenderer({
      canvas,
      antialias: G.quality !== 'low',
      powerPreference: 'high-performance'
    });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, G.Q.dpr));
    renderer.setSize(window.innerWidth, window.innerHeight);

    scene = new THREE.Scene();
    camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 900);
    G.Camera.cam = camera;

    window.addEventListener('resize', () => {
      renderer.setSize(window.innerWidth, window.innerHeight);
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
    });

    /* 初期化 */
    G.World.init(scene);
    G.Sky.init(scene);
    G.FX.init(scene);
    G.Player.init(scene);
    G.Enemies.init(scene);
    G.NPCs.init(scene);
    G.Projectiles.init(scene);
    G.Pickups.init(scene);
    G.UI.init();
    G.Input.init(canvas);
    G.UI.buildMap();

    // ダメージ時の画面フラッシュ
    flashEl = G.UI.el('div', 'flash', document.getElementById('ui'));

    // 初期チャンクを同期的に確保 (プレイヤー周辺)
    warmupChunks();

    document.getElementById('loading').style.display = 'none';

    G.UI.showTitle(newGame => Game.start(newGame));

    // タイトル背景でもワールドを描画
    running = true;
    prevT = performance.now();
    requestAnimationFrame(loop);
  };

  function warmupChunks() {
    // プレイヤー初期位置周辺のチャンクを即時生成
    for (let i = 0; i < 60; i++) {
      G.World.update(0.016, G.Player.pos.x, G.Player.pos.z);
    }
  }

  let started = false;
  Game.start = function (newGame) {
    if (newGame) {
      G.Save.reset();
      G.Save.newGame();
      G.UI.showIntro();
    } else {
      const data = G.Save.load();
      if (data) G.Save.apply(data);
      else G.Save.newGame();
    }
    G.Player.buildRig();
    G.Player.hp = Math.min(G.Player.hp, G.Stats.maxHp());
    // 進行済みの世界状態を反映
    for (const id in G.State.openedChests) G.World.openChestVisual(id);
    for (const h of G.World.herbs) {
      if (G.State.herbs[h.id]) G.World.takeHerbVisual(h);
    }
    G.Bosses.init(scene);
    G.UI.refreshTracker();
    G.UI.refreshHUDStatic();
    G.UI.setHudVisible(true);
    G.Audio.setMusic('peace');
    warmupChunks();
    started = true;
  };

  /* ---------------- イベント ---------------- */
  G.events.on('shake', v => { trauma = Math.min(1, trauma + v); });
  G.events.on('hitstop', v => { hitstop = Math.max(hitstop, v); });
  G.events.on('gameClear', () => { G.Save.save(); });

  /* ---------------- インタラクト ---------------- */
  function doInteract() {
    const it = G.findInteractable();
    if (!it) return;
    if (it.kind === 'npc') {
      G.Dialogue.start(it.obj);
    } else if (it.kind === 'shrine') {
      const s = it.obj;
      if (!G.State.shrines[s.id]) {
        G.State.shrines[s.id] = true;
        G.Audio.sfx('shrine');
        G.UI.toast(s.name + ' を灯した', 'gold');
        G.FX.burst(s.x, G.World.heightAt(s.x, s.z) + 2, s.z,
          { n: 30, color: 0x66ddff, speed: 3, up: 1.5, gravity: -1, life: 1.2, size: 3.5 });
        G.Save.save();
      } else {
        G.UI.shrineMenu(s);
      }
    } else if (it.kind === 'chest') {
      const c = it.obj;
      G.State.openedChests[c.id] = true;
      G.World.openChestVisual(c.id);
      G.Audio.sfx('uiOpen');
      if (c.gold) { G.Inv.addGold(c.gold); G.UI.toast(c.gold + ' G を手に入れた', 'gold'); }
      for (const id in c.items) {
        G.Inv.add(id, c.items[id]);
        G.UI.toast(G.Items.get(id).name + ' ×' + c.items[id] + ' を手に入れた', 'gold');
        G.events.emit('collect', { id });
      }
      G.FX.burst(c.x, G.World.heightAt(c.x, c.z) + 0.8, c.z,
        { n: 16, color: 0xffd700, speed: 2.5, up: 1.2, gravity: -0.5, life: 0.9 });
    } else if (it.kind === 'herb') {
      const h = it.obj;
      G.State.herbs[h.id] = true;
      G.World.takeHerbVisual(h);
      G.Inv.add('herb', 1);
      G.Audio.sfx('pickup');
      G.UI.toast('月光草 を摘んだ');
      G.events.emit('collect', { id: 'herb' });
    }
  }

  /* ---------------- リスポーン / 移動 ---------------- */
  Game.respawn = function () {
    const sh = G.World.shrines.find(s => s.id === G.State.respawn) || G.World.shrines[0];
    G.Player.respawn(sh.x + 3, sh.z + 3);
    G.Bosses.reset();
    for (const e of G.Enemies.list) { e.aggro = false; e.state = 'idle'; }
    G.Projectiles.clear();
    G.UI.hideDeath();
    G.UI.hideBoss();
    warmupChunks();
    G.UI.toast(sh.name + ' で目を覚ました');
  };

  Game.travelTo = function (shrine) {
    G.Player.pos.set(shrine.x + 3, G.World.heightAt(shrine.x + 3, shrine.z + 3), shrine.z + 3);
    G.Player.vy = 0;
    G.Player.target = null;
    G.Projectiles.clear();
    for (const e of G.Enemies.list) { e.aggro = false; }
    warmupChunks();
    G.Audio.sfx('shrine');
    G.UI.toast(shrine.name + ' へ移動した');
  };

  /* ---------------- ボタン処理 ---------------- */
  function handleActions() {
    for (const a of G.Input.poll()) {
      if (G.UI.isMenuOpen()) {
        if (a === 'menu' || a === 'back' || a === 'map') G.UI.closeMenu();
        continue;
      }
      if (G.paused) {
        if (a === 'back') G.UI.closeDialogue();
        continue;
      }
      if (!started) continue;
      switch (a) {
        case 'attack': G.Player.tryAttack(false); break;
        case 'heavy': G.Player.tryAttack(true); break;
        case 'roll': G.Player.tryRoll(); break;
        case 'jump': G.Player.tryJump(); break;
        case 'interact': doInteract(); break;
        case 'lock': G.Player.toggleLock(); break;
        case 'potion': G.Player.usePotion(); break;
        case 'menu': G.UI.openMenu('equip'); break;
        case 'map': G.UI.openMenu('map'); break;
      }
    }
  }

  /* ---------------- カメラ ---------------- */
  function updateCamera(dt) {
    const C = G.Camera;
    const p = G.Player;
    if (!started) {
      // タイトル画面: 村をゆっくり旋回
      C.yaw += dt * 0.06;
      const cx = p.pos.x - Math.sin(C.yaw) * 16;
      const cz = p.pos.z - Math.cos(C.yaw) * 16;
      const cy = Math.max(G.World.heightAt(cx, cz) + 2.5, p.pos.y + 5);
      camera.position.set(cx, cy, cz);
      camera.lookAt(p.pos.x, p.pos.y + 2, p.pos.z);
      return;
    }
    C.yaw -= G.Input.camDX;
    C.pitch += G.Input.camDY;
    C.pitch = G.clamp(C.pitch, -0.1, 1.15);
    G.Input.camDX = 0; G.Input.camDY = 0;
    C.dist = G.clamp(C.dist + G.Input.wheel, 4, 13);
    G.Input.wheel = 0;

    // ロックオン時は対象へ向く
    if (p.target && p.target.alive) {
      const ty = Math.atan2(p.target.pos.x - p.pos.x, p.target.pos.z - p.pos.z);
      C.yaw = G.angLerp(C.yaw, ty, G.damp(4, dt));
      C.pitch = G.lerp(C.pitch, 0.35, G.damp(3, dt));
    }

    const fx = Math.sin(C.yaw) * Math.cos(C.pitch);
    const fz = Math.cos(C.yaw) * Math.cos(C.pitch);
    const fy = Math.sin(C.pitch);
    let cx = p.pos.x - fx * C.dist;
    let cz = p.pos.z - fz * C.dist;
    let cy = p.pos.y + 1.6 + fy * C.dist;

    // 地形にめり込まない (視線上の複数点をサンプルして必要な持ち上げ量を求める)
    const gh = G.World.heightAt(cx, cz);
    if (cy < gh + 0.5) cy = gh + 0.5;
    const eyeY = p.pos.y + 1.6;
    let lift = 0;
    for (let k = 0; k < 3; k++) {
      const t = 0.3 + k * 0.25;   // 0.3, 0.55, 0.8
      const sx = p.pos.x + (cx - p.pos.x) * t;
      const sz = p.pos.z + (cz - p.pos.z) * t;
      const sy = eyeY + (cy - eyeY) * t;
      const need = (G.World.heightAt(sx, sz) + 0.45 - sy) / t;
      if (need > lift) lift = need;
    }
    if (lift > 0) cy += lift;

    // 画面揺れ
    trauma = Math.max(0, trauma - dt * 1.8);
    const sh = trauma * trauma * 0.5;
    cx += (Math.random() - 0.5) * sh;
    cy += (Math.random() - 0.5) * sh;
    cz += (Math.random() - 0.5) * sh;

    camera.position.set(cx, cy, cz);
    camera.lookAt(p.pos.x, p.pos.y + 1.5, p.pos.z);
  }

  /* ---------------- 時間 / 天候 ---------------- */
  function updateWorldState(dt) {
    const S = G.State;
    S.playtime += dt;
    S.tod += dt * (24 / 720);      // 実時間12分で1日
    if (S.tod >= 24) { S.tod -= 24; S.day++; G.UI.toast(S.day + '日目の朝が来た'); }

    S.weatherTimer -= dt;
    if (S.weatherTimer <= 0) {
      S.weatherTimer = 100 + Math.random() * 160;
      const rain = Math.random() < 0.3 ? 1 : 0;
      if (rain !== S.weatherTarget) {
        S.weatherTarget = rain;
        if (rain) G.UI.toast('雨が降ってきた…');
      }
    }
    S.weather += (S.weatherTarget - S.weather) * G.damp(0.25, dt);
    G.Audio.setRain(S.weatherTarget === 1);

    // 夜の蛍 (雨天以外)
    const night = S.tod > 20 || S.tod < 4.5;
    if (night && S.weather < 0.3 && Math.random() < dt * 2.2) {
      const p = G.Player.pos;
      const a = Math.random() * Math.PI * 2, d = 4 + Math.random() * 16;
      const x = p.x + Math.cos(a) * d, z = p.z + Math.sin(a) * d;
      const h = G.World.heightAt(x, z);
      if (h > G.World.WATER_Y) {
        G.FX.burst(x, h + 0.6 + Math.random() * 1.2, z, {
          n: 1, color: 0xaaffcc, speed: 0.4, up: 0.35, gravity: -0.15,
          life: 2.6, size: 1.6, drag: 0.4, spread: 1
        });
      }
    }
  }

  /* ---------------- 音楽状態 ---------------- */
  function updateMusic(dt) {
    musicT -= dt;
    if (musicT > 0) return;
    musicT = 0.5;
    if (!started) { G.Audio.setMusic('peace'); return; }
    let engaged = null;
    for (const b of G.Enemies.bosses) {
      if (b.alive && b.engaged) { engaged = b; break; }
    }
    if (engaged) G.Audio.setMusic('boss');
    else if (G.Enemies.anyAggro()) G.Audio.setMusic('combat');
    else G.Audio.setMusic('peace');
  }

  /* ---------------- メインループ ---------------- */
  function loop(now) {
    requestAnimationFrame(loop);
    let dt = Math.min((now - prevT) / 1000, 0.05);
    prevT = now;
    if (!running) return;

    handleActions();
    G.Input.updateFromKeys();

    if (hitstop > 0) {
      hitstop -= dt;
      dt *= 0.12;
    }

    const _t0 = performance.now();
    if (!G.paused) {
      G.time += dt;
      if (started) {
        updateWorldState(dt);
        G.Player.update(dt);
        G.Enemies.update(dt);
        G.NPCs.update(dt);
        G.Projectiles.update(dt);
        G.Pickups.update(dt);
      }
      G.FX.update(dt);
      G.World.update(dt, G.Player.pos.x, G.Player.pos.z);
      updateCamera(dt);
      G.Sky.update(dt, G.State.tod, G.State.weather, camera.position);

      // ダメージフラッシュ
      if (started) {
        if (prevHp !== null && G.Player.hp < prevHp) {
          flashEl.style.opacity = '0.45';
        }
        prevHp = G.Player.hp;
        flashEl.style.opacity = String(Math.max(0, parseFloat(flashEl.style.opacity || '0') - dt * 1.8));

        // 自動セーブ
        autosaveT -= dt;
        if (autosaveT <= 0) {
          autosaveT = 30;
          if (G.Player.alive) G.Save.save();
        }
      }
    }

    updateMusic(dt);
    if (started) G.UI.update(dt);
    const _t1 = performance.now();
    renderer.render(scene, camera);
    const _t2 = performance.now();
    // 移動平均の負荷計測 (デバッグ用)
    G.perf.sim += (_t1 - _t0 - G.perf.sim) * 0.05;
    G.perf.render += (_t2 - _t1 - G.perf.render) * 0.05;
  }
  G.perf = { sim: 0, render: 0 };

  /* ---------------- 開始 ---------------- */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', Game.boot);
  } else {
    Game.boot();
  }
})();
