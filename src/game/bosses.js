// ============================================================================
//  bosses.js — named encounters.
//
//  A boss is an Enemy with three additions: phase thresholds that rewrite its
//  moveset mid-fight, a transition state that is invulnerable and readable,
//  and a health bar the game shows while it is engaged. Phases are where the
//  drama lives — the same arena has to feel different at 40% than at 100%.
// ============================================================================

import { ARCHETYPES, Enemy, ENEMY_ATTACKS } from './enemies.js';
import { Actor, STATE, FACTION } from './actor.js';
import { ATTACKS, stage, pulse } from './anim.js';
import { AreaEffect, Projectile } from './combat.js';
import { AI_STATE } from './ai.js';
import { MAT } from './rig.js';
import { BLEND } from '../gfx/particles.js';
import { clamp, lerp, saturate, TAU } from '../core/math.js';

// ---------------------------------------------------------------------------
//  Boss-only attacks
// ---------------------------------------------------------------------------

const noop = () => ({ lunge: 0 });

const BOSS_ATTACKS = {
  warden_slam: { dur: 1.85, hit: [0.56, 0.72], stam: 30, dmg: 1.9, poise: 90, motion: 2.6, aoe: { radius: 4.4, at: 0.62 }, pose: (r, u) => ATTACKS.great_h1.pose(r, u) },
  warden_sweep: { dur: 1.45, hit: [0.40, 0.66], stam: 26, dmg: 1.5, poise: 70, motion: 2.0, pose: (r, u) => ATTACKS.great_l1.pose(r, u) },
  warden_roots: { dur: 2.20, hit: [0.5, 0.52], stam: 30, dmg: 1.0, poise: 50, motion: 0, special: 'roots', pose: (r, u) => ATTACKS.cast.pose(r, u) },
  warden_charge: { dur: 1.90, hit: [0.28, 0.66], stam: 34, dmg: 1.7, poise: 85, motion: 13.0, pose: (r, u) => ATTACKS.spear_h1.pose(r, u) },

  queen_wave: { dur: 1.70, hit: [0.5, 0.52], stam: 24, dmg: 1.0, poise: 40, motion: 0, special: 'poison_wave', pose: (r, u) => ATTACKS.cast.pose(r, u) },
  queen_lash: { dur: 1.05, hit: [0.34, 0.58], stam: 20, dmg: 1.3, poise: 45, motion: 4.0, pose: (r, u) => ATTACKS.spear_l3.pose(r, u) },
  queen_summon: { dur: 2.40, hit: [0.5, 0.52], stam: 30, dmg: 1.0, poise: 40, motion: 0, special: 'summon', pose: (r, u) => ATTACKS.cast.pose(r, u) },
  queen_dive: { dur: 1.60, hit: [0.40, 0.60], stam: 26, dmg: 1.8, poise: 70, motion: 9.0, aoe: { radius: 3.6, at: 0.52, element: 'poison' }, pose: (r, u) => ATTACKS.great_h1.pose(r, u) },

  oath_combo3: {
    dur: 2.05, stam: 30, dmg: 1.0, poise: 26, motion: 2.0,
    hit: [0.20, 0.30], hit2: [0.50, 0.60], hit3: [0.80, 0.92],
    pose: (r, u) => (u < 0.34 ? ATTACKS.sword_l1.pose(r, u * 2.9)
      : u < 0.67 ? ATTACKS.sword_l2.pose(r, (u - 0.34) * 3.0)
        : ATTACKS.sword_l3.pose(r, (u - 0.67) * 3.0)),
  },
  oath_thrust: { dur: 1.15, hit: [0.34, 0.50], stam: 24, dmg: 1.7, poise: 40, motion: 8.5, pose: (r, u) => ATTACKS.spear_h1.pose(r, u * 1.0) },
  oath_flame: { dur: 1.60, hit: [0.5, 0.52], stam: 28, dmg: 1.0, poise: 50, motion: 0, special: 'flame_arc', pose: (r, u) => ATTACKS.cast.pose(r, u) },
  oath_leap: { dur: 1.80, hit: [0.56, 0.70], stam: 34, dmg: 2.2, poise: 80, motion: 4.0, aoe: { radius: 4.0, at: 0.60, element: 'fire' }, pose: (r, u) => ATTACKS.great_h1.pose(r, u) },

  drake_wing: { dur: 1.55, hit: [0.36, 0.60], stam: 26, dmg: 1.4, poise: 65, motion: 2.0, pose: noop },
  drake_takeoff: { dur: 2.60, hit: [0.5, 0.52], stam: 40, dmg: 1.0, poise: 60, motion: 0, special: 'takeoff', pose: noop },
  drake_dive: { dur: 1.90, hit: [0.42, 0.66], stam: 36, dmg: 2.3, poise: 90, motion: 16.0, aoe: { radius: 4.6, at: 0.55 }, pose: noop },

  king_wave: { dur: 1.75, hit: [0.5, 0.52], stam: 30, dmg: 1.0, poise: 50, motion: 0, special: 'fire_wave', pose: (r, u) => ATTACKS.great_l1.pose(r, u) },
  king_combo: {
    dur: 2.30, stam: 34, dmg: 1.25, poise: 45, motion: 2.4,
    hit: [0.26, 0.38], hit2: [0.62, 0.76],
    pose: (r, u) => (u < 0.5 ? ATTACKS.great_l1.pose(r, u * 2) : ATTACKS.great_l2.pose(r, (u - 0.5) * 2)),
  },
  king_erupt: { dur: 2.05, hit: [0.5, 0.52], stam: 34, dmg: 1.0, poise: 60, motion: 0, special: 'eruption', pose: (r, u) => ATTACKS.great_h1.pose(r, u) },
  king_grab: { dur: 1.70, hit: [0.36, 0.50], stam: 30, dmg: 2.8, poise: 999, motion: 6.0, unblockable: true, pose: (r, u) => ATTACKS.spear_h1.pose(r, u) },

  sov_judgement: { dur: 2.40, hit: [0.5, 0.52], stam: 40, dmg: 1.0, poise: 70, motion: 0, special: 'judgement', pose: (r, u) => ATTACKS.cast.pose(r, u) },
  sov_rain: { dur: 2.80, hit: [0.5, 0.52], stam: 44, dmg: 1.0, poise: 70, motion: 0, special: 'rain', pose: (r, u) => ATTACKS.cast.pose(r, u) },
  sov_combo4: {
    dur: 2.65, stam: 40, dmg: 1.05, poise: 35, motion: 2.6,
    hit: [0.16, 0.24], hit2: [0.40, 0.48], hit3: [0.64, 0.72], hit4: [0.86, 0.95],
    pose: (r, u) => (u < 0.26 ? ATTACKS.sword_l1.pose(r, u * 3.8)
      : u < 0.5 ? ATTACKS.sword_l2.pose(r, (u - 0.26) * 4.1)
        : u < 0.74 ? ATTACKS.sword_l3.pose(r, (u - 0.5) * 4.1)
          : ATTACKS.great_h2.pose(r, (u - 0.74) * 3.8)),
  },
};

