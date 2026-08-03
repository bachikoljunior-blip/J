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
import { CHUNK_SIZE, CHUNKS, WORLD_HALF, WATER_LEVEL, BIOME } from './worldgen.js';
import { clamp, lerp, saturate } from '../core/math.js';

export const PROP = {
  TREE_BROAD: 0, TREE_CONIFER: 1, TREE_DEAD: 2,
  BUSH: 3, ROCK_S: 4, ROCK_L: 5, REED: 6,
};

const PROP_CELL = 9;    // metres between scatter candidates

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

export class Scatter {
  constructor(world) {
    this.world = world;
    this.cache = new Map();     // chunkKey -> array of props
    this.blockers = [];         // circles where scatter is suppressed (POIs)
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
    if (this.cache.size < 160) return;
    const drop = [];
    for (const key of this.cache.keys()) {
      const cx = key % CHUNKS, cz = Math.floor(key / CHUNKS);
      const centerX = cx * CHUNK_SIZE - WORLD_HALF + CHUNK_SIZE / 2;
      const centerZ = cz * CHUNK_SIZE - WORLD_HALF + CHUNK_SIZE / 2;
      if (Math.hypot(centerX - camX, centerZ - camZ) > keepRadius) drop.push(key);
    }
    for (const k of drop) this.cache.delete(k);
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

          const height = (0.22 + r3 * 0.26) * (0.75 + moist * 0.6);
          const width = 0.085 + r0 * 0.07;
          const yaw = r1 * Math.PI * 2;

          // Tint follows the biome ground colour, shifted greener and varied.
          const dry = biome === BIOME.ASH || biome === BIOME.SNOW || biome === BIOME.CRAG;
          const cr = dry ? 0.34 + r3 * 0.10 : lerp(0.30, 0.20, moist) + r3 * 0.10;
          const cg = dry ? 0.30 + r3 * 0.08 : lerp(0.44, 0.52, moist) + r2 * 0.10;
          const cb = dry ? 0.22 + r3 * 0.06 : 0.16 + r1 * 0.10;

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
