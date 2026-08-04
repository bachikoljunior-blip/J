// ============================================================================
//  diag-scene.mjs — capture the audit's six presentation scenes and report the
//  same statistics it does, plus a PNG of each, in about two minutes.
//
//  The audit reported surface detail of exactly 0 on four of six scenes and
//  colour diversity down by two thirds. Two hypotheses about the cause have
//  already been checked and refuted (the camera is not underground; the camera
//  state at these scenes is unchanged). Falsification #1 in docs/FALSIFY.md was
//  settled by opening the screenshot, and nothing since has been faster.
// ============================================================================

import { chromium } from '/home/user/Simple-browser-cookie-clicker-game/node_modules/playwright-core/index.mjs';
import { spawn } from 'node:child_process';
import { mkdirSync } from 'node:fs';
import { setTimeout as sleep } from 'node:timers/promises';

const PORT = 8194;
const ROOT = new URL('..', import.meta.url).pathname;
const SHOTS = `${ROOT}tools/shots`;
mkdirSync(SHOTS, { recursive: true });

const server = spawn('python3', ['-m', 'http.server', String(PORT), '--bind', '127.0.0.1'],
  { cwd: ROOT, stdio: 'ignore' });
await sleep(700);
const browser = await chromium.launch({
  executablePath: '/opt/pw-browsers/chromium',
  args: ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader',
    '--enable-unsafe-swiftshader', '--disable-dev-shm-usage'],
});
const page = await browser.newPage({ viewport: { width: 640, height: 400 } });
page.on('pageerror', (e) => console.log('ERR', e.message));
await page.goto(`http://127.0.0.1:${PORT}/index.html`, { waitUntil: 'domcontentloaded' });
await sleep(900);
await page.click('[data-t="new"]');
await sleep(300);
await page.click('[data-cls="knight"]');
await page.click('[data-t="start"]');
await page.waitForFunction(() => document.getElementById('loading').classList.contains('hidden'),
  null, { timeout: 180000 });
await sleep(1500);
await page.evaluate(() => { window.__g.applyQuality('medium'); window.__g.dynamicScale = 1; });

const SCENES = [
  { id: 'day-meadow', region: 'meadow', hour: 11.0, weather: 'clear', yaw: 0.6 },
  { id: 'peak', region: 'peak', hour: 9.0, weather: 'clear', yaw: 0.6 },
  { id: 'night-ridge', region: 'ridge', hour: 22.5, weather: 'clear', yaw: 0.6 },
];

for (const s of SCENES) {
  const stat = await page.evaluate(async (sc) => {
    const g = window.__g;
    const p = g.player;
    const wg = await import('/src/world/worldgen.js');
    const region = wg.REGIONS.find((r) => r.id === sc.region);
    const spot = g.world.findFlatSpot(region.cx, region.cz, 220, 0.25);
    p.teleport(spot.x, undefined, spot.z);
    window.__ui.closeAll();
    g.paused = false;
    g.timers.length = 0;
    p.revive();
    p.stamina = p.maxStamina; p.invuln = 9;
    g.renderer.deathFade = 0;
    g.renderer.damageFlash = 0;
    for (const e of g.enemies.slice()) { if (e.spawnRef) e.spawnRef.actor = null; g._removeActor(e); }
    p.yaw = sc.yaw;
    p.camera.yaw = sc.yaw;
    p.camera.pitch = -0.20;
    p.lockTarget = null;
    g.renderer.hour = sc.hour;
    g.renderer.forcedWeather = sc.weather;
    g.terrain.primeAround(p.x, p.z, 320);
    g.grass.dirty = true;
    await new Promise((res) => {
      let i = 0;
      const tick = () => (++i >= 150 ? res() : requestAnimationFrame(tick));
      requestAnimationFrame(tick);
    });
    const stat0 = g.renderer.readbackStats(5);
    // Why the world mask matters here: 表面ディテール is gradSum/gradN over the
    // pixels the depth-derived mask calls world. If the mask is empty, gradN is
    // zero and the criterion reports exactly 0 — which is what the audit did on
    // four of six scenes. That is a mask failure, not a rendering failure, and
    // the two are indistinguishable from the printed number alone.
    const r = g.renderer;
    let maskNonZero = -1, maskTotal = -1;
    if (r._maskBuf) {
      maskTotal = r._maskBuf.length / 4;
      maskNonZero = 0;
      for (let i = 0; i < r._maskBuf.length; i += 4) if (r._maskBuf[i] > 127) maskNonZero++;
    }
    const c = p.camera;
    return {
      dynamicScale: +(g.dynamicScale ?? -1).toFixed(3),
      rendererScale: +(r.dynamicScale ?? -1).toFixed(3),
      sceneW: r.scene ? r.scene.width : -1,
      sceneH: r.scene ? r.scene.height : -1,
      hasDepthTex: !!(r.scene && r.scene.depthTex),
      maskNonZero,
      maskTotal,
      detail: stat0 ? +(stat0.detail ?? -1).toFixed(4) : -1,
      flatRatio: stat0 ? +(stat0.flatRatio ?? -1).toFixed(4) : -1,
      colorBins: stat0 ? (stat0.colorBins ?? -1) : -1,
      localContrast: stat0 ? +(stat0.localContrast ?? -1).toFixed(4) : -1,
      saturation: stat0 ? +(stat0.saturation ?? -1).toFixed(4) : -1,
      pos: [+c.pos.x.toFixed(2), +c.pos.y.toFixed(2), +c.pos.z.toFixed(2)],
      look: [+c.look.x.toFixed(2), +c.look.y.toFixed(2), +c.look.z.toFixed(2)],
      boom: +(c.boom ?? -1).toFixed(2),
      lift: +(c.groundLift ?? -1).toFixed(3),
      ground: +g.world.heightAt(c.pos.x, c.pos.z).toFixed(2),
      clearance: +(c.pos.y - g.world.heightAt(c.pos.x, c.pos.z)).toFixed(2),
      stats: g.renderer.stats ? JSON.parse(JSON.stringify(g.renderer.stats)) : null,
    };
  }, s);
  await page.screenshot({ path: `${SHOTS}/diag-${s.id}.png` });
  console.log(`${s.id.padEnd(12)} boom=${stat.boom} clear=${stat.clearance} ` +
    `dynScale=${stat.dynamicScale}/${stat.rendererScale} scene=${stat.sceneW}x${stat.sceneH} ` +
    `depthTex=${stat.hasDepthTex}`);
  console.log(`             マスク世界画素 ${stat.maskNonZero}/${stat.maskTotal}  ` +
    `detail=${stat.detail} flat=${stat.flatRatio} bins=${stat.colorBins} ` +
    `localC=${stat.localContrast} sat=${stat.saturation}`);
}

await browser.close();
server.kill();
console.log(`\nPNG: ${SHOTS}/diag-*.png`);
