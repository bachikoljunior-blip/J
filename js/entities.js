/* =============================================================================
 * ELDRIA — entities.js
 * パーティクル / プロシージャルリグ / プレイヤー / 敵AI / ボス / NPC /
 * 飛翔体 / ドロップ品 / インタラクト対象
 * ========================================================================== */
'use strict';

/* ======================= パーティクル ======================= */
(function () {
  const FX = G.FX = {};
  let pts, pos, col, sizes, alive;
  const MAX = () => G.Q.particles;
  let P = [];   // {x,y,z,vx,vy,vz,life,max,size,r,g,b,grav,drag}
  let scene;

  FX.init = function (sc) {
    scene = sc;
    const n = MAX();
    pos = new Float32Array(n * 3);
    col = new Float32Array(n * 3);
    sizes = new Float32Array(n);
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    geo.setAttribute('color', new THREE.BufferAttribute(col, 3));
    geo.setAttribute('psize', new THREE.BufferAttribute(sizes, 1));
    const mat = new THREE.ShaderMaterial({
      transparent: true, depthWrite: false,
      blending: THREE.AdditiveBlending,   // 黒フェードのスマッジを防ぎ、光の粒として描く
      uniforms: { uTex: { value: G.makeRadialTex(32, [[0, 'rgba(255,255,255,1)'], [1, 'rgba(255,255,255,0)']]) } },
      vertexShader: `
        attribute float psize;
        attribute vec3 color;
        varying vec3 vC;
        void main(){
          vC = color;
          vec4 mv = modelViewMatrix * vec4(position, 1.0);
          gl_PointSize = psize * (240.0 / max(1.0, -mv.z));
          gl_Position = projectionMatrix * mv;
        }`,
      fragmentShader: `
        uniform sampler2D uTex;
        varying vec3 vC;
        void main(){
          vec4 t = texture2D(uTex, gl_PointCoord);
          gl_FragColor = vec4(vC, t.a);
        }`
    });
    pts = new THREE.Points(geo, mat);
    pts.frustumCulled = false;
    // 原点基準の透明ソートで水面等に沈まないよう、常に最後に加算描画する
    pts.renderOrder = 4;
    scene.add(pts);
  };

  const tmpC = new THREE.Color();
  FX.burst = function (x, y, z, o) {
    o = o || {};
    const n = o.n || 10;
    tmpC.set(o.color !== undefined ? o.color : 0xffffff);
    for (let i = 0; i < n; i++) {
      if (P.length >= MAX()) P.shift();
      const a = Math.random() * Math.PI * 2;
      const up = o.up !== undefined ? o.up : 0.5;
      const sp = (o.speed || 3) * (0.4 + Math.random() * 0.6);
      const spread = o.spread !== undefined ? o.spread : 1;
      P.push({
        x, y, z,
        vx: Math.cos(a) * sp * spread,
        vy: up * sp * (0.5 + Math.random()),
        vz: Math.sin(a) * sp * spread,
        life: 0, max: (o.life || 0.6) * (0.6 + Math.random() * 0.7),
        size: (o.size || 3) * (0.6 + Math.random() * 0.8),
        r: tmpC.r * (0.8 + Math.random() * 0.2),
        g: tmpC.g * (0.8 + Math.random() * 0.2),
        b: tmpC.b * (0.8 + Math.random() * 0.2),
        grav: o.gravity !== undefined ? o.gravity : 6,
        drag: o.drag !== undefined ? o.drag : 1.5
      });
    }
  };

  let prevN = 0;
  FX.update = function (dt) {
    if (!pts) return;
    let w = 0;
    for (let i = 0; i < P.length; i++) {
      const p = P[i];
      p.life += dt;
      if (p.life >= p.max) continue;
      const dr = Math.max(0, 1 - p.drag * dt);
      p.vx *= dr; p.vz *= dr;
      p.vy -= p.grav * dt;
      p.x += p.vx * dt; p.y += p.vy * dt; p.z += p.vz * dt;
      P[w++] = p;
    }
    P.length = w;
    const n = Math.min(w, MAX());
    // 粒子ゼロが続く間は転送も描画も行わない
    if (n === 0 && prevN === 0) { pts.visible = false; return; }
    pts.visible = n > 0;
    for (let i = 0; i < n; i++) {
      const p = P[i];
      const k = 1 - p.life / p.max;
      pos[i * 3] = p.x; pos[i * 3 + 1] = p.y; pos[i * 3 + 2] = p.z;
      col[i * 3] = p.r * k + 0.001; col[i * 3 + 1] = p.g * k; col[i * 3 + 2] = p.b * k;
      sizes[i] = p.size * (0.5 + k * 0.5);
    }
    prevN = n;
    pts.geometry.attributes.position.needsUpdate = true;
    pts.geometry.attributes.color.needsUpdate = true;
    pts.geometry.attributes.psize.needsUpdate = true;
    pts.geometry.setDrawRange(0, n);
  };
})();

