// ============================================================================
//  ai.js — enemy behaviour.
//
//  The brain is a small state machine per enemy plus a shared "attack token"
//  pool per target. Without the token pool, six wolves all reach the player on
//  the same frame and all bite at once, which is not difficulty — it is noise.
//  With it, one or two commit while the rest circle, which reads as a pack.
// ============================================================================

import {
  clamp, lerp, saturate, angleDelta, dampAngle, v3distXZ, TAU,
} from '../core/math.js';
import { STATE, FACTION } from './actor.js';

export const AI_STATE = {
  IDLE: 'idle', PATROL: 'patrol', ALERT: 'alert', CHASE: 'chase',
  COMBAT: 'combat', STRAFE: 'strafe', RECOVER: 'recover',
  FLEE: 'flee', RETURN: 'return', SLEEP: 'sleep',
};

/** Attack slots per target, so a crowd takes turns instead of swarming. */
export class AggroDirector {
  constructor() {
    this.tokens = new Map();  // targetId -> Set of holder ids
    this.maxTokens = 2;
  }

  setMax(n) { this.maxTokens = n; }

  request(holder, target) {
    if (!target) return false;
    let set = this.tokens.get(target.id);
    if (!set) { set = new Set(); this.tokens.set(target.id, set); }
    if (set.has(holder.id)) return true;
    if (set.size >= this.maxTokens) return false;
    set.add(holder.id);
    return true;
  }

  release(holder, target) {
    if (!target) return;
    const set = this.tokens.get(target.id);
    if (set) set.delete(holder.id);
  }

  releaseAll(holder) {
    for (const set of this.tokens.values()) set.delete(holder.id);
  }
}

export class EnemyBrain {
  constructor(actor, config) {
    this.actor = actor;
    this.cfg = {
      sightRange: 22,
      sightAngle: 1.35,
      hearRange: 12,
      loseRange: 40,
      leashRange: 55,
      preferredRange: 2.2,
      aggression: 0.6,       // 0 = passive, 1 = relentless
      patience: 0.9,         // seconds spent circling before committing
      canBlock: false,
      canDodge: false,
      canParry: false,
      blockChance: 0.25,
      dodgeChance: 0.2,
      strafeSpeedMul: 0.62,
      groupRadius: 14,
      wanderRadius: 9,
      ...config,
    };
    this.state = AI_STATE.IDLE;
    this.stateT = 0;
    this.target = null;
    this.homeX = actor.x;
    this.homeZ = actor.z;
    this.wanderX = actor.x;
    this.wanderZ = actor.z;
    this.attackCooldown = 0;
    this.decisionTimer = 0;
    this.strafeDir = Math.random() < 0.5 ? 1 : -1;
    this.lastSeen = 0;
    this.alertness = 0;
    this.hasToken = false;
    this.attackTimers = new Map();
    this.commitTimer = 0;
    this.blockTimer = 0;
    this.reactionDelay = 0;
    this.spawnDelay = 0;
  }

  setHome(x, z) { this.homeX = x; this.homeZ = z; this.wanderX = x; this.wanderZ = z; }

  setState(s) {
    if (this.state === s) return;
    this.state = s;
    this.stateT = 0;
  }

  /** Distance at which this enemy wants to fight, from its longest attack. */
  get engageRange() { return this.cfg.preferredRange; }

  update(dt, game) {
    const a = this.actor;
    if (a.dead) {
      if (this.hasToken) { game.director.release(a, this.target); this.hasToken = false; }
      return;
    }

    this.stateT += dt;
    this.attackCooldown = Math.max(0, this.attackCooldown - dt);
    this.decisionTimer -= dt;
    this.commitTimer = Math.max(0, this.commitTimer - dt);
    this.blockTimer = Math.max(0, this.blockTimer - dt);
    this.reactionDelay = Math.max(0, this.reactionDelay - dt);
    for (const [k, v] of this.attackTimers) {
      if (v > 0) this.attackTimers.set(k, v - dt);
    }

    // While mid-action the brain only steers; it does not re-plan.
    if (a.busy) {
      a.intentSpeed = 0;
      if (a.state === STATE.ATTACK && a.actionU < 0.28 && this.target) {
        a.faceTowards(this.target.x, this.target.z, dt, a.turnRate * 0.7);
      }
      return;
    }

    this._acquireTarget(game, dt);

    switch (this.state) {
      case AI_STATE.SLEEP: this._sleep(dt, game); break;
      case AI_STATE.IDLE: this._idle(dt, game); break;
      case AI_STATE.PATROL: this._patrol(dt, game); break;
      case AI_STATE.ALERT: this._alert(dt, game); break;
      case AI_STATE.CHASE: this._chase(dt, game); break;
      case AI_STATE.COMBAT: this._combat(dt, game); break;
      case AI_STATE.STRAFE: this._strafe(dt, game); break;
      case AI_STATE.RECOVER: this._recover(dt, game); break;
      case AI_STATE.FLEE: this._flee(dt, game); break;
      case AI_STATE.RETURN: this._return(dt, game); break;
      default: this.setState(AI_STATE.IDLE);
    }
  }

