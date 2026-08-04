// ============================================================================
//  enemies.js — enemy archetypes.
//
//  Every archetype is data: silhouette, palette, stat block, moveset with
//  ranges and cooldowns, AI temperament, and a drop table. The Enemy class
//  itself is thin — all the character comes from the numbers and from which
//  attacks are legal at which distance.
// ============================================================================

import { Actor, STATE, FACTION, defaultPalette } from './actor.js';
import { MAT } from './rig.js';
import { ATTACKS, stage, pulse } from './anim.js';
import { EnemyBrain, AI_STATE } from './ai.js';
import { getItem } from './items.js';
import { Projectile, AreaEffect } from './combat.js';
import { BLEND } from '../gfx/particles.js';
import { hash2 } from '../core/rng.js';
import { clamp, lerp, saturate, TAU } from '../core/math.js';

// ---------------------------------------------------------------------------
//  Extra attacks used only by enemies. Registered into the shared table so
//  Actor.startAttack can find them by id.
// ---------------------------------------------------------------------------

const noop = () => ({ lunge: 0 });

export const ENEMY_ATTACKS = {
  // --- beasts (poses come from quadrupedAnimate) ---------------------------
  bite: { dur: 0.78, hit: [0.30, 0.52], stam: 12, dmg: 1.0, poise: 14, motion: 3.6, pose: noop },
  bite_fast: { dur: 0.58, hit: [0.24, 0.42], stam: 10, dmg: 0.8, poise: 10, motion: 4.2, pose: noop },
  pounce: { dur: 1.15, hit: [0.34, 0.62], stam: 22, dmg: 1.5, poise: 30, motion: 13.5, pose: noop },

  // --- humanoid variants ---------------------------------------------------
  husk_swing: { dur: 1.05, hit: [0.44, 0.66], stam: 18, dmg: 1.2, poise: 22, motion: 1.6, pose: (r, u) => ATTACKS.sword_l1.pose(r, u) },
  husk_double: { dur: 1.55, hit: [0.26, 0.40], stam: 24, dmg: 1.0, poise: 18, motion: 1.4, pose: (r, u) => (u < 0.5 ? ATTACKS.sword_l1.pose(r, u * 2) : ATTACKS.sword_l2.pose(r, (u - 0.5) * 2)), hit2: [0.72, 0.88] },
  sentinel_smash: { dur: 1.55, hit: [0.52, 0.72], stam: 34, dmg: 2.1, poise: 60, motion: 2.4, pose: (r, u) => ATTACKS.great_h1.pose(r, u) },
  sentinel_sweep: { dur: 1.20, hit: [0.38, 0.62], stam: 28, dmg: 1.6, poise: 42, motion: 1.6, pose: (r, u) => ATTACKS.great_l1.pose(r, u) },
  brute_slam: { dur: 1.65, hit: [0.54, 0.70], stam: 36, dmg: 2.4, poise: 80, motion: 3.0, aoe: { radius: 3.2, at: 0.60 }, pose: (r, u) => ATTACKS.great_h1.pose(r, u) },
  wraith_slash: { dur: 0.72, hit: [0.28, 0.48], stam: 14, dmg: 1.1, poise: 16, motion: 5.0, pose: (r, u) => ATTACKS.sword_l2.pose(r, u) },
  wraith_burst: { dur: 1.30, hit: [0.5, 0.52], stam: 26, dmg: 1.0, poise: 30, motion: 0, aoe: { radius: 3.8, at: 0.58, element: 'fire' }, pose: (r, u) => ATTACKS.cast.pose(r, u) },
  archer_shot: { dur: 1.35, hit: [0.5, 0.52], stam: 16, dmg: 1.0, poise: 10, motion: 0, ranged: 'arrow', pose: (r, u) => ATTACKS.bow_shot.pose(r, u) },
  caster_bolt: { dur: 1.45, hit: [0.5, 0.52], stam: 16, dmg: 1.0, poise: 12, motion: 0, ranged: 'bolt', pose: (r, u) => ATTACKS.cast.pose(r, u) },

  // --- drake ---------------------------------------------------------------
  drake_bite: { dur: 1.05, hit: [0.36, 0.58], stam: 20, dmg: 1.5, poise: 45, motion: 5.5, pose: noop },
  drake_tail: { dur: 1.30, hit: [0.34, 0.62], stam: 24, dmg: 1.4, poise: 55, motion: 0, sweep: true, pose: noop },
  drake_breath: { dur: 2.10, hit: [0.5, 0.52], stam: 30, dmg: 1.0, poise: 40, motion: 0, ranged: 'breath', pose: noop },
  drake_stomp: { dur: 1.45, hit: [0.48, 0.62], stam: 26, dmg: 1.8, poise: 70, motion: 1.5, aoe: { radius: 4.5, at: 0.54 }, pose: noop },

  // --- shield wall ---------------------------------------------------------
  // A bash that barely damages but shreds poise: the answer to a player who
  // has decided to stand still and trade.
  wall_bash: { dur: 0.92, hit: [0.28, 0.44], stam: 20, dmg: 0.85, poise: 58, motion: 3.0, pose: (r, u) => ATTACKS.kick.pose(r, u) },
  wall_charge: { dur: 1.55, hit: [0.24, 0.60], stam: 30, dmg: 1.35, poise: 72, motion: 11.0, pose: (r, u) => ATTACKS.spear_h1.pose(r, u) },
  wall_brace: { dur: 2.20, hit: [0.50, 0.52], stam: 6, dmg: 0, poise: 8, motion: 0, special: 'brace', pose: noop },

  // --- long reach ----------------------------------------------------------
  reach_poke: { dur: 0.94, hit: [0.30, 0.50], stam: 16, dmg: 1.05, poise: 16, motion: 0.8, pose: (r, u) => ATTACKS.spear_l1.pose(r, u) },
  reach_sweep: { dur: 1.35, hit: [0.36, 0.62], stam: 24, dmg: 1.25, poise: 34, motion: 0, pose: (r, u) => ATTACKS.spear_l3.pose(r, u) },
  reach_stomp: { dur: 1.50, hit: [0.50, 0.66], stam: 26, dmg: 1.45, poise: 55, motion: 0.5, aoe: { radius: 2.9, at: 0.56 }, pose: (r, u) => ATTACKS.great_h1.pose(r, u) },

  // --- ambush --------------------------------------------------------------
  ambush_burst: { dur: 1.00, hit: [0.24, 0.46], stam: 18, dmg: 1.9, poise: 60, motion: 6.5, pose: (r, u) => ATTACKS.axe_l2.pose(r, u) },
  ambush_sink: { dur: 1.60, hit: [0.50, 0.52], stam: 14, dmg: 0, poise: 20, motion: 0, special: 'burrow', pose: noop },

  // --- flyer ---------------------------------------------------------------
  crow_rake: { dur: 0.82, hit: [0.28, 0.50], stam: 14, dmg: 1.0, poise: 18, motion: 4.6, pose: noop },
  crow_dive: { dur: 1.35, hit: [0.32, 0.58], stam: 24, dmg: 1.7, poise: 42, motion: 15.0, pose: noop },
  crow_quill: { dur: 1.20, hit: [0.50, 0.52], stam: 16, dmg: 1.0, poise: 10, motion: 0, ranged: 'shard', pose: noop },

  // --- support -------------------------------------------------------------
  rally_toll: { dur: 2.30, hit: [0.50, 0.52], stam: 20, dmg: 0, poise: 30, motion: 0, special: 'rally', pose: (r, u) => ATTACKS.cast.pose(r, u) },
  rite_raise: { dur: 2.60, hit: [0.50, 0.52], stam: 26, dmg: 0, poise: 30, motion: 0, special: 'raise', pose: (r, u) => ATTACKS.cast.pose(r, u) },
  bell_shock: { dur: 1.50, hit: [0.50, 0.52], stam: 22, dmg: 1.0, poise: 45, motion: 0, aoe: { radius: 4.6, at: 0.55 }, pose: (r, u) => ATTACKS.great_l1.pose(r, u) },

  // --- ground denial -------------------------------------------------------
  hex_rune: { dur: 1.90, hit: [0.50, 0.52], stam: 22, dmg: 1.0, poise: 30, motion: 0, special: 'rune', pose: (r, u) => ATTACKS.cast.pose(r, u) },

  // --- grappler ------------------------------------------------------------
  chain_pull: { dur: 1.55, hit: [0.50, 0.52], stam: 20, dmg: 0.5, poise: 25, motion: 0, special: 'pull', pose: (r, u) => ATTACKS.spear_h1.pose(r, u) },
  chain_grab: { dur: 1.45, hit: [0.34, 0.50], stam: 26, dmg: 2.6, poise: 999, motion: 4.0, unblockable: true, pose: (r, u) => ATTACKS.axe_h1.pose(r, u) },

  // --- burning aura --------------------------------------------------------
  aura_flare: { dur: 1.70, hit: [0.50, 0.52], stam: 20, dmg: 1.0, poise: 40, motion: 0, special: 'aura', pose: (r, u) => ATTACKS.cast.pose(r, u) },

  // --- duellist ------------------------------------------------------------
  // The stance does nothing on its own. It exists so that swinging into it is
  // the mistake, and waiting it out is the answer.
  duel_stance: { dur: 1.30, hit: [0.50, 0.52], stam: 10, dmg: 0, poise: 14, motion: 0, special: 'stance', pose: noop },
  duel_punish: { dur: 0.66, hit: [0.20, 0.38], stam: 18, dmg: 1.7, poise: 26, motion: 4.4, pose: (r, u) => ATTACKS.sword_h2.pose(r, u) },

  // --- swarm ---------------------------------------------------------------
  swarm_nip: { dur: 0.46, hit: [0.18, 0.32], stam: 8, dmg: 0.55, poise: 5, motion: 3.0, pose: (r, u) => ATTACKS.dagger_l1.pose(r, u) },
  swarm_leap: { dur: 0.85, hit: [0.26, 0.46], stam: 14, dmg: 0.9, poise: 12, motion: 9.0, pose: (r, u) => ATTACKS.dagger_h2.pose(r, u) },

  // --- misc weapon variants ------------------------------------------------
  beast_maul: { dur: 1.10, hit: [0.30, 0.56], stam: 18, dmg: 1.25, poise: 30, motion: 3.2, pose: noop },
  flail_spin: { dur: 1.25, hit: [0.24, 0.66], stam: 30, dmg: 1.35, poise: 40, motion: 1.6, pose: (r, u) => ATTACKS.axe_h2.pose(r, u) },
  stone_counter: { dur: 0.88, hit: [0.22, 0.42], stam: 22, dmg: 2.0, poise: 70, motion: 2.6, pose: (r, u) => ATTACKS.great_l2.pose(r, u) },
  harpoon_cast: { dur: 1.45, hit: [0.50, 0.52], stam: 20, dmg: 1.0, poise: 14, motion: 0, ranged: 'harpoon', pose: (r, u) => ATTACKS.spear_h2.pose(r, u) },
  venom_spit: { dur: 1.30, hit: [0.50, 0.52], stam: 16, dmg: 1.0, poise: 10, motion: 0, ranged: 'spit', pose: (r, u) => ATTACKS.cast.pose(r, u) },
  flame_lob: { dur: 1.55, hit: [0.50, 0.52], stam: 20, dmg: 1.0, poise: 16, motion: 0, ranged: 'flame', pose: (r, u) => ATTACKS.cast.pose(r, u) },
};

