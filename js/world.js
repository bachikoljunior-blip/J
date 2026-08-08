/* =============================================================================
 * ELDRIA — world.js
 * オープンワールド生成: チャンク地形 / バイオーム / 水 / 空・昼夜・天候 /
 * 植生インスタンシング / ランドマーク(村・祠・遺跡・ボス闘技場) / 衝突
 * ========================================================================== */
'use strict';
(function () {
  const W = G.World = {};
  const CHUNK = 64;          // チャンク一辺 (m)
  const SEG = 24;            // チャンク分割数
  const WATER_Y = 0;         // 海面
  W.CHUNK = CHUNK;
  W.WATER_Y = WATER_Y;
  W.SEED = 20260808;

  /* ======================= テクスチャ生成ヘルパ ======================= */
  G.makeRadialTex = function (size, stops) {
    const c = document.createElement('canvas');
    c.width = c.height = size;
    const g = c.getContext('2d');
    const grad = g.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
    for (const s of stops) grad.addColorStop(s[0], s[1]);
    g.fillStyle = grad;
    g.fillRect(0, 0, size, size);
    const t = new THREE.CanvasTexture(c);
    return t;
  };

  /* ======================= ランドマーク定義 ======================= */
  /* y: その地点の固定標高。r: 完全平坦半径, R: ブレンド終端半径 */
  W.landmarks = [
    { id: 'village',    x: 0,    z: 0,    y: 6,  r: 52, R: 95,  name: 'ミストヴェイル村' },
    { id: 'arena_wolf', x: -430, z: -140, y: 9,  r: 34, R: 70,  name: '静寂の森の空き地' },
    { id: 'arena_golem',x: 430,  z: -80,  y: 12, r: 36, R: 75,  name: '崩れた王都の遺跡' },
    { id: 'arena_drake',x: -40,  z: -640, y: 74, r: 40, R: 110, name: '竜の頂' },
    { id: 'ruin_south', x: 150,  z: 430,  y: 8,  r: 24, R: 55,  name: '南の廃墟' },
    { id: 'shrine2',    x: -380, z: -60,  y: 9,  r: 14, R: 40,  name: null },
    { id: 'shrine3',    x: -120, z: -430, y: 30, r: 14, R: 45,  name: null },
    { id: 'shrine4',    x: 350,  z: 320,  y: 7,  r: 14, R: 40,  name: null },
    { id: 'shrine5',    x: 260,  z: -180, y: 8,  r: 14, R: 40,  name: null },
    { id: 'arena_scorp',x: 390,  z: 380,  y: 8,  r: 26, R: 60,  name: '砂丘の廃墟' },
    { id: 'cave_mouth', x: -260, z: -360, y: 26, r: 12, R: 34,  name: null },
    { id: 'tower1',     x: -200, z: 200,  y: 16, r: 10, R: 35,  name: null },
    { id: 'tower2',     x: 180,  z: -320, y: 22, r: 10, R: 35,  name: null }
  ];

  /* 祠 (ファストトラベル地点)。村内の始まりの祠 + 各地 */
  W.shrines = [
    { id: 'shrine1', x: 14,   z: 20,   name: '始まりの祠' },
    { id: 'shrine2', x: -380, z: -60,  name: '森の祠' },
    { id: 'shrine3', x: -120, z: -430, name: '山麓の祠' },
    { id: 'shrine4', x: 350,  z: 320,  name: '砂丘の祠' },
    { id: 'shrine5', x: 260,  z: -180, name: '湖畔の祠' }
  ];

  /* ポータル (洞窟の出入り) */
  W.portals = [
    { x: -260, z: -360, tx: 1205, tz: 1166, label: '風哭の洞窟に入る' },
    { x: 1205, z: 1162, tx: -260, tz: -355, label: '洞窟から出る' }
  ];

  /* 宝箱: id / 位置 / 中身 (systems.js の Item id) */
  W.chests = [
    { id: 'c_vil',    x: -26,  z: 16,   items: { potion: 2 },            gold: 30 },
    { id: 'c_forest', x: -350, z: -180, items: { potion: 2, herb: 1 },   gold: 60 },
    { id: 'c_ruinE1', x: 452,  z: -60,  items: { sword_knight: 1 },     gold: 80 },
    { id: 'c_ruinE2', x: 408,  z: -102, items: { hipotion: 2 },         gold: 50 },
    { id: 'c_south',  x: 158,  z: 444,  items: { cargo: 1 },            gold: 40 },
    { id: 'c_desert', x: 380,  z: 290,  items: { armor_hunter: 1 },     gold: 90 },
    { id: 'c_lake',   x: 240,  z: -196, items: { hipotion: 1, herb: 2 }, gold: 70 },
    { id: 'c_mount',  x: -140, z: -448, items: { axe_ruin: 1 },         gold: 120 },
    { id: 'c_peak',   x: -70,  z: -616, items: { sword_dragon: 1 },     gold: 200 },
    { id: 'c_tower',  x: -200, z: 194,  items: { hipotion: 2 },         gold: 60 },
    { id: 'm_west',   x: -320, z: 120,  items: {}, gold: 0, mimic: true },
    { id: 'm_east',   x: 310,  z: -260, items: {}, gold: 0, mimic: true },
    { id: 'c_cave1',  x: 1205, z: 1236, items: { sword_wind: 1 },       gold: 150 },
    { id: 'c_cave2',  x: 1188, z: 1218, items: { hipotion: 2, magicstone: 3 }, gold: 100 }
  ];

  /* ======================= 高さ関数 ======================= */
  const S = 1 / 900; // 大陸スケール
  function baseHeight(x, z) {
    const r = Math.sqrt(x * x + z * z);
    const falloff = 1 - G.smoothstep(650, 980, r);       // 外縁 → 海
    if (falloff <= 0) return -12 + G.noise2(x * 0.01, z * 0.01) * 1.5;

    // なだらかな平原
    let h = 6 + G.fbm(x * 0.004 + 10, z * 0.004 + 10, 4) * 9
              + G.fbm(x * 0.02, z * 0.02, 2) * 1.6;

    // 丘陵
    const hills = Math.pow(Math.max(0, G.fbm(x * 0.0065 + 40, z * 0.0065 + 40, 3)), 2) * 26;
    h += hills;

    // 北の山脈 (z が小さいほど北)
    const mMask = G.smoothstep(-260, -520, z);
    if (mMask > 0) {
      const ridge = G.ridge(x * 0.0028 + 7, z * 0.0028 + 7, 4);
      h += mMask * ridge * 95;
    }

    // 南東の砂漠は低くなだらかに + 砂丘の畝
    const dMask = G.smoothstep(120, 320, x) * G.smoothstep(80, 260, z);
    if (dMask > 0) {
      const dune = 5 + Math.sin(x * 0.05 + G.noise2(x * 0.01, z * 0.01) * 3) * 1.4
                     + G.fbm(x * 0.008, z * 0.008, 2) * 3;
      h = G.lerp(h, dune, dMask * 0.85);
    }

    // 湖 (東寄り): くぼみ
    const lake = 1 - G.smoothstep(55, 110, G.dist(x, z, 265, -235));
    h = G.lerp(h, -5, lake * 0.9);

    // 大陸縁で海に沈む
    h = G.lerp(-12, h, falloff);
    return h;
  }

  /* 風哭の洞窟 (別空間: ワールド北東の海上に隔離配置) */
  W.CAVE = { x0: 1150, x1: 1260, z0: 1150, z1: 1260, cx: 1205, cz: 1205 };
  W.inCaveRegion = (x, z) => x > W.CAVE.x0 && x < W.CAVE.x1 && z > W.CAVE.z0 && z < W.CAVE.z1;
  function caveHeight(x, z) {
    const r = G.dist(x, z, W.CAVE.cx, W.CAVE.cz);
    let h = 60 + G.noise2(x * 0.15, z * 0.15) * 0.9;
    h += G.smoothstep(36, 50, r) * 40;   // 外周は壁
    return h;
  }

  W.heightAt = function (x, z) {
    if (W.inCaveRegion(x, z)) return caveHeight(x, z);
    let h = baseHeight(x, z);
    // ランドマーク平坦化
    const lm = W.landmarks;
    for (let i = 0; i < lm.length; i++) {
      const L = lm[i];
      const dx = x - L.x, dz = z - L.z;
      const d2 = dx * dx + dz * dz;
      if (d2 > L.R * L.R) continue;
      const d = Math.sqrt(d2);
      const t = G.smoothstep(L.r, L.R, d); // 0=中心 1=外
      h = G.lerp(L.y, h, t);
    }
    return h;
  };

  W.normalAt = function (x, z) {
    const e = 0.9;
    const hx = W.heightAt(x - e, z) - W.heightAt(x + e, z);
    const hz = W.heightAt(x, z - e) - W.heightAt(x, z + e);
    const n = new THREE.Vector3(hx, 2 * e, hz);
    return n.normalize();
  };

  /* 法線の Y 成分のみ (アロケーション無し)。1=平坦 */
  W.slopeYAt = function (x, z) {
    const e = 0.9;
    const hx = W.heightAt(x - e, z) - W.heightAt(x + e, z);
    const hz = W.heightAt(x, z - e) - W.heightAt(x, z + e);
    return (2 * e) / Math.sqrt(hx * hx + 4 * e * e + hz * hz);
  };

  W.isDeepWater = function (x, z) {
    return W.heightAt(x, z) < WATER_Y - 1.1;
  };

  /* ======================= バイオーム ======================= */
  /* 'grass' | 'forest' | 'desert' | 'rock' | 'snow' | 'beach' */
  W.biomeAt = function (x, z, h) {
    if (W.inCaveRegion(x, z)) return 'rock';
    if (h === undefined) h = W.heightAt(x, z);
    if (h < WATER_Y + 1.1) return 'beach';
    const temp = 0.55 + z * 0.00075 - h * 0.004;
    const moist = G.fbm(x * 0.0028 + 200, z * 0.0028 + 200, 3) * 0.5 + 0.5;
    if (h > 58 || (temp < 0.1 && h > 24)) return 'snow';
    if (h > 40) return 'rock';
    const dMask = G.smoothstep(120, 320, x) * G.smoothstep(80, 260, z);
    if (dMask > 0.5 && h < 22) return 'desert';
    if (moist > 0.52 && temp > 0.15 && temp < 0.8) return 'forest';
    return 'grass';
  };

  const BIOME_COL = {
    grass:  new THREE.Color(0x6ba14b),
    grass2: new THREE.Color(0x81ab55),
    forest: new THREE.Color(0x4c8a3e),
    desert: new THREE.Color(0xd9c37e),
    rock:   new THREE.Color(0x8b8b90),
    snow:   new THREE.Color(0xeef2f6),
    beach:  new THREE.Color(0xdccf98),
    under:  new THREE.Color(0x958d5e),
    forest2: new THREE.Color(0x39642e)
  };

  const _c = new THREE.Color();
  const PATH_COL = new THREE.Color(0xb59f74);
  /* 点と線分の距離^2 */
  function segDist2(px, pz, ax, az, bx, bz) {
    const dx = bx - ax, dz = bz - az;
    const t = G.clamp(((px - ax) * dx + (pz - az) * dz) / (dx * dx + dz * dz), 0, 1);
    const cx = ax + dx * t, cz = az + dz * t;
    return G.dist2(px, pz, cx, cz);
  }
  /* 村の土の道 */
  const PATHS = [
    [6, 34, 0, 8], [0, 8, 2, -14], [0, 8, 12, 18], [0, 8, 11, 5], [0, 8, -4, 6]
  ];
  function pathBlend(x, z) {
    if (x < -35 || x > 40 || z < -30 || z > 45) return 0;
    let best = 1e9;
    for (const [ax, az, bx, bz] of PATHS) {
      const d2 = segDist2(x, z, ax, az, bx, bz);
      if (d2 < best) best = d2;
    }
    return 1 - G.smoothstep(1.1, 2.6, Math.sqrt(best));
  }
  /* ny: 事前計算済みの法線Y (省略時は計算する) */
  const CAVE_FLOOR = new THREE.Color(0x646b7c);
  const CAVE_FLOOR2 = new THREE.Color(0x4a5265);
  const FROST_COL = new THREE.Color(0xc8dce6);
  const CHAR_COL = new THREE.Color(0x2e2824);
  const _dirtCol = new THREE.Color(0x6a5844);
  function groundColor(x, z, h, out, ny) {
    if (W.inCaveRegion(x, z)) {
      // 洞窟の床: 青灰のまだら
      const m = G.fbm(x * 0.11, z * 0.11, 2) * 0.5 + 0.5;
      out.copy(CAVE_FLOOR).lerp(CAVE_FLOOR2, m);
      return out;
    }
    // バイオーム境界は座標を揺らしてディザ (定規で引いた直線帯の解消)
    const jx = G.noise2(x * 0.09 + 31, z * 0.09) * 9;
    const jz = G.noise2(x * 0.09, z * 0.09 + 77) * 9;
    const b = W.biomeAt(x + jx, z + jz, h);
    out.copy(BIOME_COL[b] || BIOME_COL.grass);
    const pb = pathBlend(x, z);
    if (pb > 0) out.lerp(PATH_COL, pb * 0.85);
    // 雪面の起伏まだら
    if (b === 'snow') {
      out.multiplyScalar(0.88 + (G.fbm(x * 0.05, z * 0.05, 2) * 0.5 + 0.5) * 0.16);
    }
    // 岩肌の縞ムラ+土の帯 (滑空時の眼下が無地のスメアにならないように)
    if (b === 'rock') {
      out.multiplyScalar(0.68 + (G.fbm(x * 0.07, z * 0.07, 2) * 0.5 + 0.5) * 0.52);
      const dirt = G.fbm(x * 0.035 + 17, z * 0.035, 2) * 0.5 + 0.5;
      out.lerp(_dirtCol, G.smoothstep(0.6, 0.85, dirt) * 0.4);
    }
    if (b === 'grass') {
      const t = G.fbm(x * 0.012 + 55, z * 0.012 + 55, 2) * 0.5 + 0.5;
      out.lerp(BIOME_COL.grass2, t * 0.8);
    }
    // 森の林床は苔色のむらで単色ベタ塗りを避ける
    if (b === 'forest') {
      const t = G.fbm(x * 0.03 + 9, z * 0.03, 2) * 0.5 + 0.5;
      out.lerp(BIOME_COL.forest2, t * 0.75);
    }
    // 斜面は岩肌に
    if (ny === undefined) ny = W.slopeYAt(x, z);
    const slope = 1 - ny; // 0=平坦
    if (b !== 'desert' && b !== 'snow') {
      out.lerp(BIOME_COL.rock, G.smoothstep(0.22, 0.5, slope));
    }
    if (b === 'snow') {
      out.lerp(BIOME_COL.rock, G.smoothstep(0.35, 0.65, slope));
    }
    // 水中は砂色へ
    if (h < WATER_Y + 0.4) {
      out.lerp(BIOME_COL.under, G.smoothstep(WATER_Y + 0.4, WATER_Y - 2.5, h));
    }
    // フェンリルの凍土アリーナ (バイオームまだらの後に適用しないと緑に戻される)
    const fd = G.dist2(x, z, -430, -140);
    if (fd < 38 * 38) {
      out.lerp(FROST_COL, (1 - G.smoothstep(26, 38, Math.sqrt(fd))) * 0.88);
    }
    // 竜の頂の焦土 (中心ほど濃く、ひび割れ状の明暗ムラ)
    const dd = G.dist2(x, z, -40, -640);
    if (dd < 34 * 34) {
      const dr = Math.sqrt(dd);
      out.lerp(CHAR_COL, (1 - G.smoothstep(18, 34, dr)) * 0.85);
      const crack = G.fbm(x * 0.22, z * 0.22, 2);
      out.multiplyScalar(0.8 + (crack * 0.5 + 0.5) * 0.4);
      // 中心付近は残り火の熱がわずかに透ける
      if (dr < 14) out.r += (1 - dr / 14) * 0.05;
    }
    // 高度の微妙な明暗
    const shade = 0.92 + G.hash2((x * 7) | 0, (z * 7) | 0) * 0.08;
    out.multiplyScalar(shade);
    return out;
  }
  W.minimapColor = function (x, z) {
    const h = W.heightAt(x, z);
    if (h < WATER_Y - 0.3) {
      const d = G.clamp((WATER_Y - h) / 10, 0, 1);
      _c.setRGB(0.18 - d * 0.08, 0.38 - d * 0.14, 0.55 - d * 0.12);
      return _c;
    }
    groundColor(x, z, h, _c, 1);   // 地図は斜面の陰影を省略 (高速化)
    const l = G.clamp(0.75 + h * 0.006, 0.7, 1.25);
    _c.multiplyScalar(l);
    return _c;
  };

  /* ======================= ジオメトリ結合ヘルパ ======================= */
  /* parts: [{geo, m(Matrix4|null), color(hex)}] → 頂点色付き BufferGeometry */
  G.mergeGeo = function (parts) {
    const pos = [], nor = [], col = [];
    const c = new THREE.Color();
    const nm = new THREE.Matrix3();
    for (const p of parts) {
      let g = p.geo.index ? p.geo.toNonIndexed() : p.geo;
      const pa = g.attributes.position.array;
      const na = g.attributes.normal.array;
      c.set(p.color);
      const v = new THREE.Vector3(), n = new THREE.Vector3();
      if (p.m) nm.getNormalMatrix(p.m);
      for (let i = 0; i < pa.length; i += 3) {
        v.set(pa[i], pa[i + 1], pa[i + 2]);
        n.set(na[i], na[i + 1], na[i + 2]);
        if (p.m) { v.applyMatrix4(p.m); n.applyMatrix3(nm).normalize(); }
        pos.push(v.x, v.y, v.z);
        nor.push(n.x, n.y, n.z);
        col.push(c.r, c.g, c.b);
      }
      if (g !== p.geo) g.dispose();
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    geo.setAttribute('normal', new THREE.Float32BufferAttribute(nor, 3));
    geo.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
    return geo;
  };
  const M4 = (x, y, z, ry, s, sy) => {
    const m = new THREE.Matrix4();
    m.makeRotationY(ry || 0);
    m.scale(new THREE.Vector3(s || 1, sy || s || 1, s || 1));
    m.setPosition(x || 0, y || 0, z || 0);
    return m;
  };

  /* ======================= 植生ジオメトリ ======================= */
  let treeGeos = null;
  function buildTreeGeos() {
    const pineTrunk = new THREE.CylinderGeometry(0.22, 0.34, 2.2, 5);
    const pineC1 = new THREE.ConeGeometry(1.7, 3.2, 6);
    const pineC2 = new THREE.ConeGeometry(1.2, 2.6, 6);
    const pine = G.mergeGeo([
      { geo: pineTrunk, m: M4(0, 1.1, 0), color: 0x6b4a2f },
      { geo: pineC1, m: M4(0, 3.4, 0), color: 0x39683a },
      { geo: pineC2, m: M4(0, 5.2, 0), color: 0x447a42 }
    ]);
    pineTrunk.dispose(); pineC1.dispose(); pineC2.dispose();

    const oakTrunk = new THREE.CylinderGeometry(0.3, 0.45, 2.6, 5);
    const oakF1 = new THREE.IcosahedronGeometry(2.0, 0);
    const oakF2 = new THREE.IcosahedronGeometry(1.4, 0);
    const oak = G.mergeGeo([
      { geo: oakTrunk, m: M4(0, 1.3, 0), color: 0x74533a },
      { geo: oakF1, m: M4(0, 4.0, 0), color: 0x5b9143 },
      { geo: oakF2, m: M4(1.1, 3.2, 0.5), color: 0x6da24d }
    ]);
    oakTrunk.dispose(); oakF1.dispose(); oakF2.dispose();

    const rockG = new THREE.IcosahedronGeometry(1, 0);
    const rock = G.mergeGeo([{ geo: rockG, m: M4(0, 0.35, 0, 0.5, 1, 0.72), color: 0x8d8d94 }]);
    rockG.dispose();

    const cacBody = new THREE.CylinderGeometry(0.42, 0.5, 3.0, 6);
    const cacArm = new THREE.CylinderGeometry(0.26, 0.3, 1.3, 6);
    const cactus = G.mergeGeo([
      { geo: cacBody, m: M4(0, 1.5, 0), color: 0x5f8f4a },
      { geo: cacArm, m: M4(0.62, 1.9, 0, 0, 1), color: 0x69994f },
      { geo: cacArm, m: M4(-0.62, 1.4, 0, 0, 1), color: 0x69994f }
    ]);
    cacBody.dispose(); cacArm.dispose();

    const deadT = new THREE.CylinderGeometry(0.16, 0.3, 3.4, 5);
    const deadB = new THREE.CylinderGeometry(0.08, 0.14, 1.6, 4);
    const dead = G.mergeGeo([
      { geo: deadT, m: M4(0, 1.7, 0), color: 0x5c5148 },
      { geo: deadB, m: M4(0.5, 3.0, 0, 0.9, 1), color: 0x5c5148 }
    ]);
    deadT.dispose(); deadB.dispose();

    treeGeos = { pine, oak, rock, cactus, dead };
  }

  const treeMat = () => new THREE.MeshLambertMaterial({ vertexColors: true });
  let sharedTreeMat = null;

  /* ======================= 草シェーダ ======================= */
  let grassGeo = null, grassMat = null;
  function buildGrassAssets() {
    // 2枚の交差する細三角形ブレード
    const pos = [], col = [];
    const blade = (rot) => {
      const c = Math.cos(rot), s = Math.sin(rot);
      const w = 0.13, hgt = 0.85;
      // 三角形: 根本2点 + 先端
      const v = [
        [-w, 0, 0], [w, 0, 0], [0, hgt, 0],
        [w, 0, 0], [-w, 0, 0], [0, hgt, 0]  // 裏面
      ];
      for (const p of v) {
        pos.push(p[0] * c - p[2] * s, p[1], p[0] * s + p[2] * c);
        const t = p[1] / hgt;
        col.push(0.40 + t * 0.32, 0.62 + t * 0.30, 0.26 + t * 0.16);
      }
    };
    blade(0); blade(Math.PI / 2);
    grassGeo = new THREE.BufferGeometry();
    grassGeo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    grassGeo.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));

    grassMat = new THREE.ShaderMaterial({
      uniforms: {
        uTime: { value: 0 },
        uFogColor: { value: new THREE.Color(0xbccfdd) },
        uFogNear: { value: 60 },
        uFogFar: { value: 260 },
        uLight: { value: 1.0 }
      },
      vertexShader: `
        attribute vec3 color;
        varying vec3 vColor;
        varying float vDist;
        uniform float uTime;
        void main(){
          vec4 wp = instanceMatrix * vec4(position, 1.0);
          float k = step(0.25, position.y);
          float sway = sin(uTime * 1.8 + wp.x * 0.35 + wp.z * 0.45) * 0.14 * k;
          wp.x += sway; wp.z += sway * 0.55;
          vColor = color;
          vec4 mv = viewMatrix * wp;
          vDist = -mv.z;
          gl_Position = projectionMatrix * mv;
        }`,
      fragmentShader: `
        varying vec3 vColor;
        varying float vDist;
        uniform vec3 uFogColor;
        uniform float uFogNear, uFogFar, uLight;
        void main(){
          float f = smoothstep(uFogNear, uFogFar, vDist);
          vec3 c = mix(vColor * uLight, uFogColor, f);
          gl_FragColor = vec4(c, 1.0);
        }`,
      side: THREE.DoubleSide
    });
  }

  /* ======================= チャンク管理 ======================= */
  const chunks = new Map();     // "cx,cz" -> chunk
  let scene = null;
  const buildQueue = [];

  function chunkKey(cx, cz) { return cx + ',' + cz; }

  function decorDensity(biome) {
    switch (biome) {
      case 'forest': return { pine: 24, oak: 15, rock: 2, dead: 3, grass: 1.0 };
      case 'grass':  return { pine: 1, oak: 2, rock: 2, grass: 1.0 };
      case 'desert': return { cactus: 4, rock: 3, grass: 0 };
      case 'rock':   return { rock: 5, dead: 2, grass: 0.15 };
      case 'snow':   return { pine: 3, rock: 3, grass: 0 };
      case 'beach':  return { rock: 1, grass: 0.1 };
      default: return { grass: 0.4 };
    }
  }

  /* ランドマーク近傍には木を生やさない */
  function nearLandmark(x, z, margin) {
    for (const L of W.landmarks) {
      const rr = L.r + (margin || 4);
      if (G.dist2(x, z, L.x, L.z) < rr * rr) return true;
    }
    return false;
  }
  W.nearLandmark = nearLandmark;

  function buildChunk(cx, cz) {
    const key = chunkKey(cx, cz);
    if (chunks.has(key)) return chunks.get(key);
    const x0 = cx * CHUNK, z0 = cz * CHUNK;

    /* --- 地形メッシュ (高さを一度だけグリッドで求め、法線もそこから算出) --- */
    const vertsW = SEG + 1;
    const positions = new Float32Array(vertsW * vertsW * 3);
    const colors = new Float32Array(vertsW * vertsW * 3);
    const normals = new Float32Array(vertsW * vertsW * 3);
    const step = CHUNK / SEG;
    const col = new THREE.Color();
    // 法線の中央差分用に 1 頂点ぶん外側まで高さをサンプル
    const gw = SEG + 3;
    const H = new Float32Array(gw * gw);
    for (let j = 0; j < gw; j++) {
      for (let i = 0; i < gw; i++) {
        H[j * gw + i] = W.heightAt(x0 + (i - 1) * step, z0 + (j - 1) * step);
      }
    }
    let vi = 0;
    const inv = 1;
    for (let j = 0; j <= SEG; j++) {
      for (let i = 0; i <= SEG; i++) {
        const x = x0 + i * step, z = z0 + j * step;
        const gi = (j + 1) * gw + (i + 1);
        const h = H[gi];
        positions[vi] = x; positions[vi + 1] = h; positions[vi + 2] = z;
        // 中央差分による法線
        let nx = H[gi - 1] - H[gi + 1];
        let nyv = 2 * step;
        let nz = H[gi - gw] - H[gi + gw];
        const nl = 1 / Math.sqrt(nx * nx + nyv * nyv + nz * nz);
        nx *= nl; nyv *= nl; nz *= nl;
        normals[vi] = nx; normals[vi + 1] = nyv; normals[vi + 2] = nz;
        groundColor(x, z, h, col, nyv);
        colors[vi] = col.r; colors[vi + 1] = col.g; colors[vi + 2] = col.b;
        vi += 3;
      }
    }
    const indices = [];
    for (let j = 0; j < SEG; j++) {
      for (let i = 0; i < SEG; i++) {
        const a = j * vertsW + i, b = a + 1, c = a + vertsW, d = c + 1;
        indices.push(a, c, b, b, c, d);
      }
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geo.setAttribute('normal', new THREE.BufferAttribute(normals, 3));
    geo.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    geo.setIndex(indices);
    const mesh = new THREE.Mesh(geo, terrainMat);
    mesh.frustumCulled = true;
    mesh.receiveShadow = true;
    scene.add(mesh);

    const chunk = {
      cx, cz, key, mesh,
      trees: [], grassMesh: null,
      colliders: [],           // {x,z,r}
      spawns: []               // {x,z,type,alive,deadUntil,eid}
    };

    /* --- 植生 (決定的配置) --- */
    const rnd = G.srand((cx * 73856093) ^ (cz * 19349663) ^ W.SEED);
    const centerBiome = W.biomeAt(x0 + CHUNK / 2, z0 + CHUNK / 2);
    const counts = {};
    // チャンク内の 4 サンプル点でバイオーム混合を見る
    for (let s = 0; s < 4; s++) {
      const bx = x0 + (s % 2 + 0.5) * CHUNK / 2, bz = z0 + (((s / 2) | 0) + 0.5) * CHUNK / 2;
      const d = decorDensity(W.biomeAt(bx, bz));
      for (const k in d) counts[k] = Math.max(counts[k] || 0, d[k]);
    }
    for (const type of ['pine', 'oak', 'rock', 'cactus', 'dead']) {
      const n = (counts[type] || 0);
      if (!n) continue;
      const placed = [];
      for (let i = 0; i < n; i++) {
        const x = x0 + rnd() * CHUNK, z = z0 + rnd() * CHUNK;
        const h = W.heightAt(x, z);
        if (h < WATER_Y + 0.8) continue;
        if (nearLandmark(x, z, 5)) continue;
        const b = W.biomeAt(x, z, h);
        if ((type === 'pine' || type === 'oak') && (b === 'desert' || b === 'beach')) continue;
        if (type === 'cactus' && b !== 'desert') continue;
        if (W.slopeYAt(x, z) < 0.72 && type !== 'rock') continue; // 急斜面は岩のみ
        const sc = 0.75 + rnd() * 0.7;
        placed.push({ x, z, h, ry: rnd() * Math.PI * 2, s: sc });
        if (type !== 'rock' && type !== 'dead') {
          chunk.colliders.push({ x, z, r: 0.55 * sc + 0.15 });
        } else if (type === 'rock') {
          chunk.colliders.push({ x, z, r: 0.9 * sc });
        }
      }
      if (placed.length) {
        const im = new THREE.InstancedMesh(treeGeos[type], sharedTreeMat, placed.length);
        const m = new THREE.Matrix4();
        for (let i = 0; i < placed.length; i++) {
          const p = placed[i];
          m.makeRotationY(p.ry);
          const s = p.s * (type === 'rock' ? 0.8 + rnd() * 1.6 : 1);
          m.scale(new THREE.Vector3(s, s * (0.9 + rnd() * 0.25), s));
          m.setPosition(p.x, p.h - 0.08, p.z);
          im.setMatrixAt(i, m);
        }
        im.instanceMatrix.needsUpdate = true;
        // r150 の InstancedMesh は境界球がベースジオメトリ基準 (原点) のため
        // 視錐台カリングすると植生が丸ごと誤って消える。チャンク単位で管理して
        // いるのでカリングは切る。
        im.frustumCulled = false;
        im.castShadow = true;
        scene.add(im);
        chunk.trees.push(im);
      }
    }

    /* --- 敵スポーン地点 (決定的) --- */
    const spawnRnd = G.srand((cx * 83492791) ^ (cz * 297121507) ^ 999);
    const spawnCount = centerBiome === 'forest' ? 3 : centerBiome === 'rock' || centerBiome === 'snow' ? 2 :
                       centerBiome === 'desert' ? 2 : centerBiome === 'grass' ? 2 : 0;
    for (let i = 0; i < spawnCount; i++) {
      const x = x0 + spawnRnd() * CHUNK, z = z0 + spawnRnd() * CHUNK;
      const h = W.heightAt(x, z);
      if (h < WATER_Y + 1) continue;
      if (nearLandmark(x, z, 26)) continue;      // 村・祠の近くは安全地帯
      if (G.dist2(x, z, 0, 0) < 42 * 42) continue;  // 村中心はさらに広く禁止
      const b = W.biomeAt(x, z, h);
      let type;
      if (b === 'forest') type = spawnRnd() < 0.6 ? 'wolf' : 'goblin';
      else if (b === 'desert') type = spawnRnd() < 0.5 ? 'scorpion' : 'goblin';
      else if (b === 'rock' || b === 'snow') {
        const r = spawnRnd();
        type = r < 0.4 ? 'golemling' : r < 0.75 ? 'skeleton' : 'fireimp';
      }
      else {
        const r = spawnRnd();
        type = r < 0.4 ? 'goblin' : r < 0.8 ? 'wolf' : 'bandit';
      }
      chunk.spawns.push({ x, z, type, alive: false, deadUntil: 0, eid: key + ':' + i });
    }

    chunks.set(key, chunk);
    return chunk;
  }

  function addGrass(chunk) {
    if (chunk.grassMesh || !grassGeo) return;
    const x0 = chunk.cx * CHUNK, z0 = chunk.cz * CHUNK;
    const rnd = G.srand((chunk.cx * 31337) ^ (chunk.cz * 271) ^ 5);
    const max = G.Q.grassPerChunk;
    const mats = [];
    const m = new THREE.Matrix4();
    for (let i = 0; i < max; i++) {
      const x = x0 + rnd() * CHUNK, z = z0 + rnd() * CHUNK;
      if (W.inCaveRegion(x, z)) continue;   // 洞窟内に草は生えない
      if (G.dist2(x, z, -430, -140) < 30 * 30) continue;   // フェンリルの凍土に緑草は生えない
      const h = W.heightAt(x, z);
      if (h < WATER_Y + 0.7) continue;
      const b = W.biomeAt(x, z, h);
      const d = decorDensity(b).grass || 0;
      // 密度の濃淡マスク: 草原に濃い茂みと開けた地面のむらを作る
      const mask = 0.3 + (G.fbm(x * 0.016, z * 0.016, 2) * 0.5 + 0.5) * 0.95;
      if (rnd() > d * mask) continue;
      if (W.slopeYAt(x, z) < 0.8) continue;
      m.makeRotationY(rnd() * Math.PI * 2);
      const s = 0.7 + rnd() * 0.8;
      m.scale(new THREE.Vector3(s, s * (0.8 + rnd() * 0.6), s));
      m.setPosition(x, h - 0.02, z);
      mats.push(m.clone());
    }
    if (!mats.length) { chunk.grassMesh = 'none'; return; }
    const im = new THREE.InstancedMesh(grassGeo, grassMat, mats.length);
    for (let i = 0; i < mats.length; i++) im.setMatrixAt(i, mats[i]);
    im.instanceMatrix.needsUpdate = true;
    im.frustumCulled = false;   // 上記と同じ理由
    scene.add(im);
    chunk.grassMesh = im;
  }
  function removeGrass(chunk) {
    if (chunk.grassMesh && chunk.grassMesh !== 'none') {
      scene.remove(chunk.grassMesh);
      chunk.grassMesh.dispose();
    }
    chunk.grassMesh = null;
  }

  function destroyChunk(chunk) {
    scene.remove(chunk.mesh);
    chunk.mesh.geometry.dispose();
    for (const t of chunk.trees) { scene.remove(t); t.dispose(); }
    removeGrass(chunk);
    chunks.delete(chunk.key);
  }

  const terrainMat = new THREE.MeshLambertMaterial({ vertexColors: true });
  // 雨天の濡れ表現: 地形アルベドを暗く沈める uniform を注入
  terrainMat.onBeforeCompile = sh => {
    sh.uniforms.uWet = { value: 0 };
    sh.fragmentShader = 'uniform float uWet;\n' + sh.fragmentShader.replace(
      '#include <color_fragment>',
      '#include <color_fragment>\n  diffuseColor.rgb *= (1.0 - uWet * 0.3);'
    );
    terrainMat.userData.shader = sh;
  };
  W.setWetness = function (w) {
    if (terrainMat.userData.shader) terrainMat.userData.shader.uniforms.uWet.value = w;
  };

  /* ======================= 水面 ======================= */
  let waterMesh = null;
  function buildWater() {
    const geo = new THREE.PlaneGeometry(2400, 2400, 48, 48);
    geo.rotateX(-Math.PI / 2);
    const mat = new THREE.ShaderMaterial({
      transparent: true,
      uniforms: {
        uTime: { value: 0 },
        uColor: { value: new THREE.Color(0x2f6f9a) },
        uColor2: { value: new THREE.Color(0x62b8c9) },
        uFogColor: { value: new THREE.Color(0xbccfdd) },
        uFogNear: { value: 60 },
        uFogFar: { value: 260 },
        uLight: { value: 1.0 },
        uSunTint: { value: new THREE.Color(0xffffff) },
        uSunDir: { value: new THREE.Vector3(0.4, 0.8, 0.45) },
        uSunI: { value: 1.0 }
      },
      vertexShader: `
        uniform float uTime;
        varying float vWave;
        varying float vDist;
        varying vec3 vNorm;
        varying vec3 vWorld;
        void main(){
          // メッシュはカメラ追従で動くため、波はワールド座標で評価する
          vec4 wp = modelMatrix * vec4(position, 1.0);
          float w = sin(wp.x * 0.08 + uTime * 1.1) * 0.18
                  + sin(wp.z * 0.11 + uTime * 0.8) * 0.14
                  + sin((wp.x + wp.z) * 0.05 + uTime * 0.5) * 0.1;
          wp.y += w;
          vWave = w;
          // 波形の偏微分から解析的な法線 (傾きは誇張してハイライトを出す)
          float dwx = cos(wp.x * 0.08 + uTime * 1.1) * 0.0144
                    + cos((wp.x + wp.z) * 0.05 + uTime * 0.5) * 0.005;
          float dwz = cos(wp.z * 0.11 + uTime * 0.8) * 0.0154
                    + cos((wp.x + wp.z) * 0.05 + uTime * 0.5) * 0.005;
          vNorm = normalize(vec3(-dwx * 7.0, 1.0, -dwz * 7.0));
          vWorld = wp.xyz;
          vec4 mv = viewMatrix * wp;
          vDist = -mv.z;
          gl_Position = projectionMatrix * mv;
        }`,
      fragmentShader: `
        uniform vec3 uColor, uColor2, uFogColor, uSunTint, uSunDir;
        uniform float uFogNear, uFogFar, uLight, uSunI;
        varying float vWave;
        varying float vDist;
        varying vec3 vNorm;
        varying vec3 vWorld;
        void main(){
          float k = smoothstep(-0.3, 0.4, vWave);
          vec3 base = uColor * mix(vec3(1.0), uSunTint, 0.55);
          vec3 c = mix(base, uColor2 * uSunTint, k) * uLight;
          vec3 n = normalize(vNorm);
          vec3 vd = normalize(cameraPosition - vWorld);
          // 角度依存フレネル: 浅い角度ほど空 (フォグ色) を強く映す
          float fr = 0.1 + 0.7 * pow(1.0 - max(dot(vd, n), 0.0), 3.0);
          fr += smoothstep(12.0, 140.0, vDist) * 0.3;
          c = mix(c, uFogColor, clamp(fr, 0.0, 0.85));
          // 太陽のスペキュラ (波の法線でギラつく光帯)
          vec3 h = normalize(vd + normalize(uSunDir));
          float spec = pow(max(dot(n, h), 0.0), 110.0) * uSunI;
          c += uSunTint * spec * 0.9;
          float f = smoothstep(uFogNear, uFogFar, vDist);
          c = mix(c, uFogColor, f);
          gl_FragColor = vec4(c, 0.82 + fr * 0.1);
        }`
    });
    waterMesh = new THREE.Mesh(geo, mat);
    waterMesh.position.y = WATER_Y;
    waterMesh.frustumCulled = false;
    scene.add(waterMesh);
  }

  /* ======================= 建造物 ======================= */
  W.staticColliders = [];   // ランドマーク建造物の衝突円 {x,z,r}
  W.torches = [];           // {x,z,y, sprite}
  W.chestMeshes = {};       // id -> {group, lid, opened}
  W.shrineMeshes = {};      // id -> {crystal, baseY}

  function addStatic(x, z, r) { const c = { x, z, r }; W.staticColliders.push(c); return c; }

  /* 視線を遮る建造物はカメラを寄せず、半透明フェードで抜く */
  W.faders = [];
  function addFader(mesh, x, z, r, topY) {
    const mats = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
    W.faders.push({ mats, x, z, r, topY, cur: 1 });
  }
  W.updateFaders = function (dt, ax, az, bx, bz, ay, by) {
    const dx = bx - ax, dz = bz - az;
    const len2 = Math.max(dx * dx + dz * dz, 0.01);
    const k = G.damp(9, dt);
    for (const f of W.faders) {
      let target = 1;
      if (Math.abs(f.x - ax) < 60 && Math.abs(f.z - az) < 60) {
        const t = G.clamp(((f.x - ax) * dx + (f.z - az) * dz) / len2, 0.02, 0.98);
        const px = ax + dx * t, pz = az + dz * t;
        const rr = f.r + 0.55;
        // 水平に視線と交差し、かつ視線がその高さを越えていない場合のみフェード
        if (G.dist2(px, pz, f.x, f.z) < rr * rr && ay + (by - ay) * t < f.topY + 0.4) target = 0.24;
      }
      if (target === 1 && f.cur > 0.995) continue;
      f.cur += (target - f.cur) * k;
      if (f.cur > 0.995) {
        f.cur = 1;
        for (const m of f.mats) { m.transparent = false; m.opacity = 1; m.depthWrite = true; }
      } else {
        for (const m of f.mats) { m.transparent = true; m.opacity = f.cur; m.depthWrite = f.cur > 0.55; }
      }
    }
  };

  /* 建造物に影の設定を付与 */
  function shadowify(o) {
    o.traverse ? o.traverse(m => { if (m.isMesh) { m.castShadow = true; m.receiveShadow = true; } })
               : null;
    return o;
  }

  function buildHouse(x, z, ry, big) {
    const w = big ? 7 : 5, d = big ? 6 : 4.5, hh = big ? 3.2 : 2.6;
    const y = W.heightAt(x, z);
    const wall = new THREE.BoxGeometry(w, hh, d);
    const roofG = new THREE.CylinderGeometry(0.01, big ? 5.6 : 4.4, big ? 2.4 : 2.0, 4, 1);
    const doorG = new THREE.BoxGeometry(1.1, 1.8, 0.15);
    const geo = G.mergeGeo([
      { geo: wall, m: M4(0, hh / 2, 0), color: 0xcfc3a5 },
      { geo: roofG, m: (() => { const m = M4(0, hh + (big ? 1.2 : 1.0), 0, Math.PI / 4); return m; })(), color: 0x9a4f3c },
      { geo: doorG, m: M4(0, 0.9, d / 2 + 0.05), color: 0x6b4a2f }
    ]);
    wall.dispose(); roofG.dispose(); doorG.dispose();
    const mesh = shadowify(new THREE.Mesh(geo, sharedTreeMat.clone()));
    mesh.position.set(x, y, z);
    mesh.rotation.y = ry;
    scene.add(mesh);
    const cr = Math.max(w, d) * 0.62;
    addStatic(x, z, cr).fade = true;
    addFader(mesh, x, z, cr, y + hh + 2.6);
    return mesh;
  }

  function buildTorch(x, z) {
    const y = W.heightAt(x, z);
    const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.07, 0.1, 2.0, 5),
      new THREE.MeshLambertMaterial({ color: 0x6b4a2f }));
    pole.position.set(x, y + 1.0, z);
    scene.add(pole);
    const spr = new THREE.Sprite(new THREE.SpriteMaterial({
      map: G.makeRadialTex(64, [[0, 'rgba(255,220,120,1)'], [0.4, 'rgba(255,140,40,0.85)'], [1, 'rgba(255,80,0,0)']]),
      transparent: true, depthWrite: false, blending: THREE.AdditiveBlending
    }));
    spr.position.set(x, y + 2.25, z);
    spr.scale.set(1.1, 1.4, 1);
    scene.add(spr);
    W.torches.push({ x, z, y: y + 2.25, sprite: spr, seed: Math.random() * 10 });
  }

  function buildShrine(sh) {
    const x = sh.x, z = sh.z;
    const y = W.heightAt(x, z);
    const base = new THREE.CylinderGeometry(2.6, 3.0, 0.6, 8);
    const p = new THREE.BoxGeometry(0.5, 3.0, 0.5);
    const top = new THREE.BoxGeometry(3.4, 0.45, 0.7);
    const geo = G.mergeGeo([
      { geo: base, m: M4(0, 0.3, 0), color: 0xa8a49a },
      { geo: p, m: M4(-1.3, 2.0, 0), color: 0xb5b1a6 },
      { geo: p, m: M4(1.3, 2.0, 0), color: 0xb5b1a6 },
      { geo: top, m: M4(0, 3.6, 0), color: 0x9d998f }
    ]);
    base.dispose(); p.dispose(); top.dispose();
    const mesh = shadowify(new THREE.Mesh(geo, sharedTreeMat));
    mesh.position.set(x, y, z);
    scene.add(mesh);
    const crystal = new THREE.Mesh(new THREE.OctahedronGeometry(0.5, 0),
      new THREE.MeshLambertMaterial({ color: 0x5ad2ff, emissive: 0x2288cc }));
    crystal.position.set(x, y + 2.0, z);
    scene.add(crystal);
    const glow = new THREE.Sprite(new THREE.SpriteMaterial({
      map: G.makeRadialTex(64, [[0, 'rgba(120,220,255,0.9)'], [1, 'rgba(80,180,255,0)']]),
      transparent: true, depthWrite: false, blending: THREE.AdditiveBlending
    }));
    glow.position.copy(crystal.position);
    glow.scale.set(1.15, 1.15, 1);
    glow.material.opacity = 0.42;
    scene.add(glow);
    addStatic(x - 1.3, z, 0.45); addStatic(x + 1.3, z, 0.45);
    // 遠くからでも見える光の柱
    // 上に向かって細く消えるコーン (遠景で平坦な帯に見えないように)
    const beam = new THREE.Mesh(
      new THREE.CylinderGeometry(0.16, 1.2, 48, 6, 1, true),
      new THREE.MeshBasicMaterial({
        color: 0x55bbff, transparent: true, opacity: 0.09,
        blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide
      })
    );
    beam.position.set(x, y + 24, z);
    scene.add(beam);
    W.shrineMeshes[sh.id] = { crystal, glow, beam, baseY: y + 2.0 };
  }

  function buildRuinCircle(x, z, radius, n, seed, tint, ice) {
    const rnd = G.srand(seed);
    for (let i = 0; i < n; i++) {
      const a = (i / n) * Math.PI * 2;
      const px = x + Math.cos(a) * radius, pz = z + Math.sin(a) * radius;
      const py = W.heightAt(px, pz);
      const broken = rnd() < 0.4;
      const h = broken ? 1.2 + rnd() * 1.5 : 4.5 + rnd() * 1.5;
      // 氷柱は先細りの結晶プリズム+微発光、遺跡柱は石の円柱
      const pillar = new THREE.Mesh(
        ice ? new THREE.CylinderGeometry(0.16, 0.66, h, 5)
            : new THREE.CylinderGeometry(0.55, 0.7, h, 6),
        ice ? new THREE.MeshLambertMaterial({ color: tint, emissive: 0x16344a })
            : new THREE.MeshLambertMaterial({ color: tint || 0x9d998f })
      );
      shadowify(pillar);
      pillar.position.set(px, py + h / 2 - 0.1, pz);
      pillar.rotation.y = rnd();
      // 氷晶は傾けすぎると浮いて見えるため直立気味に
      if (broken) pillar.rotation.z = (rnd() - 0.5) * (ice ? 0.06 : 0.16);
      scene.add(pillar);
      addStatic(px, pz, 0.8).fade = true;
      addFader(pillar, px, pz, 0.8, py + h);
    }
  }

  /* 竜の頂の焦土に残り火 (フォグ越しでも「焦土」が伝わる暖色の光点) */
  function buildEmbers(x, z) {
    const rnd = G.srand(4242);
    const emberMat = new THREE.MeshLambertMaterial({ color: 0x33221a, emissive: 0xbb3d12 });
    const glowMap = G.makeRadialTex(48, [[0, 'rgba(255,120,40,0.7)'], [1, 'rgba(255,60,0,0)']]);
    for (let i = 0; i < 9; i++) {
      const a = rnd() * Math.PI * 2, r = 4 + rnd() * 17;
      const px = x + Math.cos(a) * r, pz = z + Math.sin(a) * r;
      const py = W.heightAt(px, pz);
      const rock = new THREE.Mesh(new THREE.DodecahedronGeometry(0.28 + rnd() * 0.3, 0), emberMat);
      rock.position.set(px, py + 0.2, pz);
      rock.rotation.set(rnd() * 3, rnd() * 3, rnd() * 3);
      scene.add(rock);
      const glow = new THREE.Sprite(new THREE.SpriteMaterial({
        map: glowMap, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending
      }));
      glow.position.set(px, py + 0.35, pz);
      glow.scale.set(1.5, 1.0, 1);
      glow.material.opacity = 0.5;
      scene.add(glow);
    }
  }

  function buildTower(x, z) {
    const y = W.heightAt(x, z);
    const body = new THREE.CylinderGeometry(2.2, 2.8, 11, 8);
    const roof = new THREE.ConeGeometry(3.0, 2.6, 8);
    const geo = G.mergeGeo([
      { geo: body, m: M4(0, 5.5, 0), color: 0xa39e92 },
      { geo: roof, m: M4(0, 12.3, 0), color: 0x7d4437 }
    ]);
    body.dispose(); roof.dispose();
    const mesh = shadowify(new THREE.Mesh(geo, sharedTreeMat.clone()));
    mesh.position.set(x, y, z);
    scene.add(mesh);
    addStatic(x, z, 2.9).fade = true;
    addFader(mesh, x, z, 2.9, y + 13.6);
  }

  function buildChest(ch) {
    const y = W.heightAt(ch.x, ch.z);
    const grp = new THREE.Group();
    const body = new THREE.Mesh(new THREE.BoxGeometry(1.1, 0.6, 0.7),
      new THREE.MeshLambertMaterial({ color: 0x7a5230 }));
    body.position.y = 0.3;
    const lid = new THREE.Group();
    const lidM = new THREE.Mesh(new THREE.BoxGeometry(1.1, 0.28, 0.7),
      new THREE.MeshLambertMaterial({ color: 0x8a5f38 }));
    lidM.position.set(0, 0.14, 0.35);
    lid.add(lidM);
    lid.position.set(0, 0.6, -0.35);
    const band = new THREE.Mesh(new THREE.BoxGeometry(1.16, 0.62, 0.12),
      new THREE.MeshLambertMaterial({ color: 0xc9a94a }));
    band.position.y = 0.31;
    grp.add(body, lid, band);
    shadowify(grp);
    grp.position.set(ch.x, y, ch.z);
    grp.rotation.y = G.hash2(ch.x | 0, ch.z | 0) * Math.PI * 2;
    scene.add(grp);
    W.chestMeshes[ch.id] = { group: grp, lid, opened: false };
    addStatic(ch.x, ch.z, 0.7);
  }

  W.hideChest = function (id) {
    const c = W.chestMeshes[id];
    if (c) scene.remove(c.group);
  };
  W.openChestVisual = function (id) {
    const c = W.chestMeshes[id];
    if (c && !c.opened) { c.opened = true; c.lid.rotation.x = -1.9; }
  };

  function buildCamp(x, z) {
    const y = W.heightAt(x, z);
    // 焚き火
    const logs = G.mergeGeo([
      { geo: new THREE.CylinderGeometry(0.08, 0.08, 1.0, 5), m: (() => { const m = M4(0, 0.12, 0, 0, 1); m.multiply(new THREE.Matrix4().makeRotationZ(1.4)); return m; })(), color: 0x5a4630 },
      { geo: new THREE.CylinderGeometry(0.08, 0.08, 1.0, 5), m: (() => { const m = M4(0, 0.12, 0, 1.2, 1); m.multiply(new THREE.Matrix4().makeRotationZ(1.4)); return m; })(), color: 0x6b5238 }
    ]);
    const lm = shadowify(new THREE.Mesh(logs, sharedTreeMat));
    lm.position.set(x, y, z);
    scene.add(lm);
    const spr = new THREE.Sprite(new THREE.SpriteMaterial({
      map: G.makeRadialTex(64, [[0, 'rgba(255,220,120,1)'], [0.4, 'rgba(255,140,40,0.85)'], [1, 'rgba(255,80,0,0)']]),
      transparent: true, depthWrite: false, blending: THREE.AdditiveBlending
    }));
    spr.position.set(x, y + 0.7, z);
    spr.scale.set(1.6, 2.0, 1);
    scene.add(spr);
    W.torches.push({ x, z, y: y + 0.7, sprite: spr, seed: Math.random() * 10 });
    // テント
    for (const [tx, tz, ry] of [[3.5, 1.5, 0.8], [-3, 2.5, -0.6], [0.5, -3.5, 2.4]]) {
      const ty = W.heightAt(x + tx, z + tz);
      const tent = shadowify(new THREE.Mesh(new THREE.ConeGeometry(1.6, 1.9, 4),
        new THREE.MeshLambertMaterial({ color: 0x6a5844 })));
      tent.position.set(x + tx, ty + 0.9, z + tz);
      tent.rotation.y = ry;
      scene.add(tent);
      addStatic(x + tx, z + tz, 1.4);
    }
  }

  function buildCaveMouth() {
    const x = -260, z = -360;
    const y = W.heightAt(x, z);
    const arch = G.mergeGeo([
      { geo: new THREE.BoxGeometry(0.9, 4.2, 0.9), m: M4(-2.0, 2.1, 0), color: 0x6a6a72 },
      { geo: new THREE.BoxGeometry(0.9, 4.2, 0.9), m: M4(2.0, 2.1, 0), color: 0x6a6a72 },
      { geo: new THREE.BoxGeometry(5.4, 0.9, 1.1), m: M4(0, 4.4, 0), color: 0x5a5a62 }
    ]);
    const m = shadowify(new THREE.Mesh(arch, sharedTreeMat));
    m.position.set(x, y, z);
    scene.add(m);
    // 暗い入口 (完全な黒ベタではなく、奥からの水晶の微光で奥行きを示す)
    const dark = new THREE.Mesh(new THREE.PlaneGeometry(3.6, 3.8),
      new THREE.MeshBasicMaterial({ color: 0x070a14 }));
    dark.position.set(x, y + 1.9, z - 0.2);
    scene.add(dark);
    const innerGlow = new THREE.Sprite(new THREE.SpriteMaterial({
      map: G.makeRadialTex(64, [[0, 'rgba(90,160,230,0.5)'], [0.5, 'rgba(60,120,200,0.2)'], [1, 'rgba(40,90,170,0)']]),
      transparent: true, depthWrite: false, blending: THREE.AdditiveBlending
    }));
    innerGlow.position.set(x, y + 1.4, z - 0.1);
    innerGlow.scale.set(2.6, 2.2, 1);
    scene.add(innerGlow);
    addStatic(x - 2, z, 0.7); addStatic(x + 2, z, 0.7);
    // 入口の周りに岩塊 (地形に埋まった洞窟らしさ)
    const rrnd = G.srand(88);
    for (let i = 0; i < 7; i++) {
      const a = (i / 7) * Math.PI * 1.5 - 0.6;
      const rx = x + Math.cos(a) * (4 + rrnd() * 3);
      const rz = z + Math.sin(a) * (3 + rrnd() * 2.5) - 1.5;
      const sc = 1.4 + rrnd() * 2.2;
      const rock = shadowify(new THREE.Mesh(new THREE.IcosahedronGeometry(1, 0),
        new THREE.MeshLambertMaterial({ color: 0x71717c })));
      rock.position.set(rx, W.heightAt(rx, rz) + sc * 0.3, rz);
      rock.scale.set(sc, sc * (0.75 + rrnd() * 0.5), sc);
      rock.rotation.y = rrnd() * 3;
      scene.add(rock);
      addStatic(rx, rz, sc * 0.8);
    }
  }

  function buildCaveInterior() {
    const cx = W.CAVE.cx, cz = W.CAVE.cz;
    // この関数で追加したオブジェクトは末尾で1グループにまとめ、
    // 遠距離では丸ごと非表示にする (天蓋球がカメラfar平面でクリップされ、
    // 地上から弧状のアーティファクトとして見えていたため)
    const childrenBefore = scene.children.length;
    // 天蓋 (内側から見える暗い殻)
    const dome = new THREE.Mesh(
      new THREE.SphereGeometry(66, 20, 12),
      new THREE.MeshLambertMaterial({ color: 0x14161e, side: THREE.BackSide })
    );
    dome.position.set(cx, 56, cz);
    scene.add(dome);
    // 石筍 (密度を上げて洞窟の情報量を出す)
    const rnd = G.srand(777);
    const stalMats = [
      new THREE.MeshLambertMaterial({ color: 0x565a66 }),
      new THREE.MeshLambertMaterial({ color: 0x454b58 }),
      new THREE.MeshLambertMaterial({ color: 0x62697a })
    ];
    const mkStal = (px, pz, h) => {
      // 2段重ねで岩らしい輪郭に (単一の滑らかな円錐はテントに見える)
      const base = shadowify(new THREE.Mesh(
        new THREE.ConeGeometry(0.62 + rnd() * 0.9, h * 0.55, 6), stalMats[(rnd() * 3) | 0]));
      base.position.set(px, caveHeight(px, pz) + h * 0.27 - 0.1, pz);
      base.rotation.y = rnd() * 3;
      scene.add(base);
      const top = shadowify(new THREE.Mesh(
        new THREE.ConeGeometry(0.34 + rnd() * 0.45, h, 5), stalMats[(rnd() * 3) | 0]));
      top.position.set(px + (rnd() - 0.5) * 0.3, caveHeight(px, pz) + h / 2 - 0.1, pz + (rnd() - 0.5) * 0.3);
      top.rotation.y = rnd() * 3;
      scene.add(top);
      if (h > 2) addStatic(px, pz, 0.7);
    };
    for (let i = 0; i < 42; i++) {
      const a = rnd() * Math.PI * 2, r = 5 + rnd() * 40;
      mkStal(cx + Math.cos(a) * r, cz + Math.sin(a) * r, 1.2 + rnd() * 3.8);
    }
    // 入口通路の両脇にも列を作り、密度と導線を出す
    for (let i = 0; i < 8; i++) {
      const zz = 1162 + i * 5.5;
      mkStal(cx - 9 - rnd() * 5, zz, 1.0 + rnd() * 2.6);
      mkStal(cx + 9 + rnd() * 5, zz, 1.0 + rnd() * 2.6);
    }
    // 床の岩屑 (平坦な床の空虚さを埋める)
    const rockMat = new THREE.MeshLambertMaterial({ color: 0x4a4f5c });
    for (let i = 0; i < 14; i++) {
      const a = rnd() * Math.PI * 2, r = 4 + rnd() * 42;
      const px = cx + Math.cos(a) * r, pz = cz + Math.sin(a) * r;
      const rock = new THREE.Mesh(new THREE.DodecahedronGeometry(0.35 + rnd() * 0.55, 0), rockMat);
      rock.position.set(px, caveHeight(px, pz) + 0.25, pz);
      rock.rotation.set(rnd() * 3, rnd() * 3, rnd() * 3);
      scene.add(rock);
    }
    // 光る水晶
    const crystalMat = new THREE.MeshLambertMaterial({ color: 0x77ccff, emissive: 0x3377bb });
    const glowMap = G.makeRadialTex(64, [[0, 'rgba(130,200,255,0.8)'], [1, 'rgba(80,150,255,0)']]);
    const addCrystal = (px, pz, s) => {
      const c = new THREE.Mesh(new THREE.OctahedronGeometry(0.7 * s, 0), crystalMat);
      c.position.set(px, caveHeight(px, pz) + 0.7 * s, pz);
      c.rotation.set(rnd(), rnd(), rnd());
      scene.add(c);
      const glow = new THREE.Sprite(new THREE.SpriteMaterial({
        map: glowMap, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending
      }));
      glow.position.copy(c.position);
      glow.scale.set(3.2 * s, 3.2 * s, 1);
      scene.add(glow);
    };
    for (let i = 0; i < 6; i++) {
      const a = (i / 6) * Math.PI * 2 + 0.4, r = 12 + (i % 3) * 9;
      addCrystal(cx + Math.cos(a) * r, cz + Math.sin(a) * r, 1);
    }
    // 入口(ポータル)から中心への通路沿いにも小水晶を灯し、進む方向を導く
    for (let i = 0; i < 5; i++) {
      addCrystal(cx + (i % 2 ? 5 : -5) + (rnd() - 0.5) * 3, 1170 + i * 8, 0.6 + rnd() * 0.3);
    }
    // 宝箱の周りに水晶群+石の台座+暖色の光 (報酬エリアの見せ場)
    const pedMat = new THREE.MeshLambertMaterial({ color: 0x5c6172 });
    const chestGlowMap = G.makeRadialTex(64, [[0, 'rgba(255,205,110,0.65)'], [1, 'rgba(255,160,50,0)']]);
    for (const ch of W.chests) {
      if (!W.inCaveRegion(ch.x, ch.z)) continue;
      for (let k = 0; k < 4; k++) {
        const a = rnd() * Math.PI * 2, r = 2.2 + rnd() * 2.5;
        addCrystal(ch.x + Math.cos(a) * r, ch.z + Math.sin(a) * r, 0.55 + rnd() * 0.5);
      }
      const hy = caveHeight(ch.x, ch.z);
      const ped = new THREE.Mesh(new THREE.CylinderGeometry(1.35, 1.6, 0.32, 8), pedMat);
      ped.position.set(ch.x, hy - 0.02, ch.z);
      scene.add(ped);
      const cg = new THREE.Sprite(new THREE.SpriteMaterial({
        map: chestGlowMap, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending
      }));
      cg.position.set(ch.x, hy + 1.3, ch.z);
      cg.scale.set(2.6, 2.0, 1);
      scene.add(cg);
    }
    // 青い光源 (中央 + 入口側)。床の高さ基準で置く (固定yだと地中に埋まり寄与しない)
    const pt = new THREE.PointLight(0x6699dd, 1.1, 70);
    pt.position.set(cx, caveHeight(cx, cz) + 9, cz);
    scene.add(pt);
    const pt2 = new THREE.PointLight(0xffe0b0, 2.6, 42);
    pt2.position.set(cx, caveHeight(cx, 1164) + 3.2, 1164);
    scene.add(pt2);
    // 出口の枠
    const arch = G.mergeGeo([
      { geo: new THREE.BoxGeometry(0.8, 3.8, 0.8), m: M4(-1.8, 1.9, 0), color: 0x6a6a72 },
      { geo: new THREE.BoxGeometry(0.8, 3.8, 0.8), m: M4(1.8, 1.9, 0), color: 0x6a6a72 },
      { geo: new THREE.BoxGeometry(4.6, 0.8, 1.0), m: M4(0, 4.0, 0), color: 0x5a5a62 }
    ]);
    const m = shadowify(new THREE.Mesh(arch, sharedTreeMat));
    m.position.set(cx, caveHeight(cx, 1160), 1160);
    scene.add(m);

    // この関数で追加した全オブジェクトをグループへ移す (遠距離カリング用)
    const grp = new THREE.Group();
    const added = scene.children.slice(childrenBefore);
    for (const o of added) grp.add(o);
    scene.add(grp);
    W._caveGrp = grp;
  }

  function buildVillage() {
    buildHouse(-18, -10, 0.3);
    buildHouse(17, -13, -0.4);
    buildHouse(-8, 24, Math.PI);
    buildHouse(21, 13, -1.2);
    buildHouse(-26, 8, 0.9);
    buildHouse(2, -22, 0, true);        // 長老の家
    // 井戸
    const wy = W.heightAt(0, 6);
    const well = new THREE.Mesh(new THREE.CylinderGeometry(1.1, 1.2, 1.0, 8),
      new THREE.MeshLambertMaterial({ color: 0x8f8b82 }));
    well.position.set(0, wy + 0.5, 6);
    scene.add(well);
    addStatic(0, 6, 1.3);
    // 屋台 (商人)
    const sy = W.heightAt(13, 4);
    const stall = G.mergeGeo([
      { geo: new THREE.BoxGeometry(2.6, 0.15, 1.4), m: M4(0, 1.0, 0), color: 0x8a6a44 },
      { geo: new THREE.BoxGeometry(3.0, 0.12, 1.8), m: M4(0, 2.15, 0, 0.06), color: 0xb04a3e },
      { geo: new THREE.BoxGeometry(0.16, 2.1, 0.16), m: M4(-1.3, 1.05, -0.7), color: 0x6b4a2f },
      { geo: new THREE.BoxGeometry(0.16, 2.1, 0.16), m: M4(1.3, 1.05, -0.7), color: 0x6b4a2f },
      { geo: new THREE.BoxGeometry(0.16, 2.1, 0.16), m: M4(-1.3, 1.05, 0.7), color: 0x6b4a2f },
      { geo: new THREE.BoxGeometry(0.16, 2.1, 0.16), m: M4(1.3, 1.05, 0.7), color: 0x6b4a2f }
    ]);
    const stallM = shadowify(new THREE.Mesh(stall, sharedTreeMat));
    stallM.position.set(13, sy, 4);
    scene.add(stallM);
    addStatic(13, 4, 1.6);
    // 松明
    buildTorch(-6, 0); buildTorch(8, -8); buildTorch(-14, 14); buildTorch(16, 8);
    buildTorch(4, 14);
    // 夜の村を照らすポイントライト (2灯だけ)
    W.villageLights = [];
    for (const [lx, lz] of [[-6, 0], [16, 8]]) {
      const pl = new THREE.PointLight(0xffa04a, 0, 26);
      pl.position.set(lx, W.heightAt(lx, lz) + 2.4, lz);
      scene.add(pl);
      W.villageLights.push(pl);
    }
  }

  /* 薬草 (収集物): 光る草 */
  W.herbs = [];  // {id,x,z,taken,mesh,glow}
  function buildHerbs() {
    const spots = [
      [-120, 90], [-180, 40], [-90, -140], [60, 170], [140, -60],
      [-240, -120], [90, 260], [-60, 220], [200, 60], [-160, -220]
    ];
    const herbMatL = new THREE.MeshLambertMaterial({ color: 0x9fe8a0, emissive: 0x2a7a3a });
    for (let i = 0; i < spots.length; i++) {
      const [bx, bz] = spots[i];
      // 付近の適地を探す
      let x = bx, z = bz;
      for (let t = 0; t < 8; t++) {
        const tx = bx + (G.hash2(i, t) - 0.5) * 30, tz = bz + (G.hash2(t, i) - 0.5) * 30;
        const h = W.heightAt(tx, tz);
        if (h > WATER_Y + 1 && !nearLandmark(tx, tz, 4)) { x = tx; z = tz; break; }
      }
      const y = W.heightAt(x, z);
      const m = new THREE.Mesh(new THREE.ConeGeometry(0.22, 0.7, 5), herbMatL);
      m.position.set(x, y + 0.35, z);
      scene.add(m);
      const glow = new THREE.Sprite(new THREE.SpriteMaterial({
        map: G.makeRadialTex(64, [[0, 'rgba(150,255,170,0.8)'], [1, 'rgba(100,255,140,0)']]),
        transparent: true, depthWrite: false, blending: THREE.AdditiveBlending
      }));
      glow.position.set(x, y + 0.5, z);
      glow.scale.set(1.4, 1.4, 1);
      scene.add(glow);
      W.herbs.push({ id: 'herb' + i, x, z, taken: false, mesh: m, glow });
    }
  }
  W.takeHerbVisual = function (h) {
    h.taken = true;
    scene.remove(h.mesh); scene.remove(h.glow);
  };

  /* ======================= 衝突 ======================= */
  W.collide = function (px, pz, r) {
    // 建造物
    let x = px, z = pz;
    const resolve = (c) => {
      const dx = x - c.x, dz = z - c.z;
      const rr = r + c.r;
      const d2 = dx * dx + dz * dz;
      if (d2 < rr * rr && d2 > 0.0001) {
        const d = Math.sqrt(d2);
        const push = (rr - d) / d;
        x += dx * push; z += dz * push;
      }
    };
    for (let i = 0; i < W.staticColliders.length; i++) {
      const c = W.staticColliders[i];
      if (Math.abs(c.x - x) < 8 && Math.abs(c.z - z) < 8) resolve(c);
    }
    // 植生 (周囲チャンク)
    const cx = Math.floor(x / CHUNK), cz = Math.floor(z / CHUNK);
    for (let j = -1; j <= 1; j++) {
      for (let i = -1; i <= 1; i++) {
        const ch = chunks.get(chunkKey(cx + i, cz + j));
        if (!ch) continue;
        for (let k = 0; k < ch.colliders.length; k++) {
          const c = ch.colliders[k];
          if (Math.abs(c.x - x) < 4 && Math.abs(c.z - z) < 4) resolve(c);
        }
      }
    }
    return { x, z };
  };

  /* カメラ視線を遮る木/岩があれば、カメラを何割まで寄せるべきかを返す (1=遮蔽なし) */
  W.cameraOcclusion = function (ax, az, bx, bz) {
    let occ = 1;
    const dx = bx - ax, dz = bz - az;
    const len2 = dx * dx + dz * dz;
    if (len2 < 1) return 1;
    // 建造物 (フェード対象はカメラを寄せず updateFaders が半透明化する)
    for (const c of W.staticColliders) {
      if (c.fade) continue;
      if (Math.abs(c.x - ax) > 60 || Math.abs(c.z - az) > 60) continue;
      const t = G.clamp(((c.x - ax) * dx + (c.z - az) * dz) / len2, 0.15, 0.95);
      const px = ax + dx * t, pz = az + dz * t;
      const rr = c.r * 0.9;
      if (G.dist2(px, pz, c.x, c.z) < rr * rr) occ = Math.min(occ, Math.max(0.3, t - 0.08));
    }
    const cx = Math.floor((ax + bx) / 2 / CHUNK), cz = Math.floor((az + bz) / 2 / CHUNK);
    for (let j = -1; j <= 1; j++) {
      for (let i = -1; i <= 1; i++) {
        const ch = chunks.get(chunkKey(cx + i, cz + j));
        if (!ch) continue;
        for (const c of ch.colliders) {
          if (c.r < 0.45) continue;
          const t = G.clamp(((c.x - ax) * dx + (c.z - az) * dz) / len2, 0.15, 0.95);
          const px = ax + dx * t, pz = az + dz * t;
          const d2 = G.dist2(px, pz, c.x, c.z);
          // 幹の衝突円より広めに取り、樹冠が視界を塞ぐ前にカメラを寄せる
          const rr = Math.max(c.r * 0.85, 1.15);
          if (d2 < rr * rr) occ = Math.min(occ, Math.max(0.3, t - 0.08));
        }
      }
    }
    return occ;
  };

  /* ======================= 初期化 / 更新 ======================= */
  W.init = function (sc) {
    scene = sc;
    sharedTreeMat = treeMat();
    buildTreeGeos();
    buildGrassAssets();
    buildWater();
    buildVillage();
    for (const sh of W.shrines) buildShrine(sh);
    buildRuinCircle(-430, -140, 18, 9, 11, 0xbfdcec, true);   // 狼ボス闘技場 (氷の結晶柱)
    buildRuinCircle(430, -80, 20, 11, 22);              // ゴーレム闘技場
    buildRuinCircle(-40, -640, 22, 12, 33, 0x3d3a4c);   // 竜の頂 (黒曜石の柱)
    buildEmbers(-40, -640);                              // 焦土の残り火
    buildRuinCircle(150, 430, 13, 7, 44);       // 南の廃墟
    buildTower(-200, 200);
    buildTower(180, -320);
    buildRuinCircle(390, 380, 16, 8, 55);       // スコルグの巣
    buildCamp(-150, 250);
    buildCamp(220, 140);
    buildCaveMouth();
    buildCaveInterior();
    for (const ch of W.chests) buildChest(ch);
    buildHerbs();
  };

  W.activeSpawns = function () {
    const out = [];
    for (const ch of chunks.values()) {
      for (const s of ch.spawns) out.push(s);
    }
    return out;
  };

  let torchT = 0;
  W.update = function (dt, camX, camZ) {
    const ccx = Math.floor(camX / CHUNK), ccz = Math.floor(camZ / CHUNK);
    const R = G.Q.chunkRadius;
    const GR = G.Q.grassRadius;

    // 必要チャンクをキューへ
    for (let j = -R; j <= R; j++) {
      for (let i = -R; i <= R; i++) {
        const key = chunkKey(ccx + i, ccz + j);
        if (!chunks.has(key) && !buildQueue.some(q => q.key === key)) {
          buildQueue.push({ cx: ccx + i, cz: ccz + j, key, d: i * i + j * j });
        }
      }
    }
    buildQueue.sort((a, b) => a.d - b.d);
    let built = 0;
    while (buildQueue.length && built < 2) {
      const q = buildQueue.shift();
      const dx = q.cx - ccx, dz = q.cz - ccz;
      if (Math.max(Math.abs(dx), Math.abs(dz)) > R) continue; // もう不要
      buildChunk(q.cx, q.cz);
      built++;
    }

    // 範囲外チャンク破棄 & 草の付け外し (草の生成は1フレーム1チャンクまで)
    let grassBuilt = false;
    for (const ch of Array.from(chunks.values())) {
      const dx = Math.abs(ch.cx - ccx), dz = Math.abs(ch.cz - ccz);
      const dist = Math.max(dx, dz);
      if (dist > R + 1) { destroyChunk(ch); continue; }
      if (dist <= GR) {
        if (!ch.grassMesh && !grassBuilt) { addGrass(ch); grassBuilt = true; }
      }
      else if (ch.grassMesh) removeGrass(ch);
      // 影パスはシャドウカメラ範囲 (±52m ≈ 2チャンク) 内の植生だけ描く
      const cast = dist <= 2;
      for (const t of ch.trees) if (t.castShadow !== cast) t.castShadow = cast;
    }

    // 水面アニメ
    if (waterMesh) {
      waterMesh.material.uniforms.uTime.value = G.time;
      waterMesh.position.x = camX; waterMesh.position.z = camZ;
    }
    if (grassMat) grassMat.uniforms.uTime.value = G.time;

    // 松明のゆらぎ + 村の灯り (夜のみ)
    if (W.villageLights) {
      const tod = G.State ? G.State.tod : 12;
      const night = G.smoothstep(18.5, 20, tod) + (1 - G.smoothstep(4.5, 6.5, tod));
      const k = G.clamp(night, 0, 1);
      for (const pl of W.villageLights) {
        pl.intensity = k * (0.9 + Math.sin(G.time * 8 + pl.position.x) * 0.12);
      }
    }
    torchT += dt;
    // 松明は暗い時間帯のみ灯す (真昼に燃えっぱなしにしない)
    const torchOn = G.clamp((0.62 - (G.Sky.lightLevel || 1)) * 3.2, 0, 1);
    for (const t of W.torches) {
      const f = 0.9 + Math.sin(torchT * 9 + t.seed * 7) * 0.15 + Math.sin(torchT * 23 + t.seed) * 0.08;
      t.sprite.scale.set(1.1 * f, 1.4 * f, 1);
      t.sprite.material.opacity = torchOn;
    }
    // 祠クリスタル回転 & 光の柱の色 (灯すと金色に)
    // 洞窟内装は近づいた時だけ描画 (遠方から天蓋の縁が見えるのを防ぐ)
    if (W._caveGrp) {
      W._caveGrp.visible = G.dist2(camX, camZ, W.CAVE.cx, W.CAVE.cz) < 350 * 350;
    }
    for (const id in W.shrineMeshes) {
      const s = W.shrineMeshes[id];
      s.crystal.rotation.y += dt * 1.2;
      s.crystal.position.y = s.baseY + Math.sin(G.time * 1.6) * 0.12;
      if (s.beam) {
        const lit = G.State && G.State.shrines && G.State.shrines[id];
        if (lit && !s.litApplied) {
          s.litApplied = true;
          s.beam.material.color.set(0xffd58a);
          s.beam.material.opacity = 0.1;
          s.crystal.material.color.set(0xffd58a);
          s.crystal.material.emissive.set(0xcc8822);
        }
        // 近距離では減衰させ、至近で祠が白飛びしないように
        const bd = G.dist(camX, camZ, s.beam.position.x, s.beam.position.z);
        const att = G.clamp(bd / 30, 0.12, 1);
        s.beam.material.opacity = ((s.litApplied ? 0.09 : 0.15) + Math.sin(G.time * 1.3 + s.baseY) * 0.03) * att;
        if (s.glow) s.glow.material.opacity = 0.42 * G.clamp(bd / 14, 0.3, 1);
      }
    }
    // 未開封の宝箱のきらめき
    sparkleT -= dt;
    if (sparkleT <= 0) {
      sparkleT = 1.4;
      for (const c of W.chests) {
        const cm = W.chestMeshes[c.id];
        if (!cm || cm.opened) continue;
        if (G.dist2(camX, camZ, c.x, c.z) > 45 * 45) continue;
        const y = c.baseY !== undefined ? c.baseY : (c.baseY = W.heightAt(c.x, c.z));
        G.FX.burst(c.x, y + 0.9, c.z, {
          n: 2, color: 0xffe08a, speed: 0.5, up: 0.8, gravity: -0.4,
          life: 1.1, size: 1.8, drag: 0.5
        });
      }
    }
  };
  let sparkleT = 0;

  /* 草・水のフォグ/明るさ同期 (Sky から呼ぶ) */
  W.syncEnv = function (fogColor, fogNear, fogFar, light, sunTint, sunDir, sunI) {
    if (grassMat) {
      grassMat.uniforms.uFogColor.value.copy(fogColor);
      grassMat.uniforms.uFogNear.value = fogNear;
      grassMat.uniforms.uFogFar.value = fogFar;
      grassMat.uniforms.uLight.value = light;
    }
    if (waterMesh) {
      const u = waterMesh.material.uniforms;
      u.uFogColor.value.copy(fogColor);
      u.uFogNear.value = fogNear;
      u.uFogFar.value = fogFar;
      u.uLight.value = light;
      if (sunTint) u.uSunTint.value.copy(sunTint);
      if (sunDir) u.uSunDir.value.copy(sunDir);
      if (sunI !== undefined) u.uSunI.value = sunI;
    }
  };
})();

