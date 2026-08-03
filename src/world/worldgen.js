// ============================================================================
//  worldgen.js — the land of Aldrath.
//
//  The terrain is fully procedural but the *layout* is authored: seven named
//  regions sit at fixed compass positions, each with its own elevation bias,
//  palette, enemy roster and set-piece. Procedural noise fills the space
//  between them. That combination is what makes an open world feel designed
//  rather than sampled — you can give directions to a landmark and have them
//  mean something.
//
//  Everything derives from one seed, and generation is written as a coroutine
//  so the loading screen can show real progress instead of freezing.
// ============================================================================

import { Noise2D, makeRng, hashSeed, hash2 } from '../core/rng.js';
import { clamp, lerp, smoothstep, saturate } from '../core/math.js';

export const WORLD_SIZE = 2560;
export const WORLD_HALF = WORLD_SIZE / 2;
export const GRID_STEP = 4;
export const GRID = WORLD_SIZE / GRID_STEP + 1;   // 641
export const WATER_LEVEL = 0;
export const CHUNK_SIZE = 128;
export const CHUNKS = WORLD_SIZE / CHUNK_SIZE;    // 20

export const BIOME = {
  OCEAN: 0, BEACH: 1, MEADOW: 2, FOREST: 3, MARSH: 4,
  HIGHLAND: 5, CRAG: 6, SNOW: 7, ASH: 8,
};

export const BIOME_INFO = {
  [BIOME.OCEAN]: { name: '沿岸', ground: [0.42, 0.40, 0.32], rock: [0.34, 0.33, 0.31] },
  [BIOME.BEACH]: { name: '砂浜', ground: [0.74, 0.68, 0.52], rock: [0.52, 0.49, 0.44] },
  [BIOME.MEADOW]: { name: '草原', ground: [0.34, 0.50, 0.22], rock: [0.40, 0.39, 0.36] },
  [BIOME.FOREST]: { name: '森', ground: [0.20, 0.36, 0.16], rock: [0.32, 0.33, 0.30] },
  [BIOME.MARSH]: { name: '湿地', ground: [0.27, 0.31, 0.18], rock: [0.29, 0.30, 0.26] },
  [BIOME.HIGHLAND]: { name: '高地', ground: [0.29, 0.38, 0.24], rock: [0.38, 0.38, 0.38] },
  [BIOME.CRAG]: { name: '岩場', ground: [0.36, 0.34, 0.30], rock: [0.44, 0.43, 0.42] },
  [BIOME.SNOW]: { name: '雪嶺', ground: [0.78, 0.82, 0.88], rock: [0.46, 0.48, 0.52] },
  [BIOME.ASH]: { name: '焦土', ground: [0.21, 0.18, 0.18], rock: [0.24, 0.21, 0.20] },
};

/**
 * Authored regions. `cx/cz` place the region centre; `radius` controls how far
 * its influence reaches; the elevation fields bias the noise underneath it.
 */
export const REGIONS = [
  {
    id: 'meadow', name: '竜草の草原', reading: 'Wyrmgrass Meadow',
    cx: 0, cz: 420, radius: 620,
    elevBase: 14, elevAmp: 22, rugged: 0.25, moisture: 0.5,
    biome: BIOME.MEADOW, level: 1,
    blurb: '王国の穀倉地帯だった場所。今は野盗と亡骸が徘徊する。',
  },
  {
    id: 'wood', name: '囁きの森', reading: 'Whispering Wood',
    cx: -760, cz: 120, radius: 620,
    elevBase: 20, elevAmp: 26, rugged: 0.35, moisture: 0.85,
    biome: BIOME.FOREST, level: 8,
    blurb: '樹冠が空を覆い、昼でも薄暗い。木々が見ている。',
  },
  {
    id: 'mire', name: '灰泥の沼', reading: 'Mireash Swamp',
    cx: 700, cz: 640, radius: 520,
    elevBase: 2.5, elevAmp: 8, rugged: 0.12, moisture: 1.0,
    biome: BIOME.MARSH, level: 14,
    blurb: '毒の霧が立ちこめる低地。踏み込めば足を取られる。',
  },
  {
    id: 'ridge', name: '鉄嶺', reading: 'Ironridge Highlands',
    cx: -180, cz: -560, radius: 660,
    elevBase: 52, elevAmp: 46, rugged: 0.62, moisture: 0.45,
    biome: BIOME.HIGHLAND, level: 22,
    blurb: '誓約者たちの砦が連なる稜線。鉄の掟だけが残っている。',
  },
  {
    id: 'crag', name: '蒼玉の断崖', reading: 'Cragfall',
    cx: -880, cz: -880, radius: 560,
    elevBase: 78, elevAmp: 74, rugged: 0.92, moisture: 0.2,
    biome: BIOME.CRAG, level: 30,
    blurb: '垂直に切り立った岩の海。竜が巣を張る。',
  },
  {
    id: 'waste', name: '焦土', reading: 'The Cinderwaste',
    cx: 860, cz: -420, radius: 620,
    elevBase: 30, elevAmp: 34, rugged: 0.55, moisture: 0.05,
    biome: BIOME.ASH, level: 38,
    blurb: '王冠が砕けた場所。灰が降り続け、火が消えない。',
  },
  {
    id: 'peak', name: '白牙峰', reading: 'Whitefang Peak',
    cx: 120, cz: -1090, radius: 440,
    elevBase: 132, elevAmp: 68, rugged: 1.0, moisture: 0.3,
    biome: BIOME.SNOW, level: 48,
    blurb: '世界の屋根。残り火の王が待つ。',
  },
];

