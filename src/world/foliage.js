// ============================================================================
//  foliage.js — deterministic vegetation and rock scatter.
//
//  Nothing is stored in the save file: every tree in Aldrath is a pure function
//  of (cell coordinate, world seed). Chunks cache their scatter the first time
//  they come into range and hold it until evicted, so revisiting an area gives
//  exactly the same forest.
//
//  Grass is handled differently — it lives in a rolling patch centred on the
//  player and is rebuilt only when they have moved far enough to matter.
// ============================================================================

import { hash2 } from '../core/rng.js';
import { CHUNK_SIZE, CHUNKS, WORLD_HALF, WATER_LEVEL, BIOME, BIOME_INFO } from './worldgen.js';
import { clamp, lerp, saturate } from '../core/math.js';

export const PROP = {
  TREE_BROAD: 0, TREE_CONIFER: 1, TREE_DEAD: 2,
  BUSH: 3, ROCK_S: 4, ROCK_L: 5, REED: 6,
};

/**
 * Ground clutter — the second, dense tier of the scatter. Props are landmarks
 * you navigate by; clutter is what stops the fifty metres between them reading
 * as a painted plane. Ids index both the mesh table in mesh.js and the batch
 * table in game.js, so the three stay in step.
 */
export const CLUTTER = {
  ROCK: 0,     // shattered stone, scree, pebble drift
  WOOD: 1,     // fallen branches, twigs, driftwood
  SCRUB: 2,    // tussocks, dry scrub, sedge
  BONE: 3,     // bone fields
  DRIFT: 4,    // ash, snow, blown sand piled against relief
  SLAB: 5,     // cracked ground plates
  STUMP: 6,    // stumps and standing scorched snags
};

/**
 * Clutter is stored packed rather than as objects: a loaded view holds tens of
 * thousands of items, and 60 bytes in one flat array beats an object header
 * each on a phone — both for memory and for the garbage collector, which must
 * not run mid-frame.
 *
 * Layout: type, x, y, z, yaw, sx, sy, sz, r, g, b, r2, g2, b2, phase
 */
export const CLUTTER_STRIDE = 15;

const PROP_CELL = 9;      // metres between scatter candidates
const CLUTTER_CELL = 2.5; // metres between clutter candidates

/** Per-biome scatter rules. Weights are relative within `trees`. */
const BIOME_SCATTER = {
  [BIOME.OCEAN]: { tree: 0, bush: 0, rock: 0.02, reed: 0, trees: [1, 0, 0] },
  [BIOME.BEACH]: { tree: 0.03, bush: 0.05, rock: 0.06, reed: 0.05, trees: [0.5, 0, 0.5] },
  [BIOME.MEADOW]: { tree: 0.15, bush: 0.22, rock: 0.07, reed: 0.02, trees: [0.85, 0.05, 0.10] },
  [BIOME.FOREST]: { tree: 0.62, bush: 0.30, rock: 0.05, reed: 0.02, trees: [0.72, 0.18, 0.10] },
  [BIOME.MARSH]: { tree: 0.22, bush: 0.26, rock: 0.03, reed: 0.42, trees: [0.35, 0.0, 0.65] },
  [BIOME.HIGHLAND]: { tree: 0.34, bush: 0.16, rock: 0.16, reed: 0.0, trees: [0.10, 0.82, 0.08] },
  [BIOME.CRAG]: { tree: 0.04, bush: 0.05, rock: 0.42, reed: 0.0, trees: [0.05, 0.55, 0.40] },
  [BIOME.SNOW]: { tree: 0.11, bush: 0.03, rock: 0.22, reed: 0.0, trees: [0.02, 0.78, 0.20] },
  [BIOME.ASH]: { tree: 0.17, bush: 0.05, rock: 0.20, reed: 0.0, trees: [0.02, 0.06, 0.92] },
};

