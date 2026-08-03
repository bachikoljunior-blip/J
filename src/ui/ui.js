// ============================================================================
//  ui.js — HUD and menus, built as DOM over the canvas.
//
//  DOM rather than in-canvas UI is the right call on mobile: real text
//  rendering for Japanese, native scrolling in long lists, correct touch
//  targets, and accessibility for free. The only canvas in here is the world
//  map, which is genuinely an image.
// ============================================================================

import { STAT_NAMES, STAT_ORDER, CLASSES, levelCost } from '../game/player.js';
import {
  getItem, getSpell, WEAPONS, ARMOR, TALISMANS, CONSUMABLES, MATERIALS, SPELLS,
  weaponAttack, UPGRADE_COST, UPGRADE_MATERIAL, UPGRADE_MUL, RARITY_COLOR, RARITY_NAME,
  meetsRequirements,
} from '../game/items.js';
import { QUESTS, QUEST_BY_ID, QUEST_STATE, DIALOGUE, NPCS } from '../game/quests.js';
import { BIOME, BIOME_INFO, WORLD_SIZE, WORLD_HALF, GRID, WATER_LEVEL, REGIONS } from '../world/worldgen.js';
import { listSaves, deleteSave, formatPlaytime, saveSettings } from '../core/save.js';
import { ACTION, haptic } from '../core/input.js';
import { clamp, lerp, saturate, angleDelta } from '../core/math.js';

const $ = (id) => document.getElementById(id);
const el = (tag, cls, html) => {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (html !== undefined) e.innerHTML = html;
  return e;
};

export class UI {
  constructor() {
    this.game = null;
    this.overlay = $('overlay');
    this.hud = $('hud');
    this.controls = $('controls');
    this.notifications = $('notifications');
    this.screen = null;
    this.mapCanvas = null;
    this.mapReady = false;
    this._notifQueue = [];
    this._soulsPop = 0;
    this._regionTimer = 0;
    this._bossBarTarget = null;
    this._lootTimer = 0;
    this.onQualityChange = null;
    this._cache = {};
    this._damageLayer = $('damage-layer');
    this._damagePool = [];
  }

  attach(game) {
    this.game = game;
    this._bindControls();
    this._buildMapTexture();
  }

  // -------------------------------------------------------------------------
  //  Touch controls
  // -------------------------------------------------------------------------

  _bindControls() {
    const input = this.game.input;
    input.bindButton($('btn-attack'), ACTION.ATTACK);
    input.bindButton($('btn-heavy'), ACTION.HEAVY);
    input.bindButton($('btn-dodge'), ACTION.DODGE);
    input.bindButton($('btn-guard'), ACTION.GUARD);
    input.bindButton($('btn-interact'), ACTION.INTERACT);
    input.bindButton($('btn-item'), ACTION.ITEM);
    input.bindButton($('btn-spell'), ACTION.SPELL);
    input.bindButton($('btn-lock'), ACTION.LOCKON);
    input.bindButton($('btn-jump'), ACTION.JUMP);
    input.bindButton($('btn-switch-item'), ACTION.SWITCH_ITEM);
    input.bindButton($('btn-switch-spell'), ACTION.SWITCH_SPELL);

    $('btn-menu').addEventListener('click', (e) => {
      e.preventDefault();
      this.openPause();
    });
    $('btn-map').addEventListener('click', (e) => {
      e.preventDefault();
      this.openMap();
    });
    $('btn-flask').addEventListener('click', (e) => {
      e.preventDefault();
      this.game.player.drinkFlask('hp');
    });
    $('btn-flask-fp').addEventListener('click', (e) => {
      e.preventDefault();
      this.game.player.drinkFlask('fp');
    });
  }

  // -------------------------------------------------------------------------
  //  Per-frame HUD
  // -------------------------------------------------------------------------

  update(dt) {
    const g = this.game;
    if (!g || !g.player) return;
    const p = g.player;

    setBar('bar-hp', p.hp / p.maxHp);
    setBar('bar-fp', p.fp / p.maxFp);
    setBar('bar-stam', p.stamina / p.maxStamina);
    $('hp-text').textContent = `${Math.ceil(p.hp)}/${p.maxHp}`;

    // Delayed "chip" bar behind HP makes damage legible at a glance.
    this._chip = this._chip === undefined ? p.hp / p.maxHp : this._chip;
    const target = p.hp / p.maxHp;
    this._chip = target > this._chip ? target : lerp(this._chip, target, 1 - Math.exp(-2.2 * dt));
    setBar('bar-hp-chip', this._chip);

    $('souls-value').textContent = formatNumber(p.souls);
    $('flask-count').textContent = p.flaskHp.cur;
    $('flask-fp-count').textContent = p.flaskFp.cur;
    $('btn-flask').classList.toggle('empty', p.flaskHp.cur <= 0);
    $('btn-flask-fp').classList.toggle('empty', p.flaskFp.cur <= 0);

    // Quick item + spell readouts.
    const qid = p.quickItems[p.quickIndex];
    const qitem = qid ? getItem(qid) : null;
    $('quick-item-name').textContent = qitem ? qitem.name : '—';
    $('quick-item-count').textContent = qitem ? p.countItem(qid) : '';
    const sp = getSpell(p.spells[p.spellIndex]);
    $('quick-spell-name').textContent = sp ? sp.name : '—';
    $('quick-spell-cost').textContent = sp ? `${sp.fp}` : '';

    // Status build-up meters only appear when they matter.
    const st = $('status-meters');
    let statusHtml = '';
    for (const key in p.status) {
      const s = p.status[key];
      const label = key === 'poison' ? '毒' : key === 'frost' ? '凍傷' : '出血';
      if (s.active > 0) {
        statusHtml += `<div class="status-chip active ${key}">${label} ${Math.ceil(s.active)}s</div>`;
      } else if (s.build > 4) {
        statusHtml += `<div class="status-chip ${key}"><span style="width:${(s.build / s.threshold) * 100}%"></span>${label}</div>`;
      }
    }
    for (const b of p.buffs) {
      statusHtml += `<div class="status-chip buff">${buffLabel(b)} ${Math.ceil(b.t)}s</div>`;
    }
    if (st.innerHTML !== statusHtml) st.innerHTML = statusHtml;

    this._updateCompass(p);
    this._updateBossBar(dt);
    this._updateNotifications(dt);
    this._updateDamageNumbers();
    this._updateMiniMap(p);

    // Roll type & load indicator.
    const loadEl = $('load-indicator');
    const labels = { light: '軽装', medium: '中装', heavy: '重装', overload: '重量超過' };
    loadEl.textContent = labels[p.rollType];
    loadEl.className = `load-${p.rollType}`;

    // Lock-on reticle.
    const reticle = $('lock-reticle');
    if (p.lockTarget && !p.lockTarget.dead) {
      const sp2 = this._projectToScreen(p.lockTarget.x, p.lockTarget.y + p.lockTarget.height * 0.6, p.lockTarget.z);
      if (sp2) {
        reticle.style.display = 'block';
        reticle.style.left = `${sp2.x}px`;
        reticle.style.top = `${sp2.y}px`;
      } else reticle.style.display = 'none';
    } else reticle.style.display = 'none';

    // Enemy health bars for anything currently engaged with the player.
    this._updateEnemyBars(p);
  }