// ---------------------------------------------------------------------------

export class World {
  constructor(seedStr = 'aldrath') {
    this.seedStr = seedStr;
    this.seed = hashSeed(seedStr);
    const rng = makeRng(this.seed);
    this.rng = rng;

    this.nBase = new Noise2D(this.seed);
    this.nRidge = new Noise2D(this.seed ^ 0x9e3779b9);
    this.nWarp = new Noise2D(this.seed ^ 0x85ebca6b);
    this.nMoist = new Noise2D(this.seed ^ 0xc2b2ae35);
    this.nRiver = new Noise2D(this.seed ^ 0x27d4eb2d);
    this.nDetail = new Noise2D(this.seed ^ 0x165667b1);

    this.height = new Float32Array(GRID * GRID);
    this.biome = new Uint8Array(GRID * GRID);
    this.moisture = new Float32Array(GRID * GRID);
    this.roadMask = new Float32Array(GRID * GRID);

    this.pois = [];
    this.roads = [];
    this.graces = [];
    this.spawnPoint = { x: 0, y: 0, z: 520 };
  }

  // -- coordinate helpers ---------------------------------------------------

  gridIndex(ix, iz) {
    ix = ix < 0 ? 0 : ix >= GRID ? GRID - 1 : ix;
    iz = iz < 0 ? 0 : iz >= GRID ? GRID - 1 : iz;
    return iz * GRID + ix;
  }

  worldToGrid(v) { return (v + WORLD_HALF) / GRID_STEP; }
  gridToWorld(i) { return i * GRID_STEP - WORLD_HALF; }

  /** Bilinear height sample. Physics, AI and rendering all read through this. */
  heightAt(x, z) {
    const gx = (x + WORLD_HALF) / GRID_STEP;
    const gz = (z + WORLD_HALF) / GRID_STEP;
    const ix = Math.floor(gx), iz = Math.floor(gz);
    const fx = gx - ix, fz = gz - iz;
    const h = this.height;
    const h00 = h[this.gridIndex(ix, iz)];
    const h10 = h[this.gridIndex(ix + 1, iz)];
    const h01 = h[this.gridIndex(ix, iz + 1)];
    const h11 = h[this.gridIndex(ix + 1, iz + 1)];
    return lerp(lerp(h00, h10, fx), lerp(h01, h11, fx), fz);
  }

  /** Surface normal from central differences on the sampled height field. */
  normalAt(x, z, out = { x: 0, y: 1, z: 0 }) {
    const d = GRID_STEP;
    const hl = this.heightAt(x - d, z);
    const hr = this.heightAt(x + d, z);
    const hd = this.heightAt(x, z - d);
    const hu = this.heightAt(x, z + d);
    let nx = hl - hr, ny = 2 * d, nz = hd - hu;
    const l = Math.hypot(nx, ny, nz) || 1;
    out.x = nx / l; out.y = ny / l; out.z = nz / l;
    return out;
  }

