// ============================================================================
//  unit-motion.mjs — turn three of axis K's booleans into numbers.
//
//  The audit currently establishes secondary motion, look-at and the additive
//  idle layer like this:
//
//    out.secondary     = !!(rig.velocityLag || rig.inertia || rig.secondary);
//    out.lookAt        = !!(rig.lookAtWeight !== undefined || p.headYaw !== undefined);
//    out.additiveIdle  = !!(anim.additiveIdle || anim.poseIdleAdditive || rig.ADDITIVE_IDLE);
//
//  Every one of those is satisfied by a field existing. Initialise the field to
//  zero and never touch it again and all three still pass — which is the exact
//  failure docs/QUALITY.md now names: a criterion that cannot be falsified by
//  its own absence will pass a run where the subsystem does nothing.
//
//  These are all observable from the rig alone, so they can be measured rather
//  than asserted, in about a second:
//
//    secondary motion — stop a moving body and watch the mass keep going
//    look-at          — give it something to look at and watch the head turn
//    additive idle    — hold it perfectly still and watch it not be a statue
// ============================================================================

import { Rig, HUMANOID, bindWorldSource, trackContinuity } from '../src/game/rig.js';
import { humanoidLocomotion, humanoidArmsNeutral } from '../src/game/anim.js';

const DT = 1 / 60;
let failures = 0;
trackContinuity(false);
bindWorldSource({ heightAt: () => 0, gazeNear: () => null });

const check = (name, ok, detail) => {
  if (!ok) failures++;
  console.log(`  ${ok ? 'ok  ' : 'FAIL'} ${name.padEnd(30)} ${detail}`);
};

/** A rig driven the way Actor._updateAnimation drives it. */
function makeRig(over = {}) {
  const rig = new Rig(HUMANOID, 1);
  let clock = 0;
  const step = (x, z, ctxOver = {}) => {
    rig.clearTarget();
    rig.rootOffset[0] = 0; rig.rootOffset[1] = 0; rig.rootOffset[2] = 0;
    rig.rootRot[0] = 0; rig.rootRot[1] = 0; rig.rootRot[2] = 0;
    const ctx = {
      phase: clock * 6, moveBlend: 0, speedRatio: 0, strafe: 0, time: clock,
      lookPitch: 0, headYaw: 0, twoHand: false, hasShield: true,
      state: 'idle', actionU: 0, airborne: false, dt: DT,
      ...over, ...ctxOver,
    };
    humanoidLocomotion(rig, ctx);
    humanoidArmsNeutral(rig, ctx);
    rig.apply(DT, x, 0, z, 0);
    clock += DT;
  };
  return { rig, step };
}

console.log('動きの層の単体検査 — 存在ではなく挙動を測る');

// --- secondary motion -------------------------------------------------------
//
// Run, then stop dead. A body with mass keeps going for a moment and settles
// back; a body without simply is where it is put. The lag is read off the rig's
// own inertia state, and it must both appear and then disappear — a spring that
// never settles is not secondary motion, it is a wobble.
{
  // Measured on acceleration, not on speed. A spring at constant velocity sits
  // at equilibrium and reports zero — the first version of this checked mid-run
  // and called that a missing feature. What inertia means is that a *change* in
  // velocity takes a moment to arrive, so the three moments worth measuring are
  // setting off, stopping, and long after stopping.
  const { rig, step } = makeRig();
  let x = 0;
  let launch = 0;
  for (let f = 0; f < 12; f++) {
    x += 0.09;
    step(x, 0, { moveBlend: 1, speedRatio: 1 });
    launch = Math.max(launch, Math.hypot(rig.secondary.x, rig.secondary.z));
  }
  for (let f = 0; f < 90; f++) { x += 0.09; step(x, 0, { moveBlend: 1, speedRatio: 1 }); }
  const cruising = Math.hypot(rig.secondary.x, rig.secondary.z);
  let peak = 0;
  for (let f = 0; f < 8; f++) {
    step(x, 0, { moveBlend: 0, speedRatio: 0 });
    peak = Math.max(peak, Math.hypot(rig.secondary.x, rig.secondary.z));
  }
  for (let f = 0; f < 150; f++) step(x, 0, { moveBlend: 0, speedRatio: 0 });
  const settled = Math.hypot(rig.secondary.x, rig.secondary.z);

  check('二次モーション: 走り出しで遅れる', launch > 0.01, `${launch.toFixed(4)} (> 0.01)`);
  check('二次モーション: 等速では落ち着く', cruising < 0.05,
    `${cruising.toFixed(4)} (< 0.05)  バネは等速で平衡`);
  check('二次モーション: 停止後も残る', peak > 0.01, `${peak.toFixed(4)} (> 0.01)`);
  check('二次モーション: やがて収まる', settled < 0.01,
    `${settled.toFixed(4)} (< 0.01)  停止2.5秒後`);
}