/* ======================= リグ (プロシージャル人型/獣型) ======================= */
(function () {
  const Rigs = G.Rigs = {};
  let shadowTex = null, shadowGeo = null;
  /* ジオメトリ/マテリアルは寸法・色でキャッシュ共有する。
     敵の入れ替わりでGPUリソースが増え続けるのを防ぎ、
     マテリアル切替も減らす (リグは全てこのキャッシュ経由)。 */
  const matCache = new Map();
  const geoCache = new Map();
  const lam = c => {
    let m = matCache.get(c);
    if (!m) { m = new THREE.MeshLambertMaterial({ color: c }); matCache.set(c, m); }
    return m;
  };
  const boxGeo = (w, h, d) => {
    const k = w + ',' + h + ',' + d;
    let g = geoCache.get(k);
    if (!g) { g = new THREE.BoxGeometry(w, h, d); geoCache.set(k, g); }
    return g;
  };

  G.makeShadow = function (scale) {
    if (!shadowTex) {
      shadowTex = G.makeRadialTex(64, [[0, 'rgba(0,0,0,0.4)'], [0.7, 'rgba(0,0,0,0.25)'], [1, 'rgba(0,0,0,0)']]);
      shadowGeo = new THREE.PlaneGeometry(1, 1);
      shadowGeo.rotateX(-Math.PI / 2);
    }
    const m = new THREE.Mesh(shadowGeo, new THREE.MeshBasicMaterial({
      map: shadowTex, transparent: true, depthWrite: false
    }));
    m.scale.set(scale, 1, scale);
    return m;
  };

  function box(w, h, d, c) {
    const m = new THREE.Mesh(boxGeo(w, h, d), lam(c));
    m.castShadow = true;
    return m;
  }

  /* 人型。conf: {skin, cloth, cloth2, hair, scale, weapon:'sword'|'axe'|'bow'|'club'|null} */
  Rigs.humanoid = function (conf) {
    conf = conf || {};
    const g = new THREE.Group();
    const s = conf.scale || 1;
    const skin = conf.skin !== undefined ? conf.skin : 0xdfb28f;
    const cloth = conf.cloth !== undefined ? conf.cloth : 0x5d7a9a;
    const cloth2 = conf.cloth2 !== undefined ? conf.cloth2 : 0x3e4f63;

    const body = box(0.5, 0.58, 0.3, cloth);
    body.position.y = 0.98;
    const hips = box(0.44, 0.2, 0.28, cloth2);
    hips.position.y = 0.62;
    const head = new THREE.Group();
    const headM = box(0.34, 0.34, 0.34, skin);
    headM.position.y = 0.17;
    head.add(headM);
    if (conf.hair !== undefined) {
      const hair = box(0.36, 0.14, 0.36, conf.hair);
      hair.position.y = 0.33;
      head.add(hair);
    }
    if (conf.skull) {
      const eL = box(0.07, 0.07, 0.02, 0x220000);
      eL.position.set(-0.08, 0.17, 0.18);
      const eR = eL.clone(); eR.position.x = 0.08;
      head.add(eL, eR);
    }
    head.position.y = 1.28;

    const mkArm = (side) => {
      const grp = new THREE.Group();
      const upper = box(0.14, 0.5, 0.14, cloth);
      upper.position.y = -0.22;
      const hand = box(0.12, 0.12, 0.12, skin);
      hand.position.y = -0.5;
      grp.add(upper, hand);
      grp.position.set(0.33 * side, 1.22, 0);
      return grp;
    };
    const mkLeg = (side) => {
      const grp = new THREE.Group();
      const l = box(0.16, 0.55, 0.16, cloth2);
      l.position.y = -0.27;
      grp.add(l);
      grp.position.set(0.13 * side, 0.55, 0);
      return grp;
    };
    const armL = mkArm(-1), armR = mkArm(1);
    const legL = mkLeg(-1), legR = mkLeg(1);

    let weapon = null;
    if (conf.weapon === 'sword' || conf.weapon === 'axe' || conf.weapon === 'club' || conf.weapon === 'spear') {
      weapon = new THREE.Group();
      if (conf.weapon === 'sword') {
        const blade = box(0.07, 0.85, 0.02, 0xc9d2da);
        blade.position.y = 0.55;
        const guard = box(0.22, 0.05, 0.05, 0x8f7a3a);
        guard.position.y = 0.12;
        const grip = box(0.05, 0.18, 0.05, 0x5a4630);
        weapon.add(blade, guard, grip);
      } else if (conf.weapon === 'axe') {
        const pole = box(0.06, 0.9, 0.06, 0x6b4a2f);
        pole.position.y = 0.35;
        const bit = box(0.3, 0.26, 0.05, 0xaab3bb);
        bit.position.set(0.14, 0.66, 0);
        weapon.add(pole, bit);
      } else if (conf.weapon === 'spear') {
        const pole = box(0.05, 1.5, 0.05, 0x6b4a2f);
        pole.position.y = 0.55;
        const tip = box(0.1, 0.3, 0.03, 0xb8c4cc);
        tip.position.y = 1.35;
        weapon.add(pole, tip);
      } else {
        const cl = box(0.12, 0.6, 0.12, 0x7a5a3a);
        cl.position.y = 0.3;
        weapon.add(cl);
      }
      weapon.position.set(0, -0.5, 0);
      armR.add(weapon);
    } else if (conf.weapon === 'bow') {
      weapon = new THREE.Group();
      let bowGeo = geoCache.get('bow');
      if (!bowGeo) { bowGeo = new THREE.TorusGeometry(0.4, 0.03, 4, 8, Math.PI); geoCache.set('bow', bowGeo); }
      const bowC = new THREE.Mesh(bowGeo, lam(0x6b4a2f));
      bowC.rotation.z = Math.PI / 2;
      weapon.add(bowC);
      weapon.position.set(0, -0.5, 0.05);
      armL.add(weapon);
    }

    let wing = null;
    if (conf.glider) {
      wing = new THREE.Group();
      // 中央から連続したアーチ状キャノピー (5枚の板を繋げる)
      for (let i = 0; i < 5; i++) {
        const t = (i - 2) / 2;             // -1..1
        const seg = box(0.5, 0.045, 0.55, i % 2 ? 0x5f9fb4 : 0x74b7cc);
        seg.position.set(t * 0.95, -Math.abs(t) * 0.22 + 0.1, 0);
        seg.rotation.z = t * 0.42;
        wing.add(seg);
      }
      const frame = box(0.06, 0.06, 0.5, 0x6b4a2f);
      frame.position.y = -0.05;
      const barL = box(0.05, 0.4, 0.05, 0x6b4a2f);
      barL.position.set(-0.18, -0.3, 0.05);
      const barR = barL.clone(); barR.position.x = 0.18;
      wing.add(frame, barL, barR);
      wing.position.set(0, 1.95, -0.05);
      wing.visible = false;
      g.add(wing);
    }

    g.add(body, hips, head, armL, armR, legL, legR);
    g.scale.setScalar(s);

    const parts = { body, hips, head, armL, armR, legL, legR, weapon, wing };

    /* pose: 状態に応じて各部の回転を設定 */
    function pose(p) {
      // p: {state, t, moveAmt, combo, atkT, phase}
      const t = G.time;
      // リセット
      armL.rotation.set(0, 0, 0.08);
      armR.rotation.set(0, 0, -0.08);
      legL.rotation.set(0, 0, 0);
      legR.rotation.set(0, 0, 0);
      body.rotation.set(0, 0, 0);
      head.rotation.set(0, 0, 0);
      g.rotation.x = 0; g.rotation.z = 0;
      g.position.y = p.baseY || 0;

      if (parts.wing) parts.wing.visible = !!p.glide;
      const mv = p.moveAmt || 0;
      if (p.ride) {
        // 騎乗姿勢
        legL.rotation.x = 0.7; legL.rotation.z = 0.4;
        legR.rotation.x = 0.7; legR.rotation.z = -0.4;
        armL.rotation.x = -0.7; armR.rotation.x = -0.7;
        body.rotation.x = 0.12;
        return;
      }
      if (p.glide) {
        // 滑空姿勢
        armL.rotation.x = -2.8; armR.rotation.x = -2.8;
        legL.rotation.x = 0.3; legR.rotation.x = 0.3;
        body.rotation.x = 0.4;
        return;
      }
      if (p.state === 'dead') {
        const k = G.clamp(p.t * 2.2, 0, 1);
        g.rotation.x = -k * Math.PI / 2 * 0.96;
        g.position.y = (p.baseY || 0) - k * 0.25;
        return;
      }
      if (p.state === 'roll') {
        g.rotation.x = -(p.t / 0.45) * Math.PI * 2;
        g.position.y = (p.baseY || 0) + 0.5;
        legL.rotation.x = 0.9; legR.rotation.x = 0.9;
        armL.rotation.x = 0.8; armR.rotation.x = 0.8;
        return;
      }
      // 歩行サイクル
      const wt = t * (8 + mv * 4);
      const swing = Math.sin(wt) * 0.75 * mv;
      legL.rotation.x = swing;
      legR.rotation.x = -swing;
      armL.rotation.x = -swing * 0.8;
      armR.rotation.x = swing * 0.8;
      body.rotation.x = mv * 0.12;
      g.position.y = (p.baseY || 0) + Math.abs(Math.sin(wt)) * 0.05 * mv;

      if (p.state === 'attack') {
        const k = p.atkT; // 0..1
        const c = p.combo || 0;
        if (p.spin) {
          body.rotation.y = k * Math.PI * 2;
          armR.rotation.x = -1.5; armR.rotation.y = -1.1;
          armL.rotation.x = -0.5; armL.rotation.z = 0.9;
          return;
        }
        if (p.heavy) {
          if (k < 0.45) { // 振りかぶり
            armR.rotation.x = -2.6 * (k / 0.45);
            armR.rotation.z = -0.3;
            body.rotation.y = -0.35 * (k / 0.45);
          } else {
            const j = (k - 0.45) / 0.55;
            armR.rotation.x = -2.6 + j * 3.6;
            body.rotation.y = -0.35 + j * 0.7;
            body.rotation.x = j * 0.3;
          }
        } else if (c % 2 === 0) { // 横薙ぎ
          if (k < 0.35) {
            armR.rotation.x = -2.1 * (k / 0.35);
            armR.rotation.y = -1.2 * (k / 0.35);
            body.rotation.y = -0.65 * (k / 0.35);
            body.rotation.z = 0.12 * (k / 0.35);
          } else {
            const j = (k - 0.35) / 0.65;
            armR.rotation.x = -1.5 + j * 1.1;
            armR.rotation.y = -0.9 + j * 2.0;
            body.rotation.y = -0.4 + j * 0.85;
          }
        } else { // 逆袈裟
          if (k < 0.35) {
            armR.rotation.x = -2.2 * (k / 0.35);
            body.rotation.y = 0.35 * (k / 0.35);
          } else {
            const j = (k - 0.35) / 0.65;
            armR.rotation.x = -2.2 + j * 2.8;
            body.rotation.y = 0.35 - j * 0.75;
          }
        }
        return;
      }
      if (p.state === 'windup') {
        armR.rotation.x = -2.3 * G.clamp(p.t / (p.windup || 0.6), 0, 1);
        body.rotation.y = -0.3;
        return;
      }
      if (p.state === 'shoot') {
        armL.rotation.x = -1.5;
        armR.rotation.x = -1.3;
        armR.rotation.y = 0.4 - G.clamp(p.t * 2, 0, 0.5);
        return;
      }
      if (p.state === 'hit') {
        body.rotation.x = -0.3;
        head.rotation.x = -0.25;
        armL.rotation.x = -0.5; armR.rotation.x = -0.5;
        return;
      }
      if (p.state === 'idle' && mv < 0.05) {
        const b = Math.sin(t * 1.8 + (p.seed || 0));
        body.rotation.x = 0.02 + b * 0.015;
        armL.rotation.z = 0.1 + b * 0.02;
        armR.rotation.z = -0.1 - b * 0.02;
      }
    }
    return { group: g, parts, pose };
  };

  /* 狼型 */
  Rigs.wolf = function (conf) {
    conf = conf || {};
    const g = new THREE.Group();
    const s = conf.scale || 1;
    const fur = conf.fur !== undefined ? conf.fur : 0x6e6459;
    const body = box(0.5, 0.45, 1.1, fur);
    body.position.y = 0.62;
    if (conf.mane) {
      // 王の鬣: 首まわりに氷青の房
      for (let i = 0; i < 5; i++) {
        const m = box(0.14, 0.5 - Math.abs(i - 2) * 0.08, 0.16, i % 2 ? 0xbdd6e8 : 0x9fc2dc);
        const a = (i - 2) * 0.5;
        m.position.set(Math.sin(a) * 0.32, 0.95 + (0.2 - Math.abs(i - 2) * 0.05), 0.42 + Math.cos(a) * 0.1);
        m.rotation.z = -a * 0.4;
        g.add(m);
      }
      const glow = new THREE.Sprite(new THREE.SpriteMaterial({
        map: G.makeRadialTex(48, [[0, 'rgba(120,210,255,0.55)'], [1, 'rgba(80,180,255,0)']]),
        transparent: true, depthWrite: false, blending: THREE.AdditiveBlending
      }));
      glow.position.set(0, 0.85, 0.75);
      glow.scale.set(1.5, 1.5, 1);
      g.add(glow);
    }
    const head = new THREE.Group();
    const hm = box(0.34, 0.3, 0.42, fur);
    const snout = box(0.16, 0.14, 0.22, conf.snout !== undefined ? conf.snout : 0x4e463e);
    snout.position.set(0, -0.05, 0.28);
    const earL = box(0.08, 0.14, 0.04, fur); earL.position.set(-0.1, 0.2, -0.05);
    const earR = earL.clone(); earR.position.x = 0.1;
    const eyeL = box(0.05, 0.05, 0.02, conf.eye !== undefined ? conf.eye : 0xcc2222);
    eyeL.position.set(-0.09, 0.05, 0.21);
    const eyeR = eyeL.clone(); eyeR.position.x = 0.09;
    head.add(hm, snout, earL, earR, eyeL, eyeR);
    if (conf.mane) {
      // 王の眼光 (氷青の発光)
      const mkGlow = (x) => {
        const gs = new THREE.Sprite(new THREE.SpriteMaterial({
          map: G.makeRadialTex(32, [[0, 'rgba(140,230,255,1)'], [1, 'rgba(80,190,255,0)']]),
          transparent: true, depthWrite: false, blending: THREE.AdditiveBlending
        }));
        gs.position.set(x, 0.06, 0.34);
        gs.scale.set(0.55, 0.55, 1);
        return gs;
      };
      head.add(mkGlow(-0.09), mkGlow(0.09));
    }
    head.position.set(0, 0.78, 0.62);
    const tail = box(0.1, 0.1, 0.5, fur);
    tail.position.set(0, 0.72, -0.75);
    const mkLeg = (x, z) => {
      const grp = new THREE.Group();
      const l = box(0.12, 0.45, 0.12, fur);
      l.position.y = -0.22;
      grp.add(l);
      grp.position.set(x, 0.45, z);
      return grp;
    };
    const legFL = mkLeg(-0.18, 0.4), legFR = mkLeg(0.18, 0.4);
    const legBL = mkLeg(-0.18, -0.4), legBR = mkLeg(0.18, -0.4);
    g.add(body, head, tail, legFL, legFR, legBL, legBR);
    g.scale.setScalar(s);
    const parts = { body, head, tail, legFL, legFR, legBL, legBR };

    function pose(p) {
      const t = G.time;
      const mv = p.moveAmt || 0;
      g.rotation.x = 0; g.position.y = p.baseY || 0;
      head.rotation.set(0, 0, 0);
      if (p.state === 'dead') {
        const k = G.clamp(p.t * 2.2, 0, 1);
        g.rotation.z = k * Math.PI / 2 * 0.9;
        g.position.y = (p.baseY || 0) - k * 0.2;
        return;
      }
      const wt = t * (9 + mv * 6);
      const sw = Math.sin(wt) * 0.9 * mv;
      legFL.rotation.x = sw; legBR.rotation.x = sw;
      legFR.rotation.x = -sw; legBL.rotation.x = -sw;
      body.position.y = 0.62 + Math.abs(Math.sin(wt)) * 0.06 * mv;
      tail.rotation.y = Math.sin(t * 3) * 0.3;
      if (p.state === 'windup') {
        g.rotation.x = 0.12;
        head.rotation.x = -0.4 * G.clamp(p.t / (p.windup || 0.5), 0, 1);
      } else if (p.state === 'attack') {
        head.rotation.x = 0.5;
        g.rotation.x = -0.1;
      } else if (p.state === 'hit') {
        g.rotation.z = 0.15;
      } else if (p.state === 'idle' && mv < 0.05) {
        head.rotation.y = Math.sin(t * 0.7 + (p.seed || 0)) * 0.4;
      }
    }
    return { group: g, parts, pose };
  };

  /* ゴーレム型 (岩の巨人) */
  Rigs.golem = function (conf) {
    conf = conf || {};
    const g = new THREE.Group();
    const s = conf.scale || 1;
    const rock = conf.rock !== undefined ? conf.rock : 0x7d7a72;
    const body = box(0.9, 0.95, 0.6, rock);
    body.position.y = 1.25;
    const head = box(0.42, 0.4, 0.42, rock);
    head.position.y = 1.98;
    const eye = box(0.26, 0.08, 0.02, 0xffcc44);
    eye.position.set(0, 1.98, 0.22);
    const mkArm = (side) => {
      const grp = new THREE.Group();
      const a = box(0.3, 0.85, 0.3, rock);
      a.position.y = -0.4;
      const fist = box(0.4, 0.35, 0.4, 0x6c6963);
      fist.position.y = -0.9;
      grp.add(a, fist);
      grp.position.set(0.68 * side, 1.62, 0);
      return grp;
    };
    const mkLeg = (side) => {
      const grp = new THREE.Group();
      const l = box(0.34, 0.75, 0.34, 0x6c6963);
      l.position.y = -0.37;
      grp.add(l);
      grp.position.set(0.3 * side, 0.78, 0);
      return grp;
    };
    const armL = mkArm(-1), armR = mkArm(1);
    const legL = mkLeg(-1), legR = mkLeg(1);
    g.add(body, head, eye, armL, armR, legL, legR);
    g.scale.setScalar(s);
    const parts = { body, head, armL, armR, legL, legR, eye };

    function pose(p) {
      const t = G.time;
      const mv = p.moveAmt || 0;
      g.rotation.x = 0; g.position.y = p.baseY || 0;
      armL.rotation.set(0, 0, 0.1); armR.rotation.set(0, 0, -0.1);
      body.rotation.set(0, 0, 0);
      if (p.state === 'dead') {
        const k = G.clamp(p.t * 1.5, 0, 1);
        g.rotation.x = -k * Math.PI / 2 * 0.9;
        g.position.y = (p.baseY || 0) - k * 0.4;
        return;
      }
      const wt = t * (4.5 + mv * 2);
      const sw = Math.sin(wt) * 0.5 * mv;
      legL.rotation.x = sw; legR.rotation.x = -sw;
      armL.rotation.x = -sw * 0.5; armR.rotation.x = sw * 0.5;
      g.position.y = (p.baseY || 0) + Math.abs(Math.sin(wt)) * 0.08 * mv;
      if (p.state === 'windup') {
        const k = G.clamp(p.t / (p.windup || 0.9), 0, 1);
        armL.rotation.x = -2.6 * k; armR.rotation.x = -2.6 * k;
        body.rotation.x = -0.2 * k;
      } else if (p.state === 'attack') {
        armL.rotation.x = 0.9; armR.rotation.x = 0.9;
        body.rotation.x = 0.35;
      } else if (p.state === 'throw') {
        const k = G.clamp(p.t / 0.5, 0, 1);
        armR.rotation.x = -2.8 + k * 3.2;
        body.rotation.y = -0.4 + k * 0.6;
      } else if (p.state === 'hit') {
        body.rotation.x = -0.12;
      }
    }
    return { group: g, parts, pose };
  };

  /* サソリ型 */
  Rigs.scorpion = function (conf) {
    conf = conf || {};
    const g = new THREE.Group();
    const s = conf.scale || 1;
    const shell = conf.shell !== undefined ? conf.shell : 0xa3703c;
    const body = box(0.7, 0.3, 0.9, shell);
    body.position.y = 0.35;
    const tailSeg = box(0.16, 0.16, 0.3, shell);
    const tail = new THREE.Group();
    for (let i = 0; i < 3; i++) {
      const t = tailSeg.clone();
      t.position.set(0, i * 0.22, -0.55 - i * 0.16);
      t.rotation.x = 0.6 + i * 0.25;
      tail.add(t);
    }
    const sting = box(0.12, 0.24, 0.12, 0x552a10);
    sting.position.set(0, 0.75, -0.95);
    tail.add(sting);
    tail.position.set(0, 0.4, 0);
    const clawL = box(0.24, 0.16, 0.4, shell);
    clawL.position.set(-0.4, 0.3, 0.55);
    const clawR = clawL.clone(); clawR.position.x = 0.4;
    g.add(body, tail, clawL, clawR);
    g.scale.setScalar(s);
    function pose(p) {
      const t = G.time;
      const mv = p.moveAmt || 0;
      g.position.y = p.baseY || 0;
      g.rotation.z = 0;
      if (p.state === 'dead') {
        const k = G.clamp(p.t * 2, 0, 1);
        g.rotation.z = k * Math.PI * 0.95;
        g.position.y = (p.baseY || 0) - k * 0.1;
        return;
      }
      body.position.y = 0.35 + Math.abs(Math.sin(t * 12)) * 0.03 * mv;
      if (p.state === 'windup') {
        tail.rotation.x = -0.5 * G.clamp(p.t / (p.windup || 0.5), 0, 1);
      } else if (p.state === 'attack') {
        tail.rotation.x = 0.7;
      } else {
        tail.rotation.x = Math.sin(t * 2 + (p.seed || 0)) * 0.1;
      }
    }
    return { group: g, parts: {}, pose };
  };

  /* ミミック (宝箱の化物) */
  Rigs.mimic = function () {
    const g = new THREE.Group();
    const body = box(1.1, 0.6, 0.7, 0x7a5230);
    body.position.y = 0.3;
    const lid = new THREE.Group();
    const lidM = box(1.1, 0.28, 0.7, 0x8a5f38);
    lidM.position.set(0, 0.14, 0.35);
    lid.add(lidM);
    for (let i = 0; i < 4; i++) {
      const tooth = box(0.1, 0.16, 0.05, 0xe8e4d0);
      tooth.position.set(-0.4 + i * 0.26, 0.02, 0.32);
      lid.add(tooth);
      const tooth2 = tooth.clone();
      tooth2.position.y = 0.55; tooth2.position.z = 0.3;
      g.add(tooth2);
    }
    lid.position.set(0, 0.6, -0.35);
    lid.rotation.x = -0.7;
    const eye = box(0.14, 0.1, 0.04, 0xcc2222);
    eye.position.set(0, 0.75, 0.1);
    lid.add(eye);
    const band = box(1.16, 0.62, 0.12, 0xc9a94a);
    band.position.y = 0.31;
    const tongue = box(0.3, 0.05, 0.4, 0xaa3344);
    tongue.position.set(0, 0.62, 0.15);
    g.add(body, lid, band, tongue);
    const parts = { lid };
    function pose(p) {
      const t = G.time;
      const mv = p.moveAmt || 0;
      g.position.y = (p.baseY || 0) + Math.abs(Math.sin(t * 9)) * 0.22 * mv;
      g.rotation.z = 0;
      if (p.state === 'dead') {
        const k = G.clamp(p.t * 2, 0, 1);
        g.rotation.z = k * Math.PI * 0.9;
        g.position.y = (p.baseY || 0) - k * 0.1;
        return;
      }
      if (p.state === 'windup') lid.rotation.x = -1.5;
      else if (p.state === 'attack') lid.rotation.x = -0.15;
      else lid.rotation.x = -0.7 + Math.sin(t * 2.5) * 0.15;
    }
    return { group: g, parts, pose };
  };

  /* 馬 */
  Rigs.horse = function () {
    const g = new THREE.Group();
    const coat = 0x8a7563, maneC = 0x3f332a;
    const body = box(0.62, 0.72, 1.7, coat);
    body.position.y = 1.12;
    const neck = box(0.3, 0.75, 0.35, coat);
    neck.position.set(0, 1.62, 0.72); neck.rotation.x = -0.45;
    const headG = new THREE.Group();
    const hm = box(0.26, 0.28, 0.6, coat);
    hm.position.z = 0.1;
    const maneM = box(0.1, 0.42, 0.3, maneC);
    maneM.position.set(0, 0.1, -0.3);
    const earL = box(0.06, 0.14, 0.05, coat); earL.position.set(-0.09, 0.24, -0.14);
    const earR = earL.clone(); earR.position.x = 0.09;
    headG.add(hm, maneM, earL, earR);
    headG.position.set(0, 2.02, 1.02);
    const tail = box(0.13, 0.62, 0.16, maneC);
    tail.position.set(0, 1.22, -0.95); tail.rotation.x = 0.5;
    const saddle = box(0.56, 0.15, 0.62, 0x5a3a28);
    saddle.position.y = 1.53;
    const mkLeg = (x, z) => {
      const grp = new THREE.Group();
      const l = box(0.16, 0.78, 0.16, coat);
      l.position.y = -0.38;
      grp.add(l);
      grp.position.set(x, 0.78, z);
      return grp;
    };
    const legFL = mkLeg(-0.22, 0.6), legFR = mkLeg(0.22, 0.6);
    const legBL = mkLeg(-0.22, -0.6), legBR = mkLeg(0.22, -0.6);
    g.add(body, neck, headG, tail, saddle, legFL, legFR, legBL, legBR);
    const parts = { body, headG, tail, legFL, legFR, legBL, legBR };
    function pose(p) {
      const t = G.time;
      const mv = p.moveAmt || 0;
      g.position.y = p.baseY || 0;
      const wt = t * (7 + mv * 6);
      const sw = Math.sin(wt) * 1.15 * mv;
      legFL.rotation.x = sw; legBR.rotation.x = sw;
      legFR.rotation.x = -sw; legBL.rotation.x = -sw;
      body.position.y = 1.12 + Math.abs(Math.sin(wt)) * 0.07 * mv;
      tail.rotation.y = Math.sin(t * 1.5) * 0.25;
      headG.rotation.x = mv > 0.05 ? -0.1 : Math.sin(t * 0.8 + (p.seed || 0)) * 0.18 + 0.12;
    }
    return { group: g, parts, pose };
  };

  /* ドラゴン */
  Rigs.dragon = function () {
    const g = new THREE.Group();
    const scale = 3.2;
    const dark = 0x3a2f3f, belly = 0x6a4a52, wingC = 0x54303c;
    const body = box(1.0, 0.8, 2.0, dark);
    body.position.y = 1.2;
    const bellyM = box(0.7, 0.4, 1.6, belly);
    bellyM.position.y = 0.9;
    const neck = new THREE.Group();
    const neckM = box(0.5, 0.5, 0.9, dark);
    neckM.position.set(0, 0.25, 0.4);
    const headG = new THREE.Group();
    const headM = box(0.5, 0.45, 0.8, dark);
    const jaw = box(0.4, 0.15, 0.6, belly);
    jaw.position.set(0, -0.25, 0.1);
    const hornL = box(0.08, 0.4, 0.08, 0xd8cfa8);
    hornL.position.set(-0.16, 0.35, -0.3); hornL.rotation.x = -0.5;
    const hornR = hornL.clone(); hornR.position.x = 0.16;
    const eyeL = box(0.08, 0.08, 0.03, 0xffaa22);
    eyeL.position.set(-0.2, 0.1, 0.3);
    const eyeR = eyeL.clone(); eyeR.position.x = 0.2;
    headG.add(headM, jaw, hornL, hornR, eyeL, eyeR);
    headG.position.set(0, 0.6, 0.9);
    neck.add(neckM, headG);
    neck.position.set(0, 1.5, 0.9);
    const tail = new THREE.Group();
    for (let i = 0; i < 4; i++) {
      const t = box(0.4 - i * 0.08, 0.3 - i * 0.05, 0.7, dark);
      t.position.set(0, 0, -0.6 - i * 0.62);
      tail.add(t);
    }
    tail.position.set(0, 1.15, -0.9);
    const mkWing = (side) => {
      const grp = new THREE.Group();
      const m1 = box(1.6, 0.08, 0.9, wingC);
      m1.position.set(0.8 * side, 0, 0);
      const m2 = box(1.2, 0.06, 0.7, wingC);
      m2.position.set(1.9 * side, -0.1, -0.1);
      grp.add(m1, m2);
      grp.position.set(0.45 * side, 1.65, 0.2);
      return grp;
    };
    const wingL = mkWing(-1), wingR = mkWing(1);
    const mkLeg = (x, z) => {
      const grp = new THREE.Group();
      const l = box(0.25, 0.7, 0.25, dark);
      l.position.y = -0.35;
      grp.add(l);
      grp.position.set(x, 0.85, z);
      return grp;
    };
    const legFL = mkLeg(-0.45, 0.6), legFR = mkLeg(0.45, 0.6);
    const legBL = mkLeg(-0.45, -0.6), legBR = mkLeg(0.45, -0.6);
    g.add(body, bellyM, neck, tail, wingL, wingR, legFL, legFR, legBL, legBR);
    g.scale.setScalar(scale);
    const parts = { body, neck, headG, tail, wingL, wingR };

    function pose(p) {
      const t = G.time;
      const mv = p.moveAmt || 0;
      const fly = p.fly || 0;   // 0=接地 1=飛行
      g.position.y = (p.baseY || 0) + fly * (2.2 + Math.sin(t * 2.2) * 0.4);
      const flap = fly > 0.05 ? Math.sin(t * 6) * (0.5 + fly * 0.4) : Math.sin(t * 1.2) * 0.06;
      wingL.rotation.z = -flap - 0.15;
      wingR.rotation.z = flap + 0.15;
      neck.rotation.x = -0.2 + Math.sin(t * 1.1) * 0.05;
      tail.rotation.y = Math.sin(t * 0.9) * 0.25;
      if (p.state === 'dead') {
        const k = G.clamp(p.t * 1.2, 0, 1);
        g.rotation.z = k * Math.PI / 2 * 0.8;
        g.position.y = (p.baseY || 0) - k * 0.3;
        return;
      }
      g.rotation.z = 0;
      if (p.state === 'windup') {
        neck.rotation.x = -0.8 * G.clamp(p.t / (p.windup || 0.8), 0, 1);
      } else if (p.state === 'attack' || p.state === 'breath') {
        neck.rotation.x = 0.35;
      }
      const wt = t * (5 + mv * 3);
      if (fly < 0.5) {
        const sw = Math.sin(wt) * 0.5 * mv;
        legFL.rotation.x = sw; legBR.rotation.x = sw;
        legFR.rotation.x = -sw; legBL.rotation.x = -sw;
      } else {
        legFL.rotation.x = legFR.rotation.x = legBL.rotation.x = legBR.rotation.x = 0.5;
      }
    }
    return { group: g, parts, pose };
  };
})();

