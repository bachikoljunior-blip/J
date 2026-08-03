// ============================================================================
//  bosses.js — named encounters.
//
//  A boss is an Enemy with three additions: phase thresholds that rewrite its
//  moveset mid-fight, a transition state that is invulnerable and readable,
//  and a health bar the game shows while it is engaged. Phases are where the
//  drama lives — the same arena has to feel different at 40% than at 100%.
// ============================================================================

import { ARCHETYPES, Enemy, ENEMY_ATTACKS, resolveAI } from './enemies.js';
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
  sov_shatter: { dur: 2.20, hit: [0.5, 0.52], stam: 38, dmg: 1.0, poise: 70, motion: 0, special: 'shatter', pose: (r, u) => ATTACKS.great_h1.pose(r, u) },
  king_ashstorm: { dur: 2.30, hit: [0.5, 0.52], stam: 36, dmg: 1.0, poise: 60, motion: 0, special: 'ash_storm', pose: (r, u) => ATTACKS.cast.pose(r, u) },

  // --- bell keeper ---------------------------------------------------------
  bell_call: { dur: 2.60, hit: [0.5, 0.52], stam: 26, dmg: 0, poise: 40, motion: 0, special: 'bell_call', pose: (r, u) => ATTACKS.cast.pose(r, u) },
  bell_wave: { dur: 2.00, hit: [0.5, 0.52], stam: 30, dmg: 1.0, poise: 55, motion: 0, special: 'bell_wave', pose: (r, u) => ATTACKS.great_l1.pose(r, u) },
  bell_flail: {
    dur: 1.95, stam: 32, dmg: 1.3, poise: 50, motion: 2.2,
    hit: [0.22, 0.36], hit2: [0.56, 0.70], hit3: [0.84, 0.94],
    pose: (r, u) => (u < 0.34 ? ATTACKS.axe_h2.pose(r, u * 2.9)
      : u < 0.68 ? ATTACKS.axe_l1.pose(r, (u - 0.34) * 3.0)
        : ATTACKS.axe_h1.pose(r, (u - 0.68) * 3.1)),
  },
  bell_clapper: { dur: 1.40, hit: [0.44, 0.64], stam: 28, dmg: 1.9, poise: 65, motion: 3.4, aoe: { radius: 3.4, at: 0.52 }, pose: (r, u) => ATTACKS.great_h1.pose(r, u) },

  // --- root father ---------------------------------------------------------
  root_lash: { dur: 1.20, hit: [0.32, 0.60], stam: 22, dmg: 1.3, poise: 42, motion: 3.6, pose: (r, u) => ATTACKS.spear_l3.pose(r, u) },
  root_thorns: { dur: 2.40, hit: [0.5, 0.52], stam: 32, dmg: 1.0, poise: 50, motion: 0, special: 'thorn_ring', pose: (r, u) => ATTACKS.cast.pose(r, u) },
  root_seed: { dur: 2.50, hit: [0.5, 0.52], stam: 28, dmg: 0, poise: 40, motion: 0, special: 'seedlings', pose: (r, u) => ATTACKS.cast.pose(r, u) },
  root_uproot: { dur: 2.00, hit: [0.30, 0.68], stam: 36, dmg: 1.8, poise: 90, motion: 12.0, pose: (r, u) => ATTACKS.great_h2.pose(r, u) },

  // --- sunken choir --------------------------------------------------------
  choir_note: { dur: 1.30, hit: [0.5, 0.52], stam: 16, dmg: 1.0, poise: 14, motion: 0, ranged: 'bolt', pose: (r, u) => ATTACKS.cast.pose(r, u) },
  choir_chord: { dur: 2.20, hit: [0.5, 0.52], stam: 34, dmg: 1.0, poise: 55, motion: 0, special: 'chord', pose: (r, u) => ATTACKS.cast.pose(r, u) },
  choir_dirge: { dur: 2.80, hit: [0.5, 0.52], stam: 34, dmg: 0, poise: 45, motion: 0, special: 'dirge', pose: (r, u) => ATTACKS.cast.pose(r, u) },
  choir_hush: { dur: 1.10, hit: [0.34, 0.54], stam: 20, dmg: 1.4, poise: 34, motion: 5.0, pose: (r, u) => ATTACKS.sword_h2.pose(r, u) },

  // --- frost jarl ----------------------------------------------------------
  jarl_hew: { dur: 1.45, hit: [0.44, 0.66], stam: 32, dmg: 1.9, poise: 65, motion: 2.6, pose: (r, u) => ATTACKS.great_l1.pose(r, u) },
  jarl_nova: { dur: 2.05, hit: [0.5, 0.52], stam: 34, dmg: 1.0, poise: 60, motion: 0, special: 'frost_nova', pose: (r, u) => ATTACKS.great_h1.pose(r, u) },
  jarl_field: { dur: 2.40, hit: [0.5, 0.52], stam: 32, dmg: 1.0, poise: 50, motion: 0, special: 'ice_field', pose: (r, u) => ATTACKS.cast.pose(r, u) },
  jarl_charge: { dur: 1.85, hit: [0.26, 0.64], stam: 34, dmg: 1.7, poise: 85, motion: 13.5, pose: (r, u) => ATTACKS.spear_h1.pose(r, u) },

  // --- ember widow ---------------------------------------------------------
  widow_veil: { dur: 1.75, hit: [0.5, 0.52], stam: 26, dmg: 1.0, poise: 45, motion: 0, special: 'aura', pose: (r, u) => ATTACKS.cast.pose(r, u) },
  widow_martyrs: { dur: 2.60, hit: [0.5, 0.52], stam: 32, dmg: 0, poise: 45, motion: 0, special: 'martyrs', pose: (r, u) => ATTACKS.cast.pose(r, u) },
  widow_pyres: { dur: 2.20, hit: [0.5, 0.52], stam: 32, dmg: 1.0, poise: 55, motion: 0, special: 'pyres', pose: (r, u) => ATTACKS.cast.pose(r, u) },
  widow_rend: {
    dur: 1.55, stam: 28, dmg: 1.15, poise: 30, motion: 4.0,
    hit: [0.18, 0.30], hit2: [0.50, 0.64],
    pose: (r, u) => (u < 0.5 ? ATTACKS.dagger_l1.pose(r, u * 2) : ATTACKS.dagger_l3.pose(r, (u - 0.5) * 2)),
  },

  // --- mini-boss movesets --------------------------------------------------
  chief_flurry: {
    dur: 1.75, stam: 28, dmg: 0.95, poise: 22, motion: 2.2,
    hit: [0.16, 0.28], hit2: [0.44, 0.56], hit3: [0.74, 0.88],
    pose: (r, u) => (u < 0.34 ? ATTACKS.sword_l1.pose(r, u * 2.9)
      : u < 0.68 ? ATTACKS.sword_l2.pose(r, (u - 0.34) * 3.0)
        : ATTACKS.dagger_h1.pose(r, (u - 0.68) * 3.1)),
  },
  chief_whistle: { dur: 1.60, hit: [0.5, 0.52], stam: 16, dmg: 0, poise: 30, motion: 0, special: 'call', pose: (r, u) => ATTACKS.cast.pose(r, u) },
  chief_shoulder: { dur: 1.05, hit: [0.28, 0.44], stam: 22, dmg: 1.1, poise: 60, motion: 7.5, pose: (r, u) => ATTACKS.kick.pose(r, u) },

  alpha_howl: { dur: 1.90, hit: [0.5, 0.52], stam: 20, dmg: 0, poise: 40, motion: 0, special: 'howl', pose: noop },
  alpha_rip: { dur: 0.92, hit: [0.26, 0.52], stam: 16, dmg: 1.35, poise: 28, motion: 5.4, pose: noop },
  alpha_run: { dur: 1.45, hit: [0.24, 0.70], stam: 26, dmg: 1.5, poise: 45, motion: 16.0, pose: noop },

  captain_shed: { dur: 1.70, hit: [0.5, 0.52], stam: 18, dmg: 0, poise: 40, motion: 0, special: 'shed', pose: noop },
  captain_line: { dur: 1.30, hit: [0.32, 0.52], stam: 26, dmg: 1.4, poise: 60, motion: 9.0, pose: (r, u) => ATTACKS.spear_h1.pose(r, u) },
  captain_reap: { dur: 1.15, hit: [0.24, 0.62], stam: 28, dmg: 1.55, poise: 44, motion: 1.8, pose: (r, u) => ATTACKS.great_h2.pose(r, u) },

  lord_blink: { dur: 1.30, hit: [0.5, 0.52], stam: 18, dmg: 0, poise: 40, motion: 0, special: 'blink', pose: (r, u) => ATTACKS.cast.pose(r, u) },
  lord_cinders: { dur: 1.85, hit: [0.5, 0.52], stam: 28, dmg: 1.0, poise: 50, motion: 0, special: 'flame_arc', pose: (r, u) => ATTACKS.cast.pose(r, u) },
  lord_rend: { dur: 0.80, hit: [0.24, 0.46], stam: 16, dmg: 1.25, poise: 22, motion: 5.4, pose: (r, u) => ATTACKS.sword_l2.pose(r, u) },
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
        addAttacks: [
          { id: 'warden_roots', range: [2.0, 22], weight: 1.3, cooldown: 5.5, recovery: 1.0 },
          { id: 'root_seed', range: [4.0, 24], weight: 0.7, cooldown: 18.0, recovery: 1.6 },
        ],
        // The floor stops being neutral: roots surface where you were standing.
        hazard: { every: 3.4, radius: 2.2, damage: 0.5, type: 'physical', color: [0.42, 0.52, 0.26], delay: 0.9, spread: 0.85 },
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
        addAttacks: [
          { id: 'queen_wave', range: [2.0, 26], weight: 1.4, cooldown: 3.2, recovery: 0.8 },
          { id: 'choir_chord', range: [4.0, 24], weight: 0.8, cooldown: 9.0, recovery: 1.3 },
        ],
        // Standing water rises: half the arena becomes a place you cannot rest.
        hazard: { every: 2.6, radius: 2.6, damage: 0.35, type: 'poison', color: [0.5, 0.72, 0.32], delay: 1.1, spread: 1.0, status: { type: 'poison', build: 14 } },
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
        // It stops attacking into your attacks and starts waiting for them.
        addAttacks: [
          { id: 'duel_stance', range: [0, 4.5], weight: 1.2, cooldown: 6.0, recovery: 0.3 },
          { id: 'duel_punish', range: [0, 3.8], weight: 1.0, cooldown: 1.4, recovery: 0.4 },
        ],
        hazard: { every: 3.0, radius: 2.4, damage: 0.45, type: 'fire', color: [1, 0.55, 0.22], delay: 0.8, spread: 0.9 },
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
          { id: 'drake_dive', range: [8.0, 26], weight: 1.0, cooldown: 8.0, recovery: 1.6 },
        ],
        // The shelf starts coming down. Standing under the overhang stops working.
        hazard: { every: 2.2, radius: 2.0, damage: 0.55, type: 'physical', color: [0.55, 0.52, 0.48], delay: 0.7, spread: 1.0 },
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
        addAttacks: [
          { id: 'king_wave', range: [1.0, 24], weight: 1.6, cooldown: 3.0, recovery: 0.8 },
          { id: 'king_ashstorm', range: [0, 30], weight: 1.0, cooldown: 12.0, recovery: 1.6 },
        ],
        // Ash falls across the whole arena; there is no safe corner left.
        hazard: { every: 1.9, radius: 2.4, damage: 0.42, type: 'fire', color: [1, 0.48, 0.16], delay: 0.75, spread: 1.0 },
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
        addAttacks: [
          { id: 'sov_judgement', range: [1.0, 28], weight: 1.8, cooldown: 5.0, recovery: 1.0 },
          { id: 'sov_shatter', range: [0, 30], weight: 1.1, cooldown: 11.0, recovery: 1.5 },
        ],
        // The arena floor breaks into pillars of light. Movement is the fight.
        hazard: { every: 1.7, radius: 2.2, damage: 0.5, type: 'holy', color: [1, 0.9, 0.6], delay: 0.7, spread: 1.0 },
      },
    ],
    reward: { souls: 80000, item: null, extra: [['mat_emberheart', 5]], ending: true },
  },

  // -------------------------------------------------------------------------
  //  Optional bosses. None of them gate the main chain; each one exists to
  //  teach or reward a specific way of playing, and each one has a phase that
  //  invalidates the plan that got the player through the previous phase.
  // -------------------------------------------------------------------------

  bellkeeper: {
    id: 'bellkeeper', title: '鐘楼の番人', subtitle: 'The Keeper of the Bell',
    optional: true, region: 'ridge',
    arch: {
      name: '鐘楼の番人', rig: 'humanoid', scale: 1.48,
      hp: 4200, damage: 96, defense: 30, poise: 140, souls: 16000,
      moveSpeed: 2.4, runSpeed: 4.2, turnRate: 4.0, mass: 4,
      height: 1.9, radius: 0.78,
      weapon: 'hammer_bell', offhand: null,
      palette: {
        SKIN: [0.48, 0.42, 0.34], CLOTH: [0.28, 0.26, 0.20], ARMOR: [0.60, 0.52, 0.28],
        LEATHER: [0.30, 0.26, 0.18], ACCENT: [0.82, 0.70, 0.34], HAIR: [0.30, 0.28, 0.24], DARK: [0.18, 0.16, 0.12],
      },
      emissive: 0.10,
      ai: {
        preferredRange: 3.2, aggression: 0.5, patience: 1.3, sightRange: 40,
        leashRange: 0, groupRadius: 0, wanderRadius: 0, canBlock: false,
        attacks: [
          { id: 'bell_clapper', range: [0, 4.4], weight: 1.0, cooldown: 2.6, recovery: 0.9 },
          { id: 'sentinel_sweep', range: [0, 4.2], weight: 0.9, cooldown: 2.4, recovery: 0.8 },
          { id: 'bell_call', range: [0, 30], weight: 0.9, cooldown: 20.0, recovery: 1.6 },
        ],
      },
      drops: [],
    },
    phases: [
      { at: 1.0 },
      {
        // The bell cracks: what was a summon becomes a shockwave you must be
        // outside of, so the adds and the boss now demand opposite positions.
        at: 0.62, name: '鐘が裂ける', tint: [1.0, 0.92, 0.72], dmgMul: 1.15, speedMul: 1.08, aggression: 0.7,
        addAttacks: [
          { id: 'bell_wave', range: [0, 24], weight: 1.3, cooldown: 6.5, recovery: 1.2 },
          { id: 'bell_call', range: [0, 30], weight: 0.7, cooldown: 16.0, recovery: 1.4 },
        ],
      },
      {
        // It stops guarding the bell and starts swinging the clapper.
        at: 0.28, name: '番人であることをやめる', tint: [1.0, 0.78, 0.46], dmgMul: 1.35, speedMul: 1.30, aggression: 1.0,
        weaponGlow: 0.9,
        addAttacks: [
          { id: 'bell_flail', range: [0, 4.2], weight: 1.4, cooldown: 3.4, recovery: 1.0 },
          { id: 'bell_wave', range: [0, 24], weight: 1.0, cooldown: 5.0, recovery: 1.0 },
        ],
        hazard: { every: 2.8, radius: 2.6, damage: 0.4, type: 'holy', color: [1.0, 0.86, 0.5], delay: 0.8, spread: 0.9 },
      },
    ],
    reward: { souls: 16000, item: 'key_bellrope', extra: [['mat_bellbronze', 4], ['hammer_bell', 1], ['tal_bulwark', 1]] },
  },

  rootfather: {
    id: 'rootfather', title: '根の父', subtitle: 'The Father of Roots',
    optional: true, region: 'wood',
    arch: {
      name: '根の父', rig: 'humanoid', scale: 2.35,
      hp: 5000, damage: 104, defense: 24, poise: 220, souls: 19000,
      moveSpeed: 1.4, runSpeed: 2.2, turnRate: 1.8, mass: 8,
      height: 1.9, radius: 1.10,
      weapon: 'great_root', offhand: null,
      palette: {
        SKIN: [0.30, 0.34, 0.24], CLOTH: [0.20, 0.28, 0.16], ARMOR: [0.24, 0.30, 0.18],
        LEATHER: [0.26, 0.22, 0.14], HAIR: [0.34, 0.44, 0.24], ACCENT: [0.48, 0.58, 0.28], DARK: [0.12, 0.16, 0.10],
      },
      status: { type: 'poison', build: 28 },
      ai: {
        // Rooted: it cannot chase, so the fight is about whether you respect
        // the ground it can reach.
        preferredRange: 4.2, aggression: 0.45, patience: 1.6, sightRange: 44,
        leashRange: 0, groupRadius: 0, wanderRadius: 0, strafeSpeedMul: 0.2,
        attacks: [
          { id: 'root_lash', range: [0, 6.4], weight: 1.0, cooldown: 2.0, recovery: 0.8 },
          { id: 'warden_sweep', range: [0, 5.6], weight: 0.8, cooldown: 3.0, recovery: 0.9 },
          { id: 'root_seed', range: [3.0, 30], weight: 0.8, cooldown: 16.0, recovery: 1.6 },
          { id: 'warden_roots', range: [4.0, 26], weight: 0.9, cooldown: 8.0, recovery: 1.4 },
        ],
      },
      drops: [],
    },
    phases: [
      { at: 1.0 },
      {
        // Thorn walls close in: the arena the player has been kiting around
        // gets smaller than their kiting circle.
        at: 0.66, name: '囲い込む', tint: [0.86, 1.0, 0.78], dmgMul: 1.12, aggression: 0.6,
        addAttacks: [{ id: 'root_thorns', range: [0, 30], weight: 1.2, cooldown: 12.0, recovery: 1.6 }],
        hazard: { every: 3.2, radius: 2.4, damage: 0.4, type: 'poison', color: [0.44, 0.56, 0.26], delay: 1.0, spread: 1.0, status: { type: 'poison', build: 12 } },
      },
      {
        // It pulls itself out of the ground. Everything you learned about its
        // reach was about a thing that could not move.
        at: 0.30, name: '根を抜く', tint: [0.92, 0.86, 0.62], dmgMul: 1.30, speedMul: 2.6, aggression: 0.95,
        addAttacks: [
          { id: 'root_uproot', range: [5.0, 18], weight: 1.3, cooldown: 7.0, recovery: 1.5 },
          { id: 'warden_slam', range: [0, 5.4], weight: 1.0, cooldown: 4.0, recovery: 1.2 },
        ],
      },
    ],
    reward: { souls: 19000, item: 'key_rootheart', extra: [['mat_core', 3], ['great_root', 1], ['tal_hound', 1]] },
  },

  sunkenchoir: {
    id: 'sunkenchoir', title: '沈める合唱', subtitle: 'The Sunken Choir',
    optional: true, region: 'mire',
    arch: {
      name: '沈める合唱', rig: 'humanoid', scale: 1.34,
      hp: 3600, damage: 100, defense: 26, poise: 90, souls: 15000,
      moveSpeed: 3.4, runSpeed: 6.0, turnRate: 8, mass: 2,
      height: 1.9, radius: 0.58,
      weapon: 'staff_bone', offhand: null,
      palette: {
        SKIN: [0.52, 0.54, 0.50], CLOTH: [0.22, 0.24, 0.30], ARMOR: [0.74, 0.72, 0.66],
        LEATHER: [0.24, 0.24, 0.26], HAIR: [0.36, 0.36, 0.40], ACCENT: [0.62, 0.66, 0.86], DARK: [0.14, 0.14, 0.16],
      },
      emissive: 0.2,
      ai: {
        // A caster that will not let you sit at range, and punishes you for
        // closing with a hush that crosses the gap faster than you can.
        ranged: true, rangedMin: 5, rangedIdeal: 11,
        preferredRange: 11, aggression: 0.45, patience: 1.0, sightRange: 44,
        leashRange: 0, groupRadius: 0, wanderRadius: 0, canDodge: true, dodgeChance: 0.45,
        attacks: [
          { id: 'choir_note', range: [4, 26], weight: 1.0, cooldown: 2.2, recovery: 0.7 },
          { id: 'choir_chord', range: [5, 26], weight: 0.9, cooldown: 7.0, recovery: 1.2 },
          { id: 'choir_hush', range: [0, 6.0], weight: 1.0, cooldown: 3.0, recovery: 0.7 },
        ],
      },
      drops: [],
    },
    phases: [
      { at: 1.0 },
      {
        // It stops singing alone. The adds are the reason the chords land.
        at: 0.60, name: '二の声', tint: [0.82, 0.88, 1.0], dmgMul: 1.15, speedMul: 1.1, aggression: 0.6,
        addAttacks: [
          { id: 'choir_dirge', range: [0, 30], weight: 1.1, cooldown: 18.0, recovery: 1.8 },
          { id: 'hex_rune', range: [4, 26], weight: 0.9, cooldown: 6.0, recovery: 1.1 },
        ],
      },
      {
        // Third voice: it abandons range entirely and fights inside your reach.
        at: 0.26, name: '三の声', tint: [0.70, 0.80, 1.0], dmgMul: 1.35, speedMul: 1.34, aggression: 1.0,
        weaponGlow: 1.2,
        addAttacks: [
          { id: 'choir_hush', range: [0, 8.0], weight: 1.6, cooldown: 1.6, recovery: 0.5 },
          { id: 'sov_combo4', range: [0, 3.8], weight: 1.0, cooldown: 5.0, recovery: 1.0 },
        ],
        aiOverride: { ranged: false, rangedIdeal: 2.6, preferredRange: 2.6, rangedMin: 0 },
      },
    ],
    reward: { souls: 15000, item: null, extra: [['mat_core', 3], ['staff_glint', 1], ['tal_ember_deep', 1]] },
  },

  frostjarl: {
    id: 'frostjarl', title: '霜の司', subtitle: 'The Jarl of Hoar',
    optional: true, region: 'peak',
    arch: {
      name: '霜の司', rig: 'humanoid', scale: 1.66,
      hp: 6400, damage: 138, defense: 42, poise: 190, souls: 26000,
      moveSpeed: 2.8, runSpeed: 5.2, turnRate: 4.6, mass: 5,
      height: 2.0, radius: 0.84,
      weapon: 'great_frost', offhand: 'shield_tower',
      palette: {
        SKIN: [0.62, 0.68, 0.74], CLOTH: [0.30, 0.36, 0.44], ARMOR: [0.62, 0.70, 0.80],
        LEATHER: [0.28, 0.32, 0.38], HAIR: [0.82, 0.88, 0.94], ACCENT: [0.74, 0.88, 1.0], DARK: [0.18, 0.22, 0.28],
      },
      emissive: 0.12,
      status: { type: 'frost', build: 32 },
      resist: { magic: 0.4, fire: -0.25 },
      ai: {
        preferredRange: 3.0, aggression: 0.6, patience: 1.1, sightRange: 46,
        leashRange: 0, groupRadius: 0, wanderRadius: 0,
        canBlock: true, blockChance: 0.55,
        attacks: [
          { id: 'jarl_hew', range: [0, 4.6], weight: 1.0, cooldown: 2.2, recovery: 0.8 },
          { id: 'great_l2', range: [0, 4.4], weight: 0.9, cooldown: 2.0, recovery: 0.7 },
          { id: 'jarl_charge', range: [6.0, 16], weight: 0.9, cooldown: 6.5, recovery: 1.3 },
          { id: 'jarl_nova', range: [0, 6.0], weight: 0.8, cooldown: 8.0, recovery: 1.4 },
        ],
      },
      drops: [],
    },
    phases: [
      { at: 1.0 },
      {
        // Freezes the floor. Rolling still works; running in a straight line
        // does not, because the ice keeps carrying you into the next field.
        at: 0.58, name: '地を凍らせる', tint: [0.84, 0.94, 1.0], dmgMul: 1.18, speedMul: 1.1, aggression: 0.8,
        addAttacks: [
          { id: 'jarl_field', range: [0, 26], weight: 1.2, cooldown: 9.0, recovery: 1.4 },
          { id: 'jarl_nova', range: [0, 7.0], weight: 1.1, cooldown: 5.5, recovery: 1.1 },
        ],
        hazard: { every: 2.6, radius: 2.8, damage: 0.38, type: 'magic', color: [0.74, 0.9, 1.0], delay: 1.0, spread: 1.0, status: { type: 'frost', build: 14 } },
      },
      {
        // Drops the shield and closes. A turtle fight becomes a chase.
        at: 0.26, name: '盾を捨てる', tint: [0.70, 0.86, 1.0], dmgMul: 1.42, speedMul: 1.45, aggression: 1.0,
        weaponGlow: 1.4, dropOffhand: true,
        addAttacks: [
          { id: 'jarl_charge', range: [4.0, 20], weight: 1.5, cooldown: 4.0, recovery: 0.9 },
          { id: 'great_h2', range: [0, 4.4], weight: 1.2, cooldown: 3.6, recovery: 1.0 },
        ],
      },
    ],
    reward: { souls: 26000, item: 'key_coldvow', extra: [['mat_emberheart', 1], ['great_frost', 1], ['head_hoar', 1], ['body_hoar', 1]] },
  },

  emberwidow: {
    id: 'emberwidow', title: '燼の寡婦', subtitle: 'The Widow of Ash',
    optional: true, region: 'waste',
    arch: {
      name: '燼の寡婦', rig: 'humanoid', scale: 1.22,
      hp: 5600, damage: 126, defense: 34, poise: 80, souls: 24000,
      moveSpeed: 4.0, runSpeed: 7.6, turnRate: 11, mass: 1.4,
      height: 1.88, radius: 0.52,
      weapon: 'dagger_ritual', offhand: null,
      palette: {
        SKIN: [0.36, 0.28, 0.28], CLOTH: [0.20, 0.16, 0.16], ARMOR: [0.28, 0.20, 0.18],
        LEATHER: [0.22, 0.16, 0.14], HAIR: [0.62, 0.26, 0.14], ACCENT: [1.0, 0.48, 0.18], DARK: [0.12, 0.10, 0.10],
      },
      emissive: 0.24,
      resist: { fire: 0.6 },
      ai: {
        // Fast, fragile for its tier, and always trying to put something
        // between you and it. Killing the adds badly is how this one wins.
        preferredRange: 2.6, aggression: 0.75, patience: 0.5, sightRange: 44,
        leashRange: 0, groupRadius: 0, wanderRadius: 0,
        canDodge: true, dodgeChance: 0.55,
        attacks: [
          { id: 'widow_rend', range: [0, 3.2], weight: 1.0, cooldown: 1.8, recovery: 0.5 },
          { id: 'dagger_h1', range: [1.5, 5.0], weight: 0.9, cooldown: 2.2, recovery: 0.6 },
          { id: 'widow_martyrs', range: [0, 30], weight: 0.9, cooldown: 17.0, recovery: 1.6 },
          { id: 'widow_veil', range: [0, 6.0], weight: 0.7, cooldown: 8.0, recovery: 1.2 },
        ],
      },
      drops: [],
    },
    phases: [
      { at: 1.0 },
      {
        // Pyres mark the arena permanently. The space to fight the adds in
        // shrinks even though nothing is chasing you.
        at: 0.64, name: '弔いの火', tint: [1.0, 0.78, 0.5], dmgMul: 1.16, speedMul: 1.12, aggression: 0.85,
        addAttacks: [
          { id: 'widow_pyres', range: [0, 30], weight: 1.2, cooldown: 10.0, recovery: 1.4 },
          { id: 'widow_martyrs', range: [0, 30], weight: 1.0, cooldown: 12.0, recovery: 1.4 },
        ],
      },
      {
        // She stops sending martyrs and becomes one: aura up, permanently.
        at: 0.28, name: '自らを焚く', tint: [1.0, 0.52, 0.28], dmgMul: 1.45, speedMul: 1.32, aggression: 1.0,
        weaponGlow: 1.6,
        addAttacks: [
          { id: 'widow_veil', range: [0, 8.0], weight: 1.6, cooldown: 4.0, recovery: 0.8 },
          { id: 'oath_leap', range: [4.0, 13], weight: 1.1, cooldown: 5.5, recovery: 1.1 },
        ],
        hazard: { every: 2.0, radius: 2.3, damage: 0.46, type: 'fire', color: [1, 0.5, 0.18], delay: 0.7, spread: 0.8 },
      },
    ],
    reward: { souls: 24000, item: null, extra: [['mat_emberheart', 1], ['tal_finality', 1], ['dagger_venom', 1]] },
  },
};

