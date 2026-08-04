// ============================================================================
//  mesh.js — procedural geometry. Every model in the game is generated here;
//  there are no art assets to download, which keeps the whole game a few
//  hundred KB and makes it start instantly on a phone connection.
//
//  ONE RULE FOR EDITING THESE BUILDERS. game.js builds the whole mesh table
//  from a single seeded stream, so the number of rng() calls a builder makes is
//  part of the interface: change it and every mesh built after it in _buildMeshes
//  is re-rolled. That is still deterministic, so nothing fails — it just
//  silently swaps out geometry nobody touched. Adding the root flare and the
//  bracket shelves below cost the bush a third of its triangles (240 -> 160),
//  the conifer 21 and the ruin pillar 64, none of which was intended or visible
//  in the diff. Detail added to a shared-stream builder therefore draws from a
//  private stream (see `subRng`) and leaves the shared one exactly where it was.
// ============================================================================

import { makeRng } from '../core/rng.js';

/**
 * A private, fixed-seed stream for geometry added to an existing builder.
 *
 * Each builder here produces exactly one mesh that is then instanced, so its
 * jitter never varied per instance in the first place and there is nothing to
 * lose by taking it off the world seed. What there is to gain is that the
 * shared stream stays put — see the note at the top of the file.
 *
 * @param {number} seed any distinct constant
 * @returns {() => number} uniform [0, 1)
 */
function subRng(seed) { return makeRng(seed); }

/** Simple CPU-side mesh under construction. */
export class MeshData {
  constructor() {
    this.positions = [];
    this.normals = [];
    this.indices = [];
    // Per-vertex blend between the instance's primary and secondary colour.
    // One mesh can then be bark-and-leaves, or wall-and-roof, in a single
    // draw call instead of two.
    this.blends = [];
    this.blend = 0;
  }

  get vertexCount() { return this.positions.length / 3; }

  /** Vertices added after this call take the given colour slot. */
  useBlend(v) { this.blend = v; return this; }

  addVertex(x, y, z, nx, ny, nz) {
    this.positions.push(x, y, z);
    this.normals.push(nx, ny, nz);
    this.blends.push(this.blend);
    return this.vertexCount - 1;
  }

  addTri(a, b, c) { this.indices.push(a, b, c); }
  addQuad(a, b, c, d) { this.indices.push(a, b, c, a, c, d); }

  /** Merge another mesh, optionally offset and scaled, into this one. */
  merge(other, ox = 0, oy = 0, oz = 0, sx = 1, sy = 1, sz = 1, blend) {
    const base = this.vertexCount;
    const b = blend !== undefined ? blend : this.blend;
    for (let i = 0; i < other.positions.length; i += 3) {
      this.positions.push(
        other.positions[i] * sx + ox,
        other.positions[i + 1] * sy + oy,
        other.positions[i + 2] * sz + oz);
      // An explicit argument wins; otherwise the current useBlend() setting
      // overrides, and only then does the source mesh's own slot apply.
      this.blends.push(blend !== undefined ? b : (this.blend || other.blends[i / 3] || 0));
    }
    // Scaling normals correctly needs the inverse transpose; for the uniform
    // and near-uniform scales used here, renormalising is sufficient.
    for (let i = 0; i < other.normals.length; i += 3) {
      let nx = other.normals[i] / sx;
      let ny = other.normals[i + 1] / sy;
      let nz = other.normals[i + 2] / sz;
      const l = Math.hypot(nx, ny, nz) || 1;
      this.normals.push(nx / l, ny / l, nz / l);
    }
    for (let i = 0; i < other.indices.length; i++) this.indices.push(other.indices[i] + base);
    return this;
  }

  /** Recompute per-vertex normals by area-weighted face averaging. */
  computeSmoothNormals() {
    const n = new Float32Array(this.positions.length);
    const p = this.positions;
    for (let i = 0; i < this.indices.length; i += 3) {
      const a = this.indices[i] * 3, b = this.indices[i + 1] * 3, c = this.indices[i + 2] * 3;
      const ux = p[b] - p[a], uy = p[b + 1] - p[a + 1], uz = p[b + 2] - p[a + 2];
      const vx = p[c] - p[a], vy = p[c + 1] - p[a + 1], vz = p[c + 2] - p[a + 2];
      const nx = uy * vz - uz * vy;
      const ny = uz * vx - ux * vz;
      const nz = ux * vy - uy * vx;
      n[a] += nx; n[a + 1] += ny; n[a + 2] += nz;
      n[b] += nx; n[b + 1] += ny; n[b + 2] += nz;
      n[c] += nx; n[c + 1] += ny; n[c + 2] += nz;
    }
    for (let i = 0; i < n.length; i += 3) {
      const l = Math.hypot(n[i], n[i + 1], n[i + 2]) || 1;
      n[i] /= l; n[i + 1] /= l; n[i + 2] /= l;
    }
    this.normals = Array.from(n);
    return this;
  }

  toTyped() {
    return {
      positions: new Float32Array(this.positions),
      normals: new Float32Array(this.normals),
      blends: new Float32Array(this.blends),
      indices: this.vertexCount > 65535 ? new Uint32Array(this.indices) : new Uint16Array(this.indices),
      indexCount: this.indices.length,
    };
  }
}

// ---------------------------------------------------------------------------
//  Primitives
//  Convention: unit meshes span x,z in [-0.5, 0.5] and y in [0, 1], so an
//  instance matrix's scale maps directly to (width, height, depth) and the
//  pivot sits at the base — exactly what bones and props both want.
// ---------------------------------------------------------------------------

export function buildBox() {
  const m = new MeshData();
  const faces = [
    { n: [0, 0, 1], v: [[-0.5, 0, 0.5], [0.5, 0, 0.5], [0.5, 1, 0.5], [-0.5, 1, 0.5]] },
    { n: [0, 0, -1], v: [[0.5, 0, -0.5], [-0.5, 0, -0.5], [-0.5, 1, -0.5], [0.5, 1, -0.5]] },
    { n: [1, 0, 0], v: [[0.5, 0, 0.5], [0.5, 0, -0.5], [0.5, 1, -0.5], [0.5, 1, 0.5]] },
    { n: [-1, 0, 0], v: [[-0.5, 0, -0.5], [-0.5, 0, 0.5], [-0.5, 1, 0.5], [-0.5, 1, -0.5]] },
    { n: [0, 1, 0], v: [[-0.5, 1, 0.5], [0.5, 1, 0.5], [0.5, 1, -0.5], [-0.5, 1, -0.5]] },
    { n: [0, -1, 0], v: [[-0.5, 0, -0.5], [0.5, 0, -0.5], [0.5, 0, 0.5], [-0.5, 0, 0.5]] },
  ];
  for (const f of faces) {
    const idx = f.v.map((v) => m.addVertex(v[0], v[1], v[2], f.n[0], f.n[1], f.n[2]));
    m.addQuad(idx[0], idx[1], idx[2], idx[3]);
  }
  return m;
}

/**
 * Box with bevelled vertical edges. Reads as hand-carved stone rather than a
 * programmer cube, and costs only 8 extra triangles.
 */
export function buildBevelBox(bevel = 0.12) {
  const m = new MeshData();
  const b = bevel;
  const ring = [
    [-0.5 + b, -0.5], [0.5 - b, -0.5],
    [0.5, -0.5 + b], [0.5, 0.5 - b],
    [0.5 - b, 0.5], [-0.5 + b, 0.5],
    [-0.5, 0.5 - b], [-0.5, -0.5 + b],
  ];
  const n = ring.length;
  const bot = [], top = [];
  for (let i = 0; i < n; i++) {
    const [x, z] = ring[i];
    const [px, pz] = ring[(i + n - 1) % n];
    const [nx2, nz2] = ring[(i + 1) % n];
    let nx = (z - pz) + (nz2 - z);
    let nz = -((x - px) + (nx2 - x));
    const l = Math.hypot(nx, nz) || 1;
    nx /= l; nz /= l;
    bot.push(m.addVertex(x, 0, z, nx, 0, nz));
    top.push(m.addVertex(x, 1, z, nx, 0, nz));
  }
  for (let i = 0; i < n; i++) {
    const j = (i + 1) % n;
    m.addQuad(bot[i], bot[j], top[j], top[i]);
  }
  const capTop = [], capBot = [];
  for (let i = 0; i < n; i++) {
    const [x, z] = ring[i];
    capTop.push(m.addVertex(x, 1, z, 0, 1, 0));
    capBot.push(m.addVertex(x, 0, z, 0, -1, 0));
  }
  for (let i = 1; i < n - 1; i++) {
    m.addTri(capTop[0], capTop[i], capTop[i + 1]);
    m.addTri(capBot[0], capBot[i + 1], capBot[i]);
  }
  return m;
}

