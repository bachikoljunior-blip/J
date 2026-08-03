// ============================================================================
//  terrain.js — chunked terrain with three LOD levels, built lazily around the
//  camera and cached with distance-based eviction.
//
//  Chunk meshes are generated on a background-ish schedule (a small budget per
//  frame) so that walking into unexplored land never causes a hitch. Cracks
//  between differing LODs are hidden with skirts rather than stitched, which
//  costs a handful of triangles and removes an entire class of bugs.
// ============================================================================

import {
  WORLD_HALF, GRID, GRID_STEP, CHUNK_SIZE, CHUNKS, WATER_LEVEL,
  BIOME, BIOME_INFO,
} from '../world/worldgen.js';
import { clamp, lerp, saturate, smoothstep, sphereInFrustum } from '../core/math.js';
import { buildPlane, GpuMesh } from './mesh.js';

const FLOATS_PER_VERT = 15; // pos3 + normal3 + splat4 + tint3 + extra2

const LOD_STEPS = [4, 8, 16];   // world units between vertices

export class TerrainChunk {
  constructor(terrain, cx, cz, lod) {
    this.terrain = terrain;
    this.cx = cx;
    this.cz = cz;
    this.lod = lod;
    this.originX = cx * CHUNK_SIZE - WORLD_HALF;
    this.originZ = cz * CHUNK_SIZE - WORLD_HALF;
    this.built = false;
    this.vao = null;
    this.lastUsed = 0;
    this.minY = 0;
    this.maxY = 0;
  }