// ---------------------------------------------------------------------------
//  Mini-bosses
//
//  These are not scaled-up commons. Each has its own moveset and its own
//  break: a single threshold at which it throws away the thing it has been
//  relying on and fights differently. That is the whole design brief — a
//  mini-boss should teach one idea that a real boss will later assume you
//  know, and it should be over before the idea gets boring.
// ---------------------------------------------------------------------------

export const MINI_BOSSES = {
  bandit_chief: {
    id: 'bandit_chief', name: '野盗の首魁', souls: 1400, drop: ['axe_twinmoon', 1],
    // Teaches: adds arrive mid-combo. Kill the caller or fight in a doorway.
    breakAt: 0.55, breakName: '仲間を呼ぶ',
    arch: {
      name: '野盗の首魁', rig: 'humanoid', scale: 1.16,
      hp: 900, damage: 52, defense: 14, poise: 46, souls: 1400,
      moveSpeed: 3.4, runSpeed: 6.2, turnRate: 9, mass: 1.3,
      weapon: 'axe_bandit', offhand: 'shield_wood',
      palette: { SKIN: [0.62, 0.46, 0.36], CLOTH: [0.36, 0.24, 0.18], ARMOR: [0.40, 0.32, 0.24], LEATHER: [0.30, 0.22, 0.16], HAIR: [0.18, 0.13, 0.09], ACCENT: [0.62, 0.20, 0.16] },
      ai: {
        preferredRange: 2.4, aggression: 0.75, patience: 0.7, sightRange: 26,
        leashRange: 45, groupRadius: 26, wanderRadius: 0,
        canBlock: true, canDodge: true, blockChance: 0.3, dodgeChance: 0.3,
        attacks: [
          { id: 'axe_l1', range: [0, 3.0], weight: 1.0, cooldown: 1.0, recovery: 0.4 },
          { id: 'axe_l2', range: [0, 3.0], weight: 1.0, cooldown: 1.0, recovery: 0.4 },
          { id: 'chief_flurry', range: [0, 3.2], weight: 0.9, cooldown: 4.0, recovery: 1.0 },
          { id: 'chief_shoulder', range: [3.0, 8.0], weight: 0.8, cooldown: 4.5, recovery: 0.8 },
        ],
      },
      drops: [['mat_chunk', 0.6, 2], ['ember_shard', 0.5, 2], ['key_ledger', 1.0, 1]],
    },
    breakAttacks: [
      { id: 'chief_whistle', range: [0, 26], weight: 1.2, cooldown: 14.0, recovery: 1.2 },
      { id: 'axe_h1', range: [0, 3.4], weight: 0.8, cooldown: 4.0, recovery: 1.0 },
    ],
    breakStats: { dmgMul: 1.2, speedMul: 1.15, aggression: 0.95 },
  },

  wolf_alpha: {
    id: 'wolf_alpha', name: '狼の長', souls: 1800, drop: ['tal_wolf', 1],
    // Teaches: pack spacing. Once it howls, the pack cuts your retreat.
    breakAt: 0.50, breakName: '遠吠え',
    arch: {
      name: '狼の長', rig: 'quadruped', scale: 1.45,
      hp: 780, damage: 48, defense: 10, poise: 34, souls: 1800,
      moveSpeed: 5.2, runSpeed: 9.6, turnRate: 13, mass: 1.2,
      height: 1.5, radius: 0.55,
      palette: { CLOTH: [0.42, 0.38, 0.34], DARK: [0.14, 0.13, 0.12] },
      ai: {
        preferredRange: 2.2, aggression: 0.8, patience: 0.5, sightRange: 30,
        leashRange: 45, groupRadius: 30, wanderRadius: 0,
        canDodge: true, dodgeChance: 0.35, strafeSpeedMul: 1.3,
        attacks: [
          { id: 'bite', range: [0, 2.8], weight: 1.0, cooldown: 1.1, recovery: 0.4 },
          { id: 'alpha_rip', range: [0, 3.2], weight: 0.9, cooldown: 2.0, recovery: 0.5 },
          { id: 'pounce', range: [4, 11], weight: 1.0, cooldown: 3.4, recovery: 0.7 },
        ],
      },
      drops: [['mat_fang', 1.0, 3], ['mat_hide', 0.8, 2]],
    },
    breakAttacks: [
      { id: 'alpha_howl', range: [0, 26], weight: 1.3, cooldown: 16.0, recovery: 1.4 },
      { id: 'alpha_run', range: [8, 22], weight: 1.1, cooldown: 5.0, recovery: 1.0 },
    ],
    breakStats: { dmgMul: 1.25, speedMul: 1.2, aggression: 1.0 },
  },

  sentinel_captain: {
    id: 'sentinel_captain', name: '哨戒隊長', souls: 4200, drop: ['tal_bulwark', 1],
    // Teaches: guard breaks. Then it removes its own guard and the lesson
    // inverts — the thing you learned to punish is gone.
    breakAt: 0.50, breakName: '盾を捨てる',
    arch: {
      name: '哨戒隊長', rig: 'humanoid', scale: 1.24,
      hp: 1500, damage: 74, defense: 30, poise: 96, souls: 4200,
      helm: true,
      moveSpeed: 2.4, runSpeed: 4.4, turnRate: 5, mass: 2.2,
      weapon: 'great_iron', offhand: 'shield_oath',
      palette: { SKIN: [0.34, 0.34, 0.36], CLOTH: [0.24, 0.26, 0.32], ARMOR: [0.52, 0.52, 0.58], LEATHER: [0.28, 0.26, 0.24], ACCENT: [0.70, 0.58, 0.24] },
      ai: {
        preferredRange: 2.8, aggression: 0.5, patience: 1.3, sightRange: 26,
        leashRange: 45, groupRadius: 22, wanderRadius: 0,
        canBlock: true, blockChance: 0.7,
        attacks: [
          { id: 'wall_brace', range: [0, 7.0], weight: 0.9, cooldown: 8.0, recovery: 0.4 },
          { id: 'wall_bash', range: [0, 2.8], weight: 1.0, cooldown: 3.2, recovery: 0.7 },
          { id: 'sentinel_sweep', range: [0, 3.8], weight: 1.0, cooldown: 2.2, recovery: 0.8 },
          { id: 'captain_line', range: [4.0, 11], weight: 0.9, cooldown: 5.0, recovery: 1.0 },
        ],
      },
      drops: [['mat_core', 0.5, 1], ['shield_oath', 0.2, 1], ['mat_chunk', 1.0, 2]],
    },
    breakAttacks: [
      { id: 'captain_shed', range: [0, 12], weight: 2.0, cooldown: 99.0, recovery: 0.6 },
      { id: 'captain_reap', range: [0, 4.0], weight: 1.2, cooldown: 3.0, recovery: 0.9 },
      { id: 'great_h1', range: [0, 3.8], weight: 0.9, cooldown: 4.5, recovery: 1.1 },
    ],
    breakStats: { dmgMul: 1.3, speedMul: 1.35, aggression: 1.0 },
  },

  wraith_lord: {
    id: 'wraith_lord', name: '灰の主', souls: 7200, drop: ['tal_lastlight', 1],
    // Teaches: a target that will not stay put. Lock-on is not enough.
    breakAt: 0.55, breakName: '燼に紛れる',
    arch: {
      name: '灰の主', rig: 'humanoid', scale: 1.22,
      hp: 1900, damage: 92, defense: 24, poise: 44, souls: 7200,
      moveSpeed: 4.0, runSpeed: 7.2, turnRate: 12, mass: 0.9,
      weapon: 'sword_ember', offhand: null,
      palette: { SKIN: [0.28, 0.20, 0.22], CLOTH: [0.22, 0.16, 0.16], ARMOR: [0.30, 0.20, 0.18], LEATHER: [0.20, 0.14, 0.13], HAIR: [0.52, 0.22, 0.12], ACCENT: [0.96, 0.40, 0.14] },
      emissive: 0.24,
      resist: { fire: 0.45 },
      ai: {
        preferredRange: 2.4, aggression: 0.8, patience: 0.5, sightRange: 30,
        leashRange: 45, groupRadius: 0, wanderRadius: 0,
        canDodge: true, dodgeChance: 0.45,
        attacks: [
          { id: 'lord_rend', range: [0, 3.0], weight: 1.0, cooldown: 0.9, recovery: 0.35 },
          { id: 'wraith_slash', range: [0, 3.0], weight: 1.0, cooldown: 1.0, recovery: 0.4 },
          { id: 'sword_h2', range: [2.0, 6.0], weight: 0.8, cooldown: 3.0, recovery: 0.7 },
          { id: 'wraith_burst', range: [0, 4.5], weight: 0.6, cooldown: 6.5, recovery: 1.2 },
        ],
      },
      drops: [['mat_core', 0.8, 2], ['ember_shard', 1.0, 3], ['key_sisterseal', 1.0, 1]],
    },
    breakAttacks: [
      { id: 'lord_blink', range: [3.0, 22], weight: 1.4, cooldown: 6.0, recovery: 0.6 },
      { id: 'lord_cinders', range: [2.0, 14], weight: 1.0, cooldown: 7.0, recovery: 1.2 },
    ],
    breakStats: { dmgMul: 1.3, speedMul: 1.25, aggression: 1.0 },
  },
};

