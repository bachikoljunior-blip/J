// ============================================================================
//  renderer.js — frame orchestration, atmosphere and post-processing.
//
//  Frame order:
//    1. shadow pass    (terrain + shadow-casting instances, from the sun)
//    2. opaque pass    (terrain, instances, grass)  -> HDR-ish render target
//    3. sky            (depth-tested, so it only fills background pixels)
//    4. water          (alpha blended, depth written)
//    5. particles      (alpha then additive, depth tested, no depth write)
//    6. post           (bright extract -> separable blur -> ACES composite)
//
//  The atmosphere model is a hand-tuned key-framed day/night cycle rather than
//  a physical sky. Physical models are prettier in stills; keyframes let the
//  dawn actually look like the dawn you want at the moment the player crests a
//  hill, which matters more.
// ============================================================================

import {
  TERRAIN_VS, TERRAIN_FS, INSTANCE_VS, INSTANCE_FS, GRASS_VS, GRASS_FS,
  SHADOW_INSTANCE_VS, SHADOW_TERRAIN_VS, SHADOW_FS, SKY_VS, SKY_FS,
  WATER_VS, WATER_FS, PARTICLE_VS, PARTICLE_FS,
  FULLSCREEN_VS, BRIGHT_FS, BLUR_FS, COMPOSITE_FS, AO_FS, AO_BLUR_FS, WORLD_MASK_FS,
} from './shaders.js';
import {
  m4, m4perspective, m4lookAt, m4ortho, m4mul, m4invert,
  makeFrustum, frustumFromMatrix, v3, v3sub, v3norm, v3cross,
  clamp, lerp, saturate, TAU,
} from '../core/math.js';
import { Noise2D } from '../core/rng.js';
import { buildTextures } from './textures.js';

// ---------------------------------------------------------------------------
//  Atmosphere keyframes: [hour, sunColor, skyTop, skyHorizon, ground, fog, fogSun, exposure]
// ---------------------------------------------------------------------------

export const SKY_KEYS = [
  { h: 0.0, sun: [0.20, 0.22, 0.32], top: [0.038, 0.050, 0.088], hor: [0.090, 0.100, 0.140], gnd: [0.058, 0.060, 0.072], fog: [0.090, 0.100, 0.135], fogSun: [0.16, 0.18, 0.26], amb: 0.52, exposure: 1.62 },
  { h: 4.6, sun: [0.26, 0.27, 0.36], top: [0.055, 0.072, 0.135], hor: [0.170, 0.150, 0.175], gnd: [0.075, 0.076, 0.084], fog: [0.160, 0.150, 0.175], fogSun: [0.34, 0.26, 0.28], amb: 0.56, exposure: 1.50 },
  { h: 6.2, sun: [1.22, 0.58, 0.31], top: [0.120, 0.190, 0.360], hor: [0.720, 0.420, 0.290], gnd: [0.150, 0.130, 0.120], fog: [0.560, 0.390, 0.320], fogSun: [1.20, 0.62, 0.34], amb: 0.55, exposure: 1.10 },
  { h: 8.0, sun: [1.12, 0.90, 0.68], top: [0.180, 0.320, 0.580], hor: [0.640, 0.640, 0.640], gnd: [0.230, 0.220, 0.200], fog: [0.620, 0.660, 0.700], fogSun: [1.05, 0.88, 0.70], amb: 0.80, exposure: 0.92 },
  { h: 12.0, sun: [1.10, 1.05, 0.94], top: [0.190, 0.370, 0.700], hor: [0.660, 0.740, 0.840], gnd: [0.300, 0.300, 0.280], fog: [0.640, 0.720, 0.820], fogSun: [1.00, 0.96, 0.86], amb: 1.00, exposure: 0.86 },
  { h: 16.5, sun: [1.14, 0.95, 0.73], top: [0.180, 0.330, 0.640], hor: [0.700, 0.660, 0.620], gnd: [0.280, 0.260, 0.230], fog: [0.660, 0.660, 0.680], fogSun: [1.10, 0.90, 0.66], amb: 0.86, exposure: 0.90 },
  { h: 18.6, sun: [1.38, 0.53, 0.25], top: [0.140, 0.180, 0.340], hor: [0.860, 0.400, 0.230], gnd: [0.170, 0.130, 0.110], fog: [0.620, 0.360, 0.270], fogSun: [1.45, 0.55, 0.24], amb: 0.52, exposure: 1.10 },
  { h: 20.2, sun: [0.48, 0.36, 0.40], top: [0.060, 0.075, 0.140], hor: [0.240, 0.165, 0.195], gnd: [0.090, 0.086, 0.094], fog: [0.225, 0.180, 0.205], fogSun: [0.54, 0.32, 0.30], amb: 0.55, exposure: 1.48 },
  { h: 24.0, sun: [0.20, 0.22, 0.32], top: [0.038, 0.050, 0.088], hor: [0.090, 0.100, 0.140], gnd: [0.058, 0.060, 0.072], fog: [0.090, 0.100, 0.135], fogSun: [0.16, 0.18, 0.26], amb: 0.52, exposure: 1.62 },
];

/** Steady-state values each weather type crossfades toward. */
const WEATHER_TARGETS = {
  clear: { rain: 0, cloud: 0.30, fog: 0, wind: 0.35 },
  overcast: { rain: 0, cloud: 0.82, fog: 0.25, wind: 0.55 },
  rain: { rain: 1, cloud: 0.95, fog: 0.5, wind: 0.75 },
  storm: { rain: 1.6, cloud: 1.0, fog: 0.7, wind: 1.5 },
  fog: { rain: 0, cloud: 0.6, fog: 1.5, wind: 0.2 },
  snow: { rain: 0.4, cloud: 0.9, fog: 0.6, wind: 0.5 },
  ash: { rain: 0.3, cloud: 0.75, fog: 0.8, wind: 0.4 },
};

function lerpArr(a, b, t) {
  return [lerp(a[0], b[0], t), lerp(a[1], b[1], t), lerp(a[2], b[2], t)];
}

export function sampleSky(hour) {
  hour = ((hour % 24) + 24) % 24;
  let i = 0;
  while (i < SKY_KEYS.length - 2 && SKY_KEYS[i + 1].h <= hour) i++;
  const a = SKY_KEYS[i], b = SKY_KEYS[i + 1];
  const t = clamp((hour - a.h) / Math.max(b.h - a.h, 0.0001), 0, 1);
  const s = t * t * (3 - 2 * t);
  return {
    sun: lerpArr(a.sun, b.sun, s),
    top: lerpArr(a.top, b.top, s),
    hor: lerpArr(a.hor, b.hor, s),
    gnd: lerpArr(a.gnd, b.gnd, s),
    fog: lerpArr(a.fog, b.fog, s),
    fogSun: lerpArr(a.fogSun, b.fogSun, s),
    amb: lerp(a.amb, b.amb, s),
    exposure: lerp(a.exposure, b.exposure, s),
  };
}

// ---------------------------------------------------------------------------

