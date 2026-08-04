// ============================================================================
//  soak.mjs — play for a while and see whether the game gets worse.
//
//  Everything else in this repo measures a moment. The audit spawns things,
//  reads them, and tears them down inside a few seconds per probe, so a defect
//  that only shows up after ten minutes of play is invisible to all of it. The
//  entry in docs/FALSIFY.md reads "長時間プレイの破綻 — 数分の自動プレイしか
//  回していない。メモリの増加、数値の桁あふれ、クエスト状態の詰まり、セーブの
//  肥大は測っていない", and this is that entry being measured instead of listed.
//
//  What it looks for, in order of how badly each one ends a session:
//
//    - frame time drifting upward. A game that is slower at minute eight than
//      at minute one is accumulating something, and this catches it whatever
//      the something is.
//    - unbounded arrays. Actors, projectiles, timers, lights, damage numbers,
//      interacts, notifications: every one of these is appended to during play
//      and every one has to come back down.
//    - heap growth, when the browser will report it.
//    - save size, which is the one that eventually breaks localStorage.
//
//  The player is driven rather than idled. An idle soak measures a game with
//  nothing happening in it, which is the same mistake as reading a camera that
//  is standing still.
// ============================================================================

import { chromium } from '/home/user/Simple-browser-cookie-clicker-game/node_modules/playwright-core/index.mjs';
import { spawn } from 'node:child_process';
import { setTimeout as sleep } from 'node:timers/promises';

const PORT = Number(process.env.PORT || 8192);
const ROOT = new URL('..', import.meta.url).pathname;
// Long enough for a trend to separate from noise, short enough to sit in front
// of a twelve-minute audit without doubling the loop.
const MINUTES = Number(process.env.SOAK_MINUTES || 4);

const server = spawn('python3', ['-m', 'http.server', String(PORT), '--bind', '127.0.0.1'],
  { cwd: ROOT, stdio: 'ignore' });
await sleep(700);

const browser = await chromium.launch({
  executablePath: '/opt/pw-browsers/chromium',
  args: ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader',
    '--enable-unsafe-swiftshader', '--disable-dev-shm-usage',
    // Without this usedJSHeapSize is bucketed coarsely enough to hide a slow leak.
    '--enable-precise-memory-info'],
});
const page = await browser.newPage({ viewport: { width: 640, height: 400 } });
const errors = [];
page.on('pageerror', (e) => errors.push(e.message));
page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });

await page.goto(`http://127.0.0.1:${PORT}/index.html`, { waitUntil: 'domcontentloaded' });
await sleep(900);
await page.click('[data-t="new"]');
await sleep(300);
await page.click('[data-cls="knight"]');
await page.click('[data-t="start"]');
await page.waitForFunction(() => document.getElementById('loading').classList.contains('hidden'),
  null, { timeout: 180000 });
await sleep(1500);

console.log(`ソーク — ${MINUTES}分の自動プレイ中の変化を測る`);

