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
};

Object.assign(ATTACKS, ENEMY_ATTACKS);

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
      ],
    },
    drops: [['mat_hide', 0.30, 1], ['bow_short', 0.05, 1], ['throwing_knife', 0.25, 4]],
  },

  husk: {
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
    drops: [['mat_shard', 0.20, 1], ['great_iron', 0.03, 1]],
  },

  husk_archer: {
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
      ],
    },
    drops: [['mat_shard', 0.18, 1], ['bow_long', 0.03, 1]],
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
        { id: 'pounce', range: [4, 11], weight: 1.0, cooldown: 3.6, recovery: 0.8 },
      ],
    },
    drops: [['mat_fang', 0.5, 2], ['mat_chunk', 0.12, 1]],
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
        { id: 'sword_l1', range: [0, 2.2], weight: 0.5, cooldown: 1.4, recovery: 0.6 },
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
      preferredRange: 1.8, aggression: 0.7, patience: 0.6, sightRange: 14,
      attacks: [
        { id: 'bite', range: [0, 2.2], weight: 1.0, cooldown: 1.5, recovery: 0.6 },
      ],
    },
    drops: [['antidote', 0.3, 1], ['mat_hide', 0.2, 1]],
  },

  sentinel: {
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
        { id: 'pounce', range: [4, 12], weight: 1.0, cooldown: 3.2, recovery: 0.7 },
      ],
    },
    drops: [['mat_fang', 0.5, 2], ['mat_core', 0.08, 1]],
  },

  oathknight: {
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

    this.brain = new EnemyBrain(this, arch.ai || {});
    this.brain.setHome(this.x, this.z);
    this.dropTable = arch.drops || [];
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
    // Multi-hit attacks re-arm the hit set for their second window.
    if (def.hit2 && this.actionU >= def.hit2[0] && this.actionU <= def.hit2[1]) {
      if (!this._secondWindow) { this._secondWindow = true; this.hitSet.clear(); }
      this.hitActive = true;
    }
    if (this.actionU < 0.05) {
      this._firedRanged = false;
      this._firedAoe = false;
      this._secondWindow = false;
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
    }
  }

  onFootstep(speed) {
    this.game.onFootstep?.(this, speed);
  }

  die(killer) {
    if (this.dead) return;
    super.die(killer);
    this.game.director.releaseAll(this);
  }
}

export function spawnLootFor(enemy, rng) {
  const out = [];
  for (const [id, chance, count] of enemy.dropTable) {
    if (rng() < chance) out.push([id, count]);
  }
  return out;
}
