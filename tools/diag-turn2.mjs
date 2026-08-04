// ============================================================================
//  diag-turn2.mjs — reproduce the audit's transition probe *exactly*, including
//  the hurt-direction probe that runs immediately before it, and report the
//  budget breakdown on the frame that exceeds the cap.
//
//  diag-turn.mjs ran the same 90-frame sequence and peaked at 0.172 rad, while
//  the audit reported 0.364 from what looked like the same code. The audit's
//  instrumentation put the event at frame 0, bone forearmR, state idle — that
//  is, on the very first frame after the hurt probe, before any of the buffered
//  inputs fire. The difference between the two harnesses is the hurt probe, so
//  this one keeps it.
//
//  The rig already caps the whole skeleton at TURN_STEP per frame. A reading
//  above the cap means some term reaches the world transform without passing
//  through the budget, and the only way to find out which is to print them all.
// ============================================================================

import { chromium } from '/home/user/Simple-browser-cookie-clicker-game/node_modules/playwright-core/index.mjs';
import { spawn } from 'node:child_process';
import { setTimeout as sleep } from 'node:timers/promises';

const PORT = 8191;
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
  const frames = (n) => new Promise((r) => {
    let i = 0;
    const step = () => (++i >= n ? r() : requestAnimationFrame(step));
    requestAnimationFrame(step);
  });

  // --- the audit's foot-IK probe -------------------------------------------
  let sx = p.x, sz = p.z, best = 0;
  for (let a = 0; a < 64; a++) {
    const x = p.x + Math.cos(a) * (20 + a * 3), z = p.z + Math.sin(a) * (20 + a * 3);
    const s = g.world.slopeAt(x, z);
    if (s > best && s < 0.55 && g.world.heightAt(x, z) > 1) { best = s; sx = x; sz = z; }
  }
  p.teleport(sx, undefined, sz);
  p.revive(); p.invuln = 99;
  await frames(40);

  // --- the audit's hurt-direction probe ------------------------------------
  const dirs = new Set();
  for (const ang of [0, Math.PI / 2, Math.PI, -Math.PI / 2]) {
    const e = g.spawnEnemy('bandit', p.x + Math.sin(ang) * 3, p.z + Math.cos(ang) * 3, { level: 1 });
    p.revive();
    p.takeDamage({ damage: 5, poise: 1, source: e, ignoreInvuln: true });
    dirs.add(Math.round((p.lastDamageDir || 0) * 8) / 8);
    if (e.spawnRef) e.spawnRef.actor = null;
    g._removeActor(e);
  }

  // --- the audit's transition probe, with the budget exposed ---------------
  p.revive();
  const names = p.rig.template.boneList.map((b) => b.name);
  const prev = new Float32Array(p.rig.worldRot.length);
  prev.set(p.rig.worldRot);
  let prevYaw = p.yaw;
  const prevRoot = Array.from(p.rig._rootTurn);
  const rows = [];

  for (let i = 0; i < 90; i++) {
    if (i === 10) p._buffer('light');
    if (i === 28) p._buffer('dodge');
    if (i === 46) p._buffer('heavy');
    await frames(1);
    const wr = p.rig.worldRot;
    let worstAng = 0, worstBone = '';
    for (let b = 0; b < wr.length; b += 9) {
      const d = prev[b + 3] * wr[b + 3] + prev[b + 4] * wr[b + 4] + prev[b + 5] * wr[b + 5];
      const ang = Math.acos(Math.max(-1, Math.min(1, d)));
      if (ang > worstAng) { worstAng = ang; worstBone = names[b / 9] || `#${b / 9}`; }
    }
    let dYaw = p.yaw - prevYaw;
    if (dYaw > Math.PI) dYaw -= 2 * Math.PI; else if (dYaw < -Math.PI) dYaw += 2 * Math.PI;
    const rt = p.rig._rootTurn;
    rows.push({
      f: i,
      ang: +worstAng.toFixed(4),
      bone: worstBone,
      state: p.state,
      dYaw: +dYaw.toFixed(4),
      dRoot: [0, 1, 2].map((a) => +(rt[a] - prevRoot[a]).toFixed(4)),
      warped: !!p.rig.warped,
      blend: p.rig.blendRate,
    });
    prev.set(wr);
    prevYaw = p.yaw;
    for (let a = 0; a < 3; a++) prevRoot[a] = rt[a];
  }
  return { rows, slope: +best.toFixed(3), dirs: dirs.size };
});

const cap = 0.27;
console.log(`斜面 slope=${out.slope}  hurtDirs=${out.dirs}  cap=${cap}`);
const over = out.rows.filter((r) => r.ang > cap);
console.log(`cap 超えフレーム: ${over.length} / 90`);
for (const r of [...out.rows].sort((a, b) => b.ang - a.ang).slice(0, 8)) {
  console.log(`  f${String(r.f).padStart(2)} ${r.bone.padEnd(11)} ${r.ang.toFixed(4)} rad  ` +
    `state=${r.state} dYaw=${r.dYaw.toFixed(4)} dRoot=${JSON.stringify(r.dRoot)} ` +
    `warped=${r.warped} blend=${r.blend}`);
}

await browser.close();
server.kill();
