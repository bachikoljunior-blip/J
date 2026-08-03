// ============================================================================
//  audio.js — everything you hear is synthesised at runtime.
//
//  No audio files means no download, no decode stall on a phone, and the
//  freedom to make the score respond continuously to what is happening: the
//  combat layer fades in as enemies notice you, the boss layer swaps the mode
//  from Aeolian to Phrygian, and the wind bed tracks the weather system.
// ============================================================================

const NOTE = (semitonesFromA4) => 440 * Math.pow(2, semitonesFromA4 / 12);

// Scale degrees, in semitones from the tonic.
const SCALES = {
  aeolian: [0, 2, 3, 5, 7, 8, 10],
  phrygian: [0, 1, 3, 5, 7, 8, 10],
  dorian: [0, 2, 3, 5, 7, 9, 10],
  lydian: [0, 2, 4, 6, 7, 9, 11],
  minorPent: [0, 3, 5, 7, 10],
};

export class AudioEngine {
  constructor() {
    this.ctx = null;
    this.ready = false;
    this.masterVolume = 0.8;
    this.musicVolume = 0.55;
    this.sfxVolume = 0.9;
    this.muted = false;
    this.musicMode = 'explore';
    this._pendingMode = null;
    this._noiseBuf = null;
    this._nextNoteTime = 0;
    this._step = 0;
    this._lastFootstep = 0;
    this.enabled = true;
  }

  /** Must be called from a user gesture on mobile. */
  init() {
    if (this.ctx) {
      if (this.ctx.state === 'suspended') this.ctx.resume();
      return;
    }
    const Ctx = window.AudioContext || window.webkitAudioContext;
    if (!Ctx) { this.enabled = false; return; }
    const ctx = new Ctx();
    this.ctx = ctx;

    this.master = ctx.createGain();
    this.master.gain.value = this.masterVolume;
    // A gentle limiter keeps a burst of overlapping hits from clipping.
    this.comp = ctx.createDynamicsCompressor();
    this.comp.threshold.value = -14;
    this.comp.knee.value = 12;
    this.comp.ratio.value = 6;
    this.comp.attack.value = 0.004;
    this.comp.release.value = 0.18;
    this.master.connect(this.comp);
    this.comp.connect(ctx.destination);

    this.musicBus = ctx.createGain();
    this.musicBus.gain.value = this.musicVolume;
    this.sfxBus = ctx.createGain();
    this.sfxBus.gain.value = this.sfxVolume;

    // Shared reverb: a synthesised impulse response.
    this.reverb = ctx.createConvolver();
    this.reverb.buffer = this._makeImpulse(2.6, 2.4);
    this.reverbSend = ctx.createGain();
    this.reverbSend.gain.value = 0.22;
    this.reverbSend.connect(this.reverb);
    this.reverb.connect(this.master);

    this.musicBus.connect(this.master);
    this.musicBus.connect(this.reverbSend);
    this.sfxBus.connect(this.master);
    this.sfxBus.connect(this.reverbSend);

    this._noiseBuf = this._makeNoise(2.0);
    this._startAmbient();
    this._nextNoteTime = ctx.currentTime + 0.1;
    this.ready = true;
  }

  resume() {
    if (this.ctx && this.ctx.state === 'suspended') this.ctx.resume();
  }

  setVolumes({ master, music, sfx }) {
    if (master !== undefined) this.masterVolume = master;
    if (music !== undefined) this.musicVolume = music;
    if (sfx !== undefined) this.sfxVolume = sfx;
    if (!this.ready) return;
    this.master.gain.value = this.muted ? 0 : this.masterVolume;
    this.musicBus.gain.value = this.musicVolume;
    this.sfxBus.gain.value = this.sfxVolume;
  }

  setMuted(m) {
    this.muted = m;
    if (this.ready) this.master.gain.value = m ? 0 : this.masterVolume;
  }

  // -------------------------------------------------------------------------
  //  Buffers
  // -------------------------------------------------------------------------

  _makeNoise(seconds) {
    const ctx = this.ctx;
    const len = Math.floor(ctx.sampleRate * seconds);
    const buf = ctx.createBuffer(1, len, ctx.sampleRate);
    const d = buf.getChannelData(0);
    for (let i = 0; i < len; i++) d[i] = Math.random() * 2 - 1;
    return buf;
  }

