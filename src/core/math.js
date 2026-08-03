// ============================================================================
//  math.js — minimal, allocation-conscious linear algebra for the renderer.
//  Vectors are plain {x,y,z}; matrices are column-major Float32Array(16),
//  matching what WebGL's uniformMatrix4fv expects with transpose=false.
// ============================================================================

export const TAU = Math.PI * 2;
export const DEG = Math.PI / 180;

export const clamp = (v, a, b) => (v < a ? a : v > b ? b : v);
export const lerp = (a, b, t) => a + (b - a) * t;
export const smoothstep = (t) => t * t * (3 - 2 * t);
export const saturate = (v) => (v < 0 ? 0 : v > 1 ? 1 : v);
export const sign = (v) => (v > 0 ? 1 : v < 0 ? -1 : 0);

/** Frame-rate independent exponential approach. `rate` = how much of the gap closes per second. */
export function damp(a, b, rate, dt) {
  return b + (a - b) * Math.exp(-rate * dt);
}

/** Shortest signed difference between two angles, in (-PI, PI]. */
export function angleDelta(from, to) {
  let d = (to - from) % TAU;
  if (d > Math.PI) d -= TAU;
  if (d < -Math.PI) d += TAU;
  return d;
}

export function approachAngle(cur, target, maxStep) {
  const d = angleDelta(cur, target);
  if (Math.abs(d) <= maxStep) return target;
  return cur + Math.sign(d) * maxStep;
}

export function dampAngle(cur, target, rate, dt) {
  return cur + angleDelta(cur, target) * (1 - Math.exp(-rate * dt));
}

// ---------------------------------------------------------------------------
//  Vec3
// ---------------------------------------------------------------------------

export const v3 = (x = 0, y = 0, z = 0) => ({ x, y, z });
export const v3copy = (a) => ({ x: a.x, y: a.y, z: a.z });
export function v3set(o, x, y, z) { o.x = x; o.y = y; o.z = z; return o; }
export function v3add(o, a, b) { o.x = a.x + b.x; o.y = a.y + b.y; o.z = a.z + b.z; return o; }
export function v3sub(o, a, b) { o.x = a.x - b.x; o.y = a.y - b.y; o.z = a.z - b.z; return o; }
export function v3scale(o, a, s) { o.x = a.x * s; o.y = a.y * s; o.z = a.z * s; return o; }
export function v3addScaled(o, a, b, s) { o.x = a.x + b.x * s; o.y = a.y + b.y * s; o.z = a.z + b.z * s; return o; }
export const v3dot = (a, b) => a.x * b.x + a.y * b.y + a.z * b.z;
export const v3len = (a) => Math.hypot(a.x, a.y, a.z);
export const v3len2 = (a) => a.x * a.x + a.y * a.y + a.z * a.z;
export const v3dist = (a, b) => Math.hypot(a.x - b.x, a.y - b.y, a.z - b.z);
export const v3dist2 = (a, b) => {
  const dx = a.x - b.x, dy = a.y - b.y, dz = a.z - b.z;
  return dx * dx + dy * dy + dz * dz;
};
/** Horizontal (XZ-plane) distance — used constantly by AI and combat range checks. */
export const v3distXZ = (a, b) => Math.hypot(a.x - b.x, a.z - b.z);

export function v3cross(o, a, b) {
  const x = a.y * b.z - a.z * b.y;
  const y = a.z * b.x - a.x * b.z;
  const z = a.x * b.y - a.y * b.x;
  o.x = x; o.y = y; o.z = z;
  return o;
}

export function v3norm(o, a = o) {
  const l = Math.hypot(a.x, a.y, a.z);
  if (l < 1e-9) { o.x = 0; o.y = 0; o.z = 0; return o; }
  o.x = a.x / l; o.y = a.y / l; o.z = a.z / l;
  return o;
}