/** Foliage palettes, sampled per instance and jittered. */
const LEAF_COLORS = {
  [BIOME.FOREST]: [[0.20, 0.40, 0.17], [0.25, 0.47, 0.19], [0.17, 0.34, 0.17]],
  [BIOME.MEADOW]: [[0.24, 0.42, 0.18], [0.30, 0.46, 0.20], [0.34, 0.44, 0.16]],
  [BIOME.MARSH]: [[0.22, 0.30, 0.14], [0.26, 0.32, 0.16], [0.18, 0.26, 0.15]],
  [BIOME.HIGHLAND]: [[0.18, 0.34, 0.24], [0.21, 0.39, 0.26], [0.16, 0.30, 0.22]],
  [BIOME.CRAG]: [[0.18, 0.26, 0.19], [0.20, 0.28, 0.20], [0.16, 0.24, 0.18]],
  [BIOME.SNOW]: [[0.15, 0.26, 0.22], [0.18, 0.29, 0.24], [0.13, 0.23, 0.21]],
  [BIOME.ASH]: [[0.22, 0.17, 0.14], [0.26, 0.20, 0.16], [0.19, 0.15, 0.13]],
  [BIOME.BEACH]: [[0.28, 0.40, 0.20], [0.32, 0.44, 0.22], [0.26, 0.38, 0.19]],
  [BIOME.OCEAN]: [[0.20, 0.30, 0.18], [0.22, 0.32, 0.20], [0.18, 0.28, 0.17]],
};

const BARK_COLORS = [[0.30, 0.22, 0.16], [0.35, 0.26, 0.18], [0.25, 0.19, 0.14]];

/**
 * Per-biome clutter budget. `d` is the chance a 2.5 m candidate cell is taken
 * before clumping, and `w` weights the kinds in CLUTTER order
 * [ROCK, WOOD, SCRUB, BONE, DRIFT, SLAB, STUMP].
 *
 * The Cinderwaste gets the highest budget of anywhere on the island. It is a
 * bare ash plain and it is meant to feel like one, but bleak is not the same as
 * empty: what makes ash country legible is drifts, burnt stumps, cracked plates
 * and bone — all of it grey, none of it flat.
 */
const CLUTTER_RULES = {
  [BIOME.OCEAN]: null,
  [BIOME.BEACH]: { d: 0.16, w: [0.30, 0.16, 0.12, 0.04, 0.30, 0.08, 0.00] },
  [BIOME.MEADOW]: { d: 0.44, w: [0.22, 0.12, 0.42, 0.02, 0.14, 0.04, 0.04] },
  [BIOME.FOREST]: { d: 0.34, w: [0.14, 0.32, 0.26, 0.03, 0.09, 0.04, 0.12] },
  [BIOME.MARSH]: { d: 0.40, w: [0.06, 0.20, 0.40, 0.04, 0.12, 0.02, 0.16] },
  [BIOME.HIGHLAND]: { d: 0.36, w: [0.32, 0.10, 0.30, 0.02, 0.14, 0.08, 0.04] },
  [BIOME.CRAG]: { d: 0.34, w: [0.50, 0.03, 0.09, 0.06, 0.10, 0.22, 0.00] },
  [BIOME.SNOW]: { d: 0.26, w: [0.34, 0.04, 0.06, 0.06, 0.36, 0.12, 0.02] },
  [BIOME.ASH]: { d: 0.42, w: [0.16, 0.08, 0.02, 0.20, 0.26, 0.16, 0.12] },
};

/** Largest `d` above — the cheap reject that runs before any terrain query. */
const CLUTTER_MAX_D = 0.44;

/** Bleached bone, and the pale splinter colour broken wood shows. */
const BONE_COLOR = [0.58, 0.56, 0.48];
const SPLINTER_COLOR = [0.44, 0.37, 0.27];

/**
 * Smooth value noise from the position hash — used to make clutter arrive in
 * patches. Uniform scatter is the thing that gives procedural worlds away:
 * debris collects, it does not sprinkle. Bilinear on a hashed lattice costs
 * four hashes and needs no stored field.
 */
function clumpNoise(x, z, seed, cellSize) {
  const fx = x / cellSize, fz = z / cellSize;
  const ix = Math.floor(fx), iz = Math.floor(fz);
  const tx = fx - ix, tz = fz - iz;
  const sx = tx * tx * (3 - 2 * tx), sz = tz * tz * (3 - 2 * tz);
  const a = hash2(ix, iz, seed), b = hash2(ix + 1, iz, seed);
  const c = hash2(ix, iz + 1, seed), d = hash2(ix + 1, iz + 1, seed);
  return lerp(lerp(a, b, sx), lerp(c, d, sx), sz);
}

export class Scatter {
  constructor(world) {
    this.world = world;
    this.cache = new Map();        // chunkKey -> array of props
    this.clutterCache = new Map(); // chunkKey -> packed Float32Array of clutter
    this.blockers = [];            // circles where scatter is suppressed (POIs)
    this._w = new Float64Array(7); // kind weights, reused per candidate
    this._n = { x: 0, y: 1, z: 0 };
    this.rebuildBlockers();
  }