  _projectToScreen(x, y, z) {
    const cam = this.game.renderer.camera;
    const m = cam.viewProj;
    const w = m[3] * x + m[7] * y + m[11] * z + m[15];
    if (w <= 0.001) return null;
    const cx = (m[0] * x + m[4] * y + m[8] * z + m[12]) / w;
    const cy = (m[1] * x + m[5] * y + m[9] * z + m[13]) / w;
    if (cx < -1.2 || cx > 1.2 || cy < -1.2 || cy > 1.2) return null;
    return {
      x: (cx * 0.5 + 0.5) * window.innerWidth,
      y: (1 - (cy * 0.5 + 0.5)) * window.innerHeight,
    };
  }

  _updateEnemyBars(p) {
    const layer = $('enemy-bars');
    const shown = [];
    for (const e of this.game.enemies) {
      if (e.dead || e.isBoss) continue;
      if (e.hp >= e.maxHp && e !== p.lockTarget) continue;
      const d = Math.hypot(e.x - p.x, e.z - p.z);
      if (d > 24) continue;
      const s = this._projectToScreen(e.x, e.y + e.height + 0.32 * e.scale, e.z);
      if (!s) continue;
      shown.push({ e, s, d });
    }
    shown.sort((a, b) => a.d - b.d);
    const max = 8;
    while (layer.children.length < Math.min(shown.length, max)) {
      const bar = el('div', 'enemy-bar', '<span class="ebar-name"></span><span class="ebar-track"><i></i></span>');
      layer.appendChild(bar);
    }
    for (let i = 0; i < layer.children.length; i++) {
      const node = layer.children[i];
      if (i >= Math.min(shown.length, max)) { node.style.display = 'none'; continue; }
      const { e, s } = shown[i];
      node.style.display = 'block';
      node.style.left = `${s.x}px`;
      node.style.top = `${s.y}px`;
      node.querySelector('.ebar-name').textContent = e.isMiniBoss ? e.name : '';
      node.querySelector('.ebar-track i').style.width = `${clamp(e.hp / e.maxHp, 0, 1) * 100}%`;
      node.classList.toggle('elite', !!(e.isMiniBoss || e.isElite));
    }
  }

  _updateCompass(p) {
    const strip = $('compass-strip');
    const yaw = p.camera.yaw;
    const marks = [
      { a: 0, t: '北' }, { a: Math.PI / 2, t: '東' },
      { a: Math.PI, t: '南' }, { a: -Math.PI / 2, t: '西' },
    ];
    // Points of interest appear as ticks so the compass is a real navigation aid.
    const pois = [];
    for (const q of this.game.world.pois) {
      if (!q.discovered) continue;
      if (q.kind !== 'grace' && q.kind !== 'village' && q.kind !== 'boss') continue;
      const d = Math.hypot(q.x - p.x, q.z - p.z);
      if (d > 600) continue;
      pois.push({ a: Math.atan2(q.x - p.x, q.z - p.z), t: q.kind === 'grace' ? '◆' : q.kind === 'boss' ? '☠' : '⌂', d });
    }
    let html = '';
    for (const m of marks.concat(pois)) {
      const off = angleDelta(yaw, m.a);
      if (Math.abs(off) > 1.15) continue;
      const x = 50 + (off / 1.15) * 50;
      html += `<span style="left:${x}%">${m.t}</span>`;
    }
    if (strip.innerHTML !== html) strip.innerHTML = html;
  }

  _updateDamageNumbers() {
    const list = this.game.damageNumbers;
    const layer = this._damageLayer;
    while (layer.children.length < list.length) layer.appendChild(el('div', 'dmg'));
    for (let i = 0; i < layer.children.length; i++) {
      const node = layer.children[i];
      if (i >= list.length) { node.style.display = 'none'; continue; }
      const d = list[i];
      const s = this._projectToScreen(d.x, d.y, d.z);
      if (!s) { node.style.display = 'none'; continue; }
      node.style.display = 'block';
      node.style.left = `${s.x}px`;
      node.style.top = `${s.y}px`;
      node.style.opacity = clamp(d.t, 0, 1);
      node.textContent = Math.round(d.value);
      node.className = `dmg${d.crit ? ' crit' : ''}${d.blocked ? ' blocked' : ''}`;
    }
  }

  // -------------------------------------------------------------------------
  //  Mini map
  // -------------------------------------------------------------------------

  _buildMapTexture() {
    const world = this.game.world;
    const size = 512;
    const cvs = document.createElement('canvas');
    cvs.width = cvs.height = size;
    const ctx = cvs.getContext('2d');
    const img = ctx.createImageData(size, size);
    const step = GRID / size;

    for (let y = 0; y < size; y++) {
      for (let x = 0; x < size; x++) {
        const gx = Math.floor(x * step);
        const gz = Math.floor(y * step);
        const i = gz * GRID + gx;
        const h = world.height[i];
        const b = world.biome[i];
        let c = BIOME_INFO[b].ground;
        let r = c[0], g = c[1], bl = c[2];
        if (h < WATER_LEVEL) {
          const depth = clamp(-h / 22, 0, 1);
          r = lerp(0.16, 0.05, depth); g = lerp(0.30, 0.10, depth); bl = lerp(0.36, 0.18, depth);
        } else {
          // Hillshade from the west so relief reads.
          const hl = world.height[world.gridIndex(gx - 1, gz)];
          const hu = world.height[world.gridIndex(gx, gz - 1)];
          const shade = clamp(1 + ((h - hl) + (h - hu)) * 0.055, 0.55, 1.5);
          r *= shade; g *= shade; bl *= shade;
          const road = world.roadMask[i];
          if (road > 0.35) {
            r = lerp(r, 0.44, road); g = lerp(g, 0.36, road); bl = lerp(bl, 0.26, road);
          }
        }
        const o = (y * size + x) * 4;
        img.data[o] = clamp(r, 0, 1) * 255;
        img.data[o + 1] = clamp(g, 0, 1) * 255;
        img.data[o + 2] = clamp(bl, 0, 1) * 255;
        img.data[o + 3] = 255;
      }
    }
    ctx.putImageData(img, 0, 0);
    this.mapCanvas = cvs;
    this.mapReady = true;
  }

