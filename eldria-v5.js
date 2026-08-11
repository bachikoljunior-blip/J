
/* ===== js/core.js ===== */
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
    haptics: true,
    shake: 0.8,
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
  s.haptics = s.haptics !== false;
  if (!Number.isFinite(s.shake)) s.shake = def.shake;
  s.shake = G.clamp(s.shake, 0, 1);
  if (!['auto', 'off'].includes(s.shadows)) s.shadows = def.shadows;
  s.save = function () {
    const o = {};
    for (const k in def) o[k] = s[k];
    G.storage.set(KEY, JSON.stringify(o));
  };
  return s;
})();

/* ---------------- モバイル触覚フィードバック ---------------- */
G.haptic = function (pattern) {
  if (!G.settings.haptics || !navigator.vibrate) return false;
  try { return navigator.vibrate(pattern); } catch (e) { return false; }
};

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

/* ===== js/audio.js ===== */
/* =============================================================================
 * ELDRIA — audio.js
 * WebAudio による完全プロシージャル音響。外部アセット無し。
 * 音楽: 平穏 / 戦闘 / ボス / 夜 のレイヤー切替。効果音: 合成。
 * ========================================================================== */
'use strict';
(function () {
  const A = G.Audio = {};
  let ctx = null, master = null, musicBus = null, sfxBus = null, rainNode = null;
  let started = false;

  A.ready = () => !!ctx;

  /* 初回のユーザー操作で呼ぶ */
  A.init = function () {
    if (ctx) { if (ctx.state === 'suspended') ctx.resume(); return; }
    try {
      ctx = new (window.AudioContext || window.webkitAudioContext)();
    } catch (e) { return; }
    master = ctx.createGain();
    master.gain.value = 1.0;
    master.connect(ctx.destination);

    musicBus = ctx.createGain();
    musicBus.gain.value = G.settings.music;
    musicBus.connect(master);

    sfxBus = ctx.createGain();
    sfxBus.gain.value = G.settings.sfx;
    sfxBus.connect(master);

    startSequencer();
    started = true;

    document.addEventListener('visibilitychange', () => {
      if (!document.hidden && ctx && ctx.state === 'suspended') ctx.resume();
    });
  };

  A.setMusicVol = v => { if (musicBus) musicBus.gain.value = v; };
  A.setSfxVol = v => { if (sfxBus) sfxBus.gain.value = v; };

  /* ======================= 効果音 ======================= */
  function noiseBuffer(len) {
    const n = ctx.createBuffer(1, (ctx.sampleRate * len) | 0, ctx.sampleRate);
    const d = n.getChannelData(0);
    for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
    return n;
  }
  let _noise = null;
  function getNoise() { return _noise || (_noise = noiseBuffer(1.0)); }

  function env(g, t0, a, d, peak, sustain) {
    g.gain.setValueAtTime(0.0001, t0);
    g.gain.linearRampToValueAtTime(peak, t0 + a);
    g.gain.exponentialRampToValueAtTime(Math.max(sustain || 0.0001, 0.0001), t0 + a + d);
  }

  function tone(freq, type, a, d, peak, opts) {
    if (!ctx) return;
    opts = opts || {};
    const t0 = ctx.currentTime + (opts.delay || 0);
    const o = ctx.createOscillator();
    o.type = type;
    o.frequency.setValueAtTime(freq, t0);
    if (opts.glide) o.frequency.exponentialRampToValueAtTime(Math.max(opts.glide, 1), t0 + a + d);
    const g = ctx.createGain();
    env(g, t0, a, d, peak);
    o.connect(g); g.connect(opts.bus || sfxBus);
    o.start(t0); o.stop(t0 + a + d + 0.1);
  }

  function noiseHit(a, d, peak, filterFreq, q, opts) {
    if (!ctx) return;
    opts = opts || {};
    const t0 = ctx.currentTime + (opts.delay || 0);
    const src = ctx.createBufferSource();
    src.buffer = getNoise(); src.loop = true;
    const f = ctx.createBiquadFilter();
    f.type = opts.ftype || 'bandpass';
    f.frequency.setValueAtTime(filterFreq, t0);
    if (opts.fglide) f.frequency.exponentialRampToValueAtTime(Math.max(opts.fglide, 20), t0 + a + d);
    f.Q.value = q || 1;
    const g = ctx.createGain();
    env(g, t0, a, d, peak);
    src.connect(f); f.connect(g); g.connect(opts.bus || sfxBus);
    src.start(t0); src.stop(t0 + a + d + 0.1);
  }

  const SFX = {
    swing()      { noiseHit(0.01, 0.14, 0.25, 1200, 1.2, { fglide: 300 }); },
    swingHeavy() { noiseHit(0.02, 0.25, 0.32, 700, 1.0, { fglide: 150 }); },
    hit() {
      tone(90, 'sine', 0.005, 0.14, 0.5, { glide: 40 });
      noiseHit(0.004, 0.09, 0.35, 2500, 0.8, { fglide: 500 });
    },
    hitPlayer() {
      tone(70, 'sine', 0.005, 0.22, 0.6, { glide: 30 });
      noiseHit(0.004, 0.12, 0.3, 900, 1.0, { fglide: 200 });
    },
    clang() {
      tone(1300, 'square', 0.002, 0.1, 0.08);
      tone(1750, 'square', 0.002, 0.14, 0.06);
      noiseHit(0.002, 0.06, 0.2, 4000, 2);
    },
    roll()   { noiseHit(0.03, 0.22, 0.16, 500, 0.7, { fglide: 180 }); },
    step()   { noiseHit(0.003, 0.05, 0.045, 700 + Math.random() * 300, 0.8); },
    jump()   { noiseHit(0.02, 0.1, 0.1, 800, 1, { fglide: 1600 }); },
    land()   { tone(90, 'sine', 0.004, 0.1, 0.2, { glide: 50 }); },
    pickup() {
      tone(660, 'sine', 0.005, 0.12, 0.16);
      tone(990, 'sine', 0.005, 0.16, 0.14, { delay: 0.07 });
    },
    gold() {
      tone(1320, 'triangle', 0.003, 0.1, 0.14);
      tone(1760, 'triangle', 0.003, 0.12, 0.12, { delay: 0.05 });
    },
    potion() {
      tone(520, 'sine', 0.02, 0.25, 0.16, { glide: 780 });
      noiseHit(0.05, 0.2, 0.06, 3000, 1);
    },
    levelup() {
      const seq = [523, 659, 784, 1047];
      seq.forEach((f, i) => tone(f, 'triangle', 0.01, 0.3, 0.2, { delay: i * 0.09 }));
    },
    questDone() {
      const seq = [587, 784, 880, 1175];
      seq.forEach((f, i) => tone(f, 'sine', 0.01, 0.4, 0.18, { delay: i * 0.12 }));
    },
    ui()     { tone(880, 'sine', 0.002, 0.06, 0.08); },
    uiOpen() { tone(660, 'sine', 0.004, 0.1, 0.09); tone(880, 'sine', 0.004, 0.1, 0.07, { delay: 0.05 }); },
    death() {
      tone(220, 'sawtooth', 0.02, 1.6, 0.25, { glide: 55 });
      tone(110, 'sine', 0.02, 2.0, 0.3, { glide: 40 });
    },
    enemyDie() {
      tone(160, 'sawtooth', 0.005, 0.3, 0.2, { glide: 60 });
      noiseHit(0.01, 0.25, 0.15, 800, 1, { fglide: 150 });
    },
    roar() {
      tone(70, 'sawtooth', 0.08, 1.2, 0.4, { glide: 45 });
      tone(105, 'sawtooth', 0.08, 1.1, 0.3, { glide: 60 });
      noiseHit(0.1, 1.0, 0.22, 400, 0.6, { fglide: 120 });
    },
    fireball() { noiseHit(0.05, 0.5, 0.25, 900, 0.8, { fglide: 200 }); },
    explode() {
      tone(60, 'sine', 0.005, 0.5, 0.5, { glide: 25 });
      noiseHit(0.005, 0.45, 0.4, 500, 0.5, { fglide: 90, ftype: 'lowpass' });
    },
    shrine() {
      const seq = [392, 523, 659, 784, 1047];
      seq.forEach((f, i) => tone(f, 'sine', 0.02, 0.8, 0.13, { delay: i * 0.15 }));
    },
    arrow()  { noiseHit(0.005, 0.12, 0.12, 2200, 2, { fglide: 900 }); },
    bird() {
      const base = 1800 + Math.random() * 1200;
      tone(base, 'sine', 0.01, 0.08, 0.06, { glide: base * 1.4 });
      tone(base * 1.15, 'sine', 0.01, 0.1, 0.05, { delay: 0.12, glide: base * 0.9 });
      if (Math.random() < 0.5) tone(base * 0.9, 'sine', 0.01, 0.07, 0.045, { delay: 0.26, glide: base * 1.3 });
    },
    cricket() {
      for (let i = 0; i < 5; i++) {
        tone(4200 + Math.random() * 400, 'sine', 0.004, 0.03, 0.025, { delay: i * 0.07 });
      }
    },
    windgust() { noiseHit(0.7, 1.6, 0.05, 500, 0.4, { fglide: 250, ftype: 'bandpass' }); },
    drip() {
      tone(900 + Math.random() * 500, 'sine', 0.002, 0.18, 0.07, { glide: 300 });
    },
    thunder() {
      tone(50, 'sawtooth', 0.01, 1.8, 0.3, { glide: 30 });
      noiseHit(0.01, 1.5, 0.25, 300, 0.5, { fglide: 80, ftype: 'lowpass' });
    }
  };

  A.sfx = function (name) {
    if (!ctx || ctx.state !== 'running') return;
    const fn = SFX[name];
    if (fn) fn();
  };

  /* ======================= 雨 ======================= */
  A.setRain = function (on) {
    if (!ctx) return;
    if (on && !rainNode) {
      const src = ctx.createBufferSource();
      src.buffer = getNoise(); src.loop = true;
      const f = ctx.createBiquadFilter();
      f.type = 'lowpass'; f.frequency.value = 1400; f.Q.value = 0.4;
      const g = ctx.createGain();
      g.gain.value = 0;
      g.gain.linearRampToValueAtTime(0.05, ctx.currentTime + 2.5);
      src.connect(f); f.connect(g); g.connect(sfxBus);
      src.start();
      rainNode = { src, g };
    } else if (!on && rainNode) {
      const r = rainNode; rainNode = null;
      r.g.gain.linearRampToValueAtTime(0.0001, ctx.currentTime + 2.5);
      setTimeout(() => { try { r.src.stop(); } catch (e) {} }, 2800);
    }
  };

  /* ======================= 音楽シーケンサ ======================= */
  /* 状態: 'title' | 'peace' | 'combat' | 'boss' | 'none' */
  let musicState = 'none';
  let intensity = 0;            // 0=平穏 1=戦闘 (クロスフェード)
  let bossMode = false;

  A.setMusic = function (state) {
    if (musicState === state) return;
    musicState = state;
    bossMode = (state === 'boss');
  };
  A.getMusic = () => musicState;

  /* コード進行 (Aマイナー界隈, 度数は半音) — 荘厳で寂しげなオープンワールド風 */
  const PROG_PEACE = [
    [57, 60, 64], [53, 57, 60], [55, 59, 62], [52, 55, 59]   // Am F G Em
  ];
  const PROG_BOSS = [
    [50, 53, 57], [50, 53, 56], [48, 51, 55], [55, 58, 62]   // Dm Ddim Cm Gm
  ];
  const SCALE = [57, 59, 60, 62, 64, 65, 67, 69, 71, 72, 74, 76]; // Aナチュラルマイナー

  const mtof = m => 440 * Math.pow(2, (m - 69) / 12);

  let seqTimer = null, stepIdx = 0, chordIdx = 0;
  const STEP = 0.22; // 秒/16分

  function padChord(notes, t0, dur, gain) {
    for (let i = 0; i < notes.length; i++) {
      const o = ctx.createOscillator();
      o.type = 'sine';
      o.frequency.value = mtof(notes[i]);
      const o2 = ctx.createOscillator();
      o2.type = 'triangle';
      o2.frequency.value = mtof(notes[i] - 12);
      const g = ctx.createGain();
      g.gain.setValueAtTime(0.0001, t0);
      g.gain.linearRampToValueAtTime(gain, t0 + dur * 0.35);
      g.gain.linearRampToValueAtTime(0.0001, t0 + dur * 1.05);
      o.connect(g); o2.connect(g); g.connect(musicBus);
      o.start(t0); o.stop(t0 + dur * 1.1);
      o2.start(t0); o2.stop(t0 + dur * 1.1);
    }
  }

  function pluck(midi, t0, gain, type) {
    const o = ctx.createOscillator();
    o.type = type || 'triangle';
    o.frequency.value = mtof(midi);
    const g = ctx.createGain();
    g.gain.setValueAtTime(0.0001, t0);
    g.gain.linearRampToValueAtTime(gain, t0 + 0.01);
    g.gain.exponentialRampToValueAtTime(0.0001, t0 + 0.5);
    o.connect(g); g.connect(musicBus);
    o.start(t0); o.stop(t0 + 0.6);
  }

  function drum(t0, kind, gain) {
    if (kind === 'kick') {
      const o = ctx.createOscillator();
      o.type = 'sine';
      o.frequency.setValueAtTime(120, t0);
      o.frequency.exponentialRampToValueAtTime(40, t0 + 0.12);
      const g = ctx.createGain();
      g.gain.setValueAtTime(gain, t0);
      g.gain.exponentialRampToValueAtTime(0.0001, t0 + 0.18);
      o.connect(g); g.connect(musicBus);
      o.start(t0); o.stop(t0 + 0.25);
    } else { // タム/ハット
      const src = ctx.createBufferSource();
      src.buffer = getNoise(); src.loop = true;
      const f = ctx.createBiquadFilter();
      f.type = kind === 'hat' ? 'highpass' : 'bandpass';
      f.frequency.value = kind === 'hat' ? 6000 : 300;
      const g = ctx.createGain();
      g.gain.setValueAtTime(gain, t0);
      g.gain.exponentialRampToValueAtTime(0.0001, t0 + (kind === 'hat' ? 0.05 : 0.2));
      src.connect(f); f.connect(g); g.connect(musicBus);
      src.start(t0); src.stop(t0 + 0.3);
    }
  }

  function startSequencer() {
    let nextTime = ctx.currentTime + 0.1;
    stepIdx = 0; chordIdx = 0;
    const rnd = G.srand((Date.now() & 0xffff) | 1);

    seqTimer = setInterval(() => {
      if (!ctx || ctx.state !== 'running') return;
      if (musicState === 'none' || document.hidden) { nextTime = ctx.currentTime + 0.1; return; }

      // 目標インテンシティへ滑らかに移行
      const target = (musicState === 'combat' || musicState === 'boss') ? 1 : 0;
      intensity += (target - intensity) * 0.06;

      while (nextTime < ctx.currentTime + 0.35) {
        const t = nextTime;
        const s = stepIdx & 15;
        const prog = bossMode ? PROG_BOSS : PROG_PEACE;

        if (s === 0) {
          const chord = prog[chordIdx % prog.length];
          chordIdx++;
          padChord(chord, t, STEP * 16, bossMode ? 0.05 : 0.045);
          if (bossMode) {
            // 低音ドローン
            pluck(chord[0] - 24, t, 0.12, 'sawtooth');
          }
        }

        // 静かな旋律 (平穏時は疎、戦闘時は密)
        const density = 0.1 + intensity * 0.32 + (bossMode ? 0.15 : 0);
        if ((s % 2 === 0) && rnd() < density) {
          const note = SCALE[(rnd() * SCALE.length) | 0] + (bossMode ? -5 : 0);
          pluck(note, t, 0.05 + intensity * 0.04, intensity > 0.5 ? 'square' : 'triangle');
        }

        // 打楽器は戦闘時のみ
        if (intensity > 0.25) {
          if (s === 0 || s === 8) drum(t, 'kick', 0.22 * intensity);
          if (bossMode && (s === 4 || s === 12)) drum(t, 'tom', 0.18 * intensity);
          if (s % 4 === 2) drum(t, 'hat', 0.05 * intensity);
        }

        stepIdx++;
        nextTime += STEP;
      }
    }, 120);
  }
})();