export const QUALITY = {
  low: {
    name: '低', resScale: 0.62, shadowSize: 1024, shadowRange: 55, viewDistance: 380,
    grassRadius: 26, grassCell: 1.05, grassBlades: 1, bloom: false, propDistance: 260,
    particleCap: 700, aberration: 0.0, detailFade: 55, cheapSurface: true,
    ao: 0, aoRadius: 0.7,
  },
  medium: {
    name: '中', resScale: 0.80, shadowSize: 1024, shadowRange: 70, viewDistance: 450,
    grassRadius: 38, grassCell: 0.90, grassBlades: 1, bloom: true, propDistance: 300,
    particleCap: 1400, aberration: 0.010, detailFade: 95, cheapSurface: false,
    ao: 0.70, aoRadius: 0.85,
  },
  high: {
    name: '高', resScale: 1.0, shadowSize: 2048, shadowRange: 88, viewDistance: 620,
    grassRadius: 52, grassCell: 0.72, grassBlades: 2, bloom: true, propDistance: 420,
    particleCap: 2600, aberration: 0.016, detailFade: 150, cheapSurface: false,
    ao: 0.82, aoRadius: 1.0,
  },
};

export class Camera {
  constructor() {
    this.pos = v3(0, 3, 0);
    this.target = v3(0, 1.6, 1);
    this.up = v3(0, 1, 0);
    this.fov = 60;
    this.near = 0.15;
    this.far = 1400;
    this.view = m4();
    this.proj = m4();
    this.viewProj = m4();
    this.invViewProj = m4();
    this.frustum = makeFrustum();
    this.right = v3(1, 0, 0);
    this.upVec = v3(0, 1, 0);
    this.forward = v3(0, 0, 1);
    this._fwd = v3();
  }

  update(aspect) {
    m4perspective(this.proj, this.fov * Math.PI / 180, aspect, this.near, this.far);
    m4lookAt(this.view, this.pos, this.target, this.up);
    m4mul(this.viewProj, this.proj, this.view);
    m4invert(this.invViewProj, this.viewProj);
    frustumFromMatrix(this.frustum, this.viewProj);
    // Basis vectors, read straight out of the view matrix.
    this.right.x = this.view[0]; this.right.y = this.view[4]; this.right.z = this.view[8];
    this.upVec.x = this.view[1]; this.upVec.y = this.view[5]; this.upVec.z = this.view[9];
    v3norm(this.forward, v3sub(this._fwd, this.target, this.pos));
  }
}

export class Renderer {
  constructor(glw, quality = 'medium') {
    this.glw = glw;
    const gl = glw.gl;

    this._shadowDefine = glw.depthTexture ? '' : '#define SHADOW_PACKED 1\n';
    // Without a renderable half-float target the opaque passes have to
    // compress their output into 8 bits and post has to expand it again.
    this._sceneDefine = glw.halfFloatColor ? '' : '#define LDR_SCENE 1\n';
    this._cheapSurface = !!(QUALITY[quality] || QUALITY.medium).cheapSurface;
    const D = (src) => this._define(src);

    this.progTerrain = glw.program(TERRAIN_VS, D(TERRAIN_FS), 'terrain');
    this.progInstance = glw.program(INSTANCE_VS, D(INSTANCE_FS), 'instance');
    this.progGrass = glw.program(GRASS_VS, D(GRASS_FS), 'grass');
    this.progShadowInst = glw.program(SHADOW_INSTANCE_VS, D(SHADOW_FS), 'shadowInst');
    this.progShadowTerr = glw.program(SHADOW_TERRAIN_VS, D(SHADOW_FS), 'shadowTerr');
    const S = (src) => this._define(src, { shadow: false });
    this.progSky = glw.program(SKY_VS, S(SKY_FS), 'sky');
    this.progWater = glw.program(WATER_VS, S(WATER_FS), 'water');
    this.progParticle = glw.program(PARTICLE_VS, S(PARTICLE_FS), 'particle');
    this.progBright = glw.program(FULLSCREEN_VS, S(BRIGHT_FS), 'bright');
    this.progBlur = glw.program(FULLSCREEN_VS, BLUR_FS, 'blur');
    this.progAO = glw.program(FULLSCREEN_VS, AO_FS, 'ao');
    this.progAOBlur = glw.program(FULLSCREEN_VS, AO_BLUR_FS, 'aoBlur');
    this.progWorldMask = glw.program(FULLSCREEN_VS, WORLD_MASK_FS, 'worldMask');
    this.progComposite = glw.program(FULLSCREEN_VS, S(COMPOSITE_FS), 'composite');

    this.quadBuf = glw.vbo(new Float32Array([-1, -1, 3, -1, -1, 3]));

    this.cloudTex = this._makeCloudTexture();
    // Surfaces. Built once here rather than lazily: it costs ~150ms and the
    // loading screen is the only place in the game where that is free.
    this.textures = buildTextures(glw, { quality: quality === 'low' ? 'low' : 'medium' });

    this.camera = new Camera();
    this.lightMatrix = m4();
    this._lightView = m4();
    this._lightProj = m4();
    this._lightEye = v3();
    this._lightTarget = v3();
    this._lightUp = v3(0, 1, 0);

    // --- atmosphere state ---------------------------------------------------
    this.hour = 9.0;
    this.dayLengthSeconds = 900;   // 15 real minutes per in-game day
    this.timeFlow = 1;
    this.sunDir = v3(0.4, 0.7, 0.3);
    this.moonDir = v3(-0.4, -0.7, -0.3);
    this.sky = sampleSky(this.hour);
    this.night = 0;

    this.weather = {
      type: 'clear',      // clear | overcast | rain | storm | fog | snow | ash
      wetness: 0,
      rainIntensity: 0,
      fogBoost: 0,
      cloudCover: 0.35,
      windX: 0.3,
      windZ: 0.1,
      target: 'clear',
      timer: 90,
    };

    this.pointLightData = new Float32Array(16);
    this.pointColorData = new Float32Array(12);
    this._lightScratch = [];

    this.exposure = 1.0;
    this.saturation = 1.05;
    this.contrast = 1.18;
    this.tint = [1, 1, 1];
    this.damageFlash = 0;
    this.deathFade = 0;
    this.bloomStrength = 0.55;
    this.vignette = 0.42;

    this.setQuality(quality);
    this._targetsFor(1, 1);

    gl.enable(gl.DEPTH_TEST);
    gl.enable(gl.CULL_FACE);
    gl.cullFace(gl.BACK);
  }

  /** Prefix a fragment shader with the compile-time switches it needs. */
  _define(src, { shadow = true, scene = true } = {}) {
    let d = '';
    if (shadow) d += this._shadowDefine;
    if (scene) d += this._sceneDefine;
    if (this._cheapSurface) d += '#define CHEAP_SURFACE 1\n';
    return d ? src.replace('precision highp float;', `precision highp float;\n${d}`) : src;
  }