// --- look-at ----------------------------------------------------------------
//
// Put something beside the body and check the head actually turns toward it,
// then take it away and check the head comes back. A look-at weight that exists
// but never leaves zero passes the current boolean and turns no heads.
{
  // Inside the gaze cone, not at the edge of it. LOOK_YAW is 1.15 rad and the
  // weight is deliberately faded out past it, so a target at 90 degrees is
  // half-released by design — the first version put one there and read the
  // fade as a missing feature. A target at about 40 degrees is what a look-at
  // is for.
  const target = { x: 5, y: 1.4, z: 6 };
  const { rig, step } = makeRig();
  bindWorldSource({ heightAt: () => 0, gazeNear: () => target });
  for (let f = 0; f < 120; f++) step(0, 0);
  const headTurn = rig.lookAtWeight;
  // The head bone's own facing, relative to the body's: the number that
  // actually decides whether a head is pointed at anything.
  const head = rig.template.byName.get('head');
  const wr = rig.worldRot;
  const fwdX = wr[head * 9 + 6], fwdZ = wr[head * 9 + 8];
  const headYaw = Math.atan2(fwdX, fwdZ);

  // Behind the body: past LOOK_YAW the gaze must be released rather than the
  // neck twisted, which is the behaviour the fade exists for.
  const behind = { x: 0, y: 1.4, z: -6 };
  bindWorldSource({ heightAt: () => 0, gazeNear: () => behind });
  for (let f = 0; f < 120; f++) step(0, 0);
  const behindWeight = rig.lookAtWeight;

  bindWorldSource({ heightAt: () => 0, gazeNear: () => null });
  for (let f = 0; f < 180; f++) step(0, 0);
  const released = rig.lookAtWeight;

  check('注視: 対象があると重みが立つ', headTurn > 0.3, `${headTurn.toFixed(3)} (> 0.3)`);
  check('注視: 頭が実際に向く', Math.abs(headYaw) > 0.15,
    `${headYaw.toFixed(3)} rad (|.| > 0.15)`);
  check('注視: 背後は首を捻らず手放す', behindWeight < 0.15,
    `${behindWeight.toFixed(3)} (< 0.15)`);
  check('注視: 対象を失うと戻る', released < 0.1, `${released.toFixed(3)} (< 0.1)`);
}

// --- additive idle ----------------------------------------------------------
//
// Hold the body perfectly still and watch the pose. A statue reports zero
// variation; a breathing body does not. Measured as the spread of the whole
// pose vector over four seconds, so it cannot be satisfied by one bone twitching
// once.
{
  const { rig, step } = makeRig();
  for (let f = 0; f < 60; f++) step(0, 0);
  const n = rig.pose.length;
  const mins = new Float32Array(n).fill(Infinity);
  const maxs = new Float32Array(n).fill(-Infinity);
  for (let f = 0; f < 240; f++) {
    step(0, 0);
    for (let i = 0; i < n; i++) {
      if (rig.pose[i] < mins[i]) mins[i] = rig.pose[i];
      if (rig.pose[i] > maxs[i]) maxs[i] = rig.pose[i];
    }
  }
  let moved = 0, span = 0;
  for (let i = 0; i < n; i++) {
    const d = maxs[i] - mins[i];
    if (d > 0.004) moved++;
    span += d;
  }
  check('加算アイドル: 動く自由度の数', moved >= 6, `${moved} 自由度 (>= 6)`);
  check('加算アイドル: 総変位', span > 0.10, `${span.toFixed(3)} rad (> 0.10)`);

  // And it must not be a loop so short it reads as a twitch: compare the pose
  // against itself a second apart and require it to have moved on.
  const { rig: r2, step: s2 } = makeRig();
  for (let f = 0; f < 60; f++) s2(0, 0);
  const a = Float32Array.from(r2.pose);
  for (let f = 0; f < 60; f++) s2(0, 0);
  let drift = 0;
  for (let i = 0; i < a.length; i++) drift += Math.abs(r2.pose[i] - a[i]);
  check('加算アイドル: 1秒後も同じ姿勢でない', drift > 0.02, `${drift.toFixed(4)} rad`);
}

bindWorldSource(null);
console.log(failures ? `\n${failures} 件 不合格` : '\n全て合格');
process.exit(failures ? 1 : 0);
