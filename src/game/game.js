// ============================================================================
//  game.js — the simulation.
//
//  Owns the world, the actors, the spawn lifecycle, interactions, quests and
//  the frame loop. The UI layer reads state from here and calls back in; the
//  renderer is handed a plain description of what to draw each frame and knows
//  nothing about gameplay.
// ============================================================================

import { GL } from '../gfx/gl.js';
import { Renderer, QUALITY } from '../gfx/renderer.js';
import { Terrain } from '../gfx/terrain.js';
import { BatchSet } from '../gfx/instancing.js';
import { ParticleSystem, BLEND } from '../gfx/particles.js';
import {
  GpuMesh, MeshData, buildBox, buildBevelBox, buildCylinder, buildCone, buildRock,
  buildGrassTuft, buildBroadleafTree, buildConiferTree, buildDeadTree, buildBush,
  buildTreeFar, buildConiferFar, buildCharacterParts, buildClutterMeshes, buildFeatureMeshes,
  buildPillar, buildCampfire, buildGrace, buildChest, buildHut, buildWatchtower, buildArch,
} from '../gfx/mesh.js';
import { MATERIAL } from '../gfx/textures.js';

import { World, WORLD_HALF, CHUNK_SIZE, CHUNKS, WATER_LEVEL, BIOME, BIOME_INFO, REGIONS } from '../world/worldgen.js';
import { Scatter, GrassField, PROP, CLUTTER_STRIDE, FEATURE_STRIDE } from '../world/foliage.js';
import { buildStructure, SPROP, pickEnemy } from '../world/structures.js';

import { Actor, STATE, FACTION, defaultPalette } from './actor.js';
import { MAT, bindWorldSource, continuityFrame } from './rig.js';
import { Player, CLASSES, levelCost } from './player.js';
import { Enemy, ARCHETYPES, spawnLootFor } from './enemies.js';
import { Boss, BOSSES, MINI_BOSSES, createMiniBoss } from './bosses.js';
import { AggroDirector, AI_STATE } from './ai.js';
import { resolveMeleeHits, Projectile, AreaEffect } from './combat.js';
import { QuestLog, QUESTS, QUEST_BY_ID, NPCS, DIALOGUE } from './quests.js';
import { getItem, getSpell, ITEM_BY_ID, UPGRADE_COST, UPGRADE_MATERIAL, UPGRADE_MUL } from './items.js';

import { Input, ACTION, haptic, setHapticsEnabled } from '../core/input.js';
import { AudioEngine } from '../core/audio.js';
import { makeRng, hash2 } from '../core/rng.js';
import { clamp, lerp, saturate, damp, v3distXZ, angleDelta, TAU, sphereInFrustum } from '../core/math.js';
import { saveGame, loadGameData, saveSettings, loadSettings } from '../core/save.js';

/**
 * Per-region colour grade, blended by region influence. Tint multiplies the
 * final image, saturation drains or lifts it, and vignette tightens the frame
 * where a place should feel oppressive.
 */
// `contrast` is the print curve for the region: open meadows and snowfields
// are inherently low-contrast subjects and need pulling apart, while the mire
// and the woods already carry their own tonal separation.
const REGION_GRADE = {
  // The meadow's lift came down from 1.06 because the frame was measuring 0.482
  // mean chroma against a 0.48 ceiling — a hair over, and the fix belongs here
  // rather than in the ground. The grass and the terrain tint are both carrying
  // real per-blade and per-patch colour variation now, and draining that to buy
  // half a percent would undo the thing the number is supposed to protect. The
  // grade is the one place where taking it out costs nothing but the excess:
  // 1.035 blends with the neighbouring regions to about 2.3% less chroma, which
  // is under the threshold where an eye can tell two frames apart.
  meadow: { tint: [1.00, 1.00, 1.00], sat: 1.035, vignette: 0.38, contrast: 1.38 },
  // The wood moves the other way, and for a reason that has nothing to do with
  // the wood floor. Fixing the sky's horizon band means the dusk keyframe's
  // authored horizon — a deep orange, 0.86/0.40/0.23 — actually reaches the
  // screen instead of being mixed halfway to zenith blue, and the Whispering
  // Wood is the one scene sampled at dusk. Modelled over the part of the sky
  // the frame statistics can see, its chroma goes from 0.32 to 0.54, and sky is
  // better than a third of that window. Against a 0.48 ceiling and a measured
  // 0.326 today that is enough headroom to be worth insuring, and 0.98 is a two
  // percent drain nobody will see. If the audit comes back with room, this is
  // the first thing to put back.
  wood: { tint: [0.95, 1.03, 0.95], sat: 0.98, vignette: 0.46, contrast: 1.14 },
  mire: { tint: [0.92, 1.02, 0.90], sat: 0.86, vignette: 0.52, contrast: 1.12 },
  ridge: { tint: [0.97, 0.99, 1.05], sat: 0.98, vignette: 0.42, contrast: 1.20 },
  crag: { tint: [0.95, 0.98, 1.07], sat: 0.86, vignette: 0.44, contrast: 1.42 },
  waste: { tint: [1.07, 0.93, 0.84], sat: 0.68, vignette: 0.56, contrast: 1.18 },
  peak: { tint: [0.93, 0.98, 1.10], sat: 0.76, vignette: 0.48, contrast: 1.34 },
};

const SPAWN_ACTIVATE = 130;
const SPAWN_DEACTIVATE = 170;
const STRUCTURE_RANGE = 480;

/**
 * Batch name and draw range per CLUTTER id, in the order foliage.js scatters
 * them. The ranges are the distance at which each kind stops being worth a
 * triangle: a 40 cm stone is under a pixel past ninety metres, while a drift
 * or a standing snag still reads as a shape at two hundred. Every item is
 * additionally capped by its own size, so the same batch can hold a knee-high
 * stump drawn to 120 m and a five-metre snag drawn to 150.
 */
const CLUTTER_BATCH = ['clutRock', 'clutWood', 'clutScrub', 'clutBone', 'clutDrift', 'clutSlab', 'clutStump'];
const CLUTTER_RANGE = [105, 100, 95, 110, 200, 160, 170];
/** The furthest any item can be drawn: the largest range times the largest
 *  per-biome multiplier foliage.js packs alongside it. */
const CLUTTER_RANGE_MAX = 240;
/** Only scrub bends in the wind; stone and bone conspicuously should not. */
const CLUTTER_SWAY = [0, 0, 1.1, 0, 0, 0, 0.12];

/**
 * Land features, in the order foliage.js scatters them:
 * [OUTCROP, THICKET, REEDBED, DUNE, MIDDEN, CAIRN, WALL].
 *
 * These are the objects that furnish the middle distance, so their ranges are
 * prop ranges rather than clutter ranges — a four-metre outcrop is still a
 * shape at three hundred metres, and on open ground it is the *only* shape.
 *
 * Only the three stone kinds cast shadows. That is not a saving so much as a
 * choice about where the shadow budget goes: a boulder, a wall and a cairn each
 * throw a long hard shadow across flat ground, which is the single strongest
 * cue that the ground is a surface in a place rather than a lit plane. A
 * thicket's own shading already reads, and a dune's crest is lit by geometry.
 */
const FEATURE_BATCH = ['featOutcrop', 'featThicket', 'featReed', 'featDune',
  'featMidden', 'featCairn', 'featWall'];
const FEATURE_RANGE = [300, 260, 200, 320, 230, 260, 285];
const FEATURE_SHADOW = [true, false, false, false, false, true, true];
/** Bramble and reed move; stone, bone and ash do not. */
const FEATURE_SWAY = [0, 0.7, 1.2, 0, 0, 0, 0];
/**
 * New clutter chunks built per frame. One chunk is a few thousand candidates
 * and several milliseconds; building the whole ring at once on a warp would be
 * a visible stall, while one a frame fills a 300 m view inside a second.
 */
const CLUTTER_BUILD_BUDGET = 1;

export class Game {
  constructor(canvas, ui) {
    this.canvas = canvas;
    this.ui = ui;
    this.glw = new GL(canvas);
    this.time = 0;
    this.playtime = 0;
    this.frame = 0;
    this.paused = false;
    this.started = false;

    this.settings = Object.assign({
      quality: this._guessQuality(),
      sensitivity: 1.0,
      invertY: false,
      master: 0.8, music: 0.5, sfx: 0.9,
      showDamage: true,
      cameraAssist: true,
      autoLock: true,
      haptics: true,
      leftHanded: false,
      uiScale: 1,
      reducedMotion: window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches || false,
      showObjectives: true,
      trackedQuest: 'main_1',
      tutorialVersion: 0,
      language: 'ja',
    }, loadSettings() || {});

    this.renderer = new Renderer(this.glw, this.settings.quality);
    this.particles = new ParticleSystem(this.glw);
    this.input = new Input(document.getElementById('touch-layer'));
    this.input.sensitivity = this.settings.sensitivity;
    this.input.invertY = this.settings.invertY;
    this.input.leftHanded = this.settings.leftHanded;
    this.audio = new AudioEngine();
    this.audio.setVolumes({ master: this.settings.master, music: this.settings.music, sfx: this.settings.sfx });
    this.applyPreferences();

    this.actors = [];
    this.enemies = [];
    this.npcs = [];
    this.projectiles = [];
    this.areaEffects = [];
    this.timers = [];
    this.lights = [];
    this.structureColliders = [];
    this.damageNumbers = [];

    this.director = new AggroDirector();
    this.quests = new QuestLog();

    this.openedChests = new Set();
    this.usedShrines = new Set();
    this.bossesKilled = new Set();
    this.minisKilled = new Set();
    this.clearedCamps = new Set();
    this.deaths = 0;
    this.killCount = 0;

    this.spawnPoints = [];
    this.spawnByKey = new Map();
    this.wildCells = new Set();
    this.structureCache = new Map();
    this.interacts = [];

    this.bossActive = null;
    this.currentRegionName = '';
    this.notifications = [];
    this.dialogue = null;
    this.className = '';
    this.friendlyFire = false;
    this._accum = 0;
    this._fpsSamples = [];
    this.dynamicScale = 1;
    /** Whether the resolution is allowed to hunt. See _updatePerf. */
    this.autoResolution = true;
    this._perfTimer = 0;
    this.activeSaveSlot = 0;
    this._autosaveClock = 0;
    this._lastAutosave = 0;
  }

  _guessQuality() {
    const mem = navigator.deviceMemory || 4;
    const cores = navigator.hardwareConcurrency || 4;
    const small = Math.min(window.innerWidth, window.innerHeight) < 420;
    if (mem <= 3 || cores <= 4 || small) return 'low';
    if (mem <= 6 || cores <= 6) return 'medium';
    return 'high';
  }

  applyPreferences() {
    if (this.input) {
      this.input.sensitivity = this.settings.sensitivity;
      this.input.invertY = this.settings.invertY;
      this.input.leftHanded = !!this.settings.leftHanded;
    }
    setHapticsEnabled(this.settings.haptics);
    document.documentElement.style.setProperty('--ui-scale', String(clamp(this.settings.uiScale || 1, 0.82, 1.2)));
    document.body.classList.toggle('left-handed', !!this.settings.leftHanded);
    document.body.classList.toggle('reduce-motion', !!this.settings.reducedMotion);
  }

  // -------------------------------------------------------------------------
  //  Boot
  // -------------------------------------------------------------------------

