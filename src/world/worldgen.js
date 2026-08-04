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
  // Surface materials, not places. See the note under BIOME_INFO.
  CINDER: 9, DRIFT: 10, PEAT: 11, SEDGE: 12,
};

/**
 * Ground and stone colour per biome. The terrain builder reads `ground` for the
 * per-vertex tint and the scatter reads both, so this table is the whole
 * palette of the island.
 *
 * The last four ids are not regions. They are the surfaces the Cinderwaste and
 * the mire are made of, and they exist because those two places were each
 * being painted in exactly one colour.
 *
 * That is a real problem and not a cosmetic one. Both biomes are dark by
 * design — ash sits at a sixth of the meadow's reflectance — so the light has
 * far less to work with there to begin with; if on top of that every square
 * metre carries the same albedo, the only thing separating one part of the
 * frame from another is the shading of the surface normal, and on a plain that
 * is almost nothing. Neither place is actually like that. Ash country is pale
 * drift where the wind has dropped it, black burnt ground where the wind has
 * taken it away, and the ordinary grey of settled fall in between. A mire is
 * black peat in the creases, pale dead sedge on the mound tops, and wet ground
 * between. Splitting each into three material ids gives the terrain tint a
 * five-to-one value range to work in, which is what those two landscapes have
 * in life and is worth more to them than any amount of extra geometry.
 */
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
  // Burnt ground: what is left when the wind has stripped the fall off it.
  // Nearly black, faintly warm, because it is fired earth rather than soot.
  [BIOME.CINDER]: { name: '焼け野', ground: [0.088, 0.074, 0.068], rock: [0.155, 0.128, 0.115] },
  // Fresh drift. Wood ash really is this pale — it is the one bright material
  // the Cinderwaste has, and withholding it is what made the place read grey.
  [BIOME.DRIFT]: { name: '灰丘', ground: [0.55, 0.52, 0.49], rock: [0.32, 0.30, 0.28] },
  // Saturated peat: black, and the shallows of the mire are made of it.
  [BIOME.PEAT]: { name: '泥炭地', ground: [0.115, 0.105, 0.080], rock: [0.19, 0.19, 0.17] },
  // Last year's cane, standing dead. A winter reedbed is genuinely one of the
  // brightest surfaces in any landscape — pale straw-gold, not green — and it
  // is what the mire has instead of the sand beach the shoreline rule used to
  // draw around every pool.
  [BIOME.SEDGE]: { name: '菅の原', ground: [0.62, 0.58, 0.36], rock: [0.32, 0.31, 0.27] },
};

// ---------------------------------------------------------------------------
//  Ground-scale relief.
//
//  The landform passes below (warped fBm, ridged mountains, a mid-frequency
//  octave) produce nothing shorter than about forty metres, so open country
//  arrives as an unbroken plane and the light has nothing to model: standing in
//  the meadow, every square metre in frame carries the same shading. Real flat
//  country is never planar. Meadow, marsh and ash plain all undulate at the
//  scale of a few paces, and that undulation is most of what you actually see
//  when you stand in one.
//
//  All of it goes into the height field itself rather than into the mesh or
//  the shader, because heightAt() is the single source of truth for collision,
//  prop placement, water and the minimap: form the player can see but not
//  stand on is worse than no form at all. It also means none of this costs a
//  triangle — the finest LOD already samples at exactly the 4 m grid spacing.
//
//  That grid spacing is also the floor. A feature much narrower than three
//  samples cannot be stored, so the shortest wavelength here is 11 m.
//  Amplitudes are chosen against the rule that governs everything below: the
//  steepest thing any of it produces is around one in three, which is ground
//  you run over without noticing rather than terrain you path around.
// ---------------------------------------------------------------------------

