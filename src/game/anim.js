// ============================================================================
//  anim.js — procedural poses.
//
//  Locomotion is written to the legs and hips; the current action then writes
//  over the upper body. Because both run every frame into the same target
//  buffer, an attack begun mid-sprint keeps its running legs for free, which
//  is the single most important thing for making melee feel connected to
//  movement rather than pasted on top of it.
//
//  Sign conventions (see rig.js for why):
//    torso bones (+Y up)   — rx > 0 leans BACK,    rx < 0 leans FORWARD
//    limb bones  (+Y down) — rx > 0 swings FORWARD, rx < 0 swings BACK/UP
//    both                  — rz > 0 moves toward +X (the character's left)
//                            ry     twists about the bone's own axis
//
//  Everything here writes the *pose* layer with `set`. The rig then runs the
//  additive layers on top — breath, look-at, inertia — with `add`, so an action
//  that overwrites the whole upper body cannot stop the character breathing.
// ============================================================================

import { clamp, lerp, saturate, TAU } from '../core/math.js';

const PI = Math.PI;

/** Normalised, smoothed progress through a sub-interval of an action. */
function stage(u, a, b) {
  if (b <= a) return u >= b ? 1 : 0;
  const t = clamp((u - a) / (b - a), 0, 1);
  return t * t * (3 - 2 * t);
}

/** Ramp up then back down across [a, b] — the shape of a swing. */
function pulse(u, a, b) {
  const t = clamp((u - a) / Math.max(b - a, 1e-5), 0, 1);
  return Math.sin(t * PI);
}

/**
 * 0..1 ramp with eased ends and a straight middle. Unlike a smoothstep — and
 * far unlike an overshooting ease — its peak rate is only 1/(1-a) times the
 * average, which is what keeps a full-revolution roll from spending its first
 * two frames turning at sixty radians a second.
 */
function rampEased(t, a = 0.22) {
  if (t <= 0) return 0;
  if (t >= 1) return 1;
  const k = 2 * a * (1 - a);
  if (t < a) return (t * t) / k;
  if (t > 1 - a) { const r = 1 - t; return 1 - (r * r) / k; }
  return (t - a * 0.5) / (1 - a);
}

// ---------------------------------------------------------------------------
//  Locomotion
// ---------------------------------------------------------------------------

export function humanoidLocomotion(rig, ctx) {
  const { phase, moveBlend, speedRatio } = ctx;
  const run = saturate(speedRatio);
  const amp = lerp(0.30, 0.76, run) * moveBlend;
  const s = Math.sin(phase);
  const c = Math.cos(phase);

  const idleT = ctx.time * 1.5;
  const breathe = Math.sin(idleT) * 0.022 * (1 - moveBlend);
  const idleSway = Math.sin(idleT * 0.63) * 0.035 * (1 - moveBlend);

  // Thighs swing in opposition; knees flex through the swing phase only.
  rig.setBone('thighL', s * amp - 0.03 * moveBlend, 0, 0.035);
  rig.setBone('thighR', -s * amp - 0.03 * moveBlend, 0, -0.035);
  const bendL = Math.max(0, Math.sin(phase + 2.0));
  const bendR = Math.max(0, Math.sin(phase + 2.0 + PI));
  rig.setBone('shinL', -(0.07 + bendL * amp * 1.55), 0, 0);
  rig.setBone('shinR', -(0.07 + bendR * amp * 1.55), 0, 0);
  rig.setBone('footL', clamp(0.10 + s * amp * 0.45, -0.35, 0.60), 0, 0);
  rig.setBone('footR', clamp(0.10 - s * amp * 0.45, -0.35, 0.60), 0, 0);

  // Pelvis counter-rotation, the vertical bob that sells weight, and the hip
  // drop on whichever side is not carrying: the pelvis is only level when both
  // feet are down, and a walk that keeps it level reads as a puppet on a rail.
  rig.setBone('pelvis', 0, -c * 0.11 * amp, idleSway * 0.5 + c * 0.055 * amp);
  rig.rootOffset[1] = (-Math.abs(c) * 0.050 * amp * (0.5 + run)) + breathe;
  rig.rootOffset[0] = 0;
  rig.rootOffset[2] = 0;

  // Forward lean scales with speed — the clearest visual cue for sprinting.
  rig.setBone('spine', -lerp(0.03, 0.22, run) * moveBlend + breathe, c * 0.055 * amp, 0);
  rig.setBone('chest', -lerp(0.01, 0.09, run) * moveBlend, c * 0.09 * amp, 0);
  rig.setBone('neck', lerp(0.02, 0.20, run) * moveBlend, 0, 0);
  rig.setBone('head', 0.03 * moveBlend + ctx.lookPitch * 0.35, ctx.headYaw || 0, 0);
  rig.setBone('hair', -0.05 - run * 0.22 * moveBlend, 0, 0);
  rig.setBone('tasset', 0.02 + Math.abs(c) * 0.05 * amp, 0, 0);
  // The cloak lags the body: the upper panel leads, the lower trails further.
  const capeSway = Math.sin(ctx.time * 1.7) * 0.06;
  rig.setBone('cape',
    -0.10 - run * 0.55 * moveBlend + Math.sin(ctx.time * 2.1) * 0.04,
    0, capeSway);
  rig.setBone('capeLower',
    -0.06 - run * 0.62 * moveBlend + Math.sin(ctx.time * 2.1 - 0.8) * 0.06,
    0, capeSway * 0.8);
}

/** Neutral arms — the caller overrides these when an action is running. */
export function humanoidArmsNeutral(rig, ctx) {
  const { phase, moveBlend, speedRatio } = ctx;
  const run = saturate(speedRatio);
  const amp = lerp(0.24, 0.62, run) * moveBlend;
  const s = Math.sin(phase);
  const idle = Math.sin(ctx.time * 1.5) * 0.035 * (1 - moveBlend);

  rig.setBone('shoulderL', 0, 0, 0.05);
  rig.setBone('shoulderR', 0, 0, -0.05);

  if (ctx.twoHand) {
    // Both hands on the grip, held to the right of centre.
    rig.setBone('upperArmL', 0.72 + idle, 0.15, 0.34);
    rig.setBone('forearmL', 0.62, 0, -0.30);
    rig.setBone('upperArmR', 0.60 + idle, -0.10, -0.18);
    rig.setBone('forearmR', 0.72, 0, 0.16);
  } else if (ctx.hasShield) {
    // The shield rests against the thigh at ease; poseBlock raises it.
    rig.setBone('upperArmL', 0.12 - s * amp * 0.35, 0.10, 0.22);
    rig.setBone('forearmL', 0.52, 0, -0.18);
    rig.setBone('upperArmR', 0.16 - s * amp * 0.75 + idle, 0, -0.15 - Math.abs(s) * amp * 0.08);
    rig.setBone('forearmR', 1.08 + Math.abs(s) * amp * 0.26, 0, 0.10);
  } else {
    rig.setBone('upperArmL', 0.08 - s * amp * 0.85 + idle, 0, 0.14 + Math.abs(s) * amp * 0.08);
    rig.setBone('forearmL', 0.36 + Math.abs(s) * amp * 0.32, 0, -0.10);
    rig.setBone('upperArmR', 0.16 + s * amp * 0.85 - idle, 0, -0.15 - Math.abs(s) * amp * 0.08);
    rig.setBone('forearmR', 1.10 + Math.abs(s) * amp * 0.26, 0, 0.10);
  }
  rig.setBone('handL', 0, 0, 0);
  // A slight wrist cock keeps a long blade angled up out of the ground.
  rig.setBone('handR', -0.45, 0, 0);
}

