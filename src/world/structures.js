// ============================================================================
//  structures.js — turns points of interest into actual places.
//
//  Each POI expands into a deterministic arrangement of props, colliders,
//  light sources and spawn points. A "camp" is not a marker on a map; it is
//  three tents, a fire, a stack of crates and four bandits placed around it
//  the same way every time you load the world.
// ============================================================================

import { makeRng } from '../core/rng.js';
import { TAU, lerp, clamp } from '../core/math.js';
// Two numbers, not geometry. A landmark reports the height it really has, and
// for four of the thirteen that height is the top of an arch or a watchtower —
// so the figure has to come from the builder that decides it rather than be
// copied here, where it would keep its old value the first time somebody adds
// a course to either mesh.
import { ARCH_HEIGHT, WATCHTOWER_HEIGHT } from '../gfx/mesh.js';

export const SPROP = {
  HUT: 'hut', PILLAR: 'pillar', ARCH: 'arch', CAMPFIRE: 'campfire',
  GRACE: 'grace', CHEST: 'chest', TOWER: 'tower', CRATE: 'crate',
  FENCE: 'fence', BANNER: 'banner', STATUE: 'statue', RUBBLE: 'rubble',
  TENT: 'tent', BARREL: 'barrel', TORCH: 'torch', ALTAR: 'altar',
  // Dressing, drawn from the ground-clutter batches. A place is not just its
  // silhouette: a camp has firewood and chips of stone around the fire, an
  // arena has what is left of everyone who came before. These cost 15 to 24
  // triangles each and are what stop the ground inside a POI reading as a
  // cleared lawn with objects standing on it.
  DEBRIS: 'debris', DEADWOOD: 'deadwood', BONES: 'bones', SCRUB: 'scrub',
};

const COLOR = {
  wood: [0.32, 0.24, 0.17],
  darkWood: [0.24, 0.18, 0.13],
  stone: [0.44, 0.43, 0.41],
  oldStone: [0.38, 0.37, 0.34],
  cloth: [0.44, 0.34, 0.24],
  banner: [0.46, 0.16, 0.15],
  metal: [0.52, 0.53, 0.56],
  gold: [0.72, 0.58, 0.24],
  ash: [0.30, 0.28, 0.27],
  bone: [0.56, 0.54, 0.46],
  scrub: [0.30, 0.33, 0.18],
  // Landmark stone. A thing meant to be picked out at four hundred metres has
  // to sit apart from the ground it stands on, and at that range colour is
  // nearly all that is left of it — so each set-piece gets a material of its
  // own rather than the ordinary ruin grey.
  pale: [0.62, 0.60, 0.54],       // weathered limestone, reads against grass
  basalt: [0.19, 0.18, 0.19],     // black stone, reads against ash and snow
  bronze: [0.40, 0.31, 0.15],
  iron: [0.29, 0.29, 0.32],
  petrified: [0.50, 0.47, 0.41],
  peatWood: [0.20, 0.17, 0.14],
};

/**
 * Scatter `n` dressing props in an annulus around a point. Deterministic like
 * everything else here — same seed, same litter.
 */
function litter(add, type, cx, cz, n, r0, r1, rng, opts = {}) {
  for (let i = 0; i < n; i++) {
    const a = rng() * TAU;
    const r = r0 + (r1 - r0) * Math.sqrt(rng());
    add(type, cx + Math.cos(a) * r, cz + Math.sin(a) * r, {
      scale: (opts.scale || 1) * (0.7 + rng() * 0.7),
      color: opts.color || COLOR.oldStone,
    });
  }
}

/**
 * @returns {{props: Array, colliders: Array, lights: Array, spawns: Array}}
 */
export function buildStructure(world, poi) {
  const rng = makeRng((world.seed ^ hashId(poi.id)) >>> 0);
  const out = { props: [], colliders: [], lights: [], spawns: [], interacts: [] };
  const ground = (x, z) => world.heightAt(x, z);

  const add = (type, x, z, opts = {}) => {
    out.props.push({
      type, x, z,
      y: opts.y !== undefined ? opts.y : ground(x, z),
      yaw: opts.yaw !== undefined ? opts.yaw : rng() * TAU,
      scale: opts.scale || 1,
      color: opts.color || COLOR.stone,
      emissive: opts.emissive || 0,
    });
    if (opts.collide) out.colliders.push({ x, z, r: opts.collide });
  };

  switch (poi.kind) {
    case 'grace': buildGrace(poi, add, out, rng); break;
    case 'camp': buildCamp(poi, add, out, rng, world); break;
    case 'ruin': buildRuin(poi, add, out, rng, world); break;
    case 'village': buildVillage(poi, add, out, rng, world); break;
    case 'boss': buildArena(poi, add, out, rng, world); break;
    case 'mini': buildMiniSite(poi, add, out, rng, world); break;
    case 'chest': buildChestSite(poi, add, out, rng); break;
    case 'shrine': buildShrine(poi, add, out, rng); break;
    case 'landmark': buildLandmark(poi, add, out, rng, world, ground); break;
    case 'merchant': case 'smith': break;   // the NPC is the structure
    default: break;
  }
  measure(out, ground);
  return out;
}

/**
 * How far above its own base each prop type reaches, per unit of `scale`.
 *
 * These mirror what game.js `_renderStructure` actually pushes — it is the
 * caller that chooses the instance dimensions, not the mesh — multiplied by the
 * mesh extents in gfx/mesh.js. Two entries are marked nominal because their
 * mesh is built from the world's shared geometry stream and so is not a fixed
 * size; nothing that reports a landmark height is built out of those.
 */
const PROP_TOP = {
  [SPROP.HUT]: 4.25,
  [SPROP.PILLAR]: 3.4,        // nominal: 2..5 seeded drums
  [SPROP.ARCH]: ARCH_HEIGHT,
  [SPROP.CAMPFIRE]: 0.34,
  [SPROP.GRACE]: 2.02,
  [SPROP.CHEST]: 0.96,
  [SPROP.TOWER]: WATCHTOWER_HEIGHT,
  [SPROP.CRATE]: 0.75,
  [SPROP.BARREL]: 1.00,
  [SPROP.TENT]: 2.20,
  [SPROP.RUBBLE]: 0.84,       // nominal: the rock mesh is seeded and lumpy
  [SPROP.TORCH]: 2.30,
  [SPROP.ALTAR]: 0.85,
  [SPROP.DEBRIS]: 0.60,
  [SPROP.DEADWOOD]: 0.16,
  [SPROP.BONES]: 0.60,
  [SPROP.SCRUB]: 0.60,
};

// Props whose renderer ignores `scale` and draws them at one fixed size.
const PROP_FIXED = {
  [SPROP.FENCE]: 1.15,
  [SPROP.BANNER]: 3.20,
  [SPROP.STATUE]: 2.60,
};

// The four prop types game.js stops drawing past 150 m. They are scattered
// wide and low, so they are excluded from the height datum below — a chip of
// stone that rolled down the hill must not make a tower taller.
const DRESSING = new Set([SPROP.DEBRIS, SPROP.DEADWOOD, SPROP.BONES, SPROP.SCRUB]);

/**
 * Record how tall the structure that was just built actually is.
 *
 * Measured off the props that were placed rather than declared alongside them,
 * because a declared height is a comment: it stays at 40 m after somebody drops
 * the top two courses.
 *
 * The datum is the *median* ground under the structure's own footprint, not the
 * ground at its centre. That distinction is the difference between a real
 * number and a flattering one for anything built across broken ground: the
 * fallen span stands on the two lips of a chasm, and measuring it from the
 * chasm floor would credit it with thirty metres of empty air that nobody
 * standing on ordinary ground can see past.
 *
 * @param {(x: number, z: number) => number} ground terrain sampler
 */
function measure(out, ground) {
  let top = -Infinity;
  const feet = [];
  for (const p of out.props) {
    const t = p.y + (PROP_FIXED[p.type] !== undefined
      ? PROP_FIXED[p.type]
      : (PROP_TOP[p.type] || 0) * p.scale);
    if (t > top) top = t;
    if (!DRESSING.has(p.type)) feet.push(ground(p.x, p.z));
  }
  if (!feet.length) { out.top = 0; out.height = 0; return; }
  feet.sort((a, b) => a - b);
  const datum = feet[feet.length >> 1];
  out.top = top;
  out.height = Math.max(0, top - datum);
}