/* ======================= 予兆リング ======================= */
(function () {
  const R = G.TelegraphRing = {};
  const pool = [];
  let scene;
  R.init = function (sc) {
    scene = sc;
    for (let i = 0; i < 4; i++) {
      const m = new THREE.Mesh(
        new THREE.RingGeometry(0.8, 1.0, 24),
        new THREE.MeshBasicMaterial({
          color: 0xff2020, transparent: true, opacity: 0.6,
          depthWrite: false, side: THREE.DoubleSide
        })
      );
      m.rotation.x = -Math.PI / 2;
      m.visible = false;
      m.renderOrder = 2;
      scene.add(m);
      pool.push(m);
    }
  };
  let used = 0;
  R.begin = function () { used = 0; };
  /* windup 中の敵の足元に出す。t: 0..1 進行度, r: 半径 */
  R.show = function (x, z, r, t) {
    if (used >= pool.length) return;
    const m = pool[used++];
    m.visible = true;
    const gh = G.World.heightAt(x, z);
    m.position.set(x, gh + 0.12, z);
    const pulse = 1 + Math.sin(G.time * 14) * 0.06;
    m.scale.setScalar(r * pulse);
    m.material.opacity = 0.3 + t * 0.45;
  };
  R.end = function () {
    for (let i = used; i < pool.length; i++) pool[i].visible = false;
  };
})();

/* ======================= 剣筋トレイル ======================= */
(function () {
  const SA = G.SwingArc = {};
  let scene;
  const pool = [];
  SA.init = function (sc) {
    scene = sc;
    const sector = new THREE.RingGeometry(1.1, 2.3, 18, 1, -1.2, 2.4);
    const full = new THREE.RingGeometry(1.2, 2.9, 24);
    for (let i = 0; i < 3; i++) {
      const m = new THREE.Mesh(i === 2 ? full : sector, new THREE.MeshBasicMaterial({
        color: 0xcfe8ff, transparent: true, opacity: 0,
        blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide
      }));
      m.rotation.x = -Math.PI / 2;
      m.visible = false;
      m.renderOrder = 3;
      scene.add(m);
      pool.push({ mesh: m, t: 1 });
    }
  };
  /* kind: 0=弱 1=強 2=回転 */
  SA.show = function (x, y, z, yaw, kind) {
    const p = pool[kind === 2 ? 2 : (pool[0].t < 1 ? 1 : 0)];
    p.t = 0;
    p.decay = kind === 0 ? 4.2 : 2.0;   // 強/回転は約0.5秒残す
    p.mesh.visible = true;
    p.mesh.position.set(x, y + 1.05, z);
    p.mesh.rotation.z = -yaw + Math.PI / 2 - 1.2;
    p.mesh.material.color.set(kind === 1 ? 0xffd27a : kind === 2 ? 0xa8ffd0 : 0xcfe8ff);
    const s = kind === 1 ? 1.2 : 1;
    p.mesh.scale.set(s, s, s);
  };
  SA.update = function (dt) {
    for (const p of pool) {
      if (p.t >= 1) { p.mesh.visible = false; continue; }
      p.t += dt * (p.decay || 4.2);
      p.mesh.material.opacity = Math.max(0, 0.75 * (1 - p.t));
      if (p.t >= 1) p.mesh.visible = false;
    }
  };
})();

/* ======================= 焦げ跡デカール ======================= */
(function () {
  const S = G.Scorch = {};
  const pool = [];
  let scene, idx = 0;
  S.init = function (sc) {
    scene = sc;
    const geo = new THREE.CircleGeometry(1.3, 12);
    geo.rotateX(-Math.PI / 2);
    for (let i = 0; i < 6; i++) {
      const m = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({
        color: 0x14100c, transparent: true, opacity: 0, depthWrite: false
      }));
      m.visible = false;
      m.renderOrder = 1;
      scene.add(m);
      pool.push({ mesh: m, t: 1 });
    }
  };
  S.add = function (x, z) {
    const p = pool[idx++ % pool.length];
    p.t = 0;
    p.mesh.visible = true;
    p.mesh.position.set(x, G.World.heightAt(x, z) + 0.08, z);
    p.mesh.scale.setScalar(0.8 + Math.random() * 0.5);
  };
  S.update = function (dt) {
    for (const p of pool) {
      if (p.t >= 1) { p.mesh.visible = false; continue; }
      p.t += dt / 6;
      p.mesh.material.opacity = 0.5 * (1 - p.t);
    }
  };
})();