/* ===== js/world.js ===== */
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

  /* 月ディスク: 実体円盤+海(暗斑)+縁の減光。ぼやけた光球ではなく「月」と読める形 */
  G.makeMoonTex = function (size) {
    const c = document.createElement('canvas');
    c.width = c.height = size;
    const g = c.getContext('2d');
    const h = size / 2, r = h * 0.86;
    g.beginPath(); g.arc(h, h, r, 0, Math.PI * 2);
    g.fillStyle = '#dfe7f4'; g.fill();
    g.save();
    g.beginPath(); g.arc(h, h, r, 0, Math.PI * 2); g.clip();
    g.fillStyle = 'rgba(168,182,205,0.55)';
    const maria = [[-0.28, -0.22, 0.3], [0.18, -0.05, 0.24], [-0.05, 0.3, 0.2], [0.32, 0.28, 0.13], [-0.38, 0.12, 0.11]];
    for (const [mx, my, mr] of maria) {
      g.beginPath(); g.arc(h + mx * r, h + my * r, mr * r, 0, Math.PI * 2); g.fill();
    }
    const sh = g.createRadialGradient(h - r * 0.3, h - r * 0.3, r * 0.2, h, h, r);
    sh.addColorStop(0, 'rgba(0,0,0,0)');
    sh.addColorStop(0.75, 'rgba(30,40,70,0.08)');
    sh.addColorStop(1, 'rgba(30,40,70,0.4)');
    g.fillStyle = sh; g.fillRect(0, 0, size, size);
    g.restore();
    return new THREE.CanvasTexture(c);
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
  const CAVE_FLOOR = new THREE.Color(0x565d6f);
  const CAVE_FLOOR2 = new THREE.Color(0x3d4456);
  const CAVE_WALL = new THREE.Color(0x262b3a);
  const FROST_COL = new THREE.Color(0xafccdf);   // 白狼が床に溶けない淡青
  const CHAR_COL = new THREE.Color(0x2e2824);
  const _dirtCol = new THREE.Color(0x6a5844);
  const _snowShade = new THREE.Color(0xb4c4da);
  // 崖の地層3色 (雪・空と色相が分離する暖灰〜茶)
  const _strata1 = new THREE.Color(0x84705c);
  const _strata2 = new THREE.Color(0x635a50);
  const _strata3 = new THREE.Color(0x75685a);
  const _winWarm = new THREE.Color(0xffd88a);
  function groundColor(x, z, h, out, ny) {
    if (W.inCaveRegion(x, z)) {
      // 洞窟の床: 青灰のまだら。壁の立ち上がりに向けて暗く落とす
      // (床も壁も同じ明るさだと空間の輪郭が消え、霧の虚空に見える)
      const m = G.fbm(x * 0.11, z * 0.11, 2) * 0.5 + 0.5;
      out.copy(CAVE_FLOOR).lerp(CAVE_FLOOR2, m);
      const wr = G.smoothstep(30, 48, G.dist(x, z, W.CAVE.cx, W.CAVE.cz));
      out.lerp(CAVE_WALL, wr);
      return out;
    }
    // バイオーム境界は座標を揺らしてディザ (定規で引いた直線帯の解消)。
    // 振幅は広め — 草原⇔凍土などの遷移が遠景でハードカットに見えない幅
    const jx = G.noise2(x * 0.09 + 31, z * 0.09) * 14;
    const jz = G.noise2(x * 0.09, z * 0.09 + 77) * 14;
    const b = W.biomeAt(x + jx, z + jz, h);
    out.copy(BIOME_COL[b] || BIOME_COL.grass);
    const pb = pathBlend(x, z);
    if (pb > 0) out.lerp(PATH_COL, pb * 0.85);
    // 雪面の起伏まだら + 風紋の青い影 (無地の白平面に情報量を足す)
    if (b === 'snow') {
      out.multiplyScalar(0.88 + (G.fbm(x * 0.05, z * 0.05, 2) * 0.5 + 0.5) * 0.16);
      const bl = G.fbm(x * 0.02 + 41, z * 0.02, 2) * 0.5 + 0.5;
      out.lerp(_snowShade, G.smoothstep(0.55, 0.85, bl) * 0.3);
    }
    // 岩肌の縞ムラ+土の帯 (滑空時の眼下が無地のスメアにならないように)。
    // 暗側の下限を上げる — 多重の暗化が重なると崖全体が煤けたスミアになる
    if (b === 'rock') {
      out.multiplyScalar(0.78 + (G.fbm(x * 0.07, z * 0.07, 2) * 0.5 + 0.5) * 0.42);
      const dirt = G.fbm(x * 0.035 + 17, z * 0.035, 2) * 0.5 + 0.5;
      out.lerp(_dirtCol, G.smoothstep(0.6, 0.85, dirt) * 0.4);
    }
    if (b === 'grass') {
      const t = G.fbm(x * 0.012 + 55, z * 0.012 + 55, 2) * 0.5 + 0.5;
      out.lerp(BIOME_COL.grass2, t * 0.8);
      // 細かい第2オクターブの濃淡 (正午の平坦な単色ベタを避ける)
      out.multiplyScalar(0.95 + (G.fbm(x * 0.06 + 3, z * 0.06, 2) * 0.5 + 0.5) * 0.1);
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
    // 急斜面 (崖面) は色相を分離した岩アルベド+ワールドYの段階色地層。
    // sin縞の明暗だけでは遠景LODの粗い頂点で潰れて無彩色のスミアになる —
    // 大きな帯単位で色そのものを変えると粗い頂点密度でも層が読める
    const steep = G.smoothstep(0.3, 0.55, slope);
    if (steep > 0.01) {
      // 帯高14m: 遠景LODの巨大三角形でも1帯が複数頂点にまたがり層が残る
      const bi = ((Math.floor((h + G.noise2(x * 0.045, z * 0.045) * 6) / 14) % 3) + 3) % 3;
      out.lerp(bi === 0 ? _strata1 : bi === 1 ? _strata2 : _strata3, steep * 0.65);
    }
    // 水中は砂色へ
    if (h < WATER_Y + 0.4) {
      out.lerp(BIOME_COL.under, G.smoothstep(WATER_Y + 0.4, WATER_Y - 2.5, h));
    }
    // フェンリルの凍土アリーナ (バイオームまだらの後に適用しないと緑に戻される)。
    // 縁の半径をノイズで揺らし、円盤のハードエッジを崩す
    const fd = G.dist2(x, z, -430, -140);
    if (fd < 42 * 42) {
      const fr2 = Math.sqrt(fd) + G.noise2(x * 0.08, z * 0.08) * 5;
      out.lerp(FROST_COL, (1 - G.smoothstep(26, 38, fr2)) * 0.88);
    }
    // 竜の頂の焦土 (中心ほど濃く、ひび割れ状の明暗ムラ)
    const dd = G.dist2(x, z, -40, -640);
    if (dd < 40 * 40) {
      const dr = Math.sqrt(dd) + G.noise2(x * 0.08 + 9, z * 0.08) * 5;
      out.lerp(CHAR_COL, (1 - G.smoothstep(18, 34, dr)) * 0.85);
      const crack = G.fbm(x * 0.22, z * 0.22, 2);
      out.multiplyScalar(0.8 + (crack * 0.5 + 0.5) * 0.4);
      // 中心付近は残り火の熱がわずかに透ける
      if (dr < 14) out.r += (1 - dr / 14) * 0.05;
    }
    // 高度の微妙な明暗。急斜面はジッタを増やし、面中央の「ボケた土の壁」を防ぐ
    const shade = 0.92 + G.hash2((x * 7) | 0, (z * 7) | 0) * 0.08;
    out.multiplyScalar(shade * (1 + (G.hash2((x * 3) | 0, (z * 3) | 0) - 0.5) * 0.16 * steep));
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
    // 肘 (幹と腕をつなぐ水平セグメント)。無いと腕が幹の横に浮かぶ平行柱に
    // 見え、サワロサボテンとして読めない
    const cacElbow = new THREE.CylinderGeometry(0.24, 0.24, 0.62, 6);
    cacElbow.rotateZ(Math.PI / 2);
    const cactus = G.mergeGeo([
      { geo: cacBody, m: M4(0, 1.5, 0), color: 0x5f8f4a },
      { geo: cacArm, m: M4(0.62, 1.9, 0, 0, 1), color: 0x69994f },
      { geo: cacArm, m: M4(-0.62, 1.4, 0, 0, 1), color: 0x69994f },
      { geo: cacElbow, m: M4(0.35, 1.32, 0), color: 0x69994f },
      { geo: cacElbow, m: M4(-0.35, 0.85, 0), color: 0x69994f }
    ]);
    cacBody.dispose(); cacArm.dispose(); cacElbow.dispose();

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
  // 植生の接地影 (柔らかい放射グラデの円盤。全チャンク共有)
  let vegShadowGeo = null, vegShadowMat = null;
  function ensureVegShadow() {
    if (vegShadowGeo) return;
    vegShadowGeo = new THREE.PlaneGeometry(2, 2);
    vegShadowGeo.rotateX(-Math.PI / 2);
    vegShadowMat = new THREE.MeshBasicMaterial({
      map: G.makeRadialTex(64, [[0, 'rgba(8,12,18,0.5)'], [0.65, 'rgba(8,12,18,0.3)'], [1, 'rgba(8,12,18,0)']]),
      transparent: true, depthWrite: false
    });
  }

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
        uLight: { value: 1.0 },
        uTint: { value: new THREE.Color(0xffffff) }
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
        uniform vec3 uFogColor, uTint;
        uniform float uFogNear, uFogFar, uLight;
        void main(){
          float f = smoothstep(uFogNear, uFogFar, vDist);
          // 朝夕の暖色ティントを草にも乗せる (木々だけ暗く沈み草が自己発光
          // して見える乖離の解消)
          vec3 c = mix(vColor * uLight * uTint, uFogColor, f);
          gl_FragColor = vec4(c, 1.0);
        }`,
      side: THREE.DoubleSide
    });
  }

  /* ======================= チャンク管理 ======================= */
  const chunks = new Map();     // "cx,cz" -> chunk
  let scene = null;
  const buildQueue = [];
  let runtimeDetail = 1;

  function effectiveChunkRadius() {
    return Math.max(3, Math.round(G.Q.chunkRadius * runtimeDetail));
  }

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
    const shadowSpots = [];   // 植生の接地ブロブ影 (世界が浮いて見える指摘)
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
        if (type === 'pine' || type === 'oak') shadowSpots.push({ x, z, h, s: sc * 1.5 });
        else if (type === 'cactus' || type === 'dead') shadowSpots.push({ x, z, h, s: sc * 0.8 });
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
    // 植生の接地ブロブ影 (1チャンク1インスタンスメッシュ。静的な柔らかいAO円)
    if (shadowSpots.length) {
      ensureVegShadow();
      const sm = new THREE.InstancedMesh(vegShadowGeo, vegShadowMat, shadowSpots.length);
      const m2 = new THREE.Matrix4();
      for (let i = 0; i < shadowSpots.length; i++) {
        const p = shadowSpots[i];
        m2.makeScale(p.s, 1, p.s);
        m2.setPosition(p.x, p.h + 0.05, p.z);
        sm.setMatrixAt(i, m2);
      }
      sm.instanceMatrix.needsUpdate = true;
      sm.frustumCulled = false;
      sm.renderOrder = 1;
      scene.add(sm);
      chunk.trees.push(sm);
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
    const max = Math.max(240, Math.floor(G.Q.grassPerChunk * runtimeDetail));
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

  // フラットシェーディング: 面ごとの法線で陰影が立ち、崖・起伏が
  // 「無構造のぼかしスミア」にならない (ローポリ美術の様式とも一致)
  const terrainMat = new THREE.MeshLambertMaterial({ vertexColors: true, flatShading: true });
  // 雨天の濡れ表現: 地形アルベドを暗く沈める uniform を注入
  terrainMat.onBeforeCompile = sh => {
    sh.uniforms.uWet = { value: 0 };
    sh.fragmentShader = 'uniform float uWet;\n' + sh.fragmentShader.replace(
      '#include <color_fragment>',
      '#include <color_fragment>\n' +
      '  diffuseColor.rgb *= (1.0 - uWet * 0.3);\n' +
      '  // 濡れた地面は青みがかった光沢感 (単なる暗化に見せない)\n' +
      '  diffuseColor.rgb = mix(diffuseColor.rgb, diffuseColor.rgb * vec3(0.92, 0.97, 1.12), uWet * 0.6);'
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
          // 角度依存フレネル: 浅い角度ほど空を強く映す。反射色は空色に
          // 弱い青バイアス — 夕刻に純粋な暖色フォグを映すと砂浜と同化するが、
          // 青すぎると今度は夕空の色を全く拾わない
          vec3 skyRef = mix(uFogColor, uFogColor * vec3(0.55, 0.78, 1.1), 0.35);
          float fr = 0.2 + 0.62 * pow(1.0 - max(dot(vd, n), 0.0), 3.0);
          fr += smoothstep(12.0, 140.0, vDist) * 0.3;
          c = mix(c, skyRef, clamp(fr, 0.0, 0.85));
          // 太陽のスペキュラ: 鋭い芯 + カメラ→太陽方位に整列した細長い光条。
          // 広ローブの面発光は湖面全体に散って「拡散した白いシート」になる —
          // 光条は方位整列 (幅) × 波形 (きらめき) で明示的に描く
          vec3 sd = normalize(uSunDir);
          vec3 h = normalize(vd + sd);
          float ndh = max(dot(n, h), 0.0);
          float lowSun = clamp(1.7 - sd.y * 2.4, 0.5, 1.7);
          vec2 toFrag = normalize(vWorld.xz - cameraPosition.xz);
          float azRaw = max(dot(toFrag, normalize(sd.xz)), 0.0);
          float az = pow(azRaw, 42.0);
          // スペキュラ全体を方位整列でゲートする — 輝度クランプでは形が
          // 丸いままなので、太陽方位の細い帯以外では発光させない (筋の強制)
          float sparkle = 0.35 + 0.65 * smoothstep(0.0, 0.28, abs(vWave));
          float spec = (min(pow(ndh, 160.0) * 0.9, 0.5) + sparkle * 0.6 * lowSun) * az;
          // 光条は太陽が傾き始めた時点から太陽色へ寄せる (無彩色の白灰にしない)
          vec3 specTint = mix(uSunTint, vec3(1.0, 0.62, 0.3), clamp((lowSun - 0.7) * 0.8, 0.0, 0.6));
          c += specTint * spec * uSunI;
          // 夕刻は水面ベースにも空の暖色を薄く乗せる (空との色乖離の解消)
          c = mix(c, skyRef, clamp((lowSun - 1.0) * 0.28, 0.0, 0.35));
          // 波頭の白泡: 光量に殆ど依存しない自己発光的な白
          // (夕刻・曇天でuLightに比例させると泡が一度も見えない)
          c += vec3(0.88, 0.92, 0.96) * smoothstep(0.14, 0.36, vWave) * (0.2 + 0.2 * uLight);
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
  /* (ex,ez,eh) 指定時はカメラ→その地点 (交戦ボス) の視線も遮蔽判定に含める
     — ボス戦で黒曜石柱がブレスの見せ場を塞ぐ指摘への対応 */
  W.updateFaders = function (dt, ax, az, bx, bz, ay, by, ex, ez, eh) {
    const segs = [[ax, az, ay]];
    if (ex !== undefined) segs.push([ex, ez, eh]);
    const k = G.damp(9, dt);
    for (const f of W.faders) {
      let target = 1;
      for (let s = 0; s < segs.length && target === 1; s++) {
        const [sx, sz, sy] = segs[s];
        if (Math.abs(f.x - sx) >= 60 || Math.abs(f.z - sz) >= 60) continue;
        const dx = bx - sx, dz = bz - sz;
        const len2 = Math.max(dx * dx + dz * dz, 0.01);
        const t = G.clamp(((f.x - sx) * dx + (f.z - sz) * dz) / len2, 0.02, 0.98);
        const px = sx + dx * t, pz = sz + dz * t;
        const rr = f.r + 0.55;
        // 水平に視線と交差し、かつ視線がその高さを越えていない場合のみフェード
        if (G.dist2(px, pz, f.x, f.z) < rr * rr && sy + (by - sy) * t < f.topY + 0.4) target = 0.24;
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
    // 窓 (夜は暖色に灯り、村に生活感を出す)
    if (!W._windowMat) W._windowMat = new THREE.MeshBasicMaterial({ color: 0x232630 });
    for (const wx of [-w * 0.28, w * 0.28]) {
      const win = new THREE.Mesh(new THREE.PlaneGeometry(0.5, 0.5), W._windowMat);
      win.position.set(wx, hh * 0.55, d / 2 + 0.03);
      mesh.add(win);
    }
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
    // 上端も幅を持たせる: 極遠で1px幅の「白い縦筋」に潰れず、柔らかな
    // 光の柱 (ビーコン) として読める太さを保つ
    const beam = new THREE.Mesh(
      new THREE.CylinderGeometry(0.5, 1.4, 48, 6, 1, true),
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
    // 金具2本+錠前+蓋の継ぎ目 — 無地の直方体が「光る段ボール」に見える指摘
    const bandMat = new THREE.MeshLambertMaterial({ color: 0xc9a94a });
    const band = new THREE.Mesh(new THREE.BoxGeometry(1.16, 0.62, 0.12), bandMat);
    band.position.set(-0.3, 0.31, 0);
    const band2 = new THREE.Mesh(new THREE.BoxGeometry(1.16, 0.62, 0.12), bandMat);
    band2.position.set(0.3, 0.31, 0);
    band2.rotation.y = Math.PI / 2; band.rotation.y = Math.PI / 2;
    const seam = new THREE.Mesh(new THREE.BoxGeometry(1.12, 0.03, 0.72),
      new THREE.MeshLambertMaterial({ color: 0x4a3018 }));
    seam.position.y = 0.6;
    const lock = new THREE.Mesh(new THREE.BoxGeometry(0.16, 0.2, 0.08), bandMat);
    lock.position.set(0, 0.52, 0.38);
    grp.add(body, lid, band, band2, seam, lock);
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
    // 半径は歩行可能な床 (r<36) 内に収める。壁の立ち上がり面に置くと
    // 床から見上げたとき空中に浮いたデブリに見える
    for (let i = 0; i < 42; i++) {
      const a = rnd() * Math.PI * 2, r = 5 + rnd() * 29;
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
      const a = rnd() * Math.PI * 2, r = 4 + rnd() * 30;
      const px = cx + Math.cos(a) * r, pz = cz + Math.sin(a) * r;
      const rock = new THREE.Mesh(new THREE.DodecahedronGeometry(0.35 + rnd() * 0.55, 0), rockMat);
      rock.position.set(px, caveHeight(px, pz) + 0.25, pz);
      rock.rotation.set(rnd() * 3, rnd() * 3, rnd() * 3);
      scene.add(rock);
    }
    // 光るキノコの群生 (壁際と通路の視覚密度を上げる低コストプロップ)
    const shroomCap = new THREE.MeshLambertMaterial({ color: 0x3aa06a, emissive: 0x1e5c3a });
    const shroomStem = new THREE.MeshLambertMaterial({ color: 0x8a8f9c });
    const addShrooms = (px, pz) => {
      const base = caveHeight(px, pz);
      for (let k = 0; k < 3 + (rnd() * 3 | 0); k++) {
        const ox = (rnd() - 0.5) * 1.6, oz = (rnd() - 0.5) * 1.6;
        const s = 0.5 + rnd() * 0.9;
        const stem = new THREE.Mesh(new THREE.CylinderGeometry(0.045 * s, 0.06 * s, 0.3 * s, 5), shroomStem);
        stem.position.set(px + ox, base + 0.15 * s, pz + oz);
        const cap = new THREE.Mesh(new THREE.ConeGeometry(0.16 * s, 0.14 * s, 6), shroomCap);
        cap.position.set(px + ox, base + 0.34 * s, pz + oz);
        scene.add(stem, cap);
      }
    };
    for (let i = 0; i < 9; i++) {
      const a = rnd() * Math.PI * 2, r = 24 + rnd() * 9;
      addShrooms(cx + Math.cos(a) * r, cz + Math.sin(a) * r);
    }
    for (let i = 0; i < 3; i++) addShrooms(cx + (i % 2 ? 7 : -7), 1168 + i * 12);
    // 吊り鍾乳石: 主洞の上方に垂下するコーン群。天蓋球は高すぎて視界に
    // 入らないため、これが「天井がある」ことを示す唯一の手掛かりになる
    for (let i = 0; i < 14; i++) {
      const a = rnd() * Math.PI * 2, r = 6 + rnd() * 26;
      const px = cx + Math.cos(a) * r, pz = cz + Math.sin(a) * r;
      const len = 2.2 + rnd() * 3.5;
      const st = new THREE.Mesh(
        new THREE.ConeGeometry(0.35 + rnd() * 0.4, len, 5), stalMats[(rnd() * 3) | 0]);
      st.rotation.x = Math.PI;   // 先端を下向きに
      st.position.set(px, caveHeight(px, pz) + 13.5 + rnd() * 3 - len / 2, pz);
      st.rotation.y = rnd() * 3;
      scene.add(st);
    }
    // 光る水晶
    // エミッシブは控えめに: 強すぎるとファセット陰影が消え、近接時に
    // 白飛びした均一シアンのビルボードに見える。フラットシェーディングで
    // 面ごとの明度差を出し、至近でも結晶のファセットが読めるように
    const crystalMat = new THREE.MeshLambertMaterial({ color: 0x77ccff, emissive: 0x1e4e78, flatShading: true });
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

  W.setRuntimeDetail = function (value) {
    const next = G.clamp(Number.isFinite(value) ? value : 1, 0.72, 1);
    if (Math.abs(next - runtimeDetail) < 0.035) return;
    runtimeDetail = next;
    // 草だけを段階的に再構築。地形・衝突・敵配置は維持するためプレイ感は変えない。
    for (const ch of chunks.values()) removeGrass(ch);
  };
  W.runtimeChunkRadius = effectiveChunkRadius;

  let torchT = 0;
  W.update = function (dt, camX, camZ) {
    const ccx = Math.floor(camX / CHUNK), ccz = Math.floor(camZ / CHUNK);
    const R = effectiveChunkRadius();
    const GR = runtimeDetail < 0.85 ? Math.max(0, G.Q.grassRadius - 1) : G.Q.grassRadius;

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
    // 家の窓も夜は暖色に灯る
    if (W._windowMat) {
      W._windowMat.color.setHex(0x232630).lerp(_winWarm, torchOn);
    }
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
          s.beam.material.opacity = 0.08;
          s.crystal.material.color.set(0xffd58a);
          // エミッシブ控えめ — 点灯直後にグロー+加算が重なると祠全体が
          // 白いブロブに沈む
          s.crystal.material.emissive.set(0x6a4614);
          if (s.glow) { s.glow.scale.set(0.72, 0.72, 1); s.glow.material.opacity = 0.3; }
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
  const _gwhite = new THREE.Color(0xffffff);
  W.syncEnv = function (fogColor, fogNear, fogFar, light, sunTint, sunDir, sunI) {
    if (grassMat) {
      grassMat.uniforms.uFogColor.value.copy(fogColor);
      grassMat.uniforms.uFogNear.value = fogNear;
      grassMat.uniforms.uFogFar.value = fogFar;
      grassMat.uniforms.uLight.value = light;
      if (sunTint) grassMat.uniforms.uTint.value.copy(sunTint).lerp(_gwhite, 0.35);
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
  let scene, hemi, sun, skyDome, sunSpr, sunHalo, moonSpr, moonHalo, stars, clouds = [];
  let ridgeFar = null, ridgeNear = null;
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
      sun.shadow.bias = -0.0005;
      sun.shadow.normalBias = 0.6;   // 近接カメラでの壁面クロスハッチ縞 (アクネ) の抑制
      sun.shadow.radius = 4;
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

    // 遠景の山なみシルエット2層 (どの地平線にも奥行きの層を作る)。
    // 空ドーム同様カメラXZに追従する書き割り。フォグ距離の外にあるため
    // fog:false とし、色は毎フレーム空の地平色から手動で合成する
    const mkRidgeLayer = (dist, count, hMin, hMax, seed) => {
      const grp = new THREE.Group();
      // Lambert+フラットシェーディング: 昼でも日向/日陰の面差が出て、
      // 無陰影の単色カード (書き割り) に見えない
      const mat2 = new THREE.MeshLambertMaterial({ color: 0x8fa6c0, fog: false, flatShading: true });
      const rr = G.srand(seed);
      for (let i = 0; i < count; i++) {
        const a = (i / count) * Math.PI * 2 + rr() * 0.5;
        const h = hMin + rr() * (hMax - hMin);
        const w = 120 + rr() * 160;
        const m = new THREE.Mesh(new THREE.ConeGeometry(w, h, 4, 1), mat2);
        m.scale.z = 0.22;
        m.rotation.y = rr() * Math.PI;
        m.position.set(Math.cos(a) * dist, h * 0.28, Math.sin(a) * dist);
        grp.add(m);
        // 副峰を重ねて完全な二等辺三角形の書き割り感を崩す
        const h2 = h * (0.5 + rr() * 0.35);
        const m2 = new THREE.Mesh(new THREE.ConeGeometry(w * (0.5 + rr() * 0.3), h2, 4, 1), mat2);
        m2.scale.z = 0.22;
        m2.rotation.y = rr() * Math.PI;
        const a2 = a + (rr() - 0.5) * 0.16;
        m2.position.set(Math.cos(a2) * dist, h2 * 0.3, Math.sin(a2) * dist);
        grp.add(m2);
      }
      grp.renderOrder = -9;
      grp.userData.mat = mat2;
      scene.add(grp);
      return grp;
    };
    ridgeFar = mkRidgeLayer(640, 9, 60, 130, 31);
    ridgeNear = mkRidgeLayer(560, 7, 36, 80, 77);

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
      map: G.makeMoonTex(128),
      transparent: true, depthWrite: false, fog: false
    }));
    moonSpr.scale.set(48, 48, 1);
    scene.add(moonSpr);
    moonHalo = new THREE.Sprite(new THREE.SpriteMaterial({
      map: G.makeRadialTex(128, [[0, 'rgba(190,210,255,0.3)'], [1, 'rgba(180,200,255,0)']]),
      transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, fog: false
    }));
    moonHalo.scale.set(68, 68, 1);   // 締まったハロー (広すぎるとぼやけた光斑に見える)
    scene.add(moonHalo);
    // 計測ハーネスから位置・不透明度を検分するための参照 (デバッグ用)
    Sky._spr = { sunSpr, sunHalo, moonSpr, moonHalo };

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
    moonHalo.visible = skyVisible;
    if (ridgeFar) { ridgeFar.visible = skyVisible; ridgeNear.visible = skyVisible; }
    stars.visible = skyVisible;
    for (const c of clouds) c.visible = skyVisible;
    if (inCave) {
      hemi.intensity = 0.9;
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
    // 太陽が低いときは環境光も暖色に+少し落とす (朝夕は世界全体が夕色に沈む)
    const sunLow = G.smoothstep(0.55, 0.12, Math.abs(Math.sin(((tod - 6) / 12) * Math.PI))) *
                   G.smoothstep(4.5, 6, tod) * (1 - G.smoothstep(19.5, 21, tod));
    hemi.intensity = s.hem * wDim * (1 - sunLow * 0.2);
    hemi.color.copy(cTop).lerp(_white, 0.5).lerp(cSun, sunLow * 0.85);
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
    // 空の灰色化は残存降雨も含める (雨が降っている間は晴天の空にしない)
    const wet2 = Math.max(weather, rainOn);
    const u = skyDome.material.uniforms;
    u.uTop.value.copy(cTop).lerp(_grey, wet2 * 0.6);
    u.uHor.value.copy(cHor).lerp(_grey, wet2 * 0.7);
    u.uSunDir.value.copy(_sunDir);
    u.uSunCol.value.copy(cSun);
    u.uGlow.value = (0.25 + s.dir * 0.6) * (1 - wet2 * 0.8);
    skyDome.position.set(cam.x, 0, cam.z);

    // 太陽・月
    // ドーム(半径700)の内側に完全に収める (半径ぎりぎりだと球殻と交差し
    // スプライトが欠けてリング状のアーティファクトになる)
    sunSpr.position.copy(_sunDir).multiplyScalar(540).add(_camXZ);
    sunSpr.material.opacity = G.clamp(_sunDir.y + 0.15, 0, 1) * (1 - weather * 0.85);
    sunHalo.position.copy(sunSpr.position);
    sunHalo.material.opacity = sunSpr.material.opacity * 0.8;
    _moonDir.copy(_sunDir).negate();
    const moonRawY = _moonDir.y;   // 不透明度は実軌道の高さで決める (低空クランプ前)
    // 月は天頂まで上げず低空の弧に留める (通常カメラの仰角で画面に入る高さ。
    // 実軌道どおり真夜中に天頂へ置くと、誰の目にも触れないまま夜が終わる)
    if (_moonDir.y > 0.42) {
      const hs = Math.sqrt((1 - 0.42 * 0.42) / Math.max(1e-4, _moonDir.x * _moonDir.x + _moonDir.z * _moonDir.z));
      _moonDir.x *= hs; _moonDir.z *= hs; _moonDir.y = 0.42;
    }
    moonSpr.position.copy(_moonDir).multiplyScalar(525).add(_camXZ);
    moonSpr.material.opacity = G.clamp(moonRawY * 1.4 + 0.1, 0, 0.95) * G.clamp(1 - Math.max(weather, rainOn) * 1.3, 0, 1);
    moonHalo.position.copy(moonSpr.position);
    moonHalo.material.opacity = moonSpr.material.opacity * 0.4;

    // 星 (降雨粒子が残っている間も減光 — 土砂降り+満天の星の矛盾を防ぐ)
    const night = G.smoothstep(19.3, 21, tod) + (1 - G.smoothstep(4, 6, tod));
    const wetSky = Math.max(weather, rainOn);
    stars.material.opacity = G.clamp(night, 0, 1) * G.clamp(1 - wetSky * 1.4, 0, 1) * 0.9;
    Sky.starsOp = stars.material.opacity;   // 検証用の証跡
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
    const baseFar = (G.World.runtimeChunkRadius ? G.World.runtimeChunkRadius() : G.Q.chunkRadius) * 64 * 0.95;
    const alt = Math.max(0, cam.y - G.World.heightAt(cam.x, cam.z));
    const altBoost = 1 + G.clamp((alt - 8) / 50, 0, 1) * 1.5;  // 高所 (滑空中) は大きく視界を広げる
    scene.fog.far = baseFar * (1 - weather * 0.35) * (0.75 + s.hem * 0.4) * altBoost;
    scene.fog.near = scene.fog.far * 0.22;
    if (scene.background) scene.background.copy(_fogC);
    else scene.background = _fogC.clone();

    // 遠景山なみ: カメラ追従+地平色より僅かに濃い色 (霧に溶ける寸前の稜線)
    if (ridgeFar) {
      ridgeFar.position.set(cam.x, 0, cam.z);
      ridgeNear.position.set(cam.x, 0, cam.z);
      ridgeFar.userData.mat.color.copy(_fogC).multiplyScalar(0.93);
      ridgeNear.userData.mat.color.copy(_fogC).multiplyScalar(0.85).lerp(cTop, 0.06);
      const rv = 1 - weather * 0.85;   // 雨天は霞に沈める
      ridgeFar.visible = skyVisible && rv > 0.3;
      ridgeNear.visible = skyVisible && rv > 0.3;
    }

    // 雨 / 雪パーティクル (雪原バイオームでは常時ゆっくり降る雪に)
    const snowy = G.World.biomeAt(cam.x, cam.z) === 'snow';
    const wantPrecip = weather > 0.5 ? 1 : (snowy ? 0.7 : 0);
    // 止むときは速く消す (晴天の空に雨筋が残留しない)
    rainOn += (wantPrecip - rainOn) * G.damp(wantPrecip < rainOn ? 4.5 : 1.5, dt);
    Sky.rainAmt = rainOn;   // HUD天候アイコンを実際の降雨粒子量と同期させる
    const snowMode = snowy && weather <= 0.5;
    // 夜間は雨粒を明るく・不透明にして暗背景でも見えるようにする
    const darkF = 1 - G.clamp(s.hem * 1.7, 0, 1);
    rainPts.material.color.set(snowMode ? 0xffffff : 0xaec8dc);
    if (!snowMode) rainPts.material.color.lerp(_white, darkF * 0.85);
    rainPts.material.opacity = rainOn < 0.06 ? 0 : Math.min(1, rainOn * (snowMode ? 0.85 : 0.85 + darkF * 0.3));
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
        const len = snowMode ? 0.08 : rainVel[i] * 0.058;
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

/* ===== js/systems.js ===== */
/* =============================================================================
 * ELDRIA — systems.js
 * アイテム / 所持品 / 成長 / 世界状態 / クエスト / 会話 / 商店 / セーブ
 * ========================================================================== */
'use strict';

/* ======================= アイテム ======================= */
(function () {
  const Items = G.Items = {};
  const DB = {
    /* 消耗品 */
    potion:    { name: '回復薬',      type: 'consumable', desc: 'HPを42%回復する薬湯。',  price: 40,  sell: 15 },
    hipotion:  { name: '上回復薬',    type: 'consumable', desc: 'HPを70%回復する濃い薬。',  price: 110, sell: 40 },
    herb:      { name: '月光草',      type: 'consumable', desc: '夜光を宿す薬草。少し回復。', price: 30, sell: 8 },
    /* 素材 */
    pelt:      { name: '狼の毛皮',    type: 'material', desc: '上質な獣の毛皮。売れる。', sell: 14 },
    bone:      { name: '古びた骨',    type: 'material', desc: '骸骨の残骸。売れる。', sell: 10 },
    magicstone:{ name: '魔石',        type: 'material', desc: '仄かに光る石。高く売れる。', sell: 25 },
    cargo:     { name: '商人の積荷',  type: 'quest', desc: 'モーガンが失くした積荷。' },
    /* 武器 */
    sword_traveler: { name: '旅人の剣',   type: 'weapon', kind: 'sword', atk: 8,  desc: '使い込まれた鉄の剣。', sell: 20 },
    sword_knight:   { name: '騎士の剣',   type: 'weapon', kind: 'sword', atk: 12, desc: '王都の騎士が帯びた剣。', price: 220, sell: 80 },
    sword_fang:     { name: '狼牙の剣',   type: 'weapon', kind: 'sword', atk: 16, desc: 'フェンリルの牙から鍛えた剣。', sell: 300 },
    axe_ruin:       { name: '遺跡の戦斧', type: 'weapon', kind: 'axe',  atk: 20, desc: '古代文明の重い戦斧。', sell: 400 },
    sword_dragon:   { name: '竜断ちの剣', type: 'weapon', kind: 'sword', atk: 26, desc: '竜をも断つと謳われた聖剣。', sell: 800 },
    spear_venom:    { name: '毒針の槍',   type: 'weapon', kind: 'spear', atk: 18, desc: '砂帝の毒針から作られた槍。', sell: 350 },
    sword_wind:     { name: '風の大剣',   type: 'weapon', kind: 'sword', atk: 23, desc: '風哭の洞窟に眠っていた大剣。', sell: 600 },
    /* 防具 */
    armor_cloth:    { name: '旅人の服',     type: 'armor', def: 2,  color: 0x5d7a9a, color2: 0x3e4f63, desc: '長旅に馴染んだ服。', sell: 10 },
    armor_leather:  { name: '旅装',         type: 'armor', def: 4,  color: 0x7a6a4a, color2: 0x554832, desc: '革を重ねた旅装。', price: 180, sell: 60 },
    armor_hunter:   { name: '狩人の革鎧',   type: 'armor', def: 7,  color: 0x5a6a3a, color2: 0x3d4828, desc: '狩人に好まれる軽鎧。', price: 340, sell: 120 },
    armor_guardian: { name: '遺跡守りの鎧', type: 'armor', def: 12, color: 0x8a8478, color2: 0x5a564e, desc: '巨像の核で強化された鎧。', sell: 400 },
    armor_dragon:   { name: '竜鱗の鎧',     type: 'armor', def: 18, color: 0x4a3a52, color2: 0x2e2436, desc: '黒竜の鱗を綴った最強の鎧。', sell: 900 }
  };
  Items.get = id => DB[id];
  Items.all = () => DB;
})();

/* ======================= 所持品 ======================= */
(function () {
  const Inv = G.Inv = {};
  Inv.items = {};
  Inv.gold = 0;
  Inv.equip = { weapon: 'sword_traveler', armor: 'armor_cloth' };
  Inv.upgrades = {};          // itemId -> 強化段階 (0-5)
  Inv.upgLevel = id => Inv.upgrades[id] || 0;

  Inv.add = function (id, n) {
    Inv.items[id] = (Inv.items[id] || 0) + (n || 1);
    G.events.emit('invChange');
  };
  Inv.remove = function (id, n) {
    n = n || 1;
    if ((Inv.items[id] || 0) < n) return false;
    Inv.items[id] -= n;
    if (Inv.items[id] <= 0) delete Inv.items[id];
    G.events.emit('invChange');
    return true;
  };
  Inv.count = id => Inv.items[id] || 0;
  Inv.addGold = function (n) {
    Inv.gold += n;
    if (n > 0) G.Audio.sfx('gold');
    G.events.emit('invChange');
  };
  Inv.equipItem = function (id) {
    const it = G.Items.get(id);
    if (!it) return;
    if (it.type === 'weapon') Inv.equip.weapon = id;
    else if (it.type === 'armor') Inv.equip.armor = id;
    else return;
    G.Audio.sfx('ui');
    G.Player.buildRig();
    G.events.emit('invChange');
  };
})();

/* ======================= 成長 ======================= */
(function () {
  const S = G.Stats = {};
  S.level = 1;
  S.xp = 0;

  S.xpNeed = function (lv) { return Math.round(50 * Math.pow(lv || S.level, 1.4)); };
  S.maxHp = () => 96 + S.level * 14;
  S.maxSta = () => 92 + S.level * 8;
  S.atk = function () {
    const w = G.Items.get(G.Inv.equip.weapon);
    return (w ? w.atk : 5) + (S.level - 1) * 2 + G.Inv.upgLevel(G.Inv.equip.weapon) * 2;
  };
  S.def = function () {
    const a = G.Items.get(G.Inv.equip.armor);
    return (a ? a.def : 0) + Math.floor((S.level - 1) * 0.6) + G.Inv.upgLevel(G.Inv.equip.armor);
  };
  S.addXP = function (n) {
    S.xp += n;
    G.events.emit('xpGain', n);
    while (S.xp >= S.xpNeed()) {
      S.xp -= S.xpNeed();
      S.level++;
      G.Player.hp = Math.min(S.maxHp(), G.Player.hp + Math.round(S.maxHp() * 0.4));
      G.Player.stamina = S.maxSta();
      G.Audio.sfx('levelup');
      G.UI.toast('レベルアップ！ Lv.' + S.level, 'gold');
      G.events.emit('levelup', S.level);
      G.FX.burst(G.Player.pos.x, G.Player.pos.y + 1, G.Player.pos.z,
        { n: 24, color: 0xffdd44, speed: 3, up: 1.5, gravity: -2, life: 1.0, size: 3.5 });
    }
  };
})();

/* ======================= 世界状態 ======================= */
(function () {
  G.State = {
    tod: 9.5,          // 時刻 0-24
    day: 1,
    weather: 0,        // 0=晴 1=雨 (現在値)
    weatherTarget: 0,
    weatherTimer: 180,
    bossKilled: {},
    openedChests: {},
    herbs: {},
    shrines: {},       // 灯した祠
    respawn: 'shrine1',
    mainStage: 0,      // 進行度 (表示用)
    cleared: false,    // 黒竜討伐済み
    playtime: 0,
    titles: {},        // 獲得した称号
    killCount: 0
  };
})();

/* ======================= クエスト ======================= */
(function () {
  const Q = G.Quests = {};

  const DEFS = {
    main1: { name: '目覚めの村',   desc: '長老ハルドと話す', main: true, mark: { x: 2, z: -17 } },
    main2: { name: '森の脅威',     desc: '西の森の白狼王フェンリルを討つ', main: true, boss: 'fenrir',
             reward: { gold: 200, items: { sword_fang: 1 } }, mark: { x: -430, z: -140 } },
    main3: { name: '遺跡の巨像',   desc: '東の遺跡に眠る巨像を倒す', main: true, boss: 'golem',
             reward: { gold: 300, items: { armor_guardian: 1 } }, mark: { x: 430, z: -80 } },
    main4: { name: '黒竜討伐',     desc: '北の頂に座す黒竜ヴァルドレクを討つ', main: true, boss: 'dragon',
             reward: { gold: 1000, items: { armor_dragon: 1 } }, final: true, mark: { x: -40, z: -640 } },
    side_herb:  { name: '月光草の採取', desc: '月光草を5本集めてリナに届ける', giver: 'healer',
                  collect: 'herb', count: 5, reward: { gold: 120, items: { hipotion: 2 } } },
    side_wolf:  { name: '狼狩り',       desc: '野狼を6匹狩ってガルドに報告する', giver: 'hunter',
                  kill: 'wolf', count: 6, reward: { gold: 150, items: { potion: 2 } } },
    side_cargo: { name: '失われた積荷', desc: '南の廃墟から積荷を持ち帰る', giver: 'merchant',
                  fetch: 'cargo', reward: { gold: 250 }, mark: { x: 150, z: 430 } },
    side_bandit: { name: '盗賊退治', desc: '街道を荒らす盗賊を5人倒しモーガンに報告', giver: 'merchant',
                  kill: 'bandit', count: 5, reward: { gold: 260, items: { hipotion: 2 } }, mark: { x: -150, z: 250 } },
    side_scorp: { name: '砂漠の異変', desc: '砂丘の主・砂帝スコルグを討つ', giver: 'hunter',
                  boss: 'scorpking', reward: { gold: 500, items: { spear_venom: 1 } }, mark: { x: 390, z: 380 } },
    side_cave: { name: '風哭の洞窟', desc: '山麓の洞窟の最深部で風の大剣を見つける', giver: 'elder',
                  fetch: 'sword_wind', reward: { gold: 400 }, mark: { x: -260, z: -360 } }
  };
  Q.DEFS = DEFS;
  Q.state = {};   // id -> {status:'active'|'ready'|'done', progress}

  Q.start = function (id) {
    if (Q.state[id]) return;
    Q.state[id] = { status: 'active', progress: 0 };
    const D = DEFS[id];
    // 対象アイテムを既に持っている場合は即「報告待ち」に
    if (D.fetch && G.Inv.count(D.fetch) > 0) Q.state[id].status = 'ready';
    if (D.collect && G.Inv.count(D.collect) >= D.count) Q.state[id].status = 'ready';
    G.UI.toast('クエスト開始: ' + D.name, 'quest');
    G.Audio.sfx('uiOpen');
    G.events.emit('questChange');
    // 対象ボスを既に討伐済みなら即完了 (順序破り対策)
    if (D.boss && G.State.bossKilled[D.boss]) Q.complete(id);
  };

  Q.isActive = id => Q.state[id] && Q.state[id].status === 'active';
  Q.isReady = id => Q.state[id] && Q.state[id].status === 'ready';
  Q.isDone = id => Q.state[id] && Q.state[id].status === 'done';

  Q.complete = function (id) {
    const st = Q.state[id];
    if (!st || st.status === 'done') return;
    st.status = 'done';
    const D = DEFS[id];
    G.UI.toast('クエスト達成: ' + D.name, 'gold');
    G.Audio.sfx('questDone');
    if (D.reward) {
      if (D.reward.gold) G.Inv.addGold(D.reward.gold);
      if (D.reward.items) {
        for (const k in D.reward.items) {
          G.Inv.add(k, D.reward.items[k]);
          G.UI.toast(G.Items.get(k).name + ' を手に入れた', 'gold');
        }
      }
    }
    if (D.main) {
      G.State.mainStage++;
      // 次のメインクエスト
      const order = ['main1', 'main2', 'main3', 'main4'];
      const idx = order.indexOf(id);
      if (idx >= 0 && idx < order.length - 1) Q.start(order[idx + 1]);
    }
    if (D.final) {
      G.State.cleared = true;
      G.events.emit('gameClear');
    }
    G.events.emit('questChange');
  };

  /* 進行中クエストの表示用リスト */
  Q.trackerLines = function () {
    const out = [];
    for (const id in Q.state) {
      const st = Q.state[id];
      if (st.status === 'done') continue;
      const D = DEFS[id];
      let line = D.name;
      if (D.kill) line += ` (${Math.min(st.progress, D.count)}/${D.count})`;
      else if (D.collect) line += ` (${Math.min(G.Inv.count(D.collect), D.count)}/${D.count})`;
      if (st.status === 'ready') line += ' — 報告する';
      // 目標地点 (ready なら村へ報告)
      const mk = st.status === 'ready' ? { x: 0, z: 0 } : (D.mark || null);
      out.push({ id, line, main: !!D.main, ready: st.status === 'ready',
                 desc: st.status === 'ready' ? '依頼主に報告しよう' : D.desc,
                 mx: mk ? mk.x : null, mz: mk ? mk.z : null });
    }
    out.sort((a, b) => (b.main ? 1 : 0) - (a.main ? 1 : 0));
    return out;
  };

  /* マップに出すマーカー */
  Q.marks = function () {
    const out = [];
    for (const id in Q.state) {
      const st = Q.state[id];
      if (st.status === 'done') continue;
      const D = DEFS[id];
      if (st.status === 'active' && D.mark) out.push({ x: D.mark.x, z: D.mark.z, name: D.name });
      if (st.status === 'ready') out.push({ x: 0, z: 0, name: '村へ報告' });
    }
    return out;
  };

  /* イベント連携 */
  G.events.on('kill', d => {
    for (const id in Q.state) {
      const st = Q.state[id], D = DEFS[id];
      if (st.status !== 'active' || !D.kill) continue;
      if (D.kill === d.type) {
        st.progress++;
        if (st.progress >= D.count) {
          st.status = 'ready';
          G.UI.toast(D.name + ': 達成！ 依頼主に報告しよう', 'quest');
          G.Audio.sfx('questDone');
        }
        G.events.emit('questChange');
      }
    }
  });

  G.events.on('collect', d => {
    for (const id in Q.state) {
      const st = Q.state[id], D = DEFS[id];
      if (st.status !== 'active') continue;
      if (D.collect === d.id && G.Inv.count(D.collect) >= D.count) {
        st.status = 'ready';
        G.UI.toast(D.name + ': 集まった！ リナに届けよう', 'quest');
        G.Audio.sfx('questDone');
        G.events.emit('questChange');
      }
      if (D.fetch === d.id) {
        st.status = 'ready';
        G.UI.toast(D.name + ': 積荷を見つけた！', 'quest');
        G.Audio.sfx('questDone');
        G.events.emit('questChange');
      }
    }
  });

  G.events.on('bossKilled', bossId => {
    for (const id in Q.state) {
      const st = Q.state[id], D = DEFS[id];
      if (st.status === 'active' && D.boss === bossId) Q.complete(id);
    }
  });
})();

/* ======================= 会話 ======================= */
(function () {
  const D = G.Dialogue = {};
  const Q = G.Quests;

  /* NPC ごとに現在の状況に応じた会話ツリーを生成 */
  D.build = function (npcId) {
    switch (npcId) {
      case 'elder': {
        if (Q.isActive('main1')) {
          return {
            text: 'おお、目を覚ましたか、旅の方。ここはミストヴェイル村。……この大地エルドリアは今、北の頂に巣食う黒竜ヴァルドレクの呪いで魔物に溢れておる。',
            options: [
              { label: '詳しく聞く', next: {
                text: '竜を討つには、まず力を付けねばならん。西の森の白狼王、東の遺跡の巨像……奴らを越えた者だけが、竜の頂に立てる。頼めるか、旅の方よ。',
                options: [
                  { label: '引き受ける', action: () => { Q.complete('main1'); }, closeText: '感謝する。まずは西の森じゃ。祠を灯せば、力尽きてもそこへ戻れる。' },
                  { label: '考えておく', close: true }
                ]
              } },
              { label: '立ち去る', close: true }
            ]
          };
        }
        if (Q.isActive('main2')) return { text: '西の森の奥、静寂の空き地に白狼王フェンリルがおる。突進は横に転がってかわすのじゃ。', options: [{ label: '分かった', close: true }] };
        if (Q.isActive('main3')) return { text: '東の遺跡の巨像は岩の拳を振るう。懐に入り、攻撃の後の隙を突け。', options: [{ label: '分かった', close: true }] };
        if (Q.isActive('main4')) return { text: '北の頂へは山麓の祠から登るがよい。竜の炎は地を這う……走り続けよ。そなたに風の加護があらんことを。', options: [{ label: '行ってくる', close: true }] };
        if (!Q.state['side_cave'] && G.State.mainStage >= 3) {
          return {
            text: 'そういえば……北西の山麓に「風哭の洞窟」と呼ばれる古い坑道がある。風の唸る奥底に、古の大剣が眠っておるそうじゃ。腕に覚えがあるなら行ってみるがよい。',
            options: [
              { label: '探索する', action: () => Q.start('side_cave'), closeText: '洞窟の入り口は山麓の祠の南東じゃ。中は暗い。魔物に気をつけよ。' },
              { label: 'また今度', close: true }
            ]
          };
        }
        if (Q.isReady('side_cave')) {
          return {
            text: 'おお、それが風の大剣か……! 見事じゃ。剣はそなたが持つがよい。これは褒美じゃ。',
            options: [{ label: '受け取る', action: () => Q.complete('side_cave'), close: true }]
          };
        }
        if (G.State.cleared) return { text: 'そなたが黒竜を討ったと聞いた時、村中が歓声に沸いたわい。エルドリアの英雄よ、この村はいつでもそなたの家じゃ。', options: [{ label: 'ありがとう', close: true }] };
        return { text: '風が穏やかじゃな……。', options: [{ label: '立ち去る', close: true }] };
      }
      case 'healer': {
        if (!Q.state['side_herb'] && G.State.mainStage >= 1) {
          return {
            text: 'あなたが長老の言っていた旅人さんね。私はリナ、薬師をしています。……お願いがあるの。夜に光る月光草を5本、集めてもらえないかしら?',
            options: [
              { label: '引き受ける', action: () => Q.start('side_herb'), closeText: 'ありがとう! 草原や森の光る草を探してみて。摘んだら私に届けてね。' },
              { label: 'また今度', close: true }
            ]
          };
        }
        if ((Q.isReady('side_herb') || Q.isActive('side_herb')) && G.Inv.count('herb') >= Q.DEFS.side_herb.count) {
          return {
            text: 'まあ、こんなに立派な月光草……! 本当にありがとう。お礼にこの薬を持っていって。',
            options: [{ label: '渡す', action: () => {
              if (G.Inv.remove('herb', Q.DEFS.side_herb.count)) Q.complete('side_herb');
            }, close: true }]
          };
        }
        if (Q.isReady('side_herb') || Q.isActive('side_herb')) return { text: '月光草は暗くなると淡く光るわ。草原を探してみて。5本必要よ。', options: [{ label: '分かった', close: true }] };
        return {
          text: '怪我はない? 疲れたらここで休んでいってね。',
          options: [
            { label: '休ませてもらう (全回復)', action: () => { G.Player.heal(9999); G.Player.stamina = G.Stats.maxSta(); }, closeText: 'はい、これで大丈夫。気をつけてね。' },
            { label: '大丈夫', close: true }
          ]
        };
      }
      case 'merchant': {
        const opts = [];
        if (!Q.state['side_cargo'] && G.State.mainStage >= 1) {
          opts.push({
            label: '困りごとを聞く',
            next: {
              text: '実はな、南の廃墟のあたりで盗賊に襲われて積荷を捨てて逃げてきたんだ。取り戻してくれたら礼は弾むぜ。',
              options: [
                { label: '引き受ける', action: () => Q.start('side_cargo'), closeText: '恩に着るよ! 南の廃墟だ、気をつけてな。' },
                { label: 'また今度', close: true }
              ]
            }
          });
        }
        if (Q.isReady('side_cargo') && G.Inv.count('cargo') > 0) {
          return {
            text: 'おお! それは俺の積荷じゃないか! あんた、命の恩人だ!',
            options: [{ label: '積荷を渡す', action: () => { G.Inv.remove('cargo', 1); Q.complete('side_cargo'); }, close: true }]
          };
        }
        if (!Q.state['side_bandit'] && G.State.mainStage >= 2) {
          opts.push({
            label: '盗賊の噂を聞く',
            next: {
              text: '最近、街道に盗賊が出て仕入れが滞ってるんだ。5人ばかり懲らしめてくれたら礼をするぜ。西と東の草原に焚き火の野営地がある。',
              options: [
                { label: '引き受ける', action: () => Q.start('side_bandit'), closeText: '頼んだぜ! 奴ら結構腕が立つから気をつけな。' },
                { label: 'また今度', close: true }
              ]
            }
          });
        }
        if (Q.isReady('side_bandit')) {
          return {
            text: 'おお、盗賊どもが逃げ出したって噂だ! あんたのおかげだな。これは約束の礼だ。',
            options: [{ label: '受け取る', action: () => Q.complete('side_bandit'), close: true }]
          };
        }
        opts.unshift({ label: '買い物をする', action: () => G.UI.openShop(), close: true });
        opts.push({ label: '立ち去る', close: true });
        return { text: 'いらっしゃい! 旅の必需品ならなんでも揃うぜ。', options: opts };
      }
      case 'smith': {
        return {
          text: 'おう、旅の人か。俺はドヴァン、鍛冶師だ。魔石と素材があれば装備を鍛えてやるぜ。+5まで強化できる。',
          options: [
            { label: '装備を強化する', action: () => G.UI.openForge(), close: true },
            { label: 'コツを聞く', next: {
              text: '魔石は岩の子鬼や骸骨がよく落とす。毛皮や骨も無駄にするなよ。強化は攻撃+2、防御+1ずつ効いてくる。',
              options: [{ label: '参考になった', close: true }]
            } },
            { label: '立ち去る', close: true }
          ]
        };
      }
      case 'hunter': {
        if (!Q.state['side_wolf'] && G.State.mainStage >= 1) {
          return {
            text: '俺はガルド、この村の狩人だ。最近、野狼が増えすぎて家畜が危ねえ。6匹ばかり間引いてくれねえか?',
            options: [
              { label: '引き受ける', action: () => Q.start('side_wolf'), closeText: '助かるぜ。奴らは森や草原をうろついてる。夜は物騒だから気をつけな。' },
              { label: 'また今度', close: true }
            ]
          };
        }
        if (Q.isReady('side_wolf')) {
          return {
            text: 'おう、見事な狩りっぷりだったってな! これは約束の礼だ。',
            options: [{ label: '受け取る', action: () => Q.complete('side_wolf'), close: true }]
          };
        }
        if (Q.isActive('side_wolf')) return { text: '狼どもは群れる前に仕留めるんだ。回避は転がりが基本だぜ。', options: [{ label: '分かった', close: true }] };
        if (Q.isDone('side_wolf') && !Q.state['side_scorp']) {
          return {
            text: '南東の砂漠で、馬鹿でかいサソリが隊商を襲ってるらしい。「砂帝スコルグ」……訛った名だが奴は本物の化物だ。挑むか?',
            options: [
              { label: '討伐を引き受ける', action: () => Q.start('side_scorp'), closeText: '砂丘の廃墟に巣があるそうだ。突進は横っ飛びでかわせ。生きて帰れよ。' },
              { label: 'また今度', close: true }
            ]
          };
        }
        if (Q.isActive('side_scorp')) return { text: 'スコルグは砂丘の廃墟だ。尻尾の一撃は喰らうな。', options: [{ label: '分かった', close: true }] };
        return { text: '戦いのコツか? 敵が構えたら転がって背後を取れ。あとはスタミナ管理だな。', options: [{ label: '参考になった', close: true }] };
      }
    }
    return { text: '……', options: [{ label: '立ち去る', close: true }] };
  };

  D.start = function (npc) {
    G.events.emit('talk', npc.id);
    G.UI.showDialogue(npc.name, D.build(npc.id));
  };
})();

/* ======================= 称号 (実績) ======================= */
(function () {
  const A = G.Achieve = {};
  const DEFS = {
    first_kill: { name: '初陣',         desc: '初めて魔物を倒した' },
    kills_100:  { name: '百戦錬磨',     desc: '魔物を100体倒した' },
    all_shrines:{ name: '導きの灯',     desc: '全ての祠を灯した' },
    lv10:       { name: '熟達の旅人',   desc: 'レベル10に到達した' },
    boss_first: { name: '狩人の証',     desc: '初めてボスを討伐した' },
    all_bosses: { name: '大地の守護者', desc: '全てのボスを討伐した' },
    cave:       { name: '風を断つ者',   desc: '風の大剣を手に入れた' },
    clear:      { name: '竜殺し',       desc: '黒竜ヴァルドレクを討った' },
    upgrade5:   { name: '名工の相棒',   desc: '装備を+5まで強化した' }
  };
  A.DEFS = DEFS;
  A.earn = function (id) {
    if (!DEFS[id] || G.State.titles[id]) return;
    G.State.titles[id] = true;
    G.UI.toast('称号獲得 「' + DEFS[id].name + '」', 'gold');
    G.Audio.sfx('questDone');
  };
  G.events.on('kill', () => {
    G.State.killCount = (G.State.killCount || 0) + 1;
    A.earn('first_kill');
    if (G.State.killCount >= 100) A.earn('kills_100');
  });
  G.events.on('bossKilled', id => {
    A.earn('boss_first');
    if (id === 'dragon') A.earn('clear');
    if (['fenrir', 'golem', 'scorpking', 'dragon'].every(b => G.State.bossKilled[b])) A.earn('all_bosses');
  });
  G.events.on('collect', d => { if (d.id === 'sword_wind') A.earn('cave'); });
  G.events.on('shrineLit', () => {
    if (Object.keys(G.State.shrines).length >= G.World.shrines.length) A.earn('all_shrines');
  });
  G.events.on('levelup', lv => { if (lv >= 10) A.earn('lv10'); });
  G.events.on('upgraded', d => { if (d.lvl >= 5) A.earn('upgrade5'); });
})();

/* ======================= 鍛冶 (強化) ======================= */
(function () {
  const F = G.Forge = {};
  /* 段階 lvl→lvl+1 のコスト */
  F.cost = function (lvl) {
    return {
      gold: [80, 180, 320, 500, 750][lvl] || 9999,
      mats: [
        { magicstone: 1 },
        { magicstone: 2 },
        { magicstone: 3, bone: 2 },
        { magicstone: 4, pelt: 3 },
        { magicstone: 6, bone: 3, pelt: 3 }
      ][lvl] || {}
    };
  };
  F.canUpgrade = function (id) {
    const lvl = G.Inv.upgLevel(id);
    if (lvl >= 5) return { ok: false, reason: '最大強化済み' };
    const c = F.cost(lvl);
    if (G.Inv.gold < c.gold) return { ok: false, reason: 'ゴールド不足', cost: c };
    for (const m in c.mats) {
      if (G.Inv.count(m) < c.mats[m]) return { ok: false, reason: G.Items.get(m).name + ' 不足', cost: c };
    }
    return { ok: true, cost: c };
  };
  F.upgrade = function (id) {
    const r = F.canUpgrade(id);
    if (!r.ok) { G.UI.toast(r.reason); return false; }
    G.Inv.gold -= r.cost.gold;
    for (const m in r.cost.mats) G.Inv.remove(m, r.cost.mats[m]);
    G.Inv.upgrades[id] = G.Inv.upgLevel(id) + 1;
    G.events.emit('upgraded', { id, lvl: G.Inv.upgrades[id] });
    G.Audio.sfx('clang');
    G.Audio.sfx('levelup');
    const it = G.Items.get(id);
    G.UI.toast(it.name + ' を +' + G.Inv.upgrades[id] + ' に強化した', 'gold');
    G.events.emit('invChange');
    return true;
  };
})();

/* ======================= 商店 ======================= */
(function () {
  const Shop = G.Shop = {};
  Shop.stock = ['potion', 'hipotion', 'sword_knight', 'armor_leather', 'armor_hunter'];

  Shop.buy = function (id) {
    const it = G.Items.get(id);
    if (!it || !it.price) return false;
    if (G.Inv.gold < it.price) { G.UI.toast('ゴールドが足りない…'); return false; }
    G.Inv.gold -= it.price;
    G.Inv.add(id, 1);
    G.Audio.sfx('gold');
    G.UI.toast(it.name + ' を購入した');
    return true;
  };

  Shop.sell = function (id) {
    const it = G.Items.get(id);
    if (!it || !it.sell) return false;
    // 装備中の最後の1個は売れない
    if ((G.Inv.equip.weapon === id || G.Inv.equip.armor === id) && G.Inv.count(id) <= 1) {
      G.UI.toast('装備中の品は売れない');
      return false;
    }
    if (!G.Inv.remove(id, 1)) return false;
    G.Inv.addGold(it.sell);
    return true;
  };
})();

/* ======================= セーブ / ロード ======================= */
(function () {
  const S = G.Save = {};
  const KEY = 'eldria_save_v1';
  const BACKUP = 'eldria_save_backup_v1';

  const isObj = v => !!v && typeof v === 'object' && !Array.isArray(v);
  function validate(data) {
    return isObj(data) && data.v === 1 && isObj(data.stats) &&
      Number.isFinite(data.stats.level) && data.stats.level >= 1 &&
      Number.isFinite(data.stats.xp) && isObj(data.pos) &&
      Number.isFinite(data.pos.x) && Number.isFinite(data.pos.z) &&
      isObj(data.inv) && isObj(data.quests);
  }
  function parse(raw) {
    if (!raw) return null;
    try {
      const data = JSON.parse(raw);
      return validate(data) ? data : null;
    } catch (e) { return null; }
  }
  function read(key) { return parse(G.storage.get(key)); }
  S.validate = validate;

  S.exists = function () {
    return !!(read(KEY) || read(BACKUP));
  };

  S.summary = function () {
    const data = read(KEY) || read(BACKUP);
    if (!data) return null;
    const st = isObj(data.state) ? data.state : {};
    return {
      level: Math.max(1, Math.floor(data.stats.level)),
      chapter: G.clamp(Math.floor(st.mainStage || 0) + 1, 1, 4),
      playtime: Math.max(0, Number(st.playtime) || 0),
      recovered: !read(KEY) && !!read(BACKUP)
    };
  };

  S.save = function () {
    try {
      const p = G.Player;
      const data = {
        v: 1,
        stats: { level: G.Stats.level, xp: G.Stats.xp },
        hp: p.hp, sta: p.stamina,
        pos: { x: Math.round(p.pos.x * 10) / 10, z: Math.round(p.pos.z * 10) / 10 },
        inv: G.Inv.items, gold: G.Inv.gold, equip: G.Inv.equip,
        quests: G.Quests.state,
        horse: { x: Math.round(G.Horse.pos.x), z: Math.round(G.Horse.pos.z) },
        upg: G.Inv.upgrades,
        state: {
          tod: G.State.tod, day: G.State.day,
          bossKilled: G.State.bossKilled,
          openedChests: G.State.openedChests,
          herbs: G.State.herbs,
          shrines: G.State.shrines,
          respawn: G.State.respawn,
          mainStage: G.State.mainStage,
          cleared: G.State.cleared,
          playtime: G.State.playtime,
          titles: G.State.titles,
          killCount: G.State.killCount
        }
      };
      const json = JSON.stringify(data);
      const previous = G.storage.get(KEY);
      if (parse(previous)) G.storage.set(BACKUP, previous);
      if (!G.storage.set(KEY, json)) return false;
      G.events.emit('saved');
      return true;
    } catch (e) { return false; }
  };

  S.load = function () {
    const primary = read(KEY);
    if (primary) return primary;
    const backup = read(BACKUP);
    if (backup) backup._recovered = true;
    return backup;
  };

  S.exportData = function () {
    const data = read(KEY) || read(BACKUP);
    if (!data) return null;
    return JSON.stringify({
      format: 'eldria-save', version: 1,
      exportedAt: new Date().toISOString(), data
    }, null, 2);
  };

  S.importData = function (raw) {
    try {
      const pack = typeof raw === 'string' ? JSON.parse(raw) : raw;
      if (!isObj(pack) || pack.format !== 'eldria-save' || pack.version !== 1 || !validate(pack.data)) return false;
      const previous = G.storage.get(KEY);
      if (parse(previous)) G.storage.set(BACKUP, previous);
      return G.storage.set(KEY, JSON.stringify(pack.data));
    } catch (e) { return false; }
  };

  S.apply = function (data) {
    if (!validate(data)) return false;
    G.Stats.level = G.clamp(Math.floor(data.stats.level), 1, 99);
    G.Stats.xp = G.clamp(Math.floor(data.stats.xp), 0, 1000000000);

    const items = {};
    for (const id in data.inv) {
      const n = data.inv[id];
      if (G.Items.get(id) && Number.isFinite(n) && n > 0) items[id] = Math.min(9999, Math.floor(n));
    }
    G.Inv.items = items;
    G.Inv.gold = Number.isFinite(data.gold) ? G.clamp(Math.floor(data.gold), 0, 1000000000) : 0;
    const equip = { weapon: 'sword_traveler', armor: 'armor_cloth' };
    if (isObj(data.equip)) {
      const weapon = G.Items.get(data.equip.weapon);
      const armor = G.Items.get(data.equip.armor);
      if (weapon && weapon.type === 'weapon') equip.weapon = data.equip.weapon;
      if (armor && armor.type === 'armor') equip.armor = data.equip.armor;
    }
    G.Inv.equip = equip;

    const quests = {};
    for (const id in data.quests) {
      const q = data.quests[id];
      if (!G.Quests.DEFS[id] || !isObj(q) || !['active', 'ready', 'done'].includes(q.status)) continue;
      quests[id] = { status: q.status, progress: Number.isFinite(q.progress) ? Math.max(0, Math.floor(q.progress)) : 0 };
    }
    G.Quests.state = quests;

    const st = isObj(data.state) ? data.state : {};
    G.State.tod = Number.isFinite(st.tod) ? G.clamp(st.tod, 0, 23.999) : 9.5;
    G.State.day = Number.isFinite(st.day) ? G.clamp(Math.floor(st.day), 1, 9999) : 1;
    G.State.mainStage = Number.isFinite(st.mainStage) ? G.clamp(Math.floor(st.mainStage), 0, 4) : 0;
    G.State.playtime = Number.isFinite(st.playtime) ? G.clamp(st.playtime, 0, 1000000000) : 0;
    G.State.killCount = Number.isFinite(st.killCount) ? G.clamp(Math.floor(st.killCount), 0, 1000000000) : 0;
    G.State.cleared = !!st.cleared;
    const cleanFlags = source => {
      const out = {};
      if (!isObj(source)) return out;
      for (const key in source) if (source[key]) out[key] = true;
      return out;
    };
    G.State.bossKilled = cleanFlags(st.bossKilled);
    G.State.openedChests = cleanFlags(st.openedChests);
    G.State.herbs = cleanFlags(st.herbs);
    G.State.shrines = cleanFlags(st.shrines);
    G.State.titles = cleanFlags(st.titles);
    const respawn = typeof st.respawn === 'string' && G.World.shrines.some(sh => sh.id === st.respawn)
      ? st.respawn : 'shrine1';
    G.State.respawn = respawn;

    const p = G.Player;
    p.hp = Number.isFinite(data.hp) ? G.clamp(data.hp, 1, G.Stats.maxHp()) : G.Stats.maxHp();
    p.stamina = Number.isFinite(data.sta) ? G.clamp(data.sta, 0, G.Stats.maxSta()) : G.Stats.maxSta();
    const px = G.clamp(data.pos.x, -1300, 1300), pz = G.clamp(data.pos.z, -1300, 1300);
    const py = G.World.heightAt(px, pz);
    p.pos.set(px, Number.isFinite(py) ? py : G.World.heightAt(6, 34), pz);
    if (isObj(data.horse) && Number.isFinite(data.horse.x) && Number.isFinite(data.horse.z)) {
      G.Horse.teleport(G.clamp(data.horse.x, -1300, 1300), G.clamp(data.horse.z, -1300, 1300));
    }
    const upgrades = {};
    if (isObj(data.upg)) {
      for (const id in data.upg) {
        if (G.Items.get(id) && Number.isFinite(data.upg[id])) upgrades[id] = G.clamp(Math.floor(data.upg[id]), 0, 5);
      }
    }
    G.Inv.upgrades = upgrades;
    return true;
  };

  S.reset = function () {
    const a = G.storage.remove(KEY);
    const b = G.storage.remove(BACKUP);
    return a && b;
  };

  S.newGame = function () {
    G.Stats.level = 1; G.Stats.xp = 0;
    G.Inv.items = { potion: 3 };
    G.Inv.gold = 50;
    G.Inv.equip = { weapon: 'sword_traveler', armor: 'armor_cloth' };
    G.Inv.upgrades = {};
    G.Quests.state = {};
    G.State.tod = 9.5; G.State.day = 1;
    G.State.bossKilled = {}; G.State.openedChests = {};
    G.State.herbs = {}; G.State.shrines = {};
    G.State.respawn = 'shrine1';
    G.State.mainStage = 0; G.State.cleared = false; G.State.playtime = 0;
    G.State.titles = {}; G.State.killCount = 0;
    const p = G.Player;
    p.hp = G.Stats.maxHp();
    p.stamina = G.Stats.maxSta();
    p.pos.set(6, G.World.heightAt(6, 34), 34);
    G.Quests.start('main1');
  };
})();

/* ===== js/entities.js ===== */
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
  const BASE_MAX = G.Q.particles;
  const MAX = () => Math.max(240, Math.min(BASE_MAX,
    Math.floor(BASE_MAX * ((G.perf && G.perf.detail) || 1))));
  let P = [];   // {x,y,z,vx,vy,vz,life,max,size,r,g,b,grav,drag}
  let scene;

  FX.init = function (sc) {
    scene = sc;
    const n = BASE_MAX;
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
  FX.clear = function () { P.length = 0; };

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
      // dirX/dirZ 指定時は指向性放出 (ブレス等)、なければ全方位
      const dk = (o.dirX !== undefined) ? 0.3 : 1;
      // spawnR: 発生点を散らす半径。加算合成は同一点発生だと全粒が重なり
      // 必ず白飽和するため、大型バーストは最初から散らして色相を保つ
      const sr = o.spawnR || 0;
      P.push({
        x: x + (Math.random() - 0.5) * 2 * sr,
        y: y + (Math.random() - 0.5) * 1.2 * sr,
        z: z + (Math.random() - 0.5) * 2 * sr,
        vx: Math.cos(a) * sp * spread * dk + (o.dirX || 0) * sp,
        vy: up * sp * (0.5 + Math.random()),
        vz: Math.sin(a) * sp * spread * dk + (o.dirZ || 0) * sp,
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
    m.userData.baseS = scale;
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
        // 刀身は太め+中央の樋 (ゲームプレイ距離で細い白棒に見えない厚み)
        const blade = box(0.1, 0.85, 0.035, 0xc9d2da);
        blade.position.y = 0.55;
        const fuller = box(0.032, 0.7, 0.04, 0x9aa6b2);
        fuller.position.y = 0.5;
        const tip = new THREE.Mesh(new THREE.ConeGeometry(0.06, 0.14, 4), new THREE.MeshLambertMaterial({ color: 0xc9d2da }));
        tip.position.y = 1.02; tip.rotation.y = Math.PI / 4;
        const guard = box(0.24, 0.055, 0.06, 0x8f7a3a);
        guard.position.y = 0.12;
        const grip = box(0.05, 0.18, 0.05, 0x5a4630);
        weapon.add(blade, fuller, tip, guard, grip);
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
      // アーチ状キャノピー: 各板の縁が隣の板の縁と一致する連鎖配置 (隙間ゼロ)
      const WP = [
        [-1.212, -0.108, 0.34], [-0.615, 0.048, 0.17], [0, 0.1, 0],
        [0.615, 0.048, -0.17], [1.212, -0.108, -0.34]
      ];
      for (let i = 0; i < 5; i++) {
        const seg = box(0.64, 0.045, 0.55, i % 2 ? 0x5f9fb4 : 0x74b7cc);
        seg.position.set(WP[i][0], WP[i][1], 0);
        seg.rotation.z = WP[i][2];
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
        const rt = G.clamp(p.t / 0.45, 0, 1);
        g.rotation.x = -rt * Math.PI * 2;
        g.position.y = (p.baseY || 0) + 0.18 + Math.sin(rt * Math.PI) * 0.42;
        // 丸まり: スカッシュ+深い抱え込みで「転がり」に読ませる
        g.scale.setScalar(s * (1 - Math.sin(rt * Math.PI) * 0.22));
        legL.rotation.x = 1.5; legR.rotation.x = 1.5;
        armL.rotation.x = 1.25; armR.rotation.x = 1.25;
        return;
      }
      g.scale.setScalar(s);
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
      // 肩の毛のたてがみウェッジ (板の列は恐竜の背板に誤読されるため廃止)。
      // 根元を胴に食い込ませる — 跳躍ポーズで胴が動くと切断された板が浮いて見える
      for (let i = 0; i < 3; i++) {
        const w = box(0.56 - i * 0.1, 0.4 - i * 0.06, 0.3, i % 2 ? 0xcfe0ec : 0xbdd6e8);
        w.position.set(0, 0.82 - i * 0.04, 0.28 - i * 0.26);
        w.rotation.x = -0.3;
        g.add(w);
      }
      const bellyM = box(0.42, 0.16, 0.92, 0xe6ebf2);
      bellyM.position.y = 0.44;
      g.add(bellyM);
      const glow = new THREE.Sprite(new THREE.SpriteMaterial({
        map: G.makeRadialTex(48, [[0, 'rgba(120,210,255,0.55)'], [1, 'rgba(80,180,255,0)']]),
        transparent: true, depthWrite: false, blending: THREE.AdditiveBlending
      }));
      glow.position.set(0, 0.9, 0.55);
      glow.scale.set(0.45, 0.45, 1);
      glow.material.opacity = 0.4;
      g.add(glow);
    }
    const head = new THREE.Group();
    // 王狼は頭部を大きく・鼻先を長く (恐竜に誤読されない狼シルエット)
    const hw = conf.mane ? 1.6 : 1;
    const hm = box(0.34 * hw, 0.3 * hw, 0.42 * hw, fur);
    const snout = box(0.17 * hw, 0.15 * hw, conf.mane ? 0.5 : 0.22, conf.snout !== undefined ? conf.snout : 0x4e463e);
    snout.position.set(0, -0.05 * hw, conf.mane ? 0.52 : 0.28);
    if (conf.mane) {
      // 鼻先の黒い鼻 (小さく、鼻筋の上端に — 大きいと顔全体が黒く見える)
      const nose = box(0.09, 0.07, 0.06, 0x1a1a20);
      nose.position.set(0, 0.02, 0.84);
      head.add(nose);
    }
    // 王狼の耳は青グレー寄り — 背景の氷スパイクと白い尖形要素同士で混同しない
    const earL = box(conf.mane ? 0.14 * hw : 0.1 * hw, 0.14 * hw * (conf.mane ? 2.1 : 1), conf.mane ? 0.07 : 0.05, conf.mane ? 0xaec4d8 : fur);
    earL.position.set(-0.11 * hw, conf.mane ? 0.3 * hw : 0.24 * hw, -0.05);
    if (conf.mane) earL.rotation.z = 0.22;
    const earR = earL.clone(); earR.position.x = 0.11 * hw;
    if (conf.mane) earR.rotation.z = -0.22;
    const eyeL = box(conf.mane ? 0.09 : 0.05, conf.mane ? 0.07 : 0.05, 0.02, conf.eye !== undefined ? conf.eye : 0xcc2222);
    if (conf.mane) {
      eyeL.material = eyeL.material.clone();
      eyeL.material.emissive.set(0x2288cc);   // 王狼の眼光
    }
    // 拡大した頭部の前面に出す (hw未反映だと頭の内部に埋まり見えない)
    eyeL.position.set(-0.09 * hw, 0.05 * hw, 0.212 * hw);
    const eyeR = eyeL.clone(); eyeR.position.x = 0.09 * hw;
    head.add(hm, snout, earL, earR, eyeL, eyeR);
    if (conf.mane) {
      // 王の眼光 (氷青の発光)
      const mkGlow = (x) => {
        const gs = new THREE.Sprite(new THREE.SpriteMaterial({
          // ボス級の拡大リグでは眼グローも拡大される。中心アルファを抑えて
          // 顔の造形 (マズル/鼻) がグローに沈まない強度に
          map: G.makeRadialTex(32, [[0, 'rgba(120,205,255,0.66)'], [1, 'rgba(80,190,255,0)']]),
          transparent: true, depthWrite: false, blending: THREE.AdditiveBlending
        }));
        gs.position.set(x, 0.06 * hw, 0.36 * hw);
        gs.scale.set(0.42, 0.42, 1);
        return gs;
      };
      head.add(mkGlow(-0.09 * hw), mkGlow(0.09 * hw));
    }
    head.position.set(0, 0.78, 0.62);
    const tail = box(conf.mane ? 0.2 : 0.1, conf.mane ? 0.2 : 0.1, conf.mane ? 0.78 : 0.5, fur);
    tail.position.set(0, conf.mane ? 0.82 : 0.72, conf.mane ? -0.88 : -0.75);
    if (conf.mane) {
      tail.rotation.x = 0.45;   // 王の尾は高く掲げ、房状に太く→先細り
      const t1 = box(0.28, 0.28, 0.3, 0xe6ebf2);
      t1.position.set(0, 0.02, -0.42);
      const t2 = box(0.22, 0.22, 0.24, 0xcfe0ec);
      t2.position.set(0, 0.05, -0.64);
      const t3 = box(0.14, 0.14, 0.18, 0xe6ebf2);
      t3.position.set(0, 0.09, -0.8);
      tail.add(t1, t2, t3);
    }
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
    if (conf.mane) {
      // 白狼王は逆光でも白く読めるよう、毛皮に弱い自己発光を乗せる
      // 毛皮・たてがみ・腹・尾房すべてに発光を乗せる (逆光で黒く潰れる指摘)
      const brightParts = new Set([fur, 0xcfe0ec, 0xbdd6e8, 0xe6ebf2, 0x9fc2dc, 0xdde2ea]);
      g.traverse(o => {
        if (o.isMesh && o.material && o.material.emissive && brightParts.has(o.material.color.getHex())) {
          o.material = o.material.clone();
          o.material.emissive.set(0x38434f);   // 逆光でも「白狼」として読める下限輝度
        }
      });
    }

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
      // 待機中も胸が呼吸で上下する (静止した置物に見えない)
      const breath = Math.sin(t * 1.9 + (p.seed || 0)) * 0.03 * (1 - mv);
      body.position.y = 0.62 + Math.abs(Math.sin(wt)) * 0.06 * mv + breath;
      body.scale.y = 1 + breath * 0.8;
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
    // 首筋のたてがみ帯 (遠目でも馬と分かる記号)
    const maneNeck = box(0.1, 0.66, 0.16, maneC);
    maneNeck.position.set(0, 0.16, -0.22);
    neck.add(maneNeck);
    const headG = new THREE.Group();
    const hm = box(0.26, 0.28, 0.6, coat);
    hm.position.z = 0.1;
    const blaze = box(0.09, 0.2, 0.03, 0xe8e0d2);   // 鼻筋の白
    blaze.position.set(0, 0.02, 0.41);
    const maneM = box(0.1, 0.42, 0.3, maneC);
    maneM.position.set(0, 0.1, -0.3);
    const earL = box(0.06, 0.14, 0.05, coat); earL.position.set(-0.09, 0.24, -0.14);
    const earR = earL.clone(); earR.position.x = 0.09;
    // 手綱 (頭から鞍方向へ)
    const reinL = box(0.025, 0.025, 0.66, 0x2e2013);
    reinL.position.set(-0.15, -0.16, -0.34); reinL.rotation.x = 0.78;
    const reinR = reinL.clone(); reinR.position.x = 0.14;
    headG.add(hm, blaze, maneM, earL, earR, reinL, reinR);
    headG.position.set(0, 2.02, 1.02);
    // 尻尾は2節で流れをつける
    const tail = box(0.13, 0.62, 0.16, maneC);
    tail.position.set(0, 1.22, -0.95); tail.rotation.x = 0.5;
    const tail2 = box(0.1, 0.4, 0.12, maneC);
    tail2.position.set(0, -0.42, -0.1); tail2.rotation.x = 0.25;
    tail.add(tail2);
    // 鞍 + 赤い鞍敷
    const blanket = box(0.68, 0.07, 0.8, 0x8a3030);
    blanket.position.y = 1.5;
    const saddle = box(0.56, 0.15, 0.62, 0x6e4629);
    saddle.position.y = 1.56;
    const pommel = box(0.14, 0.12, 0.1, 0x53341e);
    pommel.position.set(0, 0.12, 0.24);
    saddle.add(pommel);
    const mkLeg = (x, z) => {
      const grp = new THREE.Group();
      const l = box(0.16, 0.78, 0.16, coat);
      l.position.y = -0.38;
      const hoof = box(0.21, 0.15, 0.21, 0x2e2620);
      hoof.position.y = -0.72;
      grp.add(l, hoof);
      grp.position.set(x, 0.78, z);
      return grp;
    };
    const legFL = mkLeg(-0.22, 0.6), legFR = mkLeg(0.22, 0.6);
    const legBL = mkLeg(-0.22, -0.6), legBR = mkLeg(0.22, -0.6);
    g.add(body, neck, headG, tail, blanket, saddle, legFL, legFR, legBL, legBR);
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
      // 疾走時は首を前方へ伸ばし上下にバウンス (静止画でも走りが読める)
      neck.rotation.x = -0.45 - mv * 0.35 + Math.sin(wt) * 0.06 * mv;
      headG.rotation.x = mv > 0.05 ? -0.1 + mv * 0.25 : Math.sin(t * 0.8 + (p.seed || 0)) * 0.18 + 0.12;
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
    // 首の第二節 (前方+上方へ伸ばし、頭を胴体より一段高く出すS字)
    const neckM2 = box(0.44, 0.44, 0.9, 0x453a4a);
    neckM2.position.set(0, 0.62, 1.0);
    neckM2.rotation.x = -0.55;
    neck.add(neckM2);
    const headG = new THREE.Group();
    const headM = box(0.5, 0.45, 0.8, dark);
    // 下顎は前へ突き出し、口の分かれ目が側面からも読めるように
    const jaw = box(0.42, 0.16, 0.72, belly);
    jaw.position.set(0, -0.26, 0.18);
    jaw.rotation.x = 0.1;
    // 口内は暗赤 (頭部の黒と同化せず、開口が読める)。牙で輪郭を崩す
    const mouth = box(0.36, 0.1, 0.6, 0x4a1010);
    mouth.position.set(0, -0.17, 0.22);
    mouth.rotation.x = 0.1;
    const fangMat = new THREE.MeshLambertMaterial({ color: 0xd8d2c4 });
    for (const fx of [-0.14, 0.14]) {
      const fang = new THREE.Mesh(new THREE.ConeGeometry(0.045, 0.14, 4), fangMat);
      fang.position.set(fx, -0.12, 0.52);
      fang.rotation.x = Math.PI;
      headG.add(fang);
    }
    // 眉弓 (眼窩の庇) — 箱頭の上面に段差を作り「竜の顔」の凹凸を出す
    const brow = box(0.56, 0.12, 0.3, 0x2c2432);
    brow.position.set(0, 0.24, 0.28);
    brow.rotation.x = -0.18;
    // 鼻先の隆起
    const snoutRidge = box(0.24, 0.1, 0.34, 0x453a4a);
    snoutRidge.position.set(0, 0.24, 0.62);
    // 大きく後方へ湾曲する対の角 (基部=黒曜石 / 先端=金 でテーパー)
    const hornMat = new THREE.MeshLambertMaterial({ color: 0x2b2334 });
    const hornTipMat = new THREE.MeshLambertMaterial({ color: 0xd8b96a });
    const mkHorn = side => {
      const grp = new THREE.Group();
      const h1 = new THREE.Mesh(boxGeo(0.13, 0.34, 0.13), hornMat);
      h1.position.y = 0.15;
      const h2 = new THREE.Mesh(boxGeo(0.07, 0.28, 0.07), hornTipMat);
      h2.position.set(0.03 * side, 0.36, -0.2); h2.rotation.x = -1.0; h2.rotation.z = 0.2 * side;
      grp.add(h1, h2);
      grp.position.set(0.17 * side, 0.28, -0.22);
      grp.rotation.x = -0.65;
      return grp;
    };
    const hornL = mkHorn(-1), hornR = mkHorn(1);
    // 目は残り火色の自己発光+グロー (正面・側面のどちらからも見える大きさ)
    const eyeMat = new THREE.MeshLambertMaterial({ color: 0xffb433, emissive: 0xff8a1e });
    const eyeL = new THREE.Mesh(boxGeo(0.15, 0.13, 0.1), eyeMat);
    eyeL.position.set(-0.2, 0.1, 0.32);
    const eyeR = eyeL.clone(); eyeR.position.x = 0.2;
    const eyeGlowMap = G.makeRadialTex(48, [[0, 'rgba(255,150,40,0.9)'], [1, 'rgba(255,90,0,0)']]);
    for (const side of [-1, 1]) {
      const gl = new THREE.Sprite(new THREE.SpriteMaterial({
        map: eyeGlowMap, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending
      }));
      gl.position.set(0.22 * side, 0.1, 0.36);
      gl.scale.set(0.5, 0.4, 1);
      headG.add(gl);
    }
    headG.add(headM, jaw, mouth, brow, snoutRidge, hornL, hornR, eyeL, eyeR);
    headG.position.set(0, 1.05, 1.5);
    headG.rotation.x = 0.22;   // 顎を引いた頭部姿勢 (直立積み木の解消)
    // レストポーズからS字: 第1節は後傾、第2節(neckM2)は前傾済み
    neckM.rotation.x = 0.3;
    neck.add(neckM, headG);
    neck.position.set(0, 1.5, 0.9);
    // 首の付け根と胸の隙間を埋める (正面から黒い内部面が見える指摘)
    const chestPlug = box(0.8, 0.7, 0.6, dark);
    chestPlug.position.set(0, 1.35, 0.85);
    g.add(chestPlug);
    // 体側の亀裂 (通常はほぼ体色。フェーズ2で赤熱させ、黒い体でも
    // フェーズ変化が体表から読めるようにする)
    // fog:false — 赤熱亀裂は地表フォグに埋もれず距離があっても「熱」と読める
    const crackMat = new THREE.MeshBasicMaterial({ color: 0x2e2430, fog: false });
    g.userData.crackMat = crackMat;
    // ジグザグの割れ目: 各体側に短いセグメントを交互の傾きで連結し、
    // 均一な矩形パッチではなく「亀裂」として読める形に
    for (const side of [-1, 1]) {
      for (let i = 0; i < 5; i++) {
        const cr = new THREE.Mesh(boxGeo(0.075, 0.4, 0.2), crackMat);
        cr.position.set(0.51 * side, 1.18 + (i % 2) * 0.22, 0.75 - i * 0.36);
        cr.rotation.x = (i % 2 ? 0.7 : -0.7);
        cr.rotation.y = side * 0.08;
        g.add(cr);
      }
    }
    // 尻尾は6節、先細り+緩やかに持ち上がるカーブ (俯瞰でも胴体からはみ出す)
    const tail = new THREE.Group();
    for (let i = 0; i < 6; i++) {
      const t = box(Math.max(0.13, 0.4 - i * 0.05), Math.max(0.1, 0.3 - i * 0.035), 0.7,
        i === 5 ? 0x7a2430 : dark);
      t.position.set(0, i * i * 0.03, -0.6 - i * 0.6);
      tail.add(t);
      // 尾棘は根元=黒→先端=暗赤のグラデーション (交互の縞はキャンディケインに
      // 見え、漆黒の竜のトーンから浮く)
      const spikeCol = [0x1c151f, 0x241a26, 0x2e1c28, 0x3a2028, 0x4c2028, 0x5e2229][i];
      const spike = box(0.09, Math.max(0.12, 0.3 - i * 0.03), 0.14, spikeCol);
      spike.position.set(0, 0.22 + i * i * 0.03, -0.6 - i * 0.6);
      tail.add(spike);
    }
    tail.position.set(0, 1.2, -0.9);
    tail.rotation.x = 0.22;   // 持ち上げは控えめ (正対時に尾先が頭上に重なる誤読の防止)
    // 背びれの棘列 (シルエットが遠目で竜と読める高さ)。
    // 間隔を詰め奥行きを重ねて、独立したドミノ板の列に見えないように
    for (let i = 0; i < 6; i++) {
      const sp = box(0.16, Math.max(0.35, 1.0 - i * 0.13), 0.46, i % 2 ? 0x241a26 : 0x7a2430);
      sp.position.set(0, 1.9 - i * 0.05, 0.65 - i * 0.42);
      sp.rotation.x = -0.25;
      g.add(sp);
    }
    const mkWing = (side) => {
      // 骨 (前縁+指骨3本) と膜パネル2枚の構造 — 平板プランク誤読の解消
      const grp = new THREE.Group();
      const boneC = 0x2a2030;
      const bone = box(2.6, 0.11, 0.14, boneC);
      bone.position.set(1.3 * side, 0.02, 0.34);
      const f1 = box(0.08, 0.07, 0.85, boneC);
      f1.position.set(0.85 * side, -0.02, -0.08);
      f1.rotation.y = -0.12 * side;
      const f2 = f1.clone(); f2.position.x = 1.65 * side; f2.rotation.y = -0.3 * side;
      const f3 = f1.clone(); f3.position.x = 2.35 * side; f3.scale.z = 0.72; f3.rotation.y = -0.5 * side;
      const mem1 = box(0.86, 0.03, 0.86, 0x3a2438);
      mem1.position.set(1.25 * side, -0.03, 0.0);
      mem1.rotation.x = 0.09;
      const mem2 = box(1.1, 0.03, 0.9, 0x2c1e2e);
      mem2.position.set(2.05 * side, -0.06, -0.05);
      mem2.rotation.x = 0.14;
      const edge = box(2.5, 0.05, 0.1, 0x7a2430);
      edge.position.set(1.3 * side, -0.1, -0.5);
      grp.add(bone, f1, f2, f3, mem1, mem2, edge);
      grp.position.set(0.45 * side, 1.65, 0.2);
      return grp;
    };
    const wingL = mkWing(-1), wingR = mkWing(1);
    // 前後のピッチ傾け: 真正面から見ても翼膜の面積が残り、線に潰れない
    wingL.rotation.x = 0.12; wingR.rotation.x = 0.12;
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
      // 飛行+移動時は胴体を進行方向へピッチ (直立トーテムの静止浮遊に見えない)
      g.rotation.x = fly * (0.1 + mv * 0.18);
      const flap = fly > 0.05 ? Math.sin(t * 6) * (0.5 + fly * 0.4) : Math.sin(t * 1.2) * 0.06;
      wingL.rotation.z = -flap - 0.15;
      wingR.rotation.z = flap + 0.15;
      // 飛行/立ち上がり時は首を前傾させS字を保つ (垂直ブロック+水平翼の
      // 十字型シルエットにならない)
      neck.rotation.x = -0.2 + Math.sin(t * 1.1) * 0.05 + fly * 0.3;
      tail.rotation.y = Math.sin(t * 0.9) * 0.45;
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
      // 2層構造: 外周リング=攻撃範囲、内側フィル=着弾タイミングゲージ
      // fog:false — 竜の頂の地表フォグ等に予兆が埋もれない
      const m = new THREE.Mesh(
        new THREE.RingGeometry(0.9, 1.0, 24),
        new THREE.MeshBasicMaterial({
          color: 0xd01818, transparent: true, opacity: 0.6,
          depthWrite: false, side: THREE.DoubleSide, fog: false
        })
      );
      m.rotation.x = -Math.PI / 2;
      m.visible = false;
      m.renderOrder = 2;
      // 暗色の赤フィル: 白い氷床でも緑の草地でも沈まないコントラスト
      const d = new THREE.Mesh(
        new THREE.CircleGeometry(1, 24),
        new THREE.MeshBasicMaterial({
          color: 0xb31414, transparent: true, opacity: 0.3,
          depthWrite: false, side: THREE.DoubleSide, fog: false
        })
      );
      d.rotation.x = -Math.PI / 2;
      d.visible = false;
      d.renderOrder = 2;
      // 全域の薄い危険フィル (ゲージが小さい序盤でも内外が読める)
      const f = new THREE.Mesh(
        new THREE.CircleGeometry(1, 24),
        new THREE.MeshBasicMaterial({
          color: 0x8a1010, transparent: true, opacity: 0.17,
          depthWrite: false, side: THREE.DoubleSide, fog: false
        })
      );
      f.rotation.x = -Math.PI / 2;
      f.visible = false;
      f.renderOrder = 2;
      scene.add(m); scene.add(d); scene.add(f);
      pool.push({ m, d, f });
    }
  };
  const queue = [];
  R.begin = function () { queue.length = 0; };
  /* windup 中の敵の足元に出す。t: 0..1 進行度, r: 半径 */
  R.show = function (x, z, r, t) {
    queue.push({ x, z, r, t });
  };
  R.end = function () {
    // 発動が近い順に優先。フィルは上位2つだけに絞り、重なりの混濁を防ぐ
    queue.sort((a, b) => b.t - a.t);
    const n = Math.min(queue.length, pool.length);
    for (let i = 0; i < n; i++) {
      const q = queue[i], s = pool[i];
      const gh = G.World.heightAt(q.x, q.z);
      s.m.visible = true;
      s.m.position.set(q.x, gh + 0.12, q.z);
      s.m.scale.setScalar(q.r);
      // 非切迫のリングは薄い輪郭のみ — 濃い輪郭が2つ並ぶと両方フィル済みに
      // 見え、どちらを避けるべきか読めない
      s.m.material.opacity = i === 0 ? 0.5 + q.t * 0.35 : 0.22;
      // フィル (タイミングゲージ+全域) は最も切迫した1つだけ。
      // 2つ以上に出すと「どれを避けるべきか」が読めなくなる
      const fill = i === 0;
      s.d.visible = fill;
      s.f.visible = fill;
      if (fill) {
        // 内側フィルが t=1 で外周に到達する = 避けるタイミングが読める。
        // 高さ差は最小限に (差が大きいと浅い視線でフィルが輪郭から
        // 下にはみ出し、同心に見えない)
        s.d.position.set(q.x, gh + 0.115, q.z);
        s.d.scale.setScalar(Math.max(0.05, q.r * q.t));
        s.d.material.opacity = 0.28 + q.t * 0.22;
        s.f.position.set(q.x, gh + 0.11, q.z);
        s.f.scale.setScalar(q.r);
      }
    }
    for (let i = n; i < pool.length; i++) {
      pool[i].m.visible = false; pool[i].d.visible = false; pool[i].f.visible = false;
    }
  };
})();

/* ======================= 剣筋トレイル ======================= */
(function () {
  const SA = G.SwingArc = {};
  let scene;
  const pool = [];
  SA.init = function (sc) {
    scene = sc;
    const sector = new THREE.RingGeometry(1.35, 2.25, 18, 1, -1.2, 2.4);
    const full = new THREE.RingGeometry(1.5, 2.85, 24);
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
    // 短命VFXは低FPS計測では写らないため証跡ログを残す
    if (G.dmgLog) console.log('[dbg] swing arc kind=' + kind);
    const p = pool[kind === 2 ? 2 : (pool[0].t < 1 ? 1 : 0)];
    p.t = 0;
    p.kind = kind;
    p.decay = kind === 0 ? 4.2 : 2.0;   // 強/回転は約0.5秒残す
    p.mesh.visible = true;
    p.mesh.position.set(x, y + 1.05, z);
    p.mesh.rotation.z = -yaw + Math.PI / 2 - 1.2;
    // 通常=白 / 強撃=金 / 回転=鋼青 — 敵予兆の赤・地面の緑と色相分離
    p.mesh.material.color.set(kind === 1 ? 0xffd27a : kind === 2 ? 0x9fc8f0 : 0xe8f2ff);
    const s = kind === 1 ? 1.2 : 1;
    p.mesh.scale.set(s, s, s);
  };
  SA.update = function (dt) {
    for (const p of pool) {
      if (p.t >= 1) { p.mesh.visible = false; continue; }
      p.t += dt * (p.decay || 4.2);
      // 加算合成の白飛びを抑えるためピークを低めに (氷床などの明色地面対策)
      p.mesh.material.opacity = Math.max(0, (p.kind === 2 ? 0.45 : 0.6) * (1 - p.t));
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
    // 放射フォールオフのアルファマップ — ハードエッジの単色ポリゴン円盤は
    // プレースホルダーに見える
    const alphaTex = G.makeRadialTex(64,
      [[0, 'rgba(255,255,255,1)'], [0.55, 'rgba(255,255,255,0.85)'], [1, 'rgba(255,255,255,0)']]);
    const geo = new THREE.CircleGeometry(1.3, 16);
    geo.rotateX(-Math.PI / 2);
    for (let i = 0; i < 6; i++) {
      const m = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({
        color: 0x14100c, transparent: true, opacity: 0, depthWrite: false,
        alphaMap: alphaTex
      }));
      m.visible = false;
      m.renderOrder = 1;
      scene.add(m);
      pool.push({ mesh: m, t: 1 });
    }
  };
  S.add = function (x, z, color, scale) {
    const p = pool[idx++ % pool.length];
    p.t = 0;
    p.mesh.visible = true;
    p.mesh.material.color.set(color !== undefined ? color : 0x14100c);
    p.mesh.position.set(x, G.World.heightAt(x, z) + 0.08, z);
    p.mesh.scale.setScalar((scale || 1) * (0.8 + Math.random() * 0.5));
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
    const k = G.clamp(1 - (a.pos.y - gh) * 0.15, 0.4, 1);
    a.shadow.material.opacity = k * (G.shadowsOn ? 0.5 : 1);
    // 太陽が低いほど影を長く伸ばす (夕暮れの画作り)
    const elv = (G.Sky && G.Sky.sunElev !== undefined) ? G.Sky.sunElev : 1;
    const az = (G.Sky && G.Sky.sunAz) || 0;
    const stretch = G.clamp(0.42 / Math.max(elv, 0.17), 1, 2.4);
    const bs = a.shadow.userData.baseS || 1.3;
    a.shadow.rotation.y = az;
    a.shadow.scale.set(bs, 1, bs * stretch);
    // 伸びた分は太陽と反対側へオフセット
    const off = bs * (stretch - 1) * 0.4;
    a.shadow.position.set(
      a.pos.x - Math.sin(az) * off, gh + 0.06, a.pos.z - Math.cos(az) * off);
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
    // 自機の恒常識別リング: 乱戦で人型敵と配色が近くても、足元のリングで
    // 「自分」が一目で判別できる (ロックオンUIとの誤読も防ぐ)
    const idRing = new THREE.Mesh(
      new THREE.RingGeometry(0.5, 0.62, 24),
      new THREE.MeshBasicMaterial({
        color: 0xc8ecff, transparent: true, opacity: 0.5,
        depthWrite: false, depthTest: false, side: THREE.DoubleSide, fog: false
      })
    );
    idRing.rotation.x = -Math.PI / 2;
    idRing.position.y = 0.09;
    idRing.renderOrder = 3;   // 予兆フィルより上 — 乱戦時こそ自機が読める
    rig.group.add(idRing);
    // 暗色の外縁: 明色の砂道・雪面でもリングが白飛びしない図地分離
    const idRingDark = new THREE.Mesh(
      new THREE.RingGeometry(0.62, 0.72, 24),
      new THREE.MeshBasicMaterial({
        color: 0x0c1420, transparent: true, opacity: 0.4,
        depthWrite: false, depthTest: false, side: THREE.DoubleSide, fog: false
      })
    );
    idRingDark.rotation.x = -Math.PI / 2;
    idRingDark.position.y = 0.085;
    idRingDark.renderOrder = 3;
    rig.group.add(idRingDark);
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
    G.haptic(45);
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
    if (G.dmgLog) console.log('[dbg] attack start' + (heavy ? ' heavy' : spin ? ' spin' : ''));
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
    } else {
      // 非ロック時は前方±100°・6.5m内の最寄り敵へ向き直る
      // (タッチのタップ攻撃が微妙な向きズレで空振りし続けるのを防ぐソフトロック)
      let best = null, bd = 6.5 * 6.5;
      const scan = e => {
        if (!e.alive) return;
        const dx = e.pos.x - P.pos.x, dz = e.pos.z - P.pos.z;
        const d2 = dx * dx + dz * dz;
        if (d2 >= bd) return;
        let da = Math.atan2(dx, dz) - P.yaw;
        da = Math.atan2(Math.sin(da), Math.cos(da));
        if (Math.abs(da) > 1.75) return;
        bd = d2; best = e;
      };
      for (const e of G.Enemies.list) scan(e);
      for (const b of G.Enemies.bosses) scan(b);
      if (best) P.yaw = Math.atan2(best.pos.x - P.pos.x, best.pos.z - P.pos.z);
    }
  };

  P.tryRoll = function () {
    if (!P.alive || P.state === 'roll' || P.state === 'dead') return;
    if (P.mounted) G.Horse.dismount();
    if (P.stamina < 8) return;
    P.state = 'roll'; P.stateT = 0;
    useStamina(18);
    G.Audio.sfx('roll');
    // 低FPS撮影でも1フレームは写る寿命 (回避が「転倒」に誤読されない動きの手掛かり)
    G.FX.burst(P.pos.x, P.pos.y + 0.2, P.pos.z, { n: 10, color: 0x7e7460, speed: 2.2, life: 0.7, up: 0.4, spawnR: 0.4 });
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

  /* ロックオンマーカー (金の下向き三角) */
  let lockMarkSpr = null;
  function lockMark() {
    if (lockMarkSpr) return lockMarkSpr;
    const c = document.createElement('canvas');
    c.width = 64; c.height = 64;
    const x = c.getContext('2d');
    x.beginPath(); x.moveTo(13, 15); x.lineTo(51, 15); x.lineTo(32, 46); x.closePath();
    x.lineWidth = 6; x.strokeStyle = 'rgba(24,16,4,0.9)'; x.stroke();
    x.fillStyle = '#ffd35a'; x.fill();
    lockMarkSpr = new THREE.Sprite(new THREE.SpriteMaterial({
      map: new THREE.CanvasTexture(c), transparent: true, depthWrite: false
    }));
    lockMarkSpr.scale.set(0.55, 0.55, 1);
    lockMarkSpr.visible = false;
    scene.add(lockMarkSpr);
    return lockMarkSpr;
  }

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
      G.haptic(P.heavy ? 24 : 12);
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

    // ロックオン対象消滅 → 近くの敵へ自動リターゲット (UIの迷子を防ぐ)
    if (P.target && (!P.target.alive || G.dist2(P.pos.x, P.pos.z, P.target.pos.x, P.target.pos.z) > 40 * 40)) {
      const dead = !P.target.alive;
      P.target = null;
      if (dead) {
        let best = null, bd = 12 * 12;
        for (const e of G.Enemies.all()) {
          if (!e.alive) continue;
          const d2 = G.dist2(P.pos.x, P.pos.z, e.pos.x, e.pos.z);
          if (d2 < bd) { bd = d2; best = e; }
        }
        P.target = best;
      }
    }
    // ロックオン対象の頭上に金のマーカー+足元に金リング (予兆の赤と別の記号体系。
    // 至近で敵と自機が重なっても足元リングで対象が読める)
    const lm = lockMark();
    if (!P._tgtRing) {
      P._tgtRing = new THREE.Mesh(
        new THREE.RingGeometry(0.78, 0.9, 24),
        new THREE.MeshBasicMaterial({
          color: 0xffd35a, transparent: true, opacity: 0.55,
          depthWrite: false, side: THREE.DoubleSide, fog: false
        })
      );
      P._tgtRing.rotation.x = -Math.PI / 2;
      P._tgtRing.renderOrder = 3;
      scene.add(P._tgtRing);
    }
    if (P.target && P.target.alive) {
      const th = (P.target.T && P.target.T.barH) || (P.target.D && P.target.D.barH) || 2;
      lm.visible = true;
      lm.position.set(P.target.pos.x,
        P.target.pos.y + th + 0.45 + Math.sin(G.time * 5) * 0.07, P.target.pos.z);
      P._tgtRing.visible = true;
      const tr = (P.target.radius || 0.5) + 0.35;
      P._tgtRing.scale.setScalar(tr);
      P._tgtRing.position.set(P.target.pos.x, P.target.pos.y + 0.1, P.target.pos.z);
    } else {
      lm.visible = false;
      P._tgtRing.visible = false;
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

    // 通常敵との重なり分離 (密着スタック防止)
    for (const e of G.Enemies.list) {
      if (!e.alive) continue;
      const dx = P.pos.x - e.pos.x, dz = P.pos.z - e.pos.z;
      const rr = e.radius + P.radius - 0.1;
      const d2 = dx * dx + dz * dz;
      if (d2 < rr * rr && d2 > 0.0001) {
        // 低フレームレートでも1フレームで解決する強い押し出し
        // (攻撃の踏み込みで敵の内部まで入り、モデルが完全に重なる指摘)
        const d = Math.sqrt(d2);
        const push = (rr - d) * 0.95;
        P.pos.x += dx / d * push * 0.6; P.pos.z += dz / d * push * 0.6;
        e.pos.x -= dx / d * push * 0.4; e.pos.z -= dz / d * push * 0.4;
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
    P.fovBoost = P.gliding ? 0.8 : 0;
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
        // 速度感の演出用 (カメラFOVブースト)
        P.fovBoost = P.mounted ? (sprint ? 1 : 0.55) : P.gliding ? 0.8 : sprint ? 0.5 : 0;
        // ロックオン中は対象を向きつつ移動
        if (P.target && P.target.alive && !sprint && !P.mounted && !P.gliding) {
          P.yaw = G.angLerp(P.yaw, Math.atan2(P.target.pos.x - P.pos.x, P.target.pos.z - P.pos.z), G.damp(12, dt));
        } else {
          P.yaw = G.angLerp(P.yaw, dir, G.damp(P.mounted ? 5 : 11, dt));
        }
        // 浅瀬では減速 (ウェード)
        const wading = P.pos.y < G.World.WATER_Y - 0.15 && P.grounded;
        const wspd = wading ? spd * 0.55 : spd;
        G.Actors.groundMove(P, Math.sin(dir) * wspd, Math.cos(dir) * wspd, dt);
        mv = Math.min(1, wspd / (P.mounted ? 13 : 7.8));
        P.state = 'move';
        // 足音 / 水しぶき
        P.stepT = (P.stepT || 0) + dt * wspd;
        if (P.stepT > (P.mounted ? 3.2 : 2.2) && P.grounded) {
          P.stepT = 0;
          G.Audio.sfx('step');
          if (wading) {
            G.FX.burst(P.pos.x, G.World.WATER_Y + 0.1, P.pos.z,
              { n: 5, color: 0xbfe0ec, speed: 1.6, life: 0.45, size: 2.4, up: 1.2, gravity: 5 });
          }
        }
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
    // 夜間は自機に最低輝度の下駄 (月光逆光・暗い樹林背景で完全な黒
    // シルエットにならず、色と形が常に読める)
    const nightLit = (G.Sky.lightLevel || 1) < 0.3;
    if (P._nightLit !== nightLit) {
      P._nightLit = nightLit;
      rig.group.traverse(o => {
        if (o.isMesh && o.material && o.material.emissive && !o.material.userData._noNight) {
          // 控えめに — 強すぎると至近で陰影が平坦化し単色の板に見える
          o.material.emissive.setHex(nightLit ? 0x161e2a : 0x000000);
        }
      });
    }
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
    wolf:      { name: '野狼',       rigFn: 'wolf',     barH: 1.4, hp: 40,  atk: 15, speed: 5.2, xp: 14, gold: 6,  aggroR: 18, atkR: 1.7, windup: 0.45, cool: 1.2, radius: 0.5, scale: 1,   drops: [['pelt', 0.6], ['potion', 0.08]] },
    goblin:    { name: 'ゴブリン',   rigFn: 'goblin',   barH: 1.9, hp: 55,  atk: 18, speed: 3.8, xp: 18, gold: 12, aggroR: 16, atkR: 1.9, windup: 0.55, cool: 1.5, radius: 0.45, scale: 0.9, drops: [['potion', 0.12], ['magicstone', 0.1]] },
    skeleton:  { name: 'スケルトン', rigFn: 'skeleton', barH: 2.0, hp: 45,  atk: 15, speed: 3.2, xp: 20, gold: 14, aggroR: 22, atkR: 12,  windup: 0.7,  cool: 2.4, radius: 0.45, scale: 1,   ranged: true, drops: [['bone', 0.6], ['magicstone', 0.12]] },
    golemling: { name: '岩の子鬼',   rigFn: 'golemling',barH: 1.8, hp: 90,  atk: 20, speed: 2.6, xp: 30, gold: 20, aggroR: 14, atkR: 2.3, windup: 0.85, cool: 2.0, radius: 0.6, scale: 0.62, poise: 3, drops: [['magicstone', 0.5]] },
    scorpion:  { name: '砂蠍',       rigFn: 'scorpion', barH: 1.3, hp: 50,  atk: 19, speed: 4.4, xp: 22, gold: 15, aggroR: 15, atkR: 1.8, windup: 0.5,  cool: 1.4, radius: 0.55, scale: 1.1, drops: [['magicstone', 0.15], ['potion', 0.1]] },
    bandit:    { name: '盗賊',       rigFn: 'bandit',   barH: 1.9, hp: 70,  atk: 22, speed: 4.2, xp: 26, gold: 24, aggroR: 17, atkR: 1.9, windup: 0.5,  cool: 1.4, radius: 0.45, scale: 0.95, drops: [['potion', 0.15], ['magicstone', 0.1]] },
    fireimp:   { name: '火の小鬼',   rigFn: 'fireimp',  barH: 1.5, hp: 48,  atk: 19, speed: 3.6, xp: 24, gold: 18, aggroR: 20, atkR: 13,  windup: 0.6,  cool: 2.2, radius: 0.4, scale: 0.7, ranged: true, proj: 'fire', drops: [['magicstone', 0.3]] },
    mimic:     { name: 'ミミック',   rigFn: 'mimic',    barH: 1.4, hp: 130, atk: 26, speed: 5.0, xp: 60, gold: 80, aggroR: 30, atkR: 1.8, windup: 0.4,  cool: 1.1, radius: 0.55, scale: 1, poise: 3, drops: [['hipotion', 0.5], ['magicstone', 0.5]] },
    nightwisp: { name: '夜の骸骨',   rigFn: 'skeleton', barH: 2.0, hp: 38,  atk: 17, speed: 4.0, xp: 16, gold: 10, aggroR: 26, atkR: 1.8, windup: 0.5,  cool: 1.3, radius: 0.45, scale: 1, night: true, drops: [['bone', 0.5]] }
  };
  E.TYPES = TYPES;

  function buildRig(type, T) {
    switch (T.rigFn) {
      case 'wolf': return G.Rigs.wolf({ scale: T.scale });
      case 'goblin': return G.Rigs.humanoid({ scale: T.scale, skin: 0x4f8a72, hair: 0x223a30, cloth: 0x9a3a2e, cloth2: 0x5a221c, weapon: 'club' });
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

  /* 「!」アグロマーカーの共有マテリアル */
  let markMat = null;
  function getMarkMat() {
    if (markMat) return markMat;
    const c = document.createElement('canvas');
    c.width = 64; c.height = 64;
    const x = c.getContext('2d');
    x.font = 'bold 54px sans-serif';
    x.textAlign = 'center'; x.textBaseline = 'middle';
    x.lineWidth = 9; x.strokeStyle = '#fff';
    x.strokeText('!', 32, 34);
    x.fillStyle = '#ff3030';
    x.fillText('!', 32, 34);
    markMat = new THREE.SpriteMaterial({
      map: new THREE.CanvasTexture(c), transparent: true, depthWrite: false
    });
    return markMat;
  }

  E.damage = function (e, dmg, crit) {
    if (!e.alive) return;
    e.hp -= dmg;
    e.aggro = true;
    e.hurtT = 0.3;
    G.UI.dmgNum(e.pos.x, e.pos.y + (e.T && e.T.barH ? e.T.barH - 0.2 : 1.6), e.pos.z, dmg, { crit, tgt: e });
    G.FX.burst(e.pos.x, e.pos.y + 1, e.pos.z, { n: crit ? 8 : 5, color: 0xffd24a, speed: 3.2, life: 0.28, size: 1.6 });
    G.FX.burst(e.pos.x, e.pos.y + 0.9, e.pos.z, { n: 1, color: 0xfff0c8, speed: 0.05, life: 0.15, size: 4.2, gravity: 0, drag: 0 });
    if (e.hp <= 0) { kill(e); return; }
    // ノックバック (プレイヤーから離れる方向へ、強/回転は大きく)
    const kb = (G.Player.spin || G.Player.heavy) && G.Player.state === 'attack' ? 1.1 : 0.4;
    const kdx = e.pos.x - G.Player.pos.x, kdz = e.pos.z - G.Player.pos.z;
    const kd = Math.hypot(kdx, kdz) || 1;
    const c2 = G.World.collide(e.pos.x + kdx / kd * kb, e.pos.z + kdz / kd * kb, e.radius);
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
  let spawnT = 0, nightT = 0, attackerCount = 0;
  function manageSpawns(dt) {
    if (G.noSpawn) return;   // 計測/撮影用: 新規スポーン抑止
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
      // 気づき演出: 頭上に「!」
      e.aggroMarkT = 1.4;
      if (!e.mark) {
        e.mark = new THREE.Sprite(getMarkMat());
        e.mark.scale.set(0.62, 0.88, 1);
        e.mark.position.y = (T.barH || 1.6) + 0.8;   // HPバーと密着しない間隔
        e.rig.group.add(e.mark);
      }
    }
    if (e.aggro && (!p.alive || dist > T.aggroR * 2.6)) {
      e.aggro = false;
      e.state = 'idle';
    }
    // 村の中心部は安全地帯: 追跡してきた敵はアグロを解いて巣へ帰る
    if (e.aggro && G.dist2(e.pos.x, e.pos.z, 0, 0) < 26 * 26) {
      e.aggro = false;
      e.state = 'idle';
      e.wanderT = 0;
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
        } else if (e.cool <= 0 && attackerCount < 2) {
          // 攻撃トークン制: 同時に仕掛けるのは2体まで (残りは牽制に回る)
          e.state = 'windup'; e.stateT = 0;
          attackerCount++;
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
    // 被弾の仰け反り (hurtT が残る間だけ後傾)
    if (e.hurtT) e.hurtT = Math.max(0, e.hurtT - dt);
    e.rig.group.rotation.x = -((e.hurtT || 0) / 0.3) * 0.24;
    // 「!」マーカーの寿命と浮遊 (ロックオン対象は金▼と重なるため出さない)
    if (e.mark) {
      if (e.aggroMarkT > 0) e.aggroMarkT -= dt;
      e.mark.visible = e.aggroMarkT > 0 && G.Player.target !== e;
      if (e.mark.visible) e.mark.position.y = (T.barH || 1.6) + 0.8 + Math.sin(G.time * 6) * 0.06;
    }
    e.rig.pose({
      state: e.state === 'windup' ? 'windup' : e.state,
      t: e.stateT, windup: T.windup, moveAmt: e.moveAmt, seed: e.seed,
      baseY: e.pos.y,
      atkT: e.state === 'attack' ? G.clamp(e.stateT / 0.38, 0, 1) : 0,
      combo: 0
    });
    G.Actors.updateShadow(e);
  }

  /* 遮蔽フェードの適用/解除 (共有マテリアルの「!」マーカーは除外) */
  function setOccFade(e, on) {
    if (e._faded === !!on) return;
    e._faded = !!on;
    if (G.dmgLog) console.log('[dbg] occluder fade', on ? 'on' : 'off', e.bossId || (e.T && e.T.name) || '');
    e.rig.group.traverse(o => {
      if (o === e.mark) return;
      if ((o.isMesh || o.isSprite) && o.material) {
        if (o.userData._op0 === undefined) {
          o.userData._op0 = o.material.opacity;
          o.userData._tr0 = o.material.transparent;
        }
        o.material.transparent = on ? true : o.userData._tr0;
        o.material.opacity = on ? Math.min(0.3, o.userData._op0) : o.userData._op0;
        // transparent の切替はシェーダ再コンパイルが必要 — これが無いと
        // opacity を書いても視覚に反映されない
        o.material.needsUpdate = true;
      }
    });
  }

  E.update = function (dt) {
    manageSpawns(dt);
    G.TelegraphRing.begin();
    // 攻撃トークン: 現在攻撃動作中の敵数 (同時攻撃は2体まで)
    attackerCount = 0;
    for (const e of list) {
      if (e.alive && (e.state === 'windup' || e.state === 'attack')) attackerCount++;
    }
    // remove() が splice するので逆順走査 (毎フレームの配列複製を避ける)
    for (let i = list.length - 1; i >= 0; i--) {
      const e = list[i];
      updateEnemy(e, dt);
      if (e.alive && e.state === 'windup') {
        G.TelegraphRing.show(e.pos.x, e.pos.z, (e.T.atkR > 5 ? 1.2 : e.T.atkR + 0.6), G.clamp(e.stateT / e.T.windup, 0, 1));
      }
    }
    // 敵同士の相互分離 (同一地点に重なって個体が判別できなくなるのを防ぐ)
    for (let i = 0; i < list.length; i++) {
      const a = list[i];
      if (!a.alive) continue;
      for (let j = i + 1; j < list.length; j++) {
        const c = list[j];
        if (!c.alive) continue;
        const dx = c.pos.x - a.pos.x, dz = c.pos.z - a.pos.z;
        const rr = a.radius + c.radius + 0.35;
        const d2 = dx * dx + dz * dz;
        if (d2 < rr * rr && d2 > 0.0001) {
          const d = Math.sqrt(d2), push = (rr - d) / d * 0.5;
          a.pos.x -= dx * push; a.pos.z -= dz * push;
          c.pos.x += dx * push; c.pos.z += dz * push;
        }
      }
    }
    // カメラと自機の間に立つ敵の遮蔽フェード (乱戦時に自機が完全に隠れる指摘)
    const camP = G.Camera && G.Camera.cam ? G.Camera.cam.position : null;
    if (camP) {
      const pp = G.Player.pos;
      const sx = pp.x - camP.x, sy = pp.y + 1.2 - camP.y, sz = pp.z - camP.z;
      const segLen2 = sx * sx + sy * sy + sz * sz;
      const occTest = (e, r2) => {
        if (segLen2 <= 1) return false;
        const ex = e.pos.x - camP.x, ey = e.pos.y + 1 - camP.y, ez = e.pos.z - camP.z;
        const t = (ex * sx + ey * sy + ez * sz) / segLen2;
        if (t <= 0.15 || t >= 0.95) return false;
        const ox = ex - sx * t, oy = ey - sy * t, oz = ez - sz * t;
        return (ox * ox + oy * oy + oz * oz) < r2;
      };
      for (const e of list) {
        if (!e.alive || !e.rig) continue;
        // 判定半径は敵の体格+余裕 (狭すぎて下半身遮蔽で不発だった)
        const rr = e.radius + 1.1;
        setOccFade(e, occTest(e, rr * rr));
      }
      // ボスも同様 (ボス戦中に自機がボス胴体に完全遮蔽される指摘)。
      // 判定半径はボスの体格に合わせて広めに
      for (const b of bosses) {
        if (!b.alive || !b.rig) continue;
        setOccFade(b, occTest(b, Math.max(2.5, (b.D.pushR || 2) * 1.6)));
      }
    }
    for (const b of bosses) {
      G.Bosses.update(b, dt);
      if (b.alive && b.state === 'windup') {
        const t = G.clamp(b.stateT / (b.windupDur || 0.8), 0, 1);
        G.TelegraphRing.show(b.pos.x, b.pos.z, b.radius + 2.4, t);
        // 遠隔攻撃は着弾予定地 (プレイヤー足元) にも警告
        if (b.nextAtk === 'fireball' || b.nextAtk === 'breath' || b.nextAtk === 'rock') {
          const p = G.Player;
          G.TelegraphRing.show(p.pos.x, p.pos.z, 2.4, t);
        }
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
      name: '白狼王フェンリル', hp: 220, atk: 22, speed: 7.2, xp: 300, gold: 250,
      x: -430, z: -140, arenaR: 34, radius: 1.3, pushR: 3.1, barH: 3.4,
      build: () => G.Rigs.wolf({ scale: 2.9, fur: 0xd8d8e0, snout: 0xdde2ea, eye: 0x44ddff, mane: true })
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
    G.UI.dmgNum(b.pos.x, ny, b.pos.z, dmg, { crit, tgt: b });
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

    // 絶対リーシュ: 縄張りを大きく離れたら即座に帰還 (越境防止)
    if (distHome > D.arenaR * 2) {
      b.pos.set(D.x, G.World.heightAt(D.x, D.z), D.z);
      b.hp = b.maxHp;
      b.engaged = false;
      b.state = 'idle'; b.stateT = 0;
      G.events.emit('bossDisengage');
    }

    // 交戦開始/離脱
    if (!b.engaged && p.alive && dist < 26) {
      b.engaged = true;
      b.cool = b.bossId === 'dragon' ? 0.4 : 1.0;   // 開幕の間延び防止
      G.Audio.sfx('roar');
      G.events.emit('bossEngage', b);
      // 開幕にボスとプレイヤーが重なっていたら引き離す (めり込み絵の防止)
      if (dist < D.pushR + 2) {
        const a = Math.atan2(p.pos.x - b.pos.x, p.pos.z - b.pos.z);
        const rr = D.pushR + 3;
        const c = G.World.collide(b.pos.x + Math.sin(a) * rr, b.pos.z + Math.cos(a) * rr, 0.5);
        p.pos.x = c.x; p.pos.z = c.z;
        p.pos.y = G.World.heightAt(c.x, c.z);
      }
    }
    if (b.engaged && (!p.alive || dist > D.arenaR + 30)) {
      b.engaged = false;
      b.hp = Math.min(b.maxHp, b.hp + b.maxHp * 0.5);
      G.events.emit('bossDisengage');
    }

    b.cool = Math.max(0, b.cool - dt);
    let mv = 0;
    const phase2 = b.hp < b.maxHp * 0.5;

    // フェーズ2移行の一回演出 (咆哮+シェイク+バースト+残留デカール)
    if (phase2 && !b.phase2Cued && b.engaged && b.alive) {
      b.phase2Cued = true;
      G.Audio.sfx('roar');
      G.events.emit('shake', 0.6);
      // 白飽和を避けるため彩度のある色で (氷=青 / 竜=橙)
      const c = b.bossId === 'fenrir' ? 0x3d96e0 : b.bossId === 'dragon' ? 0xff6a20 : 0xc8b070;
      // サイズ/数を抑えて加算の白飽和を防ぎ、色相が読めるように
      G.FX.burst(b.pos.x, b.pos.y + 2, b.pos.z, {
        n: 16, color: c, speed: 9, up: 0.8, gravity: 2, life: 0.9, size: 2.2, spawnR: 1.4
      });
      // 足元に残留リング (低FPS計測でも痕跡が写る)。氷床上でも影と見分く濃い霜色
      G.Scorch.add(b.pos.x, b.pos.z,
        b.bossId === 'fenrir' ? 0x4a7fae : b.bossId === 'dragon' ? 0x241d18 : 0x4a4030, 3.2);
      // 竜は体側の亀裂を赤熱させる (黒い体表でもフェーズ変化が体から読める)
      const cm = b.rig && b.rig.group && b.rig.group.userData.crackMat;
      if (cm) { cm.color.set(0xff5a1a); b._crackHot = true; }
    }

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
          const mx = b.pos.x + Math.sin(b.yaw) * 3, mz = b.pos.z + Math.cos(b.yaw) * 3;
          G.Projectiles.spawn('fire', mx, sy, mz,
            b.pos.x + Math.sin(a) * 25, p.pos.y + 0.8, b.pos.z + Math.cos(a) * 25, 15, D.atk * 0.55);
          // 口元の火炎コーン (弾と別に炎の広がりを見せる)
          G.FX.burst(mx, sy, mz, {
            n: 5, color: 0xff8830, speed: 7, up: 0.5, gravity: 1.5,
            life: 0.55, size: 3.2, drag: 1.2,
            dirX: Math.sin(a), dirZ: Math.cos(a)
          });
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
    // フェーズ2の赤熱亀裂は明滅させ、距離があっても「熱」と読めるように
    if (b._crackHot) {
      const cm2 = b.rig.group.userData.crackMat;
      if (cm2) {
        // 完全消灯しない明滅 (低FPS撮影がオフ位相を引いても常に読める)
        const k = 0.88 + Math.sin(G.time * 6 + 1) * 0.12;
        cm2.color.setRGB(k, 0.38 * k, 0.1 * k);
      }
    }
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
        // 加算合成では明るい砂色が緑の上で発光して見える — 暗めに抑える
        G.FX.burst(H.pos.x - Math.sin(H.yaw) * 1.2, H.pos.y + 0.25, H.pos.z - Math.cos(H.yaw) * 1.2,
          { n: 3, color: 0x6e6250, speed: 1.8, life: 0.6, size: 2.4, up: 0.8, gravity: 1 });
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
      core.scale.setScalar(1.8);
      const glow = new THREE.Sprite(a.fireGlow);
      glow.scale.set(3.6, 3.6, 1);
      mesh.add(core, glow);
    } else { // rock
      mesh = new THREE.Mesh(a.rockGeo, a.rockMat);
    }
    mesh.position.set(x, y, z);
    if (type === 'arrow') mesh.lookAt(tx, ty, tz);
    scene.add(mesh);
    // 着弾点マーカー: 火弾は暗い焦土でも見える発光リング、岩弾はブロブ影
    let shadow = null;
    if (type === 'fire') {
      const a2 = assets();
      if (!a2.fireRingGeo) {
        a2.fireRingGeo = new THREE.RingGeometry(0.6, 0.85, 18);
        a2.fireRingGeo.rotateX(-Math.PI / 2);
      }
      shadow = new THREE.Mesh(a2.fireRingGeo, new THREE.MeshBasicMaterial({
        color: 0xff7020, transparent: true, opacity: 0.5,
        blending: THREE.AdditiveBlending, depthWrite: false
      }));
      scene.add(shadow);
    } else if (type === 'rock') {
      shadow = G.makeShadow(1.7);
      scene.add(shadow);
    }
    list.push({
      type, mesh, dmg, shadow,
      pos: new THREE.Vector3(x, y, z),
      vel: dir.multiplyScalar(speed),
      life: 0, maxLife: type === 'fire' ? 2.2 : 4,
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
        G.FX.burst(pr.pos.x, pr.pos.y, pr.pos.z, { n: 1, color: 0xff8833, speed: 0.5, life: 0.6, size: 3.6, gravity: -2, drag: 0.6 });
      }
      let dead = false;
      // 地形
      const gh = G.World.heightAt(pr.pos.x, pr.pos.z);
      if (pr.shadow) {
        pr.shadow.position.set(pr.pos.x, gh + 0.08, pr.pos.z);
        // 高度が下がるほど濃く (着弾タイミングの手掛かり)
        pr.shadow.material.opacity = G.clamp(1 - (pr.pos.y - gh) * 0.06, 0.35, 0.9);
      }
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
        if (pr.shadow) {
          scene.remove(pr.shadow);
          if (pr.type === 'fire') pr.shadow.material.dispose();
        }
        list.splice(i, 1);
      }
    }
  };

  Pr.clear = function () {
    for (const pr of list) { scene.remove(pr.mesh); if (pr.shadow) scene.remove(pr.shadow); }
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

/* ===== js/ui.js ===== */
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

  // アプリ切替・通知・メニュー遷移で pointerup が失われても、移動や攻撃を
  // 押しっぱなしにしないための単一リセット経路。
  I.reset = function () {
    joyPtr = null; camPtr = null;
    I.moveX = 0; I.moveY = 0;
    I.camDX = 0; I.camDY = 0;
    I.sprint = false; I.wheel = 0;
    I.held.jump = false; I.held.attack = false;
    pressQ.length = 0;
    for (const k in keys) keys[k] = false;
    if (typeof document !== 'undefined') {
      document.querySelectorAll('.abtn.pressed').forEach(b => b.classList.remove('pressed'));
    }
    hideJoy();
  };

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
    window.addEventListener('blur', I.reset);
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
    joyEl.style.opacity = '1';
    joyEl.style.left = (x - 64) + 'px';
    joyEl.style.top = (y - 64) + 'px';
  }
  function moveJoyThumb(dx, dy) {
    // 見た目のノブは外輪の内側に収める (入力値のクランプ半径より小さく)
    if (thumbEl) thumbEl.style.transform = `translate(${dx * 0.68}px, ${dy * 0.68}px)`;
  }
  function hideJoy() {
    if (joyEl) {
      if (G.isTouch) {
        // タッチ端末では左下に淡いゴーストを常駐 (移動操作領域のアフォーダンス)
        joyEl.style.display = 'block';
        joyEl.style.opacity = '0.28';
        joyEl.style.left = '36px';
        joyEl.style.top = (window.innerHeight - 170) + 'px';
      } else {
        joyEl.style.display = 'none';
      }
    }
    if (thumbEl) thumbEl.style.transform = 'translate(0,0)';
  }
  I.bindJoyEls = (j, t) => { joyEl = j; thumbEl = t; hideJoy(); };
})();

/* ======================= UI 本体 ======================= */
(function () {
  const UI = G.UI = {};
  let root;
  let installPrompt = null;

  function el(tag, cls, parent, html) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html !== undefined) e.innerHTML = html;
    (parent || root).appendChild(e);
    return e;
  }
  UI.el = el;

  function button(cls, parent, html, label) {
    const b = el('button', cls, parent, html);
    b.type = 'button';
    if (label) b.setAttribute('aria-label', label);
    return b;
  }

  /* タッチボタン生成 */
  function actionBtn(cls, label, action, opts) {
    opts = opts || {};
    const labels = {
      attack: '攻撃。長押しで強攻撃、さらに長押しで回転斬り',
      roll: '回避', jump: 'ジャンプ。空中で長押しして滑空',
      lock: '敵を注視', potion: '回復薬を使う', menu: 'メニュー', map: '地図'
    };
    const b = button('abtn ' + cls, hudEl, label, labels[action] || action);
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
    // スイッチコントロールや外付けキーボードの click でも基本操作を実行。
    b.addEventListener('click', e => {
      if (e.detail === 0) G.Input.push(action);
    });
    return b;
  }

  /* ---------- 生成 ---------- */
  let hudEl, hpBar, hpFill, hpChip, staFill, xpFill, lvlEl, goldEl, clockEl, weatherEl;
  let hpChipW = 100, hpChipHold = 0;
  let miniCanvas, miniCtx, mapCanvas = null;
  let bigMapCanvas = null;
  let trackerEl, toastWrap, promptEl, bossWrap, bossFill, bossName, bossChip, saveHint;
  let bossChipW = 100;
  let dlgWrap, dlgName, dlgText, dlgOpts;
  let menuWrap, menuTabs, menuBody, menuFade;
  let deathEl, endEl, titleEl, introEl;
  let dmgLayer;
  let joyBase, joyThumb;
  let potBtn;

  UI.init = function () {
    root = document.getElementById('ui');

    /* 回線断と更新を、ゲームを邪魔しない小さな状態表示で知らせる。 */
    const netState = el('div', 'netstate', root, 'オフライン — 保存済みの世界でプレイ中');
    netState.setAttribute('role', 'status');
    const updateNet = () => netState.classList.toggle('show', navigator.onLine === false);
    window.addEventListener('online', updateNet);
    window.addEventListener('offline', updateNet);
    updateNet();
    window.addEventListener('beforeinstallprompt', e => {
      e.preventDefault();
      installPrompt = e;
      if (titleEl) addInstallButton(titleEl.querySelector('.tbtns'));
    });

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
    promptEl = button('prompt', hudEl, '', '調べる');
    promptEl.style.display = 'none';
    promptEl.addEventListener('click', e => {
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

    saveHint = el('div', 'savehint', hudEl, '◆ 保存しました');
    saveHint.setAttribute('role', 'status');
    saveHint.setAttribute('aria-live', 'polite');

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
      lockBtn = actionBtn('b-lock', '◎<span class="blabel">注視</span>', 'lock');
      potBtn = actionBtn('b-potion', '薬', 'potion');
      actionBtn('b-menu', '≡', 'menu');
      actionBtn('b-map', '図', 'map');
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
    const closeB = button('mclose', mHead, '✕', 'メニューを閉じる');
    closeB.addEventListener('click', e => { e.stopPropagation(); UI.closeMenu(); });
    menuTabs = el('div', 'mtabs', menuWrap);
    menuTabs.setAttribute('role', 'tablist');
    menuBody = el('div', 'mbody', menuWrap);
    // 下端フェードはスクロールコンテナの外のオーバーレイ (sticky ::after は
    // コンテナのpadding分だけ上にずれ、最終行がフェードの下に露出していた)
    menuFade = el('div', 'mfade', menuWrap);
    menuWrap.style.display = 'none';
    const tabs = [['equip', '装備'], ['items', '持ち物'], ['map', '地図'], ['quests', '任務'], ['settings', '設定']];
    for (const [id, label] of tabs) {
      const t = button('mtab', menuTabs, label, label + 'タブ');
      t.setAttribute('role', 'tab');
      t.dataset.tab = id;
      t.setAttribute('aria-selected', 'false');
      t.addEventListener('click', e => { e.stopPropagation(); G.Audio.sfx('ui'); UI.showTab(id); });
    }

    /* 死亡画面 */
    deathEl = el('div', 'death', root, '<div class="dtext">力尽きた…</div>');
    const respawnB = button('bigbtn', deathEl, '祠から再開');
    respawnB.addEventListener('click', e => { e.stopPropagation(); G.Game.respawn(); });
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
    let saveHintTimer = 0;
    G.events.on('saved', () => {
      saveHint.classList.remove('show');
      void saveHint.offsetWidth;
      saveHint.classList.add('show');
      clearTimeout(saveHintTimer);
      saveHintTimer = setTimeout(() => saveHint.classList.remove('show'), 1500);
    });
    window.addEventListener('eldria-update-ready', UI.showUpdatePrompt);
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
      const s = G.Save.summary();
      if (s) {
        const mins = Math.floor(s.playtime / 60);
        const time = mins >= 60 ? `${Math.floor(mins / 60)}時間${mins % 60}分` : `${mins}分`;
        const progress = el('div', 'tprogress', inner,
          `<span>Lv ${s.level}</span><span>第${s.chapter}章</span><span>${time}</span>${s.recovered ? '<b>予備保存あり</b>' : ''}`);
        inner.insertBefore(progress, btns);
      }
      const c = button('bigbtn', btns, 'つづきから');
      c.addEventListener('click', e => { e.stopPropagation(); G.Audio.init(); G.Audio.sfx('uiOpen'); close(); onStart(false); });
    }
    const n = button('bigbtn' + (G.Save.exists() ? ' sub' : ''), btns, 'はじめから');
    n.addEventListener('click', e => {
      e.stopPropagation(); G.Audio.init();
      if (G.Save.exists() && !confirm('セーブデータを消して最初から始めますか?')) return;
      G.Audio.sfx('uiOpen'); close(); onStart(true);
    });
    addInstallButton(btns);
    el('div', 'tfoot', inner, G.isTouch
      ? '左: 移動 / 右: カメラ　・　Safariの共有 →「ホーム画面に追加」で全画面・オフライン対応'
      : 'WASD移動 / マウスでカメラ / クリック攻撃');
    function close() { titleEl.remove(); titleEl = null; }
  };

  function addInstallButton(parent) {
    if (!parent || parent.querySelector('.installbtn') || window.matchMedia('(display-mode: standalone)').matches || navigator.standalone) return;
    if (installPrompt) {
      const b = button('installbtn', parent, 'アプリとして追加');
      b.addEventListener('click', async e => {
        e.stopPropagation();
        const prompt = installPrompt; installPrompt = null;
        await prompt.prompt();
        b.remove();
      });
    } else if (document.documentElement.requestFullscreen) {
      const b = button('installbtn', parent, '全画面で遊ぶ');
      b.addEventListener('click', async e => {
        e.stopPropagation();
        try {
          await document.documentElement.requestFullscreen({ navigationUI: 'hide' });
          if (screen.orientation && screen.orientation.lock) await screen.orientation.lock('landscape');
        } catch (err) {}
        b.remove();
      });
    }
  }

  UI.showUpdatePrompt = function () {
    if (!root || root.querySelector('.updatebar')) return;
    const bar = el('div', 'updatebar', root);
    el('span', '', bar, '新しい冒険データを利用できます');
    const b = button('', bar, '今すぐ更新');
    b.addEventListener('click', () => location.reload());
  };

  UI.showIntro = function () {
    UI.setHudVisible(false);
    introEl = el('div', 'intro', root,
      '<div class="imist"></div><div class="imist m2"></div>' +
      '<div class="iname">E L D R I A</div>' +
      '<div class="itext">霧深き大地エルドリア。<br><br>北の頂に黒竜ヴァルドレクが目覚めしとき、<br>大地は魔物で溢れ、人々は小さな村に身を寄せた。<br><br>――旅人よ。風がお前を呼んでいる。</div>');
    const skip = button('bigbtn', introEl, '旅を始める');
    skip.addEventListener('click', e => {
      e.stopPropagation();
      introEl.remove(); introEl = null;
      UI.setHudVisible(true);
      G.Audio.sfx('uiOpen');
    });
  };

  /* ---------- HUD 更新 ---------- */
  let hudT = 0, promptT = 0, curInteract = null, lockBtn = null;
  UI.refreshHUDStatic = function () {
    goldEl.innerHTML = '<span class="gicon">G</span> ' + G.Inv.gold;
    if (potBtn) {
      const n = G.Inv.count('potion') + G.Inv.count('hipotion');
      potBtn.innerHTML = '薬<span class="pcount">' + n + '</span>';
    }
  };

  UI.update = function (dt) {
    const p = G.Player;
    // 注視ボタンのON/OFF状態を見た目に反映
    if (lockBtn) lockBtn.classList.toggle('on', !!(p.target && p.target.alive));
    // バー
    const hpPctP = 100 * p.hp / p.maxHp();
    // HPバーは残量で緑→黄→赤 (満タンでも赤いと危険状態と誤認する指摘)
    hpFill.style.background = hpPctP > 50 ? 'linear-gradient(180deg,#5fbf4a,#3e8f34)'
      : hpPctP > 25 ? 'linear-gradient(180deg,#d8b03a,#a8842a)' : 'linear-gradient(180deg,#d84a3a,#a02a22)';
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
    // アイコンは実際の降雨粒子量と同期 (状態値だけ見ると、粒子が残っている
    // のに晴れアイコンになる desync が起きる)
    const raining = G.State.weather > 0.5 || (G.Sky.rainAmt || 0) > 0.08;
    weatherEl.textContent = raining ? '☂' : (tod > 19 || tod < 5 ? '☾' : '☀');

    // ボスバー (黄色の削り残像つき)
    if (curBoss) {
      const w = 100 * Math.max(0, curBoss.hp) / curBoss.maxHp;
      bossFill.style.width = w + '%';
      // 約0.5秒で追いつく (ラグ区間が広すぎると実HPが読めない指摘)
      bossChipW += (w - bossChipW) * G.damp(5.5, dt);
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
        // 騎乗中の降車プロンプトは常時表示になるため、中央を塞がず下寄せに
        promptEl.classList.toggle('low', curInteract.kind === 'dismount');
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
      // 洞窟内は岩盤(暗)の上に歩行可能な床(明)を描き、空間の形が読めるように。
      // 床と岩盤の明度差は大きく取り、縁線で輪郭を立てる (110px円では
      // 微差だと一様な暗色ディスクにしか見えない)
      ctx.fillStyle = '#10131d';
      ctx.fillRect(0, 0, S, S);
      const C = G.World.CAVE;
      const fx = (C.cx - p.pos.x) / view * S + S / 2;
      const fz = (C.cz - p.pos.z) / view * S + S / 2;
      const fr = 46 / view * S;
      ctx.fillStyle = '#67759f';
      ctx.beginPath(); ctx.arc(fx, fz, fr, 0, Math.PI * 2); ctx.fill();
      // 入口通路 (北側の縁から主洞へ)
      const wpx = Math.max(4, 14 / view * S);
      const ez = (C.z0 - 18 - p.pos.z) / view * S + S / 2;
      ctx.fillRect(fx - wpx / 2, Math.min(ez, fz), wpx, Math.abs(fz - ez));
      ctx.strokeStyle = '#dce6fa'; ctx.lineWidth = 2;
      ctx.beginPath(); ctx.arc(fx, fz, fr, 0, Math.PI * 2); ctx.stroke();
    } else {
      const scale = (256 / (MAP_R * 2));
      const sw = view * scale;
      const [mx, mz] = worldToMap(p.pos.x, p.pos.z, 256);
      ctx.drawImage(mapCanvas, mx - sw / 2, mz - sw / 2, sw, sw, 0, 0, S, S);
      // 夜間は減光 (昼の明るい緑のままだと夜のトーンから浮く)
      const night = G.clamp((0.42 - (G.Sky.lightLevel || 1)) * 2.2, 0, 0.55);
      if (night > 0.02) {
        ctx.fillStyle = `rgba(10, 16, 32, ${night})`;
        ctx.fillRect(0, 0, S, S);
      }
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
      // 非交戦の敵は近距離のみ表示 (村の周囲が赤ドットで埋まる過密の抑制)
      if (!e.aggro && G.dist2(e.pos.x, e.pos.z, p.pos.x, p.pos.z) > 85 * 85) return;
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
        if (G.dmgLog) console.log('[dmg] merge +' + n + ' -> ' + ex.val);
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
    if (G.dmgLog) console.log('[dmg] spawn ' + n + (opts.crit ? ' crit' : ''));
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
      if (d.t > 1.25) { d.active = false; d.eln.style.display = 'none'; continue; }
      // 上昇は合算でリセットされない専用タイマーで (数字が下に跳ねない)
      const riseT = (now - (d.riseBorn || d.born)) / 1000;
      const pr = UI.project(d.x, d.y + Math.min(riseT, 1.2) * 1.2, d.z);
      if (!pr.visible) { d.eln.style.display = 'none'; continue; }
      d.eln.style.display = 'block';
      d.eln.style.left = pr.x + 'px';
      d.eln.style.top = pr.y + 'px';
      d.eln.style.opacity = d.t > 0.95 ? String(1 - (d.t - 0.95) / 0.3) : '1';
    }
  }

  /* ---------- 敵HPバー ---------- */
  const ebarPool = [];
  function updateEnemyBars(dt) {
    let used = 0;
    const p = G.Player;
    const placedBars = [];
    // ロック対象を最優先 (常に頭上固定)、次いで近距離順。
    // 重なり回避のずらしは最大2段までとし、それ以上は描かない
    // (ずらし続けると所有者から離れた「浮いたバー」になる)
    const ents = [];
    for (const e of G.Enemies.list) {
      if (!e.alive || !e.aggro) continue;
      const d2 = G.dist2(p.pos.x, p.pos.z, e.pos.x, e.pos.z);
      if (d2 > 40 * 40) continue;
      ents.push({ e, d2, locked: p.target === e });
    }
    ents.sort((a, b) => (b.locked ? 1 : 0) - (a.locked ? 1 : 0) || a.d2 - b.d2);
    for (const { e, locked } of ents) {
      const pr = UI.project(e.pos.x, e.pos.y + (e.T.barH || 1.9), e.pos.z);
      if (!pr.visible) continue;
      // 左上のHUD (HP/スタミナ/所持金) 領域には重ねない
      if (pr.y < 92 && pr.x < 360) continue;
      if (!locked) {
        let ok = false;
        for (let step = 0; step < 3 && !ok; step++) {
          const y = pr.y - step * 11;
          let hit = false;
          for (let k = 0; k < placedBars.length; k++) {
            const q = placedBars[k];
            if (Math.abs(pr.x - q.x) < 58 && Math.abs(y - q.y) < 10) { hit = true; break; }
          }
          if (!hit) { pr.y = y; ok = true; }
        }
        if (!ok) continue;
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
      // 先頭クエストは名前だけでなく「今やること」(desc) を添えて目標を明示
      const sub = (i === 0 && l.desc) ? `<div class="tgoal">${l.desc}</div>` : '';
      return `<div class="tline ${l.main ? 'main' : ''} ${l.ready ? 'ready' : ''}">${l.line}${dist}${sub}</div>`;
    }).join('');
  };
  function updateTrackerDist(dt) {
    // 毎フレーム更新 (dist計算1回は安価。スロットルすると低fps環境で
    // テレポート後も数秒古い距離が残る)
    if (!trackerMark) return;
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
    G.Input.reset();
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
          const b = button('dlgopt', dlgOpts, op.label);
          b.addEventListener('click', ev => {
            ev.stopPropagation();
            G.Audio.sfx('ui');
            if (op.closeText) {
              if (op.action) op.action();
              dlgOpts.innerHTML = '';
              typeText(op.closeText, () => {
                const c = button('dlgopt', dlgOpts, '（会話を終える）');
                c.addEventListener('click', e2 => { e2.stopPropagation(); UI.closeDialogue(); });
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
    G.Input.reset();
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
    G.Input.reset();
    G.paused = true;
    dlgWrap.style.display = 'block';
    dlgName.textContent = shrine.name;
    dlgText.textContent = '祠の温かな光が体を包む。どうする?';
    dlgOpts.innerHTML = '';
    const mk = (label, fn) => {
      const b = button('dlgopt', dlgOpts, label);
      b.addEventListener('click', e => { e.stopPropagation(); G.Audio.sfx('ui'); fn(); });
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
    G.Input.reset();
    menuOpen = true;
    G.paused = true;
    hudEl.style.visibility = 'hidden';
    menuTabs.style.display = '';
    menuWrap.style.display = 'flex';
    G.Audio.sfx('uiOpen');
    UI.showTab(tab || 'equip');
  };
  UI.closeMenu = function () {
    G.Input.reset();
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
    for (const t of menuTabs.children) {
      const selected = t.dataset.tab === tab;
      t.classList.toggle('on', selected);
      t.setAttribute('aria-selected', String(selected));
    }
    menuBody.innerHTML = '';
    if (tab === 'equip') renderEquip();
    else if (tab === 'items') renderItems();
    else if (tab === 'map') renderMap();
    else if (tab === 'quests') renderQuests();
    else if (tab === 'settings') renderSettings();
    updateScrollHint();
  };
  /* 下端フェードはスクロール余地がある時だけ (2件しかない装備画面で
     最終カードが減光され「偽のスクロール示唆」になる指摘) */
  function updateScrollHint() {
    requestAnimationFrame(() => {
      const can = menuBody.scrollHeight > menuBody.clientHeight + 4;
      if (menuFade) menuFade.classList.toggle('on', can);
    });
  }

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
        const b = button('ibtn', row, '装備');
        b.addEventListener('click', e => { e.stopPropagation(); G.Inv.equipItem(id); });
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
    potion: ['🧪', '#7a2e3e'], hipotion: ['💊', '#8e2438'], herb: ['🌿', '#2e5a38'],
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
      detail.innerHTML = `<div class="itext"><div class="iname">${it.name} ×${G.Inv.count(id)}</div><div class="idesc">${it.desc}</div></div>`;
      if (it.type === 'consumable') {
        const b = button('ibtn', detail, '使う');
        b.addEventListener('click', e => {
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
      const tile = button('itile', grid, '', it.name + 'を選択');
      tile.style.background = tint;
      tile.innerHTML = `<div class="iglyph">${glyph}</div><div class="icount">×${G.Inv.count(id)}</div><div class="itname">${it.name}</div>`;
      tile.addEventListener('click', e => { e.stopPropagation(); G.Audio.sfx('ui'); select(id, it, tile); });
      if (!first) first = [id, it, tile];
    }
    // 空きスロットのプレースホルダー (所持枠のグリッド構造を可視化)
    for (let i = ids.length; i < 12; i++) el('div', 'itile empty', grid);
    if (first) select(first[0], first[1], first[2]);
  }

  function renderMap() {
    const wrap = el('div', 'mapwrap', menuBody);
    if (!bigMapCanvas) {
      bigMapCanvas = document.createElement('canvas');
      bigMapCanvas.width = bigMapCanvas.height = 512;
    }
    wrap.appendChild(bigMapCanvas);
    bigMapCanvas.setAttribute('role', 'button');
    bigMapCanvas.setAttribute('aria-label', 'エルドリア全体地図。灯した祠をタップして移動');
    drawBigMap();
    // 凡例は横に並べて地図を大きく取る
    el('div', 'maplegend', wrap,
      '<div><span style="color:#ffd35a">◆</span> 任務</div><div><span style="color:#6fe3ff">●</span> 祠(灯)<br><span class="mlsub">タップで<br>ファストトラベル</span></div><div><span style="color:#c8d4e6">○</span> 祠(未灯)</div><div>▲ 現在地</div>');
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
    // 祠 (未灯は場所だけ淡く示す — 凡例に●があるのに1つも出ない状態を避ける)
    for (const s of G.World.shrines) {
      const [x, z] = worldToMap(s.x, s.z, 512);
      if (!G.State.shrines[s.id]) {
        // 未灯: 凡例の「○」と同じ白抜き円に暗色縁 (凡例と実マーカーの一致)
        ctx.fillStyle = 'rgba(235,242,250,0.55)';
        ctx.beginPath(); ctx.arc(x, z, 6, 0, Math.PI * 2); ctx.fill();
        ctx.strokeStyle = 'rgba(25,35,55,0.9)'; ctx.lineWidth = 2;
        ctx.stroke();
        continue;
      }
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
    // 統計もクエストカードと同じカード造形で (帯が途切れた未完成パネルに見える指摘)
    el('div', 'shophead', menuBody, '― 記録 ―');
    const srow = el('div', 'qrow', el('div', 'qlist', menuBody));
    srow.innerHTML = `<div class="qname">討伐数 <span class="istat">${G.State.killCount || 0}</span></div>` +
      `<div class="qdesc">灯した祠 ${Object.keys(G.State.shrines || {}).length} / 開けた宝箱 ${Object.keys(G.State.openedChests || {}).length}</div>`;
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
    mkSlider('画面の揺れ', () => G.settings.shake, v => { G.settings.shake = v; G.settings.save(); });

    const mkToggle = (label, get, set) => {
      const row = el('div', 'srow', wrap);
      el('div', 'slabel', row, label);
      const b = button('toggle', row, get() ? 'オン' : 'オフ', label);
      b.setAttribute('aria-pressed', String(get()));
      b.classList.toggle('on', get());
      b.addEventListener('click', e => {
        e.stopPropagation();
        const next = !get(); set(next);
        b.textContent = next ? 'オン' : 'オフ';
        b.classList.toggle('on', next); b.setAttribute('aria-pressed', String(next));
        if (next && label === '振動') G.haptic(18);
      });
      row.appendChild(b);
    };
    mkToggle('振動', () => G.settings.haptics, v => { G.settings.haptics = v; G.settings.save(); });
    mkToggle('ダメージ数値', () => G.settings.showDmg, v => { G.settings.showDmg = v; G.settings.save(); });

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

    const perf = G.perf || { resScale: 1, detail: 1 };
    el('div', 'runtimeinfo', wrap,
      `現在: ${G.quality.toUpperCase()} / 解像度 ${Math.round((perf.resScale || 1) * 100)}% / 遠景 ${Math.round((perf.detail || 1) * 100)}% / 30fps優先`);

    const save = button('bigbtn sub', wrap, '手動セーブ');
    save.addEventListener('click', e => {
      e.stopPropagation();
      if (G.Save.save()) UI.toast('セーブした', 'gold');
    });
    const portable = el('div', 'saveactions', wrap);
    const exportB = button('bigbtn sub small', portable, 'セーブを書き出す');
    exportB.addEventListener('click', e => {
      e.stopPropagation();
      G.Save.save();
      const data = G.Save.exportData();
      if (!data) { UI.toast('書き出せるセーブがありません'); return; }
      const url = URL.createObjectURL(new Blob([data], { type: 'application/json' }));
      const a = document.createElement('a');
      a.href = url; a.download = `eldria-save-${new Date().toISOString().slice(0, 10)}.json`;
      a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
      UI.toast('セーブを書き出しました', 'gold');
    });
    const importB = button('bigbtn sub small', portable, 'セーブを読み込む');
    const file = document.createElement('input');
    file.type = 'file'; file.accept = 'application/json,.json'; file.hidden = true;
    importB.addEventListener('click', e => { e.stopPropagation(); file.click(); });
    file.addEventListener('change', async () => {
      const picked = file.files && file.files[0];
      if (!picked) return;
      const ok = G.Save.importData(await picked.text());
      if (ok && confirm('セーブを読み込みました。今すぐ再起動しますか?')) location.reload();
      else if (!ok) UI.toast('ELDRIAの有効なセーブではありません');
      file.value = '';
    });
    portable.appendChild(file);
    el('div', 'dangergap', wrap);
    const reset = button('bigbtn danger small', wrap, 'データを消して最初から');
    reset.addEventListener('click', e => {
      e.stopPropagation();
      if (confirm('本当にセーブデータを削除しますか?') &&
          confirm('全ての進行が失われます。最終確認: 削除しますか?')) {
        G.Save.reset();
        location.reload();
      }
    });
    el('div', 'mnote', wrap, 'ELDRIA MOBILE MASTER 2026.08 — 完全プロシージャル・オープンワールドARPG。進行は端末内に自動保存されます。');
  }

  /* ---------- 商店 ---------- */
  UI.openShop = function () {
    G.Input.reset();
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
      row.innerHTML = `<div class="iname"><span class="rowicon">${itemIcon(id, it)[0]}</span>${it.name} <span class="istat">${it.price}G${st}</span></div><div class="idesc">${it.desc}</div>`;
      if (G.Inv.gold >= it.price) {
        const b = button('ibtn', row, '買う');
        b.addEventListener('click', e => { e.stopPropagation(); if (G.Shop.buy(id)) UI.openShop(); });
      } else {
        const off = button('ibtn off', row, 'G不足'); off.disabled = true;
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
      row.innerHTML = `<div class="iname"><span class="rowicon">${itemIcon(id, it)[0]}</span>${it.name} ×${G.Inv.count(id)} <span class="istat">${it.sell}G</span></div>`;
      const b = button('ibtn', row, '売る');
      b.addEventListener('click', e => { e.stopPropagation(); if (G.Shop.sell(id)) UI.openShop(); });
    }
    if (!any) el('div', 'mnote', sell, '売れる物がない。');
    updateScrollHint();
  };

  /* ---------- 鍛冶 ---------- */
  UI.openForge = function () {
    G.Input.reset();
    G.paused = true;
    menuOpen = true;
    hudEl.style.visibility = 'hidden';
    menuWrap.style.display = 'flex';
    menuTabs.style.display = 'none';
    menuBody.innerHTML = '';
    el('div', 'shoptitle', menuBody, '⚒ ドヴァンの鍛冶場');
    el('div', 'mnote', menuBody, `所持金: ${G.Inv.gold} G / 💠魔石×${G.Inv.count('magicstone')} 🦴骨×${G.Inv.count('bone')} 🟤毛皮×${G.Inv.count('pelt')}`);
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
          const t = `${itemIcon(m, G.Items.get(m))[0]}${G.Items.get(m).name}×${c.mats[m]}`;
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
      row.innerHTML = `<div class="iname"><span class="rowicon">${itemIcon(id, it)[0]}</span>${it.name}${lvl ? ' +' + lvl : ''} <span class="istat">${stat}</span></div>
        <div class="idesc">${lvl < 5 ? '次の強化: ' + costTxt : costTxt}</div>`;
      if (lvl < 5) {
        if (can) {
          const b = button('ibtn', row, '強化');
          b.addEventListener('click', e => {
            e.stopPropagation();
            if (G.Forge.upgrade(id)) UI.openForge();
          });
        } else {
          const off = button('ibtn off', row, '素材不足'); off.disabled = true;
        }
      }
    }
    el('div', 'mnote', menuBody, '強化は装備中の武器・防具に施される。素材は敵のドロップや売店で。');
    updateScrollHint();
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
    const b = button('bigbtn', endEl, '旅を続ける');
    b.addEventListener('click', e => {
      e.stopPropagation();
      endEl.style.display = 'none';
      G.Save.save();
    });
  };

  UI.showFatal = function (title, detail) {
    root = root || document.getElementById('ui');
    root.classList.add('fatalmode');
    const loading = document.getElementById('loading');
    if (loading) loading.style.display = 'none';
    G.Input.reset();
    G.paused = true;
    let wrap = document.querySelector('.fatal');
    if (wrap) wrap.remove();
    wrap = el('div', 'fatal', root);
    const card = el('div', 'fatalcard', wrap);
    el('div', 'fataltitle', card, title || 'ゲームを安全に停止しました');
    const body = el('div', 'fatalbody', card);
    body.textContent = detail || '進行は保存されています。再読み込みして続けてください。';
    const reload = button('bigbtn', card, '再読み込み');
    reload.addEventListener('click', () => location.reload());
  };
})();

/* ===== js/main.js ===== */
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
    trauma = Math.min(1, trauma + v * G.settings.shake);
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