Object.assign(ATTACKS, BOSS_ATTACKS);

// ---------------------------------------------------------------------------
//  Boss archetypes
// ---------------------------------------------------------------------------

export const BOSSES = {
  warden: {
    id: 'warden', title: '森の縛り手', subtitle: 'Warden of the Wood',
    arch: {
      name: '森の縛り手', rig: 'humanoid', scale: 2.05,
      hp: 2600, damage: 92, defense: 26, poise: 190, souls: 6000,
      moveSpeed: 2.4, runSpeed: 4.6, turnRate: 3.4, mass: 6,
      height: 1.8, radius: 0.95,
      weapon: 'great_husk', offhand: null,
      palette: {
        SKIN: [0.34, 0.36, 0.26], CLOTH: [0.22, 0.28, 0.18], ARMOR: [0.26, 0.32, 0.20],
        LEATHER: [0.24, 0.22, 0.16], HAIR: [0.30, 0.40, 0.22], ACCENT: [0.42, 0.52, 0.26], DARK: [0.14, 0.18, 0.12],
      },
      ai: {
        preferredRange: 3.8, aggression: 0.62, patience: 0.9, sightRange: 40,
        leashRange: 0, groupRadius: 0, wanderRadius: 0,
        attacks: [
          { id: 'warden_sweep', range: [0, 5.2], weight: 1.0, cooldown: 2.4, recovery: 0.8 },
          { id: 'warden_slam', range: [0, 5.0], weight: 0.8, cooldown: 4.5, recovery: 1.2 },
          { id: 'warden_charge', range: [5.0, 14], weight: 0.9, cooldown: 6.0, recovery: 1.3 },
          { id: 'warden_roots', range: [3.0, 18], weight: 0.6, cooldown: 9.0, recovery: 1.4 },
        ],
      },
      drops: [],
    },
    phases: [
      { at: 1.0, tint: [1, 1, 1] },
      {
        at: 0.45, name: '第二段階', tint: [1.0, 0.85, 0.65], dmgMul: 1.25, speedMul: 1.18,
        addAttacks: [{ id: 'warden_roots', range: [2.0, 22], weight: 1.3, cooldown: 5.5, recovery: 1.0 }],
        aggression: 0.85,
      },
    ],
    reward: { souls: 6000, item: 'key_shard_1', extra: [['mat_chunk', 3]] },
  },

  mirequeen: {
    id: 'mirequeen', title: '泥の女王', subtitle: 'Queen of the Mire',
    arch: {
      name: '泥の女王', rig: 'humanoid', scale: 1.55,
      hp: 3200, damage: 104, defense: 28, poise: 120, souls: 9000,
      moveSpeed: 3.0, runSpeed: 5.4, turnRate: 6, mass: 3,
      height: 1.85, radius: 0.72,
      weapon: 'spear_ash', offhand: null,
      palette: {
        SKIN: [0.44, 0.50, 0.34], CLOTH: [0.24, 0.30, 0.20], ARMOR: [0.28, 0.34, 0.22],
        LEATHER: [0.22, 0.26, 0.16], HAIR: [0.26, 0.34, 0.18], ACCENT: [0.52, 0.64, 0.28],
      },
      emissive: 0.1,
      status: { type: 'poison', build: 34 },
      ai: {
        preferredRange: 3.2, aggression: 0.55, patience: 1.1, sightRange: 40,
        leashRange: 0, groupRadius: 0, wanderRadius: 0, canDodge: true, dodgeChance: 0.35,
        attacks: [
          { id: 'queen_lash', range: [0, 4.6], weight: 1.0, cooldown: 1.6, recovery: 0.6 },
          { id: 'queen_wave', range: [3.0, 20], weight: 0.9, cooldown: 5.0, recovery: 1.0 },
          { id: 'queen_dive', range: [4.0, 12], weight: 0.8, cooldown: 6.0, recovery: 1.2 },
          { id: 'queen_summon', range: [5.0, 24], weight: 0.5, cooldown: 16.0, recovery: 1.6 },
        ],
      },
      drops: [],
    },
    phases: [
      { at: 1.0 },
      {
        at: 0.55, name: '毒の潮', tint: [0.8, 1.0, 0.7], dmgMul: 1.2, speedMul: 1.12,
        addAttacks: [{ id: 'queen_wave', range: [2.0, 26], weight: 1.4, cooldown: 3.2, recovery: 0.8 }],
        aggression: 0.75,
      },
    ],
    reward: { souls: 9000, item: 'key_shard_2', extra: [['mat_chunk', 4], ['antidote', 5]] },
  },

  ironsworn: {
    id: 'ironsworn', title: '鉄の誓約者', subtitle: 'The Sworn of Iron',
    arch: {
      name: '鉄の誓約者', rig: 'humanoid', scale: 1.18,
      hp: 3800, damage: 118, defense: 36, poise: 110, souls: 14000,
      moveSpeed: 3.6, runSpeed: 6.6, turnRate: 10, mass: 2,
      height: 1.85, radius: 0.55,
      weapon: 'sword_oath', offhand: 'shield_oath',
      palette: {
        SKIN: [0.58, 0.46, 0.38], CLOTH: [0.28, 0.18, 0.18], ARMOR: [0.50, 0.48, 0.46],
        LEATHER: [0.28, 0.24, 0.20], ACCENT: [0.72, 0.58, 0.22], HAIR: [0.20, 0.16, 0.12],
      },
      ai: {
        preferredRange: 2.6, aggression: 0.78, patience: 0.6, sightRange: 40,
        leashRange: 0, groupRadius: 0, wanderRadius: 0,
        canBlock: true, canDodge: true, canParry: true, blockChance: 0.4, dodgeChance: 0.4,
        attacks: [
          { id: 'sword_l1', range: [0, 3.0], weight: 1.0, cooldown: 0.8, recovery: 0.35 },
          { id: 'oath_combo3', range: [0, 3.2], weight: 0.9, cooldown: 4.0, recovery: 1.0 },
          { id: 'oath_thrust', range: [2.5, 8.0], weight: 0.9, cooldown: 3.2, recovery: 0.7 },
          { id: 'sword_h1', range: [0.8, 3.2], weight: 0.6, cooldown: 4.4, recovery: 0.9 },
          { id: 'kick', range: [0, 2.2], weight: 0.35, cooldown: 5.0, recovery: 0.5 },
        ],
      },
      drops: [],
    },
    phases: [
      { at: 1.0 },
      {
        at: 0.60, name: '誓いの炎', tint: [1.0, 0.72, 0.45], dmgMul: 1.22, speedMul: 1.15,
        weaponGlow: 0.6, aggression: 0.9,
        addAttacks: [
          { id: 'oath_flame', range: [2.0, 14], weight: 1.0, cooldown: 6.0, recovery: 1.0 },
          { id: 'oath_leap', range: [4.0, 12], weight: 0.9, cooldown: 7.0, recovery: 1.2 },
        ],
      },
      {
        at: 0.25, name: '最後の誓い', tint: [1.0, 0.55, 0.35], dmgMul: 1.45, speedMul: 1.3,
        weaponGlow: 1.0, aggression: 1.0,
      },
    ],
    reward: { souls: 14000, item: 'key_shard_3', extra: [['mat_core', 2], ['sword_oath', 1]] },
  },

  drake: {
    id: 'drake', title: '断崖の竜', subtitle: 'The Cragfall Drake',
    arch: {
      name: '断崖の竜', rig: 'winged', scale: 1.75,
      hp: 5200, damage: 132, defense: 40, poise: 220, souls: 22000,
      moveSpeed: 3.4, runSpeed: 6.2, turnRate: 4.0, mass: 8,
      height: 2.4, radius: 1.35,
      palette: {
        ARMOR: [0.34, 0.36, 0.42], LEATHER: [0.30, 0.28, 0.36], DARK: [0.16, 0.16, 0.20],
        CLOTH: [0.28, 0.30, 0.36], ACCENT: [0.72, 0.66, 0.30],
      },
      ai: {
        preferredRange: 4.6, aggression: 0.7, patience: 0.8, sightRange: 48,
        leashRange: 0, groupRadius: 0, wanderRadius: 0,
        attacks: [
          { id: 'drake_bite', range: [0, 6.0], weight: 1.0, cooldown: 1.8, recovery: 0.7 },
          { id: 'drake_tail', range: [0, 6.5], weight: 0.9, cooldown: 3.0, recovery: 0.9 },
          { id: 'drake_wing', range: [0, 5.5], weight: 0.8, cooldown: 3.4, recovery: 0.9 },
          { id: 'drake_stomp', range: [0, 5.0], weight: 0.7, cooldown: 4.5, recovery: 1.1 },
          { id: 'drake_breath', range: [5.0, 26], weight: 1.0, cooldown: 6.5, recovery: 1.5 },
        ],
      },
      drops: [],
    },
    phases: [
      { at: 1.0 },
      {
        at: 0.50, name: '天翔る', tint: [1.0, 0.9, 0.7], dmgMul: 1.25, speedMul: 1.1, aggression: 0.9,
        addAttacks: [
          { id: 'drake_takeoff', range: [3.0, 30], weight: 0.9, cooldown: 14.0, recovery: 2.0 },
          { id: 'drake_breath', range: [4.0, 30], weight: 1.4, cooldown: 4.5, recovery: 1.2 },
        ],
      },
    ],
    reward: { souls: 22000, item: 'key_shard_4', extra: [['mat_core', 3], ['spear_drake', 1]] },
  },

  ashking: {
    id: 'ashking', title: '灰の王', subtitle: 'The Ash King',
    arch: {
      name: '灰の王', rig: 'humanoid', scale: 1.72,
      hp: 6800, damage: 156, defense: 44, poise: 200, souls: 34000,
      moveSpeed: 3.2, runSpeed: 6.0, turnRate: 5.5, mass: 5,
      height: 2.0, radius: 0.85,
      weapon: 'great_cinder', offhand: null,
      palette: {
        SKIN: [0.30, 0.24, 0.24], CLOTH: [0.26, 0.20, 0.20], ARMOR: [0.34, 0.26, 0.24],
        LEATHER: [0.24, 0.18, 0.17], HAIR: [0.56, 0.24, 0.12], ACCENT: [0.92, 0.42, 0.16], DARK: [0.14, 0.11, 0.10],
      },
      emissive: 0.22,
      ai: {
        preferredRange: 3.4, aggression: 0.8, patience: 0.7, sightRange: 44,
        leashRange: 0, groupRadius: 0, wanderRadius: 0,
        attacks: [
          { id: 'king_combo', range: [0, 4.6], weight: 1.0, cooldown: 3.0, recovery: 0.9 },
          { id: 'sentinel_sweep', range: [0, 4.4], weight: 0.9, cooldown: 2.0, recovery: 0.7 },
          { id: 'king_wave', range: [3.0, 18], weight: 0.9, cooldown: 5.0, recovery: 1.0 },
          { id: 'king_erupt', range: [2.0, 16], weight: 0.7, cooldown: 8.0, recovery: 1.4 },
          { id: 'king_grab', range: [0, 4.0], weight: 0.4, cooldown: 10.0, recovery: 1.2 },
        ],
      },
      drops: [],
    },
    phases: [
      { at: 1.0 },
      {
        at: 0.65, name: '灰の奔流', tint: [1.0, 0.7, 0.4], dmgMul: 1.2, speedMul: 1.12, aggression: 0.9,
        weaponGlow: 0.8,
        addAttacks: [{ id: 'king_erupt', range: [1.0, 20], weight: 1.3, cooldown: 5.0, recovery: 1.0 }],
      },
      {
        at: 0.30, name: '王の激怒', tint: [1.0, 0.5, 0.25], dmgMul: 1.5, speedMul: 1.3, aggression: 1.0,
        weaponGlow: 1.4,
        addAttacks: [{ id: 'king_wave', range: [1.0, 24], weight: 1.6, cooldown: 3.0, recovery: 0.8 }],
      },
    ],
    reward: { souls: 34000, item: 'key_shard_5', extra: [['mat_emberheart', 2], ['great_cinder', 1]] },
  },

  sovereign: {
    id: 'sovereign', title: '残り火の王', subtitle: 'The Ember Sovereign',
    arch: {
      name: '残り火の王', rig: 'humanoid', scale: 1.42,
      hp: 9500, damage: 178, defense: 50, poise: 170, souls: 80000,
      moveSpeed: 3.8, runSpeed: 7.4, turnRate: 9, mass: 3.5,
      height: 1.95, radius: 0.62,
      weapon: 'sword_oath', offhand: null,
      palette: {
        SKIN: [0.72, 0.66, 0.58], CLOTH: [0.30, 0.28, 0.34], ARMOR: [0.72, 0.68, 0.58],
        LEATHER: [0.34, 0.30, 0.26], HAIR: [0.86, 0.78, 0.60], ACCENT: [1.0, 0.72, 0.30], DARK: [0.20, 0.18, 0.16],
      },
      emissive: 0.28,
      ai: {
        preferredRange: 2.8, aggression: 0.85, patience: 0.55, sightRange: 50,
        leashRange: 0, groupRadius: 0, wanderRadius: 0,
        canDodge: true, dodgeChance: 0.4, canBlock: false,
        attacks: [
          { id: 'sov_combo4', range: [0, 3.6], weight: 1.0, cooldown: 4.0, recovery: 1.0 },
          { id: 'sword_h2', range: [2.5, 8.0], weight: 0.9, cooldown: 2.8, recovery: 0.6 },
          { id: 'oath_thrust', range: [3.0, 10], weight: 0.9, cooldown: 3.0, recovery: 0.7 },
          { id: 'sov_judgement', range: [2.0, 22], weight: 0.7, cooldown: 8.0, recovery: 1.3 },
        ],
      },
      drops: [],
    },
    phases: [
      { at: 1.0 },
      {
        at: 0.70, name: '第二の火', tint: [1.0, 0.85, 0.6], dmgMul: 1.15, speedMul: 1.12,
        weaponGlow: 0.8, aggression: 0.92,
        addAttacks: [{ id: 'oath_flame', range: [2.0, 16], weight: 1.1, cooldown: 5.0, recovery: 0.9 }],
      },
      {
        at: 0.42, name: '王冠の重み', tint: [1.0, 0.65, 0.42], dmgMul: 1.32, speedMul: 1.22,
        weaponGlow: 1.2, aggression: 0.96,
        addAttacks: [
          { id: 'sov_rain', range: [3.0, 30], weight: 1.0, cooldown: 10.0, recovery: 1.6 },
          { id: 'oath_leap', range: [4.0, 14], weight: 1.0, cooldown: 6.0, recovery: 1.1 },
        ],
      },
      {
        at: 0.18, name: '灰よ、還れ', tint: [1.0, 0.45, 0.30], dmgMul: 1.6, speedMul: 1.38,
        weaponGlow: 2.0, aggression: 1.0,
        addAttacks: [{ id: 'sov_judgement', range: [1.0, 28], weight: 1.8, cooldown: 5.0, recovery: 1.0 }],
      },
    ],
    reward: { souls: 80000, item: null, extra: [['mat_emberheart', 5]], ending: true },
  },
};

