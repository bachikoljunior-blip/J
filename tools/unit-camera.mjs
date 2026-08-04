// ============================================================================
//  unit-camera.mjs — drive the third-person camera directly and measure how far
//  the view cuts in a single frame.
//
//  The rig got a continuity guarantee because a bone that snaps is visible. The
//  camera is the same defect with a much larger radius: when it jumps, the
//  entire frame jumps. Nothing measured it.
//
//  PlayerCamera needs a player, an input and a world, and all three are small
//  enough to stub — so this runs in node in about a second, no GL and no
//  browser, the same way tools/unit-continuity.mjs does.
//
//  Every scenario drives with zero look input. Anything the view does here is
//  the game moving the camera on the player's behalf, not the player moving it.
// ============================================================================

import { PlayerCamera } from '../src/game/player.js';

// Rates, not per-frame steps. A cut is a rotation that is fast in time, and
// per-frame is a unit that means something different on every machine — see the
// same argument, at length, in tools/unit-continuity.mjs.
//
// 6 rad/s is 344 deg/s, already faster than anything the game turns the camera
// by itself.
const VIEW_CAP = 6.0;     // rad/s
// How fast the boom may dolly in or out. Measured as the *length* of the orbit
// offset, not the offset itself: the eye is fully determined by focus +
// yaw/pitch + boom, so the offset vector's own delta double-counts the rotation
// VIEW_CAP already bounds. Length and direction are the two independent things,
// and they get one cap each.
const DOLLY_CAP = 7.2;    // m/s
// How long the camera may stay pinned against those two rate limits.
//
// DOLLY_CAP and VIEW_CAP are nearly unfalsifiable on their own, and this file
// is the evidence: six of twelve scenarios report a dolly of exactly 7.00 m/s,
// which is CAM_BOOM_IN, because the boom's inward speed is clamped where it is
// applied. A bound of 7.2 above a clamp of 7.0 cannot be exceeded unless the
// clamp itself breaks. It grades the clamp, not the camera, and it passed every
// time while the camera was demonstrably wrong at least twice.
//
// Saturation duration is what the clamp cannot fake, and both bounds below are
// derived from the camera's own geometry rather than fitted to a measurement:
//
//   dolly  the boom's entire travel is 5.4 - CAM_MIN_BOOM(1.25) = 4.15 m, which
//          at 7.0 m/s takes 0.593 s. A wall that suddenly occludes the player
//          legitimately spends that long pulling in. Longer than its own full
//          travel means it is not travelling — it is oscillating or fighting
//          the ground lift.
//   swing  a lock-on turn of 180 degrees at CAM_SWING_RATE(3.6) takes
//          pi/3.6 = 0.873 s, and switching to a target directly behind is
//          exactly that. Beyond it there is no framing left to reach.
//
// Both of these are structural sanity bounds, and saying so is the point:
// targetDistance is clamped to [4.8, 8.4] and the boom floor is CAM_MIN_BOOM,
// so the longest inward travel possible is 7.15 m = 1.02 s at CAM_BOOM_IN, and
// the boom stops saturating the moment it reaches its floor. A single stretch
// of saturation therefore cannot exceed about a second however wrong the camera
// is. These catch a stretch longer than the geometry can account for — a
// poisoned accumulator, a `want` that never settles — and nothing finer. The
// number that actually grades the camera is the *fraction* below.
const DOLLY_SPAN_CAP = 1.1;    // s   (1.02 structural maximum + margin)
const SWING_SPAN_CAP = 1.1;    // s   (0.873 half-turn at CAM_SWING_RATE + margin)
// The camera must stay above the ground it is flying over. This is a
// correctness bound, not a smoothness one, and it is here because leaving it
// out cost a whole audit: removing the old hard max() against terrain height
// made the boom continuous and also let the camera sit *inside* hills, which
// the eight continuity scenarios all passed cleanly while the rendered frame
// went flat — surface detail measured exactly 0 on four of six scenes.
//
// A test suite that only measures the property you were working on will
// certify the damage you did to the ones you weren't.
const CLEARANCE_MIN = 0.0;   // m above the terrain under the eye