  _makeImpulse(seconds, decay) {
    const ctx = this.ctx;
    const len = Math.floor(ctx.sampleRate * seconds);
    const buf = ctx.createBuffer(2, len, ctx.sampleRate);
    for (let c = 0; c < 2; c++) {
      const d = buf.getChannelData(c);
      for (let i = 0; i < len; i++) {
        const t = i / len;
        // Slightly decorrelated channels give the tail some width.
        d[i] = (Math.random() * 2 - 1) * Math.pow(1 - t, decay) * (c ? 0.94 : 1.0);
      }
    }
    return buf;
  }

  // -------------------------------------------------------------------------
  //  Voice helpers
  // -------------------------------------------------------------------------

  _env(gain, t, attack, decay, peak = 1, sustain = 0, release = 0.05, hold = 0) {
    const g = gain.gain;
    g.cancelScheduledValues(t);
    g.setValueAtTime(0.0001, t);
    g.exponentialRampToValueAtTime(Math.max(peak, 0.0002), t + attack);
    if (sustain > 0) {
      g.exponentialRampToValueAtTime(Math.max(sustain, 0.0002), t + attack + decay);
      g.setValueAtTime(Math.max(sustain, 0.0002), t + attack + decay + hold);
      g.exponentialRampToValueAtTime(0.0001, t + attack + decay + hold + release);
    } else {
      g.exponentialRampToValueAtTime(0.0001, t + attack + decay);
    }
  }

  _noiseVoice({ t, dur, type = 'bandpass', freq = 1200, q = 1, gain = 0.3, sweepTo = null, out = null }) {
    if (!this.ready) return;
    const ctx = this.ctx;
    const src = ctx.createBufferSource();
    src.buffer = this._noiseBuf;
    src.loop = true;
    const filt = ctx.createBiquadFilter();
    filt.type = type;
    filt.frequency.setValueAtTime(freq, t);
    filt.Q.value = q;
    if (sweepTo) filt.frequency.exponentialRampToValueAtTime(Math.max(sweepTo, 20), t + dur);
    const g = ctx.createGain();
    this._env(g, t, Math.min(0.012, dur * 0.2), dur, gain);
    src.connect(filt); filt.connect(g); g.connect(out || this.sfxBus);
    src.start(t);
    src.stop(t + dur + 0.05);
  }

  _toneVoice({ t, dur, freq, type = 'sine', gain = 0.2, detune = 0, glideTo = null, out = null, attack = 0.004 }) {
    if (!this.ready) return;
    const ctx = this.ctx;
    const osc = ctx.createOscillator();
    osc.type = type;
    osc.frequency.setValueAtTime(freq, t);
    osc.detune.value = detune;
    if (glideTo) osc.frequency.exponentialRampToValueAtTime(Math.max(glideTo, 20), t + dur);
    const g = ctx.createGain();
    this._env(g, t, attack, dur, gain);
    osc.connect(g); g.connect(out || this.sfxBus);
    osc.start(t);
    osc.stop(t + dur + 0.05);
    return osc;
  }

  /** FM voice — used for metallic and bell-like sounds. */
  _fmVoice({ t, dur, carrier, ratio = 2.7, index = 400, gain = 0.2, out = null }) {
    if (!this.ready) return;
    const ctx = this.ctx;
    const mod = ctx.createOscillator();
    const modGain = ctx.createGain();
    const car = ctx.createOscillator();
    const g = ctx.createGain();
    mod.frequency.value = carrier * ratio;
    modGain.gain.setValueAtTime(index, t);
    modGain.gain.exponentialRampToValueAtTime(1, t + dur * 0.8);
    car.frequency.value = carrier;
    mod.connect(modGain); modGain.connect(car.frequency);
    car.connect(g); g.connect(out || this.sfxBus);
    this._env(g, t, 0.003, dur, gain);
    mod.start(t); car.start(t);
    mod.stop(t + dur + 0.05); car.stop(t + dur + 0.05);
  }

  // -------------------------------------------------------------------------
  //  Ambient bed
  // -------------------------------------------------------------------------

