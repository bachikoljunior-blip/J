// ============================================================================
//  audio.js — everything you hear is synthesised at runtime.
//
//  No audio files means no download, no decode stall on a phone, and the
//  freedom to make the score respond continuously to what is happening: the
//  combat layer fades in as enemies notice you, the boss layer swaps the mode
//  from Aeolian to Phrygian, and the wind bed tracks the weather system.
//
//  The same rule holds for the voices. Nobody recorded a line for this game;
//  every syllable an NPC, a soldier or a drake produces is a buzz shaped by
//  four resonances, built here from about forty numbers per vowel. See the
//  "Voice" section near the bottom of the file.
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

    // Where the ears are. Voices are placed against this, so a call from a
    // husk forty metres off arrives quiet, dull and to one side.
    this.listener = { x: 0, y: 1.6, z: 0, yaw: 0 };
    this.voiceVolume = 1.0;
    this._voiceEnds = [];      // end times of utterances still sounding
    this._voiceGate = new Map(); // key -> earliest time it may sound again
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

    // Voices ride the SFX slider but get their own trim, because a grunt on
    // every swing needs to sit under the swing rather than on top of it.
    this.voiceBus = ctx.createGain();
    this.voiceBus.gain.value = this.voiceVolume;
    this.voiceBus.connect(this.sfxBus);

    this._noiseBuf = this._makeNoise(2.0);
    this._startAmbient();
    this._nextNoteTime = ctx.currentTime + 0.1;
    this.ready = true;
  }

  resume() {
    if (this.ctx && this.ctx.state === 'suspended') this.ctx.resume();
  }

  /**
   * Move a bus gain over a few milliseconds instead of assigning it.
   *
   * Writing .value mid-sound is a step in the waveform, and a step is a click —
   * the same defect the rig and the camera have per-frame bounds for, in the
   * one output where it is audible rather than visible. Muting during combat
   * is the worst case: every voice in the mix is cut at once, so the step is
   * the full amplitude of the mix.
   *
   * 18 ms is long enough that the discontinuity falls below hearing and short
   * enough that a mute still reads as instant.
   */
  _rampGain(node, value) {
    const g = node.gain;
    const t = this.ctx.currentTime;
    g.cancelScheduledValues(t);
    g.setValueAtTime(g.value, t);
    g.linearRampToValueAtTime(value, t + 0.018);
  }

  setVolumes({ master, music, sfx }) {
    if (master !== undefined) this.masterVolume = master;
    if (music !== undefined) this.musicVolume = music;
    if (sfx !== undefined) this.sfxVolume = sfx;
    if (!this.ready) return;
    this._rampGain(this.master, this.muted ? 0 : this.masterVolume);
    this._rampGain(this.musicBus, this.musicVolume);
    this._rampGain(this.sfxBus, this.sfxVolume);
  }

  setMuted(m) {
    this.muted = m;
    if (this.ready) this._rampGain(this.master, m ? 0 : this.masterVolume);
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

  /**
   * @param {number} dt
   * @param {{windStrength?: number, rain?: number, night?: number, indoors?: number,
   *          listener?: {x: number, y: number, z: number, yaw: number}}} opts
   *   `listener` should be the camera, not the body — it is what every
   *   positioned voice is placed against.
   */
  updateAmbient(dt, { windStrength = 0.4, rain = 0, night = 0, indoors = 0, listener = null }) {
    if (!this.ready) return;
    if (listener) this.setListener(listener.x, listener.y || 0, listener.z, listener.yaw || 0);
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
    const prev = this.musicMode;
    this.musicMode = mode;
    this._step = 0;

    // The threat mode *is* the awareness event: explore→tension is somebody
    // spotting you, tension→combat is them committing, and dropping back to
    // explore is them losing you. Calling from here means the shout lands on
    // the same frame the music turns, which is when the player expects it.
    if (prev === 'explore' && mode === 'tension') this._offscreenCall('notice');
    else if (prev === 'tension' && mode === 'combat') this._offscreenCall('rally');
    else if ((prev === 'combat' || prev === 'tension') && mode === 'explore') this._offscreenCall('lost');
  }

  /**
   * A call from an enemy the player cannot see. There is no position to use,
   * so it is placed at a plausible middle distance off to one side — which is
   * exactly what an unseen caller sounds like.
   */
  _offscreenCall(id) {
    if (!this.ready) return;
    const L = this.listener;
    const a = Math.random() * Math.PI * 2;
    const d = 11 + Math.random() * 9;
    this.playVocal(id, {
      voice: Math.random() < 0.5 ? 'knight' : 'grave',
      x: L.x + Math.sin(a) * d, y: L.y, z: L.z + Math.cos(a) * d,
      gain: 0.9,
    });
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

  /**
   * @param {number} weight  heavier weapons swing slower and lower
   * @param {{ voice?: string, family?: string, x?: number, y?: number, z?: number,
   *           scale?: number, silent?: boolean }} [opts] who is swinging
   */
  playSwing(weight = 1, opts = {}) {
    if (!this.ready) return;
    const t = this.ctx.currentTime;
    this._noiseVoice({
      t, dur: 0.18 + weight * 0.10, type: 'bandpass',
      freq: 900 / weight, sweepTo: 260 / weight, q: 1.4, gain: 0.18,
    });
    this._toneVoice({ t, dur: 0.12, freq: 220 / weight, glideTo: 90, type: 'sine', gain: 0.06 });
    // Not every swing — a fighter who grunts on all of them is a comedy.
    if (opts.silent) return;
    const heavy = weight > 1.5;
    if (heavy || Math.random() < 0.42) {
      // Weight is the only thing the call site tells us about the body doing
      // the swinging, so let it choose the throat when nobody named one.
      const o = opts.voice || opts.family ? opts : Object.assign({ voice: bodyVoice(weight) }, opts);
      this._combatVocal(heavy ? 'effort_heavy' : 'effort_light', o, heavy ? 0.85 : 0.6);
    }
  }

  /** @param {number} power @param {object} [opts] the *target* of the blow */
  playHitFlesh(power = 1, opts = {}) {
    if (!this.ready) return;
    const t = this.ctx.currentTime;
    this._noiseVoice({ t, dur: 0.10, type: 'lowpass', freq: 620, gain: 0.30 * power });
    this._toneVoice({ t, dur: 0.13, freq: 130, glideTo: 52, type: 'sine', gain: 0.22 * power });
    if (opts.silent) return;
    this._combatVocal(power > 0.95 ? 'hurt_heavy' : 'hurt_light', opts, 0.8);
  }

  /**
   * Shared tail for the combat SFX: emit the matching vocalisation in whatever
   * throat the caller named, at the caller's position when it gave one.
   */
  _combatVocal(id, opts, gain = 0.8) {
    if (!this.ready || opts.silent) return;
    // Without x/z the utterance goes straight to the bus: a sound with no
    // position is the player's own body, and that is never distant.
    const o = {
      gain, scale: opts.scale,
      x: opts.x, y: opts.y, z: opts.z,
      voice: opts.voice, family: opts.family,
    };
    if (opts.family) this.creatureVocal(opts.family, id, o);
    else this.playVocal(id, o);
  }

  playHitMetal(power = 1) {
    if (!this.ready) return;
    const t = this.ctx.currentTime;
    this._fmVoice({ t, dur: 0.28, carrier: 780, ratio: 3.9, index: 1400, gain: 0.16 * power });
    this._noiseVoice({ t, dur: 0.09, type: 'highpass', freq: 3200, gain: 0.16 * power });
  }

  /** @param {object} [opts] the blocker, whose shield just took the weight */
  playBlock(opts = {}) {
    if (!this.ready) return;
    const t = this.ctx.currentTime;
    this._fmVoice({ t, dur: 0.20, carrier: 300, ratio: 2.1, index: 700, gain: 0.20 });
    this._noiseVoice({ t, dur: 0.10, type: 'bandpass', freq: 1400, q: 2, gain: 0.16 });
    if (Math.random() < 0.6) this._combatVocal('block_grunt', opts, 0.6);
  }

  /** @param {object} [opts] the *attacker*, whose swing was just thrown back */
  playParry(opts = {}) {
    if (!this.ready) return;
    const t = this.ctx.currentTime;
    this._fmVoice({ t, dur: 0.55, carrier: 1180, ratio: 4.7, index: 2400, gain: 0.22 });
    this._toneVoice({ t: t + 0.02, dur: 0.4, freq: 2360, type: 'sine', gain: 0.10 });
    this._combatVocal('parried', opts, 0.85);
  }

  /** @param {object} [opts] the victim of the critical */
  playCritical(opts = {}) {
    if (!this.ready) return;
    const t = this.ctx.currentTime;
    this._noiseVoice({ t, dur: 0.25, type: 'lowpass', freq: 800, sweepTo: 200, gain: 0.36 });
    this._toneVoice({ t, dur: 0.5, freq: 90, glideTo: 40, type: 'sawtooth', gain: 0.20 });
    this._fmVoice({ t: t + 0.03, dur: 0.4, carrier: 520, ratio: 1.4, index: 900, gain: 0.16 });
    this._combatVocal('hurt_heavy', opts, 1.0);
  }

  /** @param {object} [opts] whoever just lost their guard */
  playGuardBreak(opts = {}) {
    if (!this.ready) return;
    const t = this.ctx.currentTime;
    this._fmVoice({ t, dur: 0.7, carrier: 180, ratio: 3.1, index: 1600, gain: 0.26 });
    this._combatVocal('stagger', opts, 0.9);
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

  /** @param {object} [opts] the roller */
  playRoll(opts = {}) {
    if (!this.ready) return;
    const t = this.ctx.currentTime;
    this._noiseVoice({ t, dur: 0.32, type: 'lowpass', freq: 1400, sweepTo: 350, gain: 0.14 });
    if (Math.random() < 0.3) this._combatVocal('exert_roll', opts, 0.45);
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

  /**
   * The drake's fire breath. The roar rides under the flame rather than before
   * it, because the animal is making both sounds with the same lungs.
   * @param {object} [opts] the breather; pass its position and scale
   */
  playBreath(opts = {}) {
    if (!this.ready) return;
    const t = this.ctx.currentTime;
    this._noiseVoice({ t, dur: 1.2, type: 'lowpass', freq: 3000, sweepTo: 700, gain: 0.24 });
    this.creatureVocal(opts.family || 'drake', 'attack', {
      x: opts.x, y: opts.y, z: opts.z, scale: opts.scale || 1.6, gain: 0.9,
    });
  }

  playDrink(opts = {}) {
    if (!this.ready) return;
    const t = this.ctx.currentTime;
    for (let i = 0; i < 3; i++) {
      this._toneVoice({ t: t + i * 0.11, dur: 0.09, freq: 210 + i * 40, glideTo: 130, type: 'sine', gain: 0.10 });
    }
    // You only reach for the flask when you are hurt; the exhale after it is
    // the only place the player's own body gets to say so.
    this.playVocal('wounded_breath', { voice: opts.voice || 'knight', gain: 0.7, when: t + 0.42 });
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

  /** @param {object} [opts] the dying actor; defaults to the player */
  playDeath(opts = {}) {
    if (!this.ready) return;
    const t = this.ctx.currentTime;
    this._toneVoice({ t, dur: 2.6, freq: 160, glideTo: 42, type: 'sawtooth', gain: 0.14, attack: 0.05 });
    this._noiseVoice({ t, dur: 2.2, type: 'lowpass', freq: 900, sweepTo: 140, gain: 0.12 });
    this._combatVocal('death_cry', Object.assign({ voice: 'knight' }, opts), 1.0);
  }

  /** @param {object} [opts] the boss; `family` picks the throat it roars with */
  playBossHorn(opts = {}) {
    if (!this.ready) return;
    const t = this.ctx.currentTime;
    [0, 7].forEach((n, i) => {
      this._toneVoice({ t: t + i * 0.02, dur: 2.2, freq: NOTE(-16 + n), type: 'sawtooth', gain: 0.11, attack: 0.25 });
    });
    this._taiko(t + 0.1, 0.5);
    this._taiko(t + 0.55, 0.4);
    if (opts.family) {
      this.creatureVocal(opts.family, 'phase', {
        x: opts.x, y: opts.y, z: opts.z, scale: opts.scale || 1.4, gain: 1.0,
      });
    } else {
      this.playVocal('boss_phase', { voice: 'grave', gain: 0.95, x: opts.x, y: opts.y, z: opts.z });
    }
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

  // -------------------------------------------------------------------------
  //  Voice
  //
  //  Three entry points, all of which end up in synthesizeVoice():
  //    speak()        — an arbitrary utterance plan
  //    speakLine()    — a line of dialogue, spoken in the invented phonology
  //    playVocal()    — a named combat vocalisation
  //    creatureVocal()— the same, in a non-human throat
  // -------------------------------------------------------------------------

  /**
   * Tell the engine where the ears are. Called with the camera, not the body:
   * what you hear should match what you are looking at.
   * @param {number} x @param {number} y @param {number} z @param {number} yaw
   */
  setListener(x, y, z, yaw = 0) {
    this.listener.x = x; this.listener.y = y; this.listener.z = z;
    this.listener.yaw = yaw;
  }

  /**
   * Build a distance chain for a sound at a world position and hand its input
   * node to `emit`. Returns null — without calling `emit` at all — when the
   * source is out of earshot, so a far-off fight costs nothing.
   * @param {number} x @param {number} y @param {number} z
   * @param {(node: GainNode, attenuation: number, distance: number) => void} emit
   * @param {{ life?: number, bus?: AudioNode }} [opts] life = seconds before teardown
   */
  playAt(x, y, z, emit, opts = {}) {
    if (!this.ready) return null;
    const ctx = this.ctx;
    const L = this.listener;
    const dx = x - L.x, dy = (y || 0) - L.y, dz = z - L.z;
    const d = Math.sqrt(dx * dx + dy * dy + dz * dz);
    const F = VOICE_FALLOFF;
    if (d > F.max) return null;
    const att = F.ref / (F.ref + F.rolloff * Math.max(0, d - F.ref));
    if (att < 0.02) return null;

    const head = ctx.createGain();
    head.gain.value = att;
    // Air and foliage eat the top end long before they eat the level, and that
    // dulling is most of what tells you a voice is far away rather than quiet.
    const lp = ctx.createBiquadFilter();
    lp.type = 'lowpass';
    lp.frequency.value = F.airFar + (F.airNear - F.airFar) * Math.pow(att, 0.55);
    lp.Q.value = 0.35;
    head.connect(lp);
    let tail = lp;
    if (ctx.createStereoPanner) {
      const pan = ctx.createStereoPanner();
      // Right vector of a yaw whose forward is (sin, cos).
      const right = (dx * Math.cos(L.yaw) - dz * Math.sin(L.yaw)) / Math.max(d, 0.001);
      pan.pan.value = Math.max(-0.92, Math.min(0.92, right * Math.min(1, d / 2.5)));
      lp.connect(pan);
      tail = pan;
    }
    tail.connect(opts.bus || this.voiceBus);

    if (emit) emit(head, att, d);
    const life = (opts.life || 2.5) + 0.5;
    setTimeout(() => { try { head.disconnect(); lp.disconnect(); if (tail !== lp) tail.disconnect(); } catch (e) { /* context closed */ } },
      life * 1000);
    return { node: head, attenuation: att, distance: d };
  }

  /** Free a slot if fewer than the cap are sounding; keeps node count bounded. */
  _voiceSlot(max = 5) {
    const now = this.ctx.currentTime;
    this._voiceEnds = this._voiceEnds.filter((e) => e > now);
    return this._voiceEnds.length < max;
  }

  /** A per-key minimum gap, so a flurry of hits does not stack ten grunts. */
  _voiceGateOpen(key, gap) {
    if (!key) return true;
    const now = this.ctx.currentTime;
    const until = this._voiceGate.get(key) || 0;
    if (now < until) return false;
    this._voiceGate.set(key, now + gap);
    return true;
  }

  /**
   * Speak an utterance plan (see utteranceFromText / VOCALS for the shape).
   * @param {object} plan
   * @param {{ voice?: string, x?: number, y?: number, z?: number, gain?: number,
   *           key?: string, gap?: number, when?: number }} [opts]
   * @returns {number} duration in seconds, 0 if nothing was scheduled
   */
  speak(plan, opts = {}) {
    if (!this.ready || !plan || this.muted) return 0;
    if (!this._voiceSlot(opts.max || 5)) return 0;
    if (!this._voiceGateOpen(opts.key, opts.gap != null ? opts.gap : 0.12)) return 0;

    const timbre = resolveTimbre(opts.voice);
    const positioned = opts.x !== undefined && opts.z !== undefined;
    let dur = 0;
    // Distance is handled by the playAt chain, so the synth always renders at
    // full level and only the routing knows how far away the speaker is.
    const run = (dest) => {
      const handle = synthesizeVoice(this.ctx, dest, plan, timbre, {
        when: opts.when, gain: opts.gain != null ? opts.gain : 1,
        noiseBuffer: this._noiseBuf,
      });
      if (handle) { dur = handle.duration; this._lastUtterance = handle; }
    };
    if (positioned) {
      const chain = this.playAt(opts.x, opts.y || 0, opts.z, run,
        { life: estimateDuration(plan, timbre) });
      if (!chain) return 0;
    } else {
      run(this.voiceBus);
    }
    if (dur > 0) this._voiceEnds.push(this.ctx.currentTime + dur);
    return dur;
  }

  /**
   * Speak a line of dialogue. The syllables and the pitch contour are derived
   * from the text itself, so a line always sounds the same and a long line
   * takes longer — without ever pronouncing a real word.
   * @param {string} text  the line as the player reads it
   * @param {{ voice?: string, x?: number, y?: number, z?: number, key?: string }} [opts]
   * @returns {number} duration in seconds
   */
  speakLine(text, opts = {}) {
    if (!this.ready || !text) return 0;
    const timbre = resolveTimbre(opts.voice);
    const plan = utteranceFromText(text, timbre);
    const prev = this._lastLine;
    const dur = this.speak(plan, Object.assign({}, opts, {
      key: opts.key || `line:${opts.voice || 'x'}`, gap: 0.25, max: 6,
    }));
    if (dur > 0) {
      // Advancing the conversation interrupts the speaker, as it should — but
      // only once the replacement is actually going to sound.
      if (prev && prev.stop) prev.stop(this.ctx.currentTime + 0.05);
      this._lastLine = this._lastUtterance;
    }
    return dur;
  }

  /**
   * A named combat vocalisation — see VOCALS for the roster.
   * @param {string} id  key in VOCALS
   * @param {{ voice?: string, family?: string, x?: number, y?: number, z?: number,
   *           gain?: number, pitch?: number }} [opts]
   */
  playVocal(id, opts = {}) {
    const base = VOCALS[id];
    if (!base) return 0;
    if (opts.family && CREATURE_VOICES[opts.family]) return this.creatureVocal(opts.family, id, opts);
    const plan = Object.assign({}, base);
    if (opts.pitch) plan.pitchScale = (plan.pitchScale || 1) * opts.pitch;
    return this.speak(plan, Object.assign({ key: `v:${opts.voice || 'c'}:${id}`, gap: 0.22 }, opts));
  }

  /**
   * The same event in a throat that is not human. Families differ in what the
   * source is (buzz, noise, or both), how many resonances survive and how wide
   * they are — a beast is noise and growl with barely a formant to its name,
   * a wraith is a voice with the body taken out of it.
   * @param {string} family  key in CREATURE_VOICES, or an archetype id
   * @param {string} event   'notice' | 'attack' | 'hurt' | 'death' | 'idle' | a VOCALS id
   * @param {{ x?: number, y?: number, z?: number, gain?: number, scale?: number }} [opts]
   */
  creatureVocal(family, event, opts = {}) {
    const fam = CREATURE_VOICES[family] || CREATURE_VOICES[CREATURE_VOICE_OF[family]];
    if (!fam) return 0;
    const call = fam.calls[event] || fam.calls[CALL_ALIAS[event]] || fam.calls.attack;
    if (!call) return 0;
    const plan = Object.assign({}, fam.voice, call);
    // A bigger animal is a longer tube and a slacker fold: lower and slower.
    const s = opts.scale || 1;
    if (s !== 1) {
      plan.pitchScale = (plan.pitchScale || 1) / Math.pow(s, 0.7);
      plan.formantScale = (plan.formantScale || 1) / Math.pow(s, 0.5);
      plan.dur = (plan.dur || 0.4) * Math.pow(s, 0.25);
    }
    const o = Object.assign({ key: `c:${family}:${event}`, gap: 0.3 }, opts);
    if (!o.voice) o.voice = fam.timbre;
    return this.speak(plan, o);
  }
}

// ===========================================================================
//  Voice
//
//  Speech is a buzz shaped by a tube. The vocal folds make a sawtooth-ish
//  pulse train at 80-250 Hz; the throat, mouth and nose above them resonate at
//  four frequencies — the formants — and those four numbers are what make a
//  vowel a vowel. A consonant is not a sound so much as a *move*: a closure, a
//  burst of turbulence, or a fast slide of those same resonances toward a
//  different place of articulation, over 40-100 ms.
//
//  So: two detuned sawtooths and a noise source into four bandpass filters
//  whose frequencies are automated. That is the whole instrument. Scaling all
//  four formants together is scaling the length of the tube, which is why the
//  same table gives a huge slow speaker and a small quick one.
// ===========================================================================

/** Vowel targets: F1..F4 in Hz, their bandwidths, and relative level. */
export const PHONEMES = {
  a:  { f: [730, 1090, 2440, 3350], bw: [90, 110, 150, 200], g: [1.00, 0.60, 0.30, 0.16] },
  ae: { f: [660, 1720, 2410, 3300], bw: [90, 120, 150, 200], g: [1.00, 0.70, 0.32, 0.16] },
  e:  { f: [530, 1840, 2480, 3450], bw: [80, 100, 140, 200], g: [1.00, 0.66, 0.30, 0.14] },
  i:  { f: [270, 2290, 3010, 3600], bw: [60, 90, 130, 200], g: [1.00, 0.50, 0.28, 0.12] },
  o:  { f: [570, 840, 2410, 3300], bw: [80, 95, 140, 200], g: [1.00, 0.72, 0.22, 0.10] },
  u:  { f: [300, 870, 2240, 3250], bw: [60, 90, 130, 200], g: [1.00, 0.55, 0.18, 0.08] },
  // 日本語の「う」 is unrounded, and keeping one of those in the inventory is
  // most of why the invented language still sounds like it belongs here.
  ux: { f: [320, 1390, 2280, 3300], bw: [65, 100, 140, 200], g: [1.00, 0.58, 0.22, 0.10] },
  ax: { f: [500, 1500, 2500, 3400], bw: [90, 120, 150, 200], g: [1.00, 0.58, 0.26, 0.12] },
};

/**
 * Consonants, as the move that makes them.
 *   stop   — silence, then a filtered click at the release
 *   fric   — turbulence in a narrow band, voicing off or nearly off
 *   nasal  — voicing continues through a damped, low-F1 tract
 *   approx — no noise at all, just the formants sliding through a locus
 *   asp    — breath through the tract the vowel is about to use
 */
export const ARTICULATIONS = {
  '':  { kind: 'open', dur: 0 },
  m:   { kind: 'nasal', dur: 0.055, locus: [280, 1100, 2300, 3200], damp: 0.5, voiced: 0.55 },
  n:   { kind: 'nasal', dur: 0.048, locus: [280, 1700, 2600, 3300], damp: 0.5, voiced: 0.55 },
  ny:  { kind: 'nasal', dur: 0.052, locus: [270, 2050, 2800, 3400], damp: 0.5, voiced: 0.5 },
  p:   { kind: 'stop', dur: 0.060, burst: 900, bq: 1.3, level: 0.34, locus: [250, 800, 2200, 3200] },
  t:   { kind: 'stop', dur: 0.054, burst: 3600, bq: 2.6, level: 0.40, locus: [300, 1750, 2900, 3500] },
  k:   { kind: 'stop', dur: 0.058, burst: 1900, bq: 2.1, level: 0.38, locus: [300, 1900, 2600, 3300] },
  b:   { kind: 'stop', dur: 0.052, burst: 700, bq: 1.2, level: 0.22, voiced: 0.30, locus: [250, 800, 2200, 3200] },
  d:   { kind: 'stop', dur: 0.048, burst: 2800, bq: 2.2, level: 0.24, voiced: 0.30, locus: [300, 1700, 2800, 3500] },
  g:   { kind: 'stop', dur: 0.052, burst: 1500, bq: 1.9, level: 0.24, voiced: 0.30, locus: [300, 1800, 2500, 3300] },
  s:   { kind: 'fric', dur: 0.080, band: 5400, bq: 3.4, level: 0.30, locus: [300, 1700, 2900, 3600] },
  sh:  { kind: 'fric', dur: 0.086, band: 2600, bq: 2.2, level: 0.34, locus: [300, 1900, 2500, 3300] },
  f:   { kind: 'fric', dur: 0.072, band: 1700, bq: 1.1, level: 0.20, locus: [320, 1100, 2300, 3200] },
  z:   { kind: 'fric', dur: 0.068, band: 4600, bq: 3.0, level: 0.20, voiced: 0.40, locus: [300, 1700, 2900, 3600] },
  ts:  { kind: 'fric', dur: 0.070, band: 4800, bq: 3.2, level: 0.34, locus: [300, 1750, 2900, 3500] },
  ch:  { kind: 'fric', dur: 0.076, band: 2900, bq: 2.4, level: 0.34, locus: [300, 2000, 2700, 3400] },
  h:   { kind: 'asp', dur: 0.062, level: 0.38 },
  r:   { kind: 'approx', dur: 0.048, locus: [320, 1150, 1650, 3200] },
  l:   { kind: 'approx', dur: 0.044, locus: [360, 1300, 2700, 3400] },
  w:   { kind: 'approx', dur: 0.050, locus: [300, 650, 2200, 3200] },
  y:   { kind: 'approx', dur: 0.044, locus: [260, 2200, 3100, 3600] },
};

const DEFAULT_TIMBRE = {
  f0: 120,          // Hz at rest
  formant: 1.0,     // tract length: <1 is a longer tube, i.e. a larger speaker
  breath: 0.25,     // how much of the source is turbulence rather than buzz
  rough: 0.30,      // fold asymmetry — detune between the two source oscillators
  rate: 6.4,        // syllables per second
  wave: 'sawtooth',
  tilt: 3000,       // spectral roll-off; a bright voice carries further
  vib: 0, vibDepth: 0,
  level: 1,
};

/**
 * The speakers. Base pitch and tract length do the heavy lifting — halving
 * `formant` does not make a voice deeper, it makes the body bigger, which is
 * a different and much stronger cue.
 */
export const VOICE_TIMBRES = {
  elder:    { f0: 98, formant: 0.94, breath: 0.30, rough: 0.55, rate: 5.4, tilt: 2500 },
  matron:   { f0: 172, formant: 1.04, breath: 0.28, rough: 0.30, rate: 6.2, tilt: 3100 },
  smith:    { f0: 82, formant: 0.84, breath: 0.16, rough: 0.72, rate: 5.6, tilt: 2200 },
  knight:   { f0: 116, formant: 0.95, breath: 0.14, rough: 0.25, rate: 6.6, tilt: 3400 },
  herald:   { f0: 132, formant: 0.92, breath: 0.10, rough: 0.20, rate: 7.0, tilt: 4200, wave: 'square' },
  merchant: { f0: 186, formant: 1.07, breath: 0.22, rough: 0.28, rate: 8.2, tilt: 3600 },
  broker:   { f0: 142, formant: 0.99, breath: 0.20, rough: 0.40, rate: 7.6, tilt: 3200 },
  ash:      { f0: 164, formant: 1.02, breath: 0.48, rough: 0.38, rate: 5.6, tilt: 2700 },
  keeper:   { f0: 202, formant: 1.13, breath: 0.30, rough: 0.22, rate: 7.4, tilt: 3800 },
  grave:    { f0: 76, formant: 0.88, breath: 0.40, rough: 0.80, rate: 4.8, tilt: 1900 },
  hermit:   { f0: 128, formant: 1.00, breath: 0.55, rough: 0.45, rate: 4.6, tilt: 2400, vib: 4.2, vibDepth: 16 },
  singer:   { f0: 214, formant: 1.16, breath: 0.18, rough: 0.12, rate: 6.0, tilt: 4000, vib: 5.4, vibDepth: 28 },
  child:    { f0: 246, formant: 1.24, breath: 0.26, rough: 0.18, rate: 8.0, tilt: 3900 },
};

/** Distance model for voices. Shared by everything that goes through playAt. */
export const VOICE_FALLOFF = {
  ref: 5,          // metres of full level
  max: 48,         // beyond this nothing is scheduled at all
  rolloff: 1.25,
  airNear: 11000,  // low-pass cutoff at the listener's ear
  airFar: 900,     // and at the edge of the world
};

const seg = (c, v, w, a, b, level) => ({ c, v, w: w || 1, f0a: a, f0b: b, level: level == null ? 1 : level });

/** Fallback speaker for a combat sound whose caller only told us the weight. */
function bodyVoice(weight) {
  return weight > 1.6 ? 'grave' : weight > 1.15 ? 'smith' : 'knight';
}

/**
 * Combat vocalisations. Each is a tiny utterance: the syllables, the pitch
 * contour over them, and how hard the folds are being driven. `press` opens
 * the spectrum and adds fold noise — the difference between a word and a
 * shout is mostly pressure, not pitch.
 */
export const VOCALS = {
  // --- attacking ---------------------------------------------------------
  effort_light: {
    segments: [seg('h', 'ax', 1, 1.15, 0.82)],
    dur: 0.21, gain: 0.30, press: 0.55, tilt: 1.05,
  },
  effort_heavy: {
    segments: [seg('h', 'a', 1, 1.00, 1.28), seg('', 'a', 1.4, 1.28, 0.68)],
    dur: 0.52, gain: 0.42, press: 0.95, growl: 30, growlDepth: 0.35, tilt: 1.15,
  },
  rally: {
    segments: [seg('w', 'a', 1, 1.28, 1.50), seg('', 'ae', 1.2, 1.52, 1.34), seg('', 'a', 1.6, 1.30, 0.92)],
    dur: 0.86, gain: 0.46, press: 1.0, tilt: 1.35,
  },
  // --- being hit ---------------------------------------------------------
  block_grunt: {
    segments: [seg('n', 'ux', 1, 0.96, 0.80)],
    dur: 0.20, gain: 0.30, press: 0.70, tilt: 0.80,
  },
  hurt_light: {
    segments: [seg('', 'a', 1, 1.34, 1.02)],
    dur: 0.25, gain: 0.36, press: 0.80, breath: 0.20, tilt: 1.1,
  },
  hurt_heavy: {
    segments: [seg('g', 'a', 1, 1.50, 1.14), seg('', 'ax', 1.5, 1.10, 0.72)],
    dur: 0.56, gain: 0.46, press: 1.0, growl: 26, growlDepth: 0.4, breath: 0.25, tilt: 1.2,
  },
  stagger: {
    segments: [seg('', 'u', 1, 1.18, 0.94), seg('h', 'ax', 1.6, 0.90, 0.60)],
    dur: 0.62, gain: 0.34, press: 0.55, breath: 0.55,
  },
  parried: {
    // Surprise is a rise that gets cut off, not a long note.
    segments: [seg('', 'a', 0.7, 1.05, 1.35), seg('', 'e', 0.6, 1.55, 1.72)],
    dur: 0.28, gain: 0.40, press: 0.60, tilt: 1.25,
  },
  // --- awareness ---------------------------------------------------------
  notice: {
    segments: [seg('h', 'e', 1, 1.18, 1.42), seg('', 'i', 1.1, 1.50, 1.30)],
    dur: 0.50, gain: 0.44, press: 0.85, tilt: 1.4,
  },
  lost: {
    segments: [seg('ts', 'ax', 1, 0.96, 0.86), seg('', 'ux', 1.3, 0.82, 0.66)],
    dur: 0.54, gain: 0.26, press: 0.35, breath: 0.35, tilt: 0.85,
  },
  // --- ending ------------------------------------------------------------
  death_cry: {
    segments: [seg('', 'a', 1, 1.48, 1.20), seg('', 'ax', 1.4, 1.05, 0.74), seg('', 'ux', 2.0, 0.62, 0.34)],
    dur: 1.45, gain: 0.46, press: 0.9, growl: 18, growlDepth: 0.45, breath: 0.55,
  },
  boss_phase: {
    segments: [seg('g', 'o', 1, 0.74, 0.98), seg('', 'a', 2.2, 1.00, 0.52)],
    dur: 2.05, gain: 0.52, press: 1.0, growl: 21, growlDepth: 0.6,
    formantScale: 0.72, pitchScale: 0.62, tilt: 0.9,
  },
  wounded_breath: {
    segments: [seg('h', 'ax', 1, 0.92, 0.74)],
    dur: 0.86, gain: 0.22, press: 0.15, breath: 1.0, voiced: 0.35, tilt: 0.9,
  },
  exert_roll: {
    segments: [seg('h', 'ux', 1, 1.06, 0.86)],
    dur: 0.23, gain: 0.24, press: 0.45, breath: 0.5,
  },
  relief: {
    segments: [seg('f', 'ux', 1, 1.00, 0.82), seg('', 'ax', 1.5, 0.80, 0.66)],
    dur: 0.78, gain: 0.24, press: 0.2, breath: 0.85, voiced: 0.5,
  },
};

/** Events a family may not name explicitly; fall back to the nearest one. */
const CALL_ALIAS = {
  effort_light: 'attack', effort_heavy: 'attack', rally: 'notice',
  hurt_light: 'hurt', hurt_heavy: 'hurt', block_grunt: 'hurt',
  stagger: 'hurt', parried: 'hurt', death_cry: 'death',
  boss_phase: 'phase', exert_roll: 'idle', wounded_breath: 'idle',
  lost: 'idle', relief: 'idle',
};

/**
 * Creature families. These are not one instrument transposed: `voiced`/`noise`
 * decide what the source even is, `formants` how many resonances survive and
 * `qScale` how sharp they are. A beast at qScale 0.22 has no formants worth
 * the name and lives in growl; the wraith is voiced 0 — the tract is still
 * there, shaping vowels, but there is no body behind it to drive them.
 */
export const CREATURE_VOICES = {
  soldier: {
    timbre: 'knight',
    voice: { voiced: 1, noise: 0.1, qScale: 1, formants: 4 },
    calls: {
      notice: VOCALS.notice, attack: VOCALS.effort_light, hurt: VOCALS.hurt_light,
      death: VOCALS.death_cry, phase: VOCALS.rally,
      idle: { segments: [seg('h', 'ax', 1, 0.94, 0.80)], dur: 0.4, gain: 0.16, breath: 0.6, press: 0.2 },
    },
  },
  brigand: {
    timbre: 'broker',
    voice: { voiced: 1, noise: 0.18, qScale: 0.92, formants: 4, tilt: 1.1 },
    calls: {
      notice: { segments: [seg('y', 'a', 1, 1.30, 1.55), seg('', 'o', 1.2, 1.48, 1.10)], dur: 0.46, gain: 0.44, press: 0.9 },
      attack: { segments: [seg('t', 'a', 1, 1.20, 0.90)], dur: 0.20, gain: 0.32, press: 0.7 },
      hurt: VOCALS.hurt_light, death: VOCALS.death_cry, phase: VOCALS.rally,
      idle: { segments: [seg('ch', 'ax', 1, 0.95, 0.8)], dur: 0.30, gain: 0.14, press: 0.3 },
    },
  },
  husk: {
    // A voice that has forgotten it is one: the tract still moves, the folds
    // barely close, and there is air leaking through the whole utterance.
    timbre: 'grave',
    voice: { voiced: 0.55, noise: 0.85, qScale: 0.55, formants: 3, growl: 14, growlDepth: 0.35, tilt: 0.7, jitter: 0.05 },
    calls: {
      notice: { segments: [seg('', 'ax', 1, 0.90, 1.10), seg('', 'a', 1.6, 1.05, 0.70)], dur: 0.9, gain: 0.40, press: 0.6 },
      attack: { segments: [seg('h', 'a', 1, 0.95, 0.72)], dur: 0.42, gain: 0.34, press: 0.7 },
      hurt: { segments: [seg('', 'ux', 1, 1.15, 0.78)], dur: 0.45, gain: 0.36, press: 0.6 },
      death: { segments: [seg('', 'a', 1, 1.00, 0.70), seg('', 'ax', 2, 0.66, 0.30)], dur: 1.6, gain: 0.40, breath: 1.0 },
      phase: { segments: [seg('', 'a', 1, 0.85, 0.55)], dur: 1.8, gain: 0.46, growl: 11, growlDepth: 0.7 },
      idle: { segments: [seg('h', 'ax', 1, 0.80, 0.66)], dur: 0.7, gain: 0.16, breath: 1.0, voiced: 0.25 },
    },
  },
  beast: {
    // No formants worth the name. Two broad resonances, a sub an octave down
    // and a hard amplitude modulation: that is a growl.
    timbre: 'grave',
    voice: {
      voiced: 0.9, noise: 0.7, qScale: 0.22, formants: 2, sub: 0.55,
      growl: 52, growlDepth: 0.75, pitchScale: 1.25, formantScale: 1.15,
      tilt: 1.0, jitter: 0.09,
    },
    calls: {
      notice: { segments: [seg('', 'a', 1, 1.20, 1.62), seg('', 'ax', 1.4, 1.55, 0.85)], dur: 0.55, gain: 0.44, press: 1.0 },
      attack: { segments: [seg('', 'a', 1, 1.35, 0.95)], dur: 0.26, gain: 0.42, press: 1.0 },
      hurt: { segments: [seg('', 'ae', 1, 1.70, 1.05)], dur: 0.34, gain: 0.44, press: 1.0 },
      death: { segments: [seg('', 'a', 1, 1.35, 0.90), seg('', 'u', 1.8, 0.80, 0.40)], dur: 1.2, gain: 0.44, growl: 34 },
      phase: { segments: [seg('', 'a', 1, 0.95, 0.60)], dur: 1.9, gain: 0.50, growl: 38, growlDepth: 0.85 },
      idle: { segments: [seg('', 'ux', 1, 0.85, 0.70)], dur: 0.8, gain: 0.18, growl: 30 },
    },
  },
  wraith: {
    // A voice with the body taken out of it: the source is pure turbulence, so
    // the formants colour air rather than a buzz, and nothing sounds driven.
    timbre: 'ash',
    voice: {
      voiced: 0.06, noise: 1.0, qScale: 1.8, formants: 4,
      pitchScale: 0.9, formantScale: 1.06, tilt: 1.5, jitter: 0.02,
    },
    calls: {
      notice: { segments: [seg('sh', 'i', 1, 1.05, 1.35), seg('', 'e', 1.6, 1.30, 1.05)], dur: 1.0, gain: 0.40 },
      attack: { segments: [seg('s', 'ax', 1, 1.10, 0.90)], dur: 0.45, gain: 0.34 },
      hurt: { segments: [seg('', 'i', 1, 1.40, 1.10)], dur: 0.5, gain: 0.38 },
      death: { segments: [seg('', 'ax', 1, 1.10, 0.80), seg('', 'u', 2.4, 0.75, 0.45)], dur: 1.9, gain: 0.36 },
      phase: { segments: [seg('', 'e', 1, 0.95, 1.25), seg('', 'ax', 2, 1.20, 0.70)], dur: 2.2, gain: 0.42 },
      idle: { segments: [seg('h', 'ux', 1, 0.95, 0.82)], dur: 0.9, gain: 0.15 },
    },
  },
  construct: {
    // Stone has resonances but no folds: a very low, very narrow pair of bands
    // scraped by noise. It reads as grinding rather than speaking, which is
    // the point — the sentinel is not talking to you.
    timbre: 'grave',
    voice: {
      voiced: 0.35, noise: 0.9, qScale: 3.2, formants: 3,
      pitchScale: 0.5, formantScale: 0.62, growl: 17, growlDepth: 0.5, tilt: 0.55,
    },
    calls: {
      notice: { segments: [seg('g', 'o', 1, 0.90, 1.10)], dur: 0.7, gain: 0.40 },
      attack: { segments: [seg('k', 'a', 1, 1.00, 0.80)], dur: 0.4, gain: 0.36 },
      hurt: { segments: [seg('', 'o', 1, 1.15, 0.90)], dur: 0.45, gain: 0.36 },
      death: { segments: [seg('', 'o', 1, 0.95, 0.60), seg('', 'u', 2, 0.55, 0.28)], dur: 1.7, gain: 0.40 },
      phase: { segments: [seg('', 'o', 1, 0.80, 0.50)], dur: 2.0, gain: 0.46, growl: 13, growlDepth: 0.8 },
      idle: { segments: [seg('', 'ux', 1, 0.70, 0.62)], dur: 1.0, gain: 0.14 },
    },
  },
  drake: {
    // Two metres of throat. Everything moves down together: the fold rate, the
    // tube length and the modulation, which is what stops it being a big wolf.
    timbre: 'grave',
    voice: {
      voiced: 1.0, noise: 0.85, qScale: 0.32, formants: 3, sub: 0.8,
      pitchScale: 0.86, formantScale: 0.46, growl: 26, growlDepth: 0.6,
      tilt: 0.55, jitter: 0.05,
    },
    calls: {
      notice: { segments: [seg('', 'a', 1, 0.95, 1.25), seg('', 'o', 2, 1.15, 0.65)], dur: 1.9, gain: 0.52, press: 1.0 },
      attack: { segments: [seg('', 'a', 1, 1.05, 0.78)], dur: 1.5, gain: 0.48, press: 1.0 },
      hurt: { segments: [seg('', 'ae', 1, 1.35, 0.90)], dur: 0.9, gain: 0.50 },
      death: { segments: [seg('', 'a', 1, 1.00, 0.62), seg('', 'u', 2.6, 0.58, 0.26)], dur: 2.8, gain: 0.50, growl: 15 },
      phase: { segments: [seg('', 'o', 1, 0.85, 1.05), seg('', 'a', 2.4, 1.00, 0.48)], dur: 2.6, gain: 0.56, growl: 19, growlDepth: 0.8 },
      idle: { segments: [seg('h', 'ux', 1, 0.75, 0.62)], dur: 1.4, gain: 0.20, breath: 1.0, voiced: 0.4 },
    },
  },
  swarm: {
    // Leeches and crows: chittering, so the "syllables" are far too short and
    // far too high to be speech, and the band is narrow and bright.
    timbre: 'child',
    voice: {
      voiced: 0.5, noise: 1.0, qScale: 2.4, formants: 3,
      pitchScale: 1.6, formantScale: 1.5, tilt: 1.8, jitter: 0.12,
    },
    calls: {
      notice: { segments: [seg('k', 'i', 0.5, 1.6, 1.9), seg('k', 'i', 0.5, 1.9, 1.6), seg('k', 'e', 0.5, 1.7, 2.0)], dur: 0.42, gain: 0.30 },
      attack: { segments: [seg('ts', 'i', 0.5, 1.9, 1.5)], dur: 0.16, gain: 0.30 },
      hurt: { segments: [seg('', 'i', 0.5, 2.1, 1.4)], dur: 0.22, gain: 0.32 },
      death: { segments: [seg('', 'i', 0.6, 2.0, 1.2), seg('', 'e', 1.0, 1.1, 0.6)], dur: 0.55, gain: 0.30 },
      phase: { segments: [seg('k', 'i', 0.5, 1.7, 2.1), seg('', 'i', 1.2, 2.0, 1.3)], dur: 1.1, gain: 0.34 },
      idle: { segments: [seg('t', 'i', 0.4, 1.8, 1.6)], dur: 0.14, gain: 0.14 },
    },
  },
  grove: {
    // Kodama and rootling: a whistle in a hollow trunk. Almost pure tone, one
    // wide resonance, no turbulence at all.
    timbre: 'child',
    voice: {
      voiced: 1.0, noise: 0.05, qScale: 0.8, formants: 2,
      pitchScale: 1.6, formantScale: 1.35, tilt: 1.2, wave: 'triangle', vib: 6.5, vibDepth: 34,
    },
    calls: {
      notice: { segments: [seg('', 'u', 1, 1.0, 1.45), seg('', 'i', 1.2, 1.5, 1.2)], dur: 0.6, gain: 0.30 },
      attack: { segments: [seg('p', 'o', 1, 1.2, 0.9)], dur: 0.25, gain: 0.30 },
      hurt: { segments: [seg('', 'i', 1, 1.6, 1.1)], dur: 0.3, gain: 0.32 },
      death: { segments: [seg('', 'u', 1, 1.2, 0.8), seg('', 'o', 1.8, 0.75, 0.4)], dur: 1.1, gain: 0.28 },
      phase: { segments: [seg('', 'u', 1, 0.9, 1.3), seg('', 'a', 2, 1.25, 0.7)], dur: 1.8, gain: 0.34 },
      idle: { segments: [seg('', 'u', 1, 1.0, 0.9)], dur: 0.7, gain: 0.14 },
    },
  },
  choir: {
    // Bellringers and ember priests chant rather than speak: long syllables,
    // narrow formants, and the vibrato of someone holding a note on purpose.
    timbre: 'herald',
    voice: {
      voiced: 1.0, noise: 0.12, qScale: 1.6, formants: 4,
      pitchScale: 0.8, tilt: 1.1, vib: 4.8, vibDepth: 20,
    },
    calls: {
      notice: { segments: [seg('', 'o', 1, 1.0, 1.0), seg('', 'a', 1.6, 1.19, 1.19)], dur: 1.2, gain: 0.36 },
      attack: { segments: [seg('l', 'a', 1, 1.0, 1.12)], dur: 0.6, gain: 0.34 },
      hurt: { segments: [seg('', 'e', 1, 1.3, 1.0)], dur: 0.4, gain: 0.36 },
      death: { segments: [seg('', 'o', 1, 1.0, 0.75), seg('', 'ax', 2, 0.7, 0.4)], dur: 1.8, gain: 0.34 },
      phase: { segments: [seg('', 'o', 1, 0.9, 1.0), seg('', 'a', 1.5, 1.19, 1.41), seg('', 'a', 2, 1.41, 0.9)], dur: 2.4, gain: 0.42 },
      idle: { segments: [seg('m', 'ux', 1, 0.95, 0.95)], dur: 1.0, gain: 0.14 },
    },
  },
};

/** Which throat each enemy archetype and boss speaks with. */
export const CREATURE_VOICE_OF = {
  bandit: 'brigand', bandit_archer: 'brigand', bandit_chief: 'brigand',
  husk: 'husk', husk_archer: 'husk', chainhusk: 'husk', flagellant: 'husk',
  ashwolf: 'beast', frostwolf: 'beast', cinderhound: 'beast',
  snowstalker: 'beast', mirestalker: 'beast', wolf_alpha: 'beast',
  wraith: 'wraith', hexbinder: 'wraith', wraith_lord: 'wraith', mirequeen: 'wraith',
  sentinel: 'construct', stoneeater: 'construct', stonecarl: 'construct',
  sentinel_captain: 'construct', ironsworn: 'construct',
  oathknight: 'soldier', spearman: 'soldier', shieldbearer: 'soldier',
  duelist: 'soldier', pyreclad: 'soldier', harpooner: 'soldier',
  stiltwalker: 'soldier', frostjarl: 'soldier',
  mireleech: 'swarm', ashcrow: 'swarm', emberwidow: 'swarm',
  kodama: 'grove', rootling: 'grove', warden: 'grove', rootfather: 'grove',
  bellringer: 'choir', emberpriest: 'choir', bellkeeper: 'choir',
  sunkenchoir: 'choir', ashking: 'choir', sovereign: 'choir',
  drake: 'drake',
};

function resolveTimbre(name, fallback) {
  const t = VOICE_TIMBRES[name] || VOICE_TIMBRES[fallback] || VOICE_TIMBRES.knight;
  return Object.assign({}, DEFAULT_TIMBRE, t);
}

function makeNoiseBuffer(ctx, seconds) {
  const len = Math.floor(ctx.sampleRate * seconds);
  const buf = ctx.createBuffer(1, len, ctx.sampleRate);
  const d = buf.getChannelData(0);
  for (let i = 0; i < len; i++) d[i] = Math.random() * 2 - 1;
  return buf;
}

/** Seconds an utterance will take, without building anything. */
function estimateDuration(plan, timbre) {
  const segs = plan.segments || [];
  if (plan.dur) return plan.dur + 0.2;
  let w = 0;
  for (const s of segs) w += (s.w || 1) + (s.pause || 0) * (timbre.rate || 6);
  return w / (timbre.rate || 6) + 0.2;
}

/**
 * Render an utterance plan into WebAudio nodes and schedule it.
 *
 * @param {AudioContext} ctx
 * @param {AudioNode} destination
 * @param {{segments: Array, dur?: number, gain?: number, press?: number,
 *          voiced?: number, noise?: number, growl?: number, growlDepth?: number,
 *          sub?: number, qScale?: number, formants?: number, jitter?: number,
 *          pitchScale?: number, formantScale?: number, tilt?: number}} plan
 * @param {object} [timbre]  a VOICE_TIMBRES entry (already merged with defaults)
 * @param {{when?: number, gain?: number, noiseBuffer?: AudioBuffer}} [opts]
 * @returns {{duration: number, stop: (when?: number) => void}|null}
 */
export function synthesizeVoice(ctx, destination, plan, timbre, opts = {}) {
  if (!ctx || !destination || !plan) return null;
  const segs = plan.segments || [];
  if (!segs.length) return null;

  const T = timbre && timbre.f0 ? timbre : resolveTimbre(null);
  const t0 = opts.when != null ? Math.max(opts.when, ctx.currentTime + 0.005) : ctx.currentTime + 0.01;
  const fScale = (T.formant || 1) * (plan.formantScale || 1);
  const f0Base = Math.max(24, (T.f0 || 120) * (plan.pitchScale || 1));
  const nForm = Math.max(1, Math.min(4, plan.formants || 4));
  const qScale = plan.qScale || 1;
  const press = plan.press != null ? plan.press : 0.5;
  const voicedAmt = plan.voiced != null ? plan.voiced : 1;
  const noiseAmt = Math.min(1.6, (plan.noise || 0) + (plan.breath || 0) + (T.breath || 0) * 0.7);
  const jitter = plan.jitter != null ? plan.jitter : 0.012 + (T.rough || 0) * 0.02;
  const level = (plan.gain != null ? plan.gain : 0.35) * (opts.gain != null ? opts.gain : 1) * (T.level || 1);

  // --- durations ---------------------------------------------------------
  const rate = T.rate || 6;
  let totalW = 0;
  for (const s of segs) totalW += s.w || 1;
  const scale = plan.dur ? plan.dur / (totalW / rate) : 1;
  const durs = segs.map((s) => Math.max(0.045, ((s.w || 1) / rate) * scale));
  let total = 0;
  for (let i = 0; i < durs.length; i++) total += durs[i] + (segs[i].pause || 0);
  const tail = 0.10 + total * 0.06;

  // --- graph -------------------------------------------------------------
  const amp = ctx.createGain();
  amp.gain.value = 0.0001;
  const tiltF = ctx.createBiquadFilter();
  tiltF.type = 'lowpass';
  // Pressure opens the spectrum: a shout is brighter than a word, not just louder.
  tiltF.frequency.value = Math.min(16000, (T.tilt || 3000) * (plan.tilt || 1) * (0.7 + press * 0.6));
  tiltF.Q.value = 0.4;
  amp.connect(tiltF);
  tiltF.connect(destination);

  const sum = ctx.createGain();
  sum.gain.value = 1;
  sum.connect(amp);

  const tract = ctx.createGain();   // everything that passes through the resonances
  tract.gain.value = 1;
  const bands = [];
  for (let k = 0; k < nForm; k++) {
    const bp = ctx.createBiquadFilter();
    bp.type = 'bandpass';
    const g = ctx.createGain();
    g.gain.value = 0.0001;
    tract.connect(bp); bp.connect(g); g.connect(sum);
    bands.push({ bp, g });
  }

  // Source: two sawtooths a few cents apart (fold asymmetry) plus an optional
  // sub an octave down for bodies too big to buzz at their own pitch.
  const voiceGain = ctx.createGain();
  voiceGain.gain.value = 0.0001;
  const growlIn = ctx.createGain();
  growlIn.gain.value = 1;
  voiceGain.connect(growlIn);
  growlIn.connect(tract);

  const wave = plan.wave || T.wave || 'sawtooth';
  const osc1 = ctx.createOscillator(); osc1.type = wave;
  const osc2 = ctx.createOscillator(); osc2.type = wave;
  osc2.detune.value = 8 + (T.rough || 0) * 34;
  const o2g = ctx.createGain(); o2g.gain.value = 0.42 + (T.rough || 0) * 0.25;
  osc1.connect(voiceGain);
  osc2.connect(o2g); o2g.connect(voiceGain);
  let sub = null;
  // A sub an octave down gives a big animal its body, but below ~30 Hz it is
  // headroom nobody can hear — phone speakers least of all.
  if (plan.sub && f0Base * 0.5 > 30) {
    sub = ctx.createOscillator();
    sub.type = 'sine';
    const sg = ctx.createGain(); sg.gain.value = plan.sub;
    sub.connect(sg); sg.connect(voiceGain);
  }

  // Aspiration runs through the tract, which is why a whisper still has vowels.
  const noiseSrc = ctx.createBufferSource();
  noiseSrc.buffer = opts.noiseBuffer || makeNoiseBuffer(ctx, 1.5);
  noiseSrc.loop = true;
  const aspFilt = ctx.createBiquadFilter();
  aspFilt.type = 'lowpass';
  aspFilt.frequency.value = 5000;
  const aspGain = ctx.createGain();
  aspGain.gain.value = 0.0001;
  noiseSrc.connect(aspFilt); aspFilt.connect(aspGain); aspGain.connect(tract);

  // Bursts and fricatives bypass the tract: the noise is made at the
  // constriction, in front of most of the resonances.
  const burstBP = ctx.createBiquadFilter();
  burstBP.type = 'bandpass';
  burstBP.frequency.value = 2000;
  burstBP.Q.value = 2;
  const burstGain = ctx.createGain();
  burstGain.gain.value = 0.0001;
  noiseSrc.connect(burstBP); burstBP.connect(burstGain); burstGain.connect(sum);

  let growlOsc = null;
  if (plan.growl) {
    const depth = Math.min(0.95, plan.growlDepth || 0.5);
    growlIn.gain.value = 1 - depth;
    growlOsc = ctx.createOscillator();
    growlOsc.type = 'sine';
    growlOsc.frequency.value = plan.growl;
    const gg = ctx.createGain();
    gg.gain.value = depth;
    growlOsc.connect(gg); gg.connect(growlIn.gain);
  }
  let vibOsc = null;
  if (T.vib) {
    vibOsc = ctx.createOscillator();
    vibOsc.type = 'sine';
    vibOsc.frequency.value = T.vib;
    const vg = ctx.createGain();
    vg.gain.value = T.vibDepth || 12;
    vibOsc.connect(vg);
    vg.connect(osc1.detune); vg.connect(osc2.detune);
  }

  // --- scheduling --------------------------------------------------------
  const setFormants = (when, targets, gains, ramp, damp) => {
    for (let k = 0; k < nForm; k++) {
      const f = Math.max(90, Math.min(ctx.sampleRate * 0.45, targets[k] * fScale));
      const bwHz = Math.max(24, (PHONEMES.ax.bw[k]) * fScale);
      const q = Math.max(0.35, Math.min(30, (f / bwHz) * qScale));
      const fp = bands[k].bp.frequency;
      const gp = bands[k].g.gain;
      const gv = Math.max(0.0002, gains[k] * damp);
      if (ramp > 0) {
        fp.linearRampToValueAtTime(f, when + ramp);
        gp.linearRampToValueAtTime(gv, when + ramp);
      } else {
        fp.setValueAtTime(f, when);
        gp.setValueAtTime(gv, when);
      }
      bands[k].bp.Q.setValueAtTime(q, when);
    }
  };
  const setF0 = (when, hz, ramp) => {
    const f = Math.max(24, hz);
    if (ramp > 0) {
      osc1.frequency.linearRampToValueAtTime(f, when + ramp);
      osc2.frequency.linearRampToValueAtTime(f, when + ramp);
      if (sub) sub.frequency.linearRampToValueAtTime(f * 0.5, when + ramp);
    } else {
      osc1.frequency.setValueAtTime(f, when);
      osc2.frequency.setValueAtTime(f, when);
      if (sub) sub.frequency.setValueAtTime(f * 0.5, when);
    }
  };

  const rest = PHONEMES.ax;
  setFormants(t0, rest.f, rest.g, 0, 0.5);
  setF0(t0, f0Base * (segs[0].f0a || 1), 0);
  voiceGain.gain.setValueAtTime(0.0001, t0);
  aspGain.gain.setValueAtTime(0.0001, t0);
  burstGain.gain.setValueAtTime(0.0001, t0);

  amp.gain.setValueAtTime(0.0001, t0);
  amp.gain.exponentialRampToValueAtTime(Math.max(0.0002, level), t0 + 0.02);

  let t = t0;
  for (let i = 0; i < segs.length; i++) {
    const s = segs[i];
    const v = PHONEMES[s.v] || PHONEMES.ax;
    const c = ARTICULATIONS[s.c] || ARTICULATIONS[''];
    const dur = durs[i];
    const cd = Math.min(c.dur || 0, dur * 0.45);
    const vStart = t + cd;
    const vDur = Math.max(0.035, dur - cd);
    const trans = Math.min(0.09, Math.max(0.035, vDur * 0.45));
    const segLevel = (s.level == null ? 1 : s.level);
    const vGain = voicedAmt * segLevel * (0.55 + press * 0.45);

    // --- the consonant: closure, turbulence, or a slide through a locus ---
    if (cd > 0) {
      if (c.locus) setFormants(t, c.locus, v.g, cd * 0.8, c.kind === 'nasal' ? (c.damp || 0.5) : 1);
      if (c.kind === 'stop') {
        // Silence, then the release: the click is the consonant.
        voiceGain.gain.setValueAtTime(Math.max(0.0002, vGain * (c.voiced || 0.02)), t);
        aspGain.gain.setValueAtTime(0.0001, t);
        burstBP.frequency.setValueAtTime(c.burst, vStart);
        burstBP.Q.setValueAtTime(c.bq || 2, vStart);
        burstGain.gain.setValueAtTime(0.0001, vStart - 0.002);
        burstGain.gain.linearRampToValueAtTime(c.level * segLevel, vStart + 0.004);
        burstGain.gain.exponentialRampToValueAtTime(0.0001, vStart + 0.032);
      } else if (c.kind === 'fric') {
        voiceGain.gain.setValueAtTime(Math.max(0.0002, vGain * (c.voiced || 0.03)), t);
        burstBP.frequency.setValueAtTime(c.band, t);
        burstBP.Q.setValueAtTime(c.bq || 2, t);
        burstGain.gain.setValueAtTime(0.0001, t);
        burstGain.gain.linearRampToValueAtTime(c.level * segLevel, t + cd * 0.35);
        burstGain.gain.linearRampToValueAtTime(0.0001, vStart + 0.012);
      } else if (c.kind === 'asp') {
        voiceGain.gain.setValueAtTime(Math.max(0.0002, vGain * 0.08), t);
        aspGain.gain.setValueAtTime(0.0001, t);
        aspGain.gain.linearRampToValueAtTime(c.level * segLevel, t + cd * 0.4);
      } else {
        // nasal / approximant: voicing never stops
        voiceGain.gain.setValueAtTime(Math.max(0.0002, vGain * (c.voiced || 0.7)), t);
      }
    }

    // --- the vowel --------------------------------------------------------
    setFormants(vStart, v.f, v.g, trans, 1);
    voiceGain.gain.linearRampToValueAtTime(Math.max(0.0002, vGain), vStart + Math.min(0.03, trans));
    aspGain.gain.linearRampToValueAtTime(Math.max(0.0001, noiseAmt * segLevel * 0.30), vStart + trans);

    // Pitch: the contour of the line, plus the small jitter that stops a
    // synthesised vowel sounding like a test tone.
    const a = f0Base * (s.f0a || 1) * (1 + (Math.random() - 0.5) * jitter);
    const b = f0Base * (s.f0b || s.f0a || 1) * (1 + (Math.random() - 0.5) * jitter);
    setF0(t, a, cd > 0 ? cd * 0.9 : 0.012);
    setF0(vStart, b, vDur * 0.92);

    // Each syllable falls away a little before the next one starts.
    const end = t + dur;
    voiceGain.gain.linearRampToValueAtTime(Math.max(0.0002, vGain * 0.62), end);
    t = end + (s.pause || 0);
    if (s.pause) {
      voiceGain.gain.linearRampToValueAtTime(0.0002, end + Math.min(0.05, s.pause));
      aspGain.gain.linearRampToValueAtTime(0.0001, end + Math.min(0.05, s.pause));
    }
  }

  const endAt = t0 + total;
  voiceGain.gain.linearRampToValueAtTime(0.0001, endAt + tail * 0.7);
  aspGain.gain.linearRampToValueAtTime(0.0001, endAt + tail * 0.9);
  amp.gain.setValueAtTime(Math.max(0.0002, level), endAt);
  amp.gain.exponentialRampToValueAtTime(0.0001, endAt + tail);

  const stopAt = endAt + tail + 0.05;
  osc1.start(t0); osc2.start(t0); noiseSrc.start(t0);
  if (sub) sub.start(t0);
  if (growlOsc) growlOsc.start(t0);
  if (vibOsc) vibOsc.start(t0);
  osc1.stop(stopAt); osc2.stop(stopAt); noiseSrc.stop(stopAt);
  if (sub) sub.stop(stopAt);
  if (growlOsc) growlOsc.stop(stopAt);
  if (vibOsc) vibOsc.stop(stopAt);

  let stopped = false;
  return {
    duration: total + tail,
    stop(when) {
      if (stopped) return;
      stopped = true;
      const w = Math.max(ctx.currentTime, when || ctx.currentTime);
      try {
        amp.gain.cancelScheduledValues(w);
        amp.gain.setValueAtTime(Math.max(0.0002, amp.gain.value), w);
        amp.gain.exponentialRampToValueAtTime(0.0001, w + 0.06);
        osc1.stop(w + 0.08); osc2.stop(w + 0.08); noiseSrc.stop(w + 0.08);
        if (sub) sub.stop(w + 0.08);
        if (growlOsc) growlOsc.stop(w + 0.08);
        if (vibOsc) vibOsc.stop(w + 0.08);
      } catch (e) { /* already stopped */ }
    },
  };
}

// ---------------------------------------------------------------------------
//  Turning a written line into something a person could be saying
//
//  Deliberately not Japanese. Synthesised speech that is almost words is worse
//  than speech that is clearly not words, so this uses one invented phonology
//  for everybody and lets prosody carry the meaning — the length of the line,
//  where its clauses break, and whether it ends in 。, ？, ！ or ……
//
//  Everything is derived from the text by hash, so a line always sounds the
//  same, and a longer line takes longer to say.
// ---------------------------------------------------------------------------

const V_ORDER = ['a', 'i', 'ux', 'e', 'o', 'a', 'ax', 'u', 'ae', 'i', 'o', 'a'];
const C_ORDER = ['', 'k', 't', 'm', 'n', 's', 'h', 'r', '', 'w', 'y', 'sh',
  'k', 'ts', 'g', 'd', 'n', 'ch', 'z', 'r', 'm', 'p', 'b', 'f'];

const PAUSE_MARKS = '、,';
const STOP_MARKS = '。.！!？?\n';
const SKIP_MARKS = '「」『』（）()…―ー・ 　\t"\'';

function hash32(str, seed) {
  let h = (seed >>> 0) || 0x811c9dc5;
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i);
    h = Math.imul(h, 16777619) >>> 0;
  }
  return h >>> 0;
}

/**
 * Build an utterance plan from a written line.
 * @param {string} text
 * @param {object} [timbre]  resolved timbre; only its rate is consulted here
 * @returns {{segments: Array, gain: number, press: number}}
 */
export function utteranceFromText(text, timbre) {
  const T = timbre && timbre.f0 ? timbre : resolveTimbre(null);
  const src = String(text || '');
  const segments = [];

  // Split into clauses, keeping the mark that ended each one: the mark is the
  // only thing here that knows whether the speaker asked or concluded.
  const clauses = [];
  let buf = '';
  for (let i = 0; i < src.length; i++) {
    const ch = src[i];
    if (STOP_MARKS.indexOf(ch) >= 0) { clauses.push({ text: buf, mark: ch }); buf = ''; }
    else if (PAUSE_MARKS.indexOf(ch) >= 0) { clauses.push({ text: buf, mark: ch }); buf = ''; }
    else buf += ch;
  }
  if (buf.trim().length) clauses.push({ text: buf, mark: '' });
  if (!clauses.length) clauses.push({ text: src, mark: '' });

  const hesitant = src.indexOf('……') >= 0;
  // A long paragraph must take longer than a short line, but nobody will sit
  // through a hundred syllables of murmur, so the total saturates here.
  const MAX_SYLLABLES = 16;
  let spoken = 0;
  let truncated = false;
  for (let ci = 0; ci < clauses.length && spoken < MAX_SYLLABLES; ci++) {
    const cl = clauses[ci];
    let body = '';
    for (let i = 0; i < cl.text.length; i++) {
      if (SKIP_MARKS.indexOf(cl.text[i]) < 0) body += cl.text[i];
    }
    if (!body.length) continue;

    // Syllable count grows with the clause but saturates: a hundred-character
    // sentence should take longer than a ten-character one without taking ten
    // times as long, because nobody would sit through that.
    const n = Math.max(1, Math.min(9, Math.round(1 + Math.sqrt(body.length) * 1.25)));
    const seed = hash32(body, 0x9e3779b1 ^ (ci * 2654435761));
    const question = cl.mark === '？' || cl.mark === '?';
    const bang = cl.mark === '！' || cl.mark === '!';
    const comma = PAUSE_MARKS.indexOf(cl.mark) >= 0;

    for (let j = 0; j < n && spoken < MAX_SYLLABLES; j++, spoken++) {
      const h = hash32(body, seed ^ Math.imul(j + 1, 0x85ebca6b));
      const c = C_ORDER[h % C_ORDER.length];
      const v = V_ORDER[(h >>> 9) % V_ORDER.length];
      const u = n > 1 ? j / (n - 1) : 0;

      // Declination — pitch drifts down across a clause — with an accent on
      // whichever syllables the text's own hash marks, so the same line always
      // lands its stresses in the same places.
      let base = 1.06 - u * 0.20;
      if ((h >>> 20) & 1) base += 0.11;
      if (bang && j === 0) base += 0.22;
      if (question && j >= n - 2) base += 0.18 + u * 0.22;
      if (hesitant) base -= 0.06;
      const next = j === n - 1
        ? (question ? base + 0.26 : comma ? base + 0.04 : base - 0.16)
        : base - 0.05;

      const w = (0.8 + ((h >>> 3) & 7) / 14) * (hesitant ? 1.15 : 1) * (bang ? 0.88 : 1);
      const level = 1 - u * 0.12 - (hesitant ? 0.1 : 0);
      const s = seg(c, v, w, base, next, level);
      if (j === n - 1) {
        s.pause = comma ? 0.13 : cl.mark ? 0.20 : 0.08;
        if (hesitant && ci === 0) s.pause += 0.12;
      }
      segments.push(s);
      if (spoken + 1 >= MAX_SYLLABLES && (j < n - 1 || ci < clauses.length - 1)) truncated = true;
    }
  }

  if (!segments.length) segments.push(seg('h', 'ax', 1, 1.0, 0.85));
  if (truncated) {
    // The cap cut us off mid-clause. Land the pitch anyway — a speaker who
    // stops on a level tone sounds like a tape running out.
    const last = segments[segments.length - 1];
    last.pause = 0;
    last.f0b = last.f0a * 0.80;
  }
  return {
    segments,
    gain: 0.30,
    press: hesitant ? 0.30 : 0.48,
    breath: hesitant ? 0.2 : 0,
    rate: T.rate,
  };
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
