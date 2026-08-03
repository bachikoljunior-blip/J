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
    case 'merchant': case 'smith': break;   // the NPC is the structure
    default: break;
  }
  return out;
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