  build(glw) {
    const world = this.terrain.world;
    const step = LOD_STEPS[this.lod];
    const cells = CHUNK_SIZE / step;
    const n = cells + 1;
    // +1 ring of skirt vertices around the border.
    const vertCount = n * n + n * 4;
    const verts = new Float32Array(vertCount * FLOATS_PER_VERT);

    let minY = Infinity, maxY = -Infinity;
    let vi = 0;

    const writeVert = (lx, lz, skirtDrop) => {
      const wx = this.originX + lx;
      const wz = this.originZ + lz;
      const h = world.heightAt(wx, wz);
      const o = vi * FLOATS_PER_VERT;

      verts[o] = lx;
      verts[o + 1] = h - skirtDrop;
      verts[o + 2] = lz;

      const nrm = world.normalAt(wx, wz, _tmpNormal);
      verts[o + 3] = nrm.x; verts[o + 4] = nrm.y; verts[o + 5] = nrm.z;

      const slope = 1 - nrm.y;
      const biome = world.biomeAt(wx, wz);

      // --- splat weights ---------------------------------------------------
      let rock = smoothstep(saturate((slope - 0.22) / 0.42));
      if (biome === BIOME.CRAG) rock = Math.max(rock, 0.55);
      if (biome === BIOME.OCEAN) rock = Math.max(rock * 0.5, 0.1);

      let snow = 0;
      if (biome === BIOME.SNOW) snow = saturate((h - 96) / 34) * (1 - rock * 0.55) + 0.35;
      snow = saturate(snow * (1 - saturate((slope - 0.45) / 0.4)));

      let sand = 0;
      if (biome === BIOME.BEACH || biome === BIOME.OCEAN) {
        sand = saturate(1 - (h - WATER_LEVEL) / 3.2);
      }
      if (biome === BIOME.ASH) sand = Math.max(sand, 0.30);

      const ground = Math.max(0.02, 1 - rock * 0.85 - snow * 0.9 - sand * 0.8);
      verts[o + 6] = ground;
      verts[o + 7] = rock;
      verts[o + 8] = sand;
      verts[o + 9] = snow;

      // --- tint: 3x3 blur of biome ground colour ---------------------------
      let tr = 0, tg = 0, tb = 0, tw = 0;
      const gx = Math.round(world.worldToGrid(wx));
      const gz = Math.round(world.worldToGrid(wz));
      for (let dz = -1; dz <= 1; dz++) {
        for (let dx = -1; dx <= 1; dx++) {
          const b = world.biome[world.gridIndex(gx + dx * 2, gz + dz * 2)];
          const c = BIOME_INFO[b].ground;
          const w = (dx === 0 && dz === 0) ? 3 : 1;
          tr += c[0] * w; tg += c[1] * w; tb += c[2] * w; tw += w;
        }
      }
      // Moisture darkens and saturates the ground colour.
      const moist = world.moisture[world.gridIndex(gx, gz)];
      const mk = lerp(1.12, 0.82, moist);
      verts[o + 10] = (tr / tw) * mk;
      verts[o + 11] = (tg / tw) * lerp(1.06, 0.9, moist);
      verts[o + 12] = (tb / tw) * lerp(1.1, 0.86, moist);

      // --- ao + road -------------------------------------------------------
      // Compare against a wide neighbourhood: hollows darken, ridges brighten.
      const r = 14;
      const avg = (world.heightAt(wx - r, wz) + world.heightAt(wx + r, wz)
        + world.heightAt(wx, wz - r) + world.heightAt(wx, wz + r)) * 0.25;
      const rel = clamp((h - avg) / 12, -1, 1);
      verts[o + 13] = clamp(0.72 + rel * 0.30, 0.42, 1.05);
      verts[o + 14] = world.roadMask[world.gridIndex(gx, gz)];

      if (skirtDrop === 0) {
        if (h < minY) minY = h;
        if (h > maxY) maxY = h;
      }
      vi++;
    };

    for (let iz = 0; iz < n; iz++) {
      for (let ix = 0; ix < n; ix++) {
        writeVert(ix * step, iz * step, 0);
      }
    }

    const indices = [];
    for (let iz = 0; iz < cells; iz++) {
      for (let ix = 0; ix < cells; ix++) {
        const a = iz * n + ix;
        const b = a + 1;
        const c = a + n;
        const d = c + 1;
        // Alternate the diagonal to avoid a visible directional bias on slopes.
        if (((ix + iz) & 1) === 0) {
          indices.push(a, c, b, b, c, d);
        } else {
          indices.push(a, c, d, a, d, b);
        }
      }
    }

    // --- skirts: a ring of vertices dropped below the border ----------------
    const skirtBase = vi;
    const drop = step * 1.6 + 3;
    for (let i = 0; i < n; i++) writeVert(i * step, 0, drop);               // -Z
    for (let i = 0; i < n; i++) writeVert(i * step, cells * step, drop);    // +Z
    for (let i = 0; i < n; i++) writeVert(0, i * step, drop);               // -X
    for (let i = 0; i < n; i++) writeVert(cells * step, i * step, drop);    // +X

    const sZ0 = skirtBase, sZ1 = skirtBase + n, sX0 = skirtBase + n * 2, sX1 = skirtBase + n * 3;
    for (let i = 0; i < cells; i++) {
      const t0 = i, t1 = i + 1;
      indices.push(t0, sZ0 + i, t1, t1, sZ0 + i, sZ0 + i + 1);
      const u0 = (n - 1) * n + i, u1 = u0 + 1;
      indices.push(u0, u1, sZ1 + i, u1, sZ1 + i + 1, sZ1 + i);
      const l0 = i * n, l1 = l0 + n;
      indices.push(l0, l1, sX0 + i, l1, sX0 + i + 1, sX0 + i);
      const r0 = i * n + (n - 1), r1 = r0 + n;
      indices.push(r0, sX1 + i, r1, r1, sX1 + i, sX1 + i + 1);
    }

    const gl = glw.gl;
    this.vbo = glw.vbo(verts);
    const useUint = vertCount > 65535;
    this.ibo = glw.ibo(useUint && glw.uintIndices ? new Uint32Array(indices) : new Uint16Array(indices));
    this.indexType = (useUint && glw.uintIndices) ? gl.UNSIGNED_INT : gl.UNSIGNED_SHORT;
    this.indexCount = indices.length;
    this.minY = minY === Infinity ? 0 : minY;
    this.maxY = maxY === -Infinity ? 0 : maxY;
    this.centerX = this.originX + CHUNK_SIZE / 2;
    this.centerZ = this.originZ + CHUNK_SIZE / 2;
    this.centerY = (this.minY + this.maxY) / 2;
    this.radius = Math.hypot(CHUNK_SIZE * 0.72, (this.maxY - this.minY) / 2 + drop);
    this.built = true;
    this.triangleCount = this.indexCount / 3;
    return this;
  }