// ---------------------------------------------------------------------------
//  Attack pose builders. `u` is 0..1 through the action.
// ---------------------------------------------------------------------------

/**
 * Horizontal slash. The chest twist does most of the work; the arm sweeps
 * across in rz while staying roughly level in rx.
 */
function poseSwingHorizontal(rig, u, dir, reach = 1) {
  const wind = stage(u, 0, 0.30);
  const strike = stage(u, 0.30, 0.50);
  const recover = stage(u, 0.58, 1.0);
  const active = wind - recover;

  const twist = (0.95 * wind - 1.90 * strike + 0.95 * recover) * dir;
  rig.setBone('pelvis', 0, twist * 0.26, 0);
  rig.setBone('spine', -0.10 * active, twist * 0.34, 0.05 * active * dir);
  rig.setBone('chest', -0.06 * active, twist * 0.50, 0.07 * active * dir);
  rig.setBone('head', 0, -twist * 0.30, 0);

  rig.setBone('shoulderR', 0.10 * wind + 0.10 * strike, 0, -0.20 * wind + 0.35 * strike);
  rig.setBone('upperArmR',
    0.35 + 0.60 * wind + 0.62 * strike - 0.95 * recover,
    -0.30 * wind + 0.55 * strike,
    -0.30 - 0.90 * wind + 1.85 * strike - 0.60 * recover);
  rig.setBone('forearmR', 0.50 + 0.45 * wind - 0.60 * strike + 0.25 * recover, 0, 0.12 * wind);
  rig.setBone('handR', 0, 0, 0);

  rig.setBone('upperArmL', 0.20 + 0.45 * wind - 0.35 * strike, 0, 0.35 + 0.30 * wind);
  rig.setBone('forearmL', 0.70, 0, -0.20);

  return { lunge: pulse(u, 0.28, 0.52) * reach };
}

/** Overhead chop: wind up over the shoulder, drop through the target. */
function poseOverhead(rig, u, power = 1) {
  const wind = stage(u, 0, 0.38);
  const strike = stage(u, 0.38, 0.54);
  const recover = stage(u, 0.62, 1.0);
  const active = wind - recover;

  rig.setBone('spine', 0.30 * wind - 0.62 * strike + 0.30 * recover, 0, 0);
  rig.setBone('chest', 0.22 * wind - 0.46 * strike + 0.22 * recover, -0.14 * wind + 0.12 * strike, 0);
  rig.setBone('pelvis', 0, -0.10 * wind + 0.10 * strike, 0);
  rig.setBone('head', -0.14 * wind + 0.26 * strike, 0, 0);

  // Both arms follow the weapon over the head, then chop down front.
  rig.setBone('shoulderR', -0.30 * wind + 0.28 * strike, 0, 0);
  rig.setBone('upperArmR', 0.35 - 2.55 * wind + 3.20 * strike - 0.55 * recover, 0.10 * wind, -0.30 + 0.25 * wind - 0.20 * strike);
  rig.setBone('forearmR', 0.40 + 0.95 * wind - 1.15 * strike, 0, 0);
  rig.setBone('handR', 0, 0, 0);
  rig.setBone('shoulderL', -0.28 * wind + 0.26 * strike, 0, 0);
  rig.setBone('upperArmL', 0.35 - 2.45 * wind + 3.10 * strike - 0.55 * recover, -0.10 * wind, 0.30 - 0.25 * wind + 0.20 * strike);
  rig.setBone('forearmL', 0.45 + 0.90 * wind - 1.10 * strike, 0, 0);

  rig.rootOffset[1] = -0.12 * strike * power + 0.05 * wind;
  return { lunge: pulse(u, 0.36, 0.58) * power };
}

/** Thrust: hips and shoulder drive a straight line forward. */
function poseThrust(rig, u, reach = 1) {
  const wind = stage(u, 0, 0.26);
  const strike = stage(u, 0.26, 0.40);
  const hold = stage(u, 0.40, 0.55);
  const recover = stage(u, 0.58, 1.0);
  const active = wind - recover;

  rig.setBone('pelvis', 0, 0.24 * wind - 0.40 * strike + 0.16 * recover, 0);
  rig.setBone('spine', -0.08 * active, 0.20 * wind - 0.34 * strike, 0);
  rig.setBone('chest', -0.05 * active, 0.42 * wind - 0.76 * strike + 0.30 * recover, 0);
  rig.setBone('head', 0, -0.10 * wind + 0.20 * strike, 0);

  rig.setBone('shoulderR', 0.10 * wind + 0.30 * strike, 0, 0);
  rig.setBone('upperArmR', 0.55 - 0.30 * wind + 0.95 * strike - 0.70 * recover, 0, -0.30 + 0.25 * wind - 0.35 * strike);
  rig.setBone('forearmR', 0.95 + 0.45 * wind - 1.30 * strike + 0.55 * recover, 0, 0);
  rig.setBone('handR', 0, 0, 0);
  rig.setBone('upperArmL', 0.35 + 0.25 * wind - 0.25 * strike, 0, 0.40);
  rig.setBone('forearmL', 0.95 - 0.30 * strike, 0, -0.12);

  return { lunge: (pulse(u, 0.24, 0.5) * 1.15 + hold * 0.15) * reach };
}

/** Rising slash from low to high. */
function poseRising(rig, u) {
  const wind = stage(u, 0, 0.32);
  const strike = stage(u, 0.32, 0.50);
  const recover = stage(u, 0.60, 1.0);
  rig.setBone('spine', -0.26 * wind + 0.46 * strike - 0.20 * recover, 0.16 * wind - 0.26 * strike, 0);
  rig.setBone('chest', -0.18 * wind + 0.34 * strike, 0.28 * wind - 0.50 * strike, 0);
  rig.setBone('shoulderR', 0.15 * wind - 0.25 * strike, 0, 0);
  rig.setBone('upperArmR',
    0.35 + 0.75 * wind - 2.55 * strike + 0.75 * recover,
    0.25 * wind - 0.25 * strike,
    -0.30 - 0.35 * wind + 0.65 * strike);
  rig.setBone('forearmR', 0.55 + 0.45 * wind - 0.75 * strike, 0, 0);
  rig.setBone('upperArmL', 0.28 + 0.20 * wind, 0, 0.38);
  rig.setBone('forearmL', 0.70, 0, -0.15);
  return { lunge: pulse(u, 0.30, 0.55) * 0.8 };
}

/** Full-body spin with the weapon held out. */
function poseSpin(rig, u) {
  const wind = stage(u, 0, 0.24);
  const spin = stage(u, 0.24, 0.62);
  const recover = stage(u, 0.70, 1.0);
  rig.rootRot[1] = -TAU * spin;
  rig.setBone('chest', -0.06, 0.45 * wind - 0.28 * spin, 0);
  rig.setBone('spine', -0.10 * wind, 0.20 * wind, 0);
  rig.setBone('upperArmR', 1.45 - 0.15 * spin, -0.15, -1.15 * wind + 0.20 * spin);
  rig.setBone('forearmR', 0.25, 0, 0.10);
  rig.setBone('upperArmL', 1.30, 0.20, 1.10 * wind);
  rig.setBone('forearmL', 0.35, 0, -0.10);
  return { lunge: pulse(u, 0.22, 0.62) * 0.7 };
}