Object.assign(ATTACKS, ENEMY_ATTACKS);

// ---------------------------------------------------------------------------
//  Combat kits
//
//  A kit is a moveset plus the spacing behaviour that goes with it: how far
//  the enemy wants to stand, how long it circles before committing, whether it
//  blocks or rolls. Kits are the reusable half of an encounter — the same
//  "shield wall" kit reads completely differently on a guardsman and on a
//  three-metre stone warden, but it teaches the player the same lesson, so
//  learning one enemy pays off against the next.
// ---------------------------------------------------------------------------

export const KITS = {
  brawler: {
    preferredRange: 2.2, aggression: 0.68, patience: 0.95, sightRange: 20,
    canBlock: true, canDodge: true, blockChance: 0.28, dodgeChance: 0.20,
    attacks: [
      { id: 'sword_l1', range: [0, 2.7], weight: 1.0, cooldown: 1.0, recovery: 0.45 },
      { id: 'sword_l2', range: [0, 2.7], weight: 1.0, cooldown: 1.0, recovery: 0.45 },
      { id: 'sword_l3', range: [0, 2.9], weight: 0.6, cooldown: 2.2, recovery: 0.6 },
      { id: 'sword_h1', range: [1.0, 3.1], weight: 0.45, cooldown: 3.4, recovery: 0.9 },
      { id: 'kick', range: [0, 2.0], weight: 0.25, cooldown: 4.5, recovery: 0.6 },
    ],
  },

  wall: {
    // Wants to be close and stationary. Everything it does is designed to make
    // standing in front of it worse than going around it.
    preferredRange: 2.4, aggression: 0.42, patience: 1.6, sightRange: 20,
    canBlock: true, blockChance: 0.78, strafeSpeedMul: 0.45,
    attacks: [
      { id: 'wall_brace', range: [0, 7.0], weight: 0.9, cooldown: 7.5, recovery: 0.4 },
      { id: 'wall_bash', range: [0, 2.6], weight: 1.0, cooldown: 3.0, recovery: 0.7 },
      { id: 'spear_l1', range: [1.4, 3.8], weight: 1.0, cooldown: 1.2, recovery: 0.5 },
      { id: 'spear_l2', range: [1.4, 3.8], weight: 0.8, cooldown: 1.2, recovery: 0.5 },
      { id: 'wall_charge', range: [5.0, 13], weight: 0.9, cooldown: 7.0, recovery: 1.2 },
    ],
  },

  reach: {
    // Holds a distance most weapons cannot answer. Closing is the whole fight.
    preferredRange: 5.4, aggression: 0.34, patience: 1.5, sightRange: 26,
    strafeSpeedMul: 0.85,
    attacks: [
      { id: 'reach_poke', range: [3.0, 6.6], weight: 1.0, cooldown: 1.3, recovery: 0.6 },
      { id: 'reach_sweep', range: [2.4, 6.0], weight: 0.8, cooldown: 3.0, recovery: 0.9 },
      { id: 'reach_stomp', range: [0, 3.0], weight: 1.2, cooldown: 4.0, recovery: 1.1 },
      { id: 'spear_h1', range: [4.0, 9.0], weight: 0.7, cooldown: 5.0, recovery: 1.0 },
    ],
  },

  skirmisher: {
    preferredRange: 2.6, aggression: 0.72, patience: 0.55, sightRange: 24,
    canDodge: true, dodgeChance: 0.48, strafeSpeedMul: 1.15,
    attacks: [
      { id: 'dagger_l1', range: [0, 2.3], weight: 1.0, cooldown: 0.7, recovery: 0.3 },
      { id: 'dagger_l2', range: [0, 2.3], weight: 1.0, cooldown: 0.7, recovery: 0.3 },
      { id: 'dagger_h1', range: [1.5, 4.4], weight: 0.8, cooldown: 2.4, recovery: 0.6 },
      { id: 'swarm_leap', range: [4.0, 9.0], weight: 0.7, cooldown: 4.0, recovery: 0.8 },
      { id: 'kick', range: [0, 2.0], weight: 0.4, cooldown: 3.5, recovery: 0.5 },
    ],
  },

  sniper: {
    ranged: true, rangedMin: 7, rangedIdeal: 16, preferredRange: 16,
    aggression: 0.22, patience: 1.6, sightRange: 32, strafeSpeedMul: 0.6,
    canDodge: true, dodgeChance: 0.3,
    attacks: [
      { id: 'archer_shot', range: [6, 32], weight: 1.0, cooldown: 2.6, recovery: 0.8 },
      { id: 'dagger_l1', range: [0, 2.2], weight: 0.8, cooldown: 1.0, recovery: 0.5 },
      { id: 'dagger_l2', range: [0, 2.2], weight: 0.8, cooldown: 1.0, recovery: 0.5 },
      { id: 'kick', range: [0, 2.1], weight: 0.6, cooldown: 3.0, recovery: 0.5 },
    ],
  },

  caster: {
    // Denies the ground you are standing on rather than the ground it is on.
    ranged: true, rangedMin: 6, rangedIdeal: 13, preferredRange: 13,
    aggression: 0.30, patience: 1.3, sightRange: 28, strafeSpeedMul: 0.85,
    attacks: [
      { id: 'caster_bolt', range: [4, 22], weight: 1.0, cooldown: 2.8, recovery: 0.8 },
      { id: 'hex_rune', range: [5, 24], weight: 0.9, cooldown: 7.0, recovery: 1.2 },
      { id: 'wraith_burst', range: [0, 4.0], weight: 0.8, cooldown: 7.5, recovery: 1.2 },
      { id: 'kick', range: [0, 2.2], weight: 0.5, cooldown: 4.0, recovery: 0.6 },
    ],
  },

  juggernaut: {
    preferredRange: 3.4, aggression: 0.62, patience: 0.9, sightRange: 22,
    strafeSpeedMul: 0.4,
    attacks: [
      { id: 'brute_slam', range: [0, 4.4], weight: 1.0, cooldown: 4.2, recovery: 1.3 },
      { id: 'sentinel_sweep', range: [0, 4.2], weight: 0.9, cooldown: 2.6, recovery: 0.9 },
      { id: 'stone_counter', range: [0, 3.4], weight: 0.7, cooldown: 3.4, recovery: 0.8 },
      { id: 'sentinel_smash', range: [0.8, 3.6], weight: 0.6, cooldown: 5.5, recovery: 1.2 },
    ],
  },

  duel: {
    // Reads the player rather than out-statting them: stance, then punish.
    preferredRange: 2.5, aggression: 0.55, patience: 1.2, sightRange: 24,
    canDodge: true, canParry: true, dodgeChance: 0.42,
    attacks: [
      { id: 'duel_stance', range: [0, 4.0], weight: 1.1, cooldown: 5.0, recovery: 0.3 },
      { id: 'duel_punish', range: [0, 3.6], weight: 1.0, cooldown: 1.6, recovery: 0.5 },
      { id: 'sword_l3', range: [0, 3.0], weight: 0.7, cooldown: 2.4, recovery: 0.7 },
      { id: 'sword_h2', range: [2.2, 6.0], weight: 0.6, cooldown: 3.6, recovery: 0.8 },
      { id: 'kick', range: [0, 2.1], weight: 0.35, cooldown: 4.5, recovery: 0.5 },
    ],
  },

  support: {
    // Never wants to be the one you are fighting. That is the problem.
    ranged: true, rangedMin: 9, rangedIdeal: 17, preferredRange: 17,
    aggression: 0.14, patience: 2.0, sightRange: 30, strafeSpeedMul: 0.7,
    groupRadius: 30,
    attacks: [
      { id: 'rally_toll', range: [0, 30], weight: 1.4, cooldown: 11.0, recovery: 1.4 },
      { id: 'caster_bolt', range: [6, 22], weight: 0.5, cooldown: 3.4, recovery: 0.9 },
      { id: 'bell_shock', range: [0, 4.6], weight: 1.0, cooldown: 5.0, recovery: 1.0 },
      { id: 'hex_rune', range: [6, 24], weight: 0.6, cooldown: 10.0, recovery: 1.2 },
    ],
  },

  swarm: {
    preferredRange: 1.6, aggression: 0.95, patience: 0.25, sightRange: 22,
    groupRadius: 26, strafeSpeedMul: 1.2,
    attacks: [
      { id: 'swarm_nip', range: [0, 1.9], weight: 1.0, cooldown: 0.6, recovery: 0.25 },
      { id: 'swarm_leap', range: [3.0, 7.5], weight: 0.9, cooldown: 3.0, recovery: 0.6 },
      { id: 'dagger_l2', range: [0, 2.1], weight: 0.8, cooldown: 0.8, recovery: 0.3 },
      { id: 'kick', range: [0, 1.9], weight: 0.4, cooldown: 4.0, recovery: 0.5 },
    ],
  },

  beast_pack: {
    preferredRange: 2.0, aggression: 0.88, patience: 0.4, sightRange: 26,
    canDodge: true, dodgeChance: 0.24, groupRadius: 22,
    attacks: [
      { id: 'bite', range: [0, 2.4], weight: 1.0, cooldown: 1.2, recovery: 0.4 },
      { id: 'bite_fast', range: [0, 2.2], weight: 0.8, cooldown: 0.9, recovery: 0.3 },
      { id: 'pounce', range: [3.5, 9.0], weight: 0.9, cooldown: 4.0, recovery: 0.8 },
      { id: 'beast_maul', range: [0, 2.8], weight: 0.7, cooldown: 3.2, recovery: 0.8 },
    ],
  },

  ambush: {
    // Sits in the ground until you are past it, then costs you a flask.
    preferredRange: 2.0, aggression: 0.85, patience: 0.3, sightRange: 11,
    sightAngle: 3.2, hearRange: 9, canDodge: false, wanderRadius: 0,
    attacks: [
      { id: 'ambush_burst', range: [0, 6.5], weight: 1.2, cooldown: 5.0, recovery: 0.9 },
      { id: 'bite', range: [0, 2.4], weight: 1.0, cooldown: 1.2, recovery: 0.45 },
      { id: 'ambush_sink', range: [4.0, 20], weight: 0.9, cooldown: 9.0, recovery: 1.0 },
      { id: 'bite_fast', range: [0, 2.2], weight: 0.8, cooldown: 0.9, recovery: 0.3 },
    ],
  },
};

/**
 * Merge an archetype's kit with its own overrides. `ai.attacks`, when present,
 * replaces the kit's list outright rather than merging — half a moveset is
 * never what an author means.
 */
