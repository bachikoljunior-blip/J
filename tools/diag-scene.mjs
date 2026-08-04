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

// Bisect: optionally run the audit's earlier probes first. The audit reports
// zero world-mask pixels on every scene; this file, running the same scenes
// against the same build, reports 25,000 to 37,000. Something one of the
// earlier probes leaves behind is the difference, and the cheapest way to find
// out which is to add them one at a time.
//
//   node tools/diag-scene.mjs            # scenes only, the working case
//   node tools/diag-scene.mjs --camera   # camera probe first
//   node tools/diag-scene.mjs --motion   # motion probe first
//   node tools/diag-scene.mjs --both
const PRE = {
  camera: process.argv.includes('--camera') || process.argv.includes('--both'),
  motion: process.argv.includes('--motion') || process.argv.includes('--both'),
};
if (PRE.camera || PRE.motion) {
  console.log(`前段プローブ: ${Object.entries(PRE).filter(([, v]) => v).map(([k]) => k).join(', ')}`);
  await page.evaluate(async (pre) => {
    const g = window.__g;
    const p = g.player;
    const frames = (n) => new Promise((r) => {
      let i = 0;
      const tick = () => (++i >= n ? r() : requestAnimationFrame(tick));
      requestAnimationFrame(tick);
    });
    if (pre.motion) {
      let sx = p.x, sz = p.z, best = 0;
      for (let a = 0; a < 64; a++) {
        const x = p.x + Math.cos(a) * (20 + a * 3), z = p.z + Math.sin(a) * (20 + a * 3);
        const sl = g.world.slopeAt(x, z);
        if (sl > best && sl < 0.55 && g.world.heightAt(x, z) > 1) { best = sl; sx = x; sz = z; }
      }
      p.teleport(sx, undefined, sz);
      p.revive(); p.invuln = 99;
      await frames(40);
      for (const ang of [0, Math.PI / 2, Math.PI, -Math.PI / 2]) {
        const e = g.spawnEnemy('bandit', p.x + Math.sin(ang) * 3, p.z + Math.cos(ang) * 3, { level: 1 });
        p.revive();
        p.takeDamage({ damage: 5, poise: 1, source: e, ignoreInvuln: true });
        if (e.spawnRef) e.spawnRef.actor = null;
        g._removeActor(e);
      }
      p.revive();
      for (let i = 0; i < 90; i++) {
        if (i === 10) p._buffer('light');
        if (i === 28) p._buffer('dodge');
        if (i === 46) p._buffer('heavy');
        await frames(1);
      }
      const e2 = g.spawnEnemy('bandit', p.x + 1.4, p.z, { level: 1 });
      for (let i = 0; i < 200 && !e2.dead; i++) {
        const yaw = Math.atan2(e2.x - p.x, e2.z - p.z);
        p.yaw = yaw;
        p.teleport(e2.x - Math.sin(yaw) * 1.5, undefined, e2.z - Math.cos(yaw) * 1.5);
        if (i % 20 === 0) p._buffer('light');
        await frames(1);
      }
      for (const e of g.enemies.slice()) { if (e.spawnRef) e.spawnRef.actor = null; g._removeActor(e); }
      p.setState('idle'); p.hp = p.maxHp; p.invuln = 0;
      await frames(2);
    }
    if (pre.camera) {
      p.revive(); p.invuln = 999; p.lockTarget = null;
      await frames(20);
      p.camera.resetTracking();
      for (let i = 0; i < 200; i++) {
        const a = i * 0.05;
        p.x += Math.sin(a) * 0.08; p.z += Math.cos(a) * 0.08;
        await frames(1);
      }
      const e1 = g.spawnEnemy('bandit', p.x + 7, p.z + 2, { level: 1 });
      const e2 = g.spawnEnemy('bandit', p.x - 6, p.z - 4, { level: 1 });
      for (const [tgt, n] of [[e1, 50], [e2, 50], [e1, 50], [null, 40]]) {
        p.lockTarget = tgt;
        await frames(n);
      }
      p.isSprinting = true;
      for (let i = 0; i < 90; i++) { p.x += 0.09; p.z += 0.04; await frames(1); }
      p.isSprinting = false;
      for (const e of [e1, e2]) { if (e.spawnRef) e.spawnRef.actor = null; g._removeActor(e); }
      p.lockTarget = null;
    }
  }, PRE);
}

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
    // Same ordering guarantee as the audit: a macrotask cannot run until the
    // whole requestAnimationFrame batch has drained, so the game's render for
    // this frame has definitely happened. Kept identical on both sides so the
    // two remain comparable — the difference between them is the thing being
    // investigated, and it must not be this.
    await new Promise((r) => { requestAnimationFrame(() => setTimeout(r, 0)); });
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
      // The field is colorCells, not colorBins. Reading the wrong name printed
      // -1 for three runs — the same shape of mistake as everything else here:
      // a value that means "not measured" wearing the costume of a number.
      colorCells: stat0 ? (stat0.colorCells ?? -1) : -1,
      worldPixelsStat: stat0 ? (stat0.worldPixels ?? -1) : -1,
      measurable: stat0 ? stat0.measurable : null,
      maskDepth: stat0 ? stat0.maskDepth : null,
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
  // Hide the HUD before the shot. readbackStats composites the scene WITHOUT
  // the DOM overlay, so a screenshot that includes buttons, bars and a minimap
  // is not the same image and cannot be compared against it — the UI's flat
  // saturated blocks move both saturation and colour-bin counts on their own.
  await page.evaluate(() => {
    const h = document.getElementById('hud');
    if (h) h.style.visibility = 'hidden';
  });
  await page.screenshot({ path: `${SHOTS}/diag-${s.id}.png` });
  await page.evaluate(() => {
    const h = document.getElementById('hud');
    if (h) h.style.visibility = '';
  });
  console.log(`${s.id.padEnd(12)} boom=${stat.boom} clear=${stat.clearance} ` +
    `dynScale=${stat.dynamicScale}/${stat.rendererScale} scene=${stat.sceneW}x${stat.sceneH} ` +
    `depthTex=${stat.hasDepthTex}`);
  console.log(`             マスク世界画素 ${stat.maskNonZero}/${stat.maskTotal}  ` +
    `detail=${stat.detail} flat=${stat.flatRatio} bins=${stat.colorCells} ` +
    `measurable=${stat.measurable} depth=${JSON.stringify(stat.maskDepth)} ` +
    `localC=${stat.localContrast} sat=${stat.saturation}`);
}

await browser.close();
server.kill();
console.log(`\nPNG: ${SHOTS}/diag-*.png`);