  slopeAt(x, z) {
    const n = this.normalAt(x, z, this._tmpN || (this._tmpN = { x: 0, y: 1, z: 0 }));
    return 1 - n.y;
  }

  biomeAt(x, z) {
    const ix = Math.round(this.worldToGrid(x));
    const iz = Math.round(this.worldToGrid(z));
    return this.biome[this.gridIndex(ix, iz)];
  }

  roadAt(x, z) {
    const ix = Math.round(this.worldToGrid(x));
    const iz = Math.round(this.worldToGrid(z));
    return this.roadMask[this.gridIndex(ix, iz)];
  }

  /** Blended region influence at a point — used for palettes and difficulty. */
  regionAt(x, z) {
    let best = REGIONS[0], bestW = -1;
    for (const r of REGIONS) {
      const d = Math.hypot(x - r.cx, z - r.cz);
      const w = 1 - saturate(d / r.radius);
      if (w > bestW) { bestW = w; best = r; }
    }
    return { region: best, weight: Math.max(bestW, 0) };
  }

  // -- generation -----------------------------------------------------------

  /**
   * Raw elevation before rivers and roads. Kept separate so the carving passes
   * can operate on the baked grid rather than re-evaluating noise.
   */
  rawElevation(wx, wz) {
    const s = 0.00075;
    const x = wx * s, z = wz * s;

    // Region influence: weighted blend of the authored elevation profiles.
    let wSum = 0, elevBase = 0, elevAmp = 0, rugged = 0;
    for (const r of REGIONS) {
      const d = Math.hypot(wx - r.cx, wz - r.cz);
      // Smooth, wide falloff so regions blend instead of tiling.
      const t = saturate(1 - d / (r.radius * 1.65));
      const w = t * t * t;
      if (w <= 0) continue;
      wSum += w;
      elevBase += r.elevBase * w;
      elevAmp += r.elevAmp * w;
      rugged += r.rugged * w;
    }
    if (wSum > 0.0001) { elevBase /= wSum; elevAmp /= wSum; rugged /= wSum; }
    else { elevBase = 8; elevAmp = 14; rugged = 0.2; }

    // Base rolling terrain, domain-warped for organic valley shapes.
    const warped = this.nBase.warped(x * 2.2, z * 2.2, 0.55, 5);
    let h = elevBase + warped * elevAmp;

    // Ridged mountains layered on top, scaled by how rugged the region is.
    const ridge = this.nRidge.ridged(x * 3.1, z * 3.1, 5, 2.1, 0.5);
    h += Math.pow(ridge, 1.7) * elevAmp * 2.3 * rugged;

    // Mid-frequency detail keeps slopes from reading as smooth blobs.
    h += this.nDetail.fbm(x * 9.0, z * 9.0, 3) * (3.0 + rugged * 8.0);

    // Continental falloff — the map is an island, so the border is ocean and
    // the player is never staring at an invisible wall.
    const d = Math.max(Math.abs(wx), Math.abs(wz)) / WORLD_HALF;
    const radial = Math.hypot(wx, wz) / (WORLD_HALF * 1.28);
    const edge = Math.max(d, radial);
    const shore = 1 - smoothstep(clamp((edge - 0.70) / 0.30, 0, 1));
    h = h * shore - (1 - shore) * 26;

    return h;
  }

  /** Distance-to-river field in [0,1]; 0 = channel centre. */
  riverField(wx, wz) {
    const s = 0.00052;
    const n = this.nRiver.warped(wx * s, wz * s, 1.1, 4);
    return Math.abs(n);
  }

