// ============================================================================
//  diag-track.mjs — why does the audit's camera probe report zero tracked
//  frames after swinging the view three radians?
//
//  The audit prints this:
//
//    camera: 0f  視線 0.000 rad/s @f-1  ドリー 0.000 m/s @f-1
//    camera probe: ... yaw旋回 3.082 rad ... 視線積算 0.00 rad
//
//  Those two lines contradict each other. The probe measured the camera's own
//  yaw moving 3.082 rad, so the camera was updating; the tracker recorded no
//  frames at all, so from its point of view nothing happened. A worst-case of
//  0.000 rad/s is also exactly what a perfect camera reports, which is the
//  third time in this project a measurement that could not be taken has come
//  back wearing the costume of a good result.
//
//  Reproducing it inside the audit costs twelve minutes a try. This runs the
//  same probe against the same live game in about one, and reports the two
//  counters that tell the possible causes apart:
//
//    updateCalls  frames that reached PlayerCamera.update
//    trackFrames  frames that reached the tracker and were counted
//
//  updates≈0            the game loop did not advance during the probe
//  updates≫0, track=0   the tracker rejected or reset every frame
// ============================================================================

import { spawn } from 'node:child_process';
import { setTimeout as sleep } from 'node:timers/promises';

const PLAYWRIGHT_CORE = process.env.PLAYWRIGHT_CORE
  || '/home/user/Simple-browser-cookie-clicker-game/node_modules/playwright-core/index.mjs';
const { chromium } = await import(PLAYWRIGHT_CORE);

const PORT = Number(process.env.PORT || 8197);
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

const out = await page.evaluate(async () => {
  const g = window.__g;
  const p = g.player;
  const c = p.camera;
  const frames = (n) => new Promise((r) => {
    let i = 0;
    const tick = () => (++i >= n ? r() : requestAnimationFrame(tick));
    requestAnimationFrame(tick);
  });

  p.revive();
  p.invuln = 999;
  p.lockTarget = null;
  await frames(20);

  // Is the camera object the probe holds the object the loop updates? A stale
  // reference would move neither counter and is the cheapest thing to rule out.
  const sameObject = g.player.camera === c;

  c.resetTracking();
  const yaw0 = c.yaw;

  // A short circuit, then a lock switch — the two parts of the audit's probe
  // that move the view most.
  let rafTicks = 0;
  for (let i = 0; i < 60; i++) {
    const a = i * 0.05;
    p.x += Math.sin(a) * 0.08;
    p.z += Math.cos(a) * 0.08;
    await frames(1); rafTicks++;
  }
  const afterWalk = { updates: c.updateCalls, track: c.trackFrames, ang: c.angSum };

  const e1 = g.spawnEnemy('bandit', p.x + 7, p.z + 2, { level: 1 });
  const e2 = g.spawnEnemy('bandit', p.x - 6, p.z - 4, { level: 1 });
  for (const [tgt, n] of [[e1, 30], [e2, 30], [e1, 30], [null, 20]]) {
    p.lockTarget = tgt;
    for (let i = 0; i < n; i++) { await frames(1); rafTicks++; }
  }
  let dYaw = c.yaw - yaw0;
  while (dYaw > Math.PI) dYaw -= 2 * Math.PI;
  while (dYaw < -Math.PI) dYaw += 2 * Math.PI;

  for (const e of [e1, e2]) { if (e.spawnRef) e.spawnRef.actor = null; g._removeActor(e); }
  p.lockTarget = null;

  // Is the *look point* finite? `pos` has a guard and a recovery path; `look`
  // has neither, and it is what the view matrix is built from. A non-finite
  // look point renders a frame with no geometry in it while every guard in the
  // class reports itself satisfied.
  const fin = (v) => Number.isFinite(v);
  const lookFinite = fin(c.look.x) && fin(c.look.y) && fin(c.look.z);
  const aimFinite = fin(c.aimOff.x) && fin(c.aimOff.y) && fin(c.aimOff.z);
  let mask = null;
  try { mask = g.renderer._spatialStats ? g.renderer._spatialStats() : null; } catch (e) { mask = String(e); }

  return {
    sameObject,
    rafTicks,
    afterWalk,
    lookFinite,
    aimFinite,
    look: { x: c.look.x, y: c.look.y, z: c.look.z },
    aim: { x: c.aimOff.x, y: c.aimOff.y, z: c.aimOff.z },
    boom: c.boom,
    pitchLift: c.pitchLift,
    mask,
    updates: c.updateCalls ?? -1,
    track: c.trackFrames ?? -1,
    ang: c.angSum ?? -1,
    warp: c.warpFrames ?? -1,
    nonFinite: c.nonFiniteFrames ?? -1,
    dtSeen: c.dtSeen ?? -1,
    worstView: c.worstView ?? -1,
    worstDolly: c.worstDolly ?? -1,
    why: c.worstViewWhy || null,
    yawMoved: +Math.abs(dYaw).toFixed(4),
    trkNull: c._trk === null,
    paused: !!g.paused,
    seeded: !!c.seeded,
  };
});

console.log(JSON.stringify(out, null, 2));

const verdict = out.updates <= 1
  ? 'ゲームループがプローブ中に進んでいない — 計測以前の問題'
  : out.track <= 1
    ? '更新は来ているのにトラッカーが全フレーム捨てている'
    : '両方動いている — 空振りは再現しない';
console.log(`\n判定: ${verdict}`);
console.log(`  update ${out.updates} 回 / 追跡 ${out.track} フレーム / rAF ${out.rafTicks} 回`);

await browser.close();
server.kill();