  setQuality(name) {
    const q = QUALITY[name] || QUALITY.medium;
    this.qualityName = QUALITY[name] ? name : 'medium';
    this.quality = q;
    if (this.shadow && this.shadow.size !== q.shadowSize) {
      this.shadow = null;
    }
    if (!this.shadow) this.shadow = this.glw.createShadowTarget(q.shadowSize);
    // Triplanar sampling is a compile-time switch, so dropping to the cheap
    // path means relinking. Only happens when the player changes the setting.
    const cheap = !!q.cheapSurface;
    if (this.progTerrain && cheap !== this._cheapSurface) {
      this._cheapSurface = cheap;
      this.progTerrain = this.glw.program(TERRAIN_VS, this._define(TERRAIN_FS), 'terrain');
      this.progInstance = this.glw.program(INSTANCE_VS, this._define(INSTANCE_FS), 'instance');
      this.progGrass = this.glw.program(GRASS_VS, this._define(GRASS_FS), 'grass');
    }
    this._sizeDirty = true;
  }

  _makeCloudTexture() {
    // A tiling fbm texture, used both for cloud shadows on the ground and as a
    // cheap detail source. 256px is plenty once it is stretched over hundreds
    // of metres.
    const size = 256;
    const cvs = document.createElement('canvas');
    cvs.width = cvs.height = size;
    const ctx = cvs.getContext('2d');
    const img = ctx.createImageData(size, size);
    const noise = new Noise2D(1337);
    for (let y = 0; y < size; y++) {
      for (let x = 0; x < size; x++) {
        // Tile by blending four wrapped samples.
        const fx = x / size, fy = y / size;
        let v = 0, w = 0;
        for (let oy = 0; oy < 2; oy++) {
          for (let ox = 0; ox < 2; ox++) {
            const wx = (fx + ox) * 4, wy = (fy + oy) * 4;
            const weight = (ox ? fx : 1 - fx) * (oy ? fy : 1 - fy);
            v += (noise.fbm(wx, wy, 4) * 0.5 + 0.5) * weight;
            w += weight;
          }
        }
        v = w > 0 ? v / w : 0.5;
        const c = Math.round(clamp(v, 0, 1) * 255);
        const i = (y * size + x) * 4;
        img.data[i] = c; img.data[i + 1] = c; img.data[i + 2] = c; img.data[i + 3] = 255;
      }
    }
    ctx.putImageData(img, 0, 0);
    return this.glw.textureFromCanvas(cvs, { mip: true, wrap: this.glw.gl.REPEAT });
  }

  resize(width, height) {
    const q = this.quality;
    const scale = q.resScale * (this.dynamicScale || 1);
    const w = Math.max(160, Math.round(width * scale));
    const h = Math.max(120, Math.round(height * scale));
    if (this.scene && this.scene.width === w && this.scene.height === h) return;
    this._targetsFor(w, h);
  }

  _targetsFor(w, h) {
    // Recreating the targets throws away the depth that the world mask reads.
    // Anything measured before the next scene render is measuring a cleared
    // buffer — and reporting that as a number rather than as "not yet" cost
    // most of a day.
    this._sceneRendered = false;
    const glw = this.glw;
    const gl = glw.gl;
    if (this.scene) {
      gl.deleteFramebuffer(this.scene.fbo);
      gl.deleteTexture(this.scene.color);
      if (this.scene.depthBuf) gl.deleteRenderbuffer(this.scene.depthBuf);
      if (this.scene.depthTex) gl.deleteTexture(this.scene.depthTex);
    }
    if (this.bloomA) {
      for (const rt of [this.bloomA, this.bloomB]) {
        gl.deleteFramebuffer(rt.fbo);
        gl.deleteTexture(rt.color);
      }
    }
    if (this.aoA) {
      for (const rt of [this.aoA, this.aoB]) {
        gl.deleteFramebuffer(rt.fbo);
        gl.deleteTexture(rt.color);
      }
    }
    // HDR where the hardware allows it, and a sampleable depth texture so
    // later passes can reason about scene geometry.
    this.scene = glw.createRenderTarget(w, h, { depth: true, hdr: true, sampleDepth: true });
    const bw = Math.max(32, w >> 2), bh = Math.max(32, h >> 2);
    this.bloomA = glw.createRenderTarget(bw, bh, { depth: false, hdr: true });
    this.bloomB = glw.createRenderTarget(bw, bh, { depth: false, hdr: true });
    // Occlusion runs at half resolution: it is a low-frequency signal and the
    // blur that follows would throw away the extra detail anyway.
    const aw = Math.max(64, w >> 1), ah = Math.max(64, h >> 1);
    this.aoA = glw.createRenderTarget(aw, ah, { depth: false });
    this.aoB = glw.createRenderTarget(aw, ah, { depth: false });
    this._sizeDirty = false;
  }

  // -------------------------------------------------------------------------
  //  Atmosphere
  // -------------------------------------------------------------------------

  updateAtmosphere(dt) {
    this.hour = (this.hour + (dt / this.dayLengthSeconds) * 24 * this.timeFlow) % 24;
    const sky = sampleSky(this.hour);
    this.sky = sky;

    // Sun path: solar geometry at a temperate latitude, not a circle through
    // the zenith.
    //
    // The old path put the noon sun 78 degrees up, which is close to the worst
    // possible key light for an open world. When the sun is nearly overhead the
    // ground's own normal *is* the light vector, d(N·L)/d(tilt) goes to zero,
    // and every bank, hollow, rut and normal map on the ground stops shading —
    // the land turns into a painted plane between noon and mid-afternoon.
    // Landing the sun at 52 degrees instead makes the same geometry model
    // itself all day: slopes facing different ways separate in value, shadows
    // have length, and a low-frequency landform reads as form rather than as
    // colour. No open-world game lights its world from the zenith.
    //
    // hour angle, zero at solar noon; sunrise and sunset stay at 6 and 18 so
    // the atmosphere keyframes still line up with the horizon crossings.
    const hourAngle = ((this.hour - 12) / 24) * TAU;
    const cosH = Math.cos(hourAngle), sinH = Math.sin(hourAngle);
    const LAT = 0.66;   // ~38 degrees, so the noon sun tops out near 52
    this.sunDir.x = -sinH;                  // rises toward +x, sets toward -x
    this.sunDir.y = cosH * Math.cos(LAT);
    this.sunDir.z = cosH * Math.sin(LAT);   // and leans to +z, the pole side
    v3norm(this.sunDir);
    this.moonDir.x = -this.sunDir.x;
    this.moonDir.y = -this.sunDir.y;
    this.moonDir.z = -this.sunDir.z;

    this.night = 1 - saturate((this.sunDir.y + 0.16) / 0.30);

    // Thin air at altitude: less atmosphere overhead means a deeper zenith and
    // weaker haze. Above the snowline this is what stops a white peak under a
    // white sky from collapsing into one flat tone.
    const alt = saturate((this.camera.pos.y - 55) / 190);
    if (alt > 0.001) {
      const deepen = 1 - 0.52 * alt;
      const hazeCut = 1 - 0.30 * alt;
      sky.top = [sky.top[0] * deepen * 0.94, sky.top[1] * deepen * 0.97, sky.top[2] * deepen];
      sky.hor = [sky.hor[0] * hazeCut, sky.hor[1] * hazeCut, sky.hor[2] * (1 - 0.18 * alt)];
      sky.fog = [sky.fog[0] * hazeCut, sky.fog[1] * hazeCut, sky.fog[2] * hazeCut];
      // And the eye stops down on a snowfield — without this the peaks blow
      // out to paper white and lose every trace of form.
      sky.exposure *= 1 - 0.26 * alt;
    }

    // When the sun is below the horizon, light the world from the moon.
    //
    // A dim, near-omnidirectional wash is not what a clear night looks like,
    // and it is what a weak key plus a soft shadow adds up to: the moon stops
    // being a light and becomes a uniform grey, geometry and normal maps have
    // nothing to shade against, and a rock ridge at midnight comes out flatter
    // than the same ridge at noon. There is no lit atmosphere at night to
    // scatter moonlight into a fill, so the moon is in fact a *harder* key than
    // the sun despite being far weaker — a lit side, a dark side and a crisp
    // terminator are the whole of what gives a moonlit landscape its form.
    //
    // Ramping both with the depth of night also keeps the handover at dusk from
    // stepping: the moon is at its weakest exactly where it takes over.
    if (this.sunDir.y < 0.02) {
      const deep = saturate((-this.sunDir.y - 0.02) / 0.26);
      const k = lerp(0.98, 1.46, deep);
      this.lightDir = this.moonDir;
      this.lightColor = [0.36 * k, 0.44 * k, 0.68 * k];
      this.shadowStrength = lerp(0.62, 0.90, deep);
    } else {
      this.lightDir = this.sunDir;
      this.lightColor = sky.sun;
      this.shadowStrength = 0.82;
    }

    this._updateWeather(dt);
  }