export function v3lerp(o, a, b, t) {
  o.x = a.x + (b.x - a.x) * t;
  o.y = a.y + (b.y - a.y) * t;
  o.z = a.z + (b.z - a.z) * t;
  return o;
}

// ---------------------------------------------------------------------------
//  Mat4 (column-major)
// ---------------------------------------------------------------------------

export function m4() {
  const m = new Float32Array(16);
  m[0] = m[5] = m[10] = m[15] = 1;
  return m;
}

export function m4identity(m) {
  m[0] = 1; m[1] = 0; m[2] = 0; m[3] = 0;
  m[4] = 0; m[5] = 1; m[6] = 0; m[7] = 0;
  m[8] = 0; m[9] = 0; m[10] = 1; m[11] = 0;
  m[12] = 0; m[13] = 0; m[14] = 0; m[15] = 1;
  return m;
}

export function m4copy(o, a) { o.set(a); return o; }

export function m4mul(o, a, b) {
  const a00 = a[0], a01 = a[1], a02 = a[2], a03 = a[3];
  const a10 = a[4], a11 = a[5], a12 = a[6], a13 = a[7];
  const a20 = a[8], a21 = a[9], a22 = a[10], a23 = a[11];
  const a30 = a[12], a31 = a[13], a32 = a[14], a33 = a[15];
  for (let i = 0; i < 4; i++) {
    const b0 = b[i * 4], b1 = b[i * 4 + 1], b2 = b[i * 4 + 2], b3 = b[i * 4 + 3];
    o[i * 4] = b0 * a00 + b1 * a10 + b2 * a20 + b3 * a30;
    o[i * 4 + 1] = b0 * a01 + b1 * a11 + b2 * a21 + b3 * a31;
    o[i * 4 + 2] = b0 * a02 + b1 * a12 + b2 * a22 + b3 * a32;
    o[i * 4 + 3] = b0 * a03 + b1 * a13 + b2 * a23 + b3 * a33;
  }
  return o;
}

export function m4perspective(o, fovy, aspect, near, far) {
  const f = 1 / Math.tan(fovy / 2);
  const nf = 1 / (near - far);
  o[0] = f / aspect; o[1] = 0; o[2] = 0; o[3] = 0;
  o[4] = 0; o[5] = f; o[6] = 0; o[7] = 0;
  o[8] = 0; o[9] = 0; o[10] = (far + near) * nf; o[11] = -1;
  o[12] = 0; o[13] = 0; o[14] = 2 * far * near * nf; o[15] = 0;
  return o;
}

export function m4ortho(o, l, r, b, t, n, f) {
  const lr = 1 / (l - r), bt = 1 / (b - t), nf = 1 / (n - f);
  o[0] = -2 * lr; o[1] = 0; o[2] = 0; o[3] = 0;
  o[4] = 0; o[5] = -2 * bt; o[6] = 0; o[7] = 0;
  o[8] = 0; o[9] = 0; o[10] = 2 * nf; o[11] = 0;
  o[12] = (l + r) * lr; o[13] = (t + b) * bt; o[14] = (f + n) * nf; o[15] = 1;
  return o;
}

const _lx = v3(), _ly = v3(), _lz = v3();
export function m4lookAt(o, eye, center, up) {
  v3norm(_lz, v3sub(_lz, eye, center));
  if (v3len2(_lz) < 1e-12) _lz.z = 1;
  v3norm(_lx, v3cross(_lx, up, _lz));
  if (v3len2(_lx) < 1e-12) { _lx.x = 1; _lx.y = 0; _lx.z = 0; }
  v3cross(_ly, _lz, _lx);
  o[0] = _lx.x; o[1] = _ly.x; o[2] = _lz.x; o[3] = 0;
  o[4] = _lx.y; o[5] = _ly.y; o[6] = _lz.y; o[7] = 0;
  o[8] = _lx.z; o[9] = _ly.z; o[10] = _lz.z; o[11] = 0;
  o[12] = -v3dot(_lx, eye); o[13] = -v3dot(_ly, eye); o[14] = -v3dot(_lz, eye); o[15] = 1;
  return o;
}

