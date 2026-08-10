// ============================================================================
//  input.js — touch-first input with full keyboard/mouse and gamepad parity.
//
//  The left thumb drives a floating analogue stick that appears wherever the
//  finger lands; the right side is a camera surface with the action cluster
//  on top of it. Buttons are real DOM elements so they get native touch
//  handling, correct hit targets and CSS feedback for free.
// ============================================================================

export const ACTION = {
  ATTACK: 'attack',
  HEAVY: 'heavy',
  DODGE: 'dodge',
  GUARD: 'guard',
  INTERACT: 'interact',
  ITEM: 'item',
  SPELL: 'spell',
  LOCKON: 'lockon',
  JUMP: 'jump',
  SPRINT: 'sprint',
  SWITCH_ITEM: 'switchItem',
  SWITCH_SPELL: 'switchSpell',
  MENU: 'menu',
  MAP: 'map',
  TWOHAND: 'twohand',
};

let hapticsEnabled = true;

export function setHapticsEnabled(enabled) {
  hapticsEnabled = enabled !== false;
}

const KEY_MAP = {
  KeyW: 'up', ArrowUp: 'up',
  KeyS: 'down', ArrowDown: 'down',
  KeyA: 'left', ArrowLeft: 'left',
  KeyD: 'right', ArrowRight: 'right',
  Space: ACTION.DODGE,
  ShiftLeft: ACTION.SPRINT, ShiftRight: ACTION.SPRINT,
  KeyE: ACTION.INTERACT,
  KeyQ: ACTION.LOCKON,
  KeyR: ACTION.ITEM,
  KeyF: ACTION.SPELL,
  KeyC: ACTION.JUMP,
  KeyX: ACTION.SWITCH_ITEM,
  KeyZ: ACTION.SWITCH_SPELL,
  KeyV: ACTION.TWOHAND,
  Tab: ACTION.MENU,
  KeyM: ACTION.MAP,
  Escape: ACTION.MENU,
};

export class Input {
  constructor(surface) {
    this.surface = surface;
    this.move = { x: 0, y: 0 };
    this.moveMag = 0;
    this.look = { x: 0, y: 0 };
    this.lookAccum = { x: 0, y: 0 };

    this.down = new Set();
    this.justPressed = new Set();
    this.justReleased = new Set();
    this.holdTime = new Map();

    this.stick = null;          // { id, ox, oy, x, y }
    this.camTouch = null;       // { id, lastX, lastY, moved, startT }
    this.pointerLocked = false;
    this.sensitivity = 1.0;
    this.invertY = false;
    this.leftHanded = false;
    this.enabled = true;
    this.usingTouch = false;

    // Tiny, local usage counters drive the first-run tutorial. They contain no
    // personal data and never leave the device.
    this.usage = { move: 0, look: 0 };
    this.actionCounts = new Map();

    this._keys = new Set();
    this._bindings = [];
    this._buttonEls = new Map();

    this._installTouch();
    this._installKeyboard();
    this._installMouse();
  }

  // -------------------------------------------------------------------------

  press(action) {
    if (!this.down.has(action)) {
      this.down.add(action);
      this.justPressed.add(action);
      this.holdTime.set(action, 0);
      this.actionCounts.set(action, (this.actionCounts.get(action) || 0) + 1);
    }
  }

  release(action) {
    if (this.down.has(action)) {
      this.down.delete(action);
      this.justReleased.add(action);
    }
  }

  held(action) { return this.down.has(action); }
  pressed(action) { return this.justPressed.has(action); }
  released(action) { return this.justReleased.has(action); }
  heldFor(action) { return this.holdTime.get(action) || 0; }
  used(action) { return (this.actionCounts.get(action) || 0) > 0; }

  /** Consume a press so one tap cannot trigger two systems. */
  consume(action) { this.justPressed.delete(action); }

  endFrame(dt) {
    for (const a of this.down) this.holdTime.set(a, (this.holdTime.get(a) || 0) + dt);
    this.justPressed.clear();
    this.justReleased.clear();
    this.look.x = this.lookAccum.x;
    this.look.y = this.lookAccum.y;
    this.lookAccum.x = 0;
    this.lookAccum.y = 0;
  }

  /** Wire a DOM element to an action. */
  bindButton(el, action, opts = {}) {
    if (!el) return;
    this._buttonEls.set(action, el);
    const start = (e) => {
      if (!this.enabled) return;
      e.preventDefault();
      e.stopPropagation();
      this.usingTouch = true;
      this.press(action);
      el.classList.add('pressed');
      if (opts.haptic !== false) haptic(8);
    };
    const end = (e) => {
      e.preventDefault();
      e.stopPropagation();
      this.release(action);
      el.classList.remove('pressed');
    };
    el.addEventListener('touchstart', start, { passive: false });
    el.addEventListener('touchend', end, { passive: false });
    el.addEventListener('touchcancel', end, { passive: false });
    el.addEventListener('mousedown', start);
    window.addEventListener('mouseup', (e) => {
      if (this.down.has(action)) end(e);
    });
    el.addEventListener('contextmenu', (e) => e.preventDefault());
  }

