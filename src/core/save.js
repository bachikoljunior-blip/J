// ============================================================================
//  save.js — three save slots in localStorage.
//
//  Saving is deliberately explicit about *what* it stores: only the things
//  that cannot be regenerated. The world, its terrain, every tree and every
//  enemy placement all rebuild from the seed, so a full save is a couple of
//  kilobytes and loading is instant.
// ============================================================================

const PREFIX = 'kurogane.save.';
const VERSION = 3;
const BACKUP_FORMAT = 'kurogane-save-backup';
const BACKUP_VERSION = 1;

export function listSaves() {
  const out = [];
  for (let i = 0; i < 3; i++) {
    let raw = null;
    try {
      raw = localStorage.getItem(PREFIX + i);
    } catch (e) {
      out.push(null);
      continue;
    }
    if (!raw) { out.push(null); continue; }
    try {
      const data = JSON.parse(raw);
      out.push({
        slot: i,
        name: data.player?.name || '刻印者',
        level: data.player?.level || 1,
        className: data.player?.className || '',
        playtime: data.meta?.playtime || 0,
        savedAt: data.meta?.savedAt || 0,
        region: data.meta?.region || '',
        bosses: (data.world?.bossesKilled || []).length,
        version: data.version,
      });
    } catch (e) {
      out.push(null);
    }
  }
  return out;
}

export function saveGame(slot, game) {
  const p = game.player;
  const data = {
    version: VERSION,
    meta: {
      savedAt: Date.now(),
      playtime: game.playtime,
      region: game.currentRegionName,
      seed: game.world.seedStr,
    },
    player: {
      name: p.name,
      className: game.className,
      level: p.playerLevel,
      stats: { ...p.stats },
      souls: p.souls,
      totalSouls: p.totalSouls,
      hp: p.hp, fp: p.fp,
      x: p.x, y: p.y, z: p.z, yaw: p.yaw,
      appearance: { ...p.appearance },
      flaskHp: { ...p.flaskHp },
      flaskFp: { ...p.flaskFp },
      equip: {
        right: p.equip.right.map((i) => (i ? i.id : null)),
        left: p.equip.left.map((i) => (i ? i.id : null)),
        head: p.equip.head?.id || null,
        body: p.equip.body?.id || null,
        arms: p.equip.arms?.id || null,
        legs: p.equip.legs?.id || null,
        talismans: p.equip.talismans.map((i) => (i ? i.id : null)),
      },
      rightIndex: p.rightIndex,
      leftIndex: p.leftIndex,
      twoHand: p.twoHand,
      inventory: Array.from(p.inventory.entries()),
      upgrades: p.upgrades ? Array.from(p.upgrades.entries()) : [],
      spells: p.spells.slice(),
      spellIndex: p.spellIndex,
      deathDrop: p.deathDrop,
      lastGraceId: p.lastGraceId,
    },
    world: {
      hour: game.renderer.hour,
      discovered: game.world.pois.filter((q) => q.discovered).map((q) => q.id),
      openedChests: Array.from(game.openedChests),
      usedShrines: Array.from(game.usedShrines),
      bossesKilled: Array.from(game.bossesKilled),
      minisKilled: Array.from(game.minisKilled),
      clearedCamps: Array.from(game.clearedCamps),
      deaths: game.deaths,
    },
    quests: game.quests.serialize(),
    settings: game.settings,
  };
  try {
    localStorage.setItem(PREFIX + slot, JSON.stringify(data));
    return true;
  } catch (e) {
    console.warn('save failed', e);
    return false;
  }
}

export function loadGameData(slot) {
  try {
    const raw = localStorage.getItem(PREFIX + slot);
    if (!raw) return null;
    const data = JSON.parse(raw);
    if (!data.version || data.version > VERSION) return null;
    return data;
  } catch (e) {
    return null;
  }
}

export function deleteSave(slot) {
  try {
    localStorage.removeItem(PREFIX + slot);
    return true;
  } catch (e) {
    return false;
  }
}

/**
 * Create a portable, human-readable backup of all three slots and settings.
 * Safari may evict site storage under pressure; this gives a long-running
 * mobile RPG an escape hatch that does not depend on an account or server.
 */
export function createBackup() {
  const slots = [];
  for (let i = 0; i < 3; i++) {
    let value = null;
    try {
      const raw = localStorage.getItem(PREFIX + i);
      value = raw ? JSON.parse(raw) : null;
    } catch (e) { /* a damaged slot is represented as empty */ }
    slots.push(value);
  }

  let settings = null;
  try {
    const raw = localStorage.getItem(SETTINGS_KEY);
    settings = raw ? JSON.parse(raw) : null;
  } catch (e) { /* settings are optional */ }

  return JSON.stringify({
    format: BACKUP_FORMAT,
    backupVersion: BACKUP_VERSION,
    exportedAt: new Date().toISOString(),
    slots,
    settings,
  }, null, 2);
}

/** Restore a backup transactionally: failed writes put the old data back. */
export function restoreBackup(text) {
  const backup = JSON.parse(String(text));
  assertSafeData(backup);
  if (backup.format !== BACKUP_FORMAT || backup.backupVersion !== BACKUP_VERSION) {
    throw new Error('対応していないバックアップ形式です');
  }
  if (!Array.isArray(backup.slots) || backup.slots.length !== 3) {
    throw new Error('セーブスロットの構成が壊れています');
  }

  const encoded = backup.slots.map((data) => {
    if (data === null) return null;
    if (!data || typeof data !== 'object' || !data.player || !data.meta || !data.world ||
        !Number.isInteger(data.version) || data.version < 1 || data.version > VERSION) {
      throw new Error('セーブデータの内容が壊れています');
    }
    return JSON.stringify(data);
  });
  const encodedSettings = backup.settings && typeof backup.settings === 'object'
    ? JSON.stringify(backup.settings) : null;

  const keys = [PREFIX + 0, PREFIX + 1, PREFIX + 2, SETTINGS_KEY];
  const previous = keys.map((key) => localStorage.getItem(key));
  try {
    for (let i = 0; i < 3; i++) {
      if (encoded[i] === null) localStorage.removeItem(PREFIX + i);
      else localStorage.setItem(PREFIX + i, encoded[i]);
    }
    if (encodedSettings === null) localStorage.removeItem(SETTINGS_KEY);
    else localStorage.setItem(SETTINGS_KEY, encodedSettings);
  } catch (error) {
    for (let i = 0; i < keys.length; i++) {
      try {
        if (previous[i] === null) localStorage.removeItem(keys[i]);
        else localStorage.setItem(keys[i], previous[i]);
      } catch (e) { /* best effort rollback when storage itself is unavailable */ }
    }
    throw error;
  }
  return encoded.filter(Boolean).length;
}

function assertSafeData(value, depth = 0) {
  if (depth > 40) throw new Error('バックアップの階層が深すぎます');
  if (!value || typeof value !== 'object') return;
  for (const key of Object.keys(value)) {
    if (key === '__proto__' || key === 'prototype' || key === 'constructor') {
      throw new Error('安全でないバックアップです');
    }
    assertSafeData(value[key], depth + 1);
  }
}

const SETTINGS_KEY = 'kurogane.settings';

export function loadSettings() {
  try {
    const raw = localStorage.getItem(SETTINGS_KEY);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch (e) {
    return null;
  }
}

export function saveSettings(settings) {
  try {
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
  } catch (e) { /* storage full or blocked; settings are not worth failing over */ }
}

export function formatPlaytime(seconds) {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return `${h}時間${String(m).padStart(2, '0')}分`;
}