// Every scenario runs at all three, because a camera that satisfies a per-frame
// bound by moving more slowly on a slow device has not solved anything.
const RATES = [60, 30, 20];

let failures = 0;

const stubWorld = (heightAt) => ({ heightAt });
const flatWorld = stubWorld(() => 0);
const noLook = { look: { x: 0, y: 0 } };

const stubPlayer = (over = {}) => ({
  x: 0, y: 0, z: 0, yaw: 0, height: 1.8, isSprinting: false, ...over,
});

/**
 * Run a scenario and report the worst single-frame view rotation and orbit
 * step. `drive(f)` may move the player, hand back a lock target, or both.
 */
/**
 * `opts.finiteOnly` asserts that the camera stays finite without also demanding
 * that it move smoothly.
 *
 * Continuity is a promise about a continuous world. A height field that answers
 * NaN in one-metre bands between real values is discontinuous by construction,
 * and no camera can follow it smoothly — demanding that would be asking the
 * engine to invent information the world did not give it. What it CAN promise
 * is that an unanswerable sample never produces a non-finite eye, because a
 * non-finite eye renders nothing at all.
 *
 * The alternative was to loosen the caps until this case passed, which would
 * have loosened them for every case that is a genuine continuity test.
 */
function scenario(name, world, drive, frames = 120, opts = {}) {
  let worstRate = 0, worstDollyRate = 0, minClear = Infinity, nonFinite = false;
  let dollySpan = 0, swingSpan = 0, dollyFrac = 0, swingFrac = 0;
  for (const fps of RATES) {
    const r = once(name, world, drive, Math.round(frames * fps / 60), 1 / fps);
    if (r.view > worstRate) worstRate = r.view;
    if (r.dolly > worstDollyRate) worstDollyRate = r.dolly;
    if (r.clear < minClear) minClear = r.clear;
    if (r.dollySpan > dollySpan) dollySpan = r.dollySpan;
    if (r.swingSpan > swingSpan) swingSpan = r.swingSpan;
    if (r.dollyFrac > dollyFrac) dollyFrac = r.dollyFrac;
    if (r.swingFrac > swingFrac) swingFrac = r.swingFrac;
    if (r.nonFinite) nonFinite = true;
  }
  // `satMax` is the share of the scenario the camera may spend pinned against
  // its own rate limits. It is per-scenario because the scenarios differ in
  // kind: a wall put directly behind the player is *asking* for a full-rate
  // pull-in and it would be wrong to call that a defect. Open flat ground is
  // asking for nothing, so a camera that races its limit there is broken no
  // matter what the peak rate says — and that is a bound the clamps cannot
  // satisfy on the engine's behalf.
  const satMax = opts.satMax ?? 0.5;
  const ok = !nonFinite && (opts.finiteOnly
    || (worstRate <= VIEW_CAP && worstDollyRate <= DOLLY_CAP && minClear >= CLEARANCE_MIN
      && dollySpan <= DOLLY_SPAN_CAP && swingSpan <= SWING_SPAN_CAP
      && dollyFrac <= satMax && swingFrac <= satMax));
  if (!ok) failures++;
  console.log(`  ${ok ? 'ok  ' : 'FAIL'} ${name.padEnd(30)} ` +
    `視線 ${worstRate.toFixed(2)} rad/s  ドリー ${worstDollyRate.toFixed(2)} m/s  ` +
    `張り付き ${(dollyFrac * 100).toFixed(0)}%/${(swingFrac * 100).toFixed(0)}% ` +
    `(最長 ${dollySpan.toFixed(2)}/${swingSpan.toFixed(2)}s, 上限 ${(satMax * 100).toFixed(0)}%)  ` +
    `地面クリア ${minClear === Infinity ? '—' : minClear.toFixed(2)} m` +
    `${opts.finiteOnly ? '  (有限性のみ)' : ''}${nonFinite ? '  ← 位置が非有限' : ''}`);
  return { worstRate, worstDollyRate, minClear, dollySpan, swingSpan, dollyFrac, swingFrac };
}