  rebuildBlockers() {
    this.blockers.length = 0;
    for (const p of this.world.pois) {
      let r = 0;
      switch (p.kind) {
        case 'village': r = 46; break;
        case 'boss': r = 36; break;
        case 'mini': r = 24; break;
        case 'camp': r = 18; break;
        case 'ruin': r = 22; break;
        case 'grace': r = 13; break;
        case 'chest': r = 5; break;
        case 'shrine': r = 9; break;
        case 'merchant': case 'smith': r = 6; break;
        default: r = 0;
      }
      if (r > 0) this.blockers.push({ x: p.x, z: p.z, r2: r * r });
    }
  }

  _blocked(x, z) {
    for (let i = 0; i < this.blockers.length; i++) {
      const b = this.blockers[i];
      const dx = x - b.x, dz = z - b.z;
      if (dx * dx + dz * dz < b.r2) return true;
    }
    return false;
  }

  chunkKey(cx, cz) { return cz * CHUNKS + cx; }

  /** Build (or fetch cached) props for a terrain chunk. */
  propsFor(cx, cz) {
    const key = this.chunkKey(cx, cz);
    const hit = this.cache.get(key);
    if (hit) return hit;

    const world = this.world;
    const props = [];
    const ox = cx * CHUNK_SIZE - WORLD_HALF;
    const oz = cz * CHUNK_SIZE - WORLD_HALF;
    const cells = Math.ceil(CHUNK_SIZE / PROP_CELL);
    const baseCellX = Math.floor(ox / PROP_CELL);
    const baseCellZ = Math.floor(oz / PROP_CELL);

    for (let jz = 0; jz < cells; jz++) {
      for (let jx = 0; jx < cells; jx++) {
        const gx = baseCellX + jx;
        const gz = baseCellZ + jz;
        const r0 = hash2(gx, gz, world.seed);
        const r1 = hash2(gx + 5501, gz + 907, world.seed);
        const r2 = hash2(gx + 131, gz + 7717, world.seed);
        const r3 = hash2(gx + 313, gz + 1237, world.seed);
        const r4 = hash2(gx + 9377, gz + 41, world.seed);

        const x = (gx + r0) * PROP_CELL;
        const z = (gz + r1) * PROP_CELL;
        if (Math.abs(x) > WORLD_HALF - 8 || Math.abs(z) > WORLD_HALF - 8) continue;

        const h = world.heightAt(x, z);
        if (h < WATER_LEVEL + 0.4) continue;
        const slope = world.slopeAt(x, z);
        const biome = world.biomeAt(x, z);
        const rules = BIOME_SCATTER[biome] || BIOME_SCATTER[BIOME.MEADOW];
        if (world.roadAt(x, z) > 0.28) continue;
        if (this._blocked(x, z)) continue;

        // Local density variation so forests have clearings.
        const clump = world.moisture[world.gridIndex(
          Math.round(world.worldToGrid(x)), Math.round(world.worldToGrid(z)))];
        const densityMul = 0.55 + clump * 0.9;

        const slopeOk = 1 - saturate((slope - 0.22) / 0.34);
        let type = -1;

        if (r2 < rules.tree * densityMul * slopeOk) {
          const tw = rules.trees;
          const pick = r3 * (tw[0] + tw[1] + tw[2]);
          type = pick < tw[0] ? PROP.TREE_BROAD
            : pick < tw[0] + tw[1] ? PROP.TREE_CONIFER : PROP.TREE_DEAD;
        } else if (r2 < (rules.tree + rules.bush) * densityMul * slopeOk) {
          type = PROP.BUSH;
        } else if (r2 < rules.tree + rules.bush + rules.rock) {
          type = r3 < 0.72 ? PROP.ROCK_S : PROP.ROCK_L;
        } else if (rules.reed > 0 && r2 < rules.tree + rules.bush + rules.rock + rules.reed
          && h < WATER_LEVEL + 2.6) {
          type = PROP.REED;
        }
        if (type < 0) continue;
        if ((type === PROP.ROCK_L) && slope < 0.06 && r4 < 0.6) continue; // boulders prefer relief

        const leafSet = LEAF_COLORS[biome] || LEAF_COLORS[BIOME.MEADOW];
        const leaf = leafSet[Math.floor(r4 * leafSet.length) % leafSet.length];
        const bark = BARK_COLORS[Math.floor(r0 * 3) % 3];

        const scale = type === PROP.TREE_BROAD ? 0.75 + r4 * 0.75
          : type === PROP.TREE_CONIFER ? 0.72 + r4 * 0.85
            : type === PROP.TREE_DEAD ? 0.65 + r4 * 0.7
              : type === PROP.BUSH ? 0.55 + r4 * 0.6
                : type === PROP.ROCK_L ? 1.5 + r4 * 2.6
                  : type === PROP.REED ? 0.7 + r4 * 0.6
                    : 0.5 + r4 * 0.9;

        props.push({
          type,
          x, y: h, z,
          yaw: r0 * Math.PI * 2,
          scale,
          leaf: [
            clamp(leaf[0] * (0.85 + r3 * 0.35), 0, 1),
            clamp(leaf[1] * (0.85 + r3 * 0.35), 0, 1),
            clamp(leaf[2] * (0.85 + r3 * 0.35), 0, 1),
          ],
          bark: [bark[0] * (0.9 + r1 * 0.25), bark[1] * (0.9 + r1 * 0.25), bark[2] * (0.9 + r1 * 0.25)],
          phase: r1 * 6.283,
          biome,
        });
      }
    }

    this.cache.set(key, props);
    return props;
  }

