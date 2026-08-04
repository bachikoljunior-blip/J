// ============================================================================
//  player.js — the character the player drives, and the camera that follows.
//
//  Stat curves, equip-load roll types, combo buffering and lock-on all follow
//  the conventions of the genre closely, because those conventions are load
//  bearing: a player who knows one of these games should be able to pick this
//  up and have their muscle memory work.
// ============================================================================

import {
  clamp, lerp, saturate, damp, dampAngle, angleDelta, TAU, v3distXZ, MAX_DT,
} from '../core/math.js';
import { Actor, STATE, FACTION, defaultPalette } from './actor.js';
import { MAT } from './rig.js';
import { ACTION } from '../core/input.js';
import { COMBOS, HEAVY_COMBOS, RUN_ATTACKS, ATTACKS } from './anim.js';
import {
  getItem, getSpell, weaponAttack, requirementPenalty, UPGRADE_MUL,
} from './items.js';
import {
  findBackstabTarget, findRiposteTarget, executeCritical, Projectile, AreaEffect,
} from './combat.js';
import { BLEND } from '../gfx/particles.js';

// ---------------------------------------------------------------------------
//  Stat curves
// ---------------------------------------------------------------------------

export const STAT_NAMES = {
  vig: '生命力', mnd: '精神力', end: '持久力',
  str: '筋力', dex: '技量', int: '理力', fth: '信仰',
};
export const STAT_ORDER = ['vig', 'mnd', 'end', 'str', 'dex', 'int', 'fth'];

export function hpFromVigor(v) {
  if (v <= 25) return Math.round(280 + (v - 10) * 33);
  if (v <= 40) return Math.round(775 + (v - 25) * 36);
  if (v <= 60) return Math.round(1315 + (v - 40) * 19);
  return Math.round(1695 + (v - 60) * 7);
}

export function fpFromMind(v) {
  if (v <= 15) return Math.round(60 + (v - 10) * 7);
  if (v <= 35) return Math.round(95 + (v - 15) * 9);
  if (v <= 60) return Math.round(275 + (v - 35) * 5);
  return Math.round(400 + (v - 60) * 2);
}

export function staminaFromEnd(v) {
  if (v <= 15) return Math.round(90 + (v - 10) * 2.4);
  if (v <= 30) return Math.round(102 + (v - 15) * 2.6);
  if (v <= 50) return Math.round(141 + (v - 30) * 1.3);
  return Math.round(167 + (v - 50) * 0.3);
}

export function loadFromEnd(v, str) {
  return 42 + v * 1.5 + str * 0.35;
}

/**
 * Cost in embers of the next level.
 *
 * The cubic is the genre's standard curve, but it only behaves above level 12
 * — below that it goes negative — so the early levels come from a small table,
 * chosen to meet the cubic exactly at 12.
 */
const EARLY_LEVEL_COST = [0, 673, 689, 706, 723, 740, 757, 775, 793, 811, 829, 847];

export function levelCost(level) {
  if (level < EARLY_LEVEL_COST.length) return EARLY_LEVEL_COST[Math.max(level, 1)];
  const L = level;
  return Math.round(0.02 * L * L * L + 3.06 * L * L + 105.6 * L - 895);
}

export const CLASSES = [
  {
    id: 'knight', name: '騎士', blurb: '重い鎧と真っ直ぐな剣。堅実に戦える。',
    level: 9, stats: { vig: 14, mnd: 10, end: 12, str: 15, dex: 13, int: 9, fth: 9 },
    weapons: ['sword_knight'], offhand: ['shield_kite'],
    armor: ['head_knight', 'body_knight', 'arms_knight', 'legs_knight'],
    items: [['flask_hp', 4], ['flask_fp', 2]], spells: [],
  },
  {
    id: 'warrior', name: '戦士', blurb: '両手斧の一撃で押し切る。守りは自分の足で。',
    level: 8, stats: { vig: 13, mnd: 9, end: 14, str: 16, dex: 11, int: 8, fth: 8 },
    weapons: ['axe_wood'], offhand: ['shield_wood'],
    armor: ['head_bandit', 'body_bandit', 'arms_bandit', 'legs_bandit'],
    items: [['flask_hp', 4], ['flask_fp', 1]], spells: [],
  },
  {
    id: 'hunter', name: '狩人', blurb: '弓と短刀。間合いを支配する者。',
    level: 8, stats: { vig: 11, mnd: 10, end: 13, str: 11, dex: 17, int: 10, fth: 9 },
    weapons: ['dagger_thief', 'bow_short'], offhand: [],
    armor: ['head_bandit', 'body_marked', 'arms_bandit', 'legs_bandit'],
    items: [['flask_hp', 4], ['flask_fp', 2], ['throwing_knife', 12]], spells: [],
  },
  {
    id: 'sorcerer', name: '魔術師', blurb: '輝石の魔術。近づかれる前に終わらせる。',
    level: 8, stats: { vig: 10, mnd: 15, end: 10, str: 9, dex: 12, int: 17, fth: 8 },
    weapons: ['staff_apprentice', 'dagger_thief'], offhand: [],
    armor: ['head_arcane', 'body_arcane', 'arms_arcane', 'legs_arcane'],
    items: [['flask_hp', 3], ['flask_fp', 4]], spells: ['sp_bolt'],
  },
  {
    id: 'cleric', name: '祈祷師', blurb: '祈りは火となり、傷を塞ぐ。',
    level: 8, stats: { vig: 12, mnd: 14, end: 11, str: 12, dex: 10, int: 8, fth: 16 },
    weapons: ['staff_ember', 'sword_broken'], offhand: ['shield_wood'],
    armor: ['head_marked', 'body_marked', 'arms_marked', 'legs_marked'],
    items: [['flask_hp', 4], ['flask_fp', 3]], spells: ['sp_flame', 'sp_heal'],
  },
  {
    id: 'wretch', name: '無頼', blurb: '何も持たない。全てを選べる。',
    level: 1, stats: { vig: 10, mnd: 10, end: 10, str: 10, dex: 10, int: 10, fth: 10 },
    weapons: ['sword_broken'], offhand: [],
    armor: ['body_marked', 'legs_marked'],
    items: [['flask_hp', 3], ['flask_fp', 1]], spells: [],
  },
];

// ---------------------------------------------------------------------------

export class Player extends Actor {
  constructor(game, opts = {}) {
    super(game, {
      ...opts,
      faction: FACTION.PLAYER,
      radius: 0.38,
      height: 1.90,
      maxHp: 400,
      maxStamina: 100,
      poise: 30,
      name: opts.name || '刻印者',
      moveSpeed: 2.6,
      runSpeed: 5.0,
      sprintSpeed: 7.4,
      turnRate: 13,
      mass: 1.2,
    });

    this.stats = { vig: 10, mnd: 10, end: 10, str: 10, dex: 10, int: 10, fth: 10 };
    this.playerLevel = 1;
    this.souls = 0;
    this.totalSouls = 0;

    this.equip = {
      right: [null, null, null],
      left: [null, null, null],
      head: null, body: null, arms: null, legs: null,
      talismans: [null, null, null, null],
    };
    this.rightIndex = 0;
    this.leftIndex = 0;
    this.twoHand = false;

    this.inventory = new Map();
    this.spells = [];
    this.spellIndex = 0;
    this.quickItems = [];
    this.quickIndex = 0;

    this.flaskHp = { max: 4, cur: 4, heal: 380 };
    this.flaskFp = { max: 2, cur: 2, heal: 90 };

    this.fp = 100;
    this.maxFp = 100;
    this.equipLoad = 0;
    this.maxLoad = 60;
    this.rollType = 'medium';

    this.lockTarget = null;
    this.lockSwitchCd = 0;
    this.interactTarget = null;
    this.comboChain = null;
    this.comboStep = 0;
    this.bufferedInput = null;
    this.bufferTime = 0;
    this.sprintHeld = 0;
    this.isSprinting = false;
    this.lastGraceId = null;
    this.deathDrop = null;
    this.hitStreak = 0;
    this.hitStreakTimer = 0;
    this.critBonus = 1;
    this.castQueued = null;
    this.restTimer = 0;
    this.canRest = false;

    this.palette = defaultPalette();
    this.appearance = { skin: 0, hair: 0, cape: [0.30, 0.09, 0.09] };

    this.camera = new PlayerCamera(this);
    this.recomputeDerived(true);
  }