function once(name, world, drive, frames, DT) {
  const player = stubPlayer();
  const cam = new PlayerCamera(player);
  cam.shakeT = 0; cam.shakeAmp = 0;   // shake is random by design; not the subject
  let prevDir = null, prevOrbit = null;
  let worstView = 0, worstOrbit = 0, atView = -1, atOrbit = -1;
  let minClear = Infinity;
  let nonFinite = false;

  // Settle on the opening conditions first. A camera constructed at its
  // defaults spends its first frames arriving, and that is not a cut.
  const K = DT * 60;
  const first = drive(0, K) || {};
  Object.assign(player, first.player || {});
  const ph0 = world.heightAt(player.x, player.z);
  player.y = Number.isFinite(ph0) ? ph0 : 0;
  for (let w = 0; w < 40; w++) cam.update(DT, noLook, world, first.lock || null);

  for (let f = 0; f < frames; f++) {
    const d = drive(f, K) || {};
    Object.assign(player, d.player || {});
    // The player stands on the ground. Without this the body sinks into a rise
    // and the boom collides with terrain the player is supposedly inside.
    //
    // An unanswerable sample keeps the last good height rather than moving the
    // player to NaN: the game never lets a body reach a coordinate the height
    // field cannot answer for, so a harness that does is testing a condition
    // the camera is not responsible for. What IS the camera's responsibility is
    // surviving an unanswerable sample from its own boom march, which reaches
    // past the player by several metres.
    const ph = world.heightAt(player.x, player.z);
    if (Number.isFinite(ph)) player.y = ph;
    cam.update(DT, noLook, world, d.lock || null);

    const vx = cam.look.x - cam.pos.x, vy = cam.look.y - cam.pos.y, vz = cam.look.z - cam.pos.z;
    const vl = Math.hypot(vx, vy, vz) || 1;
    const dir = [vx / vl, vy / vl, vz / vl];
    const orbit = Math.hypot(cam.pos.x - cam.focusX, cam.pos.y - cam.focusY, cam.pos.z - cam.focusZ);
    // A camera that has gone non-finite renders nothing at all, so this is
    // checked before anything else and reported as its own failure.
    if (!Number.isFinite(cam.pos.x) || !Number.isFinite(cam.pos.y) || !Number.isFinite(cam.pos.z)
      || !Number.isFinite(cam.look.x) || !Number.isFinite(cam.look.y) || !Number.isFinite(cam.look.z)) {
      nonFinite = true;
    }
    const gh = world.heightAt(cam.pos.x, cam.pos.z);
    const clear = Number.isFinite(gh) ? cam.pos.y - gh : Infinity;
    if (clear < minClear) minClear = clear;

    if (prevDir) {
      const dot = dir[0] * prevDir[0] + dir[1] * prevDir[1] + dir[2] * prevDir[2];
      const ang = Math.acos(dot > 1 ? 1 : dot < -1 ? -1 : dot);
      if (ang > worstView) { worstView = ang; atView = f; }
      const step = Math.abs(orbit - prevOrbit);
      if (step > worstOrbit) { worstOrbit = step; atOrbit = f; }
    }
    prevDir = dir; prevOrbit = orbit;
  }

  void atView; void atOrbit;
  return {
    view: worstView / DT, dolly: worstOrbit / DT, clear: minClear, nonFinite,
    // Read from the camera's own tracker rather than recomputed here, so this
    // check and the audit are looking at the same instrument. A peak rate is
    // clamped by construction — six of these scenarios report exactly 7.00 m/s,
    // which is CAM_BOOM_IN — so the peak says only that the clamp is present.
    // How long the camera stays pinned against it is the part the clamp cannot
    // make look good.
    dollySpan: cam.worstDollySpan || 0,
    swingSpan: cam.worstSwingSpan || 0,
    dollyFrac: cam.dollySatFrac,
    swingFrac: cam.swingSatFrac,
  };
}

