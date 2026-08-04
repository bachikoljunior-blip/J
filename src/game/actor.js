// ============================================================================
//  actor.js — the shared body for every living thing in the world.
//
//  Movement, collision, the animation state machine, poise/stagger, status
//  build-up, guarding, parrying and death all live here. The player and every
//  enemy differ only in what drives `intent` each frame.
// ============================================================================

import {
  clamp, lerp, saturate, damp, dampAngle, angleDelta, TAU,
  v3distXZ, closestOnSegmentXZ,
} from '../core/math.js';
import {
  Rig, HUMANOID, QUADRUPED, WINGED, MAT, deriveTemplate, PROPORTIONS,
} from './rig.js';
import {
  humanoidLocomotion, humanoidArmsNeutral, quadrupedAnimate, wingedAnimate,
  poseRoll, poseBackstep, poseBlock, poseParry, poseHurt, poseStagger,
  poseDeath, poseJump, poseDrink, poseRest, ATTACKS,
} from './anim.js';
import { mitigate } from './items.js';
import { MATERIAL as SURFACE } from '../gfx/textures.js';

export const STATE = {
  IDLE: 'idle', MOVE: 'move', ROLL: 'roll', BACKSTEP: 'backstep',
  ATTACK: 'attack', BLOCK: 'block', PARRY: 'parry', PARRIED: 'parried',
  HURT: 'hurt', STAGGER: 'stagger', DEATH: 'death', JUMP: 'jump',
  DRINK: 'drink', REST: 'rest', CAST: 'cast', RIPOSTE: 'riposte',
  RIPOSTED: 'riposted', SPAWN: 'spawn', TAUNT: 'taunt',
};

export const FACTION = { PLAYER: 0, ENEMY: 1, NEUTRAL: 2 };

const GRAVITY = -26;
const MAX_STEP = 0.62;         // height the actor can walk up without jumping
const SLOPE_LIMIT = 0.78;      // 1 - normal.y above this is unwalkable

let NEXT_ID = 1;

export class Actor {
  constructor(game, opts = {}) {
    this.id = NEXT_ID++;
    this.game = game;
    this.world = game.world;

    this.x = opts.x || 0;
    this.y = opts.y !== undefined ? opts.y : this.world.heightAt(this.x, opts.z || 0);
    this.z = opts.z || 0;
    this.yaw = opts.yaw || 0;
    this.velX = 0; this.velY = 0; this.velZ = 0;
    this.grounded = true;

    this.radius = opts.radius || 0.42;
    this.height = opts.height || 1.75;
    this.scale = opts.scale || 1;
    this.mass = opts.mass || 1;

    this.faction = opts.faction !== undefined ? opts.faction : FACTION.ENEMY;
    this.name = opts.name || 'unknown';
    this.level = opts.level || 1;

    // --- vitals -------------------------------------------------------------
    this.maxHp = opts.maxHp || 100;
    this.hp = this.maxHp;
    this.maxStamina = opts.maxStamina || 100;
    this.stamina = this.maxStamina;
    this.staminaRegen = opts.staminaRegen || 34;
    this.staminaLock = 0;
    this.maxPoise = opts.poise || 20;
    this.poise = this.maxPoise;
    this.poiseRegen = opts.poiseRegen || 14;

    this.defense = opts.defense || 8;
    this.resist = opts.resist || {};

    // --- state machine ------------------------------------------------------
    this.state = STATE.IDLE;
    this.stateT = 0;
    this.action = null;         // current attack definition
    this.actionId = null;
    this.actionU = 0;
    this.hitSet = new Set();
    this.invuln = 0;            // i-frame timer
    this.hyperArmor = 0;
    this.comboIndex = 0;
    this.comboWindow = 0;
    this.queuedAction = null;

    this.blocking = false;
    this.parryTimer = 0;
    this.parryWindow = 0.22;
    this.riposteVictim = null;
    this.staggerSource = null;

    // --- locomotion ---------------------------------------------------------
    this.moveSpeed = opts.moveSpeed || 3.4;
    this.runSpeed = opts.runSpeed || 5.6;
    this.sprintSpeed = opts.sprintSpeed || 7.6;
    this.turnRate = opts.turnRate || 9;
    this.phase = 0;
    this.moveBlend = 0;
    this.speedRatio = 0;
    this.intentX = 0;
    this.intentZ = 0;
    this.intentSpeed = 0;
    this.lookPitch = 0;
    this.headYaw = 0;
    this.rootMotion = 0;        // forward impulse from the current action

    // --- status effects -----------------------------------------------------
    this.status = {
      poison: { build: 0, active: 0, threshold: 100, tick: 0 },
      frost: { build: 0, active: 0, threshold: 100, tick: 0 },
      bleed: { build: 0, active: 0, threshold: 100, tick: 0 },
    };
    this.buffs = [];

    // --- rig ----------------------------------------------------------------
    const base = opts.rig === 'quadruped' ? QUADRUPED
      : opts.rig === 'winged' ? WINGED : HUMANOID;
    // Body shape, not just body size. A brute and a duellist at the same scale
    // should be distinguishable in silhouette alone, because at the distance
    // where you decide how to approach an enemy, silhouette is all you have.
    // deriveTemplate caches by identity, so the derived skeleton is built once
    // per (template, build) pair, not once per spawn.
    const build = opts.build && PROPORTIONS[opts.build] ? PROPORTIONS[opts.build] : null;
    const template = build ? deriveTemplate(base, build) : base;
    this.rigKind = opts.rig || 'humanoid';
    this.rig = new Rig(template, this.scale);
    this.palette = opts.palette || defaultPalette();
    this.weapon = opts.weapon || null;
    this.offhand = opts.offhand || null;
    this.weaponClass = opts.weaponClass || 'sword';

    this.dead = false;
    this.deathTimer = 0;
    this.removeAfter = opts.removeAfter || 8;
    this.flash = 0;
    this.lastHitBy = null;
    this.hitStop = 0;
    this.lastDamageDir = 0;

    this.footTimer = 0;
    this.lastFootPhase = 0;
    this.aggro = false;
    this.visible = true;
  }

