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

// Expressed as an angular *velocity*, not as an angle per frame.
//
// A cut is a rotation that is fast in time. Per-frame is the wrong unit for it,
// because the same criterion then means something different on every machine —
// and worse, an engine built to satisfy a per-frame bound turns more slowly
// when frames are long. This engine did exactly that: a 180 degree turn took
// 0.25 s at 60 fps and 0.95 s at 20 fps, so the game played differently on a
// weaker phone rather than merely looking rougher. The per-frame caps are now
// backstops at RATE * MAX_DT and the rate is what governs.
//
// TOL is room for the fact that the limiter's cost model bounds a bone's swept
// angle rather than computing it exactly.
const CAP_RATE = 17;      // rad/s, the rig's own TURN_RATE
const TOL = 1.12;

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
  const rate = r.maxSteady;              // already rad/s
  const worst = r.maxSteadyAngle;        // the angle it took on one frame
  const ok = rate <= CAP_RATE * TOL;
  if (!ok) failures++;
  const where = r.worst[0] ? `${r.worst[0].bone}@f${r.worst[0].frame}` : '-';
  console.log(`  ${ok ? 'ok  ' : 'FAIL'} ${name.padEnd(34)} ${rate.toFixed(2)} rad/s ` +
    `(${worst.toFixed(4)} rad @ ${(dt * 1000).toFixed(0)}ms)  ${where}`);
  return rate;
}

console.log(`継続性の単体検査 — 上限 ${CAP_RATE} rad/s (許容 ${(CAP_RATE * TOL).toFixed(1)})`);

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

// --- hostile input ----------------------------------------------------------
// The limited facing is an accumulator, so a single non-finite yaw would be
// permanent and the body would draw at NaN — which renders nothing at all.
console.log('非有限入力の検査 — 一度のNaNが恒久化しないこと');
{
  trackContinuity(false);
  const rig = new Rig(HUMANOID, 1);
  for (let f = 0; f < 20; f++) rig.apply(1 / 60, 0, 0, 0, 0);
  rig.apply(1 / 60, 0, 0, 0, NaN);
  for (let f = 0; f < 40; f++) rig.apply(1 / 60, 0, 0, 0, PI / 2);
  const finite = Number.isFinite(rig._yawS)
    && rig.worldRot.every((v) => Number.isFinite(v))
    && rig.worldPos.every((v) => Number.isFinite(v));
  const arrived = Math.abs((rig._yawS ?? 0) - PI / 2) < 0.02;
  const ok = finite && arrived;
  if (!ok) failures++;
  console.log(`  ${ok ? 'ok  ' : 'FAIL'} ${'yaw に一度 NaN が来る'.padEnd(30)} ` +
    `有限=${finite} 目標到達=${arrived} (_yawS=${rig._yawS})`);
}

// --- the debt has to be repaid ---------------------------------------------
// A limiter that drops what it cannot afford is not a limiter, it is a bug that
// leaves the model facing the wrong way. Check the facing actually arrives.
console.log('追従の検査 — 制限した向きが一致し、所要時間がフレームレートに依らないこと');
// The time a turn takes must not depend on the frame rate, which is the whole
// reason the caps were rewritten. Same turn, three frame rates, same seconds.
for (const [label, target, budget] of [['180deg', PI, 0.40], ['90deg', PI / 2, 0.24], ['45deg', PI / 4, 0.14]]) {
  const times = [];
  for (const fps of [60, 30, 20]) {
    trackContinuity(false);
    const dt = 1 / fps;
    const rig = new Rig(HUMANOID, 1);
    for (let f = 0; f < 40; f++) rig.apply(dt, 0, 0, 0, 0);
    let t = -1;
    // Run past the settle point rather than breaking at it: the residual is
    // checked below, and stopping the moment the error drops under 0.02 rad
    // means the residual can only ever be 0.02.
    for (let f = 0; f < 400; f++) {
      rig.apply(dt, 0, 0, 0, target);
      if (t < 0 && Math.abs((rig._yawS ?? target) - target) < 0.02) t = (f + 1) * dt;
    }
    times.push({ fps, t, err: Math.abs((rig._yawS ?? target) - target) });
  }
  const slowest = Math.max(...times.map((x) => x.t));
  const fastest = Math.min(...times.map((x) => x.t));
  // The spread has a floor that has nothing to do with the engine: a 20 fps
  // frame is 50 ms, so a duration measured there is quantised to 50 ms, and the
  // settle threshold costs another frame either side. Two slow frames is the
  // tightest this measurement can resolve — asking for less would be asking the
  // engine to beat the clock it is timed with.
  const spreadFloor = 2 / Math.min(...times.map((x) => x.fps));
  const ok = times.every((x) => x.t > 0 && x.t <= budget && x.err < 1e-4)
    && slowest - fastest <= spreadFloor;
  if (!ok) failures++;
  console.log(`  ${ok ? 'ok  ' : 'FAIL'} ${label.padEnd(34)} ` +
    times.map((x) => `${x.fps}fps ${x.t.toFixed(3)}s`).join('  ') +
    `  幅 ${(slowest - fastest).toFixed(3)}s (量子化下限 ${spreadFloor.toFixed(3)}s, 所要上限 ${budget}s)`);
}

trackContinuity(false);
console.log(failures ? `\n${failures} 件 不合格` : '\n全て合格');
process.exit(failures ? 1 : 0);