  // -------------------------------------------------------------------------

  _acquireTarget(game, dt) {
    const a = this.actor;
    const p = game.player;
    if (!p || p.dead) {
      this.target = null;
      if (this.state !== AI_STATE.RETURN && this.state !== AI_STATE.IDLE) this.setState(AI_STATE.RETURN);
      return;
    }

    const d = v3distXZ(a, p);

    if (this.target) {
      if (d > this.cfg.loseRange) {
        this.lastSeen += dt;
        if (this.lastSeen > 4) {
          this.target = null;
          game.director.release(a, p);
          this.hasToken = false;
          this.setState(AI_STATE.RETURN);
        }
      } else {
        this.lastSeen = 0;
      }
      return;
    }

    if (a.aggro && d < this.cfg.loseRange) {
      // Being hit reveals the attacker regardless of line of sight.
      this._engage(p, game);
      return;
    }

    // Sight: cone + range, with a bonus for a sprinting or attacking player.
    const noisy = p.isSprinting || p.state === STATE.ATTACK;
    const range = this.cfg.sightRange * (noisy ? 1.25 : 1) * (game.isNight ? 0.75 : 1);
    if (d < range && a.facing(p, this.cfg.sightAngle)) {
      this.alertness += dt * (2.2 + (range - d) / range * 2);
    } else if (d < this.cfg.hearRange && noisy) {
      this.alertness += dt * 1.4;
    } else {
      this.alertness = Math.max(0, this.alertness - dt * 0.8);
    }

    if (this.alertness > 1) this._engage(p, game);
    else if (this.alertness > 0.3 && this.state === AI_STATE.IDLE) this.setState(AI_STATE.ALERT);
  }

  _engage(target, game) {
    if (this.target === target) return;
    this.target = target;
    this.alertness = 2;
    this.reactionDelay = 0.15 + Math.random() * 0.35;
    this.setState(AI_STATE.CHASE);
    this.actor.onNotice?.(target);
    // Shout: nearby allies of the same group join in.
    game.alertNearby(this.actor, this.cfg.groupRadius, target);
  }

  // -------------------------------------------------------------------------

  _sleep(dt, game) {
    const a = this.actor;
    a.intentSpeed = 0;
    if (this.target) this.setState(AI_STATE.CHASE);
  }

  _idle(dt, game) {
    const a = this.actor;
    a.intentSpeed = 0;
    if (this.target) { this.setState(AI_STATE.CHASE); return; }
    if (this.cfg.wanderRadius > 0 && this.stateT > 2 + Math.random() * 3) {
      this.setState(AI_STATE.PATROL);
      const ang = Math.random() * TAU;
      const r = Math.random() * this.cfg.wanderRadius;
      this.wanderX = this.homeX + Math.cos(ang) * r;
      this.wanderZ = this.homeZ + Math.sin(ang) * r;
    }
  }

  _patrol(dt, game) {
    const a = this.actor;
    if (this.target) { this.setState(AI_STATE.CHASE); return; }
    const d = Math.hypot(this.wanderX - a.x, this.wanderZ - a.z);
    if (d < 1.2 || this.stateT > 9) { this.setState(AI_STATE.IDLE); a.intentSpeed = 0; return; }
    this._steerTo(this.wanderX, this.wanderZ, a.moveSpeed * 0.55, dt);
  }

  _alert(dt, game) {
    const a = this.actor;
    a.intentSpeed = 0;
    const p = game.player;
    if (p) a.faceTowards(p.x, p.z, dt, 4);
    if (this.target) { this.setState(AI_STATE.CHASE); return; }
    if (this.stateT > 3 || this.alertness <= 0.05) this.setState(AI_STATE.IDLE);
  }