  _updateWeather(dt) {
    const w = this.weather;
    w.timer -= dt;
    if (w.timer <= 0) {
      const roll = Math.random();
      w.target = roll < 0.38 ? 'clear'
        : roll < 0.60 ? 'overcast'
          : roll < 0.80 ? 'rain'
            : roll < 0.88 ? 'fog'
              : roll < 0.95 ? 'storm' : 'clear';
      w.timer = 90 + Math.random() * 180;
    }
    if (this.forcedWeather) w.target = this.forcedWeather;

    const t = WEATHER_TARGETS[w.target] || WEATHER_TARGETS.clear;
    // An override arrives fully formed. Weather crossfades over a ~4.5 s time
    // constant, which is right for a sky changing on its own and wrong for a
    // caller that has said "it is storming here": the tools set forcedWeather
    // and then sample after about two and a half seconds, so before this every
    // forced scene was measured less than half way to the weather it asked for
    // — and, because the states settle in sequence, carrying whatever the
    // previous scene left behind. The Cinderwaste sample, nominally clear, was
    // reading at roughly cloud 0.5 because the storm shot ran before it. That
    // did not matter while the cloud layer was a flat wash; now that cover
    // drives both the deck and its brightness, it decides the frame.
    if (this.forcedWeather && this.forcedWeather !== this._forcedApplied) {
      this._forcedApplied = this.forcedWeather;
      w.rainIntensity = t.rain;
      w.cloudCover = t.cloud;
      w.fogBoost = t.fog;
      w.windX = t.wind * 0.8;
      w.windZ = t.wind * 0.35;
      w.wetness = t.rain > 0.15 ? 1 : 0;
    } else if (!this.forcedWeather) {
      this._forcedApplied = null;
    }
    const k = 1 - Math.exp(-dt * 0.22);
    w.rainIntensity = lerp(w.rainIntensity, t.rain, k);
    w.cloudCover = lerp(w.cloudCover, t.cloud, k);
    w.fogBoost = lerp(w.fogBoost, t.fog, k);
    const windTarget = t.wind;
    w.windX = lerp(w.windX, windTarget * 0.8, k);
    w.windZ = lerp(w.windZ, windTarget * 0.35, k);
    w.type = w.target;

    const wetTarget = w.rainIntensity > 0.15 ? 1 : 0;
    w.wetness = lerp(w.wetness, wetTarget, dt * (wetTarget ? 0.25 : 0.08));
  }

  /** Fog density combines the time-of-day base with the current weather. */
  get fogDensity() {
    const base = 0.0016 + this.night * 0.0011;
    return base * (1 + this.weather.fogBoost * 1.9);
  }

  // -------------------------------------------------------------------------
  //  Uniform blocks
  // -------------------------------------------------------------------------

  _applyCommon(prog, time) {
    const glw = this.glw;
    const sky = this.sky;
    const amb = sky.amb;
    glw.u3f(prog, 'uSunDir', this.lightDir.x, this.lightDir.y, this.lightDir.z);
    glw.u3f(prog, 'uSunColor', this.lightColor[0], this.lightColor[1], this.lightColor[2]);
    // Sky ambient used to be strong enough to tint brown bark blue-grey. It is
    // now balanced against a stronger ground bounce so materials keep their hue.
    glw.u3f(prog, 'uSkyColor',
      sky.top[0] * 0.86 * amb + 0.030, sky.top[1] * 0.86 * amb + 0.035, sky.top[2] * 0.86 * amb + 0.048);
    // The horizon band as irradiance rather than as sky radiance. The ~0.6 is
    // roughly the share of a surface's cosine-weighted hemisphere that band
    // covers; the slight per-channel tilt is the extra air a horizon ray goes
    // through, which reddens it. The ambient model had no term for this band at
    // all, which meant the brightest part of the sky at dawn and dusk lit
    // nothing in the world below it.
    glw.u3f(prog, 'uHorizonColor',
      sky.hor[0] * 0.62 * amb, sky.hor[1] * 0.60 * amb, sky.hor[2] * 0.58 * amb);
    glw.u3f(prog, 'uGroundColor',
      sky.gnd[0] * 1.55 * amb, sky.gnd[1] * 1.50 * amb, sky.gnd[2] * 1.38 * amb);
    glw.u3f(prog, 'uFogColor', sky.fog[0], sky.fog[1], sky.fog[2]);
    glw.u3f(prog, 'uFogSunColor', sky.fogSun[0], sky.fogSun[1], sky.fogSun[2]);
    glw.u2f(prog, 'uFogParams', this.fogDensity, 0.012);
    glw.u3f(prog, 'uCameraPos', this.camera.pos.x, this.camera.pos.y, this.camera.pos.z);
    glw.u1f(prog, 'uTime', time);
    glw.u1i(prog, 'uCloudTex', 3);
    glw.u4f(prog, 'uCloudParams',
      time * 0.0035 * (1 + this.weather.windX), time * 0.0021,
      0.0016, 0.30 * saturate(this.weather.cloudCover * 1.2) * (1 - this.night * 0.8));
    glw.u2f(prog, 'uWind', this.weather.windX, this.weather.windZ);

    glw.u1i(prog, 'uShadowMap', 2);
    glw.umat(prog, 'uLightMatrix', this.lightMatrix);
    glw.u2f(prog, 'uShadowParams', 1 / this.shadow.size, this.shadowStrength);

    // Surfaces. Units 4 and 5 are reserved for these for the whole frame, so
    // binding them once per program is only a uniform write.
    const tex = this.textures;
    glw.bindTexture(4, tex.surface);
    glw.bindTexture(5, tex.normal);
    glw.u1i(prog, 'uSurfTex', 4);
    glw.u1i(prog, 'uNormTex', 5);
    glw.u1f(prog, 'uDetailFade', this.quality.detailFade);

    const gl = glw.gl;
    const ms = prog.uniforms.uMatSurf;
    if (ms) gl.uniform4fv(ms, tex.surf);
    const mb = prog.uniforms.uMatBrdf;
    if (mb) gl.uniform4fv(mb, tex.brdf);

    const lp = prog.uniforms.uPointLights;
    if (lp) gl.uniform4fv(lp, this.pointLightData);
    const lc = prog.uniforms.uPointColors;
    if (lc) gl.uniform3fv(lc, this.pointColorData);
  }

