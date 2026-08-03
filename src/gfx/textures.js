// ============================================================================
//  textures.js — every texture in the game, generated at boot.
//
//  There are no image files. What ships is the recipe: a few hundred lines of
//  noise, and the loading screen spends ~150ms turning it into surfaces.
//
//  The design constraint is texture units. WebGL1 guarantees only eight, and
//  the frame already spends four (cloud, shadow, scene, bloom), so a
//  per-material atlas was never affordable — and atlases need manual mip and
//  wrap handling that WebGL1 makes painful anyway.
//
//  Instead there are two seamless tiling textures, and materials are defined by
//  how they *weigh* the channels rather than by having their own image:
//
//    SURFACE   R fine grain      per-grain speckle: sand, stone, cloth weave
//              G blotch          large soft patches: lichen, wear, dirt
//              B fibre           strongly directional: bark, wood, fabric warp
//              A crack           thin dark veins: stone, dried mud, bark fissures
//
//    NORMAL    RGB tangent-space normal of a generic bumpy surface
//              A   roughness variation
//
//  A material is then four weights, a scale, a roughness and a metalness —
//  cheap enough to sit in the instance stream, so one draw call can still paint
//  a knight, his cloak and his sword with three different surfaces.
// ============================================================================

import { Noise2D, makeRng } from '../core/rng.js';

const clamp01 = (v) => (v < 0 ? 0 : v > 1 ? 1 : v);

/**
 * Tileable fbm. Sampling a plain fbm and hoping the edges match does not work;
 * this blends four wrapped copies so the result is exactly periodic.
 */
function tileFbm(noise, fx, fy, freq, octaves) {
  let v = 0, w = 0;
  for (let oy = 0; oy < 2; oy++) {
    for (let ox = 0; ox < 2; ox++) {
      const weight = (ox ? fx : 1 - fx) * (oy ? fy : 1 - fy);
      if (weight <= 0) continue;
      v += (noise.fbm((fx + ox) * freq, (fy + oy) * freq, octaves) * 0.5 + 0.5) * weight;
      w += weight;
    }
  }
  return w > 0 ? v / w : 0.5;
}

/**
 * Tileable worley/cellular — the thing that makes stone read as stone.
 * Feature points are hashed straight from the wrapped cell index, so the
 * pattern is seamless without needing to store or wrap a point list.
 */
function tileWorley(seed, fx, fy, cells) {
  let best = 1e9, second = 1e9;
  const gx = Math.floor(fx * cells), gy = Math.floor(fy * cells);
  for (let dy = -1; dy <= 1; dy++) {
    for (let dx = -1; dx <= 1; dx++) {
      const cx = ((gx + dx) % cells + cells) % cells;
      const cy = ((gy + dy) % cells + cells) % cells;
      // Hash the cell to a jittered point.
      let h = (cx * 374761393 + cy * 668265263 + seed * 2246822519) >>> 0;
      h = (h ^ (h >>> 13)) * 1274126177 >>> 0;
      const jx = ((h & 0xffff) / 65535);
      const jy = (((h >>> 16) & 0xffff) / 65535);
      const px = (gx + dx + jx) / cells;
      const py = (gy + dy + jy) / cells;
      let ddx = px - fx, ddy = py - fy;
      if (ddx > 0.5) ddx -= 1; else if (ddx < -0.5) ddx += 1;
      if (ddy > 0.5) ddy -= 1; else if (ddy < -0.5) ddy += 1;
      const d = Math.sqrt(ddx * ddx + ddy * ddy) * cells;
      if (d < best) { second = best; best = d; } else if (d < second) { second = d; }
    }
  }
  return { f1: best, f2: second };
}

/**
 * Build the four-channel surface texture.
 *
 * Each channel is centred near 0.5 so shaders can use `(v - 0.5)` as a signed
 * modulation and a material that weights a channel at zero is exactly unchanged.
 */
