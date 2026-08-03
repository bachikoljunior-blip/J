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
// ============================================================================

const PI = Math.PI;

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

// ---------------------------------------------------------------------------
//  Materials
// ---------------------------------------------------------------------------

export const MAT = {
  SKIN: 0, CLOTH: 1, ARMOR: 2, LEATHER: 3, HAIR: 4, ACCENT: 5, METAL: 6, DARK: 7,
};

// Bone tuple: [name, parentName|null, offset, len, w, d, mat, bind?]
// Parents are named rather than indexed so inserting a bone can never silently
// re-parent the ones after it.
const DOWN = [PI, 0, 0];        // hangs from the joint
const FORWARD = [PI / 2, 0, 0]; // points along the parent's forward axis

export const HUMANOID = {
  name: 'humanoid',
  hipHeight: 0.86,
  bones: [
    ['pelvis', null, [0, 0, 0], 0.19, 0.335, 0.225, MAT.ARMOR],
    ['tasset', 'pelvis', [0, 0.015, 0], 0.24, 0.375, 0.265, MAT.LEATHER, DOWN],
    ['spine', 'pelvis', [0, 0.18, 0], 0.23, 0.355, 0.235, MAT.ARMOR],
    ['chest', 'spine', [0, 0.22, 0], 0.27, 0.425, 0.275, MAT.ARMOR],
    ['neck', 'chest', [0, 0.265, 0], 0.07, 0.125, 0.125, MAT.SKIN],
    ['head', 'neck', [0, 0.07, 0], 0.255, 0.230, 0.250, MAT.SKIN],
    ['hair', 'head', [0, 0.155, -0.012], 0.13, 0.255, 0.27, MAT.HAIR],
    // Helm, visor and crest replace the bare head when a head slot is filled.
    ['helm', 'neck', [0, 0.055, 0], 0.285, 0.265, 0.285, MAT.ARMOR],
    ['visor', 'helm', [0, 0.125, 0.125], 0.06, 0.20, 0.055, MAT.DARK],
    ['crest', 'helm', [0, 0.275, -0.02], 0.13, 0.05, 0.22, MAT.ACCENT],

    ['shoulderL', 'chest', [0.225, 0.235, 0], 0.11, 0.20, 0.195, MAT.ARMOR, DOWN],
    ['upperArmL', 'shoulderL', [0, 0.09, 0], 0.26, 0.135, 0.135, MAT.CLOTH],
    ['forearmL', 'upperArmL', [0, 0.26, 0], 0.24, 0.115, 0.115, MAT.SKIN],
    ['handL', 'forearmL', [0, 0.24, 0], 0.10, 0.105, 0.135, MAT.SKIN],

    ['shoulderR', 'chest', [-0.225, 0.235, 0], 0.11, 0.20, 0.195, MAT.ARMOR, DOWN],
    ['upperArmR', 'shoulderR', [0, 0.09, 0], 0.26, 0.135, 0.135, MAT.CLOTH],
    ['forearmR', 'upperArmR', [0, 0.26, 0], 0.24, 0.115, 0.115, MAT.SKIN],
    ['handR', 'forearmR', [0, 0.24, 0], 0.10, 0.105, 0.135, MAT.SKIN],

    ['thighL', 'pelvis', [0.108, 0.03, 0], 0.40, 0.175, 0.185, MAT.LEATHER, DOWN],
    ['shinL', 'thighL', [0, 0.40, 0], 0.38, 0.142, 0.152, MAT.LEATHER],
    ['footL', 'shinL', [0, 0.38, 0], 0.245, 0.150, 0.115, MAT.DARK, FORWARD],

    ['thighR', 'pelvis', [-0.108, 0.03, 0], 0.40, 0.175, 0.185, MAT.LEATHER, DOWN],
    ['shinR', 'thighR', [0, 0.40, 0], 0.38, 0.142, 0.152, MAT.LEATHER],
    ['footR', 'shinR', [0, 0.38, 0], 0.245, 0.150, 0.115, MAT.DARK, FORWARD],

    // Two segments so the cloak can actually bend and trail.
    ['cape', 'chest', [0, 0.255, -0.135], 0.40, 0.36, 0.035, MAT.ACCENT, DOWN],
    ['capeLower', 'cape', [0, 0.40, 0], 0.44, 0.31, 0.03, MAT.ACCENT],
  ],
  // Hidden until something turns them on (a head slot being filled).
  optional: ['helm', 'visor', 'crest'],
  handR: 'handR',
  handL: 'handL',
  head: 'head',
  chest: 'chest',
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
    ['core', null, [0, 0, 0], 0.48, 0.34, 0.32, MAT.CLOTH],
    ['chest', 'core', [0, 0.46, 0], 0.30, 0.37, 0.35, MAT.CLOTH],
    ['neck', 'chest', [0, 0.28, -0.09], 0.24, 0.21, 0.21, MAT.CLOTH],
    ['head', 'neck', [0, 0.23, 0], 0.22, 0.22, 0.24, MAT.CLOTH],
    ['snout', 'head', [0, 0.19, 0.05], 0.17, 0.14, 0.15, MAT.DARK],
    ['earL', 'head', [0.085, 0.15, -0.09], 0.14, 0.07, 0.05, MAT.DARK, [-0.5, 0, 0]],
    ['earR', 'head', [-0.085, 0.15, -0.09], 0.14, 0.07, 0.05, MAT.DARK, [-0.5, 0, 0]],
    ['tail', 'core', [0, -0.02, -0.08], 0.42, 0.10, 0.10, MAT.CLOTH, QUAD_BACK],

    ['legFL', 'chest', [0.165, 0.14, 0.06], 0.32, 0.11, 0.11, MAT.CLOTH, QUAD_DOWN],
    ['footFL', 'legFL', [0, 0.32, 0], 0.30, 0.105, 0.14, MAT.DARK],
    ['legFR', 'chest', [-0.165, 0.14, 0.06], 0.32, 0.11, 0.11, MAT.CLOTH, QUAD_DOWN],
    ['footFR', 'legFR', [0, 0.32, 0], 0.30, 0.105, 0.14, MAT.DARK],
    ['legBL', 'core', [0.165, 0.08, 0.06], 0.32, 0.13, 0.13, MAT.CLOTH, QUAD_DOWN],
    ['footBL', 'legBL', [0, 0.32, 0], 0.30, 0.115, 0.15, MAT.DARK],
    ['legBR', 'core', [-0.165, 0.08, 0.06], 0.32, 0.13, 0.13, MAT.CLOTH, QUAD_DOWN],
    ['footBR', 'legBR', [0, 0.32, 0], 0.30, 0.115, 0.15, MAT.DARK],
  ],
  head: 'head',
  chest: 'chest',
};