// Register boss archetypes so Enemy can construct them by id.
for (const key in BOSSES) {
  ARCHETYPES[`boss_${key}`] = BOSSES[key].arch;
}
for (const key in MINI_BOSSES) {
  ARCHETYPES[`mini_${key}`] = MINI_BOSSES[key].arch;
}

// ---------------------------------------------------------------------------

export class Boss extends Enemy {
  constructor(game, bossId, opts = {}) {
    const def = BOSSES[bossId];
    // A named fight is authored end to end; a random affix on top of it would
    // only make the tell the player learned in the fog gate a lie.
    super(game, `boss_${bossId}`, { ...opts, level: opts.level || 1, noAffix: true });
    this.bossId = bossId;
    this.def = def;
    this.phases = def.phases;
    this.phaseIndex = 0;
    this.isBoss = true;
    this.noCritical = false;
    this.arenaX = opts.x;
    this.arenaZ = opts.z;
    this.arenaRadius = opts.arenaRadius || 30;
    this.baseAttacks = (resolveAI(def.arch).attacks || []).slice();
    this.transitioning = false;
    this.introDone = false;
    this.phaseTint = [1, 1, 1];
    this.weaponGlow = 0;
    this.hazardTimer = 0;
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
    this._updateHazard(dt);
    this._constrainToArena();
  }