// Three fixed wavelengths rather than an fBm, so the amplitudes stay legible.
// The weighting is toward the short end: a metre of amplitude at 15 m turns the
// surface normal about twice as much as a metre at 26 m does, for the same
// slope underfoot, because the 4 m grid renders the short one as facets with a
// real break between them. Anything under about 10 m is past the point where
// the grid can hold it at all — the reconstruction beats against the sample
// spacing and the mound you see is not quite the mound you walk on.
const SWELL_LEN = 26, SWELL_AMP = 2.2;      // broad ground swells
const MOUND_LEN = 15, MOUND_AMP = 1.3;      // hummocks — the scale underfoot
const DIMPLE_LEN = 11, DIMPLE_AMP = 0.55;   // ankle-height, and the grid floor

// Banks. Tread spacing works out near 45 m, the riser occupies under a fifth,
// so a bank is about 2.2 m of drop over 8 m of ground — two paces of real
// break, which is what makes one readable from across a plain.
const BENCH_FLIGHT = 13.0;
const BENCH_RISER_FRAC = 0.18;
const BENCH_RISE = 2.75;

// Dry watercourses, at two scales, because drainage is fractal and a single
// scale of it reads as a canal. GULLY_BANK is a threshold on a distance-like
// field rather than a width; it works out around twelve metres either side of
// a wash and five either side of a rill. GULLY_BED is the inner fraction that
// is level gravel floor — a wash is not a V, it is a flat bed between two
// banks, and it is those two break lines that make one readable across a
// plain.
const GULLY_SCALE = 0.0024, GULLY_BANK = 0.075, GULLY_DEPTH = 2.4;
const RILL_SCALE = 0.0062, RILL_BANK = 0.085, RILL_DEPTH = 1.1;
const GULLY_BED = 0.55;

// Ash dunes. The windward fraction is deliberately far from a half — that
// asymmetry is the whole point, and it puts a ten-metre lee face under every
// crest, which is the steepest honest thing on the whole plain.
const DUNE_SPACING = 38;
const DUNE_WINDWARD = 0.74;
const DUNE_HEIGHT = 5.0;

// Tussock relief. Larger than it looks, and it has to be: the mire is the one
// open region with no dry watercourses in it — the gully pass only cuts above
// the water table, which is most of what gives the meadow its break lines —
// and its landform is the shallowest on the island. Measured at the same
// camera, the mire's ground was turning the surface normal a little over half
// as much per metre as the meadow's, on a surface that in life is the most
// broken ground in the world. All of that has to come from the mounds.
const TUSSOCK_AMP = 3.0;
const TUSSOCK_FINE = 2.2;