/* ======================= アクター共通 ======================= */
(function () {
  G.Actors = {};

  G.Actors.groundMove = function (a, vx, vz, dt) {
    // 水平移動 + 衝突 + 接地
    let nx = a.pos.x + vx * dt;
    let nz = a.pos.z + vz * dt;
    // 深水は進入不可
    if (G.World.isDeepWater(nx, nz)) {
      if (!G.World.isDeepWater(nx, a.pos.z)) nz = a.pos.z;
      else if (!G.World.isDeepWater(a.pos.x, nz)) nx = a.pos.x;
      else { nx = a.pos.x; nz = a.pos.z; }
    }
    const c = G.World.collide(nx, nz, a.radius);
    a.pos.x = c.x; a.pos.z = c.z;
    const gh = G.World.heightAt(a.pos.x, a.pos.z);
    if (a.pos.y > gh + 0.02 || a.vy > 0) {
      a.vy -= 26 * dt;
      a.pos.y += a.vy * dt;
      if (a.pos.y <= gh) { a.pos.y = gh; if (a.vy < -9) G.Audio.sfx('land'); a.vy = 0; a.grounded = true; }
      else a.grounded = false;
    } else {
      a.pos.y = gh;
      a.vy = 0;
      a.grounded = true;
    }
  };

  G.Actors.updateShadow = function (a) {
    if (!a.shadow) return;
    const gh = G.World.heightAt(a.pos.x, a.pos.z);
    a.shadow.position.set(a.pos.x, gh + 0.06, a.pos.z);
    const k = G.clamp(1 - (a.pos.y - gh) * 0.15, 0.4, 1);
    a.shadow.material.opacity = k * (G.shadowsOn ? 0.5 : 1);
  };
})();

/* ======================= プレイヤー ======================= */
(function () {
  const P = G.Player = {};
  let scene, rig;
  const V = new THREE.Vector3();

  P.pos = new THREE.Vector3(6, 6, 34);
  P.yaw = Math.PI;
  P.vy = 0;
  P.radius = 0.45;
  P.hp = 100; P.stamina = 100;
  P.state = 'idle';       // idle move roll attack hit dead
  P.stateT = 0;
  P.combo = 0;
  P.heavy = false;
  P.atkDone = false;      // 現在の攻撃で判定を出したか
  P.grounded = true;
  P.target = null;        // ロックオン対象
  P.iframe = 0;
  P.staRegenDelay = 0;
  P.moveAmt = 0;
  P.alive = true;
  P.lastAtkEnd = -9;      // コンボ受付
  P.potionCd = 0;

  P.init = function (sc) {
    scene = sc;
    P.buildRig();
    P.shadow = G.makeShadow(1.3);
    scene.add(P.shadow);
  };

  /* 装備に応じた見た目再構築 */
  P.buildRig = function () {
    if (rig) scene.remove(rig.group);
    const eq = G.Inv.equip;
    const armor = G.Items.get(eq.armor);
    const wpn = G.Items.get(eq.weapon);
    rig = G.Rigs.humanoid({
      skin: 0xdfb28f,
      hair: 0x4a3628,
      cloth: armor ? armor.color : 0x5d7a9a,
      cloth2: armor ? armor.color2 : 0x3e4f63,
      weapon: wpn ? (wpn.kind || 'sword') : 'sword',
      glider: true
    });
    scene.add(rig.group);
  };

  P.maxHp = () => G.Stats.maxHp();
  P.maxSta = () => G.Stats.maxSta();

  P.heal = function (n) {
    P.hp = Math.min(P.maxHp(), P.hp + n);
    G.FX.burst(P.pos.x, P.pos.y + 1, P.pos.z, { n: 14, color: 0x66ff88, speed: 2, up: 1.2, gravity: -1, life: 0.8, size: 3 });
  };

  P.takeDamage = function (dmg, srcX, srcZ) {
    if (!P.alive || P.iframe > 0 || P.state === 'roll' && P.stateT > 0.03 && P.stateT < 0.36) return;
    const def = G.Stats.def();
    const real = Math.max(1, Math.round(dmg * (100 / (100 + def * 6))));
    P.hp -= real;
    P.iframe = 0.55;
    G.Audio.sfx('hitPlayer');
    G.events.emit('shake', 0.35);
    if (navigator.vibrate) navigator.vibrate(45);
    G.UI.dmgNum(P.pos.x, P.pos.y + 1.6, P.pos.z, real, { player: true });
    G.FX.burst(P.pos.x, P.pos.y + 1, P.pos.z, { n: 10, color: 0xcc3333, speed: 3, life: 0.5 });
    if (P.hp <= 0) {
      P.hp = 0; P.alive = false;
      P.state = 'dead'; P.stateT = 0;
      G.Audio.sfx('death');
      G.events.emit('playerDead');
    } else if (P.state !== 'attack' && P.state !== 'roll') {
      P.state = 'hit'; P.stateT = 0;
      // ノックバック
      if (srcX !== undefined) {
        const dx = P.pos.x - srcX, dz = P.pos.z - srcZ;
        const d = Math.max(0.1, Math.hypot(dx, dz));
        P.pos.x += dx / d * 0.5; P.pos.z += dz / d * 0.5;
      }
    }
  };

  P.respawn = function (x, z) {
    P.pos.set(x, G.World.heightAt(x, z), z);
    P.hp = P.maxHp();
    P.stamina = P.maxSta();
    P.alive = true;
    P.state = 'idle'; P.stateT = 0;
    P.vy = 0; P.iframe = 1.5;
    P.target = null;
  };

  function useStamina(n) {
    P.stamina = Math.max(0, P.stamina - n);
    P.staRegenDelay = 0.85;
  }

  /* id 指定でその薬だけを使う。省略時は弱い方から */
  P.usePotion = function (id) {
    if (P.potionCd > 0 || !P.alive) return;
    if (!id) id = G.Inv.count('potion') > 0 ? 'potion' : 'hipotion';
    if (id === 'potion' && G.Inv.remove('potion', 1)) {
      P.heal(Math.round(P.maxHp() * 0.42));
    } else if (id === 'hipotion' && G.Inv.remove('hipotion', 1)) {
      P.heal(Math.round(P.maxHp() * 0.7));
    } else {
      G.UI.toast('回復薬がない…');
      return;
    }
    G.Audio.sfx('potion');
    P.potionCd = 1.2;
  };

  P.tryAttack = function (kind) {
    if (!P.alive || P.state === 'roll' || P.state === 'dead') return;
    if (P.mounted) { G.Horse.dismount(); return; }
    const heavy = kind === true;
    const spin = kind === 'spin';
    const cost = spin ? 30 : heavy ? 22 : 11;
    if (P.stamina < cost * 0.4) return;
    if (P.state === 'attack') {
      // 先行入力: 現在の振りが半ばまで進んでいれば次のコンボへ
      if (P.atkT > 0.5 && P.combo < 2 && !heavy && !spin && !P.heavy && !P.spin) {
        P.queued = true;
      }
      return;
    }
    // コンボ継続判定
    if (!heavy && !spin && G.time - P.lastAtkEnd < 0.7) P.combo = (P.combo + 1) % 3;
    else P.combo = 0;
    P.state = 'attack';
    P.stateT = 0;
    P.atkT = 0;
    P.heavy = heavy;
    P.spin = spin;
    P.atkDone = false;
    P.queued = false;
    useStamina(cost);
    G.Audio.sfx(heavy || spin ? 'swingHeavy' : 'swing');
    // ロックオン中は対象へ向く
    if (P.target && P.target.alive) {
      P.yaw = Math.atan2(P.target.pos.x - P.pos.x, P.target.pos.z - P.pos.z);
    }
  };

  P.tryRoll = function () {
    if (!P.alive || P.state === 'roll' || P.state === 'dead') return;
    if (P.mounted) G.Horse.dismount();
    if (P.stamina < 8) return;
    P.state = 'roll'; P.stateT = 0;
    useStamina(18);
    G.Audio.sfx('roll');
    G.FX.burst(P.pos.x, P.pos.y + 0.2, P.pos.z, { n: 8, color: 0xb0a58a, speed: 2, life: 0.4, up: 0.4 });
    // 入力方向 or 前方
    const inp = G.Input;
    const cy = G.Camera.yaw;
    if (Math.abs(inp.moveX) > 0.1 || Math.abs(inp.moveY) > 0.1) {
      P.rollDir = Math.atan2(
        inp.moveX * Math.cos(cy) - inp.moveY * Math.sin(cy),
        -inp.moveY * Math.cos(cy) - inp.moveX * Math.sin(cy)
      );
    } else {
      P.rollDir = P.yaw;
    }
    P.yaw = P.rollDir;
  };

  P.tryJump = function () {
    if (!P.alive || !P.grounded || P.state === 'roll') return;
    if (P.stamina < 5) return;
    P.vy = 8.2;
    P.pos.y += 0.05;
    P.grounded = false;
    useStamina(6);
    G.Audio.sfx('jump');
  };

  P.toggleLock = function () {
    if (P.target) { P.target = null; return; }
    let best = null, bd = 24 * 24;
    for (const e of G.Enemies.all()) {
      if (!e.alive) continue;
      const d2 = G.dist2(P.pos.x, P.pos.z, e.pos.x, e.pos.z);
      if (d2 < bd) { bd = d2; best = e; }
    }
    P.target = best;
    if (best) G.Audio.sfx('ui');
  };

  /* 攻撃の当たり判定 */
  function doAttackHit() {
    const reach = P.spin ? 3.0 : P.heavy ? 2.6 : 2.3;
    const atk = G.Stats.atk();
    const mult = P.spin ? 1.7 : P.heavy ? 1.9 : [1.0, 1.05, 1.3][P.combo];
    let hitAny = false;
    for (const e of G.Enemies.all()) {
      if (!e.alive) continue;
      const dx = e.pos.x - P.pos.x, dz = e.pos.z - P.pos.z;
      const d = Math.hypot(dx, dz);
      if (d > reach + e.radius) continue;
      const ang = Math.atan2(dx, dz);
      if (!P.spin && Math.abs(G.angDiff(P.yaw, ang)) > 1.25) continue;
      const crit = Math.random() < 0.1;
      let dmg = Math.round(atk * mult * (0.92 + Math.random() * 0.16) * (crit ? 1.6 : 1));
      G.Enemies.damage(e, dmg, crit);
      hitAny = true;
    }
    if (hitAny) {
      G.Audio.sfx('hit');
      G.events.emit('hitstop', P.heavy ? 0.09 : 0.05);
      G.events.emit('shake', P.heavy ? 0.25 : 0.12);
    }
  }

  P.update = function (dt) {
    const inp = G.Input;
    P.stateT += dt;
    P.iframe = Math.max(0, P.iframe - dt);
    P.potionCd = Math.max(0, P.potionCd - dt);

    // スタミナ回復
    P.staRegenDelay -= dt;
    if (P.staRegenDelay <= 0 && P.state !== 'roll') {
      P.stamina = Math.min(P.maxSta(), P.stamina + 24 * dt);
    }

    // ロックオン対象消滅
    if (P.target && (!P.target.alive || G.dist2(P.pos.x, P.pos.z, P.target.pos.x, P.target.pos.z) > 40 * 40)) {
      P.target = null;
    }

    if (P.state === 'dead') {
      rig.group.position.copy(P.pos);
      rig.group.rotation.y = P.yaw;
      rig.pose({ state: 'dead', t: P.stateT, baseY: P.pos.y });
      G.Actors.updateShadow(P);
      return;
    }

    if (P.state === 'hit') {
      if (P.stateT > 0.32) { P.state = 'idle'; P.stateT = 0; }
    }

    if (P.state === 'roll') {
      const sp = 8.8;
      G.Actors.groundMove(P, Math.sin(P.rollDir) * sp, Math.cos(P.rollDir) * sp, dt);
      if (P.stateT >= 0.45) { P.state = 'idle'; P.stateT = 0; }
    } else if (P.state === 'attack') {
      const dur = P.spin ? 0.85 : P.heavy ? 0.75 : 0.42;
      P.atkT = P.stateT / dur;
      // 踏み込み
      const lunge = (!P.spin && P.atkT > 0.3 && P.atkT < 0.6) ? (P.heavy ? 2.6 : 2.0) : 0;
      if (lunge) G.Actors.groundMove(P, Math.sin(P.yaw) * lunge, Math.cos(P.yaw) * lunge, dt);
      if (!P.atkDone && P.atkT >= (P.spin ? 0.5 : P.heavy ? 0.55 : 0.45)) {
        P.atkDone = true;
        G.SwingArc.show(P.pos.x, P.pos.y, P.pos.z, P.yaw, P.spin ? 2 : P.heavy ? 1 : 0);
        doAttackHit();
      }
      if (P.atkT >= 1) {
        P.lastAtkEnd = G.time;
        P.state = 'idle'; P.stateT = 0;
        if (P.queued) { P.queued = false; P.tryAttack(false); }
      }
    }

    // ボス体内への侵入を押し出す (見た目サイズの押し出し半径)
    for (const b of G.Enemies.bosses) {
      if (!b.alive) continue;
      const dx = P.pos.x - b.pos.x, dz = P.pos.z - b.pos.z;
      const rr = (b.D.pushR || b.radius) + P.radius;
      const d2 = dx * dx + dz * dz;
      if (d2 < rr * rr && d2 > 0.0001) {
        const d = Math.sqrt(d2);
        P.pos.x += dx / d * (rr - d);
        P.pos.z += dz / d * (rr - d);
      }
    }

    // 滑空判定 (空中で跳躍ボタン長押し)
    P.gliding = !P.grounded && P.vy < -0.5 && inp.held.jump &&
                P.stamina > 1 && !P.mounted &&
                P.state !== 'roll' && P.state !== 'dead';
    if (P.gliding) useStamina(4 * dt);
    // 落下速度の記録 (落下ダメージ用)
    if (!P.grounded) P.fallVy = Math.min(P.fallVy || 0, P.vy);

    // 移動 (attack/roll 以外)
    let mv = 0;
    if (P.state !== 'roll' && P.state !== 'attack' && P.state !== 'hit') {
      const ix = inp.moveX, iy = inp.moveY;
      const len = Math.hypot(ix, iy);
      if (len > 0.08) {
        const cy = G.Camera.yaw;
        // カメラ基準の移動方向
        const wx = (ix * Math.cos(cy) - iy * Math.sin(cy));
        const wz = (-iy * Math.cos(cy) - ix * Math.sin(cy));
        const dir = Math.atan2(wx, wz);
        const sprint = inp.sprint && (P.mounted || P.stamina > 1) && len > 0.5;
        if (sprint && !P.mounted) useStamina(11 * dt);
        let spd;
        if (P.mounted) spd = (10.5 + (sprint ? 3.2 : 0)) * Math.min(1, len);
        else if (P.gliding) spd = 7.5;
        else spd = (4.6 + (sprint ? 3.2 : 0)) * Math.min(1, len);
        // ロックオン中は対象を向きつつ移動
        if (P.target && P.target.alive && !sprint && !P.mounted && !P.gliding) {
          P.yaw = G.angLerp(P.yaw, Math.atan2(P.target.pos.x - P.pos.x, P.target.pos.z - P.pos.z), G.damp(12, dt));
        } else {
          P.yaw = G.angLerp(P.yaw, dir, G.damp(P.mounted ? 5 : 11, dt));
        }
        G.Actors.groundMove(P, Math.sin(dir) * spd, Math.cos(dir) * spd, dt);
        mv = Math.min(1, spd / (P.mounted ? 13 : 7.8));
        P.state = 'move';
        // 足音
        P.stepT = (P.stepT || 0) + dt * spd;
        if (P.stepT > (P.mounted ? 3.2 : 2.2) && P.grounded) { P.stepT = 0; G.Audio.sfx('step'); }
      } else if (P.gliding) {
        // 入力なしでも前方へ滑空
        G.Actors.groundMove(P, Math.sin(P.yaw) * 6.5, Math.cos(P.yaw) * 6.5, dt);
        mv = 0.5;
        P.state = 'move';
      } else {
        P.state = 'idle';
        G.Actors.groundMove(P, 0, 0, dt);
      }
      // 滑空中は落下速度を抑える
      if (P.gliding) { P.vy = Math.max(P.vy, -2.2); P.fallVy = Math.max(P.fallVy || 0, -6); }
    } else if (P.state === 'attack' || P.state === 'hit') {
      G.Actors.groundMove(P, 0, 0, dt);
    }
    // 落下ダメージ
    if (P.grounded && P.alive && (P.fallVy || 0) < -19) {
      const dmg = Math.round((-P.fallVy - 19) * 5);
      P.hp -= dmg;
      G.UI.dmgNum(P.pos.x, P.pos.y + 1.6, P.pos.z, dmg, { player: true });
      G.Audio.sfx('hitPlayer');
      G.events.emit('shake', 0.4);
      if (P.hp <= 0) {
        P.hp = 0; P.alive = false;
        P.state = 'dead'; P.stateT = 0;
        G.Audio.sfx('death');
        G.events.emit('playerDead');
      }
    }
    if (P.grounded) P.fallVy = 0;
    P.moveAmt += (mv - P.moveAmt) * G.damp(10, dt);

    // リグ更新
    rig.group.position.copy(P.pos);
    rig.group.rotation.y = P.yaw;
    rig.pose({
      state: P.state === 'move' ? 'idle' : P.state,
      t: P.stateT, atkT: P.atkT || 0, combo: P.combo,
      heavy: P.heavy, spin: P.spin, moveAmt: P.mounted ? 0 : P.moveAmt,
      baseY: P.pos.y + (P.mounted ? 0.92 : 0),
      glide: P.gliding, ride: P.mounted
    });
    G.Actors.updateShadow(P);
  };

  P.getRig = () => rig;
})();