  // -------------------------------------------------------------------------
  //  Derived stats
  // -------------------------------------------------------------------------

  recomputeDerived(full = false) {
    const s = this.stats;
    const mods = this.talismanMods();

    const hpMul = mods.hpMul || 1;
    const newMaxHp = Math.round(hpFromVigor(s.vig) * hpMul);
    const hpRatio = this.maxHp > 0 ? this.hp / this.maxHp : 1;
    this.maxHp = newMaxHp;
    this.hp = full ? this.maxHp : clamp(hpRatio * this.maxHp, 1, this.maxHp);

    this.maxFp = Math.round(fpFromMind(s.mnd) * (mods.fpMul || 1));
    if (full) this.fp = this.maxFp; else this.fp = Math.min(this.fp, this.maxFp);

    this.maxStamina = staminaFromEnd(s.end);
    if (full) this.stamina = this.maxStamina; else this.stamina = Math.min(this.stamina, this.maxStamina);
    this.staminaRegen = 42 * (mods.staminaRegenMul || 1);

    this.maxLoad = loadFromEnd(s.end, s.str) * (mods.loadMul || 1);

    // Armour totals.
    let def = 6 + s.vig * 0.35;
    let poise = 8 + (mods.poiseAdd || 0);
    let weight = 0;
    const resist = { fire: 0, magic: 0, lightning: 0, holy: 0, poison: 0 };
    for (const slot of ['head', 'body', 'arms', 'legs']) {
      const it = this.equip[slot];
      if (!it) continue;
      def += it.def;
      poise += it.poise;
      weight += it.weight;
      for (const k in it.resist || {}) resist[k] = (resist[k] || 0) + it.resist[k];
    }
    for (const w of [this.rightHand, this.leftHand]) if (w) weight += w.weight;
    for (const t of this.equip.talismans) if (t) weight += t.weight || 0;

    if (mods.fireResist) resist.fire += mods.fireResist;

    this.defense = def;
    this.maxPoise = Math.max(4, poise);
    this.resist = resist;
    this.equipLoad = weight;

    const ratio = this.maxLoad > 0 ? weight / this.maxLoad : 1;
    this.loadRatio = ratio;
    this.rollType = ratio < 0.30 ? 'light' : ratio < 0.70 ? 'medium' : ratio < 1.0 ? 'heavy' : 'overload';

    const speedMul = this.rollType === 'light' ? 1.06
      : this.rollType === 'medium' ? 1.0
        : this.rollType === 'heavy' ? 0.90 : 0.68;
    this.moveSpeed = 2.6 * speedMul;
    this.runSpeed = 5.0 * speedMul;
    this.sprintSpeed = 7.4 * speedMul;

    this.critBonus = mods.critMul || 1;
    this.parryWindow = 0.20 + (mods.parryWindow || 0);
    this.soulsMul = mods.soulsMul || 1;
    this.dmgMul = mods.dmgMul || 1;
    this.takenMul = mods.takenMul || 1;
    this.comboRamp = mods.comboRamp || 0;
    this.desperation = mods.desperation || 0;
    this.critHeal = mods.critHeal || 0;
    this.fireMul = mods.fireMul || 1;

    this._applyPalette();
  }

  talismanMods() {
    const out = {};
    for (const t of this.equip.talismans) {
      if (!t || !t.mods) continue;
      for (const k in t.mods) {
        if (k.endsWith('Mul')) out[k] = (out[k] || 1) * t.mods[k];
        else out[k] = (out[k] || 0) + t.mods[k];
      }
    }
    return out;
  }

  get rightHand() { return this.equip.right[this.rightIndex]; }
  get leftHand() { return this.equip.left[this.leftIndex]; }
  get weapon() { return this.rightHand; }
  set weapon(v) { /* driven by equipment */ }
  get offhand() { return this.twoHand ? null : this.leftHand; }
  set offhand(v) { /* driven by equipment */ }
  get weaponClass() { return this.rightHand ? this.rightHand.class : 'sword'; }
  set weaponClass(v) { }

  _applyPalette() {
    const p = defaultPalette();
    const skins = [[0.78, 0.62, 0.50], [0.60, 0.44, 0.34], [0.44, 0.31, 0.24], [0.86, 0.72, 0.62]];
    const hairs = [[0.14, 0.11, 0.09], [0.36, 0.24, 0.12], [0.62, 0.58, 0.50], [0.52, 0.16, 0.12]];
    p[MAT.SKIN] = skins[this.appearance.skin % skins.length];
    p[MAT.HAIR] = hairs[this.appearance.hair % hairs.length];
    p[MAT.ACCENT] = this.appearance.cape;
    for (const slot of ['body', 'head', 'arms', 'legs']) {
      const it = this.equip[slot];
      if (!it || !it.colors) continue;
      if (it.colors.armor) p[MAT.ARMOR] = it.colors.armor;
      if (it.colors.cloth) p[MAT.CLOTH] = it.colors.cloth;
      if (it.colors.leather) p[MAT.LEATHER] = it.colors.leather;
      if (it.colors.accent) p[MAT.ACCENT] = it.colors.accent;
    }
    this.palette = p;
    // A filled head slot swaps the bare head for a helm with a visor slit.
    this.rig.setHelm(!!this.equip.head);
  }

  // -------------------------------------------------------------------------
  //  Inventory & equipment
  // -------------------------------------------------------------------------

  addItem(id, count = 1) {
    const item = getItem(id);
    if (!item) return null;
    this.inventory.set(id, (this.inventory.get(id) || 0) + count);
    this._refreshQuickItems();
    return item;
  }

  removeItem(id, count = 1) {
    const have = this.inventory.get(id) || 0;
    if (have <= count) this.inventory.delete(id);
    else this.inventory.set(id, have - count);
    this._refreshQuickItems();
  }

  countItem(id) { return this.inventory.get(id) || 0; }

  _refreshQuickItems() {
    const list = [];
    for (const [id, n] of this.inventory) {
      const it = getItem(id);
      if (it && it.kind === 'consumable' && !it.flask && n > 0) list.push(id);
    }
    this.quickItems = list;
    if (this.quickIndex >= list.length) this.quickIndex = 0;
  }

  equipItem(id, slotHint) {
    const item = getItem(id);
    if (!item) return false;
    if (item.kind === 'weapon') {
      const isShield = item.class === 'shield';
      if (slotHint === 'left' || (isShield && slotHint !== 'right')) {
        this.equip.left[this.leftIndex] = item;
      } else {
        this.equip.right[this.rightIndex] = item;
      }
    } else if (item.kind === 'armor') {
      this.equip[item.slot] = item;
    } else if (item.kind === 'talisman') {
      const free = this.equip.talismans.findIndex((t) => !t);
      const idx = slotHint !== undefined && typeof slotHint === 'number' ? slotHint
        : free >= 0 ? free : 0;
      this.equip.talismans[idx] = item;
    } else {
      return false;
    }
    this.recomputeDerived();
    return true;
  }

  unequip(kind, index = 0) {
    if (kind === 'right') this.equip.right[index] = null;
    else if (kind === 'left') this.equip.left[index] = null;
    else if (kind === 'talisman') this.equip.talismans[index] = null;
    else this.equip[kind] = null;
    this.recomputeDerived();
  }