// Where each plain's three surfaces divide. Chosen against the material fields
// below to leave roughly a third of the ground in each class: enough of the
// dark to keep both places bleak, enough of the pale to give the light a range
// to work in, and enough of the middle that the two extremes read as the ends
// of something rather than as two colours.
const ASH_BURNT = -0.48, ASH_PALE = 0.10;
const MIRE_BLACK = -0.30, MIRE_PALE = 0.20;

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
    this.nGround = new Noise2D(this.seed ^ 0x3b1f77c1);   // hummocks, tussocks
    this.nBench = new Noise2D(this.seed ^ 0x6f4e2d09);    // banks and benches
    this.nGully = new Noise2D(this.seed ^ 0x7ad39b45);    // dry watercourses
    this.nDune = new Noise2D(this.seed ^ 0x1c9a55e3);     // ash drift

    // Prevailing wind for the Cinderwaste, fixed per world. Dunes are the one
    // landform with a direction, so it has to come from somewhere stable.
    const wind = hash2(7, 13, this.seed) * Math.PI * 2;
    this._windC = Math.cos(wind);
    this._windS = Math.sin(wind);

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
    // Non-finite input must not fall through: NaN survives every comparison
    // below and would produce NaN indices that silently read `undefined` all
    // the way into terrain generation.
    if (!Number.isFinite(ix)) ix = 0;
    if (!Number.isFinite(iz)) iz = 0;
    ix = ix < 0 ? 0 : ix >= GRID ? GRID - 1 : ix | 0;
    iz = iz < 0 ? 0 : iz >= GRID ? GRID - 1 : iz | 0;
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

  /**
   * Grass clumping, 0..1, at metre scale.
   *
   * Deliberately not stored in the grid: it is needed at a finer resolution
   * than GRID_STEP and only while the grass patch rebuilds, so evaluating the
   * noise twice per blade is cheaper than another 640k-entry array. Two octaves
   * give both the patch (~6 m) and the thinning at its edge (~1.5 m).
   */
  grassClump(x, z) {
    if (!this._clumpNoise) this._clumpNoise = new Noise2D(this.seed ^ 0x51ab7);
    const a = this._clumpNoise.noise(x * 0.17, z * 0.17) * 0.5 + 0.5;
    const b = this._clumpNoise.noise(x * 0.63, z * 0.63) * 0.5 + 0.5;
    return saturate((a * 0.72 + b * 0.28 - 0.28) * 1.9);
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
   * Ground-scale undulation: hummocks, swells and the hollows between them.
   *
   * Three fixed wavelengths rather than an fBm so the amplitudes stay legible
   * and bounded — an fBm with enough octaves to reach 12 m would also drag its
   * long-wavelength energy in and quietly change the landform.
   *
   * @param {number} wx world X
   * @param {number} wz world Z
   * @param {number} open 0 on crags, 1 on the plains
   * @returns {number} metres to add to the landform height
   */
  groundRelief(wx, wz, open) {
    if (open <= 0.01) return 0;
    const n = this.nGround;
    // Ground is not uniformly hummocky: quiet stretches and busy ones, at the
    // scale of a few hundred metres. The floor is high on purpose — a patch of
    // genuinely planar meadow is the thing being removed, and anything that
    // leaves one behind just relocates the problem instead of fixing it.
    const calm = 0.72 + 0.28 * (n.noise(wx * 0.0021, wz * 0.0021) * 0.5 + 0.5);
    // Hollows read broader and shallower than mounds are tall, because soil
    // and water both collect in them. Softening the negative half is what
    // keeps this from looking like a field of bubbles.
    const shape = (v, amp) => (v > 0 ? v : v * 0.75) * amp;
    return (shape(n.noise(wx / SWELL_LEN, wz / SWELL_LEN), SWELL_AMP)
      + shape(n.noise(wx / MOUND_LEN + 41.3, wz / MOUND_LEN - 7.9), MOUND_AMP)
      + shape(n.noise(wx / DIMPLE_LEN - 18.6, wz / DIMPLE_LEN + 23.1), DIMPLE_AMP))
      * open * calm;
  }

  /**
   * Banks and benches — the short steep breaks where a plain steps down to the
   * next level, with the ground holding level between them.
   *
   * Built as a level set of a slow field taken through a hard shoulder. The
   * field's own ramp is subtracted back out so this contributes stepping only:
   * it must not become a second landform octave and move the coastline.
   *
   * @returns {number} metres to add, bounded by +/- 0.42 * BENCH_RISE
   */
  benchStep(wx, wz, open) {
    if (open <= 0.01) return 0;
    const n = this.nBench;
    const x = wx * 0.0026, z = wz * 0.0026;
    // Terraces come in flights with smooth country between them, so where they
    // occur is itself a slow field — biased so that most open ground is
    // benched somewhere in view and the unbenched stretches are the exception.
    const mask = saturate((n.noise(x * 0.42 + 61.4, z * 0.42 - 17.2) + 0.36) * 1.7);
    if (mask <= 0.01) return 0;
    const f = n.fbm(x, z, 2) * BENCH_FLIGHT;
    const k = Math.floor(f);
    const t = f - k;
    const riser = smoothstep(saturate((t - 0.40) / BENCH_RISER_FRAC));
    // riser - t: a short rise onto the tread, then a long gentle fall away
    // from it. That is a scarp with a dip slope behind it, which is what a
    // stepped plain actually looks like from ground level.
    return (riser - t) * BENCH_RISE * mask * open;
  }

  /**
   * Distance-to-dry-watercourse field in [0,1]; 0 = channel line.
   *
   * The same construction as riverField at a fifth of the scale, so the dry
   * courses run with the drainage they feed — following one downhill always
   * brings you to water, which makes them navigation as well as form.
   *
   * @param {number} s frequency: GULLY_SCALE for washes, RILL_SCALE for the
   *   rills that feed them
   * @param {number} off decorrelates the two networks, which are otherwise the
   *   same pattern at two sizes
   */
  gullyField(wx, wz, s = GULLY_SCALE, off = 0) {
    const x = wx * s + off, z = wz * s - off;
    // One warp pass. Without it the channels are smooth curves; with it they
    // braid and rejoin the way runoff actually cuts ground.
    const a = this.nGully.noise(x * 0.6 + 3.1, z * 0.6 - 1.7);
    const b = this.nGully.noise(x * 0.6 - 8.3, z * 0.6 + 5.9);
    return Math.abs(this.nGully.fbm(x + a * 0.9, z + b * 0.9, 3));
  }

  /**
   * Channel cross-section, 0 at the bank top and 1 on the bed.
   * @param {number} u distance from the channel line, normalised to the bank
   */
  channelProfile(u) {
    return smoothstep(saturate((1 - u) / (1 - GULLY_BED)));
  }

  /**
   * Dune profile at a point: 0 on the pan floor, 1 on the crest, with the
   * interdune mask already applied.
   *
   * Both the height field and the surface material read it, and they have to
   * read the *same* one. Fresh ash lies where the wind dropped it, which is the
   * dune it built; if the pale material were computed from its own copy of
   * these numbers the two would part company on the first edit and the drift
   * would end up lying beside the dunes instead of on them.
   */
  _duneProfile(wx, wz) {
    const n = this.nDune;
    const u = wx * this._windC + wz * this._windS;    // downwind
    const v = -wx * this._windS + wz * this._windC;   // along the crest
    // Interdune pans. The old bias sat so far positive that this never reached
    // zero, so the plain was wall-to-wall dune and read as corrugation; but a
    // gentle ramp is no better, because it scales every dune down instead of
    // choosing between dune country and pan. An erg does choose: this is close
    // to a threshold, with a band of a few dozen metres where the field dies
    // out so the edge of it is not a line.
    const drift = smoothstep(saturate(n.noise(u * 0.0032 + 12.7, v * 0.0026 - 5.1) * 5.0 + 1.0));
    if (drift <= 0.001) return 0;
    // Crests wander along their length instead of ruling straight lines.
    const meander = n.noise(u * 0.0048, v * 0.0075) * 15;
    const p = (u + meander) / DUNE_SPACING;
    const t = p - Math.floor(p);
    // The lee face is linear and that is the entire shape. A dune has a brink
    // at the top of its slip face and a toe at the bottom, and those two break
    // lines are what makes one legible from a kilometre away. Smoothstepping
    // the lee rounded both off and buried the steepest ground in the middle of
    // the face where nothing can read it — and it was steeper there than this
    // is anywhere: smoothstep peaks at 1.5x the mean slope, so the old profile
    // hit about 1 in 1.3 against 1 in 2 for the honest straight face.
    return (t < DUNE_WINDWARD
      ? smoothstep(t / DUNE_WINDWARD)
      : 1 - (t - DUNE_WINDWARD) / (1 - DUNE_WINDWARD)) * drift;
  }

  /**
   * Wind-drifted ash dunes, for the Cinderwaste.
   *
   * Dunes are the one landform that is not symmetric: the windward side is a
   * long ramp material is pushed up, the lee side is the short face it
   * avalanches down. That asymmetry is what makes an ash plain read as swept
   * rather than merely bumpy.
   *
   * @param {number} w blended weight of the ash region, 0..1
   */
  ashDunes(wx, wz, w) {
    if (w <= 0.01) return 0;
    return this._duneProfile(wx, wz) * DUNE_HEIGHT * w;
  }

  /**
   * Which material the ash plain is showing, -1 (scoured back to burnt
   * hardpan) to +1 (fresh pale drift).
   *
   * The mechanism is sorting, and it is the same wind that built the dunes:
   * material is dropped on the ramps and the crests and stripped from the pans
   * between them, so the pale fall lies exactly where the dune is and the black
   * burnt ground is everywhere it has been taken from. Reading the dune profile
   * for it rather than an independent noise is the whole point — the albedo and
   * the surface normal then agree about where the crest is, which is what turns
   * a lit mound into a legible one.
   *
   * @returns {number} -1..1
   */
  ashSurface(wx, wz) {
    const n = this.nDune;
    const d = this._duneProfile(wx, wz);
    // Whole stretches of an erg are buried and whole stretches are stripped;
    // without that the material would read as stripes painted across the
    // ground. 34 m is the sheet and 14 m the ragged edge where it runs out.
    const sheet = n.noise(wx / 34 + 5.3, wz / 34 - 9.1);
    const edge = n.noise(wx / 14 - 2.7, wz / 14 + 6.4);
    return clamp((d - 0.42) * 1.8 + sheet * 0.95 + edge * 0.30, -1, 1);
  }

  /**
   * The mire's mound field, before it becomes either height or colour.
   *
   * Shared so that the tussock the player walks over and the pale dead cane
   * growing on it are built from one number. Two fields would put the colour
   * across the form instead of on it, which is exactly what makes procedural
   * ground look printed rather than grown.
   */
  marshField(wx, wz) {
    return this.nGround.fbm(wx / 26 + 13.7, wz / 26 - 4.2, 2, 2.3, 0.55);
  }

  /**
   * Tussock ground, for the mire. A marsh surface is raised mounds of root mat
   * with water lying in the creases between them, not a wet plane.
   *
   * @param {number} w blended weight of the marsh region, 0..1
   * @param {number} h landform height so far, used to fade above the water table
   */
  marshTussock(wx, wz, w, h) {
    if (w <= 0.01) return 0;
    // This fade used to run the other way — full relief on the dry ground and
    // almost none at the waterline — so that the shore of every pool stayed one
    // clean edge. That is backwards for a marsh. The waterline is where a mire
    // has its entire character: a hundred mound tops standing as islands with
    // black water lying between them, and suppressing the relief there left the
    // wet third of the region as a smooth wet plane, which is the one thing a
    // swamp never is. The fade belongs at the top instead, where the ground
    // climbs clear of the water table and becomes ordinary damp meadow.
    const wet = 1 - smoothstep(saturate((h - WATER_LEVEL - 4.0) / 7.0));
    if (wet <= 0.01) return 0;
    const t = this.marshField(wx, wz);
    // |t| makes mounds; the creases where it crosses zero dish out into
    // channels. They are cut deeper than the mounds stand tall because the
    // water lying in them carries the peat away, and it is that asymmetry —
    // not the mounds — that puts standing water in the mire rather than merely
    // wet ground.
    const crown = Math.abs(t) - 0.34;
    const mound = crown > 0 ? crown : crown * 1.7;
    // A second scale at the grid's floor: a mire is islands inside islands, and
    // one wavelength of mound on its own reads as corrugation. 12 m is a group
    // of tussocks rather than one — a single tussock is a metre across, which
    // the height field cannot hold and the clutter scatter carries instead.
    const fine = Math.abs(this.nGround.noise(wx / 12 - 31.4, wz / 12 + 17.8)) - 0.32;
    return (mound * TUSSOCK_AMP + fine * TUSSOCK_FINE) * w * wet;
  }

  /**
   * The mire's surface material, -1 (black saturated peat, in the creases and
   * the shallows) to +1 (pale dead sedge and cane on the tussock crowns).
   *
   * A marsh reads as a marsh because it is a mosaic and for no other reason —
   * a wet plane of one green is a lawn. Built from marshField so the pale
   * material sits on the mounds the light is already catching and the black
   * sits in the creases the water lies in.
   *
   * @param {number} h baked height, which decides what can dry out at all
   */
  marshSurface(wx, wz, h) {
    const t = Math.abs(this.marshField(wx, wz));
    const fine = Math.abs(this.nGround.noise(wx / 12 - 31.4, wz / 12 + 17.8));
    // How far the ground stands clear of the water table. Nothing sitting in it
    // carries dead cane whatever the mound underneath is doing, and the mound
    // tops that do stand clear are exactly where a marsh keeps its pale
    // material — so this is the term that ties the colour to the water rather
    // than merely to a noise field.
    const drain = saturate((h - WATER_LEVEL - 0.4) / 3.0);
    return clamp(t * 3.4 + fine * 1.1 + drain * 1.0 - 1.25, -1, 1);
  }

  /**
   * Raw elevation before rivers and roads. Kept separate so the carving passes
   * can operate on the baked grid rather than re-evaluating noise.
   */
  rawElevation(wx, wz) {
    const s = 0.00075;
    const x = wx * s, z = wz * s;

    // Region influence: weighted blend of the authored elevation profiles.
    let wSum = 0, elevBase = 0, elevAmp = 0, rugged = 0, wAsh = 0, wMire = 0;
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
      // Two regions have a signature surface of their own. Biome is not
      // assigned until pass 3, so the region weight is what we have here.
      if (r.biome === BIOME.ASH) wAsh += w;
      if (r.biome === BIOME.MARSH) wMire += w;
    }
    if (wSum > 0.0001) {
      elevBase /= wSum; elevAmp /= wSum; rugged /= wSum;
      wAsh /= wSum; wMire /= wSum;
    } else { elevBase = 8; elevAmp = 14; rugged = 0.2; }

    // Base rolling terrain, domain-warped for organic valley shapes.
    const warped = this.nBase.warped(x * 2.2, z * 2.2, 0.55, 5);
    let h = elevBase + warped * elevAmp;

    // Ridged mountains layered on top, scaled by how rugged the region is.
    const ridge = this.nRidge.ridged(x * 3.1, z * 3.1, 5, 2.1, 0.5);
    h += Math.pow(ridge, 1.7) * elevAmp * 2.3 * rugged;

    // Mid-frequency detail keeps slopes from reading as smooth blobs.
    h += this.nDetail.fbm(x * 9.0, z * 9.0, 3) * (3.0 + rugged * 8.0);

    // --- ground scale -------------------------------------------------------
    // Only the two genuinely vertical regions are held back: the crags and the
    // peak already carry more shape per metre than a player can take in, and
    // hummocking a cliff face is meaningless. Everything else — including the
    // highlands, whose benches and saddles are as planar as any meadow — gets
    // the full treatment.
    const open = 1 - saturate((rugged - 0.55) / 0.45);

    h += this.benchStep(wx, wz, open);
    h += this.groundRelief(wx, wz, open);
    h += this.ashDunes(wx, wz, wAsh);
    h += this.marshTussock(wx, wz, wMire, h);

    // Dry watercourses. Cut everywhere runoff would run, including the
    // highlands where it cuts deepest — only the plains need the hummocks, but
    // every slope sheds water.
    let cut = 0;
    const gf = this.gullyField(wx, wz, GULLY_SCALE, 0);
    if (gf < GULLY_BANK) cut += this.channelProfile(gf / GULLY_BANK) * GULLY_DEPTH;
    const rf = this.gullyField(wx, wz, RILL_SCALE, 27.3);
    if (rf < RILL_BANK) cut += this.channelProfile(rf / RILL_BANK) * RILL_DEPTH;
    // Above the water table only: a channel driven through the shoreline would
    // open a canal into the sea.
    if (cut > 0) h -= cut * (0.35 + 0.65 * open) * saturate((h - 4) / 6);

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
        const boggy = b === BIOME.MARSH;

        if (h < WATER_LEVEL - 0.5) b = BIOME.OCEAN;
        // The generic shoreline rule puts sand around every pool, which in a
        // peat swamp is a tropical beach in the wrong hemisphere. The mire keeps
        // its own margin instead: black saturated mud at the water and bleached
        // litter a pace above it, which the mosaic below sorts out by itself.
        else if (h < WATER_LEVEL + 1.6) b = boggy ? BIOME.MARSH : BIOME.BEACH;
        else if (h > 118 + this.nDetail.noise(wx * 0.004, wz * 0.004) * 16) b = BIOME.SNOW;
        else if (slope > 0.62 && h > 24) b = BIOME.CRAG;
        else if (boggy && h > 12) b = BIOME.MEADOW;

        // Which of its three surfaces the ground is showing. Both plains are
        // material mosaics rather than one colour — see BIOME_INFO — and the
        // classification runs after the overrides above so that it covers
        // exactly the ash and marsh footprint, ecotone included.
        let mat = 0;
        if (b === BIOME.ASH) {
          mat = this.ashSurface(wx, wz);
          b = mat > ASH_PALE ? BIOME.DRIFT : mat < ASH_BURNT ? BIOME.CINDER : BIOME.ASH;
        } else if (b === BIOME.MARSH) {
          mat = this.marshSurface(wx, wz, h);
          b = mat > MIRE_PALE ? BIOME.SEDGE : mat < MIRE_BLACK ? BIOME.PEAT : BIOME.MARSH;
        }
        this.biome[i] = b;

        // Wetness carried at the scale the surface is actually built at. The
        // mire's creases hold water and its crowns shed it; in the waste fresh
        // drift is bone dry and the scoured pans keep what damp is left. This
        // matters beyond the scatter because the terrain tint is modulated by
        // moisture, so without it the only variation either place has below the
        // 800 m swell of the noise field is none.
        this.moisture[i] = saturate(m - mat * 0.22);
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
    // Flattest dry candidate seen regardless of the limit. Open country now
    // undulates at the scale of a few paces, so a tight maxSlope can come up
    // empty in ground that is still perfectly buildable — and dropping back to
    // the raw target point can drop a village on a river bank or a bench face.
    let fallback = null, fallbackSlope = Infinity;
    for (let i = 0; i < 220; i++) {
      const a = rng() * Math.PI * 2;
      const r = Math.sqrt(rng()) * searchRadius;
      const x = cx + Math.cos(a) * r;
      const z = cz + Math.sin(a) * r;
      if (Math.abs(x) > WORLD_HALF - 60 || Math.abs(z) > WORLD_HALF - 60) continue;
      const h = this.heightAt(x, z);
      if (h < WATER_LEVEL + 2.5) continue;
      const s = this.slopeAt(x, z);
      if (s < fallbackSlope) { fallbackSlope = s; fallback = { x, z, y: h }; }
      if (s > maxSlope) continue;
      const score = -s * 8 - r / searchRadius;
      if (score > bestScore) { bestScore = score; best = { x, z, y: h }; }
    }
    if (!best) best = fallback;
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
    // Ruins and mini-boss sites join the network too: a road that only links
    // checkpoints tells the player nothing about where the content is.
    const hubs = this.pois.filter((p) => p.kind === 'grace' || p.kind === 'village'
      || p.kind === 'mini' || p.kind === 'ruin');
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
    while (placed < 62 && attempts < 6000) {
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
    for (let i = 0; i < 17; i++) {
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
