// ============================================================================
//  instancing.js — one draw call per mesh type per frame.
//
//  Characters are the interesting case: a humanoid is ~18 boxes, so a fight
//  with 12 enemies is 200+ boxes. Pushing them all through a single instanced
//  box batch keeps that at one draw call instead of two hundred, which is the
//  difference between smooth and unplayable on a mid-range phone.
// ============================================================================

// row0(4) row1(4) row2(4) color(4) params(4) color2(4) material(4)
// color2 pairs with the mesh's per-vertex blend attribute so one draw call can
// paint bark and leaves, or walls and roof, from a single instance. material
// carries the two surface ids the same blend selects between, so the trunk gets
// cracked fibrous bark and the canopy gets soft foliage without a second batch.
export const INSTANCE_FLOATS = 28;

export class InstanceBatch {
  constructor(glw, mesh, capacity = 1024) {
    this.glw = glw;
    this.mesh = mesh;
    this.capacity = capacity;
    this.data = new Float32Array(capacity * INSTANCE_FLOATS);
    this.count = 0;
    this.buffer = glw.gl.createBuffer();
    this._uploaded = 0;
    this.castsShadow = true;
    // Current material, applied to every push until changed. Batches are
    // per-mesh-type and usually homogeneous, so this keeps push() callable
    // without threading material through every one of its arguments.
    this.mat0 = 0;
    this.mat1 = 0;
    this.roughMul = 1;
    this.scaleMul = 1;
  }

  /**
   * @param {number} primary   material id used where the mesh blend is 0
   * @param {number} [secondary] material id used where the blend is 1
   * @param {number} [roughMul]  multiplies the material's roughness
   * @param {number} [scaleMul]  multiplies its world texture frequency
   */
  material(primary, secondary = primary, roughMul = 1, scaleMul = 1) {
    this.mat0 = primary;
    this.mat1 = secondary;
    this.roughMul = roughMul;
    this.scaleMul = scaleMul;
    return this;
  }

  clear() { this.count = 0; }

  _grow() {
    const next = this.capacity * 2;
    const nd = new Float32Array(next * INSTANCE_FLOATS);
    nd.set(this.data);
    this.data = nd;
    this.capacity = next;
    this._uploaded = 0; // force a full re-allocation on the GPU side
  }

  /**
   * Push an instance built from an axis-aligned scale + Y rotation.
   * This covers props and most bones; `pushMatrix` handles arbitrary bases.
   */
  push(x, y, z, sx, sy, sz, yaw, r, g, b, emissive = 0, sway = 0, phase = 0, ao = 1, alpha = 1,
    r2, g2, b2) {
    if (this.count >= this.capacity) this._grow();
    const o = this.count * INSTANCE_FLOATS;
    const d = this.data;
    const c = Math.cos(yaw), s = Math.sin(yaw);
    d[o] = c * sx; d[o + 1] = 0; d[o + 2] = -s * sx; d[o + 3] = x;
    d[o + 4] = 0; d[o + 5] = sy; d[o + 6] = 0; d[o + 7] = y;
    d[o + 8] = s * sz; d[o + 9] = 0; d[o + 10] = c * sz; d[o + 11] = z;
    d[o + 12] = r; d[o + 13] = g; d[o + 14] = b; d[o + 15] = emissive;
    d[o + 16] = sway; d[o + 17] = phase; d[o + 18] = ao; d[o + 19] = alpha;
    d[o + 20] = r2 !== undefined ? r2 : r;
    d[o + 21] = g2 !== undefined ? g2 : g;
    d[o + 22] = b2 !== undefined ? b2 : b;
    d[o + 23] = emissive;
    d[o + 24] = this.mat0; d[o + 25] = this.mat1;
    d[o + 26] = this.roughMul; d[o + 27] = this.scaleMul;
    this.count++;
  }