  /**
   * Build (or fetch cached) ground clutter for a terrain chunk.
   *
   * Kept in its own cache, and its own packed array, deliberately: clutter
   * outnumbers props by two orders of magnitude and nothing collides with it,
   * so it must never enter the arrays movement code walks every step.
   *
   * @returns {Float32Array} items of CLUTTER_STRIDE floats
   */
  clutterFor(cx, cz, build = true) {
    const key = this.chunkKey(cx, cz);
    const hit = this.clutterCache.get(key);
    if (hit) return hit;
    // A chunk is a few thousand candidates; letting a frame build several of
    // them at once is a visible stutter when the player crosses a chunk line.
    // The caller budgets them, and a chunk that misses out simply draws next
    // frame instead.
    if (!build) return null;

    const world = this.world;
    const seed = world.seed;
    const out = [];
    const ox = cx * CHUNK_SIZE - WORLD_HALF;
    const oz = cz * CHUNK_SIZE - WORLD_HALF;
    const cells = Math.ceil(CHUNK_SIZE / CLUTTER_CELL);
    const baseCellX = Math.floor(ox / CLUTTER_CELL);
    const baseCellZ = Math.floor(oz / CLUTTER_CELL);
    const w = this._w;

    for (let jz = 0; jz < cells; jz++) {
      for (let jx = 0; jx < cells; jx++) {
        const gx = baseCellX + jx;
        const gz = baseCellZ + jz;
        // One hash decides acceptance, and the biggest budget on the island
        // bounds it — so nine cells in ten cost a single hash and nothing else.
        const r0 = hash2(gx, gz, seed ^ 0x5c1a77e5);
        if (r0 > CLUTTER_MAX_D) continue;

        const r1 = hash2(gx + 4409, gz + 71, seed ^ 0x13);
        const r2 = hash2(gx + 97, gz + 6151, seed ^ 0x71);
        const x = (gx + r1) * CLUTTER_CELL;
        const z = (gz + r2) * CLUTTER_CELL;
        if (Math.abs(x) > WORLD_HALF - 6 || Math.abs(z) > WORLD_HALF - 6) continue;

        const biome = world.biomeAt(x, z);
        const rules = CLUTTER_RULES[biome];
        if (!rules) continue;

        // Patchiness: two lattices, one for the field and one much smaller for
        // the gaps inside it, so a scree slope has bare rock showing through.
        const patch = clumpNoise(x, z, seed ^ 0x2f7, 19)
          * (0.55 + clumpNoise(x, z, seed ^ 0x81b, 5.5) * 0.75);
        if (r0 > rules.d * (0.18 + patch * 1.9)) continue;

        const h = world.heightAt(x, z);
        if (h < WATER_LEVEL + 0.25) continue;
        if (world.roadAt(x, z) > 0.30) continue;
        if (this._blocked(x, z)) continue;

        const slope = world.slopeAt(x, z);
        if (slope > 0.72) continue;   // nothing stays on a cliff face

        const r3 = hash2(gx + 811, gz + 233, seed ^ 0xa5);
        const r4 = hash2(gx + 37, gz + 9403, seed ^ 0xc3);
        const r5 = hash2(gx + 6203, gz + 149, seed ^ 0x1d);

        // Relief drives what collects where: stone shed from a face piles at
        // its foot, drifts bank up on the moderate ground below it, and the
        // soft things that need soil stay off both.
        const scree = saturate((slope - 0.16) / 0.28);
        const bank = saturate(1 - Math.abs(slope - 0.22) / 0.22);
        const moist = world.moisture[world.gridIndex(
          Math.round(world.worldToGrid(x)), Math.round(world.worldToGrid(z)))];

        let total = 0;
        for (let k = 0; k < 7; k++) w[k] = rules.w[k];
        w[CLUTTER.ROCK] *= 1 + scree * 2.4;
        w[CLUTTER.SLAB] *= 1 + scree * 1.1;
        w[CLUTTER.DRIFT] *= 0.4 + bank * 1.8;
        w[CLUTTER.SCRUB] *= (1 - scree * 0.85) * (0.45 + moist * 1.1);
        w[CLUTTER.WOOD] *= (1 - scree * 0.8) * (0.4 + moist * 1.3);
        w[CLUTTER.STUMP] *= (1 - scree * 0.9);
        for (let k = 0; k < 7; k++) total += w[k];
        if (total <= 0) continue;

        let pick = r3 * total;
        // Starts unset rather than at the last kind: rounding must not be able
        // to drop a stump onto a crag whose stump weight is zero.
        let type = -1;
        for (let k = 0; k < 7; k++) {
          pick -= w[k];
          if (pick <= 0 && w[k] > 0) { type = k; break; }
        }
        if (type < 0) continue;

        const rock = BIOME_INFO[biome].rock;
        const ground = BIOME_INFO[biome].ground;
        const snowy = biome === BIOME.SNOW;
        const ashy = biome === BIOME.ASH;
        let sx = 1, sy = 1, sz = 1, yaw = r4 * 6.283;
        let cr = 0.4, cg = 0.4, cb = 0.4;
        let c2r = 0.5, c2g = 0.5, c2b = 0.5;

        switch (type) {
          case CLUTTER.ROCK: {
            sx = 0.5 + r4 * 1.0 + scree * 0.5;
            sy = sx * (0.45 + r5 * 0.5);
            sz = sx * (0.8 + r5 * 0.4);
            const t = 0.78 + r5 * 0.5;
            cr = rock[0] * t; cg = rock[1] * t; cb = rock[2] * t;
            // The crust on top: snow on the peak, ash everywhere it falls,
            // otherwise the lichen-pale tone weathered stone takes.
            c2r = snowy ? 0.78 : ashy ? 0.30 : cr * 1.35 + 0.06;
            c2g = snowy ? 0.82 : ashy ? 0.28 : cg * 1.35 + 0.06;
            c2b = snowy ? 0.90 : ashy ? 0.27 : cb * 1.30 + 0.05;
            break;
          }
          case CLUTTER.WOOD: {
            sx = 0.9 + r4 * 1.9;
            sy = 0.10 + r5 * 0.14;
            sz = sy;
            const t = 0.85 + r5 * 0.35;
            if (ashy) { cr = 0.115; cg = 0.100; cb = 0.095; }
            else { cr = 0.26 * t; cg = 0.20 * t; cb = 0.145 * t; }
            c2r = SPLINTER_COLOR[0]; c2g = SPLINTER_COLOR[1]; c2b = SPLINTER_COLOR[2];
            break;
          }
          case CLUTTER.SCRUB: {
            sx = 0.45 + r4 * 0.65;
            sy = 0.35 + r5 * 0.62;
            sz = sx;
            const leafSet = LEAF_COLORS[biome] || LEAF_COLORS[BIOME.MEADOW];
            const leaf = leafSet[Math.floor(r5 * leafSet.length) % leafSet.length];
            // Scrub is the dry counterpart of the grass field: where the grass
            // thins it goes straw, and it is that alternation the eye reads as
            // ground rather than carpet.
            const parch = saturate(0.75 - moist * 0.6 + r4 * 0.3);
            cr = lerp(leaf[0], 0.42, parch);
            cg = lerp(leaf[1], 0.37, parch);
            cb = lerp(leaf[2], 0.20, parch);
            c2r = cr * 1.25 + 0.08; c2g = cg * 1.2 + 0.07; c2b = cb * 1.1 + 0.04;
            break;
          }
          case CLUTTER.BONE: {
            sx = 0.7 + r4 * 0.9;
            sy = sx * 0.5;
            sz = sx;
            const t = 0.82 + r5 * 0.34;
            cr = BONE_COLOR[0] * t; cg = BONE_COLOR[1] * t; cb = BONE_COLOR[2] * t;
            c2r = cr * 1.2; c2g = cg * 1.2; c2b = cb * 1.15;
            break;
          }
          case CLUTTER.DRIFT: {
            sx = 1.6 + r4 * 3.4;
            sy = 0.24 + r4 * 0.5 + bank * 0.3;
            sz = sx * (0.4 + r5 * 0.35);
            // Drifts lie across the slope, because that is where blown material
            // stops. The terrain normal gives the downhill direction for free.
            world.normalAt(x, z, this._n);
            const gl = Math.hypot(this._n.x, this._n.z);
            yaw = gl > 0.02
              ? Math.atan2(this._n.x, this._n.z) + Math.PI / 2 + (r4 - 0.5) * 0.5
              : r4 * 6.283;
            const t = 0.9 + r5 * 0.3;
            cr = lerp(ground[0], rock[0], 0.45) * t;
            cg = lerp(ground[1], rock[1], 0.45) * t;
            cb = lerp(ground[2], rock[2], 0.45) * t;
            c2r = snowy ? 0.86 : cr * 1.4 + 0.05;
            c2g = snowy ? 0.89 : cg * 1.4 + 0.05;
            c2b = snowy ? 0.95 : cb * 1.35 + 0.05;
            break;
          }
          case CLUTTER.SLAB: {
            sx = 1.0 + r4 * 2.2;
            sy = 0.10 + r5 * 0.26;
            sz = sx * (0.65 + r5 * 0.45);
            const t = 0.7 + r5 * 0.4;
            cr = rock[0] * t; cg = rock[1] * t; cb = rock[2] * t;
            c2r = cr * 1.3 + 0.05; c2g = cg * 1.3 + 0.05; c2b = cb * 1.25 + 0.05;
            break;
          }
          default: {   // CLUTTER.STUMP
            // One in four is a snag rather than a stump: a standing dead trunk
            // is the only clutter tall enough to break the horizon line, which
            // is exactly what the emptiest country needs.
            //
            // Its height is capped just under three metres, and that cap is a
            // correctness bound rather than a taste one. Clutter deliberately
            // never enters the collider arrays — it is two orders of magnitude
            // more numerous than props and movement walks those arrays every
            // step — so anything in this tier is walked through. At half a
            // metre of debris nobody notices; at five metres it is a tree you
            // pass straight through, and the world already has PROP.TREE_DEAD,
            // which is the same silhouette *with* a collider. Under three
            // metres it reads as a snapped-off trunk, in the same family as
            // the reeds and bushes the player already walks through, and it
            // still stands well above eye height on the horizon.
            const snag = r5 > 0.74;
            sy = snag ? 1.55 + r4 * 1.35 : 0.45 + r4 * 0.85;
            sx = snag ? 0.34 + r4 * 0.26 : 0.45 + r4 * 0.6;
            sz = sx * (0.85 + r5 * 0.3);
            const t = 0.85 + r5 * 0.35;
            if (ashy) { cr = 0.125 * t; cg = 0.108 * t; cb = 0.100 * t; }
            else { cr = 0.24 * t; cg = 0.19 * t; cb = 0.14 * t; }
            c2r = ashy ? 0.20 : SPLINTER_COLOR[0];
            c2g = ashy ? 0.17 : SPLINTER_COLOR[1];
            c2b = ashy ? 0.15 : SPLINTER_COLOR[2];
            break;
          }
        }

        // Instances carry a yaw and a scale but no tilt, so anything long has
        // to be levelled to the lowest ground it covers: half-buried at the
        // high end looks like settled debris, hovering at the low end looks
        // like a bug. Short clutter just sinks a little.
        let y = h;
        if (sx > 1.0) {
          const ex = Math.cos(yaw) * sx * 0.5, ez = Math.sin(yaw) * sx * 0.5;
          let ha = world.heightAt(x + ex, z + ez);
          let hb = world.heightAt(x - ex, z - ez);
          const drop = Math.max(h, ha, hb) - Math.min(h, ha, hb);
          if (drop > sy * 0.9) {
            // More relief under it than it is tall: shorten it rather than
            // discard it. Small debris on a steep bank is what actually
            // collects there, and a long slab would just vanish into the hill.
            const k = Math.max(0.3, (sy * 0.9) / drop);
            sx *= k; sz *= k;
            const nx = Math.cos(yaw) * sx * 0.5, nz = Math.sin(yaw) * sx * 0.5;
            ha = world.heightAt(x + nx, z + nz);
            hb = world.heightAt(x - nx, z - nz);
          }
          y = Math.min(h, ha, hb);
        }
        out.push(type, x, y - sy * 0.06, z, yaw, sx, sy, sz,
          clamp(cr, 0, 1), clamp(cg, 0, 1), clamp(cb, 0, 1),
          clamp(c2r, 0, 1), clamp(c2g, 0, 1), clamp(c2b, 0, 1), r2 * 6.283);
      }
    }

    const packed = new Float32Array(out);
    this.clutterCache.set(key, packed);
    return packed;
  }