  _chase(dt, game) {
    const a = this.actor;
    const t = this.target;
    if (!t || t.dead) { this.target = null; this.setState(AI_STATE.RETURN); return; }
    if (this.reactionDelay > 0) { a.intentSpeed = 0; a.faceTowards(t.x, t.z, dt, 8); return; }

    const d = v3distXZ(a, t);
    const homeD = Math.hypot(a.x - this.homeX, a.z - this.homeZ);
    if (homeD > this.cfg.leashRange && this.cfg.leashRange > 0) {
      this.target = null;
      game.director.release(a, t);
      this.hasToken = false;
      this.setState(AI_STATE.RETURN);
      return;
    }

    if (d < this.engageRange + 0.9) {
      this.setState(AI_STATE.COMBAT);
      return;
    }

    // Ranged enemies keep their distance instead of closing.
    if (this.cfg.ranged && d < this.cfg.rangedMin) {
      const away = Math.atan2(a.x - t.x, a.z - t.z);
      this._steerDir(Math.sin(away), Math.cos(away), a.moveSpeed, dt);
      a.faceTowards(t.x, t.z, dt, 6);
      return;
    }
    if (this.cfg.ranged && d < this.cfg.sightRange) {
      this.setState(AI_STATE.COMBAT);
      return;
    }

    const speed = d > 8 ? a.runSpeed : a.moveSpeed * 1.2;
    this._steerTo(t.x, t.z, speed, dt);
  }

  _combat(dt, game) {
    const a = this.actor;
    const t = this.target;
    if (!t || t.dead) { this.target = null; this.setState(AI_STATE.RETURN); return; }

    const d = v3distXZ(a, t);
    a.faceTowards(t.x, t.z, dt, a.turnRate);

    if (d > this.cfg.loseRange) { this.setState(AI_STATE.CHASE); return; }

    // Defensive reactions: the enemy sees a swing coming and answers it.
    if (this._considerDefense(dt, game, t, d)) return;

    if (a.stamina < a.maxStamina * 0.18) { this.setState(AI_STATE.RECOVER); return; }

    // Attack tokens gate commitment.
    if (!this.hasToken) this.hasToken = game.director.request(a, t);

    const pick = this._chooseAttack(d, t);
    if (pick && this.hasToken && this.attackCooldown <= 0) {
      a.intentSpeed = 0;
      if (a.startAttack(pick.id, { speedMul: pick.speedMul || 1, damageMul: pick.damageMul || 1 })) {
        this.attackTimers.set(pick.id, pick.cooldown || 1.2);
        this.attackCooldown = (pick.recovery || 0.35) + Math.random() * 0.35;
        this.commitTimer = 0;
        game.onEnemySwing?.(a, pick.id);
        if (Math.random() < 0.35) {
          // Sometimes hold the token for a follow-up, sometimes yield it.
          game.director.release(a, t);
          this.hasToken = false;
        }
      }
      return;
    }

    // Not attacking: circle, close, or back off depending on range.
    this.setState(AI_STATE.STRAFE);
  }

  _strafe(dt, game) {
    const a = this.actor;
    const t = this.target;
    if (!t || t.dead) { this.setState(AI_STATE.RETURN); return; }
    const d = v3distXZ(a, t);
    a.faceTowards(t.x, t.z, dt, a.turnRate * 0.85);

    if (this._considerDefense(dt, game, t, d)) return;

    const want = this.cfg.ranged ? this.cfg.rangedIdeal || 12 : this.engageRange;
    const err = d - want;
    const toT = Math.atan2(t.x - a.x, t.z - a.z);
    // Tangential component keeps them moving around the player.
    const tang = toT + Math.PI / 2 * this.strafeDir;
    let dx = Math.sin(tang) * 0.85;
    let dz = Math.cos(tang) * 0.85;
    // Radial component corrects the range error.
    const radial = clamp(err * 0.5, -1, 1);
    dx += Math.sin(toT) * radial;
    dz += Math.cos(toT) * radial;
    const l = Math.hypot(dx, dz) || 1;
    this._steerDir(dx / l, dz / l, a.moveSpeed * this.cfg.strafeSpeedMul, dt);

    if (this.stateT > 0.6 + Math.random() * 1.2) this.strafeDir *= -1;

    // Commit after the patience window, or immediately for aggressive types.
    const patience = this.cfg.patience * (1 - this.cfg.aggression * 0.7);
    if (this.stateT > patience && this.attackCooldown <= 0) {
      this.setState(AI_STATE.COMBAT);
    }
    if (this.stateT > 4) this.setState(AI_STATE.COMBAT);
  }

  _recover(dt, game) {
    const a = this.actor;
    const t = this.target;
    a.blocking = this.cfg.canBlock && !!a.offhand;
    if (!t || t.dead) { this.setState(AI_STATE.RETURN); return; }
    const d = v3distXZ(a, t);
    a.faceTowards(t.x, t.z, dt, 6);
    if (d < this.engageRange + 2.5) {
      const away = Math.atan2(a.x - t.x, a.z - t.z);
      this._steerDir(Math.sin(away), Math.cos(away), a.moveSpeed * 0.7, dt);
    } else {
      a.intentSpeed = 0;
    }
    if (a.stamina > a.maxStamina * 0.62 || this.stateT > 3.5) {
      a.blocking = false;
      this.setState(AI_STATE.COMBAT);
    }
  }