console.log(`カメラの連続性 — 視線 ≤ ${VIEW_CAP} rad/s, ドリー ≤ ${DOLLY_CAP} m/s  (60/30/20fps)`);

// --- terrain occlusion ------------------------------------------------------
// A wall the camera has to pull in past, then clear. The pull-in samples eight
// discrete points along the boom, so the distance it picks moves in steps of an
// eighth of the boom length — and letting go of it restores the full length.
const wall = stubWorld((x, z) => (z < -4 && z > -9 ? 20 : 0));
scenario('壁に寄る（引き込み）', wall, (f, k) => ({ player: { z: 6 - f * 0.05 * k } }));
scenario('壁から離れる（戻り）', wall, (f, k) => ({ player: { z: 0 + f * 0.05 * k } }));

// --- ground clamp -----------------------------------------------------------
// pos.y is clamped to the terrain with a hard max(), so walking onto a rise
// crosses the clamp and the camera stops falling in one frame.
const ridge = stubWorld((x, z) => Math.max(0, (-z - 2) * 0.9));
scenario('尾根を越える（下限クランプ）', ridge, (f, k) => ({ player: { z: 4 - f * 0.06 * k } }));

// --- lock-on ----------------------------------------------------------------
// Acquiring a target moves the shoulder offset, the focus height and the look
// point all at once, and the look point is a lerp toward a target that may be
// many metres away.
const target = { x: 6, y: 0, z: 6, height: 1.8 };
scenario('ロックオン取得', flatWorld, (f, k) => (f > 40 / k ? { lock: target } : {}));
scenario('ロックオン解除', flatWorld, (f, k) => (f < 40 / k ? { lock: target } : {}));
scenario('ロックオン切替', flatWorld,
  (f, k) => (f > 40 / k && f < 80 / k ? { lock: target } : f >= 80 / k ? { lock: { x: -7, y: 0, z: 3, height: 1.8 } } : {}));

// --- hostile terrain samples ------------------------------------------------
// The world's height function is not guaranteed to answer for every coordinate
// the camera asks about: the boom marches out past the player, and near a world
// edge those samples leave the map. A damped accumulator poisoned by one
// non-finite sample stays poisoned for the rest of the session, where the hard
// max() it replaced recovered on the next frame. A NaN camera position renders
// nothing, writes no depth, and produces a frame of pure sky — which is what
// the audit measured while the game itself looked correct.
const edgeWorld = stubWorld((x, z) => (Math.hypot(x, z) > 12 ? NaN : 0));
scenario('世界の縁でNaNが返る', edgeWorld, (f, k) => ({ player: { x: -6 + f * 0.08 * k } }));
const spikyNaN = stubWorld((x, z) => (Math.floor(Math.abs(z)) % 7 === 3 ? NaN : Math.sin(z * 0.2)));
scenario('断続的にNaNが返る', spikyNaN, (f, k) => ({ player: { z: -f * 0.09 * k } }), 120,
  { finiteOnly: true });

// --- steep ground -----------------------------------------------------------
// The case the removed max() was carrying: a slope rising behind the player, so
// the boom is aimed into the hillside. If the boom cannot get short enough, the
// eye ends up inside the hill and the frame goes flat.
const slope = stubWorld((x, z) => Math.max(0, (-z - 2) * 1.6));
scenario('急斜面を背に立つ', slope, (f, k) => ({ player: { z: 6 - f * 0.05 * k } }));
const bowl = stubWorld((x, z) => Math.max(0, (Math.hypot(x, z) - 6) * 2.2));
scenario('窪地の底', bowl, (f, k) => ({ player: { x: Math.sin(f * 0.02 * k) * 3, z: Math.cos(f * 0.02 * k) * 3 } }));

// --- ordinary movement, as a control ---------------------------------------
// Nothing here should ever trip: this is what the camera doing its job looks
// like, and if the caps flagged it the caps would be wrong.
// Flat open ground has nothing for the boom to pull in past, so any saturation
// at all is the camera fighting itself rather than the world.
scenario('走行（対照）', flatWorld, (f, k) => ({ player: { z: -f * 0.11 * k, isSprinting: true } }),
  120, { satMax: 0.02 });