/** Compose translate * rotateY * scale — the common case for props and bones. */
export function m4trs(o, px, py, pz, ry, sx, sy, sz) {
  const c = Math.cos(ry), s = Math.sin(ry);
  o[0] = c * sx; o[1] = 0; o[2] = -s * sx; o[3] = 0;
  o[4] = 0; o[5] = sy; o[6] = 0; o[7] = 0;
  o[8] = s * sz; o[9] = 0; o[10] = c * sz; o[11] = 0;
  o[12] = px; o[13] = py; o[14] = pz; o[15] = 1;
  return o;
}

export function m4translate(o, x, y, z) {
  m4identity(o);
  o[12] = x; o[13] = y; o[14] = z;
  return o;
}

export function m4scale(o, x, y, z) {
  m4identity(o);
  o[0] = x; o[5] = y; o[10] = z;
  return o;
}

export function m4rotX(o, a) {
  const c = Math.cos(a), s = Math.sin(a);
  m4identity(o);
  o[5] = c; o[6] = s; o[9] = -s; o[10] = c;
  return o;
}

export function m4rotY(o, a) {
  const c = Math.cos(a), s = Math.sin(a);
  m4identity(o);
  o[0] = c; o[2] = -s; o[8] = s; o[10] = c;
  return o;
}

export function m4rotZ(o, a) {
  const c = Math.cos(a), s = Math.sin(a);
  m4identity(o);
  o[0] = c; o[1] = s; o[4] = -s; o[5] = c;
  return o;
}

/** Full inverse. Returns null for singular matrices. */
export function m4invert(o, m) {
  const a00 = m[0], a01 = m[1], a02 = m[2], a03 = m[3];
  const a10 = m[4], a11 = m[5], a12 = m[6], a13 = m[7];
  const a20 = m[8], a21 = m[9], a22 = m[10], a23 = m[11];
  const a30 = m[12], a31 = m[13], a32 = m[14], a33 = m[15];
  const b00 = a00 * a11 - a01 * a10, b01 = a00 * a12 - a02 * a10;
  const b02 = a00 * a13 - a03 * a10, b03 = a01 * a12 - a02 * a11;
  const b04 = a01 * a13 - a03 * a11, b05 = a02 * a13 - a03 * a12;
  const b06 = a20 * a31 - a21 * a30, b07 = a20 * a32 - a22 * a30;
  const b08 = a20 * a33 - a23 * a30, b09 = a21 * a32 - a22 * a31;
  const b10 = a21 * a33 - a23 * a31, b11 = a22 * a33 - a23 * a32;
  let det = b00 * b11 - b01 * b10 + b02 * b09 + b03 * b08 - b04 * b07 + b05 * b06;
  if (!det) return null;
  det = 1.0 / det;
  o[0] = (a11 * b11 - a12 * b10 + a13 * b09) * det;
  o[1] = (a02 * b10 - a01 * b11 - a03 * b09) * det;
  o[2] = (a31 * b05 - a32 * b04 + a33 * b03) * det;
  o[3] = (a22 * b04 - a21 * b05 - a23 * b03) * det;
  o[4] = (a12 * b08 - a10 * b11 - a13 * b07) * det;
  o[5] = (a00 * b11 - a02 * b08 + a03 * b07) * det;
  o[6] = (a32 * b02 - a30 * b05 - a33 * b01) * det;
  o[7] = (a20 * b05 - a22 * b02 + a23 * b01) * det;
  o[8] = (a10 * b10 - a11 * b08 + a13 * b06) * det;
  o[9] = (a01 * b08 - a00 * b10 - a03 * b06) * det;
  o[10] = (a30 * b04 - a31 * b02 + a33 * b00) * det;
  o[11] = (a21 * b02 - a20 * b04 - a23 * b00) * det;
  o[12] = (a11 * b07 - a10 * b09 - a12 * b06) * det;
  o[13] = (a00 * b09 - a01 * b07 + a02 * b06) * det;
  o[14] = (a31 * b01 - a30 * b03 - a32 * b00) * det;
  o[15] = (a20 * b03 - a21 * b01 + a22 * b00) * det;
  return o;
}