/** Shield-bash style kick to break a guard. */
function poseKick(rig, u) {
  const wind = stage(u, 0, 0.28);
  const strike = stage(u, 0.28, 0.44);
  const recover = stage(u, 0.52, 1.0);
  // The standing leg stays planted — that is what the kick is levered against.
  rig.planted(1 - strike + recover * 0.9, 1);
  rig.setBone('spine', 0.20 * wind - 0.30 * strike + 0.14 * recover, 0, 0);
  rig.setBone('thighR', -0.55 * wind + 2.05 * strike - 1.55 * recover, 0, -0.05);
  rig.setBone('shinR', -1.25 * wind + 1.15 * strike - 0.20 * recover, 0, 0);
  rig.setBone('footR', 0.35 * wind - 0.55 * strike, 0, 0);
  rig.setBone('thighL', 0.10 * wind, 0, 0.05);
  rig.setBone('shinL', -0.35 * wind, 0, 0);
  rig.setBone('upperArmL', 0.55 + 0.45 * strike, 0.25, 0.55);
  rig.setBone('forearmL', 0.85, 0, -0.20);
  rig.setBone('upperArmR', 0.20, -0.20, -0.45);
  rig.setBone('forearmR', 0.55, 0, 0.15);
  return { lunge: pulse(u, 0.26, 0.5) * 0.55 };
}

function poseBowDraw(rig, u, released) {
  const draw = stage(u, 0, 0.5);
  const rel = released ? stage(u, 0.5, 0.62) : 0;
  rig.setBone('chest', 0, -0.55 + 0.15 * rel, 0);
  rig.setBone('spine', 0, -0.20, 0);
  rig.setBone('pelvis', 0, -0.20, 0);
  // Left arm extended holding the bow, right hand at the cheek.
  rig.setBone('upperArmL', 1.52, 0.25, 0.28);
  rig.setBone('forearmL', 0.06, 0, -0.05);
  rig.setBone('upperArmR', 1.40, -0.30, -0.45 - 0.35 * draw + 0.55 * rel);
  rig.setBone('forearmR', 1.15 + 0.85 * draw - 1.05 * rel, 0, 0);
  rig.setBone('head', 0, -0.35, 0);
  return { lunge: 0 };
}

function poseCast(rig, u) {
  const wind = stage(u, 0, 0.42);
  const push = stage(u, 0.42, 0.58);
  const recover = stage(u, 0.68, 1.0);
  rig.setBone('spine', 0.14 * wind - 0.26 * push + 0.12 * recover, 0, 0);
  rig.setBone('chest', 0.10 * wind - 0.20 * push, 0.20 * wind - 0.32 * push, 0);
  rig.setBone('upperArmR', 0.85 + 0.75 * wind - 0.35 * push - 0.40 * recover, -0.30 * wind + 0.50 * push, -0.45 - 0.20 * wind);
  rig.setBone('forearmR', 0.95 + 0.55 * wind - 0.95 * push, 0, 0);
  rig.setBone('handR', 0.35 * wind - 0.45 * push, 0, 0);
  rig.setBone('upperArmL', 0.45 + 0.30 * wind, 0.25, 0.42);
  rig.setBone('forearmL', 0.80, 0, -0.20);
  return { lunge: push * 0.15 };
}

// ---------------------------------------------------------------------------
//  Moveset registry
// ---------------------------------------------------------------------------

/**
 * Each entry: duration, the window during which the weapon can hit, stamina
 * cost, damage multiplier, poise damage, how far the attack carries the
 * attacker, and the pose builder.
 */
export const ATTACKS = {
  // --- straight sword ------------------------------------------------------
  sword_l1: { dur: 0.62, hit: [0.30, 0.50], stam: 16, dmg: 1.0, poise: 12, motion: 1.6, pose: (r, u) => poseSwingHorizontal(r, u, 1) },
  sword_l2: { dur: 0.60, hit: [0.28, 0.48], stam: 16, dmg: 1.0, poise: 12, motion: 1.5, pose: (r, u) => poseSwingHorizontal(r, u, -1) },
  sword_l3: { dur: 0.78, hit: [0.34, 0.56], stam: 20, dmg: 1.25, poise: 18, motion: 2.0, pose: (r, u) => poseOverhead(r, u, 0.8) },
  sword_h1: { dur: 1.02, hit: [0.42, 0.60], stam: 30, dmg: 1.85, poise: 32, motion: 2.4, pose: (r, u) => poseOverhead(r, u, 1.15) },
  sword_h2: { dur: 0.92, hit: [0.30, 0.46], stam: 27, dmg: 1.65, poise: 26, motion: 4.2, pose: (r, u) => poseThrust(r, u, 1.3) },
  sword_run: { dur: 0.72, hit: [0.22, 0.44], stam: 22, dmg: 1.30, poise: 20, motion: 5.0, pose: (r, u) => poseSwingHorizontal(r, u, 1, 1.6) },

  // --- greatsword ----------------------------------------------------------
  great_l1: { dur: 0.94, hit: [0.40, 0.62], stam: 26, dmg: 1.55, poise: 30, motion: 2.2, pose: (r, u) => poseSwingHorizontal(r, u, 1, 1.2) },
  great_l2: { dur: 0.98, hit: [0.40, 0.64], stam: 28, dmg: 1.60, poise: 32, motion: 2.2, pose: (r, u) => poseSwingHorizontal(r, u, -1, 1.2) },
  great_h1: { dur: 1.42, hit: [0.52, 0.72], stam: 44, dmg: 2.75, poise: 60, motion: 3.0, pose: (r, u) => poseOverhead(r, u, 1.4) },
  great_h2: { dur: 1.30, hit: [0.26, 0.66], stam: 42, dmg: 2.30, poise: 55, motion: 2.0, pose: (r, u) => poseSpin(r, u) },
  great_run: { dur: 1.04, hit: [0.26, 0.52], stam: 32, dmg: 1.9, poise: 40, motion: 5.5, pose: (r, u) => poseOverhead(r, u, 1.0) },

  // --- spear ---------------------------------------------------------------
  spear_l1: { dur: 0.56, hit: [0.24, 0.42], stam: 14, dmg: 0.95, poise: 10, motion: 2.6, pose: (r, u) => poseThrust(r, u, 1.0) },
  spear_l2: { dur: 0.54, hit: [0.24, 0.40], stam: 14, dmg: 0.95, poise: 10, motion: 2.6, pose: (r, u) => poseThrust(r, u, 1.0) },
  spear_l3: { dur: 0.74, hit: [0.30, 0.52], stam: 20, dmg: 1.2, poise: 20, motion: 1.4, pose: (r, u) => poseSwingHorizontal(r, u, -1, 1.1) },
  spear_h1: { dur: 0.98, hit: [0.34, 0.52], stam: 28, dmg: 1.9, poise: 28, motion: 6.5, pose: (r, u) => poseThrust(r, u, 1.7) },
  spear_h2: { dur: 1.12, hit: [0.44, 0.64], stam: 32, dmg: 2.0, poise: 34, motion: 2.0, pose: (r, u) => poseOverhead(r, u, 1.0) },
  spear_run: { dur: 0.68, hit: [0.20, 0.40], stam: 20, dmg: 1.35, poise: 18, motion: 6.5, pose: (r, u) => poseThrust(r, u, 1.5) },

  // --- axe -----------------------------------------------------------------
  axe_l1: { dur: 0.72, hit: [0.34, 0.54], stam: 20, dmg: 1.25, poise: 22, motion: 1.8, pose: (r, u) => poseOverhead(r, u, 0.85) },
  axe_l2: { dur: 0.70, hit: [0.32, 0.52], stam: 20, dmg: 1.25, poise: 22, motion: 1.6, pose: (r, u) => poseRising(r, u) },
  axe_h1: { dur: 1.22, hit: [0.48, 0.68], stam: 38, dmg: 2.35, poise: 48, motion: 2.6, pose: (r, u) => poseOverhead(r, u, 1.3) },
  axe_h2: { dur: 1.10, hit: [0.28, 0.62], stam: 36, dmg: 2.05, poise: 44, motion: 1.8, pose: (r, u) => poseSpin(r, u) },
  axe_run: { dur: 0.86, hit: [0.24, 0.48], stam: 26, dmg: 1.6, poise: 30, motion: 5.0, pose: (r, u) => poseOverhead(r, u, 1.0) },

  // --- dagger --------------------------------------------------------------
  dagger_l1: { dur: 0.40, hit: [0.18, 0.32], stam: 10, dmg: 0.62, poise: 6, motion: 1.8, pose: (r, u) => poseThrust(r, u, 0.6) },
  dagger_l2: { dur: 0.38, hit: [0.16, 0.30], stam: 10, dmg: 0.62, poise: 6, motion: 1.8, pose: (r, u) => poseSwingHorizontal(r, u, -1, 0.6) },
  dagger_l3: { dur: 0.44, hit: [0.18, 0.34], stam: 12, dmg: 0.75, poise: 8, motion: 2.2, pose: (r, u) => poseSwingHorizontal(r, u, 1, 0.7) },
  dagger_h1: { dur: 0.68, hit: [0.24, 0.48], stam: 22, dmg: 1.25, poise: 14, motion: 3.4, pose: (r, u) => poseThrust(r, u, 1.0) },
  dagger_h2: { dur: 0.62, hit: [0.22, 0.42], stam: 20, dmg: 1.1, poise: 12, motion: 3.0, pose: (r, u) => poseRising(r, u) },
  dagger_run: { dur: 0.50, hit: [0.16, 0.34], stam: 14, dmg: 0.9, poise: 10, motion: 4.6, pose: (r, u) => poseThrust(r, u, 0.9) },

  // --- unarmed / shared ----------------------------------------------------
  kick: { dur: 0.62, hit: [0.28, 0.42], stam: 14, dmg: 0.35, poise: 30, motion: 2.2, pose: poseKick },
  bow_shot: { dur: 1.05, hit: [0.5, 0.52], stam: 18, dmg: 1.0, poise: 8, motion: 0, ranged: true, pose: (r, u) => poseBowDraw(r, u, true) },
  cast: { dur: 0.95, hit: [0.5, 0.52], stam: 0, dmg: 1.0, poise: 8, motion: 0, ranged: true, pose: poseCast },
};