  upgradeLevelOf(item) {
    if (!item) return 0;
    return this.upgrades?.get(item.id) || 0;
  }

  setUpgrade(itemId, level) {
    if (!this.upgrades) this.upgrades = new Map();
    this.upgrades.set(itemId, level);
    this.recomputeDerived();
  }

  learnSpell(id) {
    if (!this.spells.includes(id)) this.spells.push(id);
  }

  // -------------------------------------------------------------------------
  //  Damage output
  // -------------------------------------------------------------------------

  buildAttackInfo(target) {
    const w = this.rightHand;
    const level = this.upgradeLevelOf(w);
    const atk = weaponAttack(w, level, this.stats);
    const penalty = requirementPenalty(w, this.stats);
    const def = this.action || ATTACKS.sword_l1;

    let mul = (def.dmg || 1) * penalty * this.dmgMul * (this.actionDamageMul || 1);
    if (this.twoHand) mul *= 1.12;
    mul *= this.buffValue('atkMul', 1);
    if (this.comboRamp) mul *= 1 + Math.min(3, this.hitStreak) * this.comboRamp;
    if (this.desperation && this.hp < this.maxHp * 0.25) mul *= 1 + this.desperation;

    const addFire = this.buffAdd('addFire');
    const addMagic = this.buffAdd('addMagic');
    let element = atk.element;
    let elementType = atk.elementType;
    if (addFire > 0) { element += addFire; elementType = 'fire'; }
    if (addMagic > 0) { element += addMagic; elementType = 'magic'; }
    if (elementType === 'fire') element *= this.fireMul;

    const status = w && w.effect ? { type: w.effect.type, build: w.effect.build } : null;

    return {
      damage: (atk.physical + element) * mul,
      poise: (def.poise || 10) * (this.twoHand ? 1.25 : 1),
      type: elementType || 'physical',
      knockback: 2.0 + (def.poise || 10) * 0.05,
      status,
      critMul: 1.9 * (w ? w.crit || 1 : 1) * this.critBonus,
      big: (def.poise || 0) > 30,
      source: this,
    };
  }

  // -------------------------------------------------------------------------
  //  Input handling
  // -------------------------------------------------------------------------

  handleInput(input, dt, camYaw) {
    if (this.dead) { this.intentSpeed = 0; this.intentX = 0; this.intentZ = 0; return; }

    if (this.state === STATE.REST) {
      if (input.pressed(ACTION.INTERACT) || input.pressed(ACTION.DODGE)) {
        this.setState(STATE.IDLE);
        this.game.onLeaveGrace?.();
      }
      this.intentSpeed = 0; this.intentX = 0; this.intentZ = 0;
      return;
    }

    const move = input.sample();
    const mag = Math.min(1, Math.hypot(move.x, move.y));

    // Camera-relative movement.
    let wx = 0, wz = 0;
    if (mag > 0.06) {
      const fx = Math.sin(camYaw), fz = Math.cos(camYaw);
      const rx = Math.cos(camYaw), rz = -Math.sin(camYaw);
      wx = fx * -move.y + rx * move.x;
      wz = fz * -move.y + rz * move.x;
      const l = Math.hypot(wx, wz) || 1;
      wx /= l; wz /= l;
    }

    // Sprint: hold the dodge button while moving.
    const dodgeHeld = input.held(ACTION.DODGE) || input.held(ACTION.SPRINT);
    if (dodgeHeld && mag > 0.5 && this.stamina > 4) {
      this.sprintHeld += dt;
    } else {
      this.sprintHeld = 0;
    }
    this.isSprinting = this.sprintHeld > 0.22 && this.stamina > 1 && this.rollType !== 'overload';
    if (this.isSprinting) {
      this.stamina = Math.max(0, this.stamina - 16 * dt);
      this.staminaLock = 0.4;
      if (this.stamina <= 0) this.isSprinting = false;
    }

    // Guard is a hold; it can be entered from idle or movement.
    const wantGuard = input.held(ACTION.GUARD) && this.leftHand && this.leftHand.guard && !this.twoHand;
    this.blocking = wantGuard && !this.busy;

    // --- action inputs, with a short buffer so presses during recovery land --
    if (input.pressed(ACTION.ATTACK)) this._buffer('light');
    if (input.pressed(ACTION.HEAVY)) this._buffer('heavy');
    if (input.pressed(ACTION.DODGE) && this.sprintHeld < 0.22) this._buffer('dodge');
    if (input.released(ACTION.DODGE) && this.sprintHeld > 0 && this.sprintHeld < 0.22) this._buffer('dodge');
    if (input.pressed(ACTION.SPELL)) this._buffer('spell');
    if (input.pressed(ACTION.ITEM)) this._buffer('item');
    if (input.pressed(ACTION.JUMP)) this._buffer('jump');

    if (input.pressed(ACTION.GUARD) && this.canAct && (!this.leftHand || !this.leftHand.guard)) {
      // No shield: the guard button becomes a parry attempt.
      this._buffer('parry');
    } else if (input.pressed(ACTION.HEAVY) && input.held(ACTION.GUARD) && this.leftHand && this.leftHand.guard) {
      this._buffer('parry');
    }

    this.bufferTime -= dt;
    // An input that aged out without being consumed is the other way a
    // buffered press disappears, and the one a player actually notices: they
    // pressed attack, the window passed while they were still recovering, and
    // nothing happened.
    if (this.bufferTime <= 0) {
      if (this.bufferedInput) {
        this.bufferExpired = (this.bufferExpired || 0) + 1;
        this.lastBufferExpiry = this.bufferedInput;
      }
      this.bufferedInput = null;
    }

    // --- lock-on ------------------------------------------------------------
    this.lockSwitchCd = Math.max(0, this.lockSwitchCd - dt);
    if (input.pressed(ACTION.LOCKON)) {
      if (this.lockTarget) this.lockTarget = null;
      else this.lockTarget = this.game.findLockTarget(this);
      input.consume(ACTION.LOCKON);
    }
    if (this.lockTarget && (this.lockTarget.dead || v3distXZ(this, this.lockTarget) > 34)) {
      this.lockTarget = null;
    }
    if (this.lockTarget && this.lockSwitchCd <= 0 && Math.abs(input.look.x) > 0.35) {
      const next = this.game.findLockTarget(this, this.lockTarget, Math.sign(input.look.x));
      if (next) { this.lockTarget = next; this.lockSwitchCd = 0.45; }
    }

    if (input.pressed(ACTION.TWOHAND) && this.canAct) {
      this.twoHand = !this.twoHand;
      this.recomputeDerived();
    }
    if (input.pressed(ACTION.SWITCH_ITEM)) {
      this.quickIndex = this.quickItems.length ? (this.quickIndex + 1) % this.quickItems.length : 0;
    }
    if (input.pressed(ACTION.SWITCH_SPELL)) {
      this.spellIndex = this.spells.length ? (this.spellIndex + 1) % this.spells.length : 0;
    }

    // --- consume the buffer -------------------------------------------------
    if (this.canAct || (this.state === STATE.ATTACK && this.comboWindow > 0)) {
      this._tryConsumeBuffer(wx, wz);
    }

    // --- locomotion ---------------------------------------------------------
    if (this.state === STATE.IDLE || this.state === STATE.MOVE || this.blocking) {
      const base = this.blocking ? this.moveSpeed * 0.82
        : this.isSprinting ? this.sprintSpeed
          : mag > 0.72 ? this.runSpeed
            : this.moveSpeed;
      this.intentX = wx;
      this.intentZ = wz;
      this.intentSpeed = mag > 0.06 ? base * (this.isSprinting ? 1 : lerp(0.55, 1, mag)) : 0;

      if (mag > 0.06) {
        if (this.lockTarget && !this.isSprinting) {
          // Locked on: face the target and strafe around it.
          this.faceTowards(this.lockTarget.x, this.lockTarget.z, dt, 14);
        } else {
          this.yaw = dampAngle(this.yaw, Math.atan2(wx, wz), this.turnRate, dt);
        }
      } else if (this.lockTarget) {
        this.faceTowards(this.lockTarget.x, this.lockTarget.z, dt, 10);
      }
    } else {
      this.intentSpeed = 0;
    }

    // Aim assist during attacks: snap toward the lock target or nearest enemy.
    if (this.state === STATE.ATTACK && this.actionU < 0.30) {
      const t = this.lockTarget || this.game.nearestEnemy(this, 4.5, 1.2);
      if (t) this.faceTowards(t.x, t.z, dt, 16);
    }

    this.hitStreakTimer -= dt;
    if (this.hitStreakTimer <= 0) this.hitStreak = 0;
  }

