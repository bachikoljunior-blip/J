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
  let basePixelRatio = 1, resScale = 1, perfEMA = 16, perfAdjustT = 0, lastRawGap = 16;
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
    basePixelRatio = Math.min(window.devicePixelRatio || 1, G.Q.dpr);
    renderer.setPixelRatio(basePixelRatio);
    renderer.setSize(window.innerWidth, window.innerHeight);

    // リアルタイム影 (low品質と設定オフ以外)
    G.shadowsOn = G.quality !== 'low' && G.settings.shadows !== 'off';
    if (G.shadowsOn) {
      renderer.shadowMap.enabled = true;
      renderer.shadowMap.type = THREE.PCFShadowMap;
    }

    scene = new THREE.Scene();
    camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 900);
    G.Camera.cam = camera;
    G.renderer = renderer;
    G.scene = scene;

    window.addEventListener('resize', () => {
      renderer.setSize(window.innerWidth, window.innerHeight);
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
    });

    /* 初期化 */
    G.World.init(scene);
    G.Sky.init(scene);
    G.FX.init(scene);
    G.TelegraphRing.init(scene);
    G.SwingArc.init(scene);
    G.Scorch.init(scene);
    G.Player.init(scene);
    G.Enemies.init(scene);
    G.NPCs.init(scene);
    G.Horse.init(scene);
    G.Projectiles.init(scene);
    G.Pickups.init(scene);
    G.UI.init();
    G.Input.init(canvas);
    G.UI.buildMap();

    // ダメージ時の画面フラッシュ
    flashEl = G.UI.el('div', 'flash', document.getElementById('ui'));

    // 夜間の自機視認用フィルライト
    G.playerLight = new THREE.PointLight(0xffe8c8, 0, 11);
    scene.add(G.playerLight);

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
      tutStart();
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

  /* ---------------- 段階式チュートリアル ---------------- */
  /* 全操作を1行に詰めた常時ヘルプの代わりに、1つずつ提示して実行で進める */
  const TUT = [
    { k: '<b>移動</b>: WASD (Shiftで走る)', t: '<b>移動</b>: 左スティック' },
    { k: '<b>長老ハルド</b>に近づき <b>E</b> で話す', t: '<b>長老ハルド</b>に近づき「調べる」で話す' },
    { k: '<b>攻撃</b>: F / クリック (長押しで強撃)', t: '<b>攻撃</b>: 剣ボタン (長押しで強撃)' },
    { k: '<b>回避</b>: Space', t: '<b>回避</b>: 回避ボタン' }
  ];
  let tutStage = -1, tutMove = 0, tutPX = null, tutPZ = null, tutHidden = false;
  function tutStart() {
    if (localStorage.getItem('eldria_tut') === 'done') { G.UI.setKeyhelpVisible(true); return; }
    tutStage = 0; tutMove = 0;
    G.UI.setKeyhelpVisible(false);
    G.UI.showTutChip(G.isTouch ? TUT[0].t : TUT[0].k);
  }
  function tutAdvance(i) {
    if (tutStage !== i) return;
    tutStage++;
    G.Audio.sfx('ui');
    if (tutStage >= TUT.length) {
      tutStage = -1;
      localStorage.setItem('eldria_tut', 'done');
      G.UI.hideTutChip();
      G.UI.setKeyhelpVisible(true);
      G.UI.toast('基本操作を覚えた', 'gold');
    } else {
      G.UI.showTutChip(G.isTouch ? TUT[tutStage].t : TUT[tutStage].k);
    }
  }
  // 「話す」ステップは会話を終えた時点で完了 (会話中に次のヒントを出さない)
  G.events.on('dialogueClosed', () => { tutAdvance(1); tutHidden = true; });

  /* チュートリアルを外部からスキップ (計測ハーネス・デバッグ用) */
  G.tutSkip = function () {
    tutStage = -1;
    localStorage.setItem('eldria_tut', 'done');
    G.UI.hideTutChip();
    G.UI.setKeyhelpVisible(true);
  };

  function tutUpdate() {
    if (tutStage < 0) return;
    const p = G.Player.pos;
    if (tutPX !== null && tutStage === 0) {
      tutMove += Math.hypot(p.x - tutPX, p.z - tutPZ);
      if (tutMove > 6) tutAdvance(0);
    }
    tutPX = p.x; tutPZ = p.z;
    // 村を大きく離れたら「長老と話す」は押し付けない (次の戦闘ヒントへ)
    if (tutStage === 1 && G.dist2(p.x, p.z, 0, 0) > 120 * 120) tutAdvance(1);
    // ボス交戦中はチップを隠す (演出を邪魔しない)
    let bossOn = false;
    for (const b of G.Enemies.bosses) { if (b.alive && b.engaged) { bossOn = true; break; } }
    if (bossOn && !tutHidden) { tutHidden = true; G.UI.hideTutChip(); }
    else if (!bossOn && tutHidden && tutStage >= 0) {
      tutHidden = false;
      G.UI.showTutChip(G.isTouch ? TUT[tutStage].t : TUT[tutStage].k);
    }
  }

  /* ---------------- イベント ---------------- */
  G.events.on('shake', v => { trauma = Math.min(1, trauma + v); });
  let bossCine = 0, cineBoss = null;
  G.events.on('bossEngage', b => { bossCine = 2.1; cineBoss = b; G.events.emit('shake', 0.55); });
  G.events.on('hitstop', v => { hitstop = Math.max(hitstop, v); });
  G.events.on('gameClear', () => { G.Save.save(); });

  /* ---------------- インタラクト ---------------- */
  function doInteract() {
    const it = G.findInteractable();
    if (!it) return;
    if (it.kind === 'horse') {
      G.Horse.mount();
    } else if (it.kind === 'dismount') {
      G.Horse.dismount();
    } else if (it.kind === 'npc') {
      G.Dialogue.start(it.obj);
      dialogueCam(it.obj);
    } else if (it.kind === 'shrine') {
      const s = it.obj;
      if (!G.State.shrines[s.id]) {
        G.State.shrines[s.id] = true;
        G.Audio.sfx('shrine');
        G.UI.toast(s.name + ' を灯した', 'gold');
        G.FX.burst(s.x, G.World.heightAt(s.x, s.z) + 2, s.z,
          { n: 16, color: 0x66ddff, speed: 3, up: 1.5, gravity: -1, life: 0.85, size: 2.4 });
        G.events.emit('shrineLit');
        G.Save.save();
      } else {
        G.UI.shrineMenu(s);
      }
    } else if (it.kind === 'portal') {
      const pt = it.obj;
      if (G.Player.mounted) G.Horse.dismount();
      G.Player.pos.set(pt.tx, G.World.heightAt(pt.tx, pt.tz), pt.tz);
      G.Player.vy = 0;
      G.Player.target = null;
      G.Projectiles.clear();
      warmupChunks();
      G.Audio.sfx('shrine');
      G.UI.toast(pt.label.includes('入る') ? '風哭の洞窟 — 風の唸りが聞こえる…' : '外の光が眩しい');
    } else if (it.kind === 'chest') {
      const c = it.obj;
      if (c.mimic) {
        // ミミック!
        G.State.openedChests[c.id] = true;
        G.World.hideChest(c.id);
        const e = G.Enemies.spawn('mimic', c.x, c.z);
        e.aggro = true;
        G.Audio.sfx('roar');
        G.events.emit('shake', 0.5);
        G.UI.toast('宝箱はミミックだった！');
        return;
      }
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
    G.Horse.teleport(shrine.x - 4, shrine.z - 4);
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
        case 'attack': G.Player.tryAttack(false); tutAdvance(2); break;
        case 'heavy': G.Player.tryAttack(true); tutAdvance(2); break;
        case 'spin': G.Player.tryAttack('spin'); tutAdvance(2); break;
        case 'roll': G.Player.tryRoll(); tutAdvance(3); break;
        case 'jump': G.Player.tryJump(); break;
        case 'interact': doInteract(); break;
        case 'lock': G.Player.toggleLock(); break;
        case 'potion': G.Player.usePotion(); break;
        case 'menu': G.UI.openMenu('equip'); break;
        case 'map': G.UI.openMenu('map'); break;
      }
    }
  }

  /* 会話用の肩越しカメラ (会話中はカメラ更新が止まるので一度だけ配置する) */
  function dialogueCam(npc) {
    const p = G.Player.pos, n = npc.pos;
    const mx = (p.x + n.x) / 2, mz = (p.z + n.z) / 2;
    // 二人を結ぶ線に対し横へオフセットし、両者を画面に収める
    const a = Math.atan2(n.x - p.x, n.z - p.z);
    const side = a + Math.PI / 2;
    const cx = mx + Math.sin(side) * 3.4 - Math.sin(a) * 1.2;
    const cz = mz + Math.cos(side) * 3.4 - Math.cos(a) * 1.2;
    let cy = Math.max(p.y, n.y) + 1.9;
    const gh = G.World.heightAt(cx, cz);
    if (cy < gh + 0.6) cy = gh + 0.6;
    camera.position.set(cx, cy, cz);
    camera.lookAt(mx, Math.max(p.y, n.y) + 1.35, mz);
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
    // ボス遭遇: 2秒だけ全身を映すカメラ
    if (bossCine > 0 && cineBoss && cineBoss.alive) {
      bossCine -= dt;
      const b = cineBoss;
      const dx = p.pos.x - b.pos.x, dz = p.pos.z - b.pos.z;
      const back = b.radius * 3 + 9;
      const h = (b.D.barH || 3);
      // 真後ろからだとボスと自機が重なるため、側面へ回り込んだ2ショット構図
      const a = Math.atan2(dx, dz) + 0.95;
      camera.position.set(
        b.pos.x + Math.sin(a) * back,
        b.pos.y + h * 1.05 + 1.2,
        b.pos.z + Math.cos(a) * back
      );
      camera.lookAt(
        b.pos.x * 0.72 + p.pos.x * 0.28,
        b.pos.y + h * 0.5,
        b.pos.z * 0.72 + p.pos.z * 0.28
      );
      if (bossCine <= 0) cineBoss = null;
      G.Input.camDX = 0; G.Input.camDY = 0;
      return;
    }
    C.yaw -= G.Input.camDX;
    C.pitch += G.Input.camDY;
    C.pitch = G.clamp(C.pitch, -0.1, 1.15);
    // 滑空中は視線を下げて着地予定地点を見せる
    if (p.gliding) C.pitch = G.lerp(C.pitch, 0.68, G.damp(1.1, dt));
    G.Input.camDX = 0; G.Input.camDY = 0;
    C.dist = G.clamp(C.dist + G.Input.wheel, 4, 13);
    G.Input.wheel = 0;

    // ロックオン時は対象へ向く (巨大ボスはカメラを引いて全身を映す)
    let bigBoss = p.target && p.target.alive && p.target.D && (p.target.D.barH || 0) > 3;
    if (!bigBoss) {
      for (const b of G.Enemies.bosses) {
        if (b.alive && b.engaged && (b.D.barH || 0) > 3 &&
            G.dist2(p.pos.x, p.pos.z, b.pos.x, b.pos.z) < 22 * 22) { bigBoss = true; break; }
      }
    }
    if (p.target && p.target.alive) {
      const ty = Math.atan2(p.target.pos.x - p.pos.x, p.target.pos.z - p.pos.z);
      C.yaw = G.angLerp(C.yaw, ty, G.damp(4, dt));
      C.pitch = G.lerp(C.pitch, bigBoss ? 0.5 : 0.35, G.damp(3, dt));
    } else if (bigBoss) {
      C.pitch = G.lerp(C.pitch, 0.45, G.damp(2.5, dt));
      // 最も近い交戦ボスへ弱くヨー追従
      let nb = null, nd = 1e9;
      for (const b of G.Enemies.bosses) {
        if (!b.alive || !b.engaged) continue;
        const d2 = G.dist2(p.pos.x, p.pos.z, b.pos.x, b.pos.z);
        if (d2 < nd) { nd = d2; nb = b; }
      }
      if (nb) {
        const ty = Math.atan2(nb.pos.x - p.pos.x, nb.pos.z - p.pos.z);
        C.yaw = G.angLerp(C.yaw, ty, G.damp(1.4, dt));
      }
    }

    const fx = Math.sin(C.yaw) * Math.cos(C.pitch);
    const fz = Math.cos(C.yaw) * Math.cos(C.pitch);
    const fy = Math.sin(C.pitch);
    let bossBonus = 0;
    if (bigBoss) {
      bossBonus = 4.5;
      for (const b of G.Enemies.bosses) {
        if (b.alive && b.engaged && (b.D.barH || 0) > 5) { bossBonus = 8.5; break; }
      }
    }
    const dist = C.dist + (p.mounted ? 1.8 : 0) + bossBonus;
    let cx = p.pos.x - fx * dist;
    let cz = p.pos.z - fz * dist;
    let cy = p.pos.y + 1.6 + fy * dist;

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

    // 木や岩が視線を遮るならカメラを手前へ寄せる
    const occ = G.World.cameraOcclusion(p.pos.x, p.pos.z, cx, cz);
    if (occ < 1) {
      cx = p.pos.x + (cx - p.pos.x) * occ;
      cz = p.pos.z + (cz - p.pos.z) * occ;
      cy = eyeY + (cy - eyeY) * occ;
    }

    // カメラは常に水面より上 (いかなる場合も水没しない)
    if (cy < G.World.WATER_Y + 0.45) cy = G.World.WATER_Y + 0.45;

    // 画面揺れ
    trauma = Math.max(0, trauma - dt * 1.8);
    const sh = trauma * trauma * 0.5;
    cx += (Math.random() - 0.5) * sh;
    cy += (Math.random() - 0.5) * sh;
    cz += (Math.random() - 0.5) * sh;

    camera.position.set(cx, cy, cz);
    camera.lookAt(p.pos.x, p.pos.y + 1.5, p.pos.z);

    // 視線を遮る建造物 (柱・塔・家屋) を半透明化
    G.World.updateFaders(dt, p.pos.x, p.pos.z, cx, cz, eyeY, cy);

    // 疾走・騎乗・滑空の速度感: FOVを滑らかに広げる
    const tFov = 60 + (p.fovBoost || 0) * 12;
    if (Math.abs(camera.fov - tFov) > 0.05) {
      camera.fov = G.lerp(camera.fov, tFov, G.damp(4, dt));
      camera.updateProjectionMatrix();
    }
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

    // 雨の地面スプラッシュ (降雨がワールドに触れている感触)
    if (S.weather > 0.5 && Math.random() < dt * 10) {
      const p = G.Player.pos;
      const a = Math.random() * Math.PI * 2, d = 2 + Math.random() * 9;
      const x = p.x + Math.cos(a) * d, z = p.z + Math.sin(a) * d;
      const h = G.World.heightAt(x, z);
      G.FX.burst(x, Math.max(h, G.World.WATER_Y) + 0.08, z, {
        n: 2, color: 0xcfe4f2, speed: 1.4, up: 1.6, gravity: 5,
        life: 0.32, size: 1.3, drag: 0.8
      });
    }

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

  /* ---------------- 環境音 ---------------- */
  let ambientT = 4;
  function updateAmbient(dt) {
    ambientT -= dt;
    if (ambientT > 0) return;
    ambientT = 2.5 + Math.random() * 5;
    if (!started || G.paused) return;
    const tod = G.State.tod;
    const p = G.Player.pos;
    if (G.inCave) { G.Audio.sfx('drip'); return; }
    const night = tod > 20 || tod < 5;
    if (night) { G.Audio.sfx('cricket'); return; }
    if (p.y > 38) { G.Audio.sfx('windgust'); return; }
    const b = G.World.biomeAt(p.x, p.z);
    if (b === 'forest' || b === 'grass') G.Audio.sfx('bird');
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
    const rawGap = now - prevT;
    let dt = Math.min(rawGap / 1000, 0.05);
    prevT = now;
    lastRawGap = rawGap;
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
        tutUpdate();
        G.Player.update(dt);
        G.Horse.update(dt);
        G.Enemies.update(dt);
        G.NPCs.update(dt);
        G.Projectiles.update(dt);
        G.Pickups.update(dt);
      }
      G.FX.update(dt);
      G.SwingArc.update(dt);
      G.Scorch.update(dt);
      G.World.update(dt, G.Player.pos.x, G.Player.pos.z);
      updateCamera(dt);
      G.inCave = G.World.inCaveRegion(G.Player.pos.x, G.Player.pos.z);
      G.Sky.update(dt, G.State.tod, G.State.weather, camera.position, G.inCave);
      // 暗いほど自機フィルライトを強く。洞窟では携行光として常時強めに灯す
      G.playerLight.position.set(G.Player.pos.x, G.Player.pos.y + 2.2, G.Player.pos.z);
      G.playerLight.intensity = G.inCave ? 1.25
        : G.clamp((0.5 - G.Sky.lightLevel) * 1.6, 0, 0.65);
      G.playerLight.distance = G.inCave ? 16 : 11;

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
    updateAmbient(dt);
    G.UI.updateTyping(dt);   // 会話送りはポーズ中も進める
    if (started) G.UI.update(dt);
    const _t1 = performance.now();
    renderer.render(scene, camera);
    const _t2 = performance.now();
    // 移動平均の負荷計測 (デバッグ用)
    G.perf.sim += (_t1 - _t0 - G.perf.sim) * 0.05;
    G.perf.render += (_t2 - _t1 - G.perf.render) * 0.05;

    // 動的解像度スケーリング: 低スペック端末では描画解像度を下げて
    // フレームレートを守る (render時間のEMAで2.5秒ごとに調整)
    perfEMA += (_t2 - _t0 - perfEMA) * 0.04;
    perfAdjustT += dt;
    // RAF間隔が異常に長い環境 (バックグラウンド/ヘッドレス計測) では調整しない
    if (perfAdjustT > 2.5 && started && lastRawGap < 150) {
      perfAdjustT = 0;
      let want = resScale;
      if (perfEMA > 36 && resScale > 0.6) want = Math.max(0.6, resScale - 0.15);
      else if (perfEMA < 20 && resScale < 1) want = Math.min(1, resScale + 0.1);
      if (want !== resScale) {
        resScale = want;
        renderer.setPixelRatio(basePixelRatio * resScale);
      }
    }
  }
  G.perf = { sim: 0, render: 0 };

  /* ---------------- 開始 ---------------- */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', Game.boot);
  } else {
    Game.boot();
  }
})();