  // -------------------------------------------------------------------------
  //  Queries
  // -------------------------------------------------------------------------

  get eyeY() { return this.y + this.height * 0.86; }
  get centerY() { return this.y + this.height * 0.55; }
  get alive() { return !this.dead; }
  get busy() {
    return this.state === STATE.ATTACK || this.state === STATE.ROLL
      || this.state === STATE.BACKSTEP || this.state === STATE.HURT
      || this.state === STATE.STAGGER || this.state === STATE.PARRY
      || this.state === STATE.PARRIED || this.state === STATE.CAST
      || this.state === STATE.DRINK || this.state === STATE.RIPOSTE
      || this.state === STATE.RIPOSTED || this.state === STATE.DEATH;
  }
  get canAct() { return !this.dead && !this.busy; }

  distanceTo(o) { return v3distXZ(this, o); }

  angleTo(o) { return Math.atan2(o.x - this.x, o.z - this.z); }

  /**
   * The facing the body is *drawn* at, which is what the player can see.
   *
   * The rig damps the actor's yaw under the continuity budget, so a body that
   * has decided to turn takes up to a quarter of a second to finish doing it.
   * Judging a backstab or a block on `this.yaw` means judging it on an intent
   * the model has not expressed yet: an enemy that visibly still has its back
   * turned would deny the backstab, and one that visibly faces away would block.
   *
   * Weapon hitboxes already work this way — combat.js builds them from the rig's
   * own bones — so the facing tests were the odd ones out. What the player sees
   * is what the rules use.
   */
  get drawnYaw() {
    const y = this.rig && this.rig._yawS;
    return y === null || y === undefined ? this.yaw : y;
  }

  /** Is `o` in front of this actor, within `halfAngle`? */
  facing(o, halfAngle = 1.05) {
    return Math.abs(angleDelta(this.drawnYaw, this.angleTo(o))) < halfAngle;
  }

  /** Is this actor behind `o` (for backstabs)? */
  isBehind(o) {
    return Math.abs(angleDelta(o.drawnYaw, Math.atan2(this.x - o.x, this.z - o.z))) > 2.10;
  }

  // -------------------------------------------------------------------------
  //  State machine
  // -------------------------------------------------------------------------

  setState(state, opts = {}) {
    if (this.state === STATE.DEATH && state !== STATE.DEATH) return;
    this.state = state;
    this.stateT = 0;
    this.actionU = 0;
    this.hitSet.clear();
    if (opts.action) {
      this.action = opts.action;
      this.actionId = opts.actionId || null;
    } else if (state !== STATE.ATTACK && state !== STATE.CAST) {
      this.action = null;
      this.actionId = null;
    }
    this.stateDuration = opts.duration || (this.action ? this.action.dur : 0.4);
    this.rootMotion = opts.motion !== undefined ? opts.motion : 0;
    this.rig.blendRate = opts.blendRate || (
      state === STATE.ATTACK ? 30
        : state === STATE.ROLL ? 26
          : state === STATE.HURT ? 24
            : state === STATE.BLOCK ? 20 : 14);
  }

  startAttack(actionId, mods = {}) {
    const def = ATTACKS[actionId];
    if (!def) return false;
    const cost = (def.stam || 0) * (mods.staminaMul || 1);
    if (this.stamina < 1) return false;
    this.spendStamina(cost);
    this.setState(STATE.ATTACK, { action: def, actionId, duration: def.dur * (mods.speedMul ? 1 / mods.speedMul : 1), motion: def.motion });
    this.actionSpeedMul = mods.speedMul || 1;
    this.actionDamageMul = mods.damageMul || 1;
    this.hyperArmor = def.dur * 0.5;
    return true;
  }

  startRoll(dirX, dirZ, opts = {}) {
    const cost = opts.cost !== undefined ? opts.cost : 22;
    if (this.stamina < 8) return false;
    this.spendStamina(cost);
    const len = Math.hypot(dirX, dirZ);
    if (len > 0.05) {
      this.yaw = Math.atan2(dirX, dirZ);
      this.setState(STATE.ROLL, { duration: opts.duration || 0.62, motion: opts.speed || 8.6 });
      this.invuln = opts.iframes !== undefined ? opts.iframes : 0.36;
    } else {
      this.setState(STATE.BACKSTEP, { duration: 0.46, motion: -6.4 });
      this.invuln = 0.18;
    }
    return true;
  }

  spendStamina(v) {
    this.stamina = Math.max(0, this.stamina - v);
    this.staminaLock = Math.max(this.staminaLock, 0.55);
  }

  // -------------------------------------------------------------------------
  //  Damage
  // -------------------------------------------------------------------------

