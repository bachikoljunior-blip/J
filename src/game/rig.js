// ============================================================================
//  rig.js — skeletons and procedural animation.
//
//  Every character is a hierarchy of boxes. There are no baked animation
//  clips: poses are functions of (state, phase, speed, look direction), which
//  means a wolf lunging and a knight recovering from a parry both read
//  correctly without a single keyframe file.
//
//  Convention: a bone's local +Y runs *along* the bone, and its box is drawn
//  from the joint to +len. A per-bone `bind` rotation orients the chain at
//  rest — limbs get a 180° bind so they hang downward, which makes every
//  animated rotation read the same way: positive X swings the limb forward,
//  negative swings it back and up. Child offsets are then always [0, parentLen, 0].
//
//  Poses are damped toward their target each frame rather than crossfaded
//  between clips. That gives free blending everywhere — the tricky
//  attack-into-dodge-into-run transitions come out smooth by construction —
//  and per-state damping rates let attacks stay snappy while idles stay soft.
//  On top of the damping there is a hard rate limit: no frame may swing any
//  bone's axis further than TURN_STEP, which is what makes "continuous" a
//  property of the rig rather than a property of whoever wrote the pose.
//
//  Then, every frame, after the pose:
//    * the hips find the ground — dropped by the leg that has furthest to
//      reach, tilted onto the slope, counter-rotated back out of the shoulders
//    * both legs are solved analytically so the soles land on the height field
//      instead of on the plane the pelvis happens to be floating over
//    * the body lags itself: torso, head and cloak trail sudden changes in
//      velocity, so stopping takes a beat and a direction change whips
//    * the head and chest turn toward whatever the actor should be watching
//    * breath, weight shift and small settles are added over all of it
//  None of these are poses. They are what the difference is between a pose and
//  a body wearing one.
// ============================================================================

import { clamp, saturate, damp, MAX_DT } from '../core/math.js';
import { MATERIAL as SURFACE } from '../gfx/textures.js';
import { CHAR_PART } from '../gfx/mesh.js';
import { additiveIdle } from './anim.js';

const PI = Math.PI;

// Nothing may turn further than this in one frame, or faster than this per
// second, whichever binds first. The per-frame cap is what stops a pose change
// from arriving as a jump-cut on a slow device; the per-second cap is what
// keeps a fast attack fast on a quick one.
const TURN_RATE = 17;    // rad/s — the bound that actually governs
// Backstops, not limits. Each is its rate over the longest frame the loop will
// hand out, so it cannot bind while dt is clamped — it only catches a
// regression in that clamp. Set any of them lower and the engine turns, plants
// and steps more slowly on a slow device, which is a gameplay difference rather
// than a visual one.
const TURN_STEP = TURN_RATE * MAX_DT;   // rad/frame

// How fast the ground solver takes hold of a foot, and lets go of one, in
// weight per second. Asymmetric on purpose: a pose that lifts a foot has
// already lifted it and the solver must get out of the way at once, while a
// foot coming back down should be set down over a few frames rather than
// teleported onto the terrain the instant the roll ends.
const PLANT_ENGAGE = 7.0;
const PLANT_RELEASE = 40.0;

// How far above the ground sample a sole is planted. Not zero: a foot pinned
// exactly to a bilinear height field reads as sunk, and the sole has thickness.
const SOLE_LIFT = 0.02;

// How fast the ground correction itself may move, in metres of foot travel per
// second and per frame. The pose limiter above cannot see this one — a foot
// correction is not a rotation — so it gets its own budget, sized so that the
// worst case (a leg let go of the ground by a roll, then handed back to the
// solver a metre above it) comes in over a few frames instead of on one.
const IK_SLEW = 1.6;     // m/s
const IK_STEP = IK_SLEW * MAX_DT;    // m/frame
// The same argument for the contact weight, which scales how far the sole is
// laid onto the slope: handing a foot back to the solver is a rotation too.
const PLANT_SLEW = 7;      // 1/s
const PLANT_STEP = PLANT_SLEW * MAX_DT;  // per frame

// Look-at limits. Past LOOK_YAW the neck would invert, so the gaze is released
// instead of twisted.
const LOOK_YAW = 1.15;
const LOOK_PITCH = 0.55;
const LOOK_RANGE = 18;

// Inertia. Underdamped on purpose: a body that stops moving does not stop
// instantly, it overshoots once and settles, and that beat is most of what
// separates a character from a diagram. ~10 rad/s, damping ratio ~0.6.
const SWAY_K = 105;
const SWAY_C = 12.4;
const SWAY_PITCH = 0.55;   // radians of torso lean per metre of lag
const SWAY_ROLL = 0.50;
const TRAIL_PITCH = 1.60;  // cloaks and tails travel much further
const TRAIL_ROLL = 1.30;

// Which primitive a bone is drawn with, and — since the name is also the batch
// name — which draw call it lands in. Bones that name nothing get the box, so
// an unconverted rig still renders.
export const PART = CHAR_PART;

// ---------------------------------------------------------------------------
//  The world a rig is standing in
//
//  Two of the layers above need something no bone hierarchy can reach: the feet
//  need the height field under them, and the eyes need somebody to look at.
//  Rigs are built deep inside actors that never hand either one down, and a
//  rig is not a scene graph node — it has no parent to ask. So the source is
//  registered once, for the process.
//
//  Until a host registers one we read it off the running game, which main.js
//  publishes. That is one global read instead of threading a world reference
//  through every constructor between here and there; bindWorldSource is the
//  seam for anyone who needs it done properly — a test harness, a model
//  viewer, a second world.
// ---------------------------------------------------------------------------

let hostSource = null;
let autoSource = null;
let autoFrom = null;

/**
 * Tell every rig which world it stands in and who is in it.
 * @param {?{heightAt: function(number, number): number,
 *           gazeNear?: function(number, number, number): ?object}} src
 */
export function bindWorldSource(src) {
  hostSource = src || null;
}

/** Nearest living body to a point, ignoring whoever is standing on it. */
function nearestActor(g, x, z, maxDist) {
  // Whoever is asking is standing at (x, z), so anything inside half a metre
  // is the looker itself.
  const lock = g.player && g.player.lockTarget;
  if (lock && !lock.dead) {
    const px = g.player.x - x, pz = g.player.z - z;
    if (px * px + pz * pz < 0.36) return lock;
  }
  let best = null;
  let bestD = maxDist * maxDist;
  const list = g.enemies;
  const consider = (a) => {
    if (!a || a.dead || a.visible === false) return;
    const dx = a.x - x, dz = a.z - z;
    const d2 = dx * dx + dz * dz;
    if (d2 < 0.36 || d2 >= bestD) return;
    bestD = d2; best = a;
  };
  consider(g.player);
  if (list) for (let i = 0; i < list.length; i++) consider(list[i]);
  return best;
}

function worldSource() {
  if (hostSource) return hostSource;
  const g = typeof globalThis !== 'undefined' ? globalThis.__g : null;
  if (!g || !g.world || typeof g.world.heightAt !== 'function') return null;
  if (g !== autoFrom) {
    autoFrom = g;
    // Read g.world through the game every call: a new world can be generated
    // under a live game, and a stale height field is worse than none.
    autoSource = {
      heightAt: (x, z) => g.world.heightAt(x, z),
      gazeNear: (x, z, maxDist) => nearestActor(g, x, z, maxDist),
    };
  }
  return autoSource;
}

// ---------------------------------------------------------------------------
//  3x3 helpers (column-major, matching the instance attribute layout)
// ---------------------------------------------------------------------------

function mat3Identity(o) {
  o[0] = 1; o[1] = 0; o[2] = 0;
  o[3] = 0; o[4] = 1; o[5] = 0;
  o[6] = 0; o[7] = 0; o[8] = 1;
  return o;
}

function mat3RotXYZ(o, rx, ry, rz) {
  const cx = Math.cos(rx), sx = Math.sin(rx);
  const cy = Math.cos(ry), sy = Math.sin(ry);
  const cz = Math.cos(rz), sz = Math.sin(rz);
  // R = Ry * Rx * Rz — yaw outermost keeps limb twist intuitive.
  const m00 = cy * cz + sy * sx * sz;
  const m01 = cx * sz;
  const m02 = -sy * cz + cy * sx * sz;
  const m10 = -cy * sz + sy * sx * cz;
  const m11 = cx * cz;
  const m12 = sy * sz + cy * sx * cz;
  const m20 = sy * cx;
  const m21 = -sx;
  const m22 = cy * cx;
  o[0] = m00; o[1] = m10; o[2] = m20;
  o[3] = m01; o[4] = m11; o[5] = m21;
  o[6] = m02; o[7] = m12; o[8] = m22;
  return o;
}

function mat3Mul(o, a, b) {
  const a0 = a[0], a1 = a[1], a2 = a[2], a3 = a[3], a4 = a[4], a5 = a[5], a6 = a[6], a7 = a[7], a8 = a[8];
  const b0 = b[0], b1 = b[1], b2 = b[2], b3 = b[3], b4 = b[4], b5 = b[5], b6 = b[6], b7 = b[7], b8 = b[8];
  o[0] = a0 * b0 + a3 * b1 + a6 * b2;
  o[1] = a1 * b0 + a4 * b1 + a7 * b2;
  o[2] = a2 * b0 + a5 * b1 + a8 * b2;
  o[3] = a0 * b3 + a3 * b4 + a6 * b5;
  o[4] = a1 * b3 + a4 * b4 + a7 * b5;
  o[5] = a2 * b3 + a5 * b4 + a8 * b5;
  o[6] = a0 * b6 + a3 * b7 + a6 * b8;
  o[7] = a1 * b6 + a4 * b7 + a7 * b8;
  o[8] = a2 * b6 + a5 * b7 + a8 * b8;
  return o;
}

function mat3Apply(m, x, y, z, out) {
  out[0] = m[0] * x + m[3] * y + m[6] * z;
  out[1] = m[1] * x + m[4] * y + m[7] * z;
  out[2] = m[2] * x + m[5] * y + m[8] * z;
  return out;
}

/** o[oi..] = a[ai..] * b[bi..], for matrices living inside flat pose arrays. */
function mat3MulAt(o, oi, a, ai, b, bi) {
  const a0 = a[ai], a1 = a[ai + 1], a2 = a[ai + 2];
  const a3 = a[ai + 3], a4 = a[ai + 4], a5 = a[ai + 5];
  const a6 = a[ai + 6], a7 = a[ai + 7], a8 = a[ai + 8];
  const b0 = b[bi], b1 = b[bi + 1], b2 = b[bi + 2];
  const b3 = b[bi + 3], b4 = b[bi + 4], b5 = b[bi + 5];
  const b6 = b[bi + 6], b7 = b[bi + 7], b8 = b[bi + 8];
  o[oi] = a0 * b0 + a3 * b1 + a6 * b2;
  o[oi + 1] = a1 * b0 + a4 * b1 + a7 * b2;
  o[oi + 2] = a2 * b0 + a5 * b1 + a8 * b2;
  o[oi + 3] = a0 * b3 + a3 * b4 + a6 * b5;
  o[oi + 4] = a1 * b3 + a4 * b4 + a7 * b5;
  o[oi + 5] = a2 * b3 + a5 * b4 + a8 * b5;
  o[oi + 6] = a0 * b6 + a3 * b7 + a6 * b8;
  o[oi + 7] = a1 * b6 + a4 * b7 + a7 * b8;
  o[oi + 8] = a2 * b6 + a5 * b7 + a8 * b8;
  return o;
}