  _buffer(kind) {
    // One slot, so a second input inside the window discards the first. Latest
    // intent winning is the right policy for an action game — a player who
    // presses dodge after attack means dodge — but it is still a dropped input,
    // and docs/FALSIFY.md lists 先行入力の取りこぼし as unmeasured. Count it, so
    // the rate is a number rather than an opinion.
    if (this.bufferedInput && this.bufferTime > 0 && this.bufferedInput !== kind) {
      this.bufferDropped = (this.bufferDropped || 0) + 1;
      this.lastBufferDrop = `${this.bufferedInput}->${kind}`;
    }
    this.bufferedInput = kind;
    this.bufferTime = 0.28;
    this.bufferOffered = (this.bufferOffered || 0) + 1;
  }

  _tryConsumeBuffer(wx, wz) {
    const b = this.bufferedInput;
    if (!b) return;

    switch (b) {
      case 'dodge': {
        if (this.rollType === 'overload') {
          if (this.stamina >= 30) {
            this.bufferedInput = null;
            this.setState(STATE.BACKSTEP, { duration: 0.7, motion: -2.4 });
            this.spendStamina(30);
          }
          return;
        }
        const cost = this.rollType === 'light' ? 18 : this.rollType === 'medium' ? 22 : 28;
        if (this.stamina < 8) return;
        this.bufferedInput = null;
        const iframes = this.rollType === 'light' ? 0.44 : this.rollType === 'medium' ? 0.36 : 0.28;
        const speed = this.rollType === 'light' ? 9.6 : this.rollType === 'medium' ? 8.6 : 7.2;
        const dur = this.rollType === 'heavy' ? 0.78 : 0.62;
        this.startRoll(wx, wz, { cost, iframes, speed, duration: dur });
        this.game.onRoll?.(this);
        return;
      }
      case 'light':
      case 'heavy': {
        if (this.stamina < 3) return;
        const cls = this.weaponClass;
        const heavy = b === 'heavy';
        const chain = heavy ? HEAVY_COMBOS[cls] : COMBOS[cls];
        if (!chain) return;

        // Running attacks replace the first hit of the chain.
        let id;
        if (this.isSprinting && this.comboStep === 0) {
          id = RUN_ATTACKS[cls] || chain[0];
        } else {
          const sameChain = this.comboChain === (heavy ? 'heavy' : 'light');
          const step = sameChain && this.comboWindow > 0 ? (this.comboStep + 1) % chain.length : 0;
          id = chain[step];
          this.comboStep = step;
          this.comboChain = heavy ? 'heavy' : 'light';
        }

        if (cls === 'staff') { this._castSpell(); this.bufferedInput = null; return; }
        if (cls === 'bow') { this._shootArrow(); this.bufferedInput = null; return; }

        // Criticals take priority over a normal swing.
        if (!heavy) {
          const riposte = findRiposteTarget(this, this.game.actors);
          if (riposte) {
            this.bufferedInput = null;
            executeCritical(this.game, this, riposte, 'riposte');
            return;
          }
          const back = findBackstabTarget(this, this.game.actors);
          if (back) {
            this.bufferedInput = null;
            executeCritical(this.game, this, back, 'backstab');
            return;
          }
        }

        this.bufferedInput = null;
        this.isSprinting = false;
        this.sprintHeld = 0;
        this.startAttack(id, { staminaMul: this.twoHand ? 1.08 : 1 });
        this.game.onSwing?.(this, id);
        return;
      }
      case 'parry': {
        if (this.stamina < 12) return;
        this.bufferedInput = null;
        this.spendStamina(12);
        this.setState(STATE.PARRY, { duration: 0.6 });
        return;
      }
      case 'spell': {
        this.bufferedInput = null;
        this._castSpell();
        return;
      }
      case 'item': {
        this.bufferedInput = null;
        this.useQuickItem();
        return;
      }
      case 'jump': {
        if (!this.grounded || this.stamina < 10) return;
        this.bufferedInput = null;
        this.spendStamina(10);
        this.grounded = false;
        this.velY = 7.6;
        this.setState(STATE.JUMP, { duration: 0.9 });
        return;
      }
      default:
        this.bufferedInput = null;
    }
  }

  // -------------------------------------------------------------------------
  //  Abilities
  // -------------------------------------------------------------------------

  _castSpell() {
    const id = this.spells[this.spellIndex];
    const spell = getSpell(id);
    if (!spell) { this.game.notify('魔法が装備されていない'); return; }
    const catalyst = [this.rightHand, this.leftHand].find((w) => w && w.catalyst);
    if (!catalyst) { this.game.notify('触媒が必要だ'); return; }
    if (catalyst.catalyst !== spell.school) {
      this.game.notify(spell.school === 'int' ? '杖が必要だ' : '聖印が必要だ');
      return;
    }
    if (this.fp < spell.fp) { this.game.notify('FPが足りない'); return; }
    for (const k in spell.req || {}) {
      if ((this.stats[k] || 0) < spell.req[k]) { this.game.notify('能力値が足りない'); return; }
    }

    this.fp -= spell.fp;
    this.castQueued = spell;
    this.setState(STATE.CAST, { action: ATTACKS.cast, actionId: 'cast', duration: Math.max(0.5, spell.cast) });
    this.spendStamina(8);
    this.game.schedule(spell.cast * 0.55, () => {
      if (this.dead) return;
      this.releaseSpell(spell);
    });
  }