  bind(glw, prog, withAttribs = true) {
    const gl = glw.gl;
    const a = prog.attribs;
    const stride = FLOATS_PER_VERT * 4;
    gl.bindBuffer(gl.ARRAY_BUFFER, this.vbo);
    const set = (name, size, offset) => {
      const loc = a[name];
      if (loc === undefined || loc < 0) return;
      gl.enableVertexAttribArray(loc);
      gl.vertexAttribPointer(loc, size, gl.FLOAT, false, stride, offset * 4);
      glw.vertexAttribDivisorFn(loc, 0);
    };
    set('aPos', 3, 0);
    if (withAttribs) {
      set('aNormal', 3, 3);
      set('aSplat', 4, 6);
      set('aTint', 3, 10);
      set('aExtra', 2, 13);
    }
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, this.ibo);
  }

  dispose(glw) {
    const gl = glw.gl;
    if (this.vbo) gl.deleteBuffer(this.vbo);
    if (this.ibo) gl.deleteBuffer(this.ibo);
    this.built = false;
  }
}

const _tmpNormal = { x: 0, y: 1, z: 0 };

// ---------------------------------------------------------------------------

export class Terrain {
  constructor(glw, world) {
    this.glw = glw;
    this.world = world;
    this.chunks = new Map();          // key "cx,cz,lod"
    this.visible = [];
    this.buildQueue = [];
    this.frame = 0;
    this.chunkBudgetPerFrame = 2;

    this.waterMesh = new GpuMesh(glw, buildPlane(10));
    this.waterTiles = [];
    this._scanWaterTiles();
  }

  _scanWaterTiles() {
    // A chunk needs a water quad only if some of it sits below sea level.
    const w = this.world;
    for (let cz = 0; cz < CHUNKS; cz++) {
      for (let cx = 0; cx < CHUNKS; cx++) {
        const ox = cx * CHUNK_SIZE - WORLD_HALF;
        const oz = cz * CHUNK_SIZE - WORLD_HALF;
        let below = false;
        for (let s = 0; s <= 8 && !below; s++) {
          for (let t = 0; t <= 8 && !below; t++) {
            const h = w.heightAt(ox + (s / 8) * CHUNK_SIZE, oz + (t / 8) * CHUNK_SIZE);
            if (h < WATER_LEVEL + 0.3) below = true;
          }
        }
        if (below) this.waterTiles.push({ x: ox + CHUNK_SIZE / 2, z: oz + CHUNK_SIZE / 2 });
      }
    }
  }

  keyFor(cx, cz, lod) { return cx * 100000 + cz * 10 + lod; }

  lodFor(dist, viewDistance) {
    if (dist < viewDistance * 0.28) return 0;
    if (dist < viewDistance * 0.62) return 1;
    return 2;
  }

  /**
   * Decide which chunks should be resident this frame. Chunks are requested,
   * not built, here — building is rate-limited so a fast-moving player never
   * stalls the frame.
   */
  update(camX, camZ, viewDistance, frustum, cameraY) {
    this.frame++;
    this.visible.length = 0;
    this.buildQueue.length = 0;

    const range = Math.ceil(viewDistance / CHUNK_SIZE) + 1;
    const pcx = Math.floor((camX + WORLD_HALF) / CHUNK_SIZE);
    const pcz = Math.floor((camZ + WORLD_HALF) / CHUNK_SIZE);

    for (let dz = -range; dz <= range; dz++) {
      for (let dx = -range; dx <= range; dx++) {
        const cx = pcx + dx, cz = pcz + dz;
        if (cx < 0 || cz < 0 || cx >= CHUNKS || cz >= CHUNKS) continue;
        const centerX = cx * CHUNK_SIZE - WORLD_HALF + CHUNK_SIZE / 2;
        const centerZ = cz * CHUNK_SIZE - WORLD_HALF + CHUNK_SIZE / 2;
        const dist = Math.hypot(centerX - camX, centerZ - camZ);
        if (dist > viewDistance + CHUNK_SIZE) continue;

        const lod = this.lodFor(dist, viewDistance);
        const key = this.keyFor(cx, cz, lod);
        let chunk = this.chunks.get(key);
        if (!chunk) {
          chunk = new TerrainChunk(this, cx, cz, lod);
          this.chunks.set(key, chunk);
        }
        chunk.lastUsed = this.frame;

        if (!chunk.built) {
          this.buildQueue.push({ chunk, dist });
          // Fall back to a coarser LOD that is already resident so there is no
          // hole in the world while the finer mesh is being built.
          let fallback = null;
          for (let l = lod + 1; l < LOD_STEPS.length; l++) {
            const f = this.chunks.get(this.keyFor(cx, cz, l));
            if (f && f.built) { fallback = f; break; }
          }
          for (let l = lod - 1; l >= 0 && !fallback; l--) {
            const f = this.chunks.get(this.keyFor(cx, cz, l));
            if (f && f.built) { fallback = f; break; }
          }
          if (fallback) {
            fallback.lastUsed = this.frame;
            if (this._cull(fallback, frustum)) this.visible.push(fallback);
          }
          continue;
        }
        if (this._cull(chunk, frustum)) this.visible.push(chunk);
      }
    }

    // Build nearest-first, within budget.
    this.buildQueue.sort((a, b) => a.dist - b.dist);
    const budget = this.buildQueue.length > 24 ? this.chunkBudgetPerFrame + 2 : this.chunkBudgetPerFrame;
    for (let i = 0; i < Math.min(budget, this.buildQueue.length); i++) {
      const c = this.buildQueue[i].chunk;
      c.build(this.glw);
      if (this._cull(c, frustum)) this.visible.push(c);
    }

    this._evict();
    return this.visible;
  }