/** Light-attack chains per weapon class. */
export const COMBOS = {
  sword: ['sword_l1', 'sword_l2', 'sword_l3'],
  greatsword: ['great_l1', 'great_l2'],
  spear: ['spear_l1', 'spear_l2', 'spear_l3'],
  axe: ['axe_l1', 'axe_l2'],
  dagger: ['dagger_l1', 'dagger_l2', 'dagger_l3'],
  bow: ['bow_shot'],
  staff: ['cast'],
};

export const HEAVY_COMBOS = {
  sword: ['sword_h1', 'sword_h2'],
  greatsword: ['great_h1', 'great_h2'],
  spear: ['spear_h1', 'spear_h2'],
  axe: ['axe_h1', 'axe_h2'],
  dagger: ['dagger_h1', 'dagger_h2'],
  bow: ['bow_shot'],
  staff: ['cast'],
};

export const RUN_ATTACKS = {
  sword: 'sword_run', greatsword: 'great_run', spear: 'spear_run',
  axe: 'axe_run', dagger: 'dagger_run', bow: 'bow_shot', staff: 'cast',
};

// ---------------------------------------------------------------------------
//  Non-attack action poses
// ---------------------------------------------------------------------------

export function poseRoll(rig, u, ctx) {
  // A full forward revolution with a tuck in the middle. The revolution is
  // spread across almost the whole roll at a near-constant rate: a dodge reads
  // as fast because it *covers ground* fast, not because the body teleports
  // through the first third of the turn.
  const spin = rampEased(clamp(u / 0.92, 0, 1));
  rig.rootRot[0] = -TAU * spin;
  // Nothing to stand on mid-revolution: the ground solver keeps out of it.
  rig.planted(0);
  const tuck = pulse(u, 0.0, 0.85);
  rig.rootOffset[1] = -0.42 * tuck;
  rig.setBone('spine', -0.55 * tuck, 0, 0);
  rig.setBone('chest', -0.45 * tuck, 0, 0);
  rig.setBone('neck', -0.35 * tuck, 0, 0);
  rig.setBone('thighL', 1.85 * tuck + 0.1, 0, 0.05);
  rig.setBone('thighR', 1.85 * tuck + 0.1, 0, -0.05);
  rig.setBone('shinL', -1.75 * tuck - 0.1, 0, 0);
  rig.setBone('shinR', -1.75 * tuck - 0.1, 0, 0);
  rig.setBone('footL', 0.4 * tuck, 0, 0);
  rig.setBone('footR', 0.4 * tuck, 0, 0);
  rig.setBone('upperArmL', 0.45 + 1.05 * tuck, 0.20, 0.45);
  rig.setBone('upperArmR', 0.45 + 1.05 * tuck, -0.20, -0.45);
  rig.setBone('forearmL', 1.35 * tuck + 0.3, 0, -0.20);
  rig.setBone('forearmR', 1.35 * tuck + 0.3, 0, 0.20);
  rig.setBone('cape', 0.8 * tuck, 0, 0);
  rig.setBone('capeLower', 0.7 * tuck, 0, 0);
  rig.setBone('tasset', 0.5 * tuck, 0, 0);
}

export function poseBackstep(rig, u) {
  const hop = pulse(u, 0, 0.7);
  rig.planted(1 - hop);
  rig.rootOffset[1] = 0.16 * hop;
  rig.setBone('spine', -0.24 * hop, 0, 0);
  rig.setBone('thighL', 0.80 * hop, 0, 0.05);
  rig.setBone('thighR', 0.58 * hop, 0, -0.05);
  rig.setBone('shinL', -0.90 * hop, 0, 0);
  rig.setBone('shinR', -0.70 * hop, 0, 0);
  rig.setBone('upperArmL', 0.30 - 0.45 * hop, 0.15, 0.35);
  rig.setBone('upperArmR', 0.30 - 0.45 * hop, -0.15, -0.35);
  rig.setBone('forearmL', 0.55, 0, -0.15);
  rig.setBone('forearmR', 0.55, 0, 0.15);
}