  /**
   * Nearest living body to a point, for rigs deciding what to look at.
   * Whoever is asking is standing at (x, z), so anything inside half a metre is
   * the looker itself and must not be returned — a character staring at its own
   * navel is the failure mode this guards against.
   */
  _gazeNear(x, z, maxDist) {
    const lock = this.player && this.player.lockTarget;
    if (lock && !lock.dead) {
      const px = this.player.x - x, pz = this.player.z - z;
      if (px * px + pz * pz < 0.36) return lock;
    }
    let best = null;
    let bestD = maxDist * maxDist;
    const consider = (a) => {
      if (!a || a.dead || a.visible === false) return;
      const dx = a.x - x, dz = a.z - z;
      const d2 = dx * dx + dz * dz;
      if (d2 < 0.36 || d2 >= bestD) return;
      bestD = d2; best = a;
    };
    consider(this.player);
    for (const list of [this.enemies, this.npcs]) {
      if (!list) continue;
      for (let i = 0; i < list.length; i++) consider(list[i]);
    }
    return best;
  }

  /** Generator so the loading screen can report real progress. */
  *boot(seedStr = 'aldrath') {
    yield { p: 0.02, label: '大地を編んでいる' };
    this.world = new World(seedStr);
    const gen = this.world.generate();
    let step = gen.next();
    while (!step.done) {
      yield { p: 0.02 + step.value * 0.62, label: '大地を編んでいる' };
      step = gen.next();
    }

    // Rigs need the height field under their feet and somebody to look at, and
    // a rig is built deep inside an actor that is handed neither. rig.js falls
    // back to reading the running game off a global; binding it here is the
    // same thing done properly, and it is what lets a test harness or a model
    // viewer stand a character in a different world.
    bindWorldSource({
      heightAt: (x, z) => this.world.heightAt(x, z),
      gazeNear: (x, z, maxDist) => this._gazeNear(x, z, maxDist),
    });

    yield { p: 0.66, label: '木々を植えている' };
    this.scatter = new Scatter(this.world);
    this.grass = new GrassField(this.world, this.scatter);
    this.terrain = new Terrain(this.glw, this.world);

    yield { p: 0.72, label: '形をつくっている' };
    this._buildMeshes();

    yield { p: 0.84, label: '住人を配置している' };
    this._buildSpawnPoints();
    this._buildNpcs();

    yield { p: 0.92, label: '地形を刻んでいる' };
    this.terrain.primeAround(this.world.spawnPoint.x, this.world.spawnPoint.z, 300);

    yield { p: 0.99, label: '準備完了' };
    this.resize();
    yield { p: 1.0, label: '完了' };
  }

  _buildMeshes() {
    const glw = this.glw;
    const rng = makeRng(this.world.seed ^ 0xbeef);
    this.batches = new BatchSet(glw);

    // Materials are per-batch by default. The box batch is the exception: it
    // draws every character, every limb and every piece of equipment, so its
    // material is set per push by whoever is drawing.
    const M = MATERIAL;

    // Character/prop primitive — the workhorse batch.
    this.batches.add('box', new GpuMesh(glw, buildBevelBox(0.10)), 4096);

    // Character silhouette. Every bone used to be the box above, which made a
    // bandit and a boss the same object at two scales. One batch per primitive
    // keeps a twelve-enemy fight at six draw calls while giving each bone a
    // shape: tapered limbs, a shouldered torso, a jawed skull, domed pauldrons
    // and flat plates for tassets, feet, capes and crests.
    const CHAR_CAPACITY = { limb: 1536, torso: 512, skull: 384, pauldron: 384, plate: 768 };
    const charParts = buildCharacterParts();
    for (const name in charParts) {
      // Material is set per push by rig.js, exactly as for the box batch.
      this.batches.add(name, new GpuMesh(glw, charParts[name]), CHAR_CAPACITY[name] || 512);
    }

    // Vegetation. The second material is what the mesh's blend attribute
    // selects: trunk bark on one side, canopy foliage on the other.
    this.batches.add('treeBroad', new GpuMesh(glw, buildBroadleafTree(rng)), 512)
      .material(M.BARK, M.FOLIAGE);
    this.batches.add('treeConifer', new GpuMesh(glw, buildConiferTree(rng)), 512)
      .material(M.BARK, M.FOLIAGE);
    this.batches.add('treeDead', new GpuMesh(glw, buildDeadTree(rng)), 256)
      .material(M.BARK, M.BARK);
    this.batches.add('treeFar', new GpuMesh(glw, buildTreeFar(rng)), 1024, { castsShadow: false })
      .material(M.BARK, M.FOLIAGE, 1, 0.4);
    this.batches.add('coniferFar', new GpuMesh(glw, buildConiferFar()), 1024, { castsShadow: false })
      .material(M.BARK, M.FOLIAGE, 1, 0.4);
    this.batches.add('bush', new GpuMesh(glw, buildBush(rng)), 768, { castsShadow: false })
      .material(M.FOLIAGE);
    this.batches.add('rockS', new GpuMesh(glw, buildRock(1, 0.30, rng)), 768).material(M.STONE);
    this.batches.add('rockL', new GpuMesh(glw, buildRock(1, 0.26, rng)), 384)
      .material(M.STONE, M.STONE, 1, 0.6);
    this.batches.add('reed', new GpuMesh(glw, buildCone(4)), 512, { castsShadow: false })
      .material(M.FOLIAGE);

    // Ground clutter. None of it casts a shadow: a stump's shadow is one pixel
    // at the distance most of them are seen, and the shadow pass draws a whole
    // batch regardless of range, so including them would double the cost of the
    // densest thing in the world for almost nothing. Their own facet shading
    // and the SSAO pass are what make them read.
    const clutter = buildClutterMeshes(rng);
    const CLUTTER_MAT = [
      [M.STONE, M.STONE, 1, 1.0],     // rock: crusted top in the secondary slot
      [M.BARK, M.WOOD, 1, 1.6],       // deadwood: fibre along the branch
      [M.FOLIAGE, M.FOLIAGE, 1, 3.0], // scrub
      [M.BONE, M.BONE, 0.9, 2.2],     // bone
      [M.DEFAULT, M.DEFAULT, 1.1, 0.5], // drift: broad soft blotching
      [M.STONE, M.STONE, 1, 0.55],    // slab: big cracks, not gravel
      [M.BARK, M.WOOD, 1, 1.2],       // stump / snag
    ];
    const CLUTTER_CAPACITY = [2048, 1024, 3072, 768, 1536, 1024, 1536];
    this.clutterBatches = CLUTTER_BATCH.map((name, i) => this.batches
      .add(name, new GpuMesh(glw, clutter[i]), CLUTTER_CAPACITY[i], { castsShadow: false })
      .material(...CLUTTER_MAT[i]));

    // Land features — the two-to-eight metre tier. Same idea as clutter one
    // size up, and the size is the point: these are what a plain has instead of
    // a mountain's banks and benches, and they are read from a hundred metres.
    const features = buildFeatureMeshes(rng);
    const FEATURE_MAT = [
      [M.STONE, M.STONE, 1, 0.5],       // outcrop: broad rock grain, not gravel
      [M.FOLIAGE, M.WOOD, 1.1, 2.0],    // thicket: leaf mass over dead cane
      [M.FOLIAGE, M.WOOD, 1, 2.6],      // reed bed and its rotting posts
      [M.DEFAULT, M.DEFAULT, 1.15, 0.4], // dune: soft, broadly blotched
      [M.BONE, M.BONE, 0.9, 1.4],       // midden
      [M.STONE, M.STONE, 1, 0.9],       // cairn: course-sized stone
      [M.STONE, M.STONE, 1, 1.1],       // field wall
    ];
    const FEATURE_CAPACITY = [768, 512, 256, 512, 256, 256, 512];
    this.featureBatches = FEATURE_BATCH.map((name, i) => this.batches
      .add(name, new GpuMesh(glw, features[i]), FEATURE_CAPACITY[i],
        { castsShadow: FEATURE_SHADOW[i] })
      .material(...FEATURE_MAT[i]));

    // Structures.
    this.batches.add('hut', new GpuMesh(glw, buildHut(rng)), 96).material(M.WOOD, M.THATCH);
    this.batches.add('pillar', new GpuMesh(glw, buildPillar(rng)), 256).material(M.STONE);
    this.batches.add('arch', new GpuMesh(glw, buildArch()), 48).material(M.STONE);
    this.batches.add('campfire', new GpuMesh(glw, buildCampfire()), 64).material(M.WOOD);
    this.batches.add('grace', new GpuMesh(glw, buildGrace()), 48).material(M.STONE, M.GEM);
    this.batches.add('chest', new GpuMesh(glw, buildChest()), 96).material(M.WOOD, M.METAL);
    this.batches.add('tower', new GpuMesh(glw, buildWatchtower()), 32).material(M.STONE, M.WOOD);
    this.batches.add('cylinder', new GpuMesh(glw, buildCylinder(8)), 512).material(M.STONE);
    this.batches.add('cone', new GpuMesh(glw, buildCone(6)), 256).material(M.STONE);

    // Grass gets its own program, so it lives outside the batch set.
    this.grassBatch = this.batches.add('grass', new GpuMesh(glw, buildGrassTuft()), 8192, { castsShadow: false });
    this.batches.map.delete('grass');
    this.batches.order.pop();
  }

  // -------------------------------------------------------------------------
  //  Spawns
  // -------------------------------------------------------------------------

  _buildSpawnPoints() {
    const world = this.world;
    const rng = makeRng(world.seed ^ 0x1234);

    for (const poi of world.pois) {
      const st = this._structureFor(poi);
      const level = world.levelAt(poi.x, poi.z);
      for (const s of st.spawns) {
        if (s.role === 'boss') {
          this._addSpawn({
            key: `boss_${poi.id}`, x: s.x, z: s.z, kind: 'boss',
            boss: s.boss, level, poiId: poi.id, arenaRadius: poi.radius,
          });
        } else if (s.role === 'mini') {
          this._addSpawn({
            key: `mini_${poi.id}`, x: s.x, z: s.z, kind: 'mini',
            mini: s.mini, level, poiId: poi.id,
          });
        } else {
          const arch = pickEnemy(poi.region, s.role, rng);
          this._addSpawn({
            key: `${poi.id}_${this.spawnPoints.length}`, x: s.x, z: s.z,
            kind: 'enemy', archetype: arch, level, poiId: poi.id,
            elite: rng() < 0.06,
          });
        }
      }
    }
  }

  _addSpawn(s) {
    s.actor = null;
    s.dead = false;
    s.homeX = s.x;
    s.homeZ = s.z;
    this.spawnPoints.push(s);
    this.spawnByKey.set(s.key, s);
    return s;
  }