  _cull(chunk, frustum) {
    if (!frustum) return true;
    return sphereInFrustum(frustum, chunk.centerX, chunk.centerY, chunk.centerZ, chunk.radius);
  }

  _evict() {
    if (this.chunks.size < 220) return;
    const stale = [];
    for (const [key, c] of this.chunks) {
      if (this.frame - c.lastUsed > 240) stale.push(key);
    }
    for (const key of stale) {
      const c = this.chunks.get(key);
      c.dispose(this.glw);
      this.chunks.delete(key);
    }
  }

  /** Force-build every chunk near a point — used once at spawn so the first
   *  frame the player sees is complete rather than popping in. */
  primeAround(x, z, radius = 320) {
    const range = Math.ceil(radius / CHUNK_SIZE);
    const pcx = Math.floor((x + WORLD_HALF) / CHUNK_SIZE);
    const pcz = Math.floor((z + WORLD_HALF) / CHUNK_SIZE);
    let built = 0;
    for (let dz = -range; dz <= range; dz++) {
      for (let dx = -range; dx <= range; dx++) {
        const cx = pcx + dx, cz = pcz + dz;
        if (cx < 0 || cz < 0 || cx >= CHUNKS || cz >= CHUNKS) continue;
        const centerX = cx * CHUNK_SIZE - WORLD_HALF + CHUNK_SIZE / 2;
        const centerZ = cz * CHUNK_SIZE - WORLD_HALF + CHUNK_SIZE / 2;
        const dist = Math.hypot(centerX - x, centerZ - z);
        const lod = dist < radius * 0.5 ? 0 : 1;
        const key = this.keyFor(cx, cz, lod);
        if (this.chunks.has(key)) continue;
        const chunk = new TerrainChunk(this, cx, cz, lod);
        chunk.build(this.glw);
        chunk.lastUsed = this.frame;
        this.chunks.set(key, chunk);
        built++;
      }
    }
    return built;
  }

  draw(prog, shadowPass = false) {
    const glw = this.glw;
    const gl = glw.gl;
    for (const c of this.visible) {
      c.bind(glw, prog, !shadowPass);
      glw.u3f(prog, 'uChunkOffset', c.originX, 0, c.originZ);
      gl.drawElements(gl.TRIANGLES, c.indexCount, c.indexType, 0);
      glw.drawCalls++;
      glw.triangles += c.triangleCount;
    }
  }

  /** Water quads near the camera, drawn after opaque geometry. */
  drawWater(prog, camX, camZ, viewDistance) {
    const glw = this.glw;
    const gl = glw.gl;
    this.waterMesh.bindGeometry(prog);
    let drawn = 0;
    for (const t of this.waterTiles) {
      const d = Math.hypot(t.x - camX, t.z - camZ);
      if (d > viewDistance) continue;
      glw.u3f(prog, 'uOffset', t.x, WATER_LEVEL, t.z);
      gl.drawElements(gl.TRIANGLES, this.waterMesh.indexCount, this.waterMesh.indexType, 0);
      drawn++;
    }
    glw.drawCalls += drawn;
    glw.triangles += this.waterMesh.triangleCount * drawn;
  }

  get waterTileScale() { return CHUNK_SIZE; }
}