function hashId(str) {
  let h = 5381;
  for (let i = 0; i < str.length; i++) h = ((h << 5) + h + str.charCodeAt(i)) >>> 0;
  return h;
}

// ---------------------------------------------------------------------------

function buildGrace(poi, add, out, rng) {
  add(SPROP.GRACE, poi.x, poi.z, { scale: 1, color: [0.58, 0.56, 0.52], collide: 0.7, emissive: 0 });
  // A ring of low stones marking the site.
  for (let i = 0; i < 6; i++) {
    const a = (i / 6) * TAU + rng() * 0.3;
    const r = 2.6 + rng() * 0.8;
    add(SPROP.RUBBLE, poi.x + Math.cos(a) * r, poi.z + Math.sin(a) * r, {
      scale: 0.5 + rng() * 0.5, color: COLOR.oldStone,
    });
  }
  litter(add, SPROP.SCRUB, poi.x, poi.z, 6, 2.0, 6.5, rng, { color: COLOR.scrub, scale: 1.1 });
  out.lights.push({ x: poi.x, y: 1.2, z: poi.z, color: [1.0, 0.72, 0.34], radius: 9, kind: 'grace' });
  out.interacts.push({ x: poi.x, z: poi.z, r: 3.0, kind: 'grace', poi });
}

function buildCamp(poi, add, out, rng, world) {
  const fx = poi.x, fz = poi.z;
  add(SPROP.CAMPFIRE, fx, fz, { scale: 1, color: COLOR.stone, collide: 0.6 });
  out.lights.push({ x: fx, y: 0.6, z: fz, color: [1.0, 0.55, 0.20], radius: 11, kind: 'fire' });

  const tents = 2 + Math.floor(rng() * 2);
  for (let i = 0; i < tents; i++) {
    const a = (i / tents) * TAU + rng() * 0.6;
    const r = 4.5 + rng() * 2.5;
    const x = fx + Math.cos(a) * r, z = fz + Math.sin(a) * r;
    add(SPROP.TENT, x, z, { yaw: a + Math.PI, scale: 0.9 + rng() * 0.3, color: COLOR.cloth, collide: 1.5 });
  }
  const crates = 2 + Math.floor(rng() * 3);
  for (let i = 0; i < crates; i++) {
    const a = rng() * TAU, r = 2.5 + rng() * 4;
    add(rng() < 0.5 ? SPROP.CRATE : SPROP.BARREL, fx + Math.cos(a) * r, fz + Math.sin(a) * r, {
      scale: 0.8 + rng() * 0.4, color: COLOR.wood, collide: 0.55,
    });
  }
  for (let i = 0; i < 2; i++) {
    const a = rng() * TAU, r = 6 + rng() * 2;
    add(SPROP.TORCH, fx + Math.cos(a) * r, fz + Math.sin(a) * r, { color: COLOR.darkWood, emissive: 0 });
    out.lights.push({
      x: fx + Math.cos(a) * r, y: 1.9, z: fz + Math.sin(a) * r,
      color: [1.0, 0.6, 0.25], radius: 8, kind: 'fire',
    });
  }

  const count = 3 + Math.floor(rng() * 3);
  for (let i = 0; i < count; i++) {
    const a = (i / count) * TAU + rng() * 0.8;
    const r = 3 + rng() * 5;
    out.spawns.push({ x: fx + Math.cos(a) * r, z: fz + Math.sin(a) * r, role: 'camp' });
  }
  if (rng() < 0.55) {
    const a = rng() * TAU;
    out.interacts.push({
      x: fx + Math.cos(a) * 6, z: fz + Math.sin(a) * 6, r: 1.6,
      kind: 'chest', poi: { id: `${poi.id}_chest`, kind: 'chest', tier: rng() < 0.3 ? 1 : 0, opened: false },
    });
    add(SPROP.CHEST, fx + Math.cos(a) * 6, fz + Math.sin(a) * 6, { color: COLOR.darkWood, collide: 0.7 });
  }

  // Dressing last, always: it draws from the same rng stream, and placing it
  // earlier would shift every spawn in the camp.
  // Firewood by the fire, stone chips trodden into the ground around it, and
  // the leavings of whatever they last ate.
  litter(add, SPROP.DEADWOOD, fx, fz, 5, 1.4, 5.0, rng, { color: COLOR.darkWood, scale: 0.9 });
  litter(add, SPROP.DEBRIS, fx, fz, 7, 1.2, 9.0, rng, { color: COLOR.oldStone, scale: 0.8 });
  litter(add, SPROP.BONES, fx, fz, 3, 2.5, 8.0, rng, { color: COLOR.bone, scale: 0.85 });
}

function buildRuin(poi, add, out, rng, world) {
  const cx = poi.x, cz = poi.z;
  if (rng() < 0.6) {
    add(SPROP.ARCH, cx, cz, { yaw: rng() * TAU, scale: 0.9 + rng() * 0.4, color: COLOR.oldStone, collide: 1.1 });
  }
  const pillars = 4 + Math.floor(rng() * 5);
  for (let i = 0; i < pillars; i++) {
    const a = (i / pillars) * TAU + rng() * 0.4;
    const r = 5 + rng() * 8;
    add(SPROP.PILLAR, cx + Math.cos(a) * r, cz + Math.sin(a) * r, {
      scale: 0.8 + rng() * 0.7, color: COLOR.oldStone, collide: 0.55,
    });
  }
  const rubble = 6 + Math.floor(rng() * 8);
  for (let i = 0; i < rubble; i++) {
    const a = rng() * TAU, r = rng() * 14;
    add(SPROP.RUBBLE, cx + Math.cos(a) * r, cz + Math.sin(a) * r, {
      scale: 0.6 + rng() * 1.2, color: COLOR.oldStone,
    });
  }
  if (rng() < 0.5) {
    add(SPROP.STATUE, cx + (rng() - 0.5) * 6, cz + (rng() - 0.5) * 6, {
      scale: 1.0 + rng() * 0.3, color: COLOR.stone, collide: 0.6,
    });
  }
  const count = 2 + Math.floor(rng() * 3);
  for (let i = 0; i < count; i++) {
    const a = rng() * TAU, r = 3 + rng() * 9;
    out.spawns.push({ x: cx + Math.cos(a) * r, z: cz + Math.sin(a) * r, role: 'ruin' });
  }
  if (rng() < 0.7) {
    const a = rng() * TAU, r = 2 + rng() * 5;
    const x = cx + Math.cos(a) * r, z = cz + Math.sin(a) * r;
    add(SPROP.CHEST, x, z, { color: COLOR.darkWood, collide: 0.7 });
    out.interacts.push({
      x, z, r: 1.6, kind: 'chest',
      poi: { id: `${poi.id}_chest`, kind: 'chest', tier: rng() < 0.4 ? 1 : 0, opened: false },
    });
  }
  // What fell off the pillars, and what has grown back through it since.
  litter(add, SPROP.DEBRIS, cx, cz, 14, 2.0, 16, rng, { color: COLOR.oldStone, scale: 1.1 });
  litter(add, SPROP.SCRUB, cx, cz, 10, 3.0, 17, rng, { color: COLOR.scrub, scale: 1.0 });
  litter(add, SPROP.DEADWOOD, cx, cz, 3, 4.0, 15, rng, { color: COLOR.darkWood });
}