export const WINGED = {
  name: 'winged',
  hipHeight: 1.30,
  rootPitch: -PI / 2,
  bones: [
    ['core', null, [0, 0, 0], 0.78, 0.58, 0.54, MAT.ARMOR],
    ['chest', 'core', [0, 0.74, 0], 0.46, 0.62, 0.58, MAT.ARMOR],
    ['neck', 'chest', [0, 0.44, -0.16], 0.42, 0.26, 0.26, MAT.ARMOR],
    ['head', 'neck', [0, 0.40, 0], 0.30, 0.30, 0.34, MAT.ARMOR],
    ['jaw', 'head', [0, 0.22, 0.10], 0.24, 0.26, 0.16, MAT.DARK],
    ['hornL', 'head', [0.13, 0.16, -0.14], 0.34, 0.08, 0.08, MAT.DARK, [-0.8, 0, 0]],
    ['hornR', 'head', [-0.13, 0.16, -0.14], 0.34, 0.08, 0.08, MAT.DARK, [-0.8, 0, 0]],
    ['tail', 'core', [0, -0.04, -0.10], 0.80, 0.21, 0.21, MAT.ARMOR, QUAD_BACK],
    ['tailTip', 'tail', [0, 0.80, 0], 0.62, 0.13, 0.13, MAT.DARK],

    ['wingL0', 'chest', [0.32, 0.30, -0.22], 0.92, 0.14, 0.10, MAT.LEATHER, [-1.15, 0, 0.9]],
    ['wingL1', 'wingL0', [0, 0.92, 0], 1.10, 0.84, 0.05, MAT.LEATHER],
    ['wingR0', 'chest', [-0.32, 0.30, -0.22], 0.92, 0.14, 0.10, MAT.LEATHER, [-1.15, 0, -0.9]],
    ['wingR1', 'wingR0', [0, 0.92, 0], 1.10, 0.84, 0.05, MAT.LEATHER],

    ['legFL', 'chest', [0.30, 0.22, 0.10], 0.50, 0.17, 0.17, MAT.ARMOR, QUAD_DOWN],
    ['footFL', 'legFL', [0, 0.50, 0], 0.44, 0.16, 0.22, MAT.DARK],
    ['legFR', 'chest', [-0.30, 0.22, 0.10], 0.50, 0.17, 0.17, MAT.ARMOR, QUAD_DOWN],
    ['footFR', 'legFR', [0, 0.50, 0], 0.44, 0.16, 0.22, MAT.DARK],
    ['legBL', 'core', [0.30, 0.10, 0.10], 0.56, 0.20, 0.20, MAT.ARMOR, QUAD_DOWN],
    ['footBL', 'legBL', [0, 0.56, 0], 0.48, 0.18, 0.24, MAT.DARK],
    ['legBR', 'core', [-0.30, 0.10, 0.10], 0.56, 0.20, 0.20, MAT.ARMOR, QUAD_DOWN],
    ['footBR', 'legBR', [0, 0.56, 0], 0.48, 0.18, 0.24, MAT.DARK],
  ],
  head: 'head',
  chest: 'chest',
};