// Rolling terrain the boom has to ride over: the pull-in is active every frame
// here, so it is the smoothness of the pull-in itself under test, not its onset.
// Gentle rises do briefly occlude, so this gets room the flat control does not.
scenario('起伏を走る（対照）', stubWorld((x, z) => Math.sin(z * 0.22) * 1.4),
  (f, k) => ({ player: { z: -f * 0.09 * k } }), 120, { satMax: 0.10 });

// --- can these criteria fail? -----------------------------------------------
//
// Every number above is a pass, and this project has learned twice over that a
// pass is a reason to check the instrument. The peak-rate criteria that this
// file has carried since it was written cannot fail at all: the boom's inward
// speed is clamped to CAM_BOOM_IN where it is applied, so six of the twelve
// scenarios report a dolly of exactly 7.00 m/s against a bound of 7.2, and have
// done every run. They were green throughout the two occasions the camera was
// actually broken.
//
// So the saturation criteria do not get to be believed on the strength of
// passing. Drive the camera through terrain built to pin the boom, and require
// that the number rises far enough to trip the bound. A criterion that cannot
// be made to fail on demand is not measuring anything.
function mustDetect(name, world, drive, frames, pick, floor) {
  const before = failures;
  const r = scenario(`${name}`, world, drive, frames, { satMax: 0.02 });
  // This scenario is *expected* to breach its bounds — that is the assertion.
  // But suppressing the whole verdict also suppresses anything else it breached,
  // and the corrugated case does breach ground clearance at -0.99 m. That is not
  // hidden: its wavelength is 3.70 m against a height field sampled every 4 m,
  // so it is terrain the world cannot express and the real-terrain check at the
  // bottom of this file is the one with authority on clearance.
  failures = before;
  const got = pick(r);
  const ok = got > floor;
  if (!ok) failures++;
  console.log(`  ${ok ? 'ok  ' : 'FAIL'} ${`↑ 上の指標が反応する`.padEnd(30)} ` +
    `張り付き ${(got * 100).toFixed(0)}% > 要求 ${(floor * 100).toFixed(0)}%` +
    `${ok ? '' : '  ← 悪いカメラを悪いと言えていない'}`);
}

console.log('\n指標そのものの検査 — 悪いカメラを与えたら反応するか');
// Ground that rises and falls faster than the boom can ride it, so `want` is
// never settled and the pull-in is re-triggered continuously. This is what a
// camera being dragged by the world looks like, and it is exactly the case the
// peak-rate criteria call a clean 7.00 m/s pass.
// Calibration, stated rather than assumed — and the dolly figure is the weaker
// of the two, which is worth saying out loud rather than leaving for someone to
// find. Across the flat control, rolling ground, the wall and this, the dolly
// fraction runs 0% / 4% / 7% / 12%. That is its whole range: the 50% default
// for non-control scenarios is nearly as inert as the peak-rate bound it
// replaced, and only the tight bounds on the two controls do any work.
//
// It was 23% here before the pitch floor landed. The range shrank because the
// camera stopped thrashing the boom, which is the metric behaving correctly and
// also a warning: a threshold fitted to yesterday's engine measures yesterday's
// engine. The real check on a camera dragged by terrain is now the real-terrain
// clearance test at the bottom of this file, which is direct rather than
// circumstantial.
mustDetect('荒れ地を全力疾走', stubWorld((x, z) => Math.max(0, Math.sin(z * 1.7) * 3.2)),
  (f, k) => ({ player: { z: -f * 0.16 * k, isSprinting: true } }), 240,
  (r) => r.dollyFrac, 0.08);
// A target that keeps moving to the far side of the player, so the yaw is asked
// for a fresh half-turn before the last one has landed.
const orbiter = { x: 0, y: 0, z: 0, height: 1.8 };
mustDetect('標的が周囲を回り続ける', flatWorld, (f, k) => {
  const a = f * 0.09 * k;
  orbiter.x = Math.sin(a) * 7; orbiter.z = Math.cos(a) * 7;
  return { lock: orbiter };
}, 240, (r) => r.swingFrac, 0.25);