export function buildCylinder(segments = 8, topRadius = 0.5, bottomRadius = 0.5) {
  const m = new MeshData();
  const bot = [], top = [];
  for (let i = 0; i < segments; i++) {
    const a = (i / segments) * Math.PI * 2;
    const cx = Math.cos(a), sz = Math.sin(a);
    // Slanted sides need a normal tilted by the radius difference.
    const slope = (bottomRadius - topRadius);
    let nx = cx, ny = slope, nz = sz;
    const l = Math.hypot(nx, ny, nz) || 1;
    nx /= l; ny /= l; nz /= l;
    bot.push(m.addVertex(cx * bottomRadius, 0, sz * bottomRadius, nx, ny, nz));
    top.push(m.addVertex(cx * topRadius, 1, sz * topRadius, nx, ny, nz));
  }
  for (let i = 0; i < segments; i++) {
    const j = (i + 1) % segments;
    m.addQuad(bot[i], bot[j], top[j], top[i]);
  }
  if (topRadius > 0.001) {
    const c = m.addVertex(0, 1, 0, 0, 1, 0);
    const ring = [];
    for (let i = 0; i < segments; i++) {
      const a = (i / segments) * Math.PI * 2;
      ring.push(m.addVertex(Math.cos(a) * topRadius, 1, Math.sin(a) * topRadius, 0, 1, 0));
    }
    for (let i = 0; i < segments; i++) m.addTri(c, ring[i], ring[(i + 1) % segments]);
  }
  if (bottomRadius > 0.001) {
    const c = m.addVertex(0, 0, 0, 0, -1, 0);
    const ring = [];
    for (let i = 0; i < segments; i++) {
      const a = (i / segments) * Math.PI * 2;
      ring.push(m.addVertex(Math.cos(a) * bottomRadius, 0, Math.sin(a) * bottomRadius, 0, -1, 0));
    }
    for (let i = 0; i < segments; i++) m.addTri(c, ring[(i + 1) % segments], ring[i]);
  }
  return m;
}

export function buildCone(segments = 7) {
  return buildCylinder(segments, 0.0, 0.5);
}

/** Icosphere-ish blob; `jitter` deforms it into a believable boulder. */
export function buildRock(subdiv = 1, jitter = 0.22, seedFn = Math.random) {
  const t = (1 + Math.sqrt(5)) / 2;
  let verts = [
    [-1, t, 0], [1, t, 0], [-1, -t, 0], [1, -t, 0],
    [0, -1, t], [0, 1, t], [0, -1, -t], [0, 1, -t],
    [t, 0, -1], [t, 0, 1], [-t, 0, -1], [-t, 0, 1],
  ].map((v) => {
    const l = Math.hypot(v[0], v[1], v[2]);
    return [v[0] / l, v[1] / l, v[2] / l];
  });
  let faces = [
    [0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11],
    [1, 5, 9], [5, 11, 4], [11, 10, 2], [10, 7, 6], [7, 1, 8],
    [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9],
    [4, 9, 5], [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1],
  ];

  for (let s = 0; s < subdiv; s++) {
    const cache = new Map();
    const mid = (a, b) => {
      const key = a < b ? `${a}_${b}` : `${b}_${a}`;
      if (cache.has(key)) return cache.get(key);
      const va = verts[a], vb = verts[b];
      let x = (va[0] + vb[0]) / 2, y = (va[1] + vb[1]) / 2, z = (va[2] + vb[2]) / 2;
      const l = Math.hypot(x, y, z);
      verts.push([x / l, y / l, z / l]);
      const i = verts.length - 1;
      cache.set(key, i);
      return i;
    };
    const nf = [];
    for (const f of faces) {
      const a = mid(f[0], f[1]), b = mid(f[1], f[2]), c = mid(f[2], f[0]);
      nf.push([f[0], a, c], [f[1], b, a], [f[2], c, b], [a, b, c]);
    }
    faces = nf;
  }

  // Deform, squash vertically, and drop the pivot to the base.
  const deformed = verts.map((v) => {
    const k = 1 + (seedFn() - 0.5) * 2 * jitter;
    return [v[0] * 0.5 * k, v[1] * 0.42 * k, v[2] * 0.5 * k];
  });
  const minY = deformed.reduce((acc, v) => Math.min(acc, v[1]), Infinity);

  const m = new MeshData();
  for (const v of deformed) m.addVertex(v[0], v[1] - minY, v[2], 0, 1, 0);
  for (const f of faces) m.addTri(f[0], f[1], f[2]);
  m.computeSmoothNormals();
  return m;
}

/**
 * A tuft of five blades fanned around the vertical axis — five triangles.
 *
 * This used to be three curved ribbons of five triangles each. Fifteen
 * triangles per tuft, at fifty to a hundred thousand tufts a frame, was the
 * single largest item in the budget, and it bought a curve nobody can see: a
 * 30 cm blade is a couple of pixels wide past three metres.
 *
 * One triangle per blade is the whole blade — base pair, tip point — so five
 * blades give *more* silhouette than the old three for a third of the cost.
 * The grass pass draws with culling disabled and flips the normal toward the
 * viewer, so a single-sided triangle is safe here in a way it would not be in
 * the instanced pass. The normal is tilted 0.3 upward rather than left purely
 * horizontal so a field does not go black under a high sun.
 */
export function buildGrassTuft() {
  const m = new MeshData();
  // Yaws are spread irregularly rather than evenly: an even fan reads as a
  // rosette, and a hundred rosettes read as a pattern.
  const blades = [
    { yaw: 0.00, w: 0.50, h: 1.00, reach: 0.06, skew: 0.10 },
    { yaw: 1.18, w: 0.45, h: 0.86, reach: 0.22, skew: -0.14 },
    { yaw: 2.15, w: 0.42, h: 0.94, reach: 0.14, skew: 0.16 },
    { yaw: 3.55, w: 0.38, h: 0.74, reach: 0.30, skew: -0.08 },
    { yaw: 4.90, w: 0.34, h: 0.88, reach: 0.18, skew: 0.12 },
  ];
  for (const b of blades) {
    const c = Math.cos(b.yaw), s = Math.sin(b.yaw);
    const px = -s, pz = c;          // across the blade
    let nx = px, ny = 0.30, nz = pz;
    const l = Math.hypot(nx, ny, nz);
    nx /= l; ny /= l; nz /= l;
    const bx = c * 0.05, bz = s * 0.05;
    const a0 = m.addVertex(bx + px * b.w, 0, bz + pz * b.w, nx, ny, nz);
    const a1 = m.addVertex(bx - px * b.w, 0, bz - pz * b.w, nx, ny, nz);
    const t = m.addVertex(
      bx + c * b.reach + px * b.skew, b.h, bz + s * b.reach + pz * b.skew,
      nx, ny, nz);
    m.addTri(a0, a1, t);
  }
  return m;
}

// ---------------------------------------------------------------------------
//  Ground clutter
//
//  Most of every frame is ground, and bare ground is what reads as unfinished
//  however good the terrain shading is: real plains carry rubble, drifts,
//  deadwood and scrub the whole way to the horizon. These are the cheapest
//  objects that still catch light at a different angle from the ground they
//  sit on, which is what puts gradient into the mid distance — out there a
//  ground texture is already sub-pixel and only silhouettes survive.
//
//  Ten to twenty-four triangles each, flat shaded so every facet is its own
//  tone. All of them are closed and wound outward so back-face culling cannot
//  open a hole in one, and all carry the blend attribute so a single batch can
//  hold stone with a snow crust, or bark with a pale splintered core.
// ---------------------------------------------------------------------------

/**
 * Flat-shaded triangle: the face normal is derived here and the vertices are
 * duplicated rather than shared. Chipped stone and split wood are *made* of
 * hard edges; smoothing them turns debris into clay.
 * @param {MeshData} m
 * @param {number[]} a [x, y, z]
 * @param {number[]} b
 * @param {number[]} c
 * @param {number} [ba] blend slot for a (0 = primary colour, 1 = secondary)
 * @param {number} [bb] blend slot for b
 * @param {number} [bc] blend slot for c
 */
function flatTri(m, a, b, c, ba = 0, bb = ba, bc = ba) {
  const ux = b[0] - a[0], uy = b[1] - a[1], uz = b[2] - a[2];
  const vx = c[0] - a[0], vy = c[1] - a[1], vz = c[2] - a[2];
  let nx = uy * vz - uz * vy, ny = uz * vx - ux * vz, nz = ux * vy - uy * vx;
  const l = Math.hypot(nx, ny, nz) || 1;
  nx /= l; ny /= l; nz /= l;
  const i0 = m.useBlend(ba).addVertex(a[0], a[1], a[2], nx, ny, nz);
  const i1 = m.useBlend(bb).addVertex(b[0], b[1], b[2], nx, ny, nz);
  const i2 = m.useBlend(bc).addVertex(c[0], c[1], c[2], nx, ny, nz);
  m.useBlend(0);
  m.addTri(i0, i1, i2);
}