function buildVillage(poi, add, out, rng, world) {
  const cx = poi.x, cz = poi.z;
  const huts = 5 + Math.floor(rng() * 4);
  for (let i = 0; i < huts; i++) {
    const a = (i / huts) * TAU + rng() * 0.3;
    const r = 9 + rng() * 12;
    const x = cx + Math.cos(a) * r, z = cz + Math.sin(a) * r;
    add(SPROP.HUT, x, z, { yaw: a + Math.PI + (rng() - 0.5) * 0.5, scale: 0.9 + rng() * 0.3, color: COLOR.wood, collide: 2.6 });
    if (rng() < 0.5) {
      out.lights.push({ x, y: 1.6, z, color: [1.0, 0.66, 0.32], radius: 7, kind: 'window' });
    }
  }
  add(SPROP.CAMPFIRE, cx, cz, { scale: 1.4, color: COLOR.stone, collide: 0.8 });
  out.lights.push({ x: cx, y: 0.8, z: cz, color: [1.0, 0.58, 0.24], radius: 14, kind: 'fire' });

  add(SPROP.TOWER, cx + 16, cz - 12, { scale: 1, color: COLOR.stone, collide: 2.2 });

  // Fence line around the settlement, with a gap for the road.
  const segs = 26;
  for (let i = 0; i < segs; i++) {
    const a = (i / segs) * TAU;
    if (a > 2.5 && a < 3.4) continue;
    const r = 24 + Math.sin(a * 3) * 2;
    add(SPROP.FENCE, cx + Math.cos(a) * r, cz + Math.sin(a) * r, {
      yaw: a + Math.PI / 2, scale: 1, color: COLOR.darkWood, collide: 0.5,
    });
  }
  for (let i = 0; i < 4; i++) {
    const a = rng() * TAU, r = 6 + rng() * 10;
    add(SPROP.BANNER, cx + Math.cos(a) * r, cz + Math.sin(a) * r, {
      scale: 1, color: COLOR.banner, collide: 0.35,
    });
  }
  for (let i = 0; i < 5; i++) {
    const a = rng() * TAU, r = 4 + rng() * 14;
    add(rng() < 0.5 ? SPROP.CRATE : SPROP.BARREL, cx + Math.cos(a) * r, cz + Math.sin(a) * r, {
      scale: 0.8 + rng() * 0.3, color: COLOR.wood, collide: 0.5,
    });
  }
  // Cut wood stacked where it was split, and the gravel of a worked yard.
  litter(add, SPROP.DEADWOOD, cx, cz, 8, 5, 20, rng, { color: COLOR.wood, scale: 0.95 });
  litter(add, SPROP.DEBRIS, cx, cz, 10, 4, 22, rng, { color: COLOR.stone, scale: 0.75 });
}

function buildArena(poi, add, out, rng, world) {
  const cx = poi.x, cz = poi.z;
  const R = poi.radius || 30;

  // A broken colonnade defining the arena edge.
  const pillars = 16;
  for (let i = 0; i < pillars; i++) {
    const a = (i / pillars) * TAU;
    const r = R * (0.94 + rng() * 0.10);
    add(SPROP.PILLAR, cx + Math.cos(a) * r, cz + Math.sin(a) * r, {
      scale: 1.4 + rng() * 1.0, color: COLOR.oldStone, collide: 0.65,
    });
  }
  for (let i = 0; i < 10; i++) {
    const a = rng() * TAU, r = rng() * R * 0.8;
    add(SPROP.RUBBLE, cx + Math.cos(a) * r, cz + Math.sin(a) * r, {
      scale: 0.8 + rng() * 1.4, color: COLOR.oldStone,
    });
  }
  // Braziers for light and for silhouetting the boss.
  for (let i = 0; i < 4; i++) {
    const a = (i / 4) * TAU + 0.4;
    const r = R * 0.6;
    const x = cx + Math.cos(a) * r, z = cz + Math.sin(a) * r;
    add(SPROP.TORCH, x, z, { scale: 1.6, color: COLOR.metal, collide: 0.4 });
    out.lights.push({ x, y: 2.4, z, color: [1.0, 0.52, 0.20], radius: 16, kind: 'fire' });
  }
  add(SPROP.ALTAR, cx, cz, { scale: 1, color: COLOR.oldStone, collide: 0 });
  // Everyone who came before. The bone field is the arena's whole warning, and
  // it costs less than one more pillar.
  litter(add, SPROP.BONES, cx, cz, 12, R * 0.15, R * 0.85, rng, { color: COLOR.bone, scale: 1.15 });
  litter(add, SPROP.DEBRIS, cx, cz, 16, R * 0.2, R * 0.95, rng, { color: COLOR.oldStone, scale: 1.2 });

  // The fog gate sits between the approach and the arena.
  const toCentre = Math.atan2(-cz, -cx);
  out.interacts.push({
    x: cx + Math.cos(toCentre) * (R * 0.92),
    z: cz + Math.sin(toCentre) * (R * 0.92),
    r: 3.2, kind: 'fog', poi,
  });
  out.spawns.push({ x: cx, z: cz, role: 'boss', boss: poi.boss });
}

function buildMiniSite(poi, add, out, rng, world) {
  const cx = poi.x, cz = poi.z;
  add(SPROP.CAMPFIRE, cx, cz, { scale: 1.1, color: COLOR.stone, collide: 0.6 });
  out.lights.push({ x: cx, y: 0.7, z: cz, color: [1.0, 0.5, 0.2], radius: 12, kind: 'fire' });
  for (let i = 0; i < 6; i++) {
    const a = (i / 6) * TAU + rng() * 0.5;
    const r = 8 + rng() * 4;
    add(SPROP.PILLAR, cx + Math.cos(a) * r, cz + Math.sin(a) * r, {
      scale: 0.9 + rng() * 0.6, color: COLOR.oldStone, collide: 0.55,
    });
  }
  out.spawns.push({ x: cx, z: cz, role: 'mini', mini: poi.boss });
  for (let i = 0; i < 2; i++) {
    const a = rng() * TAU;
    out.spawns.push({ x: cx + Math.cos(a) * 6, z: cz + Math.sin(a) * 6, role: 'camp' });
  }
  const a = rng() * TAU;
  const x = cx + Math.cos(a) * 9, z = cz + Math.sin(a) * 9;
  add(SPROP.CHEST, x, z, { color: COLOR.gold, collide: 0.7 });
  out.interacts.push({
    x, z, r: 1.6, kind: 'chest',
    poi: { id: `${poi.id}_chest`, kind: 'chest', tier: 2, opened: false },
  });
  litter(add, SPROP.BONES, cx, cz, 6, 2.5, 11, rng, { color: COLOR.bone });
  litter(add, SPROP.DEBRIS, cx, cz, 9, 2.0, 13, rng, { color: COLOR.oldStone });
}

function buildChestSite(poi, add, out, rng) {
  add(SPROP.CHEST, poi.x, poi.z, {
    color: poi.tier >= 2 ? COLOR.gold : COLOR.darkWood, collide: 0.7,
  });
  for (let i = 0; i < 3; i++) {
    const a = rng() * TAU, r = 1.5 + rng() * 2.5;
    add(SPROP.RUBBLE, poi.x + Math.cos(a) * r, poi.z + Math.sin(a) * r, {
      scale: 0.4 + rng() * 0.6, color: COLOR.oldStone,
    });
  }
  litter(add, SPROP.DEBRIS, poi.x, poi.z, 5, 1.2, 5.0, rng, { color: COLOR.oldStone, scale: 0.8 });
  out.interacts.push({ x: poi.x, z: poi.z, r: 1.7, kind: 'chest', poi });
}

function buildShrine(poi, add, out, rng) {
  add(SPROP.ALTAR, poi.x, poi.z, { scale: 1.1, color: COLOR.oldStone, collide: 0.9 });
  for (let i = 0; i < 4; i++) {
    const a = (i / 4) * TAU + 0.6;
    add(SPROP.PILLAR, poi.x + Math.cos(a) * 2.6, poi.z + Math.sin(a) * 2.6, {
      scale: 0.7, color: COLOR.oldStone, collide: 0.45,
    });
  }
  litter(add, SPROP.SCRUB, poi.x, poi.z, 8, 1.8, 7.0, rng, { color: COLOR.scrub });
  litter(add, SPROP.DEBRIS, poi.x, poi.z, 6, 1.5, 7.5, rng, { color: COLOR.oldStone, scale: 0.8 });
  out.lights.push({ x: poi.x, y: 1.4, z: poi.z, color: [0.55, 0.72, 1.0], radius: 8, kind: 'shrine' });
  out.interacts.push({ x: poi.x, z: poi.z, r: 2.4, kind: 'shrine', poi });
}

