import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile, access } from 'node:fs/promises';
import { resolve } from 'node:path';

import { QuestLog, QUEST_STATE } from '../src/game/quests.js';

const root = resolve(import.meta.dirname, '..');

test('main quest advances and reports a final turn-in as ready', () => {
  const log = new QuestLog();
  assert.equal(log.start('main_1'), true);

  let progress = log.notify({ type: 'talk', npc: 'harum' });
  assert.equal(progress[0].result.step.id, 's2');
  assert.equal(log.get('main_1').step, 1);

  progress = log.notify({ type: 'boss', boss: 'warden' });
  assert.equal(progress[0].result.step.id, 's3');
  assert.equal(log.get('main_1').step, 2);

  progress = log.notify({ type: 'talk', npc: 'harum' });
  assert.equal(progress[0].result.ready, true);
  assert.equal(log.get('main_1').status, QUEST_STATE.ACTIVE);
  assert.equal(log.isStepReady('main_1', 's3'), true);
});

test('quest save data round-trips without losing counters or flags', () => {
  const source = new QuestLog();
  source.start('main_1');
  source.notify({ type: 'talk', npc: 'harum' });
  source.setFlag('quality_verified');

  const restored = new QuestLog();
  restored.deserialize(source.serialize());
  assert.deepEqual(restored.serialize(), source.serialize());
  assert.equal(restored.hasFlag('quality_verified'), true);
});

test('HTML ids are unique and the new mobile guidance surfaces exist', async () => {
  const html = await readFile(resolve(root, 'index.html'), 'utf8');
  const ids = [...html.matchAll(/\bid="([^"]+)"/g)].map((match) => match[1]);
  assert.equal(new Set(ids).size, ids.length, 'duplicate HTML id');
  for (const id of ['objective-tracker', 'objective-marker', 'tutorial-card', 'save-indicator']) {
    assert.ok(ids.includes(id), `missing #${id}`);
  }
});

test('every service-worker asset exists', async () => {
  const source = await readFile(resolve(root, 'sw.js'), 'utf8');
  const list = source.match(/const ASSETS = \[([\s\S]*?)\];/)?.[1] || '';
  const paths = [...list.matchAll(/'\.\/([^']*)'/g)].map((match) => match[1]).filter(Boolean);
  assert.ok(paths.length >= 25, 'asset list unexpectedly short');
  await Promise.all(paths.map((path) => access(resolve(root, path))));
});

test('all touch actions retain an accessible label', async () => {
  const html = await readFile(resolve(root, 'index.html'), 'utf8');
  const controls = [...html.matchAll(/<button\s+id="(btn-[^"]+)"([^>]*)>/g)];
  assert.ok(controls.length >= 15);
  for (const [, id, attrs] of controls) {
    assert.match(attrs, /aria-label="[^"]+"/, `${id} has no aria-label`);
  }
});

test('the frame loop stops after a fatal error and WebGL loss is recoverable', async () => {
  const source = await readFile(resolve(root, 'src/main.js'), 'utf8');
  const frame = source.match(/function frame\(now\) \{([\s\S]*?)\n\}/)?.[1] || '';
  assert.ok(frame.indexOf('try {') < frame.indexOf('requestAnimationFrame(frame)'),
    'the next frame must only be queued after a successful update');
  assert.match(source, /webglcontextlost/);
  assert.match(source, /webglcontextrestored/);
  assert.match(source, /autosave\('描画復旧前'/);
});

test('mobile controls never shrink below a 44px touch target', async () => {
  const css = await readFile(resolve(root, 'style.css'), 'utf8');
  assert.match(css, /--btn-sm:\s*clamp\(44px,/);
  assert.match(css, /button\s*\{\s*min-width:\s*44px;\s*min-height:\s*44px;/);
});