/** Flat quad; `bLow` applies to a and b, `bHigh` to c and d. */
function flatQuad(m, a, b, c, d, bLow = 0, bHigh = bLow) {
  flatTri(m, a, b, c, bLow, bLow, bHigh);
  flatTri(m, a, c, d, bLow, bHigh, bHigh);
}

/**
 * Horizontal ring of jittered points. Rings run *clockwise* seen from +Y: that
 * is the convention under which (ring[i], ring[i+1], apexAbove) faces outward
 * and (centre, ring[i], ring[i+1]) faces up, which is what every builder below
 * relies on.
 */
function groundRing(n, cx, cz, radius, y, a0, rng, jitter = 0.3) {
  const ring = [];
  for (let i = 0; i < n; i++) {
    const a = a0 - (i / n) * Math.PI * 2;
    const r = radius * (1 - jitter + rng() * jitter * 2);
    ring.push([cx + Math.cos(a) * r, y, cz + Math.sin(a) * r]);
  }
  return ring;
}

/**
 * Closed rod from a to b, capped with a point at each end: a fallen branch, a
 * long bone, a splintered stake. `4 * sides` triangles.
 */
function addRod(m, a, b, r0, r1, sides, blend = 0, tipBlend = blend) {
  let dx = b[0] - a[0], dy = b[1] - a[1], dz = b[2] - a[2];
  const len = Math.hypot(dx, dy, dz) || 1;
  dx /= len; dy /= len; dz /= len;
  // Any reference not parallel to the axis gives a usable ring basis.
  const rx = Math.abs(dy) > 0.9 ? 1 : 0, ry = Math.abs(dy) > 0.9 ? 0 : 1;
  // u = normalize(ref x d), v = d x u, so that cross(u, v) === d — the sense
  // under which an increasing ring angle winds outward.
  let ux = ry * dz - 0 * dy, uy = 0 * dx - rx * dz, uz = rx * dy - ry * dx;
  const ul = Math.hypot(ux, uy, uz) || 1;
  ux /= ul; uy /= ul; uz /= ul;
  const vx = dy * uz - dz * uy, vy = dz * ux - dx * uz, vz = dx * uy - dy * ux;
  const inset = len * 0.12;
  const ringAt = (t, r) => {
    const cxp = a[0] + dx * t, cyp = a[1] + dy * t, czp = a[2] + dz * t;
    const out = [];
    for (let i = 0; i < sides; i++) {
      const ang = (i / sides) * Math.PI * 2;
      const ca = Math.cos(ang) * r, sa = Math.sin(ang) * r;
      out.push([cxp + ux * ca + vx * sa, cyp + uy * ca + vy * sa, czp + uz * ca + vz * sa]);
    }
    return out;
  };
  const A = ringAt(inset, r0);
  const B = ringAt(len - inset, r1);
  for (let i = 0; i < sides; i++) {
    const j = (i + 1) % sides;
    flatQuad(m, A[i], A[j], B[j], B[i], blend, blend);
  }
  for (let i = 0; i < sides; i++) {
    const j = (i + 1) % sides;
    flatTri(m, B[i], B[j], b, blend, blend, tipBlend);
    flatTri(m, A[j], A[i], a, blend, blend, tipBlend);
  }
}

/**
 * Shattered rock: three angular chips sharing one footprint. Scree at the foot
 * of a cliff, pebble drifts on a path, snow-crusted stone on the peak — the
 * apex of each chip takes the secondary colour, which is where a crust would
 * sit. 15 triangles.
 */
export function buildClutterRock(rng) {
  const m = new MeshData();
  const n = 5;
  for (let s = 0; s < 3; s++) {
    const cx = (rng() - 0.5) * 0.62, cz = (rng() - 0.5) * 0.62;
    const rad = 0.12 + rng() * 0.17;
    const h = 0.30 + rng() * 0.68;
    const ring = groundRing(n, cx, cz, rad, 0, rng() * 6.283, rng, 0.45);
    // Off-centre apex: a split stone leans, a ball does not.
    const apex = [cx + (rng() - 0.5) * rad, h, cz + (rng() - 0.5) * rad];
    for (let i = 0; i < n; i++) flatTri(m, ring[i], ring[(i + 1) % n], apex, 0, 0, 1);
  }
  return m;
}

/**
 * Fallen branch, one end propped off the ground the way deadwood actually
 * lands. The tip takes the secondary colour for pale broken wood. 16 triangles.
 */
export function buildClutterWood(rng) {
  const m = new MeshData();
  const lift = 0.10 + rng() * 0.22;
  addRod(m,
    [-0.5, 0.42, (rng() - 0.5) * 0.3],
    [0.5, 0.42 + lift, (rng() - 0.5) * 0.3],
    0.42, 0.26, 4, 0, 1);
  return m;
}

/**
 * Dry scrub / tussock: five splayed blades, each drawn from both sides because
 * the instanced pass culls back faces and a tussock the player walks behind
 * must not blink out. 10 triangles.
 */
export function buildClutterScrub(rng) {
  const m = new MeshData();
  const blades = 5;
  for (let i = 0; i < blades; i++) {
    const a = (i / blades) * Math.PI * 2 + rng() * 0.6;
    const c = Math.cos(a), s = Math.sin(a);
    const px = -s, pz = c;
    const w = 0.10 + rng() * 0.13;
    const h = 0.55 + rng() * 0.45;
    const reach = 0.10 + rng() * 0.36;
    const bx = c * 0.06, bz = s * 0.06;
    const A = [bx + px * w, 0, bz + pz * w];
    const B = [bx - px * w, 0, bz - pz * w];
    const T = [bx + c * reach, h, bz + s * reach];
    flatTri(m, A, B, T, 0, 0, 1);
    flatTri(m, B, A, T, 0, 0, 1);
  }
  return m;
}

/** Two weathered long bones lying where the carcass fell. 24 triangles. */
export function buildClutterBone(rng) {
  const m = new MeshData();
  addRod(m,
    [-0.46, 0.16, -0.24 + rng() * 0.1],
    [0.42, 0.14, -0.02 + rng() * 0.1],
    0.15, 0.12, 3, 0, 1);
  addRod(m,
    [-0.30 - rng() * 0.15, 0.13, 0.30],
    [0.44, 0.19, 0.08 - rng() * 0.12],
    0.12, 0.15, 3, 0, 1);
  return m;
}

/**
 * Wind-built drift — ash, snow, blown sand, silt against a bank. Smooth-shaded
 * on purpose: it is the one piece of clutter that should read as a soft mass,
 * and a smooth curved mound is what turns a single directional light into a
 * whole tonal ramp across the ground. The crest carries the secondary colour,
 * which is where sun catches the fresh material. 14 triangles.
 */
export function buildClutterDrift(rng) {
  const m = new MeshData();
  const N = 4;
  const ridge = [], skirtA = [], skirtB = [];
  for (let i = 0; i < N; i++) {
    const t = i / (N - 1);
    // Crest nearer one end and tailing off: wind piles asymmetrically, and a
    // symmetric pillow reads as a bag of sand.
    const prof = Math.sin(Math.PI * Math.pow(t, 0.78));
    const h = (0.55 + rng() * 0.45) * prof + 0.02;
    const wA = 0.5 * (0.35 + 0.65 * prof) * (0.8 + rng() * 0.4);   // windward, long
    const wB = 0.5 * (0.13 + 0.30 * prof) * (0.8 + rng() * 0.4);   // lee, steep
    const zc = (rng() - 0.5) * 0.08;
    ridge.push(m.useBlend(1).addVertex(t - 0.5, h, zc - wB * 0.55, 0, 1, 0));
    skirtA.push(m.useBlend(0).addVertex(t - 0.5, 0, zc + wA, 0, 1, 0));
    skirtB.push(m.useBlend(0).addVertex(t - 0.5, 0, zc - wB, 0, 1, 0));
  }
  m.useBlend(0);
  for (let i = 0; i < N - 1; i++) {
    m.addQuad(skirtA[i], skirtA[i + 1], ridge[i + 1], ridge[i]);
    m.addQuad(ridge[i], ridge[i + 1], skirtB[i + 1], skirtB[i]);
  }
  m.addTri(ridge[0], skirtB[0], skirtA[0]);
  m.addTri(ridge[N - 1], skirtA[N - 1], skirtB[N - 1]);
  m.computeSmoothNormals();
  return m;
}

