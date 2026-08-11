/* =============================================================================
 * ELDRIA — core.js
 * 基盤: 名前空間 / 疑似乱数 / ノイズ / 数学ユーティリティ / イベント / 設定
 * ========================================================================== */
'use strict';
window.G = window.G || {};

/* ---------------- 疑似乱数 (mulberry32) ---------------- */
G.srand = function (seed) {
  let a = seed >>> 0;
  return function () {
    a |= 0; a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
};

/* 座標から決定的なハッシュ値 [0,1) */
G.hash2 = function (x, y) {
  let h = Math.imul(x | 0, 374761393) + Math.imul(y | 0, 668265263) + 0x9E3779B9;
  h = Math.imul(h ^ (h >>> 13), 1274126177);
  return ((h ^ (h >>> 16)) >>> 0) / 4294967296;
};

/* ---------------- 値ノイズ + fBm ---------------- */
(function () {
  const PERM = new Uint8Array(512);
  const rnd = G.srand(1337);
  const p = [];
  for (let i = 0; i < 256; i++) p[i] = i;
  for (let i = 255; i > 0; i--) {
    const j = (rnd() * (i + 1)) | 0;
    const t = p[i]; p[i] = p[j]; p[j] = t;
  }
  for (let i = 0; i < 512; i++) PERM[i] = p[i & 255];

  const GRAD = new Float32Array(512 * 2);
  for (let i = 0; i < 512; i++) {
    const a = (PERM[i] / 256) * Math.PI * 2;
    GRAD[i * 2] = Math.cos(a);
    GRAD[i * 2 + 1] = Math.sin(a);
  }

  function fade(t) { return t * t * t * (t * (t * 6 - 15) + 10); }

  /* 勾配ノイズ 2D — 戻り値おおよそ [-1,1] */
  G.noise2 = function (x, y) {
    const X = Math.floor(x), Y = Math.floor(y);
    const xf = x - X, yf = y - Y;
    const xi = X & 255, yi = Y & 255;
    const aa = PERM[PERM[xi] + yi], ab = PERM[PERM[xi] + yi + 1];
    const ba = PERM[PERM[xi + 1] + yi], bb = PERM[PERM[xi + 1] + yi + 1];
    const u = fade(xf), v = fade(yf);
    const g = (h, dx, dy) => GRAD[h * 2] * dx + GRAD[h * 2 + 1] * dy;
    const x1 = g(aa, xf, yf) + u * (g(ba, xf - 1, yf) - g(aa, xf, yf));
    const x2 = g(ab, xf, yf - 1) + u * (g(bb, xf - 1, yf - 1) - g(ab, xf, yf - 1));
    return (x1 + v * (x2 - x1)) * 1.4;
  };

  G.fbm = function (x, y, oct, lac, gain) {
    oct = oct || 4; lac = lac || 2.0; gain = gain || 0.5;
    let amp = 1, freq = 1, sum = 0, norm = 0;
    for (let i = 0; i < oct; i++) {
      sum += G.noise2(x * freq, y * freq) * amp;
      norm += amp;
      amp *= gain; freq *= lac;
    }
    return sum / norm;
  };

  /* 尾根ノイズ (山脈用) */
  G.ridge = function (x, y, oct) {
    oct = oct || 4;
    let amp = 0.5, freq = 1, sum = 0;
    for (let i = 0; i < oct; i++) {
      sum += (1 - Math.abs(G.noise2(x * freq, y * freq))) * amp;
      amp *= 0.5; freq *= 2.1;
    }
    return sum;
  };
})();

/* ---------------- 数学ユーティリティ ---------------- */
G.clamp = (v, a, b) => (v < a ? a : v > b ? b : v);
G.lerp = (a, b, t) => a + (b - a) * t;
G.smoothstep = (a, b, x) => {
  const t = G.clamp((x - a) / (b - a), 0, 1);
  return t * t * (3 - 2 * t);
};
G.dist2 = (x1, z1, x2, z2) => {
  const dx = x2 - x1, dz = z2 - z1;
  return dx * dx + dz * dz;
};
G.dist = (x1, z1, x2, z2) => Math.sqrt(G.dist2(x1, z1, x2, z2));
/* 角度差 [-PI,PI] */
G.angDiff = (a, b) => {
  let d = (b - a) % (Math.PI * 2);
  if (d > Math.PI) d -= Math.PI * 2;
  if (d < -Math.PI) d += Math.PI * 2;
  return d;
};
G.angLerp = (a, b, t) => a + G.angDiff(a, b) * G.clamp(t, 0, 1);
/* フレームレート非依存の減衰係数 */
G.damp = (rate, dt) => 1 - Math.exp(-rate * dt);

/* ---------------- イベントバス ---------------- */
G.events = (function () {
  const map = {};
  return {
    on(name, fn) { (map[name] = map[name] || []).push(fn); },
    emit(name, data) {
      const l = map[name];
      if (l) for (let i = 0; i < l.length; i++) l[i](data);
    }
  };
})();

/* ---------------- 例外を外へ漏らさない端末ストレージ ---------------- */
G.storage = {
  get(key) {
    try { return localStorage.getItem(key); } catch (e) { return null; }
  },
  set(key, value) {
    try { localStorage.setItem(key, value); return true; } catch (e) { return false; }
  },
  remove(key) {
    try { localStorage.removeItem(key); return true; } catch (e) { return false; }
  }
};

/* ---------------- 設定 (localStorage 永続化) ---------------- */
G.settings = (function () {
  const KEY = 'eldria_settings_v1';
  const def = {
    quality: 'auto',   // 'low' | 'mid' | 'high' | 'auto'
    music: 0.8,
    sfx: 0.9,
    sens: 1.0,         // カメラ感度
    invertY: false,
    showDmg: true,
    shadows: 'auto'    // 'auto' | 'off'
  };
  let raw = {};
  try { raw = JSON.parse(G.storage.get(KEY) || '{}'); } catch (e) { raw = {}; }
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) raw = {};
  const s = Object.assign({}, def, raw);
  if (!['auto', 'low', 'mid', 'high'].includes(s.quality)) s.quality = def.quality;
  if (!Number.isFinite(s.music)) s.music = def.music;
  if (!Number.isFinite(s.sfx)) s.sfx = def.sfx;
  if (!Number.isFinite(s.sens)) s.sens = def.sens;
  s.music = G.clamp(s.music, 0, 1);
  s.sfx = G.clamp(s.sfx, 0, 1);
  s.sens = G.clamp(s.sens, 0.25, 2);
  s.invertY = !!s.invertY;
  s.showDmg = s.showDmg !== false;
  if (!['auto', 'off'].includes(s.shadows)) s.shadows = def.shadows;
  s.save = function () {
    const o = {};
    for (const k in def) o[k] = s[k];
    G.storage.set(KEY, JSON.stringify(o));
  };
  return s;
})();