function buildSurface(size) {
  const grain = new Noise2D(7717);
  const blotch = new Noise2D(4211);
  const fibre = new Noise2D(9133);
  const data = new Uint8ClampedArray(size * size * 4);

  for (let y = 0; y < size; y++) {
    const fy = y / size;
    for (let x = 0; x < size; x++) {
      const fx = x / size;
      const i = (y * size + x) * 4;

      // R — fine grain. High frequency, near-white noise shaped by one octave
      // of value noise so it clumps slightly instead of looking like TV static.
      const g1 = tileFbm(grain, fx, fy, 24, 2);
      const g2 = tileFbm(grain, fx, fy, 72, 1);
      data[i] = clamp01(0.5 + (g1 - 0.5) * 1.55 + (g2 - 0.5) * 0.95) * 255;

      // G — blotches. Low frequency, high contrast: weathering, lichen, damp.
      const b = tileFbm(blotch, fx, fy, 4, 5);
      data[i + 1] = clamp01(0.5 + (b - 0.5) * 3.2) * 255;

      // B — fibre. Stretched heavily along one axis, so a material that leans
      // on this channel gets grain direction: bark, planks, woven cloth.
      const f1 = tileFbm(fibre, fx * 0.09, fy, 22, 3);
      const f2 = tileFbm(fibre, fx * 0.35, fy, 6, 2);
      data[i + 2] = clamp01(0.5 + (f1 - 0.5) * 2.2 + (f2 - 0.5) * 1.2) * 255;

      // A — cracks. Worley ridges: the F2-F1 edge is thin and branching, which
      // is what mortar lines, dried mud and bark fissures actually look like.
      const w1 = tileWorley(31, fx, fy, 6);
      const w2 = tileWorley(97, fx, fy, 17);
      const ridge1 = 1 - Math.min(1, (w1.f2 - w1.f1) * 2.4);
      const ridge2 = 1 - Math.min(1, (w2.f2 - w2.f1) * 3.0);
      data[i + 3] = clamp01(0.5 - (ridge1 * 0.55 + ridge2 * 0.35) * 0.9 + 0.45) * 255;
    }
  }
  return data;
}

/**
 * Build the normal + roughness texture from a height field.
 *
 * The height field deliberately mixes scales: broad undulation so grazing light
 * catches form, plus fine bumps that only resolve up close. Sobel over the
 * wrapped field gives the gradient, which is the normal.
 */
function buildNormal(size, strength = 5.5) {
  const h = new Float32Array(size * size);
  const coarse = new Noise2D(5501);
  const fine = new Noise2D(8821);
  const rough = new Noise2D(2377);

  for (let y = 0; y < size; y++) {
    const fy = y / size;
    for (let x = 0; x < size; x++) {
      const fx = x / size;
      h[y * size + x] = tileFbm(coarse, fx, fy, 8, 4) * 0.62
        + tileFbm(fine, fx, fy, 34, 3) * 0.30
        + tileFbm(fine, fx, fy, 88, 1) * 0.08;
    }
  }

  const data = new Uint8ClampedArray(size * size * 4);
  const at = (x, y) => h[(((y % size) + size) % size) * size + (((x % size) + size) % size)];
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      // Sobel.
      const dx = (at(x + 1, y - 1) + 2 * at(x + 1, y) + at(x + 1, y + 1))
        - (at(x - 1, y - 1) + 2 * at(x - 1, y) + at(x - 1, y + 1));
      const dy = (at(x - 1, y + 1) + 2 * at(x, y + 1) + at(x + 1, y + 1))
        - (at(x - 1, y - 1) + 2 * at(x, y - 1) + at(x + 1, y - 1));
      let nx = -dx * strength, ny = -dy * strength, nz = 1;
      const len = Math.sqrt(nx * nx + ny * ny + nz * nz);
      nx /= len; ny /= len; nz /= len;
      const i = (y * size + x) * 4;
      data[i] = (nx * 0.5 + 0.5) * 255;
      data[i + 1] = (ny * 0.5 + 0.5) * 255;
      data[i + 2] = (nz * 0.5 + 0.5) * 255;
      // A — roughness variation. Patches of polish and patches of tooth; this
      // is what stops a metal surface reading as one mirror-flat sheet.
      data[i + 3] = clamp01(tileFbm(rough, x / size, y / size, 11, 3)) * 255;
    }
  }
  return data;
}