/* ======================= 敵 ======================= */
(function () {
  const E = G.Enemies = {};
  let scene;
  const list = [];         // 通常敵
  const bosses = [];       // ボス
  E.list = list;
  E.bosses = bosses;
  E.all = function () { return list.concat(bosses); };

  const TYPES = {
    wolf:      { name: '野狼',       rigFn: 'wolf',     barH: 1.4, hp: 40,  atk: 12, speed: 5.2, xp: 14, gold: 6,  aggroR: 18, atkR: 1.7, windup: 0.45, cool: 1.2, radius: 0.5, scale: 1,   drops: [['pelt', 0.6], ['potion', 0.08]] },
    goblin:    { name: 'ゴブリン',   rigFn: 'goblin',   barH: 1.9, hp: 55,  atk: 15, speed: 3.8, xp: 18, gold: 12, aggroR: 16, atkR: 1.9, windup: 0.55, cool: 1.5, radius: 0.45, scale: 0.9, drops: [['potion', 0.12], ['magicstone', 0.1]] },
    skeleton:  { name: 'スケルトン', rigFn: 'skeleton', barH: 2.0, hp: 45,  atk: 13, speed: 3.2, xp: 20, gold: 14, aggroR: 22, atkR: 12,  windup: 0.7,  cool: 2.4, radius: 0.45, scale: 1,   ranged: true, drops: [['bone', 0.6], ['magicstone', 0.12]] },
    golemling: { name: '岩の子鬼',   rigFn: 'golemling',barH: 1.8, hp: 90,  atk: 20, speed: 2.6, xp: 30, gold: 20, aggroR: 14, atkR: 2.3, windup: 0.85, cool: 2.0, radius: 0.6, scale: 0.62, poise: 3, drops: [['magicstone', 0.5]] },
    scorpion:  { name: '砂蠍',       rigFn: 'scorpion', barH: 1.3, hp: 50,  atk: 16, speed: 4.4, xp: 22, gold: 15, aggroR: 15, atkR: 1.8, windup: 0.5,  cool: 1.4, radius: 0.55, scale: 1.1, drops: [['magicstone', 0.15], ['potion', 0.1]] },
    bandit:    { name: '盗賊',       rigFn: 'bandit',   barH: 1.9, hp: 70,  atk: 18, speed: 4.2, xp: 26, gold: 24, aggroR: 17, atkR: 1.9, windup: 0.5,  cool: 1.4, radius: 0.45, scale: 0.95, drops: [['potion', 0.15], ['magicstone', 0.1]] },
    fireimp:   { name: '火の小鬼',   rigFn: 'fireimp',  barH: 1.5, hp: 48,  atk: 16, speed: 3.6, xp: 24, gold: 18, aggroR: 20, atkR: 13,  windup: 0.6,  cool: 2.2, radius: 0.4, scale: 0.7, ranged: true, proj: 'fire', drops: [['magicstone', 0.3]] },
    mimic:     { name: 'ミミック',   rigFn: 'mimic',    barH: 1.4, hp: 130, atk: 26, speed: 5.0, xp: 60, gold: 80, aggroR: 30, atkR: 1.8, windup: 0.4,  cool: 1.1, radius: 0.55, scale: 1, poise: 3, drops: [['hipotion', 0.5], ['magicstone', 0.5]] },
    nightwisp: { name: '夜の骸骨',   rigFn: 'skeleton', barH: 2.0, hp: 38,  atk: 14, speed: 4.0, xp: 16, gold: 10, aggroR: 26, atkR: 1.8, windup: 0.5,  cool: 1.3, radius: 0.45, scale: 1, night: true, drops: [['bone', 0.5]] }
  };
  E.TYPES = TYPES;

  function buildRig(type, T) {
    switch (T.rigFn) {
      case 'wolf': return G.Rigs.wolf({ scale: T.scale });
      case 'goblin': return G.Rigs.humanoid({ scale: T.scale, skin: 0x7a9a4a, cloth: 0x6b5a3a, cloth2: 0x4a3f2a, weapon: 'club' });
      case 'skeleton': return G.Rigs.humanoid({ scale: T.scale, skin: 0xd8d4c8, cloth: 0xb5b0a3, cloth2: 0x8a867c, skull: true, weapon: type === 'nightwisp' ? 'sword' : 'bow' });
      case 'golemling': return G.Rigs.golem({ scale: T.scale });
      case 'scorpion': return G.Rigs.scorpion({ scale: T.scale });
      case 'bandit': return G.Rigs.humanoid({ scale: T.scale, skin: 0xd8a880, hair: 0x992222, cloth: 0x4a4a55, cloth2: 0x33333c, weapon: 'sword' });
      case 'fireimp': return G.Rigs.humanoid({ scale: T.scale, skin: 0xd05533, hair: 0x220000, cloth: 0x882211, cloth2: 0x551108 });
      case 'mimic': return G.Rigs.mimic();
    }
    return G.Rigs.humanoid({ scale: T.scale });
  }

  E.init = function (sc) { scene = sc; };

  E.spawn = function (type, x, z, opts) {
    opts = opts || {};
    const T = TYPES[type];
    const rig = buildRig(type, T);
    const e = {
      type, T, rig,
      name: T.name,
      pos: new THREE.Vector3(x, G.World.heightAt(x, z), z),
      home: new THREE.Vector3(x, 0, z),
      yaw: Math.random() * Math.PI * 2,
      vy: 0, radius: T.radius,
      hp: T.hp * (opts.hpMult || 1), maxHp: T.hp * (opts.hpMult || 1),
      state: 'idle', stateT: 0, moveAmt: 0,
      cool: 0, alive: true, aggro: false,
      poise: T.poise || 1, poiseC: 0,
      spawnRef: opts.spawnRef || null,
      temp: !!opts.temp,
      seed: Math.random() * 10,
      wanderT: 0, wanderA: Math.random() * Math.PI * 2,
      deadT: 0
    };
    rig.group.position.copy(e.pos);
    scene.add(rig.group);
    e.shadow = G.makeShadow(T.radius * 2.6);
    scene.add(e.shadow);
    list.push(e);
    return e;
  };

  E.damage = function (e, dmg, crit) {
    if (!e.alive) return;
    e.hp -= dmg;
    e.aggro = true;
    G.UI.dmgNum(e.pos.x, e.pos.y + (e.T && e.T.barH ? e.T.barH - 0.2 : 1.6), e.pos.z, dmg, { crit });
    G.FX.burst(e.pos.x, e.pos.y + 1, e.pos.z, { n: crit ? 8 : 5, color: 0xffd24a, speed: 3.2, life: 0.28, size: 1.6 });
    G.FX.burst(e.pos.x, e.pos.y + 0.9, e.pos.z, { n: 1, color: 0xffffff, speed: 0.05, life: 0.18, size: 9, gravity: 0, drag: 0 });
    if (e.hp <= 0) { kill(e); return; }
    // ノックバック (プレイヤーから離れる方向へ)
    const kdx = e.pos.x - G.Player.pos.x, kdz = e.pos.z - G.Player.pos.z;
    const kd = Math.hypot(kdx, kdz) || 1;
    const c2 = G.World.collide(e.pos.x + kdx / kd * 0.4, e.pos.z + kdz / kd * 0.4, e.radius);
    e.pos.x = c2.x; e.pos.z = c2.z;
    e.poiseC++;
    if (e.poiseC >= (e.T.poise || 1)) {
      e.poiseC = 0;
      if (e.state !== 'dead') { e.state = 'hit'; e.stateT = 0; }
    }
  };

  function kill(e) {
    e.alive = false;
    e.state = 'dead'; e.stateT = 0; e.deadT = 0;
    G.Audio.sfx('enemyDie');
    const T = e.T;
    G.Stats.addXP(T.xp);
    G.Inv.addGold(T.gold + ((Math.random() * T.gold * 0.5) | 0));
    G.FX.burst(e.pos.x, e.pos.y + 0.8, e.pos.z, { n: 18, color: 0x554466, speed: 3, life: 0.7 });
    // ドロップ
    if (T.drops) {
      for (const [id, p] of T.drops) {
        if (Math.random() < p) G.Pickups.drop(id, e.pos.x, e.pos.z);
      }
    }
    if (e.spawnRef) { e.spawnRef.alive = false; e.spawnRef.deadUntil = G.time + 100; }
    G.events.emit('kill', { type: e.type, pos: e.pos });
  }

  function remove(e) {
    scene.remove(e.rig.group);
    scene.remove(e.shadow);
    e.shadow.material.dispose();   // 影のマテリアルのみ個別 (geo/texは共有)
    const i = list.indexOf(e);
    if (i >= 0) list.splice(i, 1);
    if (e.spawnRef && e.alive) e.spawnRef.alive = false;
    if (G.Player.target === e) G.Player.target = null;  // 幽霊ロックオン防止
  }
  E.removeAll = function () {
    for (const e of list.slice()) remove(e);
  };

  /* 盗賊キャンプの固定スポーン */
  const FIXED_SPAWNS = [
    { x: -153, z: 247, type: 'bandit', alive: false, deadUntil: 0 },
    { x: -147, z: 252, type: 'bandit', alive: false, deadUntil: 0 },
    { x: -150, z: 256, type: 'bandit', alive: false, deadUntil: 0 },
    { x: 217, z: 137, type: 'bandit', alive: false, deadUntil: 0 },
    { x: 224, z: 142, type: 'bandit', alive: false, deadUntil: 0 },
    { x: 220, z: 146, type: 'bandit', alive: false, deadUntil: 0 }
  ];

  /* スポーン管理 */
  let spawnT = 0, nightT = 0;
  function manageSpawns(dt) {
    spawnT -= dt;
    if (spawnT > 0) return;
    spawnT = 0.8;
    const p = G.Player.pos;
    // ボス交戦中は雑魚の新規湧きを止める (ボスの召喚は例外)
    let bossFight = false;
    for (const b of bosses) if (b.alive && b.engaged) { bossFight = true; break; }
    if (!bossFight && list.length < 26) {
      for (const s of FIXED_SPAWNS) {
        if (s.alive || G.time < s.deadUntil) continue;
        const d2 = G.dist2(p.x, p.z, s.x, s.z);
        if (d2 < 28 * 28 || d2 > 190 * 190) continue;
        s.alive = true;
        E.spawn(s.type, s.x, s.z, { spawnRef: s });
      }
      for (const s of G.World.activeSpawns()) {
        if (s.alive || G.time < s.deadUntil) continue;
        const d2 = G.dist2(p.x, p.z, s.x, s.z);
        if (d2 < 28 * 28 || d2 > 190 * 190) continue;
        s.alive = true;
        E.spawn(s.type, s.x, s.z, { spawnRef: s });
        if (list.length >= 26) break;
      }
    }
    // 夜の追加湧き
    const tod = G.State.tod;
    const isNight = tod > 20.3 || tod < 4.5;
    if (isNight && list.filter(e => e.temp).length < 4 && !G.World.nearLandmark(p.x, p.z, 30)) {
      nightT -= 0.8;
      if (nightT <= 0) {
        nightT = 9;
        const a = Math.random() * Math.PI * 2, d = 28 + Math.random() * 20;
        const x = p.x + Math.cos(a) * d, z = p.z + Math.sin(a) * d;
        if (!G.World.isDeepWater(x, z) && !G.World.nearLandmark(x, z, 26)) {
          const e = E.spawn('nightwisp', x, z, { temp: true });
          G.FX.burst(x, e.pos.y + 1, z, { n: 16, color: 0x8866cc, speed: 2.5, life: 0.8 });
        }
      }
    }
    // 昼になったら夜敵は消える / 遠すぎる敵は片付け
    for (const e of list.slice()) {
      if (e.temp && !isNight && e.alive) {
        G.FX.burst(e.pos.x, e.pos.y + 1, e.pos.z, { n: 12, color: 0x8866cc, speed: 2, life: 0.6 });
        remove(e);
        continue;
      }
      if (G.dist2(p.x, p.z, e.pos.x, e.pos.z) > 240 * 240) remove(e);
    }
  }

  /* 敵 1 体の AI */
  function updateEnemy(e, dt) {
    e.stateT += dt;
    const p = G.Player;
    const T = e.T;

    if (e.state === 'dead') {
      e.deadT += dt;
      e.rig.pose({ state: 'dead', t: e.deadT, baseY: e.pos.y });
      e.rig.group.position.copy(e.pos);
      if (e.deadT > 2.4) remove(e);
      return;
    }

    const d2 = G.dist2(p.pos.x, p.pos.z, e.pos.x, e.pos.z);
    const dist = Math.sqrt(d2);
    // AI LOD: 遠い敵は間引き
    if (dist > 70) {
      e.rig.group.position.copy(e.pos);
      G.Actors.updateShadow(e);
      return;
    }
    const toP = Math.atan2(p.pos.x - e.pos.x, p.pos.z - e.pos.z);

    if (!e.aggro && p.alive && dist < T.aggroR) {
      e.aggro = true;
      e.cool = 0.4 + Math.random() * 0.5;
    }
    if (e.aggro && (!p.alive || dist > T.aggroR * 2.6)) {
      e.aggro = false;
      e.state = 'idle';
    }

    e.cool = Math.max(0, e.cool - dt);
    let mv = 0;

    if (e.state === 'hit') {
      if (e.stateT > 0.34) { e.state = 'idle'; e.stateT = 0; }
    } else if (e.state === 'windup') {
      e.yaw = G.angLerp(e.yaw, toP, G.damp(6, dt));
      if (e.stateT >= T.windup) {
        e.state = 'attack'; e.stateT = 0;
        if (T.ranged && e.type !== 'nightwisp') {
          const pj = T.proj || 'arrow';
          G.Audio.sfx(pj === 'fire' ? 'fireball' : 'arrow');
          const sy = e.pos.y + 1.2;
          G.Projectiles.spawn(pj, e.pos.x, sy, e.pos.z, p.pos.x, p.pos.y + 0.9, p.pos.z, pj === 'fire' ? 13 : 16, T.atk);
        } else {
          G.Audio.sfx('swing');
        }
      }
    } else if (e.state === 'attack') {
      const isMelee = !T.ranged || e.type === 'nightwisp';
      if (isMelee && e.stateT > 0.12 && !e.hitDone) {
        e.hitDone = true;
        const reach = T.atkR + 0.7;
        if (dist < reach && Math.abs(G.angDiff(e.yaw, toP)) < 1.1 && p.alive) {
          p.takeDamage(T.atk * (0.9 + Math.random() * 0.2), e.pos.x, e.pos.z);
        }
      }
      if (e.stateT > 0.38) {
        e.state = 'idle'; e.stateT = 0;
        e.hitDone = false;
        e.cool = T.cool * (0.8 + Math.random() * 0.5);
      }
    } else if (e.aggro && p.alive) {
      // 追跡 / 攻撃距離キープ
      e.yaw = G.angLerp(e.yaw, toP, G.damp(7, dt));
      if (T.ranged && e.type !== 'nightwisp') {
        // 距離を保つ
        let want = 0;
        if (dist < 7) want = -1;
        else if (dist > 15) want = 1;
        if (want !== 0) {
          const sp = T.speed * want;
          G.Actors.groundMove(e, Math.sin(toP) * sp, Math.cos(toP) * sp, dt);
          mv = 0.8;
        }
        if (e.cool <= 0 && dist < 18 && dist > 4) {
          e.state = 'windup'; e.stateT = 0;
        }
      } else {
        if (dist > T.atkR) {
          const sp = T.speed;
          G.Actors.groundMove(e, Math.sin(toP) * sp, Math.cos(toP) * sp, dt);
          mv = 1;
        } else if (e.cool <= 0) {
          e.state = 'windup'; e.stateT = 0;
        } else {
          // クールダウン中は左右にステップ
          const strafe = toP + Math.PI / 2 * (e.seed > 5 ? 1 : -1);
          G.Actors.groundMove(e, Math.sin(strafe) * T.speed * 0.35, Math.cos(strafe) * T.speed * 0.35, dt);
          mv = 0.35;
        }
      }
    } else {
      // うろつき
      e.wanderT -= dt;
      if (e.wanderT <= 0) {
        e.wanderT = 2 + Math.random() * 4;
        e.wanderA = Math.random() * Math.PI * 2;
        e.wandering = Math.random() < 0.6;
      }
      if (e.wandering) {
        // 巣から離れすぎたら戻る
        if (G.dist2(e.pos.x, e.pos.z, e.home.x, e.home.z) > 220) {
          e.wanderA = Math.atan2(e.home.x - e.pos.x, e.home.z - e.pos.z);
        }
        e.yaw = G.angLerp(e.yaw, e.wanderA, G.damp(3, dt));
        G.Actors.groundMove(e, Math.sin(e.yaw) * T.speed * 0.3, Math.cos(e.yaw) * T.speed * 0.3, dt);
        mv = 0.3;
      }
    }

    e.moveAmt += (mv - e.moveAmt) * G.damp(8, dt);
    e.rig.group.position.copy(e.pos);
    e.rig.group.rotation.y = e.yaw;
    e.rig.pose({
      state: e.state === 'windup' ? 'windup' : e.state,
      t: e.stateT, windup: T.windup, moveAmt: e.moveAmt, seed: e.seed,
      baseY: e.pos.y,
      atkT: e.state === 'attack' ? G.clamp(e.stateT / 0.38, 0, 1) : 0,
      combo: 0
    });
    G.Actors.updateShadow(e);
  }

  E.update = function (dt) {
    manageSpawns(dt);
    G.TelegraphRing.begin();
    // remove() が splice するので逆順走査 (毎フレームの配列複製を避ける)
    for (let i = list.length - 1; i >= 0; i--) {
      const e = list[i];
      updateEnemy(e, dt);
      if (e.alive && e.state === 'windup') {
        G.TelegraphRing.show(e.pos.x, e.pos.z, (e.T.atkR > 5 ? 1.2 : e.T.atkR + 0.6), G.clamp(e.stateT / e.T.windup, 0, 1));
      }
    }
    for (const b of bosses) {
      G.Bosses.update(b, dt);
      if (b.alive && b.state === 'windup') {
        G.TelegraphRing.show(b.pos.x, b.pos.z, b.radius + 2.4, G.clamp(b.stateT / (b.windupDur || 0.8), 0, 1));
      }
    }
    G.TelegraphRing.end();
  };

  E.anyAggro = function () {
    for (const e of list) if (e.alive && e.aggro) return true;
    return false;
  };
})();

