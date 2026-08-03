// ============================================================================
//  mesh.js — procedural geometry. Every model in the game is generated here;
//  there are no art assets to download, which keeps the whole game a few
//  hundred KB and makes it start instantly on a phone connection.
// ============================================================================

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
 * A tuft of three tapered blades fanned around the vertical axis.
 *
 * A single flat quad reads as a paper triangle from any angle the camera
 * happens to take; three crossed blades read as a clump of grass from all of
 * them, for 12 triangles instead of 4. That trade lets the scatter run at a
 * third of the instance count for a better result.
 */
export function buildGrassTuft() {
  const m = new MeshData();
  const blades = [
    { yaw: 0.0, lean: 0.10, h: 1.00, w: 1.00 },
    { yaw: 1.15, lean: -0.16, h: 0.82, w: 0.85 },
    { yaw: 2.30, lean: 0.22, h: 0.90, w: 0.78 },
  ];
  const widths = [0.5, 0.36, 0.17, 0.0];
  const heights = [0, 0.38, 0.74, 1.0];

  for (const b of blades) {
    const c = Math.cos(b.yaw), s = Math.sin(b.yaw);
    const nx = -s, nz = c;   // blade faces perpendicular to its own axis
    const rows = [];
    for (let i = 0; i < 4; i++) {
      const w = widths[i] * b.w;
      const y = heights[i] * b.h;
      // Lean grows with height so the blade curves rather than tilting rigidly.
      const bend = b.lean * heights[i] * heights[i];
      if (w === 0) {
        rows.push([m.addVertex(c * bend, y, s * bend, nx, 0.25, nz)]);
      } else {
        rows.push([
          m.addVertex(c * (bend - w), y, s * (bend - w), nx, 0.25, nz),
          m.addVertex(c * (bend + w), y, s * (bend + w), nx, 0.25, nz),
        ]);
      }
    }
    m.addQuad(rows[0][0], rows[0][1], rows[1][1], rows[1][0]);
    m.addQuad(rows[1][0], rows[1][1], rows[2][1], rows[2][0]);
    m.addTri(rows[2][0], rows[2][1], rows[3][0]);
  }
  return m;
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