export function poseBlock(rig, ctx, impact = 0) {
  const push = impact;
  rig.setBone('spine', -0.14 - 0.16 * push, -0.12, 0);
  rig.setBone('chest', -0.06, -0.30 - 0.12 * push, 0);
  rig.setBone('pelvis', 0, -0.14, 0);
  if (ctx.hasShield) {
    // Shield arm up and across, sword arm tucked back ready to counter.
    rig.setBone('shoulderL', 0.30, 0, 0.10);
    rig.setBone('upperArmL', 1.28 + 0.12 * push, 0.35, 0.42);
    rig.setBone('forearmL', 1.05, 0, -0.55);
    rig.setBone('upperArmR', 0.35, -0.15, -0.34);
    rig.setBone('forearmR', 0.62, 0, 0.14);
  } else {
    rig.setBone('upperArmL', 1.15 + 0.12 * push, 0.35, 0.50);
    rig.setBone('forearmL', 0.90, 0, -0.30);
    rig.setBone('upperArmR', 1.10 + 0.12 * push, -0.30, -0.55);
    rig.setBone('forearmR', 0.88, 0, 0.28);
  }
  rig.setBone('head', -0.08, -0.10, 0);
  rig.setBone('thighL', 0.24, 0, 0.06);
  rig.setBone('thighR', 0.12, 0, -0.06);
  rig.setBone('shinL', -0.36, 0, 0);
  rig.setBone('shinR', -0.26, 0, 0);
  rig.rootOffset[1] = -0.09 - 0.06 * push;
}

export function poseParry(rig, u, ctx) {
  const sweep = pulse(u, 0, 0.6);
  rig.setBone('chest', 0, -0.55 * sweep + 0.30, 0);
  rig.setBone('upperArmL', 1.30 + 0.35 * sweep, 0.85 * sweep, 0.35 + 0.60 * sweep);
  rig.setBone('forearmL', 0.85, 0, -0.25);
  rig.setBone('upperArmR', 0.40, -0.15, -0.35);
  rig.setBone('forearmR', 0.55, 0, 0.15);
  rig.rootOffset[1] = -0.05 * sweep;
}

// ---------------------------------------------------------------------------
//  Reactions
//
//  A reaction has to be picked from something. `dirLocal` says where the blow
//  came from, and the rig measures how hard the body was actually thrown —
//  during a flinch or a death nothing else moves the actor, so the speed it is
//  travelling at *is* the knockback the hit delivered. A tap and a greathammer
//  are three metres a second apart, and that is the difference between a
//  shoulder twitching and a body folding.
// ---------------------------------------------------------------------------

/** Knockback speeds (m/s) separating light / mid / heavy flinches. */
const FLINCH_CUT = [2.4, 5.0];

/**
 * Latch which variant of a reaction is playing.
 *
 * `u` running backwards is the only signal a pose function gets that this is a
 * new hit rather than the next frame of the old one. The knockback that decides
 * the variant is integrated a frame or two after the state changes, so the
 * choice stays open through the opening of the pose — by u = 0.12 the body has
 * moved a couple of centimetres and nobody can see it change its mind.
 */
function reaction(rig, key, u, choose) {
  const table = rig.reactions || (rig.reactions = {});
  let st = table[key];
  if (!st) st = table[key] = { u: 2, v: 0, side: 0, front: 0 };
  const restart = u < st.u - 1e-6 || st.u > 1.5;
  if (restart) { st.v = 0; st.side = 0; st.front = 0; }
  if (restart || u < 0.12) choose(st, restart);
  st.u = u;
  return st;
}

/** Impact strength → flinch tier, from the speed the body is being thrown at. */
function flinchTier(rig) {
  const push = rig.recoil || 0;
  return push >= FLINCH_CUT[1] ? 2 : push >= FLINCH_CUT[0] ? 1 : 0;
}

/**
 * A rap that never breaks stride: the head and chest snap away from the blow
 * and come back. Written additively over the arms and not at all over the
 * legs, so a light hit taken mid-walk does not stop the walk.
 */
function poseFlinchLight(rig, u, front, side) {
  const hit = 1 - stage(u, 0.10, 0.80);
  rig.addBone('spine', 0.13 * hit * front, -0.12 * hit * side, -0.09 * hit * side);
  rig.addBone('chest', 0.15 * hit * front, -0.20 * hit * side, -0.12 * hit * side);
  rig.addBone('head', 0.26 * hit * front, -0.30 * hit * side, -0.10 * hit * side);
  rig.addBone('shoulderL', 0.12 * hit * saturate(side), 0, 0.10 * hit);
  rig.addBone('shoulderR', 0.12 * hit * saturate(-side), 0, -0.10 * hit);
  rig.addBone('upperArmL', -0.22 * hit, 0, 0.14 * hit);
  rig.addBone('upperArmR', -0.18 * hit, 0, -0.14 * hit);
}

/** The middle tier: the whole body absorbs it and the stance breaks. */
function poseFlinchMid(rig, u, front, side) {
  const hit = 1 - stage(u, 0.2, 1.0);
  rig.setBone('spine', 0.42 * hit * front, -0.30 * side * hit, -0.25 * side * hit);
  rig.setBone('chest', 0.30 * hit * front, -0.22 * side * hit, -0.18 * side * hit);
  rig.setBone('head', 0.35 * hit * front, -0.25 * side * hit, 0);
  rig.setBone('upperArmL', 0.25 - 0.85 * hit, 0.30, 0.45 + 0.30 * hit);
  rig.setBone('upperArmR', 0.25 - 0.65 * hit, -0.30, -0.45 - 0.30 * hit);
  rig.setBone('forearmL', 0.95 * hit + 0.30, 0, -0.20);
  rig.setBone('forearmR', 0.85 * hit + 0.30, 0, 0.20);
  // The trailing leg takes the weight; the near leg is driven back a step.
  rig.setBone('thighL', (-0.35 - 0.25 * saturate(side)) * hit, 0, 0.05);
  rig.setBone('thighR', (-0.20 - 0.25 * saturate(-side)) * hit, 0, -0.05);
  rig.setBone('shinL', -0.50 * hit, 0, 0);
  rig.setBone('shinR', -0.35 * hit, 0, 0);
  rig.rootOffset[1] = -0.12 * hit;
}

/** Folded over it: the hit goes through the guard and takes the body with it. */
function poseFlinchHeavy(rig, u, front, side) {
  const hit = 1 - stage(u, 0.26, 1.0);
  const whip = pulse(u, 0, 0.42);
  rig.setBone('pelvis', 0, -0.22 * side * hit, -0.14 * side * hit);
  rig.setBone('spine', (0.70 * hit + 0.20 * whip) * front, -0.55 * side * hit, -0.42 * side * hit);
  rig.setBone('chest', (0.52 * hit) * front, -0.40 * side * hit, -0.30 * side * hit);
  rig.setBone('neck', 0.30 * hit * front, 0, 0);
  rig.setBone('head', (0.55 * hit + 0.25 * whip) * front, -0.45 * side * hit, 0);
  // Both arms fly out and then clamp in — the reflex, then the guard.
  rig.setBone('upperArmL', 0.25 - 1.45 * hit, 0.55 * hit, 0.55 + 0.55 * hit);
  rig.setBone('upperArmR', 0.25 - 1.30 * hit, -0.55 * hit, -0.55 - 0.55 * hit);
  rig.setBone('forearmL', 1.35 * hit + 0.30, 0, -0.30);
  rig.setBone('forearmR', 1.25 * hit + 0.30, 0, 0.30);
  rig.setBone('thighL', (-0.55 - 0.45 * saturate(side)) * hit, 0, 0.05 + 0.12 * hit);
  rig.setBone('thighR', (-0.35 - 0.45 * saturate(-side)) * hit, 0, -0.05 - 0.12 * hit);
  rig.setBone('shinL', -0.85 * hit, 0, 0);
  rig.setBone('shinR', -0.65 * hit, 0, 0);
  rig.setBone('cape', 0.55 * whip, 0, 0);
  rig.setBone('capeLower', 0.70 * whip, 0, 0);
  rig.rootOffset[1] = -0.26 * hit;
}