/**
 * Write the world basis of a bone that points along `y`, with the reference
 * direction `f` (the side the joint bends toward) taken as its front.
 *
 * The rig's frame convention, read off a resting limb: +Y runs down the bone
 * and +Z points out its back, so the knee — the front — is -Z, and X closes
 * the right-handed triple as Y × Z.
 */
function boneFrameAt(out, o, yx, yy, yz, fx, fy, fz) {
  // Front, made perpendicular to the bone.
  const d = fx * yx + fy * yy + fz * yz;
  let zx = -(fx - yx * d), zy = -(fy - yy * d), zz = -(fz - yz * d);
  let l = Math.hypot(zx, zy, zz);
  if (l < 1e-5) {
    // Bone is pointing straight along the reference: any perpendicular will do.
    zx = -yy; zy = yx; zz = 0;
    l = Math.hypot(zx, zy, zz);
    if (l < 1e-5) { zx = 1; zy = 0; zz = 0; l = 1; }
  }
  zx /= l; zy /= l; zz /= l;
  out[o + 3] = yx; out[o + 4] = yy; out[o + 5] = yz;
  out[o + 6] = zx; out[o + 7] = zy; out[o + 8] = zz;
  out[o] = yy * zz - yz * zy;
  out[o + 1] = yz * zx - yx * zz;
  out[o + 2] = yx * zy - yy * zx;
}

// A leg is never asked to reach further than this fraction of its own length.
// The last three per cent is the difference between a leg and a strut.
const LEG_REACH = 0.97;

/**
 * Two-bone analytic IK, straight into world transforms.
 *
 * Places the tip of the lower bone on (tx, ty, tz) and bends the joint toward
 * `p`. The caller guarantees the target is inside reach, so there is nothing to
 * fudge here: the solve is exact, which is what lets the sole land on the same
 * height sample the target was taken from.
 *
 * Each bone keeps the twist it came in with. The pole decides which way the
 * knee points and nothing else — using it as the twist reference as well makes
 * the roll of a bone depend on the angle between two things that are nearly
 * parallel whenever a leg is tucked, and a shin whose twist jitters takes the
 * whole foot with it. Referencing each bone's own front is stable by
 * construction: a solve with nothing to correct leaves the bone where it was.
 */
function solveLeg(wr, wp, ui, li, L1, L2, hx, hy, hz, tx, ty, tz, px, py, pz) {
  const ufx = -wr[ui * 9 + 6], ufy = -wr[ui * 9 + 7], ufz = -wr[ui * 9 + 8];
  const lfx = -wr[li * 9 + 6], lfy = -wr[li * 9 + 7], lfz = -wr[li * 9 + 8];
  let vx = tx - hx, vy = ty - hy, vz = tz - hz;
  let d = Math.hypot(vx, vy, vz);
  if (d < 1e-5) { vx = 0; vy = -1; vz = 0; d = 1e-5; } else { vx /= d; vy /= d; vz /= d; }
  const dc = clamp(d, Math.abs(L1 - L2) + 1e-3, (L1 + L2) - 1e-4);

  // Angle between the upper bone and the line to the target.
  const a = Math.acos(clamp((L1 * L1 + dc * dc - L2 * L2) / (2 * L1 * dc), -1, 1));
  const ca = Math.cos(a), sa = Math.sin(a);

  // Bend plane: the part of the pole that is perpendicular to that line.
  const pd = px * vx + py * vy + pz * vz;
  let qx = px - vx * pd, qy = py - vy * pd, qz = pz - vz * pd;
  let ql = Math.hypot(qx, qy, qz);
  if (ql < 1e-5) {
    qx = -vy; qy = vx; qz = 0;
    ql = Math.hypot(qx, qy, qz);
    if (ql < 1e-5) { qx = 1; qy = 0; qz = 0; ql = 1; }
  }
  qx /= ql; qy /= ql; qz /= ql;

  const ux = vx * ca + qx * sa, uy = vy * ca + qy * sa, uz = vz * ca + qz * sa;
  const kx = hx + ux * L1, ky = hy + uy * L1, kz = hz + uz * L1;
  let lx = tx - kx, ly = ty - ky, lz = tz - kz;
  const ll = Math.hypot(lx, ly, lz) || 1;
  lx /= ll; ly /= ll; lz /= ll;

  boneFrameAt(wr, ui * 9, ux, uy, uz, ufx, ufy, ufz);
  boneFrameAt(wr, li * 9, lx, ly, lz, lfx, lfy, lfz);
  wp[li * 3] = kx; wp[li * 3 + 1] = ky; wp[li * 3 + 2] = kz;
}

// ---------------------------------------------------------------------------
//  Materials
// ---------------------------------------------------------------------------

export const MAT = {
  SKIN: 0, CLOTH: 1, ARMOR: 2, LEATHER: 3, HAIR: 4, ACCENT: 5, METAL: 6, DARK: 7,
};

// Which surface each palette slot is made of. The palette says what colour a
// bone is; this says what it is *made of*, which is what decides whether the
// sun glances off it or sinks into it.
export const MAT_SURFACE = [
  SURFACE.SKIN,     // SKIN
  SURFACE.CLOTH,    // CLOTH
  SURFACE.METAL,    // ARMOR
  SURFACE.LEATHER,  // LEATHER
  SURFACE.CLOTH,    // HAIR — fibrous, matte
  SURFACE.CLOTH,    // ACCENT — sashes, tabards
  SURFACE.METAL,    // METAL
  SURFACE.LEATHER,  // DARK
];

// Bone tuple: [name, parentName|null, offset, len, w, d, mat, bind?, part?]
// Parents are named rather than indexed so inserting a bone can never silently
// re-parent the ones after it. `part` names the primitive — and therefore the
// batch — the bone is drawn with; omitting it gives the bevelled box.
const DOWN = [PI, 0, 0];        // hangs from the joint
const FORWARD = [PI / 2, 0, 0]; // points along the parent's forward axis

const LIMB = PART.LIMB;
const TORSO = PART.TORSO;
const SKULL = PART.SKULL;
const DOME = PART.PAULDRON;
const PLATE = PART.PLATE;

export const HUMANOID = {
  name: 'humanoid',
  // Has to be what the legs can actually reach: thigh + shin, less the joint
  // offset, plus a few centimetres of knee. Standing a skeleton higher than
  // its own legs used to be free — the feet were placed on the hip plane and
  // nobody asked the ground. Now the solver would spend its whole budget
  // pulling the body back down to where its feet already are.
  hipHeight: 0.80,
  bones: [
    ['pelvis', null, [0, 0, 0], 0.19, 0.335, 0.225, MAT.ARMOR, null, TORSO],
    ['tasset', 'pelvis', [0, 0.015, 0], 0.24, 0.375, 0.265, MAT.LEATHER, DOWN, PLATE],
    // A belt breaks the trunk in two, which is most of what makes a waist read.
    ['belt', 'pelvis', [0, 0.150, 0], 0.062, 0.385, 0.275, MAT.LEATHER],
    ['spine', 'pelvis', [0, 0.18, 0], 0.23, 0.355, 0.235, MAT.ARMOR, null, TORSO],
    ['chest', 'spine', [0, 0.22, 0], 0.27, 0.445, 0.275, MAT.ARMOR, null, TORSO],
    ['neck', 'chest', [0, 0.265, 0], 0.07, 0.125, 0.125, MAT.SKIN, null, LIMB],
    ['head', 'neck', [0, 0.07, 0], 0.255, 0.230, 0.250, MAT.SKIN, null, SKULL],
    ['hair', 'head', [0, 0.155, -0.012], 0.13, 0.255, 0.27, MAT.HAIR, null, SKULL],
    // Helm, visor and crest replace the bare head when a head slot is filled.
    ['helm', 'neck', [0, 0.055, 0], 0.285, 0.265, 0.285, MAT.ARMOR, null, SKULL],
    ['visor', 'helm', [0, 0.125, 0.125], 0.06, 0.20, 0.055, MAT.DARK, null, PLATE],
    ['crest', 'helm', [0, 0.275, -0.02], 0.13, 0.05, 0.22, MAT.ACCENT, null, PLATE],

    // Pauldrons, not cubes: the dome is what says "soldier" from far enough
    // away that nothing else about the character is legible.
    ['shoulderL', 'chest', [0.222, 0.230, 0], 0.135, 0.235, 0.225, MAT.ARMOR, DOWN, DOME],
    ['upperArmL', 'shoulderL', [0, 0.09, 0], 0.26, 0.135, 0.135, MAT.CLOTH, null, LIMB],
    ['forearmL', 'upperArmL', [0, 0.26, 0], 0.24, 0.115, 0.115, MAT.SKIN, null, LIMB],
    ['gloveL', 'forearmL', [0, 0.170, 0], 0.085, 0.132, 0.132, MAT.LEATHER, null, LIMB],
    ['handL', 'forearmL', [0, 0.24, 0], 0.10, 0.105, 0.135, MAT.SKIN, null, LIMB],

    ['shoulderR', 'chest', [-0.222, 0.230, 0], 0.135, 0.235, 0.225, MAT.ARMOR, DOWN, DOME],
    ['upperArmR', 'shoulderR', [0, 0.09, 0], 0.26, 0.135, 0.135, MAT.CLOTH, null, LIMB],
    ['forearmR', 'upperArmR', [0, 0.26, 0], 0.24, 0.115, 0.115, MAT.SKIN, null, LIMB],
    ['gloveR', 'forearmR', [0, 0.170, 0], 0.085, 0.132, 0.132, MAT.LEATHER, null, LIMB],
    ['handR', 'forearmR', [0, 0.24, 0], 0.10, 0.105, 0.135, MAT.SKIN, null, LIMB],

    ['thighL', 'pelvis', [0.108, 0.03, 0], 0.40, 0.175, 0.185, MAT.LEATHER, DOWN, LIMB],
    ['shinL', 'thighL', [0, 0.40, 0], 0.38, 0.142, 0.152, MAT.LEATHER, null, LIMB],
    // The boot shaft is a separate segment so the leg reads as leg-then-boot
    // rather than as one tapering stick.
    ['bootL', 'shinL', [0, 0.155, 0], 0.245, 0.168, 0.178, MAT.DARK, null, LIMB],
    ['footL', 'shinL', [0, 0.38, 0], 0.245, 0.150, 0.115, MAT.DARK, FORWARD, PLATE],

    ['thighR', 'pelvis', [-0.108, 0.03, 0], 0.40, 0.175, 0.185, MAT.LEATHER, DOWN, LIMB],
    ['shinR', 'thighR', [0, 0.40, 0], 0.38, 0.142, 0.152, MAT.LEATHER, null, LIMB],
    ['bootR', 'shinR', [0, 0.155, 0], 0.245, 0.168, 0.178, MAT.DARK, null, LIMB],
    ['footR', 'shinR', [0, 0.38, 0], 0.245, 0.150, 0.115, MAT.DARK, FORWARD, PLATE],

    // Two segments so the cloak can actually bend and trail.
    ['cape', 'chest', [0, 0.255, -0.135], 0.40, 0.36, 0.035, MAT.ACCENT, DOWN, PLATE],
    ['capeLower', 'cape', [0, 0.40, 0], 0.44, 0.31, 0.03, MAT.ACCENT, null, PLATE],
  ],
  // Hidden until something turns them on (a head slot being filled).
  optional: ['helm', 'visor', 'crest'],
  handR: 'handR',
  handL: 'handL',
  head: 'head',
  chest: 'chest',

  // --- what the solvers need to know about this body -----------------------
  // Which euler slot means what in this rig's frame. Torso bones here stand
  // with +Y up, so ry turns the body and rz leans it.
  axes: { pitch: 0, yaw: 1, roll: 2, yawSign: -1 },
  // Where a turn of the gaze is spent — furthest from the eyes first, so the
  // chest starts the turn and the head finishes it.
  gaze: [['chest', 0.22], ['neck', 0.30], ['head', 0.48]],
  // What lags when the hips change speed, and by how much.
  sway: [['spine', 0.55], ['chest', 0.42], ['neck', 0.30], ['head', 0.26]],
  // How far the hips lie down onto the slope they are standing on, and what
  // takes that tilt back out again so the shoulders stay level.
  bodyTilt: 0.45,
  hipCounter: [['spine', -0.55], ['chest', -0.32]],
  // What keeps going after the body has stopped.
  trail: [['cape', 1.0], ['capeLower', 1.45]],
  // Legs solved onto the ground. The contact point is the tip of the lower
  // bone, which is exactly where the foot is jointed.
  legs: [
    { upper: 'thighL', lower: 'shinL', sole: 'footL' },
    { upper: 'thighR', lower: 'shinR', sole: 'footR' },
  ],
  stance: 0.17,
};