  /** Wilderness encounters, generated deterministically per 72m cell. */
  _ensureWildSpawns(px, pz) {
    const CELL = 72;
    const range = 3;
    const cx0 = Math.floor(px / CELL) - range;
    const cz0 = Math.floor(pz / CELL) - range;
    const world = this.world;
    for (let cz = cz0; cz <= cz0 + range * 2; cz++) {
      for (let cx = cx0; cx <= cx0 + range * 2; cx++) {
        const key = `w_${cx}_${cz}`;
        if (this.wildCells.has(key)) continue;
        this.wildCells.add(key);

        const r0 = hash2(cx, cz, world.seed ^ 0x77);
        const x = (cx + hash2(cx + 3, cz + 7, world.seed)) * CELL;
        const z = (cz + hash2(cx + 11, cz + 5, world.seed)) * CELL;
        if (Math.abs(x) > WORLD_HALF - 40 || Math.abs(z) > WORLD_HALF - 40) continue;
        const h = world.heightAt(x, z);
        if (h < WATER_LEVEL + 1.5) continue;
        if (world.slopeAt(x, z) > 0.35) continue;
        // Keep the wilds quieter near settlements and graces.
        let nearHub = false;
        for (const p of world.pois) {
          if (p.kind !== 'village' && p.kind !== 'grace') continue;
          if (Math.hypot(p.x - x, p.z - z) < 60) { nearHub = true; break; }
        }
        if (nearHub) continue;
        if (r0 > 0.62) continue;

        const region = world.regionAt(x, z).region;
        const level = world.levelAt(x, z);
        const rng = makeRng((hash2(cx, cz, world.seed ^ 0x999) * 4294967296) >>> 0);
        const arch = pickEnemy(region.id, 'wild', rng);
        const packSize = ARCHETYPES[arch].rig === 'quadruped' ? 2 + Math.floor(rng() * 3) : 1 + Math.floor(rng() * 2);
        for (let i = 0; i < packSize; i++) {
          const a = rng() * TAU, r = rng() * 7;
          this._addSpawn({
            key: `${key}_${i}`, x: x + Math.cos(a) * r, z: z + Math.sin(a) * r,
            kind: 'enemy', archetype: arch, level, wild: true,
            elite: rng() < 0.04,
          });
        }
      }
    }
  }

  _updateSpawns(dt) {
    const p = this.player;
    this._ensureWildSpawns(p.x, p.z);

    for (const s of this.spawnPoints) {
      const d = Math.hypot(s.x - p.x, s.z - p.z);
      if (!s.actor && !s.dead && d < SPAWN_ACTIVATE) {
        this._activateSpawn(s);
      } else if (s.actor && d > SPAWN_DEACTIVATE) {
        if (s.actor.dead) { s.actor = null; continue; }
        if (s.actor.isBoss && s.actor.introDone) continue;
        this._removeActor(s.actor);
        s.actor = null;
      }
    }
  }

  _activateSpawn(s) {
    let actor = null;
    if (s.kind === 'boss') {
      if (this.bossesKilled.has(s.boss)) { s.dead = true; return; }
      actor = new Boss(this, s.boss, {
        x: s.x, z: s.z, level: s.level, arenaRadius: s.arenaRadius || 30,
      });
    } else if (s.kind === 'mini') {
      if (this.minisKilled.has(s.key)) { s.dead = true; return; }
      actor = createMiniBoss(this, s.mini, s.x, s.z, s.level);
      if (!actor) return;
    } else {
      actor = new Enemy(this, s.archetype, {
        x: s.x, z: s.z, level: s.level, elite: s.elite,
      });
    }
    actor.spawnRef = s;
    actor.y = this.world.heightAt(actor.x, actor.z);
    actor.yaw = Math.random() * TAU;
    if (actor.brain) actor.brain.setHome(s.homeX, s.homeZ);
    s.actor = actor;
    this.actors.push(actor);
    this.enemies.push(actor);
  }

  _removeActor(a) {
    let i = this.actors.indexOf(a);
    if (i >= 0) this.actors.splice(i, 1);
    i = this.enemies.indexOf(a);
    if (i >= 0) this.enemies.splice(i, 1);
    this.director.releaseAll(a);
  }

  /** Rest at a grace: heal, refill, and bring the world back. */
  respawnWorld() {
    for (const s of this.spawnPoints) {
      if (s.kind === 'boss' && this.bossesKilled.has(s.boss)) continue;
      if (s.kind === 'mini' && this.minisKilled.has(s.key)) continue;
      if (s.actor) { this._removeActor(s.actor); s.actor = null; }
      s.dead = false;
    }
    this.bossActive = null;
    this.projectiles.length = 0;
    this.areaEffects.length = 0;
  }

  // -------------------------------------------------------------------------
  //  NPCs
  // -------------------------------------------------------------------------

  _buildNpcs() {
    const world = this.world;
    for (const key in NPCS) {
      const def = NPCS[key];
      // Anchor each NPC to a matching POI in their home region.
      let anchor = world.pois.find((p) => p.region === def.region
        && (def.role === 'merchant' ? p.kind === 'merchant'
          : def.role === 'smith' ? p.kind === 'smith'
            : p.kind === 'village'));
      if (!anchor) {
        anchor = world.pois.find((p) => p.region === def.region && p.kind === 'grace')
          || world.pois.find((p) => p.kind === 'grace');
      }
      if (!anchor) continue;
      const jitter = def.role === 'quest' ? 5 : 0;
      const x = anchor.x + (Math.random() - 0.5) * jitter;
      const z = anchor.z + (Math.random() - 0.5) * jitter + (def.role === 'quest' ? 4 : 0);
      const npc = new Actor(this, {
        x, z, faction: FACTION.NEUTRAL, name: def.name,
        maxHp: 9999, radius: 0.4, height: 1.75,
        palette: this._paletteFrom(def.palette),
      });
      npc.npcId = def.id;
      npc.npcDef = def;
      npc.noPush = true;
      npc.noCritical = true;
      npc.invulnerable = true;
      npc.turnRate = 6;
      npc.yaw = Math.random() * TAU;
      this.actors.push(npc);
      this.npcs.push(npc);
      this.interacts.push({ x, z, r: 2.6, kind: 'npc', npc });
    }
  }

  _paletteFrom(over) {
    const p = defaultPalette();
    for (const k in over || {}) if (MAT[k] !== undefined) p[MAT[k]] = over[k];
    return p;
  }

  // -------------------------------------------------------------------------
  //  Structures
  // -------------------------------------------------------------------------

  _structureFor(poi) {
    let st = this.structureCache.get(poi.id);
    if (!st) {
      st = buildStructure(this.world, poi);
      this.structureCache.set(poi.id, st);
    }
    return st;
  }

  _gatherStructures(px, pz) {
    this.structureColliders.length = 0;
    this.lights.length = 0;
    this.interacts.length = 0;
    for (const npc of this.npcs) {
      this.interacts.push({ x: npc.x, z: npc.z, r: 2.6, kind: 'npc', npc });
    }

    for (const poi of this.world.pois) {
      const d = Math.hypot(poi.x - px, poi.z - pz);
      if (d > STRUCTURE_RANGE) continue;
      const st = this._structureFor(poi);

      if (d < 90) {
        for (const c of st.colliders) this.structureColliders.push(c);
        for (const it of st.interacts) this.interacts.push(it);
      }
      if (d < 180) {
        for (const l of st.lights) {
          const flicker = l.kind === 'fire'
            ? 0.82 + Math.sin(this.time * 11 + l.x) * 0.10 + Math.sin(this.time * 27 + l.z) * 0.06
            : 1;
          const nightBoost = l.kind === 'window' ? this.renderer.night : 1;
          this.lights.push({
            x: l.x, y: l.y + poiHeight(this.world, l), z: l.z,
            color: l.color, radius: l.radius, intensity: flicker * nightBoost,
          });
        }
      }
      this._renderStructure(st, d);
    }
  }

  _renderStructure(st, dist) {
    const B = this.batches;
    // Dressing is small: past this it is sub-pixel, and a POI four hundred
    // metres away must not pay for its firewood.
    const dressing = dist < 150;
    for (const p of st.props) {
      const c = p.color;
      switch (p.type) {
        case SPROP.DEBRIS: case SPROP.DEADWOOD: case SPROP.BONES: case SPROP.SCRUB: {
          if (!dressing) break;
          const s = p.scale;
          const batch = p.type === SPROP.DEBRIS ? 'clutRock'
            : p.type === SPROP.DEADWOOD ? 'clutWood'
              : p.type === SPROP.BONES ? 'clutBone' : 'clutScrub';
          // Long things lie along their own axis; the rest stay roughly square.
          const long = p.type === SPROP.DEADWOOD;
          B.get(batch).push(p.x, p.y, p.z,
            (long ? 1.5 : 0.9) * s, (long ? 0.16 : 0.6) * s, (long ? 0.16 : 0.9) * s, p.yaw,
            c[0], c[1], c[2], 0, p.type === SPROP.SCRUB ? 1.1 : 0, p.x * 0.7 + p.z, 1, 1,
            c[0] * 1.3 + 0.05, c[1] * 1.3 + 0.05, c[2] * 1.25 + 0.05);
          break;
        }
        case SPROP.HUT:
          B.get('hut').push(p.x, p.y, p.z, p.scale, p.scale, p.scale, p.yaw,
            c[0], c[1], c[2], 0, 0, 0, 1, 1, 0.30, 0.22, 0.17);
          break;
        case SPROP.PILLAR: B.get('pillar').push(p.x, p.y, p.z, p.scale, p.scale, p.scale, p.yaw, c[0], c[1], c[2]); break;
        case SPROP.ARCH: B.get('arch').push(p.x, p.y, p.z, p.scale, p.scale, p.scale, p.yaw, c[0], c[1], c[2]); break;
        case SPROP.CAMPFIRE: {
          B.get('campfire').push(p.x, p.y, p.z, p.scale, p.scale, p.scale, p.yaw,
            c[0], c[1], c[2], 0, 0, 0, 1, 1, 0.24, 0.16, 0.11);
          // Glowing coals.
          B.get('rockS').push(p.x, p.y + 0.02, p.z, 0.5 * p.scale, 0.22 * p.scale, 0.5 * p.scale, p.yaw,
            1.0, 0.42, 0.12, 1.2, 0, 0, 1, 1);
          break;
        }
        case SPROP.GRACE: {
          B.get('grace').push(p.x, p.y, p.z, p.scale, p.scale, p.scale, p.yaw,
            c[0], c[1], c[2], 0, 0, 0, 1, 1, 0.74, 0.70, 0.62);
          B.get('rockS').push(p.x, p.y + 1.86 * p.scale, p.z, 0.24, 0.24, 0.24, 0,
            1.0, 0.72, 0.30, 2.0, 0, 0, 1, 1);
          break;
        }
        case SPROP.CHEST:
          B.get('chest').push(p.x, p.y, p.z, p.scale, p.scale, p.scale, p.yaw,
            c[0], c[1], c[2], 0, 0, 0, 1, 1, 0.60, 0.55, 0.34);
          break;
        case SPROP.TOWER: B.get('tower').push(p.x, p.y, p.z, p.scale, p.scale, p.scale, p.yaw, c[0], c[1], c[2]); break;
        case SPROP.RUBBLE: B.get('rockS').push(p.x, p.y, p.z, p.scale * 1.4, p.scale, p.scale * 1.4, p.yaw, c[0], c[1], c[2]); break;
        case SPROP.CRATE: B.get('box').push(p.x, p.y, p.z, 0.8 * p.scale, 0.75 * p.scale, 0.8 * p.scale, p.yaw, c[0], c[1], c[2]); break;
        case SPROP.BARREL: B.get('cylinder').push(p.x, p.y, p.z, 0.72 * p.scale, 1.0 * p.scale, 0.72 * p.scale, p.yaw, c[0], c[1], c[2]); break;
        case SPROP.TENT: B.get('cone').push(p.x, p.y, p.z, 3.4 * p.scale, 2.2 * p.scale, 3.4 * p.scale, p.yaw, c[0], c[1], c[2]); break;
        case SPROP.FENCE: {
          B.get('box').push(p.x, p.y, p.z, 1.9, 0.14, 0.10, p.yaw, c[0], c[1], c[2]);
          B.get('box').push(p.x, p.y + 0.55, p.z, 1.9, 0.14, 0.10, p.yaw, c[0], c[1], c[2]);
          B.get('cylinder').push(p.x, p.y, p.z, 0.16, 1.15, 0.16, p.yaw, c[0] * 0.9, c[1] * 0.9, c[2] * 0.9);
          break;
        }
        case SPROP.BANNER: {
          B.get('cylinder').push(p.x, p.y, p.z, 0.11, 3.2, 0.11, p.yaw, 0.28, 0.22, 0.16);
          B.get('box').push(p.x, p.y + 1.5, p.z, 0.06, 1.5, 0.85, p.yaw, c[0], c[1], c[2]);
          break;
        }
        case SPROP.STATUE: {
          B.get('box').push(p.x, p.y, p.z, 1.1, 0.4, 1.1, p.yaw, c[0] * 0.9, c[1] * 0.9, c[2] * 0.9);
          B.get('cylinder').push(p.x, p.y + 0.4, p.z, 0.7, 1.7, 0.7, p.yaw, c[0], c[1], c[2]);
          B.get('rockS').push(p.x, p.y + 2.05, p.z, 0.55, 0.55, 0.55, p.yaw, c[0], c[1], c[2]);
          break;
        }
        case SPROP.TORCH: {
          B.get('cylinder').push(p.x, p.y, p.z, 0.14 * p.scale, 2.0 * p.scale, 0.14 * p.scale, p.yaw, 0.26, 0.20, 0.15);
          B.get('rockS').push(p.x, p.y + 2.0 * p.scale, p.z, 0.32 * p.scale, 0.3 * p.scale, 0.32 * p.scale, p.yaw,
            1.0, 0.5, 0.16, 1.6, 0, 0, 1, 1);
          break;
        }
        case SPROP.ALTAR: {
          B.get('box').push(p.x, p.y, p.z, 2.0 * p.scale, 0.35 * p.scale, 2.0 * p.scale, p.yaw, c[0], c[1], c[2]);
          B.get('box').push(p.x, p.y + 0.35 * p.scale, p.z, 1.5 * p.scale, 0.5 * p.scale, 1.5 * p.scale, p.yaw, c[0] * 1.05, c[1] * 1.05, c[2] * 1.05);
          break;
        }
        default: break;
      }
    }
  }

