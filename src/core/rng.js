// ============================================================================
//  rng.js — deterministic randomness and coherent noise.
//  Everything in the world (terrain, loot tables, encampment layouts) derives
//  from one seed, so a given seed always produces the same world.
// ============================================================================

/** Hash a string into a 32-bit unsigned seed. */
export function hashSeed(str) {
  let h = 2166136261 >>> 0;
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i);
    h = Math.imul(h, 16777619) >>> 0;
  }
  return h >>> 0;
}

/** Small, fast, well-distributed PRNG (mulberry32). */
export function makeRng(seed) {
  let a = seed >>> 0;
  const next = () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  next.range = (lo, hi) => lo + next() * (hi - lo);
  next.int = (lo, hi) => Math.floor(lo + next() * (hi - lo + 1));
  next.pick = (arr) => arr[Math.floor(next() * arr.length) % arr.length];
  next.chance = (p) => next() < p;
  /** Weighted pick. `items` are [value, weight] pairs. */
  next.weighted = (items) => {
    let total = 0;
    for (const it of items) total += it[1];
    let r = next() * total;
    for (const it of items) {
      r -= it[1];
      if (r <= 0) return it[0];
    }
    return items[items.length - 1][0];
  };
  /** Fisher-Yates, in place. */
  next.shuffle = (arr) => {
    for (let i = arr.length - 1; i > 0; i--) {
      const j = Math.floor(next() * (i + 1));
      const t = arr[i]; arr[i] = arr[j]; arr[j] = t;
    }
    return arr;
  };
  next.gaussian = () => {
    // Box-Muller; good enough for scatter jitter.
    let u = 0, v = 0;
    while (u === 0) u = next();
    while (v === 0) v = next();
    return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
  };
  return next;
}

// ---------------------------------------------------------------------------
//  Value / gradient noise
// ---------------------------------------------------------------------------

/**
 * Permutation-table gradient noise (Perlin-flavoured, 2D).
 * We build our own table from the seed so worlds are reproducible.
 */
export class Noise2D {
  constructor(seed) {
    const rng = makeRng(seed >>> 0);
    const p = new Uint8Array(256);
    for (let i = 0; i < 256; i++) p[i] = i;
    rng.shuffle(p);
    this.perm = new Uint8Array(512);
    this.permMod12 = new Uint8Array(512);
    for (let i = 0; i < 512; i++) {
      this.perm[i] = p[i & 255];
      this.permMod12[i] = this.perm[i] % 12;
    }
  }

  /** Raw noise in roughly [-1, 1]. */
  noise(x, y) {
    const X = Math.floor(x) & 255;
    const Y = Math.floor(y) & 255;
    const xf = x - Math.floor(x);
    const yf = y - Math.floor(y);
    const u = xf * xf * xf * (xf * (xf * 6 - 15) + 10);
    const v = yf * yf * yf * (yf * (yf * 6 - 15) + 10);
    const p = this.perm;
    const aa = p[p[X] + Y], ab = p[p[X] + Y + 1];
    const ba = p[p[X + 1] + Y], bb = p[p[X + 1] + Y + 1];
    const g = (h, dx, dy) => {
      switch (h & 7) {
        case 0: return dx + dy;
        case 1: return dx - dy;
        case 2: return -dx + dy;
        case 3: return -dx - dy;
        case 4: return dx;
        case 5: return -dx;
        case 6: return dy;
        default: return -dy;
      }
    };
    const x1 = g(aa, xf, yf) + u * (g(ba, xf - 1, yf) - g(aa, xf, yf));
    const x2 = g(ab, xf, yf - 1) + u * (g(bb, xf - 1, yf - 1) - g(ab, xf, yf - 1));
    return (x1 + v * (x2 - x1)) * 1.1;
  }

  /** Fractal Brownian motion. */
  fbm(x, y, octaves = 4, lacunarity = 2.0, gain = 0.5) {
    let amp = 1, freq = 1, sum = 0, norm = 0;
    for (let i = 0; i < octaves; i++) {
      sum += amp * this.noise(x * freq, y * freq);
      norm += amp;
      amp *= gain;
      freq *= lacunarity;
    }
    return sum / norm;
  }

  /** Ridged multifractal — produces mountain crests rather than rolling hills. */
  ridged(x, y, octaves = 4, lacunarity = 2.0, gain = 0.5) {
    let amp = 1, freq = 1, sum = 0, norm = 0;
    for (let i = 0; i < octaves; i++) {
      const n = 1 - Math.abs(this.noise(x * freq, y * freq));
      sum += amp * n * n;
      norm += amp;
      amp *= gain;
      freq *= lacunarity;
    }
    return sum / norm;
  }

  /** Domain-warped fbm: bends the noise field through itself for organic shapes. */
  warped(x, y, warp = 0.6, octaves = 5) {
    const wx = this.fbm(x + 5.2, y + 1.3, 3);
    const wy = this.fbm(x + 9.7, y + 4.1, 3);
    return this.fbm(x + warp * wx, y + warp * wy, octaves);
  }
}

/** Cheap deterministic hash for scattering — no table lookup, no allocation. */
export function hash2(x, y, seed = 0) {
  let h = Math.imul(x | 0, 0x27d4eb2d) ^ Math.imul(y | 0, 0x165667b1) ^ Math.imul(seed | 0, 0x9e3779b9);
  h = Math.imul(h ^ (h >>> 15), 0x85ebca6b);
  h = Math.imul(h ^ (h >>> 13), 0xc2b2ae35);
  return ((h ^ (h >>> 16)) >>> 0) / 4294967296;
}

/**
 * Poisson-ish scatter inside a cell grid: one jittered candidate per cell.
 * Cheap, deterministic, and produces even coverage without clumping.
 */
export function scatterInCell(cellX, cellY, cellSize, seed, index = 0) {
  const a = hash2(cellX, cellY, seed + index * 7919);
  const b = hash2(cellX + 31, cellY + 17, seed + index * 104729);
  return {
    x: (cellX + a) * cellSize,
    y: (cellY + b) * cellSize,
    r1: hash2(cellX + 101, cellY + 71, seed + index * 15485863),
    r2: hash2(cellX + 211, cellY + 149, seed + index * 32452843),
  };
}