/* ======================= ボス ======================= */
(function () {
  const B = G.Bosses = {};
  let scene;

  const DEFS = {
    fenrir: {
      name: '白狼王フェンリル', hp: 380, atk: 22, speed: 7.2, xp: 300, gold: 250,
      x: -430, z: -140, arenaR: 34, radius: 1.3, pushR: 2.1, barH: 3.4,
      build: () => G.Rigs.wolf({ scale: 2.9, fur: 0xd8d8e0, snout: 0xb8b8c2, eye: 0x44ddff, mane: true })
    },
    golem: {
      name: '遺跡の巨像', hp: 700, atk: 34, speed: 2.9, xp: 600, gold: 500,
      x: 430, z: -80, arenaR: 36, radius: 1.6, pushR: 2.2, barH: 5.0,
      build: () => G.Rigs.golem({ scale: 2.4, rock: 0x8a8478 })
    },
    scorpking: {
      name: '砂帝スコルグ', hp: 550, atk: 30, speed: 5.6, xp: 900, gold: 700,
      x: 390, z: 380, arenaR: 30, radius: 1.5, pushR: 2.4, barH: 2.6,
      build: () => G.Rigs.scorpion({ scale: 2.6, shell: 0xb8863f })
    },
    dragon: {
      name: '黒竜ヴァルドレク', hp: 1400, atk: 40, xp: 2000, gold: 1500, speed: 5,
      x: -40, z: -640, arenaR: 40, radius: 4.0, barH: 6.5,
      build: () => G.Rigs.dragon()
    }
  };
  B.DEFS = DEFS;

  B.init = function (sc) {
    scene = sc;
    for (const id in DEFS) {
      if (G.State.bossKilled[id]) continue;
      spawnBoss(id);
    }
  };

  function spawnBoss(id) {
    const D = DEFS[id];
    const rig = D.build();
    const b = {
      isBoss: true, bossId: id, T: { scale: id === 'dragon' ? 3.2 : 2.2 },
      name: D.name, D,
      pos: new THREE.Vector3(D.x, G.World.heightAt(D.x, D.z), D.z),
      yaw: 0, vy: 0, radius: D.radius,
      hp: D.hp, maxHp: D.hp,
      state: 'idle', stateT: 0, moveAmt: 0, fly: 0,
      cool: 2, alive: true, engaged: false,
      atkPattern: 0, seed: Math.random() * 10, rig,
      deadT: 0
    };
    rig.group.position.copy(b.pos);
    scene.add(rig.group);
    b.shadow = G.makeShadow(D.radius * 3);
    scene.add(b.shadow);
    G.Enemies.bosses.push(b);
    return b;
  }

  B.damage = function (b, dmg, crit) {
    if (!b.alive) return;
    b.hp -= dmg;
    b.engaged = true;
    const ny = b.pos.y + (b.D.barH || 2.5) + (b.fly || 0) * 2.4;
    G.UI.dmgNum(b.pos.x, ny, b.pos.z, dmg, { crit });
    G.FX.burst(b.pos.x, b.pos.y + 1.5, b.pos.z, { n: 6, color: 0xffd24a, speed: 3.5, life: 0.3, size: 1.7 });
    if (b.hp <= 0) {
      b.hp = 0; b.alive = false;
      b.state = 'dead'; b.stateT = 0; b.deadT = 0;
      G.Audio.sfx('roar');
      G.Audio.sfx('enemyDie');
      G.Stats.addXP(b.D.xp);
      G.Inv.addGold(b.D.gold);
      G.FX.burst(b.pos.x, b.pos.y + 2, b.pos.z, { n: 60, color: 0xffaa44, speed: 8, life: 1.4, size: 5 });
      G.State.bossKilled[b.bossId] = true;
      G.events.emit('bossKilled', b.bossId);
      G.events.emit('shake', 0.8);
    }
  };

  /* Enemies.damage から分岐させる */
  const origDamage = G.Enemies.damage;
  G.Enemies.damage = function (e, dmg, crit) {
    if (e.isBoss) B.damage(e, dmg, crit);
    else origDamage(e, dmg, crit);
  };

  B.reset = function () {
    // プレイヤー死亡時: 生存ボスを原位置へ
    for (const b of G.Enemies.bosses) {
      if (!b.alive) continue;
      b.pos.set(b.D.x, G.World.heightAt(b.D.x, b.D.z), b.D.z);
      b.hp = b.maxHp;
      b.engaged = false;
      b.state = 'idle'; b.stateT = 0;
      b.fly = 0;
    }
    G.events.emit('bossDisengage');
  };

  function bossAttackMelee(b, dmg, reach, arc) {
    const p = G.Player;
    const dx = p.pos.x - b.pos.x, dz = p.pos.z - b.pos.z;
    const d = Math.hypot(dx, dz);
    if (d < reach && p.alive) {
      const ang = Math.atan2(dx, dz);
      if (Math.abs(G.angDiff(b.yaw, ang)) < (arc || 1.2)) {
        p.takeDamage(dmg, b.pos.x, b.pos.z);
      }
    }
  }

  B.update = function (b, dt) {
    b.stateT += dt;
    const p = G.Player;
    const D = b.D;

    if (b.state === 'dead') {
      b.deadT += dt;
      b.rig.pose({ state: 'dead', t: b.deadT, fly: 0, baseY: b.pos.y });
      b.rig.group.position.copy(b.pos);
      if (b.deadT > 5 && b.rig.group.parent) {
        scene.remove(b.rig.group);
        scene.remove(b.shadow);
      }
      return;
    }

    const dist = G.dist(p.pos.x, p.pos.z, b.pos.x, b.pos.z);
    const toP = Math.atan2(p.pos.x - b.pos.x, p.pos.z - b.pos.z);
    const distHome = G.dist(b.pos.x, b.pos.z, D.x, D.z);

    // 交戦開始/離脱
    if (!b.engaged && p.alive && dist < 26) {
      b.engaged = true;
      b.cool = b.bossId === 'dragon' ? 0.4 : 1.0;   // 開幕の間延び防止
      G.Audio.sfx('roar');
      G.events.emit('bossEngage', b);
    }
    if (b.engaged && (!p.alive || dist > D.arenaR + 30)) {
      b.engaged = false;
      b.hp = Math.min(b.maxHp, b.hp + b.maxHp * 0.5);
      G.events.emit('bossDisengage');
    }

    b.cool = Math.max(0, b.cool - dt);
    let mv = 0;
    const phase2 = b.hp < b.maxHp * 0.5;

    // スコルグ: 半減で子サソリ召喚
    if (b.bossId === 'scorpking' && phase2 && !b.summoned && b.engaged && b.alive) {
      b.summoned = true;
      G.Enemies.spawn('scorpion', b.pos.x + 3, b.pos.z + 2).aggro = true;
      G.Enemies.spawn('scorpion', b.pos.x - 3, b.pos.z - 2).aggro = true;
      G.Audio.sfx('roar');
      G.UI.toast('スコルグが仔サソリを呼んだ！');
    }

    if (!b.engaged) {
      // 帰還
      if (distHome > 3) {
        const back = Math.atan2(D.x - b.pos.x, D.z - b.pos.z);
        b.yaw = G.angLerp(b.yaw, back, G.damp(4, dt));
        G.Actors.groundMove(b, Math.sin(back) * D.speed * 0.6, Math.cos(back) * D.speed * 0.6, dt);
        mv = 0.6;
      }
      b.fly += (0 - b.fly) * G.damp(2, dt);
    } else if (b.state === 'windup') {
      b.yaw = G.angLerp(b.yaw, toP, G.damp(3.5, dt));
      const wd = b.windupDur || 0.8;
      if (b.stateT >= wd) {
        b.state = 'attack'; b.stateT = 0;
        execAttack(b);
      }
    } else if (b.state === 'attack' || b.state === 'breath' || b.state === 'throw') {
      if (b.state === 'breath') {
        // 火炎放射継続
        b.breathT = (b.breathT || 0) + dt;
        if (b.breathT > 0.08) {
          b.breathT = 0;
          const sy = b.pos.y + 3.2;
          const spread = (Math.random() - 0.5) * 0.5;
          const a = b.yaw + spread;
          G.Projectiles.spawn('fire', b.pos.x + Math.sin(b.yaw) * 3, sy, b.pos.z + Math.cos(b.yaw) * 3,
            b.pos.x + Math.sin(a) * 25, p.pos.y + 0.8, b.pos.z + Math.cos(a) * 25, 15, D.atk * 0.55);
        }
        b.yaw = G.angLerp(b.yaw, toP, G.damp(0.9, dt));
      }
      const dur = b.state === 'breath' ? 2.6 : 0.5;
      if (b.stateT > dur) {
        b.state = 'idle'; b.stateT = 0;
        b.cool = (phase2 ? 1.1 : 1.8) + Math.random();
      }
    } else if (b.state === 'charge') {
      // 突進 (フェンリル)
      G.Actors.groundMove(b, Math.sin(b.yaw) * D.speed * 2.1, Math.cos(b.yaw) * D.speed * 2.1, dt);
      mv = 1;
      if (!b.chargeHit) {
        const d = G.dist(p.pos.x, p.pos.z, b.pos.x, b.pos.z);
        if (d < b.radius + 1.1 && p.alive) {
          b.chargeHit = true;
          p.takeDamage(D.atk * 1.2, b.pos.x, b.pos.z);
        }
      }
      if (b.stateT > 0.85) {
        b.state = 'idle'; b.stateT = 0;
        b.cool = 1.4 + Math.random();
      }
    } else if (p.alive) {
      // 立ち回り
      b.yaw = G.angLerp(b.yaw, toP, G.damp(4, dt));
      const wantR = b.bossId === 'dragon' ? (b.fly > 0.5 ? 14 : 5) : (b.bossId === 'golem' ? 2.8 : 2.2);
      if (b.bossId === 'dragon') {
        // 竜: フェーズ2で時々飛ぶ
        if (phase2 && b.cool <= 0 && Math.random() < 0.005) b.flyTarget = 1 - (b.flyTarget || 0);
        b.fly += ((b.flyTarget || 0) - b.fly) * G.damp(1.2, dt);
      }
      if (dist > wantR + 1) {
        G.Actors.groundMove(b, Math.sin(toP) * D.speed, Math.cos(toP) * D.speed, dt);
        mv = 1;
      }
      if (b.cool <= 0) {
        chooseAttack(b, dist, phase2);
      }
    }

    b.moveAmt += (mv - b.moveAmt) * G.damp(6, dt);
    b.rig.group.position.copy(b.pos);
    b.rig.group.rotation.y = b.yaw;
    b.rig.pose({
      state: b.state, t: b.stateT, windup: b.windupDur || 0.8,
      moveAmt: b.moveAmt, seed: b.seed, fly: b.fly || 0, baseY: b.pos.y
    });
    G.Actors.updateShadow(b);
  };

  function chooseAttack(b, dist, phase2) {
    const id = b.bossId;
    if (id === 'fenrir') {
      if (dist > 6 && Math.random() < 0.55) {
        // 突進
        b.state = 'charge'; b.stateT = 0; b.chargeHit = false;
        G.Audio.sfx('roar');
      } else if (dist < 4) {
        b.state = 'windup'; b.stateT = 0; b.windupDur = phase2 ? 0.35 : 0.5;
        b.nextAtk = 'bite';
      } else {
        b.cool = 0.5;
      }
    } else if (id === 'golem') {
      if (dist < 5) {
        b.state = 'windup'; b.stateT = 0; b.windupDur = phase2 ? 0.7 : 0.95;
        b.nextAtk = 'slam';
      } else if (dist < 30) {
        b.state = 'windup'; b.stateT = 0; b.windupDur = 0.6;
        b.nextAtk = 'rock';
      }
    } else if (id === 'scorpking') {
      if (dist > 7 && Math.random() < 0.5) {
        b.state = 'charge'; b.stateT = 0; b.chargeHit = false;
        G.Audio.sfx('roar');
      } else if (dist < 4.5) {
        b.state = 'windup'; b.stateT = 0; b.windupDur = phase2 ? 0.35 : 0.5;
        b.nextAtk = 'bite';
      } else {
        b.cool = 0.5;
      }
    } else if (id === 'dragon') {
      if (b.fly > 0.5) {
        b.state = 'windup'; b.stateT = 0; b.windupDur = 0.5;
        b.nextAtk = 'fireball';
      } else if (dist < 7) {
        b.state = 'windup'; b.stateT = 0; b.windupDur = phase2 ? 0.4 : 0.6;
        b.nextAtk = 'bite';
      } else if (dist < 26) {
        b.state = 'windup'; b.stateT = 0; b.windupDur = 0.8;
        b.nextAtk = Math.random() < (phase2 ? 0.55 : 0.35) ? 'breath' : 'fireball';
      }
    }
  }

  function execAttack(b) {
    const D = b.D;
    const p = G.Player;
    const atk = b.nextAtk;
    if (atk === 'bite') {
      bossAttackMelee(b, D.atk, b.radius + 2.6, 1.1);
      G.Audio.sfx('swingHeavy');
    } else if (atk === 'slam') {
      // 地面叩きつけ: 円形 AoE
      G.Audio.sfx('explode');
      G.events.emit('shake', 0.6);
      const cx = b.pos.x + Math.sin(b.yaw) * 2.2, cz = b.pos.z + Math.cos(b.yaw) * 2.2;
      G.FX.burst(cx, b.pos.y + 0.3, cz, { n: 26, color: 0x9a8a6a, speed: 7, life: 0.8, size: 4 });
      const d = G.dist(p.pos.x, p.pos.z, cx, cz);
      if (d < 4.2 && p.alive) p.takeDamage(D.atk * 1.15, b.pos.x, b.pos.z);
    } else if (atk === 'rock') {
      b.state = 'throw'; b.stateT = 0;
      G.Projectiles.spawn('rock', b.pos.x, b.pos.y + 3.5, b.pos.z,
        p.pos.x, p.pos.y + 0.5, p.pos.z, 13, D.atk * 0.9);
      G.Audio.sfx('swingHeavy');
      return;
    } else if (atk === 'fireball') {
      G.Audio.sfx('fireball');
      const n = b.hp < b.maxHp * 0.5 ? 3 : 1;
      for (let i = 0; i < n; i++) {
        const off = (i - (n - 1) / 2) * 0.35;
        const a = Math.atan2(p.pos.x - b.pos.x, p.pos.z - b.pos.z) + off;
        const dd = G.dist(p.pos.x, p.pos.z, b.pos.x, b.pos.z);
        G.Projectiles.spawn('fire', b.pos.x + Math.sin(b.yaw) * 3, b.pos.y + 3.4, b.pos.z + Math.cos(b.yaw) * 3,
          b.pos.x + Math.sin(a) * dd, p.pos.y + 0.8, b.pos.z + Math.cos(a) * dd, 14, D.atk * 0.8);
      }
    } else if (atk === 'breath') {
      b.state = 'breath'; b.stateT = 0; b.breathT = 0;
      G.Audio.sfx('roar');
      return;
    }
  }
})();

