// ============================================================================
//  particles.js — one pooled, sorted billboard system for every effect in the
//  game: sparks, blood, dust, embers, rain, snow, magic, boss telegraphs.
//
//  Particles are stored in flat typed arrays and drawn as a single instanced
//  quad batch. Sorting is skipped for additive particles (order-independent)
//  and done coarsely for alpha ones, which is invisible in motion.
// ============================================================================

const MAX_PARTICLES = 3000;

export const BLEND = { ALPHA: 0, ADDITIVE: 1 };

export class ParticleSystem {
  constructor(glw) {
    this.glw = glw;
    this.cap = MAX_PARTICLES;
    this.count = 0;

    this.px = new Float32Array(this.cap);
    this.py = new Float32Array(this.cap);
    this.pz = new Float32Array(this.cap);
    this.vx = new Float32Array(this.cap);
    this.vy = new Float32Array(this.cap);
    this.vz = new Float32Array(this.cap);
    this.life = new Float32Array(this.cap);
    this.maxLife = new Float32Array(this.cap);
    this.size0 = new Float32Array(this.cap);
    this.size1 = new Float32Array(this.cap);
    this.r = new Float32Array(this.cap);
    this.g = new Float32Array(this.cap);
    this.b = new Float32Array(this.cap);
    this.a0 = new Float32Array(this.cap);
    this.drag = new Float32Array(this.cap);
    this.grav = new Float32Array(this.cap);
    this.rot = new Float32Array(this.cap);
    this.rotSpeed = new Float32Array(this.cap);
    this.soft = new Float32Array(this.cap);
    this.blend = new Uint8Array(this.cap);
    this.ground = new Uint8Array(this.cap);   // collide with terrain?

    // GPU buffers: unit quad + per-particle instance stream.
    const gl = glw.gl;
    this.cornerBuf = glw.vbo(new Float32Array([
      -0.5, -0.5, 0.5, -0.5, 0.5, 0.5,
      -0.5, -0.5, 0.5, 0.5, -0.5, 0.5,
    ]));
    this.instData = new Float32Array(this.cap * 10); // center4 + color4 + extra2
    this.instBuf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, this.instBuf);
    gl.bufferData(gl.ARRAY_BUFFER, this.instData.byteLength, gl.DYNAMIC_DRAW);
    this.drawCounts = [0, 0];
  }

  spawn(opts) {
    if (this.count >= this.cap) {
      // Recycle the oldest slot rather than dropping the newest — new effects
      // are always the ones the player is looking at.
      this._remove(0);
    }
    const i = this.count++;
    this.px[i] = opts.x; this.py[i] = opts.y; this.pz[i] = opts.z;
    this.vx[i] = opts.vx || 0; this.vy[i] = opts.vy || 0; this.vz[i] = opts.vz || 0;
    this.maxLife[i] = opts.life || 1;
    this.life[i] = this.maxLife[i];
    this.size0[i] = opts.size || 0.2;
    this.size1[i] = opts.sizeEnd !== undefined ? opts.sizeEnd : this.size0[i] * 0.4;
    this.r[i] = opts.r !== undefined ? opts.r : 1;
    this.g[i] = opts.g !== undefined ? opts.g : 1;
    this.b[i] = opts.b !== undefined ? opts.b : 1;
    this.a0[i] = opts.alpha !== undefined ? opts.alpha : 1;
    this.drag[i] = opts.drag !== undefined ? opts.drag : 1.6;
    this.grav[i] = opts.gravity !== undefined ? opts.gravity : -9;
    this.rot[i] = opts.rot || 0;
    this.rotSpeed[i] = opts.rotSpeed || 0;
    this.soft[i] = opts.soft !== undefined ? opts.soft : 0.6;
    this.blend[i] = opts.blend !== undefined ? opts.blend : BLEND.ALPHA;
    this.ground[i] = opts.collide ? 1 : 0;
    return i;
  }

  _remove(i) {
    const last = --this.count;
    if (i === last) return;
    const arrays = [this.px, this.py, this.pz, this.vx, this.vy, this.vz, this.life,
      this.maxLife, this.size0, this.size1, this.r, this.g, this.b, this.a0,
      this.drag, this.grav, this.rot, this.rotSpeed, this.soft];
    for (const arr of arrays) arr[i] = arr[last];
    this.blend[i] = this.blend[last];
    this.ground[i] = this.ground[last];
  }

  update(dt, world) {
    for (let i = 0; i < this.count; i++) {
      this.life[i] -= dt;
      if (this.life[i] <= 0) { this._remove(i); i--; continue; }
      const d = Math.exp(-this.drag[i] * dt);
      this.vx[i] *= d;
      this.vz[i] *= d;
      this.vy[i] = this.vy[i] * d + this.grav[i] * dt;
      this.px[i] += this.vx[i] * dt;
      this.py[i] += this.vy[i] * dt;
      this.pz[i] += this.vz[i] * dt;
      this.rot[i] += this.rotSpeed[i] * dt;

      if (this.ground[i] && world) {
        const h = world.heightAt(this.px[i], this.pz[i]);
        if (this.py[i] < h + 0.03) {
          this.py[i] = h + 0.03;
          this.vy[i] *= -0.28;
          this.vx[i] *= 0.55;
          this.vz[i] *= 0.55;
          if (Math.abs(this.vy[i]) < 0.4) { this.vy[i] = 0; this.grav[i] = 0; this.ground[i] = 0; }
        }
      }
    }
  }

  /** Pack instance data, grouped by blend mode so we can do two draw calls. */
  pack() {
    const d = this.instData;
    let n = 0;
    this.drawCounts[0] = 0;
    this.drawCounts[1] = 0;
    for (let pass = 0; pass < 2; pass++) {
      for (let i = 0; i < this.count; i++) {
        if (this.blend[i] !== pass) continue;
        const t = 1 - this.life[i] / this.maxLife[i];
        const size = this.size0[i] + (this.size1[i] - this.size0[i]) * t;
        // Fade in fast, out slow — reads better than a linear ramp.
        const fade = t < 0.12 ? t / 0.12 : 1 - (t - 0.12) / 0.88;
        const o = n * 10;
        d[o] = this.px[i]; d[o + 1] = this.py[i]; d[o + 2] = this.pz[i]; d[o + 3] = size;
        d[o + 4] = this.r[i]; d[o + 5] = this.g[i]; d[o + 6] = this.b[i];
        d[o + 7] = this.a0[i] * Math.max(fade, 0);
        d[o + 8] = this.rot[i]; d[o + 9] = this.soft[i];
        n++;
      }
      this.drawCounts[pass] = n - (pass === 1 ? this.drawCounts[0] : 0);
    }
    this.packed = n;
    if (n > 0) {
      const gl = this.glw.gl;
      gl.bindBuffer(gl.ARRAY_BUFFER, this.instBuf);
      gl.bufferSubData(gl.ARRAY_BUFFER, 0, d.subarray(0, n * 10));
    }
    return n;
  }

  draw(prog, blendMode, offset, count) {
    if (count <= 0) return;
    const gl = this.glw.gl;
    const a = prog.attribs;

    gl.bindBuffer(gl.ARRAY_BUFFER, this.cornerBuf);
    gl.enableVertexAttribArray(a.aCorner);
    gl.vertexAttribPointer(a.aCorner, 2, gl.FLOAT, false, 0, 0);
    this.glw.vertexAttribDivisorFn(a.aCorner, 0);

    gl.bindBuffer(gl.ARRAY_BUFFER, this.instBuf);
    const stride = 40;
    const set = (name, size, off) => {
      const loc = a[name];
      if (loc === undefined || loc < 0) return;
      gl.enableVertexAttribArray(loc);
      gl.vertexAttribPointer(loc, size, gl.FLOAT, false, stride, offset * stride + off * 4);
      this.glw.vertexAttribDivisorFn(loc, 1);
    };
    set('aCenter', 4, 0);
    set('aColor', 4, 4);
    set('aExtra', 2, 8);

    this.glw.drawArraysInstancedFn(gl.TRIANGLES, 0, 6, count);
    this.glw.drawCalls++;
    this.glw.triangles += count * 2;
  }

  clear() { this.count = 0; }

  // -- effect presets -------------------------------------------------------

  burst(x, y, z, n, opts = {}) {
    const spread = opts.spread || 3;
    for (let i = 0; i < n; i++) {
      const a = Math.random() * Math.PI * 2;
      const up = opts.up !== undefined ? opts.up : 2.5;
      const s = Math.random() * spread;
      this.spawn({
        x, y, z,
        vx: Math.cos(a) * s + (opts.vx || 0),
        vy: up * (0.3 + Math.random()) + (opts.vy || 0),
        vz: Math.sin(a) * s + (opts.vz || 0),
        ...opts,
        life: (opts.life || 0.7) * (0.6 + Math.random() * 0.8),
        size: (opts.size || 0.16) * (0.7 + Math.random() * 0.7),
        rot: Math.random() * 6.28,
        rotSpeed: (Math.random() - 0.5) * 6,
      });
    }
  }

  bloodSpray(x, y, z, dx, dz, power = 1) {
    for (let i = 0; i < Math.round(9 * power); i++) {
      const a = Math.atan2(dz, dx) + (Math.random() - 0.5) * 1.5;
      const s = (2 + Math.random() * 5) * power;
      this.spawn({
        x, y: y + (Math.random() - 0.5) * 0.4, z,
        vx: Math.cos(a) * s, vy: 1.5 + Math.random() * 3.5, vz: Math.sin(a) * s,
        life: 0.55 + Math.random() * 0.5,
        size: 0.10 + Math.random() * 0.14, sizeEnd: 0.03,
        r: 0.52, g: 0.05, b: 0.06, alpha: 0.95,
        drag: 1.1, gravity: -16, soft: 0.35, collide: true,
        blend: BLEND.ALPHA,
      });
    }
  }

  sparkHit(x, y, z, dx, dz) {
    for (let i = 0; i < 12; i++) {
      const a = Math.atan2(dz, dx) + (Math.random() - 0.5) * 2.2;
      const s = 3 + Math.random() * 7;
      this.spawn({
        x, y, z,
        vx: Math.cos(a) * s, vy: 1 + Math.random() * 4, vz: Math.sin(a) * s,
        life: 0.25 + Math.random() * 0.3,
        size: 0.07, sizeEnd: 0.01,
        r: 1.0, g: 0.78, b: 0.35, alpha: 1,
        drag: 2.4, gravity: -14, soft: 0.15,
        blend: BLEND.ADDITIVE,
      });
    }
  }

  dustStep(x, y, z, power = 1) {
    for (let i = 0; i < 2; i++) {
      const a = Math.random() * Math.PI * 2;
      this.spawn({
        x: x + Math.cos(a) * 0.2, y: y + 0.04, z: z + Math.sin(a) * 0.2,
        vx: Math.cos(a) * 0.7 * power, vy: 0.5 * power, vz: Math.sin(a) * 0.7 * power,
        life: 0.5 + Math.random() * 0.4,
        size: 0.16 * power, sizeEnd: 0.5 * power,
        r: 0.62, g: 0.58, b: 0.48, alpha: 0.24,
        drag: 3.2, gravity: 0.4, soft: 0.9,
        blend: BLEND.ALPHA,
      });
    }
  }

  ember(x, y, z) {
    const a = Math.random() * Math.PI * 2;
    this.spawn({
      x: x + Math.cos(a) * 0.35, y: y + Math.random() * 0.3, z: z + Math.sin(a) * 0.35,
      vx: (Math.random() - 0.5) * 0.5, vy: 1.1 + Math.random() * 1.4, vz: (Math.random() - 0.5) * 0.5,
      life: 1.1 + Math.random() * 1.4,
      size: 0.055, sizeEnd: 0.012,
      r: 1.0, g: 0.55 + Math.random() * 0.3, b: 0.16, alpha: 1,
      drag: 0.7, gravity: 0.6, soft: 0.2,
      blend: BLEND.ADDITIVE,
    });
  }
}