  /**
   * @returns {object} result — { hit, blocked, parried, damage, killed }
   */
  takeDamage(info) {
    if (this.dead) return { hit: false };
    if (this.invuln > 0 && !info.ignoreInvuln) return { hit: false, dodged: true };

    const src = info.source;
    const fromAngle = src ? Math.atan2(src.x - this.x, src.z - this.z) : this.yaw + Math.PI;
    // Drawn, not intended: a shield the player can see pointing away must not
    // block, and one pointing at the blow must. See drawnYaw.
    const frontal = Math.abs(angleDelta(this.drawnYaw, fromAngle)) < 1.25;

    // --- parry -------------------------------------------------------------
    if (this.parryTimer > 0 && frontal && info.parryable !== false && src && !src.unparryable) {
      this.parryTimer = 0;
      src.getParried(this);
      this.game.onParry?.(this, src);
      return { hit: false, parried: true };
    }

    // --- guard -------------------------------------------------------------
    let damage = info.damage;
    let blocked = false;
    if (this.blocking && frontal && this.offhand && this.offhand.guard) {
      blocked = true;
      const guard = this.offhand.guard;
      const stability = this.offhand.stability || 20;
      const staminaHit = Math.max(4, (info.poise || 10) * 1.2 * (1 - stability / 120) + damage * 0.10);
      this.spendStamina(staminaHit);
      damage *= (1 - guard);
      if (this.stamina <= 0) {
        // Guard break: a real opening, not just chip damage.
        this.blocking = false;
        this.setState(STATE.STAGGER, { duration: 1.35 });
        this.poise = this.maxPoise;
        this.game.onGuardBreak?.(this, src);
      }
      this.game.onBlock?.(this, src, info);
    }

    // --- mitigation --------------------------------------------------------
    const resistKey = info.type && info.type !== 'physical' ? info.type : null;
    const resist = resistKey ? (this.resist[resistKey] || 0) : 0;
    let final = mitigate(damage, this.defense, resist);
    if (info.crit) final *= info.critMul || 1.9;
    final = Math.max(1, Math.round(final));

    this.hp -= final;
    this.flash = 1;
    this.lastHitBy = src || null;
    this.lastDamageDir = angleDelta(this.yaw, fromAngle);
    this.aggro = true;

    // --- status build-up ---------------------------------------------------
    if (info.status) {
      const st = this.status[info.status.type];
      if (st) {
        st.build += info.status.build;
        if (st.build >= st.threshold) {
          st.build = 0;
          st.active = info.status.type === 'frost' ? 12 : 22;
          this.game.onStatusProc?.(this, info.status.type);
        }
      }
    }

    // --- poise / stagger ---------------------------------------------------
    if (!blocked) {
      const poiseDmg = info.poise || 10;
      const armored = this.hyperArmor > 0 && poiseDmg < this.maxPoise * 0.7;
      if (!armored) {
        this.poise -= poiseDmg;
        if (this.poise <= 0) {
          this.poise = this.maxPoise;
          this.setState(info.big ? STATE.STAGGER : STATE.HURT, {
            duration: info.big ? 1.15 : 0.48,
          });
          this.staggerSource = src;
        } else if (this.state !== STATE.ATTACK) {
          this.setState(STATE.HURT, { duration: 0.34 });
        }
      }
    }

    // --- knockback ---------------------------------------------------------
    const push = (info.knockback || 2.2) / Math.max(0.4, this.mass);
    this.velX += Math.sin(fromAngle) * -push;
    this.velZ += Math.cos(fromAngle) * -push;

    this.hitStop = Math.min(0.09, 0.03 + final / 900);

    const killed = this.hp <= 0;
    if (killed) this.die(src);

    return { hit: true, blocked, damage: final, killed };
  }

  getParried(by) {
    this.setState(STATE.PARRIED, { duration: 1.6 });
    this.poise = this.maxPoise;
    this.velX = 0; this.velZ = 0;
  }

  /**
   * Move an actor somewhere instantly. Not just an assignment: carrying a fall
   * velocity across a teleport makes the very next ground check report a
   * hundred-metre landing, which is fatal — respawning after a long fall would
   * kill the player again the moment they arrived.
   */
  teleport(x, y, z) {
    this.x = x;
    this.z = z;
    this.y = y !== undefined ? y : this.world.heightAt(x, z);
    this.velX = 0; this.velY = 0; this.velZ = 0;
    this.grounded = true;
  }

  /**
   * Bring a dead actor back. `setState` deliberately latches DEATH so nothing
   * can interrupt a death animation, which means it cannot be used to leave
   * that state — clearing the latch here is the only way out, and without it a
   * respawned player stays permanently `busy` and can never act again.
   */
  revive(hp) {
    this.dead = false;
    this.deathTimer = 0;
    this.hp = hp !== undefined ? hp : this.maxHp;
    this.poise = this.maxPoise;
    this.blocking = false;
    this.hyperArmor = 0;
    this.velX = 0; this.velY = 0; this.velZ = 0;
    this.grounded = true;
    this.state = STATE.IDLE;
    this.setState(STATE.IDLE);
  }

  die(killer) {
    if (this.dead) return;
    this.dead = true;
    this.hp = 0;
    this.blocking = false;
    this.setState(STATE.DEATH, { duration: 1.4 });
    this.deathTimer = 0;
    this.game.onDeath?.(this, killer);
  }

  heal(v) {
    this.hp = Math.min(this.maxHp, this.hp + v);
  }

  addBuff(buff) {
    this.buffs = this.buffs.filter((b) => b.id !== buff.id);
    this.buffs.push({ ...buff, t: buff.dur });
  }

  buffValue(key, base = 1) {
    let v = base;
    for (const b of this.buffs) if (b[key] !== undefined) v *= b[key];
    return v;
  }