/** Light, middle, heavy — indexed by tier. */
export const FLINCH_TIERS = [poseFlinchLight, poseFlinchMid, poseFlinchHeavy];

/**
 * @param {object} rig
 * @param {number} u        progress through the flinch
 * @param {number} dirLocal bearing of the attacker in the victim's frame
 * @param {number} [tier]   0..2; measured from the knockback when omitted
 */
export function poseHurt(rig, u, dirLocal, tier) {
  const st = reaction(rig, 'flinch', u, (s, restart) => {
    const t = tier !== undefined ? tier : flinchTier(rig);
    // Never downgrade mid-flinch: the first frames may not have felt the
    // knockback yet, and a flinch that shrinks halfway through reads as a bug.
    s.v = restart ? t : Math.max(s.v, t);
    s.side = Math.sin(dirLocal);
    s.front = Math.cos(dirLocal);
  });
  FLINCH_TIERS[st.v](rig, u, st.front, st.side);
}

export function poseStagger(rig, u) {
  const k = Math.sin(u * PI);
  const wobble = Math.sin(u * 22) * 0.12 * k;
  rig.setBone('spine', 0.55 * k, wobble * 2, wobble);
  rig.setBone('chest', 0.35 * k, wobble, 0);
  rig.setBone('head', 0.45 * k, wobble * 3, 0);
  rig.setBone('upperArmL', 0.30 - 1.25 * k, 0.45, 0.65);
  rig.setBone('upperArmR', 0.30 - 1.15 * k, -0.45, -0.65);
  rig.setBone('forearmL', 0.45, 0, -0.20);
  rig.setBone('forearmR', 0.45, 0, 0.20);
  rig.setBone('thighL', -0.55 * k, 0, 0.15 * k);
  rig.setBone('thighR', -0.25 * k, 0, -0.15 * k);
  rig.setBone('shinL', -0.70 * k, 0, 0);
  rig.setBone('shinR', -0.40 * k, 0, 0);
  rig.rootOffset[1] = -0.22 * k;
}

/** Thrown forward off the blow: pitches over and lands face down. */
function deathFaceDown(rig, u) {
  rig.planted(0);
  const fall = u * u;
  rig.rootRot[0] = -1.50 * fall;
  rig.rootOffset[1] = -0.70 * fall;
  rig.setBone('spine', 0.30 * fall, 0.15 * fall, 0);
  rig.setBone('chest', 0.22 * fall, 0.10 * fall, 0);
  rig.setBone('head', 0.50 * fall, 0.35 * fall, 0);
  rig.setBone('upperArmL', 0.30 + 0.75 * fall, 0.45 * fall, 0.75 * fall + 0.3);
  rig.setBone('upperArmR', 0.30 + 0.65 * fall, -0.45 * fall, -0.75 * fall - 0.3);
  rig.setBone('forearmL', 0.35 * fall + 0.2, 0, 0);
  rig.setBone('forearmR', 0.30 * fall + 0.2, 0, 0);
  rig.setBone('thighL', 0.20 * fall, 0.1, 0.2 * fall);
  rig.setBone('thighR', 0.35 * fall, -0.1, -0.2 * fall);
  rig.setBone('shinL', -0.85 * fall, 0, 0);
  rig.setBone('shinR', -0.55 * fall, 0, 0);
}

/**
 * Driven backwards: the legs are taken out from under it, the chest goes up
 * first and the body lands on its back with one knee still folded.
 */
function deathOnBack(rig, u) {
  rig.planted(0);
  const fall = u * u;
  const arch = pulse(u, 0, 0.55);
  rig.rootRot[0] = 1.42 * fall;
  rig.rootOffset[1] = -0.62 * fall;
  rig.rootOffset[2] = -0.30 * fall;
  rig.setBone('spine', -0.32 * fall - 0.20 * arch, -0.10 * fall, 0);
  rig.setBone('chest', -0.20 * fall - 0.12 * arch, 0, 0);
  rig.setBone('neck', 0.25 * fall, 0, 0);
  rig.setBone('head', 0.60 * fall, -0.25 * fall, 0);
  rig.setBone('upperArmL', 0.20 - 1.20 * fall, 0.30, 0.55 + 0.35 * fall);
  rig.setBone('upperArmR', 0.20 - 1.05 * fall, -0.30, -0.55 - 0.35 * fall);
  rig.setBone('forearmL', 0.55 + 0.35 * arch, 0, -0.15);
  rig.setBone('forearmR', 0.50 + 0.35 * arch, 0, 0.15);
  rig.setBone('thighL', 0.95 * fall, 0.12, 0.18 * fall);
  rig.setBone('thighR', 0.35 * fall, -0.12, -0.10 * fall);
  rig.setBone('shinL', -1.25 * fall, 0, 0);
  rig.setBone('shinR', -0.45 * fall, 0, 0);
  rig.setBone('cape', 0.55 * fall, 0, 0);
  rig.setBone('capeLower', 0.70 * fall, 0, 0);
}

/** Swept off the side: spins down onto one shoulder and stays curled. */
function deathSideways(rig, u, side) {
  rig.planted(0);
  const fall = u * u;
  const s = side >= 0 ? 1 : -1;
  rig.rootRot[2] = 1.40 * fall * s;
  rig.rootRot[1] = 0.55 * fall * s;
  rig.rootOffset[1] = -0.66 * fall;
  rig.setBone('pelvis', 0, 0.20 * fall * s, 0);
  rig.setBone('spine', 0.18 * fall, 0.25 * fall * s, -0.28 * fall * s);
  rig.setBone('chest', 0.14 * fall, 0.18 * fall * s, -0.22 * fall * s);
  rig.setBone('head', 0.30 * fall, 0.35 * fall * s, -0.20 * fall * s);
  rig.setBone('upperArmL', 0.30 + 0.55 * fall, 0.30, 0.35 + 0.45 * fall * s);
  rig.setBone('upperArmR', 0.30 + 0.45 * fall, -0.30, -0.35 + 0.45 * fall * s);
  rig.setBone('forearmL', 0.75 * fall + 0.25, 0, -0.20);
  rig.setBone('forearmR', 0.65 * fall + 0.25, 0, 0.20);
  rig.setBone('thighL', 0.70 * fall, 0.10, (0.25 + 0.20 * s) * fall);
  rig.setBone('thighR', 0.55 * fall, -0.10, (-0.25 + 0.20 * s) * fall);
  rig.setBone('shinL', -1.10 * fall, 0, 0);
  rig.setBone('shinR', -0.95 * fall, 0, 0);
}

/**
 * Nothing threw it — bleed-out, poison, the last point of a long fight. The
 * knees go first, it kneels for a moment, then folds over them.
 */