// The quadruped's root is pitched so the body lies along the forward axis;
// inside that frame +Y is forward, +Z is down and +X is to the right.
const QUAD_DOWN = [-PI / 2, 0, 0];
const QUAD_BACK = [PI, 0, 0];

export const QUADRUPED = {
  name: 'quadruped',
  hipHeight: 0.66,
  rootPitch: -PI / 2,
  bones: [
    ['core', null, [0, 0, 0], 0.48, 0.34, 0.32, MAT.CLOTH, null, TORSO],
    ['chest', 'core', [0, 0.46, 0], 0.30, 0.37, 0.35, MAT.CLOTH, null, TORSO],
    ['neck', 'chest', [0, 0.28, -0.09], 0.24, 0.21, 0.21, MAT.CLOTH, null, LIMB],
    ['head', 'neck', [0, 0.23, 0], 0.22, 0.22, 0.24, MAT.CLOTH, null, SKULL],
    ['snout', 'head', [0, 0.19, 0.05], 0.17, 0.14, 0.15, MAT.DARK, null, LIMB],
    ['earL', 'head', [0.085, 0.15, -0.09], 0.14, 0.07, 0.05, MAT.DARK, [-0.5, 0, 0], PLATE],
    ['earR', 'head', [-0.085, 0.15, -0.09], 0.14, 0.07, 0.05, MAT.DARK, [-0.5, 0, 0], PLATE],
    ['tail', 'core', [0, -0.02, -0.08], 0.42, 0.10, 0.10, MAT.CLOTH, QUAD_BACK, LIMB],

    ['legFL', 'chest', [0.165, 0.14, 0.06], 0.32, 0.11, 0.11, MAT.CLOTH, QUAD_DOWN, LIMB],
    ['footFL', 'legFL', [0, 0.32, 0], 0.30, 0.105, 0.14, MAT.DARK, null, PLATE],
    ['legFR', 'chest', [-0.165, 0.14, 0.06], 0.32, 0.11, 0.11, MAT.CLOTH, QUAD_DOWN, LIMB],
    ['footFR', 'legFR', [0, 0.32, 0], 0.30, 0.105, 0.14, MAT.DARK, null, PLATE],
    ['legBL', 'core', [0.165, 0.08, 0.06], 0.32, 0.13, 0.13, MAT.CLOTH, QUAD_DOWN, LIMB],
    ['footBL', 'legBL', [0, 0.32, 0], 0.30, 0.115, 0.15, MAT.DARK, null, PLATE],
    ['legBR', 'core', [-0.165, 0.08, 0.06], 0.32, 0.13, 0.13, MAT.CLOTH, QUAD_DOWN, LIMB],
    ['footBR', 'legBR', [0, 0.32, 0], 0.30, 0.115, 0.15, MAT.DARK, null, PLATE],
  ],
  head: 'head',
  chest: 'chest',

  // Inside the pitched root frame ry rolls the body and rz turns it — the
  // mirror image of the humanoid, which is why the axis map exists at all.
  axes: { pitch: 0, yaw: 2, roll: 1, yawSign: 1 },
  gaze: [['neck', 0.45], ['head', 0.55]],
  sway: [['core', 0.30], ['neck', 0.48], ['head', 0.30]],
  trail: [['tail', 1.0]],
  // A tail is hinged across the body, not fore and aft: most of what it does
  // with the body's inertia it does sideways.
  trailPitch: 0.45,
  legs: [
    { upper: 'legFL', lower: 'footFL' },
    { upper: 'legFR', lower: 'footFR' },
    { upper: 'legBL', lower: 'footBL' },
    { upper: 'legBR', lower: 'footBR' },
  ],
  // A metre of body between the front and back feet: a wolf crossing a bank
  // pitches with it long before its legs run out of travel.
  stance: 0.55,
  bodyTilt: 0.85,
};

export const WINGED = {
  name: 'winged',
  hipHeight: 1.30,
  rootPitch: -PI / 2,
  bones: [
    ['core', null, [0, 0, 0], 0.78, 0.58, 0.54, MAT.ARMOR, null, TORSO],
    ['chest', 'core', [0, 0.74, 0], 0.46, 0.62, 0.58, MAT.ARMOR, null, TORSO],
    ['neck', 'chest', [0, 0.44, -0.16], 0.42, 0.26, 0.26, MAT.ARMOR, null, LIMB],
    ['head', 'neck', [0, 0.40, 0], 0.30, 0.30, 0.34, MAT.ARMOR, null, SKULL],
    ['jaw', 'head', [0, 0.22, 0.10], 0.24, 0.26, 0.16, MAT.DARK, null, PLATE],
    ['hornL', 'head', [0.13, 0.16, -0.14], 0.34, 0.08, 0.08, MAT.DARK, [-0.8, 0, 0], LIMB],
    ['hornR', 'head', [-0.13, 0.16, -0.14], 0.34, 0.08, 0.08, MAT.DARK, [-0.8, 0, 0], LIMB],
    ['tail', 'core', [0, -0.04, -0.10], 0.80, 0.21, 0.21, MAT.ARMOR, QUAD_BACK, LIMB],
    ['tailTip', 'tail', [0, 0.80, 0], 0.62, 0.13, 0.13, MAT.DARK, null, LIMB],

    ['wingL0', 'chest', [0.32, 0.30, -0.22], 0.92, 0.14, 0.10, MAT.LEATHER, [-1.15, 0, 0.9], LIMB],
    ['wingL1', 'wingL0', [0, 0.92, 0], 1.10, 0.84, 0.05, MAT.LEATHER, null, PLATE],
    ['wingR0', 'chest', [-0.32, 0.30, -0.22], 0.92, 0.14, 0.10, MAT.LEATHER, [-1.15, 0, -0.9], LIMB],
    ['wingR1', 'wingR0', [0, 0.92, 0], 1.10, 0.84, 0.05, MAT.LEATHER, null, PLATE],

    ['legFL', 'chest', [0.30, 0.22, 0.10], 0.50, 0.17, 0.17, MAT.ARMOR, QUAD_DOWN, LIMB],
    ['footFL', 'legFL', [0, 0.50, 0], 0.44, 0.16, 0.22, MAT.DARK, null, PLATE],
    ['legFR', 'chest', [-0.30, 0.22, 0.10], 0.50, 0.17, 0.17, MAT.ARMOR, QUAD_DOWN, LIMB],
    ['footFR', 'legFR', [0, 0.50, 0], 0.44, 0.16, 0.22, MAT.DARK, null, PLATE],
    ['legBL', 'core', [0.30, 0.10, 0.10], 0.56, 0.20, 0.20, MAT.ARMOR, QUAD_DOWN, LIMB],
    ['footBL', 'legBL', [0, 0.56, 0], 0.48, 0.18, 0.24, MAT.DARK, null, PLATE],
    ['legBR', 'core', [-0.30, 0.10, 0.10], 0.56, 0.20, 0.20, MAT.ARMOR, QUAD_DOWN, LIMB],
    ['footBR', 'legBR', [0, 0.56, 0], 0.48, 0.18, 0.24, MAT.DARK, null, PLATE],
  ],
  head: 'head',
  chest: 'chest',

  axes: { pitch: 0, yaw: 2, roll: 1, yawSign: 1 },
  gaze: [['neck', 0.40], ['head', 0.60]],
  sway: [['core', 0.22], ['neck', 0.40], ['head', 0.28]],
  trail: [['tail', 0.9], ['tailTip', 1.35]],
  trailPitch: 0.45,
  // No ground solve: a drake spends half its life in the air and its stance is
  // deliberately tall. Pinning those feet to the terrain would fight every
  // flight pose it has, and land it on a slope like a table.
  legs: [],
  stance: 0.70,
};

const TEMPLATE_CACHE = new Map();

/**
 * The skeleton with every animated rotation at zero, in the root's own frame.
 *
 * The ground solver needs it for one number per leg: where that leg's contact
 * point sits when nothing is moving. That plane is what animation lift is
 * measured against, so a stride keeps its shape while the ground under it is
 * corrected. Derived rather than declared — a template with longer legs is
 * still described correctly by its own bones.
 */