  /** Radius used for culling and for blocking the player's movement. */
  static colliderFor(prop) {
    switch (prop.type) {
      case PROP.TREE_BROAD: return 0.42 * prop.scale;
      case PROP.TREE_CONIFER: return 0.34 * prop.scale;
      case PROP.TREE_DEAD: return 0.32 * prop.scale;
      case PROP.ROCK_L: return 0.55 * prop.scale;
      default: return 0;   // bushes, small rocks and reeds are walk-through
    }
  }

  /** All solid props near a point — used by movement collision. */
  collidersNear(x, z, radius, out = []) {
    out.length = 0;
    const cx0 = Math.floor((x - radius + WORLD_HALF) / CHUNK_SIZE);
    const cx1 = Math.floor((x + radius + WORLD_HALF) / CHUNK_SIZE);
    const cz0 = Math.floor((z - radius + WORLD_HALF) / CHUNK_SIZE);
    const cz1 = Math.floor((z + radius + WORLD_HALF) / CHUNK_SIZE);
    for (let cz = cz0; cz <= cz1; cz++) {
      for (let cx = cx0; cx <= cx1; cx++) {
        if (cx < 0 || cz < 0 || cx >= CHUNKS || cz >= CHUNKS) continue;
        const props = this.propsFor(cx, cz);
        for (let i = 0; i < props.length; i++) {
          const p = props[i];
          const r = Scatter.colliderFor(p);
          if (r <= 0) continue;
          const dx = p.x - x, dz = p.z - z;
          const rr = r + radius;
          if (dx * dx + dz * dz < rr * rr) out.push({ x: p.x, z: p.z, r });
        }
      }
    }
    return out;
  }