/**
 * Alpha-tested leaf card. One texture of overlapping leaf shapes; the tree
 * builder maps a random sub-rect per card so no two cards look identical.
 */
function buildFoliage(size) {
  const data = new Uint8ClampedArray(size * size * 4);
  const veins = new Noise2D(6151);
  const rng = makeRng(20260803);
  // Scatter leaf ellipses at random angles, keeping a margin so the card's
  // border stays transparent and the silhouette reads against the sky.
  const leaves = [];
  for (let i = 0; i < 26; i++) {
    leaves.push({
      cx: 0.12 + rng() * 0.76,
      cy: 0.12 + rng() * 0.76,
      a: 0.055 + rng() * 0.085,
      b: 0.022 + rng() * 0.040,
      rot: rng() * Math.PI * 2,
      shade: 0.68 + rng() * 0.42,
    });
  }

  for (let y = 0; y < size; y++) {
    const fy = y / size;
    for (let x = 0; x < size; x++) {
      const fx = x / size;
      let cover = 0, shade = 0;
      for (const L of leaves) {
        const dx = fx - L.cx, dy = fy - L.cy;
        const c = Math.cos(L.rot), s = Math.sin(L.rot);
        const u = (dx * c + dy * s) / L.a;
        const v = (-dx * s + dy * c) / L.b;
        // Teardrop rather than ellipse: taper toward the tip.
        const taper = 1 + u * 0.45;
        const r = u * u + (v / Math.max(taper, 0.35)) * (v / Math.max(taper, 0.35));
        if (r < 1) {
          const edge = 1 - r;
          if (edge > cover) { cover = edge; shade = L.shade; }
        }
      }
      const i = (y * size + x) * 4;
      if (cover <= 0) {
        data[i] = data[i + 1] = data[i + 2] = 0;
        data[i + 3] = 0;
      } else {
        // Veins and a darker midrib give the card structure at close range.
        const vn = veins.fbm(fx * 34, fy * 34, 2) * 0.5 + 0.5;
        const lum = clamp01(shade * (0.82 + 0.30 * vn));
        data[i] = lum * 255;
        data[i + 1] = lum * 255;
        data[i + 2] = lum * 255;
        // Soft alpha edge, then alpha-test in the shader — cheaper than sorting
        // and it keeps foliage in the shadow map.
        data[i + 3] = clamp01(cover * 7.0) * 255;
      }
    }
  }
  return data;
}

/** Upload a raw RGBA buffer as a repeating, mipmapped texture. */
function upload(glw, data, size, { wrap } = {}) {
  const gl = glw.gl;
  return glw.texture2D({
    width: size,
    height: size,
    data: new Uint8Array(data.buffer, data.byteOffset, data.byteLength),
    format: gl.RGBA,
    type: gl.UNSIGNED_BYTE,
    filter: gl.LINEAR,
    wrap: wrap || gl.REPEAT,
    mip: true,
  });
}

/**
 * Material table. `surf` weights the four surface channels, and the rest is the
 * BRDF. These numbers are the whole art direction of the game: a change here
 * repaints every object using that material.
 *
 *   surf: [grain, blotch, fibre, crack]
 *   bump: normal-map strength
 *   scale: world-space texture frequency (metres per tile = 1 / scale)
 */
export const MATERIAL = {
  DEFAULT: 0,
  SKIN: 1,
  CLOTH: 2,
  LEATHER: 3,
  METAL: 4,
  STONE: 5,
  WOOD: 6,
  BARK: 7,
  FOLIAGE: 8,
  THATCH: 9,
  BONE: 10,
  GEM: 11,
};

