// ============================================================================
//  png-stats.mjs — compute the presentation statistics from a PNG, using an
//  implementation that shares no code with the one being checked.
//
//  Falsification #3 in docs/FALSIFY.md was settled exactly this way: the audit
//  claimed a number, an independent decode of the same frames reproduced that
//  number over the *wrong half of the image*, and that proved the audit was
//  measuring the sky. The claim and its check must not share the code that could
//  be wrong, or the check confirms the bug.
//
//  So this decodes the PNG itself — zlib is in node, and PNG is a filtered
//  scanline format — and recomputes mean luma, contrast, saturation, Sobel
//  gradient, flat ratio, local RMS contrast and colour-bin occupancy with the
//  same definitions docs/QUALITY.md gives, in code written separately from
//  src/gfx/renderer.js.
//
//  It cannot use the depth-derived world mask, because a PNG has no depth. It
//  therefore reports every statistic twice: over the whole frame, and over the
//  rows below the horizon estimated from the image itself. Neither is the
//  audit's number. That is the point — where they disagree is where to look.
//
//    node tools/png-stats.mjs tools/shots/diag-day-meadow.png [...]
// ============================================================================

import { readFileSync } from 'node:fs';
import { inflateSync } from 'node:zlib';

/** Minimal PNG reader: 8-bit RGB/RGBA, non-interlaced. */
function decodePNG(buf) {
  if (buf.readUInt32BE(0) !== 0x89504e47) throw new Error('not a PNG');
  let pos = 8;
  let w = 0, h = 0, bitDepth = 0, colorType = 0, interlace = 0;
  const idat = [];
  while (pos < buf.length) {
    const len = buf.readUInt32BE(pos);
    const type = buf.toString('ascii', pos + 4, pos + 8);
    const data = buf.subarray(pos + 8, pos + 8 + len);
    if (type === 'IHDR') {
      w = data.readUInt32BE(0);
      h = data.readUInt32BE(4);
      bitDepth = data[8];
      colorType = data[9];
      interlace = data[12];
    } else if (type === 'IDAT') {
      idat.push(data);
    } else if (type === 'IEND') break;
    pos += 12 + len;
  }
  if (bitDepth !== 8) throw new Error(`bit depth ${bitDepth} unsupported`);
  if (interlace !== 0) throw new Error('interlaced PNG unsupported');
  const channels = colorType === 6 ? 4 : colorType === 2 ? 3 : 0;
  if (!channels) throw new Error(`colour type ${colorType} unsupported`);

  const raw = inflateSync(Buffer.concat(idat));
  const stride = w * channels;
  const out = new Uint8Array(w * h * 3);
  const prev = new Uint8Array(stride);
  const cur = new Uint8Array(stride);

  for (let y = 0; y < h; y++) {
    const filter = raw[y * (stride + 1)];
    const line = raw.subarray(y * (stride + 1) + 1, (y + 1) * (stride + 1));
    for (let i = 0; i < stride; i++) {
      const a = i >= channels ? cur[i - channels] : 0;   // left
      const b = prev[i];                                  // up
      const c = i >= channels ? prev[i - channels] : 0;   // up-left
      let v = line[i];
      switch (filter) {
        case 0: break;
        case 1: v = (v + a) & 255; break;
        case 2: v = (v + b) & 255; break;
        case 3: v = (v + ((a + b) >> 1)) & 255; break;
        case 4: {
          const p = a + b - c;
          const pa = Math.abs(p - a), pb = Math.abs(p - b), pc = Math.abs(p - c);
          v = (v + (pa <= pb && pa <= pc ? a : pb <= pc ? b : c)) & 255;
          break;
        }
        default: throw new Error(`filter ${filter}`);
      }
      cur[i] = v;
    }
    for (let x = 0; x < w; x++) {
      out[(y * w + x) * 3] = cur[x * channels];
      out[(y * w + x) * 3 + 1] = cur[x * channels + 1];
      out[(y * w + x) * 3 + 2] = cur[x * channels + 2];
    }
    prev.set(cur);
  }
  return { w, h, rgb: out };
}

/**
 * Statistics over the pixels `keep(x, y)` accepts. Definitions taken from
 * docs/QUALITY.md, implemented here rather than imported, deliberately.
 */