// Mini-bosses reuse ordinary archetypes with boosted numbers.
export const MINI_BOSSES = {
  bandit_chief: { base: 'bandit', name: '野盗の首魁', hpMul: 3.4, dmgMul: 1.5, scaleMul: 1.18, souls: 900, drop: ['axe_bandit', 1] },
  wolf_alpha: { base: 'ashwolf', name: '狼の長', hpMul: 4.0, dmgMul: 1.6, scaleMul: 1.45, souls: 1200, drop: ['tal_wolf', 1] },
  sentinel_captain: { base: 'sentinel', name: '哨戒隊長', hpMul: 2.8, dmgMul: 1.4, scaleMul: 1.12, souls: 3200, drop: ['tal_stone', 1] },
  wraith_lord: { base: 'wraith', name: '灰の主', hpMul: 3.0, dmgMul: 1.5, scaleMul: 1.2, souls: 5400, drop: ['tal_lastlight', 1] },
};

// Register boss archetypes so Enemy can construct them by id.
for (const key in BOSSES) {
  ARCHETYPES[`boss_${key}`] = BOSSES[key].arch;
}

// ---------------------------------------------------------------------------

export class Boss extends Enemy {
  constructor(game, bossId, opts = {}) {
    const def = BOSSES[bossId];
    super(game, `boss_${bossId}`, { ...opts, level: opts.level || 1 });
    this.bossId = bossId;
    this.def = def;
    this.phases = def.phases;
    this.phaseIndex = 0;
    this.isBoss = true;
    this.noCritical = false;
    this.arenaX = opts.x;
    this.arenaZ = opts.z;
    this.arenaRadius = opts.arenaRadius || 30;
    this.baseAttacks = def.arch.ai.attacks.slice();
    this.transitioning = false;
    this.introDone = false;
    this.phaseTint = [1, 1, 1];
    this.weaponGlow = 0;
    this.brain.setHome(opts.x, opts.z);
    this.brain.cfg.leashRange = 0;
    this.brain.state = AI_STATE.SLEEP;
    this.noPush = true;
  }