const TEMPLATE_CACHE = new Map();

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
    };
  });
  const compiled = { ...template, boneList: bones, byName };
  TEMPLATE_CACHE.set(template, compiled);
  return compiled;
}

// ---------------------------------------------------------------------------
//  Rig instance
// ---------------------------------------------------------------------------

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
    this._rootBasis = new Float32Array(9);
    this._local = new Float32Array(9);
    this._localBind = new Float32Array(9);
    this._vec = [0, 0, 0];
    this._basis = new Float32Array(9);

    for (const name of this.template.optional || []) {
      const i = this.template.byName.get(name);
      if (i !== undefined) this.hidden[i] = 1;
    }
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

  clearTarget() { this.target.fill(0); }

  /** Damp the current pose toward the target and rebuild world transforms. */
  apply(dt, x, y, z, yaw) {
    const k = 1 - Math.exp(-this.blendRate * dt);
    const pose = this.pose, target = this.target;
    for (let i = 0; i < pose.length; i++) pose[i] += (target[i] - pose[i]) * k;

    const bones = this.template.boneList;
    const s = this.scale;
    const rootBasis = this._rootBasis;
    mat3RotXYZ(rootBasis,
      this.rootRot[0] + (this.template.rootPitch || 0),
      yaw + this.rootRot[1],
      this.rootRot[2]);

    const baseY = y + (this.template.hipHeight * s) + this.rootOffset[1] * s;
    const off = this._vec;
    mat3Apply(rootBasis, this.rootOffset[0] * s, 0, this.rootOffset[2] * s, off);

    const wr = this.worldRot, wp = this.worldPos;
    const local = this._local;
    const localBind = this._localBind;

    for (let i = 0; i < bones.length; i++) {
      const b = bones[i];
      mat3RotXYZ(local, pose[i * 3], pose[i * 3 + 1], pose[i * 3 + 2]);
      if (b.hasBind) mat3Mul(localBind, b.bind, local);
      else localBind.set(local);

      const dst = wr.subarray(i * 9, i * 9 + 9);
      if (b.parent < 0) {
        mat3Mul(dst, rootBasis, localBind);
        wp[i * 3] = x + off[0];
        wp[i * 3 + 1] = baseY;
        wp[i * 3 + 2] = z + off[2];
      } else {
        const pr = wr.subarray(b.parent * 9, b.parent * 9 + 9);
        mat3Mul(dst, pr, localBind);
        mat3Apply(pr, b.offset[0] * s, b.offset[1] * s, b.offset[2] * s, off);
        wp[i * 3] = wp[b.parent * 3] + off[0];
        wp[i * 3 + 1] = wp[b.parent * 3 + 1] + off[1];
        wp[i * 3 + 2] = wp[b.parent * 3 + 2] + off[2];
      }
    }
  }

  /** Push every visible bone into an instanced box batch. */
  render(batch, palette, opts = {}) {
    const bones = this.template.boneList;
    const s = this.scale;
    const alpha = opts.alpha !== undefined ? opts.alpha : 1;
    const emissive = opts.emissive || 0;
    const tintR = opts.tintR !== undefined ? opts.tintR : 1;
    const tintG = opts.tintG !== undefined ? opts.tintG : 1;
    const tintB = opts.tintB !== undefined ? opts.tintB : 1;
    const basis = this._basis;
    const wr = this.worldRot;

    for (let i = 0; i < bones.length; i++) {
      if (this.hidden[i]) continue;
      const b = bones[i];
      const sy = b.len * s;
      const sw = b.w * s, sd = b.d * s;
      const o = i * 9;
      basis[0] = wr[o] * sw; basis[1] = wr[o + 1] * sw; basis[2] = wr[o + 2] * sw;
      basis[3] = wr[o + 3] * sy; basis[4] = wr[o + 4] * sy; basis[5] = wr[o + 5] * sy;
      basis[6] = wr[o + 6] * sd; basis[7] = wr[o + 7] * sd; basis[8] = wr[o + 8] * sd;

      const c = palette[b.mat] || palette[MAT.CLOTH] || [0.6, 0.6, 0.6];
      batch.pushMatrix(basis,
        this.worldPos[i * 3], this.worldPos[i * 3 + 1], this.worldPos[i * 3 + 2],
        c[0] * tintR, c[1] * tintG, c[2] * tintB,
        emissive, 0.92, alpha);
    }
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
