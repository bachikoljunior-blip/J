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
 * Land features — the tier between clutter and props. Two to eight metres,
 * clustered, and placed by what the ground is doing rather than sprinkled.
 *
 * Clutter cannot furnish open country: a 30 cm stone is gone by ninety metres,
 * so on a plain everything from the middle distance out is bare terrain shading
 * however dense the near field is. Features are what a plain is actually made
 * of — outcrops on the slope breaks, thickets down the hollows, reed beds at
 * the water, dunes lying across the wind, and the walls and cairns people left.
 * They are the difference between land that has form and a lit surface.
 */
export const FEATURE = {
  OUTCROP: 0,  // rock outcrop, boulder cluster, tor
  THICKET: 1,  // bramble mass, hedgerow run
  REEDBED: 2,  // reeds and rotting posts at the water margin
  DUNE: 3,     // wind-built ash or sand dune, timber in its crest
  MIDDEN: 4,   // bone heap
  CAIRN: 5,    // stacked marker stones
  WALL: 6,     // drystone field wall, in runs
};

/**
 * Clutter is stored packed rather than as objects: a loaded view holds tens of
 * thousands of items, and 60 bytes in one flat array beats an object header
 * each on a phone — both for memory and for the garbage collector, which must
 * not run mid-frame.
 *
 * Layout: type, x, y, z, yaw, sx, sy, sz, r, g, b, r2, g2, b2, phase, rangeMul
 *
 * `rangeMul` scales the kind's draw distance per item. It is a per-biome value
 * decided at scatter time rather than a constant in game.js because the biomes
 * that need debris carried further are exactly the flat ones — a stone on a
 * plain is the only thing between the player and an empty surface, while in the
 * woods the same stone is behind a tree.
 */
export const CLUTTER_STRIDE = 16;

/** Features are packed the same way. The last slot is a collider radius. */
export const FEATURE_STRIDE = 16;

const PROP_CELL = 9;      // metres between scatter candidates
const CLUTTER_CELL = 2.5; // metres between clutter candidates
const FEATURE_CELL = 13;  // metres between feature candidates
/**
 * How far a clustered run can reach from the cell that opened it. Collision has
 * to search this much wider than the chunk it is standing in, because the
 * record for the wall segment under the player's feet lives in whichever chunk
 * the run started in.
 */
const FEATURE_REACH = 44;

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
 * The three flat biomes — meadow, marsh and ash — carry roughly half again the
 * budget of the rest, because a near field that reads as swept is only a
 * problem where there is nothing else in the frame. Under trees or against a
 * crag the eye has plenty to hold on to; on a plain the ten metres in front of
 * the player is the only place the ground can prove it is ground.
 *
 * The Cinderwaste gets the highest budget of anywhere on the island. It is a
 * bare ash plain and it is meant to feel like one, but bleak is not the same as
 * empty: what makes ash country legible is drifts, burnt stumps, cracked plates
 * and bone — all of it grey, none of it flat.
 */
const CLUTTER_RULES = {
  [BIOME.OCEAN]: null,
  [BIOME.BEACH]: { d: 0.16, w: [0.30, 0.16, 0.12, 0.04, 0.30, 0.08, 0.00] },
  [BIOME.MEADOW]: { d: 0.62, w: [0.22, 0.14, 0.40, 0.02, 0.13, 0.02, 0.07] },
  [BIOME.FOREST]: { d: 0.34, w: [0.14, 0.32, 0.26, 0.03, 0.09, 0.04, 0.12] },
  [BIOME.MARSH]: { d: 0.58, w: [0.06, 0.21, 0.38, 0.04, 0.11, 0.02, 0.18] },
  [BIOME.HIGHLAND]: { d: 0.36, w: [0.32, 0.10, 0.30, 0.02, 0.14, 0.08, 0.04] },
  [BIOME.CRAG]: { d: 0.34, w: [0.50, 0.03, 0.09, 0.06, 0.10, 0.22, 0.00] },
  [BIOME.SNOW]: { d: 0.26, w: [0.34, 0.04, 0.06, 0.06, 0.36, 0.12, 0.02] },
  [BIOME.ASH]: { d: 0.64, w: [0.16, 0.08, 0.02, 0.19, 0.24, 0.15, 0.16] },
};

