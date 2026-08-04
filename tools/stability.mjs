// ============================================================================
//  stability.mjs — which criteria measure the game, and which measure the
//  machine it happened to run on.
//
//  Two audits of the same commit reported 229,045 and 409,347 triangles against
//  a 260,000 target. One passed, one failed, and nothing about the game changed
//  between them; the second run simply had more CPU, so more terrain chunks had
//  finished building by the time the probe looked.
//
//  That is not a small problem. The gate's whole purpose is to be a termination
//  condition, and a verdict that flips with machine load is not one. Worse, it
//  breaks the stall detector in tools/gate.mjs in the direction that hides the
//  failure: a noisy criterion makes every attempt's failure signature different,
//  so the loop reads noise as progress and keeps burning twelve-minute runs.
//
//  This reads docs/audit-runs.json — every audit appends its full criterion
//  table there with the commit it ran on — and reports, per criterion, the
//  spread across runs of a SINGLE commit. Anything that moves while the code did
//  not is measuring something other than the code.
//
//    node tools/stability.mjs
//
//  It needs at least two runs of one commit to say anything, and says so plainly
//  when it does not have them rather than inventing a verdict from one sample.
// ============================================================================

import { readFileSync, existsSync } from 'node:fs';

const ROOT = new URL('..', import.meta.url).pathname;
const PATH = `${ROOT}docs/audit-runs.json`;

if (!existsSync(PATH)) {
  console.log('docs/audit-runs.json が無い。監査を1回以上走らせること。');
  process.exit(0);
}

const runs = JSON.parse(readFileSync(PATH, 'utf8'));
console.log(`記録された監査: ${runs.length} 回`);
for (const r of runs) {
  console.log(`  ${r.stamp}  ${r.commit}  総合 ${r.total}  未達 ${r.unmet}  ${r.pass ? 'PASS' : 'FAIL'}`);
}

// Group by commit: the comparison is only meaningful within one build.
const byCommit = new Map();
for (const r of runs) {
  if (!byCommit.has(r.commit)) byCommit.set(r.commit, []);
  byCommit.get(r.commit).push(r);
}

const repeated = [...byCommit.entries()].filter(([, rs]) => rs.length >= 2);
if (!repeated.length) {
  console.log('\n同一コミットでの複数回の記録が無いので、安定性は判定できない。');
  console.log('同じコミットでもう一度 node tools/audit.mjs を走らせること。');
  console.log('（1回の実行から安定性を語ることはできない——それが今回の問題そのもの）');
  process.exit(0);
}

const numeric = (v) => (typeof v === 'number' ? v : null);
let unstable = 0;

for (const [commit, rs] of repeated) {
  console.log(`\n═══ ${commit} — ${rs.length} 回の実行 ═══`);
  const labels = new Map();
  for (const r of rs) {
    for (const it of r.items) {
      const key = `${it.axis} ${it.label}`;
      if (!labels.has(key)) labels.set(key, []);
      labels.get(key).push(it);
    }
  }

  const rows = [];
  for (const [key, its] of labels) {
    if (its.length < 2) continue;
    const vals = its.map((i) => numeric(i.value)).filter((v) => v !== null);
    const oks = its.map((i) => i.ok);
    const flipped = oks.some((o) => o !== oks[0]);
    if (vals.length < 2) {
      // Non-numeric (あり/なし). Only a flip matters.
      if (flipped) rows.push({ key, flipped, spread: null, lo: null, hi: null, rel: 1 });
      continue;
    }
    const lo = Math.min(...vals), hi = Math.max(...vals);
    const denom = Math.max(Math.abs(lo), Math.abs(hi), 1e-9);
    const rel = (hi - lo) / denom;
    if (rel > 0.02 || flipped) rows.push({ key, flipped, spread: hi - lo, lo, hi, rel });
  }

  rows.sort((a, b) => (b.flipped - a.flipped) || (b.rel - a.rel));
  if (!rows.length) {
    console.log('  同じコミットでは全項目が一致した。この範囲では計測は安定している。');
    continue;
  }
  for (const r of rows) {
    if (r.flipped) unstable++;
    const mark = r.flipped ? '合否が反転' : '値が動く  ';
    const range = r.spread === null ? '' :
      `  ${r.lo} → ${r.hi}  (幅 ${(r.rel * 100).toFixed(1)}%)`;
    console.log(`  ${r.flipped ? '!!' : '  '} ${mark}  ${r.key}${range}`);
  }
}

console.log('');
if (unstable) {
  console.log(`${unstable} 件の項目が、同じコードで合否を変えている。`);
  console.log('この状態のゲートは終了条件として使えない——同じビルドを測り直すだけで');
  console.log('判定が変わるため、修正が効いたのか実行がぶれただけなのか区別できない。');
  console.log('該当項目は、定常状態に達してから測るか、機械の速度に依らない量に置き換えること。');
} else {
  console.log('同じコードで合否が反転した項目は無い。');
}
process.exit(unstable ? 1 : 0);