  /**
   * Coroutine: yields a 0..1 progress value. Driven by the loader so the UI
   * stays responsive during the ~1s of terrain baking.
   */
  *generate() {
    const step = 24;   // rows per yield

    // --- pass 1: elevation --------------------------------------------------
    for (let iz = 0; iz < GRID; iz++) {
      const wz = this.gridToWorld(iz);
      for (let ix = 0; ix < GRID; ix++) {
        const wx = this.gridToWorld(ix);
        let h = this.rawElevation(wx, wz);

        // River carving: a V-channel wherever the river field is near zero.
        const rf = this.riverField(wx, wz);
        const bank = 0.055;
        if (rf < bank && h > -6) {
          const t = 1 - rf / bank;                // 0 at bank, 1 at centre
          const depth = 9 * t * t + 2 * t;
          const target = Math.min(h, WATER_LEVEL - 0.4);
          h = lerp(h, target - depth * 0.35, smoothstep(t) * 0.92);
        }

        this.height[iz * GRID + ix] = h;
      }
      if (iz % step === 0) yield 0.05 + 0.45 * (iz / GRID);
    }

    // --- pass 2: light thermal erosion --------------------------------------
    // Two relaxation passes knock the sharpest noise spikes off cliffs so the
    // player is not constantly blocked by 80-degree pinnacles.
    for (let pass = 0; pass < 2; pass++) {
      const src = this.height;
      const dst = new Float32Array(src.length);
      dst.set(src);
      for (let iz = 1; iz < GRID - 1; iz++) {
        for (let ix = 1; ix < GRID - 1; ix++) {
          const i = iz * GRID + ix;
          const c = src[i];
          const n = [src[i - 1], src[i + 1], src[i - GRID], src[i + GRID]];
          let moved = 0;
          for (const h of n) {
            const diff = c - h;
            // Talus angle: only material above ~40 degrees slumps.
            if (diff > GRID_STEP * 0.85) moved += (diff - GRID_STEP * 0.85) * 0.18;
          }
          dst[i] = c - moved * 0.25;
        }
      }
      this.height = dst;
      yield 0.5 + 0.06 * pass;
    }

    // --- pass 3: moisture + biome -------------------------------------------
    for (let iz = 0; iz < GRID; iz++) {
      const wz = this.gridToWorld(iz);
      for (let ix = 0; ix < GRID; ix++) {
        const wx = this.gridToWorld(ix);
        const i = iz * GRID + ix;
        const h = this.height[i];

        let regionMoist = 0.4, wSum = 0;
        for (const r of REGIONS) {
          const d = Math.hypot(wx - r.cx, wz - r.cz);
          const t = saturate(1 - d / (r.radius * 1.5));
          const w = t * t;
          if (w > 0) { regionMoist += r.moisture * w; wSum += w; }
        }
        if (wSum > 0) regionMoist /= (wSum + 1);

        const nm = this.nMoist.fbm(wx * 0.0012, wz * 0.0012, 4) * 0.5 + 0.5;
        const riverBonus = saturate(1 - this.riverField(wx, wz) / 0.16) * 0.35;
        const m = saturate(regionMoist * 0.65 + nm * 0.35 + riverBonus);
        this.moisture[i] = m;

        // Nearest authored region decides the base biome. The distance is
        // perturbed by low-frequency noise so borders interlock like real
        // ecotones instead of forming a Voronoi diagram.
        const warpA = this.nWarp.fbm(wx * 0.0016, wz * 0.0016, 3);
        const warpB = this.nWarp.fbm(wx * 0.0042 + 31.7, wz * 0.0042 - 12.3, 3);
        const jitter = 1 + warpA * 0.26 + warpB * 0.10;
        let best = null, bestW = -Infinity;
        for (const r of REGIONS) {
          const d = Math.hypot(wx - r.cx, wz - r.cz) * jitter;
          const w = 1 - d / r.radius;
          if (w > bestW) { bestW = w; best = r; }
        }

        let b = best ? best.biome : BIOME.MEADOW;
        if (bestW < -0.25) b = BIOME.MEADOW;               // the in-between land
        const slope = this._slopeFromGrid(ix, iz);

        if (h < WATER_LEVEL - 0.5) b = BIOME.OCEAN;
        else if (h < WATER_LEVEL + 1.6) b = BIOME.BEACH;
        else if (h > 118 + this.nDetail.noise(wx * 0.004, wz * 0.004) * 16) b = BIOME.SNOW;
        else if (slope > 0.62 && h > 24) b = BIOME.CRAG;
        else if (b === BIOME.MARSH && h > 12) b = BIOME.MEADOW;
        this.biome[i] = b;
      }
      if (iz % step === 0) yield 0.56 + 0.18 * (iz / GRID);
    }

    yield 0.76;
    this._placeRegionSites();
    yield 0.84;
    this._buildRoads();
    yield 0.92;
    this._placeScatteredPois();
    yield 0.97;
    this._chooseSpawn();
    yield 1.0;
  }