  buffAdd(key) {
    let v = 0;
    for (const b of this.buffs) if (b[key] !== undefined) v += b[key];
    return v;
  }

  // -------------------------------------------------------------------------
  //  Update
  // -------------------------------------------------------------------------

  update(dt) {
    if (this.hitStop > 0) {
      this.hitStop -= dt;
      dt *= 0.15;
    }
    this.stateT += dt;
    this.invuln = Math.max(0, this.invuln - dt);
    this.hyperArmor = Math.max(0, this.hyperArmor - dt);
    this.parryTimer = Math.max(0, this.parryTimer - dt);
    this.staminaLock = Math.max(0, this.staminaLock - dt);
    this.comboWindow = Math.max(0, this.comboWindow - dt);
    this.flash = Math.max(0, this.flash - dt * 4);

    this._updateStatus(dt);
    this._updateBuffs(dt);

    if (!this.dead) {
      if (this.staminaLock <= 0 && !this.blocking) {
        const regen = this.staminaRegen * this.buffValue('staminaRegen', 1) * (this.status.frost.active > 0 ? 0.7 : 1);
        this.stamina = Math.min(this.maxStamina, this.stamina + regen * dt);
      } else if (this.blocking) {
        this.stamina = Math.min(this.maxStamina, this.stamina + this.staminaRegen * 0.32 * dt);
      }
      this.poise = Math.min(this.maxPoise, this.poise + this.poiseRegen * dt);
    }

    this._updateAction(dt);
    this._updateMovement(dt);
    this._updateAnimation(dt);

    if (this.dead) {
      this.deathTimer += dt;
    }
  }

  _updateStatus(dt) {
    for (const key in this.status) {
      const st = this.status[key];
      if (st.active > 0) {
        st.active -= dt;
        st.tick -= dt;
        if (st.tick <= 0) {
          st.tick = 1.0;
          if (key === 'poison') {
            this.hp -= Math.max(2, this.maxHp * 0.014);
            if (this.hp <= 0) this.die(null);
          } else if (key === 'bleed') {
            this.hp -= Math.max(3, this.maxHp * 0.02);
            if (this.hp <= 0) this.die(null);
          }
        }
      } else if (st.build > 0) {
        st.build = Math.max(0, st.build - dt * 6);
      }
    }
  }

  _updateBuffs(dt) {
    for (let i = this.buffs.length - 1; i >= 0; i--) {
      this.buffs[i].t -= dt;
      if (this.buffs[i].t <= 0) this.buffs.splice(i, 1);
    }
  }

  _updateAction(dt) {
    const dur = this.stateDuration || 0.4;
    this.actionU = dur > 0 ? clamp(this.stateT / dur, 0, 1) : 1;

    if (this.state === STATE.ATTACK && this.action) {
      const [h0, h1] = this.action.hit;
      this.hitActive = this.actionU >= h0 && this.actionU <= h1;
      if (this.actionU > 0.62) this.comboWindow = 0.35;
    } else {
      this.hitActive = false;
    }

    if (this.state === STATE.PARRY) {
      // Parry frames start a beat after the input, so mistimed presses whiff.
      this.parryTimer = (this.stateT > 0.08 && this.stateT < 0.08 + this.parryWindow) ? 0.05 : 0;
    }

    if (this.stateT >= dur) {
      switch (this.state) {
        case STATE.DEATH:
          break;
        case STATE.ATTACK:
        case STATE.CAST:
        case STATE.ROLL:
        case STATE.BACKSTEP:
        case STATE.HURT:
        case STATE.STAGGER:
        case STATE.PARRY:
        case STATE.PARRIED:
        case STATE.DRINK:
        case STATE.RIPOSTE:
        case STATE.RIPOSTED:
        case STATE.JUMP:
        case STATE.TAUNT:
        case STATE.SPAWN:
          this.setState(STATE.IDLE);
          break;
        default:
          break;
      }
    }
  }

