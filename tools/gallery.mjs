// ============================================================================
//  gallery.mjs — visual spot-check.
//
//  Teleports to the things a normal playthrough would take an hour to reach —
//  each boss, the coast, a village, a wolf pack — and photographs them, so
//  content that is never exercised by the other tests still gets looked at.
// ============================================================================

import { chromium } from '/home/user/Simple-browser-cookie-clicker-game/node_modules/playwright-core/index.mjs';
import { spawn } from 'node:child_process';
import { mkdirSync } from 'node:fs';
import { setTimeout as sleep } from 'node:timers/promises';

const PORT = process.env.PORT || 8141;
const ROOT = new URL('..', import.meta.url).pathname;
const SHOTS = `${ROOT}tools/shots`;
mkdirSync(SHOTS, { recursive: true });

const server = spawn('python3', ['-m', 'http.server', String(PORT), '--bind', '127.0.0.1'],
  { cwd: ROOT, stdio: 'ignore' });
await sleep(700);

const errors = [];
let browser;

const SETUP = (cfg) => {
  const g = window.__g;
  const p = g.player;
  window.__ui.closeAll();
  g.paused = false;
  g.dialogue = null;
  if (p.dead) { p.dead = false; p.setState('idle'); }
  p.hp = p.maxHp;
  for (const e of g.enemies.slice()) { if (e.spawnRef) e.spawnRef.actor = null; g._removeActor(e); }
  g.projectiles.length = 0;
  g.areaEffects.length = 0;
  g.particles.clear();

  if (cfg.hour !== undefined) g.renderer.hour = cfg.hour;
  if (cfg.weather) g.renderer.forcedWeather = cfg.weather;
  else g.renderer.forcedWeather = null;

  let target = null;
  if (cfg.poi) {
    target = g.world.pois.find((q) => q.kind === cfg.poi && (!cfg.boss || q.boss === cfg.boss));
  } else if (cfg.coast) {
    // Find shoreline: land within a few metres of sea level.
    for (let i = 0; i < 6000; i++) {
      const x = (Math.random() - 0.5) * 2200;
      const z = (Math.random() - 0.5) * 2200;
      const h = g.world.heightAt(x, z);
      if (h > 0.6 && h < 3.2 && g.world.heightAt(x + 25, z) < -1.5) { target = { x, z }; break; }
    }
  }
  if (!target) return { ok: false };

  p.x = target.x + (cfg.dx || 0);
  p.z = target.z + (cfg.dz || 14);
  p.y = g.world.heightAt(p.x, p.z);
  p.camera.yaw = Math.atan2(target.x - p.x, target.z - p.z);
  p.camera.pitch = cfg.pitch !== undefined ? cfg.pitch : -0.14;
  p.lockTarget = null;
  g.terrain.primeAround(p.x, p.z, 300);
  g.grass.dirty = true;

  for (const spawn of cfg.spawns || []) {
    for (let i = 0; i < spawn.n; i++) {
      const a = (i / spawn.n) * Math.PI * 2;
      const e = g.spawnEnemy(spawn.id, p.x + Math.sin(a) * 5 + Math.sin(p.camera.yaw) * 8,
        p.z + Math.cos(a) * 5 + Math.cos(p.camera.yaw) * 8, { level: spawn.level || 10 });
      e.brain.target = p;
      e.brain.state = 'chase';
    }
  }
  return { ok: true, x: p.x, z: p.z };
};

const REPORT = () => {
  const g = window.__g;
  const p = g.player;
  return {
    enemies: g.enemies.length,
    boss: g.enemies.filter((e) => e.isBoss).map((e) => ({
      name: e.name, dist: Math.round(Math.hypot(e.x - p.x, e.z - p.z)),
      started: e.introDone, hp: Math.round(e.hp),
    })),
    tris: g.glw.triangles,
  };
};