  _slopeFromGrid(ix, iz) {
    const h = this.height;
    const c = h[this.gridIndex(ix, iz)];
    const l = h[this.gridIndex(ix - 1, iz)];
    const r = h[this.gridIndex(ix + 1, iz)];
    const d = h[this.gridIndex(ix, iz - 1)];
    const u = h[this.gridIndex(ix, iz + 1)];
    const dx = (r - l) / (2 * GRID_STEP);
    const dz = (u - d) / (2 * GRID_STEP);
    return 1 - 1 / Math.sqrt(1 + dx * dx + dz * dz);
  }

  /** Find buildable ground near a target: gentle slope, above water. */
  findFlatSpot(cx, cz, searchRadius = 140, maxSlope = 0.18, rng = this.rng) {
    let best = null, bestScore = -Infinity;
    for (let i = 0; i < 220; i++) {
      const a = rng() * Math.PI * 2;
      const r = Math.sqrt(rng()) * searchRadius;
      const x = cx + Math.cos(a) * r;
      const z = cz + Math.sin(a) * r;
      if (Math.abs(x) > WORLD_HALF - 60 || Math.abs(z) > WORLD_HALF - 60) continue;
      const h = this.heightAt(x, z);
      if (h < WATER_LEVEL + 2.5) continue;
      const s = this.slopeAt(x, z);
      if (s > maxSlope) continue;
      const score = -s * 8 - r / searchRadius;
      if (score > bestScore) { bestScore = score; best = { x, z, y: h }; }
    }
    if (!best) {
      const h = this.heightAt(cx, cz);
      best = { x: cx, z: cz, y: h };
    }
    return best;
  }

  // -- points of interest ---------------------------------------------------

  addPoi(poi) {
    poi.id = poi.id || `${poi.kind}_${this.pois.length}`;
    poi.y = poi.y !== undefined ? poi.y : this.heightAt(poi.x, poi.z);
    this.pois.push(poi);
    if (poi.kind === 'grace') this.graces.push(poi);
    return poi;
  }