function deathCrumple(rig, u) {
  const knees = stage(u, 0, 0.34);
  rig.planted(1 - knees);
  const fold = stage(u, 0.30, 0.85);
  rig.rootRot[0] = -0.45 * fold;
  rig.rootOffset[1] = -0.52 * knees - 0.24 * fold;
  rig.setBone('spine', -0.15 * knees + 0.55 * fold, 0.10 * fold, 0);
  rig.setBone('chest', -0.10 * knees + 0.40 * fold, 0, 0);
  rig.setBone('neck', -0.20 * knees + 0.35 * fold, 0, 0);
  rig.setBone('head', 0.25 * knees + 0.40 * fold, 0.15 * fold, 0);
  rig.setBone('upperArmL', 0.35 + 0.30 * knees + 0.55 * fold, 0.20, 0.30);
  rig.setBone('upperArmR', 0.35 + 0.25 * knees + 0.50 * fold, -0.20, -0.30);
  rig.setBone('forearmL', 0.55 + 0.45 * fold, 0, -0.15);
  rig.setBone('forearmR', 0.50 + 0.45 * fold, 0, 0.15);
  rig.setBone('thighL', 1.35 * knees + 0.30 * fold, 0.14, 0.08);
  rig.setBone('thighR', 1.25 * knees + 0.30 * fold, -0.14, -0.08);
  rig.setBone('shinL', -1.90 * knees, 0, 0);
  rig.setBone('shinR', -1.85 * knees, 0, 0);
  rig.setBone('footL', 0.55 * knees, 0, 0);
  rig.setBone('footR', 0.55 * knees, 0, 0);
  rig.setBone('cape', 0.30 * fold, 0, 0);
  rig.setBone('capeLower', 0.45 * fold, 0, 0);
}

/** Every way a body can stop. Which one plays is decided by the killing blow. */
export const DEATH_VARIANTS = [deathFaceDown, deathOnBack, deathSideways, deathCrumple];

/** Speed (m/s) below which a death was not thrown by anything. */
const DEATH_THROWN = 1.5;

export function poseDeath(rig, u) {
  const st = reaction(rig, 'death', u, (s) => {
    // The body falls the way it was actually thrown: the bearing of its own
    // knockback, measured in its own frame. Hit from behind and it pitches
    // onto its face; walked into a spear and it goes over backwards.
    const push = rig.recoil || 0;
    const a = rig.recoilAngle || 0;
    s.side = Math.sin(a) >= 0 ? 1 : -1;
    s.v = push < DEATH_THROWN ? 3
      : Math.abs(a) < 0.85 ? 0
        : Math.abs(a) > 2.30 ? 1 : 2;
  });
  DEATH_VARIANTS[st.v](rig, clamp(u, 0, 1), st.side);
}

export function poseJump(rig, u, rising) {
  const k = rising ? 1 : 0.5;
  rig.planted(0);
  rig.setBone('spine', -0.10, 0, 0);
  rig.setBone('thighL', 0.45 * k, 0, 0.05);
  rig.setBone('thighR', -0.25 * k + 0.35 * (1 - k), 0, -0.05);
  rig.setBone('shinL', -0.95 * k, 0, 0);
  rig.setBone('shinR', -0.45 * k, 0, 0);
  rig.setBone('footL', 0.35 * k, 0, 0);
  rig.setBone('footR', 0.35 * k, 0, 0);
  rig.setBone('upperArmL', 0.30 - 0.95 * k, 0.30, 0.60);
  rig.setBone('upperArmR', 0.30 - 0.95 * k, -0.30, -0.60);
  rig.setBone('forearmL', 0.45, 0, -0.20);
  rig.setBone('forearmR', 0.45, 0, 0.20);
  rig.setBone('cape', 0.75 * k, 0, 0);
  rig.setBone('capeLower', 0.85 * k, 0, 0);
}

export function poseDrink(rig, u) {
  const raise = stage(u, 0.1, 0.4);
  const drink = stage(u, 0.4, 0.62);
  const lower = stage(u, 0.7, 1.0);
  const k = raise - lower;
  rig.setBone('upperArmL', 0.35 + 1.65 * k, 0.35 * k, 0.35 + 0.25 * k);
  rig.setBone('forearmL', 0.40 + 1.45 * k, 0, -0.30 * k);
  rig.setBone('head', 0.42 * drink * (1 - lower), 0, 0);
  rig.setBone('spine', 0.10 * k, 0, 0);
}

export function poseRest(rig, u) {
  const k = stage(u, 0, 0.5);
  // Kneeling: the shins are on the ground, not the soles.
  rig.planted(1 - k);
  // Kneeling at the grace.
  rig.setBone('spine', -0.42 * k, 0, 0);
  rig.setBone('chest', -0.24 * k, 0, 0);
  rig.setBone('head', 0.30 * k, 0, 0);
  rig.setBone('thighL', 1.45 * k, 0.15, 0.06);
  rig.setBone('thighR', 0.30 * k, -0.15, -0.06);
  rig.setBone('shinL', -1.85 * k, 0, 0);
  rig.setBone('shinR', -1.75 * k, 0, 0);
  rig.setBone('footL', 0.55 * k, 0, 0);
  rig.setBone('footR', 0.75 * k, 0, 0);
  rig.setBone('upperArmL', 0.35 + 0.45 * k, 0.20, 0.35);
  rig.setBone('upperArmR', 0.35 + 0.35 * k, -0.20, -0.35);
  rig.setBone('forearmL', 0.65, 0, -0.15);
  rig.setBone('forearmR', 0.60, 0, 0.15);
  rig.rootOffset[1] = -0.58 * k;
}

// ---------------------------------------------------------------------------
//  Additive idle
// ---------------------------------------------------------------------------

/** Deterministic 0..1 from an integer. Settles must not reach for Math.random. */
function hash1(i) {
  const x = Math.sin(i * 127.1 + 311.7) * 43758.5453;
  return x - Math.floor(x);
}

/**
 * Breathing, weight shifts and small settles, added on top of whatever pose is
 * playing. Two things matter. It is additive, so an attack that writes the
 * whole upper body cannot flatten it — a character mid-swing is still a
 * character with lungs. And it is desynced per actor through `ctx.seed`, in
 * both phase and rate, so six guards standing at a gate do not inhale together,
 * which is the most mechanical thing a crowd can possibly do.
 *
 * The rig runs this last, every frame, for every state.
 *
 * @param {object} rig
 * @param {{time:number, seed:number, moveBlend:number, effort:number}} ctx
 */