// ===========================================================================
//  Landmarks
//
//  Thirteen structures, no two alike, each tall enough to be picked out from the
//  far side of its region and sited (by worldgen's _placeLandmarks) on ground
//  that puts it against the sky. They are the answer to a specific complaint:
//  before them nothing in this world was tall enough to navigate by, so the
//  island was something you crossed by compass bearing rather than by looking
//  up and seeing where you were going.
//
//  They are built out of the same prop kit as everything else, which sounds
//  like a limitation and is actually the constraint that makes them cheap: the
//  renderer already has a batch for each of these meshes, so a forty-metre
//  colossus is instances in batches that were going to be drawn anyway, not a
//  new draw call. The kit's one real restriction is that game.js scales a prop
//  on all three axes at once, so a BARREL is always 1.39 times as tall as it is
//  wide and a CRATE is close to a cube. Anything with a different aspect ratio
//  is therefore a *stack* — which is also how the real thing was built, and
//  what lets the height be known exactly instead of estimated.
//
//  Cost control: the silhouette is made of props the renderer draws at any
//  range, and the ground-level detail — the chips, the fallen litter, the
//  scorch — is DEBRIS/BONES/SCRUB, which game.js drops past 150 m. A landmark
//  seen from four hundred metres away therefore pays for its outline only.
// ===========================================================================

const BARREL_W = 0.72, BARREL_H = 1.00;   // game.js: cylinder push, per scale
const CRATE_W = 0.80, CRATE_H = 0.75;     // game.js: box push, per scale

/**
 * A shaft of stacked drums, one per entry in `widths`. `opts.leanX/leanZ`
 * shift each course over the one below, which is the only lean available:
 * instances rotate about Y and nothing else.
 *
 * @returns {number} world Y of the top of the stack
 */
function taper(add, x, z, y0, widths, color, opts = {}) {
  let y = y0;
  for (let i = 0; i < widths.length; i++) {
    const s = widths[i] / BARREL_W;
    add(SPROP.BARREL, x + (opts.leanX || 0) * i, z + (opts.leanZ || 0) * i, {
      y, scale: s, yaw: opts.yaw || 0, color,
    });
    y += s * BARREL_H;
  }
  return y;
}

/** `taper` with every course the same width: a plain column of `n` drums. */
function drums(add, x, z, y0, width, n, color, opts = {}) {
  return taper(add, x, z, y0, new Array(n).fill(width), color, opts);
}

/** A course-built pier of `n` cyclopean blocks, each `width` metres across. */
function blocks(add, x, z, y0, width, n, color, opts = {}) {
  const s = width / CRATE_W;
  let y = y0;
  for (let i = 0; i < n; i++) {
    add(SPROP.CRATE, x + (opts.leanX || 0) * i, z + (opts.leanZ || 0) * i, {
      y, scale: s, yaw: opts.yaw || 0, color,
    });
    y += s * CRATE_H;
  }
  return y;
}

/** Block the player out of a solid mass without adding another prop for it. */
function solid(out, x, z, r) { out.colliders.push({ x, z, r }); }

/** A chest worth the climb. */
function reward(out, add, poi, x, z, y, tier) {
  add(SPROP.CHEST, x, z, { y, scale: 1, color: tier >= 2 ? COLOR.gold : COLOR.darkWood, collide: 0.7 });
  out.interacts.push({
    x, z, r: 1.8, kind: 'chest',
    poi: { id: `${poi.id}_chest`, kind: 'chest', tier, opened: false },
  });
}

/**
 * The twelve set-pieces, by variant id.
 *
 * `name` and `reading` are the place's identity and live here with its
 * geometry; where it stands is worldgen's business. `vertical` marks the ones
 * with ground you can climb onto and fight on — worldgen cuts the terrace and
 * the ramp that get you up there.
 */
export const SETPIECES = {
  gate: { name: '竜骨の門', reading: 'The Wyrmbone Gate', build: lmGate, vertical: false },
  henge: { name: '環の丘', reading: 'The Ring on the Hill', build: lmHenge, vertical: false },
  watchtower: { name: '梢の物見櫓', reading: 'The Canopy Watch', build: lmWatchtower, vertical: true },
  greatstump: { name: '朽ちた大樹の骸', reading: 'The Stone Bole', build: lmGreatStump, vertical: false },
  belltower: { name: '沈鐘の塔', reading: 'The Drowned Bell', build: lmBellTower, vertical: false },
  pilings: { name: '杭の森', reading: 'The Piling Forest', build: lmPilings, vertical: false },
  gatekeep: { name: '断ちの砦門', reading: 'The Severing Gate', build: lmGateKeep, vertical: true },
  stele: { name: '折れた誓約碑', reading: 'The Broken Oath', build: lmStele, vertical: false },
  colossus: { name: '見上げの巨像', reading: 'The Upward Colossus', build: lmColossus, vertical: false },
  span: { name: '落ちた吊り橋', reading: 'The Fallen Span', build: lmSpan, vertical: false },
  aqueduct: { name: '灰の水道橋', reading: 'The Ash Aqueduct', build: lmAqueduct, vertical: false },
  crown: { name: '砕けた王冠', reading: 'The Shattered Crown', build: lmCrown, vertical: false },
  beacon: { name: '頂の灯', reading: 'The Summit Cresset', build: lmBeacon, vertical: true },
};

function buildLandmark(poi, add, out, rng, world, ground) {
  const set = SETPIECES[poi.variant];
  if (set) set.build(poi, add, out, rng, world, ground);
}

// --- meadow ----------------------------------------------------------------

/**
 * A single colossal arch standing free on a rise, with its twin fallen beside
 * it. Chosen for the meadow because the meadow is the only region open enough
 * that you can see clean through an arch to the country on the other side, and
 * because a hole in a silhouette survives haze better than a solid mass does.
 */
function lmGate(poi, add, out, rng, world, ground) {
  const cx = poi.x, cz = poi.z, yaw = poi.yaw || 0;
  const ax = Math.cos(yaw), az = Math.sin(yaw);     // the arch spans along here
  const base = ground(cx, cz);
  const s = 5.4;                                    // 8.12 * 5.4 = 43.8 m
  add(SPROP.ARCH, cx, cz, { y: base, yaw, scale: s, color: COLOR.pale });
  // Only the piers are solid; the whole point is that you walk through it.
  for (const k of [-1, 1]) {
    solid(out, cx + ax * 2.575 * s * k, cz + az * 2.575 * s * k, 3.4);
  }
  // The twin that fell: its ring lies in order across the ground, which is what
  // tells you it was a pair rather than a single monument.
  const fx = cx - az * 26, fz = cz + ax * 26;
  for (let i = 0; i < 7; i++) {
    const t = (i - 3) * 5.6;
    add(SPROP.RUBBLE, fx + ax * t + (rng() - 0.5) * 2, fz + az * t + (rng() - 0.5) * 2, {
      scale: 3.4 + rng() * 2.2, color: COLOR.pale,
    });
  }
  blocks(add, fx + ax * 20, fz + az * 20, ground(fx + ax * 20, fz + az * 20), 4.6, 2, COLOR.pale, { yaw });
  solid(out, fx + ax * 20, fz + az * 20, 3.0);
  reward(out, add, poi, cx + ax * 9, cz + az * 9, ground(cx + ax * 9, cz + az * 9), 1);
  litter(add, SPROP.DEBRIS, cx, cz, 20, 6, 34, rng, { color: COLOR.pale, scale: 1.3 });
  litter(add, SPROP.SCRUB, cx, cz, 14, 8, 32, rng, { color: COLOR.scrub, scale: 1.1 });
}

/**
 * Ten uprights and what is left of their lintels, on the meadow's high knoll.
 * Wide rather than tall: a ring reads as a broken crown on the skyline from a
 * direction no single tower can give you, and it is the one landmark whose
 * inside is a place.
 */