/**
 * Cracked ground plate: a heaved slab of bedrock or baked mud, tilted so one
 * edge stands proud. The top face takes the secondary colour — sun-bleached
 * against the raw broken edge. 15 triangles.
 */
export function buildClutterSlab(rng) {
  const m = new MeshData();
  const n = 5;
  // Always decisively tilted, and to one side or the other rather than around
  // zero. A plate that has been heaved has a raised edge and a buried one; the
  // old range went through flat, and a flat plate lying on flat ground is a
  // painted patch — same normal as everything under it, so it has no lit face,
  // no shaded face and nothing for the light to say about it.
  const tilt = (rng() < 0.5 ? -1 : 1) * (0.35 + rng() * 0.55);
  const top = groundRing(n, 0, 0, 0.5, 1, rng() * 6.283, rng, 0.28);
  let mid = 0;
  for (const p of top) { p[1] = 1 + p[0] * tilt; mid += p[1]; }
  mid /= n;
  const bot = top.map((p) => [p[0] * 0.94, 0, p[2] * 0.94]);
  for (let i = 0; i < n; i++) {
    flatQuad(m, bot[i], bot[(i + 1) % n], top[(i + 1) % n], top[i], 0, 1);
  }
  const c = [0, mid, 0];
  for (let i = 0; i < n; i++) flatTri(m, c, top[i], top[(i + 1) % n], 1, 1, 1);
  return m;
}

/**
 * Broken stump. Scaled tall it is a standing scorched snag, which is the
 * silhouette the Cinderwaste is missing. The splintered core takes the
 * secondary colour, together with the bracket shelves. 24 triangles.
 */
export function buildClutterStump(rng) {
  const m = new MeshData();
  // Six sides, unchanged. Dropping to five to pay for the shelves below saved
  // three triangles on a mesh instanced a few hundred times, and cost far more
  // than that elsewhere: the shorter trunk loop pulled the shared mesh stream
  // three draws forward and re-rolled every builder after it. See the note at
  // the top of the file. The waste has the headroom for the six.
  const n = 6;
  const base = groundRing(n, 0, 0, 0.5, 0, rng() * 6.283, rng, 0.18);
  const top = [];
  for (let i = 0; i < n; i++) {
    const b = base[i];
    const k = 0.60 + rng() * 0.16;
    top.push([b[0] * k, 0.70 + rng() * 0.30, b[2] * k]);   // uneven, snapped rim
  }
  for (let i = 0; i < n; i++) {
    flatQuad(m, base[i], base[(i + 1) % n], top[(i + 1) % n], top[i], 0, 0);
  }
  // The rim falls away to a low core, the way a trunk actually breaks.
  const core = [(rng() - 0.5) * 0.16, 0.52 + rng() * 0.18, (rng() - 0.5) * 0.16];
  for (let i = 0; i < n; i++) flatTri(m, core, top[i], top[(i + 1) % n], 1, 1, 1);

  // Bracket fungus, three shelves stepping round the trunk, on the secondary
  // colour slot with the snapped core.
  //
  // A bracket is the brightest small object on a forest floor — near-white, and
  // several times the reflectance of wet loam — and it is the one thing down
  // there that still reads once the canopy has taken the light. Two triangles
  // apiece buy a lit upper face and an underside that is never lit, so each
  // shelf is its own small tonal step rather than one bright patch.
  //
  // The same geometry serves everywhere the stump does: outside the wood the
  // secondary is splintered wood or, in the waste, char, and the shelves read
  // as the flanges of bark left standing on a broken trunk.
  const br = subRng(0x5f3b21);
  for (let i = 0; i < 3; i++) {
    const a = br() * 6.283;
    const y = 0.22 + i * 0.19 + br() * 0.08;
    const spread = 0.28 + br() * 0.18;   // half-angle where it grips the trunk
    const reach = 0.30 + br() * 0.26;
    // The trunk narrows going up, so the grip radius has to follow it or a
    // shelf near the rim floats off the side.
    const grip = 0.46 - y * 0.14;
    const A = [Math.cos(a - spread) * grip, y, Math.sin(a - spread) * grip];
    const B = [Math.cos(a + spread) * grip, y + (br() - 0.5) * 0.05,
      Math.sin(a + spread) * grip];
    const T = [Math.cos(a) * (grip + reach), y + 0.04 + br() * 0.04,
      Math.sin(a) * (grip + reach)];
    const U = [Math.cos(a) * (grip + reach * 0.78), y - 0.06 - br() * 0.05,
      Math.sin(a) * (grip + reach * 0.78)];
    flatTri(m, A, B, T, 1, 1, 1);   // upper face, catches what light there is
    // Reversed, or the shelf is a flat tab with two lit faces. A and B run
    // anticlockwise round the trunk, and for that order the face normal takes
    // its sign from how far out the third point sits, not from whether it is
    // above or below — so T and U wound the same way both come out facing up.
    flatTri(m, B, A, U, 1, 1, 1);
  }
  return m;
}

/**
 * Every clutter mesh, keyed by the CLUTTER id foliage.js scatters. Kept here so
 * the geometry and the id table cannot drift apart.
 * @param {function(): number} rng
 * @returns {Array<MeshData>}
 */
export function buildClutterMeshes(rng) {
  return [
    buildClutterRock(rng),
    buildClutterWood(rng),
    buildClutterScrub(rng),
    buildClutterBone(rng),
    buildClutterDrift(rng),
    buildClutterSlab(rng),
    buildClutterStump(rng),
  ];
}

// ---------------------------------------------------------------------------
//  Land features
//
//  The tier between clutter and props: two to eight metres, tens of them in a
//  view rather than thousands. They exist because a plain is not made legible
//  by surface treatment. A 30 cm stone is a smudge at forty metres and gone at
//  ninety, so on open ground the whole middle distance — which is most of the
//  frame — falls back to bare terrain shading. What fixes that is mass: things
//  with a lit face, a shaded face and a cast silhouette, big enough that the
//  land around them reads as having somewhere to stand.
//
//  They are also where the world stops looking generated. Outcrops on the
//  slope breaks, thickets along the hollows, reed beds at the water's edge,
//  dunes lying across the wind, and walls and cairns left by people — each one
//  says something about the ground it sits on.
//
//  A hundred triangles each is affordable at this density and buys real
//  silhouette, which is the only thing that survives past fifty metres.
// ---------------------------------------------------------------------------

/**
 * Rock outcrop: four angular masses shouldering out of the turf at different
 * heights and leans, sharing one footprint. Scaled small and wide it is a
 * boulder cluster; scaled tall it is a tor. Every base ring sits below y = 0 so
 * the mass stays bedded whatever the ground does under it — the instance
 * transform carries no tilt, and a flat-bottomed rock on a slope floats.
 * The upper rings take the secondary colour: lichen, snow crust or ash fall.
 * 60 triangles.
 */
export function buildOutcrop(rng) {
  const m = new MeshData();
  const n = 5;
  for (let s = 0; s < 4; s++) {
    const cx = (rng() - 0.5) * 0.66, cz = (rng() - 0.5) * 0.66;
    const rad = 0.17 + rng() * 0.19;
    const h = 0.30 + rng() * 0.70;
    const lx = (rng() - 0.5) * 0.30, lz = (rng() - 0.5) * 0.30;
    const a0 = rng() * 6.283;
    const base = groundRing(n, cx, cz, rad, -0.35, a0, rng, 0.34);
    const top = groundRing(n, cx + lx, cz + lz, rad * (0.42 + rng() * 0.34), h, a0, rng, 0.30);
    for (let i = 0; i < n; i++) {
      const j = (i + 1) % n;
      flatQuad(m, base[i], base[j], top[j], top[i], 0, 1);
    }
    const cap = [cx + lx, h + 0.05 + rng() * 0.08, cz + lz];
    for (let i = 0; i < n; i++) flatTri(m, cap, top[i], top[(i + 1) % n], 1, 1, 1);
  }
  return m;
}

/**
 * Bramble thicket: three lumpy masses in a line with bare arching stems over
 * them. Stretched along x it becomes a hedgerow, which is what actually divides
 * grassland — and a hedgerow run is a horizon-crossing shape a smooth meadow
 * has nothing else to offer. The stems take the secondary colour so the dead
 * wood reads pale against the mass. 108 triangles.
 */