  /**
   * Each authored region gets a fixed set-piece: a grace, a settlement or camp
   * cluster, and a boss arena. This is the backbone the player navigates by.
   */
  _placeRegionSites() {
    const rng = makeRng(this.seed ^ 0x5f3a);

    const SITES = {
      meadow: { grace: '朽ちた道標', camps: 3, ruins: 2, village: '灯火の村', boss: null, mini: 'bandit_chief' },
      wood: { grace: '苔むした祠', camps: 3, ruins: 2, village: null, boss: 'warden', mini: 'wolf_alpha' },
      mire: { grace: '沈んだ社', camps: 2, ruins: 3, village: null, boss: 'mirequeen', mini: null },
      ridge: { grace: '誓いの炉', camps: 3, ruins: 3, village: '鉄砦', boss: 'ironsworn', mini: 'sentinel_captain' },
      crag: { grace: '風喰みの棚', camps: 2, ruins: 2, village: null, boss: 'drake', mini: null },
      waste: { grace: '灰の祭壇', camps: 3, ruins: 3, village: null, boss: 'ashking', mini: 'wraith_lord' },
      peak: { grace: '頂の火', camps: 1, ruins: 2, village: null, boss: 'sovereign', mini: null },
    };

    for (const region of REGIONS) {
      const cfg = SITES[region.id];
      if (!cfg) continue;

      // Grace: the region's anchor. Deliberately placed toward the region
      // entrance (biased back toward world centre) so it is found early.
      const towardCentre = Math.atan2(-region.cz, -region.cx);
      const gx = region.cx + Math.cos(towardCentre) * region.radius * 0.42;
      const gz = region.cz + Math.sin(towardCentre) * region.radius * 0.42;
      const gspot = this.findFlatSpot(gx, gz, 120, 0.16, rng);
      this.addPoi({
        kind: 'grace', id: `grace_${region.id}`, name: cfg.grace,
        x: gspot.x, z: gspot.z, region: region.id, discovered: false,
      });

      // Boss arena: deep inside the region, away from the grace.
      if (cfg.boss) {
        const ba = towardCentre + Math.PI + (rng() - 0.5) * 0.9;
        const bx = region.cx + Math.cos(ba) * region.radius * 0.46;
        const bz = region.cz + Math.sin(ba) * region.radius * 0.46;
        const bspot = this.findFlatSpot(bx, bz, 150, 0.20, rng);
        this._flatten(bspot.x, bspot.z, 34, 0.85);
        this.addPoi({
          kind: 'boss', id: `boss_${cfg.boss}`, boss: cfg.boss,
          name: BOSS_SITE_NAMES[cfg.boss] || '闘技場',
          x: bspot.x, z: bspot.z, region: region.id, radius: 30, cleared: false, discovered: false,
        });
        // A grace right outside every boss arena — the checkpoint contract.
        const ga = ba + Math.PI;
        const gg = this.findFlatSpot(bspot.x + Math.cos(ga) * 62, bspot.z + Math.sin(ga) * 62, 40, 0.2, rng);
        this.addPoi({
          kind: 'grace', id: `grace_${cfg.boss}_gate`, name: `${cfg.grace}・前庭`,
          x: gg.x, z: gg.z, region: region.id, discovered: false,
        });
      }

      if (cfg.mini) {
        const ma = rng() * Math.PI * 2;
        const ms = this.findFlatSpot(
          region.cx + Math.cos(ma) * region.radius * 0.55,
          region.cz + Math.sin(ma) * region.radius * 0.55, 110, 0.22, rng);
        this.addPoi({
          kind: 'mini', id: `mini_${region.id}`, boss: cfg.mini,
          name: MINI_SITE_NAMES[cfg.mini] || '野営跡',
          x: ms.x, z: ms.z, region: region.id, radius: 20, cleared: false, discovered: false,
        });
      }

      if (cfg.village) {
        const va = towardCentre + (rng() - 0.5) * 1.4;
        const vs = this.findFlatSpot(
          region.cx + Math.cos(va) * region.radius * 0.30,
          region.cz + Math.sin(va) * region.radius * 0.30, 130, 0.13, rng);
        this._flatten(vs.x, vs.z, 42, 0.9);
        this.addPoi({
          kind: 'village', id: `village_${region.id}`, name: cfg.village,
          x: vs.x, z: vs.z, region: region.id, radius: 40, discovered: false,
        });
      }

      for (let i = 0; i < cfg.camps; i++) {
        const a = rng() * Math.PI * 2;
        const r = region.radius * (0.30 + rng() * 0.55);
        const spot = this.findFlatSpot(region.cx + Math.cos(a) * r, region.cz + Math.sin(a) * r, 90, 0.22, rng);
        this.addPoi({
          kind: 'camp', id: `camp_${region.id}_${i}`, name: '野営地',
          x: spot.x, z: spot.z, region: region.id, radius: 16, cleared: false, discovered: false,
        });
      }

      for (let i = 0; i < cfg.ruins; i++) {
        const a = rng() * Math.PI * 2;
        const r = region.radius * (0.25 + rng() * 0.65);
        const spot = this.findFlatSpot(region.cx + Math.cos(a) * r, region.cz + Math.sin(a) * r, 100, 0.26, rng);
        this.addPoi({
          kind: 'ruin', id: `ruin_${region.id}_${i}`, name: '遺構',
          x: spot.x, z: spot.z, region: region.id, radius: 22, cleared: false, discovered: false,
        });
      }
    }
  }

  /** Lower the terrain toward its local average so structures sit level. */
  _flatten(cx, cz, radius, strength) {
    const gx0 = Math.max(0, Math.floor(this.worldToGrid(cx - radius)));
    const gx1 = Math.min(GRID - 1, Math.ceil(this.worldToGrid(cx + radius)));
    const gz0 = Math.max(0, Math.floor(this.worldToGrid(cz - radius)));
    const gz1 = Math.min(GRID - 1, Math.ceil(this.worldToGrid(cz + radius)));
    let sum = 0, n = 0;
    for (let iz = gz0; iz <= gz1; iz++) {
      for (let ix = gx0; ix <= gx1; ix++) {
        sum += this.height[iz * GRID + ix]; n++;
      }
    }
    if (!n) return;
    const target = sum / n;
    for (let iz = gz0; iz <= gz1; iz++) {
      const wz = this.gridToWorld(iz);
      for (let ix = gx0; ix <= gx1; ix++) {
        const wx = this.gridToWorld(ix);
        const d = Math.hypot(wx - cx, wz - cz);
        if (d > radius) continue;
        const t = 1 - smoothstep(saturate(d / radius));
        const i = iz * GRID + ix;
        this.height[i] = lerp(this.height[i], target, t * strength);
      }
    }
  }