  /**
   * Pick the four nearest active lights to the camera. More than four costs
   * more than it adds — the fifth brazier is never the one you are standing by.
   */
  setPointLights(lights, camX, camY, camZ) {
    if (!this.pointLightData) {
      this.pointLightData = new Float32Array(16);
      this.pointColorData = new Float32Array(12);
      this._lightScratch = [];
    }
    const scratch = this._lightScratch;
    scratch.length = 0;
    for (let i = 0; i < lights.length; i++) {
      const l = lights[i];
      if (l.intensity !== undefined && l.intensity <= 0.01) continue;
      const d = Math.hypot(l.x - camX, l.y - camY, l.z - camZ);
      if (d > l.radius + 60) continue;
      scratch.push({ l, d });
    }
    scratch.sort((a, b) => a.d - b.d);
    this.pointLightData.fill(0);
    this.pointColorData.fill(0);
    const n = Math.min(4, scratch.length);
    for (let i = 0; i < n; i++) {
      const l = scratch[i].l;
      const k = (l.intensity !== undefined ? l.intensity : 1);
      this.pointLightData[i * 4] = l.x;
      this.pointLightData[i * 4 + 1] = l.y;
      this.pointLightData[i * 4 + 2] = l.z;
      this.pointLightData[i * 4 + 3] = l.radius;
      this.pointColorData[i * 3] = l.color[0] * k;
      this.pointColorData[i * 3 + 1] = l.color[1] * k;
      this.pointColorData[i * 3 + 2] = l.color[2] * k;
    }
  }

  /** Fit an orthographic light frustum to a box around the camera focus. */
  _updateLightMatrix(focusX, focusY, focusZ) {
    const range = this.quality.shadowRange;
    const dist = 160;
    // Snap the light target to shadow-map texels so shadows do not shimmer
    // while the camera moves — the classic stable-cascade trick.
    const texel = (range * 2) / this.shadow.size;
    const fx = Math.round(focusX / texel) * texel;
    const fz = Math.round(focusZ / texel) * texel;
    const fy = focusY;

    this._lightTarget.x = fx; this._lightTarget.y = fy; this._lightTarget.z = fz;
    this._lightEye.x = fx + this.lightDir.x * dist;
    this._lightEye.y = fy + Math.max(this.lightDir.y, 0.25) * dist;
    this._lightEye.z = fz + this.lightDir.z * dist;

    m4lookAt(this._lightView, this._lightEye, this._lightTarget, this._lightUp);
    m4ortho(this._lightProj, -range, range, -range, range, 1, dist * 2.2);
    m4mul(this.lightMatrix, this._lightProj, this._lightView);
  }

  // -------------------------------------------------------------------------
  //  Frame
  // -------------------------------------------------------------------------

  render(scene, time, dt) {
    const glw = this.glw;
    const gl = glw.gl;
    const cam = this.camera;
    glw.resetStats();

    if (this._sizeDirty) this.resize(glw.canvas.width, glw.canvas.height);

    // ---- 1. shadow pass ----------------------------------------------------
    const fx = cam.target.x, fz = cam.target.z;
    const fy = scene.focusY !== undefined ? scene.focusY : cam.target.y;
    this._updateLightMatrix(fx, fy, fz);

    glw.setTag('shadow');
    glw.bindTarget(this.shadow);
    gl.colorMask(true, true, true, true);
    gl.clearColor(1, 1, 1, 1);
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    gl.enable(gl.DEPTH_TEST);
    gl.depthMask(true);
    gl.disable(gl.BLEND);
    // Front-face culling in the shadow pass pushes acne to surfaces the camera
    // cannot see.
    gl.cullFace(gl.FRONT);

    let p = glw.use(this.progShadowTerr);
    glw.umat(p, 'uLightMatrix', this.lightMatrix);
    scene.terrain.draw(p, true, this._lightTarget, this.quality.shadowRange);

    p = glw.use(this.progShadowInst);
    glw.umat(p, 'uLightMatrix', this.lightMatrix);
    glw.u1f(p, 'uTime', time);
    scene.batches.drawAll(p, true);

    gl.cullFace(gl.BACK);

    // ---- 2. opaque pass ----------------------------------------------------
    glw.bindTarget(this.scene);
    // The scene target now holds a rendered frame, so its depth texture is
    // meaningful. Until this point after a resize it is a freshly created
    // texture cleared to the far plane, and the world mask derived from it
    // would call every pixel sky.
    this._sceneRendered = true;
    const sky = this.sky;
    gl.clearColor(sky.fog[0], sky.fog[1], sky.fog[2], 1);
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    gl.enable(gl.DEPTH_TEST);
    gl.depthFunc(gl.LEQUAL);
    gl.depthMask(true);
    gl.disable(gl.BLEND);

    glw.bindTexture(2, this.shadow.texture);
    glw.bindTexture(3, this.cloudTex);

    glw.setTag('terrain');
    p = glw.use(this.progTerrain);
    glw.umat(p, 'uViewProj', cam.viewProj);
    this._applyCommon(p, time);
    const pal = scene.palette || {};
    glw.u3f(p, 'uRockColor', ...(pal.rock || [0.40, 0.39, 0.37]));
    glw.u3f(p, 'uSandColor', ...(pal.sand || [0.70, 0.64, 0.48]));
    glw.u3f(p, 'uSnowColor', ...(pal.snow || [0.70, 0.75, 0.82]));
    glw.u3f(p, 'uRoadColor', ...(pal.road || [0.40, 0.34, 0.26]));
    glw.u1f(p, 'uWetness', this.weather.wetness);
    scene.terrain.draw(p, false);

    glw.setTag('instances');
    p = glw.use(this.progInstance);
    glw.umat(p, 'uViewProj', cam.viewProj);
    this._applyCommon(p, time);
    scene.batches.drawAll(p, false);

    if (scene.grassBatch && scene.grassBatch.count > 0) {
      gl.disable(gl.CULL_FACE);
    glw.setTag('grass');
      p = glw.use(this.progGrass);
      glw.umat(p, 'uViewProj', cam.viewProj);
      this._applyCommon(p, time);
      const gr = this.quality.grassRadius;
      glw.u2f(p, 'uFadeRange', gr * 0.62, gr);
      const tr = scene.trample || cam.target;
      glw.u3f(p, 'uTrample', tr.x, tr.y, tr.z);
      glw.u1f(p, 'uTrampleRadius', scene.trampleRadius || 0.9);
      scene.grassBatch.draw(p);
      gl.enable(gl.CULL_FACE);
    }

    // ---- 3. sky ------------------------------------------------------------
    gl.depthMask(false);
    glw.setTag('sky');
    p = glw.use(this.progSky);
    glw.umat(p, 'uInvViewProj', cam.invViewProj);
    glw.u3f(p, 'uSunDir', this.sunDir.x, this.sunDir.y, this.sunDir.z);
    glw.u3f(p, 'uMoonDir', this.moonDir.x, this.moonDir.y, this.moonDir.z);
    glw.u3f(p, 'uSunColor', sky.sun[0], sky.sun[1], sky.sun[2]);
    glw.u3f(p, 'uSkyTop', sky.top[0], sky.top[1], sky.top[2]);
    glw.u3f(p, 'uSkyHorizon', sky.hor[0], sky.hor[1], sky.hor[2]);
    glw.u3f(p, 'uGroundColor', sky.gnd[0], sky.gnd[1], sky.gnd[2]);
    glw.u1f(p, 'uTime', time);
    glw.u1f(p, 'uNight', this.night);
    glw.u1f(p, 'uCloudCover', this.weather.cloudCover);
    glw.u1f(p, 'uCloudSpeed', 1.0);
    glw.u2f(p, 'uCloudWind', time * 0.0022 * (1 + this.weather.windX), time * 0.0013);
    this._drawFullscreen(p);
    gl.depthMask(true);

    // ---- 4. water ----------------------------------------------------------
    gl.enable(gl.BLEND);
    gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
    glw.setTag('water');
    p = glw.use(this.progWater);
    glw.umat(p, 'uViewProj', cam.viewProj);
    this._applyCommon(p, time);
    glw.u1f(p, 'uTileScale', scene.terrain.waterTileScale);
    glw.u1f(p, 'uNight', this.night);
    glw.u3f(p, 'uWaterShallow', ...(pal.waterShallow || [0.18, 0.34, 0.36]));
    glw.u3f(p, 'uWaterDeep', ...(pal.waterDeep || [0.045, 0.10, 0.14]));
    scene.terrain.drawWater(p, cam.pos.x, cam.pos.z, this.quality.viewDistance, cam.frustum);

    // ---- 5. particles ------------------------------------------------------
    if (scene.particles) {
      const n = scene.particles.pack();
      if (n > 0) {
        gl.depthMask(false);
    glw.setTag('particles');
        p = glw.use(this.progParticle);
        glw.umat(p, 'uViewProj', cam.viewProj);
        glw.u3f(p, 'uCamRight', cam.right.x, cam.right.y, cam.right.z);
        glw.u3f(p, 'uCamUp', cam.upVec.x, cam.upVec.y, cam.upVec.z);
        const counts = scene.particles.drawCounts;
        gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
        scene.particles.draw(p, 0, 0, counts[0]);
        gl.blendFunc(gl.SRC_ALPHA, gl.ONE);
        scene.particles.draw(p, 1, counts[0], counts[1]);
        gl.depthMask(true);
      }
    }
    gl.disable(gl.BLEND);

    // ---- 6. post -----------------------------------------------------------
    this._post(time, dt);
  }

