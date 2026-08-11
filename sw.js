// Offline cache. The whole game is a handful of source files, so a simple
// cache-first strategy with a versioned bucket is enough — bump CACHE on
// release and the old bucket is dropped on activate.
const CACHE = 'kurogane-v4-quality-reforged';

const ASSETS = [
  './',
  './index.html',
  './style.css',
  './manifest.json',
  './icon.svg',
  './icon-180.png',
  './icon-192.png',
  './icon-512.png',
  './src/main.js',
  './src/core/math.js',
  './src/core/rng.js',
  './src/core/input.js',
  './src/core/audio.js',
  './src/core/save.js',
  './src/gfx/gl.js',
  './src/gfx/shaders.js',
  './src/gfx/mesh.js',
  './src/gfx/instancing.js',
  './src/gfx/terrain.js',
  './src/gfx/particles.js',
  './src/gfx/renderer.js',
  './src/world/worldgen.js',
  './src/world/foliage.js',
  './src/world/structures.js',
  './src/game/rig.js',
  './src/game/anim.js',
  './src/game/actor.js',
  './src/game/combat.js',
  './src/game/items.js',
  './src/game/player.js',
  './src/game/ai.js',
  './src/game/enemies.js',
  './src/game/bosses.js',
  './src/game/quests.js',
  './src/game/game.js',
  './src/ui/ui.js',
];

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE)
      .then((c) => c.addAll(ASSETS))
      // Only activate a complete offline build. If any asset is unavailable,
      // rejecting install keeps the previous known-good worker and cache.
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (e) => {
  if (e.request.method !== 'GET') return;
  if (e.request.mode === 'navigate') {
    e.respondWith(
      fetch(e.request).then((res) => {
        if (res && res.status === 200) {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put('./index.html', copy));
        }
        return res;
      }).catch(() => caches.match('./index.html'))
    );
    return;
  }
  e.respondWith(
    caches.match(e.request).then((hit) => hit || fetch(e.request).then((res) => {
      if (res && res.status === 200 && res.type === 'basic') {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(e.request, copy));
      }
      return res;
    }))
  );
});