function lmHenge(poi, add, out, rng, world, ground) {
  const cx = poi.x, cz = poi.z;
  const N = 10, R = 19;
  const tops = [];
  for (let i = 0; i < N; i++) {
    const a = (i / N) * TAU + (poi.yaw || 0);
    const x = cx + Math.cos(a) * R, z = cz + Math.sin(a) * R;
    // Two of the ten have gone over, so the ring is not a machined circle.
    const n = i === 2 ? 3 : i === 7 ? 4 : 7;
    tops.push(blocks(add, x, z, ground(x, z), 2.7, n, COLOR.pale, { yaw: a }));
    solid(out, x, z, 2.1);
  }
  // Lintels survive on five of the ten spans, laid as four stones each. None
  // of the five touches one of the two fallen uprights — a lintel with nothing
  // under one end is not a ruin, it is a bug.
  for (const i of [0, 3, 4, 5, 8]) {
    const a0 = (i / N) * TAU + (poi.yaw || 0), a1 = ((i + 1) / N) * TAU + (poi.yaw || 0);
    const y = Math.min(tops[i], tops[(i + 1) % N]);
    for (let k = 0; k < 4; k++) {
      const t = (k + 0.5) / 4;
      const a = lerp(a0, a1, t);
      blocks(add, cx + Math.cos(a) * R, cz + Math.sin(a) * R, y, 2.9, 1, COLOR.pale, { yaw: a });
    }
  }
  add(SPROP.ALTAR, cx, cz, { scale: 2.6, color: COLOR.oldStone });
  out.spawns.push({ x: cx + 8, z: cz, role: 'ruin' }, { x: cx - 7, z: cz + 5, role: 'ruin' });
  litter(add, SPROP.DEBRIS, cx, cz, 22, 4, 26, rng, { color: COLOR.pale, scale: 1.2 });
  litter(add, SPROP.SCRUB, cx, cz, 16, 3, 24, rng, { color: COLOR.scrub });
}

// --- wood ------------------------------------------------------------------

/**
 * A stone watchtower on the wood's high knoll — the one landmark in a region
 * whose canopy hides everything else, so it has to clear the trees by enough
 * that you find it from outside the wood entirely.
 */
function lmWatchtower(poi, add, out, rng, world, ground) {
  const cx = poi.x, cz = poi.z;
  const base = ground(cx, cz);
  add(SPROP.TOWER, cx, cz, { y: base, yaw: poi.yaw || 0, scale: 3.4, color: COLOR.stone });
  solid(out, cx, cz, 8.4);
  // Revetment: the terrace worldgen cut for this is faced with block so its
  // edge reads as built rather than as an odd flat place on a hill.
  for (let i = 0; i < 10; i++) {
    const a = (i / 10) * TAU;
    const x = cx + Math.cos(a) * 15, z = cz + Math.sin(a) * 15;
    blocks(add, x, z, ground(x, z) - 1.6, 4.2, 1, COLOR.oldStone, { yaw: a });
  }
  // The tower it replaced, down to two courses.
  const sx = cx + 21, sz = cz - 13;
  blocks(add, sx, sz, ground(sx, sz), 5.0, 2, COLOR.oldStone, { yaw: 0.7 });
  solid(out, sx, sz, 3.2);
  for (let i = 0; i < 5; i++) {
    const a = rng() * TAU, r = 12 + rng() * 12;
    add(SPROP.PILLAR, cx + Math.cos(a) * r, cz + Math.sin(a) * r, {
      scale: 1.1 + rng() * 0.8, color: COLOR.oldStone, collide: 0.6,
    });
  }
  for (let i = 0; i < 3; i++) {
    const a = rng() * TAU, r = 6 + rng() * 8;
    out.spawns.push({ x: cx + Math.cos(a) * r, z: cz + Math.sin(a) * r, role: 'ruin' });
  }
  // A light's y is its height above the ground under it, not a world height —
  // game.js adds heightAt(l.x, l.z) when it gathers them.
  out.lights.push({ x: cx, y: 30, z: cz, color: [1.0, 0.62, 0.26], radius: 18, kind: 'fire' });
  add(SPROP.TORCH, cx + 2.6, cz, { y: base + 28.4, scale: 1.6, color: COLOR.darkWood });
  // Clear of the shaft's own collider (8.4 m) and inside the revetment ring at
  // 15 m: a chest tucked against the wall is a chest you cannot open, because
  // the collision that stops you walking into the tower stops you reaching it.
  const rx = cx - 8.8, rz = cz + 5.9;
  reward(out, add, poi, rx, rz, ground(rx, rz), 2);
  litter(add, SPROP.DEBRIS, cx, cz, 18, 5, 22, rng, { color: COLOR.oldStone });
  litter(add, SPROP.DEADWOOD, cx, cz, 8, 8, 24, rng, { color: COLOR.darkWood });
}

/**
 * A petrified trunk nine metres through at the foot, snapped off at thirty-
 * eight. It is a tree shape at a scale no tree in the scatter can reach, which
 * is exactly why it works as a landmark inside a forest: everything around it
 * is the same shape and a tenth the size, so it reads as distance rather than
 * as another tree.
 */
function lmGreatStump(poi, add, out, rng, world, ground) {
  const cx = poi.x, cz = poi.z;
  const base = ground(cx, cz);
  taper(add, cx, cz, base, [9.0, 7.4, 6.0, 4.8], COLOR.petrified, { leanX: 0.35 });
  solid(out, cx, cz, 5.4);
  // Broken limbs, still standing where they sheared.
  const limbs = [[13.0, 3.4, 0.6], [21.0, 3.0, 2.7], [28.0, 2.6, 4.6]];
  for (const [ly, lr, la] of limbs) {
    taper(add, cx + Math.cos(la) * lr, cz + Math.sin(la) * lr, base + ly, [2.4, 1.7], COLOR.petrified);
  }
  // Root buttresses, the part of a giant tree you actually walk among.
  for (let i = 0; i < 7; i++) {
    const a = (i / 7) * TAU + rng() * 0.5;
    const r = 6.5 + rng() * 3.5;
    const x = cx + Math.cos(a) * r, z = cz + Math.sin(a) * r;
    add(SPROP.RUBBLE, x, z, { scale: 4.5 + rng() * 3.0, color: COLOR.petrified });
    solid(out, x, z, 2.6);
  }
  out.spawns.push({ x: cx + 9, z: cz + 4, role: 'ruin' }, { x: cx - 6, z: cz - 9, role: 'wild' });
  reward(out, add, poi, cx + 7.5, cz - 6.0, ground(cx + 7.5, cz - 6.0), 1);
  litter(add, SPROP.DEBRIS, cx, cz, 16, 6, 20, rng, { color: COLOR.petrified });
  litter(add, SPROP.SCRUB, cx, cz, 18, 5, 22, rng, { color: COLOR.scrub, scale: 1.2 });
}

// --- mire ------------------------------------------------------------------

/**
 * A bell-tower leaning out of the water with its bell still hung. Sited low on
 * purpose — it is the only landmark you look slightly *down* at from the
 * surrounding ground, and in a region with no relief to hide anything, a lean
 * is the silhouette cue that carries.
 */
function lmBellTower(poi, add, out, rng, world, ground) {
  const cx = poi.x, cz = poi.z, yaw = poi.yaw || 0;
  const base = ground(cx, cz) - 2.2;                 // the foot is under water
  const lean = 0.62;
  const lx = Math.cos(yaw) * lean, lz = Math.sin(yaw) * lean;
  const top = blocks(add, cx, cz, base, 6.2, 5, COLOR.oldStone, { yaw, leanX: lx, leanZ: lz });
  solid(out, cx + lx * 2, cz + lz * 2, 4.6);
  // Belfry: four corner posts, so the bell shows through from every side.
  const bx = cx + lx * 5, bz = cz + lz * 5;
  for (let i = 0; i < 4; i++) {
    const a = (i / 4) * TAU + Math.PI / 4 + yaw;
    drums(add, bx + Math.cos(a) * 2.7, bz + Math.sin(a) * 2.7, top, 1.5, 2, COLOR.oldStone);
  }
  const belfry = top + 2 * (1.5 / BARREL_W);
  add(SPROP.RUBBLE, bx, bz, { y: top + 0.6, scale: 4.2, color: COLOR.bronze });
  add(SPROP.TENT, bx, bz, { y: belfry, yaw, scale: 2.6, color: COLOR.peatWood });
  // Stepping stones out to it — the approach is half the place.
  for (let i = 0; i < 9; i++) {
    const t = i * 5.0 + 9;
    const x = cx - Math.cos(yaw) * t, z = cz - Math.sin(yaw) * t;
    add(SPROP.RUBBLE, x + (rng() - 0.5) * 2.4, z + (rng() - 0.5) * 2.4, {
      y: ground(x, z) - 0.4, scale: 2.0 + rng() * 1.4, color: COLOR.oldStone,
    });
  }
  out.spawns.push({ x: cx + 10, z: cz + 6, role: 'ruin' }, { x: cx - 9, z: cz - 7, role: 'ruin' });
  // Height above the ground under the belfry, not a world height: game.js adds
  // heightAt(l.x, l.z) back on when it gathers the lights.
  out.lights.push({
    x: bx, y: belfry - 1.0 - ground(bx, bz), z: bz,
    color: [0.55, 0.72, 1.0], radius: 12, kind: 'shrine',
  });
  reward(out, add, poi, cx + 6.5, cz + 5.5, ground(cx + 6.5, cz + 5.5), 2);
  litter(add, SPROP.DEBRIS, cx, cz, 14, 5, 20, rng, { color: COLOR.oldStone });
  litter(add, SPROP.BONES, cx, cz, 8, 6, 22, rng, { color: COLOR.bone });
}

