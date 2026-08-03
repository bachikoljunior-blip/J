// ============================================================================
//  gameplay.mjs — systems integration test.
//
//  The smoke test proves the game boots and renders. This one proves it is a
//  game: enemies notice you and commit attacks, a boss wakes and changes
//  phase, quests advance off world events, levelling and shops move numbers in
//  the right direction, and dying drops embers you can pick back up.
// ============================================================================

import { chromium } from '/home/user/Simple-browser-cookie-clicker-game/node_modules/playwright-core/index.mjs';
import { spawn } from 'node:child_process';
import { mkdirSync } from 'node:fs';
import { setTimeout as sleep } from 'node:timers/promises';

const PORT = process.env.PORT || 8133;
const ROOT = new URL('..', import.meta.url).pathname;
const SHOTS = `${ROOT}tools/shots`;
mkdirSync(SHOTS, { recursive: true });

const server = spawn('python3', ['-m', 'http.server', String(PORT), '--bind', '127.0.0.1'],
  { cwd: ROOT, stdio: 'ignore' });
await sleep(700);

const failures = [];
const errors = [];
let browser;

const check = (name, ok, detail) => {
  console.log(`  ${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? `  — ${detail}` : ''}`);
  if (!ok) failures.push(`${name}${detail ? `: ${detail}` : ''}`);
};

/**
 * Phases must not contaminate each other: the camp fight can legitimately kill
 * the player, which pauses the simulation and would fail everything after it
 * for reasons that have nothing to do with what those checks are testing.
 */
const RESET = `() => {
  const g = window.__g;
  const p = g.player;
  window.__ui.closeAll();
  g.dialogue = null;
  g.paused = false;
  if (p.dead) { p.dead = false; p.deathTimer = 0; p.setState('idle'); }
  p.hp = p.maxHp; p.fp = p.maxFp; p.stamina = p.maxStamina;
  p.poise = p.maxPoise; p.invuln = 0; p.buffs.length = 0;
  p.deathDrop = null;
  g.renderer.deathFade = 0;
  for (const e of g.enemies.slice()) { if (e.spawnRef) e.spawnRef.actor = null; g._removeActor(e); }
  g.projectiles.length = 0;
  g.areaEffects.length = 0;
}`;