  _startAmbient() {
    const ctx = this.ctx;
    // Wind: looping noise through a slowly modulated bandpass.
    const src = ctx.createBufferSource();
    src.buffer = this._makeNoise(4);
    src.loop = true;
    const filt = ctx.createBiquadFilter();
    filt.type = 'bandpass';
    filt.frequency.value = 420;
    filt.Q.value = 0.7;
    const lfo = ctx.createOscillator();
    const lfoGain = ctx.createGain();
    lfo.frequency.value = 0.07;
    lfoGain.gain.value = 240;
    lfo.connect(lfoGain); lfoGain.connect(filt.frequency);
    const g = ctx.createGain();
    g.gain.value = 0.045;
    src.connect(filt); filt.connect(g); g.connect(this.master);
    src.start();
    lfo.start();
    this.windGain = g;
    this.windFilter = filt;

    // Rain: a second noise bed, silent until the weather asks for it.
    const rsrc = ctx.createBufferSource();
    rsrc.buffer = this._makeNoise(4);
    rsrc.loop = true;
    const rfilt = ctx.createBiquadFilter();
    rfilt.type = 'highpass';
    rfilt.frequency.value = 900;
    const rg = ctx.createGain();
    rg.gain.value = 0;
    rsrc.connect(rfilt); rfilt.connect(rg); rg.connect(this.master);
    rsrc.start();
    this.rainGain = rg;
  }

  updateAmbient(dt, { windStrength = 0.4, rain = 0, night = 0, indoors = 0 }) {
    if (!this.ready) return;
    const t = this.ctx.currentTime;
    const wind = 0.030 + windStrength * 0.075;
    this.windGain.gain.setTargetAtTime(wind * (1 - indoors * 0.6), t, 0.8);
    this.windFilter.frequency.setTargetAtTime(360 + windStrength * 520, t, 1.2);
    this.rainGain.gain.setTargetAtTime(rain * 0.075, t, 0.9);

    // Occasional bird / insect calls, keyed to the time of day.
    this._critterTimer = (this._critterTimer || 0) - dt;
    if (this._critterTimer <= 0) {
      this._critterTimer = 3 + Math.random() * 7;
      if (rain < 0.3 && Math.random() < 0.55) {
        if (night > 0.5) this._cricket();
        else this._birdCall();
      }
    }
  }

  _birdCall() {
    const t = this.ctx.currentTime;
    const base = 1800 + Math.random() * 1400;
    const n = 2 + Math.floor(Math.random() * 3);
    for (let i = 0; i < n; i++) {
      this._toneVoice({
        t: t + i * 0.09, dur: 0.07,
        freq: base * (1 + i * 0.12), glideTo: base * (1.2 + i * 0.1),
        type: 'sine', gain: 0.020,
      });
    }
  }

  _cricket() {
    const t = this.ctx.currentTime;
    for (let i = 0; i < 5; i++) {
      this._noiseVoice({
        t: t + i * 0.055, dur: 0.02,
        type: 'bandpass', freq: 4600, q: 22, gain: 0.020,
      });
    }
  }

  // -------------------------------------------------------------------------
  //  Adaptive music
  // -------------------------------------------------------------------------

  setMusicMode(mode) {
    if (this.musicMode === mode) return;
    this.musicMode = mode;
    this._step = 0;
  }

  /** Called every frame; schedules notes a short way ahead of the clock. */
  updateMusic(dt) {
    if (!this.ready || this.musicVolume <= 0.001) return;
    const ctx = this.ctx;
    const lookahead = 0.35;
    const mode = this.musicMode;

    const cfg = MUSIC_MODES[mode] || MUSIC_MODES.explore;
    const stepDur = 60 / cfg.bpm / cfg.subdiv;

    while (this._nextNoteTime < ctx.currentTime + lookahead) {
      this._scheduleStep(this._nextNoteTime, this._step, cfg);
      this._nextNoteTime += stepDur;
      this._step++;
    }
  }

