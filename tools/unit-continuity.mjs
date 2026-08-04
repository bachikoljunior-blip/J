// ============================================================================
//  unit-continuity.mjs — drive rigs directly and assert the continuity budget
//  actually holds.
//
//  Why this exists as its own tool: the browser audit measured this for weeks
//  and got it wrong twice. It reported 0.364 rad/frame, which is above the cap
//  the limiter enforces and therefore already a proof that something escaped
//  the budget — and because the probe drove the player through a window it
//  chose itself, it could not say what. Two full browser diagnostics, at about
//  twelve minutes each, failed to reproduce the number at all.
//
//  The rig is plain JavaScript. Constructing one and calling apply() in a loop
//  needs no browser, no GL, no world, and runs in about two seconds — and the
//  first run of it found the cause immediately: a 180-degree yaw reassignment
//  moved a foot 2.71 rad in a single frame, because _skin wrote the actor's
//  facing straight into the world transform without passing it through _damp.
//
//  So: adversarial input at the unit level first, and the slow end-to-end run
//  only afterwards. A cheap test that can fail is worth more than an expensive
//  one that cannot say why.
// ============================================================================

import { Rig, HUMANOID, QUADRUPED, WINGED, trackContinuity, continuityReport, continuityFrame }
  from '../src/game/rig.js';

// The limiter's own cap, plus room for the fact that the cost model bounds a
// bone's swept angle rather than computing it exactly.
const CAP = 0.27;
const TOL = 1.12;
const LIMIT = CAP * TOL;

const PI = Math.PI;
let failures = 0;

/**
 * Run one scenario and report the worst single-frame rotation any bone took.
 * `drive` returns {yaw, rootRot} for a frame, so a case can move the facing,
 * the body tilt, or both at once.
 */
function scenario(name, template, dt, frames, drive) {
  trackContinuity(true);
  const rig = new Rig(template, 1);
  rig.hostTag = name;
  rig.hostState = 'unit';
  for (let f = 0; f < frames; f++) {
    continuityFrame();
    const d = drive(f) || {};
    if (d.rootRot) rig.rootRot = d.rootRot;
    rig.hostState = d.state || 'unit';
    rig.apply(dt, d.x || 0, d.y || 0, d.z || 0, d.yaw || 0);
  }
  const r = continuityReport(3);
  const worst = r.maxSteady;
  const ok = worst <= LIMIT;
  if (!ok) failures++;
  const where = r.worst[0] ? `${r.worst[0].bone}@f${r.worst[0].frame}` : '-';
  console.log(`  ${ok ? 'ok  ' : 'FAIL'} ${name.padEnd(34)} ${worst.toFixed(4)} rad  ${where}`);
  return worst;
}

console.log(`継続性の単体検査 — 上限 ${CAP} rad/frame (許容 ${LIMIT.toFixed(3)})`);

// --- facing -----------------------------------------------------------------
// dodge() assigns this.yaw outright, and AI turning is a damped step whose size
// grows with the frame time. Both used to bypass the budget entirely.
for (const [label, turn] of [['180deg', PI], ['90deg', PI / 2], ['45deg', PI / 4]]) {
  scenario(`yaw snap ${label}`, HUMANOID, 1 / 60, 60, (f) => ({ yaw: f < 30 ? 0 : turn }));
}
// A slow frame is where this bites hardest: the damped turn toward a target
// takes a bigger bite the longer the frame, so the worst case is a stutter.
for (const dt of [1 / 30, 1 / 20, 1 / 10]) {
  scenario(`yaw snap 180deg @ dt=${dt.toFixed(3)}`, HUMANOID, dt, 40, (f) => ({ yaw: f < 20 ? 0 : PI }));
}
// Alternating: a body caught between two targets must not buzz.
scenario('yaw alternating +-90deg', HUMANOID, 1 / 60, 60, (f) => ({ yaw: f % 2 ? PI / 2 : -PI / 2 }));

// --- body tilt --------------------------------------------------------------
// Deaths and rolls write rootRot straight through, same as facing did.
scenario('rootRot snap (death pitch)', HUMANOID, 1 / 60, 60,
  (f) => ({ rootRot: f < 30 ? [0, 0, 0] : [PI / 2, 0, 0] }));
scenario('rootRot tumble (roll)', HUMANOID, 1 / 60, 60,
  (f) => ({ rootRot: [f * 0.35, 0, 0] }));

// --- both at once -----------------------------------------------------------
// The budget is one scale for the whole skeleton, so two sources spending it
// together must still land inside it.
scenario('yaw + rootRot together', HUMANOID, 1 / 60, 60,
  (f) => ({ yaw: f < 30 ? 0 : PI, rootRot: f < 30 ? [0, 0, 0] : [PI / 2, 0, 0] }));

// --- other skeletons --------------------------------------------------------
// The guarantee is a property of the rig, not of the humanoid.
scenario('quadruped yaw snap 180deg', QUADRUPED, 1 / 60, 60, (f) => ({ yaw: f < 30 ? 0 : PI }));
scenario('winged yaw snap 180deg', WINGED, 1 / 60, 60, (f) => ({ yaw: f < 30 ? 0 : PI }));

// --- the debt has to be repaid ---------------------------------------------
// A limiter that drops what it cannot afford is not a limiter, it is a bug that
// leaves the model facing the wrong way. Check the facing actually arrives.
console.log('追従の検査 — 制限した向きが最終的に一致すること');
for (const [label, target, budget] of [['180deg', PI, 20], ['90deg', PI / 2, 12], ['45deg', PI / 4, 8]]) {
  trackContinuity(false);
  const rig = new Rig(HUMANOID, 1);
  for (let f = 0; f < 30; f++) rig.apply(1 / 60, 0, 0, 0, 0);
  let settled = -1;
  for (let f = 0; f < 90; f++) {
    rig.apply(1 / 60, 0, 0, 0, target);
    if (settled < 0 && Math.abs((rig._yawS ?? target) - target) < 0.02) settled = f + 1;
  }
  const err = Math.abs((rig._yawS ?? target) - target);
  const ok = settled > 0 && settled <= budget && err < 1e-4;
  if (!ok) failures++;
  console.log(`  ${ok ? 'ok  ' : 'FAIL'} ${label.padEnd(34)} ${settled} フレーム ` +
    `(${(settled / 60).toFixed(3)}s, 上限 ${budget})  残差 ${err.toFixed(6)}`);
}

trackContinuity(false);
console.log(failures ? `\n${failures} 件 不合格` : '\n全て合格');
process.exit(failures ? 1 : 0);