export function resolveAI(arch) {
  const kit = arch.kit ? KITS[arch.kit] : null;
  if (!kit) return arch.ai || {};
  const merged = { ...kit, ...(arch.ai || {}) };
  if (arch.ai && arch.ai.addAttacks) {
    merged.attacks = (arch.ai.attacks || kit.attacks).concat(arch.ai.addAttacks);
    delete merged.addAttacks;
  }
  return merged;
}

// ---------------------------------------------------------------------------
//  Affixes
//
//  The third axis. A silhouette says what it looks like, a kit says how it
//  fights, and an affix says what it is carrying — fire, poison, plate, a
//  banner. Affixes multiply the roster without multiplying the authoring:
//  twenty-nine archetypes and eight affixes is a lot of distinct fights, and
//  the player can read all of them from the tint and the name.
// ---------------------------------------------------------------------------

export const AFFIXES = {
  ember: {
    prefix: '燼の', hpMul: 1.0, dmgMul: 1.12, emissive: 0.18,
    palette: { ACCENT: [0.92, 0.42, 0.16], HAIR: [0.52, 0.24, 0.12] },
    resist: { fire: 0.5 },
    addAttacks: [{ id: 'flame_lob', range: [5, 20], weight: 0.8, cooldown: 6.0, recovery: 1.0 }],
    drops: [['resin_fire', 0.18, 1], ['mat_ashsalt', 0.20, 1]],
    soulsMul: 1.4,
  },
  hoar: {
    prefix: '霜の', hpMul: 1.22, dmgMul: 1.05, speedMul: 0.92,
    palette: { CLOTH: [0.58, 0.66, 0.74], ACCENT: [0.74, 0.86, 0.94] },
    status: { type: 'frost', build: 26 }, resist: { magic: 0.3 },
    addAttacks: [{ id: 'crow_quill', range: [5, 22], weight: 0.7, cooldown: 5.5, recovery: 1.0 }],
    drops: [['warm_stone', 0.22, 1]],
    soulsMul: 1.45,
  },
  venom: {
    prefix: '毒の', hpMul: 1.05, dmgMul: 1.0,
    palette: { CLOTH: [0.30, 0.42, 0.24], ACCENT: [0.56, 0.76, 0.32] },
    status: { type: 'poison', build: 30 }, resist: { poison: 0.6 },
    addAttacks: [{ id: 'venom_spit', range: [5, 18], weight: 0.8, cooldown: 5.0, recovery: 0.9 }],
    drops: [['antidote', 0.30, 1]],
    soulsMul: 1.35,
  },
  plated: {
    // Poise, not health. It will not flinch, so trading with it never works.
    prefix: '鉄殻の', hpMul: 1.35, dmgMul: 1.0, speedMul: 0.86,
    defenseAdd: 16, poiseMul: 2.4,
    palette: { ARMOR: [0.56, 0.56, 0.60], LEATHER: [0.30, 0.28, 0.26] },
    ai: { canBlock: true, blockChance: 0.55 },
    drops: [['mat_chunk', 0.20, 1]],
    soulsMul: 1.6,
  },
  frenzied: {
    prefix: '狂える', hpMul: 0.72, dmgMul: 1.30, speedMul: 1.32,
    poiseMul: 0.55, emissive: 0.08,
    palette: { SKIN: [0.66, 0.38, 0.34], ACCENT: [0.78, 0.22, 0.18] },
    ai: { aggression: 1.0, patience: 0.2, dodgeChance: 0.05 },
    drops: [['mat_fang', 0.30, 1]],
    soulsMul: 1.5,
  },
  ambusher: {
    // Not stronger. Just never where you left it.
    prefix: '忍びの', hpMul: 0.85, dmgMul: 1.24, speedMul: 1.10,
    palette: { CLOTH: [0.16, 0.16, 0.18], DARK: [0.10, 0.10, 0.12], ACCENT: [0.24, 0.26, 0.26] },
    ai: { sightRange: 13, sightAngle: 3.0, canDodge: true, dodgeChance: 0.5, patience: 0.4 },
    addAttacks: [{ id: 'ambush_sink', range: [5, 22], weight: 0.8, cooldown: 10.0, recovery: 1.0 }],
    drops: [['dagger_venom', 0.04, 1]],
    soulsMul: 1.5,
  },
  warded: {
    prefix: '呪詛の', hpMul: 1.10, dmgMul: 1.06, emissive: 0.14,
    resist: { magic: 0.55, holy: 0.25 },
    palette: { CLOTH: [0.24, 0.22, 0.36], ACCENT: [0.56, 0.46, 0.86] },
    addAttacks: [
      { id: 'caster_bolt', range: [5, 22], weight: 0.8, cooldown: 4.0, recovery: 0.9 },
      { id: 'hex_rune', range: [6, 24], weight: 0.6, cooldown: 9.0, recovery: 1.2 },
    ],
    drops: [['flask_fp', 0.06, 1], ['mat_core', 0.06, 1]],
    soulsMul: 1.7,
  },
  bannered: {
    // Alone it is unremarkable. It is never alone.
    prefix: '旗持ちの', hpMul: 1.15, dmgMul: 1.0,
    palette: { ACCENT: [0.72, 0.18, 0.16], CLOTH: [0.34, 0.20, 0.18] },
    ai: { groupRadius: 34, aggression: 0.5 },
    addAttacks: [{ id: 'rally_toll', range: [0, 26], weight: 1.0, cooldown: 13.0, recovery: 1.4 }],
    drops: [['mat_bellbronze', 0.15, 1]],
    soulsMul: 1.8,
  },
};

const AFFIX_KEYS = Object.keys(AFFIXES);

/**
 * Deterministic affix roll for a spawn. Position and world seed only, so the
 * same encounter carries the same affix every time the world is loaded — an
 * affix the player can learn to recognise on the approach is a mechanic; one
 * that is re-rolled per visit is noise.
 */
export function rollAffix(arch, x, z, level, seed) {
  const legal = arch.affixes === undefined ? AFFIX_KEYS : arch.affixes;
  if (!legal || !legal.length) return null;
  const gx = Math.round(x * 4), gz = Math.round(z * 4);
  const chance = clamp(0.10 + level * 0.011, 0.10, 0.40);
  if (hash2(gx, gz, (seed ^ 0x5eed0001) | 0) > chance) return null;
  const pick = hash2(gz, gx, (seed ^ 0x0a771000) | 0);
  return legal[Math.floor(pick * legal.length) % legal.length];
}

// ---------------------------------------------------------------------------
//  Archetypes
// ---------------------------------------------------------------------------

const pal = (over) => {
  const p = defaultPalette();
  for (const k in over) p[MAT[k]] = over[k];
  return p;
};