  _updateMovement(dt) {
    const world = this.world;

    // Root motion from attacks and rolls.
    let moveX = 0, moveZ = 0;
    if (this.rootMotion !== 0 && this.state !== STATE.IDLE && this.state !== STATE.MOVE) {
      // Impulse curve: most of the travel happens early in the action.
      const u = this.actionU;
      const curve = this.state === STATE.ROLL || this.state === STATE.BACKSTEP
        ? Math.max(0, 1 - u * u * 1.35)
        : Math.max(0, Math.sin(Math.min(u / 0.55, 1) * Math.PI) * (u < 0.55 ? 1 : 0.3));
      const s = this.rootMotion * curve;
      moveX += Math.sin(this.yaw) * s * dt;
      moveZ += Math.cos(this.yaw) * s * dt;
    }

    // Intent-driven locomotion.
    if (!this.dead && (this.state === STATE.IDLE || this.state === STATE.MOVE || this.state === STATE.BLOCK)) {
      const speed = this.intentSpeed * (this.status.frost.active > 0 ? 0.72 : 1);
      moveX += this.intentX * speed * dt;
      moveZ += this.intentZ * speed * dt;
      const mag = Math.hypot(this.intentX, this.intentZ);
      this.speedRatio = speed > 0 ? clamp(speed / this.sprintSpeed, 0, 1) : 0;
      this.moveBlend = damp(this.moveBlend, mag > 0.05 ? 1 : 0, 12, dt);
      if (mag > 0.05) {
        if (this.state === STATE.IDLE) this.state = STATE.MOVE;
      } else if (this.state === STATE.MOVE) {
        this.state = STATE.IDLE;
      }
    } else {
      this.moveBlend = damp(this.moveBlend, 0, 10, dt);
      this.speedRatio = damp(this.speedRatio, 0, 8, dt);
    }

    // External velocity (knockback).
    moveX += this.velX * dt;
    moveZ += this.velZ * dt;
    const dragK = Math.exp(-9 * dt);
    this.velX *= dragK;
    this.velZ *= dragK;

    this._moveWithCollision(moveX, moveZ);

    // --- vertical ----------------------------------------------------------
    const ground = world.heightAt(this.x, this.z);
    // The horizontal solve below already refuses to move a body to a non-finite
    // coordinate; the vertical one accumulates and did not. `velY` is summed
    // every frame and `y` is summed from it, so one bad value sticks — and a
    // body at a non-finite height is gone: it cannot be drawn, hit, or hit
    // anything, permanently and silently. Fall back to the ground under it,
    // which is where a body that has lost track of its height belongs.
    if (!Number.isFinite(this.velY)) this.velY = 0;
    if (!Number.isFinite(this.y)) {
      this.y = Number.isFinite(ground) ? ground : 0;
      this.velY = 0;
      this.grounded = true;
    }
    if (this.state === STATE.JUMP || !this.grounded) {
      this.velY += GRAVITY * dt;
      this.y += this.velY * dt;
      if (this.y <= ground) {
        const fallSpeed = -this.velY;
        this.y = ground;
        this.velY = 0;
        if (!this.grounded) {
          this.grounded = true;
          this.onLand?.(fallSpeed);
        }
      }
    } else {
      const diff = ground - this.y;
      if (diff > MAX_STEP * 2.2) {
        // Big upward jump means we clipped into a wall; push back out.
        this.y = ground;
      } else if (diff < -0.55) {
        this.grounded = false;
        this.velY = 0;
      } else {
        this.y = lerp(this.y, ground, 1 - Math.exp(-24 * dt));
      }
    }

    // --- animation phase ---------------------------------------------------
    const planarSpeed = Math.hypot(moveX, moveZ) / Math.max(dt, 1e-5);
    const stride = this.rigKind === 'quadruped' || this.rigKind === 'winged' ? 2.4 : 1.65;
    if (this.moveBlend > 0.02) {
      const prev = this.phase;
      this.phase += (planarSpeed / stride) * dt * TAU * 0.55;
      // Footstep events fire when the phase crosses a half cycle.
      if (Math.floor(prev / Math.PI) !== Math.floor(this.phase / Math.PI)) {
        this.onFootstep?.(planarSpeed);
      }
    } else {
      this.phase = damp(this.phase % TAU, 0, 6, dt);
    }
  }

  _moveWithCollision(dx, dz) {
    if (dx === 0 && dz === 0) return;
    const world = this.world;
    const startX = this.x, startZ = this.z;
    let nx = this.x + dx, nz = this.z + dz;

    // Terrain slope: refuse to climb near-vertical faces.
    const targetH = world.heightAt(nx, nz);
    const curH = world.heightAt(this.x, this.z);
    if (targetH - curH > MAX_STEP && this.grounded) {
      const slope = world.slopeAt(nx, nz);
      if (slope > SLOPE_LIMIT) {
        // Slide along the wall instead of sticking to it.
        const nrm = world.normalAt(nx, nz, this._n || (this._n = { x: 0, y: 1, z: 0 }));
        const dot = dx * nrm.x + dz * nrm.z;
        nx = this.x + (dx - nrm.x * dot);
        nz = this.z + (dz - nrm.z * dot);
        if (world.heightAt(nx, nz) - curH > MAX_STEP) { nx = this.x; nz = this.z; }
      }
    }

    // Prop colliders (trees, boulders).
    const cols = this.game.scatter.collidersNear(nx, nz, this.radius, this._colBuf || (this._colBuf = []));
    for (let i = 0; i < cols.length; i++) {
      const c = cols[i];
      const ddx = nx - c.x, ddz = nz - c.z;
      const d = Math.hypot(ddx, ddz);
      const minD = c.r + this.radius;
      if (d < minD && d > 1e-4) {
        nx = c.x + (ddx / d) * minD;
        nz = c.z + (ddz / d) * minD;
      }
    }

    // Structure colliders placed by the world builder.
    const sc = this.game.structureColliders;
    if (sc) {
      for (let i = 0; i < sc.length; i++) {
        const c = sc[i];
        const ddx = nx - c.x, ddz = nz - c.z;
        const d2 = ddx * ddx + ddz * ddz;
        const minD = c.r + this.radius;
        if (d2 < minD * minD && d2 > 1e-8) {
          const d = Math.sqrt(d2);
          nx = c.x + (ddx / d) * minD;
          nz = c.z + (ddz / d) * minD;
        }
      }
    }

    // World border.
    const lim = 1240;
    nx = clamp(nx, -lim, lim);
    nz = clamp(nz, -lim, lim);

    // A degenerate collision (zero-length separation, NaN velocity) must never
    // escape into the world sampler, which would corrupt terrain generation.
    if (!Number.isFinite(nx) || !Number.isFinite(nz)) { nx = startX; nz = startZ; }
    this.x = nx;
    this.z = nz;
    this.actualSpeed = Math.hypot(this.x - startX, this.z - startZ);
  }