  releaseSpell(spell) {
    const g = this.game;
    const scale = spell.scale ? 0.6 + 1.4 * (this.stats[spell.scale] / 60) : 1;
    const power = (spell.dmg || 0) * scale * this.dmgMul;

    const hand = this.rig.boneTip('handR', {});
    const dir = this.aimDirection();

    if (spell.heal) {
      this.heal(spell.heal * scale);
      g.particles.burst(this.x, this.y + 1.0, this.z, 26, {
        r: spell.color[0], g: spell.color[1], b: spell.color[2],
        size: 0.22, life: 0.9, spread: 1.4, up: 2.2, gravity: 1.5,
        blend: BLEND.ADDITIVE, alpha: 0.9, drag: 1.2,
      });
      g.audio.playSpell('heal');
      return;
    }
    if (spell.buff) {
      this.addBuff({ id: spell.id, ...spell.buff });
      g.particles.burst(this.x, this.y + 1.0, this.z, 20, {
        r: spell.color[0], g: spell.color[1], b: spell.color[2],
        size: 0.18, life: 0.8, spread: 1.0, up: 1.8, gravity: 0.8,
        blend: BLEND.ADDITIVE, alpha: 0.85, drag: 1.4,
      });
      g.audio.playSpell('buff');
      return;
    }
    if (spell.ground) {
      const t = this.lockTarget || g.nearestEnemy(this, 16, 1.4);
      const tx = t ? t.x : this.x + dir.x * 8;
      const tz = t ? t.z : this.z + dir.z * 8;
      g.areaEffects.push(new AreaEffect(g, {
        x: tx, y: g.world.heightAt(tx, tz), z: tz,
        radius: spell.radius || 3.4, delay: spell.delay || 0.5,
        damage: power, type: spell.element || 'magic',
        source: this, faction: FACTION.PLAYER, color: spell.color,
      }));
      g.audio.playSpell('pyre');
      return;
    }
    if (spell.cone) {
      for (let i = 0; i < 26; i++) {
        const spreadA = (Math.random() - 0.5) * 0.7;
        const ca = Math.atan2(dir.x, dir.z) + spreadA;
        g.projectiles.push(new Projectile(g, {
          x: hand.x, y: hand.y, z: hand.z,
          vx: Math.sin(ca) * (spell.speed + Math.random() * 6),
          vy: dir.y * spell.speed * 0.6 + (Math.random() - 0.5) * 2,
          vz: Math.cos(ca) * (spell.speed + Math.random() * 6),
          life: spell.life || 1.0, damage: power / 6, poise: 4,
          type: spell.element || 'magic', source: this, faction: FACTION.PLAYER,
          gravity: 0, color: spell.color, size: 0.3, radius: 0.4,
          status: spell.effect ? { type: spell.effect.type, build: spell.effect.build / 6 } : null,
          trail: false, kind: 'orb',
        }));
      }
      g.audio.playSpell('frost');
      return;
    }

    g.projectiles.push(new Projectile(g, {
      x: hand.x, y: hand.y, z: hand.z,
      vx: dir.x * spell.speed, vy: dir.y * spell.speed, vz: dir.z * spell.speed,
      life: spell.life || 3, damage: power, poise: 14,
      type: spell.element || 'magic', source: this, faction: FACTION.PLAYER,
      gravity: spell.element === 'fire' ? -2 : 0,
      color: spell.color, size: 0.28, radius: 0.34,
      homing: this.lockTarget ? 1.6 : 0, target: this.lockTarget,
      kind: 'orb',
    }));
    g.audio.playSpell(spell.element === 'fire' ? 'fire' : 'magic');
  }

  _shootArrow() {
    const arrows = this.countItem('arrow');
    this.setState(STATE.ATTACK, { action: ATTACKS.bow_shot, actionId: 'bow_shot', duration: ATTACKS.bow_shot.dur });
    this.spendStamina(ATTACKS.bow_shot.stam);
    const w = this.rightHand;
    const level = this.upgradeLevelOf(w);
    const atk = weaponAttack(w, level, this.stats);
    const dir = this.aimDirection();
    this.game.schedule(0.52, () => {
      if (this.dead) return;
      const hand = this.rig.boneTip('handL', {});
      this.game.projectiles.push(new Projectile(this.game, {
        x: hand.x, y: hand.y, z: hand.z,
        vx: dir.x * 42, vy: dir.y * 42 + 1.2, vz: dir.z * 42,
        life: 3, damage: atk.total * this.dmgMul, poise: 12,
        type: 'physical', source: this, faction: FACTION.PLAYER,
        gravity: -7, color: [0.62, 0.55, 0.44], size: 0.1, radius: 0.22,
        kind: 'arrow', emissive: 0,
      }));
      this.game.audio.playBow();
    });
  }

  aimDirection() {
    if (this.lockTarget) {
      const dx = this.lockTarget.x - this.x;
      const dy = (this.lockTarget.y + this.lockTarget.height * 0.55) - (this.y + 1.35);
      const dz = this.lockTarget.z - this.z;
      const d = Math.hypot(dx, dy, dz) || 1;
      return { x: dx / d, y: dy / d, z: dz / d };
    }
    const pitch = -this.camera.pitch * 0.8;
    const cy = Math.cos(pitch);
    return { x: Math.sin(this.yaw) * cy, y: Math.sin(pitch), z: Math.cos(this.yaw) * cy };
  }

  useQuickItem() {
    const id = this.quickItems[this.quickIndex];
    if (!id) { this.drinkFlask('hp'); return; }
    const item = getItem(id);
    if (!item || this.countItem(id) <= 0) return;
    this.setState(STATE.DRINK, { duration: 0.85 });
    this.removeItem(id, 1);
    this.game.schedule(0.42, () => {
      if (this.dead) return;
      this.applyConsumable(item);
    });
  }

  applyConsumable(item) {
    const g = this.game;
    if (item.effect) {
      if (item.effect.cure) {
        const st = this.status[item.effect.cure];
        if (st) { st.active = 0; st.build = 0; }
        g.notify(`${item.name}を使った`);
      } else {
        this.addBuff({ id: item.id, ...item.effect });
        g.notify(`${item.name}の効果`);
      }
    }
    if (item.souls) { this.gainSouls(item.souls); }
    if (item.homeward) { g.warpToLastGrace(); }
    if (item.throw) {
      const dir = this.aimDirection();
      const hand = this.rig.boneTip('handR', {});
      g.projectiles.push(new Projectile(g, {
        x: hand.x, y: hand.y, z: hand.z,
        vx: dir.x * 22, vy: dir.y * 22 + 3, vz: dir.z * 22,
        damage: item.throw.dmg, type: item.throw.element || 'physical',
        source: this, faction: FACTION.PLAYER, gravity: -12,
        color: item.throw.element === 'fire' ? [1, 0.5, 0.15] : [0.7, 0.7, 0.72],
        size: 0.14, radius: 0.26, kind: item.throw.element ? 'orb' : 'arrow',
        explode: item.throw.radius ? {
          radius: item.throw.radius, damage: item.throw.dmg,
          type: 'fire', color: [1, 0.5, 0.15], faction: FACTION.PLAYER, source: this,
        } : null,
      }));
    }
    g.audio.playUseItem();
  }

  drinkFlask(kind) {
    if (!this.canAct) return false;
    const flask = kind === 'fp' ? this.flaskFp : this.flaskHp;
    if (flask.cur <= 0) { this.game.notify('聖杯瓶が空だ'); return false; }
    flask.cur--;
    this.setState(STATE.DRINK, { duration: 0.9 });
    this.game.schedule(0.45, () => {
      if (this.dead) return;
      if (kind === 'fp') this.fp = Math.min(this.maxFp, this.fp + flask.heal);
      else this.heal(flask.heal);
      this.game.particles.burst(this.x, this.y + 1.2, this.z, 12, {
        r: kind === 'fp' ? 0.4 : 0.9, g: kind === 'fp' ? 0.6 : 0.25, b: kind === 'fp' ? 1.0 : 0.3,
        size: 0.14, life: 0.6, spread: 0.8, up: 1.4, gravity: 0.5,
        blend: BLEND.ADDITIVE, alpha: 0.8, drag: 2,
      });
      this.game.audio.playDrink();
    });
    return true;
  }

  refillFlasks() {
    this.flaskHp.cur = this.flaskHp.max;
    this.flaskFp.cur = this.flaskFp.max;
  }

  gainSouls(n) {
    const gained = Math.round(n * this.soulsMul);
    this.souls += gained;
    this.totalSouls += gained;
    return gained;
  }

  canLevel() { return this.souls >= levelCost(this.playerLevel); }

  levelUp(stat) {
    const cost = levelCost(this.playerLevel);
    if (this.souls < cost) return false;
    if (this.stats[stat] >= 99) return false;
    this.souls -= cost;
    this.stats[stat]++;
    this.playerLevel++;
    this.recomputeDerived();
    return true;
  }

  // -------------------------------------------------------------------------

  takeDamage(info) {
    const scaled = { ...info, damage: info.damage * this.takenMul };
    const res = super.takeDamage(scaled);
    if (res.hit) {
      this.game.onPlayerHurt?.(res, info);
      this.lockTarget = this.lockTarget || (info.source && info.source.faction !== this.faction ? info.source : null);
    }
    return res;
  }