  /**
   * Roads connect graces and settlements. They flatten the ground slightly and
   * write into roadMask, which the terrain shader reads as a dirt splat — the
   * result is a visible path network the player can actually navigate by.
   */
  _buildRoads() {
    const hubs = this.pois.filter((p) => p.kind === 'grace' || p.kind === 'village');
    // Greedy nearest-neighbour spanning tree: cheap, and produces the branching
    // topology real road networks have.
    if (hubs.length < 2) return;
    const connected = [hubs[0]];
    const remaining = hubs.slice(1);
    while (remaining.length) {
      let bestI = 0, bestJ = 0, bestD = Infinity;
      for (let i = 0; i < connected.length; i++) {
        for (let j = 0; j < remaining.length; j++) {
          const d = Math.hypot(connected[i].x - remaining[j].x, connected[i].z - remaining[j].z);
          if (d < bestD) { bestD = d; bestI = i; bestJ = j; }
        }
      }
      const a = connected[bestI], b = remaining[bestJ];
      this._carveRoad(a, b);
      connected.push(b);
      remaining.splice(bestJ, 1);
    }
  }

  _carveRoad(a, b) {
    const dist = Math.hypot(b.x - a.x, b.z - a.z);
    const steps = Math.max(8, Math.ceil(dist / 6));
    const pts = [];
    // Perpendicular sine offset gives the road a natural meander instead of a
    // ruler-straight line across the landscape.
    const px = -(b.z - a.z) / dist, pz = (b.x - a.x) / dist;
    const amp = Math.min(70, dist * 0.14);
    const phase = hash2(Math.round(a.x), Math.round(b.z), this.seed) * Math.PI * 2;
    for (let i = 0; i <= steps; i++) {
      const t = i / steps;
      const bend = Math.sin(t * Math.PI) * Math.sin(t * 3.1 + phase) * amp;
      const x = lerp(a.x, b.x, t) + px * bend;
      const z = lerp(a.z, b.z, t) + pz * bend;
      pts.push({ x, z });
    }
    this.roads.push(pts);

    const halfWidth = 3.2;
    for (let i = 0; i < pts.length - 1; i++) {
      const p0 = pts[i], p1 = pts[i + 1];
      const segLen = Math.hypot(p1.x - p0.x, p1.z - p0.z);
      const sub = Math.max(1, Math.ceil(segLen / 2));
      for (let s = 0; s <= sub; s++) {
        const t = s / sub;
        const x = lerp(p0.x, p1.x, t);
        const z = lerp(p0.z, p1.z, t);
        this._stampRoad(x, z, halfWidth);
      }
    }
  }

  _stampRoad(cx, cz, halfWidth) {
    const rad = halfWidth + GRID_STEP * 0.6;
    const gx0 = Math.max(0, Math.floor(this.worldToGrid(cx - rad)));
    const gx1 = Math.min(GRID - 1, Math.ceil(this.worldToGrid(cx + rad)));
    const gz0 = Math.max(0, Math.floor(this.worldToGrid(cz - rad)));
    const gz1 = Math.min(GRID - 1, Math.ceil(this.worldToGrid(cz + rad)));
    for (let iz = gz0; iz <= gz1; iz++) {
      const wz = this.gridToWorld(iz);
      for (let ix = gx0; ix <= gx1; ix++) {
        const wx = this.gridToWorld(ix);
        const d = Math.hypot(wx - cx, wz - cz);
        if (d > rad) continue;
        const t = 1 - saturate(d / rad);
        const i = iz * GRID + ix;
        this.roadMask[i] = Math.max(this.roadMask[i], t);
        // Only smooth the road bed, do not trench it.
        if (t > 0.35 && this.height[i] > WATER_LEVEL + 0.5) {
          const avg = (this.height[this.gridIndex(ix - 1, iz)] + this.height[this.gridIndex(ix + 1, iz)]
            + this.height[this.gridIndex(ix, iz - 1)] + this.height[this.gridIndex(ix, iz + 1)]) * 0.25;
          this.height[i] = lerp(this.height[i], avg, (t - 0.35) * 0.8);
        }
      }
    }
  }