  _scheduleStep(t, step, cfg) {
    const scale = SCALES[cfg.scale] || SCALES.aeolian;
    const bar = Math.floor(step / (cfg.subdiv * 4));
    const beat = step % (cfg.subdiv * 4);
    const root = cfg.root;

    // --- pad: one long chord per bar -------------------------------------
    if (beat === 0) {
      const degree = cfg.progression[bar % cfg.progression.length];
      this._lastDegree = degree;
      const chord = [0, 2, 4].map((i) => scale[(degree + i) % scale.length] + (degree + i >= scale.length ? 12 : 0));
      const barDur = (60 / cfg.bpm) * 4;
      for (let i = 0; i < chord.length; i++) {
        const f = NOTE(root + chord[i]);
        this._toneVoice({
          t, dur: barDur * 0.98, freq: f, type: cfg.padWave,
          gain: cfg.padGain * (i === 0 ? 1 : 0.68), detune: (i - 1) * 6,
          attack: barDur * 0.22, out: this.musicBus,
        });
      }
      // Bass
      this._toneVoice({
        t, dur: barDur * 0.7, freq: NOTE(root + scale[degree] - 24),
        type: 'triangle', gain: cfg.bassGain, attack: 0.02, out: this.musicBus,
      });
    }

    // --- melody / arpeggio -------------------------------------------------
    if (cfg.melody && cfg.melodyPattern[step % cfg.melodyPattern.length]) {
      const degree = this._lastDegree || 0;
      const idx = (degree + (step * 3) % scale.length) % scale.length;
      const oct = ((step >> 2) % 2) * 12;
      this._toneVoice({
        t, dur: cfg.melodyDur, freq: NOTE(root + scale[idx] + 12 + oct),
        type: cfg.melodyWave, gain: cfg.melodyGain, attack: 0.01, out: this.musicBus,
      });
    }

    // --- percussion --------------------------------------------------------
    if (cfg.drums) {
      const p = cfg.drumPattern;
      const hit = p[step % p.length];
      if (hit === 1) this._kick(t, cfg.drumGain);
      else if (hit === 2) this._taiko(t, cfg.drumGain * 0.9);
      else if (hit === 3) this._shaker(t, cfg.drumGain * 0.5);
    }

    // --- choir stabs on boss phase ----------------------------------------
    if (cfg.choir && step % (cfg.subdiv * 8) === 0) {
      const degree = this._lastDegree || 0;
      for (const o of [0, 7, 12]) {
        this._toneVoice({
          t, dur: 2.4, freq: NOTE(root + scale[degree] + o),
          type: 'sawtooth', gain: 0.035, attack: 0.5, out: this.musicBus,
        });
      }
    }
  }

  _kick(t, gain = 0.4) {
    const ctx = this.ctx;
    const osc = ctx.createOscillator();
    const g = ctx.createGain();
    osc.frequency.setValueAtTime(120, t);
    osc.frequency.exponentialRampToValueAtTime(38, t + 0.12);
    this._env(g, t, 0.002, 0.22, gain);
    osc.connect(g); g.connect(this.musicBus);
    osc.start(t); osc.stop(t + 0.3);
  }

  _taiko(t, gain = 0.35) {
    this._noiseVoice({ t, dur: 0.20, type: 'lowpass', freq: 380, q: 1.2, gain: gain * 0.8, out: this.musicBus });
    const ctx = this.ctx;
    const osc = ctx.createOscillator();
    const g = ctx.createGain();
    osc.frequency.setValueAtTime(180, t);
    osc.frequency.exponentialRampToValueAtTime(70, t + 0.16);
    this._env(g, t, 0.002, 0.24, gain);
    osc.connect(g); g.connect(this.musicBus);
    osc.start(t); osc.stop(t + 0.3);
  }

  _shaker(t, gain = 0.2) {
    this._noiseVoice({ t, dur: 0.05, type: 'highpass', freq: 6200, gain, out: this.musicBus });
  }

  // -------------------------------------------------------------------------
  //  SFX
  // -------------------------------------------------------------------------

  playSwing(weight = 1) {
    if (!this.ready) return;
    const t = this.ctx.currentTime;
    this._noiseVoice({
      t, dur: 0.18 + weight * 0.10, type: 'bandpass',
      freq: 900 / weight, sweepTo: 260 / weight, q: 1.4, gain: 0.18,
    });
    this._toneVoice({ t, dur: 0.12, freq: 220 / weight, glideTo: 90, type: 'sine', gain: 0.06 });
  }

  playHitFlesh(power = 1) {
    if (!this.ready) return;
    const t = this.ctx.currentTime;
    this._noiseVoice({ t, dur: 0.10, type: 'lowpass', freq: 620, gain: 0.30 * power });
    this._toneVoice({ t, dur: 0.13, freq: 130, glideTo: 52, type: 'sine', gain: 0.22 * power });
  }

  playHitMetal(power = 1) {
    if (!this.ready) return;
    const t = this.ctx.currentTime;
    this._fmVoice({ t, dur: 0.28, carrier: 780, ratio: 3.9, index: 1400, gain: 0.16 * power });
    this._noiseVoice({ t, dur: 0.09, type: 'highpass', freq: 3200, gain: 0.16 * power });
  }