export const ARCHETYPES = {
  bandit: {
    build: 'stocky',
    name: '野盗', rig: 'humanoid', scale: 1.0,
    hp: 190, damage: 34, defense: 10, poise: 22, souls: 120,
    moveSpeed: 3.0, runSpeed: 5.4, turnRate: 8, mass: 1.0,
    weapon: 'sword_knight', offhand: 'shield_wood',
    palette: { SKIN: [0.66, 0.50, 0.40], CLOTH: [0.34, 0.26, 0.20], ARMOR: [0.36, 0.30, 0.24], LEATHER: [0.28, 0.22, 0.17], HAIR: [0.16, 0.12, 0.09], ACCENT: [0.45, 0.20, 0.16] },
    ai: {
      preferredRange: 2.1, aggression: 0.62, patience: 1.1,
      canBlock: true, canDodge: true, blockChance: 0.30, dodgeChance: 0.18,
      sightRange: 20, attacks: [
        { id: 'sword_l1', range: [0, 2.7], weight: 1.0, cooldown: 1.1, recovery: 0.5 },
        { id: 'sword_l2', range: [0, 2.7], weight: 0.9, cooldown: 1.1, recovery: 0.5 },
        { id: 'sword_h1', range: [1.2, 3.1], weight: 0.4, cooldown: 3.2, recovery: 0.9 },
        { id: 'sword_run', range: [3.0, 6.5], weight: 0.6, cooldown: 3.6, recovery: 0.8 },
        { id: 'kick', range: [0, 2.0], weight: 0.25, cooldown: 4.0, recovery: 0.7 },
      ],
    },
    drops: [['mat_hide', 0.35, 1], ['flask_hp', 0.03, 1], ['throwing_knife', 0.18, 3], ['sword_knight', 0.04, 1]],
  },

  bandit_archer: {
    build: 'lithe',
    name: '野盗弓兵', rig: 'humanoid', scale: 0.98,
    hp: 140, damage: 30, defense: 7, poise: 14, souls: 130,
    moveSpeed: 3.2, runSpeed: 5.6, turnRate: 9, mass: 0.9,
    weapon: 'bow_short', offhand: null,
    palette: { SKIN: [0.68, 0.52, 0.42], CLOTH: [0.28, 0.30, 0.22], ARMOR: [0.30, 0.28, 0.22], LEATHER: [0.26, 0.22, 0.16], HAIR: [0.22, 0.16, 0.10] },
    ai: {
      ranged: true, rangedMin: 6, rangedIdeal: 13, preferredRange: 13,
      aggression: 0.30, patience: 1.4, canDodge: true, dodgeChance: 0.30,
      sightRange: 30, strafeSpeedMul: 0.8,
      attacks: [
        { id: 'archer_shot', range: [5, 30], weight: 1.0, cooldown: 2.4, recovery: 0.7 },
        { id: 'dagger_l1', range: [0, 2.2], weight: 0.8, cooldown: 1.0, recovery: 0.5 },
        { id: 'dagger_l2', range: [0, 2.2], weight: 0.8, cooldown: 1.0, recovery: 0.5 },
        { id: 'kick', range: [0, 2.0], weight: 0.6, cooldown: 3.2, recovery: 0.5 },
      ],
    },
    drops: [['mat_hide', 0.30, 1], ['bow_short', 0.05, 1], ['throwing_knife', 0.25, 4]],
  },

  husk: {
    build: 'gaunt',
    name: '亡骸兵', rig: 'humanoid', scale: 1.02,
    helm: true,
    hp: 240, damage: 40, defense: 14, poise: 34, souls: 180,
    moveSpeed: 2.1, runSpeed: 3.4, turnRate: 4.5, mass: 1.2,
    weapon: 'great_iron', offhand: null,
    palette: { SKIN: [0.46, 0.46, 0.42], CLOTH: [0.24, 0.24, 0.22], ARMOR: [0.32, 0.32, 0.30], LEATHER: [0.22, 0.20, 0.18], HAIR: [0.12, 0.12, 0.11], DARK: [0.10, 0.10, 0.10] },
    ai: {
      preferredRange: 2.6, aggression: 0.85, patience: 0.5,
      canBlock: false, canDodge: false, sightRange: 16, sightAngle: 2.4,
      attacks: [
        { id: 'husk_swing', range: [0, 3.3], weight: 1.0, cooldown: 1.6, recovery: 0.7 },
        { id: 'husk_double', range: [0, 3.1], weight: 0.55, cooldown: 4.5, recovery: 1.0 },
        { id: 'great_l2', range: [0, 3.4], weight: 0.6, cooldown: 2.4, recovery: 0.8 },
      ],
    },
    drops: [['mat_shard', 0.20, 1], ['great_iron', 0.03, 1], ['mat_bone', 0.30, 1]],
  },

  husk_archer: {
    build: 'gaunt',
    name: '亡骸弓兵', rig: 'humanoid', scale: 1.0,
    helm: true,
    hp: 160, damage: 36, defense: 10, poise: 16, souls: 165,
    moveSpeed: 2.0, runSpeed: 3.2, turnRate: 5, mass: 1.0,
    weapon: 'bow_long', offhand: null,
    palette: { SKIN: [0.46, 0.46, 0.42], CLOTH: [0.22, 0.24, 0.24], ARMOR: [0.28, 0.30, 0.30], HAIR: [0.12, 0.12, 0.11] },
    ai: {
      ranged: true, rangedMin: 8, rangedIdeal: 18, preferredRange: 18,
      aggression: 0.2, patience: 1.8, sightRange: 34, strafeSpeedMul: 0.5,
      attacks: [
        { id: 'archer_shot', range: [6, 34], weight: 1.0, cooldown: 3.0, recovery: 0.9 },
        { id: 'husk_swing', range: [0, 3.0], weight: 0.9, cooldown: 1.8, recovery: 0.8 },
        { id: 'kick', range: [0, 2.1], weight: 0.4, cooldown: 4.0, recovery: 0.6 },
      ],
    },
    drops: [['mat_shard', 0.18, 1], ['bow_long', 0.03, 1], ['mat_bone', 0.28, 1]],
  },

  ashwolf: {
    name: '灰狼', rig: 'quadruped', scale: 1.0,
    hp: 130, damage: 30, defense: 6, poise: 12, souls: 95,
    moveSpeed: 4.4, runSpeed: 8.2, turnRate: 11, mass: 0.75,
    height: 1.15, radius: 0.42,
    palette: { CLOTH: [0.32, 0.30, 0.28], DARK: [0.16, 0.15, 0.14] },
    ai: {
      preferredRange: 1.9, aggression: 0.9, patience: 0.35,
      canDodge: true, dodgeChance: 0.22, sightRange: 26, groupRadius: 22,
      strafeSpeedMul: 1.0,
      attacks: [
        { id: 'bite', range: [0, 2.4], weight: 1.0, cooldown: 1.2, recovery: 0.4 },
        { id: 'bite_fast', range: [0, 2.2], weight: 0.8, cooldown: 0.9, recovery: 0.3 },
        { id: 'pounce', range: [3.5, 9.0], weight: 0.9, cooldown: 4.0, recovery: 0.8 },
      ],
    },
    drops: [['mat_fang', 0.40, 1], ['mat_hide', 0.30, 1]],
  },

  frostwolf: {
    name: '霜狼', rig: 'quadruped', scale: 1.15,
    hp: 260, damage: 52, defense: 14, poise: 22, souls: 320,
    moveSpeed: 4.6, runSpeed: 8.6, turnRate: 11, mass: 0.9,
    height: 1.3, radius: 0.48,
    palette: { CLOTH: [0.62, 0.68, 0.74], DARK: [0.32, 0.38, 0.46] },
    status: { type: 'frost', build: 22 },
    ai: {
      preferredRange: 2.1, aggression: 0.85, patience: 0.4,
      canDodge: true, dodgeChance: 0.25, sightRange: 28, groupRadius: 22,
      attacks: [
        { id: 'bite', range: [0, 2.6], weight: 1.0, cooldown: 1.2, recovery: 0.45 },
        { id: 'bite_fast', range: [0, 2.4], weight: 0.8, cooldown: 0.9, recovery: 0.3 },
        { id: 'pounce', range: [4, 11], weight: 1.0, cooldown: 3.6, recovery: 0.8 },
        { id: 'beast_maul', range: [0, 2.8], weight: 0.7, cooldown: 3.4, recovery: 0.9 },
      ],
    },
    drops: [['mat_fang', 0.5, 2], ['mat_chunk', 0.12, 1], ['mat_scale', 0.15, 1]],
  },

  kodama: {
    name: '木霊', rig: 'humanoid', scale: 0.82,
    hp: 120, damage: 34, defense: 8, poise: 10, souls: 140,
    moveSpeed: 2.8, runSpeed: 4.4, turnRate: 7, mass: 0.7,
    weapon: 'staff_apprentice', offhand: null,
    palette: { SKIN: [0.42, 0.52, 0.34], CLOTH: [0.24, 0.34, 0.22], ARMOR: [0.28, 0.36, 0.24], LEATHER: [0.22, 0.28, 0.18], HAIR: [0.30, 0.42, 0.24], ACCENT: [0.52, 0.62, 0.30] },
    emissive: 0.12,
    ai: {
      ranged: true, rangedMin: 5, rangedIdeal: 11, preferredRange: 11,
      aggression: 0.35, patience: 1.2, sightRange: 24, strafeSpeedMul: 0.9,
      attacks: [
        { id: 'caster_bolt', range: [4, 22], weight: 1.0, cooldown: 2.6, recovery: 0.8 },
        { id: 'hex_rune', range: [5, 20], weight: 0.7, cooldown: 9.0, recovery: 1.2 },
        { id: 'sword_l1', range: [0, 2.2], weight: 0.5, cooldown: 1.4, recovery: 0.6 },
        { id: 'kick', range: [0, 2.0], weight: 0.4, cooldown: 4.0, recovery: 0.6 },
      ],
    },
    drops: [['mat_shard', 0.25, 1], ['flask_fp', 0.04, 1], ['sp_bolt', 0.02, 1]],
  },

  mireleech: {
    name: '沼のヒル', rig: 'quadruped', scale: 0.95,
    hp: 180, damage: 32, defense: 9, poise: 30, souls: 150,
    moveSpeed: 2.2, runSpeed: 3.6, turnRate: 5, mass: 1.1,
    height: 0.95, radius: 0.5,
    palette: { CLOTH: [0.30, 0.34, 0.22], DARK: [0.20, 0.24, 0.15] },
    status: { type: 'poison', build: 30 },
    ai: {
      preferredRange: 1.8, aggression: 0.7, patience: 0.6, sightRange: 18,
      attacks: [
        { id: 'bite', range: [0, 2.2], weight: 1.0, cooldown: 1.5, recovery: 0.6 },
        { id: 'ambush_burst', range: [3.0, 7.0], weight: 0.8, cooldown: 6.0, recovery: 1.0 },
        { id: 'venom_spit', range: [5.0, 16], weight: 0.9, cooldown: 4.5, recovery: 1.0 },
      ],
    },
    drops: [['antidote', 0.3, 1], ['mat_hide', 0.2, 1]],
  },

  sentinel: {
    build: 'brute',
    name: '鉄兵', rig: 'humanoid', scale: 1.14,
    helm: true,
    hp: 420, damage: 62, defense: 26, poise: 62, souls: 480,
    moveSpeed: 2.3, runSpeed: 4.0, turnRate: 4.5, mass: 1.8,
    weapon: 'great_iron', offhand: 'shield_kite',
    palette: { SKIN: [0.34, 0.34, 0.36], CLOTH: [0.26, 0.28, 0.32], ARMOR: [0.48, 0.48, 0.52], LEATHER: [0.28, 0.26, 0.24], ACCENT: [0.62, 0.52, 0.22] },
    ai: {
      preferredRange: 2.8, aggression: 0.55, patience: 1.2,
      canBlock: true, blockChance: 0.5, sightRange: 20,
      attacks: [
        { id: 'sentinel_sweep', range: [0, 3.6], weight: 1.0, cooldown: 2.2, recovery: 0.8 },
        { id: 'sentinel_smash', range: [0.8, 3.4], weight: 0.7, cooldown: 5.0, recovery: 1.2 },
        { id: 'great_l2', range: [0, 3.5], weight: 0.7, cooldown: 2.0, recovery: 0.7 },
        { id: 'kick', range: [0, 2.2], weight: 0.3, cooldown: 5.0, recovery: 0.6 },
      ],
    },
    drops: [['mat_chunk', 0.25, 1], ['shield_kite', 0.05, 1], ['great_iron', 0.04, 1]],
  },

  stoneeater: {
    build: 'hulk',
    name: '石喰い', rig: 'humanoid', scale: 1.55,
    hp: 680, damage: 84, defense: 30, poise: 95, souls: 900,
    moveSpeed: 2.0, runSpeed: 3.8, turnRate: 3.2, mass: 3.0,
    weapon: 'axe_stone', offhand: null,
    palette: { SKIN: [0.42, 0.40, 0.38], CLOTH: [0.30, 0.28, 0.26], ARMOR: [0.36, 0.34, 0.32], LEATHER: [0.26, 0.24, 0.22], HAIR: [0.20, 0.19, 0.18] },
    ai: {
      preferredRange: 3.4, aggression: 0.7, patience: 0.8, sightRange: 22,
      attacks: [
        { id: 'brute_slam', range: [0, 4.4], weight: 1.0, cooldown: 4.0, recovery: 1.3 },
        { id: 'sentinel_sweep', range: [0, 4.2], weight: 0.9, cooldown: 2.6, recovery: 0.9 },
        { id: 'great_h2', range: [0, 4.0], weight: 0.5, cooldown: 6.0, recovery: 1.4 },
      ],
    },
    drops: [['mat_core', 0.20, 1], ['axe_stone', 0.05, 1]],
  },

  wraith: {
    build: 'gaunt',
    name: '燼の亡霊', rig: 'humanoid', scale: 1.05,
    hp: 380, damage: 74, defense: 20, poise: 26, souls: 720,
    moveSpeed: 3.6, runSpeed: 6.4, turnRate: 10, mass: 0.8,
    weapon: 'sword_ember', offhand: null,
    palette: { SKIN: [0.30, 0.22, 0.24], CLOTH: [0.24, 0.18, 0.18], ARMOR: [0.28, 0.20, 0.18], LEATHER: [0.22, 0.16, 0.15], HAIR: [0.42, 0.20, 0.12], ACCENT: [0.82, 0.34, 0.14] },
    emissive: 0.16,
    ai: {
      preferredRange: 2.3, aggression: 0.8, patience: 0.55,
      canDodge: true, dodgeChance: 0.35, sightRange: 24,
      attacks: [
        { id: 'wraith_slash', range: [0, 3.0], weight: 1.0, cooldown: 1.0, recovery: 0.4 },
        { id: 'sword_h2', range: [2.0, 5.5], weight: 0.7, cooldown: 3.2, recovery: 0.8 },
        { id: 'wraith_burst', range: [0, 4.0], weight: 0.5, cooldown: 6.5, recovery: 1.2 },
      ],
    },
    drops: [['mat_core', 0.18, 1], ['ember_shard', 0.3, 1], ['sword_ember', 0.04, 1]],
  },

  cinderhound: {
    name: '燼犬', rig: 'quadruped', scale: 1.05,
    hp: 300, damage: 62, defense: 16, poise: 20, souls: 420,
    moveSpeed: 4.8, runSpeed: 8.8, turnRate: 12, mass: 0.85,
    height: 1.2, radius: 0.45,
    palette: { CLOTH: [0.34, 0.20, 0.16], DARK: [0.52, 0.22, 0.10] },
    emissive: 0.2,
    ai: {
      preferredRange: 2.0, aggression: 0.95, patience: 0.3,
      canDodge: true, dodgeChance: 0.2, sightRange: 28, groupRadius: 20,
      attacks: [
        { id: 'bite', range: [0, 2.5], weight: 1.0, cooldown: 1.0, recovery: 0.35 },
        { id: 'beast_maul', range: [0, 2.8], weight: 0.8, cooldown: 3.0, recovery: 0.8 },
        { id: 'pounce', range: [4, 12], weight: 1.0, cooldown: 3.2, recovery: 0.7 },
        { id: 'flame_lob', range: [8, 20], weight: 0.6, cooldown: 8.0, recovery: 1.2 },
      ],
    },
    drops: [['mat_fang', 0.5, 2], ['mat_core', 0.08, 1]],
  },

  oathknight: {
    build: 'brute',
    name: '誓約騎士', rig: 'humanoid', scale: 1.06,
    helm: true,
    hp: 520, damage: 78, defense: 30, poise: 55, souls: 860,
    moveSpeed: 3.0, runSpeed: 5.6, turnRate: 8, mass: 1.5,
    weapon: 'sword_oath', offhand: 'shield_oath',
    palette: { SKIN: [0.62, 0.48, 0.40], CLOTH: [0.30, 0.20, 0.20], ARMOR: [0.46, 0.44, 0.42], LEATHER: [0.28, 0.24, 0.20], ACCENT: [0.68, 0.56, 0.22] },
    ai: {
      preferredRange: 2.4, aggression: 0.7, patience: 0.85,
      canBlock: true, canDodge: true, canParry: true,
      blockChance: 0.45, dodgeChance: 0.3, sightRange: 24,
      attacks: [
        { id: 'sword_l1', range: [0, 2.9], weight: 1.0, cooldown: 0.9, recovery: 0.4 },
        { id: 'sword_l2', range: [0, 2.9], weight: 1.0, cooldown: 0.9, recovery: 0.4 },
        { id: 'sword_l3', range: [0, 3.0], weight: 0.7, cooldown: 2.0, recovery: 0.7 },
        { id: 'sword_h1', range: [1.0, 3.2], weight: 0.5, cooldown: 4.0, recovery: 1.0 },
        { id: 'sword_h2', range: [2.2, 6.0], weight: 0.7, cooldown: 3.4, recovery: 0.8 },
        { id: 'kick', range: [0, 2.1], weight: 0.3, cooldown: 5.0, recovery: 0.6 },
      ],
    },
    drops: [['mat_chunk', 0.3, 1], ['sword_oath', 0.05, 1], ['shield_oath', 0.03, 1]],
  },

  spearman: {
    build: 'lithe',
    name: '衛兵', rig: 'humanoid', scale: 1.0,
    helm: true,
    hp: 260, damage: 44, defense: 16, poise: 28, souls: 260,
    moveSpeed: 2.9, runSpeed: 5.0, turnRate: 7, mass: 1.1,
    weapon: 'spear_knight', offhand: 'shield_wood',
    palette: { SKIN: [0.64, 0.50, 0.40], CLOTH: [0.26, 0.28, 0.34], ARMOR: [0.42, 0.42, 0.46], LEATHER: [0.28, 0.24, 0.20] },
    ai: {
      preferredRange: 3.2, aggression: 0.5, patience: 1.2,
      canBlock: true, blockChance: 0.4, sightRange: 22,
      attacks: [
        { id: 'spear_l1', range: [1.5, 4.0], weight: 1.0, cooldown: 1.0, recovery: 0.45 },
        { id: 'spear_l2', range: [1.5, 4.0], weight: 1.0, cooldown: 1.0, recovery: 0.45 },
        { id: 'spear_h1', range: [2.5, 6.5], weight: 0.6, cooldown: 3.4, recovery: 0.9 },
        { id: 'spear_l3', range: [0, 3.0], weight: 0.5, cooldown: 2.4, recovery: 0.7 },
      ],
    },
    drops: [['mat_shard', 0.3, 1], ['spear_knight', 0.05, 1]],
  },

  // -------------------------------------------------------------------------
  //  The composed roster. Each of these is a silhouette plus a kit; the reason
  //  it exists is written above it, and it is always about what the player has
  //  to do differently, never about how much health it has.
  //
  //  Palette slots decide the surface as well as the colour (see MAT_SURFACE
  //  in rig.js, which maps them onto the MATERIAL ids in gfx/textures.js):
  //  ARMOR and METAL render as metal, LEATHER and DARK as leather, CLOTH,
  //  HAIR and ACCENT as woven cloth, SKIN as skin. A pale ARMOR reads as
  //  polished bone; a dark CLOTH reads as sacking.
  // -------------------------------------------------------------------------

  // Cannot be fought from the front. Either break the guard or go around.
  shieldbearer: {
    build: 'brute',
    name: '塔盾兵', rig: 'humanoid', scale: 1.08, kit: 'wall',
    helm: true,
    hp: 340, damage: 46, defense: 24, poise: 70, souls: 380,
    moveSpeed: 2.0, runSpeed: 3.4, turnRate: 3.6, mass: 2.0,
    weapon: 'spear_knight', offhand: 'shield_tower',
    palette: { SKIN: [0.58, 0.46, 0.38], CLOTH: [0.26, 0.28, 0.32], ARMOR: [0.44, 0.45, 0.50], LEATHER: [0.28, 0.24, 0.20], ACCENT: [0.54, 0.48, 0.28] },
    drops: [['mat_chunk', 0.18, 1], ['shield_tower', 0.03, 1], ['spear_knight', 0.05, 1]],
  },

  // Dies fast and takes the room with it. Finishing it in melee is the trap.
  flagellant: {
    build: 'gaunt',
    name: '苦行者', rig: 'humanoid', scale: 0.98, kit: 'skirmisher',
    hp: 150, damage: 44, defense: 6, poise: 8, souls: 260,
    moveSpeed: 3.8, runSpeed: 6.8, turnRate: 11, mass: 0.8,
    weapon: 'dagger_thief', offhand: null,
    palette: { SKIN: [0.62, 0.46, 0.42], CLOTH: [0.44, 0.40, 0.34], ARMOR: [0.34, 0.30, 0.26], LEATHER: [0.30, 0.24, 0.20], ACCENT: [0.72, 0.34, 0.20], HAIR: [0.22, 0.18, 0.14] },
    emissive: 0.10,
    deathEffect: { radius: 4.2, damage: 1.6, type: 'fire', color: [1.0, 0.48, 0.16], delay: 0.55 },
    affixes: ['ember', 'frenzied', 'venom'],
    drops: [['firebomb', 0.35, 2], ['mat_ashsalt', 0.25, 1]],
  },

  // Six metres of reach on stilts. Standing at sword range is losing.
  stiltwalker: {
    build: 'gaunt',
    name: '高足', rig: 'humanoid', scale: 1.42, kit: 'reach',
    hp: 300, damage: 52, defense: 12, poise: 18, souls: 420,
    moveSpeed: 2.6, runSpeed: 3.8, turnRate: 2.6, mass: 0.9,
    height: 2.5, radius: 0.40,
    weapon: 'spear_mire', offhand: null,
    palette: { SKIN: [0.52, 0.52, 0.44], CLOTH: [0.32, 0.34, 0.26], ARMOR: [0.30, 0.32, 0.26], LEATHER: [0.34, 0.28, 0.20], HAIR: [0.24, 0.24, 0.18] },
    status: { type: 'bleed', build: 20 },
    drops: [['spear_mire', 0.05, 1], ['mat_hide', 0.3, 1]],
  },

  // The first enemy that is not on the ground. Lock-on and patience, or a bow.
  ashcrow: {
    name: '灰鴉', rig: 'winged', scale: 0.62,
    hp: 210, damage: 48, defense: 12, poise: 14, souls: 340,
    moveSpeed: 4.6, runSpeed: 8.0, turnRate: 9, mass: 0.7,
    height: 1.4, radius: 0.55,
    palette: { ARMOR: [0.26, 0.25, 0.26], LEATHER: [0.20, 0.19, 0.20], DARK: [0.13, 0.12, 0.13], CLOTH: [0.24, 0.23, 0.24], ACCENT: [0.62, 0.58, 0.42] },
    ai: {
      preferredRange: 3.4, aggression: 0.72, patience: 0.5, sightRange: 30,
      canDodge: true, dodgeChance: 0.3, strafeSpeedMul: 1.2, groupRadius: 18,
      attacks: [
        { id: 'crow_rake', range: [0, 3.2], weight: 1.0, cooldown: 1.1, recovery: 0.4 },
        { id: 'crow_dive', range: [6.0, 18], weight: 1.1, cooldown: 4.2, recovery: 0.9 },
        { id: 'crow_quill', range: [7.0, 24], weight: 0.7, cooldown: 5.0, recovery: 1.0 },
        { id: 'drake_tail', range: [0, 3.6], weight: 0.6, cooldown: 3.6, recovery: 0.8 },
      ],
    },
    drops: [['mat_fang', 0.35, 1], ['bow_whisper', 0.02, 1]],
  },

  // It is already where you are walking. Sprinting through the mire stops.
  mirestalker: {
    build: 'lithe',
    name: '泥潜み', rig: 'quadruped', scale: 1.1, kit: 'ambush',
    hp: 260, damage: 58, defense: 10, poise: 26, souls: 380,
    moveSpeed: 3.4, runSpeed: 6.6, turnRate: 8, mass: 1.0,
    height: 1.0, radius: 0.55,
    palette: { CLOTH: [0.24, 0.26, 0.18], DARK: [0.14, 0.16, 0.11] },
    status: { type: 'poison', build: 26 },
    affixes: ['venom', 'frenzied', 'hoar'],
    drops: [['antidote', 0.35, 2], ['mat_hide', 0.35, 1]],
  },

  // Harmless. Makes everything near it not harmless. Kill it first.
  bellringer: {
    build: 'stocky',
    name: '鐘守', rig: 'humanoid', scale: 1.04, kit: 'support',
    helm: true,
    hp: 230, damage: 34, defense: 16, poise: 20, souls: 520,
    moveSpeed: 2.6, runSpeed: 4.8, turnRate: 6, mass: 1.1,
    weapon: 'hammer_bell', offhand: null,
    palette: { SKIN: [0.60, 0.48, 0.40], CLOTH: [0.30, 0.28, 0.22], ARMOR: [0.56, 0.50, 0.30], LEATHER: [0.28, 0.24, 0.18], ACCENT: [0.72, 0.62, 0.30] },
    emissive: 0.08,
    drops: [['mat_bellbronze', 0.45, 1], ['hammer_bell', 0.03, 1]],
  },

  // Takes the floor away from you. Fighting it in a corridor is a mistake.
  hexbinder: {
    build: 'gaunt',
    name: '呪縛者', rig: 'humanoid', scale: 1.0, kit: 'caster',
    hp: 200, damage: 50, defense: 12, poise: 14, souls: 460,
    moveSpeed: 2.8, runSpeed: 4.6, turnRate: 7, mass: 0.9,
    weapon: 'staff_bone', offhand: null,
    palette: { SKIN: [0.48, 0.46, 0.52], CLOTH: [0.22, 0.20, 0.32], ARMOR: [0.26, 0.24, 0.34], LEATHER: [0.22, 0.20, 0.26], HAIR: [0.30, 0.26, 0.40], ACCENT: [0.56, 0.46, 0.86] },
    emissive: 0.14,
    affixes: ['warded', 'hoar', 'ambusher'],
    drops: [['flask_fp', 0.06, 1], ['staff_bone', 0.05, 1], ['mat_core', 0.06, 1]],
  },

  // Pulls you off the ledge you were carefully standing on, then grabs.
  chainhusk: {
    build: 'brute',
    name: '鎖亡骸', rig: 'humanoid', scale: 1.10,
    helm: true,
    hp: 380, damage: 62, defense: 20, poise: 46, souls: 560,
    moveSpeed: 2.2, runSpeed: 3.6, turnRate: 4.0, mass: 1.6,
    weapon: 'axe_bandit', offhand: null,
    palette: { SKIN: [0.44, 0.44, 0.40], CLOTH: [0.24, 0.22, 0.20], ARMOR: [0.36, 0.34, 0.32], LEATHER: [0.24, 0.20, 0.16], DARK: [0.12, 0.11, 0.10] },
    ai: {
      preferredRange: 2.8, aggression: 0.66, patience: 0.9, sightRange: 24,
      attacks: [
        { id: 'chain_pull', range: [5.0, 16], weight: 1.2, cooldown: 7.0, recovery: 1.0 },
        { id: 'chain_grab', range: [0, 3.4], weight: 0.9, cooldown: 6.0, recovery: 1.2 },
        { id: 'axe_l1', range: [0, 3.0], weight: 1.0, cooldown: 1.4, recovery: 0.6 },
        { id: 'flail_spin', range: [0, 3.6], weight: 0.7, cooldown: 4.0, recovery: 1.0 },
      ],
    },
    drops: [['axe_bandit', 0.05, 1], ['mat_chunk', 0.18, 1]],
  },

  // Braces, eats the combo, and answers it. Punishes committed strings.
  stonecarl: {
    build: 'hulk',
    name: '石守', rig: 'humanoid', scale: 1.30, kit: 'juggernaut',
    hp: 560, damage: 76, defense: 32, poise: 110, souls: 780,
    moveSpeed: 1.9, runSpeed: 3.2, turnRate: 3.0, mass: 2.6,
    weapon: 'great_bell', offhand: null,
    palette: { SKIN: [0.46, 0.45, 0.43], CLOTH: [0.32, 0.31, 0.29], ARMOR: [0.42, 0.41, 0.39], LEATHER: [0.28, 0.26, 0.24], HAIR: [0.24, 0.23, 0.22] },
    ai: { addAttacks: [{ id: 'wall_brace', range: [0, 8.0], weight: 1.0, cooldown: 8.0, recovery: 0.4 }] },
    resist: { magic: 0.2 },
    affixes: ['plated', 'ember', 'warded'],
    drops: [['mat_core', 0.14, 1], ['great_bell', 0.04, 1]],
  },

  // Parries. Mashing light attacks into it hands it a free riposte window.
  duelist: {
    build: 'lithe',
    name: '影打ち', rig: 'humanoid', scale: 1.0, kit: 'duel',
    hp: 320, damage: 66, defense: 18, poise: 30, souls: 700,
    moveSpeed: 3.4, runSpeed: 6.2, turnRate: 10, mass: 1.0,
    weapon: 'sword_curved', offhand: 'shield_buckler',
    palette: { SKIN: [0.56, 0.44, 0.38], CLOTH: [0.20, 0.20, 0.24], ARMOR: [0.34, 0.34, 0.38], LEATHER: [0.24, 0.22, 0.20], HAIR: [0.16, 0.14, 0.12], ACCENT: [0.44, 0.42, 0.48] },
    affixes: ['ambusher', 'frenzied', 'hoar'],
    drops: [['sword_curved', 0.05, 1], ['shield_buckler', 0.08, 1], ['tal_parry', 0.03, 1]],
  },

  // You cannot stand next to it. Everything about the fight is spacing.
  pyreclad: {
    build: 'brute',
    name: '火纏い', rig: 'humanoid', scale: 1.16,
    hp: 400, damage: 70, defense: 20, poise: 40, souls: 720,
    moveSpeed: 2.6, runSpeed: 4.8, turnRate: 5.5, mass: 1.4,
    weapon: 'axe_ember', offhand: null,
    palette: { SKIN: [0.34, 0.24, 0.22], CLOTH: [0.30, 0.20, 0.16], ARMOR: [0.36, 0.26, 0.20], LEATHER: [0.26, 0.18, 0.14], HAIR: [0.54, 0.24, 0.12], ACCENT: [0.96, 0.46, 0.16] },
    emissive: 0.26,
    resist: { fire: 0.6 },
    affixes: ['ember', 'plated', 'frenzied'],
    ai: {
      preferredRange: 2.6, aggression: 0.7, patience: 0.7, sightRange: 26,
      attacks: [
        { id: 'aura_flare', range: [0, 6.0], weight: 1.1, cooldown: 6.5, recovery: 1.1 },
        { id: 'axe_l1', range: [0, 3.0], weight: 1.0, cooldown: 1.3, recovery: 0.5 },
        { id: 'axe_l2', range: [0, 3.0], weight: 1.0, cooldown: 1.3, recovery: 0.5 },
        { id: 'flame_lob', range: [6, 20], weight: 0.8, cooldown: 5.0, recovery: 1.0 },
      ],
    },
    drops: [['axe_ember', 0.05, 1], ['resin_fire', 0.25, 1], ['tal_ashskin', 0.03, 1]],
  },

  // Individually free. In sixes it eats every attack token and your stamina.
  rootling: {
    build: 'small',
    name: '根の子', rig: 'humanoid', scale: 0.58, kit: 'swarm',
    hp: 70, damage: 22, defense: 4, poise: 4, souls: 45,
    moveSpeed: 3.8, runSpeed: 7.0, turnRate: 13, mass: 0.4,
    height: 1.05, radius: 0.28,
    weapon: 'dagger_thief', offhand: null,
    palette: { SKIN: [0.38, 0.46, 0.30], CLOTH: [0.24, 0.32, 0.20], ARMOR: [0.26, 0.34, 0.22], LEATHER: [0.22, 0.26, 0.16], HAIR: [0.30, 0.40, 0.22], ACCENT: [0.52, 0.60, 0.28] },
    emissive: 0.06,
    affixes: ['venom', 'frenzied'],
    drops: [['mat_hide', 0.12, 1]],
  },

  // Refuses to commit until you do. Whiffing is what kills you here.
  snowstalker: {
    name: '雪走り', rig: 'quadruped', scale: 1.08, kit: 'beast_pack',
    hp: 290, damage: 58, defense: 16, poise: 18, souls: 480,
    moveSpeed: 5.0, runSpeed: 9.4, turnRate: 13, mass: 0.8,
    height: 1.2, radius: 0.44,
    palette: { CLOTH: [0.78, 0.82, 0.86], DARK: [0.40, 0.48, 0.58] },
    status: { type: 'frost', build: 24 },
    ai: {
      aggression: 0.35, patience: 2.2, strafeSpeedMul: 1.35, dodgeChance: 0.55,
      addAttacks: [{ id: 'ambush_burst', range: [4.0, 11], weight: 1.3, cooldown: 3.4, recovery: 0.7 }],
    },
    affixes: ['hoar', 'frenzied', 'ambusher'],
    drops: [['mat_fang', 0.5, 2], ['warm_stone', 0.2, 1]],
  },

  // Puts the husks you already killed back on their feet. Clear it or loop.
  emberpriest: {
    build: 'gaunt',
    name: '燼の祈祷者', rig: 'humanoid', scale: 1.06, kit: 'support',
    hp: 280, damage: 44, defense: 18, poise: 22, souls: 820,
    moveSpeed: 2.4, runSpeed: 4.4, turnRate: 6, mass: 1.0,
    weapon: 'staff_ember', offhand: null,
    palette: { SKIN: [0.40, 0.30, 0.28], CLOTH: [0.34, 0.24, 0.20], ARMOR: [0.32, 0.24, 0.20], LEATHER: [0.26, 0.20, 0.16], HAIR: [0.50, 0.24, 0.12], ACCENT: [0.90, 0.48, 0.20] },
    emissive: 0.18,
    resist: { fire: 0.4 },
    ai: {
      addAttacks: [
        { id: 'rite_raise', range: [0, 26], weight: 1.3, cooldown: 15.0, recovery: 1.6 },
        { id: 'flame_lob', range: [7, 22], weight: 0.7, cooldown: 5.0, recovery: 1.0 },
      ],
    },
    affixes: ['ember', 'warded', 'bannered'],
    drops: [['staff_ember', 0.04, 1], ['ember_shard', 0.35, 1], ['sp_censer', 0.02, 1]],
  },

  // Bleeds you from outside your reach, then keeps backing up.
  harpooner: {
    build: 'stocky',
    name: '銛打ち', rig: 'humanoid', scale: 1.0, kit: 'sniper',
    hp: 220, damage: 46, defense: 12, poise: 18, souls: 340,
    moveSpeed: 3.0, runSpeed: 5.4, turnRate: 8, mass: 1.0,
    weapon: 'spear_harpoon', offhand: null,
    palette: { SKIN: [0.60, 0.50, 0.42], CLOTH: [0.28, 0.32, 0.28], ARMOR: [0.30, 0.32, 0.28], LEATHER: [0.30, 0.26, 0.18], HAIR: [0.20, 0.16, 0.12] },
    status: { type: 'bleed', build: 24 },
    ai: {
      rangedIdeal: 13, preferredRange: 13,
      attacks: [
        { id: 'harpoon_cast', range: [6, 24], weight: 1.0, cooldown: 3.0, recovery: 0.9 },
        { id: 'spear_l1', range: [1.4, 3.8], weight: 0.9, cooldown: 1.2, recovery: 0.5 },
        { id: 'reach_sweep', range: [0, 3.6], weight: 0.6, cooldown: 3.2, recovery: 0.9 },
        { id: 'kick', range: [0, 2.1], weight: 0.5, cooldown: 3.5, recovery: 0.5 },
      ],
    },
    drops: [['spear_harpoon', 0.05, 1], ['blood_stanch', 0.25, 1], ['mat_hide', 0.3, 1]],
  },
};

