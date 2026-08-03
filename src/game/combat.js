// ============================================================================
//  combat.js — hit resolution.
//
//  Melee uses a swept capsule taken from the actual weapon bone, so reach is
//  a property of the weapon model rather than a hand-tuned number per attack.
//  A greatsword genuinely reaches further than a dagger because its blade is
//  longer, and the arc it sweeps is the arc you see.
// ============================================================================

import { clamp, lerp, saturate, angleDelta, v3distXZ } from '../core/math.js';
import { STATE, FACTION } from './actor.js';
import { BLEND } from '../gfx/particles.js';

const _segA = { x: 0, y: 0, z: 0 };
const _segB = { x: 0, y: 0, z: 0 };

/** Where the damaging part of an actor's attack is this frame. */
export function weaponSegment(actor, outA, outB) {
  if (actor.rigKind === 'quadruped' || actor.rigKind === 'winged') {
    const head = actor.rig.jointPos(actor.rigKind === 'winged' ? 'jaw' : 'snout', outA);
    actor.rig.boneTip(actor.rigKind === 'winged' ? 'jaw' : 'snout', outB);
    return actor.rigKind === 'winged' ? 0.55 * actor.scale : 0.30 * actor.scale;
  }
  actor.rig.boneTip('handR', outA);
  const shape = actor.weapon ? actor.weapon.shape || {} : {};
  const len = (shape.len || 0.75) * actor.scale;
  const b = actor.rig.boneBasis('handR', actor._segBasis || (actor._segBasis = new Float32Array(9)));
  outB.x = outA.x + b[3] * len;
  outB.y = outA.y + b[4] * len;
  outB.z = outA.z + b[5] * len;
  return (shape.w ? Math.max(0.16, shape.w * 3 * actor.scale) : 0.22 * actor.scale);
}

/** Closest distance between a segment and an actor's vertical capsule. */
function segmentHitsActor(ax, ay, az, bx, by, bz, radius, target) {
  const cx = target.x;
  const cz = target.z;
  const y0 = target.y;
  const y1 = target.y + target.height;
  const R = target.radius + radius;

  // Sample the segment; 5 samples is plenty for weapon-length spans.
  let best = Infinity, bestT = 0;
  for (let i = 0; i <= 4; i++) {
    const t = i / 4;
    const px = ax + (bx - ax) * t;
    const py = ay + (by - ay) * t;
    const pz = az + (bz - az) * t;
    const dy = py < y0 ? y0 - py : py > y1 ? py - y1 : 0;
    const dx = px - cx, dz = pz - cz;
    const d = Math.sqrt(dx * dx + dz * dz + dy * dy);
    if (d < best) { best = d; bestT = t; }
  }
  return best <= R ? bestT : -1;
}

/**
 * Run melee hit detection for one attacker against a candidate list.
 * Returns the number of targets struck this frame.
 */
export function resolveMeleeHits(game, attacker, candidates) {
  if (!attacker.hitActive || attacker.dead) return 0;
  const radius = weaponSegment(attacker, _segA, _segB);
  let hits = 0;

  for (let i = 0; i < candidates.length; i++) {
    const t = candidates[i];
    if (t === attacker || t.dead) continue;
    if (t.faction === attacker.faction && !game.friendlyFire) continue;
    if (attacker.hitSet.has(t.id)) continue;
    // Broad-phase before the segment test.
    const rough = v3distXZ(attacker, t);
    if (rough > 6 * attacker.scale + t.radius) continue;

    const u = segmentHitsActor(_segA.x, _segA.y, _segA.z, _segB.x, _segB.y, _segB.z, radius, t);
    if (u < 0) continue;

    attacker.hitSet.add(t.id);
    hits++;

    const info = attacker.buildAttackInfo
      ? attacker.buildAttackInfo(t)
      : { damage: 20, poise: 12, type: 'physical', source: attacker };
    info.source = attacker;

    const hx = lerp(_segA.x, _segB.x, u);
    const hy = lerp(_segA.y, _segB.y, u);
    const hz = lerp(_segA.z, _segB.z, u);

    const result = t.takeDamage(info);
    game.onHitResolved?.(attacker, t, info, result, { x: hx, y: hy, z: hz });
  }
  return hits;
}