/**
 * The piles of a harbour whose water moved. Thirteen of them plus a gantry,
 * all vertical, all different lengths — a thicket of verticals is a silhouette
 * nothing else in the world makes, and it reads from any direction because it
 * has no front.
 */
function lmPilings(poi, add, out, rng, world, ground) {
  const cx = poi.x, cz = poi.z;
  for (let i = 0; i < 10; i++) {
    const a = rng() * TAU, r = Math.sqrt(rng()) * 33;
    const x = cx + Math.cos(a) * r, z = cz + Math.sin(a) * r;
    const w = 1.2 + rng() * 0.8;
    drums(add, x, z, ground(x, z) - 1.2, w, 4 + Math.floor(rng() * 4), COLOR.peatWood);
    solid(out, x, z, w * 0.7);
  }
  // The gantry the piles were driven for: two masts and the beam between them.
  const gx = cx, gz = cz, yaw = poi.yaw || 0;
  const ux = Math.cos(yaw), uz = Math.sin(yaw);
  let deck = 0;
  for (const k of [-1, 1]) {
    const x = gx + ux * 4.6 * k, z = gz + uz * 4.6 * k;
    deck = drums(add, x, z, ground(x, z) - 1.2, 2.4, 8, COLOR.peatWood);
    solid(out, x, z, 1.8);
  }
  for (let i = 0; i < 5; i++) {
    const t = (i - 2) * 2.4;
    blocks(add, gx + ux * t, gz + uz * t, deck, 2.4, 1, COLOR.peatWood, { yaw });
  }
  out.spawns.push({ x: cx + 12, z: cz - 8, role: 'ruin' }, { x: cx - 11, z: cz + 9, role: 'wild' });
  reward(out, add, poi, cx + 4.0, cz + 8.0, ground(cx + 4.0, cz + 8.0), 1);
  litter(add, SPROP.DEADWOOD, cx, cz, 18, 4, 34, rng, { color: COLOR.peatWood, scale: 1.4 });
  litter(add, SPROP.BONES, cx, cz, 10, 5, 30, rng, { color: COLOR.bone });
}

// --- ridge -----------------------------------------------------------------

/**
 * A gate across the saddle: two keeps, a curtain either side and an arch you
 * walk through. Built on the one line of ground everything crossing the ridge
 * has to use, so it is both the thing you see from below and the thing you go
 * through when you get there.
 */
function lmGateKeep(poi, add, out, rng, world, ground) {
  const cx = poi.x, cz = poi.z, yaw = poi.yaw || 0;
  const ux = Math.cos(yaw), uz = Math.sin(yaw);     // along the wall
  add(SPROP.ARCH, cx, cz, { y: ground(cx, cz), yaw, scale: 3.2, color: COLOR.iron });
  for (const k of [-1, 1]) solid(out, cx + ux * 8.2 * k, cz + uz * 8.2 * k, 2.4);

  for (const k of [-1, 1]) {
    const tx = cx + ux * 14.5 * k, tz = cz + uz * 14.5 * k;
    add(SPROP.TOWER, tx, tz, { y: ground(tx, tz), yaw, scale: 2.4, color: COLOR.iron });
    solid(out, tx, tz, 5.9);
    // Curtain running out from each keep, dropping a bay where it was breached.
    for (let i = 0; i < 4; i++) {
      if (k > 0 && i === 2) continue;
      const d = 20.5 + i * 5.2;
      const x = cx + ux * d * k, z = cz + uz * d * k;
      blocks(add, x, z, ground(x, z), 5.2, i < 2 ? 3 : 2, COLOR.iron, { yaw });
      solid(out, x, z, 3.0);
    }
  }
  add(SPROP.BANNER, cx + ux * 6 - uz * 4, cz + uz * 6 + ux * 4, { color: COLOR.banner });
  add(SPROP.BANNER, cx - ux * 6 - uz * 4, cz - uz * 6 + ux * 4, { color: COLOR.banner });
  for (let i = 0; i < 4; i++) {
    const a = rng() * TAU, r = 7 + rng() * 9;
    out.spawns.push({ x: cx + Math.cos(a) * r, z: cz + Math.sin(a) * r, role: 'camp' });
  }
  for (const k of [-1, 1]) {
    const x = cx - uz * 5.5 * k, z = cz + ux * 5.5 * k;
    add(SPROP.TORCH, x, z, { scale: 1.8, color: COLOR.metal });
    out.lights.push({ x, y: 3.6, z, color: [1.0, 0.58, 0.24], radius: 14, kind: 'fire' });
  }
  reward(out, add, poi, cx - uz * 9, cz + ux * 9, ground(cx - uz * 9, cz + ux * 9), 2);
  litter(add, SPROP.DEBRIS, cx, cz, 24, 6, 34, rng, { color: COLOR.iron, scale: 1.2 });
  litter(add, SPROP.BONES, cx, cz, 10, 5, 26, rng, { color: COLOR.bone });
}

/**
 * One stone, split. Two slabs thirty-three metres high leaning apart with a
 * slot of sky between them — the narrowest silhouette of the twelve, and the
 * only one whose shape changes completely as you walk around it.
 */
function lmStele(poi, add, out, rng, world, ground) {
  const cx = poi.x, cz = poi.z, yaw = poi.yaw || 0;
  const px = -Math.sin(yaw), pz = Math.cos(yaw);
  const base = ground(cx, cz);
  for (const k of [-1, 1]) {
    const x = cx + px * 4.6 * k, z = cz + pz * 4.6 * k;
    blocks(add, x, z, base, 7.0, 5, COLOR.basalt, {
      yaw, leanX: px * 0.42 * k, leanZ: pz * 0.42 * k,
    });
    solid(out, x, z, 4.4);
  }
  // The piece that came off, lying where it landed.
  for (let i = 0; i < 5; i++) {
    const t = 12 + i * 5.5;
    const x = cx + Math.cos(yaw) * t + (rng() - 0.5) * 3;
    const z = cz + Math.sin(yaw) * t + (rng() - 0.5) * 3;
    add(SPROP.RUBBLE, x, z, { scale: 5.0 + rng() * 4.0, color: COLOR.basalt });
    solid(out, x, z, 3.4);
  }
  add(SPROP.ALTAR, cx, cz, { yaw, scale: 3.0, color: COLOR.basalt });
  out.lights.push({ x: cx, y: 2.4, z: cz, color: [0.55, 0.72, 1.0], radius: 11, kind: 'shrine' });
  out.spawns.push({ x: cx + px * 11, z: cz + pz * 11, role: 'ruin' });
  reward(out, add, poi, cx - Math.cos(yaw) * 8, cz - Math.sin(yaw) * 8,
    ground(cx - Math.cos(yaw) * 8, cz - Math.sin(yaw) * 8), 2);
  litter(add, SPROP.DEBRIS, cx, cz, 20, 5, 24, rng, { color: COLOR.basalt, scale: 1.3 });
}