function restLayout(bones, rootPitch) {
  const n = bones.length;
  const rot = new Float32Array(n * 9);
  const pos = new Float32Array(n * 3);
  const root = new Float32Array(9);
  mat3RotXYZ(root, rootPitch || 0, 0, 0);
  const v = [0, 0, 0];
  for (let i = 0; i < n; i++) {
    const b = bones[i];
    const o = i * 9;
    if (b.parent < 0) {
      if (b.hasBind) mat3MulAt(rot, o, root, 0, b.bind, 0);
      else for (let k = 0; k < 9; k++) rot[o + k] = root[k];
    } else {
      const p = b.parent * 9;
      if (b.hasBind) mat3MulAt(rot, o, rot, p, b.bind, 0);
      else for (let k = 0; k < 9; k++) rot[o + k] = rot[p + k];
      v[0] = rot[p] * b.offset[0] + rot[p + 3] * b.offset[1] + rot[p + 6] * b.offset[2];
      v[1] = rot[p + 1] * b.offset[0] + rot[p + 4] * b.offset[1] + rot[p + 7] * b.offset[2];
      v[2] = rot[p + 2] * b.offset[0] + rot[p + 5] * b.offset[1] + rot[p + 8] * b.offset[2];
      pos[i * 3] = pos[b.parent * 3] + v[0];
      pos[i * 3 + 1] = pos[b.parent * 3 + 1] + v[1];
      pos[i * 3 + 2] = pos[b.parent * 3 + 2] + v[2];
    }
  }
  return { rot, pos };
}

function compile(template) {
  if (TEMPLATE_CACHE.has(template)) return TEMPLATE_CACHE.get(template);
  const byName = new Map();
  template.bones.forEach((b, i) => byName.set(b[0], i));

  const bones = template.bones.map((b, i) => {
    const bind = b[7];
    const bindMat = new Float32Array(9);
    if (bind) mat3RotXYZ(bindMat, bind[0], bind[1], bind[2]);
    else mat3Identity(bindMat);
    let parent = -1;
    if (b[1] !== null && b[1] !== undefined) {
      parent = byName.has(b[1]) ? byName.get(b[1]) : -1;
      if (parent < 0) throw new Error(`rig ${template.name}: unknown parent "${b[1]}" for bone "${b[0]}"`);
      if (parent >= i) throw new Error(`rig ${template.name}: bone "${b[0]}" must come after its parent`);
    }
    return {
      index: i,
      name: b[0],
      parent,
      offset: b[2],
      len: b[3],
      w: b[4],
      d: b[5],
      mat: b[6],
      bind: bindMat,
      hasBind: !!bind,
      part: b[8] || PART.BOX,
    };
  });
  // Resolve every name the solvers use once, here, rather than hashing strings
  // thirty times a frame per character.
  const idx = (name) => {
    const i = byName.get(name);
    return i === undefined ? -1 : i;
  };
  const pairs = (list) => (list || [])
    .map(([name, gain]) => [idx(name), gain])
    .filter((e) => e[0] >= 0);

  const rest = restLayout(bones, template.rootPitch || 0);
  const rootIndex = bones.findIndex((b) => b.parent < 0);
  // Which way is up, expressed inside the root bone so it survives the root
  // bone being rotated. The quadruped's root lies along its own spine, so "up"
  // there is not the Y axis and the ground solver cannot assume it is.
  const rr = rootIndex * 9;
  const restUp = rootIndex < 0 ? [0, 1, 0]
    : [rest.rot[rr + 1], rest.rot[rr + 4], rest.rot[rr + 7]];
  const legChains = [];
  for (const spec of template.legs || []) {
    const upper = idx(spec.upper), lower = idx(spec.lower);
    if (upper < 0 || lower < 0) continue;
    // The contact point is the tip of the lower bone: for a humanoid that is
    // exactly where the foot is jointed, for a quadruped it is the toe.
    const restY = rest.pos[lower * 3 + 1] + rest.rot[lower * 9 + 4] * bones[lower].len;
    // How far below its own hip the contact point hangs at rest. Lift is
    // measured against *that*, not against the body, so tilting the hips onto
    // a slope does not read as the animation picking the foot up.
    legChains.push({
      upper, lower, sole: idx(spec.sole || ''),
      restDrop: restY - (rootIndex < 0 ? 0 : rest.pos[rootIndex * 3 + 1]),
    });
  }

  const compiled = {
    ...template,
    boneList: bones,
    byName,
    legChains,
    rootIndex,
    restUp,
    gazeBones: pairs(template.gaze),
    swayBones: pairs(template.sway),
    trailBones: pairs(template.trail),
    hipCounterBones: pairs(template.hipCounter),
    boneAxes: template.axes || { pitch: 0, yaw: 1, roll: 2, yawSign: -1 },
  };
  TEMPLATE_CACHE.set(template, compiled);
  return compiled;
}

// ---------------------------------------------------------------------------
//  Proportions
//
//  Two archetypes that differ only in `scale` are the same character seen from
//  a different distance. Differing in *ratio* is what makes a brute lumber and
//  an assassin look quick before either of them has moved.
// ---------------------------------------------------------------------------

// Which body group a bone belongs to. Side and index suffixes are stripped
// first, so adding a bone named `forearmL` needs no entry here.
const PROPORTION_GROUP = {
  pelvis: 'torso', belt: 'torso', tasset: 'torso', spine: 'torso', chest: 'torso', core: 'torso',
  neck: 'neck',
  head: 'head', hair: 'head', helm: 'head', visor: 'head', crest: 'head',
  snout: 'head', jaw: 'head', horn: 'head', ear: 'head',
  shoulder: 'shoulder',
  upperArm: 'arm', forearm: 'arm', wing: 'arm',
  glove: 'hand', hand: 'hand',
  thigh: 'leg', shin: 'leg', leg: 'leg', legF: 'leg', legB: 'leg',
  boot: 'foot', foot: 'foot', footF: 'foot', footB: 'foot',
  cape: 'body', capeLower: 'body', tail: 'body', tailTip: 'body',
};

function groupOf(name) {
  if (PROPORTION_GROUP[name]) return PROPORTION_GROUP[name];
  const base = name.replace(/(L|R)[0-9]*$/, '');
  return PROPORTION_GROUP[base] || 'body';
}

function factorsFor(props, group) {
  const len = props[group] !== undefined ? props[group]
    : (props.body !== undefined ? props.body : 1);
  const girthKey = `${group}Girth`;
  const girth = props[girthKey] !== undefined ? props[girthKey]
    : (props.girth !== undefined ? props.girth : 1);
  return [len, girth];
}

const DERIVED_CACHE = new Map();

/**
 * Derive a template whose body ratios differ from the base.
 *
 * `props` keys are body groups — torso, neck, head, shoulder, arm, hand, leg,
 * foot, body — scaling that group's bone lengths, plus `<group>Girth` and a
 * global `girth` scaling width and depth. A bone's offset is scaled by its
 * *parent's* factors rather than its own, so the skeleton stays connected no
 * matter how far the ratios are pushed.
 *
 * @param {object} base   HUMANOID, QUADRUPED, WINGED or another derived template
 * @param {object} [props]
 * @returns {object} a cached template; identical props return the same object,
 *                   which matters because the bone compiler caches by identity
 */
export function deriveTemplate(base, props = {}) {
  const keys = Object.keys(props).sort();
  if (keys.length === 0) return base;
  const key = `${base.name}|${keys.map((k) => `${k}=${props[k]}`).join(',')}`;
  const cached = DERIVED_CACHE.get(key);
  if (cached) return cached;

  const factors = new Map();
  for (const b of base.bones) factors.set(b[0], factorsFor(props, groupOf(b[0])));

  const bones = base.bones.map((b) => {
    const [fl, fg] = factors.get(b[0]);
    const parent = b[1] !== null && b[1] !== undefined ? factors.get(b[1]) : null;
    const pl = parent ? parent[0] : 1;
    const pg = parent ? parent[1] : 1;
    const out = b.slice();
    out[2] = [b[2][0] * pg, b[2][1] * pl, b[2][2] * pg];
    out[3] = b[3] * fl;
    out[4] = b[4] * fg;
    out[5] = b[5] * fg;
    return out;
  });

  // Longer legs stand the hips higher; nothing else feeds ground contact.
  const derived = {
    ...base,
    name: key,
    bones,
    hipHeight: base.hipHeight * factorsFor(props, 'leg')[0],
  };
  DERIVED_CACHE.set(key, derived);
  return derived;
}

/** Ready-made silhouettes for archetypes to pick from. */
export const PROPORTIONS = {
  // Heavy through the chest and shoulders, short in the leg: reads as mass.
  brute: { torso: 1.10, shoulder: 1.25, arm: 1.06, leg: 0.90, neck: 0.70, head: 0.94, girth: 1.22, headGirth: 1.05 },
  // Small, wide and low — ogres, stone-eaters.
  hulk: { torso: 1.16, shoulder: 1.40, arm: 1.14, leg: 0.82, neck: 0.55, head: 0.86, girth: 1.45 },
  // Long limbs, narrow trunk, high shoulders: reads as fast.
  lithe: { torso: 0.94, shoulder: 0.85, arm: 1.08, leg: 1.10, neck: 1.15, head: 0.96, girth: 0.84 },
  // Starved and overlong — husks and revenants.
  gaunt: { torso: 1.02, shoulder: 0.80, arm: 1.18, leg: 1.12, neck: 1.30, head: 1.02, girth: 0.70 },
  // Short and thick, villagers and dwarfish fighters.
  stocky: { torso: 1.00, shoulder: 1.05, arm: 0.90, leg: 0.86, neck: 0.80, head: 1.10, girth: 1.15 },
  // Children and small spirits: head-heavy, everything else short.
  small: { torso: 0.92, shoulder: 0.90, arm: 0.88, leg: 0.84, neck: 0.85, head: 1.22, girth: 0.92 },
};

// ---------------------------------------------------------------------------
//  Rig instance
// ---------------------------------------------------------------------------

// Successive rigs are handed points of the golden-ratio walk, so two actors
// spawned back to back are as far out of phase as two points can be. Spawn
// order comes from the world seed, so this is reproducible.
let RIG_PHASE = 0.31;

// ---------------------------------------------------------------------------
//  Continuity tracking
//
//  The audit used to measure pose continuity by watching one rig across a
//  90-frame window it drove itself. That reported 0.364 rad/frame — above the
//  limiter's own 0.27 cap, which should be impossible — and the number would
//  not reproduce in a standalone harness running the identical 90 frames. Two
//  diagnostics went looking for the difference between the harnesses and found
//  none, because the window was never the thing that mattered: the limiter
//  bounds `pose`, and `_ground` writes `worldRot` after it.
//
//  A probe that only watches its own window can only see the events inside it.
//  This watches every rig on every frame it is enabled for, so whatever causes
//  a discontinuity reports itself with its own context attached instead of
//  having to be guessed at from one aggregate number.
// ---------------------------------------------------------------------------