  // -------------------------------------------------------------------------
  //  Start / load
  // -------------------------------------------------------------------------

  startNewGame(classId, appearance, name) {
    const cls = CLASSES.find((c) => c.id === classId) || CLASSES[0];
    this.className = cls.name;
    const sp = this.world.spawnPoint;
    const p = new Player(this, { x: sp.x, z: sp.z, name: name || '刻印者' });
    p.stats = { ...cls.stats };
    p.playerLevel = cls.level;
    p.appearance = appearance || p.appearance;

    for (let i = 0; i < cls.weapons.length; i++) {
      p.addItem(cls.weapons[i]);
      p.equip.right[i] = getItem(cls.weapons[i]);
    }
    for (let i = 0; i < cls.offhand.length; i++) {
      p.addItem(cls.offhand[i]);
      p.equip.left[i] = getItem(cls.offhand[i]);
    }
    for (const a of cls.armor) {
      p.addItem(a);
      const it = getItem(a);
      if (it) p.equip[it.slot] = it;
    }
    for (const [id, n] of cls.items) p.addItem(id, n);
    for (const s of cls.spells) p.learnSpell(s);
    p.addItem('flask_hp', 0);

    p.recomputeDerived(true);
    this.player = p;
    this.actors.push(p);
    this.quests.start('main_1');
    this.renderer.hour = 8.5;
    this.started = true;
    this._afterPlayerReady();
    this.autosave('旅の開始', true);
    this.ui?.startOnboarding();
  }

  loadFromData(data) {
    const d = data.player;
    const p = new Player(this, { x: d.x, z: d.z, name: d.name });
    p.stats = { ...d.stats };
    p.playerLevel = d.level;
    p.souls = d.souls || 0;
    p.totalSouls = d.totalSouls || 0;
    p.appearance = d.appearance || p.appearance;
    p.y = d.y;
    p.yaw = d.yaw || 0;
    p.inventory = new Map(d.inventory || []);
    p.upgrades = new Map(d.upgrades || []);
    p.spells = d.spells || [];
    p.spellIndex = d.spellIndex || 0;
    p.flaskHp = d.flaskHp || p.flaskHp;
    p.flaskFp = d.flaskFp || p.flaskFp;
    p.deathDrop = d.deathDrop || null;
    p.lastGraceId = d.lastGraceId || null;
    p.rightIndex = d.rightIndex || 0;
    p.leftIndex = d.leftIndex || 0;
    p.twoHand = !!d.twoHand;

    const e = d.equip || {};
    p.equip.right = (e.right || []).map((id) => getItem(id));
    p.equip.left = (e.left || []).map((id) => getItem(id));
    while (p.equip.right.length < 3) p.equip.right.push(null);
    while (p.equip.left.length < 3) p.equip.left.push(null);
    p.equip.head = getItem(e.head);
    p.equip.body = getItem(e.body);
    p.equip.arms = getItem(e.arms);
    p.equip.legs = getItem(e.legs);
    p.equip.talismans = (e.talismans || [null, null, null, null]).map((id) => getItem(id));
    while (p.equip.talismans.length < 4) p.equip.talismans.push(null);

    p.recomputeDerived(true);
    p.hp = clamp(d.hp || p.maxHp, 1, p.maxHp);
    p.fp = clamp(d.fp || p.maxFp, 0, p.maxFp);
    p._refreshQuickItems();

    this.className = d.className || '';
    this.player = p;
    this.actors.push(p);

    const w = data.world || {};
    this.renderer.hour = w.hour !== undefined ? w.hour : 9;
    this.openedChests = new Set(w.openedChests || []);
    this.usedShrines = new Set(w.usedShrines || []);
    this.bossesKilled = new Set(w.bossesKilled || []);
    this.minisKilled = new Set(w.minisKilled || []);
    this.clearedCamps = new Set(w.clearedCamps || []);
    this.deaths = w.deaths || 0;
    const disc = new Set(w.discovered || []);
    for (const poi of this.world.pois) if (disc.has(poi.id)) poi.discovered = true;

    this.quests.deserialize(data.quests);
    this.playtime = data.meta?.playtime || 0;
    this.started = true;
    this._afterPlayerReady();
    this.autosave('再開', true);
  }

  _afterPlayerReady() {
    const p = this.player;
    p.camera.yaw = p.yaw;
    this.terrain.primeAround(p.x, p.z, 300);
    this.grass.dirty = true;
    this.audio.init();
    this.audio.setMusicMode('explore');
    this.applyQuality(this.settings.quality);
  }

  applyQuality(name) {
    this.settings.quality = name;
    this.renderer.setQuality(name);
    const q = this.renderer.quality;
    this.grass.configure(q.grassRadius, q.grassCell, q.grassBlades);
    this.particles.cap = Math.min(this.particles.cap, q.particleCap);
    this.terrain.chunkBudgetPerFrame = name === 'low' ? 1 : 2;
    saveSettings(this.settings);
    this.resize();
  }

  resize() {
    const dpr = Math.min(window.devicePixelRatio || 1, this.settings.quality === 'high' ? 2 : 1.5);
    const w = Math.round(window.innerWidth * dpr);
    const h = Math.round(window.innerHeight * dpr);
    if (this.canvas.width !== w || this.canvas.height !== h) {
      this.canvas.width = w;
      this.canvas.height = h;
    }
    this.renderer.dynamicScale = this.dynamicScale;
    this.renderer.resize(w, h);
  }

  // -------------------------------------------------------------------------
  //  Frame
  // -------------------------------------------------------------------------

  schedule(delay, fn) {
    this.timers.push({ t: delay, fn });
  }

  notify(text, kind = 'info') {
    this.notifications.push({ text, kind, t: 3.2 });
    this.ui?.pushNotification(text, kind);
  }

  /** Route quest events through one place so progression is never silent. */
  questEvent(event) {
    const progressed = this.quests.notify(event);
    for (const entry of progressed) {
      const q = entry.quest;
      const result = entry.result || {};
      if (result.failed) {
        this.notify(`失敗：${q.name}`, 'bad');
      } else if (result.ready) {
        this.notify(`報告可能：${q.name}`, 'good');
      } else if (result.completed) {
        this.notify(`使命完了：${q.name}`, 'good');
        if (q.main && q.next) this.settings.trackedQuest = q.next;
      } else if (result.step) {
        this.notify(`使命更新：${result.step.text}`, 'discovery');
      }
    }
    if (progressed.length) {
      saveSettings(this.settings);
      this.ui?.pulseObjective();
      this.autosave('使命更新');
    }
    return progressed;
  }

  shake(amp, dur) {
    this.player?.camera.shake(amp, dur);
  }

  get isNight() { return this.renderer.night > 0.5; }

  update(dt) {
    this.time += dt;
    if (this.started && !this.paused) this.playtime += dt;
    this.frame++;
    continuityFrame();

    // Timers run even while paused so scheduled fades still resolve.
    for (let i = this.timers.length - 1; i >= 0; i--) {
      const t = this.timers[i];
      t.t -= dt;
      if (t.t <= 0) { this.timers.splice(i, 1); t.fn(); }
    }

    if (this.paused || !this.started) {
      this.renderer.updateAtmosphere(dt * 0.15);
      this.input.endFrame(dt);
      return;
    }

    this._autosaveClock += dt;
    if (this._autosaveClock >= 60) this.autosave('定期保存');

    const p = this.player;

    // --- input & player ----------------------------------------------------
    if (!this.dialogue) {
      p.handleInput(this.input, dt, p.camera.yaw);
    } else {
      p.intentSpeed = 0; p.intentX = 0; p.intentZ = 0;
    }

    // --- actors ------------------------------------------------------------
    for (const a of this.actors) a.update(dt);
    Actor.separate(this.actors, dt);

    // --- melee hits --------------------------------------------------------
    for (const a of this.actors) {
      if (a.hitActive) resolveMeleeHits(this, a, this.actors);
    }

    // --- projectiles & areas ----------------------------------------------
    for (let i = this.projectiles.length - 1; i >= 0; i--) {
      const pr = this.projectiles[i];
      pr.update(dt, this.actors);
      if (pr.dead) this.projectiles.splice(i, 1);
    }
    for (let i = this.areaEffects.length - 1; i >= 0; i--) {
      const ae = this.areaEffects[i];
      ae.update(dt, this.actors);
      if (ae.dead) this.areaEffects.splice(i, 1);
    }

    // --- cleanup dead ------------------------------------------------------
    for (let i = this.actors.length - 1; i >= 0; i--) {
      const a = this.actors[i];
      if (a === p) continue;
      if (a.dead && a.deathTimer > a.removeAfter) {
        if (a.spawnRef) { a.spawnRef.dead = true; a.spawnRef.actor = null; }
        this._removeActor(a);
      } else if (a.dead && a.deathTimer > a.removeAfter - 2) {
        a.fadeAlpha = clamp((a.removeAfter - a.deathTimer) / 2, 0, 1);
        a.visible = a.fadeAlpha > 0.02;
      }
    }

    this._updateSpawns(dt);
    this.particles.update(dt, this.world);
    this._updateInteraction(dt);
    this._updateBossState(dt);
    this._updateAmbientEffects(dt);
    this._updateMusic(dt);
    this._updateDamageNumbers(dt);

    // --- camera & atmosphere ----------------------------------------------
    p.camera.update(dt, this.input, this.world, p.lockTarget);
    this.renderer.updateAtmosphere(dt);

    this._updateGrade(dt);

    const region = this.world.regionAt(p.x, p.z).region;
    if (region.name !== this.currentRegionName) {
      const first = this.currentRegionName !== '';
      this.currentRegionName = region.name;
      if (first) {
        this.ui?.showRegionTitle(region.name, region.blurb);
        this.audio.playDiscovery();
      }
    }

    this.input.endFrame(dt);
    this._updatePerformance(dt);
  }