/* ======================= NPC ======================= */
(function () {
  const N = G.NPCs = {};
  let scene;
  const list = [];
  N.list = list;

  const DEFS = [
    { id: 'elder',    name: '長老ハルド',   x: 2,   z: -17, conf: { skin: 0xd8b090, hair: 0xcccccc, cloth: 0x7a6a8a, cloth2: 0x4a4058 } },
    { id: 'healer',   name: '薬師リナ',     x: -15, z: -5,  conf: { skin: 0xe8c0a0, hair: 0x8a4a2a, cloth: 0x5a8a6a, cloth2: 0x3a5a48 } },
    { id: 'merchant', name: '商人モーガン', x: 13,  z: 6,   conf: { skin: 0xd8a880, hair: 0x3a2a1a, cloth: 0x8a6a3a, cloth2: 0x5a452a } },
    { id: 'hunter',   name: '狩人ガルド',   x: -3,  z: 17,  conf: { skin: 0xc89878, hair: 0x2a2a2a, cloth: 0x6a5a4a, cloth2: 0x4a3f33, weapon: 'bow' } },
    { id: 'smith',    name: '鍛冶屋ドヴァン', x: -6, z: 6,  conf: { skin: 0xc08868, hair: 0x6a3a1a, cloth: 0x55504a, cloth2: 0x38342e, weapon: 'club' } }
  ];

  N.init = function (sc) {
    scene = sc;
    for (const d of DEFS) {
      const rig = G.Rigs.humanoid(d.conf);
      const n = {
        id: d.id, name: d.name,
        pos: new THREE.Vector3(d.x, G.World.heightAt(d.x, d.z), d.z),
        home: { x: d.x, z: d.z },
        yaw: Math.random() * Math.PI * 2,
        vy: 0, radius: 0.4, rig,
        wanderT: Math.random() * 4, wanderA: 0, wandering: false,
        moveAmt: 0, seed: Math.random() * 10
      };
      rig.group.position.copy(n.pos);
      scene.add(rig.group);
      n.shadow = G.makeShadow(1.1);
      scene.add(n.shadow);
      list.push(n);
    }
  };

  N.update = function (dt) {
    const p = G.Player;
    for (const n of list) {
      const d2 = G.dist2(p.pos.x, p.pos.z, n.pos.x, n.pos.z);
      let mv = 0;
      if (d2 < 5 * 5) {
        // プレイヤーの方を向く
        const toP = Math.atan2(p.pos.x - n.pos.x, p.pos.z - n.pos.z);
        n.yaw = G.angLerp(n.yaw, toP, G.damp(6, dt));
      } else if (d2 < 90 * 90) {
        n.wanderT -= dt;
        if (n.wanderT <= 0) {
          n.wanderT = 3 + Math.random() * 5;
          n.wandering = Math.random() < 0.5;
          n.wanderA = Math.random() * Math.PI * 2;
        }
        if (n.wandering) {
          if (G.dist2(n.pos.x, n.pos.z, n.home.x, n.home.z) > 36) {
            n.wanderA = Math.atan2(n.home.x - n.pos.x, n.home.z - n.pos.z);
          }
          n.yaw = G.angLerp(n.yaw, n.wanderA, G.damp(3, dt));
          G.Actors.groundMove(n, Math.sin(n.yaw) * 1.1, Math.cos(n.yaw) * 1.1, dt);
          mv = 0.25;
        }
      }
      n.moveAmt += (mv - n.moveAmt) * G.damp(8, dt);
      n.rig.group.position.copy(n.pos);
      n.rig.group.rotation.y = n.yaw;
      n.rig.pose({ state: 'idle', t: 0, moveAmt: n.moveAmt, seed: n.seed, baseY: n.pos.y });
      G.Actors.updateShadow(n);
    }
  };
})();