// --- the real world, at its worst ------------------------------------------
//
// Every scenario above uses a stub height field, which is what makes them fast
// and also what makes them arguable: a camera failure on sin(z*1.7)*3.2 invites
// the answer "the world never does that". So bake the actual world and drive
// the camera over the steepest ground in it. Nothing here is invented, so
// nothing here can be dismissed.
//
// This found the defect the stubs could not settle: the eye sat 3.086 m
// underground at (-920, -732) on a gradient of 3.5, because the boom cannot get
// shorter than CAM_MIN_BOOM and at that length it is inside the hill for its
// whole length. An eye inside a hill renders a frame with no geometry in it,
// which is the failure that once measured surface detail of exactly 0 on four
// of six scenes — found then by a frame statistic, four axes away from its
// cause. This is that cause, measured directly.
{
  const { World, GRID, GRID_STEP } = await import('../src/world/worldgen.js');
  const world = new World('aldrath');
  for (const _ of world.generate()) { /* bake */ }

  // The steepest cells, not one lucky spot.
  const cells = [];
  const hf = world.height;
  for (let iz = 1; iz < GRID - 1; iz++) {
    for (let ix = 1; ix < GRID - 1; ix++) {
      const a = hf[iz * GRID + ix];
      const g = Math.max(Math.abs(hf[iz * GRID + ix + 1] - a),
        Math.abs(hf[(iz + 1) * GRID + ix] - a)) / GRID_STEP;
      cells.push([g, world.gridToWorld(ix), world.gridToWorld(iz)]);
    }
  }
  cells.sort((p, q) => q[0] - p[0]);

  // How far under the surface the eye is allowed to graze. CAM_SKIN is the
  // clearance the boom solve keeps, so anything inside it is the eye brushing
  // the ground rather than being in it — which is what a camera on a 77-degree
  // slope does in every game that has one.
  const GRAZE = 0.42;
  let worstClear = Infinity, worstAt = null, worstGrade = 0;
  for (const [g, cx, cz] of cells.slice(0, 40)) {
    for (const dir of [[0, 1], [0, -1], [1, 0], [-1, 0]]) {
      const player = { x: cx, y: 0, z: cz, yaw: 0, height: 1.8, isSprinting: true };
      const cam = new PlayerCamera(player);
      cam.shakeT = 0; cam.shakeAmp = 0;
      const DT = 1 / 60;
      for (let f = 0; f < 200; f++) {
        const t = (f - 60) / 60 * 6;          // sprint through, entering 6 m out
        player.x = cx + dir[0] * t; player.z = cz + dir[1] * t;
        const ph = world.heightAt(player.x, player.z);
        player.y = Number.isFinite(ph) ? ph : 0;
        cam.update(DT, noLook, world, null);
        if (f < 60) continue;                  // settle
        const ground = world.heightAt(cam.pos.x, cam.pos.z);
        if (!Number.isFinite(ground)) continue;
        const clear = cam.pos.y - ground;
        if (clear < worstClear) { worstClear = clear; worstAt = [cx, cz]; worstGrade = g; }
      }
    }
  }
  const ok = worstClear > -GRAZE;
  if (!ok) failures++;
  console.log(`\n実地形 — 生成された世界で最も急な40地点を全力疾走`);
  console.log(`  ${ok ? 'ok  ' : 'FAIL'} ${'眼が地面に潜らない'.padEnd(30)} ` +
    `最小クリア ${worstClear.toFixed(3)} m (> ${-GRAZE}) @ ${JSON.stringify(worstAt)} 勾配 ${worstGrade.toFixed(2)}` +
    `${ok ? '' : '  ← 地面の中'}`);
}

console.log(failures ? `\n${failures} 件 不合格` : '\n全て合格');
process.exit(failures ? 1 : 0);