  _updatePerformance(dt) {
    // Adaptive resolution: if we are consistently missing frame time, drop
    // internal resolution before dropping features the player would notice.
    this._fpsSamples.push(dt);
    if (this._fpsSamples.length > 60) this._fpsSamples.shift();
    this._perfTimer -= dt;
    if (this._perfTimer > 0 || this._fpsSamples.length < 60) return;
    this._perfTimer = 2.0;
    let sum = 0;
    for (const s of this._fpsSamples) sum += s;
    const avg = sum / this._fpsSamples.length;
    const fps = 1 / avg;
    const prev = this.dynamicScale;
    // Resolution can be pinned. Every change recreates the render targets,
    // including the depth texture the presentation statistics read, so a
    // measurement taken while this is still hunting is a measurement taken
    // across a target recreation. Pinning it makes the audit deterministic, and
    // it is the setting a player would want on a device where the hunting is
    // itself the thing they can see.
    if (!this.autoResolution) { this.fps = fps; return; }
    if (fps < 42) this.dynamicScale = Math.max(0.6, this.dynamicScale - 0.08);
    else if (fps > 57) this.dynamicScale = Math.min(1.0, this.dynamicScale + 0.05);
    if (Math.abs(prev - this.dynamicScale) > 0.005) {
      this.renderer.dynamicScale = this.dynamicScale;
      this.renderer.resize(this.canvas.width, this.canvas.height);
    }
    this.fps = fps;
  }

  _updateMusic(dt) {
    const p = this.player;
    let mode = 'explore';
    if (p.dead) mode = 'silent';
    else if (this.bossActive && this.bossActive.introDone && !this.bossActive.dead) mode = 'boss';
    else if (p.state === STATE.REST) mode = 'grace';
    else {
      let threat = 0;
      for (const e of this.enemies) {
        if (e.dead) continue;
        const d = v3distXZ(e, p);
        if (d < 26 && e.brain && e.brain.target) threat = Math.max(threat, d < 12 ? 2 : 1);
      }
      const nearVillage = this.world.pois.some((q) => q.kind === 'village' && Math.hypot(q.x - p.x, q.z - p.z) < 40);
      mode = threat >= 2 ? 'combat' : threat >= 1 ? 'tension' : nearVillage ? 'village' : 'explore';
    }
    this.audio.setMusicMode(mode);
    this.audio.updateMusic(dt);
    this.audio.updateAmbient(dt, {
      windStrength: this.renderer.weather.windX,
      rain: this.renderer.weather.rainIntensity,
      night: this.renderer.night,
    });
  }

  /**
   * Per-region colour grade. The lighting model is shared across the whole
   * island, so this is what actually makes the Cinderwaste feel like ash and
   * the peak feel like cold — a grade blended by region influence rather than
   * switched at a boundary.
   */
  _updateGrade(dt) {
    const p = this.player;
    let tr = 0, tg = 0, tb = 0, sat = 0, vig = 0, con = 0, wSum = 0;
    for (const r of REGIONS) {
      const d = Math.hypot(p.x - r.cx, p.z - r.cz);
      const t = saturate(1 - d / (r.radius * 1.5));
      const w = t * t + 0.0001;
      const grade = REGION_GRADE[r.id] || REGION_GRADE.meadow;
      tr += grade.tint[0] * w; tg += grade.tint[1] * w; tb += grade.tint[2] * w;
      sat += grade.sat * w;
      vig += grade.vignette * w;
      con += grade.contrast * w;
      wSum += w;
    }
    tr /= wSum; tg /= wSum; tb /= wSum; sat /= wSum; vig /= wSum; con /= wSum;

    const k = 1 - Math.exp(-1.2 * dt);
    const rend = this.renderer;
    rend.tint[0] += (tr - rend.tint[0]) * k;
    rend.tint[1] += (tg - rend.tint[1]) * k;
    rend.tint[2] += (tb - rend.tint[2]) * k;
    rend.saturation += (sat - rend.saturation) * k;
    rend.vignette += (vig - rend.vignette) * k;
    rend.contrast += (con - rend.contrast) * k;
  }

  _updateAmbientEffects(dt) {
    const p = this.player;
    const w = this.renderer.weather;

    // Rain / snow particles around the camera.
    if (w.rainIntensity > 0.05) {
      const count = Math.round(w.rainIntensity * 26 * dt * 60);
      const snow = this.world.biomeAt(p.x, p.z) === BIOME.SNOW;
      for (let i = 0; i < count; i++) {
        const a = Math.random() * TAU;
        const r = Math.sqrt(Math.random()) * 16;
        const x = p.x + Math.cos(a) * r;
        const z = p.z + Math.sin(a) * r;
        this.particles.spawn({
          x, y: p.y + 12 + Math.random() * 4, z,
          vx: w.windX * 3, vy: snow ? -2.5 : -22, vz: w.windZ * 3,
          life: snow ? 3.0 : 0.85,
          size: snow ? 0.09 : 0.045, sizeEnd: snow ? 0.09 : 0.045,
          r: snow ? 0.95 : 0.62, g: snow ? 0.97 : 0.72, b: snow ? 1.0 : 0.86,
          alpha: snow ? 0.85 : 0.34, drag: snow ? 1.2 : 0.05, gravity: 0,
          soft: snow ? 0.9 : 0.2, blend: BLEND.ALPHA,
        });
      }
    }

    // Embers and motes near fires.
    for (const l of this.lights) {
      if (l.kind === 'shrine') continue;
      if (Math.random() < dt * 12 * (l.radius / 12)) {
        this.particles.ember(l.x, l.y, l.z);
      }
    }

    // Drifting ash in the wastes; pollen in the meadow.
    const biome = this.world.biomeAt(p.x, p.z);
    // The waste is three surfaces now — burnt pan, settled fall, drift crest —
    // and ash falls on all of them.
    const inAsh = biome === BIOME.ASH || biome === BIOME.CINDER || biome === BIOME.DRIFT;
    if (inAsh && Math.random() < dt * 22) {
      const a = Math.random() * TAU, r = Math.random() * 14;
      this.particles.spawn({
        x: p.x + Math.cos(a) * r, y: p.y + 1 + Math.random() * 6, z: p.z + Math.sin(a) * r,
        vx: (Math.random() - 0.5) * 0.6, vy: -0.35, vz: (Math.random() - 0.5) * 0.6,
        life: 5, size: 0.07, sizeEnd: 0.05,
        r: 0.62, g: 0.58, b: 0.55, alpha: 0.35,
        drag: 0.5, gravity: 0, soft: 0.85, blend: BLEND.ALPHA,
      });
    } else if ((biome === BIOME.MEADOW || biome === BIOME.FOREST) && !this.isNight && Math.random() < dt * 8) {
      const a = Math.random() * TAU, r = Math.random() * 10;
      this.particles.spawn({
        x: p.x + Math.cos(a) * r, y: p.y + 0.6 + Math.random() * 2.4, z: p.z + Math.sin(a) * r,
        vx: (Math.random() - 0.5) * 0.4, vy: 0.12, vz: (Math.random() - 0.5) * 0.4,
        life: 6, size: 0.05, sizeEnd: 0.03,
        r: 1.0, g: 0.95, b: 0.6, alpha: 0.5,
        drag: 0.4, gravity: 0, soft: 0.9, blend: BLEND.ADDITIVE,
      });
    } else if (this.isNight && Math.random() < dt * 5 && !inAsh) {
      const a = Math.random() * TAU, r = 2 + Math.random() * 12;
      this.particles.spawn({
        x: p.x + Math.cos(a) * r, y: p.y + 0.5 + Math.random() * 2, z: p.z + Math.sin(a) * r,
        vx: (Math.random() - 0.5) * 0.3, vy: 0.2, vz: (Math.random() - 0.5) * 0.3,
        life: 4.5, size: 0.055, sizeEnd: 0.02,
        r: 0.6, g: 0.95, b: 0.7, alpha: 0.9,
        drag: 0.6, gravity: 0, soft: 0.3, blend: BLEND.ADDITIVE,
      });
    }
  }

  _updateDamageNumbers(dt) {
    for (let i = this.damageNumbers.length - 1; i >= 0; i--) {
      const d = this.damageNumbers[i];
      d.t -= dt;
      d.y += dt * 1.5;
      if (d.t <= 0) this.damageNumbers.splice(i, 1);
    }
  }

  // -------------------------------------------------------------------------
  //  Interaction
  // -------------------------------------------------------------------------

  _updateInteraction(dt) {
    const p = this.player;
    let best = null, bestD = Infinity;
    for (const it of this.interacts) {
      const d = Math.hypot(it.x - p.x, it.z - p.z);
      if (d > it.r) continue;
      if (it.kind === 'chest' && this.openedChests.has(it.poi.id)) continue;
      if (it.kind === 'shrine' && this.usedShrines.has(it.poi.id)) continue;
      if (it.kind === 'fog' && this.bossesKilled.has(it.poi.boss)) continue;
      if (d < bestD) { bestD = d; best = it; }
    }
    p.interactTarget = best;
    this.ui?.setInteractPrompt(best ? interactLabel(best) : null);

    // Discovering a place is its own small reward.
    for (const poi of this.world.pois) {
      if (poi.discovered) continue;
      const d = Math.hypot(poi.x - p.x, poi.z - p.z);
      const radius = poi.kind === 'village' ? 70 : poi.kind === 'grace' ? 26 : poi.kind === 'boss' ? 55 : 30;
      if (d < radius) {
        poi.discovered = true;
        if (poi.kind === 'grace' || poi.kind === 'village' || poi.kind === 'boss') {
          this.notify(`${poi.name} を発見`, 'discovery');
          this.audio.playDiscovery();
        }
        this.questEvent({ type: 'reach', poi: poi.id });
      }
    }

    if (best && this.input.pressed(ACTION.INTERACT) && !this.dialogue) {
      this.input.consume(ACTION.INTERACT);
      this.doInteract(best);
    }
  }

  doInteract(it) {
    const p = this.player;
    switch (it.kind) {
      case 'grace': this.restAtGrace(it.poi); break;
      case 'chest': this.openChest(it.poi); break;
      case 'shrine': this.useShrine(it.poi); break;
      case 'npc': this.talkTo(it.npc); break;
      case 'fog': this.enterBossArena(it.poi); break;
      default: break;
    }
  }