  playBlock() {
    if (!this.ready) return;
    const t = this.ctx.currentTime;
    this._fmVoice({ t, dur: 0.20, carrier: 300, ratio: 2.1, index: 700, gain: 0.20 });
    this._noiseVoice({ t, dur: 0.10, type: 'bandpass', freq: 1400, q: 2, gain: 0.16 });
  }

  playParry() {
    if (!this.ready) return;
    const t = this.ctx.currentTime;
    this._fmVoice({ t, dur: 0.55, carrier: 1180, ratio: 4.7, index: 2400, gain: 0.22 });
    this._toneVoice({ t: t + 0.02, dur: 0.4, freq: 2360, type: 'sine', gain: 0.10 });
  }

  playCritical() {
    if (!this.ready) return;
    const t = this.ctx.currentTime;
    this._noiseVoice({ t, dur: 0.25, type: 'lowpass', freq: 800, sweepTo: 200, gain: 0.36 });
    this._toneVoice({ t, dur: 0.5, freq: 90, glideTo: 40, type: 'sawtooth', gain: 0.20 });
    this._fmVoice({ t: t + 0.03, dur: 0.4, carrier: 520, ratio: 1.4, index: 900, gain: 0.16 });
  }

  playGuardBreak() {
    if (!this.ready) return;
    const t = this.ctx.currentTime;
    this._fmVoice({ t, dur: 0.7, carrier: 180, ratio: 3.1, index: 1600, gain: 0.26 });
  }

  playFootstep(surface = 'grass', speed = 1) {
    if (!this.ready) return;
    const now = this.ctx.currentTime;
    if (now - this._lastFootstep < 0.08) return;
    this._lastFootstep = now;
    const presets = {
      grass: { freq: 2400, q: 0.8, gain: 0.055, dur: 0.07, type: 'highpass' },
      dirt: { freq: 900, q: 1.0, gain: 0.070, dur: 0.08, type: 'bandpass' },
      stone: { freq: 1600, q: 2.2, gain: 0.080, dur: 0.07, type: 'bandpass' },
      water: { freq: 1200, q: 0.6, gain: 0.090, dur: 0.16, type: 'lowpass' },
      snow: { freq: 3400, q: 0.7, gain: 0.050, dur: 0.09, type: 'highpass' },
      sand: { freq: 1800, q: 0.5, gain: 0.055, dur: 0.10, type: 'bandpass' },
    };
    const p = presets[surface] || presets.grass;
    this._noiseVoice({
      t: now, dur: p.dur, type: p.type, freq: p.freq, q: p.q,
      gain: p.gain * (0.7 + speed * 0.4),
    });
  }

  playRoll() {
    if (!this.ready) return;
    const t = this.ctx.currentTime;
    this._noiseVoice({ t, dur: 0.32, type: 'lowpass', freq: 1400, sweepTo: 350, gain: 0.14 });
  }

  playLand(speed) {
    if (!this.ready || speed < 3) return;
    const t = this.ctx.currentTime;
    const p = Math.min(1, speed / 18);
    this._noiseVoice({ t, dur: 0.14, type: 'lowpass', freq: 500, gain: 0.10 + p * 0.25 });
    this._toneVoice({ t, dur: 0.18, freq: 90, glideTo: 44, type: 'sine', gain: 0.08 + p * 0.2 });
  }

  playBow() {
    if (!this.ready) return;
    const t = this.ctx.currentTime;
    this._toneVoice({ t, dur: 0.20, freq: 260, glideTo: 130, type: 'triangle', gain: 0.14 });
    this._noiseVoice({ t, dur: 0.12, type: 'bandpass', freq: 2600, q: 3, gain: 0.10 });
  }