  /**
   * Re-run the composite into a small offscreen target and describe the result
   * statistically.
   *
   * Judging "does this look good" by eye does not scale and does not regress-
   * test. Mean luminance, contrast, saturation and the fraction of pixels
   * crushed to black or clipped to white do: a frame that is blown out, muddy,
   * flat or desaturated shows up as a number that moved.
   *
   * It has to go through its own target because the default framebuffer is not
   * readable after the compositor has presented it — reading it back gives a
   * cleared buffer, which silently reports every frame as pure black.
   */
  readbackStats(stride = 1) {
    const glw = this.glw;
    const gl = glw.gl;
    if (!this.captureTarget) {
      this.captureTarget = glw.createRenderTarget(320, 180, { depth: false });
    }
    const rt = this.captureTarget;
    const w = rt.width, h = rt.height;

    gl.disable(gl.DEPTH_TEST);
    gl.disable(gl.BLEND);
    glw.bindTarget(rt);
    this._composite(this._lastCompositeTime || 0);

    if (!this._readBuf || this._readBuf.length < w * h * 4) {
      this._readBuf = new Uint8Array(w * h * 4);
    }
    const buf = this._readBuf;
    gl.readPixels(0, 0, w, h, gl.RGBA, gl.UNSIGNED_BYTE, buf);

    // Second pass into the same target: which of those pixels are world rather
    // than sky. Without this the spatial statistics grade a clear afternoon sky
    // as featureless ground, which it is not.
    let mask = null;
    if (this.scene.depthTex && this._sceneRendered) {
      const mp = glw.use(this.progWorldMask);
      glw.bindTexture(0, this.scene.depthTex);
      glw.u1i(mp, 'uDepthTex', 0);
      this._drawFullscreen(mp);
      if (!this._maskBuf || this._maskBuf.length < w * h * 4) {
        this._maskBuf = new Uint8Array(w * h * 4);
      }
      mask = this._maskBuf;
      gl.readPixels(0, 0, w, h, gl.RGBA, gl.UNSIGNED_BYTE, mask);
      // Summarise the depth the mask was derived from, so an empty mask can be
      // explained rather than guessed at. All-255 with every pixel flagged
      // exactly 1.0 means a cleared attachment; a spread means the depth is
      // real and the threshold is what is wrong.
      let dMin = 255, dMax = 0, dSum = 0, atFar = 0;
      for (let i = 0; i < mask.length; i += 4) {
        const d = mask[i + 1];
        if (d < dMin) dMin = d;
        if (d > dMax) dMax = d;
        dSum += d;
        if (mask[i + 2] > 127) atFar++;
      }
      const n = mask.length / 4;
      this._maskDepth = {
        min: dMin, max: dMax, mean: Math.round(dSum / n), atFar, total: n,
      };
    }

    glw.bindTarget(null);
    gl.enable(gl.DEPTH_TEST);

    let n = 0, sum = 0, sumSq = 0, sat = 0, clipped = 0, crushed = 0;
    let rSum = 0, gSum = 0, bSum = 0;
    const step = stride * 4;
    for (let i = 0; i < w * h * 4; i += step) {
      const r = buf[i] / 255, g = buf[i + 1] / 255, b = buf[i + 2] / 255;
      const lum = 0.2126 * r + 0.7152 * g + 0.0722 * b;
      const mx = Math.max(r, g, b), mn = Math.min(r, g, b);
      sum += lum;
      sumSq += lum * lum;
      sat += mx > 0.001 ? (mx - mn) / mx : 0;
      if (mx > 0.995) clipped++;
      if (mx < 0.02) crushed++;
      rSum += r; gSum += g; bSum += b;
      n++;
    }
    const mean = sum / n;
    return {
      pixels: n,
      meanLuma: mean,
      contrast: Math.sqrt(Math.max(0, sumSq / n - mean * mean)),
      saturation: sat / n,
      clippedRatio: clipped / n,
      crushedRatio: crushed / n,
      channelBalance: [rSum / n, gSum / n, bSum / n],
      ...this._spatialStats(buf, w, h, mask),
    };
  }

