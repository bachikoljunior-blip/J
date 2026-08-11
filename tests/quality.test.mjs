import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const read = file => fs.readFileSync(path.join(ROOT, file), 'utf8');

function loadCore(localStorage) {
  const context = {
    console,
    navigator: { userAgent: 'iPhone', deviceMemory: 4, hardwareConcurrency: 4, maxTouchPoints: 5 },
    localStorage
  };
  context.window = context;
  vm.createContext(context);
  vm.runInContext(read('js/core.js'), context, { filename: 'js/core.js' });
  return context.G;
}

test('30fpsを快適域として維持し、重い時だけ二段階で負荷を下げる', () => {
  const storage = { getItem: () => null, setItem: () => {}, removeItem: () => {} };
  const G = loadCore(storage);
  let state = G.PerformanceGovernor.initial();
  for (let i = 0; i < 20; i++) state = G.PerformanceGovernor.step(state, 33.3, 'mid');
  assert.equal(state.resolution, 1);
  assert.equal(state.detail, 1);

  for (let i = 0; i < 30; i++) state = G.PerformanceGovernor.step(state, 50, 'mid');
  assert.equal(state.resolution, 0.64);
  assert.equal(state.detail, 0.72);

  for (let i = 0; i < 60; i++) state = G.PerformanceGovernor.step(state, 20, 'mid');
  assert.equal(state.resolution, 1);
  assert.equal(state.detail, 1);
});

test('ストレージが拒否されても設定初期化は落ちない', () => {
  const blocked = {
    getItem() { throw new Error('blocked'); },
    setItem() { throw new Error('blocked'); },
    removeItem() { throw new Error('blocked'); }
  };
  const G = loadCore(blocked);
  assert.equal(G.settings.quality, 'auto');
  assert.doesNotThrow(() => G.settings.save());
});

test('壊れた主保存から有効な予備保存へ復旧できる', () => {
  const data = {
    v: 1,
    stats: { level: 3, xp: 12 },
    pos: { x: 4, z: 8 },
    inv: {}, quests: {}
  };
  const store = new Map([
    ['eldria_save_v1', '{broken'],
    ['eldria_save_backup_v1', JSON.stringify(data)]
  ]);
  const G = {
    storage: {
      get: key => store.get(key) ?? null,
      set: (key, value) => { store.set(key, value); return true; },
      remove: key => { store.delete(key); return true; }
    }
  };
  const systems = read('js/systems.js');
  const saveSection = systems.slice(systems.indexOf('/* ======================= セーブ / ロード'));
  vm.runInNewContext(saveSection, { G }, { filename: 'save-section.js' });
  const loaded = G.Save.load();
  assert.equal(loaded.stats.level, 3);
  assert.equal(loaded._recovered, true);
  assert.equal(G.Save.exists(), true);
  assert.equal(G.Save.reset(), true);
  assert.equal(store.size, 0);
});

test('PWAの全キャッシュ資産・iPhone用アイコンが存在する', () => {
  const manifest = JSON.parse(read('manifest.json'));
  for (const size of ['180x180', '192x192', '512x512']) {
    const icon = manifest.icons.find(item => item.sizes === size && item.type === 'image/png');
    assert.ok(icon, `${size} PNG icon`);
    assert.ok(fs.existsSync(path.join(ROOT, icon.src)), icon.src);
  }
  const sw = read('sw.js');
  const block = sw.match(/const ASSETS = \[([\s\S]*?)\];/)[1];
  for (const [, asset] of block.matchAll(/'\.\/(.*?)'/g)) {
    const local = asset || 'index.html';
    assert.ok(fs.existsSync(path.join(ROOT, local)), `missing ${local}`);
  }
  assert.match(sw, /e\.request\.mode === 'navigate'/);
  assert.match(sw, /caches\.match\('\.\/index\.html'\)/);
});

test('HTMLとモバイルUIに公開品質の基礎要件がある', () => {
  const html = read('index.html');
  const ids = [...html.matchAll(/\sid="([^"]+)"/g)].map(m => m[1]);
  assert.equal(new Set(ids).size, ids.length, 'duplicate id');
  assert.match(html, /apple-touch-icon/);
  assert.match(html, /<canvas[^>]+aria-label=/);
  assert.match(html, /meta name="description"/);
  assert.match(html, /style-v5\.css/);
  assert.match(html, /eldria-v5\.js/);

  const css = read('style.css');
  assert.match(css, /\.b-menu \{[^}]*width: 44px; height: 44px/s);
  assert.match(css, /orientation: landscape[^}]*max-height: 430px/s);
  assert.match(css, /prefers-reduced-motion: reduce/);
  assert.match(css, /\.bigbtn \{[^}]*min-height: 48px/s);

  const ui = read('js/ui.js');
  assert.match(ui, /I\.reset = function/);
  assert.match(ui, /el\('button'/);
  assert.match(ui, /aria-selected/);
  assert.match(ui, /classList\.add\('fatalmode'\)/);
  assert.match(css, /#ui\.fatalmode \{ z-index: 120; \}/);
});

test('中断・描画喪失・実行時例外を安全に処理する', () => {
  const main = read('js/main.js');
  assert.match(main, /visibilitychange/);
  assert.match(main, /pagehide/);
  assert.match(main, /webglcontextlost/);
  assert.match(main, /webglcontextrestored/);
  assert.match(main, /fatalStop\(error\)/);
  assert.match(main, /if \(running\) requestAnimationFrame\(loop\)/);
  assert.doesNotMatch(main, /function loop\(now\) \{\s*requestAnimationFrame\(loop\)/);
});

test('不変ファイル名の公開ランタイムが正規ソースと一致する', () => {
  const sourceFiles = ['js/core.js', 'js/audio.js', 'js/world.js', 'js/systems.js', 'js/entities.js', 'js/ui.js', 'js/main.js'];
  const expected = sourceFiles.map(file => `\n/* ===== ${file} ===== */\n${read(file)}`).join('');
  assert.equal(read('eldria-v5.js'), expected);
  assert.equal(read('style-v5.css'), read('style.css'));
  assert.deepEqual(JSON.parse(read('manifest-v5.json')), JSON.parse(read('manifest.json')));
});

test('モバイル完結機能が設定・保存・更新導線まで揃う', () => {
  const core = read('js/core.js');
  const systems = read('js/systems.js');
  const ui = read('js/ui.js');
  const main = read('js/main.js');
  const css = read('style.css');

  assert.match(core, /haptics: true/);
  assert.match(core, /shake: 0\.8/);
  assert.match(core, /G\.haptic = function/);
  assert.match(main, /v \* G\.settings\.shake/);
  assert.match(systems, /S\.summary = function/);
  assert.match(systems, /S\.exportData = function/);
  assert.match(systems, /S\.importData = function/);
  assert.match(ui, /beforeinstallprompt/);
  assert.match(ui, /UI\.showUpdatePrompt/);
  assert.match(ui, /セーブを書き出す/);
  assert.match(ui, /セーブを読み込む/);
  assert.match(css, /\.updatebar/);
  assert.match(css, /\.saveactions/);
});

test('CIはmainを書き換えず、古い作業ブランチを再公開しない', () => {
  const workflow = read('.github/workflows/pages.yml');
  assert.doesNotMatch(workflow, /schedule:/);
  assert.doesNotMatch(workflow, /contents:\s*write/);
  assert.doesNotMatch(workflow, /claude\/mobile-open-world/);
  assert.match(workflow, /npm test/);
  assert.match(workflow, /tools\/parsecheck\.sh/);
});
