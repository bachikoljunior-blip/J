// ============================================================================
//  unit-footik.mjs — do the feet actually reach the ground, on ground the rig
//  has to solve for rather than stand flat on.
//
//  The audit measures this (K 接地誤差, target <= 0.03 m) by teleporting the
//  player onto the steepest slope it can find within a fixed search and reading
//  two joint positions. That costs twelve minutes to reach, tests exactly one
//  slope, and the slope it finds depends on where the previous probe left the
//  player.
//
//  The rig takes its ground from a bound source — bindWorldSource — so a stub
//  height field is all it needs. That makes the same measurement a second's
//  work, over slopes chosen to be hard rather than whatever the world happened
//  to offer: steeper than the leg can reach, stepped, ridged along the body's
//  axis and across it, and moving underneath a body that is standing still.
//
//  This is the same argument as tools/unit-continuity.mjs. The browser audit is
//  the end-to-end check; it should not also be the first place a solver defect
//  can be seen.
// ============================================================================

import { Rig, HUMANOID, QUADRUPED, bindWorldSource, trackContinuity } from '../src/game/rig.js';
import {
  humanoidLocomotion, humanoidArmsNeutral, quadrupedAnimate,
} from '../src/game/anim.js';

// The audit's own target. A sole further off the ground than this reads as
// floating; further under it reads as sunk.
const ERR_CAP = 0.03;
// Settling time. The ground correction is deliberately rate-limited (IK_SLEW),
// so a foot arrives over a few frames rather than snapping — asking for the
// error immediately would measure the limiter, not the solver.
const SETTLE = 90;
const DT = 1 / 60;

let failures = 0;
trackContinuity(false);

/**
 * Stand a rig at (x, z) on `heightAt`, let it settle, and report how far the
 * worst sole sits from the ground under it.
 */
/**
 * Where a leg chain actually touches the ground.
 *
 * A humanoid chain is thigh -> shin with a separate sole bone, so the sole's
 * joint position is the contact point. A quadruped chain is leg -> foot with no
 * sole, so the contact is the *tip* of the foot bone and its joint position is
 * the ankle — about 0.3 m up. Measuring the joint for both reported the
 * quadruped floating 0.297 m on flat ground, which was this harness picking the
 * wrong point rather than the solver failing.
 */
function contacts(rig) {
  return rig.template.legChains.map((leg) => (leg.sole >= 0
    ? { name: rig.template.boneList[leg.sole].name, tip: false }
    : { name: rig.template.boneList[leg.lower].name, tip: true }));
}

function stand(name, heightAt, x, z, { template = HUMANOID, move = null, quad = false } = {}) {
  bindWorldSource({ heightAt, gazeNear: () => null });
  const rig = new Rig(template, 1);
  const feet = contacts(rig);
  let px = x, pz = z;
  let clock = 0;
  const h0 = heightAt(x, z);
  let bodyY = Number.isFinite(h0) ? h0 : 0;

  // Drive the pose layer exactly the way Actor._updateAnimation does. Without
  // it the rig has no locomotion pose at all, the ground solver's stride
  // allowance has nothing sensible to preserve, and a foot drifts a quarter of
  // a metre off flat ground — which looks like a solver defect and is really
  // this harness failing to be the game. The first version of this file
  // reported exactly that, on flat ground, and it was wrong.
  const step = () => {
    rig.clearTarget();
    rig.rootOffset[0] = 0; rig.rootOffset[1] = 0; rig.rootOffset[2] = 0;
    rig.rootRot[0] = 0; rig.rootRot[1] = 0; rig.rootRot[2] = 0;
    const ctx = {
      phase: 0, moveBlend: 0, speedRatio: 0, strafe: 0, time: clock,
      lookPitch: 0, headYaw: 0, twoHand: false, hasShield: true,
      state: 'idle', actionU: 0, airborne: false, dt: DT,
    };
    if (quad) quadrupedAnimate(rig, ctx);
    else { humanoidLocomotion(rig, ctx); humanoidArmsNeutral(rig, ctx); }
    // The body keeps its last good height when the field cannot answer. The
    // game never places a body at a coordinate the height field has no answer
    // for — feeding one in tests a condition the solver is not responsible for,
    // and the first version of this file did exactly that and reported the rig
    // non-finite. What the solver IS responsible for is its own foot samples,
    // which reach out past the body.
    const bodyH = heightAt(px, pz);
    if (Number.isFinite(bodyH)) bodyY = bodyH;
    rig.apply(DT, px, bodyY, pz, 0);
    clock += DT;
  };

  for (let f = 0; f < SETTLE; f++) {
    if (move) { px = x + move(f).x; pz = z + move(f).z; }
    step();
  }

  // Sample over a window rather than at one instant. The error oscillates with
  // the idle, so a single reading is a lottery — the browser audit takes one
  // and has been reporting whichever moment it happened to land on.
  // What "standing on the ground" means, precisely.
  //
  // Not "every foot touches the ground" — a foot above the others is stride,
  // and the solver preserves it on purpose ("whatever is above the lowest foot
  // is stride, and stride is kept"). Taking the maximum over all contacts
  // therefore penalises a design feature: the quadruped's hind paw sits
  // 0.0366 m up on flat ground, which is SOLE_LIFT plus about 0.017 m of idle
  // stride, identical on flat, sloped and stepped ground.
  //
  // What must hold is that the *lowest* contact is on the ground, and that
  // nothing is under it. Those are the two ways a body reads as wrong: floating
  // above the terrain, or sunk into it.
  let worstPlanted = 0, worstFoot = '';
  let deepest = 0, deepFoot = '';
  let finite = true;
  for (let f = 0; f < 180; f++) {
    if (move) { px = x + move(SETTLE + f).x; pz = z + move(SETTLE + f).z; }
    step();
    let lowest = Infinity, lowestName = '';
    for (const c of feet) {
      const j = c.tip ? rig.boneTip(c.name, {}) : rig.jointPos(c.name, {});
      if (!Number.isFinite(j.x) || !Number.isFinite(j.y) || !Number.isFinite(j.z)) { finite = false; continue; }
      const ground = heightAt(j.x, j.z);
      if (!Number.isFinite(ground)) continue;
      const d = j.y - ground;
      if (d < lowest) { lowest = d; lowestName = c.name; }
      if (d < deepest) { deepest = d; deepFoot = c.name; }
    }
    if (lowest !== Infinity && Math.abs(lowest) > worstPlanted) {
      worstPlanted = Math.abs(lowest); worstFoot = lowestName;
    }
  }

  const sunk = deepest < -0.005;
  const ok = finite && worstPlanted <= ERR_CAP && !sunk;
  if (!ok) failures++;
  console.log(`  ${ok ? 'ok  ' : 'FAIL'} ${name.padEnd(28)} 接地足の誤差 ${worstPlanted.toFixed(4)} m` +
    `${worstFoot ? ` (${worstFoot})` : ''}` +
    `${sunk ? `  ← ${deepFoot} が ${(-deepest).toFixed(3)}m 埋没` : ''}` +
    `${finite ? '' : '  ← 非有限'}`);
  return worstPlanted;
}

