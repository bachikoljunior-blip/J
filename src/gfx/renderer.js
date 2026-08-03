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
  FULLSCREEN_VS, BRIGHT_FS, BLUR_FS, COMPOSITE_FS,
} from './shaders.js';
import {
  m4, m4perspective, m4lookAt, m4ortho, m4mul, m4invert,
  makeFrustum, frustumFromMatrix, v3, v3sub, v3norm, v3cross,
  clamp, lerp, saturate, TAU,
} from '../core/math.js';
import { Noise2D } from '../core/rng.js';

// ---------------------------------------------------------------------------
//  Atmosphere keyframes: [hour, sunColor, skyTop, skyHorizon, ground, fog, fogSun, exposure]
// ---------------------------------------------------------------------------

const SKY_KEYS = [
  { h: 0.0, sun: [0.10, 0.13, 0.26], top: [0.018, 0.028, 0.070], hor: [0.055, 0.070, 0.125], gnd: [0.030, 0.036, 0.055], fog: [0.055, 0.070, 0.120], fogSun: [0.10, 0.12, 0.22], amb: 0.30, exposure: 1.55 },
  { h: 4.6, sun: [0.16, 0.17, 0.30], top: [0.035, 0.055, 0.120], hor: [0.140, 0.120, 0.150], gnd: [0.050, 0.052, 0.062], fog: [0.130, 0.120, 0.150], fogSun: [0.30, 0.20, 0.22], amb: 0.36, exposure: 1.45 },
  { h: 6.2, sun: [1.55, 0.72, 0.38], top: [0.120, 0.190, 0.360], hor: [0.720, 0.420, 0.290], gnd: [0.150, 0.130, 0.120], fog: [0.560, 0.390, 0.320], fogSun: [1.20, 0.62, 0.34], amb: 0.55, exposure: 1.18 },
  { h: 8.0, sun: [1.45, 1.15, 0.86], top: [0.180, 0.320, 0.580], hor: [0.640, 0.640, 0.640], gnd: [0.230, 0.220, 0.200], fog: [0.620, 0.660, 0.700], fogSun: [1.05, 0.88, 0.70], amb: 0.80, exposure: 1.02 },
  { h: 12.0, sun: [1.42, 1.36, 1.20], top: [0.190, 0.370, 0.700], hor: [0.660, 0.740, 0.840], gnd: [0.300, 0.300, 0.280], fog: [0.640, 0.720, 0.820], fogSun: [1.00, 0.96, 0.86], amb: 1.00, exposure: 0.95 },
  { h: 16.5, sun: [1.48, 1.22, 0.92], top: [0.180, 0.330, 0.640], hor: [0.700, 0.660, 0.620], gnd: [0.280, 0.260, 0.230], fog: [0.660, 0.660, 0.680], fogSun: [1.10, 0.90, 0.66], amb: 0.86, exposure: 1.00 },
  { h: 18.6, sun: [1.75, 0.66, 0.30], top: [0.140, 0.180, 0.340], hor: [0.860, 0.400, 0.230], gnd: [0.170, 0.130, 0.110], fog: [0.620, 0.360, 0.270], fogSun: [1.45, 0.55, 0.24], amb: 0.52, exposure: 1.20 },
  { h: 20.2, sun: [0.42, 0.28, 0.34], top: [0.045, 0.060, 0.130], hor: [0.220, 0.140, 0.170], gnd: [0.070, 0.065, 0.075], fog: [0.200, 0.150, 0.180], fogSun: [0.50, 0.26, 0.24], amb: 0.38, exposure: 1.45 },
  { h: 24.0, sun: [0.10, 0.13, 0.26], top: [0.018, 0.028, 0.070], hor: [0.055, 0.070, 0.125], gnd: [0.030, 0.036, 0.055], fog: [0.055, 0.070, 0.120], fogSun: [0.10, 0.12, 0.22], amb: 0.30, exposure: 1.55 },
];

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
    grassRadius: 24, grassCell: 1.35, grassBlades: 1, bloom: false, propDistance: 260,
    particleCap: 700, aberration: 0.0,
  },
  medium: {
    name: '中', resScale: 0.80, shadowSize: 1024, shadowRange: 70, viewDistance: 560,
    grassRadius: 36, grassCell: 1.05, grassBlades: 1, bloom: true, propDistance: 380,
    particleCap: 1400, aberration: 0.14,
  },
  high: {
    name: '高', resScale: 1.0, shadowSize: 2048, shadowRange: 88, viewDistance: 760,
    grassRadius: 50, grassCell: 0.85, grassBlades: 2, bloom: true, propDistance: 520,
    particleCap: 2600, aberration: 0.22,
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

    const defines = glw.depthTexture ? '' : '#define SHADOW_PACKED 1\n';
    const D = (src) => (defines ? src.replace('precision highp float;', 'precision highp float;\n' + defines) : src);

    this.progTerrain = glw.program(TERRAIN_VS, D(TERRAIN_FS), 'terrain');
    this.progInstance = glw.program(INSTANCE_VS, D(INSTANCE_FS), 'instance');
    this.progGrass = glw.program(GRASS_VS, D(GRASS_FS), 'grass');
    this.progShadowInst = glw.program(SHADOW_INSTANCE_VS, D(SHADOW_FS), 'shadowInst');
    this.progShadowTerr = glw.program(SHADOW_TERRAIN_VS, D(SHADOW_FS), 'shadowTerr');
    this.progSky = glw.program(SKY_VS, SKY_FS, 'sky');
    this.progWater = glw.program(WATER_VS, WATER_FS, 'water');
    this.progParticle = glw.program(PARTICLE_VS, PARTICLE_FS, 'particle');
    this.progBright = glw.program(FULLSCREEN_VS, BRIGHT_FS, 'bright');
    this.progBlur = glw.program(FULLSCREEN_VS, BLUR_FS, 'blur');
    this.progComposite = glw.program(FULLSCREEN_VS, COMPOSITE_FS, 'composite');

    this.quadBuf = glw.vbo(new Float32Array([-1, -1, 3, -1, -1, 3]));

    this.cloudTex = this._makeCloudTexture();

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

  setQuality(name) {
    const q = QUALITY[name] || QUALITY.medium;
    this.qualityName = QUALITY[name] ? name : 'medium';
    this.quality = q;
    if (this.shadow && this.shadow.size !== q.shadowSize) {
      this.shadow = null;
    }
    if (!this.shadow) this.shadow = this.glw.createShadowTarget(q.shadowSize);
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
    const glw = this.glw;
    const gl = glw.gl;
    if (this.scene) {
      gl.deleteFramebuffer(this.scene.fbo);
      gl.deleteTexture(this.scene.color);
      if (this.scene.depthBuf) gl.deleteRenderbuffer(this.scene.depthBuf);
    }
    if (this.bloomA) {
      for (const rt of [this.bloomA, this.bloomB]) {
        gl.deleteFramebuffer(rt.fbo);
        gl.deleteTexture(rt.color);
      }
    }
    this.scene = glw.createRenderTarget(w, h, { depth: true });
    const bw = Math.max(32, w >> 2), bh = Math.max(32, h >> 2);
    this.bloomA = glw.createRenderTarget(bw, bh, { depth: false });
    this.bloomB = glw.createRenderTarget(bw, bh, { depth: false });
    this._sizeDirty = false;
  }

  // -------------------------------------------------------------------------
  //  Atmosphere
  // -------------------------------------------------------------------------

  updateAtmosphere(dt) {
    this.hour = (this.hour + (dt / this.dayLengthSeconds) * 24 * this.timeFlow) % 24;
    const sky = sampleSky(this.hour);
    this.sky = sky;

    // Sun path: tilted circle so it rises in the east and sets in the west
    // rather than passing straight overhead.
    const ang = ((this.hour - 6) / 24) * TAU;
    const tilt = 0.35;
    const sx = Math.cos(ang);
    const sy = Math.sin(ang);
    this.sunDir.x = sx * Math.cos(tilt) - 0;
    this.sunDir.y = sy;
    this.sunDir.z = -sx * Math.sin(tilt) + 0.22;
    v3norm(this.sunDir);
    this.moonDir.x = -this.sunDir.x;
    this.moonDir.y = -this.sunDir.y;
    this.moonDir.z = -this.sunDir.z;

    this.night = 1 - saturate((this.sunDir.y + 0.16) / 0.30);

    // When the sun is below the horizon, light the world from the moon.
    if (this.sunDir.y < 0.02) {
      this.lightDir = this.moonDir;
      this.lightColor = [0.16 * (1), 0.20, 0.34];
      this.shadowStrength = 0.35;
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

    const targets = {
      clear: { rain: 0, cloud: 0.30, fog: 0, wind: 0.35 },
      overcast: { rain: 0, cloud: 0.82, fog: 0.25, wind: 0.55 },
      rain: { rain: 1, cloud: 0.95, fog: 0.5, wind: 0.75 },
      storm: { rain: 1.6, cloud: 1.0, fog: 0.7, wind: 1.5 },
      fog: { rain: 0, cloud: 0.6, fog: 1.5, wind: 0.2 },
      snow: { rain: 0.4, cloud: 0.9, fog: 0.6, wind: 0.5 },
      ash: { rain: 0.3, cloud: 0.75, fog: 0.8, wind: 0.4 },
    };
    const t = targets[w.target] || targets.clear;
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
      sky.top[0] * 0.95 * amb + 0.03, sky.top[1] * 0.95 * amb + 0.035, sky.top[2] * 0.95 * amb + 0.05);
    glw.u3f(prog, 'uGroundColor',
      sky.gnd[0] * 1.35 * amb, sky.gnd[1] * 1.30 * amb, sky.gnd[2] * 1.20 * amb);
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

    const gl = glw.gl;
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
    scene.terrain.draw(p, true);

    p = glw.use(this.progShadowInst);
    glw.umat(p, 'uLightMatrix', this.lightMatrix);
    glw.u1f(p, 'uTime', time);
    scene.batches.drawAll(p, true);

    gl.cullFace(gl.BACK);

    // ---- 2. opaque pass ----------------------------------------------------
    glw.bindTarget(this.scene);
    const sky = this.sky;
    gl.clearColor(sky.fog[0], sky.fog[1], sky.fog[2], 1);
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    gl.enable(gl.DEPTH_TEST);
    gl.depthFunc(gl.LEQUAL);
    gl.depthMask(true);
    gl.disable(gl.BLEND);

    glw.bindTexture(2, this.shadow.texture);
    glw.bindTexture(3, this.cloudTex);

    p = glw.use(this.progTerrain);
    glw.umat(p, 'uViewProj', cam.viewProj);
    this._applyCommon(p, time);
    const pal = scene.palette || {};
    glw.u3f(p, 'uRockColor', ...(pal.rock || [0.40, 0.39, 0.37]));
    glw.u3f(p, 'uSandColor', ...(pal.sand || [0.70, 0.64, 0.48]));
    glw.u3f(p, 'uSnowColor', ...(pal.snow || [0.86, 0.90, 0.95]));
    glw.u3f(p, 'uRoadColor', ...(pal.road || [0.40, 0.34, 0.26]));
    glw.u1f(p, 'uWetness', this.weather.wetness);
    scene.terrain.draw(p, false);

    p = glw.use(this.progInstance);
    glw.umat(p, 'uViewProj', cam.viewProj);
    this._applyCommon(p, time);
    scene.batches.drawAll(p, false);

    if (scene.grassBatch && scene.grassBatch.count > 0) {
      gl.disable(gl.CULL_FACE);
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
    p = glw.use(this.progWater);
    glw.umat(p, 'uViewProj', cam.viewProj);
    this._applyCommon(p, time);
    glw.u1f(p, 'uTileScale', scene.terrain.waterTileScale);
    glw.u1f(p, 'uNight', this.night);
    glw.u3f(p, 'uWaterShallow', ...(pal.waterShallow || [0.18, 0.34, 0.36]));
    glw.u3f(p, 'uWaterDeep', ...(pal.waterDeep || [0.045, 0.10, 0.14]));
    scene.terrain.drawWater(p, cam.pos.x, cam.pos.z, this.quality.viewDistance);

    // ---- 5. particles ------------------------------------------------------
    if (scene.particles) {
      const n = scene.particles.pack();
      if (n > 0) {
        gl.depthMask(false);
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

  _drawFullscreen(prog) {
    const gl = this.glw.gl;
    gl.bindBuffer(gl.ARRAY_BUFFER, this.quadBuf);
    const loc = prog.attribs.aPos;
    gl.enableVertexAttribArray(loc);
    gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
    this.glw.vertexAttribDivisorFn(loc, 0);
    gl.drawArrays(gl.TRIANGLES, 0, 3);
    this.glw.drawCalls++;
  }

  _post(time, dt) {
    const glw = this.glw;
    const gl = glw.gl;
    gl.disable(gl.DEPTH_TEST);
    gl.disable(gl.BLEND);

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
    glw.u1f(p, 'uAberration', this.quality.aberration);
    glw.u1f(p, 'uTime', time);
    glw.u1f(p, 'uDamage', this.damageFlash);
    glw.u1f(p, 'uDeath', this.deathFade);
    this._drawFullscreen(p);

    gl.enable(gl.DEPTH_TEST);
    this.damageFlash = Math.max(0, this.damageFlash - dt * 2.6);
  }
}