let CONTINUITY = null;

/** Start (or stop, and clear) session-wide continuity tracking. */
export function trackContinuity(on = true) {
  CONTINUITY = on ? { frame: 0, events: [], rigs: 0 } : null;
}

/** Advance the shared frame counter. Hosts call this once per rendered frame. */
export function continuityFrame() {
  if (CONTINUITY) CONTINUITY.frame++;
}

/**
 * The worst frames seen since tracking began, worst first.
 *
 * `warped` marks a frame the rig was teleported on. Those are reported but
 * kept separate: a body that was moved across the map did not *rotate* into
 * its new orientation, and counting that as a snap would hide the ones that
 * are real.
 */
export function continuityReport(limit = 12) {
  if (!CONTINUITY) return null;
  // Ranked by rate, not by per-frame angle. A 0.8 rad step on a 50 ms frame and
  // a 0.27 rad step on a 17 ms frame are the same rotation happening at the
  // same speed; ranking by the raw angle would put the slow machine's ordinary
  // frames above the fast machine's real defects.
  const rateOf = (e) => (e.dt > 1e-6 ? e.ang / e.dt : 0);
  const ev = CONTINUITY.events.slice().sort((a, b) => rateOf(b) - rateOf(a));
  const steady = ev.filter((e) => !e.warped);
  const decorate = (e) => ({ ...e, rate: Math.round(rateOf(e) * 100) / 100 });
  return {
    frames: CONTINUITY.frame,
    rigs: CONTINUITY.rigs,
    maxAny: ev.length ? rateOf(ev[0]) : 0,
    maxSteady: steady.length ? rateOf(steady[0]) : 0,
    maxSteadyAngle: steady.length ? steady[0].ang : 0,
    worst: steady.slice(0, limit).map(decorate),
    worstWarped: ev.filter((e) => e.warped).slice(0, 4).map(decorate),
  };
}

export class Rig {
  constructor(template, scale = 1) {
    this.template = compile(template);
    this.scale = scale;
    const n = this.template.boneList.length;
    this.n = n;
    this.pose = new Float32Array(n * 3);        // current, damped
    this.target = new Float32Array(n * 3);      // desired this frame
    this.worldRot = new Float32Array(n * 9);
    this.worldPos = new Float32Array(n * 3);
    this.hidden = new Uint8Array(n);
    this.rootOffset = [0, 0, 0];                // animation-driven body offset
    this.rootRot = [0, 0, 0];                   // extra pitch/roll (rolls, death)
    this.blendRate = 16;
    // The facing the body is *drawn* at, which trails the actor's own yaw by
    // however much the continuity budget could not afford this frame.
    this._yawS = null;
    this._yawIn = 0;

    // --- the layers on top of the pose --------------------------------------
    this.clock = 0;
    RIG_PHASE = (RIG_PHASE + 0.6180339887498949) % 1;
    this.seed = RIG_PHASE;
    this.legs = this.template.legChains;
    /** True when this skeleton has legs the ground solver can plant. */
    this.footIK = this.legs.length > 0;
    this.ikWeight = 1;
    /** Per-leg contact this frame, written by the poses. See planted(). */
    this.plant = new Float32Array(this.legs.length).fill(1);
    // What the solver actually uses: the pose's plant weight, rate-limited.
    // Poses set plant per frame, so a roll ending flips a leg from 0 to 1 in
    // one frame and the foot snaps down onto the terrain. Easing the weight
    // instead lets the foot arrive — which is both what a landing looks like
    // and what keeps the frame-to-frame rotation inside the continuity budget.
    this.plantS = new Float32Array(this.legs.length).fill(1);
    /** How far the hips are sunk this frame so the deepest foot can reach. */
    this.pelvisDrop = 0;
    /** 0..1 — how much of the gaze is currently spent on the look target. */
    this.lookAtWeight = 0;
    this.lookTarget = null;
    this.lookHold = false;          // set by hosts that pick the target themselves
    this.gazeRange = LOOK_RANGE;
    /** Where the body's mass is relative to its hips: the inertia state. */
    this.secondary = { x: 0, z: 0, vx: 0, vz: 0 };
    this.reactions = {};            // latched flinch / death variants
    this.speed = 0;
    this.moveBlend = 0;
    /** Planar speed the body is being thrown at, and its bearing in body space. */
    this.recoil = 0;
    this.recoilAngle = 0;
    this.warped = false;

    this._rootBasis = new Float32Array(9);
    this._yawBasis = new Float32Array(9);
    this._tilt = new Float32Array(9);
    this._bodyBasis = new Float32Array(9);
    this._local = new Float32Array(9);
    this._localMat = new Float32Array(n * 9);   // kept for the ground solver
    this._step = new Float32Array(n * 3);
    this._cost = new Float32Array(n);
    this._dirty = new Uint8Array(n);
    this._rootTurn = [0, 0, 0];
    this._rootStep = [0, 0, 0];
    this._rootPos = [0, 0, 0];    // rootOffset after the rate limit
    this._rootPosStep = [0, 0, 0];
    this._vec = [0, 0, 0];
    this._basis = new Float32Array(9);
    this._rot = new Float32Array(9);
    this._partBatch = new Map();     // part name -> batch, reused every frame
    this._usedBatches = [];
    this._feet = this.legs.map(() => ({
      w: 0, x: 0, y: 0, z: 0, lift: 0, corr: 0, nx: 0, ny: 1, nz: 0, seeded: false,
    }));
    this._prev = { x: 0, y: 0, z: 0, vx: 0, vz: 0, set: false };
    this._idleCtx = { time: 0, seed: 0, moveBlend: 0, effort: 0 };
    this._scan = 0;

    for (const name of this.template.optional || []) {
      const i = this.template.byName.get(name);
      if (i !== undefined) this.hidden[i] = 1;
    }
  }

  /**
   * Watch a specific thing until told otherwise. Passing null hands the choice
   * back to the rig, which picks the nearest body.
   * @param {?object} target anything with x/z (and ideally eyeY)
   */
  setLookTarget(target) {
    this.lookTarget = target || null;
    this.lookHold = !!target;
  }

  setVisible(name, on) {
    const i = this.template.byName.get(name);
    if (i !== undefined) this.hidden[i] = on ? 0 : 1;
  }

  /** Swap the bare head for a helm (and hide the hair underneath it). */
  setHelm(on) {
    this.setVisible('helm', on);
    this.setVisible('visor', on);
    this.setVisible('crest', on);
    this.setVisible('hair', !on);
  }

  boneIndex(name) {
    const i = this.template.byName.get(name);
    return i === undefined ? -1 : i;
  }

  setBone(name, rx, ry, rz) {
    const i = this.template.byName.get(name);
    if (i === undefined) return;
    this.target[i * 3] = rx;
    this.target[i * 3 + 1] = ry;
    this.target[i * 3 + 2] = rz;
  }

  addBone(name, rx, ry, rz) {
    const i = this.template.byName.get(name);
    if (i === undefined) return;
    this.target[i * 3] += rx;
    this.target[i * 3 + 1] += ry;
    this.target[i * 3 + 2] += rz;
  }

  clearTarget() {
    this.target.fill(0);
    // Feet are assumed to be standing on something until a pose says otherwise,
    // which is the right default: most poses are standing ones.
    // Ease the solver's weight toward whatever the pose asked for last frame
    // before the poses overwrite it. Engaging is slower than releasing: a foot
    // leaving the ground should be instant (the pose has already taken it), a
    // foot arriving should not.
    for (let i = 0; i < this.plant.length; i++) {
      const target = this.plant[i];
      const cur = this.plantS[i];
      const rate = target > cur ? PLANT_ENGAGE : PLANT_RELEASE;
      const d = target - cur;
      const step = rate * (this._lastDt || 0.016);
      this.plantS[i] = Math.abs(d) <= step ? target : cur + Math.sign(d) * step;
      this.plant[i] = 1;
    }
  }

  /**
   * Tell the ground solver how much this frame's pose means its feet to be on
   * the ground. Poses that take the legs off it — rolls, jumps, kneeling,
   * dying — turn it down; everything else leaves it alone.
   * @param {number} w      0 = the solver keeps its hands off the legs
   * @param {number} [leg]  chain index; all of them when omitted
   */
  planted(w, leg) {
    if (leg === undefined) { for (let i = 0; i < this.plant.length; i++) this.plant[i] = w; }
    else if (leg >= 0 && leg < this.plant.length) this.plant[leg] = w;
  }

  /**
   * One frame of the whole body: read what the world did to it, add the layers
   * the pose does not know about, damp into the pose under a rate limit, build
   * world transforms, then put the feet on the ground.
   */
  apply(dt, x, y, z, yaw) {
    // clearTarget() advances the smoothed plant weight and is called from the
    // pose layer, which has no dt of its own.
    this._lastDt = dt;
    this._yawIn = yaw;
    this._sense(dt, x, y, z, yaw);
    this._layers(dt, x, y, z);
    this._damp(dt);
    this._skin(x, y, z, yaw);
    if (this.footIK) this._ground(dt, x, y, z);
    if (CONTINUITY) this._continuity(dt);
  }

  /**
   * Record how far the worst bone turned this frame, measured on the final
   * world transforms — after the ground solver, which is the only place that
   * can move a bone the limiter never charged for.
   */
  _continuity(dt) {
    const wr = this.worldRot;
    if (!this._contPrev) {
      this._contPrev = new Float32Array(wr.length);
      this._contPrev.set(wr);
      CONTINUITY.rigs++;
      return;
    }
    const prev = this._contPrev;
    let worst = 0, at = 0;
    for (let b = 0; b < wr.length; b += 9) {
      const d = prev[b + 3] * wr[b + 3] + prev[b + 4] * wr[b + 4] + prev[b + 5] * wr[b + 5];
      const ang = Math.acos(d > 1 ? 1 : d < -1 ? -1 : d);
      if (ang > worst) { worst = ang; at = b / 9; }
    }
    prev.set(wr);
    // Only frames worth explaining are kept, and the list is trimmed rather
    // than grown without bound — a long session must not turn the diagnostic
    // into the leak it is there to find. The threshold is a rate so that a slow
    // machine does not flood the list with ordinary frames.
    if (dt > 1e-6 && worst / dt > 7) {
      const ev = CONTINUITY.events;
      ev.push({
        frame: CONTINUITY.frame,
        bone: (this.template.boneList[at] || {}).name || `#${at}`,
        ang: Math.round(worst * 1e4) / 1e4,
        dt: Math.round(dt * 1e4) / 1e4,
        state: this.hostState || '?',
        host: this.hostTag || '?',
        warped: !!this.warped,
        blend: this.blendRate,
        yawLag: Math.round((this._yawS === null ? 0 : this._yawIn - this._yawS) * 1e3) / 1e3,
        ik: this.footIK ? Math.round(this.ikWeight * 100) / 100 : null,
      });
      if (ev.length > 400) {
        ev.sort((a, b) => (b.ang / b.dt) - (a.ang / a.dt));
        ev.length = 200;
      }
    }
  }