function stats({ w, h, rgb }, keep) {
  const lum = new Float32Array(w * h);
  for (let i = 0; i < w * h; i++) {
    lum[i] = (0.2126 * rgb[i * 3] + 0.7152 * rgb[i * 3 + 1] + 0.0722 * rgb[i * 3 + 2]) / 255;
  }

  let n = 0, sum = 0, sumSq = 0, sat = 0, clip = 0, crush = 0;
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      if (!keep(x, y)) continue;
      const i = y * w + x;
      const r = rgb[i * 3] / 255, g = rgb[i * 3 + 1] / 255, b = rgb[i * 3 + 2] / 255;
      const mx = Math.max(r, g, b), mn = Math.min(r, g, b);
      sum += lum[i]; sumSq += lum[i] * lum[i];
      sat += mx > 0.001 ? (mx - mn) / mx : 0;
      if (mx > 0.995) clip++;
      if (mx < 0.02) crush++;
      n++;
    }
  }
  if (!n) return null;
  const mean = sum / n;

  let gradSum = 0, gradN = 0, flat = 0;
  for (let y = 1; y < h - 1; y++) {
    for (let x = 1; x < w - 1; x++) {
      if (!keep(x, y)) continue;
      const i = y * w + x;
      const gx = (lum[i - w + 1] + 2 * lum[i + 1] + lum[i + w + 1])
        - (lum[i - w - 1] + 2 * lum[i - 1] + lum[i + w - 1]);
      const gy = (lum[i + w - 1] + 2 * lum[i + w] + lum[i + w + 1])
        - (lum[i - w - 1] + 2 * lum[i - w] + lum[i - w + 1]);
      const g = Math.sqrt(gx * gx + gy * gy);
      gradSum += g; gradN++;
      if (g < 0.012) flat++;
    }
  }

  let tileSum = 0, tiles = 0;
  for (let ty = 0; ty + 8 <= h; ty += 8) {
    for (let tx = 0; tx + 8 <= w; tx += 8) {
      let kept = 0;
      for (let y = 0; y < 8; y += 2) for (let x = 0; x < 8; x += 2) if (keep(tx + x, ty + y)) kept++;
      if (kept < 10) continue;
      let s = 0, s2 = 0;
      for (let y = 0; y < 8; y++) {
        for (let x = 0; x < 8; x++) { const v = lum[(ty + y) * w + tx + x]; s += v; s2 += v * v; }
      }
      const m = s / 64;
      tileSum += Math.sqrt(Math.max(0, s2 / 64 - m * m));
      tiles++;
    }
  }

  const bins = new Uint8Array(12 * 8 * 8);
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      if (!keep(x, y)) continue;
      const i = y * w + x;
      const r = rgb[i * 3] / 255, g = rgb[i * 3 + 1] / 255, b = rgb[i * 3 + 2] / 255;
      const mx = Math.max(r, g, b), mn = Math.min(r, g, b), d = mx - mn;
      let hue = 0;
      if (d > 1e-6) {
        if (mx === r) hue = ((g - b) / d + 6) % 6;
        else if (mx === g) hue = (b - r) / d + 2;
        else hue = (r - g) / d + 4;
        hue /= 6;
      }
      const hi = Math.min(11, Math.floor(hue * 12));
      const si = Math.min(7, Math.floor((mx > 0 ? d / mx : 0) * 8));
      const vi = Math.min(7, Math.floor(mx * 8));
      bins[(hi * 8 + si) * 8 + vi] = 1;
    }
  }

  return {
    pixels: n,
    luma: mean,
    contrast: Math.sqrt(Math.max(0, sumSq / n - mean * mean)),
    saturation: sat / n,
    clip: clip / n,
    crush: crush / n,
    detail: gradN ? gradSum / gradN : 0,
    gradN,
    flatRatio: gradN ? flat / gradN : 1,
    localContrast: tiles ? tileSum / tiles : 0,
    colorBins: bins.reduce((a, v) => a + v, 0),
  };
}

/**
 * Estimate the horizon as the highest row from which every row below has more
 * gradient than the rows above. Crude on purpose — it is a cross-check on the
 * depth mask, not a replacement for it.
 */
function horizonRow({ w, h, rgb }) {
  const rowGrad = new Float64Array(h);
  for (let y = 1; y < h - 1; y++) {
    let s = 0;
    for (let x = 1; x < w - 1; x++) {
      const a = (y * w + x) * 3, b = (y * w + x - 1) * 3, c = ((y - 1) * w + x) * 3;
      s += Math.abs(rgb[a] - rgb[b]) + Math.abs(rgb[a] - rgb[c]);
    }
    rowGrad[y] = s / w;
  }
  const all = [...rowGrad].sort((p, q) => p - q);
  const mid = all[Math.floor(all.length / 2)];
  for (let y = 0; y < h; y++) if (rowGrad[y] > mid * 1.6) return y;
  return Math.floor(h * 0.5);
}

const files = process.argv.slice(2);
if (!files.length) {
  console.log('使い方: node tools/png-stats.mjs <png> [<png>...]');
  process.exit(2);
}

for (const f of files) {
  let img;
  try {
    img = decodePNG(readFileSync(f));
  } catch (e) {
    console.log(`${f}: 読めない — ${e.message}`);
    continue;
  }
  const hz = horizonRow(img);
  const whole = stats(img, () => true);
  const below = stats(img, (x, y) => y >= hz);
  const name = f.split('/').pop();
  console.log(`\n${name}  ${img.w}x${img.h}  推定地平線 y=${hz} (上から ${(hz / img.h * 100).toFixed(0)}%)`);
  const row = (label, s) => {
    if (!s) { console.log(`  ${label}: 対象画素なし`); return; }
    console.log(`  ${label.padEnd(6)} luma=${s.luma.toFixed(3)} contrast=${s.contrast.toFixed(3)} ` +
      `sat=${s.saturation.toFixed(3)} clip=${(s.clip * 100).toFixed(1)}% crush=${(s.crush * 100).toFixed(1)}%`);
    console.log(`  ${''.padEnd(6)} detail=${s.detail.toFixed(4)} flat=${(s.flatRatio * 100).toFixed(1)}% ` +
      `localC=${s.localContrast.toFixed(4)} bins=${s.colorBins} (${s.pixels}px)`);
  };
  row('全画面', whole);
  row('地平線下', below);
}