export function additiveIdle(rig, ctx) {
  const seed = ctx.seed;
  const t = ctx.time + seed * 17.3;
  const still = 1 - 0.72 * saturate(ctx.moveBlend);
  const effort = saturate(ctx.effort);

  // Breath. Faster and deeper the harder the body is working: the chest opens,
  // the shoulders follow a beat behind, the head last.
  const rate = lerp(1.25, 3.30, effort) * lerp(1.0, 1.14, seed);
  const br = Math.sin(t * rate);
  const brLag = Math.sin(t * rate - 0.55);
  const depth = lerp(0.65, 1.55, effort);
  rig.addBone('spine', br * 0.016 * depth, 0, 0);
  rig.addBone('core', br * 0.013 * depth, 0, 0);
  rig.addBone('chest', br * 0.026 * depth, 0, 0);
  rig.addBone('neck', -br * 0.012 * depth, 0, 0);
  rig.addBone('shoulderL', -brLag * 0.030 * depth, 0, -brLag * 0.020 * depth);
  rig.addBone('shoulderR', -brLag * 0.030 * depth, 0, brLag * 0.020 * depth);
  rig.addBone('head', brLag * 0.010 * depth, 0, 0);

  // Weight shift. A standing body drifts from one hip to the other over several
  // seconds and never once holds still.
  const swayA = Math.sin(t * 0.37 + seed * 6.1);
  const swayB = Math.sin(t * 0.23 + seed * 2.7);
  rig.addBone('pelvis', 0, swayB * 0.028 * still, swayA * 0.036 * still);
  rig.addBone('spine', 0, -swayB * 0.018 * still, -swayA * 0.024 * still);
  rig.addBone('head', 0, swayB * 0.050 * still, -swayA * 0.018 * still);

  // Settles. Every few seconds one thing corrects itself — a shoulder drops
  // back, the head resets. Sparse, short, and different each time, which is
  // what keeps the sway from reading as a loop.
  const cyc = t * 0.21 + seed * 3.3;
  const idx = Math.floor(cyc);
  const w = cyc - idx;
  if (w < 0.17) {
    const k = Math.sin((w / 0.17) * PI) * still;
    const r = hash1(idx), r2 = hash1(idx + 811);
    const dir = r2 < 0.5 ? -1 : 1;
    if (r < 0.34) {
      rig.addBone('head', -0.055 * k, 0.13 * k * dir, 0);
      rig.addBone('neck', 0.020 * k, 0.05 * k * dir, 0);
    } else if (r < 0.67) {
      rig.addBone('shoulderL', 0.075 * k * dir, 0, 0.05 * k * dir);
      rig.addBone('shoulderR', -0.055 * k * dir, 0, 0.05 * k * dir);
      rig.addBone('chest', 0, 0.030 * k * dir, 0);
    } else {
      rig.addBone('pelvis', 0.030 * k, 0.045 * k * dir, 0.05 * k * dir);
      rig.addBone('spine', -0.025 * k, -0.030 * k * dir, 0);
    }
  }
}

// ---------------------------------------------------------------------------
//  Quadruped
//  In the quadruped root frame +Y is forward and +Z is down, so a leg's
//  rx > 0 swings it forward and a neck's rx > 0 raises the head.
// ---------------------------------------------------------------------------

export function quadrupedAnimate(rig, ctx) {
  const { phase, moveBlend, speedRatio, time, state, actionU } = ctx;
  const run = saturate(speedRatio);
  const amp = lerp(0.38, 0.98, run) * moveBlend;

  // Diagonal gait at a walk, gathered bound at a run.
  const gait = lerp(PI, 0.6, run);
  const sF = Math.sin(phase), sB = Math.sin(phase + gait);

  rig.setBone('legFL', sF * amp + 0.06, 0, 0);
  rig.setBone('legFR', -sF * amp + 0.06, 0, 0);
  rig.setBone('legBL', sB * amp - 0.10, 0, 0);
  rig.setBone('legBR', -sB * amp - 0.10, 0, 0);
  rig.setBone('footFL', -Math.max(0, -sF) * amp * 1.0 - 0.18, 0, 0);
  rig.setBone('footFR', -Math.max(0, sF) * amp * 1.0 - 0.18, 0, 0);
  rig.setBone('footBL', -Math.max(0, -sB) * amp * 1.0 - 0.30, 0, 0);
  rig.setBone('footBR', -Math.max(0, sB) * amp * 1.0 - 0.30, 0, 0);

  const bound = Math.abs(Math.sin(phase)) * run * 0.14 * moveBlend;
  rig.rootOffset[1] = bound;
  rig.setBone('core', -0.04 - bound * 0.5, Math.sin(phase * 0.5) * 0.05 * moveBlend, 0);
  rig.setBone('chest', 0.06 + 0.06 * run * moveBlend, 0, 0);
  rig.setBone('neck', 0.42 + 0.10 * run * moveBlend + ctx.lookPitch * 0.3, (ctx.headYaw || 0) * 0.5, 0);
  rig.setBone('head', -0.30, (ctx.headYaw || 0) * 0.5, 0);
  rig.setBone('snout', -0.10, 0, 0);
  rig.setBone('tail', -0.55 + Math.sin(time * 3 + phase) * 0.18, Math.sin(time * 2.3) * 0.25, 0);
  rig.setBone('earL', 0.10 + Math.sin(time * 5.1) * 0.06, 0, 0.15);
  rig.setBone('earR', 0.10 + Math.sin(time * 4.7) * 0.06, 0, -0.15);

  if (state === 'attack') {
    const u = actionU;
    const crouch = stage(u, 0.05, 0.28);
    const lunge = stage(u, 0.28, 0.44);
    const bite = pulse(u, 0.32, 0.58);
    const rec = stage(u, 0.58, 1.0);
    rig.setBone('core', -0.04 + 0.30 * crouch - 0.45 * lunge + 0.30 * rec, 0, 0);
    rig.setBone('neck', 0.42 - 0.35 * crouch + 0.55 * lunge - 0.35 * rec, 0, 0);
    rig.setBone('head', -0.30 - 0.30 * lunge, 0, 0);
    rig.setBone('snout', -0.10 - 0.65 * bite, 0, 0);
    rig.setBone('legFL', 0.95 * lunge - 0.35 * crouch, 0, 0);
    rig.setBone('legFR', 0.95 * lunge - 0.35 * crouch, 0, 0);
    rig.setBone('legBL', -0.55 * crouch + 0.35 * lunge, 0, 0);
    rig.setBone('legBR', -0.55 * crouch + 0.35 * lunge, 0, 0);
    rig.rootOffset[1] = 0.26 * lunge - 0.10 * crouch;
    rig.planted(1 - lunge);
  } else if (state === 'hurt') {
    const k = 1 - actionU;
    rig.setBone('core', -0.30 * k, 0.25 * k, 0);
    rig.setBone('neck', 0.10 * k + 0.42, 0, 0);
    rig.setBone('head', -0.30 - 0.30 * k, 0.35 * k, 0);
  } else if (state === 'death') {
    const fall = clamp(actionU, 0, 1);
    rig.planted(1 - fall);
    rig.rootRot[2] = 1.45 * fall;
    rig.rootOffset[1] = -0.38 * fall;
    rig.setBone('neck', 0.42 - 0.55 * fall, 0, 0);
    rig.setBone('legFL', 0.85 * fall, 0, 0);
    rig.setBone('legFR', 0.60 * fall, 0, 0);
    rig.setBone('legBL', 0.70 * fall, 0, 0);
    rig.setBone('legBR', 0.50 * fall, 0, 0);
  }
}

// ---------------------------------------------------------------------------
//  Winged (drake) — shares quadruped legs, adds wing beats
// ---------------------------------------------------------------------------

export function wingedAnimate(rig, ctx) {
  quadrupedAnimate(rig, ctx);
  const { time, state, actionU, airborne } = ctx;
  const beat = Math.sin(time * (airborne ? 5.2 : 1.1));
  const spread = airborne ? 1 : 0.28;
  rig.setBone('wingL0', -beat * 0.45 * spread, 0, 0.55 * spread);
  rig.setBone('wingL1', -0.30 - beat * 0.60 * spread, 0, 0.45 * spread);
  rig.setBone('wingR0', -beat * 0.45 * spread, 0, -0.55 * spread);
  rig.setBone('wingR1', -0.30 - beat * 0.60 * spread, 0, -0.45 * spread);
  rig.setBone('hornL', 0, 0, 0.12);
  rig.setBone('hornR', 0, 0, -0.12);
  rig.setBone('tailTip', -0.25 + Math.sin(time * 2.6) * 0.2, 0, 0);
  rig.setBone('jaw', state === 'attack' ? -0.85 * pulse(actionU, 0.3, 0.6) - 0.15 : -0.12, 0, 0);
}

export { stage, pulse };