export function buildThicket(rng) {
  const m = new MeshData();
  for (let i = 0; i < 3; i++) {
    const t = i / 2 - 0.5;
    const s = 0.52 + rng() * 0.34;
    m.merge(buildRock(0, 0.34, rng),
      t * 0.54 + (rng() - 0.5) * 0.10, 0, (rng() - 0.5) * 0.18,
      s, 0.74 + rng() * 0.42, s * 0.9, 0);
  }
  // Stems arch up and over: a bramble mass is defined by the canes that escape
  // it, and without them the blob reads as a bush the size of a house.
  for (let i = 0; i < 4; i++) {
    const bx = (rng() - 0.5) * 0.8;
    const a = rng() * 6.283;
    addRod(m,
      [bx, 0.05, (rng() - 0.5) * 0.3],
      [bx + Math.cos(a) * 0.30, 0.78 + rng() * 0.30, Math.sin(a) * 0.30],
      0.035, 0.018, 3, 1, 1);
  }
  return m;
}

/**
 * Reed bed: a stand of tall blades with two rotting posts left in it. Reeds
 * grow in beds at the water margin, never singly, and the posts are what turn
 * a green patch into somewhere that was once used. Blades are double-sided
 * because the instanced pass culls back faces. 64 triangles.
 */
export function buildReedBed(rng) {
  const m = new MeshData();
  for (let i = 0; i < 16; i++) {
    const a = (i / 16) * Math.PI * 2 + rng() * 0.5;
    const r = 0.16 + rng() * 0.34;
    const bx = Math.cos(a) * r, bz = Math.sin(a) * r;
    const w = 0.022 + rng() * 0.034;
    const h = 0.62 + rng() * 0.38;
    const lean = rng() * 0.22;
    const A = [bx - w, 0, bz];
    const B = [bx + w, 0, bz];
    const T = [bx + Math.cos(a) * lean, h, bz + Math.sin(a) * lean];
    flatTri(m, A, B, T, 0, 0, 1);
    flatTri(m, B, A, T, 0, 0, 1);
  }
  for (let i = 0; i < 2; i++) {
    const bx = (rng() - 0.5) * 0.5, bz = (rng() - 0.5) * 0.5;
    addRod(m, [bx, 0, bz],
      [bx + (rng() - 0.5) * 0.22, 0.5 + rng() * 0.45, bz + (rng() - 0.5) * 0.22],
      0.055, 0.042, 4, 1, 1);
  }
  return m;
}

/**
 * Wind-built dune with burnt timber standing out of its crest.
 *
 * The mound is smooth-shaded and the spars are faceted, so it is built in two
 * pieces and merged: one call to computeSmoothNormals would round the timber
 * off with it. Windward face long, lee face short and steep.
 *
 * The colour split is the point of this shape. Primary is charred ground and
 * secondary is fresh pale ash, and the mesh ramps from one to the other up the
 * flank, so a single directional light gives a dark base, a bright crest and a
 * whole tonal range in between — which is exactly what a plain of uniform grey
 * cannot do for itself.
 *
 * The spars deliberately break the unit-height convention and reach half again
 * above the crest: on the ash plain the horizon sits low in frame, and a thing
 * that crosses it is worth more than the same triangles spent below it.
 * 54 triangles.
 */
export function buildAshDune(rng) {
  const mound = new MeshData();
  const N = 5;
  const ridge = [], skirtA = [], skirtB = [];
  for (let i = 0; i < N; i++) {
    const t = i / (N - 1);
    const prof = Math.sin(Math.PI * Math.pow(t, 0.72));
    const h = (0.70 + rng() * 0.30) * prof + 0.01;
    const wA = 0.5 * (0.30 + 0.70 * prof) * (0.85 + rng() * 0.3);
    // Lee face half what it was, and the crest line pushed most of the way out
    // onto it. The terrain's own dunes now carry a straight slip face with a
    // brink at the top of it, and a feature dune sitting in that field with a
    // gently rounded back read as a different landform standing on it.
    const wB = 0.5 * (0.09 + 0.19 * prof) * (0.85 + rng() * 0.3);
    const zc = (rng() - 0.5) * 0.10;
    ridge.push(mound.useBlend(1).addVertex(t - 0.5, h, zc - wB * 0.62, 0, 1, 0));
    skirtA.push(mound.useBlend(0).addVertex(t - 0.5, 0, zc + wA, 0, 1, 0));
    skirtB.push(mound.useBlend(0).addVertex(t - 0.5, 0, zc - wB, 0, 1, 0));
  }
  mound.useBlend(0);
  for (let i = 0; i < N - 1; i++) {
    mound.addQuad(skirtA[i], skirtA[i + 1], ridge[i + 1], ridge[i]);
    mound.addQuad(ridge[i], ridge[i + 1], skirtB[i + 1], skirtB[i]);
  }
  mound.addTri(ridge[0], skirtB[0], skirtA[0]);
  mound.addTri(ridge[N - 1], skirtA[N - 1], skirtB[N - 1]);
  mound.computeSmoothNormals();

  const m = new MeshData();
  m.merge(mound);
  for (let i = 0; i < 3; i++) {
    const bx = (rng() - 0.6) * 0.7;
    const a = rng() * 6.283;
    const len = 0.5 + rng() * 0.7;
    addRod(m,
      [bx, 0.1, (rng() - 0.5) * 0.2],
      [bx + Math.cos(a) * len * 0.45, 0.35 + len, Math.sin(a) * len * 0.45],
      0.045, 0.022, 3, 0, 0);
  }
  return m;
}

/**
 * Bone midden: a heaped mound with long bones spilling out of it. The mound
 * takes the primary colour — bone that has been in the ash long enough to stain
 * — and the loose bones the bleached secondary. 80 triangles.
 */
export function buildBoneMidden(rng) {
  const m = new MeshData();
  m.merge(buildRock(0, 0.30, rng), 0, 0, 0, 0.95, 0.80, 0.85, 0);
  for (let i = 0; i < 5; i++) {
    const a = rng() * 6.283;
    const r = 0.18 + rng() * 0.34;
    const bx = Math.cos(a) * r, bz = Math.sin(a) * r;
    addRod(m,
      [bx, 0.04 + rng() * 0.12, bz],
      [bx + Math.cos(a) * 0.34, 0.16 + rng() * 0.80, bz + Math.sin(a) * 0.34],
      0.05, 0.035, 3, 1, 1);
  }
  return m;
}

/**
 * Cairn: five courses of flat stone, each smaller and slightly offset from the
 * one below, leaning as a hand-stacked pile does. Courses alternate colour so
 * the stack bands, which is what makes it read as built rather than dropped —
 * and a cairn on a rise is the cheapest thing in the game that tells the player
 * someone has walked here before. 65 triangles.
 */
export function buildCairn(rng) {
  const m = new MeshData();
  const n = 5;
  const lean = (rng() - 0.5) * 0.18;
  let y = 0;
  for (let s = 0; s < 5; s++) {
    const t = s / 4;
    const rad = 0.5 * (1 - t * 0.62);
    const h = (0.24 - t * 0.06) * (0.7 + rng() * 0.6);
    const cx = lean * t + (rng() - 0.5) * 0.06;
    const cz = lean * t * 0.6 + (rng() - 0.5) * 0.06;
    const a0 = rng() * 6.283;
    const bot = groundRing(n, cx, cz, rad, y, a0, rng, 0.20);
    const top = bot.map((p) => [p[0] * 0.94, y + h, p[2] * 0.94]);
    const b = s & 1;
    for (let i = 0; i < n; i++) {
      const j = (i + 1) % n;
      flatQuad(m, bot[i], bot[j], top[j], top[i], b, b);
    }
    const c = [cx, y + h, cz];
    for (let i = 0; i < n; i++) flatTri(m, c, top[i], top[(i + 1) % n], b, b, b);
    y += h;
  }
  return m;
}

/**
 * Drystone field wall, one unit long along x, meant to be chained into a run.
 *
 * The top line is jittered station by station and one station is dropped to
 * near ground level, so every segment is a different broken profile and a run
 * of them reads as a wall that has been falling down for a century rather than
 * a fence built this morning. The top course takes the secondary colour —
 * weathered cap stone, or turf where the wall is really a hedgebank.
 * 50 triangles.
 */