  evictFarChunks(camX, camZ, keepRadius) {
    // Clutter is evicted on a much tighter radius than props: it is never drawn
    // beyond a few hundred metres and it is by far the heavier cache.
    this._evict(this.clutterCache, camX, camZ, Math.min(keepRadius, 420), 24);
    this._evict(this.cache, camX, camZ, keepRadius, 160);
  }

  _evict(cache, camX, camZ, keepRadius, floor) {
    if (cache.size < floor) return;
    const drop = [];
    for (const key of cache.keys()) {
      const cx = key % CHUNKS, cz = Math.floor(key / CHUNKS);
      const centerX = cx * CHUNK_SIZE - WORLD_HALF + CHUNK_SIZE / 2;
      const centerZ = cz * CHUNK_SIZE - WORLD_HALF + CHUNK_SIZE / 2;
      if (Math.hypot(centerX - camX, centerZ - camZ) > keepRadius) drop.push(key);
    }
    for (const k of drop) cache.delete(k);
  }
}

// ---------------------------------------------------------------------------
//  Grass — a rolling patch around the player
// ---------------------------------------------------------------------------

const GRASS_DENSITY = {
  [BIOME.MEADOW]: 1.0,
  [BIOME.FOREST]: 0.55,
  [BIOME.MARSH]: 0.6,
  [BIOME.HIGHLAND]: 0.5,
  [BIOME.BEACH]: 0.12,
  [BIOME.CRAG]: 0.08,
  [BIOME.SNOW]: 0.05,
  [BIOME.ASH]: 0.10,
  [BIOME.OCEAN]: 0,
};

