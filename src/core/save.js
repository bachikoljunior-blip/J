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

export function listSaves() {
  const out = [];
  for (let i = 0; i < 3; i++) {
    const raw = localStorage.getItem(PREFIX + i);
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
  const raw = localStorage.getItem(PREFIX + slot);
  if (!raw) return null;
  try {
    const data = JSON.parse(raw);
    if (!data.version || data.version > VERSION) return null;
    return data;
  } catch (e) {
    return null;
  }
}

export function deleteSave(slot) {
  localStorage.removeItem(PREFIX + slot);
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