/* 実効品質: 'auto' は端末から推定 */
G.quality = (function () {
  if (G.settings.quality !== 'auto') return G.settings.quality;
  const mobile = /Android|iPhone|iPad|Mobile/i.test(navigator.userAgent);
  const mem = navigator.deviceMemory || 4;
  const cores = navigator.hardwareConcurrency || 4;
  if (mobile && (mem <= 3 || cores <= 4)) return 'low';
  if (mobile) return 'mid';
  return 'high';
})();

G.QUALITY = {
  low:  { dpr: 1.0, chunkRadius: 3, grassRadius: 1, grassPerChunk: 500,  particles: 500 },
  mid:  { dpr: 1.5, chunkRadius: 4, grassRadius: 1, grassPerChunk: 1100, particles: 900 },
  high: { dpr: 2.0, chunkRadius: 5, grassRadius: 2, grassPerChunk: 1100, particles: 1400 }
};
// 実行時の負荷制御で値を調整してもプリセット定義を壊さないよう複製する。
G.Q = Object.assign({}, G.QUALITY[G.quality] || G.QUALITY.mid);

/* ---------------- 30fps基準のモバイル負荷制御 ---------------- */
G.PerformanceGovernor = (function () {
  const FLOORS = { low: 0.72, mid: 0.64, high: 0.58 };
  const round = v => Math.round(v * 1000) / 1000;
  return {
    initial() {
      return { resolution: 1, detail: 1, slow: 0, critical: 0, fast: 0 };
    },
    step(previous, frameMs, quality) {
      const p = previous || this.initial();
      const n = {
        resolution: Number.isFinite(p.resolution) ? p.resolution : 1,
        detail: Number.isFinite(p.detail) ? p.detail : 1,
        slow: p.slow || 0,
        critical: p.critical || 0,
        fast: p.fast || 0
      };
      if (!Number.isFinite(frameMs) || frameMs <= 0 || frameMs >= 150) return n;
      const floor = FLOORS[quality] || FLOORS.mid;

      // 33.3ms (30fps) は快適域として維持。2回続けて28fpsを下回った時だけ
      // 解像度を落とし、瞬間的な戦闘エフェクトで画質が揺れないようにする。
      n.slow = frameMs > 36 ? n.slow + 1 : 0;
      if (n.slow >= 2) {
        n.resolution = Math.max(floor, n.resolution - 0.12);
        n.slow = 0;
      }

      // GPU解像度を下げ切っても24fpsを割るならCPU/ドローコール側が律速。
      // 遠景・草・粒子を二段目として絞り、最低でも世界の輪郭は残す。
      n.critical = frameMs > 42 && n.resolution <= floor + 0.001 ? n.critical + 1 : 0;
      if (n.critical >= 2) {
        n.detail = Math.max(0.72, n.detail - 0.12);
        n.critical = 0;
      }

      n.fast = frameMs < 24 ? n.fast + 1 : 0;
      if (n.fast >= 4) {
        if (n.resolution < 1) n.resolution = Math.min(1, n.resolution + 0.08);
        else if (n.detail < 1) n.detail = Math.min(1, n.detail + 0.08);
        n.fast = 0;
      }
      n.resolution = round(n.resolution);
      n.detail = round(n.detail);
      return n;
    }
  };
})();

G.isTouch = ('ontouchstart' in window) || navigator.maxTouchPoints > 0;

/* グローバル時間 (メインループが更新) */
G.time = 0;