/**
 * How far each biome's clutter is worth drawing, as a multiple of the kind's
 * own range in game.js. Open country pays for it and closed country does not:
 * in the woods a stone at 130 m is behind three trees, on the ash plain it is
 * the only thing in that part of the frame.
 */
const CLUTTER_RANGE_MUL = {
  [BIOME.MEADOW]: 1.15,
  [BIOME.MARSH]: 1.15,
  [BIOME.ASH]: 1.20,
};

/** Largest `d` above — the cheap reject that runs before any terrain query. */
const CLUTTER_MAX_D = 0.64;

/**
 * Per-biome feature budget. `d` is the chance a 13 m candidate cell opens a
 * cluster before the clustering gate, and `w` weights the kinds in FEATURE
 * order [OUTCROP, THICKET, REEDBED, DUNE, MIDDEN, CAIRN, WALL].
 *
 * The three biomes that are flat open ground — meadow, marsh and ash — get by
 * far the largest budgets, because they are the ones with nothing else. The
 * Cinderwaste gets the largest of all: dunes and middens are the only relief it
 * is allowed to have, since anything green would contradict the place.
 */
const FEATURE_RULES = {
  [BIOME.OCEAN]: null,
  [BIOME.BEACH]: { d: 0.22, w: [0.34, 0.08, 0.10, 0.30, 0.02, 0.06, 0.10] },
  [BIOME.MEADOW]: { d: 0.58, w: [0.26, 0.24, 0.03, 0.00, 0.00, 0.12, 0.35] },
  [BIOME.FOREST]: { d: 0.22, w: [0.26, 0.38, 0.02, 0.00, 0.00, 0.10, 0.24] },
  [BIOME.MARSH]: { d: 0.56, w: [0.10, 0.20, 0.46, 0.00, 0.02, 0.04, 0.18] },
  [BIOME.HIGHLAND]: { d: 0.62, w: [0.40, 0.14, 0.00, 0.00, 0.00, 0.20, 0.26] },
  [BIOME.CRAG]: { d: 0.34, w: [0.70, 0.04, 0.00, 0.00, 0.02, 0.16, 0.08] },
  [BIOME.SNOW]: { d: 0.28, w: [0.62, 0.02, 0.00, 0.00, 0.02, 0.32, 0.02] },
  [BIOME.ASH]: { d: 0.84, w: [0.24, 0.02, 0.00, 0.34, 0.20, 0.08, 0.12] },
};

const FEATURE_MAX_D = 0.84;

/** Straw of dead cane, and the tone rotting timber goes in standing water. */
const CANE_COLOR = [0.42, 0.36, 0.24];
const ROT_COLOR = [0.20, 0.16, 0.12];

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

/**
 * First scatter-cell index a chunk owns, given the chunk's world origin.
 *
 * A cell belongs to exactly one chunk: the one containing its anchor, `i *
 * cell`. Taking `floor(origin / cell)` instead — which is the obvious thing,
 * and what this used to do — hands the cell straddling a chunk line to *both*
 * neighbours. Both then generate it from the same hashes, so the same tree or
 * the same wall is emitted twice at exactly the same transform: invisible,
 * because the opaque pass is LEQUAL and the second copy shades identically, but
 * paid for in full. It was costing about a tenth of every prop drawn.
 *
 * The half-open range [cellFirst(o), cellFirst(o + CHUNK_SIZE)) partitions the
 * integers, so nothing is dropped either.
 */
const cellFirst = (origin, cell) => Math.ceil(origin / cell);