  restAtGrace(poi) {
    const p = this.player;
    p.lastGraceId = poi.id;
    poi.discovered = true;
    p.setState(STATE.REST, { duration: 999 });
    p.hp = p.maxHp;
    p.fp = p.maxFp;
    p.stamina = p.maxStamina;
    p.refillFlasks();
    for (const k in p.status) { p.status[k].active = 0; p.status[k].build = 0; }
    this.respawnWorld();
    this.audio.playGrace();
    this.ui?.openGrace(poi);
    this.notify(`${poi.name} で休息した`);
    this.autosave('篝火');
  }

  onLeaveGrace() {
    this.ui?.closeGrace();
  }

  openChest(poi) {
    if (this.openedChests.has(poi.id)) return;
    this.openedChests.add(poi.id);
    poi.opened = true;
    const rng = makeRng((this.world.seed ^ hashStr(poi.id)) >>> 0);
    const level = this.world.levelAt(poi.x, poi.z);
    const loot = rollChestLoot(rng, poi.tier || 0, level);
    const p = this.player;
    const lines = [];
    for (const [id, n] of loot.items) {
      p.addItem(id, n);
      const it = getItem(id);
      if (it) lines.push(`${it.name}${n > 1 ? ` ×${n}` : ''}`);
    }
    if (loot.souls > 0) {
      p.gainSouls(loot.souls);
      lines.push(`残り火 ${loot.souls}`);
    }
    this.audio.playPickup();
    haptic(20);
    this.ui?.showLoot(lines);
    this.questEvent({ type: 'inventory', has: (id) => p.countItem(id) > 0 });
  }

  useShrine(poi) {
    if (this.usedShrines.has(poi.id)) return;
    this.usedShrines.add(poi.id);
    const p = this.player;
    // Shrines grant a permanent, small boost — exploration that matters.
    const boost = ['vig', 'end', 'str', 'dex', 'int', 'fth', 'mnd'];
    const rng = makeRng((this.world.seed ^ hashStr(poi.id)) >>> 0);
    const stat = boost[Math.floor(rng() * boost.length)];
    p.stats[stat] += 1;
    p.recomputeDerived();
    this.audio.playLevelUp();
    this.notify(`古き祠の加護：${statLabel(stat)} +1`, 'good');
    this.questEvent({ type: 'shrine' });
    this.particles.burst(poi.x, poi.y + 1.2, poi.z, 30, {
      r: 0.6, g: 0.8, b: 1.0, size: 0.2, life: 1.2, spread: 1.6, up: 2.6,
      blend: BLEND.ADDITIVE, alpha: 0.9, drag: 1.2, gravity: 0.6,
    });
  }

  talkTo(npc) {
    this.dialogue = { npc, node: 'start', tree: DIALOGUE[npc.npcDef.dialogue] };
    npc.faceTowards(this.player.x, this.player.z, 1, 20);
    this.player.faceTowards(npc.x, npc.z, 1, 20);
    this.questEvent({ type: 'talk', npc: npc.npcId });
    this.ui?.openDialogue(this.dialogue);
    this.audio.playUI('confirm');
  }

  closeDialogue() {
    this.dialogue = null;
    this.ui?.closeDialogue();
  }

  enterBossArena(poi) {
    const boss = this.enemies.find((e) => e.isBoss && e.bossId === poi.boss);
    if (!boss) { this.notify('ここには誰もいない'); return; }
    this.bossActive = boss;
    boss.begin();
    this.audio.playBossHorn();
    this.ui?.showBossBar(boss);
    this.notify(`${BOSSES[poi.boss].title}`, 'boss');
  }

  warpToGrace(poi) {
    const p = this.player;
    p.teleport(poi.x + 3, undefined, poi.z + 3);
    p.lastGraceId = poi.id;
    this.terrain.primeAround(p.x, p.z, 220);
    this.grass.dirty = true;
    this.respawnWorld();
    this.ui?.closeAll();
    this.notify(`${poi.name} へ移動した`);
  }

  warpToLastGrace() {
    const poi = this.world.pois.find((q) => q.id === this.player.lastGraceId)
      || this.world.graces.find((g) => g.isStart);
    if (poi) this.warpToGrace(poi);
  }

  // -------------------------------------------------------------------------
  //  Boss lifecycle
  // -------------------------------------------------------------------------

  _updateBossState(dt) {
    if (!this.bossActive) return;
    const b = this.bossActive;
    if (b.dead) {
      if (b.deathTimer > 2.2) {
        this.ui?.hideBossBar();
        this.bossActive = null;
      }
      return;
    }
    // Leaving the arena ends the fight and resets the boss.
    const d = v3distXZ(this.player, b);
    if (d > b.arenaRadius + 26) {
      b.introDone = false;
      b.brain.state = AI_STATE.SLEEP;
      b.brain.target = null;
      b.hp = b.maxHp;
      b.phaseIndex = 0;
      b.brain.cfg.attacks = b.baseAttacks.slice();
      b.baseDamage = b.arch.damage * (1 + (b.level - 1) * 0.062);
      b.phaseTint = [1, 1, 1];
      b.weaponGlow = 0;
      b.x = b.arenaX; b.z = b.arenaZ;
      this.ui?.hideBossBar();
      this.bossActive = null;
    }
  }

  // -------------------------------------------------------------------------
  //  Event callbacks (wired into actors/combat)
  // -------------------------------------------------------------------------

  onHitResolved(attacker, target, info, result, point) {
    if (!result.hit) {
      if (result.parried) return;
      return;
    }
    const isPlayerAttack = attacker === this.player;
    const metal = result.blocked || (target.equip && target.equip.body);

    if (result.blocked) this.audio.playBlock();
    else if (metal) this.audio.playHitMetal(clamp(result.damage / 120, 0.4, 1.4));
    else this.audio.playHitFlesh(clamp(result.damage / 120, 0.4, 1.4));

    const dx = target.x - attacker.x, dz = target.z - attacker.z;
    if (result.blocked) {
      this.particles.sparkHit(point.x, point.y, point.z, dx, dz);
      target.blockImpact = 1;
    } else {
      this.particles.bloodSpray(point.x, point.y, point.z, dx, dz, clamp(result.damage / 90, 0.5, 2));
      this.particles.sparkHit(point.x, point.y, point.z, dx, dz);
    }

    if (isPlayerAttack) {
      this.player.hitStreak++;
      this.player.hitStreakTimer = 3;
      haptic(result.blocked ? 8 : 14);
      this.shake(result.blocked ? 0.08 : Math.min(0.28, 0.06 + result.damage / 700), 0.16);
      if (this.settings.showDamage) {
        this.damageNumbers.push({
          x: point.x, y: point.y, z: point.z, value: result.damage,
          t: 1.0, crit: !!info.crit, blocked: result.blocked,
        });
      }
    }
    if (target === this.player) {
      this.renderer.damageFlash = Math.min(1, this.renderer.damageFlash + clamp(result.damage / this.player.maxHp * 2.2, 0.15, 1));
      haptic(result.blocked ? 12 : 30);
      this.shake(0.3, 0.22);
    }
  }

  onSwing(actor, id) {
    const w = actor.weapon;
    this.audio.playSwing(w ? clamp(w.weight / 5, 0.6, 2.2) : 1);
  }

  onEnemySwing(actor, id) {
    this.audio.playSwing(clamp((actor.scale || 1) * 1.2, 0.7, 2.4));
  }

  onRoll(actor) {
    this.audio.playRoll();
    this.particles.dustStep(actor.x, actor.y, actor.z, 1.4);
    haptic(6);
  }

  onParry(defender, attacker) {
    this.audio.playParry();
    this.shake(0.35, 0.25);
    haptic(40);
    this.particles.burst(attacker.x, attacker.y + 1.2, attacker.z, 18, {
      r: 1.0, g: 0.92, b: 0.6, size: 0.16, life: 0.5, spread: 4, up: 2,
      blend: BLEND.ADDITIVE, alpha: 1, drag: 3, gravity: -3,
    });
    if (defender === this.player) this.notify('弾いた！', 'good');
  }

  onGuardBreak(actor, source) {
    this.audio.playGuardBreak();
    if (actor === this.player) this.notify('ガードを崩された', 'bad');
    this.shake(0.4, 0.3);
  }

  onBlock(defender, attacker, info) {
    if (defender === this.player) haptic(10);
  }

  onCriticalStart(attacker, victim, kind) {
    if (attacker === this.player) {
      this.shake(0.2, 0.2);
      this.notify(kind === 'backstab' ? '背後からの一撃' : '致命の一撃', 'good');
    }
  }

  onCritical(attacker, victim, kind, res) {
    this.audio.playCritical();
    this.shake(0.6, 0.4);
    haptic(60);
    this.particles.bloodSpray(victim.x, victim.y + 1.1, victim.z,
      victim.x - attacker.x, victim.z - attacker.z, 3);
    if (attacker === this.player && this.player.critHeal) {
      this.player.heal(this.player.critHeal);
    }
  }

  onStatusProc(actor, type) {
    if (actor === this.player) {
      this.notify(type === 'poison' ? '毒に侵された' : type === 'frost' ? '凍傷' : '出血', 'bad');
      haptic(50);
    }
  }

  onPlayerHurt(res, info) {
    if (res.blocked) return;
    this.player.lockSwitchCd = 0.2;
  }

  onFootstep(actor, speed) {
    if (v3distXZ(actor, this.player) > 22) return;
    const b = this.world.biomeAt(actor.x, actor.z);
    const road = this.world.roadAt(actor.x, actor.z);
    const surface = road > 0.4 ? 'dirt'
      : b === BIOME.SNOW ? 'snow'
        : b === BIOME.BEACH || b === BIOME.DRIFT ? 'sand'
          : b === BIOME.CRAG || b === BIOME.CINDER ? 'stone'
            : b === BIOME.MARSH || b === BIOME.PEAT ? 'water' : 'grass';
    this.audio.playFootstep(surface, clamp(speed / 6, 0.4, 1.4));
    if (speed > 4) this.particles.dustStep(actor.x, actor.y, actor.z, clamp(speed / 8, 0.4, 1.2));
  }

  onDeath(actor, killer) {
    if (actor === this.player) {
      this.deaths++;
      this.audio.playDeath();
      this.renderer.deathFade = 0;
      this.schedule(0.1, () => { this.ui?.showDeath(); });
      let f = 0;
      const fade = () => {
        f += 0.06;
        this.renderer.deathFade = Math.min(1, f);
        if (f < 1) this.schedule(0.05, fade);
      };
      fade();
      return;
    }

    if (killer === this.player || (killer && killer.faction === FACTION.PLAYER)) {
      const gained = this.player.gainSouls(actor.soulsValue || 20);
      this.killCount++;
      this.ui?.pushSouls(gained);
      const rng = makeRng((this.world.seed ^ (actor.id * 2654435761)) >>> 0);
      if (actor.dropTable) {
        for (const [id, n] of spawnLootFor(actor, rng)) {
          if (getItem(id)) {
            this.player.addItem(id, n);
            this.notify(`${getItem(id).name} を手に入れた`, 'loot');
          } else if (getSpell(id)) {
            this.player.learnSpell(id);
            this.notify(`${getSpell(id).name} を覚えた`, 'loot');
          }
        }
      }
      this.questEvent({ type: 'kill', archetype: actor.archetypeId });
      if (actor.isMiniBoss && actor.spawnRef) {
        this.minisKilled.add(actor.spawnRef.key);
        const kind = actor.spawnRef.mini;
        this.questEvent({ type: 'kill', archetype: kind });
      }
    }

    this.particles.burst(actor.x, actor.y + 1.0, actor.z, 16, {
      r: 0.35, g: 0.06, b: 0.06, size: 0.2, life: 0.8, spread: 2.4, up: 1.6,
      alpha: 0.8, drag: 1.6, gravity: -8, collide: true,
    });
  }