  setButtonLabel(action, text) {
    const el = this._buttonEls.get(action);
    if (el) {
      const label = el.querySelector('.btn-label');
      if (label) label.textContent = text;
      else el.textContent = text;
    }
  }

  setButtonEnabled(action, on) {
    const el = this._buttonEls.get(action);
    if (el) el.classList.toggle('disabled', !on);
  }

  // -------------------------------------------------------------------------
  //  Touch
  // -------------------------------------------------------------------------

  _installTouch() {
    const el = this.surface;
    const stickRadius = () => Math.min(110, Math.max(70, window.innerHeight * 0.14));

    const onStart = (e) => {
      if (!this.enabled) return;
      this.usingTouch = true;
      for (const t of e.changedTouches) {
        const movementSide = this.leftHanded
          ? t.clientX > window.innerWidth * 0.56
          : t.clientX < window.innerWidth * 0.44;
        if (movementSide && !this.stick) {
          this.stick = { id: t.identifier, ox: t.clientX, oy: t.clientY, x: 0, y: 0 };
          this._showStick(t.clientX, t.clientY);
        } else if (!this.camTouch) {
          this.camTouch = {
            id: t.identifier, lastX: t.clientX, lastY: t.clientY,
            startX: t.clientX, startY: t.clientY, moved: 0, startT: performance.now(),
          };
        }
      }
      e.preventDefault();
    };

    const onMove = (e) => {
      if (!this.enabled) return;
      for (const t of e.changedTouches) {
        if (this.stick && t.identifier === this.stick.id) {
          const R = stickRadius();
          let dx = t.clientX - this.stick.ox;
          let dy = t.clientY - this.stick.oy;
          const d = Math.hypot(dx, dy);
          if (d > R) {
            // Drag the origin so the stick never feels stuck at the rim.
            this.stick.ox += dx * (1 - R / d);
            this.stick.oy += dy * (1 - R / d);
            dx *= R / d; dy *= R / d;
            this._showStick(this.stick.ox, this.stick.oy);
          }
          this.stick.x = dx / R;
          this.stick.y = dy / R;
          this._moveStickKnob(dx, dy);
        } else if (this.camTouch && t.identifier === this.camTouch.id) {
          const dx = t.clientX - this.camTouch.lastX;
          const dy = t.clientY - this.camTouch.lastY;
          this.camTouch.lastX = t.clientX;
          this.camTouch.lastY = t.clientY;
          this.camTouch.moved += Math.abs(dx) + Math.abs(dy);
          this.usage.look += Math.abs(dx) + Math.abs(dy);
          this.lookAccum.x += dx * 0.0055 * this.sensitivity;
          this.lookAccum.y += dy * 0.0045 * this.sensitivity * (this.invertY ? -1 : 1);
        }
      }
      e.preventDefault();
    };

    const onEnd = (e) => {
      for (const t of e.changedTouches) {
        if (this.stick && t.identifier === this.stick.id) {
          this.stick = null;
          this._hideStick();
        } else if (this.camTouch && t.identifier === this.camTouch.id) {
          this.camTouch = null;
        }
      }
    };

    el.addEventListener('touchstart', onStart, { passive: false });
    el.addEventListener('touchmove', onMove, { passive: false });
    el.addEventListener('touchend', onEnd, { passive: false });
    el.addEventListener('touchcancel', onEnd, { passive: false });
  }

  _showStick(x, y) {
    let base = this._stickEl;
    if (!base) {
      base = document.createElement('div');
      base.className = 'vstick';
      base.innerHTML = '<div class="vstick-knob"></div>';
      document.getElementById('touch-layer').appendChild(base);
      this._stickEl = base;
      this._knobEl = base.querySelector('.vstick-knob');
    }
    base.style.left = `${x}px`;
    base.style.top = `${y}px`;
    base.style.opacity = '1';
  }

  _moveStickKnob(dx, dy) {
    if (this._knobEl) this._knobEl.style.transform = `translate(${dx}px, ${dy}px)`;
  }

  _hideStick() {
    if (this._stickEl) {
      this._stickEl.style.opacity = '0';
      if (this._knobEl) this._knobEl.style.transform = 'translate(0,0)';
    }
  }

  // -------------------------------------------------------------------------
  //  Keyboard & mouse
  // -------------------------------------------------------------------------