/**
 * Where the composed roster belongs, by region and structure role. The world
 * builder owns the live table (structures.js REGION_ENEMIES); this is the
 * authored intent for it, kept next to the archetypes it describes so the two
 * cannot drift apart silently.
 */
export const REGION_ROSTER = {
  meadow: { camp: ['shieldbearer'], ruin: ['rootling'], wild: ['rootling'] },
  wood: { camp: ['rootling', 'duelist'], ruin: ['hexbinder', 'rootling'], wild: ['rootling', 'hexbinder'] },
  mire: { camp: ['harpooner', 'stiltwalker'], ruin: ['stiltwalker', 'hexbinder'], wild: ['mirestalker', 'harpooner'] },
  ridge: { camp: ['shieldbearer', 'bellringer'], ruin: ['shieldbearer', 'duelist'], wild: ['duelist', 'bellringer'] },
  crag: { camp: ['stonecarl', 'ashcrow'], ruin: ['stonecarl'], wild: ['ashcrow', 'stonecarl'] },
  waste: { camp: ['pyreclad', 'emberpriest'], ruin: ['flagellant', 'emberpriest'], wild: ['flagellant', 'pyreclad', 'ashcrow'] },
  peak: { camp: ['snowstalker', 'duelist'], ruin: ['stonecarl', 'shieldbearer'], wild: ['snowstalker', 'ashcrow'] },
};