  onBossBegin(boss) {
    this.ui?.showBossIntro(boss);
  }

  onBossPhase(boss, phase, index) {
    if (phase.name) this.ui?.showBossPhase(phase.name);
    this.audio.playBossHorn();
    haptic(80);
  }

  onBossDefeated(boss) {
    const def = BOSSES[boss.bossId];
    this.bossesKilled.add(boss.bossId);
    if (boss.spawnRef) boss.spawnRef.dead = true;
    const reward = def.reward || {};
    const gained = this.player.gainSouls(reward.souls || boss.soulsValue);
    if (reward.item) this.player.addItem(reward.item, 1);
    for (const [id, n] of reward.extra || []) this.player.addItem(id, n);
    this.questEvent({ type: 'boss', boss: boss.bossId });
    this.questEvent({ type: 'inventory', has: (id) => this.player.countItem(id) > 0 });
    this.audio.playVictory();
    this.ui?.showBossVictory(def, gained, reward);
    this.schedule(0.4, () => { this.ui?.hideBossBar(); });
    this.bossActive = null;
    this.autosave('王の撃破', true);
    if (reward.ending) this.schedule(4.0, () => this.ui?.showEnding());
  }

  // -------------------------------------------------------------------------
  //  Queries used by the player and UI
  // -------------------------------------------------------------------------

  findLockTarget(from, current = null, dir = 0, maxDist = 30) {
    const cam = from.camera;
    let best = null, bestScore = -Infinity;
    for (const a of this.actors) {
      if (a === from || a.dead || a.faction === from.faction) continue;
      if (a.faction === FACTION.NEUTRAL) continue;
      const d = v3distXZ(from, a);
      if (d > maxDist) continue;
      // Prefer targets near the centre of the screen.
      const ang = Math.atan2(a.x - from.x, a.z - from.z);
      const off = angleDelta(cam.yaw, ang);
      if (Math.abs(off) > 1.15) continue;
      if (current) {
        const curAng = Math.atan2(current.x - from.x, current.z - from.z);
        const rel = angleDelta(curAng, ang);
        if (dir > 0 && rel <= 0.05) continue;
        if (dir < 0 && rel >= -0.05) continue;
        if (a === current) continue;
      }
      const score = -Math.abs(off) * 3 - d * 0.05 + (a.isBoss ? 2 : 0);
      if (score > bestScore) { bestScore = score; best = a; }
    }
    if (best) this.audio.playUI('click');
    return best;
  }

  nearestEnemy(from, maxDist = 6, cone = Math.PI) {
    let best = null, bestD = maxDist;
    for (const a of this.actors) {
      if (a === from || a.dead || a.faction === from.faction) continue;
      if (a.faction === FACTION.NEUTRAL) continue;
      const d = v3distXZ(from, a);
      if (d > bestD) continue;
      if (Math.abs(angleDelta(from.yaw, Math.atan2(a.x - from.x, a.z - from.z))) > cone) continue;
      best = a; bestD = d;
    }
    return best;
  }

  alertNearby(source, radius, target) {
    if (radius <= 0) return;
    for (const e of this.enemies) {
      if (e === source || e.dead || !e.brain) continue;
      if (e.brain.target) continue;
      if (v3distXZ(e, source) > radius) continue;
      e.brain.target = target;
      e.brain.alertness = 2;
      e.brain.reactionDelay = 0.3 + Math.random() * 0.6;
      e.brain.setState(AI_STATE.CHASE);
    }
  }

  spawnEnemy(archetype, x, z, opts = {}) {
    const e = new Enemy(this, archetype, { x, z, level: opts.level || 1, ...opts });
    e.y = this.world.heightAt(x, z);
    this.actors.push(e);
    this.enemies.push(e);
    if (opts.summoned) {
      e.removeAfter = 4;
      this.particles.burst(x, e.y + 0.6, z, 18, {
        r: 0.4, g: 0.7, b: 0.3, size: 0.24, life: 0.7, spread: 2, up: 2,
        blend: BLEND.ADDITIVE, alpha: 0.9, drag: 2, gravity: 1,
      });
    }
    return e;
  }

  spawnExplosion(x, y, z, opts) {
    this.areaEffects.push(new AreaEffect(this, {
      x, y, z,
      radius: opts.radius || 3, delay: 0, duration: 0.3,
      damage: opts.damage || 60, poise: 30, type: opts.type || 'fire',
      source: opts.source || null, faction: opts.faction !== undefined ? opts.faction : FACTION.ENEMY,
      color: opts.color || [1, 0.5, 0.2], telegraph: false,
    }));
  }

  // -------------------------------------------------------------------------
  //  Player death / respawn
  // -------------------------------------------------------------------------

  respawnPlayer() {
    const p = this.player;
    const poi = this.world.pois.find((q) => q.id === p.lastGraceId)
      || this.world.graces.find((g) => g.isStart) || this.world.graces[0];
    p.revive();
    p.fp = p.maxFp;
    p.stamina = p.maxStamina;
    p.buffs.length = 0;
    for (const k in p.status) { p.status[k].active = 0; p.status[k].build = 0; }
    p.lockTarget = null;
    p.invuln = 1.5;
    if (poi) p.teleport(poi.x + 3, undefined, poi.z + 3);
    p.refillFlasks();
    this.renderer.deathFade = 0;
    this.respawnWorld();
    this.terrain.primeAround(p.x, p.z, 220);
    this.grass.dirty = true;
    this.ui?.closeAll();
  }

  collectDeathDrop() {
    const p = this.player;
    if (!p.deathDrop) return false;
    const d = Math.hypot(p.deathDrop.x - p.x, p.deathDrop.z - p.z);
    if (d > 2.6) return false;
    p.souls += p.deathDrop.souls;
    this.notify(`残り火 ${p.deathDrop.souls} を取り戻した`, 'good');
    this.audio.playPickup();
    p.deathDrop = null;
    return true;
  }

  // -------------------------------------------------------------------------
  //  Render
  // -------------------------------------------------------------------------

  render(dt) {
    const p = this.player;
    const cam = this.renderer.camera;
    if (p) {
      cam.pos.x = p.camera.pos.x; cam.pos.y = p.camera.pos.y; cam.pos.z = p.camera.pos.z;
      cam.target.x = p.camera.look.x; cam.target.y = p.camera.look.y; cam.target.z = p.camera.look.z;
      cam.fov = p.camera.fov;
    }
    cam.far = this.renderer.quality.viewDistance * 2.2;
    cam.update(this.canvas.width / this.canvas.height);

    // The grass batch is *not* cleared per frame: it is a rolling patch that
    // only changes when the player has moved far enough, so it stays uploaded
    // between rebuilds.
    this.batches.clearAll();

    const view = this.renderer.quality.viewDistance;
    this.terrain.update(cam.pos.x, cam.pos.z, view, cam.frustum, cam.pos.y);

    if (p) {
      this._gatherStructures(p.x, p.z);
      this._gatherProps(p.x, p.z);
      if (this.grass.needsRebuild(p.x, p.z)) {
        this.grass.rebuild(this.grassBatch, p.x, p.z);
        this._grassDirty = true;
      }
      this.scatter.evictFarChunks(p.x, p.z, STRUCTURE_RANGE + 200);
    }

    for (const a of this.actors) {
      if (!a.visible) continue;
      const d = v3distXZ(a, cam.pos);
      if (d > view) continue;
      a.render(this.batches);
    }
    for (const pr of this.projectiles) pr.render(this.batches);

    // The player's dropped embers.
    if (p && p.deathDrop) {
      const dd = p.deathDrop;
      const y = this.world.heightAt(dd.x, dd.z);
      this.batches.get('rockS').push(dd.x, y + 0.2 + Math.sin(this.time * 2) * 0.08, dd.z,
        0.5, 0.5, 0.5, this.time * 0.7, 1.0, 0.72, 0.30, 2.4, 0, 0, 1, 1);
      if (Math.random() < 0.4) this.particles.ember(dd.x, y + 0.3, dd.z);
    }

    this.batches.uploadAll();
    if (this._grassDirty) { this.grassBatch.upload(); this._grassDirty = false; }
    this.renderer.setPointLights(this.lights, cam.pos.x, cam.pos.y, cam.pos.z);

    const scene = {
      terrain: this.terrain,
      batches: this.batches,
      grassBatch: this.grassBatch,
      particles: this.particles,
      palette: this._regionPalette(),
      trample: p ? { x: p.x, y: p.y, z: p.z } : { x: 0, y: 0, z: 0 },
      trampleRadius: 1.1,
      focusY: p ? p.y : 0,
    };
    this.renderer.render(scene, this.time, dt);
  }

