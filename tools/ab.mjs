// ab.mjs — measure one scene under two engine states, in a single boot.
// Usage: node tools/ab.mjs
import { chromium } from '/home/user/Simple-browser-cookie-clicker-game/node_modules/playwright-core/index.mjs';
import { spawn } from 'node:child_process';
import { mkdirSync } from 'node:fs';
import { setTimeout as sleep } from 'node:timers/promises';

const PORT = 8181;
const ROOT = new URL('..', import.meta.url).pathname;
const server = spawn('python3', ['-m', 'http.server', String(PORT), '--bind', '127.0.0.1'], { cwd: ROOT, stdio: 'ignore' });
await sleep(700);
mkdirSync(`${ROOT}tools/shots`, { recursive: true });
const browser = await chromium.launch({
  executablePath: '/opt/pw-browsers/chromium',
  args: ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--disable-dev-shm-usage'],
});
const page = await browser.newPage({ viewport: { width: 900, height: 520 } });
page.on('pageerror', (e) => console.log('ERR', e.message));
await page.goto(`http://127.0.0.1:${PORT}/index.html`, { waitUntil: 'domcontentloaded' });
await sleep(900);
await page.click('[data-t="new"]');
await sleep(300);
await page.click('[data-cls="knight"]');
await page.click('[data-t="start"]');
await page.waitForFunction(() => document.getElementById('loading').classList.contains('hidden'), null, { timeout: 180000 });
await sleep(1200);
await page.evaluate(() => { window.__g.applyQuality('medium'); window.__g.dynamicScale = 1; });
await sleep(500);

await page.evaluate(async () => {
  const g = window.__g;
  const p = g.player;
  const wg = await import('/src/world/worldgen.js');
  const r = wg.REGIONS.find((x) => x.id === 'meadow');
  const spot = g.world.findFlatSpot(r.cx, r.cz, 220, 0.25);
  p.teleport(spot.x, undefined, spot.z);
  p.revive(); p.invuln = 999;
  p.yaw = 0.6; p.camera.yaw = 0.6; p.camera.pitch = -0.20;
  g.renderer.hour = 11; g.renderer.forcedWeather = 'clear';
  g.terrain.primeAround(p.x, p.z, 320);
  g.grass.dirty = true;
  await new Promise((res) => { let i = 0; const t = () => (++i >= 150 ? res() : requestAnimationFrame(t)); requestAnimationFrame(t); });
});

for (const fade of [0, 95]) {
  const st = await page.evaluate(async (f) => {
    const g = window.__g;
    g.renderer.quality.detailFade = f;
    await new Promise((res) => { let i = 0; const t = () => (++i >= 6 ? res() : requestAnimationFrame(t)); requestAnimationFrame(t); });
    return new Promise((res) => requestAnimationFrame(() => res(g.renderer.readbackStats(5))));
  }, fade);
  console.log(`detailFade=${String(fade).padStart(3)}  luma=${st.meanLuma.toFixed(4)} ` +
    `detail=${st.detail.toFixed(4)} flat=${(st.flatRatio * 100).toFixed(2)}% ` +
    `edge=${(st.edgeRatio * 100).toFixed(2)}% loc=${st.localContrast.toFixed(4)} col=${st.colorCells}`);
  await page.screenshot({ path: `${ROOT}tools/shots/ab-${fade}.png` });
}

await browser.close();
server.kill();