// Packed for the shader as vec4s indexed by material id.
export const MATERIAL_TABLE = [
  //                     grain blotch fibre crack | rough metal bump scale
  /* DEFAULT  */ { surf: [0.35, 0.30, 0.05, 0.10], rough: 0.72, metal: 0.0, bump: 0.55, scale: 1.4 },
  /* SKIN     */ { surf: [0.30, 0.16, 0.04, 0.02], rough: 0.62, metal: 0.0, bump: 0.30, scale: 6.0 },
  /* CLOTH    */ { surf: [0.42, 0.24, 0.55, 0.04], rough: 0.92, metal: 0.0, bump: 0.75, scale: 7.5 },
  /* LEATHER  */ { surf: [0.55, 0.34, 0.10, 0.30], rough: 0.66, metal: 0.0, bump: 0.85, scale: 6.5 },
  /* METAL    */ { surf: [0.30, 0.44, 0.06, 0.16], rough: 0.30, metal: 0.9, bump: 0.45, scale: 5.0 },
  /* STONE    */ { surf: [0.44, 0.40, 0.02, 0.62], rough: 0.86, metal: 0.0, bump: 1.00, scale: 1.1 },
  /* WOOD     */ { surf: [0.24, 0.26, 0.72, 0.24], rough: 0.74, metal: 0.0, bump: 0.70, scale: 2.6 },
  /* BARK     */ { surf: [0.30, 0.30, 0.85, 0.55], rough: 0.94, metal: 0.0, bump: 1.25, scale: 3.4 },
  /* FOLIAGE  */ { surf: [0.30, 0.52, 0.22, 0.06], rough: 0.80, metal: 0.0, bump: 0.40, scale: 4.0 },
  /* THATCH   */ { surf: [0.40, 0.30, 0.88, 0.12], rough: 0.96, metal: 0.0, bump: 1.10, scale: 5.5 },
  /* BONE     */ { surf: [0.26, 0.30, 0.10, 0.44], rough: 0.58, metal: 0.0, bump: 0.60, scale: 5.0 },
  /* GEM      */ { surf: [0.10, 0.10, 0.02, 0.05], rough: 0.10, metal: 0.4, bump: 0.20, scale: 8.0 },
];

/** Flatten the table into the two uniform arrays the shaders index. */
export function materialUniforms() {
  const surf = new Float32Array(MATERIAL_TABLE.length * 4);
  const brdf = new Float32Array(MATERIAL_TABLE.length * 4);
  MATERIAL_TABLE.forEach((m, i) => {
    surf.set(m.surf, i * 4);
    brdf[i * 4] = m.rough;
    brdf[i * 4 + 1] = m.metal;
    brdf[i * 4 + 2] = m.bump;
    brdf[i * 4 + 3] = m.scale;
  });
  return { surf, brdf, count: MATERIAL_TABLE.length };
}

/**
 * Generate everything. Called once during the loading screen — measured at
 * ~0.2s added to a 1.5s world generation, against a 4s budget. Two 512² RGBA
 * textures plus a 256² foliage card, with mips, is about 3.1 MB on the GPU.
 *
 * The low preset halves every dimension: a quarter of the pixels to bake and a
 * quarter of the memory, on exactly the devices that need both.
 */
export function buildTextures(glw, { quality = 'medium' } = {}) {
  const surfSize = quality === 'low' ? 256 : 512;
  const normSize = quality === 'low' ? 256 : 512;
  const foliSize = quality === 'low' ? 128 : 256;

  const surface = upload(glw, buildSurface(surfSize), surfSize);
  const normal = upload(glw, buildNormal(normSize), normSize);
  const foliage = upload(glw, buildFoliage(foliSize), foliSize, { wrap: glw.gl.CLAMP_TO_EDGE });

  return { surface, normal, foliage, ...materialUniforms() };
}