  die(killer) {
    if (this.dead) return;
    // Drop the embers where you fell — recoverable exactly once.
    this.deathDrop = { x: this.x, y: this.y, z: this.z, souls: this.souls };
    this.souls = 0;
    super.die(killer);
  }

  update(dt) {
    super.update(dt);
    if (!this.dead) {
      // FP trickles back only from items and rest; this is intentional.
      this.fp = Math.min(this.maxFp, this.fp);
    }
  }

  onFootstep(speed) {
    this.game.onFootstep?.(this, speed);
  }

  onLand(fallSpeed) {
    if (fallSpeed > 15) {
      const dmg = Math.pow(fallSpeed - 15, 1.7) * 3.2;
      if (fallSpeed > 27) {
        this.hp = 0;
        this.die(null);
      } else {
        this.takeDamage({ damage: dmg, poise: 40, type: 'physical', ignoreInvuln: true, source: null, knockback: 0 });
      }
      this.game.shake(0.4, 0.25);
    } else if (fallSpeed > 6) {
      this.game.particles.dustStep(this.x, this.y, this.z, 1.6);
    }
    this.game.audio.playLand(fallSpeed);
  }
}

// ---------------------------------------------------------------------------
//  Camera
// ---------------------------------------------------------------------------

// How far the camera may move and turn on its own in one frame.
//
// The rig has had a per-frame bound on every bone for a while, on the grounds
// that a limb which snaps is visible. The camera is the same defect with the
// whole screen behind it, and until these existed nothing measured it: a wall
// beside the player threw the view 19.8 m and 88 degrees in a single frame, and
// switching lock-on targets swung it 0.76 rad. tools/unit-camera.mjs drives
// these cases directly, in about a second, with no browser.
const CAM_SKIN = 0.42;          // clearance kept between the boom and terrain
const CAM_MIN_BOOM = 1.25;      // m, closest the boom may be drawn in to
const CAM_BOOM_IN = 7.0;        // m/s, racing an obstruction about to occlude
const CAM_BOOM_OUT = 2.2;       // m/s, nothing to race, so ease back out
const CAM_MAX_LIFT = 1.5;       // m, ground roughness only — never a wall
const CAM_AIM_RATE = 12;        // 1/s, how quickly the aim follows the framing
// The aim's bound is angular, not linear. Sizing it in metres per second was
// the mistake that let the view exceed its cap in the real game: the same
// 0.32 m of aim slide is a sixteenth of a radian at a 5 m boom and a quarter of
// one at a 1.3 m boom, so a linear cap bounds nothing in particular. Converting
// through the current view distance is what makes it spend a known share of the
// same budget the swing spends.
const CAM_AIM_ANG = 1.6;        // rad/s of view rotation the aim may contribute
// What the camera may swing around the player under its own steam. Player look
// input is deliberately outside this: that is the player's own hand, and
// limiting it would read as the controller sticking. This bounds the game
// moving the camera — lock-on, and the sprint realign.
//
// These sit below the 0.10 rad/frame the view is held to rather than at it,
// because the eye swinging and the aim sliding off the focus both turn the
// view and their steps add. Set to the cap, the pair measured 0.1005 — and the
// fix for that is to leave room in the budget, not to raise the number the
// budget is checked against.
//
// 4.0 and 1.6 together are 5.6, inside the 6.0 the view is held to, with the
// rest left for the focus sliding as the shoulder offset swings around the
// player. Measured before this split: 8.25 rad/s, from dYaw 0.240 and dAim
// 0.3225 arriving on the same frame — each inside its own cap, and together
// well outside the only bound that matters.
const CAM_SWING_RATE = 4.0;     // rad/s — a 90 deg lock-on lands in 0.39 s
const CAM_SWING_STEP = CAM_SWING_RATE * MAX_DT;   // backstop only; see MAX_DT

export class PlayerCamera {
  constructor(player) {
    this.player = player;
    this.yaw = 0;
    this.pitch = -0.20;
    this.distance = 5.4;
    this.targetDistance = 5.4;
    this.height = 1.50;
    this.shakeAmp = 0;
    this.shakeT = 0;
    this.fov = 62;
    this.targetFov = 62;
    this.pos = { x: 0, y: 0, z: 0 };
    this.look = { x: 0, y: 0, z: 0 };
    this.autoAlign = 0;

    // --- continuity state ----------------------------------------------------
    // Everything below exists so that the frame the game changes its mind is
    // not a frame the player sees a cut. Measured by tools/unit-camera.mjs.
    /** How much of the framing belongs to the lock-on, blended not switched. */
    this.lockBlend = 0;
    /** Boom length actually in use, rate-limited toward what collision wants. */
    this.boom = this.distance;
    /** Damped lift out of the ground, bounded so a wall cannot launch it. */
    this.groundLift = 0;
    /** Aim point as an offset from the focus, so the eye's own motion is not
     *  compensated for by pointing the camera somewhere else. */
    this.aimOff = { x: 0, y: 0, z: 0 };
    this.lastLock = null;
    this.seeded = false;
  }