  _updateMiniMap(p) {
    const cvs = $('minimap');
    if (!cvs || !this.mapReady) return;
    const ctx = cvs.getContext('2d');
    const S = cvs.width;
    const worldSpan = 340;   // metres shown across the minimap
    const scale = (this.mapCanvas.width / WORLD_SIZE);
    const srcSpan = worldSpan * scale;
    const sx = (p.x + WORLD_HALF) * scale - srcSpan / 2;
    const sy = (p.z + WORLD_HALF) * scale - srcSpan / 2;

    ctx.save();
    ctx.clearRect(0, 0, S, S);
    ctx.beginPath();
    ctx.arc(S / 2, S / 2, S / 2 - 1, 0, Math.PI * 2);
    ctx.clip();
    ctx.drawImage(this.mapCanvas, sx, sy, srcSpan, srcSpan, 0, 0, S, S);

    // POI pins.
    for (const q of this.game.world.pois) {
      if (!q.discovered) continue;
      const dx = (q.x - p.x) / worldSpan * S;
      const dz = (q.z - p.z) / worldSpan * S;
      if (Math.hypot(dx, dz) > S / 2 - 6) continue;
      const px = S / 2 + dx, py = S / 2 + dz;
      ctx.fillStyle = poiColor(q.kind);
      ctx.beginPath();
      ctx.arc(px, py, q.kind === 'boss' ? 4 : 3, 0, Math.PI * 2);
      ctx.fill();
    }
    if (p.deathDrop) {
      const dx = (p.deathDrop.x - p.x) / worldSpan * S;
      const dz = (p.deathDrop.z - p.z) / worldSpan * S;
      if (Math.hypot(dx, dz) < S / 2 - 4) {
        ctx.fillStyle = '#ffb347';
        ctx.beginPath();
        ctx.arc(S / 2 + dx, S / 2 + dz, 3.5, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    // Player arrow.
    ctx.translate(S / 2, S / 2);
    ctx.rotate(p.camera.yaw);
    ctx.fillStyle = '#f4e8d0';
    ctx.beginPath();
    ctx.moveTo(0, -6);
    ctx.lineTo(4.5, 5);
    ctx.lineTo(0, 2.5);
    ctx.lineTo(-4.5, 5);
    ctx.closePath();
    ctx.fill();
    ctx.restore();
  }

  // -------------------------------------------------------------------------
  //  Notifications, banners
  // -------------------------------------------------------------------------

  pushNotification(text, kind = 'info') {
    const node = el('div', `notif notif-${kind}`, escapeHtml(text));
    this.notifications.appendChild(node);
    requestAnimationFrame(() => node.classList.add('in'));
    setTimeout(() => {
      node.classList.remove('in');
      setTimeout(() => node.remove(), 400);
    }, 2600);
  }

  _updateNotifications(dt) {
    if (this._soulsPop > 0) {
      this._soulsPop -= dt;
      $('souls-gain').style.opacity = clamp(this._soulsPop, 0, 1);
    }
    if (this._regionTimer > 0) {
      this._regionTimer -= dt;
      if (this._regionTimer <= 0) $('region-title').classList.remove('show');
    }
  }

  pushSouls(n) {
    const g = $('souls-gain');
    g.textContent = `+${formatNumber(n)}`;
    g.style.opacity = '1';
    this._soulsPop = 1.6;
  }

  showRegionTitle(name, blurb) {
    const node = $('region-title');
    node.innerHTML = `<h2>${escapeHtml(name)}</h2><p>${escapeHtml(blurb || '')}</p>`;
    node.classList.add('show');
    this._regionTimer = 4.5;
  }

  setInteractPrompt(text) {
    const node = $('interact-prompt');
    if (!text) { node.classList.remove('show'); return; }
    if (node.dataset.text !== text) {
      node.dataset.text = text;
      node.innerHTML = `<span class="key">調べる</span> ${escapeHtml(text)}`;
    }
    node.classList.add('show');
  }

  showLoot(lines) {
    if (!lines.length) return;
    const node = $('loot-popup');
    node.innerHTML = `<h4>入手</h4>${lines.map((l) => `<div>${escapeHtml(l)}</div>`).join('')}`;
    node.classList.add('show');
    clearTimeout(this._lootTO);
    this._lootTO = setTimeout(() => node.classList.remove('show'), 2800);
  }

  // -------------------------------------------------------------------------
  //  Boss bar
  // -------------------------------------------------------------------------

  showBossBar(boss) {
    this._bossBarTarget = boss;
    const node = $('boss-bar');
    node.querySelector('.boss-name').textContent = boss.name;
    node.classList.add('show');
    this._bossChip = 1;
  }

  hideBossBar() {
    this._bossBarTarget = null;
    $('boss-bar').classList.remove('show');
  }

  _updateBossBar(dt) {
    const b = this._bossBarTarget;
    if (!b) return;
    const node = $('boss-bar');
    const ratio = clamp(b.hp / b.maxHp, 0, 1);
    this._bossChip = ratio > this._bossChip ? ratio : lerp(this._bossChip, ratio, 1 - Math.exp(-1.8 * dt));
    node.querySelector('.boss-fill').style.width = `${ratio * 100}%`;
    node.querySelector('.boss-chip').style.width = `${this._bossChip * 100}%`;
  }

  showBossIntro(boss) {
    const def = boss.def;
    const node = $('boss-intro');
    node.innerHTML = `<h2>${escapeHtml(def.title)}</h2><p>${escapeHtml(def.subtitle)}</p>`;
    node.classList.add('show');
    setTimeout(() => node.classList.remove('show'), 3600);
  }

  showBossPhase(name) {
    const node = $('boss-intro');
    node.innerHTML = `<h3>${escapeHtml(name)}</h3>`;
    node.classList.add('show');
    setTimeout(() => node.classList.remove('show'), 2200);
  }

  showBossVictory(def, souls, reward) {
    const node = $('boss-victory');
    let extra = '';
    if (reward.item) {
      const it = getItem(reward.item);
      if (it) extra = `<p class="reward">${escapeHtml(it.name)} を手に入れた</p>`;
    }
    node.innerHTML = `<h2>撃破</h2><p>${escapeHtml(def.title)}</p>
      <p class="souls">残り火 ${formatNumber(souls)}</p>${extra}`;
    node.classList.add('show');
    setTimeout(() => node.classList.remove('show'), 5200);
  }

  showEnding() {
    this._openScreen('ending', `
      <div class="ending">
        <h1>残り火は、確かに継がれた</h1>
        <p>王冠は再び形を取り、灰は静かに降りやんだ。<br>
        だが刻印は消えない。次に目を覚ますのは、いつになるだろう。</p>
        <p class="stats">
          討伐した王：${this.game.bossesKilled.size} / 6<br>
          討った者：${this.game.killCount}<br>
          死んだ回数：${this.game.deaths}<br>
          旅の時間：${formatPlaytime(this.game.playtime)}
        </p>
        <button class="btn primary" data-action="continue-after-ending">世界に戻る</button>
      </div>
    `);
  }

  // -------------------------------------------------------------------------
  //  Screens
  // -------------------------------------------------------------------------

  get isOpen() { return !!this.screen; }

  _openScreen(name, html, opts = {}) {
    this.screen = name;
    this.overlay.className = `overlay open screen-${name}`;
    this.overlay.innerHTML = html;
    this.overlay.scrollTop = 0;
    this.game.paused = opts.pause !== false;
    this.game.input.enabled = false;
    document.body.classList.add('menu-open');
    this.overlay.onclick = (e) => this._handleClick(e);
    this.overlay.oninput = (e) => this._handleInput(e);
  }

  closeAll() {
    this.screen = null;
    this.overlay.className = 'overlay';
    this.overlay.innerHTML = '';
    this.game.paused = false;
    this.game.input.enabled = true;
    document.body.classList.remove('menu-open');
  }

  _handleInput(e) {
    const t = e.target;
    const action = t.dataset.input;
    if (!action) return;
    if (action === 'setting') {
      const key = t.dataset.key;
      const v = t.type === 'checkbox' ? t.checked : parseFloat(t.value);
      this.game.settings[key] = v;
      if (key === 'sensitivity') this.game.input.sensitivity = v;
      if (key === 'invertY') this.game.input.invertY = v;
      if (['master', 'music', 'sfx'].includes(key)) {
        this.game.audio.setVolumes({ [key]: v });
      }
      saveSettings(this.game.settings);
      const out = t.parentElement.querySelector('.range-value');
      if (out) out.textContent = typeof v === 'number' ? v.toFixed(2) : v;
    }
  }

  _handleClick(e) {
    const btn = e.target.closest('[data-action]');
    if (!btn) return;
    e.preventDefault();
    const a = btn.dataset.action;
    const g = this.game;
    g.audio.playUI(a === 'close' || a === 'back' ? 'cancel' : 'click');
    haptic(8);

    switch (a) {
      case 'close': this.closeAll(); break;
      case 'tab': this._pauseTab = btn.dataset.tab; this.openPause(); break;
      case 'levelup': {
        const stat = btn.dataset.stat;
        if (g.player.levelUp(stat)) {
          g.audio.playLevelUp();
          this.openLevelUp();
        } else {
          g.audio.playUI('error');
        }
        break;
      }
      case 'grace-level': this.openLevelUp(); break;
      case 'grace-travel': this.openFastTravel(); break;
      case 'grace-rest': this.closeAll(); break;
      case 'travel-to': {
        const poi = g.world.pois.find((q) => q.id === btn.dataset.poi);
        if (poi) { g.warpToGrace(poi); }
        break;
      }
      case 'equip': this._doEquip(btn.dataset.item, btn.dataset.slot); break;
      case 'unequip': g.player.unequip(btn.dataset.kind, parseInt(btn.dataset.index || '0', 10)); this.openPause(); break;
      case 'use-item': {
        const item = getItem(btn.dataset.item);
        if (item && g.player.countItem(item.id) > 0) {
          g.player.removeItem(item.id, 1);
          g.player.applyConsumable(item);
          this.openPause();
        }
        break;
      }
      case 'select-spell': g.player.spellIndex = parseInt(btn.dataset.index, 10); this.openPause(); break;
      case 'dialogue-option': this._dialogueOption(parseInt(btn.dataset.index, 10)); break;
      case 'dialogue-close': g.closeDialogue(); this.closeAll(); break;
      case 'shop-buy': this._buy(btn.dataset.item); break;
      case 'shop-sell': this._sell(btn.dataset.item); break;
      case 'smith-upgrade': this._upgrade(btn.dataset.item); break;
      case 'respawn': g.respawnPlayer(); this.closeAll(); break;
      case 'save': g.save(parseInt(btn.dataset.slot, 10)); this.openPause(); break;
      case 'quality': {
        g.applyQuality(btn.dataset.q);
        this.openSettings();
        break;
      }
      case 'to-title': location.reload(); break;
      case 'continue-after-ending': this.closeAll(); break;
      case 'open-map': this.openMap(); break;
      case 'open-settings': this.openSettings(); break;
      case 'back': this.openPause(); break;
      default: break;
    }
  }

  _doEquip(id, slot) {
    const g = this.game;
    g.player.equipItem(id, slot);
    g.audio.playUI('confirm');
    this.openPause();
  }

  // -------------------------------------------------------------------------
  //  Pause / status screens
  // -------------------------------------------------------------------------

  openPause() {
    const tab = this._pauseTab || 'status';
    const g = this.game;
    const p = g.player;
    const tabs = [
      ['status', 'ステータス'], ['equip', '装備'], ['items', '道具'],
      ['magic', '魔法'], ['quests', 'クエスト'], ['system', 'システム'],
    ];
    const tabHtml = tabs.map(([id, label]) =>
      `<button class="tab${tab === id ? ' active' : ''}" data-action="tab" data-tab="${id}">${label}</button>`).join('');

    let body = '';
    if (tab === 'status') body = this._statusBody(p);
    else if (tab === 'equip') body = this._equipBody(p);
    else if (tab === 'items') body = this._itemsBody(p);
    else if (tab === 'magic') body = this._magicBody(p);
    else if (tab === 'quests') body = this._questsBody(g);
    else if (tab === 'system') body = this._systemBody(g);

    this._openScreen('pause', `
      <div class="panel wide">
        <div class="panel-head">
          <h2>${escapeHtml(p.name)} <small>Lv.${p.playerLevel} ${escapeHtml(g.className)}</small></h2>
          <button class="icon-btn" data-action="close">✕</button>
        </div>
        <div class="tabs">${tabHtml}</div>
        <div class="panel-body">${body}</div>
      </div>
    `);
  }

  _statusBody(p) {
    const rows = STAT_ORDER.map((k) =>
      `<div class="stat-row"><span>${STAT_NAMES[k]}</span><b>${p.stats[k]}</b></div>`).join('');
    const atk = weaponAttack(p.rightHand, p.upgradeLevelOf(p.rightHand), p.stats);
    return `
      <div class="cols">
        <div class="col">
          <h3>能力値</h3>
          ${rows}
          <div class="stat-row total"><span>次のレベル</span><b>${formatNumber(levelCost(p.playerLevel))}</b></div>
        </div>
        <div class="col">
          <h3>派生</h3>
          <div class="stat-row"><span>HP</span><b>${Math.ceil(p.hp)} / ${p.maxHp}</b></div>
          <div class="stat-row"><span>FP</span><b>${Math.ceil(p.fp)} / ${p.maxFp}</b></div>
          <div class="stat-row"><span>スタミナ</span><b>${Math.round(p.maxStamina)}</b></div>
          <div class="stat-row"><span>攻撃力</span><b>${Math.round(atk.physical)}${atk.element > 0 ? ` + ${Math.round(atk.element)}` : ''}</b></div>
          <div class="stat-row"><span>防御力</span><b>${Math.round(p.defense)}</b></div>
          <div class="stat-row"><span>強靭度</span><b>${Math.round(p.maxPoise)}</b></div>
          <div class="stat-row"><span>装備重量</span><b>${p.equipLoad.toFixed(1)} / ${p.maxLoad.toFixed(1)}</b></div>
          <div class="stat-row"><span>ローリング</span><b>${{ light: '軽量', medium: '中量', heavy: '重量', overload: '超過' }[p.rollType]}</b></div>
          <div class="stat-row"><span>残り火</span><b>${formatNumber(p.souls)}</b></div>
        </div>
      </div>
      <div class="hint">篝火（休息）で残り火を使ってレベルを上げられる。</div>
    `;
  }

  _equipBody(p) {
    const slotRow = (label, item, kind, index) => `
      <div class="equip-slot">
        <span class="slot-label">${label}</span>
        <span class="slot-item" style="color:${item ? RARITY_COLOR[item.rarity || 1] : '#666'}">
          ${item ? escapeHtml(item.name) + (p.upgradeLevelOf(item) ? ` +${p.upgradeLevelOf(item)}` : '') : '—'}
        </span>
        ${item ? `<button class="mini-btn" data-action="unequip" data-kind="${kind}" data-index="${index}">外す</button>` : ''}
      </div>`;

    const owned = [];
    for (const [id, n] of p.inventory) {
      const it = getItem(id);
      if (!it) continue;
      if (it.kind === 'weapon' || it.kind === 'armor' || it.kind === 'talisman') owned.push(it);
    }
    owned.sort((a, b) => (a.kind || '').localeCompare(b.kind) || (b.rarity || 1) - (a.rarity || 1));

    const list = owned.map((it) => {
      const eq = isEquipped(p, it);
      const ok = it.kind !== 'weapon' || meetsRequirements(it, p.stats);
      const slot = it.class === 'shield' ? 'left' : it.kind === 'weapon' ? 'right' : undefined;
      return `<button class="item-row${eq ? ' equipped' : ''}${ok ? '' : ' locked'}"
        data-action="equip" data-item="${it.id}" ${slot ? `data-slot="${slot}"` : ''}>
        <span class="name" style="color:${RARITY_COLOR[it.rarity || 1]}">${escapeHtml(it.name)}</span>
        <span class="meta">${itemMeta(it, p)}</span>
        <span class="desc">${escapeHtml(it.desc || '')}</span>
      </button>`;
    }).join('') || '<div class="empty">装備できるものがない</div>';

    return `
      <div class="cols">
        <div class="col">
          <h3>装備中</h3>
          ${slotRow('右手', p.equip.right[0], 'right', 0)}
          ${slotRow('右手2', p.equip.right[1], 'right', 1)}
          ${slotRow('左手', p.equip.left[0], 'left', 0)}
          ${slotRow('左手2', p.equip.left[1], 'left', 1)}
          ${slotRow('頭', p.equip.head, 'head', 0)}
          ${slotRow('胴', p.equip.body, 'body', 0)}
          ${slotRow('腕', p.equip.arms, 'arms', 0)}
          ${slotRow('脚', p.equip.legs, 'legs', 0)}
          ${slotRow('護符1', p.equip.talismans[0], 'talisman', 0)}
          ${slotRow('護符2', p.equip.talismans[1], 'talisman', 1)}
          ${slotRow('護符3', p.equip.talismans[2], 'talisman', 2)}
          ${slotRow('護符4', p.equip.talismans[3], 'talisman', 3)}
        </div>
        <div class="col scroll">
          <h3>所持品</h3>
          ${list}
        </div>
      </div>`;
  }

  _itemsBody(p) {
    const groups = { consumable: [], material: [], key: [] };
    for (const [id, n] of p.inventory) {
      const it = getItem(id);
      if (!it) continue;
      if (groups[it.kind]) groups[it.kind].push([it, n]);
    }
    const section = (title, arr, usable) => `
      <h3>${title}</h3>
      ${arr.length ? arr.map(([it, n]) => `
        <div class="item-row static">
          <span class="name">${escapeHtml(it.name)}</span>
          <span class="meta">×${n}</span>
          <span class="desc">${escapeHtml(it.desc || '')}</span>
          ${usable && !it.flask ? `<button class="mini-btn" data-action="use-item" data-item="${it.id}">使う</button>` : ''}
        </div>`).join('') : '<div class="empty">なし</div>'}`;
    return `<div class="scroll-body">
      ${section('消耗品', groups.consumable, true)}
      ${section('素材', groups.material, false)}
      ${section('重要アイテム', groups.key, false)}
    </div>`;
  }

  _magicBody(p) {
    if (!p.spells.length) return '<div class="empty">覚えている魔法がない</div>';
    return `<div class="scroll-body">${p.spells.map((id, i) => {
      const s = getSpell(id);
      if (!s) return '';
      const ok = Object.keys(s.req || {}).every((k) => p.stats[k] >= s.req[k]);
      return `<button class="item-row${p.spellIndex === i ? ' equipped' : ''}${ok ? '' : ' locked'}"
        data-action="select-spell" data-index="${i}">
        <span class="name">${escapeHtml(s.name)}</span>
        <span class="meta">FP ${s.fp} / ${s.school === 'int' ? '理力' : '信仰'} ${Object.values(s.req || {})[0] || 0}</span>
        <span class="desc">${escapeHtml(s.desc)}</span>
      </button>`;
    }).join('')}</div>`;
  }

  _questsBody(g) {
    const active = [], done = [];
    for (const q of QUESTS) {
      const s = g.quests.get(q.id);
      if (!s) continue;
      if (s.status === QUEST_STATE.ACTIVE) active.push([q, s]);
      else if (s.status === QUEST_STATE.DONE) done.push([q, s]);
    }
    const render = ([q, s]) => {
      const step = q.steps[s.step];
      const counterKey = step ? `${step.id}_count` : null;
      const count = counterKey && s.counters[counterKey] !== undefined
        ? ` (${s.counters[counterKey]}/${step.count || 1})` : '';
      return `<div class="quest${q.main ? ' main' : ''}">
        <h4>${q.main ? '【主】' : ''}${escapeHtml(q.name)}</h4>
        <p>${escapeHtml(q.summary)}</p>
        ${step ? `<div class="quest-step">▸ ${escapeHtml(step.text)}${count}</div>` : '<div class="quest-step done">完了</div>'}
      </div>`;
    };
    return `<div class="scroll-body">
      <h3>進行中</h3>
      ${active.length ? active.map(render).join('') : '<div class="empty">なし</div>'}
      <h3>完了</h3>
      ${done.length ? done.map(([q]) => `<div class="quest done"><h4>${escapeHtml(q.name)}</h4></div>`).join('') : '<div class="empty">なし</div>'}
    </div>`;
  }

  _systemBody(g) {
    const saves = listSaves();
    return `<div class="scroll-body">
      <h3>セーブ</h3>
      ${saves.map((s, i) => `
        <div class="save-row">
          <span>${s ? `スロット${i + 1}：Lv.${s.level} ${escapeHtml(s.className)} / ${formatPlaytime(s.playtime)}` : `スロット${i + 1}：空`}</span>
          <button class="mini-btn" data-action="save" data-slot="${i}">保存</button>
        </div>`).join('')}
      <h3>その他</h3>
      <button class="btn" data-action="open-map">地図を開く</button>
      <button class="btn" data-action="open-settings">設定</button>
      <button class="btn danger" data-action="to-title">タイトルへ戻る</button>
      <div class="hint">進行状況は篝火での休息時に自動保存されない。手動で保存すること。</div>
    </div>`;
  }

  // -------------------------------------------------------------------------
  //  Grace / level up / travel
  // -------------------------------------------------------------------------

  openGrace(poi) {
    this._openScreen('grace', `
      <div class="panel">
        <div class="panel-head"><h2>${escapeHtml(poi.name)}</h2></div>
        <div class="panel-body center">
          <p class="flavor">火は小さいが、確かに燃えている。</p>
          <button class="btn primary" data-action="grace-level">レベルアップ</button>
          <button class="btn" data-action="grace-travel">篝火を渡る</button>
          <button class="btn" data-action="grace-rest">立ち上がる</button>
        </div>
      </div>`, { pause: false });
  }

  closeGrace() {
    if (this.screen === 'grace' || this.screen === 'levelup' || this.screen === 'travel') this.closeAll();
  }

  openLevelUp() {
    const p = this.game.player;
    const cost = levelCost(p.playerLevel);
    const rows = STAT_ORDER.map((k) => `
      <button class="stat-up${p.souls >= cost ? '' : ' locked'}" data-action="levelup" data-stat="${k}">
        <span>${STAT_NAMES[k]}</span>
        <b>${p.stats[k]}</b>
        <i>→ ${p.stats[k] + 1}</i>
      </button>`).join('');
    this._openScreen('levelup', `
      <div class="panel">
        <div class="panel-head">
          <h2>レベルアップ</h2>
          <button class="icon-btn" data-action="close">✕</button>
        </div>
        <div class="panel-body">
          <div class="level-summary">
            <div>現在 Lv.<b>${p.playerLevel}</b></div>
            <div>必要 <b>${formatNumber(cost)}</b></div>
            <div>所持 <b class="${p.souls >= cost ? 'ok' : 'ng'}">${formatNumber(p.souls)}</b></div>
          </div>
          <div class="stat-grid">${rows}</div>
        </div>
      </div>`, { pause: false });
  }

  openFastTravel() {
    const g = this.game;
    const list = g.world.graces.filter((q) => q.discovered);
    const rows = list.map((q) => {
      const region = REGIONS.find((r) => r.id === q.region);
      return `<button class="item-row" data-action="travel-to" data-poi="${q.id}">
        <span class="name">${escapeHtml(q.name)}</span>
        <span class="meta">${escapeHtml(region ? region.name : '')}</span>
      </button>`;
    }).join('') || '<div class="empty">まだ他の篝火を見つけていない</div>';
    this._openScreen('travel', `
      <div class="panel">
        <div class="panel-head"><h2>篝火を渡る</h2><button class="icon-btn" data-action="close">✕</button></div>
        <div class="panel-body scroll">${rows}</div>
      </div>`, { pause: false });
  }

  // -------------------------------------------------------------------------
  //  Map
  // -------------------------------------------------------------------------

  openMap() {
    this._openScreen('map', `
      <div class="panel wide">
        <div class="panel-head"><h2>アルドラス</h2><button class="icon-btn" data-action="close">✕</button></div>
        <div class="map-wrap"><canvas id="worldmap"></canvas></div>
        <div class="map-legend">
          <span><i style="background:#ffb347"></i>篝火</span>
          <span><i style="background:#8fd4ff"></i>村</span>
          <span><i style="background:#ff6f6f"></i>ボス</span>
          <span><i style="background:#d8c48a"></i>宝箱</span>
          <span><i style="background:#b18cff"></i>祠</span>
          <span><i style="background:#f4e8d0"></i>現在地</span>
        </div>
      </div>`);
    this._drawWorldMap();
  }

  _drawWorldMap() {
    const cvs = $('worldmap');
    if (!cvs || !this.mapReady) return;
    const wrap = cvs.parentElement;
    const size = Math.min(wrap.clientWidth, wrap.clientHeight) || 320;
    cvs.width = size;
    cvs.height = size;
    const ctx = cvs.getContext('2d');
    ctx.imageSmoothingEnabled = true;
    ctx.drawImage(this.mapCanvas, 0, 0, size, size);

    const toXY = (x, z) => ({
      x: (x + WORLD_HALF) / WORLD_SIZE * size,
      y: (z + WORLD_HALF) / WORLD_SIZE * size,
    });

    // Region labels.
    ctx.font = `${Math.max(10, size * 0.028)}px system-ui, sans-serif`;
    ctx.textAlign = 'center';
    ctx.fillStyle = 'rgba(240,230,210,0.72)';
    ctx.shadowColor = 'rgba(0,0,0,0.85)';
    ctx.shadowBlur = 4;
    for (const r of REGIONS) {
      const q = toXY(r.cx, r.cz);
      ctx.fillText(r.name, q.x, q.y);
    }
    ctx.shadowBlur = 0;

    for (const q of this.game.world.pois) {
      if (!q.discovered) continue;
      const s = toXY(q.x, q.z);
      ctx.fillStyle = poiColor(q.kind);
      ctx.beginPath();
      ctx.arc(s.x, s.y, q.kind === 'boss' || q.kind === 'village' ? size * 0.010 : size * 0.007, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = 'rgba(0,0,0,0.6)';
      ctx.lineWidth = 1;
      ctx.stroke();
    }

    const p = this.game.player;
    const ps = toXY(p.x, p.z);
    ctx.save();
    ctx.translate(ps.x, ps.y);
    ctx.rotate(p.camera.yaw);
    ctx.fillStyle = '#f4e8d0';
    ctx.strokeStyle = 'rgba(0,0,0,0.8)';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(0, -size * 0.018);
    ctx.lineTo(size * 0.013, size * 0.015);
    ctx.lineTo(0, size * 0.008);
    ctx.lineTo(-size * 0.013, size * 0.015);
    ctx.closePath();
    ctx.fill();
    ctx.stroke();
    ctx.restore();

    if (p.deathDrop) {
      const d = toXY(p.deathDrop.x, p.deathDrop.z);
      ctx.fillStyle = '#ffb347';
      ctx.beginPath();
      ctx.arc(d.x, d.y, size * 0.008, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  // -------------------------------------------------------------------------
  //  Dialogue, shop, smith
  // -------------------------------------------------------------------------

  openDialogue(dlg) {
    this._renderDialogue();
  }

  closeDialogue() {
    if (this.screen === 'dialogue') this.closeAll();
  }

  _renderDialogue() {
    const g = this.game;
    const d = g.dialogue;
    if (!d) return;
    const node = d.tree[d.node];
    if (!node) { g.closeDialogue(); this.closeAll(); return; }
    const ctx = { q: g.quests, p: g.player, g };
    const text = typeof node.text === 'function' ? node.text(ctx) : node.text;
    const options = (node.options || []).filter((o) => !o.cond || o.cond(ctx));
    this._dialogueOptions = options;

    this._openScreen('dialogue', `
      <div class="dialogue">
        <div class="speaker">${escapeHtml(d.npc.name)}</div>
        <div class="dtext">${escapeHtml(text)}</div>
        <div class="doptions">
          ${options.map((o, i) => `<button class="dopt" data-action="dialogue-option" data-index="${i}">${escapeHtml(o.text)}</button>`).join('')}
        </div>
      </div>`, { pause: false });
  }

  _dialogueOption(index) {
    const g = this.game;
    const opt = this._dialogueOptions[index];
    if (!opt) return;
    if (opt.goto) {
      g.dialogue.node = opt.goto;
      this._renderDialogue();
      return;
    }
    const a = opt.action;
    if (a === 'close') { g.closeDialogue(); this.closeAll(); return; }
    if (a === 'shop') { this.openShop(g.dialogue.npc); return; }
    if (a === 'sell') { this.openShop(g.dialogue.npc, true); return; }
    if (a === 'smith') { this.openSmith(); return; }
    if (a && a.startsWith('accept_')) {
      const questId = a.replace('accept_', '').replace('main1', 'main_1').replace('main3', 'main_3');
      const id = questId.startsWith('side_') || questId.startsWith('main_') ? questId : `side_${questId}`;
      if (g.quests.start(id)) {
        const q = QUEST_BY_ID.get(id);
        g.notify(`クエスト受注：${q ? q.name : id}`, 'good');
      }
      g.quests.notify({ type: 'talk', npc: g.dialogue.npc.npcId });
      g.closeDialogue();
      this.closeAll();
      return;
    }
    if (a && a.startsWith('complete_')) {
      const id = a.replace('complete_', '');
      this._completeQuest(id);
      g.closeDialogue();
      this.closeAll();
      return;
    }
    g.closeDialogue();
    this.closeAll();
  }

  _completeQuest(id) {
    const g = this.game;
    const q = QUEST_BY_ID.get(id);
    const s = g.quests.get(id);
    if (!q || !s) return;
    if (q.steps[s.step] && q.steps[s.step].type === 'deliver') {
      const step = q.steps[s.step];
      if (g.player.countItem(step.target) < (step.count || 1)) {
        g.notify('必要なものが足りない', 'bad');
        return;
      }
      g.player.removeItem(step.target, step.count || 1);
    }
    const r = g.quests.advance(id);
    const rewards = q.rewards || {};
    if (rewards.souls) {
      const n = g.player.gainSouls(rewards.souls);
      this.pushSouls(n);
    }
    for (const [itemId, n] of rewards.items || []) g.player.addItem(itemId, n);
    if (rewards.spell) g.player.learnSpell(rewards.spell);
    if (rewards.unlock) g.quests.setFlag(rewards.unlock);
    if (rewards.flaskUp) {
      const f = rewards.flaskUp === 'fp' ? g.player.flaskFp : g.player.flaskHp;
      f.max++; f.cur = f.max;
      g.notify('聖杯瓶の使用回数が増えた', 'good');
    }
    g.audio.playLevelUp();
    g.notify(`クエスト達成：${q.name}`, 'good');
    if (q.next) g.quests.start(q.next);
  }

  openShop(npc, sellMode = false) {
    const g = this.game;
    const p = g.player;
    const def = npc.npcDef;
    let stock = (def.stock || []).slice();
    if (g.quests.hasFlag('merchant_tier2')) stock = stock.concat(def.stockTier2 || []);

    const buyList = stock.map((id) => {
      const it = getItem(id) || getSpell(id);
      if (!it) return '';
      const price = Math.round((it.value || 200) * 1.4);
      const can = p.souls >= price;
      return `<button class="item-row${can ? '' : ' locked'}" data-action="shop-buy" data-item="${id}">
        <span class="name" style="color:${RARITY_COLOR[it.rarity || 1]}">${escapeHtml(it.name)}</span>
        <span class="meta price">${formatNumber(price)}</span>
        <span class="desc">${escapeHtml(it.desc || '')}</span>
      </button>`;
    }).join('');

    const sellable = [];
    for (const [id, n] of p.inventory) {
      const it = getItem(id);
      if (!it || it.kind === 'key' || it.flask) continue;
      if (isEquipped(p, it)) continue;
      sellable.push([it, n]);
    }
    const sellList = sellable.map(([it, n]) => `
      <button class="item-row" data-action="shop-sell" data-item="${it.id}">
        <span class="name">${escapeHtml(it.name)}</span>
        <span class="meta price">${formatNumber(Math.round((it.value || 100) * 0.35))} ×${n}</span>
      </button>`).join('') || '<div class="empty">売れるものがない</div>';

    this._openScreen('shop', `
      <div class="panel wide">
        <div class="panel-head">
          <h2>${escapeHtml(npc.name)}</h2>
          <span class="souls-head">残り火 ${formatNumber(p.souls)}</span>
          <button class="icon-btn" data-action="dialogue-close">✕</button>
        </div>
        <div class="panel-body cols">
          <div class="col scroll"><h3>買う</h3>${buyList}</div>
          <div class="col scroll"><h3>売る</h3>${sellList}</div>
        </div>
      </div>`);
  }

  _buy(id) {
    const g = this.game;
    const p = g.player;
    const it = getItem(id) || getSpell(id);
    if (!it) return;
    const price = Math.round((it.value || 200) * 1.4);
    if (p.souls < price) { g.audio.playUI('error'); g.notify('残り火が足りない', 'bad'); return; }
    p.souls -= price;
    if (getSpell(id)) p.learnSpell(id);
    else p.addItem(id, 1);
    g.audio.playUI('confirm');
    g.notify(`${it.name} を購入`, 'loot');
    const npc = g.dialogue?.npc;
    if (npc) this.openShop(npc);
  }

  _sell(id) {
    const g = this.game;
    const p = g.player;
    const it = getItem(id);
    if (!it || p.countItem(id) <= 0) return;
    p.removeItem(id, 1);
    p.souls += Math.round((it.value || 100) * 0.35);
    g.audio.playUI('confirm');
    const npc = g.dialogue?.npc;
    if (npc) this.openShop(npc);
  }

  openSmith() {
    const g = this.game;
    const p = g.player;
    const maxTier = g.quests.hasFlag('smith_tier2') ? 10 : 6;
    const weapons = [];
    for (const [id] of p.inventory) {
      const it = getItem(id);
      if (it && it.kind === 'weapon') weapons.push(it);
    }
    const rows = weapons.map((w) => {
      const lvl = p.upgradeLevelOf(w);
      const next = lvl + 1;
      const capped = next > maxTier;
      const cost = UPGRADE_COST[Math.min(next, UPGRADE_COST.length - 1)];
      const matTier = next <= 4 ? 'mat_shard' : next <= 7 ? 'mat_chunk' : next <= 9 ? 'mat_core' : 'mat_emberheart';
      const matN = UPGRADE_MATERIAL[Math.min(next, UPGRADE_MATERIAL.length - 1)];
      const mat = getItem(matTier);
      const can = !capped && p.souls >= cost && p.countItem(matTier) >= matN && next < UPGRADE_MUL.length;
      const atkNow = weaponAttack(w, lvl, p.stats);
      const atkNext = weaponAttack(w, Math.min(next, UPGRADE_MUL.length - 1), p.stats);
      return `<button class="item-row${can ? '' : ' locked'}" data-action="smith-upgrade" data-item="${w.id}">
        <span class="name">${escapeHtml(w.name)} +${lvl}</span>
        <span class="meta">${Math.round(atkNow.total)} → ${Math.round(atkNext.total)}</span>
        <span class="desc">${capped ? '炉の火が足りない' : `残り火 ${formatNumber(cost)} / ${mat.name} ×${matN}（所持 ${p.countItem(matTier)}）`}</span>
      </button>`;
    }).join('') || '<div class="empty">強化できる武器がない</div>';

    this._openScreen('smith', `
      <div class="panel">
        <div class="panel-head">
          <h2>鍛冶</h2>
          <span class="souls-head">残り火 ${formatNumber(p.souls)}</span>
          <button class="icon-btn" data-action="dialogue-close">✕</button>
        </div>
        <div class="panel-body scroll">${rows}</div>
      </div>`);
  }

  _upgrade(id) {
    const g = this.game;
    const p = g.player;
    const w = getItem(id);
    if (!w) return;
    const lvl = p.upgradeLevelOf(w);
    const next = lvl + 1;
    if (next >= UPGRADE_MUL.length) { g.audio.playUI('error'); return; }
    const maxTier = g.quests.hasFlag('smith_tier2') ? 10 : 6;
    if (next > maxTier) { g.notify('炉の火が足りない', 'bad'); g.audio.playUI('error'); return; }
    const cost = UPGRADE_COST[next];
    const matTier = next <= 4 ? 'mat_shard' : next <= 7 ? 'mat_chunk' : next <= 9 ? 'mat_core' : 'mat_emberheart';
    const matN = UPGRADE_MATERIAL[next];
    if (p.souls < cost || p.countItem(matTier) < matN) {
      g.audio.playUI('error');
      g.notify('素材か残り火が足りない', 'bad');
      return;
    }
    p.souls -= cost;
    p.removeItem(matTier, matN);
    p.setUpgrade(w.id, next);
    g.audio.playLevelUp();
    g.notify(`${w.name} を +${next} に強化した`, 'good');
    this.openSmith();
  }

  // -------------------------------------------------------------------------
  //  Death / settings
  // -------------------------------------------------------------------------

  showDeath() {
    this._openScreen('death', `
      <div class="death">
        <h1>死　亡</h1>
        <p>残り火を落とした。倒れた場所に戻れば、取り戻せる。</p>
        <button class="btn primary" data-action="respawn">篝火で目を覚ます</button>
      </div>`);
  }

  openSettings() {
    const g = this.game;
    const s = g.settings;
    const qBtn = (id, label) => `<button class="chip${s.quality === id ? ' active' : ''}" data-action="quality" data-q="${id}">${label}</button>`;
    this._openScreen('settings', `
      <div class="panel">
        <div class="panel-head"><h2>設定</h2><button class="icon-btn" data-action="back">戻る</button></div>
        <div class="panel-body scroll">
          <h3>グラフィック</h3>
          <div class="chips">${qBtn('low', '低')}${qBtn('medium', '中')}${qBtn('high', '高')}</div>
          <div class="hint">端末の性能に応じて描画解像度は自動調整されます（現在 ${Math.round(g.dynamicScale * 100)}%）。</div>

          <h3>操作</h3>
          <label class="range">カメラ感度
            <input type="range" min="0.3" max="2.5" step="0.05" value="${s.sensitivity}" data-input="setting" data-key="sensitivity">
            <span class="range-value">${s.sensitivity.toFixed(2)}</span>
          </label>
          <label class="check"><input type="checkbox" ${s.invertY ? 'checked' : ''} data-input="setting" data-key="invertY"> Y軸反転</label>
          <label class="check"><input type="checkbox" ${s.showDamage ? 'checked' : ''} data-input="setting" data-key="showDamage"> ダメージ表示</label>

          <h3>音量</h3>
          <label class="range">全体
            <input type="range" min="0" max="1" step="0.05" value="${s.master}" data-input="setting" data-key="master">
            <span class="range-value">${s.master.toFixed(2)}</span>
          </label>
          <label class="range">音楽
            <input type="range" min="0" max="1" step="0.05" value="${s.music}" data-input="setting" data-key="music">
            <span class="range-value">${s.music.toFixed(2)}</span>
          </label>
          <label class="range">効果音
            <input type="range" min="0" max="1" step="0.05" value="${s.sfx}" data-input="setting" data-key="sfx">
            <span class="range-value">${s.sfx.toFixed(2)}</span>
          </label>

          <h3>操作説明</h3>
          <div class="help">
            <p><b>移動</b>：画面左半分をドラッグ／WASD</p>
            <p><b>視点</b>：画面右側をスワイプ／マウス</p>
            <p><b>ダッシュ</b>：回避ボタンを押し続ける／Shift</p>
            <p><b>回避</b>：回避ボタンを短く押す／Space</p>
            <p><b>攻撃</b>：R1／左クリック　<b>強攻撃</b>：R2</p>
            <p><b>ガード</b>：L1／右クリック　<b>パリィ</b>：盾なしでガード、または L1+R2</p>
            <p><b>ロックオン</b>：ロックボタン／Q</p>
            <p><b>調べる</b>：手のアイコン／E</p>
          </div>
        </div>
      </div>`);
  }
}

// ---------------------------------------------------------------------------
//  Helpers
// ---------------------------------------------------------------------------

function setBar(id, ratio) {
  const node = document.getElementById(id);
  if (node) node.style.width = `${clamp(ratio, 0, 1) * 100}%`;
}

function formatNumber(n) {
  return Math.round(n).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

function escapeHtml(s) {
  return String(s === undefined || s === null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function poiColor(kind) {
  switch (kind) {
    case 'grace': return '#ffb347';
    case 'village': return '#8fd4ff';
    case 'boss': return '#ff6f6f';
    case 'mini': return '#ff9f5f';
    case 'chest': return '#d8c48a';
    case 'shrine': return '#b18cff';
    case 'merchant': case 'smith': return '#9fe0a0';
    case 'camp': return '#c88a6a';
    case 'ruin': return '#a9a29a';
    default: return '#cccccc';
  }
}

function isEquipped(p, it) {
  return p.equip.right.includes(it) || p.equip.left.includes(it)
    || p.equip.head === it || p.equip.body === it || p.equip.arms === it || p.equip.legs === it
    || p.equip.talismans.includes(it);
}

function itemMeta(it, p) {
  if (it.kind === 'weapon') {
    const atk = weaponAttack(it, p.upgradeLevelOf(it), p.stats);
    const scale = Object.entries(it.scaling || {}).map(([k, v]) => `${k.toUpperCase()}:${v}`).join(' ');
    return `攻 ${Math.round(atk.total)} / 重 ${it.weight} / ${scale}`;
  }
  if (it.kind === 'armor') return `防 ${it.def} / 強靭 ${it.poise} / 重 ${it.weight}`;
  if (it.kind === 'talisman') return `重 ${it.weight}`;
  return '';
}

function buffLabel(b) {
  if (b.atkMul) return '攻撃強化';
  if (b.addFire) return '炎付与';
  if (b.addMagic) return '魔力付与';
  if (b.defMul) return '防御強化';
  if (b.staminaRegen) return 'スタミナ回復';
  return '強化';
}

export { formatNumber, escapeHtml };