// ---------------------------------------------------------------------------

const LEVEL_HP = 0.085;
const LEVEL_DMG = 0.062;

export class Enemy extends Actor {
  constructor(game, archetypeId, opts = {}) {
    const arch = ARCHETYPES[archetypeId];
    if (!arch) throw new Error(`unknown archetype: ${archetypeId}`);
    const level = opts.level || 1;
    const scaleK = 1 + (level - 1) * LEVEL_HP;
    const dmgK = 1 + (level - 1) * LEVEL_DMG;

    super(game, {
      ...opts,
      rig: arch.rig,
      // Silhouette preset. An archetype that names one gets a differently
      // proportioned skeleton, not just a differently sized one.
      build: arch.build || null,
      scale: (arch.scale || 1) * (opts.scaleMul || 1),
      radius: (arch.radius || 0.42) * (arch.scale || 1),
      height: (arch.height || 1.75) * (arch.scale || 1),
      maxHp: Math.round(arch.hp * scaleK * (opts.hpMul || 1)),
      maxStamina: 100 + level * 2,
      poise: arch.poise,
      defense: arch.defense * (1 + (level - 1) * 0.05),
      moveSpeed: arch.moveSpeed,
      runSpeed: arch.runSpeed,
      turnRate: arch.turnRate,
      mass: arch.mass || 1,
      faction: FACTION.ENEMY,
      name: arch.name,
      level,
      resist: { ...(arch.resist || {}) },
      palette: pal(arch.palette || {}),
    });

    this.archetypeId = archetypeId;
    this.arch = arch;
    this.baseDamage = arch.damage * dmgK * (opts.dmgMul || 1);
    this.soulsValue = Math.round(arch.souls * (1 + (level - 1) * 0.14) * (opts.soulsMul || 1));
    this.emissive = arch.emissive || 0;
    this.statusEffect = arch.status || null;
    this.staminaRegen = 26;

    if (arch.weapon) this.weapon = getItem(arch.weapon);
    if (arch.offhand) this.offhand = getItem(arch.offhand);
    this.weaponClass = this.weapon ? this.weapon.class : 'sword';
    if (arch.rig !== 'quadruped' && arch.rig !== 'winged') this.rig.setHelm(!!arch.helm);

    this.brain = new EnemyBrain(this, resolveAI(arch));
    this.brain.setHome(this.x, this.z);
    this.dropTable = arch.drops || [];

    // Affix comes last so it can see the finished stat block. Bosses and
    // mini-bosses opt out: their identity is authored, not composed.
    this.affix = null;
    if (!opts.noAffix) {
      const key = opts.affix !== undefined
        ? opts.affix
        : rollAffix(arch, this.x, this.z, level, game.world ? game.world.seed : 0);
      if (key && AFFIXES[key]) this._applyAffix(key, AFFIXES[key]);
    }

    this.isElite = !!opts.elite;
    if (this.isElite) {
      this.maxHp = Math.round(this.maxHp * 2.1);
      this.hp = this.maxHp;
      this.baseDamage *= 1.35;
      this.soulsValue = Math.round(this.soulsValue * 3.2);
      this.maxPoise *= 1.6;
      this.poise = this.maxPoise;
      this.scale *= 1.12;
      this.rig.scale = this.scale;
      this.name = `強き${this.name}`;
    }
  }