  /** The player entered the fog — wake up and play the intro. */
  begin() {
    if (this.introDone) return;
    this.introDone = true;
    this.brain.state = AI_STATE.CHASE;
    this.brain.target = this.game.player;
    this.setState(STATE.TAUNT, { duration: 1.6 });
    this.invuln = 1.6;
    this.game.onBossBegin?.(this);
  }

  update(dt) {
    if (!this.introDone) {
      // Idle in place until engaged.
      this.intentSpeed = 0;
      super.update(dt);
      return;
    }
    this._checkPhase();
    if (this.transitioning) {
      this.intentSpeed = 0;
      this.invuln = Math.max(this.invuln, 0.05);
    }
    super.update(dt);
    this._handleBossSpecial(dt);
    this._constrainToArena();
  }

  _constrainToArena() {
    const dx = this.x - this.arenaX, dz = this.z - this.arenaZ;
    const d = Math.hypot(dx, dz);
    if (d > this.arenaRadius) {
      this.x = this.arenaX + (dx / d) * this.arenaRadius;
      this.z = this.arenaZ + (dz / d) * this.arenaRadius;
    }
  }

  _checkPhase() {
    const ratio = this.hp / this.maxHp;
    const next = this.phaseIndex + 1;
    if (next >= this.phases.length) return;
    if (ratio > this.phases[next].at) return;

    const phase = this.phases[next];
    this.phaseIndex = next;
    this.transitioning = true;
    this.setState(STATE.TAUNT, { duration: 1.9 });
    this.invuln = 1.9;
    this.poise = this.maxPoise;

    // Multipliers are applied against the archetype base, not the running
    // value, so successive phases do not compound into absurd numbers.
    this.baseDamage = this.arch.damage * (1 + (this.level - 1) * 0.062) * (phase.dmgMul || 1);
    if (phase.speedMul) {
      this.moveSpeed = this.arch.moveSpeed * phase.speedMul;
      this.runSpeed = this.arch.runSpeed * phase.speedMul;
      this.turnRate = this.arch.turnRate * Math.min(phase.speedMul, 1.3);
    }
    if (phase.aggression !== undefined) this.brain.cfg.aggression = phase.aggression;
    if (phase.addAttacks) {
      this.brain.cfg.attacks = this.baseAttacks.concat(phase.addAttacks);
    }
    if (phase.tint) this.phaseTint = phase.tint;
    if (phase.weaponGlow !== undefined) this.weaponGlow = phase.weaponGlow;

    // Shockwave that clears the space around the boss.
    this.game.areaEffects.push(new AreaEffect(this.game, {
      x: this.x, y: this.y, z: this.z, radius: 6.5, delay: 0, duration: 0.4,
      damage: this.baseDamage * 0.5, poise: 60, type: 'physical',
      source: this, faction: this.faction, color: phase.tint || [1, 0.7, 0.3],
      telegraph: false, knockback: 9,
    }));
    this.game.shake(0.9, 0.7);
    this.game.onBossPhase?.(this, phase, next);

    this.game.schedule(1.9, () => { this.transitioning = false; });
  }