const result = await page.evaluate(async (minutes) => {
  const g = window.__g;
  const p = g.player;
  const frame = () => new Promise((r) => requestAnimationFrame(r));

  const ARRAYS = ['actors', 'enemies', 'npcs', 'projectiles', 'areaEffects', 'timers',
    'lights', 'structureColliders', 'damageNumbers', 'interacts', 'notifications'];
  const sample = () => {
    const counts = {};
    for (const k of ARRAYS) counts[k] = Array.isArray(g[k]) ? g[k].length : -1;
    return {
      t: performance.now(),
      counts,
      heap: performance.memory ? performance.memory.usedJSHeapSize : 0,
      // Every save slot, not one guessed key: the bloat that ends a session is
      // the total the browser is holding, and a quest log that grows without
      // bound grows in whichever slot the player happens to use.
      save: (() => {
        try {
          let n = 0;
          for (let k = 0; k < localStorage.length; k++) {
            const key = localStorage.key(k);
            if (key && key.startsWith('kurogane.')) n += (localStorage.getItem(key) || '').length;
          }
          return n;
        } catch { return 0; }
      })(),
    };
  };

  // Warm-up: the first seconds include chunk streaming and shader compilation,
  // which is startup cost rather than drift, and folding it into the trend
  // would report a leak on every run.
  for (let i = 0; i < 240; i++) await frame();

  const samples = [];
  const frameTimes = [];
  const endAt = performance.now() + minutes * 60000;
  let last = performance.now();
  let i = 0;
  let sinceSample = 0;

  while (performance.now() < endAt) {
    // Drive: run a wandering circuit, swing periodically, and pick fights with
    // whatever is nearby. Idling would soak a game with nothing happening in it.
    const a = i * 0.017;
    p.x += Math.sin(a) * 0.10 + Math.sin(a * 0.13) * 0.05;
    p.z += Math.cos(a) * 0.10 + Math.cos(a * 0.11) * 0.05;
    if (i % 37 === 0) p._buffer('light');
    if (i % 149 === 0) p._buffer('heavy');
    if (i % 211 === 0) p._buffer('dodge');
    if (i % 90 === 0) { p.hp = p.maxHp; p.revive(); p.invuln = 3; }
    if (i % 600 === 0) {
      const ang = i * 0.7;
      g.spawnEnemy('bandit', p.x + Math.sin(ang) * 9, p.z + Math.cos(ang) * 9, { level: 1 });
    }
    if (i % 900 === 0) { try { g.save?.(); } catch { /* save is measured, not required */ } }

    await frame();
    const now = performance.now();
    frameTimes.push(now - last);
    last = now;
    i++;

    if (++sinceSample >= 120) { sinceSample = 0; samples.push(sample()); }
  }
  samples.push(sample());

  // Split the run in half and compare. A least-squares slope would be tidier,
  // but half-versus-half is harder to fool with a single spike and reads
  // directly as "was the second half worse than the first".
  const half = Math.floor(frameTimes.length / 2);
  const median = (xs) => {
    const s = xs.slice().sort((x, y) => x - y);
    return s.length ? s[Math.floor(s.length / 2)] : 0;
  };
  const firstHalf = median(frameTimes.slice(0, half));
  const secondHalf = median(frameTimes.slice(half));

  const first = samples[0], lastS = samples[samples.length - 1];
  const growth = {};
  for (const k of ARRAYS) growth[k] = lastS.counts[k] - first.counts[k];

  return {
    frames: frameTimes.length,
    minutes: (lastS.t - first.t) / 60000,
    frameFirst: firstHalf,
    frameSecond: secondHalf,
    frameDrift: firstHalf > 0 ? secondHalf / firstHalf : 1,
    heapFirst: first.heap,
    heapLast: lastS.heap,
    heapMBPerMin: first.heap
      ? ((lastS.heap - first.heap) / 1048576) / Math.max(0.1, (lastS.t - first.t) / 60000)
      : null,
    saveFirst: first.save,
    saveLast: lastS.save,
    countsFirst: first.counts,
    countsLast: lastS.counts,
    growth,
    peak: samples.reduce((acc, s) => {
      for (const k of ARRAYS) acc[k] = Math.max(acc[k] || 0, s.counts[k]);
      return acc;
    }, {}),
  };
}, MINUTES);

// --- verdict ----------------------------------------------------------------
const fails = [];
const line = (ok, text) => console.log(`  ${ok ? 'ok  ' : 'FAIL'} ${text}`);

console.log(`  ${result.frames} フレーム / ${result.minutes.toFixed(2)} 分`);

// A game that is 25% slower in its second half is accumulating something.
const driftOK = result.frameDrift <= 1.25;
if (!driftOK) fails.push('フレーム時間の悪化');
line(driftOK, `フレーム時間 前半 ${result.frameFirst.toFixed(1)}ms → 後半 ` +
  `${result.frameSecond.toFixed(1)}ms  (比 ${result.frameDrift.toFixed(3)}, 上限 1.25)`);

// Every one of these is appended to during play and must come back down.
// Enemies are excluded from the cap only in the sense that the driver spawns
// them on purpose; they still have to be bounded, so the cap is generous
// rather than absent.
for (const [k, v] of Object.entries(result.growth)) {
  const cap = k === 'enemies' || k === 'actors' ? 40 : 20;
  const ok = v <= cap;
  if (!ok) fails.push(`${k} が ${v} 増加`);
  if (v !== 0 || !ok) {
    line(ok, `${k.padEnd(19)} ${String(result.countsFirst[k]).padStart(4)} → ` +
      `${String(result.countsLast[k]).padStart(4)}  (増 ${v >= 0 ? '+' : ''}${v}, ` +
      `最大 ${result.peak[k]}, 上限 +${cap})`);
  }
}

if (result.heapMBPerMin !== null) {
  // Generous: a JS heap wanders with GC timing, and the point is to catch a
  // leak that would end a session, not to police allocation.
  const ok = result.heapMBPerMin <= 12;
  if (!ok) fails.push('ヒープの増加');
  line(ok, `ヒープ ${(result.heapFirst / 1048576).toFixed(1)}MB → ` +
    `${(result.heapLast / 1048576).toFixed(1)}MB  (${result.heapMBPerMin.toFixed(2)} MB/分, 上限 12)`);
} else {
  console.log('  --   ヒープ: この環境では読めない');
}

const saveOK = result.saveLast <= 20480;
if (!saveOK) fails.push('セーブの肥大');
line(saveOK, `セーブ ${result.saveFirst}B → ${result.saveLast}B  (上限 20480)`);

const errOK = errors.length === 0;
if (!errOK) fails.push(`コンソールエラー ${errors.length} 件`);
line(errOK, `コンソールエラー ${errors.length} 件`);
for (const e of errors.slice(0, 5)) console.log(`       ${e}`);

console.log(fails.length ? `\n${fails.length} 件 不合格: ${fails.join('、')}` : '\n全て合格');

await browser.close();
server.kill();
process.exit(fails.length ? 1 : 0);