  /**
   * Velocity, effort and impact, read off the path the body actually took.
   * Nothing hands the rig a velocity, and the path is the honest source: it
   * already contains knockback, root motion and being shoved by a crowd.
   */
  _sense(dt, x, y, z, yaw) {
    this.clock += dt;
    const h = dt > 1e-4 ? dt : 1e-4;
    const p = this._prev;
    const dx = x - p.x, dz = z - p.z;
    // Metres in a single frame is a teleport, not a movement. It must not
    // become a velocity, an impact, or a foot damping its way across the map.
    const warped = !p.set || Math.abs(dx) > 2.5 || Math.abs(dz) > 2.5 || Math.abs(y - p.y) > 4;
    this.warped = warped;
    const vx = warped ? 0 : dx / h;
    const vz = warped ? 0 : dz / h;
    const dvx = vx - p.vx, dvz = vz - p.vz;
    p.x = x; p.y = y; p.z = z; p.vx = vx; p.vz = vz; p.set = true;

    // The character's own frame, without any body tilt in it. Everything that
    // has to be expressed as "forward" or "to the left" is resolved through
    // this, which is why none of it has to know the yaw convention.
    const yb = this._yawBasis;
    const cy = Math.cos(yaw), sy = Math.sin(yaw);
    yb[0] = cy; yb[1] = 0; yb[2] = -sy;
    yb[3] = 0; yb[4] = 1; yb[5] = 0;
    yb[6] = sy; yb[7] = 0; yb[8] = cy;

    const speed = Math.hypot(vx, vz);
    this.speed = speed;
    this.moveBlend = saturate(speed * 0.85);
    // What a reaction reads to decide how hard it was hit. While flinching or
    // dying an actor has no intent and no root motion, so the speed it is
    // travelling at *is* the knockback the blow gave it.
    this.recoil = speed;
    if (speed > 0.3) {
      // Bearing of the throw in body space: 0 is straight ahead, +ve to the left.
      const lx = yb[0] * vx + yb[2] * vz;
      const lz = yb[6] * vx + yb[8] * vz;
      this.recoilAngle = Math.atan2(lx, lz);
    }

    // Inertia. The trailing mass keeps the velocity the hips just gave up, so
    // a change of speed enters as an impulse and leaves as a settle.
    const sec = this.secondary;
    if (warped) { sec.x = 0; sec.z = 0; sec.vx = 0; sec.vz = 0; return; }
    sec.vx -= dvx; sec.vz -= dvz;
    sec.vx += (-SWAY_K * sec.x - SWAY_C * sec.vx) * dt;
    sec.vz += (-SWAY_K * sec.z - SWAY_C * sec.vz) * dt;
    sec.x = clamp(sec.x + sec.vx * dt, -0.5, 0.5);
    sec.z = clamp(sec.z + sec.vz * dt, -0.5, 0.5);
  }

  /**
   * The additive layers, written over the pose the actions left behind: hips
   * onto the slope, gaze onto whatever matters, torso and cloak behind the
   * hips, breath over everything.
   */
  _layers(dt, x, y, z) {
    const T = this.template;
    const ax = T.boneAxes;
    const t = this.target;
    const yb = this._yawBasis;
    const src = worldSource();

    // --- hips follow the ground ---------------------------------------------
    if (src && T.bodyTilt && T.rootIndex >= 0) {
      const st = (T.stance || 0.17) * this.scale;
      // Local axes on the ground plane: +Z ahead of the body, +X to its left.
      const fx = yb[6] * st, fz = yb[8] * st;
      const lx = yb[0] * st, lz = yb[2] * st;
      const gradF = (src.heightAt(x + fx, z + fz) - src.heightAt(x - fx, z - fz)) / (2 * st);
      const gradL = (src.heightAt(x + lx, z + lz) - src.heightAt(x - lx, z - lz)) / (2 * st);
      // The surface normal leans away from the rise; the hips lean with it.
      const pitch = clamp(Math.atan(gradF), -0.6, 0.6) * T.bodyTilt;
      const roll = clamp(-Math.atan(gradL), -0.6, 0.6) * T.bodyTilt;
      const r = T.rootIndex * 3;
      t[r + ax.pitch] += pitch;
      t[r + ax.roll] += roll;
      // Hips are not shoulders: take most of it back out up the spine, or the
      // character reads as leaning over rather than standing on a hill.
      for (const [i, g] of T.hipCounterBones) {
        t[i * 3 + ax.pitch] += pitch * g;
        t[i * 3 + ax.roll] += roll * g;
      }
    }

    // --- look at something ---------------------------------------------------
    this._scan -= dt;
    if (this._scan <= 0) {
      // Staggered per rig: a crowd must never all scan on the same frame.
      this._scan = 0.18 + this.seed * 0.14;
      if (!this.lookHold && src && src.gazeNear) {
        this.lookTarget = src.gazeNear(x, z, this.gazeRange);
      }
    }
    let want = 0;
    const tgt = this.lookTarget;
    if (tgt && !tgt.dead && T.gazeBones.length) {
      const hi = T.byName.get(T.head);
      const ex = hi !== undefined ? this.worldPos[hi * 3] : x;
      const ey = hi !== undefined ? this.worldPos[hi * 3 + 1] : y + 1.5 * this.scale;
      const ez = hi !== undefined ? this.worldPos[hi * 3 + 2] : z;
      const dx = tgt.x - ex;
      const dy = (tgt.eyeY !== undefined ? tgt.eyeY : tgt.y + 1.4) - ey;
      const dz = tgt.z - ez;
      const flat = Math.hypot(dx, dz);
      if (flat > 0.3) {
        const bx = yb[0] * dx + yb[2] * dz;
        const bz = yb[6] * dx + yb[8] * dz;
        const bearing = Math.atan2(bx, bz);
        const pitch = Math.atan2(dy, flat);
        // Released rather than twisted: past the limit the neck would invert.
        want = saturate(1 - flat / this.gazeRange)
          * (1 - saturate((Math.abs(bearing) - LOOK_YAW) / 0.55));
        this.lookAtWeight = damp(this.lookAtWeight, want, 5, dt);
        const w = this.lookAtWeight;
        if (w > 0.002) {
          const by = clamp(bearing, -LOOK_YAW, LOOK_YAW) * ax.yawSign * w;
          const bp = clamp(pitch, -LOOK_PITCH, LOOK_PITCH) * w;
          for (const [i, g] of T.gazeBones) {
            t[i * 3 + ax.yaw] += by * g;
            t[i * 3 + ax.pitch] += bp * g;
          }
        }
      }
    }
    if (want <= 0) this.lookAtWeight = damp(this.lookAtWeight, 0, 5, dt);

    // --- the body behind the hips -------------------------------------------
    const sec = this.secondary;
    const offL = yb[0] * sec.x + yb[2] * sec.z;   // to the left of the hips
    const offF = yb[6] * sec.x + yb[8] * sec.z;   // ahead of them
    if (offL * offL + offF * offF > 1e-8) {
      // A torso leans the way its mass went; a cloak hanging from that torso
      // swings the same way, and its bone points down, so its pitch is the
      // other sign. That is the whole of secondary motion.
      const lean = -offF * SWAY_PITCH;
      const tip = offL * SWAY_ROLL;
      for (const [i, g] of T.swayBones) {
        t[i * 3 + ax.pitch] += lean * g;
        t[i * 3 + ax.roll] += tip * g;
      }
      const tp = T.trailPitch !== undefined ? T.trailPitch : 1;
      for (const [i, g] of T.trailBones) {
        t[i * 3] += offF * TRAIL_PITCH * g * tp;
        t[i * 3 + 2] += offL * TRAIL_ROLL * g;
      }
    }

    // --- breath, weight shift, settles --------------------------------------
    const ctx = this._idleCtx;
    ctx.time = this.clock;
    ctx.seed = this.seed;
    ctx.moveBlend = this.moveBlend;
    ctx.effort = this.speed * 0.16;
    additiveIdle(this, ctx);
  }

  /**
   * Damp the pose toward the target, under a hard limit on how far anything is
   * allowed to turn in one frame.
   *
   * The limit is what makes continuity a property of the rig instead of a
   * property of whoever wrote the pose: a state change that assigns a wholly
   * different pose, or a curve with a violent first derivative, arrives as a
   * fast blend rather than as a cut. One scale for the whole skeleton, so a
   * limited frame is slower and never distorted.
   */
  _damp(dt) {
    const pose = this.pose, target = this.target, step = this._step;
    const n = pose.length;
    const k = 1 - Math.exp(-this.blendRate * dt);
    for (let i = 0; i < n; i++) step[i] = (target[i] - pose[i]) * k;

    // The root turn is written straight through by poses rather than damped,
    // and a dodge turns a whole revolution — so take the short way round, or
    // the wrap back to zero at the end of one is a jump of six radians.
    const rt = this._rootTurn, rr = this.rootRot, rs = this._rootStep;
    let rootCost = 0;
    for (let a = 0; a < 3; a++) {
      let d = rr[a] - rt[a];
      if (d > PI) d -= 2 * PI; else if (d < -PI) d += 2 * PI;
      rs[a] = d;
      rootCost += Math.abs(d);
    }

    // The actor's facing arrives from outside the rig, and _skin used to write
    // it straight into the world transform. That made the one rotation which
    // moves every bone at once the one rotation the budget never saw: a dodge
    // assigns yaw outright, and an AI turning toward a target on a 50 ms frame
    // can swing more than a radian. Both left the limiter reporting it had
    // spent nothing while the whole body spun — a 180-degree reassignment moved
    // a foot 2.71 rad in one frame, ten times the cap the limiter enforces on
    // everything it can see. Charge it here, and draw the body at whatever
    // facing the budget could actually pay for. The debt is never dropped, so
    // the facing always arrives; it just takes 0.25 s to turn all the way round
    // instead of zero.
    let dYaw = 0;
    if (this._yawS === null || this.warped) this._yawS = this._yawIn;
    else {
      dYaw = this._yawIn - this._yawS;
      if (dYaw > PI) dYaw -= 2 * PI; else if (dYaw < -PI) dYaw += 2 * PI;
      rootCost += Math.abs(dYaw);
    }

    // The body offset is written straight through as well, and once the feet
    // are on the ground a step in body height *is* a step in leg angle: a
    // flinch that drops the hips 20 cm on its first frame swings the shin
    // further than any pose ever asks for, because the solver has to find that
    // distance somewhere. Charge the translation the angle it costs the legs —
    // roughly the drop over half the hip height — and put it through the same
    // budget, so the limiter still bounds the whole body and not just the part
    // of it that happens to be expressed as a rotation.
    const rp = this._rootPos, ro = this.rootOffset, ps = this._rootPosStep;
    if (this.warped) { rp[0] = ro[0]; rp[1] = ro[1]; rp[2] = ro[2]; }
    for (let a = 0; a < 3; a++) ps[a] = ro[a] - rp[a];
    if (this.footIK) {
      const lever = Math.max(0.15, this.template.hipHeight * 0.5);
      rootCost += Math.hypot(ps[0], ps[1], ps[2]) / lever;
    }

    // A bone's cost is what its parents did to it plus what it does to itself:
    // an upper bound on the angle its own axis sweeps through this frame.
    const bones = this.template.boneList;
    const cost = this._cost;
    let worst = rootCost;
    for (let i = 0; i < bones.length; i++) {
      const o = i * 3;
      const own = Math.hypot(step[o], step[o + 2]);
      const p = bones[i].parent;
      const base = p < 0 ? rootCost : cost[p];
      if (base + own > worst) worst = base + own;
      // Twist about a bone's own axis does not move that axis, but it does
      // move every axis below it.
      cost[i] = base + own + Math.abs(step[o + 1]);
    }

    const cap = Math.min(TURN_RATE * dt, TURN_STEP);
    const f = worst > cap ? cap / worst : 1;
    for (let i = 0; i < n; i++) pose[i] += step[i] * f;
    for (let a = 0; a < 3; a++) {
      let v = rt[a] + rs[a] * f;
      if (v > PI) v -= 2 * PI; else if (v < -PI) v += 2 * PI;
      rt[a] = v;
      rp[a] += ps[a] * f;
    }
    let ys = this._yawS + dYaw * f;
    if (ys > PI) ys -= 2 * PI; else if (ys < -PI) ys += 2 * PI;
    this._yawS = ys;
  }