// ---------------------------------------------------------------------------
//  Criticals: backstabs and ripostes
// ---------------------------------------------------------------------------

export function findBackstabTarget(actor, candidates, maxDist = 1.5) {
  let best = null, bestD = maxDist;
  for (const t of candidates) {
    if (t === actor || t.dead || t.faction === actor.faction) continue;
    if (t.noCritical) continue;
    const d = v3distXZ(actor, t);
    if (d > bestD) continue;
    if (!actor.isBehind(t)) continue;
    if (!actor.facing(t, 0.9)) continue;
    best = t; bestD = d;
  }
  return best;
}

export function findRiposteTarget(actor, candidates, maxDist = 1.9) {
  let best = null, bestD = maxDist;
  for (const t of candidates) {
    if (t === actor || t.dead || t.faction === actor.faction) continue;
    if (t.state !== STATE.PARRIED && t.state !== STATE.STAGGER) continue;
    if (t.noCritical) continue;
    const d = v3distXZ(actor, t);
    if (d > bestD) continue;
    if (!actor.facing(t, 1.2)) continue;
    best = t; bestD = d;
  }
  return best;
}

/** Lock both actors into the critical animation and schedule the damage. */
export function executeCritical(game, attacker, victim, kind) {
  const angle = Math.atan2(attacker.x - victim.x, attacker.z - victim.z);
  // Snap the attacker to the correct side and both to a shared facing.
  const dist = kind === 'backstab' ? 0.95 : 1.15;
  attacker.x = victim.x + Math.sin(angle) * dist;
  attacker.z = victim.z + Math.cos(angle) * dist;
  attacker.yaw = Math.atan2(victim.x - attacker.x, victim.z - attacker.z);
  if (kind === 'riposte') victim.yaw = attacker.yaw + Math.PI;

  attacker.setState(STATE.RIPOSTE, { duration: kind === 'backstab' ? 1.05 : 1.25 });
  attacker.invuln = kind === 'backstab' ? 1.0 : 1.2;
  victim.setState(STATE.RIPOSTED, { duration: kind === 'backstab' ? 1.05 : 1.25 });
  victim.invuln = 0;
  victim.noPush = true;

  const delay = kind === 'backstab' ? 0.45 : 0.55;
  game.schedule(delay, () => {
    victim.noPush = false;
    if (victim.dead) return;
    const info = attacker.buildAttackInfo ? attacker.buildAttackInfo(victim) : { damage: 40, poise: 40 };
    info.crit = true;
    info.critMul = (kind === 'backstab' ? 2.2 : 2.9) * (attacker.critBonus || 1);
    info.ignoreInvuln = true;
    info.poise = 9999;
    info.big = true;
    info.source = attacker;
    const res = victim.takeDamage(info);
    game.onCritical?.(attacker, victim, kind, res);
  });
  game.onCriticalStart?.(attacker, victim, kind);
}

// ---------------------------------------------------------------------------
//  Projectiles
// ---------------------------------------------------------------------------

export class Projectile {
  constructor(game, opts) {
    this.game = game;
    this.x = opts.x; this.y = opts.y; this.z = opts.z;
    this.vx = opts.vx; this.vy = opts.vy; this.vz = opts.vz;
    this.life = opts.life || 4;
    this.radius = opts.radius || 0.28;
    this.damage = opts.damage || 30;
    this.poise = opts.poise || 10;
    this.type = opts.type || 'physical';
    this.source = opts.source || null;
    this.faction = opts.faction !== undefined ? opts.faction : FACTION.ENEMY;
    this.gravity = opts.gravity !== undefined ? opts.gravity : -9;
    this.color = opts.color || [1, 0.8, 0.4];
    this.size = opts.size || 0.22;
    this.trail = opts.trail !== undefined ? opts.trail : true;
    this.status = opts.status || null;
    this.pierce = opts.pierce || 0;
    this.hitSet = new Set();
    this.dead = false;
    this.kind = opts.kind || 'arrow';
    this.knockback = opts.knockback || 2.5;
    this.emissive = opts.emissive !== undefined ? opts.emissive : 0.8;
    this.homing = opts.homing || 0;
    this.target = opts.target || null;
    this.explode = opts.explode || null;
  }