  update(dt, input, world, lockTarget) {
    const p = this.player;

    // Blended, not switched. See the shoulder offset below.
    this.lockBlend = this.seeded
      ? damp(this.lockBlend, lockTarget ? 1 : 0, 8, dt)
      : (lockTarget ? 1 : 0);

    if (lockTarget) {
      // Lock-on: frame both combatants, biasing toward the target.
      const dx = lockTarget.x - p.x;
      const dz = lockTarget.z - p.z;
      const dist = Math.hypot(dx, dz);
      const desiredYaw = Math.atan2(dx, dz);
      this.yaw = this._swing(this.yaw, dampAngle(this.yaw, desiredYaw, 9, dt), dt);
      const heightDiff = (lockTarget.y + lockTarget.height * 0.6) - (p.y + 1.3);
      const desiredPitch = clamp(-0.10 + heightDiff / Math.max(dist, 3) * 0.5, -0.55, 0.35);
      this.pitch = this._swing(this.pitch, damp(this.pitch, desiredPitch, 6, dt), dt);
      this.targetDistance = clamp(4.8 + dist * 0.20, 4.8, 8.4);
    } else {
      this.yaw -= input.look.x;
      this.pitch = clamp(this.pitch - input.look.y, -1.05, 0.72);
      this.targetDistance = 5.4;

      // Gently swing behind the player when sprinting and not steering.
      if (p.isSprinting && Math.abs(input.look.x) < 0.001) {
        this.yaw = this._swing(this.yaw, dampAngle(this.yaw, p.yaw, 1.6, dt), dt);
      }
    }

    // Widen the view when sprinting — a cheap, strong speed cue.
    this.targetFov = p.isSprinting ? 70 : lockTarget ? 60 : 62;
    this.fov = damp(this.fov, this.targetFov, 5, dt);
    // targetDistance comes from the distance to the lock target, so it inherits
    // whatever that actor's coordinates are. `distance` is a damped
    // accumulator, and damp(NaN, x) is NaN forever — one bad frame would pin
    // the boom, the eye and every frame after it. Guard at the source as well
    // as recovering below; a value that never goes bad needs no recovery.
    if (!Number.isFinite(this.targetDistance)) this.targetDistance = 5.4;
    if (!Number.isFinite(this.distance)) this.distance = this.targetDistance;
    this.distance = damp(this.distance, this.targetDistance, 7, dt);
    if (!Number.isFinite(this.boom)) this.boom = this.distance;
    if (!Number.isFinite(this.groundLift)) this.groundLift = 0;
    if (!Number.isFinite(this.lockBlend)) this.lockBlend = 0;
    if (!Number.isFinite(this.yaw)) this.yaw = 0;
    if (!Number.isFinite(this.pitch)) this.pitch = -0.20;
    // shakeDur is only assigned by shake(); if anything sets shakeT or shakeAmp
    // directly, the k below divides by undefined.
    if (!Number.isFinite(this.shakeDur) || this.shakeDur <= 0) this.shakeDur = 0.2;

    // Over-the-shoulder offset: without it the character stands squarely in
    // front of everything the player is trying to look at. Blended on the
    // lock-on rather than switched — the offset, the focus height and the aim
    // point all move together over about a fifth of a second, so acquiring a
    // target reframes instead of cutting.
    const shoulder = lerp(0.52, 0.22, this.lockBlend);
    const rx2 = Math.cos(this.yaw), rz2 = -Math.sin(this.yaw);
    const focusX = p.x + rx2 * shoulder;
    const focusY = p.y + this.height + 0.25 * this.lockBlend;
    const focusZ = p.z + rz2 * shoulder;

    const cp = Math.cos(this.pitch);
    let ox = -Math.sin(this.yaw) * cp;
    let oz = -Math.cos(this.yaw) * cp;
    const oy = Math.sin(this.pitch);

    // --- how long the boom wants to be --------------------------------------
    //
    // Walk it out from the focus and interpolate the crossing instead of
    // snapping to whichever sample happened to be under the ground. Eight
    // discrete samples moved the boom in steps of an eighth of its length —
    // 0.68 m arriving in one frame, which is a jump on its own even when
    // nothing else is wrong. Sixteen samples plus the crossing makes the
    // length a continuous function of where the player is standing.
    let want = this.distance;
    const focusGround = world.heightAt(focusX, focusZ);
    // Guarded like the loop samples below. A non-finite seed would make the
    // first crossing's interpolation NaN; `prevGap > 0` happens to reject NaN
    // and fall back to the segment start, so this is not a live defect — but
    // relying on a comparison's NaN behaviour to be safe is not a thing to
    // leave in place.
    let prevGap = Number.isFinite(focusGround)
      ? focusY - (focusGround + CAM_SKIN)
      : Infinity;
    for (let i = 1; i <= 16; i++) {
      const t = (i / 16) * this.distance;
      const sx = focusX + ox * t;
      const sy = focusY + oy * t;
      const sz = focusZ + oz * t;
      const gh = world.heightAt(sx, sz);
      // An unanswerable sample is not an obstruction. Treating it as one would
      // pull the boom in for the rest of the walk along a world edge.
      const gap = Number.isFinite(gh) ? sy - (gh + CAM_SKIN) : Infinity;
      if (gap < 0) {
        const t0 = ((i - 1) / 16) * this.distance;
        // Where along this segment the boom actually crossed the surface.
        const hit = prevGap > 0 ? t0 + (t - t0) * (prevGap / (prevGap - gap)) : t0;
        want = Math.max(CAM_MIN_BOOM, hit - 0.30);
        break;
      }
      prevGap = gap;
    }

    // --- and how fast it may get there --------------------------------------
    //
    // Asymmetric, because the two directions are different problems: coming in
    // races an obstruction that is about to occlude the player, going out has
    // nothing to race and a boom that springs back the instant a pillar clears
    // is the most obvious cut a third-person camera makes.
    if (!this.seeded) this.boom = want;
    else if (want < this.boom) this.boom = Math.max(want, this.boom - CAM_BOOM_IN * dt);
    else this.boom = Math.min(want, this.boom + CAM_BOOM_OUT * dt);
    const dist = this.boom;

    this.shakeT -= dt;
    // Let the amplitude die with the timer. Without this a single heavy hit
    // leaves shakeAmp high for the rest of the session, and shake() taking
    // max(previous * 0.6, amp) then means a light hit an hour later still
    // shakes like the heavy one did.
    if (this.shakeT <= 0) this.shakeAmp = 0;
    let shakeX = 0, shakeY = 0;
    if (this.shakeT > 0 && this.shakeAmp > 0) {
      const k = this.shakeAmp * (this.shakeT / this.shakeDur);
      shakeX = (Math.random() - 0.5) * k;
      shakeY = (Math.random() - 0.5) * k;
    }

    const px = focusX + ox * dist;
    const pz = focusZ + oz * dist;
    const naturalY = focusY + oy * dist;

    // --- lift out of the ground ---------------------------------------------
    //
    // This used to be a bare max() against the terrain under the camera, which
    // has a failure mode far worse than the roughness it was smoothing: stand
    // near anything tall and the sample lands inside it, so the camera is
    // clamped to the top. Walking beside a wall threw the view 19.8 m upward
    // and 88 degrees over in one frame. The boom solve above is what keeps the
    // camera out of geometry now; this is only for the last few centimetres of
    // ground roughness, so it is bounded and damped rather than absolute.
    const groundHere = world.heightAt(px, pz);
    // An unanswerable sample is not a height of zero — it is no information.
    // Forcing the target to zero made the lift oscillate wherever the height
    // field could not answer on alternate frames, which moved the eye further
    // than the boom limiter ever allows. Holding the current value is what
    // "unknown" actually means.
    const liftWant = Number.isFinite(groundHere)
      ? Math.min(CAM_MAX_LIFT, Math.max(0, groundHere + 0.30 - naturalY))
      : this.groundLift;
    const liftNext = this.seeded ? damp(this.groundLift, liftWant, 12, dt) : liftWant;
    // The lift moves the eye, so it spends the same budget the boom does and
    // needs the same kind of bound. Without it the two together can step
    // further in a frame than either is allowed to on its own.
    const liftCap = CAM_BOOM_IN * dt;
    this.groundLift += clamp(liftNext - this.groundLift, -liftCap, liftCap);

    this.pos.x = px + shakeX;
    this.pos.y = naturalY + this.groundLift + shakeY;
    this.pos.z = pz;

    // A non-finite camera renders nothing: the view matrix is garbage, no
    // geometry survives clipping, no depth is written, and the frame comes out
    // as bare sky. Nothing upstream is supposed to produce one — the height
    // field answers 0 for every coordinate including far outside the world —
    // but this class now carries damped accumulators (boom, groundLift, aimOff)
    // where it used to carry a hard max(), and a damped value poisoned once
    // stays poisoned for the rest of the session. That turns a transient glitch
    // into a permanent black screen, which is a much worse failure than the
    // snap the damping was added to remove.
    //
    // So: notice, recover, and count. The count is what makes it a fact rather
    // than a theory next time a frame comes back empty.
    if (!Number.isFinite(this.pos.x) || !Number.isFinite(this.pos.y) || !Number.isFinite(this.pos.z)) {
      this.nonFiniteFrames = (this.nonFiniteFrames || 0) + 1;
      this.boom = this.distance;
      this.groundLift = 0;
      this.aimOff.x = 0; this.aimOff.y = 0; this.aimOff.z = 0;
      const fy = Number.isFinite(focusY) ? focusY : (Number.isFinite(p.y) ? p.y + this.height : 0);
      const fx = Number.isFinite(focusX) ? focusX : (Number.isFinite(p.x) ? p.x : 0);
      const fz = Number.isFinite(focusZ) ? focusZ : (Number.isFinite(p.z) ? p.z : 0);
      this.pos.x = fx; this.pos.y = fy + 1; this.pos.z = fz - this.distance;
      this.focusX = fx; this.focusY = fy; this.focusZ = fz;
      this.look.x = fx; this.look.y = fy; this.look.z = fz;
      this.focusX = fx; this.focusY = fy; this.focusZ = fz;
      this._trk = null;
      // Recovery must not be a trap. Without this, `seeded` stays false — it is
      // only set at the end of a completed update — and every later frame takes
      // the un-seeded branches, which is not the state this class expects to be
      // in after the first frame.
      this.seeded = true;
      this._track(dt);
      return;
    }

    // --- where it is pointed -------------------------------------------------
    //
    // The aim is damped toward what the framing asks for, not assigned. Every
    // discontinuity the framing can produce arrives here — acquiring a lock,
    // dropping one, and above all switching between two targets on opposite
    // sides, which used to swing the view 0.76 rad in a single frame. Damping
    // the point handles all three with one mechanism, and the angular cap below
    // bounds whatever the damping alone does not.
    const aimW = 0.42 * this.lockBlend;
    const t = lockTarget || this.lastLock;
    const wx = t ? (t.x - focusX) * aimW : 0;
    const wy = t ? (t.y + t.height * 0.55 - focusY) * aimW : 0;
    const wz = t ? (t.z - focusZ) * aimW : 0;
    if (lockTarget) this.lastLock = lockTarget;
    else if (this.lockBlend < 0.01 || this.lastLock?.dead) this.lastLock = null;

    const a = this.aimOff;
    if (!this.seeded) { a.x = wx; a.y = wy; a.z = wz; } else {
      const k = 1 - Math.exp(-CAM_AIM_RATE * dt);
      let sx = (wx - a.x) * k, sy2 = (wy - a.y) * k, sz2 = (wz - a.z) * k;
      // A rate is not a bound: a long frame, or a switch to a target on the
      // other side, still lands a cut. Cap the step as well as damp it.
      const m = Math.hypot(sx, sy2, sz2);
      // How far the aim may slide this frame to rotate the view by no more than
      // CAM_AIM_ANG: an offset that far from the eye subtends that angle.
      const aimCap = CAM_AIM_ANG * dt * Math.max(1.0, dist);
      if (m > aimCap) { const f2 = aimCap / m; sx *= f2; sy2 *= f2; sz2 *= f2; }
      a.x += sx; a.y += sy2; a.z += sz2;
    }
    this.look.x = focusX + a.x;
    this.look.y = focusY + a.y;
    this.look.z = focusZ + a.z;

    this.focusX = focusX;
    this.focusY = focusY;
    this.focusZ = focusZ;
    this.seeded = true;
    this._track(dt);
  }