export function m4transformPoint(o, m, p) {
  const x = p.x, y = p.y, z = p.z;
  const w = m[3] * x + m[7] * y + m[11] * z + m[15] || 1;
  o.x = (m[0] * x + m[4] * y + m[8] * z + m[12]) / w;
  o.y = (m[1] * x + m[5] * y + m[9] * z + m[13]) / w;
  o.z = (m[2] * x + m[6] * y + m[10] * z + m[14]) / w;
  return o;
}

export function m4transformDir(o, m, p) {
  const x = p.x, y = p.y, z = p.z;
  o.x = m[0] * x + m[4] * y + m[8] * z;
  o.y = m[1] * x + m[5] * y + m[9] * z;
  o.z = m[2] * x + m[6] * y + m[10] * z;
  return o;
}

// ---------------------------------------------------------------------------
//  Frustum culling — extract 6 planes from a view-projection matrix.
// ---------------------------------------------------------------------------

export function makeFrustum() {
  return new Float32Array(24); // 6 planes x (nx, ny, nz, d)
}

export function frustumFromMatrix(planes, m) {
  const rows = [
    [m[3] + m[0], m[7] + m[4], m[11] + m[8], m[15] + m[12]],   // left
    [m[3] - m[0], m[7] - m[4], m[11] - m[8], m[15] - m[12]],   // right
    [m[3] + m[1], m[7] + m[5], m[11] + m[9], m[15] + m[13]],   // bottom
    [m[3] - m[1], m[7] - m[5], m[11] - m[9], m[15] - m[13]],   // top
    [m[3] + m[2], m[7] + m[6], m[11] + m[10], m[15] + m[14]],  // near
    [m[3] - m[2], m[7] - m[6], m[11] - m[10], m[15] - m[14]],  // far
  ];
  for (let i = 0; i < 6; i++) {
    const r = rows[i];
    const l = Math.hypot(r[0], r[1], r[2]) || 1;
    planes[i * 4] = r[0] / l;
    planes[i * 4 + 1] = r[1] / l;
    planes[i * 4 + 2] = r[2] / l;
    planes[i * 4 + 3] = r[3] / l;
  }
  return planes;
}

export function sphereInFrustum(planes, x, y, z, r) {
  for (let i = 0; i < 6; i++) {
    const d = planes[i * 4] * x + planes[i * 4 + 1] * y + planes[i * 4 + 2] * z + planes[i * 4 + 3];
    if (d < -r) return false;
  }
  return true;
}

// ---------------------------------------------------------------------------
//  Misc helpers used by gameplay code
// ---------------------------------------------------------------------------

/** Signed angle of a horizontal direction, matching the engine's yaw convention. */
export const yawFromDir = (dx, dz) => Math.atan2(dx, dz);

/** Is `target` inside a cone of half-angle `halfAngle` centred on yaw `yaw` from `origin`? */
export function inCone(originX, originZ, yaw, targetX, targetZ, halfAngle) {
  const dx = targetX - originX, dz = targetZ - originZ;
  if (dx === 0 && dz === 0) return true;
  return Math.abs(angleDelta(yaw, Math.atan2(dx, dz))) <= halfAngle;
}

/** Closest point on segment AB to point P, in the XZ plane. Returns parameter t in [0,1]. */
export function closestOnSegmentXZ(ax, az, bx, bz, px, pz) {
  const abx = bx - ax, abz = bz - az;
  const len2 = abx * abx + abz * abz;
  if (len2 < 1e-9) return 0;
  return clamp(((px - ax) * abx + (pz - az) * abz) / len2, 0, 1);
}