const SHOTS_LIST = [
  { file: 'v1-wolves', label: 'ashwolf pack', cfg: { poi: 'grace', dz: 16, hour: 10, spawns: [{ id: 'ashwolf', n: 4, level: 6 }] } },
  { file: 'v2-village', label: 'village', cfg: { poi: 'village', dz: 40, hour: 18.4, pitch: -0.08 } },
  { file: 'v3-coast', label: 'coastline', cfg: { coast: true, dz: 22, hour: 7.5, pitch: -0.10 } },
  { file: 'v4-warden', label: 'boss: warden', cfg: { poi: 'boss', boss: 'warden', dx: 11, dz: 16, hour: 12, startBoss: true } },
  { file: 'v5-drake', label: 'boss: drake', cfg: { poi: 'boss', boss: 'drake', dx: 13, dz: 18, hour: 15, startBoss: true } },
  { file: 'v6-sovereign', label: 'boss: sovereign', cfg: { poi: 'boss', boss: 'sovereign', dx: 10, dz: 15, hour: 20.5, startBoss: true, phase: true } },
  { file: 'v7-ashking', label: 'boss: ash king', cfg: { poi: 'boss', boss: 'ashking', dx: 12, dz: 16, hour: 13, startBoss: true } },
  { file: 'v8-rain', label: 'storm', cfg: { poi: 'grace', dz: 18, hour: 11, weather: 'storm', spawns: [{ id: 'husk', n: 3, level: 8 }] } },
  { file: 'v9-ruin', label: 'ruins', cfg: { poi: 'ruin', dz: 26, hour: 6.4, pitch: -0.06 } },
  { file: 'v10-sentinel', label: 'sentinels', cfg: { poi: 'camp', dz: 12, hour: 9, spawns: [{ id: 'sentinel', n: 2, level: 20 }, { id: 'spearman', n: 2, level: 18 }] } },
];

try {
  browser = await chromium.launch({
    executablePath: process.env.CHROME_PATH || '/opt/pw-browsers/chromium',
    args: ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader',
      '--enable-unsafe-swiftshader', '--disable-dev-shm-usage'],
  });
  const page = await browser.newPage({ viewport: { width: 960, height: 540 }, deviceScaleFactor: 1 });
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
  await sleep(800);
  // Best-looking preset for the gallery, regardless of what the device guessed.
  await page.evaluate(() => { window.__g.applyQuality('medium'); window.__g.dynamicScale = 1; });
  await sleep(600);

  for (const shot of SHOTS_LIST) {
    const res = await page.evaluate(SETUP, shot.cfg);
    if (!res.ok) { console.log(`  SKIP  ${shot.label} (no target)`); continue; }
    if (shot.cfg.startBoss) {
      // Bosses respawn on the next spawn tick, so waking them has to wait a
      // beat after the teleport that cleared the previous scene.
      await sleep(600);
      await page.evaluate((phase) => {
        const g = window.__g;
        const b = g.enemies.find((e) => e.isBoss);
        if (!b) return;
        if (phase) b.hp = b.maxHp * 0.30;
        const arena = g.world.pois.find((q) => q.kind === 'boss' && q.boss === b.bossId);
        if (arena) g.enterBossArena(arena);
      }, !!shot.cfg.phase);
    }
    await sleep(2800);
    const rep = await page.evaluate(REPORT);
    await page.screenshot({ path: `${SHOTS}/${shot.file}.png` });
    const bossInfo = rep.boss.length
      ? rep.boss.map((b) => `${b.name}@${b.dist}m${b.started ? ' (engaged)' : ''}`).join(', ')
      : '';
    console.log(`  shot  ${shot.label.padEnd(18)} enemies=${rep.enemies} ${bossInfo}`);
  }
} catch (e) {
  errors.push(`FATAL: ${e.message}\n${e.stack}`);
} finally {
  if (browser) await browser.close();
  server.kill();
}

console.log('\n================');
if (errors.length) {
  for (const e of [...new Set(errors)].slice(0, 10)) console.log(' !', e);
  process.exit(1);
}
console.log('gallery complete');