  update(dt, candidates) {
    if (this.dead) return;
    this.life -= dt;
    if (this.life <= 0) { this.expire(); return; }

    if (this.homing > 0 && this.target && !this.target.dead) {
      const dx = this.target.x - this.x;
      const dy = (this.target.y + this.target.height * 0.55) - this.y;
      const dz = this.target.z - this.z;
      const d = Math.hypot(dx, dy, dz) || 1;
      const speed = Math.hypot(this.vx, this.vy, this.vz);
      const k = this.homing * dt;
      this.vx = lerp(this.vx, (dx / d) * speed, k);
      this.vy = lerp(this.vy, (dy / d) * speed, k);
      this.vz = lerp(this.vz, (dz / d) * speed, k);
    }

    this.vy += this.gravity * dt;
    const px = this.x, py = this.y, pz = this.z;
    this.x += this.vx * dt;
    this.y += this.vy * dt;
    this.z += this.vz * dt;

    if (this.trail) {
      this.game.particles.spawn({
        x: px, y: py, z: pz,
        vx: 0, vy: 0.2, vz: 0,
        life: 0.28, size: this.size * 0.8, sizeEnd: 0.02,
        r: this.color[0], g: this.color[1], b: this.color[2], alpha: 0.85,
        drag: 3, gravity: 0.3, soft: 0.4, blend: BLEND.ADDITIVE,
      });
    }

    // Terrain.
    const h = this.game.world.heightAt(this.x, this.z);
    if (this.y <= h) {
      this.y = h;
      this.expire(true);
      return;
    }

    // Actors: swept sphere against the segment travelled this frame.
    for (const t of candidates) {
      if (t.dead || t.faction === this.faction) continue;
      if (this.hitSet.has(t.id)) continue;
      const u = segmentHitsActor(px, py, pz, this.x, this.y, this.z, this.radius, t);
      if (u < 0) continue;
      this.hitSet.add(t.id);
      const info = {
        damage: this.damage, poise: this.poise, type: this.type,
        source: this.source, knockback: this.knockback,
        status: this.status, parryable: false,
      };
      const res = t.takeDamage(info);
      this.game.onHitResolved?.(this.source, t, info, res, { x: this.x, y: this.y, z: this.z });
      if (this.pierce > 0) { this.pierce--; } else { this.expire(true); return; }
    }
  }

  expire(impact = false) {
    if (this.dead) return;
    this.dead = true;
    if (this.explode) {
      this.game.spawnExplosion(this.x, this.y, this.z, this.explode);
    } else if (impact) {
      this.game.particles.burst(this.x, this.y, this.z, 6, {
        r: this.color[0], g: this.color[1], b: this.color[2],
        size: 0.14, life: 0.35, spread: 2.2, up: 1.4,
        blend: BLEND.ADDITIVE, alpha: 0.9, drag: 3, gravity: -4,
      });
    }
  }

  render(batches) {
    const b = batches.get('box');
    const speed = Math.hypot(this.vx, this.vy, this.vz) || 1;
    const dx = this.vx / speed, dy = this.vy / speed, dz = this.vz / speed;
    // Build an orthonormal basis with +Y along the flight direction.
    let ux = 0, uy = 1, uz = 0;
    if (Math.abs(dy) > 0.95) { ux = 1; uy = 0; uz = 0; }
    let rx = uy * dz - uz * dy, ry = uz * dx - ux * dz, rz = ux * dy - uy * dx;
    const rl = Math.hypot(rx, ry, rz) || 1;
    rx /= rl; ry /= rl; rz /= rl;
    const fx = dy * rz - dz * ry, fy = dz * rx - dx * rz, fz = dx * ry - dy * rx;

    const len = this.kind === 'arrow' ? 0.62 : this.size * 2;
    const w = this.kind === 'arrow' ? 0.035 : this.size;
    const basis = this._basis || (this._basis = new Float32Array(9));
    basis[0] = rx * w; basis[1] = ry * w; basis[2] = rz * w;
    basis[3] = dx * len; basis[4] = dy * len; basis[5] = dz * len;
    basis[6] = fx * w; basis[7] = fy * w; basis[8] = fz * w;
    b.pushMatrix(basis, this.x - dx * len * 0.5, this.y - dy * len * 0.5, this.z - dz * len * 0.5,
      this.color[0], this.color[1], this.color[2], this.emissive, 1, 1);
  }
}