export function buildFieldWall(rng) {
  const m = new MeshData();
  const N = 7;
  const gap = 1 + Math.floor(rng() * (N - 2));   // the course that has collapsed
  const top = [], loA = [], loB = [];
  for (let i = 0; i < N; i++) {
    const x = i / (N - 1) - 0.5;
    const w = 0.5 * (0.72 + rng() * 0.28);
    const h = i === gap ? 0.16 + rng() * 0.12 : 0.72 + rng() * 0.28;
    const zc = (rng() - 0.5) * 0.12;
    top.push([[x, h, zc + w * 0.62], [x, h, zc - w * 0.62]]);
    loA.push([x, -0.15, zc + w]);
    loB.push([x, -0.15, zc - w]);
  }
  for (let i = 0; i < N - 1; i++) {
    flatQuad(m, loA[i], loA[i + 1], top[i + 1][0], top[i][0], 0, 1);
    flatQuad(m, top[i][1], top[i + 1][1], loB[i + 1], loB[i], 1, 0);
    flatQuad(m, top[i][0], top[i + 1][0], top[i + 1][1], top[i][1], 1, 1);
  }
  flatTri(m, loA[0], top[0][0], top[0][1], 0, 1, 1);
  flatTri(m, loA[0], top[0][1], loB[0], 0, 1, 0);
  flatTri(m, top[N - 1][0], loA[N - 1], loB[N - 1], 1, 0, 0);
  flatTri(m, top[N - 1][0], loB[N - 1], top[N - 1][1], 1, 0, 1);
  return m;
}

/**
 * Every land-feature mesh, keyed by the FEATURE id foliage.js scatters, in the
 * same order — kept here so geometry and id table cannot drift apart.
 * @param {function(): number} rng
 * @returns {Array<MeshData>}
 */
export function buildFeatureMeshes(rng) {
  return [
    buildOutcrop(rng),
    buildThicket(rng),
    buildReedBed(rng),
    buildAshDune(rng),
    buildBoneMidden(rng),
    buildCairn(rng),
    buildFieldWall(rng),
  ];
}

// ---------------------------------------------------------------------------
//  Character primitives
//
//  A skeleton assembled from boxes reads as a stack of boxes, and at the thirty
//  metres a phone screen actually shows an enemy at, silhouette is the only
//  thing left. These five shapes are what the rig draws instead of a box, each
//  in its own instanced batch — so a twelve-enemy fight is six draw calls
//  rather than one per limb.
//
//  They all follow the unit convention above, so a bone's (w, len, d) still
//  maps straight onto the instance scale, and they are all a hexagonal
//  cross-section lofted through a table of rings. That is deliberate: the
//  difference between a blade and a ribcage is the ring table plus the
//  non-uniform scale the bone applies, not a second vertex format.
// ---------------------------------------------------------------------------

/**
 * Hexagonal cross-section, flat front and back with chamfered sides, spanning
 * the full [-0.5, 0.5] in both axes so `w` and `d` mean what they say. Squashed
 * along z by a bone it becomes a blade; left square it becomes a torso.
 */
const HEX = [
  [0.5, 0], [0.25, 0.5], [-0.25, 0.5],
  [-0.5, 0], [-0.25, -0.5], [0.25, -0.5],
];

/** Ring k of `profile`: scaled, slid back by `dz`, front half pushed by `fz`. */
function ringPoint(profile, ring, i, out) {
  const px = profile[i][0], pz = profile[i][1];
  out[0] = px * (ring.sx !== undefined ? ring.sx : 1);
  out[1] = ring.y;
  out[2] = pz * (ring.sz !== undefined ? ring.sz : 1) + (ring.dz || 0);
  if (pz > 0 && ring.fz) out[2] += ring.fz;
  return out;
}

/**
 * Loft a closed convex profile through a stack of rings.
 *
 * A ring is `{ y, sx, sz, dz, fz }`: `dz` slides the whole ring fore or aft
 * (the curve of a back), `fz` pushes only the front half (a jaw, a muzzle).
 * Winding and cap order match buildBevelBox so every mesh in the game agrees
 * on which way is out.
 *
 * @param {MeshData} m
 * @param {Array<Array<number>>} profile  XZ points, counter-clockwise
 * @param {Array<object>} rings           bottom to top
 * @param {object} [opts]  apexY: close the bottom with a point at that height;
 *                         blendAt(ringIndex): per-ring colour/material slot
 */
function loftRings(m, profile, rings, opts = {}) {
  const n = profile.length;
  const nr = rings.length;
  const a = [0, 0, 0], b = [0, 0, 0], p = [0, 0, 0];
  const blendAt = opts.blendAt || (() => 0);
  const ringIdx = [];

  for (let k = 0; k < nr; k++) {
    m.useBlend(blendAt(k));
    const idx = [];
    for (let i = 0; i < n; i++) {
      ringPoint(profile, rings[k], i, p);
      ringPoint(profile, rings[k], (i + n - 1) % n, a);
      ringPoint(profile, rings[k], (i + 1) % n, b);
      // Horizontal normal: the mean of the two edge normals meeting here, each
      // normalised first so a long edge cannot drag a corner around.
      const n1x = p[2] - a[2], n1z = -(p[0] - a[0]);
      const n2x = b[2] - p[2], n2z = -(b[0] - p[0]);
      const l1 = Math.hypot(n1x, n1z) || 1, l2 = Math.hypot(n2x, n2z) || 1;
      let hx = n1x / l1 + n2x / l2, hz = n1z / l1 + n2z / l2;
      const hl = Math.hypot(hx, hz) || 1;
      hx /= hl; hz /= hl;
      // Tilt by how fast the profile is opening or closing, so a taper shades
      // as a cone instead of as a cylinder with a seam.
      ringPoint(profile, rings[Math.max(0, k - 1)], i, a);
      ringPoint(profile, rings[Math.min(nr - 1, k + 1)], i, b);
      const dy = b[1] - a[1];
      const ny = dy > 1e-5 ? -((b[0] - a[0]) * hx + (b[2] - a[2]) * hz) / dy : 0;
      const l = Math.hypot(hx, ny, hz) || 1;
      idx.push(m.addVertex(p[0], p[1], p[2], hx / l, ny / l, hz / l));
    }
    ringIdx.push(idx);
  }

  for (let k = 0; k < nr - 1; k++) {
    for (let i = 0; i < n; i++) {
      const j = (i + 1) % n;
      m.addQuad(ringIdx[k][i], ringIdx[k][j], ringIdx[k + 1][j], ringIdx[k + 1][i]);
    }
  }

  m.useBlend(blendAt(0));
  if (opts.apexY !== undefined) {
    const apex = m.addVertex(0, opts.apexY, rings[0].dz || 0, 0, -1, 0);
    for (let i = 0; i < n; i++) m.addTri(apex, ringIdx[0][(i + 1) % n], ringIdx[0][i]);
  } else if (opts.capBottom !== false) {
    const cap = [];
    for (let i = 0; i < n; i++) {
      ringPoint(profile, rings[0], i, p);
      cap.push(m.addVertex(p[0], p[1], p[2], 0, -1, 0));
    }
    for (let i = 1; i < n - 1; i++) m.addTri(cap[0], cap[i + 1], cap[i]);
  }
  if (opts.capTop !== false) {
    m.useBlend(blendAt(nr - 1));
    const cap = [];
    for (let i = 0; i < n; i++) {
      ringPoint(profile, rings[nr - 1], i, p);
      cap.push(m.addVertex(p[0], p[1], p[2], 0, 1, 0));
    }
    for (let i = 1; i < n - 1; i++) m.addTri(cap[0], cap[i], cap[i + 1]);
  }
  m.useBlend(0);
  return m;
}

/**
 * Arm or leg segment: widest at the joint it hangs from, with a slight swell
 * just below it for muscle, narrowing to the next joint. 32 triangles.
 * @param {number} [tip] width at the far end, as a fraction of the joint
 */
export function buildTaperedLimb(tip = 0.56) {
  const m = new MeshData();
  return loftRings(m, HEX, [
    { y: 0.00, sx: 1.00, sz: 1.00 },
    { y: 0.34, sx: 0.96, sz: 0.96 },
    { y: 1.00, sx: tip, sz: tip },
  ]);
}

/**
 * Torso: narrow at the waist, widest across the shoulders, and leaning very
 * slightly back as it rises. That back curve is what stops a standing
 * character reading as a stack of crates. 44 triangles.
 */
export function buildTorso() {
  const m = new MeshData();
  return loftRings(m, HEX, [
    { y: 0.00, sx: 0.76, sz: 0.82, dz: 0.020 },   // waist
    { y: 0.42, sx: 0.84, sz: 0.90, dz: -0.005 },  // ribs
    { y: 0.80, sx: 1.00, sz: 0.92, dz: -0.030 },  // shoulders
    { y: 1.00, sx: 0.92, sz: 0.78, dz: -0.055 },  // collar
  ]);
}

/**
 * Skull: a jaw that jutts ahead of a receding chin, a brow at its widest, and
 * a crown that tapers away. The jaw rings take the secondary colour slot, so a
 * helm can carry a dark visor band or a beast a bone muzzle for free.
 * 44 triangles.
 */