  _gatherProps(px, pz) {
    const B = this.batches;
    const propDist = this.renderer.quality.propDistance;
    const lodLine = Math.min(95, propDist * 0.34);
    const cam = this.renderer.camera;
    const range = Math.ceil(propDist / CHUNK_SIZE);
    const pcx = Math.floor((px + WORLD_HALF) / CHUNK_SIZE);
    const pcz = Math.floor((pz + WORLD_HALF) / CHUNK_SIZE);
    // Off-screen props still matter inside the shadow range — a tree behind the
    // camera casts across the ground in front of it — so the frustum test only
    // applies beyond that radius.
    const frustum = cam.frustum;
    const shadowKeep = this.renderer.quality.shadowRange + CHUNK_SIZE * 0.75;
    // Per prop the radius can be tight: anything past the shadow range simply
    // isn't in the shadow map, so off-screen props out there cost nothing but
    // triangles. The chunk test above has to stay loose by a chunk radius.
    const propShadowKeep = this.renderer.quality.shadowRange * 1.1;
    // Clutter casts no shadow, so unlike the props above it can be frustum
    // culled at any distance — nothing off-screen contributes to the frame.
    const clutterScale = propDist / 300;
    let clutterBudget = CLUTTER_BUILD_BUDGET;

    for (let dz = -range; dz <= range; dz++) {
      for (let dx = -range; dx <= range; dx++) {
        const cx = pcx + dx, cz = pcz + dz;
        if (cx < 0 || cz < 0 || cx >= CHUNKS || cz >= CHUNKS) continue;
        const centerX = cx * CHUNK_SIZE - WORLD_HALF + CHUNK_SIZE / 2;
        const centerZ = cz * CHUNK_SIZE - WORLD_HALF + CHUNK_SIZE / 2;
        const cd = Math.hypot(centerX - px, centerZ - pz);
        if (cd > propDist + CHUNK_SIZE) continue;
        if (frustum && cd > shadowKeep) {
          // Sphere is generous on Y: props sit on terrain that swings well
          // above and below the chunk's nominal centre height.
          const cy = this.world.heightAt(centerX, centerZ);
          if (!sphereInFrustum(frustum, centerX, cy + 12, centerZ, CHUNK_SIZE * 0.78)) continue;
        }

        const props = this.scatter.propsFor(cx, cz);
        for (let i = 0; i < props.length; i++) {
          const p = props[i];
          const d = Math.hypot(p.x - px, p.z - pz);
          if (d > propDist) continue;
          const s = p.scale;
          if (frustum && d > propShadowKeep
            && !sphereInFrustum(frustum, p.x, p.y + s * 3, p.z, s * 5)) continue;
          // Detailed silhouettes only where the player can read them; past the
          // LOD line the simplified meshes are indistinguishable through fog.
          const far = d > lodLine;
          switch (p.type) {
            case PROP.TREE_BROAD:
              B.get(far ? 'treeFar' : 'treeBroad').push(p.x, p.y, p.z, s, s, s, p.yaw,
                p.bark[0], p.bark[1], p.bark[2], 0, far ? 0 : 1, p.phase, 1, 1,
                p.leaf[0], p.leaf[1], p.leaf[2]);
              break;
            case PROP.TREE_CONIFER:
              B.get(far ? 'coniferFar' : 'treeConifer').push(p.x, p.y, p.z, s, s, s, p.yaw,
                p.bark[0] * 0.9, p.bark[1] * 0.9, p.bark[2] * 0.9, 0, far ? 0 : 0.8, p.phase, 1, 1,
                p.leaf[0] * 0.9, p.leaf[1] * 0.95, p.leaf[2] * 0.9);
              break;
            case PROP.TREE_DEAD:
              B.get('treeDead').push(p.x, p.y, p.z, s, s, s, p.yaw,
                p.bark[0], p.bark[1], p.bark[2], 0, 0.5, p.phase, 1, 1);
              break;
            case PROP.BUSH:
              if (d < propDist * 0.55) {
                B.get('bush').push(p.x, p.y, p.z, s, s, s, p.yaw,
                  p.leaf[0] * 1.1, p.leaf[1] * 1.1, p.leaf[2] * 1.1, 0, 1.4, p.phase, 0.9, 1);
              }
              break;
            case PROP.ROCK_S:
              B.get('rockS').push(p.x, p.y, p.z, s, s * 0.8, s, p.yaw, 0.40, 0.39, 0.37);
              break;
            case PROP.ROCK_L:
              B.get('rockL').push(p.x, p.y, p.z, s, s * 0.85, s, p.yaw, 0.38, 0.37, 0.35);
              break;
            case PROP.REED:
              if (d < propDist * 0.4) {
                B.get('reed').push(p.x, p.y, p.z, s * 0.45, s * 1.6, s * 0.45, p.yaw,
                  p.leaf[0] * 1.2, p.leaf[1] * 1.15, p.leaf[2] * 0.9, 0, 2.2, p.phase, 1, 1);
              }
              break;
            default: break;
          }
        }

        // --- land features ----------------------------------------------------
        // Built unbudgeted, unlike clutter: a chunk is about a hundred
        // candidates, and movement collision reads the same cache and cannot be
        // told to wait a frame for the wall in front of the player.
        const feat = this.scatter.featuresFor(cx, cz);
        for (let i = 0; i < feat.length; i += FEATURE_STRIDE) {
          const t = feat[i];
          const x = feat[i + 1], y = feat[i + 2], z = feat[i + 3];
          const ddx = x - px, ddz = z - pz;
          const d2 = ddx * ddx + ddz * ddz;
          let sx = feat[i + 5], sy = feat[i + 6], sz = feat[i + 7];
          const lim = Math.min(FEATURE_RANGE[t], propDist);
          if (d2 > lim * lim) continue;
          // Off-screen features are worth keeping only while they can still
          // cast into the frame; the rest are pure cost.
          const keep = FEATURE_SHADOW[t] ? propShadowKeep : 16;
          const size = sx > sz ? sx : sz;
          if (frustum && d2 > keep * keep
            && !sphereInFrustum(frustum, x, y + sy * 0.6, z, size * 0.9 + sy)) continue;
          const fadeAt = lim * 0.9;
          if (d2 > fadeAt * fadeAt) {
            const f = (lim - Math.sqrt(d2)) / (lim * 0.1);
            sx *= f; sy *= f; sz *= f;
          }
          this.featureBatches[t].push(x, y, z, sx, sy, sz, feat[i + 4],
            feat[i + 8], feat[i + 9], feat[i + 10], 0, FEATURE_SWAY[t], feat[i + 14], 1, 1,
            feat[i + 11], feat[i + 12], feat[i + 13]);
        }

        // --- ground clutter -------------------------------------------------
        if (cd > CLUTTER_RANGE_MAX * clutterScale + CHUNK_SIZE) continue;
        const fresh = !this.scatter.clutterCache.has(this.scatter.chunkKey(cx, cz));
        const cl = this.scatter.clutterFor(cx, cz, clutterBudget > 0);
        if (!cl) continue;              // over budget: it arrives next frame
        if (fresh) clutterBudget--;
        // Squared distances throughout: this loop runs over every cached item
        // in a fifteen-chunk ring every frame, and a square root per item is
        // the one avoidable cost in it.
        for (let i = 0; i < cl.length; i += CLUTTER_STRIDE) {
          const t = cl[i];
          const x = cl[i + 1], y = cl[i + 2], z = cl[i + 3];
          const ddx = x - px, ddz = z - pz;
          const d2 = ddx * ddx + ddz * ddz;
          let sx = cl[i + 5], sy = cl[i + 6], sz = cl[i + 7];
          // An object earns its draw distance by its size: below roughly one
          // pixel it is only cost. 150x the largest dimension is that pixel at
          // the resolutions this runs at, capped by the kind's own limit.
          const size = sx > sy ? (sx > sz ? sx : sz) : (sy > sz ? sy : sz);
          // ...then stretched by the biome's own multiplier. On a plain the
          // last stretch of that range is drawing sub-pixel debris, which is
          // usually waste — but there it is the only thing standing between the
          // middle distance and bare shading, so the flat biomes buy it.
          const lim = Math.min(CLUTTER_RANGE[t], Math.max(40, size * 150))
            * cl[i + 15] * clutterScale;
          if (d2 > lim * lim) continue;
          if (frustum && d2 > 196
            && !sphereInFrustum(frustum, x, y + sy * 0.5, z, size * 0.9)) continue;
          // Shrink into the ground over the last stretch rather than popping.
          const fadeAt = lim * 0.86;
          if (d2 > fadeAt * fadeAt) {
            const f = (lim - Math.sqrt(d2)) / (lim * 0.14);
            sx *= f; sy *= f; sz *= f;
          }
          // Embers are worth seeing across a burnt pan and worth nothing as a
          // sub-pixel sparkle beyond it — a glowing dot smaller than a pixel is
          // just noise on the horizon — so the glow is carried only while the
          // crack holding it is still resolvable. Squared distance throughout:
          // this is the hottest loop in the frame.
          const emis = cl[i + 16] > 0 && d2 < 12100 ? cl[i + 16] * (1 - d2 / 12100) : 0;
          this.clutterBatches[t].push(x, y, z, sx, sy, sz, cl[i + 4],
            cl[i + 8], cl[i + 9], cl[i + 10], emis, CLUTTER_SWAY[t], cl[i + 14], 1, 1,
            cl[i + 11], cl[i + 12], cl[i + 13]);
        }
      }
    }
  }

  _regionPalette() {
    const p = this.player;
    if (!p) return {};
    const { region } = this.world.regionAt(p.x, p.z);
    const rock = BIOME_INFO[region.biome]?.rock || [0.40, 0.39, 0.37];
    return {
      rock,
      sand: region.biome === BIOME.ASH ? [0.34, 0.30, 0.28] : [0.70, 0.64, 0.48],
      snow: [0.70, 0.75, 0.82],
      road: region.biome === BIOME.ASH ? [0.30, 0.26, 0.24] : [0.40, 0.34, 0.26],
      waterShallow: region.biome === BIOME.MARSH ? [0.20, 0.26, 0.16] : [0.18, 0.34, 0.36],
      waterDeep: region.biome === BIOME.MARSH ? [0.08, 0.12, 0.07] : [0.045, 0.10, 0.14],
    };
  }

  // -------------------------------------------------------------------------

  save(slot, opts = {}) {
    const target = clamp(Number.isFinite(slot) ? Math.floor(slot) : this.activeSaveSlot, 0, 2);
    this.activeSaveSlot = target;
    const ok = saveGame(target, this);
    if (ok) {
      this._lastAutosave = Date.now();
      this._autosaveClock = 0;
      if (opts.silent) this.ui?.showSavePulse();
      else this.notify(`スロット${target + 1}にセーブしました`);
    } else if (!opts.silent) {
      this.notify('セーブに失敗しました', 'bad');
    }
    return ok;
  }

  autosave(reason = '自動保存', force = false) {
    if (!this.started || !this.player || this.player.dead) return false;
    const now = Date.now();
    if (!force && now - this._lastAutosave < 15000) return false;
    const ok = this.save(this.activeSaveSlot, { silent: true });
    if (!ok) this.notify(`${reason}に失敗しました`, 'bad');
    return ok;
  }
}

// ---------------------------------------------------------------------------
//  Helpers
// ---------------------------------------------------------------------------

function poiHeight(world, l) {
  return world.heightAt(l.x, l.z);
}

function hashStr(s) {
  let h = 2166136261 >>> 0;
  for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619) >>> 0; }
  return h >>> 0;
}

function interactLabel(it) {
  switch (it.kind) {
    case 'grace': return `${it.poi.name} で休息`;
    case 'chest': return '宝箱を開ける';
    case 'shrine': return '祠に触れる';
    case 'fog': return '霧をくぐる';
    case 'npc': return `${it.npc.name} と話す`;
    default: return '調べる';
  }
}

function statLabel(k) {
  return { vig: '生命力', mnd: '精神力', end: '持久力', str: '筋力', dex: '技量', int: '理力', fth: '信仰' }[k] || k;
}

const CHEST_TABLES = [
  // tier 0
  { souls: [120, 400], items: [['flask_hp', 0.10, 1], ['mat_shard', 0.45, 1], ['herb_green', 0.3, 1], ['throwing_knife', 0.3, 4], ['ember_shard', 0.25, 1]] },
  // tier 1
  { souls: [400, 1400], items: [['mat_shard', 0.5, 2], ['mat_chunk', 0.25, 1], ['firebomb', 0.3, 3], ['stone_whet', 0.25, 2], ['ember_shard', 0.35, 2], ['tal_vigor', 0.08, 1], ['tal_endure', 0.08, 1]] },
  // tier 2
  { souls: [1500, 5200], items: [['mat_chunk', 0.6, 2], ['mat_core', 0.28, 1], ['homeward', 0.3, 2], ['resin_fire', 0.3, 2], ['tal_hunter', 0.12, 1], ['tal_stone', 0.12, 1], ['tal_parry', 0.08, 1], ['sword_ember', 0.06, 1], ['great_frost', 0.04, 1]] },
];

function rollChestLoot(rng, tier, level) {
  const table = CHEST_TABLES[Math.min(tier, CHEST_TABLES.length - 1)];
  const items = [];
  for (const [id, chance, n] of table.items) {
    if (rng() < chance) items.push([id, n]);
  }
  if (!items.length) items.push(['mat_shard', 1]);
  const souls = Math.round(lerp(table.souls[0], table.souls[1], rng()) * (1 + level * 0.05));
  return { items, souls };
}

export { rollChestLoot, interactLabel, statLabel };
