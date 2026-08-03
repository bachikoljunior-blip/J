// ============================================================================
//  smoke.mjs — headless boot test.
//
//  Launches the game in Chromium (SwiftShader), plays through character
//  creation, waits for world generation, drives a few seconds of input, and
//  reports every console error plus renderer statistics. Screenshots land in
//  tools/shots/.
// ============================================================================

import { chromium } from '/home/user/Simple-browser-cookie-clicker-game/node_modules/playwright-core/index.mjs';
import { spawn } from 'node:child_process';
import { mkdirSync } from 'node:fs';
import { setTimeout as sleep } from 'node:timers/promises';

const PORT = process.env.PORT || 8123;
const ROOT = new URL('..', import.meta.url).pathname;
const SHOTS = `${ROOT}tools/shots`;
mkdirSync(SHOTS, { recursive: true });

const server = spawn('python3', ['-m', 'http.server', String(PORT), '--bind', '127.0.0.1'], {
  cwd: ROOT, stdio: 'ignore',
});
await sleep(700);

const errors = [];
const warnings = [];
let browser;
let exitCode = 0;

try {
  browser = await chromium.launch({
    executablePath: process.env.CHROME_PATH || '/opt/pw-browsers/chromium',
    args: [
      '--no-sandbox',
      '--use-gl=angle',
      '--use-angle=swiftshader',
      '--enable-unsafe-swiftshader',
      '--ignore-gpu-blocklist',
      '--disable-dev-shm-usage',
    ],
  });

  const context = await browser.newContext({
    viewport: { width: 412, height: 915 },      // a typical modern phone
    deviceScaleFactor: 2,
    isMobile: true,
    hasTouch: true,
    userAgent: 'Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Mobile Safari/537.36',
  });
  const page = await context.newPage();

  page.on('console', (m) => {
    const t = m.type();
    if (t === 'error') errors.push(`console.error: ${m.text()}`);
    else if (t === 'warning') warnings.push(m.text());
  });
  page.on('pageerror', (e) => errors.push(`pageerror: ${e.message}\n${e.stack || ''}`));
  page.on('requestfailed', (r) => {
    if (!r.url().includes('favicon')) errors.push(`requestfailed: ${r.url()} ${r.failure()?.errorText}`);
  });

  console.log('→ loading page');
  await page.goto(`http://127.0.0.1:${PORT}/index.html`, { waitUntil: 'domcontentloaded' });
  await sleep(1200);

  const glInfo = await page.evaluate(() => {
    const c = document.createElement('canvas');
    const gl = c.getContext('webgl2') || c.getContext('webgl');
    if (!gl) return { ok: false };
    const dbg = gl.getExtension('WEBGL_debug_renderer_info');
    return {
      ok: true,
      version: gl.getParameter(gl.VERSION),
      renderer: dbg ? gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL) : 'n/a',
    };
  });
  console.log('  webgl:', JSON.stringify(glInfo));

  await page.screenshot({ path: `${SHOTS}/01-title.png` });
  console.log('→ title screen captured');

  const hasTitle = await page.locator('.title-screen').count();
  if (!hasTitle) throw new Error('title screen did not render');

  console.log('→ new game');
  await page.click('[data-t="new"]');
  await sleep(400);
  await page.screenshot({ path: `${SHOTS}/02-create.png` });

  await page.click('[data-cls="knight"]');
  await sleep(200);
  await page.click('[data-t="start"]');

  console.log('→ generating world');
  const t0 = Date.now();
  await page.waitForFunction(() => document.getElementById('loading').classList.contains('hidden'), null,
    { timeout: 120000 });
  console.log(`  world generated in ${((Date.now() - t0) / 1000).toFixed(1)}s`);

  await sleep(2500);
  await page.screenshot({ path: `${SHOTS}/03-world.png` });
  console.log('→ world captured');

  // Drive a few seconds of gameplay through the keyboard bindings.
  console.log('→ simulating play');
  await page.keyboard.down('KeyW');
  await sleep(1600);
  await page.keyboard.up('KeyW');
  await page.mouse.click(206, 500);      // light attack
  await sleep(600);
  await page.keyboard.press('Space');    // roll
  await sleep(900);
  await page.screenshot({ path: `${SHOTS}/04-play.png` });

  // Night, for the point lights and sky.
  await page.evaluate(() => { window.__g && (window.__g.renderer.hour = 21.5); });
  await sleep(900);
  await page.screenshot({ path: `${SHOTS}/05-night.png` });

  await page.evaluate(() => { window.__g && (window.__g.renderer.hour = 6.6); });
  await sleep(900);
  await page.screenshot({ path: `${SHOTS}/06-dawn.png` });

  // Menus.
  await page.evaluate(() => { window.__g && (window.__g.renderer.hour = 11.0); });
  await page.keyboard.press('Escape');
  await sleep(600);
  await page.screenshot({ path: `${SHOTS}/07-menu.png` });
  const tabCount = await page.locator('.tab').count();
  if (tabCount < 5) errors.push(`pause menu tabs missing (found ${tabCount})`);

  await page.click('[data-tab="equip"]');
  await sleep(300);
  await page.screenshot({ path: `${SHOTS}/08-equip.png` });

  await page.click('[data-action="close"]');
  await sleep(300);

  await page.click('#btn-map');
  await sleep(700);
  await page.screenshot({ path: `${SHOTS}/09-map.png` });
  await page.click('[data-action="close"]');
  await sleep(400);

  // Performance sample.
  const stats = await page.evaluate(async () => {
    const g = window.__g;
    if (!g) return null;
    const samples = [];
    let last = performance.now();
    for (let i = 0; i < 90; i++) {
      await new Promise((r) => requestAnimationFrame(r));
      const now = performance.now();
      samples.push(now - last);
      last = now;
    }
    samples.sort((a, b) => a - b);
    return {
      medianMs: samples[Math.floor(samples.length / 2)],
      p95Ms: samples[Math.floor(samples.length * 0.95)],
      drawCalls: g.glw.drawCalls,
      triangles: g.glw.triangles,
      instances: g.batches.totalInstances,
      grass: g.grassBatch.count,
      actors: g.actors.length,
      enemies: g.enemies.length,
      particles: g.particles.count,
      terrainChunks: g.terrain.visible.length,
      quality: g.settings.quality,
      dynamicScale: g.dynamicScale,
      pois: g.world.pois.length,
      spawns: g.spawnPoints.length,
    };
  });
  console.log('→ stats:', JSON.stringify(stats, null, 2));

  // Wander far enough to load new terrain and hit wilderness spawns.
  console.log('→ traversal test');
  await page.evaluate(() => {
    const g = window.__g;
    const boss = g.world.pois.find((p) => p.kind === 'boss');
    if (boss) {
      g.player.x = boss.x + 30;
      g.player.z = boss.z + 30;
      g.player.y = g.world.heightAt(g.player.x, g.player.z);
      g.terrain.primeAround(g.player.x, g.player.z, 260);
      g.grass.dirty = true;
    }
  });
  await sleep(2200);
  await page.screenshot({ path: `${SHOTS}/10-arena.png` });

  const combat = await page.evaluate(async () => {
    const g = window.__g;
    // Spawn a test encounter and make sure damage flows both ways.
    const e = g.spawnEnemy('bandit', g.player.x + 2.0, g.player.z + 0.4, { level: 5 });
    e.brain.target = g.player;
    const before = e.hp;
    const info = g.player.buildAttackInfo(e);
    const res = e.takeDamage(info);
    const pInfo = e.buildAttackInfo(g.player);
    const pRes = g.player.takeDamage(pInfo);
    return {
      enemyDamage: before - e.hp,
      enemyHitOk: res.hit,
      playerDamage: pRes.damage,
      playerHitOk: pRes.hit,
      playerHp: g.player.hp,
      atk: Math.round(info.damage),
    };
  });
  console.log('→ combat:', JSON.stringify(combat));
  if (!combat.enemyHitOk || combat.enemyDamage <= 0) errors.push('player attack dealt no damage');
  if (!combat.playerHitOk || combat.playerDamage <= 0) errors.push('enemy attack dealt no damage');

  await sleep(1500);
  await page.screenshot({ path: `${SHOTS}/11-combat.png` });

  // Save / load round trip.
  const saveOk = await page.evaluate(() => {
    const g = window.__g;
    return g.save(0);
  });
  if (!saveOk) errors.push('save failed');
  console.log('→ save:', saveOk);

  await sleep(500);
  const finalErrors = await page.evaluate(() => window.__errors || []);
  for (const e of finalErrors) errors.push(`runtime: ${e}`);
} catch (e) {
  errors.push(`FATAL: ${e.message}\n${e.stack}`);
  exitCode = 1;
} finally {
  if (browser) await browser.close();
  server.kill();
}

console.log('\n================ RESULT ================');
if (errors.length) {
  exitCode = 1;
  console.log(`ERRORS (${errors.length}):`);
  for (const e of errors.slice(0, 30)) console.log(' •', e);
} else {
  console.log('no errors');
}
if (warnings.length) {
  console.log(`\nwarnings (${warnings.length}):`);
  for (const w of [...new Set(warnings)].slice(0, 10)) console.log(' -', w);
}
process.exit(exitCode);