  /** Separate overlapping actors so crowds do not stack into one point. */
  static separate(actors, dt) {
    for (let i = 0; i < actors.length; i++) {
      const a = actors[i];
      if (a.dead || a.noPush) continue;
      for (let j = i + 1; j < actors.length; j++) {
        const b = actors[j];
        if (b.dead || b.noPush) continue;
        const dx = b.x - a.x, dz = b.z - a.z;
        const minD = a.radius + b.radius;
        const d2 = dx * dx + dz * dz;
        if (d2 >= minD * minD || d2 < 1e-8) continue;
        const d = Math.sqrt(d2);
        const overlap = (minD - d) * 0.5;
        const ux = dx / d, uz = dz / d;
        const ma = b.mass / (a.mass + b.mass);
        const mb = 1 - ma;
        a.x -= ux * overlap * ma * 2;
        a.z -= uz * overlap * ma * 2;
        b.x += ux * overlap * mb * 2;
        b.z += uz * overlap * mb * 2;
      }
    }
  }

  // -------------------------------------------------------------------------
  //  Animation
  // -------------------------------------------------------------------------

  _updateAnimation(dt) {
    const rig = this.rig;
    rig.clearTarget();
    rig.rootOffset[0] = 0; rig.rootOffset[1] = 0; rig.rootOffset[2] = 0;
    rig.rootRot[0] = 0; rig.rootRot[1] = 0; rig.rootRot[2] = 0;

    const ctx = {
      phase: this.phase,
      moveBlend: this.moveBlend,
      speedRatio: this.speedRatio,
      strafe: 0,
      time: this.game.time,
      lookPitch: this.lookPitch,
      headYaw: this.headYaw,
      twoHand: this.twoHand,
      hasShield: !!(this.offhand && this.offhand.guard),
      state: this.state,
      actionU: this.actionU,
      airborne: !this.grounded,
      dt,
    };

    if (this.rigKind === 'quadruped') {
      quadrupedAnimate(rig, ctx);
    } else if (this.rigKind === 'winged') {
      wingedAnimate(rig, ctx);
    } else {
      humanoidLocomotion(rig, ctx);
      humanoidArmsNeutral(rig, ctx);

      switch (this.state) {
        case STATE.ATTACK:
        case STATE.CAST:
          if (this.action && this.action.pose) {
            const r = this.action.pose(rig, this.actionU, ctx);
            this.actionLunge = r ? r.lunge : 0;
          }
          break;
        case STATE.ROLL: poseRoll(rig, this.actionU, ctx); break;
        case STATE.BACKSTEP: poseBackstep(rig, this.actionU); break;
        case STATE.BLOCK: poseBlock(rig, ctx, this.blockImpact || 0); break;
        case STATE.PARRY: poseParry(rig, this.actionU, ctx); break;
        case STATE.PARRIED: poseStagger(rig, this.actionU); break;
        case STATE.HURT: poseHurt(rig, this.actionU, this.lastDamageDir); break;
        case STATE.STAGGER: poseStagger(rig, this.actionU); break;
        case STATE.DEATH: poseDeath(rig, clamp(this.deathTimer / 0.9, 0, 1)); break;
        case STATE.JUMP: poseJump(rig, this.actionU, this.velY > 0); break;
        case STATE.DRINK: poseDrink(rig, this.actionU); break;
        case STATE.REST: poseRest(rig, clamp(this.stateT / 1.2, 0, 1)); break;
        case STATE.RIPOSTE: {
          // A short, brutal thrust; the victim is held in place by the game.
          const u = this.actionU;
          rig.setBone('spine', -0.25 + 0.55 * Math.sin(u * Math.PI), 0, 0);
          rig.setBone('upperArmR', -1.85 + 1.5 * Math.sin(u * Math.PI), -0.2, 0.5);
          rig.setBone('forearmR', -0.5 + 1.0 * Math.sin(u * Math.PI), 0, 0);
          break;
        }
        case STATE.RIPOSTED:
          poseStagger(rig, this.actionU);
          break;
        default:
          if (this.blocking) poseBlock(rig, ctx, this.blockImpact || 0);
          break;
      }
    }

    this.blockImpact = Math.max(0, (this.blockImpact || 0) - dt * 5);
    // Context for the continuity tracker, which sees the rig and not its host.
    rig.hostState = this.state;
    rig.hostTag = this.kind || this.archetype || (this.isPlayer ? 'player' : 'actor');
    rig.apply(dt, this.x, this.y, this.z, this.yaw);
  }

  faceTowards(x, z, dt, rate) {
    const target = Math.atan2(x - this.x, z - this.z);
    this.yaw = dampAngle(this.yaw, target, rate !== undefined ? rate : this.turnRate, dt);
  }

  // -------------------------------------------------------------------------
  //  Rendering
  // -------------------------------------------------------------------------

  render(batches) {
    if (!this.visible) return;
    const flashK = this.flash;
    // Hit flash: enough to read at a glance, not enough to turn the character
    // into a solid red silhouette mid-combo.
    const opts = {
      tintR: 1 + flashK * 0.85,
      tintG: 1 - flashK * 0.42,
      tintB: 1 - flashK * 0.42,
      alpha: this.fadeAlpha !== undefined ? this.fadeAlpha : 1,
      emissive: this.emissive || 0,
    };
    if (this.status.frost.active > 0) { opts.tintB += 0.35; opts.tintG += 0.15; }
    if (this.status.poison.active > 0) { opts.tintG += 0.30; opts.tintR -= 0.15; }
    // renderTo, not render: bones name the primitive they are drawn with, so a
    // shoulder lands in the pauldron batch and a thigh in the tapered-limb
    // batch. That is a handful of draw calls for the whole fight rather than
    // one per character, and it is the difference between a box-man and a
    // silhouette you can read at thirty metres.
    this.rig.renderTo(batches, this.palette, opts);
    this._renderEquipment(batches, opts);
  }