  _handleBossSpecial(dt) {
    if (this.state !== STATE.ATTACK || !this.action) return;
    const def = this.action;
    if (!def.special) {
      // Multi-hit windows.
      for (const key of ['hit2', 'hit3', 'hit4']) {
        const w = def[key];
        if (!w) continue;
        if (this.actionU >= w[0] && this.actionU <= w[1]) {
          if (this._lastWindow !== key) { this._lastWindow = key; this.hitSet.clear(); }
          this.hitActive = true;
        }
      }
      if (this.actionU < 0.05) this._lastWindow = null;
      return;
    }
    if (this._firedSpecial) {
      if (this.actionU < 0.05) this._firedSpecial = false;
      return;
    }
    if (this.actionU < 0.45) return;
    this._firedSpecial = true;
    this._fireSpecial(def.special, def);
  }

  _fireSpecial(kind, def) {
    const g = this.game;
    const t = this.brain.target || g.player;
    const dmg = this.baseDamage * (def.dmg || 1);

    switch (kind) {
      case 'roots': {
        // A ring of delayed spikes around the player, leaving gaps to dodge.
        const cx = t ? t.x : this.x, cz = t ? t.z : this.z;
        for (let i = 0; i < 7; i++) {
          const a = (i / 7) * TAU + Math.random() * 0.4;
          const r = 2.0 + Math.random() * 4.5;
          g.areaEffects.push(new AreaEffect(g, {
            x: cx + Math.cos(a) * r, y: g.world.heightAt(cx + Math.cos(a) * r, cz + Math.sin(a) * r),
            z: cz + Math.sin(a) * r,
            radius: 2.1, delay: 0.55 + i * 0.09, duration: 0.35,
            damage: dmg * 0.55, poise: 40, type: 'physical',
            source: this, faction: this.faction, color: [0.42, 0.52, 0.26],
          }));
        }
        break;
      }
      case 'poison_wave': {
        const base = Math.atan2((t ? t.x : this.x) - this.x, (t ? t.z : this.z) - this.z);
        for (let i = 0; i < 12; i++) {
          const a = base + (i - 5.5) * 0.13;
          g.projectiles.push(new Projectile(g, {
            x: this.x, y: this.y + 1.2, z: this.z,
            vx: Math.sin(a) * 15, vy: 1.5, vz: Math.cos(a) * 15,
            damage: dmg * 0.35, poise: 16, type: 'poison',
            source: this, faction: this.faction, gravity: -2.5,
            color: [0.5, 0.72, 0.32], size: 0.4, radius: 0.5, kind: 'orb', life: 2.6,
            status: { type: 'poison', build: 18 },
          }));
        }
        break;
      }
      case 'summon': {
        for (let i = 0; i < 3; i++) {
          const a = Math.random() * TAU;
          const r = 5 + Math.random() * 6;
          g.spawnEnemy('mireleech', this.x + Math.cos(a) * r, this.z + Math.sin(a) * r, {
            level: this.level, summoned: true,
          });
        }
        g.notify('女王が眷属を呼んだ');
        break;
      }
      case 'flame_arc': {
        const base = Math.atan2((t ? t.x : this.x) - this.x, (t ? t.z : this.z) - this.z);
        for (let i = 0; i < 9; i++) {
          const a = base + (i - 4) * 0.16;
          const dist = 4 + i * 0.0;
          g.areaEffects.push(new AreaEffect(g, {
            x: this.x + Math.sin(a) * 5.5, y: this.y, z: this.z + Math.cos(a) * 5.5,
            radius: 1.9, delay: 0.3, duration: 0.3,
            damage: dmg * 0.5, poise: 30, type: 'fire',
            source: this, faction: this.faction, color: [1, 0.55, 0.2],
          }));
        }
        break;
      }
      case 'fire_wave': {
        // An expanding ring — jump or roll through the gap.
        for (let ring = 0; ring < 3; ring++) {
          const R = 4.5 + ring * 3.6;
          const count = 8 + ring * 4;
          for (let i = 0; i < count; i++) {
            const a = (i / count) * TAU + ring * 0.2;
            g.areaEffects.push(new AreaEffect(g, {
              x: this.x + Math.cos(a) * R, y: this.y, z: this.z + Math.sin(a) * R,
              radius: 2.3, delay: 0.25 + ring * 0.30, duration: 0.28,
              damage: dmg * 0.45, poise: 34, type: 'fire',
              source: this, faction: this.faction, color: [1, 0.45, 0.15],
            }));
          }
        }
        break;
      }
      case 'eruption': {
        const cx = t ? t.x : this.x, cz = t ? t.z : this.z;
        for (let i = 0; i < 5; i++) {
          const a = Math.random() * TAU;
          const r = i === 0 ? 0 : 2 + Math.random() * 5;
          const px = cx + Math.cos(a) * r, pz = cz + Math.sin(a) * r;
          g.areaEffects.push(new AreaEffect(g, {
            x: px, y: g.world.heightAt(px, pz), z: pz,
            radius: 3.0, delay: 0.6 + i * 0.22, duration: 0.35,
            damage: dmg * 0.7, poise: 45, type: 'fire',
            source: this, faction: this.faction, color: [1, 0.4, 0.12],
          }));
        }
        break;
      }
      case 'judgement': {
        // A slow tracking pillar the player must keep moving to avoid.
        const cx = t ? t.x : this.x, cz = t ? t.z : this.z;
        g.areaEffects.push(new AreaEffect(g, {
          x: cx, y: g.world.heightAt(cx, cz), z: cz,
          radius: 4.6, delay: 1.0, duration: 0.5,
          damage: dmg * 1.4, poise: 90, type: 'holy',
          source: this, faction: this.faction, color: [1, 0.9, 0.55], knockback: 8,
        }));
        break;
      }
      case 'rain': {
        for (let i = 0; i < 14; i++) {
          const a = Math.random() * TAU;
          const r = Math.sqrt(Math.random()) * 16;
          const px = this.arenaX + Math.cos(a) * r;
          const pz = this.arenaZ + Math.sin(a) * r;
          g.areaEffects.push(new AreaEffect(g, {
            x: px, y: g.world.heightAt(px, pz), z: pz,
            radius: 2.4, delay: 0.5 + i * 0.13, duration: 0.3,
            damage: dmg * 0.5, poise: 30, type: 'fire',
            source: this, faction: this.faction, color: [1, 0.7, 0.35],
          }));
        }
        break;
      }
      case 'takeoff': {
        this.airborne = true;
        this.velY = 9;
        this.grounded = false;
        g.schedule(2.0, () => {
          this.airborne = false;
        });
        break;
      }
      default: break;
    }
  }

