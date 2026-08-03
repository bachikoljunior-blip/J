// ============================================================================
//  grade-lab.mjs — fast iteration on the look.
//
//  Boots the game once, then measures readbackStats for a list of scenes under
//  a set of candidate sky/grade tweaks. Tuning exposure or moonlight through a
//  full audit run costs minutes per guess; this costs one boot for all of them.
//
//    node tools/grade-lab.mjs                 # measure the current look
//    node tools/grade-lab.mjs --shots         # also write tools/shots/lab-*.png
// ============================================================================

import { chromium } from '/home/user/Simple-browser-cookie-clicker-game/node_modules/playwright-core/index.mjs';
import { spawn } from 'node:child_process';
import { mkdirSync } from 'node:fs';
import { setTimeout as sleep } from 'node:timers/promises';

const PORT = process.env.PORT || 8178;
const ROOT = new URL('..', import.meta.url).pathname;
const SHOTS = process.argv.includes('--shots');

const SCENES = [
  { id: 'day-meadow', region: 'meadow', hour: 11.0, weather: 'clear', yaw: 0.6 },
  { id: 'dusk-wood', region: 'wood', hour: 18.3, weather: 'clear', yaw: 0.6 },
  { id: 'night-ridge', region: 'ridge', hour: 22.5, weather: 'clear', yaw: 0.6 },
  { id: 'storm-mire', region: 'mire', hour: 13.0, weather: 'storm', yaw: 0.6 },
  { id: 'waste', region: 'waste', hour: 12.0, weather: 'clear', yaw: 0.6 },
  { id: 'peak', region: 'peak', hour: 9.0, weather: 'clear', yaw: 0.6 },
];

const server = spawn('python3', ['-m', 'http.server', String(PORT), '--bind', '127.0.0.1'],
  { cwd: ROOT, stdio: 'ignore' });
await sleep(700);
if (SHOTS) mkdirSync(`${ROOT}tools/shots`, { recursive: true });

const browser = await chromium.launch({
  executablePath: process.env.CHROME_PATH || '/opt/pw-browsers/chromium',
  args: ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader',
    '--enable-unsafe-swiftshader', '--disable-dev-shm-usage'],
});
const page = await browser.newPage({ viewport: { width: 900, height: 520 } });
page.on('pageerror', (e) => console.log('ERR', e.message));
await page.goto(`http://127.0.0.1:${PORT}/index.html`, { waitUntil: 'domcontentloaded' });
await sleep(900);
await page.click('[data-t="new"]');
await sleep(300);
await page.click('[data-cls="knight"]');
await page.click('[data-t="start"]');
await page.waitForFunction(() => document.getElementById('loading').classList.contains('hidden'),
  null, { timeout: 180000 });
await sleep(1200);
await page.evaluate(() => { window.__g.applyQuality('medium'); window.__g.dynamicScale = 1; });
await sleep(500);

const rows = [];
for (const s of SCENES) {
  const st = await page.evaluate(async (sc) => {
    const g = window.__g;
    const p = g.player;
    const wg = await import('/src/world/worldgen.js');
    const region = wg.REGIONS.find((r) => r.id === sc.region);
    const spot = g.world.findFlatSpot(region.cx, region.cz, 220, 0.25);
    p.teleport(spot.x, undefined, spot.z);
    // Measure the world, not a death overlay: teleporting can drop the player
    // and an unlucky landing turns a "peak at 9am" sample into a red fade.
    const revive = () => {
      window.__ui.closeAll();
      g.paused = false;
      if (p.dead) { p.dead = false; p.deathTimer = 0; p.setState('idle'); }
      p.hp = p.maxHp; p.stamina = p.maxStamina; p.invuln = 9;
      g.renderer.deathFade = 0;
      g.renderer.damageFlash = 0;
      for (const e of g.enemies.slice()) { if (e.spawnRef) e.spawnRef.actor = null; g._removeActor(e); }
    };
    revive();
    // Pin the heading: "how much sky is in frame" moves mean luma by 0.1 on
    // its own, so an unpinned camera makes these numbers unreproducible.
    p.yaw = sc.yaw;
    p.camera.yaw = sc.yaw;
    p.camera.pitch = -0.20;
    p.lockTarget = null;
    g.lockTarget = null;
    g.renderer.hour = sc.hour;
    g.renderer.forcedWeather = sc.weather;
    g.terrain.primeAround(p.x, p.z, 320);
    g.grass.dirty = true;
    await new Promise((r) => {
      let i = 0;
      const t = () => (++i >= 150 ? r() : requestAnimationFrame(t));
      requestAnimationFrame(t);
    });
    revive();
    return new Promise((resolve) => requestAnimationFrame(() => {
      const st2 = g.renderer.readbackStats(5);
      st2.exposure = g.renderer.exposure;
      st2.triangles = g.glw.triangles;
      st2.triByTag = { ...g.glw.triByTag };
      st2.drawCalls = g.glw.drawCalls;
      st2.byTag = { ...g.glw.byTag };
      resolve(st2);
    }));
  }, s);
  rows.push({ ...s, ...st });
  console.log(`${s.id.padEnd(12)} luma=${st.meanLuma.toFixed(3)} contrast=${st.contrast.toFixed(3)} ` +
    `sat=${st.saturation.toFixed(3)} clip=${(st.clippedRatio * 100).toFixed(1)}% ` +
    `crush=${(st.crushedRatio * 100).toFixed(1)}% tris=${st.triangles} draws=${st.drawCalls}`);
  if (SHOTS) await page.screenshot({ path: `${ROOT}tools/shots/lab-${s.id}.png` });
}

const day = rows.find((r) => r.id === 'day-meadow');
const night = rows.find((r) => r.id === 'night-ridge');
console.log(`\n昼夜輝度差 ${Math.abs(day.meanLuma - night.meanLuma).toFixed(3)} (目標 ≥ 0.12)`);
const worst = rows.slice().sort((a, b) => a.contrast - b.contrast)[0];
console.log(`最低コントラスト ${worst.id} ${worst.contrast.toFixed(3)} (目標 ≥ 0.11)`);
console.log('三角形内訳:', JSON.stringify(rows[0].triByTag));
console.log('ドロー内訳:', JSON.stringify(rows[0].byTag));

await browser.close();
server.kill();