export class Scatter {
  constructor(world) {
    this.world = world;
    this.cache = new Map();        // chunkKey -> array of props
    this.clutterCache = new Map(); // chunkKey -> packed Float32Array of clutter
    this.featureCache = new Map(); // chunkKey -> packed Float32Array of features
    this.blockers = [];            // circles where scatter is suppressed (POIs)
    this._w = new Float64Array(7); // kind weights, reused per candidate
    this._fw = new Float64Array(7);
    this._n = { x: 0, y: 1, z: 0 };
    // One wind direction for the whole island. Dune fields only read as wind
    // if every dune on the horizon agrees about which way it was blowing.
    this.windYaw = hash2(1013, 71, world.seed ^ 0x1d3a5) * Math.PI * 2;
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
    const gx0 = cellFirst(ox, PROP_CELL), gx1 = cellFirst(ox + CHUNK_SIZE, PROP_CELL);
    const gz0 = cellFirst(oz, PROP_CELL), gz1 = cellFirst(oz + CHUNK_SIZE, PROP_CELL);

    for (let gz = gz0; gz < gz1; gz++) {
      for (let gx = gx0; gx < gx1; gx++) {
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
    const gx0 = cellFirst(ox, CLUTTER_CELL), gx1 = cellFirst(ox + CHUNK_SIZE, CLUTTER_CELL);
    const gz0 = cellFirst(oz, CLUTTER_CELL), gz1 = cellFirst(oz + CHUNK_SIZE, CLUTTER_CELL);
    const w = this._w;

    for (let gz = gz0; gz < gz1; gz++) {
      for (let gx = gx0; gx < gx1; gx++) {
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
        // The reject above is bounded by the *island's* biggest budget, which
        // is the Cinderwaste's; on a quiet coast that lets four cells in five
        // through to a noise lookup that was always going to refuse them. 2.65
        // is the largest the patch term below can reach, so this cannot change
        // where anything lands — it only declines earlier.
        if (r0 > rules.d * 2.65) continue;

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
          clamp(c2r, 0, 1), clamp(c2g, 0, 1), clamp(c2b, 0, 1), r2 * 6.283,
          CLUTTER_RANGE_MUL[biome] || 1);
      }
    }

    const packed = new Float32Array(out);
    this.clutterCache.set(key, packed);
    return packed;
  }

  /**
   * Seat a feature on the ground.
   *
   * The instance transform carries a yaw and a scale but no tilt, so anything
   * metres across has to be levelled to the lowest ground under its footprint
   * and let its buried skirt swallow the difference. Returns -Infinity when the
   * drop across that footprint is more than the shape can hide, which is the
   * signal to skip the placement rather than to leave it floating.
   */
  _seat(x, z, halfX, halfZ, yaw, tolerance) {
    const c = Math.cos(yaw), s = Math.sin(yaw);
    // The engine's yaw takes local +Z to (sin, cos) — forward — and local +X to
    // (cos, -sin) — right; see actor.js movement and the instance matrix in
    // instancing.js. Sampling the footprint along (cos, sin) instead mirrors it
    // in Z, so a wall's footprint would be probed across the wall rather than
    // along it and the seat would come from the wrong ground.
    const ax = c * halfX, az = -s * halfX;
    const bx = s * halfZ, bz = c * halfZ;
    const world = this.world;
    let lo = world.heightAt(x, z), hi = lo;
    for (let i = 0; i < 4; i++) {
      const px = x + (i === 0 ? ax : i === 1 ? -ax : i === 2 ? bx : -bx);
      const pz = z + (i === 0 ? az : i === 1 ? -az : i === 2 ? bz : -bz);
      const h = world.heightAt(px, pz);
      if (h < lo) lo = h;
      if (h > hi) hi = h;
    }
    return hi - lo > tolerance ? -Infinity : lo;
  }

  /**
   * Size, colour and seat one feature instance, appending it to `out`.
   *
   * Every kind takes its palette from the biome it stands in rather than from a
   * table of its own, so an outcrop in the mire is the mire's stone with moss on
   * it and the same outcrop in the waste is ash-covered — one mesh, and the
   * place still decides what it is made of.
   *
   * @returns {boolean} false when the ground refused it
   */
  _placeFeature(out, type, x, z, yaw, biome, moist, s0, s1) {
    const world = this.world;
    if (Math.abs(x) > WORLD_HALF - 12 || Math.abs(z) > WORLD_HALF - 12) return false;
    if (world.roadAt(x, z) > 0.22) return false;
    if (this._blocked(x, z)) return false;

    const h = world.heightAt(x, z);
    // Reeds stand in the shallows; everything else needs dry ground.
    const floor = type === FEATURE.REEDBED ? WATER_LEVEL - 0.8 : WATER_LEVEL + 0.35;
    if (h < floor) return false;
    const slope = world.slopeAt(x, z);
    if (slope > (type === FEATURE.OUTCROP ? 0.80 : 0.42)) return false;

    const rock = BIOME_INFO[biome].rock;
    const ground = BIOME_INFO[biome].ground;
    const snowy = biome === BIOME.SNOW;
    const ashy = biome === BIOME.ASH;
    const boggy = biome === BIOME.MARSH;
    let sx = 1, sy = 1, sz = 1, collide = 0, tol = 1;
    let cr = 0.4, cg = 0.4, cb = 0.4;
    let c2r = 0.5, c2g = 0.5, c2b = 0.5;

    switch (type) {
      case FEATURE.OUTCROP: {
        sx = 3.0 + s0 * 4.6;
        sy = sx * (0.30 + s1 * 0.34);
        sz = sx * (0.66 + s1 * 0.46);
        collide = Math.min(sx, sz) * 0.34;
        tol = sy * 1.4;
        const t = 0.72 + s1 * 0.46;
        cr = rock[0] * t; cg = rock[1] * t; cb = rock[2] * t;
        // What the top of a standing stone collects: snow on the peak, ash
        // where it falls, moss in the wet, lichen everywhere else.
        c2r = snowy ? 0.80 : ashy ? 0.33 : boggy ? 0.21 : cr * 1.40 + 0.08;
        c2g = snowy ? 0.84 : ashy ? 0.30 : boggy ? 0.27 : cg * 1.40 + 0.08;
        c2b = snowy ? 0.90 : ashy ? 0.29 : boggy ? 0.16 : cb * 1.34 + 0.06;
        break;
      }
      case FEATURE.THICKET: {
        sx = 3.8 + s0 * 4.0;
        sy = 1.5 + s1 * 1.3;
        sz = 2.0 + s1 * 1.8;
        // Only the dense core stops the player: the edge of a bramble mass is
        // something you shoulder through, and a hedgerow run that seals a
        // meadow shut would be a wall the map never told anyone about.
        collide = sz * 0.28;
        tol = sy * 0.9;
        const leafSet = LEAF_COLORS[biome] || LEAF_COLORS[BIOME.MEADOW];
        const leaf = leafSet[Math.floor(s1 * leafSet.length) % leafSet.length];
        const t = 0.72 + s0 * 0.4;
        cr = leaf[0] * t; cg = leaf[1] * t; cb = leaf[2] * t;
        // Dead cane over living mass. A thicket read only by its leaf colour
        // sits on grass as one flat green shape and disappears.
        c2r = lerp(CANE_COLOR[0], cr * 1.5, moist * 0.5);
        c2g = lerp(CANE_COLOR[1], cg * 1.5, moist * 0.5);
        c2b = lerp(CANE_COLOR[2], cb * 1.5, moist * 0.5);
        break;
      }
      case FEATURE.REEDBED: {
        sx = 3.0 + s0 * 3.4;
        sy = 1.4 + s1 * 1.2;
        sz = sx * (0.58 + s1 * 0.5);
        tol = 1.7;
        const t = 0.8 + s1 * 0.4;
        cr = lerp(0.40, 0.26, moist) * t;
        cg = lerp(0.40, 0.44, moist) * t;
        cb = 0.17 * t;
        c2r = ROT_COLOR[0]; c2g = ROT_COLOR[1]; c2b = ROT_COLOR[2];
        break;
      }
      case FEATURE.DUNE: {
        sx = 7.0 + s0 * 7.0;
        sy = 0.9 + s1 * 1.1;
        sz = sx * (0.28 + s1 * 0.22);
        tol = sy * 1.3;
        // Dark charred ground below, fresh pale material on the crest. That
        // ramp is the whole reason the shape is here: it turns one directional
        // light into a full tonal range across ground that otherwise has none.
        const t = 0.85 + s1 * 0.3;
        cr = ground[0] * 0.62 * t; cg = ground[1] * 0.62 * t; cb = ground[2] * 0.62 * t;
        c2r = ashy ? 0.50 : lerp(ground[0], 1, 0.35);
        c2g = ashy ? 0.47 : lerp(ground[1], 1, 0.35);
        c2b = ashy ? 0.45 : lerp(ground[2], 1, 0.35);
        break;
      }
      case FEATURE.MIDDEN: {
        sx = 2.4 + s0 * 2.8;
        sy = sx * (0.42 + s1 * 0.3);
        sz = sx * (0.82 + s1 * 0.3);
        collide = sx * 0.25;
        tol = sy * 1.0;
        const t = 0.5 + s1 * 0.25;
        cr = lerp(BONE_COLOR[0] * t, ground[0], 0.45);
        cg = lerp(BONE_COLOR[1] * t, ground[1], 0.45);
        cb = lerp(BONE_COLOR[2] * t, ground[2], 0.45);
        c2r = BONE_COLOR[0]; c2g = BONE_COLOR[1]; c2b = BONE_COLOR[2];
        break;
      }
      case FEATURE.CAIRN: {
        sx = 1.1 + s0 * 0.9;
        sy = 1.7 + s1 * 1.7;
        sz = sx * (0.9 + s1 * 0.25);
        collide = sx * 0.42;
        tol = 0.8;
        const t = 0.74 + s1 * 0.3;
        cr = rock[0] * t; cg = rock[1] * t; cb = rock[2] * t;
        c2r = cr * 1.34 + 0.07; c2g = cg * 1.34 + 0.07; c2b = cb * 1.28 + 0.06;
        break;
      }
      default: {   // FEATURE.WALL
        sx = 4.6 + s0 * 2.2;
        sy = 0.85 + s1 * 0.75;
        sz = 0.7 + s1 * 0.5;
        collide = sz * 0.55;
        tol = sy * 1.3;
        const t = 0.68 + s1 * 0.34;
        cr = rock[0] * t; cg = rock[1] * t; cb = rock[2] * t;
        // In grassland the wall is really a hedgebank: stone below, turf on
        // top. On the moor and in the waste it is bare weathered cap stone.
        const turf = biome === BIOME.MEADOW || biome === BIOME.FOREST;
        c2r = turf ? ground[0] * 0.85 : cr * 1.32 + 0.06;
        c2g = turf ? ground[1] * 0.85 : cg * 1.32 + 0.06;
        c2b = turf ? ground[2] * 0.85 : cb * 1.26 + 0.05;
        break;
      }
    }

    const y = this._seat(x, z, sx * 0.5, sz * 0.5, yaw, tol);
    if (y === -Infinity) return false;
    out.push(type, x, y, z, yaw, sx, sy, sz,
      clamp(cr, 0, 1), clamp(cg, 0, 1), clamp(cb, 0, 1),
      clamp(c2r, 0, 1), clamp(c2g, 0, 1), clamp(c2b, 0, 1),
      (x * 0.37 + z * 0.19) % 6.283, collide);
    return true;
  }

  /**
   * Build (or fetch cached) land features for a terrain chunk.
   *
   * Cheap enough to build on demand — a chunk is a hundred candidates, not the
   * few thousand clutter needs — which matters because movement collision reads
   * this cache directly and cannot wait a frame for it.
   *
   * @returns {Float32Array} items of FEATURE_STRIDE floats
   */
  featuresFor(cx, cz) {
    const key = this.chunkKey(cx, cz);
    const hit = this.featureCache.get(key);
    if (hit) return hit;

    const world = this.world;
    const seed = world.seed;
    const out = [];
    const ox = cx * CHUNK_SIZE - WORLD_HALF;
    const oz = cz * CHUNK_SIZE - WORLD_HALF;
    const gx0 = cellFirst(ox, FEATURE_CELL), gx1 = cellFirst(ox + CHUNK_SIZE, FEATURE_CELL);
    const gz0 = cellFirst(oz, FEATURE_CELL), gz1 = cellFirst(oz + CHUNK_SIZE, FEATURE_CELL);
    const w = this._fw;

    for (let gz = gz0; gz < gz1; gz++) {
      for (let gx = gx0; gx < gx1; gx++) {
        const r0 = hash2(gx, gz, seed ^ 0x3b91c7);
        if (r0 > FEATURE_MAX_D) continue;

        const r1 = hash2(gx + 227, gz + 8117, seed ^ 0x2a);
        const r2 = hash2(gx + 6473, gz + 59, seed ^ 0x9e);
        const x = (gx + r1) * FEATURE_CELL;
        const z = (gz + r2) * FEATURE_CELL;
        if (Math.abs(x) > WORLD_HALF - 14 || Math.abs(z) > WORLD_HALF - 14) continue;

        const biome = world.biomeAt(x, z);
        const rules = FEATURE_RULES[biome];
        if (!rules) continue;

        // Clustering, and it is the whole point. Large objects at even spacing
        // look worse than none at all — that is the signature of a generated
        // world. One coarse lattice decides which stretches of country have
        // features and which are open, and squaring it makes the boundary
        // between the two definite instead of a haze.
        const field = clumpNoise(x, z, seed ^ 0x9e37, 78) * 0.62
          + clumpNoise(x, z, seed ^ 0x2c1b, 23) * 0.38;
        const gate = saturate((field - 0.38) / 0.30);
        if (r0 > rules.d * gate * gate) continue;

        const h = world.heightAt(x, z);
        if (h < WATER_LEVEL - 0.8) continue;
        if (world.roadAt(x, z) > 0.22) continue;
        if (this._blocked(x, z)) continue;

        // What the land is doing here, at the scale a feature is placed by.
        // Convexity over ten metres separates the knolls and slope breaks from
        // the hollows; on ground as gentle as the meadow the numbers are only
        // tens of centimetres, which is exactly why they are normalised small.
        const slope = world.slopeAt(x, z);
        const ha = world.heightAt(x + 10, z), hb = world.heightAt(x - 10, z);
        const hc = world.heightAt(x, z + 10), hd = world.heightAt(x, z - 10);
        const conv = h - (ha + hb + hc + hd) * 0.25;
        const roadNear = saturate(Math.max(
          world.roadAt(x + 15, z), world.roadAt(x - 15, z),
          world.roadAt(x, z + 15), world.roadAt(x, z - 15)) * 2.2);
        const moist = world.moisture[world.gridIndex(
          Math.round(world.worldToGrid(x)), Math.round(world.worldToGrid(z)))];

        let total = 0;
        for (let k = 0; k < 7; k++) w[k] = rules.w[k];
        // Stone belongs where the ground has already broken: crests, slope
        // breaks, anywhere the soil is thin.
        w[FEATURE.OUTCROP] *= 0.30 + saturate(slope / 0.30) * 1.5 + saturate(conv / 0.8) * 1.7;
        // Scrub belongs in the hollows, where the water and the shelter are.
        w[FEATURE.THICKET] *= (0.30 + saturate(-conv / 0.8) * 1.7 + moist * 0.8)
          * (1 - saturate((slope - 0.22) / 0.30));
        w[FEATURE.REEDBED] *= saturate((WATER_LEVEL + 3.0 - h) / 2.0) * (0.35 + moist);
        // Dunes need open flats to build on and a hollow to settle into.
        w[FEATURE.DUNE] *= (1 - saturate(slope / 0.26)) * (0.55 + saturate(-conv / 1.4) * 0.9);
        w[FEATURE.MIDDEN] *= 1 - saturate(slope / 0.32);
        // People put markers where they can be seen and walls where they can be
        // walked; both cling to the roads, which is what makes them read as
        // traces of somebody rather than as more scenery.
        w[FEATURE.CAIRN] *= 0.35 + saturate(conv / 0.6) * 1.7 + roadNear * 1.6;
        w[FEATURE.WALL] *= (1 - saturate((slope - 0.14) / 0.28)) * (0.55 + roadNear * 1.4);
        for (let k = 0; k < 7; k++) total += w[k];
        if (total <= 0) continue;

        let pick = hash2(gx + 313, gz + 1091, seed ^ 0x77) * total;
        let type = -1;
        for (let k = 0; k < 7; k++) {
          pick -= w[k];
          if (pick <= 0 && w[k] > 0) { type = k; break; }
        }
        if (type < 0) continue;

        const s0 = hash2(gx + 41, gz + 2731, seed ^ 0xb7);
        const s1 = hash2(gx + 5237, gz + 163, seed ^ 0x4d);
        const s2 = hash2(gx + 907, gz + 3491, seed ^ 0xe1);

        // Which way the cluster runs. Thickets and reed beds follow the
        // contour, because that is where the wet ground and the shoreline are;
        // walls follow a field system shared by everything for three hundred
        // metres around, so a district's boundaries look laid out rather than
        // dropped; dunes lie across the island's one wind.
        world.normalAt(x, z, this._n);
        const gl = Math.hypot(this._n.x, this._n.z);
        // A yaw whose long axis (local +X, world (cos, -sin)) lies across the
        // gradient, so a hedgerow runs along the slope instead of straight down
        // it. normalAt's horizontal part points downhill, so the contour is its
        // perpendicular: (-n.z, n.x), which is this yaw.
        const contour = gl > 0.02 ? Math.atan2(-this._n.x, -this._n.z) : s2 * 6.283;
        const fieldYaw = hash2(Math.floor(x / 300), Math.floor(z / 300), seed ^ 0x1e1d) * Math.PI;
        let dir = s2 * 6.283;
        if (type === FEATURE.THICKET || type === FEATURE.REEDBED) dir = contour + (s0 - 0.5) * 0.5;
        else if (type === FEATURE.WALL) dir = fieldYaw;
        else if (type === FEATURE.DUNE) dir = this.windYaw + Math.PI / 2;

        let n = 1;
        switch (type) {
          case FEATURE.OUTCROP: n = 1 + Math.floor(s2 * 3); break;
          case FEATURE.THICKET: n = 2 + Math.floor(s2 * 3); break;
          case FEATURE.REEDBED: n = 2 + Math.floor(s2 * 3); break;
          case FEATURE.DUNE: n = 2 + Math.floor(s2 * 2); break;
          case FEATURE.MIDDEN: n = 1 + Math.floor(s2 * 2); break;
          case FEATURE.CAIRN: n = s2 > 0.82 ? 2 : 1; break;
          default: n = 3 + Math.floor(s2 * 5); break;   // WALL: a boundary, not a stone
        }

        // A wall with no way through is a fence around the player's ankles, so
        // one span in most runs is missing — a gate, or the part that fell.
        const gap = type === FEATURE.WALL && s1 > 0.25 ? 1 + Math.floor(s1 * (n - 2)) : -1;

        const step = type === FEATURE.DUNE ? 15 + s0 * 12 : 0;
        // Yaw -> world direction of the mesh's own long axis (local +X). The
        // minus on sin is the engine convention, not a choice: get it wrong and
        // a run of walls is laid out along one line while each stone in it sits
        // rotated onto a different one, which reads as scattered rubble.
        const dx = Math.cos(dir), dz = -Math.sin(dir);
        for (let k = 0; k < n; k++) {
          if (k === gap) continue;
          const q0 = hash2(gx * 7 + k, gz * 13 + k * 331, seed ^ 0x5b);
          const q1 = hash2(gx * 11 + k * 97, gz * 3 + k, seed ^ 0xc9);
          const q2 = hash2(gx + k * 6131, gz + k * 41, seed ^ 0x2f);
          // Size is drawn from its own hashes: reusing the offset ones makes
          // every far-flung member of a cluster the big one.
          const q3 = hash2(gx * 3 + k * 71, gz * 5 + k * 1873, seed ^ 0x8a);
          const q4 = hash2(gx * 17 + k, gz * 23 + k * 509, seed ^ 0x36);
          let px = x, pz = z, yaw = q2 * 6.283;
          if (type === FEATURE.DUNE) {
            // Along the wind, not across it: a dune field is ranks of ridges
            // marching downwind, each one lying broadside to it.
            // Same convention as `dx/dz` above: the downwind march has to use
            // the yaw->direction mapping the crests are drawn with, or the
            // ranks stop being square to the ridges they are made of.
            px += Math.cos(this.windYaw) * step * k;
            pz += -Math.sin(this.windYaw) * step * k;
            yaw = dir + (q0 - 0.5) * 0.24;
          } else if (type === FEATURE.WALL || type === FEATURE.THICKET
            || type === FEATURE.REEDBED) {
            const run = (type === FEATURE.WALL ? 5.4 : 4.2) * k;
            px += dx * run + (q0 - 0.5) * 1.4;
            pz += dz * run + (q1 - 0.5) * 1.4;
            yaw = dir + (q0 - 0.5) * (type === FEATURE.WALL ? 0.16 : 0.7);
          } else {
            const rad = 3 + q2 * 7;
            const a = q0 * 6.283;
            px += Math.cos(a) * rad * (k === 0 ? 0 : 1);
            pz += Math.sin(a) * rad * (k === 0 ? 0 : 1);
          }
          this._placeFeature(out, type, px, pz, yaw, biome, moist, q3, q4);
        }
      }
    }

    const packed = new Float32Array(out);
    this.featureCache.set(key, packed);
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

  /**
   * All solid props and features near a point — used by movement collision.
   *
   * Features are searched over a wider ring of chunks than props: a wall run is
   * built from the cell that opened it and can reach forty metres from there,
   * so the chunk holding the segment the player is walking into is often not
   * the one holding its record.
   */
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

    const fx0 = Math.floor((x - FEATURE_REACH + WORLD_HALF) / CHUNK_SIZE);
    const fx1 = Math.floor((x + FEATURE_REACH + WORLD_HALF) / CHUNK_SIZE);
    const fz0 = Math.floor((z - FEATURE_REACH + WORLD_HALF) / CHUNK_SIZE);
    const fz1 = Math.floor((z + FEATURE_REACH + WORLD_HALF) / CHUNK_SIZE);
    for (let cz = fz0; cz <= fz1; cz++) {
      for (let cx = fx0; cx <= fx1; cx++) {
        if (cx < 0 || cz < 0 || cx >= CHUNKS || cz >= CHUNKS) continue;
        const f = this.featuresFor(cx, cz);
        for (let i = 0; i < f.length; i += FEATURE_STRIDE) {
          const r = f[i + 15];
          if (r <= 0) continue;
          const fx = f[i + 1], fz = f[i + 3], sx = f[i + 5], yaw = f[i + 4];
          // A wall is five metres of obstacle, not a disc: long features are
          // resolved as a short chain of circles laid along their own axis, or
          // the player walks through the middle of every one of them.
          // Enough circles that consecutive ones overlap: laying `steps` of
          // them across `sx` leaves a gap unless steps * r >= sx / 2, and a gap
          // in a wall is a hole the player falls through at a run. Rounding to
          // a spacing instead of solving for coverage left about one sample in
          // twenty of a five-metre wall unguarded.
          const steps = clamp(Math.ceil(sx / (r * 2)), 1, 6);
          // Along local +X, which the instance matrix takes to (cos, -sin).
          const span = (sx * 0.5 - r) * 2 / Math.max(1, steps - 1 || 1);
          const ux = Math.cos(yaw) * span;
          const uz = -Math.sin(yaw) * span;
          for (let k = 0; k < steps; k++) {
            const t = steps === 1 ? 0 : k - (steps - 1) * 0.5;
            const px = fx + ux * t, pz = fz + uz * t;
            const dx = px - x, dz = pz - z;
            const rr = r + radius;
            if (dx * dx + dz * dz < rr * rr) out.push({ x: px, z: pz, r });
          }
        }
      }
    }
    return out;
  }

  evictFarChunks(camX, camZ, keepRadius) {
    // Clutter is evicted on a much tighter radius than props: it is never drawn
    // beyond a few hundred metres and it is by far the heavier cache.
    this._evict(this.clutterCache, camX, camZ, Math.min(keepRadius, 420), 24);
    this._evict(this.featureCache, camX, camZ, keepRadius, 160);
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