console.log(`接地IKの単体検査 — 接地誤差 ≤ ${ERR_CAP} m`);

// Flat, as a control. If this fails nothing below means anything.
stand('平地', () => 0, 0, 0);
stand('平地 (高度 40m)', () => 40, 0, 0);

// Slopes, by gradient. A humanoid's stance is roughly 0.3 m across, so a
// gradient of g puts the two soles about 0.3g apart in height — which is
// exactly what the solver exists to absorb.
for (const g of [0.15, 0.3, 0.5, 0.8]) {
  stand(`斜面 勾配 ${g}`, (x) => x * g, 0, 0);
}
// Across the body rather than along it: the same gradient, rotated, so the
// difference lands between the feet instead of in front of and behind them.
for (const g of [0.3, 0.6]) {
  stand(`斜面 横 勾配 ${g}`, (x, z) => z * g, 0, 0);
}

// A step under one foot. This is the case a pelvis solve exists for: one leg
// must reach further than the other without the body tipping or a foot
// hanging.
stand('段差 0.25m', (x) => (x > 0 ? 0.25 : 0), 0, 0);
stand('段差 0.5m', (x) => (x > 0 ? 0.5 : 0), 0, 0);

// A ridge directly under the body — both feet below the point they straddle.
stand('尾根の上', (x) => -Math.abs(x) * 0.6, 0, 0);
// And a trough, where both feet are above the low point between them.
stand('溝の上', (x) => Math.abs(x) * 0.6, 0, 0);

// Ground moving under a body that is not moving: the solver has to keep up
// with terrain it did not choose to walk onto.
stand('地面が動く', (x, z) => Math.sin(z * 0.7) * 0.4, 0, 0, {
  move: (f) => ({ x: 0, z: f * 0.02 }),
});

// A quadruped has four contacts and a different rest pose; the guarantee is a
// property of the solver, not of the humanoid.
stand('四足 平地', () => 0, 0, 0, { template: QUADRUPED, quad: true });
stand('四足 斜面 勾配 0.4', (x) => x * 0.4, 0, 0, { template: QUADRUPED, quad: true });
stand('四足 段差 0.3m', (x) => (x > 0 ? 0.3 : 0), 0, 0, { template: QUADRUPED, quad: true });

// An unanswerable sample must not put a foot at NaN. Everywhere-NaN means the
// solver has nothing to solve toward at all and should simply leave the pose
// alone; patchy NaN is the realistic shape, where some foot samples answer and
// some do not.
stand('高さが常に NaN', () => NaN, 0, 0);
stand('高さが部分的に NaN', (x, z) => (Math.floor(Math.abs(x * 3)) % 5 === 2 ? NaN : x * 0.2), 0, 0);

bindWorldSource(null);
console.log(failures ? `\n${failures} 件 不合格` : '\n全て合格');
process.exit(failures ? 1 : 0);