  _installKeyboard() {
    window.addEventListener('keydown', (e) => {
      if (!this.enabled && e.code !== 'Escape') return;
      if (e.repeat) return;
      const a = KEY_MAP[e.code];
      if (a) {
        this._keys.add(e.code);
        this.press(a);
        if (e.code === 'Tab' || e.code === 'Space') e.preventDefault();
      }
    });
    window.addEventListener('keyup', (e) => {
      const a = KEY_MAP[e.code];
      if (a) {
        this._keys.delete(e.code);
        // Only release if no other key maps to the same action.
        let stillDown = false;
        for (const code of this._keys) if (KEY_MAP[code] === a) stillDown = true;
        if (!stillDown) this.release(a);
      }
    });
    window.addEventListener('blur', () => {
      this._keys.clear();
      for (const a of Array.from(this.down)) this.release(a);
      this.stick = null;
      this._hideStick();
    });
  }

  _installMouse() {
    const el = this.surface;
    el.addEventListener('mousedown', (e) => {
      if (!this.enabled) return;
      if (e.button === 0) this.press(ACTION.ATTACK);
      else if (e.button === 2) this.press(ACTION.GUARD);
      else if (e.button === 1) this.press(ACTION.HEAVY);
      if (!this.pointerLocked && this.allowPointerLock) {
        el.requestPointerLock?.();
      }
    });
    window.addEventListener('mouseup', (e) => {
      if (e.button === 0) this.release(ACTION.ATTACK);
      else if (e.button === 2) this.release(ACTION.GUARD);
      else if (e.button === 1) this.release(ACTION.HEAVY);
    });
    el.addEventListener('contextmenu', (e) => e.preventDefault());
    document.addEventListener('pointerlockchange', () => {
      this.pointerLocked = document.pointerLockElement === el;
    });
    window.addEventListener('mousemove', (e) => {
      if (!this.enabled) return;
      if (this.pointerLocked) {
        this.usage.look += Math.abs(e.movementX) + Math.abs(e.movementY);
        this.lookAccum.x += e.movementX * 0.0022 * this.sensitivity;
        this.lookAccum.y += e.movementY * 0.0020 * this.sensitivity * (this.invertY ? -1 : 1);
      }
    });
    window.addEventListener('wheel', (e) => {
      this.wheel = (this.wheel || 0) + Math.sign(e.deltaY);
    }, { passive: true });
  }

  // -------------------------------------------------------------------------

  /** Combine stick, keyboard and gamepad into a single movement vector. */
  sample() {
    let mx = 0, my = 0;
    if (this.stick) {
      mx = this.stick.x;
      my = this.stick.y;
    }
    if (this.down.has('left')) mx -= 1;
    if (this.down.has('right')) mx += 1;
    if (this.down.has('up')) my -= 1;
    if (this.down.has('down')) my += 1;

    const pads = navigator.getGamepads ? navigator.getGamepads() : [];
    for (const pad of pads) {
      if (!pad) continue;
      const ax = pad.axes[0] || 0, ay = pad.axes[1] || 0;
      if (Math.abs(ax) > 0.18) mx += ax;
      if (Math.abs(ay) > 0.18) my += ay;
      const rx = pad.axes[2] || 0, ry = pad.axes[3] || 0;
      this.usage.look += Math.abs(rx) + Math.abs(ry);
      if (Math.abs(rx) > 0.15) this.lookAccum.x += rx * 0.045 * this.sensitivity;
      if (Math.abs(ry) > 0.15) this.lookAccum.y += ry * 0.035 * this.sensitivity * (this.invertY ? -1 : 1);
      this._padButton(pad, 0, ACTION.DODGE);
      this._padButton(pad, 1, ACTION.INTERACT);
      this._padButton(pad, 2, ACTION.ITEM);
      this._padButton(pad, 3, ACTION.JUMP);
      this._padButton(pad, 4, ACTION.GUARD);
      this._padButton(pad, 5, ACTION.ATTACK);
      this._padButton(pad, 6, ACTION.SPELL);
      this._padButton(pad, 7, ACTION.HEAVY);
      this._padButton(pad, 10, ACTION.LOCKON);
      this._padButton(pad, 9, ACTION.MENU);
    }

    const mag = Math.hypot(mx, my);
    if (mag > 1) { mx /= mag; my /= mag; }
    this.move.x = mx;
    this.move.y = my;
    this.moveMag = Math.min(1, mag);
    if (this.moveMag > 0.08) this.usage.move += this.moveMag;
    return this.move;
  }

  _padButton(pad, index, action) {
    const b = pad.buttons[index];
    if (!b) return;
    if (b.pressed) this.press(action);
    else this.release(action);
  }
}

export function haptic(ms) {
  if (hapticsEnabled && navigator.vibrate) {
    try { navigator.vibrate(ms); } catch (e) { /* ignore */ }
  }
}