export class GrassField {
  constructor(world, scatter) {
    this.world = world;
    this.scatter = scatter;
    this.lastX = Infinity;
    this.lastZ = Infinity;
    this.radius = 46;
    this.cell = 1.35;
    this.bladesPerCell = 2;
    this.dirty = true;
  }

  configure(radius, cell, bladesPerCell) {
    if (radius !== this.radius || cell !== this.cell || bladesPerCell !== this.bladesPerCell) {
      this.radius = radius;
      this.cell = cell;
      this.bladesPerCell = bladesPerCell;
      this.dirty = true;
    }
  }

  needsRebuild(x, z) {
    return this.dirty || Math.hypot(x - this.lastX, z - this.lastZ) > this.cell * 5;
  }

  /** Fill an InstanceBatch with blades around (x, z). */
  rebuild(batch, x, z) {
    batch.clear();
    const world = this.world;
    const cell = this.cell;
    const R = this.radius;
    const R2 = R * R;
    const cx0 = Math.floor((x - R) / cell);
    const cx1 = Math.floor((x + R) / cell);
    const cz0 = Math.floor((z - R) / cell);
    const cz1 = Math.floor((z + R) / cell);

    for (let gz = cz0; gz <= cz1; gz++) {
      for (let gx = cx0; gx <= cx1; gx++) {
        const baseX = gx * cell, baseZ = gz * cell;
        const ddx = baseX - x, ddz = baseZ - z;
        if (ddx * ddx + ddz * ddz > R2) continue;

        const biome = world.biomeAt(baseX, baseZ);
        const density = GRASS_DENSITY[biome] || 0;
        if (density <= 0) continue;

        const h0 = world.heightAt(baseX, baseZ);
        if (h0 < WATER_LEVEL + 0.25) continue;
        const slope = world.slopeAt(baseX, baseZ);
        if (slope > 0.42) continue;
        const road = world.roadAt(baseX, baseZ);
        if (road > 0.55) continue;

        const moist = world.moisture[world.gridIndex(
          Math.round(world.worldToGrid(baseX)), Math.round(world.worldToGrid(baseZ)))];
        const localDensity = density * (0.45 + moist * 0.85) * (1 - road * 0.9)
          * (1 - saturate((slope - 0.18) / 0.28) * 0.8);

        for (let b = 0; b < this.bladesPerCell; b++) {
          const r0 = hash2(gx, gz, world.seed + b * 7919);
          if (r0 > localDensity) continue;
          const r1 = hash2(gx + 733, gz + 191, world.seed + b * 104729);
          const r2 = hash2(gx + 17, gz + 2903, world.seed + b * 15485863);
          const r3 = hash2(gx + 5099, gz + 61, world.seed + b * 32452843);

          const px = baseX + r1 * cell;
          const pz = baseZ + r2 * cell;
          const py = world.heightAt(px, pz);
          if (py < WATER_LEVEL + 0.2) continue;

          // Clumping. Uniformly scattered blades read as a green fuzz; real
          // grass grows in patches with bare ground between them, and it is
          // that alternation — not the blade count — that makes a field look
          // like a field. One low-frequency noise lookup buys it.
          const clump = world.grassClump(px, pz);
          const height = (0.20 + r3 * 0.30) * (0.75 + moist * 0.6) * (0.55 + clump * 0.85);
          const width = (0.080 + r0 * 0.075) * (0.7 + clump * 0.5);
          const yaw = r1 * Math.PI * 2;

          // Tint follows the biome ground colour, shifted greener and varied.
          // The per-blade spread is wide on purpose: a patch of one flat green
          // is the single most synthetic thing a meadow can do.
          const dry = biome === BIOME.ASH || biome === BIOME.SNOW || biome === BIOME.CRAG;
          // Sparse blades sit in the dry gaps and go straw-coloured, which is
          // what ties the grass to the bleached patches in the terrain shader.
          const parch = (1 - clump) * 0.55 + r3 * 0.25;
          let cr, cg, cb;
          if (dry) {
            cr = 0.32 + r3 * 0.14; cg = 0.28 + r3 * 0.11; cb = 0.20 + r3 * 0.08;
          } else {
            cr = lerp(0.28, 0.19, moist) + r3 * 0.16 + parch * 0.30;
            cg = lerp(0.46, 0.55, moist) + r2 * 0.14 + parch * 0.14;
            cb = 0.14 + r1 * 0.13;
          }

          batch.push(px, py - 0.03, pz, width, height, width, yaw,
            cr, cg, cb, 0, 1, r2 * 6.283, 1, 1);
        }
      }
    }
    this.lastX = x;
    this.lastZ = z;
    this.dirty = false;
    return batch.count;
  }
}
