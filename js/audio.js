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