/* ======================= 騎乗馬 ======================= */
(function () {
  const H = G.Horse = {};
  let scene, rig;
  H.pos = new THREE.Vector3(-16, 0, 28);
  H.yaw = 1.2;
  H.mounted = false;
  H.radius = 0.8;
  H.name = 'アッシュ';

  H.init = function (sc) {
    scene = sc;
    rig = G.Rigs.horse();
    H.pos.y = G.World.heightAt(H.pos.x, H.pos.z);
    rig.group.position.copy(H.pos);
    rig.group.rotation.y = H.yaw;
    scene.add(rig.group);
    H.shadow = G.makeShadow(2.4);
    scene.add(H.shadow);
  };

  H.mount = function () {
    if (H.mounted) return;
    H.mounted = true;
    G.Player.mounted = true;
    G.Player.target = null;
    G.Player.pos.set(H.pos.x, H.pos.y, H.pos.z);
    G.Player.yaw = H.yaw;
    G.Audio.sfx('jump');
    G.UI.toast('アッシュに乗った');
  };

  H.dismount = function () {
    if (!H.mounted) return;
    H.mounted = false;
    G.Player.mounted = false;
    const px = H.pos.x + Math.cos(H.yaw) * 1.3;
    const pz = H.pos.z - Math.sin(H.yaw) * 1.3;
    const c = G.World.collide(px, pz, 0.45);
    G.Player.pos.set(c.x, G.World.heightAt(c.x, c.z), c.z);
  };

  H.teleport = function (x, z) {
    if (H.mounted) return;
    H.pos.set(x, G.World.heightAt(x, z), z);
    if (rig) rig.group.position.copy(H.pos);
  };

  H.update = function (dt) {
    if (!rig) return;
    if (H.mounted) {
      H.pos.copy(G.Player.pos);
      H.yaw = G.Player.yaw;
    }
    rig.group.position.copy(H.pos);
    rig.group.rotation.y = H.yaw;
    rig.pose({
      state: 'idle',
      moveAmt: H.mounted ? G.Player.moveAmt : 0,
      baseY: H.pos.y, seed: 3
    });
    // 疾走時の砂埃
    if (H.mounted && G.Player.moveAmt > 0.5 && G.Player.grounded) {
      H.dustT = (H.dustT || 0) - dt;
      if (H.dustT <= 0) {
        H.dustT = 0.12;
        G.FX.burst(H.pos.x - Math.sin(H.yaw) * 1.2, H.pos.y + 0.25, H.pos.z - Math.cos(H.yaw) * 1.2,
          { n: 4, color: 0xc4b394, speed: 1.8, life: 0.65, size: 3.8, up: 0.8, gravity: 1 });
      }
    }
    G.Actors.updateShadow(H);
  };
})();

/* ======================= 飛翔体 ======================= */
(function () {
  const Pr = G.Projectiles = {};
  let scene;
  const list = [];

  Pr.init = function (sc) { scene = sc; };

  /* 共有アセット (毎発の geometry/material/texture 生成はリークかつ遅い) */
  let A = null;
  function assets() {
    if (A) return A;
    A = {
      arrowGeo: new THREE.BoxGeometry(0.05, 0.05, 0.7),
      arrowMat: new THREE.MeshLambertMaterial({ color: 0x8a6a3a }),
      fireGeo: new THREE.SphereGeometry(0.28, 6, 5),
      fireMat: new THREE.MeshBasicMaterial({ color: 0xffaa33 }),
      fireGlow: new THREE.SpriteMaterial({
        map: G.makeRadialTex(64, [[0, 'rgba(255,200,80,0.9)'], [1, 'rgba(255,100,0,0)']]),
        transparent: true, depthWrite: false, blending: THREE.AdditiveBlending
      }),
      rockGeo: new THREE.IcosahedronGeometry(0.55, 0),
      rockMat: new THREE.MeshLambertMaterial({ color: 0x8a8478 })
    };
    return A;
  }

  Pr.spawn = function (type, x, y, z, tx, ty, tz, speed, dmg) {
    // 重力弾は落下ぶんを狙点に上乗せする簡易弾道補正 (補正無しだと必ず手前に落ちる)
    const grav0 = type === 'rock' ? 6 : (type === 'arrow' ? 2 : 0);
    if (grav0 > 0) {
      const d = Math.hypot(tx - x, ty - y, tz - z);
      const t = d / speed;
      ty += 0.5 * grav0 * t * t;
    }
    const dir = new THREE.Vector3(tx - x, ty - y, tz - z).normalize();
    const a = assets();
    let mesh;
    if (type === 'arrow') {
      mesh = new THREE.Mesh(a.arrowGeo, a.arrowMat);
    } else if (type === 'fire') {
      mesh = new THREE.Group();
      const core = new THREE.Mesh(a.fireGeo, a.fireMat);
      core.scale.setScalar(1.4);
      const glow = new THREE.Sprite(a.fireGlow);
      glow.scale.set(2.6, 2.6, 1);
      mesh.add(core, glow);
    } else { // rock
      mesh = new THREE.Mesh(a.rockGeo, a.rockMat);
    }
    mesh.position.set(x, y, z);
    if (type === 'arrow') mesh.lookAt(tx, ty, tz);
    scene.add(mesh);
    list.push({
      type, mesh, dmg,
      pos: new THREE.Vector3(x, y, z),
      vel: dir.multiplyScalar(speed),
      life: 0, maxLife: 4,
      grav: type === 'rock' ? 6 : (type === 'arrow' ? 2 : 0)
    });
  };

  Pr.update = function (dt) {
    const p = G.Player;
    for (let i = list.length - 1; i >= 0; i--) {
      const pr = list[i];
      pr.life += dt;
      pr.vel.y -= pr.grav * dt;
      pr.pos.addScaledVector(pr.vel, dt);
      pr.mesh.position.copy(pr.pos);
      if (pr.type === 'fire') {
        G.FX.burst(pr.pos.x, pr.pos.y, pr.pos.z, { n: 1, color: 0xff8833, speed: 0.5, life: 0.35, size: 3, gravity: -2 });
      }
      let dead = false;
      // 地形
      const gh = G.World.heightAt(pr.pos.x, pr.pos.z);
      if (pr.pos.y <= gh) {
        dead = true;
        if (pr.type === 'fire' || pr.type === 'rock') {
          G.Audio.sfx('explode');
          if (pr.type === 'fire') G.Scorch.add(pr.pos.x, pr.pos.z);
          G.FX.burst(pr.pos.x, gh + 0.3, pr.pos.z, { n: 20, color: pr.type === 'fire' ? 0xff8833 : 0x9a8a6a, speed: 6, life: 0.6, size: 4 });
          // 爆風
          if (p.alive && G.dist2(p.pos.x, p.pos.z, pr.pos.x, pr.pos.z) < 2.8 * 2.8) {
            p.takeDamage(pr.dmg * 0.7, pr.pos.x, pr.pos.z);
          }
        }
      }
      // プレイヤー直撃
      if (!dead && p.alive) {
        const hitR = pr.type === 'fire' ? 1.1 : 0.8;
        const d2 = G.dist2(p.pos.x, p.pos.z, pr.pos.x, pr.pos.z);
        const dy = Math.abs((p.pos.y + 0.9) - pr.pos.y);
        if (d2 < hitR * hitR && dy < 1.4) {
          p.takeDamage(pr.dmg, pr.pos.x - pr.vel.x, pr.pos.z - pr.vel.z);
          dead = true;
          if (pr.type === 'fire') G.FX.burst(pr.pos.x, pr.pos.y, pr.pos.z, { n: 14, color: 0xff8833, speed: 4, life: 0.5 });
        }
      }
      if (pr.life > pr.maxLife) dead = true;
      if (dead) {
        scene.remove(pr.mesh);
        list.splice(i, 1);
      }
    }
  };

  Pr.clear = function () {
    for (const pr of list) scene.remove(pr.mesh);
    list.length = 0;
  };
})();

/* ======================= ドロップ品 ======================= */
(function () {
  const Pk = G.Pickups = {};
  let scene;
  const list = [];

  Pk.init = function (sc) { scene = sc; };

  const COLORS = { potion: 0xff6688, hipotion: 0xff4466, pelt: 0xaa8855, bone: 0xddddcc, magicstone: 0x66aaff, herb: 0x88ff99 };
  /* アイテム色ごとにマテリアル/テクスチャを共有 */
  let dropGeo = null, glowTex = null;
  const coreMats = {}, glowMats = {};
  function dropAssets(id) {
    if (!dropGeo) {
      dropGeo = new THREE.OctahedronGeometry(0.22, 0);
      glowTex = G.makeRadialTex(48, [[0, 'rgba(255,255,255,0.6)'], [1, 'rgba(255,255,255,0)']]);
    }
    const c = COLORS[id] || 0xffffff;
    if (!coreMats[id]) {
      coreMats[id] = new THREE.MeshLambertMaterial({ color: c, emissive: c, emissiveIntensity: 0.4 });
      glowMats[id] = new THREE.SpriteMaterial({
        map: glowTex, transparent: true, depthWrite: false,
        blending: THREE.AdditiveBlending, color: c
      });
    }
    return { core: coreMats[id], glow: glowMats[id] };
  }

  Pk.drop = function (id, x, z) {
    const y = G.World.heightAt(x, z);
    const am = dropAssets(id);
    const mesh = new THREE.Group();
    const core = new THREE.Mesh(dropGeo, am.core);
    const glow = new THREE.Sprite(am.glow);
    glow.scale.set(1, 1, 1);
    mesh.add(core, glow);
    mesh.position.set(x + (Math.random() - 0.5) * 1.2, y + 0.4, z + (Math.random() - 0.5) * 1.2);
    scene.add(mesh);
    list.push({ id, mesh, x: mesh.position.x, z: mesh.position.z, y: y, t: Math.random() * 5, life: 0 });
  };

  Pk.update = function (dt) {
    const p = G.Player;
    for (let i = list.length - 1; i >= 0; i--) {
      const it = list[i];
      it.t += dt; it.life += dt;
      it.mesh.position.y = it.y + 0.45 + Math.sin(it.t * 3) * 0.12;
      it.mesh.rotation.y += dt * 2;
      if (it.life > 60) { scene.remove(it.mesh); list.splice(i, 1); continue; }
      if (p.alive && G.dist2(p.pos.x, p.pos.z, it.x, it.z) < 1.6 * 1.6) {
        G.Inv.add(it.id, 1);
        G.UI.toast(G.Items.get(it.id).name + ' を拾った');
        G.Audio.sfx('pickup');
        G.events.emit('collect', { id: it.id });
        scene.remove(it.mesh);
        list.splice(i, 1);
      }
    }
  };
})();

/* ======================= インタラクト対象の探索 ======================= */
(function () {
  /* 戻り値: {kind, label, obj} | null */
  G.findInteractable = function () {
    const p = G.Player;
    if (!p.alive) return null;
    if (p.mounted) return { kind: 'dismount', label: '馬から降りる', obj: null };
    if (!p.grounded) return null;   // 空中 (滑空/跳躍) 中は調べられない
    const R2 = 2.6 * 2.6;
    // 馬
    if (G.Horse.pos && G.dist2(p.pos.x, p.pos.z, G.Horse.pos.x, G.Horse.pos.z) < 2.8 * 2.8) {
      return { kind: 'horse', label: 'アッシュに乗る', obj: null };
    }
    // NPC
    for (const n of G.NPCs.list) {
      if (G.dist2(p.pos.x, p.pos.z, n.pos.x, n.pos.z) < R2 + 1) {
        return { kind: 'npc', label: n.name + ' と話す', obj: n };
      }
    }
    // ポータル
    for (const pt of G.World.portals) {
      if (G.dist2(p.pos.x, p.pos.z, pt.x, pt.z) < 4.2 * 4.2) {
        return { kind: 'portal', label: pt.label, obj: pt };
      }
    }
    // 祠
    for (const s of G.World.shrines) {
      if (G.dist2(p.pos.x, p.pos.z, s.x, s.z) < 3.2 * 3.2) {
        const disc = G.State.shrines[s.id];
        return { kind: 'shrine', label: disc ? s.name + ' で休む' : '祠を灯す', obj: s };
      }
    }
    // 宝箱
    for (const c of G.World.chests) {
      if (G.State.openedChests[c.id]) continue;
      if (G.dist2(p.pos.x, p.pos.z, c.x, c.z) < R2) {
        return { kind: 'chest', label: '宝箱を開ける', obj: c };
      }
    }
    // 薬草
    for (const h of G.World.herbs) {
      if (h.taken || G.State.herbs[h.id]) continue;
      if (G.dist2(p.pos.x, p.pos.z, h.x, h.z) < R2) {
        return { kind: 'herb', label: '月光草を摘む', obj: h };
      }
    }
    return null;
  };
})();
