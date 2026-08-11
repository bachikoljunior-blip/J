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
  let basePixelRatio = 1, perfAdjustT = 0, lastRawGap = 16;
  let frameEMA = 16, workEMA = 16;
  let perfState = G.PerformanceGovernor.initial();
  let autosaveT = 30;
  let musicT = 0;
  let prevHp = null;
  let flashEl = null;

  G.paused = false;
  // ?drs=1: ヘッドレス計測でも動的解像度スケーリングを作動させる検証フック
  G.forceDRS = /[?&]drs=1/.test(location.search);
  G.Camera = { yaw: Math.PI, pitch: 0.42, dist: 7.5, cam: null };
  G.perf = { sim: 0, render: 0, calls: 0, resScale: 1, detail: 1, frameMs: 16 };

  function fatalStop(error, title) {
    running = false;
    try { if (started && G.Player && G.Player.alive) G.Save.save(); } catch (e) {}
    try { if (G.Input && G.Input.reset) G.Input.reset(); } catch (e) {}
    console.error('[ELDRIA] fatal', error);
    const detail = '進行は保存されています。再読み込みして続けてください。';
    if (G.UI && G.UI.showFatal) {
      G.UI.showFatal(title || 'ゲームを安全に停止しました', detail);
    } else {
      const loading = document.getElementById('loading');
      if (loading) {
        loading.style.display = 'flex';
        loading.textContent = (title || '起動できませんでした') + ' — 再読み込みしてください';
      }
    }
  }

  /* ---------------- 起動 ---------------- */
  Game.boot = function () {
    document.body.classList.toggle('reduced-motion', G.prefersReducedMotion());
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
      // ソフトPCF: ジャギーのスクリブル影・壁面のクロスハッチ縞の緩和
      renderer.shadowMap.type = THREE.PCFSoftShadowMap;
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

    let visibilityPaused = false;
    document.addEventListener('visibilitychange', () => {
      G.Input.reset();
      if (document.hidden) {
        if (started && G.Player.alive) G.Save.save();
        visibilityPaused = started && !G.paused;
        if (visibilityPaused) G.paused = true;
      } else {
        prevT = performance.now();
        if (visibilityPaused) G.paused = false;
        visibilityPaused = false;
      }
    });
    window.addEventListener('pagehide', () => {
      G.Input.reset();
      if (started && G.Player.alive) G.Save.save();
    });
    canvas.addEventListener('webglcontextlost', e => {
      e.preventDefault();
      fatalStop(e, '描画機能を復旧しています');
    });
    canvas.addEventListener('webglcontextrestored', () => location.reload());

    // ダメージ時の画面フラッシュ
    flashEl = G.UI.el('div', 'flash', document.getElementById('ui'));

    // 夜間の自機視認用フィルライト
    G.playerLight = new THREE.PointLight(0xffe8c8, 0, 11);
    scene.add(G.playerLight);

    // 初期チャンクを同期的に確保 (プレイヤー周辺)
    // 画面が固まる長い同期生成は避け、近傍だけ先に作る。残りはタイトル背景の
    // 通常フレームで2チャンクずつ生成されるため、見た目を保ったまま起動が速い。
    warmupChunks(6);

    document.getElementById('loading').style.display = 'none';

    G.UI.showTitle(newGame => Game.start(newGame));

    // タイトル背景でもワールドを描画
    running = true;
    prevT = performance.now();
    requestAnimationFrame(loop);
  };

  function warmupChunks(steps) {
    // 足元とカメラ周辺だけを同期生成し、長いメインスレッド停止を防ぐ。
    for (let i = 0; i < (steps || 6); i++) {
      G.World.update(0.016, G.Player.pos.x, G.Player.pos.z);
    }
  }

  let started = false;
  Game.start = function (newGame) {
    G.Save.requestPersistence();
    let recovered = false;
    if (newGame) {
      G.Save.reset();
      G.Save.newGame();
      G.UI.showIntro();
      tutStart();
    } else {
      const data = G.Save.load();
      if (data && G.Save.apply(data)) recovered = !!data._recovered;
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
    if (recovered) {
      G.Save.save();
      G.UI.toast('予備保存から進行を復旧しました', 'gold');
    }
    // 新規開始時は導入オーバーレイが閉じた時にHUDを出す (半透明の導入越しに
    // HUDが透けるのを防ぐ)
    G.UI.setHudVisible(!newGame);
    G.Audio.setMusic('peace');
    warmupChunks(8);
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
    if (G.storage.get('eldria_tut') === 'done') { G.UI.setKeyhelpVisible(true); return; }
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
      G.storage.set('eldria_tut', 'done');
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
    G.storage.set('eldria_tut', 'done');
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
    // ボス交戦中と、同内容のインタラクトプロンプト表示中はチップを隠す
    let bossOn = false;
    for (const b of G.Enemies.bosses) { if (b.alive && b.engaged) { bossOn = true; break; } }
    if (G.UI.promptShowing) bossOn = true;   // プロンプト表示中はチップを出さず導線を1系統に
    if (bossOn && !tutHidden) { tutHidden = true; G.UI.hideTutChip(); }
    else if (!bossOn && tutHidden && tutStage >= 0) {
      tutHidden = false;
      G.UI.showTutChip(G.isTouch ? TUT[tutStage].t : TUT[tutStage].k);
    }
  }

  /* ---------------- イベント ---------------- */
  G.events.on('shake', v => {
    const scale = G.settings.shake * (G.prefersReducedMotion() ? 0.18 : 1);
    trauma = Math.min(1, trauma + v * scale);
  });
  let bossCine = 0, cineBoss = null, framePull = 0;
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
      // 話者同士が向き合う
      it.obj.yaw = Math.atan2(G.Player.pos.x - it.obj.pos.x, G.Player.pos.z - it.obj.pos.z);
      G.Player.yaw = Math.atan2(it.obj.pos.x - G.Player.pos.x, it.obj.pos.z - G.Player.pos.z);
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

  /* 会話用の肩越しカメラ。切替はスナップではなく0.55秒のイーズで寄る */
  let dlgTween = null, camBlend = 0;
  const _lookTmp = new THREE.Vector3();
  function dialogueCam(npc) {
    const p = G.Player.pos, n = npc.pos;
    const mx = (p.x + n.x) / 2, mz = (p.z + n.z) / 2;
    // 二人を結ぶ線に対し横へオフセットし、両者を画面に収める。
    // 候補位置が建物コライダー内に入るなら反対側へ回る (壁内カメラの防止)
    const a = Math.atan2(n.x - p.x, n.z - p.z);
    const cols = G.World.staticColliders || [];
    const bad = (x, z) => {
      // カメラ位置がコライダー内、または話者への視線が建物に遮られる候補は不可
      for (let i = 0; i < cols.length; i++) {
        const c = cols[i];
        if (G.dist2(x, z, c.x, c.z) < (c.r + 0.6) * (c.r + 0.6)) return true;
        const dx = (mx - x) * 0.75, dz = (mz - z) * 0.75;   // 中点の手前70%まで
        const L2 = dx * dx + dz * dz || 1;
        let t = ((c.x - x) * dx + (c.z - z) * dz) / L2;
        t = Math.max(0, Math.min(1, t));
        const px = x + dx * t, pz = z + dz * t;
        if (G.dist2(px, pz, c.x, c.z) < (c.r + 0.2) * (c.r + 0.2)) return true;
      }
      return false;
    };
    // 候補: 右側面 / 左側面 / 正面引き — 遮られない最初の構図を採用
    const cands = [
      [mx + Math.sin(a + Math.PI / 2) * 3.4 - Math.sin(a) * 1.2, mz + Math.cos(a + Math.PI / 2) * 3.4 - Math.cos(a) * 1.2],
      [mx + Math.sin(a - Math.PI / 2) * 3.4 - Math.sin(a) * 1.2, mz + Math.cos(a - Math.PI / 2) * 3.4 - Math.cos(a) * 1.2],
      [mx - Math.sin(a) * 3.8, mz - Math.cos(a) * 3.8]
    ];
    let cx = cands[0][0], cz = cands[0][1];
    for (const [qx, qz] of cands) {
      if (!bad(qx, qz)) { cx = qx; cz = qz; break; }
    }
    // やや高め+注視も高め: 話者の頭部が下部の会話パネルに隠れない構図
    let cy = Math.max(p.y, n.y) + 2.05;
    const gh = G.World.heightAt(cx, cz);
    if (cy < gh + 0.6) cy = gh + 0.6;
    dlgTween = {
      k: 0,
      p0: camera.position.clone(),
      p1: new THREE.Vector3(cx, cy, cz),
      l0: new THREE.Vector3(p.x, p.y + 1.5, p.z),
      // 注視はやや低め — 話者が画面上半分に収まり、選択肢の背の高い
      // パネルが出ても胴体まで見える
      l1: new THREE.Vector3(mx, Math.max(p.y, n.y) + 1.1, mz)
    };
  }
  G.events.on('dialogueClosed', () => { dlgTween = null; camBlend = 0.45; });

  /* ---------------- カメラ ---------------- */
  const _lastCam = new THREE.Vector3();
  function updateCamera(dt) {
    const C = G.Camera;
    const p = G.Player;
    _lastCam.copy(camera.position);
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
    // 洞窟内は近め固定 (通路でカメラが引き離され自機が豆粒になるのを防ぐ)。
    // 滑空中は引き画 (翼が画面の大半を覆い進行方向が見えない指摘)
    const camDist = G.inCave ? Math.min(C.dist, 6.5) : (p.gliding ? C.dist + 3 : C.dist);

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
    const dist = camDist + (p.mounted ? 1.8 : 0) + bossBonus + framePull;
    let cx = p.pos.x - fx * dist;
    let cz = p.pos.z - fz * dist;
    let cy = p.pos.y + 1.6 + fy * dist;

    // 地形にめり込まない (視線上の複数点をサンプルして必要な持ち上げ量を求める)
    const gh = G.World.heightAt(cx, cz);
    if (cy < gh + 0.5) cy = gh + 0.5;
    const eyeY = p.pos.y + 1.6;
    let lift = 0, worstT = 1;
    for (let k = 0; k < 3; k++) {
      const t = 0.3 + k * 0.25;   // 0.3, 0.55, 0.8
      const sx = p.pos.x + (cx - p.pos.x) * t;
      const sz = p.pos.z + (cz - p.pos.z) * t;
      const sy = eyeY + (cy - eyeY) * t;
      const need = (G.World.heightAt(sx, sz) + 0.45 - sy) / t;
      if (need > lift) { lift = need; worstT = t; }
    }
    if (lift > 4.5) {
      // 壁級の遮蔽 (崖・洞窟口) は持ち上げると崖上からの俯瞰になり画面が
      // 岩肌で埋まる。持ち上げず、遮蔽の手前までカメラを寄せる
      const f = Math.max(0.3, worstT - 0.18);
      cx = p.pos.x + (cx - p.pos.x) * f;
      cz = p.pos.z + (cz - p.pos.z) * f;
      cy = eyeY + (cy - eyeY) * f;
      // 地表すれすれだと斜面の稜が自機下半身を隠す — 十分な余裕で持ち上げ、
      // さらに短縮後の視線に対してもう一度リフトを掛けて全身を確保する
      const gh2 = G.World.heightAt(cx, cz);
      if (cy < gh2 + 1.4) cy = gh2 + 1.4;
      let lift2 = 0;
      for (let k = 0; k < 3; k++) {
        const t2 = 0.35 + k * 0.3;
        const sx2 = p.pos.x + (cx - p.pos.x) * t2;
        const sz2 = p.pos.z + (cz - p.pos.z) * t2;
        const sy2 = eyeY + (cy - eyeY) * t2;
        const need2 = (G.World.heightAt(sx2, sz2) + 0.45 - sy2) / t2;
        if (need2 > lift2) lift2 = need2;
      }
      if (lift2 > 0) cy += Math.min(lift2, 3.5);
    } else if (lift > 0) cy += lift;

    // 木や岩が視線を遮るならカメラを手前へ寄せる
    const occ = G.World.cameraOcclusion(p.pos.x, p.pos.z, cx, cz);
    if (occ < 1) {
      cx = p.pos.x + (cx - p.pos.x) * occ;
      cz = p.pos.z + (cz - p.pos.z) * occ;
      cy = eyeY + (cy - eyeY) * occ;
    }

    // カメラは常に水面より上 (いかなる場合も水没しない)
    if (cy < G.World.WATER_Y + 0.45) cy = G.World.WATER_Y + 0.45;

    // 洞窟内: 入口付近でカメラが外郭の崖上に持ち上がり、自機が豆粒の
    // 高所俯瞰になるのを防ぐ (目線からの上方超過を制限)
    if (G.inCave && cy > eyeY + 5) cy = eyeY + 5;

    // 画面揺れ
    trauma = Math.max(0, trauma - dt * 1.8);
    const sh = trauma * trauma * 0.5;
    cx += (Math.random() - 0.5) * sh;
    cy += (Math.random() - 0.5) * sh;
    cz += (Math.random() - 0.5) * sh;

    // ボス頭部のフレーミング: 接近戦で頭が画面上端に見切れるなら、来フレームで
    // その分だけカメラを引く (フィードバックで数フレームかけて収束・離脱で減衰)。
    // 滞空ボスは引きでは追い切れないため、注視点を上へずらして仰ぎ見る
    let overAng = -1, lookUp = 0, fbBoss = null;
    if (bigBoss) {
      let fb = (p.target && p.target.alive && p.target.D && (p.target.D.barH || 0) > 3) ? p.target : null;
      if (!fb) {
        let nd = 30 * 30;
        for (const b of G.Enemies.bosses) {
          if (!b.alive || !b.engaged || (b.D.barH || 0) <= 3) continue;
          const d2 = G.dist2(p.pos.x, p.pos.z, b.pos.x, b.pos.z);
          if (d2 < nd) { nd = d2; fb = b; }
        }
      }
      if (fb) {
        fbBoss = fb;
        lookUp = Math.min(7, Math.max(0, fb.pos.y - p.pos.y) * 0.6);
        // 立ち上がりモーション中は頭部が barH より上に出るため 1.5倍で見積もる
        const headY = fb.pos.y + (fb.D.barH || 3) * 1.5 + 1.0;
        const headAng = Math.atan2(headY - cy, Math.hypot(fb.pos.x - cx, fb.pos.z - cz));
        const ctrAng = Math.atan2((p.pos.y + 1.5 + lookUp) - cy, Math.hypot(p.pos.x - cx, p.pos.z - cz));
        // 視野上半分 (FOV60の半分=0.52rad) に対する余白付き限界
        overAng = (headAng - ctrAng) - 0.4;
      }
    }
    // 引き量は控えめに上限 — 引き一辺倒だとボスもプレイヤーも豆粒になる。
    // 収まらない分は注視点の上方バイアス (lookUp) が仰角で吸収する
    framePull = G.clamp(framePull + (overAng > 0 ? overAng * 26 : -6) * dt, 0, 9);

    camera.position.set(cx, cy, cz);
    // 会話終了直後は前フレーム位置からなだらかに復帰 (スナップバック防止)
    if (camBlend > 0) {
      camBlend -= dt;
      camera.position.lerp(_lastCam, G.clamp(camBlend / 0.45, 0, 1) * 0.85);
    }
    camera.lookAt(p.pos.x, p.pos.y + 1.5 + lookUp, p.pos.z);

    // 視線を遮る建造物 (柱・塔・家屋) を半透明化。交戦ボスへの視線も守る
    if (fbBoss) {
      G.World.updateFaders(dt, p.pos.x, p.pos.z, cx, cz, eyeY, cy,
        fbBoss.pos.x, fbBoss.pos.z, fbBoss.pos.y + 2);
    } else {
      G.World.updateFaders(dt, p.pos.x, p.pos.z, cx, cz, eyeY, cy);
    }

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
        n: 2, color: 0x7e93a4, speed: 1.3, up: 1.4, gravity: 5,
        life: 0.22, size: 0.8, drag: 0.8
      });
    }

    // 夜の蛍 (雨天以外 — 残存降雨粒子がある間も出さない)
    const night = S.tod > 20 || S.tod < 4.5;
    if (night && S.weather < 0.3 && (G.Sky.rainAmt || 0) < 0.2 && Math.random() < dt * 2.2) {
      const p = G.Player.pos;
      const a = Math.random() * Math.PI * 2, d = 4 + Math.random() * 16;
      const x = p.x + Math.cos(a) * d, z = p.z + Math.sin(a) * d;
      const h = G.World.heightAt(x, z);
      // カメラ至近の加算スプライトは画面全体を覆う巨大グローになるため湧かせない
      const cp = G.Camera.cam ? G.Camera.cam.position : p;
      if (h > G.World.WATER_Y && G.dist2(x, z, cp.x, cp.z) > 6 * 6) {
        G.FX.burst(x, h + 0.6 + Math.random() * 1.2, z, {
          n: 1, color: 0xaaffcc, speed: 0.4, up: 0.35, gravity: -0.15,
          life: 2.6, size: 1.3, drag: 0.4, spread: 1
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
    if (!running) return;
    try {
      frame(now);
      if (running) requestAnimationFrame(loop);
    } catch (error) {
      fatalStop(error);
    }
  }

  function frame(now) {
    const rawGap = now - prevT;
    let dt = Math.min(rawGap / 1000, 0.05);
    prevT = now;
    lastRawGap = rawGap;

    handleActions();
    G.Input.updateFromKeys();

    if (hitstop > 0) {
      hitstop -= dt;
      dt *= 0.12;
    }

    // 会話カメラのトゥイーン (会話中は G.paused で通常カメラが止まるためここで駆動)
    if (G.paused && dlgTween) {
      dlgTween.k = Math.min(1, dlgTween.k + dt / 0.55);
      const e = 1 - Math.pow(1 - dlgTween.k, 3);   // easeOutCubic
      camera.position.lerpVectors(dlgTween.p0, dlgTween.p1, e);
      _lookTmp.lerpVectors(dlgTween.l0, dlgTween.l1, e);
      camera.lookAt(_lookTmp.x, _lookTmp.y, _lookTmp.z);
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
      // 夜間は自機が背景に溶けないだけの補助光を保証する (夜でも自機は必ず読める)
      G.playerLight.intensity = G.inCave ? 1.6
        : G.clamp((0.5 - G.Sky.lightLevel) * 2.0, 0, 0.8);
      G.playerLight.distance = G.inCave ? 19 : 11;

      // ダメージフラッシュ
      if (started) {
        if (prevHp !== null && G.Player.hp < prevHp) {
          flashEl.style.opacity = G.prefersReducedMotion() ? '0.16' : '0.45';
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
    G.perf.calls = renderer.info.render.calls;   // ドローコール削減の指標

    // RAF間隔も含めて観測する。GPU待ちで JS 計測だけが軽く見える端末でも
    // 30fpsを守れる一方、33.3msは快適域として画質を落とさない。
    const sampleGap = Math.min(Math.max(lastRawGap, 1), 150);
    const emaA = 1 - Math.exp(-sampleGap / 800);
    if (lastRawGap > 0 && lastRawGap < 150) frameEMA += (lastRawGap - frameEMA) * emaA;
    workEMA += (_t2 - _t0 - workEMA) * emaA;
    G.perf.frameMs = Math.max(frameEMA, workEMA);
    perfAdjustT += Math.min(lastRawGap, 150) / 1000;
    if (perfAdjustT > 1.5 && started && (lastRawGap < 150 || G.forceDRS)) {
      perfAdjustT = 0;
      const next = G.PerformanceGovernor.step(perfState, G.perf.frameMs, G.quality);
      if (next.resolution !== perfState.resolution) {
        renderer.setPixelRatio(basePixelRatio * next.resolution);
      }
      if (next.detail !== perfState.detail && G.World.setRuntimeDetail) {
        G.World.setRuntimeDetail(next.detail);
      }
      perfState = next;
      G.perf.resScale = next.resolution;
      G.perf.detail = next.detail;
    }
  }

  /* ---------------- 開始 ---------------- */
  function safeBoot() {
    try { Game.boot(); } catch (error) { fatalStop(error, 'ELDRIAを起動できませんでした'); }
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', safeBoot);
  } else {
    safeBoot();
  }
})();