  /** Chests, shrines and merchant posts sprinkled between the set-pieces. */
  _placeScatteredPois() {
    const rng = makeRng(this.seed ^ 0xa1b2);
    const tooClose = (x, z, minD) =>
      this.pois.some((p) => Math.hypot(p.x - x, p.z - z) < minD);

    // Treasure: biased toward interesting terrain (steep ground, riversides).
    let placed = 0, attempts = 0;
    while (placed < 46 && attempts < 4000) {
      attempts++;
      const x = (rng() - 0.5) * (WORLD_SIZE - 260);
      const z = (rng() - 0.5) * (WORLD_SIZE - 260);
      const h = this.heightAt(x, z);
      if (h < WATER_LEVEL + 2) continue;
      const s = this.slopeAt(x, z);
      if (s > 0.34) continue;
      if (tooClose(x, z, 90)) continue;
      const { region } = this.regionAt(x, z);
      this.addPoi({
        kind: 'chest', id: `chest_${placed}`, name: '宝箱',
        x, z, region: region.id, opened: false, discovered: false,
        tier: rng() < 0.18 ? 2 : rng() < 0.5 ? 1 : 0,
      });
      placed++;
    }

    // Merchants: one in each village, plus two wanderers on the roads.
    for (const p of this.pois.filter((v) => v.kind === 'village')) {
      this.addPoi({
        kind: 'merchant', id: `merchant_${p.region}`, name: '行商人',
        x: p.x + 8, z: p.z + 6, region: p.region, discovered: false,
      });
      this.addPoi({
        kind: 'smith', id: `smith_${p.region}`, name: '鍛冶',
        x: p.x - 9, z: p.z + 4, region: p.region, discovered: false,
      });
    }
    for (let i = 0; i < 2; i++) {
      const road = this.roads[Math.floor(rng() * this.roads.length)] || [];
      const pt = road[Math.floor(rng() * road.length)] || { x: 0, z: 0 };
      this.addPoi({
        kind: 'merchant', id: `merchant_wander_${i}`, name: '流れの商人',
        x: pt.x + 4, z: pt.z + 4, region: this.regionAt(pt.x, pt.z).region.id, discovered: false,
      });
    }

    // Shrines: small stat-boost sites that reward exploring off the roads.
    for (let i = 0; i < 12; i++) {
      let x, z, ok = false;
      for (let t = 0; t < 200 && !ok; t++) {
        x = (rng() - 0.5) * (WORLD_SIZE - 300);
        z = (rng() - 0.5) * (WORLD_SIZE - 300);
        const h = this.heightAt(x, z);
        ok = h > WATER_LEVEL + 6 && this.slopeAt(x, z) < 0.25 && !tooClose(x, z, 130);
      }
      if (!ok) continue;
      this.addPoi({
        kind: 'shrine', id: `shrine_${i}`, name: '古き祠',
        x, z, region: this.regionAt(x, z).region.id, used: false, discovered: false,
      });
    }
  }

  _chooseSpawn() {
    const g = this.pois.find((p) => p.id === 'grace_meadow');
    if (g) {
      this.spawnPoint = { x: g.x + 4, y: this.heightAt(g.x + 4, g.z + 4), z: g.z + 4 };
      g.discovered = true;
      g.isStart = true;
    } else {
      const s = this.findFlatSpot(0, 400, 200, 0.15);
      this.spawnPoint = { x: s.x, y: s.y, z: s.z };
    }
  }

  /** Recommended level for content at a location — drives loot and scaling. */
  levelAt(x, z) {
    let acc = 0, wSum = 0;
    for (const r of REGIONS) {
      const d = Math.hypot(x - r.cx, z - r.cz);
      const t = saturate(1 - d / (r.radius * 1.5));
      const w = t * t + 0.0001;
      acc += r.level * w; wSum += w;
    }
    return Math.max(1, Math.round(acc / wSum));
  }
}

export const BOSS_SITE_NAMES = {
  warden: '縛り手の空洞',
  mirequeen: '沈殿の玉座',
  ironsworn: '誓約の闘技場',
  drake: '竜の棚',
  ashking: '燼の玉座',
  sovereign: '残り火の頂',
};

export const MINI_SITE_NAMES = {
  bandit_chief: '首魁の砦',
  wolf_alpha: '狼の巣',
  sentinel_captain: '哨戒隊の陣',
  wraith_lord: '灰の輪',
};