// --- crag ------------------------------------------------------------------

/**
 * Forty-nine metres of seated figure with its head on the ground in front of
 * it. The tallest thing on the island, in the region that has the height to
 * put under it — and the head at the foot is what gives the rest of it scale,
 * because until you stand next to something you know the size of, a big
 * silhouette is just a near one.
 */
function lmColossus(poi, add, out, rng, world, ground) {
  const cx = poi.x, cz = poi.z, yaw = poi.yaw || 0;
  const fx = Math.cos(yaw), fz = Math.sin(yaw);     // the way it faces
  const px = -fz, pz = fx;
  const base = ground(cx, cz);

  add(SPROP.ALTAR, cx, cz, { y: base, yaw, scale: 7.0, color: COLOR.basalt });
  const plinth = base + 0.85 * 7.0;
  solid(out, cx, cz, 7.6);

  let legTop = plinth;
  for (const k of [-1, 1]) {
    legTop = drums(add, cx + px * 3.6 * k, cz + pz * 3.6 * k, plinth, 3.4, 4, COLOR.pale);
  }
  const torsoTop = blocks(add, cx, cz, legTop, 9.5, 2, COLOR.pale, { yaw });
  for (const k of [-1, 1]) {
    drums(add, cx + px * 5.2 * k, cz + pz * 5.2 * k, torsoTop, 4.6, 1, COLOR.pale);
  }
  drums(add, cx, cz, torsoTop, 3.2, 1, COLOR.pale);   // the neck it broke at

  // The head, eighteen metres out, face up.
  const hx = cx + fx * 18, hz = cz + fz * 18;
  add(SPROP.RUBBLE, hx, hz, { y: ground(hx, hz), scale: 9.0, color: COLOR.pale });
  solid(out, hx, hz, 6.4);
  for (let i = 0; i < 3; i++) {
    const a = rng() * TAU;
    blocks(add, hx + Math.cos(a) * 8, hz + Math.sin(a) * 8,
      ground(hx + Math.cos(a) * 8, hz + Math.sin(a) * 8), 4.4, 1, COLOR.pale, { yaw: a });
  }
  out.spawns.push({ x: hx + 6, z: hz + 4, role: 'ruin' }, { x: cx + px * 12, z: cz + pz * 12, role: 'wild' });
  reward(out, add, poi, hx - fx * 7, hz - fz * 7, ground(hx - fx * 7, hz - fz * 7), 2);
  litter(add, SPROP.DEBRIS, cx, cz, 26, 8, 32, rng, { color: COLOR.pale, scale: 1.4 });
  litter(add, SPROP.BONES, hx, hz, 10, 3, 14, rng, { color: COLOR.bone });
}

/**
 * Two pylons on opposite lips of a chasm with the deck between them gone, the
 * cables still hanging off both heads.
 *
 * A pair reads differently from anything single: from far off you see two
 * verticals at a fixed spacing and the eye insists on joining them, so the gap
 * where the deck used to be is the thing you actually notice. It is also the
 * only landmark that tells you something you need — that the ground between
 * those two points does not go through.
 */
function lmSpan(poi, add, out, rng, world, ground) {
  const cx = poi.x, cz = poi.z, yaw = poi.yaw || 0;
  const ux = Math.cos(yaw), uz = Math.sin(yaw);
  for (const k of [-1, 1]) {
    const x = cx + ux * 29 * k, z = cz + uz * 29 * k;
    const head = blocks(add, x, z, ground(x, z), 4.6, 7, COLOR.oldStone, { yaw });
    solid(out, x, z, 3.2);
    // The cable, still made fast, sagging into the gap it no longer crosses —
    // but never below the ground under it, since the chasm is terrain and its
    // floor is wherever the crag put it rather than wherever the curve wants.
    for (let i = 1; i <= 6; i++) {
      const t = i * 2.9;
      const bx = x - ux * t * k, bz = z - uz * t * k;
      const y = Math.max(head - i * i * 0.85, ground(bx, bz) - 0.8);
      blocks(add, bx, bz, y, 1.6, 1, COLOR.iron, { yaw });
    }
    // Anchor block, back from the lip.
    const ax = x + ux * 9 * k, az = z + uz * 9 * k;
    blocks(add, ax, az, ground(ax, az), 3.4, 1, COLOR.oldStone, { yaw });
    solid(out, ax, az, 2.4);
  }
  for (let i = 0; i < 8; i++) {
    const a = rng() * TAU, r = 8 + rng() * 22;
    add(SPROP.RUBBLE, cx + Math.cos(a) * r, cz + Math.sin(a) * r, {
      scale: 2.2 + rng() * 3.0, color: COLOR.oldStone,
    });
  }
  out.spawns.push({ x: cx + ux * 34, z: cz + uz * 34, role: 'ruin' },
    { x: cx - ux * 34, z: cz - uz * 34, role: 'wild' });
  reward(out, add, poi, cx + ux * 33 - uz * 6, cz + uz * 33 + ux * 6,
    ground(cx + ux * 33 - uz * 6, cz + uz * 33 + ux * 6), 2);
  litter(add, SPROP.DEBRIS, cx, cz, 20, 6, 34, rng, { color: COLOR.oldStone, scale: 1.2 });
}

// --- waste -----------------------------------------------------------------

/**
 * Seven bays of arcade, the stumps of two more and the rubble of the rest:
 * two hundred metres of it lying across the ash.
 *
 * This is the one landmark that is a *line* rather than a point, and that is
 * the whole design: a point you either see or you do not, but a line crosses
 * your route, disappears behind the dunes as you drop into an interdune pan
 * and comes back when you climb out. Worldgen turns it onto the bearing with
 * the deepest ground under the middle of it, which is what an aqueduct is for.
 *
 * The channel is level and the ground is not — that is the whole difference
 * between an aqueduct and a wall — so every bay is set at one deck height and
 * the drop underneath is made up in courses of pier. The bays over the low
 * ground therefore stand on twenty metres of masonry and the one on the high
 * point stands on none, which is what tells you the land dips.
 */
function lmAqueduct(poi, add, out, rng, world, ground) {
  const cx = poi.x, cz = poi.z, yaw = poi.yaw || 0;
  const ux = Math.cos(yaw), uz = Math.sin(yaw);
  const s = 3.6;
  const pitch = 6.2 * s;                              // pier face to pier face
  const BAYS = 7;
  const at = (i) => {
    const t = (i - (BAYS - 1) / 2) * pitch;
    return [cx + ux * t, cz + uz * t];
  };
  // The springing line is set by the highest ground the arcade crosses, so no
  // bay is ever buried and every other one has piers to make up the fall.
  let deck = -Infinity;
  for (let i = 0; i < BAYS; i++) {
    const [x, z] = at(i);
    if (ground(x, z) > deck) deck = ground(x, z);
  }
  for (let i = 0; i < BAYS; i++) {
    const [x, z] = at(i);
    add(SPROP.ARCH, x, z, { y: deck, yaw, scale: s, color: COLOR.ash });
    for (const k of [-1, 1]) {
      const px = x + ux * 2.575 * s * k, pz = z + uz * 2.575 * s * k;
      solid(out, px, pz, 2.6);
      const g = ground(px, pz);
      // Courses sized to land exactly on the springing line: a pier that
      // overshoots pokes up beside the arch it is supposed to carry. Under
      // 1.7 m of fall there is no pier at all — the arch's own plinth is
      // deeper than that.
      const gap = deck - g;
      if (gap < 1.7) continue;
      const n = Math.max(1, Math.round(gap / 5.25));
      blocks(add, px, pz, g, clamp(gap / (n * 0.9375), 1.7, 8.0), n, COLOR.ash, { yaw });
    }
  }
  // Where it comes down: two bare piers, then rubble, then nothing.
  const end = ((BAYS - 1) / 2) * pitch;
  for (let i = 1; i <= 2; i++) {
    const t = end + i * pitch;
    const x = cx + ux * t, z = cz + uz * t;
    blocks(add, x, z, ground(x, z), 3.8, 5 - i, COLOR.ash, { yaw });
    solid(out, x, z, 2.6);
  }
  for (let i = 0; i < 12; i++) {
    const t = end + pitch * (2.4 + rng() * 2.2);
    const x = cx + ux * t + (rng() - 0.5) * 16, z = cz + uz * t + (rng() - 0.5) * 16;
    add(SPROP.RUBBLE, x, z, { scale: 2.6 + rng() * 3.4, color: COLOR.ash });
  }
  out.spawns.push(
    { x: cx + ux * pitch, z: cz + uz * pitch, role: 'ruin' },
    { x: cx - ux * pitch * 2, z: cz - uz * pitch * 2, role: 'ruin' },
    { x: cx - uz * 9, z: cz + ux * 9, role: 'wild' });
  reward(out, add, poi, cx - uz * 7, cz + ux * 7, ground(cx - uz * 7, cz + ux * 7), 2);
  litter(add, SPROP.DEBRIS, cx, cz, 26, 6, 44, rng, { color: COLOR.ash, scale: 1.3 });
  litter(add, SPROP.BONES, cx, cz, 12, 8, 40, rng, { color: COLOR.bone });
}