  /** Pose to world transforms. */
  _skin(x, y, z, yaw) {
    const bones = this.template.boneList;
    const pose = this.pose;
    const s = this.scale;
    const rt = this._rootTurn;

    // Yaw and body tilt cannot be built in one call: a bone rotation composes
    // in the bone's own frame, so a dodge roll's tumble axis would sit wherever
    // the character happened to be facing. Facing first, body inside it — and
    // the facing is built here rather than borrowed, so the model's forward is
    // the direction the actor is actually moving.
    const fy = this._yawS !== null ? this._yawS : yaw;
    const cy = Math.cos(fy + rt[1]), sy = Math.sin(fy + rt[1]);
    const tilt = this._tilt;
    mat3RotXYZ(tilt, rt[0], 0, rt[2]);
    // The body's own frame: facing, plus whatever it is leaning. Its Y column
    // is which way is up *for this body*, which is the axis the ground solver
    // measures foot lift along — a rig lying on its side has not lifted a foot.
    const body = this._bodyBasis;
    body[0] = cy; body[1] = 0; body[2] = -sy;
    body[3] = 0; body[4] = 1; body[5] = 0;
    body[6] = sy; body[7] = 0; body[8] = cy;
    mat3Mul(body, body, tilt);

    const rootBasis = this._rootBasis;
    const rp = this.template.rootPitch || 0;
    if (rp) {
      mat3RotXYZ(this._local, rp, 0, 0);
      mat3Mul(rootBasis, body, this._local);
    } else {
      rootBasis.set(body);
    }

    // The rate-limited offset, not the raw one the pose wrote: see _damp.
    const ofs = this._rootPos;
    const baseY = y + (this.template.hipHeight * s) + ofs[1] * s;
    const off = this._vec;
    mat3Apply(rootBasis, ofs[0] * s, 0, ofs[2] * s, off);

    const wr = this.worldRot, wp = this.worldPos;
    const local = this._local;
    const lm = this._localMat;

    for (let i = 0; i < bones.length; i++) {
      const b = bones[i];
      const o = i * 9;
      mat3RotXYZ(local, pose[i * 3], pose[i * 3 + 1], pose[i * 3 + 2]);
      // Kept, not discarded: the ground solver rebuilds part of the skeleton
      // and needs every bone's local transform to do it.
      if (b.hasBind) mat3MulAt(lm, o, b.bind, 0, local, 0);
      else for (let q = 0; q < 9; q++) lm[o + q] = local[q];

      if (b.parent < 0) {
        mat3MulAt(wr, o, rootBasis, 0, lm, o);
        wp[i * 3] = x + off[0];
        wp[i * 3 + 1] = baseY;
        wp[i * 3 + 2] = z + off[2];
      } else {
        const p = b.parent * 9;
        mat3MulAt(wr, o, wr, p, lm, o);
        wp[i * 3] = wp[b.parent * 3]
          + wr[p] * b.offset[0] * s + wr[p + 3] * b.offset[1] * s + wr[p + 6] * b.offset[2] * s;
        wp[i * 3 + 1] = wp[b.parent * 3 + 1]
          + wr[p + 1] * b.offset[0] * s + wr[p + 4] * b.offset[1] * s + wr[p + 7] * b.offset[2] * s;
        wp[i * 3 + 2] = wp[b.parent * 3 + 2]
          + wr[p + 2] * b.offset[0] * s + wr[p + 5] * b.offset[1] * s + wr[p + 8] * b.offset[2] * s;
      }
    }
  }

  /**
   * Put the feet on the ground.
   *
   * Measure where the animation wanted each foot, raycast the height field
   * straight down there, sink the hips by however far the leg with the longest
   * reach falls short, then solve both legs analytically onto the ground. The
   * hips move first because a leg that has to straighten completely to reach
   * has stopped being a leg.
   *
   * Runs after the skinning pass and rewrites part of it, which is why the
   * skinning pass keeps every bone's local transform: the bones hanging off a
   * solved leg have to be rebuilt.
   */
  _ground(dt, x, y, z) {
    const src = worldSource();
    if (!src) return;
    const s = this.scale;
    const legs = this.legs;
    const feet = this._feet;
    const bones = this.template.boneList;
    const wr = this.worldRot, wp = this.worldPos;
    const warped = this.warped;

    // Airborne bodies have nothing to stand on. Fade out rather than reach for
    // ground that is forty metres down a cliff.
    const under = src.heightAt(x, z);
    const air = saturate((y - under - 0.22 * s) / (0.55 * s));
    // Nor has a body that is no longer upright: a pose that has pitched the
    // whole rig over is a body on the floor, whatever its feet think.
    const upright = saturate((this._bodyBasis[4] - 0.55) / 0.25);
    const gw = clamp(this.ikWeight, 0, 1) * (1 - air) * upright;

    // --- 1. how far the pose has each foot off the floor it is standing on --
    //
    // Measured up the body's own vertical, not the world's, and relative to
    // where that leg hangs at rest — so tilting the hips onto a slope, or the
    // breathing bob, or a crouch, do not read as the animation picking a foot
    // up. Baselined against the lowest foot, which is the one the weight is on:
    // whatever is above it is stride, and stride is kept.
    const rootI = this.template.rootIndex;
    const ri = rootI * 3, rq = rootI * 9;
    const rx = wp[ri], ry = wp[ri + 1], rz = wp[ri + 2];
    // Up, as the root bone currently holds it: hips tilted onto a slope carry
    // the legs with them, and that is not the animation lifting a foot.
    const u = this.template.restUp;
    const ux = wr[rq] * u[0] + wr[rq + 3] * u[1] + wr[rq + 6] * u[2];
    const uy = wr[rq + 1] * u[0] + wr[rq + 4] * u[1] + wr[rq + 7] * u[2];
    const uz = wr[rq + 2] * u[0] + wr[rq + 5] * u[1] + wr[rq + 8] * u[2];
    let lowest = Infinity;
    for (let c = 0; c < legs.length; c++) {
      const leg = legs[c], f = feet[c];
      const li = leg.lower;
      const L2 = bones[li].len * s;
      f.x = wp[li * 3] + wr[li * 9 + 3] * L2;
      f.y = wp[li * 3 + 1] + wr[li * 9 + 4] * L2;
      f.z = wp[li * 3 + 2] + wr[li * 9 + 5] * L2;
      const up = (f.x - rx) * ux + (f.y - ry) * uy + (f.z - rz) * uz;
      f.lift = up - leg.restDrop * s;
      if (f.lift < lowest) lowest = f.lift;
    }

    // --- 2. where each foot wants to be, and what that costs the hips -------
    let sink = 0;
    for (let c = 0; c < legs.length; c++) {
      const leg = legs[c], f = feet[c];
      const ui = leg.upper, li = leg.lower;
      const lift = Math.max(0, f.lift - lowest);
      const gy = src.heightAt(f.x, f.z);
      const w = gw * clamp(this.plantS[c], 0, 1);
      const wlim = Math.min(PLANT_SLEW * dt, PLANT_STEP);
      f.w = warped ? w : clamp(w, f.w - wlim, f.w + wlim);
      const fk = f.y;

      // What the solver is about to bend the leg by — and it has to come in at
      // a rate a leg can move. A pose that let go of the ground (a roll, a
      // death, a jump) leaves the feet a long way off it, and taking that back
      // in one frame is precisely the jump-cut the rate limiter in _damp
      // exists to prevent; the limiter cannot see it, because this correction
      // is not a pose. Slewing it here is what keeps the ground solve inside
      // the same continuity guarantee as everything else.
      const want = (gy + SOLE_LIFT + lift - fk) * f.w;
      const lim = Math.min(IK_SLEW * dt, IK_STEP) * s;
      f.corr = warped ? want : clamp(want, f.corr - lim, f.corr + lim);
      f.y = fk + f.corr;

      // Exactly how far the hip has to sink for this leg to reach without
      // straightening: the vertical drop it needs, less the vertical drop it
      // has left once the horizontal part of the reach is paid for.
      if (f.w > 0.001 || Math.abs(f.corr) > 1e-4) {
        const reach = (bones[ui].len + bones[li].len) * s * LEG_REACH;
        const hx = wp[ui * 3], hy = wp[ui * 3 + 1], hz = wp[ui * 3 + 2];
        const flat2 = (f.x - hx) * (f.x - hx) + (f.z - hz) * (f.z - hz);
        const room = reach * reach - flat2;
        const need = (hy - f.y) - (room > 0 ? Math.sqrt(room) : 0);
        if (need > sink) sink = need;
      }

      // Slope under the sole, for laying the foot flat on it. Samples wide
      // enough apart to cross a bilinear cell edge without popping.
      if (leg.sole >= 0 && f.w > 0.01) {
        const d = 0.32 * s;
        const nx = (src.heightAt(f.x - d, f.z) - src.heightAt(f.x + d, f.z)) / (2 * d);
        const nz = (src.heightAt(f.x, f.z - d) - src.heightAt(f.x, f.z + d)) / (2 * d);
        const l = Math.hypot(nx, 1, nz);
        if (!f.seeded || warped) { f.nx = nx / l; f.ny = 1 / l; f.nz = nz / l; f.seeded = true; }
        else {
          f.nx = damp(f.nx, nx / l, 9, dt);
          f.ny = damp(f.ny, 1 / l, 9, dt);
          f.nz = damp(f.nz, nz / l, 9, dt);
        }
      }
    }

    // --- 3. sink the hips ----------------------------------------------------
    const maxDrop = this.template.hipHeight * s * 0.5;
    const dropWant = clamp(sink, 0, maxDrop);
    this.pelvisDrop = warped ? dropWant : damp(this.pelvisDrop, dropWant, 9, dt);
    const drop = this.pelvisDrop;
    if (drop > 1e-5) {
      // The root only translates, so every bone hanging off it translates with
      // it — no need to rebuild a single rotation.
      for (let i = 1; i < wp.length; i += 3) wp[i] -= drop;
    }

    // --- 4. solve each leg ---------------------------------------------------
    //
    // Every leg, every frame, including the ones with no contact left. Skipping
    // the solve at low weight looks like an optimisation and is really a cliff:
    // an unsolved leg is the pose's own chain, a solved one at zero correction
    // is the same chain rebuilt, and the frame the branch flips the difference
    // between them arrives all at once — which is exactly the snap this whole
    // system exists to remove. Solving always means the only thing that varies
    // is the correction, and the correction is rate-limited.
    for (let c = 0; c < legs.length; c++) {
      const leg = legs[c], f = feet[c];
      const ui = leg.upper, li = leg.lower;
      const L1 = bones[ui].len * s, L2 = bones[li].len * s;
      const reach = (L1 + L2) * LEG_REACH;
      const hx = wp[ui * 3], hy = wp[ui * 3 + 1], hz = wp[ui * 3 + 2];

      // Keep the contact point in the xz the animation chose — that is where
      // the ground was sampled — and give up height instead when the leg is
      // genuinely out of travel. A foot that slides sideways to stay planted
      // is worse than a foot that hangs.
      let ox = f.x - hx, oz = f.z - hz;
      const flat = Math.hypot(ox, oz);
      if (flat > reach * 0.94) {
        const k = (reach * 0.94) / flat;
        ox *= k; oz *= k;
      }
      const room = reach * reach - (ox * ox + oz * oz);
      const ty = Math.max(f.y, hy - Math.sqrt(room > 0 ? room : 0));

      // The knee keeps pointing where the animation was pointing it, which is
      // what makes this work for a kick, a crouch and a wolf's hock alike.
      solveLeg(wr, wp, ui, li, L1, L2, hx, hy, hz, hx + ox, ty, hz + oz,
        -wr[ui * 9 + 6], -wr[ui * 9 + 7], -wr[ui * 9 + 8]);

      // Everything hanging off the leg: boot shafts, feet, anything added later.
      this._rebuild(ui, li);

      // Lay the sole along the slope it is standing on.
      if (leg.sole >= 0) this._alignSole(leg.sole, f);
    }
  }