  /**
   * Start the continuity record over.
   *
   * Probes call this so that what they measure is what they drove. Reading the
   * running total during a probe that holds the player still measures a
   * stationary camera and reports 0.0000 — which is a true number about
   * nothing, and the third time in this project that a measurement has been
   * taken over a window where the thing being measured could not happen.
   */
  resetTracking() {
    this._trk = null;
    this.worstView = 0; this.worstDolly = 0;
    this.worstViewAt = -1; this.worstDollyAt = -1;
    this.worstViewWhy = null;
    this.trackFrames = 0;
    this.warpFrames = 0;
    this.angSum = 0;
  }

  /**
   * Watch how far the view actually cut, every frame, in the real game.
   *
   * tools/unit-camera.mjs drives this class with stubs, which is what makes it
   * fast enough to run before every audit — and also what makes it incomplete.
   * A stub world is not the terrain generator and a stub player does not roll,
   * get knocked back, or die. The rig learned this the expensive way: its own
   * probe watched a window it drove itself, reported a number 2.5 times under
   * the truth, and cost days. So the live camera reports on itself too, and the
   * audit reads the worst frame of the whole session rather than of a window.
   */
  _track(dt) {
    const dx = this.look.x - this.pos.x, dy = this.look.y - this.pos.y, dz = this.look.z - this.pos.z;
    const l = Math.hypot(dx, dy, dz) || 1;
    const nx = dx / l, ny = dy / l, nz = dz / l;
    const orbit = Math.hypot(this.pos.x - this.focusX, this.pos.y - this.focusY, this.pos.z - this.focusZ);
    const prev = this._trk;
    if (prev && dt > 1e-5) {
      const dot = clamp(nx * prev.x + ny * prev.y + nz * prev.z, -1, 1);
      const ang = Math.acos(dot);
      // A teleport moves the focus across the map; the view did not turn to
      // get there. Warps are the game cutting on purpose, and a cut on purpose
      // is a different thing from a cut by accident.
      const focusStep = v3distXZ({ x: this.focusX, z: this.focusZ }, prev.focus);
      const warped = focusStep > 3;
      // Counters, not a verdict. The audit's probe swung the camera 3.119 rad
      // and the tracker still reported a worst of exactly 0, which can only
      // mean every frame was discarded or every angle was zero — and those need
      // telling apart by counting, not by reasoning about which is likelier.
      this.angSum = (this.angSum || 0) + ang;
      if (warped) {
        this.warpFrames = (this.warpFrames || 0) + 1;
        this.lastWarpStep = +focusStep.toFixed(3);
      }
      if (!warped) {
        // Rates, for the same reason the rig reports rates: per-frame is a unit
        // that means something different on every machine, and the audit runs
        // on a software rasteriser at a fraction of the target frame rate.
        const vr = ang / dt;
        if (vr > this.worstView) {
          this.worstView = vr;
          this.worstViewAt = this.trackFrames;
          // One number cannot say which of the four things that move the view
          // did it. Record them, so the next time this exceeds its bound the
          // answer does not need another day of diagnostics.
          this.worstViewWhy = {
            dYaw: +((this.yaw - prev.yaw)).toFixed(4),
            dPitch: +((this.pitch - prev.pitch)).toFixed(4),
            dBoom: +((orbit - prev.orbit)).toFixed(4),
            dFocus: +v3distXZ({ x: this.focusX, z: this.focusZ }, prev.focus).toFixed(4),
            dAim: +Math.hypot(this.aimOff.x - prev.aim.x, this.aimOff.y - prev.aim.y,
              this.aimOff.z - prev.aim.z).toFixed(4),
            lock: +this.lockBlend.toFixed(3),
            dt: +dt.toFixed(4),
          };
        }
        const dr = Math.abs(orbit - prev.orbit) / dt;
        if (dr > this.worstDolly) { this.worstDolly = dr; this.worstDollyAt = this.trackFrames; }
      }
      this.trackFrames++;
    } else if (this._trk === null) {
      // First frame after a reset only seeds the reference. It must not clear
      // the maxima: an accidental reset mid-probe is indistinguishable from a
      // clean run, and reports a perfect zero either way.
      this.worstView = this.worstView || 0;
      this.worstDolly = this.worstDolly || 0;
      this.trackFrames = this.trackFrames || 0;
    }
    this._trk = {
      x: nx, y: ny, z: nz, orbit,
      focus: { x: this.focusX, z: this.focusZ },
      yaw: this.yaw, pitch: this.pitch,
      aim: { x: this.aimOff.x, y: this.aimOff.y, z: this.aimOff.z },
    };
  }

  /**
   * Bound one frame of camera rotation the game asked for.
   *
   * Damping toward a target is a rate, and a rate scales with how far away the
   * target is: dampAngle at 9/s takes 0.44 rad in a single frame when the
   * target is on the opposite side, which is what switching lock-on between two
   * enemies does. That swung the eye 1.74 m around the player in one frame.
   *
   * The bound goes on the eye rather than on the view direction. Capping the
   * direction instead would hold the number down by aiming the camera away from
   * the player while the eye kept swinging, which is a worse picture than the
   * one being prevented.
   */
  _swing(from, to, dt) {
    let d = to - from;
    if (d > Math.PI) d -= TAU; else if (d < -Math.PI) d += TAU;
    const cap = Math.min(CAM_SWING_RATE * dt, CAM_SWING_STEP);
    if (d > cap) d = cap; else if (d < -cap) d = -cap;
    return from + d;
  }

  shake(amp, dur) {
    this.shakeAmp = Math.max(this.shakeAmp * 0.6, amp);
    this.shakeDur = dur;
    this.shakeT = dur;
  }
}