export function buildSkull() {
  const m = new MeshData();
  return loftRings(m, HEX, [
    { y: 0.00, sx: 0.58, sz: 0.52, fz: 0.10 },    // chin
    { y: 0.32, sx: 0.90, sz: 0.80, fz: 0.10 },    // jaw and cheek
    { y: 0.70, sx: 1.00, sz: 0.96, dz: -0.02 },   // brow
    { y: 1.00, sx: 0.70, sz: 0.68, dz: -0.06 },   // crown
  ], { blendAt: (k) => (k < 2 ? 1 : 0) });
}

/**
 * Pauldron: a domed cap, apex at the joint, flaring to a rim at the far end.
 * On a shoulder bone (which hangs downward) that is a plate covering the top
 * of the arm — the one shape that makes a soldier read as armoured at thirty
 * metres. 46 triangles.
 */
export function buildPauldron() {
  const m = new MeshData();
  return loftRings(m, HEX, [
    { y: 0.10, sx: 0.46, sz: 0.46 },
    { y: 0.42, sx: 0.78, sz: 0.78 },
    { y: 0.78, sx: 0.96, sz: 0.96 },
    { y: 1.00, sx: 1.00, sz: 1.00 },
  ], { apexY: 0 });
}

/**
 * Flat slab that runs straight for most of its length and then chamfers to an
 * edge: a blade, a tasset, a cape panel, a shield face, a helmet crest. The
 * chamfer takes the secondary slot so a blade's edge can be brighter steel
 * than its flat. 32 triangles.
 * @param {number} [tipW] width at the tip
 * @param {number} [tipT] thickness at the tip
 */
export function buildPlateSlab(tipW = 0.76, tipT = 0.30) {
  const m = new MeshData();
  return loftRings(m, HEX, [
    { y: 0.00, sx: 1.00, sz: 1.00 },
    { y: 0.86, sx: 1.00, sz: 1.00 },
    { y: 1.00, sx: tipW, sz: tipT },
  ], { blendAt: (k) => (k === 2 ? 1 : 0) });
}

/**
 * Batch name for each character primitive. rig.js re-exports this as PART and
 * bones name their shape with it; game.js registers one batch per entry. The
 * three have to agree, so the strings live here, next to the geometry.
 */
export const CHAR_PART = {
  BOX: 'box',
  LIMB: 'limb',
  TORSO: 'torso',
  SKULL: 'skull',
  PAULDRON: 'pauldron',
  PLATE: 'plate',
};

/**
 * Every character primitive, keyed by its batch name. The box is not included:
 * it is registered separately because props use it too.
 * @returns {Object<string, MeshData>}
 */
export function buildCharacterParts() {
  return {
    [CHAR_PART.LIMB]: buildTaperedLimb(),
    [CHAR_PART.TORSO]: buildTorso(),
    [CHAR_PART.SKULL]: buildSkull(),
    [CHAR_PART.PAULDRON]: buildPauldron(),
    [CHAR_PART.PLATE]: buildPlateSlab(),
  };
}

/** Flat XZ quad, unit sized, centred — used for water tiles and decals. */
export function buildPlane(res = 1) {
  const m = new MeshData();
  for (let z = 0; z <= res; z++) {
    for (let x = 0; x <= res; x++) {
      m.addVertex(x / res - 0.5, 0, z / res - 0.5, 0, 1, 0);
    }
  }
  const stride = res + 1;
  for (let z = 0; z < res; z++) {
    for (let x = 0; x < res; x++) {
      const a = z * stride + x;
      m.addQuad(a, a + 1, a + stride + 1, a + stride);
    }
  }
  return m;
}

// ---------------------------------------------------------------------------
//  Composite props
// ---------------------------------------------------------------------------

/**
 * Broadleaf tree: tapered trunk plus stacked, offset canopy blobs.
 * The canopy uses subdivision 0 icospheres (20 faces each) — at the distances
 * trees are actually viewed, the extra subdivision was invisible and cost
 * three quarters of the frame's triangle budget.
 */
export function buildBroadleafTree(rng) {
  const m = new MeshData();
  const trunk = buildCylinder(5, 0.24, 0.42);
  m.merge(trunk, 0, 0, 0, 1.0, 3.4, 1.0, 0);

  // Root plate: a flare of buttress roots spreading out of the trunk foot.
  //
  // A broadleaf standing in deep soil does not meet the ground on a line, and
  // the line was costing more than it looked. Where a tree meets the floor is
  // the darkest place in a wood — it is the middle of the tree's own shadow —
  // so it is exactly where the frame has nothing to say, and a hard silhouette
  // edge against flat shade is all the eye gets. Fourteen faceted triangles at
  // the base give that shadow something with a lit side and a turned-away side.
  //
  // Alternating the foot radius makes spurs rather than a smooth cone, and the
  // knee heights vary per spur, so no two panels take the light at the same
  // angle. The knee ring sits inside the pentagonal trunk's inscribed radius
  // (0.42 * cos 36 deg at the foot) so the flare emerges from under the bark
  // instead of leaving a visible ledge, and the foot sits below y = 0 so it
  // stays bedded when the ground tilts under it.
  const rootN = 7;
  const rr = subRng(0x2c91d7);
  const a0 = rr() * 6.283;
  const foot = [], knee = [];
  for (let i = 0; i < rootN; i++) {
    const a = a0 - (i / rootN) * Math.PI * 2;   // clockwise: see groundRing
    const spur = (i & 1) === 0 ? 0.98 : 0.62;
    const r = spur * (0.80 + rr() * 0.34);
    // Bedded deep, not just below zero. The foot ring is over a metre out on
    // the long spurs, and the ground under a tree in the Whispering Wood is
    // rarely level across that span: measured against the real height field,
    // a foot at -0.12 left 23% of the rim hanging in the air and 10% of it
    // more than a hand's width up. -0.28 takes that to 6% and 2%, and what it
    // costs is only the part of the flare that was underground anyway — on the
    // flat the spur still breaks the surface at twice the trunk radius.
    foot.push([Math.cos(a) * r, -0.28, Math.sin(a) * r]);
    knee.push([Math.cos(a) * 0.28, 0.40 + rr() * 0.34, Math.sin(a) * 0.28]);
  }
  for (let i = 0; i < rootN; i++) {
    const j = (i + 1) % rootN;
    flatQuad(m, foot[i], foot[j], knee[j], knee[i], 0, 0);
  }

  m.useBlend(1);

  const blobCount = 3 + Math.floor(rng() * 2);
  for (let i = 0; i < blobCount; i++) {
    const blob = buildRock(0, 0.20, rng);
    const a = (i / blobCount) * Math.PI * 2 + rng() * 0.8;
    const r = i === 0 ? 0 : 0.55 + rng() * 0.5;
    const s = (i === 0 ? 2.5 : 1.7 + rng() * 0.8);
    m.merge(blob,
      Math.cos(a) * r, 2.5 + rng() * 0.9 + (i === 0 ? 0.3 : 0), Math.sin(a) * r,
      s, s * 0.85, s);
  }
  return m;
}

/** Distant tree: one trunk, one blob. ~40 triangles instead of ~140. */
export function buildTreeFar(rng) {
  const m = new MeshData();
  m.merge(buildCylinder(4, 0.22, 0.38), 0, 0, 0, 1, 3.0, 1, 0);
  m.merge(buildRock(0, 0.15, rng), 0, 2.4, 0, 3.4, 2.6, 3.4, 1);
  return m;
}

/** Distant conifer: trunk plus a single tall cone. */
export function buildConiferFar() {
  const m = new MeshData();
  m.merge(buildCylinder(4, 0.14, 0.28), 0, 0, 0, 1, 2.2, 1, 0);
  m.merge(buildCone(5), 0, 1.1, 0, 2.4, 4.0, 2.4, 1);
  return m;
}

/** Conifer: straight bole with three descending skirts. */
export function buildConiferTree(rng) {
  const m = new MeshData();
  m.merge(buildCylinder(6, 0.14, 0.30), 0, 0, 0, 1, 4.2, 1, 0);
  m.useBlend(1);
  const tiers = 3 + Math.floor(rng() * 2);
  for (let i = 0; i < tiers; i++) {
    const t = i / tiers;
    const y = 1.1 + t * 3.2;
    const w = (2.6 - t * 1.6) * (0.9 + rng() * 0.25);
    const h = 1.7 - t * 0.4;
    m.merge(buildCone(7), 0, y, 0, w, h, w);
  }
  return m;
}