  playSpell(kind) {
    if (!this.ready) return;
    const t = this.ctx.currentTime;
    if (kind === 'fire') {
      this._noiseVoice({ t, dur: 0.45, type: 'lowpass', freq: 2400, sweepTo: 500, gain: 0.20 });
      this._toneVoice({ t, dur: 0.3, freq: 140, glideTo: 70, type: 'sawtooth', gain: 0.08 });
    } else if (kind === 'heal') {
      for (let i = 0; i < 3; i++) {
        this._toneVoice({ t: t + i * 0.07, dur: 0.55, freq: NOTE(4 + i * 5), type: 'sine', gain: 0.09 });
      }
    } else if (kind === 'buff') {
      this._toneVoice({ t, dur: 0.7, freq: 220, glideTo: 440, type: 'triangle', gain: 0.10 });
    } else if (kind === 'frost') {
      this._noiseVoice({ t, dur: 0.6, type: 'highpass', freq: 2200, sweepTo: 5200, gain: 0.16 });
    } else if (kind === 'pyre') {
      this._toneVoice({ t, dur: 0.6, freq: 70, glideTo: 34, type: 'sawtooth', gain: 0.16 });
      this._noiseVoice({ t, dur: 0.7, type: 'lowpass', freq: 1600, sweepTo: 300, gain: 0.22 });
    } else {
      this._fmVoice({ t, dur: 0.4, carrier: 620, ratio: 1.9, index: 900, gain: 0.13 });
    }
  }

  playBreath() {
    if (!this.ready) return;
    const t = this.ctx.currentTime;
    this._noiseVoice({ t, dur: 1.2, type: 'lowpass', freq: 3000, sweepTo: 700, gain: 0.24 });
  }

  playDrink() {
    if (!this.ready) return;
    const t = this.ctx.currentTime;
    for (let i = 0; i < 3; i++) {
      this._toneVoice({ t: t + i * 0.11, dur: 0.09, freq: 210 + i * 40, glideTo: 130, type: 'sine', gain: 0.10 });
    }
  }

  playUseItem() {
    if (!this.ready) return;
    const t = this.ctx.currentTime;
    this._noiseVoice({ t, dur: 0.10, type: 'bandpass', freq: 2000, q: 2, gain: 0.10 });
  }

  playUI(kind = 'click') {
    if (!this.ready) return;
    const t = this.ctx.currentTime;
    if (kind === 'click') this._toneVoice({ t, dur: 0.05, freq: 900, type: 'square', gain: 0.045 });
    else if (kind === 'confirm') {
      this._toneVoice({ t, dur: 0.09, freq: 660, type: 'triangle', gain: 0.07 });
      this._toneVoice({ t: t + 0.06, dur: 0.14, freq: 990, type: 'triangle', gain: 0.07 });
    } else if (kind === 'cancel') this._toneVoice({ t, dur: 0.11, freq: 330, glideTo: 220, type: 'triangle', gain: 0.07 });
    else if (kind === 'error') this._toneVoice({ t, dur: 0.16, freq: 180, type: 'square', gain: 0.06 });
  }

  playGrace() {
    if (!this.ready) return;
    const t = this.ctx.currentTime;
    const notes = [0, 4, 7, 11, 14];
    notes.forEach((n, i) => {
      this._toneVoice({ t: t + i * 0.13, dur: 1.6, freq: NOTE(-8 + n), type: 'sine', gain: 0.085, attack: 0.02 });
    });
  }

  playLevelUp() {
    if (!this.ready) return;
    const t = this.ctx.currentTime;
    [0, 3, 7, 12, 15].forEach((n, i) => {
      this._toneVoice({ t: t + i * 0.075, dur: 0.9, freq: NOTE(-4 + n), type: 'triangle', gain: 0.09 });
    });
  }

  playDiscovery() {
    if (!this.ready) return;
    const t = this.ctx.currentTime;
    [0, 5, 9].forEach((n, i) => {
      this._toneVoice({ t: t + i * 0.10, dur: 1.4, freq: NOTE(2 + n), type: 'sine', gain: 0.08, attack: 0.05 });
    });
  }

  playDeath() {
    if (!this.ready) return;
    const t = this.ctx.currentTime;
    this._toneVoice({ t, dur: 2.6, freq: 160, glideTo: 42, type: 'sawtooth', gain: 0.14, attack: 0.05 });
    this._noiseVoice({ t, dur: 2.2, type: 'lowpass', freq: 900, sweepTo: 140, gain: 0.12 });
  }

  playBossHorn() {
    if (!this.ready) return;
    const t = this.ctx.currentTime;
    [0, 7].forEach((n, i) => {
      this._toneVoice({ t: t + i * 0.02, dur: 2.2, freq: NOTE(-16 + n), type: 'sawtooth', gain: 0.11, attack: 0.25 });
    });
    this._taiko(t + 0.1, 0.5);
    this._taiko(t + 0.55, 0.4);
  }