  /**
   * A phase hazard is the part of a transition the player cannot dodge by
   * learning a new tell: the arena itself starts doing damage, so the space
   * they had been retreating into is no longer free.
   */
  _updateHazard(dt) {
    const phase = this.phases[this.phaseIndex];
    if (!phase || !phase.hazard || this.dead || this.transitioning) return;
    const h = phase.hazard;
    this.hazardTimer -= dt;
    if (this.hazardTimer > 0) return;
    this.hazardTimer = h.every || 3;

    const g = this.game;
    const t = this.brain.target || g.player;
    const spread = h.spread !== undefined ? h.spread : 1;
    // Biased towards the player: the closer `spread` is to 0, the more the
    // hazard hunts rather than rains.
    const cx = t ? lerp(t.x, this.arenaX, spread * 0.5) : this.arenaX;
    const cz = t ? lerp(t.z, this.arenaZ, spread * 0.5) : this.arenaZ;
    const a = Math.random() * TAU;
    const r = Math.sqrt(Math.random()) * this.arenaRadius * 0.55 * spread;
    const px = cx + Math.cos(a) * r, pz = cz + Math.sin(a) * r;
    g.areaEffects.push(new AreaEffect(g, {
      x: px, y: g.world.heightAt(px, pz), z: pz,
      radius: h.radius || 2.4, delay: h.delay !== undefined ? h.delay : 0.8, duration: 0.3,
      damage: this.baseDamage * (h.damage || 0.45),
      poise: h.poise || 26, type: h.type || 'fire',
      source: this, faction: this.faction, color: h.color || [1, 0.5, 0.2],
      status: h.status || null,
    }));
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
    // Spacing changes are the other half of a phase: a boss that stops being a
    // caster has to stop wanting to be at fourteen metres, or nothing changed.
    if (phase.aiOverride) Object.assign(this.brain.cfg, phase.aiOverride);
    if (phase.dropOffhand && this.offhand) {
      this.offhand = null;
      this.blocking = false;
      this.brain.cfg.canBlock = false;
    }
    this.hazardTimer = phase.hazard ? (phase.hazard.every || 3) : 0;

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
      case 'shatter': {
        // Pillars on the arena rim, then one under the player: the safe ring
        // is briefly the middle, which is exactly where the boss is.
        const count = 10;
        for (let i = 0; i < count; i++) {
          const a = (i / count) * TAU + Math.random() * 0.2;
          const R = this.arenaRadius * 0.62;
          const px = this.arenaX + Math.cos(a) * R, pz = this.arenaZ + Math.sin(a) * R;
          g.areaEffects.push(new AreaEffect(g, {
            x: px, y: g.world.heightAt(px, pz), z: pz,
            radius: 3.0, delay: 0.5 + i * 0.06, duration: 0.3,
            damage: dmg * 0.6, poise: 45, type: 'holy',
            source: this, faction: this.faction, color: [1, 0.9, 0.6],
          }));
        }
        if (t) {
          g.areaEffects.push(new AreaEffect(g, {
            x: t.x, y: g.world.heightAt(t.x, t.z), z: t.z,
            radius: 4.0, delay: 1.35, duration: 0.4,
            damage: dmg * 1.1, poise: 70, type: 'holy',
            source: this, faction: this.faction, color: [1, 0.92, 0.66], knockback: 8,
          }));
        }
        break;
      }
      case 'ash_storm': {
        // A dense scatter across the whole arena for a few seconds.
        for (let i = 0; i < 20; i++) {
          const a = Math.random() * TAU;
          const r = Math.sqrt(Math.random()) * this.arenaRadius * 0.85;
          const px = this.arenaX + Math.cos(a) * r, pz = this.arenaZ + Math.sin(a) * r;
          g.areaEffects.push(new AreaEffect(g, {
            x: px, y: g.world.heightAt(px, pz), z: pz,
            radius: 2.2, delay: 0.4 + i * 0.11, duration: 0.28,
            damage: dmg * 0.4, poise: 24, type: 'fire',
            source: this, faction: this.faction, color: [0.9, 0.52, 0.24],
          }));
        }
        break;
      }
      case 'bell_call': {
        // The bell is the summon. Silencing it is the fight.
        const kinds = ['husk', 'spearman', 'rootling'];
        for (let i = 0; i < 3; i++) {
          const a = (i / 3) * TAU + Math.random() * 0.5;
          const r = 9 + Math.random() * 5;
          g.spawnEnemy(kinds[i % kinds.length], this.x + Math.cos(a) * r, this.z + Math.sin(a) * r, {
            level: this.level, summoned: true, noAffix: true,
          });
        }
        g.notify('鐘の音に応える者がいる');
        break;
      }
      case 'bell_wave': {
        // Rings expanding outwards with a gap: run out, not around.
        for (let ring = 0; ring < 4; ring++) {
          const R = 3.0 + ring * 3.4;
          const count = 7 + ring * 4;
          for (let i = 0; i < count; i++) {
            const a = (i / count) * TAU + ring * 0.28;
            g.areaEffects.push(new AreaEffect(g, {
              x: this.x + Math.cos(a) * R, y: this.y, z: this.z + Math.sin(a) * R,
              radius: 2.1, delay: 0.2 + ring * 0.26, duration: 0.24,
              damage: dmg * 0.42, poise: 34, type: 'holy',
              source: this, faction: this.faction, color: [1, 0.88, 0.52],
            }));
          }
        }
        break;
      }
      case 'thorn_ring': {
        // A closing wall of thorns: the arena is smaller from now until it dies.
        const R = Math.max(9, this.arenaRadius * 0.66);
        const count = 22;
        for (let i = 0; i < count; i++) {
          const a = (i / count) * TAU;
          const px = this.arenaX + Math.cos(a) * R, pz = this.arenaZ + Math.sin(a) * R;
          g.areaEffects.push(new AreaEffect(g, {
            x: px, y: g.world.heightAt(px, pz), z: pz,
            radius: 2.6, delay: 0.8 + (i % 4) * 0.12, duration: 0.4,
            damage: dmg * 0.7, poise: 45, type: 'physical',
            source: this, faction: this.faction, color: [0.40, 0.50, 0.24],
            status: { type: 'bleed', build: 18 },
          }));
        }
        g.notify('茨が輪を狭める');
        break;
      }
      case 'seedlings': {
        for (let i = 0; i < 4; i++) {
          const a = Math.random() * TAU;
          const r = 5 + Math.random() * 7;
          g.spawnEnemy('rootling', this.x + Math.cos(a) * r, this.z + Math.sin(a) * r, {
            level: this.level, summoned: true, noAffix: true,
          });
        }
        break;
      }
      case 'chord': {
        // Three pillars in a line through the player: sidestep, do not retreat.
        if (!t) break;
        const a = Math.atan2(t.x - this.x, t.z - this.z);
        for (let i = 0; i < 3; i++) {
          const d = 5 + i * 5.5;
          const px = this.x + Math.sin(a) * d, pz = this.z + Math.cos(a) * d;
          g.areaEffects.push(new AreaEffect(g, {
            x: px, y: g.world.heightAt(px, pz), z: pz,
            radius: 3.0, delay: 0.5 + i * 0.20, duration: 0.3,
            damage: dmg * 0.75, poise: 45, type: 'magic',
            source: this, faction: this.faction, color: [0.62, 0.70, 1.0],
          }));
        }
        break;
      }
      case 'dirge': {
        // Heals itself off its own adds' presence, so ignoring them is a loop.
        let allies = 0;
        for (const e of g.enemies) {
          if (e === this || e.dead) continue;
          if (Math.hypot(e.x - this.x, e.z - this.z) < 22) allies++;
        }
        for (let i = 0; i < 2; i++) {
          const a = Math.random() * TAU, r = 7 + Math.random() * 6;
          g.spawnEnemy('husk_archer', this.x + Math.cos(a) * r, this.z + Math.sin(a) * r, {
            level: this.level, summoned: true, noAffix: true,
          });
        }
        if (allies > 0) {
          this.hp = Math.min(this.maxHp, this.hp + this.maxHp * 0.04 * Math.min(allies, 4));
          g.notify('合唱が声を取り戻す');
        }
        break;
      }
      case 'frost_nova': {
        for (let ring = 0; ring < 2; ring++) {
          const R = 3.4 + ring * 3.2;
          const count = 8 + ring * 5;
          for (let i = 0; i < count; i++) {
            const a = (i / count) * TAU + ring * 0.22;
            g.areaEffects.push(new AreaEffect(g, {
              x: this.x + Math.cos(a) * R, y: this.y, z: this.z + Math.sin(a) * R,
              radius: 2.2, delay: 0.2 + ring * 0.28, duration: 0.26,
              damage: dmg * 0.5, poise: 40, type: 'magic',
              source: this, faction: this.faction, color: [0.74, 0.9, 1.0],
              status: { type: 'frost', build: 22 },
            }));
          }
        }
        break;
      }
      case 'ice_field': {
        // A wide, slow, persistent patch centred on the player's last position.
        const cx = t ? t.x : this.x, cz = t ? t.z : this.z;
        for (let i = 0; i < 6; i++) {
          const a = (i / 6) * TAU;
          const px = cx + Math.cos(a) * 2.8, pz = cz + Math.sin(a) * 2.8;
          g.areaEffects.push(new AreaEffect(g, {
            x: px, y: g.world.heightAt(px, pz), z: pz,
            radius: 2.8, delay: 1.0 + i * 0.1, duration: 0.5,
            damage: dmg * 0.45, poise: 30, type: 'magic',
            source: this, faction: this.faction, color: [0.8, 0.92, 1.0],
            status: { type: 'frost', build: 26 },
          }));
        }
        break;
      }
      case 'martyrs': {
        // Adds that explode. Killing them next to yourself is the trap.
        for (let i = 0; i < 3; i++) {
          const a = Math.random() * TAU;
          const r = 6 + Math.random() * 6;
          g.spawnEnemy('flagellant', this.x + Math.cos(a) * r, this.z + Math.sin(a) * r, {
            level: this.level, summoned: true, noAffix: true,
          });
        }
        g.notify('殉教者が立ち上がる');
        break;
      }
      case 'pyres': {
        // Fixed burning columns that persist as a hazard for the phase.
        for (let i = 0; i < 5; i++) {
          const a = (i / 5) * TAU + 0.3;
          const R = this.arenaRadius * 0.45;
          const px = this.arenaX + Math.cos(a) * R, pz = this.arenaZ + Math.sin(a) * R;
          for (let k = 0; k < 3; k++) {
            g.areaEffects.push(new AreaEffect(g, {
              x: px, y: g.world.heightAt(px, pz), z: pz,
              radius: 2.8, delay: 0.6 + k * 1.5, duration: 0.4,
              damage: dmg * 0.55, poise: 34, type: 'fire',
              source: this, faction: this.faction, color: [1, 0.46, 0.16],
            }));
          }
        }
        break;
      }
      default:
        // Everything an ordinary enemy can do, a boss can do too.
        super._fireSpecial(kind, def);
        break;
    }
  }

  render(batches) {
    const t = this.phaseTint;
    const prev = this.emissive;
    this.emissive = prev + this.weaponGlow * 0.10;
    const opts = {
      tintR: t[0] * (1 + this.flash * 1.4),
      tintG: t[1] * (1 - this.flash * 0.3),
      tintB: t[2] * (1 - this.flash * 0.3),
      alpha: 1,
      emissive: this.emissive,
    };
    this.rig.renderTo(batches, this.palette, opts);
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

/**
 * A mini-boss: an authored Enemy with one threshold. The threshold is not a
 * damage multiplier — it swaps in a new set of moves and, in three of the four
 * cases, removes something the enemy had been relying on.
 */
export class MiniBoss extends Enemy {
  constructor(game, kind, opts = {}) {
    const cfg = MINI_BOSSES[kind];
    super(game, `mini_${kind}`, { ...opts, noAffix: true });
    this.miniId = kind;
    this.cfg = cfg;
    this.isMiniBoss = true;
    this.broken = false;
    this.baseAttacks = cfg.arch.ai.attacks.slice();
    if (cfg.drop) this.dropTable = this.dropTable.concat([[cfg.drop[0], 1.0, cfg.drop[1]]]);
  }

  update(dt) {
    if (!this.broken && !this.dead && this.hp <= this.maxHp * (this.cfg.breakAt || 0.5)) {
      this._break();
    }
    super.update(dt);
  }

  _break() {
    this.broken = true;
    const cfg = this.cfg;
    const s = cfg.breakStats || {};
    this.setState(STATE.TAUNT, { duration: 1.2 });
    this.invuln = 1.2;
    this.poise = this.maxPoise;
    this.baseDamage *= s.dmgMul || 1;
    if (s.speedMul) {
      this.moveSpeed *= s.speedMul;
      this.runSpeed *= s.speedMul;
    }
    if (s.aggression !== undefined) this.brain.cfg.aggression = s.aggression;
    if (cfg.breakAttacks) {
      this.brain.cfg.attacks = this.baseAttacks.concat(cfg.breakAttacks);
    }
    this.game.shake(0.5, 0.4);
    this.game.particles.burst(this.x, this.y + 1.4, this.z, 22, {
      r: 1.0, g: 0.66, b: 0.28, size: 0.22, life: 0.8, spread: 3.0, up: 2.4,
      blend: BLEND.ADDITIVE, alpha: 0.9, drag: 2, gravity: 0.5,
    });
    if (cfg.breakName) this.game.notify(`${this.name} — ${cfg.breakName}`, 'boss');
  }

  /** Mini-boss-only behaviours; anything else falls through to the shared set. */
  _fireSpecial(kind, def) {
    const g = this.game;
    const t = this.brain.target || g.player;
    switch (kind) {
      case 'call': {
        // Two archers on the flanks. The chief is suddenly not the problem.
        for (let i = 0; i < 2; i++) {
          const a = Math.atan2(this.x - (t ? t.x : this.x), this.z - (t ? t.z : this.z))
            + (i === 0 ? 1.5 : -1.5);
          const r = 11;
          g.spawnEnemy('bandit_archer', this.x + Math.sin(a) * r, this.z + Math.cos(a) * r, {
            level: this.level, summoned: true, noAffix: true,
          });
        }
        g.notify('首魁が指笛を鳴らした');
        break;
      }
      case 'howl': {
        // Three wolves, placed between the player and the way out.
        for (let i = 0; i < 3; i++) {
          const a = Math.atan2((t ? t.x : this.x) - this.x, (t ? t.z : this.z) - this.z)
            + (i - 1) * 0.9;
          const r = 13;
          const w = g.spawnEnemy('ashwolf', (t ? t.x : this.x) + Math.sin(a) * r,
            (t ? t.z : this.z) + Math.cos(a) * r, {
              level: this.level, summoned: true, noAffix: true,
            });
          if (w) w.removeAfter = 20;
        }
        g.notify('遠吠えが返ってくる');
        break;
      }
      case 'shed': {
        // Throws the greatshield away. Faster, and no longer blockable-through.
        this.offhand = null;
        this.blocking = false;
        this.brain.cfg.canBlock = false;
        this.brain.cfg.strafeSpeedMul = 1.0;
        this.brain.cfg.preferredRange = 3.2;
        this.maxPoise *= 0.6;
        this.poise = this.maxPoise;
        g.shake(0.35, 0.3);
        g.notify('隊長が盾を投げ捨てた');
        break;
      }
      case 'blink': {
        // Reappears behind. The reason lock-on alone does not carry this fight.
        if (!t) break;
        const a = t.yaw + Math.PI + (Math.random() - 0.5) * 0.8;
        this.invuln = Math.max(this.invuln, 0.5);
        g.particles.burst(this.x, this.y + 1.0, this.z, 20, {
          r: 1.0, g: 0.5, b: 0.18, size: 0.2, life: 0.6, spread: 2.6, up: 2.0,
          blend: BLEND.ADDITIVE, alpha: 0.9, drag: 2.4, gravity: 0.4,
        });
        this.teleport(t.x + Math.sin(a) * 2.6, undefined, t.z + Math.cos(a) * 2.6);
        this.yaw = Math.atan2(t.x - this.x, t.z - this.z);
        break;
      }
      default:
        super._fireSpecial(kind, def);
        break;
    }
  }
}

export function createMiniBoss(game, kind, x, z, level) {
  if (!MINI_BOSSES[kind]) return null;
  return new MiniBoss(game, kind, { x, z, level });
}