  /**
   * Push an instance from three basis vectors plus a translation.
   * `basis` is a 9-element column-major 3x3.
   */
  pushMatrix(basis, tx, ty, tz, r, g, b, emissive = 0, ao = 1, alpha = 1, sway = 0, phase = 0) {
    if (this.count >= this.capacity) this._grow();
    const o = this.count * INSTANCE_FLOATS;
    const d = this.data;
    d[o] = basis[0]; d[o + 1] = basis[1]; d[o + 2] = basis[2]; d[o + 3] = tx;
    d[o + 4] = basis[3]; d[o + 5] = basis[4]; d[o + 6] = basis[5]; d[o + 7] = ty;
    d[o + 8] = basis[6]; d[o + 9] = basis[7]; d[o + 10] = basis[8]; d[o + 11] = tz;
    d[o + 12] = r; d[o + 13] = g; d[o + 14] = b; d[o + 15] = emissive;
    d[o + 16] = sway; d[o + 17] = phase; d[o + 18] = ao; d[o + 19] = alpha;
    d[o + 20] = r; d[o + 21] = g; d[o + 22] = b; d[o + 23] = emissive;
    d[o + 24] = this.mat0; d[o + 25] = this.mat1;
    d[o + 26] = this.roughMul; d[o + 27] = this.scaleMul;
    this.count++;
  }

  upload() {
    if (this.count === 0) return;
    const gl = this.glw.gl;
    gl.bindBuffer(gl.ARRAY_BUFFER, this.buffer);
    const needed = this.count * INSTANCE_FLOATS;
    if (this._uploaded < needed) {
      // Allocate with slack so steady-state frames only ever call bufferSubData.
      const alloc = Math.min(this.capacity * INSTANCE_FLOATS, Math.max(needed * 2, 1024));
      gl.bufferData(gl.ARRAY_BUFFER, alloc * 4, gl.DYNAMIC_DRAW);
      this._uploaded = alloc;
    }
    gl.bufferSubData(gl.ARRAY_BUFFER, 0, this.data.subarray(0, needed));
  }

  bindInstanceAttribs(prog) {
    const gl = this.glw.gl;
    const a = prog.attribs;
    const stride = INSTANCE_FLOATS * 4;
    gl.bindBuffer(gl.ARRAY_BUFFER, this.buffer);
    const set = (name, offsetFloats) => {
      const loc = a[name];
      if (loc === undefined || loc < 0) return;
      gl.enableVertexAttribArray(loc);
      gl.vertexAttribPointer(loc, 4, gl.FLOAT, false, stride, offsetFloats * 4);
      this.glw.vertexAttribDivisorFn(loc, 1);
    };
    set('aRow0', 0);
    set('aRow1', 4);
    set('aRow2', 8);
    set('aColor', 12);
    set('aParams', 16);
    set('aColor2', 20);
    set('aMaterial', 24);
  }

  draw(prog) {
    if (this.count === 0) return;
    const gl = this.glw.gl;
    this.mesh.bindGeometry(prog);
    this.bindInstanceAttribs(prog);
    this.glw.drawInstanced(gl.TRIANGLES, this.mesh.indexCount, this.mesh.indexType, 0, this.count);
    this.glw.countDraw();
    this.glw.countTris(this.mesh.triangleCount * this.count);
  }

  dispose() { this.glw.gl.deleteBuffer(this.buffer); }
}

/**
 * Registry of batches keyed by name, so gameplay code can say
 * `batches.get('box').push(...)` without owning GPU state.
 */
export class BatchSet {
  constructor(glw) {
    this.glw = glw;
    this.map = new Map();
    this.order = [];
  }

  add(name, mesh, capacity = 512, { castsShadow = true } = {}) {
    const b = new InstanceBatch(this.glw, mesh, capacity);
    b.castsShadow = castsShadow;
    b.name = name;
    this.map.set(name, b);
    this.order.push(b);
    return b;
  }

  get(name) { return this.map.get(name); }
  clearAll() { for (const b of this.order) b.clear(); }
  uploadAll() { for (const b of this.order) b.upload(); }

  drawAll(prog, shadowPass = false) {
    for (const b of this.order) {
      if (shadowPass && !b.castsShadow) continue;
      b.draw(prog);
    }
  }

  get totalInstances() {
    let n = 0;
    for (const b of this.order) n += b.count;
    return n;
  }
}