  _flee(dt, game) {
    const a = this.actor;
    const t = this.target;
    if (!t) { this.setState(AI_STATE.RETURN); return; }
    const away = Math.atan2(a.x - t.x, a.z - t.z);
    this._steerDir(Math.sin(away), Math.cos(away), a.runSpeed, dt);
    a.yaw = dampAngle(a.yaw, away, 8, dt);
    if (this.stateT > 3 && v3distXZ(a, t) > 16) this.setState(AI_STATE.COMBAT);
  }

  _return(dt, game) {
    const a = this.actor;
    a.aggro = false;
    const d = Math.hypot(this.homeX - a.x, this.homeZ - a.z);
    if (d < 1.5) {
      a.intentSpeed = 0;
      this.setState(AI_STATE.IDLE);
      // Regenerate on disengage, as the genre expects.
      a.hp = Math.min(a.maxHp, a.hp + a.maxHp * 0.5);
      return;
    }
    this._steerTo(this.homeX, this.homeZ, a.moveSpeed, dt);
    if (this.target) this.setState(AI_STATE.CHASE);
  }

  // -------------------------------------------------------------------------

  _considerDefense(dt, game, t, d) {
    const a = this.actor;
    const cfg = this.cfg;

    // Read the player's wind-up: the tell is the first third of their attack.
    const incoming = t.state === STATE.ATTACK && t.actionU < 0.45 && d < 3.6
      && Math.abs(angleDelta(t.yaw, Math.atan2(a.x - t.x, a.z - t.z))) < 0.9;

    if (incoming && this.blockTimer <= 0) {
      if (cfg.canDodge && Math.random() < cfg.dodgeChance * cfg.aggression + 0.12) {
        this.blockTimer = 1.4;
        const side = Math.random() < 0.5 ? 1 : -1;
        const ang = Math.atan2(a.x - t.x, a.z - t.z) + side * 1.1;
        a.startRoll(Math.sin(ang), Math.cos(ang), { cost: 12, iframes: 0.30, speed: 7.4 });
        return true;
      }
      if (cfg.canBlock && a.offhand && Math.random() < cfg.blockChance + 0.2) {
        this.blockTimer = 1.1;
        a.blocking = true;
        a.intentSpeed = 0;
        return true;
      }
    }
    if (a.blocking && (!incoming || this.blockTimer <= 0.2)) a.blocking = false;
    return false;
  }

  _chooseAttack(d, target) {
    const list = this.cfg.attacks;
    if (!list || !list.length) return null;
    const options = [];
    for (const atk of list) {
      if ((this.attackTimers.get(atk.id) || 0) > 0) continue;
      const [min, max] = atk.range;
      if (d < min || d > max) continue;
      let w = atk.weight || 1;
      // Prefer attacks whose sweet spot matches the current distance.
      const mid = (min + max) / 2;
      w *= 1 - clamp(Math.abs(d - mid) / Math.max(max - min, 0.5), 0, 0.7);
      if (atk.requiresBehind && !this.actor.isBehind(target)) continue;
      if (atk.hpBelow && this.actor.hp > this.actor.maxHp * atk.hpBelow) continue;
      if (w > 0) options.push([atk, w]);
    }
    if (!options.length) return null;
    let total = 0;
    for (const o of options) total += o[1];
    let r = Math.random() * total;
    for (const o of options) {
      r -= o[1];
      if (r <= 0) return o[0];
    }
    return options[options.length - 1][0];
  }

  _steerTo(x, z, speed, dt) {
    const a = this.actor;
    const dx = x - a.x, dz = z - a.z;
    const d = Math.hypot(dx, dz) || 1;
    this._steerDir(dx / d, dz / d, speed, dt);
    a.faceTowards(x, z, dt, a.turnRate * 0.8);
  }

  _steerDir(dx, dz, speed, dt) {
    const a = this.actor;
    // Simple obstacle avoidance: if the way ahead climbs a cliff, slide.
    const probe = 1.4;
    const ahead = a.world.heightAt(a.x + dx * probe, a.z + dz * probe);
    const here = a.world.heightAt(a.x, a.z);
    if (ahead - here > 1.6) {
      const side = this.strafeDir;
      const ang = Math.atan2(dx, dz) + side * 0.9;
      dx = Math.sin(ang); dz = Math.cos(ang);
    }
    a.intentX = dx;
    a.intentZ = dz;
    a.intentSpeed = speed;
  }
}
