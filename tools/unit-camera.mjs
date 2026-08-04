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
function scenario(name, world, drive, frames = 120) {
  let worstRate = 0, worstDollyRate = 0, minClear = Infinity;
  for (const fps of RATES) {
    const r = once(name, world, drive, Math.round(frames * fps / 60), 1 / fps);
    if (r.view > worstRate) worstRate = r.view;
    if (r.dolly > worstDollyRate) worstDollyRate = r.dolly;
    if (r.clear < minClear) minClear = r.clear;
  }
  const ok = worstRate <= VIEW_CAP && worstDollyRate <= DOLLY_CAP && minClear >= CLEARANCE_MIN;
  if (!ok) failures++;
  console.log(`  ${ok ? 'ok  ' : 'FAIL'} ${name.padEnd(30)} ` +
    `視線 ${worstRate.toFixed(2)} rad/s  ドリー ${worstDollyRate.toFixed(2)} m/s  ` +
    `地面クリア ${minClear.toFixed(2)} m`);
  return { worstRate, worstDollyRate, minClear };
}

function once(name, world, drive, frames, DT) {
  const player = stubPlayer();
  const cam = new PlayerCamera(player);
  cam.shakeT = 0; cam.shakeAmp = 0;   // shake is random by design; not the subject
  let prevDir = null, prevOrbit = null;
  let worstView = 0, worstOrbit = 0, atView = -1, atOrbit = -1;
  let minClear = Infinity;

  // Settle on the opening conditions first. A camera constructed at its
  // defaults spends its first frames arriving, and that is not a cut.
  const K = DT * 60;
  const first = drive(0, K) || {};
  Object.assign(player, first.player || {});
  player.y = world.heightAt(player.x, player.z);
  for (let w = 0; w < 40; w++) cam.update(DT, noLook, world, first.lock || null);

  for (let f = 0; f < frames; f++) {
    const d = drive(f, K) || {};
    Object.assign(player, d.player || {});
    // The player stands on the ground. Without this the body sinks into a rise
    // and the boom collides with terrain the player is supposedly inside.
    player.y = world.heightAt(player.x, player.z);
    cam.update(DT, noLook, world, d.lock || null);

    const vx = cam.look.x - cam.pos.x, vy = cam.look.y - cam.pos.y, vz = cam.look.z - cam.pos.z;
    const vl = Math.hypot(vx, vy, vz) || 1;
    const dir = [vx / vl, vy / vl, vz / vl];
    const orbit = Math.hypot(cam.pos.x - cam.focusX, cam.pos.y - cam.focusY, cam.pos.z - cam.focusZ);
    const clear = cam.pos.y - world.heightAt(cam.pos.x, cam.pos.z);
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
  return { view: worstView / DT, dolly: worstOrbit / DT, clear: minClear };
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
scenario('走行（対照）', flatWorld, (f, k) => ({ player: { z: -f * 0.11 * k, isSprinting: true } }));
// Rolling terrain the boom has to ride over: the pull-in is active every frame
// here, so it is the smoothness of the pull-in itself under test, not its onset.
scenario('起伏を走る（対照）', stubWorld((x, z) => Math.sin(z * 0.22) * 1.4),
  (f, k) => ({ player: { z: -f * 0.09 * k } }));

console.log(failures ? `\n${failures} 件 不合格` : '\n全て合格');
process.exit(failures ? 1 : 0);