  render(batches) {
    const t = this.phaseTint;
    const prev = this.emissive;
    this.emissive = prev + this.weaponGlow * 0.10;
    const box = batches.get('box');
    const opts = {
      tintR: t[0] * (1 + this.flash * 1.4),
      tintG: t[1] * (1 - this.flash * 0.3),
      tintB: t[2] * (1 - this.flash * 0.3),
      alpha: 1,
      emissive: this.emissive,
    };
    this.rig.render(box, this.palette, opts);
    if (this.weaponGlow > 0 && this.weapon) {
      const saved = this.weapon.shape.glow;
      this.weapon.shape.glow = Math.max(saved || 0, this.weaponGlow);
      this._renderEquipment(batches, opts);
      this.weapon.shape.glow = saved;
    } else {
      this._renderEquipment(batches, opts);
    }
    this.emissive = prev;
  }

  die(killer) {
    if (this.dead) return;
    super.die(killer);
    this.game.onBossDefeated?.(this);
  }
}

export function createMiniBoss(game, kind, x, z, level) {
  const cfg = MINI_BOSSES[kind];
  if (!cfg) return null;
  const e = new Enemy(game, cfg.base, {
    x, z, level,
    hpMul: cfg.hpMul, dmgMul: cfg.dmgMul, scaleMul: cfg.scaleMul,
    soulsMul: 1,
  });
  e.name = cfg.name;
  e.soulsValue = Math.round(cfg.souls * (1 + (level - 1) * 0.12));
  e.isMiniBoss = true;
  e.maxPoise *= 1.8;
  e.poise = e.maxPoise;
  if (cfg.drop) e.dropTable = e.dropTable.concat([[cfg.drop[0], 1.0, cfg.drop[1]]]);
  e.brain.cfg.leashRange = 45;
  return e;
}