  playVictory() {
    if (!this.ready) return;
    const t = this.ctx.currentTime;
    [0, 4, 7, 12].forEach((n, i) => {
      this._toneVoice({ t: t + i * 0.16, dur: 2.4, freq: NOTE(-5 + n), type: 'triangle', gain: 0.10, attack: 0.08 });
    });
  }

  playPickup() {
    if (!this.ready) return;
    const t = this.ctx.currentTime;
    this._toneVoice({ t, dur: 0.12, freq: 880, type: 'sine', gain: 0.07 });
    this._toneVoice({ t: t + 0.07, dur: 0.20, freq: 1320, type: 'sine', gain: 0.06 });
  }
}

// ---------------------------------------------------------------------------
//  Music mode definitions
// ---------------------------------------------------------------------------

const MUSIC_MODES = {
  silent: {
    bpm: 60, subdiv: 2, scale: 'aeolian', root: -21,
    progression: [0], padWave: 'sine', padGain: 0.0, bassGain: 0,
    melody: false, drums: false, melodyPattern: [0], melodyDur: 0.4,
    melodyWave: 'sine', melodyGain: 0, drumPattern: [0], drumGain: 0,
  },
  explore: {
    bpm: 52, subdiv: 2, scale: 'aeolian', root: -21,
    progression: [0, 5, 3, 4],
    padWave: 'sine', padGain: 0.055, bassGain: 0.05,
    melody: true, melodyPattern: [1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    melodyDur: 1.1, melodyWave: 'sine', melodyGain: 0.030,
    drums: false, drumPattern: [0], drumGain: 0, choir: false,
  },
  tension: {
    bpm: 64, subdiv: 2, scale: 'aeolian', root: -21,
    progression: [0, 0, 5, 4],
    padWave: 'triangle', padGain: 0.055, bassGain: 0.07,
    melody: true, melodyPattern: [1, 0, 0, 1, 0, 0, 1, 0],
    melodyDur: 0.5, melodyWave: 'triangle', melodyGain: 0.028,
    drums: true, drumPattern: [1, 0, 3, 0, 2, 0, 3, 0], drumGain: 0.13, choir: false,
  },
  combat: {
    bpm: 96, subdiv: 2, scale: 'phrygian', root: -21,
    progression: [0, 0, 6, 5],
    padWave: 'sawtooth', padGain: 0.030, bassGain: 0.085,
    melody: true, melodyPattern: [1, 0, 1, 1, 0, 1, 1, 0],
    melodyDur: 0.24, melodyWave: 'triangle', melodyGain: 0.032,
    drums: true, drumPattern: [1, 3, 2, 3, 1, 3, 2, 2], drumGain: 0.20, choir: false,
  },
  boss: {
    bpm: 108, subdiv: 2, scale: 'phrygian', root: -24,
    progression: [0, 1, 0, 6],
    padWave: 'sawtooth', padGain: 0.035, bassGain: 0.10,
    melody: true, melodyPattern: [1, 1, 0, 1, 1, 0, 1, 0],
    melodyDur: 0.20, melodyWave: 'sawtooth', melodyGain: 0.030,
    drums: true, drumPattern: [1, 2, 3, 2, 1, 2, 3, 3], drumGain: 0.24, choir: true,
  },
  grace: {
    bpm: 44, subdiv: 2, scale: 'lydian', root: -19,
    progression: [0, 3, 4, 3],
    padWave: 'sine', padGain: 0.060, bassGain: 0.035,
    melody: true, melodyPattern: [1, 0, 0, 0, 1, 0, 0, 0],
    melodyDur: 1.4, melodyWave: 'sine', melodyGain: 0.036,
    drums: false, drumPattern: [0], drumGain: 0, choir: false,
  },
  village: {
    bpm: 68, subdiv: 2, scale: 'dorian', root: -19,
    progression: [0, 4, 5, 3],
    padWave: 'triangle', padGain: 0.045, bassGain: 0.045,
    melody: true, melodyPattern: [1, 0, 1, 0, 1, 0, 0, 1],
    melodyDur: 0.5, melodyWave: 'sine', melodyGain: 0.034,
    drums: false, drumPattern: [0], drumGain: 0, choir: false,
  },
};

export { MUSIC_MODES };