  _renderEquipment(batches, opts) {
    if (this.rigKind !== 'humanoid') return;
    const box = batches.get('box');
    const basis = new Float32Array(9);
    const scale = this.scale;

    if (this.weapon && !this.weaponHidden) {
      const shape = this.weapon.shape || {};
      const hand = this.rig.boneTip('handR', this._h1 || (this._h1 = {}));
      this.rig.boneBasis('handR', basis);
      renderWeapon(box, basis, hand, shape, scale, opts, this.weapon.class);
    }
    if (this.offhand && this.offhand.class === 'shield') {
      const shape = this.offhand.shape || {};
      // Strapped to the forearm, not gripped in the fingers.
      const arm = this.rig.jointPos('forearmL', this._h2 || (this._h2 = {}));
      this.rig.boneBasis('forearmL', basis);
      renderShield(box, basis, arm, shape, scale, opts);
    }
  }
}

// ---------------------------------------------------------------------------
//  Equipment geometry — built from the same instanced box batch as the body.
// ---------------------------------------------------------------------------

const _wb = new Float32Array(9);

/**
 * Weapons extend along the hand bone's +Y. The basis columns are scaled to the
 * blade's cross-section, so one box becomes a blade, another the guard, and so
 * on — the whole armoury is a dozen boxes.
 */
function renderWeapon(box, handBasis, handPos, shape, scale, opts, cls) {
  // A bow is wood and a sword is steel, and the difference is entirely in how
  // the sun sits on them. Bows and staves take the wood surface; everything
  // else is metal until the grip, which is leather.
  box.material(cls === 'bow' || cls === 'staff' ? SURFACE.WOOD : SURFACE.METAL);
  const len = (shape.len || 0.9) * scale;
  const w = (shape.w || 0.08) * scale;
  const t = (shape.t || 0.028) * scale;
  const blade = shape.blade || [0.7, 0.72, 0.75];
  const hilt = shape.hilt || [0.28, 0.22, 0.16];
  const glow = shape.glow || 0;
  const b = handBasis;

  // Grip, extending back from the hand.
  box.material(SURFACE.LEATHER);
  setScaled(_wb, b, w * 0.55, -0.16 * scale, t * 1.6);
  box.pushMatrix(_wb, handPos.x, handPos.y, handPos.z,
    hilt[0] * opts.tintR, hilt[1] * opts.tintG, hilt[2] * opts.tintB, 0, 0.9, opts.alpha);
  box.material(cls === 'bow' || cls === 'staff' ? SURFACE.WOOD : SURFACE.METAL);

  if (cls === 'bow') {
    // Bow: two limbs angled away from the grip, plus a string.
    for (const dir of [1, -1]) {
      setScaled(_wb, b, w * 0.9, len * 0.5 * dir, t * 1.2);
      box.pushMatrix(_wb, handPos.x, handPos.y, handPos.z,
        blade[0] * opts.tintR, blade[1] * opts.tintG, blade[2] * opts.tintB, 0, 0.9, opts.alpha);
    }
    setScaled(_wb, b, 0.012 * scale, len * 0.5, 0.012 * scale);
    box.pushMatrix(_wb,
      handPos.x + b[6] * 0.06 * scale, handPos.y + b[7] * 0.06 * scale, handPos.z + b[8] * 0.06 * scale,
      0.8, 0.78, 0.7, 0, 0.9, opts.alpha);
    setScaled(_wb, b, 0.012 * scale, -len * 0.5, 0.012 * scale);
    box.pushMatrix(_wb,
      handPos.x + b[6] * 0.06 * scale, handPos.y + b[7] * 0.06 * scale, handPos.z + b[8] * 0.06 * scale,
      0.8, 0.78, 0.7, 0, 0.9, opts.alpha);
    return;
  }

  if (cls === 'staff') {
    setScaled(_wb, b, w, len, w);
    box.pushMatrix(_wb, handPos.x, handPos.y, handPos.z,
      blade[0] * opts.tintR, blade[1] * opts.tintG, blade[2] * opts.tintB, glow * 0.3, 0.9, opts.alpha);
    // Focus stone at the tip.
    const tipX = handPos.x + b[3] * len, tipY = handPos.y + b[4] * len, tipZ = handPos.z + b[5] * len;
    setScaled(_wb, b, w * 2.2, w * 2.4, w * 2.2);
    box.pushMatrix(_wb, tipX, tipY, tipZ, blade[0] * 1.4, blade[1] * 1.3, blade[2] * 1.6, glow, 1, opts.alpha);
    return;
  }

  if (shape.haft) {
    // Spear: long haft, short head.
    setScaled(_wb, b, w * 0.85, len * 0.82, w * 0.85);
    box.pushMatrix(_wb, handPos.x, handPos.y, handPos.z,
      hilt[0] * opts.tintR, hilt[1] * opts.tintG, hilt[2] * opts.tintB, 0, 0.9, opts.alpha);
    const hx = handPos.x + b[3] * len * 0.82, hy = handPos.y + b[4] * len * 0.82, hz = handPos.z + b[5] * len * 0.82;
    setScaled(_wb, b, w * 2.4, len * 0.20, t * 1.6);
    box.pushMatrix(_wb, hx, hy, hz,
      blade[0] * opts.tintR, blade[1] * opts.tintG, blade[2] * opts.tintB, glow, 1, opts.alpha);
    return;
  }

  if (shape.axe) {
    setScaled(_wb, b, w * 0.6, len, w * 0.6);
    box.pushMatrix(_wb, handPos.x, handPos.y, handPos.z,
      hilt[0] * opts.tintR, hilt[1] * opts.tintG, hilt[2] * opts.tintB, 0, 0.9, opts.alpha);
    const hx = handPos.x + b[3] * len * 0.86, hy = handPos.y + b[4] * len * 0.86, hz = handPos.z + b[5] * len * 0.86;
    // Head offset to one side so it reads as an axe, not a hammer.
    const ox = b[0] * w * 0.9, oy = b[1] * w * 0.9, oz = b[2] * w * 0.9;
    setScaled(_wb, b, w * 1.9, len * 0.34, t * 3.4);
    box.pushMatrix(_wb, hx + ox, hy + oy, hz + oz,
      blade[0] * opts.tintR, blade[1] * opts.tintG, blade[2] * opts.tintB, glow, 1, opts.alpha);
    return;
  }

  // Swords: crossguard, blade, pommel.
  setScaled(_wb, b, w * 3.4, 0.035 * scale, t * 2.6);
  box.pushMatrix(_wb, handPos.x, handPos.y, handPos.z,
    hilt[0] * 1.5 * opts.tintR, hilt[1] * 1.4 * opts.tintG, hilt[2] * 1.3 * opts.tintB, 0, 0.9, opts.alpha);
  setScaled(_wb, b, w, len, t);
  const gx = handPos.x + b[3] * 0.035 * scale;
  const gy = handPos.y + b[4] * 0.035 * scale;
  const gz = handPos.z + b[5] * 0.035 * scale;
  box.pushMatrix(_wb, gx, gy, gz,
    blade[0] * opts.tintR, blade[1] * opts.tintG, blade[2] * opts.tintB, glow, 1, opts.alpha);
  setScaled(_wb, b, w * 1.2, -0.06 * scale, w * 1.2);
  box.pushMatrix(_wb, handPos.x, handPos.y, handPos.z,
    hilt[0] * 1.3, hilt[1] * 1.2, hilt[2] * 1.1, 0, 0.9, opts.alpha);
}