  /** Rebuild the world transforms of every bone below two just-solved ones. */
  _rebuild(ui, li) {
    const bones = this.template.boneList;
    const wr = this.worldRot, wp = this.worldPos, lm = this._localMat;
    const dirty = this._dirty;
    const s = this.scale;
    dirty.fill(0);
    dirty[ui] = 1; dirty[li] = 1;
    for (let i = (ui < li ? ui : li) + 1; i < bones.length; i++) {
      const b = bones[i];
      if (b.parent < 0 || !dirty[b.parent] || i === li) continue;
      const p = b.parent * 9, o = i * 9;
      mat3MulAt(wr, o, wr, p, lm, o);
      wp[i * 3] = wp[b.parent * 3]
        + wr[p] * b.offset[0] * s + wr[p + 3] * b.offset[1] * s + wr[p + 6] * b.offset[2] * s;
      wp[i * 3 + 1] = wp[b.parent * 3 + 1]
        + wr[p + 1] * b.offset[0] * s + wr[p + 4] * b.offset[1] * s + wr[p + 7] * b.offset[2] * s;
      wp[i * 3 + 2] = wp[b.parent * 3 + 2]
        + wr[p + 2] * b.offset[0] * s + wr[p + 5] * b.offset[1] * s + wr[p + 8] * b.offset[2] * s;
      dirty[i] = 1;
    }
  }

  /**
   * Turn a sole onto the ground plane under it. A foot that stays level while
   * the ground tilts is the tell that legs were placed rather than planted.
   */
  _alignSole(i, f) {
    const wr = this.worldRot;
    const o = i * 9;
    // The sole's up is the back of its own depth axis (see the FORWARD bind).
    const ux = -wr[o + 6], uy = -wr[o + 7], uz = -wr[o + 8];
    // Minimal rotation from that to the ground normal, scaled by contact.
    let axX = uy * f.nz - uz * f.ny;
    let axY = uz * f.nx - ux * f.nz;
    let axZ = ux * f.ny - uy * f.nx;
    const sn = Math.hypot(axX, axY, axZ);
    if (sn < 1e-5) return;
    const dot = clamp(ux * f.nx + uy * f.ny + uz * f.nz, -1, 1);
    const ang = clamp(Math.atan2(sn, dot), -0.5, 0.5) * f.w;
    if (Math.abs(ang) < 1e-4) return;
    axX /= sn; axY /= sn; axZ /= sn;
    const c = Math.cos(ang), si = Math.sin(ang), t = 1 - c;
    const r = this._rot;
    r[0] = t * axX * axX + c;        r[1] = t * axX * axY + si * axZ; r[2] = t * axX * axZ - si * axY;
    r[3] = t * axX * axY - si * axZ; r[4] = t * axY * axY + c;        r[5] = t * axY * axZ + si * axX;
    r[6] = t * axX * axZ + si * axY; r[7] = t * axY * axZ - si * axX; r[8] = t * axZ * axZ + c;
    mat3MulAt(wr, o, r, 0, wr, o);
  }

  /**
   * Push every visible bone into a single instanced batch, drawing all of them
   * with that batch's mesh. Kept for callers that only own the box batch.
   * @param {object} batch  InstanceBatch
   */
  render(batch, palette, opts = {}) {
    this._pushBones(null, batch, palette, opts);
    batch.material(SURFACE.DEFAULT);
  }

  /**
   * Push every visible bone into the batch its primitive belongs to, so a
   * shoulder is a pauldron and a thigh is a tapered limb. Still a handful of
   * draw calls for the whole fight: one per primitive, not one per character.
   * @param {object|Function} batches  BatchSet, or a name -> batch function
   */
  renderTo(batches, palette, opts = {}) {
    const lookup = typeof batches === 'function' ? batches : (n) => batches.get(n);
    const fallback = lookup(PART.BOX);
    const resolved = this._pushBones(lookup, fallback, palette, opts);
    for (const b of resolved) b.material(SURFACE.DEFAULT);
  }

  /**
   * Shared body of render/renderTo.
   * @returns {Array<object>} the batches actually written to
   */
  _pushBones(lookup, fallback, palette, opts) {
    const bones = this.template.boneList;
    const s = this.scale;
    const alpha = opts.alpha !== undefined ? opts.alpha : 1;
    const emissive = opts.emissive || 0;
    const tintR = opts.tintR !== undefined ? opts.tintR : 1;
    const tintG = opts.tintG !== undefined ? opts.tintG : 1;
    const tintB = opts.tintB !== undefined ? opts.tintB : 1;
    const basis = this._basis;
    const wr = this.worldRot;
    // Resolved once per part per call rather than once per bone; there are five
    // parts and thirty bones.
    const byPart = this._partBatch;
    const used = this._usedBatches;
    byPart.clear();
    used.length = 0;

    for (let i = 0; i < bones.length; i++) {
      if (this.hidden[i]) continue;
      const b = bones[i];
      let batch = fallback;
      if (lookup) {
        batch = byPart.get(b.part);
        if (batch === undefined) {
          // A part with no batch registered falls back to the box, so a rig
          // never silently disappears because a mesh was not wired up.
          batch = lookup(b.part) || fallback;
          byPart.set(b.part, batch);
          used.push(batch);
        }
      }
      const sy = b.len * s;
      const sw = b.w * s, sd = b.d * s;
      const o = i * 9;
      basis[0] = wr[o] * sw; basis[1] = wr[o + 1] * sw; basis[2] = wr[o + 2] * sw;
      basis[3] = wr[o + 3] * sy; basis[4] = wr[o + 4] * sy; basis[5] = wr[o + 5] * sy;
      basis[6] = wr[o + 6] * sd; basis[7] = wr[o + 7] * sd; basis[8] = wr[o + 8] * sd;

      const c = palette[b.mat] || palette[MAT.CLOTH] || [0.6, 0.6, 0.6];
      // Steel, leather and linen on the same character, still one draw call:
      // the batch's material is a per-instance attribute, so changing it
      // between pushes costs nothing but two floats.
      const surf = MAT_SURFACE[b.mat] !== undefined ? MAT_SURFACE[b.mat] : SURFACE.CLOTH;
      batch.material(surf, surf);
      batch.pushMatrix(basis,
        this.worldPos[i * 3], this.worldPos[i * 3 + 1], this.worldPos[i * 3 + 2],
        c[0] * tintR, c[1] * tintG, c[2] * tintB,
        emissive, 0.92, alpha);
    }
    return used;
  }

  /** World-space position of a bone's joint. */
  jointPos(name, out = { x: 0, y: 0, z: 0 }) {
    const i = this.template.byName.get(name);
    if (i === undefined) return out;
    out.x = this.worldPos[i * 3];
    out.y = this.worldPos[i * 3 + 1];
    out.z = this.worldPos[i * 3 + 2];
    return out;
  }

  /** World-space position of a bone's far end. */
  boneTip(name, out = { x: 0, y: 0, z: 0 }) {
    const i = this.template.byName.get(name);
    if (i === undefined) return out;
    const len = this.template.boneList[i].len * this.scale;
    const wr = this.worldRot;
    out.x = this.worldPos[i * 3] + wr[i * 9 + 3] * len;
    out.y = this.worldPos[i * 3 + 1] + wr[i * 9 + 4] * len;
    out.z = this.worldPos[i * 3 + 2] + wr[i * 9 + 5] * len;
    return out;
  }

  /** Basis of a bone, for attaching weapons and effects. */
  boneBasis(name, out = new Float32Array(9)) {
    const i = this.template.byName.get(name);
    if (i === undefined) return mat3Identity(out);
    out.set(this.worldRot.subarray(i * 9, i * 9 + 9));
    return out;
  }

  boneLength(name) {
    const i = this.template.byName.get(name);
    return i === undefined ? 0 : this.template.boneList[i].len * this.scale;
  }
}

export { mat3Mul, mat3RotXYZ, mat3Apply, mat3Identity };