/**
 * Nine shards of black stone canted outward round a crater, still burning at
 * the centre. The only landmark that emits light, which is what makes it the
 * one you can steer by after dark — everything else in the waste goes to
 * silhouette at dusk and this does not.
 */
function lmCrown(poi, add, out, rng, world, ground) {
  const cx = poi.x, cz = poi.z;
  const N = 9, R = 23;
  for (let i = 0; i < N; i++) {
    const a = (i / N) * TAU + (poi.yaw || 0);
    const ox = Math.cos(a), oz = Math.sin(a);
    const x = cx + ox * R, z = cz + oz * R;
    // Broken to different lengths: an even ring reads as a fence.
    const w = [6.0, 4.8, 3.8, 2.8].slice(0, 2 + (i % 3));
    taper(add, x, z, ground(x, z), w, COLOR.basalt, { yaw: a, leanX: ox * 1.0, leanZ: oz * 1.0 });
    solid(out, x, z, 3.6);
  }
  add(SPROP.TORCH, cx, cz, { y: ground(cx, cz), scale: 4.0, color: COLOR.basalt });
  // Above the ground, not above sea level — see the note in lmWatchtower.
  out.lights.push({ x: cx, y: 8.5, z: cz, color: [1.0, 0.44, 0.14], radius: 26, kind: 'fire' });
  for (let i = 0; i < 6; i++) {
    const a = rng() * TAU, r = 5 + rng() * 8;
    add(SPROP.RUBBLE, cx + Math.cos(a) * r, cz + Math.sin(a) * r, {
      scale: 2.0 + rng() * 2.4, color: COLOR.basalt,
    });
  }
  for (let i = 0; i < 3; i++) {
    const a = rng() * TAU;
    out.spawns.push({ x: cx + Math.cos(a) * 14, z: cz + Math.sin(a) * 14, role: 'ruin' });
  }
  reward(out, add, poi, cx + 6, cz - 6, ground(cx + 6, cz - 6), 2);
  litter(add, SPROP.DEBRIS, cx, cz, 24, 4, 30, rng, { color: COLOR.basalt, scale: 1.2 });
  litter(add, SPROP.BONES, cx, cz, 14, 6, 28, rng, { color: COLOR.bone });
}

// --- peak ------------------------------------------------------------------

/**
 * A cresset on a stepped platform at the top of the world, lit. Worldgen cuts
 * the platform as real terrain with a ramp, so this is the one landmark you
 * climb *onto* rather than merely up to — and from the top of it you can see
 * most of the other eleven.
 */
function lmBeacon(poi, add, out, rng, world, ground) {
  const cx = poi.x, cz = poi.z;
  const base = ground(cx, cz);
  // Four legs and the bowl they carry.
  let legTop = base;
  for (let i = 0; i < 4; i++) {
    const a = (i / 4) * TAU + Math.PI / 4 + (poi.yaw || 0);
    legTop = drums(add, cx + Math.cos(a) * 4.2, cz + Math.sin(a) * 4.2, base, 3.0, 4, COLOR.iron);
    solid(out, cx + Math.cos(a) * 4.2, cz + Math.sin(a) * 4.2, 2.2);
  }
  add(SPROP.RUBBLE, cx, cz, { y: legTop, scale: 10.0, color: COLOR.iron });
  add(SPROP.TORCH, cx, cz, { y: legTop, scale: 9.0, color: COLOR.iron });
  // The cresset burns at legTop + 4 in world terms; the light is stored as the
  // height above the summit under it, which is what game.js expects.
  out.lights.push({
    x: cx, y: legTop + 4 - base, z: cz, color: [1.0, 0.66, 0.30], radius: 30, kind: 'fire',
  });

  // The stair edges, marked so you can find the ramp in a whiteout.
  for (let i = 0; i < 8; i++) {
    const a = (i / 8) * TAU;
    const x = cx + Math.cos(a) * 16, z = cz + Math.sin(a) * 16;
    add(SPROP.PILLAR, x, z, { scale: 1.7, color: COLOR.pale, collide: 0.8 });
    if (i % 2 === 0) {
      add(SPROP.TORCH, cx + Math.cos(a) * 12, cz + Math.sin(a) * 12, { scale: 2.6, color: COLOR.iron });
      out.lights.push({
        x: cx + Math.cos(a) * 12, y: 5.6, z: cz + Math.sin(a) * 12,
        color: [1.0, 0.58, 0.24], radius: 13, kind: 'fire',
      });
    }
  }
  for (let i = 0; i < 4; i++) {
    const a = (i / 4) * TAU + 0.9;
    add(SPROP.BANNER, cx + Math.cos(a) * 9, cz + Math.sin(a) * 9, { color: COLOR.banner });
  }
  add(SPROP.ALTAR, cx + 7.5, cz, { scale: 2.2, color: COLOR.pale });
  for (let i = 0; i < 3; i++) {
    const a = rng() * TAU;
    out.spawns.push({ x: cx + Math.cos(a) * 11, z: cz + Math.sin(a) * 11, role: 'ruin' });
  }
  reward(out, add, poi, cx - 8.5, cz + 3.0, ground(cx - 8.5, cz + 3.0), 2);
  litter(add, SPROP.DEBRIS, cx, cz, 20, 6, 22, rng, { color: COLOR.pale });
  litter(add, SPROP.BONES, cx, cz, 8, 8, 20, rng, { color: COLOR.bone });
}

// ---------------------------------------------------------------------------
//  Enemy tables per region and role
// ---------------------------------------------------------------------------

export const REGION_ENEMIES = {
  meadow: {
    camp: ['bandit', 'bandit', 'bandit_archer'],
    ruin: ['husk', 'husk_archer'],
    wild: ['ashwolf', 'bandit', 'husk'],
  },
  wood: {
    camp: ['bandit', 'bandit_archer', 'ashwolf'],
    ruin: ['kodama', 'husk'],
    wild: ['ashwolf', 'kodama', 'husk'],
  },
  mire: {
    camp: ['bandit', 'mireleech'],
    ruin: ['mireleech', 'husk_archer'],
    wild: ['mireleech', 'husk', 'kodama'],
  },
  ridge: {
    camp: ['spearman', 'sentinel'],
    ruin: ['sentinel', 'husk_archer'],
    wild: ['spearman', 'sentinel', 'ashwolf'],
  },
  crag: {
    camp: ['sentinel', 'stoneeater'],
    ruin: ['stoneeater', 'sentinel'],
    wild: ['stoneeater', 'frostwolf', 'sentinel'],
  },
  waste: {
    camp: ['wraith', 'cinderhound'],
    ruin: ['wraith', 'husk'],
    wild: ['cinderhound', 'wraith', 'stoneeater'],
  },
  peak: {
    camp: ['frostwolf', 'oathknight'],
    ruin: ['oathknight', 'sentinel'],
    wild: ['frostwolf', 'oathknight', 'stoneeater'],
  },
};

export function pickEnemy(regionId, role, rng) {
  const table = REGION_ENEMIES[regionId] || REGION_ENEMIES.meadow;
  const list = table[role] || table.wild;
  return list[Math.floor(rng() * list.length) % list.length];
}