  /** Fold an affix into the finished stat block, palette and moveset. */
  _applyAffix(key, af) {
    this.affix = key;
    this.name = `${af.prefix}${this.name}`;

    this.maxHp = Math.max(1, Math.round(this.maxHp * (af.hpMul || 1)));
    this.hp = this.maxHp;
    this.baseDamage *= af.dmgMul || 1;
    this.defense += af.defenseAdd || 0;
    this.maxPoise = Math.max(2, this.maxPoise * (af.poiseMul || 1));
    this.poise = this.maxPoise;
    if (af.speedMul) {
      this.moveSpeed *= af.speedMul;
      this.runSpeed *= af.speedMul;
      this.turnRate *= Math.min(af.speedMul, 1.25);
    }
    this.soulsValue = Math.round(this.soulsValue * (af.soulsMul || 1));
    if (af.emissive) this.emissive = Math.max(this.emissive, af.emissive);
    if (af.status) this.statusEffect = af.status;
    for (const k in af.resist || {}) {
      this.resist[k] = (this.resist[k] || 0) + af.resist[k];
    }
    for (const slot in af.palette || {}) {
      if (MAT[slot] !== undefined) this.palette[MAT[slot]] = af.palette[slot];
    }
    if (af.ai) Object.assign(this.brain.cfg, af.ai);
    if (af.addAttacks) {
      // Concat, never replace: the affix adds an answer, it does not remove the
      // moveset the player has already learned to read.
      this.brain.cfg.attacks = (this.brain.cfg.attacks || []).concat(af.addAttacks);
    }
    if (af.drops) this.dropTable = this.dropTable.concat(af.drops);
  }

  buildAttackInfo(target) {
    const def = this.action || ATTACKS.sword_l1;
    const dmg = this.baseDamage * (def.dmg || 1);
    return {
      damage: dmg,
      poise: def.poise || 12,
      type: 'physical',
      knockback: 1.8 + (def.poise || 10) * 0.04,
      status: this.statusEffect,
      big: (def.poise || 0) > 40,
      parryable: def.unblockable ? false : undefined,
      // Forwarded separately from `parryable`: a grab that cannot be parried
      // should not be stopped by a shield either, and the guard path needs its
      // own flag to see that. Actor.takeDamage is what has to honour it.
      unblockable: !!def.unblockable,
      source: this,
    };
  }

  update(dt) {
    this.brain.update(dt, this.game);
    super.update(dt);
    this._handleSpecialAttack(dt);
  }

  /**
   * Some attacks emit a projectile or a shockwave at a point in the animation
   * rather than relying on the weapon hitbox.
   */
  _handleSpecialAttack(dt) {
    if (this.state !== STATE.ATTACK || !this.action) return;
    const def = this.action;

    if (def.ranged && !this._firedRanged && this.actionU >= 0.5) {
      this._firedRanged = true;
      this._fireRanged(def);
    }
    if (def.aoe && !this._firedAoe && this.actionU >= def.aoe.at) {
      this._firedAoe = true;
      this.game.areaEffects.push(new AreaEffect(this.game, {
        x: this.x, y: this.y, z: this.z,
        radius: def.aoe.radius * this.scale,
        delay: 0, duration: 0.3,
        damage: this.baseDamage * (def.dmg || 1) * 0.85,
        poise: def.poise || 40,
        type: def.aoe.element || 'physical',
        source: this, faction: this.faction,
        color: def.aoe.element === 'fire' ? [1, 0.45, 0.15] : [0.7, 0.62, 0.5],
        telegraph: false,
      }));
      this.game.shake(0.3, 0.25);
    }
    // Boss subclasses run their own, richer special table; letting both fire
    // would double every summon and every shockwave.
    if (def.special && !this.isBoss && !this._firedSpecial && this.actionU >= 0.45) {
      this._firedSpecial = true;
      this._fireSpecial(def.special, def);
    }
    // Multi-hit attacks re-arm the hit set for their second window.
    if (def.hit2 && this.actionU >= def.hit2[0] && this.actionU <= def.hit2[1]) {
      if (!this._secondWindow) { this._secondWindow = true; this.hitSet.clear(); }
      this.hitActive = true;
    }
    if (this.actionU < 0.05) {
      this._firedRanged = false;
      this._firedAoe = false;
      this._firedSpecial = false;
      this._secondWindow = false;
    }
  }

