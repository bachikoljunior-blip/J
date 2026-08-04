// ============================================================================
//  diag-camera.mjs — what is the camera actually doing, in the real game.
//
//  The audit reported surface detail of exactly 0 on four of six scenes, colour
//  diversity down by two thirds, and triangles up 57%, immediately after the
//  camera was rewritten. Two guesses at the cause were made and neither is
//  supported by the unit harness, which keeps 0.2 to 0.43 m of ground clearance
//  in every scenario including a hillside and a bowl.
//
//  Guessing at this costs twelve minutes a try. Booting the game and reading
//  the camera costs about one, so read the camera.
// ============================================================================

import { chromium } from '/home/user/Simple-browser-cookie-clicker-game/node_modules/playwright-core/index.mjs';
import { spawn } from 'node:child_process';
import { setTimeout as sleep } from 'node:timers/promises';

const PORT = 8193;
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
  const frames = (n) => new Promise((r) => {
    let i = 0;
    const tick = () => (++i >= n ? r() : requestAnimationFrame(tick));
    requestAnimationFrame(tick);
  });
  const c = p.camera;

  const snap = (label) => {
    const ground = g.world.heightAt(c.pos.x, c.pos.z);
    const dx = c.look.x - c.pos.x, dy = c.look.y - c.pos.y, dz = c.look.z - c.pos.z;
    const l = Math.hypot(dx, dy, dz) || 1;
    return {
      label,
      player: [+p.x.toFixed(1), +p.y.toFixed(2), +p.z.toFixed(1)],
      pos: [+c.pos.x.toFixed(2), +c.pos.y.toFixed(2), +c.pos.z.toFixed(2)],
      look: [+c.look.x.toFixed(2), +c.look.y.toFixed(2), +c.look.z.toFixed(2)],
      // Positive means the view is aimed above the horizon — at the sky.
      pitchDeg: +(Math.asin(dy / l) * 180 / Math.PI).toFixed(1),
      clearance: +(c.pos.y - ground).toFixed(2),
      boom: +(c.boom ?? -1).toFixed(2),
      lift: +(c.groundLift ?? -1).toFixed(3),
      yaw: +c.yaw.toFixed(3),
      camPitch: +c.pitch.toFixed(3),
      chunks: g.renderer?.stats?.terrainChunks ?? g._stats?.terrainChunks ?? -1,
    };
  };

  const rows = [];
  rows.push(snap('起動直後'));

  // The audit's own scenes, teleported to the same way it does.
  const SCENES = [
    ['day-meadow', 0, 0], ['peak', 239, 704], ['waste', -600, 300],
  ];
  for (const [name, x, z] of SCENES) {
    p.teleport(x, undefined, z);
    p.revive();
    await frames(60);
    rows.push(snap(`${name} 60f`));
    await frames(120);
    rows.push(snap(`${name} 180f`));
  }

  // The audit's camera probe, run verbatim, with the things it does not report
  // added: whether the lock stuck, and how far the camera yaw actually moved.
  // The probe drove 479 frames and reported a view rotation of exactly 0.000,
  // which either means the camera never turned or means the probe never asked
  // it to, and only one of those is a camera bug.
  p.revive();
  p.invuln = 999;
  p.lockTarget = null;
  await frames(20);
  c.resetTracking();
  const yawTrace = [];
  let lockHeld = 0, lockAsked = 0;
  const note = () => yawTrace.push(+c.yaw.toFixed(3));

  for (let i = 0; i < 200; i++) {
    const a2 = i * 0.05;
    p.x += Math.sin(a2) * 0.08;
    p.z += Math.cos(a2) * 0.08;
    await frames(1);
    if (i % 50 === 0) note();
  }
  const walkedTo = [+p.x.toFixed(1), +p.z.toFixed(1)];

  const e1 = g.spawnEnemy('bandit', p.x + 7, p.z + 2, { level: 1 });
  const e2 = g.spawnEnemy('bandit', p.x - 6, p.z - 4, { level: 1 });
  const spawned = [!!e1, !!e2];
  for (const [tgt, n] of [[e1, 50], [e2, 50], [e1, 50], [null, 40]]) {
    p.lockTarget = tgt;
    for (let i = 0; i < n; i++) {
      if (tgt) { lockAsked++; if (p.lockTarget === tgt) lockHeld++; }
      await frames(1);
    }
    note();
  }

  p.isSprinting = true;
  for (let i = 0; i < 90; i++) { p.x += 0.09; p.z += 0.04; await frames(1); }
  p.isSprinting = false;
  note();

  return {
    rows,
    probe: {
      view: +(c.worstView ?? -1).toFixed(4),
      warpFrames: c.warpFrames ?? -1,
      angSum: +(c.angSum ?? -1).toFixed(3),
      lastWarpStep: c.lastWarpStep ?? -1,
      why: c.worstViewWhy,
      dolly: +(c.worstDolly ?? -1).toFixed(4),
      frames: c.trackFrames,
      yawTrace,
      walkedTo,
      spawned,
      lockHeld,
      lockAsked,
      e1: e1 ? [+e1.x.toFixed(1), +e1.z.toFixed(1), e1.dead] : null,
      e2: e2 ? [+e2.x.toFixed(1), +e2.z.toFixed(1), e2.dead] : null,
    },
  };
});

console.log('カメラの実測');
for (const r of out.rows) {
  console.log(`  ${r.label.padEnd(16)} player=[${r.player}] pos=[${r.pos}]`);
  console.log(`  ${''.padEnd(16)} 視線仰角 ${String(r.pitchDeg).padStart(6)}deg  ` +
    `地面クリア ${String(r.clearance).padStart(7)}m  boom ${r.boom}  lift ${r.lift}  ` +
    `camPitch ${r.camPitch}  chunks ${r.chunks}`);
}
console.log('\n監査のカメラプローブを、そのまま走らせた結果');
console.log(`  ${JSON.stringify(out.probe)}`);

await browser.close();
server.kill();