/* =============================================================================
 * 空 / 昼夜 / 天候
 * ========================================================================== */
(function () {
  const Sky = G.Sky = {};
  let scene, hemi, sun, skyDome, sunSpr, sunHalo, moonSpr, stars, clouds = [];
  let rainPts = null, rainVel = null, rainPos = null, rainN = 0, rainOn = 0;

  /* 時刻キーフレーム: [時, 天頂色, 地平色, 太陽色, 直射光強度, 半球光強度] */
  const KEYS = [
    [0,  0x0a1026, 0x141c33, 0x223, 0.02, 0.16],
    [4,  0x0a1026, 0x141c33, 0x223, 0.02, 0.16],
    [5.5, 0x2c3e6b, 0xc47b52, 0xff9a55, 0.3, 0.28],
    [7,  0x6a95c4, 0xf0d3a4, 0xffd9a0, 0.95, 0.5],
    [8.5, 0x4a86d0, 0xc8dcea, 0xfff0d4, 1.05, 0.62],
    [12, 0x4a86d0, 0xbcd8e8, 0xfff2dd, 1.32, 0.5],
    [16, 0x4d82c2, 0xd6c9a2, 0xffe2b2, 1.0, 0.6],
    [17.5, 0x46639e, 0xe6a878, 0xffb070, 1.05, 0.62],
    [18.7, 0x3a4a80, 0xe08a55, 0xff8a4a, 0.95, 0.56],
    [20, 0x141c3d, 0x33305c, 0x445, 0.05, 0.2],
    [24, 0x0a1026, 0x141c33, 0x223, 0.02, 0.16]
  ];
  const cA = new THREE.Color(), cB = new THREE.Color(), cTop = new THREE.Color(),
        cHor = new THREE.Color(), cSun = new THREE.Color();

  function sample(tod) {
    let i = 0;
    while (i < KEYS.length - 1 && KEYS[i + 1][0] < tod) i++;
    const a = KEYS[i], b = KEYS[Math.min(i + 1, KEYS.length - 1)];
    const t = b[0] === a[0] ? 0 : (tod - a[0]) / (b[0] - a[0]);
    cTop.set(a[1]).lerp(cB.set(b[1]), t);
    cHor.set(a[2]).lerp(cB.set(b[2]), t);
    cSun.set(a[3]).lerp(cB.set(b[3]), t);
    return {
      dir: G.lerp(a[4], b[4], t),
      hem: G.lerp(a[5], b[5], t)
    };
  }

  Sky.init = function (sc) {
    scene = sc;
    hemi = new THREE.HemisphereLight(0xbfd8ff, 0x6a7a52, 0.6);
    scene.add(hemi);
    sun = new THREE.DirectionalLight(0xfff2dd, 1.0);
    sun.position.set(60, 100, 30);
    if (G.shadowsOn) {
      sun.castShadow = true;
      const size = G.quality === 'high' ? 2048 : 1024;
      sun.shadow.mapSize.set(size, size);
      const c = sun.shadow.camera;
      c.near = 20; c.far = 400;
      c.left = -52; c.right = 52; c.top = 52; c.bottom = -52;
      c.updateProjectionMatrix();
      sun.shadow.bias = -0.0008;
      sun.shadow.normalBias = 0.25;
    }
    scene.add(sun);
    scene.add(sun.target);

    // スカイドーム
    const geo = new THREE.SphereGeometry(700, 24, 12);
    const mat = new THREE.ShaderMaterial({
      side: THREE.BackSide,
      depthWrite: false,
      uniforms: {
        uTop: { value: new THREE.Color(0x4a86d0) },
        uHor: { value: new THREE.Color(0xbcd8e8) },
        uSunDir: { value: new THREE.Vector3(0, 1, 0) },
        uSunCol: { value: new THREE.Color(0xfff2dd) },
        uGlow: { value: 0.6 }
      },
      vertexShader: `
        varying vec3 vDir;
        void main(){
          vDir = normalize(position);
          vec4 p = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
          gl_Position = p.xyww;
        }`,
      fragmentShader: `
        uniform vec3 uTop, uHor, uSunCol;
        uniform vec3 uSunDir;
        uniform float uGlow;
        varying vec3 vDir;
        void main(){
          float t = smoothstep(-0.05, 0.35, vDir.y);
          vec3 c = mix(uHor, uTop, t);
          float s = max(dot(normalize(vDir), normalize(uSunDir)), 0.0);
          // 太陽ディスク本体はスプライトが担当。ドームは広い残光のみ
          // (超高指数の点光はチャンネルクリップの縁がリング状に見える)
          c += uSunCol * pow(s, 24.0) * uGlow;
          gl_FragColor = vec4(min(c, vec3(1.0)), 1.0);
        }`
    });
    skyDome = new THREE.Mesh(geo, mat);
    skyDome.frustumCulled = false;
    skyDome.renderOrder = -10;
    scene.add(skyDome);

    // 太陽・月スプライト
    // 本体は通常合成の実体ディスク (加算だと明るい空で中心が飽和して
    // テクスチャの縁だけがリング状に浮くアーティファクトになる)
    sunSpr = new THREE.Sprite(new THREE.SpriteMaterial({
      map: G.makeRadialTex(128, [[0, 'rgba(255,247,225,1)'], [0.38, 'rgba(255,240,205,1)'], [0.48, 'rgba(255,232,185,0.85)'], [0.58, 'rgba(255,224,165,0)'], [1, 'rgba(255,224,165,0)']]),
      transparent: true, depthWrite: false, fog: false
    }));
    sunSpr.scale.set(64, 64, 1);
    scene.add(sunSpr);
    // 柔らかいハローだけ加算合成
    sunHalo = new THREE.Sprite(new THREE.SpriteMaterial({
      map: G.makeRadialTex(128, [[0, 'rgba(255,236,190,0.55)'], [1, 'rgba(255,210,130,0)']]),
      transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, fog: false
    }));
    sunHalo.scale.set(150, 150, 1);
    scene.add(sunHalo);
    moonSpr = new THREE.Sprite(new THREE.SpriteMaterial({
      map: G.makeRadialTex(128, [[0, 'rgba(230,238,255,1)'], [0.18, 'rgba(210,225,255,0.85)'], [0.3, 'rgba(190,210,255,0.2)'], [1, 'rgba(180,200,255,0)']]),
      transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, fog: false
    }));
    moonSpr.scale.set(70, 70, 1);
    scene.add(moonSpr);

    // 星
    const N = 450, sp = [];
    const rnd = G.srand(77);
    for (let i = 0; i < N; i++) {
      const a = rnd() * Math.PI * 2, b = Math.acos(rnd() * 0.95);
      const r = 660;
      sp.push(r * Math.sin(b) * Math.cos(a), r * Math.cos(b), r * Math.sin(b) * Math.sin(a));
    }
    const sgeo = new THREE.BufferGeometry();
    sgeo.setAttribute('position', new THREE.Float32BufferAttribute(sp, 3));
    stars = new THREE.Points(sgeo, new THREE.PointsMaterial({
      color: 0xdfe8ff, size: 1.6, sizeAttenuation: false, transparent: true, opacity: 0,
      depthWrite: false, fog: false
    }));
    stars.frustumCulled = false;
    scene.add(stars);

    // 雲
    const cloudTex = (() => {
      const c = document.createElement('canvas');
      c.width = 256; c.height = 128;
      const g = c.getContext('2d');
      g.clearRect(0, 0, 256, 128);
      const crnd = G.srand(99);
      for (let i = 0; i < 22; i++) {
        const x = 40 + crnd() * 176, y = 40 + crnd() * 48, r = 14 + crnd() * 26;
        const gr = g.createRadialGradient(x, y, 0, x, y, r);
        gr.addColorStop(0, 'rgba(255,255,255,0.5)');
        gr.addColorStop(1, 'rgba(255,255,255,0)');
        g.fillStyle = gr;
        g.fillRect(0, 0, 256, 128);
      }
      return new THREE.CanvasTexture(c);
    })();
    const crnd = G.srand(31);
    for (let i = 0; i < 16; i++) {
      const spm = new THREE.SpriteMaterial({
        map: cloudTex, transparent: true, opacity: 0.55, depthWrite: false, fog: false
      });
      const s = new THREE.Sprite(spm);
      const scl = 90 + crnd() * 160;
      s.scale.set(scl, scl * 0.4, 1);
      s.userData = {
        a: crnd() * Math.PI * 2, r: 180 + crnd() * 380,
        // 滑空高度 (~100m) と交差しない高さに置く (灰色の板が視界を塞ぐ指摘)
        y: 175 + crnd() * 110, sp: 0.002 + crnd() * 0.004
      };
      scene.add(s);
      clouds.push(s);
    }

    // 雨: 落下方向のラインストリーク (点よりも「雨が降っている」ことが伝わる)
    const RN = 500;
    rainN = RN;
    rainPos = new Float32Array(RN * 3);
    rainVel = new Float32Array(RN);
    const rp = new Float32Array(RN * 6);   // 1粒 = 2頂点
    const rrnd = G.srand(55);
    for (let i = 0; i < RN; i++) {
      rainPos[i * 3] = (rrnd() - 0.5) * 60;
      rainPos[i * 3 + 1] = rrnd() * 30;
      rainPos[i * 3 + 2] = (rrnd() - 0.5) * 60;
      rainVel[i] = 22 + rrnd() * 12;
    }
    const rgeo = new THREE.BufferGeometry();
    rgeo.setAttribute('position', new THREE.BufferAttribute(rp, 3));
    rainPts = new THREE.LineSegments(rgeo, new THREE.LineBasicMaterial({
      color: 0xbdd4e6, transparent: true, opacity: 0, depthWrite: false, fog: false
    }));
    rainPts.frustumCulled = false;
    scene.add(rainPts);

    scene.fog = new THREE.Fog(0xbcd8e8, 60, 300);
  };

  Sky.lightLevel = 1;

  const _sunDir = new THREE.Vector3();
  const _lightDir = new THREE.Vector3();
  const _moonDir = new THREE.Vector3();
  const _camXZ = new THREE.Vector3();
  const _grey = new THREE.Color(0x8b98a5);
  const _white = new THREE.Color(0xffffff);
  const _fogC = new THREE.Color();
  const _tint = new THREE.Color();

  /* tod: 0-24, weather: 0(晴)〜1(雨), cam: THREE.Vector3, inCave: 洞窟内 */
  Sky.update = function (dt, tod, weather, cam, inCave) {
    const s = sample(tod);
    _camXZ.set(cam.x, 0, cam.z);
    // 空関連の表示切替
    const skyVisible = !inCave;
    skyDome.visible = skyVisible;
    sunSpr.visible = skyVisible;
    sunHalo.visible = skyVisible;
    moonSpr.visible = skyVisible;
    stars.visible = skyVisible;
    for (const c of clouds) c.visible = skyVisible;
    if (inCave) {
      hemi.intensity = 0.78;
      hemi.color.set(0x9fb0dd);
      hemi.groundColor.set(0x525d7d);
      sun.intensity = 0.02;
      _fogC.set(0x0c1120);
      scene.fog.color.copy(_fogC);
      scene.fog.near = 12;
      scene.fog.far = 82;
      if (scene.background) scene.background.copy(_fogC);
      rainPts.material.opacity = 0;
      const lightC = 0.6;
      Sky.lightLevel = lightC;
      Sky.sunElev = 1;   // 洞窟では影を伸ばさない
      G.World.syncEnv(_fogC, scene.fog.near, scene.fog.far, lightC);
      return;
    }
    // 天候で暗く
    const wDim = 1 - weather * 0.45;
    hemi.intensity = s.hem * wDim;
    // 太陽が低いときは環境光も暖色に (朝夕の空気感)
    const sunLow = G.smoothstep(0.55, 0.12, Math.abs(Math.sin(((tod - 6) / 12) * Math.PI))) *
                   G.smoothstep(4.5, 6, tod) * (1 - G.smoothstep(19.5, 21, tod));
    hemi.color.copy(cTop).lerp(_white, 0.5).lerp(cSun, sunLow * 0.7);
    hemi.groundColor.set(0x6a7a52);
    // 朝夕は地面にも暖色を強くバウンスさせ、空と前景の乖離を防ぐ
    hemi.groundColor.lerp(cSun, sunLow * 0.7);
    // 雨天は地面が濡れて暗くなる
    hemi.groundColor.multiplyScalar(1 - weather * 0.3);
    sun.intensity = s.dir * wDim;
    sun.color.copy(cSun);

    // 太陽の位置 (6時に東から昇り18時に西へ沈む)
    const sunA = ((tod - 6) / 12) * Math.PI; // 高度角パラメータ
    _sunDir.set(Math.cos(sunA) * 0.8, Math.sin(sunA), 0.45).normalize();
    // 照明用の方向は薄暮でも地平線下に沈めない (地形の上向き面が
    // 夕焼け空の下で真っ暗なオリーブ色に落ちる問題への対策)。
    // 見た目の太陽スプライトは実方向のまま沈む
    _lightDir.copy(_sunDir);
    if (s.dir > 0.05 && _lightDir.y < 0.34) {
      // 0.34 まで持ち上げると上向きの地形面にも夕陽の暖色が乗る
      _lightDir.y = 0.34;
      _lightDir.normalize();
    }
    sun.position.copy(_lightDir).multiplyScalar(150).add(_camXZ);
    sun.target.position.set(cam.x, 0, cam.z);
    sun.target.updateMatrixWorld();
    // ブロブ影の方位/伸び用 (夕暮れの長い影)
    Sky.sunAz = Math.atan2(_lightDir.x, _lightDir.z);
    Sky.sunElev = _lightDir.y;

    // ドーム (雨天のグレーは時間帯の明るさに追従して暗くなる)
    const gk = G.clamp(s.hem * 1.6, 0.18, 1);
    _grey.setRGB(0.545 * gk, 0.596 * gk, 0.647 * gk);
    const u = skyDome.material.uniforms;
    u.uTop.value.copy(cTop).lerp(_grey, weather * 0.6);
    u.uHor.value.copy(cHor).lerp(_grey, weather * 0.7);
    u.uSunDir.value.copy(_sunDir);
    u.uSunCol.value.copy(cSun);
    u.uGlow.value = (0.25 + s.dir * 0.6) * (1 - weather * 0.8);
    skyDome.position.set(cam.x, 0, cam.z);

    // 太陽・月
    // ドーム(半径700)の内側に完全に収める (半径ぎりぎりだと球殻と交差し
    // スプライトが欠けてリング状のアーティファクトになる)
    sunSpr.position.copy(_sunDir).multiplyScalar(540).add(_camXZ);
    sunSpr.material.opacity = G.clamp(_sunDir.y + 0.15, 0, 1) * (1 - weather * 0.85);
    sunHalo.position.copy(sunSpr.position);
    sunHalo.material.opacity = sunSpr.material.opacity * 0.8;
    _moonDir.copy(_sunDir).negate();
    moonSpr.position.copy(_moonDir).multiplyScalar(525).add(_camXZ);
    moonSpr.material.opacity = G.clamp(_moonDir.y + 0.1, 0, 0.9) * (1 - weather * 0.85);

    // 星
    const night = G.smoothstep(19.3, 21, tod) + (1 - G.smoothstep(4, 6, tod));
    stars.material.opacity = G.clamp(night, 0, 1) * G.clamp(1 - weather * 1.4, 0, 1) * 0.9;
    stars.position.set(cam.x, 0, cam.z);

    // 雲
    for (const c of clouds) {
      const ud = c.userData;
      ud.a += ud.sp * dt;
      c.position.set(
        cam.x + Math.cos(ud.a) * ud.r,
        ud.y,
        cam.z + Math.sin(ud.a) * ud.r
      );
      c.material.opacity = (0.2 + weather * 0.45) * G.clamp(s.hem * 2, 0.25, 1);
    }

    // 霧 (雪原では少し濃い青に寄せて空と分離)
    _fogC.copy(cHor).lerp(_grey, weather * 0.7);
    const camGh = G.World.heightAt(cam.x, cam.z);
    if (G.World.biomeAt(cam.x, cam.z) === 'snow' || camGh > 46) {
      _fogC.multiplyScalar(0.85);
      _fogC.b = Math.min(1, _fogC.b * 1.14);
    }
    scene.fog.color.copy(_fogC);
    const baseFar = G.Q.chunkRadius * 64 * 0.95;
    const alt = Math.max(0, cam.y - G.World.heightAt(cam.x, cam.z));
    const altBoost = 1 + G.clamp((alt - 8) / 50, 0, 1) * 1.5;  // 高所 (滑空中) は大きく視界を広げる
    scene.fog.far = baseFar * (1 - weather * 0.35) * (0.75 + s.hem * 0.4) * altBoost;
    scene.fog.near = scene.fog.far * 0.22;
    if (scene.background) scene.background.copy(_fogC);
    else scene.background = _fogC.clone();

    // 雨 / 雪パーティクル (雪原バイオームでは常時ゆっくり降る雪に)
    const snowy = G.World.biomeAt(cam.x, cam.z) === 'snow';
    const wantPrecip = weather > 0.5 ? 1 : (snowy ? 0.7 : 0);
    // 止むときは速く消す (晴天の空に雨筋が残留しない)
    rainOn += (wantPrecip - rainOn) * G.damp(wantPrecip < rainOn ? 4.5 : 1.5, dt);
    const snowMode = snowy && weather <= 0.5;
    // 夜間は雨粒を明るく・不透明にして暗背景でも見えるようにする
    const darkF = 1 - G.clamp(s.hem * 1.7, 0, 1);
    rainPts.material.color.set(snowMode ? 0xffffff : 0xaec8dc);
    if (!snowMode) rainPts.material.color.lerp(_white, darkF * 0.85);
    rainPts.material.opacity = rainOn < 0.06 ? 0 : rainOn * (snowMode ? 0.85 : 0.72 + darkF * 0.25);
    rainPts.visible = rainOn > 0.06;
    if (rainOn > 0.02) {
      const pa = rainPts.geometry.attributes.position;
      const fall = snowMode ? 0.12 : 1;
      for (let i = 0; i < rainN; i++) {
        let x = rainPos[i * 3], y = rainPos[i * 3 + 1], z = rainPos[i * 3 + 2];
        y -= rainVel[i] * dt * fall;
        if (snowMode) x += Math.sin(G.time * 1.3 + i) * dt * 0.6;
        if (y < -2) {
          y = 25 + Math.random() * 8;
          x = (Math.random() - 0.5) * 60;
          z = (Math.random() - 0.5) * 60;
        }
        rainPos[i * 3] = x; rainPos[i * 3 + 1] = y; rainPos[i * 3 + 2] = z;
        // 雪は短い点、雨は速度に応じた縦ストリーク
        const len = snowMode ? 0.08 : rainVel[i] * 0.045;
        pa.setXYZ(i * 2, x, y + len, z);
        pa.setXYZ(i * 2 + 1, x, y, z);
      }
      pa.needsUpdate = true;
      rainPts.position.set(cam.x, cam.y, cam.z);
    }

    // 雨天は地形が濡れて暗くなる
    G.World.setWetness(weather * 0.85);

    // 光量 (草/水シェーダ用) と環境同期
    // 地形の Lambert 照明 (hemi+直射) に近い明るさを草/水にも与える
    const light = G.clamp(0.05 + s.hem * 1.4, 0.16, 1.15) * wDim;
    Sky.lightLevel = light;
    _tint.set(0xffffff).lerp(cSun, sunLow * 0.85);
    G.World.syncEnv(_fogC, scene.fog.near, scene.fog.far, light, _tint,
      _sunDir, G.clamp(_sunDir.y * 2.2, 0, 1) * s.dir * wDim);
  };
})();