try {
  browser = await chromium.launch({
    executablePath: process.env.CHROME_PATH || '/opt/pw-browsers/chromium',
    args: ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader',
      '--enable-unsafe-swiftshader', '--disable-dev-shm-usage'],
  });
  const page = await browser.newPage({ viewport: { width: 900, height: 520 } });
  page.on('pageerror', (e) => errors.push(`pageerror: ${e.message}`));
  page.on('console', (m) => { if (m.type() === 'error' && !m.text().includes('favicon')) errors.push(m.text()); });

  await page.goto(`http://127.0.0.1:${PORT}/index.html`, { waitUntil: 'domcontentloaded' });
  await sleep(900);
  await page.click('[data-t="new"]');
  await sleep(300);
  await page.click('[data-cls="knight"]');
  await page.click('[data-t="start"]');
  await page.waitForFunction(() => document.getElementById('loading').classList.contains('hidden'),
    null, { timeout: 120000 });
  await sleep(1200);
  console.log('\n— world ready —\n');

  // -------------------------------------------------------------------------
  console.log('[world]');
  const world = await page.evaluate(() => {
    const g = window.__g;
    const kinds = {};
    for (const p of g.world.pois) kinds[p.kind] = (kinds[p.kind] || 0) + 1;
    let land = 0, water = 0, hi = -1e9, lo = 1e9;
    for (let i = 0; i < g.world.height.length; i += 37) {
      const h = g.world.height[i];
      if (h > 0) land++; else water++;
      if (h > hi) hi = h;
      if (h < lo) lo = h;
    }
    const biomes = {};
    for (let i = 0; i < g.world.biome.length; i += 37) {
      biomes[g.world.biome[i]] = (biomes[g.world.biome[i]] || 0) + 1;
    }
    return { kinds, landRatio: land / (land + water), hi, lo, biomeCount: Object.keys(biomes).length };
  });
  check('graces placed', world.kinds.grace >= 10, `${world.kinds.grace}`);
  check('boss arenas placed', world.kinds.boss === 6, `${world.kinds.boss}`);
  check('chests placed', world.kinds.chest >= 40, `${world.kinds.chest}`);
  check('shrines placed', world.kinds.shrine >= 8, `${world.kinds.shrine}`);
  check('island has coastline', world.landRatio > 0.35 && world.landRatio < 0.92,
    `land ${(world.landRatio * 100).toFixed(0)}%`);
  check('terrain has relief', world.hi > 100 && world.lo < -5, `${world.lo.toFixed(0)}..${world.hi.toFixed(0)}m`);
  check('all biomes present', world.biomeCount >= 7, `${world.biomeCount} biomes`);

  // -------------------------------------------------------------------------
  console.log('\n[combat / AI]');
  const combat = await page.evaluate(async () => {
    const g = window.__g;
    const p = g.player;
    // Drop the player into a bandit camp and let the AI run.
    const camp = g.world.pois.find((q) => q.kind === 'camp' && q.region === 'meadow');
    p.x = camp.x; p.z = camp.z + 8;
    p.y = g.world.heightAt(p.x, p.z);
    g.terrain.primeAround(p.x, p.z, 200);
    const frames = () => new Promise((r) => requestAnimationFrame(r));

    let noticed = 0, attacked = 0, enemyHitPlayer = 0, maxEnemies = 0;
    const startHp = p.hp;
    p.invuln = 0;
    for (let i = 0; i < 300; i++) {
      await frames();
      maxEnemies = Math.max(maxEnemies, g.enemies.length);
      for (const e of g.enemies) {
        if (e.brain && e.brain.target) noticed++;
        if (e.state === 'attack') attacked++;
      }
      if (p.hp < startHp) enemyHitPlayer = 1;
    }
    return {
      enemies: maxEnemies,
      noticed: noticed > 0,
      attacked: attacked > 0,
      damagedPlayer: enemyHitPlayer === 1,
      hpLost: Math.round(startHp - p.hp),
    };
  });
  check('camp spawned enemies', combat.enemies >= 3, `${combat.enemies}`);
  check('AI acquired the player', combat.noticed);
  check('AI committed attacks', combat.attacked);
  check('AI landed damage', combat.damagedPlayer, `${combat.hpLost} hp`);

  await page.screenshot({ path: `${SHOTS}/g1-camp.png` });

  // -------------------------------------------------------------------------
  console.log('\n[player combat]');
  await page.evaluate(RESET);
  await sleep(200);
  const kill = await page.evaluate(async () => {
    const g = window.__g;
    const p = g.player;
    p.hp = p.maxHp;
    const before = p.souls;
    const e = g.spawnEnemy('bandit', p.x + 1.6, p.z, { level: 1 });
    const frames = () => new Promise((r) => requestAnimationFrame(r));
    let swings = 0;
    for (let i = 0; i < 500 && !e.dead; i++) {
      if (p.canAct) { p.yaw = Math.atan2(e.x - p.x, e.z - p.z); p._buffer('light'); swings++; }
      await frames();
    }
    return { killed: e.dead, swings, soulsGained: p.souls - before, streak: p.hitStreak };
  });
  check('player can kill an enemy', kill.killed, `${kill.swings} swing attempts`);
  check('kill awards embers', kill.soulsGained > 0, `+${kill.soulsGained}`);

  // -------------------------------------------------------------------------
  console.log('\n[progression]');
  await page.evaluate(RESET);
  await sleep(200);
  const prog = await page.evaluate(() => {
    const g = window.__g;
    const p = g.player;
    p.souls = 200000;
    const hp0 = p.maxHp, lvl0 = p.playerLevel;
    for (let i = 0; i < 10; i++) p.levelUp('vig');
    const hpUp = p.maxHp > hp0 && p.playerLevel === lvl0 + 10;

    // Weapon upgrades must actually raise attack rating.
    const w = p.rightHand;
    const a0 = g.constructor === undefined ? 0 : 0;
    p.addItem('mat_shard', 40); p.addItem('mat_chunk', 40); p.addItem('mat_core', 40);
    const before = p.buildAttackInfo(null).damage;
    p.setUpgrade(w.id, 6);
    const after = p.buildAttackInfo(null).damage;

    // Equip load must change roll type.
    const light = p.rollType;
    p.equipItem('body_oath'); p.equipItem('legs_oath'); p.equipItem('head_oath'); p.equipItem('arms_oath');
    const heavy = p.rollType;

    // Talismans must apply their modifiers.
    p.addItem('tal_vigor');
    const hpBefore = p.maxHp;
    p.equipItem('tal_vigor');
    const hpAfter = p.maxHp;

    return {
      hpUp, atkBefore: Math.round(before), atkAfter: Math.round(after),
      light, heavy, talismanWorked: hpAfter > hpBefore,
      load: `${p.equipLoad.toFixed(1)}/${p.maxLoad.toFixed(1)}`,
    };
  });
  check('levelling raises max HP', prog.hpUp);
  check('weapon upgrade raises attack', prog.atkAfter > prog.atkBefore,
    `${prog.atkBefore} → ${prog.atkAfter}`);
  check('equip load changes roll type', prog.light !== prog.heavy,
    `${prog.light} → ${prog.heavy} (${prog.load})`);
  check('talisman modifies stats', prog.talismanWorked);

  // -------------------------------------------------------------------------
  console.log('\n[boss]');
  await page.evaluate(RESET);
  await sleep(200);
  const boss = await page.evaluate(async () => {
    const g = window.__g;
    const p = g.player;
    const arena = g.world.pois.find((q) => q.kind === 'boss' && q.boss === 'warden');
    p.x = arena.x + 6; p.z = arena.z + 6;
    p.y = g.world.heightAt(p.x, p.z);
    g.terrain.primeAround(p.x, p.z, 200);
    const frames = () => new Promise((r) => requestAnimationFrame(r));
    for (let i = 0; i < 40; i++) await frames();

    const b = g.enemies.find((e) => e.isBoss);
    if (!b) return { spawned: false };
    const phases = b.phases.length;
    g.enterBossArena(arena);
    for (let i = 0; i < 30; i++) await frames();
    const started = b.introDone;

    // Drive it to the second phase and confirm the moveset actually changes.
    const attacksBefore = b.brain.cfg.attacks.length;
    const dmgBefore = b.baseDamage;
    b.hp = b.maxHp * 0.40;
    for (let i = 0; i < 40; i++) await frames();
    const phased = b.phaseIndex >= 1;
    const attacksAfter = b.brain.cfg.attacks.length;

    // And that killing it is registered.
    b.hp = 1;
    b.takeDamage({ damage: 99999, poise: 9999, source: p, ignoreInvuln: true });
    for (let i = 0; i < 20; i++) await frames();
    return {
      spawned: true, phases, started, phased,
      attacksBefore, attacksAfter,
      dmgBefore: Math.round(dmgBefore), dmgAfter: Math.round(b.baseDamage),
      dead: b.dead,
      recorded: g.bossesKilled.has('warden'),
      gotShard: p.countItem('key_shard_1') > 0,
      bossBarShown: !!document.getElementById('boss-bar').classList.contains('show'),
    };
  });
  check('boss spawned in its arena', boss.spawned);
  check('boss has multiple phases', boss.phases >= 2, `${boss.phases}`);
  check('fog gate starts the fight', boss.started);
  check('phase transition fired', boss.phased);
  check('phase changes the moveset', boss.attacksAfter > boss.attacksBefore,
    `${boss.attacksBefore} → ${boss.attacksAfter} attacks`);
  check('phase raises damage', boss.dmgAfter > boss.dmgBefore, `${boss.dmgBefore} → ${boss.dmgAfter}`);
  check('boss death recorded', boss.dead && boss.recorded);
  check('boss reward granted', boss.gotShard);

  await page.screenshot({ path: `${SHOTS}/g2-boss.png` });

  // -------------------------------------------------------------------------
  console.log('\n[quests & NPCs]');
  await page.evaluate(RESET);
  await sleep(200);
  const quest = await page.evaluate(async () => {
    const g = window.__g;
    const p = g.player;
    const main1 = g.quests.get('main_1');
    const npc = g.npcs.find((n) => n.npcId === 'harum');
    if (!npc) return { npc: false };
    p.x = npc.x + 1.5; p.z = npc.z;
    p.y = g.world.heightAt(p.x, p.z);
    g.talkTo(npc);
    const opened = window.__ui.screen === 'dialogue';
    const optionCount = document.querySelectorAll('.dopt').length;
    g.closeDialogue();
    window.__ui.closeAll();

    // The boss kill above should have advanced the main quest.
    const advanced = main1.step > 0 || main1.status === 2;

    // Wolf side quest counts kills.
    g.quests.start('side_wolves');
    for (let i = 0; i < 10; i++) g.quests.notify({ type: 'kill', archetype: 'ashwolf' });
    const wolves = g.quests.get('side_wolves');

    return {
      npc: true, opened, optionCount, advanced,
      wolvesReady: wolves.counters.s1_ready === 1 || wolves.status === 2,
      npcCount: g.npcs.length,
    };
  });
  check('NPCs exist in the world', quest.npc && quest.npcCount >= 4, `${quest.npcCount}`);
  check('dialogue opens with options', quest.opened && quest.optionCount >= 2, `${quest.optionCount} options`);
  check('main quest advanced on boss kill', quest.advanced);
  check('kill quest counts progress', quest.wolvesReady);

  // -------------------------------------------------------------------------
  console.log('\n[death & recovery]');
  await page.evaluate(RESET);
  await sleep(200);
  const death = await page.evaluate(async () => {
    const g = window.__g;
    const p = g.player;
    p.souls = 5000;
    const dropX = p.x, dropZ = p.z;
    p.hp = 1;
    p.takeDamage({ damage: 9999, poise: 9999, source: null, ignoreInvuln: true });
    const frames = () => new Promise((r) => requestAnimationFrame(r));
    for (let i = 0; i < 30; i++) await frames();
    const dropped = p.deathDrop && p.deathDrop.souls === 5000 && p.souls === 0;
    const screenShown = window.__ui.screen === 'death';
    g.respawnPlayer();
    for (let i = 0; i < 10; i++) await frames();
    const alive = !p.dead && p.hp === p.maxHp;
    // Walk back to the bloodstain and reclaim.
    p.x = dropX; p.z = dropZ;
    const reclaimed = g.collectDeathDrop();
    return { dropped, screenShown, alive, reclaimed, souls: p.souls };
  });
  check('death drops embers', death.dropped);
  check('death screen shown', death.screenShown);
  check('respawn restores the player', death.alive);
  check('embers can be reclaimed', death.reclaimed && death.souls === 5000, `${death.souls}`);

  // -------------------------------------------------------------------------
  console.log('\n[grace & travel]');
  await page.evaluate(RESET);
  await sleep(200);
  const grace = await page.evaluate(async () => {
    const g = window.__g;
    const p = g.player;
    p.flaskHp.cur = 0;
    p.hp = 10;
    const gr = g.world.pois.find((q) => q.kind === 'grace');
    g.restAtGrace(gr);
    const healed = p.hp === p.maxHp && p.flaskHp.cur === p.flaskHp.max;
    const menu = window.__ui.screen === 'grace';
    // Fast travel to another discovered grace.
    const other = g.world.pois.filter((q) => q.kind === 'grace')[3];
    other.discovered = true;
    const beforeX = p.x;
    g.warpToGrace(other);
    const moved = Math.abs(p.x - beforeX) > 1;
    return { healed, menu, moved, lastGrace: p.lastGraceId === other.id };
  });
  check('resting heals and refills flasks', grace.healed);
  check('grace menu opens', grace.menu);
  check('fast travel moves the player', grace.moved && grace.lastGrace);

  // -------------------------------------------------------------------------
  console.log('\n[economy]');
  await page.evaluate(RESET);
  await sleep(200);
  const shop = await page.evaluate(() => {
    const g = window.__g;
    const p = g.player;
    window.__ui.closeAll();
    const merchant = g.npcs.find((n) => n.npcDef.role === 'merchant');
    if (!merchant) return { merchant: false };
    g.dialogue = { npc: merchant, node: 'start', tree: {} };
    window.__ui.openShop(merchant);
    const rows = document.querySelectorAll('[data-action="shop-buy"]').length;
    p.souls = 100000;
    const before = p.countItem('flask_hp');
    window.__ui._buy('herb_green');
    const bought = p.countItem('herb_green') > 0 && p.souls < 100000;
    window.__ui.closeAll();
    g.dialogue = null;
    return { merchant: true, rows, bought };
  });
  check('merchant has stock', shop.merchant && shop.rows >= 8, `${shop.rows} items`);
  check('buying works', shop.bought);

  // -------------------------------------------------------------------------
  console.log('\n[save / load round trip]');
  await page.evaluate(RESET);
  await sleep(200);
  const save = await page.evaluate(() => {
    const g = window.__g;
    const p = g.player;
    p.stats.vig = 42;
    p.souls = 12345;
    const ok = g.save(1);
    const raw = localStorage.getItem('kurogane.save.1');
    const data = JSON.parse(raw);
    return {
      ok,
      bytes: raw.length,
      vig: data.player.stats.vig,
      souls: data.player.souls,
      bosses: data.world.bossesKilled.length,
      quests: Object.keys(data.quests.quests).length,
    };
  });
  check('save succeeds', save.ok);
  check('save is compact', save.bytes < 20000, `${save.bytes} bytes`);
  check('save keeps stats', save.vig === 42 && save.souls === 12345);
  check('save keeps world state', save.bosses >= 1 && save.quests >= 8);

  await page.screenshot({ path: `${SHOTS}/g3-final.png` });
} catch (e) {
  failures.push(`FATAL: ${e.message}\n${e.stack}`);
} finally {
  if (browser) await browser.close();
  server.kill();
}

console.log('\n================ RESULT ================');
if (errors.length) {
  console.log(`runtime errors (${errors.length}):`);
  for (const e of [...new Set(errors)].slice(0, 10)) console.log(' !', e);
}
if (failures.length) {
  console.log(`\n${failures.length} FAILED:`);
  for (const f of failures) console.log(' •', f);
} else {
  console.log('all gameplay checks passed');
}
process.exit(failures.length || errors.length ? 1 : 0);