// ---------------------------------------------------------------------------
//  Area effects
// ---------------------------------------------------------------------------

export class AreaEffect {
  constructor(game, opts) {
    this.game = game;
    this.x = opts.x; this.y = opts.y; this.z = opts.z;
    this.radius = opts.radius || 3;
    this.delay = opts.delay || 0;
    this.duration = opts.duration || 0.4;
    this.damage = opts.damage || 60;
    this.poise = opts.poise || 30;
    this.type = opts.type || 'fire';
    this.source = opts.source || null;
    this.faction = opts.faction !== undefined ? opts.faction : FACTION.ENEMY;
    this.color = opts.color || [1, 0.5, 0.2];
    this.t = 0;
    this.fired = false;
    this.dead = false;
    this.telegraph = opts.telegraph !== false;
    this.status = opts.status || null;
    this.knockback = opts.knockback || 5;
  }

  update(dt, candidates) {
    this.t += dt;
    if (this.telegraph && this.delay > 0 && this.t < this.delay) {
      // Warning ring — the player's only fair chance to react.
      const k = this.t / this.delay;
      if (Math.random() < dt * 30) {
        const a = Math.random() * Math.PI * 2;
        const r = this.radius * (0.75 + 0.25 * k);
        this.game.particles.spawn({
          x: this.x + Math.cos(a) * r, y: this.y + 0.08, z: this.z + Math.sin(a) * r,
          vx: 0, vy: 0.35, vz: 0, life: 0.35,
          size: 0.18, sizeEnd: 0.05,
          r: this.color[0], g: this.color[1], b: this.color[2], alpha: 0.6 + 0.4 * k,
          drag: 2, gravity: 0, soft: 0.5, blend: BLEND.ADDITIVE,
        });
      }
      return;
    }
    if (!this.fired) {
      this.fired = true;
      this._detonate(candidates);
    }
    if (this.t > this.delay + this.duration) this.dead = true;
  }

  _detonate(candidates) {
    const g = this.game;
    for (let i = 0; i < 34; i++) {
      const a = Math.random() * Math.PI * 2;
      const r = Math.sqrt(Math.random()) * this.radius;
      g.particles.spawn({
        x: this.x + Math.cos(a) * r, y: this.y + 0.1, z: this.z + Math.sin(a) * r,
        vx: Math.cos(a) * 1.5, vy: 3 + Math.random() * 5, vz: Math.sin(a) * 1.5,
        life: 0.5 + Math.random() * 0.6,
        size: 0.30 + Math.random() * 0.30, sizeEnd: 0.06,
        r: this.color[0], g: this.color[1], b: this.color[2], alpha: 0.95,
        drag: 1.6, gravity: 1.5, soft: 0.7, blend: BLEND.ADDITIVE,
      });
    }
    g.shake(0.35, 0.3);
    for (const t of candidates) {
      if (t.dead || t.faction === this.faction) continue;
      const d = Math.hypot(t.x - this.x, t.z - this.z);
      if (d > this.radius + t.radius) continue;
      const falloff = 1 - saturate((d - this.radius * 0.4) / (this.radius * 0.7));
      const info = {
        damage: this.damage * lerp(0.55, 1, falloff),
        poise: this.poise, type: this.type, source: this.source,
        knockback: this.knockback, status: this.status,
        parryable: false, big: true,
      };
      const res = t.takeDamage(info);
      g.onHitResolved?.(this.source, t, info, res, { x: t.x, y: t.y + 1, z: t.z });
    }
  }
}
