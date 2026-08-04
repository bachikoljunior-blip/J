// ============================================================================
//  diag-perf.mjs — the steady-state draw load, measured after the world has
//  finished streaming in rather than while it is still arriving.
//
//  Two audits of the same commit reported 229,045 and 409,347 triangles against
//  a 260,000 target, and the terrain chunk count went from 24 to 65. Terrain
//  chunks build a few per frame on a budget, so a probe that looks early sees a
//  partly-built world and reports a number that is not the game's — it is the
//  streaming system's progress at the instant it was asked.
//
//  The reflex is to call the high number noise and the low one correct. That is
//  backwards. A phone renders the world once it has arrived, so the honest
//  figure is the one taken after the build queue drains, and it is the larger of
//  the two. If the game is over budget, the measurement was hiding it.
//
//  This drives the build queue to empty, holds still, and reports the counts
//  with their spread across samples, so the difference between "the game draws
//  this much" and "this is where streaming had got to" is visible rather than
//  inferred.
// ============================================================================

import { chromium } from '/home/user/Simple-browser-cookie-clicker-game/node_modules/playwright-core/index.mjs';
import { spawn } from 'node:child_process';
import { setTimeout as sleep } from 'node:timers/promises';

const PORT = 8195;
const ROOT = new URL('..', import.meta.url).pathname;
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

// One budget was being applied to whichever tier the audit happened to run.
// The tiers differ mainly in how far they draw — viewDistance 380 / 450 / 620
// and propDistance 260 / 300 / 420 — and triangle count scales with the area
// that covers, so a number derived for the weakest device says nothing about
// the middle one. Measure each tier and let the evidence set the budgets.
const TIERS = ['low', 'medium', 'high'];
const SPOTS = [
  ['peak', 239, 704],
  ['meadow', 0, 0],
];

for (const tier of TIERS) {
  await page.evaluate((t) => {
    const g = window.__g;
    g.applyQuality(t);
    g.autoResolution = false;
    g.dynamicScale = 1;
    g.renderer.dynamicScale = 1;
    g.renderer.resize(g.canvas.width, g.canvas.height);
  }, tier);
  console.log(`
══════ 品質 ${tier} ══════`);
for (const [name, x, z] of SPOTS) {
  const r = await page.evaluate(async (spot) => {
    const g = window.__g;
    const p = g.player;
    const wait = (n) => new Promise((res) => {
      let i = 0;
      const tick = () => (++i >= n ? res() : requestAnimationFrame(tick));
      requestAnimationFrame(tick);
    });
    if (spot[1] !== null) { p.teleport(spot[1], undefined, spot[2]); p.revive(); }
    p.invuln = 999;
    await wait(30);

    // Drain the build queue: keep priming and waiting until nothing is left to
    // build for several consecutive frames. This is the difference between the
    // world the game draws and the world that had arrived when someone looked.
    let drained = 0, waited = 0;
    while (drained < 30 && waited < 1200) {
      g.terrain.primeAround(p.x, p.z, g.renderer.quality.viewDistance);
      const q = g.terrain.buildQueue ? g.terrain.buildQueue.length : 0;
      drained = q === 0 ? drained + 1 : 0;
      await wait(1);
      waited++;
    }

    // Then sample several times: a steady state that still moves is not one.
    const samples = [];
    for (let i = 0; i < 8; i++) {
      await wait(8);
      // Same source the audit reads: the GL wrapper's per-frame counters.
      samples.push({
        tri: g.glw.triangles,
        calls: g.glw.drawCalls,
        chunks: g.terrain.visible.length,
        byPass: { ...g.glw.triByTag },
      });
    }
    const tris = samples.map((s) => s.tri);
    const calls = samples.map((s) => s.calls);
    return {
      drainedAfter: waited,
      queueLeft: g.terrain.buildQueue ? g.terrain.buildQueue.length : -1,
      chunkMapSize: g.terrain.chunks ? g.terrain.chunks.size : -1,
      triMin: Math.min(...tris), triMax: Math.max(...tris),
      callMin: Math.min(...calls), callMax: Math.max(...calls),
      chunks: samples[samples.length - 1].chunks,
      byPass: samples[samples.length - 1].byPass,
      viewDistance: g.renderer.quality.viewDistance,
      propDistance: g.renderer.quality.propDistance,
      dynamicScale: +g.dynamicScale.toFixed(2),
    };
  }, [name, x, z]);

  console.log(`  ${name}  (viewDistance ${r.viewDistance}, propDistance ${r.propDistance})`);
  console.log(`    ビルド待ち行列が空になるまで ${r.drainedAfter} フレーム、残り ${r.queueLeft}`);
  console.log(`    チャンク: 描画 ${r.chunks} / 保持 ${r.chunkMapSize}`);
  console.log(`    三角形 ${r.triMin} – ${r.triMax}  (目標 ≤ 260000)  ${r.triMax > 260000 ? '← 超過' : 'ok'}`);
  console.log(`    ドローコール ${r.callMin} – ${r.callMax}  (目標 ≤ 120)  ${r.callMax > 120 ? '← 超過' : 'ok'}`);
  console.log(`    内訳 ${JSON.stringify(r.byPass)}`);
}
}

await browser.close();
server.kill();