  /**
   * Spatial statistics of the frame — how much structure is actually in the
   * image, as opposed to how bright it is.
   *
   * A flat-shaded low-poly renderer produces frames that are almost entirely
   * constant-coloured facets: large regions with zero gradient, separated by a
   * few hard edges. Textured, normal-mapped, occluded surfaces produce gradient
   * almost everywhere. That difference is what these numbers capture, and it is
   * the one thing mean luminance and stdev cannot see.
   *
   * These must be computed over the whole buffer, not a strided sample: skipping
   * pixels destroys exactly the spatial relationships being measured.
   */
  _spatialStats(buf, w, h, mask) {
    const lum = this._lumaBuf && this._lumaBuf.length === w * h
      ? this._lumaBuf : (this._lumaBuf = new Float32Array(w * h));
    for (let i = 0, p = 0; i < w * h; i++, p += 4) {
      lum[i] = (0.2126 * buf[p] + 0.7152 * buf[p + 1] + 0.0722 * buf[p + 2]) / 255;
    }

    // How many pixels the mask calls world. Reported alongside the statistics,
    // because every one of them is an average over exactly these pixels and a
    // small or empty set makes them meaningless — while still printing as a
    // perfectly ordinary number. An empty mask used to surface as
    // "表面ディテール: 0", which reads as a flat image and is in fact a failed
    // measurement. Those two need to be distinguishable.
    let worldPixels = 0;
    let gradSum = 0, gradN = 0, edges = 0, flat = 0;
    // Structure is measured over the pixels that actually contain world.
    //
    // A smooth sky gradient is *correct* — it is what a sky looks like — and it
    // fills the top of every frame. Counting it as "flat" would mean a night
    // scene fails a detail check for the crime of having a night sky, and would
    // reward putting noise in the atmosphere.
    //
    // Two earlier attempts at excluding it were both wrong, and the way they
    // were wrong is worth keeping written down. The first cropped to a fraction
    // of the buffer, but gl.readPixels returns rows bottom-up, so it kept
    // exactly the half it meant to discard. The second fixed the direction and
    // still failed, because the camera pitches up about eleven degrees: the true
    // horizon sits near 67% of screen height, so a third to a half of any
    // "lower 62%" window is sky no matter which way it is measured.
    //
    // Depth knows which pixels are sky. A pixel counts if it, or any of its
    // immediate neighbours, has geometry — the neighbour test keeps the horizon
    // silhouette, which is real structure and should be graded.
    const isWorld = (x, y) => {
      if (!mask) return true;
      for (let dy = -1; dy <= 1; dy++) {
        for (let dx = -1; dx <= 1; dx++) {
          const nx = x + dx, ny = y + dy;
          if (nx < 0 || ny < 0 || nx >= w || ny >= h) continue;
          if (mask[(ny * w + nx) * 4] > 127) return true;
        }
      }
      return false;
    };
    // Sobel over the interior. The two thresholds are chosen against 8-bit
    // output: 1/255 is the smallest representable step, so "flat" means
    // genuinely quantised-identical, and the edge threshold sits well above
    // dither noise.
    for (let y = 1; y < h - 1; y++) {
      for (let x = 1; x < w - 1; x++) {
        if (!isWorld(x, y)) continue;
        worldPixels++;
        const i = y * w + x;
        const gx = (lum[i - w + 1] + 2 * lum[i + 1] + lum[i + w + 1])
          - (lum[i - w - 1] + 2 * lum[i - 1] + lum[i + w - 1]);
        const gy = (lum[i + w - 1] + 2 * lum[i + w] + lum[i + w + 1])
          - (lum[i - w - 1] + 2 * lum[i - w] + lum[i - w + 1]);
        const g = Math.sqrt(gx * gx + gy * gy);
        gradSum += g;
        gradN++;
        if (g > 0.10) edges++;
        if (g < 0.012) flat++;
      }
    }

    // Local RMS contrast in 8x8 tiles: micro-shading variation, which survives
    // even where the frame has no strong edges.
    let tileSum = 0, tiles = 0;
    for (let ty = 0; ty + 8 <= h; ty += 8) {
      for (let tx = 0; tx + 8 <= w; tx += 8) {
        // A tile counts once most of it is world; a tile straddling the horizon
        // would otherwise report the sky's flatness as the ground's.
        let world = 0;
        for (let y = 0; y < 8; y += 2) {
          for (let x = 0; x < 8; x += 2) if (isWorld(tx + x, ty + y)) world++;
        }
        if (world < 10) continue;
        let s = 0, s2 = 0;
        for (let y = 0; y < 8; y++) {
          for (let x = 0; x < 8; x++) {
            const v = lum[(ty + y) * w + tx + x];
            s += v; s2 += v * v;
          }
        }
        const m = s / 64;
        tileSum += Math.sqrt(Math.max(0, s2 / 64 - m * m));
        tiles++;
      }
    }

    // Colour diversity: populated cells of a 12x8x8 hue/sat/value histogram.
    // Guards against a frame that is detailed but monochrome.
    const bins = this._colorBins || (this._colorBins = new Uint8Array(12 * 8 * 8));
    bins.fill(0);
    for (let p = 0; p < w * h * 4; p += 4) {
      const r = buf[p] / 255, g = buf[p + 1] / 255, b = buf[p + 2] / 255;
      const mx = Math.max(r, g, b), mn = Math.min(r, g, b);
      const d = mx - mn;
      let hue = 0;
      if (d > 0.0001) {
        if (mx === r) hue = ((g - b) / d + 6) % 6;
        else if (mx === g) hue = (b - r) / d + 2;
        else hue = (r - g) / d + 4;
        hue /= 6;
      }
      const hi = Math.min(11, (hue * 12) | 0);
      const si = Math.min(7, ((mx > 0 ? d / mx : 0) * 8) | 0);
      const vi = Math.min(7, (mx * 8) | 0);
      bins[(hi * 8 + si) * 8 + vi] = 1;
    }
    let filled = 0;
    for (let i = 0; i < bins.length; i++) filled += bins[i];

    // Max(n, 1) turns "nothing was measured" into a value of zero, and zero is
    // a legitimate reading here — it is what a perfectly flat frame scores. The
    // two have to be told apart: an empty mask reported 表面ディテール 0 on four
    // of six scenes and read as a rendering collapse, when the frames were fine
    // and the mask was not. So the count travels with the numbers, and callers
    // that care check `measurable` rather than trusting a zero.
    // No mask at all means the statistics cover the whole frame including sky,
    // which is a weaker reading but a real one. An empty mask means the depth
    // was not available and nothing was measured. Only the second is a failure.
    const measurable = mask ? (worldPixels > (w * h) * 0.02 && tiles > 0) : tiles > 0;
    return {
      // Mean gradient magnitude: the headline "is there surface detail" number.
      detail: gradSum / Math.max(gradN, 1),
      edgeRatio: edges / Math.max(gradN, 1),
      // Fraction of the frame that is a dead flat facet. Falls as materials,
      // normal maps and occlusion fill the image with shading.
      flatRatio: flat / Math.max(gradN, 1),
      localContrast: tileSum / Math.max(tiles, 1),
      colorCells: filled,
      worldPixels,
      worldTiles: tiles,
      maskPresent: !!mask,
      maskDepth: this._maskDepth || null,
      measurable,
    };
  }