function renderShield(box, basis, armPos, shape, scale, opts) {
  box.material(shape.wooden ? SURFACE.WOOD : SURFACE.METAL);
  const w = (shape.w || 0.5) * scale;
  const h = (shape.h || 0.8) * scale;
  const t = (shape.t || 0.08) * scale;
  const face = shape.face || [0.5, 0.5, 0.55];
  const rim = shape.rim || [0.35, 0.35, 0.38];
  const b = basis;
  // The board spans the forearm's X (width) and Y (length, running down the
  // arm), with thickness along Z. The bone's local +Z points behind the
  // character, so the face is pushed out along -Z and slightly outboard in X.
  const back = h * 0.06;
  const out = -t * 1.6;
  const side = w * 0.10;
  const bx = armPos.x + b[3] * back + b[6] * out + b[0] * side;
  const by = armPos.y + b[4] * back + b[7] * out + b[1] * side;
  const bz = armPos.z + b[5] * back + b[8] * out + b[2] * side;

  setScaled(_wb, b, w, h, t);
  box.pushMatrix(_wb, bx, by, bz,
    face[0] * opts.tintR, face[1] * opts.tintG, face[2] * opts.tintB, 0, 0.9, opts.alpha);
  // Rim: a slightly larger, thinner slab behind the face.
  setScaled(_wb, b, w * 1.12, h * 1.06, t * 0.5);
  box.pushMatrix(_wb, bx + b[6] * t * 0.35, by + b[7] * t * 0.35, bz + b[8] * t * 0.35,
    rim[0] * opts.tintR, rim[1] * opts.tintG, rim[2] * opts.tintB, 0, 0.85, opts.alpha);
  // Boss (the central stud) — reads as metal at a glance.
  setScaled(_wb, b, w * 0.26, h * 0.16, t * 1.1);
  box.pushMatrix(_wb,
    bx + b[3] * h * 0.42 - b[6] * t * 0.9,
    by + b[4] * h * 0.42 - b[7] * t * 0.9,
    bz + b[5] * h * 0.42 - b[8] * t * 0.9,
    rim[0] * 1.4 * opts.tintR, rim[1] * 1.4 * opts.tintG, rim[2] * 1.4 * opts.tintB, 0, 0.9, opts.alpha);
  box.material(SURFACE.DEFAULT);
}

/** Scale the three basis columns independently. */
function setScaled(out, b, sx, sy, sz) {
  out[0] = b[0] * sx; out[1] = b[1] * sx; out[2] = b[2] * sx;
  out[3] = b[3] * sy; out[4] = b[4] * sy; out[5] = b[5] * sy;
  out[6] = b[6] * sz; out[7] = b[7] * sz; out[8] = b[8] * sz;
  return out;
}

export function defaultPalette() {
  const p = [];
  p[MAT.SKIN] = [0.74, 0.58, 0.46];
  p[MAT.CLOTH] = [0.34, 0.30, 0.27];
  p[MAT.ARMOR] = [0.40, 0.40, 0.44];
  p[MAT.LEATHER] = [0.30, 0.24, 0.19];
  p[MAT.HAIR] = [0.18, 0.14, 0.11];
  p[MAT.ACCENT] = [0.52, 0.20, 0.18];
  p[MAT.METAL] = [0.62, 0.63, 0.68];
  p[MAT.DARK] = [0.16, 0.15, 0.14];
  return p;
}

export { setScaled, renderWeapon, renderShield };