/** Dead tree: bare bole with a few angled branches. */
export function buildDeadTree(rng) {
  const m = new MeshData();
  m.merge(buildCylinder(5, 0.10, 0.34), 0, 0, 0, 1, 3.6 + rng() * 1.2, 1);
  const branches = 3 + Math.floor(rng() * 3);
  for (let i = 0; i < branches; i++) {
    const a = rng() * Math.PI * 2;
    const y = 1.4 + rng() * 1.8;
    const len = 0.9 + rng() * 0.9;
    const br = buildCylinder(4, 0.04, 0.11);
    // Cheap slanted branch: stretch along the branch axis and skew via merge offsets.
    const steps = 4;
    for (let s = 0; s < steps; s++) {
      const f = s / steps;
      m.merge(br,
        Math.cos(a) * len * f, y + f * 0.75, Math.sin(a) * len * f,
        0.35, len * 0.4, 0.35);
    }
  }
  return m;
}

export function buildBush(rng) {
  const m = new MeshData();
  const n = 2 + Math.floor(rng() * 2);
  for (let i = 0; i < n; i++) {
    const a = rng() * Math.PI * 2;
    const r = i === 0 ? 0 : 0.25 + rng() * 0.3;
    const s = 0.8 + rng() * 0.5;
    m.merge(buildRock(1, 0.25, rng), Math.cos(a) * r, rng() * 0.15, Math.sin(a) * r, s, s * 0.8, s);
  }
  return m;
}

/** Ruined pillar: stacked drums with a broken top. */
export function buildPillar(rng) {
  const m = new MeshData();
  const drums = 2 + Math.floor(rng() * 4);
  let y = 0;
  for (let i = 0; i < drums; i++) {
    const h = 0.7 + rng() * 0.5;
    const r = 0.42 - i * 0.02;
    m.merge(buildCylinder(8, r, r + 0.02), (rng() - 0.5) * 0.08, y, (rng() - 0.5) * 0.08, 1, h, 1);
    y += h;
  }
  m.merge(buildRock(0, 0.4, rng), 0, y - 0.1, 0, 0.9, 0.5, 0.9);
  return m;
}

export function buildCampfire() {
  const m = new MeshData();
  for (let i = 0; i < 6; i++) {
    const a = (i / 6) * Math.PI * 2;
    m.merge(buildBevelBox(0.2), Math.cos(a) * 0.55, 0, Math.sin(a) * 0.55, 0.34, 0.22, 0.34);
  }
  m.useBlend(1);
  for (let i = 0; i < 4; i++) {
    const a = (i / 4) * Math.PI * 2 + 0.4;
    m.merge(buildCylinder(4, 0.05, 0.09), Math.cos(a) * 0.16, 0.05, Math.sin(a) * 0.16, 1, 0.62, 1, 1);
  }
  return m;
}

/** The player's checkpoint marker: a sword driven into a low stone dais. */
export function buildGrace() {
  const m = new MeshData();
  m.merge(buildCylinder(10, 0.85, 1.0), 0, 0, 0, 1, 0.22, 1, 0);
  m.merge(buildCylinder(9, 0.55, 0.68), 0, 0.22, 0, 1, 0.14, 1, 0);
  m.merge(buildBevelBox(0.25), 0, 0.30, 0, 0.13, 1.5, 0.05, 1);   // blade
  m.merge(buildBevelBox(0.3), 0, 1.42, 0, 0.55, 0.09, 0.11, 1);   // crossguard
  m.merge(buildCylinder(6, 0.06, 0.06), 0, 1.50, 0, 1, 0.34, 1, 0); // grip
  m.merge(buildRock(1, 0.1, () => 0.5), 0, 1.82, 0, 0.2, 0.2, 0.2, 1); // pommel
  return m;
}

export function buildChest() {
  const m = new MeshData();
  m.merge(buildBevelBox(0.08), 0, 0, 0, 1.1, 0.62, 0.75, 0);
  m.merge(buildCylinder(8, 0.5, 0.5), 0, 0.62, 0, 1.1, 0.34, 0.75, 0); // simplified curved lid
  m.merge(buildBevelBox(0.2), 0, 0.28, 0.38, 0.20, 0.30, 0.08, 1);     // lock plate
  return m;
}

/** Simple gabled hut used for villages and camps. */
export function buildHut(rng) {
  const m = new MeshData();
  m.merge(buildBevelBox(0.04), 0, 0, 0, 4.2, 2.4, 3.6, 0);
  // Roof: two slabs leaning toward each other, approximated by a wide cone.
  m.merge(buildCone(4), 0, 2.35, 0, 6.2, 1.9, 5.4, 1);
  m.merge(buildBevelBox(0.1), 0, 0, 1.82, 1.0, 1.75, 0.16, 1);  // door frame
  if (rng() < 0.5) m.merge(buildCylinder(6, 0.28, 0.34), 1.4, 2.2, -0.8, 1, 1.6, 1, 0); // chimney
  return m;
}

export function buildWatchtower() {
  const m = new MeshData();
  m.merge(buildCylinder(8, 1.5, 1.9), 0, 0, 0, 1, 6.5, 1);
  m.merge(buildCylinder(9, 2.3, 2.0), 0, 6.5, 0, 1, 0.9, 1);
  for (let i = 0; i < 8; i++) {
    const a = (i / 8) * Math.PI * 2;
    m.merge(buildBevelBox(0.15), Math.cos(a) * 2.05, 7.4, Math.sin(a) * 2.05, 0.5, 0.75, 0.5);
  }
  return m;
}

/** Broken archway — the silhouette that marks ruins from a distance. */
export function buildArch() {
  const m = new MeshData();
  m.merge(buildBevelBox(0.1), -2.0, 0, 0, 1.0, 5.2, 1.2);
  m.merge(buildBevelBox(0.1), 2.0, 0, 0, 1.0, 4.4, 1.2);
  const segs = 7;
  for (let i = 0; i <= segs; i++) {
    const t = i / segs;
    const a = Math.PI * t;
    m.merge(buildBevelBox(0.1),
      -Math.cos(a) * 2.0, 5.0 + Math.sin(a) * 1.4, 0,
      0.85, 0.7, 1.2);
  }
  return m;
}

// ---------------------------------------------------------------------------
//  GPU mesh
// ---------------------------------------------------------------------------

export class GpuMesh {
  constructor(glw, meshData) {
    const gl = glw.gl;
    const t = meshData.toTyped();
    this.glw = glw;
    this.posBuf = glw.vbo(t.positions);
    this.normBuf = glw.vbo(t.normals);
    this.blendBuf = glw.vbo(t.blends);
    this.idxBuf = glw.ibo(t.indices);
    this.indexCount = t.indexCount;
    this.indexType = t.indices instanceof Uint32Array ? gl.UNSIGNED_INT : gl.UNSIGNED_SHORT;
    this.triangleCount = t.indexCount / 3;

    // Bounding sphere for culling.
    let cx = 0, cy = 0, cz = 0;
    const n = t.positions.length / 3;
    for (let i = 0; i < t.positions.length; i += 3) {
      cx += t.positions[i]; cy += t.positions[i + 1]; cz += t.positions[i + 2];
    }
    cx /= n; cy /= n; cz /= n;
    let r2 = 0;
    for (let i = 0; i < t.positions.length; i += 3) {
      const dx = t.positions[i] - cx, dy = t.positions[i + 1] - cy, dz = t.positions[i + 2] - cz;
      r2 = Math.max(r2, dx * dx + dy * dy + dz * dz);
    }
    this.center = { x: cx, y: cy, z: cz };
    this.radius = Math.sqrt(r2);
  }

  bindGeometry(prog) {
    const gl = this.glw.gl;
    const a = prog.attribs;
    gl.bindBuffer(gl.ARRAY_BUFFER, this.posBuf);
    gl.enableVertexAttribArray(a.aPos);
    gl.vertexAttribPointer(a.aPos, 3, gl.FLOAT, false, 0, 0);
    this.glw.vertexAttribDivisorFn(a.aPos, 0);
    if (a.aNormal !== undefined && a.aNormal >= 0) {
      gl.bindBuffer(gl.ARRAY_BUFFER, this.normBuf);
      gl.enableVertexAttribArray(a.aNormal);
      gl.vertexAttribPointer(a.aNormal, 3, gl.FLOAT, false, 0, 0);
      this.glw.vertexAttribDivisorFn(a.aNormal, 0);
    }
    if (a.aBlend !== undefined && a.aBlend >= 0) {
      gl.bindBuffer(gl.ARRAY_BUFFER, this.blendBuf);
      gl.enableVertexAttribArray(a.aBlend);
      gl.vertexAttribPointer(a.aBlend, 1, gl.FLOAT, false, 0, 0);
      this.glw.vertexAttribDivisorFn(a.aBlend, 0);
    }
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, this.idxBuf);
  }

  dispose() {
    const gl = this.glw.gl;
    gl.deleteBuffer(this.posBuf);
    gl.deleteBuffer(this.normBuf);
    gl.deleteBuffer(this.blendBuf);
    gl.deleteBuffer(this.idxBuf);
  }
}