  /**
   * Non-damage behaviours: the pieces that make a kit read as a tactic rather
   * than a damage number. Each one changes where the player can safely stand.
   */
  _fireSpecial(kind, def) {
    const g = this.game;
    const t = this.brain.target || g.player;
    const dmg = this.baseDamage * (def.dmg || 1);

    switch (kind) {
      case 'brace': {
        // Raises the guard and hardens it for a beat. The window to hit it is
        // after the brace drops, not during.
        this.blocking = !!this.offhand;
        const bonus = 14 + this.level * 0.8;
        this.defense += bonus;
        this.poise = this.maxPoise;
        g.schedule(2.4, () => {
          if (this.dead) return;
          this.blocking = false;
          this.defense -= bonus;
        });
        break;
      }
      case 'rally': {
        // Wakes and hurries everything nearby. The reason to kill the ringer.
        let woken = 0;
        for (const e of g.enemies) {
          if (e === this || e.dead || !e.brain) continue;
          if (Math.hypot(e.x - this.x, e.z - this.z) > 24) continue;
          e.brain.cfg.aggression = Math.min(1, (e.brain.cfg.aggression || 0.6) + 0.25);
          e.moveSpeed *= 1.12;
          e.runSpeed *= 1.12;
          e.hp = Math.min(e.maxHp, e.hp + e.maxHp * 0.12);
          if (t) {
            e.brain.target = t;
            e.brain.alertness = 2;
            e.brain.setState(AI_STATE.CHASE);
          }
          woken++;
          g.particles.burst(e.x, e.y + 1.4, e.z, 8, {
            r: 1.0, g: 0.78, b: 0.34, size: 0.16, life: 0.6, spread: 1.2, up: 2.0,
            blend: BLEND.ADDITIVE, alpha: 0.9, drag: 2, gravity: 0.5,
          });
        }
        if (woken > 0) g.notify('鐘が鳴った');
        break;
      }
      case 'raise': {
        // Puts a husk back up. Short-lived, but it costs the player the tempo.
        const a = hash2(Math.round(this.x), Math.round(this.z + g.time), 0x5150) * TAU;
        const r = 4 + hash2(Math.round(this.z), Math.round(this.x + g.time), 0x9911) * 4;
        const e = g.spawnEnemy('husk', this.x + Math.cos(a) * r, this.z + Math.sin(a) * r, {
          level: this.level, summoned: true,
        });
        if (e) {
          e.removeAfter = 22;
          e.hp = Math.round(e.maxHp * 0.6);
          e.soulsValue = 0;
        }
        break;
      }
      case 'rune': {
        // A slow circle on the ground where the player is standing now.
        const cx = t ? t.x : this.x, cz = t ? t.z : this.z;
        g.areaEffects.push(new AreaEffect(g, {
          x: cx, y: g.world.heightAt(cx, cz), z: cz,
          radius: 3.6, delay: 1.25, duration: 0.4,
          damage: dmg * 1.1, poise: 45, type: 'magic',
          source: this, faction: this.faction, color: [0.58, 0.46, 0.92], knockback: 6,
        }));
        break;
      }
      case 'pull': {
        // Drags the target in. Ledges and hazards suddenly matter.
        if (!t) break;
        const a = Math.atan2(this.x - t.x, this.z - t.z);
        const force = 13 / Math.max(0.5, t.mass);
        t.velX += Math.sin(a) * force;
        t.velZ += Math.cos(a) * force;
        t.takeDamage({
          damage: dmg, poise: 22, type: 'physical', source: this,
          knockback: 0, parryable: false,
        });
        break;
      }
      case 'aura': {
        // A ring at its own feet, twice. Standing in melee is the mistake.
        for (let ring = 0; ring < 2; ring++) {
          const R = 2.4 + ring * 2.0;
          const count = 6 + ring * 4;
          for (let i = 0; i < count; i++) {
            const ang = (i / count) * TAU + ring * 0.3;
            g.areaEffects.push(new AreaEffect(g, {
              x: this.x + Math.cos(ang) * R, y: this.y, z: this.z + Math.sin(ang) * R,
              radius: 1.7, delay: 0.2 + ring * 0.35, duration: 0.26,
              damage: dmg * 0.5, poise: 26, type: 'fire',
              source: this, faction: this.faction, color: [1, 0.5, 0.18],
            }));
          }
        }
        break;
      }
      case 'stance': {
        // Holds a parry. Swinging into it hands over a full punish window.
        this.parryTimer = Math.max(this.parryTimer, 0.95);
        g.particles.burst(this.x, this.y + 1.3, this.z, 6, {
          r: 0.9, g: 0.92, b: 1.0, size: 0.12, life: 0.4, spread: 0.8, up: 1.2,
          blend: BLEND.ADDITIVE, alpha: 0.7, drag: 2.5, gravity: 0,
        });
        break;
      }
      case 'burrow': {
        // Reposition, not a teleport attack: it reappears flanking.
        if (!t) break;
        const a = Math.atan2(this.x - t.x, this.z - t.z) + (this.brain.strafeDir > 0 ? 2.1 : -2.1);
        const r = 4.5;
        this.invuln = Math.max(this.invuln, 0.8);
        g.particles.burst(this.x, this.y + 0.3, this.z, 18, {
          r: 0.32, g: 0.30, b: 0.22, size: 0.26, life: 0.7, spread: 2.4, up: 1.6,
          alpha: 0.8, drag: 2, gravity: -5,
        });
        this.teleport(t.x + Math.sin(a) * r, undefined, t.z + Math.cos(a) * r);
        this.yaw = Math.atan2(t.x - this.x, t.z - this.z);
        break;
      }
      default: break;
    }
  }

  _fireRanged(def) {
    const g = this.game;
    const t = this.brain.target || g.player;
    if (!t) return;
    const from = this.rig.jointPos('chest', {});
    from.y += 0.4 * this.scale;
    const dx = t.x - from.x;
    const dy = (t.y + t.height * 0.55) - from.y;
    const dz = t.z - from.z;
    const dist = Math.hypot(dx, dz) || 1;
    const dmg = this.baseDamage * (def.dmg || 1);

    if (def.ranged === 'arrow') {
      const speed = 38;
      const flight = dist / speed;
      // Lead the target and add arc compensation.
      const aimY = dy + 0.5 * 7 * flight * flight;
      const len = Math.hypot(dx, aimY, dz) || 1;
      g.projectiles.push(new Projectile(g, {
        x: from.x, y: from.y, z: from.z,
        vx: (dx / len) * speed, vy: (aimY / len) * speed, vz: (dz / len) * speed,
        damage: dmg, poise: def.poise, type: 'physical',
        source: this, faction: this.faction, gravity: -7,
        color: [0.55, 0.48, 0.38], size: 0.09, radius: 0.24, kind: 'arrow', emissive: 0,
      }));
      g.audio.playBow();
    } else if (def.ranged === 'bolt') {
      const speed = 20;
      const len = Math.hypot(dx, dy, dz) || 1;
      g.projectiles.push(new Projectile(g, {
        x: from.x, y: from.y, z: from.z,
        vx: (dx / len) * speed, vy: (dy / len) * speed, vz: (dz / len) * speed,
        damage: dmg, poise: def.poise, type: 'magic',
        source: this, faction: this.faction, gravity: 0,
        color: [0.6, 0.9, 0.55], size: 0.26, radius: 0.32, kind: 'orb',
        homing: 0.9, target: t,
      }));
      g.audio.playSpell('magic');
    } else if (def.ranged === 'breath') {
      // A stream of fire emitted over the attack's active window.
      const emit = () => {
        if (this.dead) return;
        const tt = this.brain.target || g.player;
        if (!tt) return;
        const o = this.rig.jointPos('jaw', {});
        const ddx = tt.x - o.x, ddy = (tt.y + 1) - o.y, ddz = tt.z - o.z;
        const l = Math.hypot(ddx, ddy, ddz) || 1;
        for (let i = 0; i < 3; i++) {
          const sp = 16 + Math.random() * 8;
          g.projectiles.push(new Projectile(g, {
            x: o.x, y: o.y, z: o.z,
            vx: (ddx / l) * sp + (Math.random() - 0.5) * 3,
            vy: (ddy / l) * sp + (Math.random() - 0.5) * 2,
            vz: (ddz / l) * sp + (Math.random() - 0.5) * 3,
            damage: dmg * 0.12, poise: 6, type: 'fire',
            source: this, faction: this.faction, gravity: -1.5,
            color: [1, 0.5, 0.16], size: 0.34, radius: 0.42, kind: 'orb',
            life: 0.8, trail: false,
          }));
        }
      };
      for (let k = 0; k < 8; k++) g.schedule(k * 0.09, emit);
      g.audio.playBreath();
    } else if (def.ranged === 'harpoon') {
      // Flat and fast, and it bleeds. Rolling sideways beats it; backing off
      // does not, which is the point of the enemy that throws it.
      const speed = 30;
      const flight = dist / speed;
      const aimY = dy + 0.5 * 4 * flight * flight;
      const len = Math.hypot(dx, aimY, dz) || 1;
      g.projectiles.push(new Projectile(g, {
        x: from.x, y: from.y, z: from.z,
        vx: (dx / len) * speed, vy: (aimY / len) * speed, vz: (dz / len) * speed,
        damage: dmg, poise: 22, type: 'physical',
        source: this, faction: this.faction, gravity: -4,
        color: [0.58, 0.56, 0.50], size: 0.13, radius: 0.30, kind: 'arrow', emissive: 0,
        status: { type: 'bleed', build: 26 }, knockback: 5,
      }));
      g.audio.playBow();
    } else if (def.ranged === 'spit') {
      const speed = 17;
      const flight = dist / speed;
      const aimY = dy + 0.5 * 8 * flight * flight;
      const len = Math.hypot(dx, aimY, dz) || 1;
      g.projectiles.push(new Projectile(g, {
        x: from.x, y: from.y, z: from.z,
        vx: (dx / len) * speed, vy: (aimY / len) * speed, vz: (dz / len) * speed,
        damage: dmg * 0.7, poise: 12, type: 'poison',
        source: this, faction: this.faction, gravity: -8,
        color: [0.52, 0.74, 0.32], size: 0.30, radius: 0.42, kind: 'orb',
        status: { type: 'poison', build: 30 },
      }));
      g.audio.playSpell('magic');
    } else if (def.ranged === 'shard') {
      // A tight fan, so strafing one way clears it and standing still does not.
      const base = Math.atan2(dx, dz);
      for (let i = -1; i <= 1; i++) {
        const a = base + i * 0.11;
        g.projectiles.push(new Projectile(g, {
          x: from.x, y: from.y, z: from.z,
          vx: Math.sin(a) * 26, vy: dy / Math.max(dist, 1) * 8, vz: Math.cos(a) * 26,
          damage: dmg * 0.42, poise: 8, type: 'magic',
          source: this, faction: this.faction, gravity: -1.5,
          color: [0.74, 0.88, 1.0], size: 0.18, radius: 0.26, kind: 'arrow',
          status: { type: 'frost', build: 12 }, life: 2.4,
        }));
      }
      g.audio.playSpell('magic');
    } else if (def.ranged === 'flame') {
      const speed = 15;
      const flight = dist / speed;
      const aimY = dy + 0.5 * 9 * flight * flight;
      const len = Math.hypot(dx, aimY, dz) || 1;
      g.projectiles.push(new Projectile(g, {
        x: from.x, y: from.y, z: from.z,
        vx: (dx / len) * speed, vy: (aimY / len) * speed, vz: (dz / len) * speed,
        damage: dmg * 0.4, poise: 14, type: 'fire',
        source: this, faction: this.faction, gravity: -9,
        color: [1, 0.52, 0.18], size: 0.32, radius: 0.40, kind: 'orb',
        explode: {
          radius: 3.0, damage: dmg * 0.75, type: 'fire',
          color: [1, 0.5, 0.16], faction: this.faction, source: this,
        },
      }));
      g.audio.playSpell('fire');
    }
  }

  onFootstep(speed) {
    this.game.onFootstep?.(this, speed);
  }

  die(killer) {
    if (this.dead) return;
    super.die(killer);
    this.game.director.releaseAll(this);

    // Some things are more dangerous dead than alive. The delay is the tell.
    const fx = this.arch.deathEffect;
    if (fx) {
      const g = this.game;
      const x = this.x, y = this.y, z = this.z;
      g.areaEffects.push(new AreaEffect(g, {
        x, y, z,
        radius: fx.radius * this.scale, delay: fx.delay !== undefined ? fx.delay : 0.5,
        duration: 0.35,
        damage: this.baseDamage * (fx.damage || 1),
        poise: fx.poise || 45, type: fx.type || 'fire',
        source: this, faction: this.faction,
        color: fx.color || [1, 0.5, 0.18], knockback: 7,
      }));
    }
  }
}

export function spawnLootFor(enemy, rng) {
  const out = [];
  for (const [id, chance, count] of enemy.dropTable) {
    if (rng() < chance) out.push([id, count]);
  }
  return out;
}