  _drawFullscreen(prog) {
    const gl = this.glw.gl;
    gl.bindBuffer(gl.ARRAY_BUFFER, this.quadBuf);
    const loc = prog.attribs.aPos;
    gl.enableVertexAttribArray(loc);
    gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
    this.glw.vertexAttribDivisorFn(loc, 0);
    gl.drawArrays(gl.TRIANGLES, 0, 3);
    this.glw.countDraw();
  }

  _post(time, dt) {
    const glw = this.glw;
    glw.setTag('post');
    const gl = glw.gl;
    gl.disable(gl.DEPTH_TEST);
    gl.disable(gl.BLEND);

    this._aoReady = this._renderAO();

    const useBloom = this.quality.bloom;
    if (useBloom) {
      glw.bindTarget(this.bloomA);
      let p = glw.use(this.progBright);
      glw.bindTexture(0, this.scene.color);
      glw.u1i(p, 'uTex', 0);
      glw.u2f(p, 'uTexel', 1 / this.scene.width, 1 / this.scene.height);
      glw.u1f(p, 'uThreshold', 0.82);
      this._drawFullscreen(p);

      p = glw.use(this.progBlur);
      glw.bindTarget(this.bloomB);
      glw.bindTexture(0, this.bloomA.color);
      glw.u1i(p, 'uTex', 0);
      glw.u2f(p, 'uDir', 1 / this.bloomA.width, 0);
      this._drawFullscreen(p);

      glw.bindTarget(this.bloomA);
      glw.bindTexture(0, this.bloomB.color);
      glw.u1i(p, 'uTex', 0);
      glw.u2f(p, 'uDir', 0, 1 / this.bloomA.height);
      this._drawFullscreen(p);
    }

    glw.bindTarget(null);
    this._lastCompositeTime = time;
    this._compositeBloom = useBloom;
    this._composite(time);

    gl.enable(gl.DEPTH_TEST);
    this.damageFlash = Math.max(0, this.damageFlash - dt * 2.6);
  }

  /**
   * Screen-space ambient occlusion from the scene depth texture.
   *
   * Returns false when it could not run — no depth texture, or the quality
   * preset has it off — so the composite knows to skip the fetch entirely
   * rather than sample a stale or absent buffer.
   */
  _renderAO() {
    const amount = this.quality.ao || 0;
    if (amount <= 0 || !this.scene.depthTex || !this.aoA) return false;
    const glw = this.glw;
    const cam = this.camera;
    const tanHalf = Math.tan(cam.fov * Math.PI / 360);
    const aspect = this.scene.width / Math.max(this.scene.height, 1);

    glw.setTag('ao');
    glw.bindTarget(this.aoA);
    let p = glw.use(this.progAO);
    glw.bindTexture(0, this.scene.depthTex);
    glw.u1i(p, 'uDepthTex', 0);
    glw.u2f(p, 'uTexel', 1 / this.aoA.width, 1 / this.aoA.height);
    glw.u2f(p, 'uNearFar', cam.near, cam.far);
    glw.u2f(p, 'uProjScale', tanHalf * aspect, tanHalf);
    glw.u1f(p, 'uRadius', this.quality.aoRadius || 0.75);
    glw.u1f(p, 'uStrength', 1.0);
    this._drawFullscreen(p);

    // Separable depth-aware blur. Two passes, ping-ponging, ending in aoA so
    // the composite always reads the same target.
    p = glw.use(this.progAOBlur);
    glw.bindTarget(this.aoB);
    glw.bindTexture(0, this.aoA.color);
    glw.bindTexture(1, this.scene.depthTex);
    glw.u1i(p, 'uTex', 0);
    glw.u1i(p, 'uDepthTex', 1);
    glw.u2f(p, 'uNearFar', cam.near, cam.far);
    glw.u2f(p, 'uDir', 1 / this.aoA.width, 0);
    this._drawFullscreen(p);

    glw.bindTarget(this.aoA);
    glw.bindTexture(0, this.aoB.color);
    glw.u1i(p, 'uTex', 0);
    glw.u2f(p, 'uDir', 0, 1 / this.aoA.height);
    this._drawFullscreen(p);
    glw.setTag('post');
    return true;
  }

  /** The final grade pass, factored out so a capture can replay it verbatim. */
  _composite(time) {
    const glw = this.glw;
    const useBloom = this._compositeBloom;
    const p = glw.use(this.progComposite);
    glw.bindTexture(0, this.scene.color);
    glw.bindTexture(1, useBloom ? this.bloomA.color : this.scene.color);
    glw.u1i(p, 'uScene', 0);
    glw.u1i(p, 'uBloom', 1);
    glw.u2f(p, 'uTexel', 1 / this.scene.width, 1 / this.scene.height);
    glw.u1f(p, 'uBloomStrength', useBloom ? this.bloomStrength : 0);
    glw.u1f(p, 'uExposure', this.sky.exposure * this.exposure);
    glw.u1f(p, 'uVignette', this.vignette + this.night * 0.14);
    // Human night vision is nearly colourless; draining saturation after dark
    // does more for the mood than any amount of blue tinting.
    glw.u1f(p, 'uSaturation', this.saturation * (1 - this.night * 0.45));
    glw.u3f(p, 'uTint', this.tint[0], this.tint[1], this.tint[2]);
    // Night keeps a little extra contrast: moonlit scenes read as flat murk
    // otherwise, and the eye expects hard silhouettes after dark.
    glw.u1f(p, 'uContrast', this.contrast + this.night * 0.12);
    // ...and the curve has to pivot on where this scene's midtone actually
    // sits. A daylight frame is built around 0.30; a moonlit one is built two
    // and a half stops below that, and pivoting a night frame on a daylight
    // midtone turns the whole S-curve into a shadow crush.
    glw.u1f(p, 'uContrastPivot', lerp(0.30, 0.15, this.night));
    glw.u1f(p, 'uAberration', this.quality.aberration);
    glw.u1f(p, 'uTime', time);
    glw.u1f(p, 'uDamage', this.damageFlash);
    glw.u1f(p, 'uDeath', this.deathFade);
    const aoAmount = this._aoReady ? (this.quality.ao || 0) : 0;
    if (aoAmount > 0) {
      glw.bindTexture(6, this.aoA.color);
      glw.u1i(p, 'uAO', 6);
    }
    glw.u1f(p, 'uAOAmount', aoAmount);
    this._drawFullscreen(p);
  }
}
