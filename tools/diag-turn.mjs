// ============================================================================
//  diag-turn.mjs — find which bone, on which frame, in which state, produces
//  the largest single-frame rotation.
//
//  The audit reports one number for this and it has been bit-identical across
//  seven runs, which says the cause is a single deterministic event rather than
//  anything that drifts. One number cannot say which event; this prints the
//  ranked list so the fix can go at the cause instead of at the cap.
// ============================================================================

import { chromium } from '/home/user/Simple-browser-cookie-clicker-game/node_modules/playwright-core/index.mjs';
import { spawn } from 'node:child_process';
import { setTimeout as sleep } from 'node:timers/promises';

const PORT = 8190;
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
await sleep(1200);

const out = await page.evaluate(async () => {
  const g = window.__g;
  const p = g.player;
  const frames = () => new Promise((r) => requestAnimationFrame(r));
  // Reproduce the audit exactly: it runs this sequence *after* the foot-IK
  // probe has teleported the player onto the steepest slope it could find, so
  // whatever the number is, it is a number about standing on a slope.
  let sx = p.x, sz = p.z, best = 0;
  for (let a = 0; a < 64; a++) {
    const x = p.x + Math.cos(a) * (20 + a * 3), z = p.z + Math.sin(a) * (20 + a * 3);
    const s = g.world.slopeAt(x, z);
    if (s > best && s < 0.55 && g.world.heightAt(x, z) > 1) { best = s; sx = x; sz = z; }
  }
  p.teleport(sx, undefined, sz);
  p.revive();
  p.invuln = 999;
  for (let i = 0; i < 40; i++) await frames();

  const names = p.rig.template.boneList.map((b) => b.name);
  const events = [];
  const prev = new Float32Array(p.rig.worldRot.length);
  prev.set(p.rig.worldRot);

  for (let i = 0; i < 90; i++) {
    if (i === 10) p._buffer('light');
    if (i === 28) p._buffer('dodge');
    if (i === 46) p._buffer('heavy');
    await frames();
    const wr = p.rig.worldRot;
    for (let b = 0; b < wr.length; b += 9) {
      const d = prev[b + 3] * wr[b + 3] + prev[b + 4] * wr[b + 4] + prev[b + 5] * wr[b + 5];
      const ang = Math.acos(Math.max(-1, Math.min(1, d)));
      if (ang > 0.15) {
        events.push({
          frame: i,
          bone: names[b / 9] || `#${b / 9}`,
          ang: +ang.toFixed(4),
          state: p.state,
          plant: p.rig.plantS ? Array.from(p.rig.plantS).map((v) => +v.toFixed(2)) : null,
          ikw: +(p.rig.ikWeight || 0).toFixed(2),
        });
      }
    }
    prev.set(wr);
  }
  events.sort((a, b) => b.ang - a.ang);
  return { top: events.slice(0, 18), count: events.length, slope: +best.toFixed(3) };
});

console.log(`斜面 slope=${out.slope} / 0.15 rad/frame 超え: ${out.count}`);
for (const e of out.top) {
  console.log(`  f${String(e.frame).padStart(2)} ${e.bone.padEnd(11)} ${e.ang.toFixed(4)} rad` +
    `  state=${e.state} ik=${e.ikw} plant=${JSON.stringify(e.plant)}`);
}

await browser.close();
server.kill();
