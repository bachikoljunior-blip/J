// ============================================================================
//  shaders.js — all GLSL for the engine, written against GLSL ES 1.00 so the
//  same source links on WebGL1 and WebGL2.
//
//  The lighting model shared by every opaque surface:
//    * one directional light (sun or moon) with a wrapped-Lambert term,
//    * hemispheric ambient blending sky colour into ground bounce,
//    * a rim term that catches the sky behind silhouettes,
//    * scrolling cloud shadows sampled from a noise texture in world space,
//    * height-attenuated exponential fog tinted toward the sun (a cheap stand-in
//      for aerial perspective, which is what actually sells long sightlines).
// ============================================================================

// ---------------------------------------------------------------------------
//  Shared chunks
// ---------------------------------------------------------------------------

const COMMON_UNIFORMS = `
uniform vec3 uSunDir;        // points *toward* the sun
uniform vec3 uSunColor;
uniform vec3 uSkyColor;
uniform vec3 uGroundColor;
uniform vec3 uFogColor;
uniform vec3 uFogSunColor;
uniform vec2 uFogParams;     // x = density, y = height falloff
uniform vec3 uCameraPos;
uniform float uTime;
uniform sampler2D uCloudTex;
uniform vec4 uCloudParams;   // xy = wind offset, z = scale, w = strength
uniform vec4 uPointLights[4];  // xyz = world position, w = radius (0 = off)
uniform vec3 uPointColors[4];
`;

const LIGHTING_FUNCS = `
float cloudShadow(vec3 worldPos) {
  vec2 uv = worldPos.xz * uCloudParams.z + uCloudParams.xy;
  float c = texture2D(uCloudTex, uv).r;
  float s = smoothstep(0.42, 0.72, c);
  return mix(1.0, 1.0 - uCloudParams.w, s);
}

vec3 applyLighting(vec3 albedo, vec3 N, vec3 worldPos, float shadow, float ao, float rimAmt) {
  vec3 V = normalize(uCameraPos - worldPos);
  float ndl = dot(N, uSunDir);
  // Wrapped diffuse keeps terminators soft, which suits the stylised look and
  // hides the low polygon count on characters.
  float wrapped = max(0.0, (ndl + 0.35) / 1.35);
  vec3 direct = uSunColor * wrapped * shadow;

  // Hemispheric ambient.
  float hemi = N.y * 0.5 + 0.5;
  vec3 ambient = mix(uGroundColor, uSkyColor, hemi) * ao;

  // Cheap specular-ish sheen from the sun.
  vec3 H = normalize(uSunDir + V);
  float spec = pow(max(dot(N, H), 0.0), 24.0) * 0.16 * shadow * max(ndl, 0.0);

  // Rim: sky light wrapping around the silhouette.
  float rim = pow(1.0 - max(dot(N, V), 0.0), 3.0) * rimAmt;

  // Point lights: campfires, braziers, graces. Four is enough because we
  // upload only the nearest four to the camera each frame.
  vec3 point = vec3(0.0);
  for (int i = 0; i < 4; i++) {
    float radius = uPointLights[i].w;
    if (radius <= 0.0) continue;
    vec3 toL = uPointLights[i].xyz - worldPos;
    float dist = length(toL);
    if (dist > radius) continue;
    vec3 L = toL / max(dist, 0.001);
    // Smooth inverse-square-ish falloff clipped to the radius.
    float atten = clamp(1.0 - dist / radius, 0.0, 1.0);
    atten *= atten;
    float ndl = max(dot(N, L), 0.0) * 0.75 + 0.25;
    point += uPointColors[i] * ndl * atten;
  }

  vec3 lit = albedo * (direct + ambient + point) + uSunColor * spec + uSkyColor * rim * 0.6;
  return lit;
}

vec3 applyFog(vec3 color, vec3 worldPos) {
  vec3 toCam = worldPos - uCameraPos;
  float dist = length(toCam);
  // Height-attenuated integral of an exponentially decaying medium.
  float h = uFogParams.y;
  float camH = max(uCameraPos.y, -50.0);
  float fragH = max(worldPos.y, -50.0);
  float dy = fragH - camH;
  float density;
  if (abs(dy) < 0.01) {
    density = uFogParams.x * dist * exp(-camH * h);
  } else {
    density = uFogParams.x * dist * (exp(-camH * h) - exp(-fragH * h)) / (dy * h);
  }
  float f = 1.0 - exp(-max(density, 0.0));
  vec3 dir = dist > 0.001 ? toCam / dist : vec3(0.0, 0.0, 1.0);
  float sunAmount = max(dot(dir, uSunDir), 0.0);
  vec3 fogCol = mix(uFogColor, uFogSunColor, pow(sunAmount, 6.0));
  return mix(color, fogCol, clamp(f, 0.0, 1.0));
}
`;

const SHADOW_FUNCS = `
uniform sampler2D uShadowMap;
uniform mat4 uLightMatrix;
uniform vec2 uShadowParams;  // x = texel size, y = strength

#ifdef SHADOW_PACKED
float unpackDepth(vec4 c) {
  return dot(c, vec4(1.0, 1.0 / 255.0, 1.0 / 65025.0, 1.0 / 16581375.0));
}
#endif

float sampleShadowTexel(vec2 uv, float ref) {
#ifdef SHADOW_PACKED
  float d = unpackDepth(texture2D(uShadowMap, uv));
#else
  float d = texture2D(uShadowMap, uv).r;
#endif
  return ref > d ? 0.0 : 1.0;
}

float shadowFactor(vec3 worldPos, vec3 N) {
  // Normal offset removes most acne without the peter-panning of a big constant bias.
  vec3 offsetPos = worldPos + N * 0.14;
  vec4 lp = uLightMatrix * vec4(offsetPos, 1.0);
  vec3 proj = lp.xyz / lp.w;
  proj = proj * 0.5 + 0.5;
  if (proj.x < 0.002 || proj.x > 0.998 || proj.y < 0.002 || proj.y > 0.998 || proj.z > 1.0) return 1.0;

  float ref = proj.z - 0.0016;
  float t = uShadowParams.x;
  // 5-tap cross PCF: visibly softer than 1 tap, meaningfully cheaper than 3x3.
  float s = sampleShadowTexel(proj.xy, ref);
  s += sampleShadowTexel(proj.xy + vec2(t, 0.0), ref);
  s += sampleShadowTexel(proj.xy + vec2(-t, 0.0), ref);
  s += sampleShadowTexel(proj.xy + vec2(0.0, t), ref);
  s += sampleShadowTexel(proj.xy + vec2(0.0, -t), ref);
  s *= 0.2;

  // Fade the shadow out at the edge of the map so the boundary is invisible.
  vec2 fadeUV = abs(proj.xy - 0.5) * 2.0;
  float edge = 1.0 - smoothstep(0.75, 0.99, max(fadeUV.x, fadeUV.y));
  s = mix(1.0, s, edge);
  return mix(1.0, s, uShadowParams.y);
}
`;

const HASH_NOISE = `
float hash12(vec2 p) {
  vec3 p3 = fract(vec3(p.xyx) * 0.1031);
  p3 += dot(p3, p3.yzx + 33.33);
  return fract((p3.x + p3.y) * p3.z);
}
float vnoise(vec2 p) {
  vec2 i = floor(p), f = fract(p);
  f = f * f * (3.0 - 2.0 * f);
  float a = hash12(i);
  float b = hash12(i + vec2(1.0, 0.0));
  float c = hash12(i + vec2(0.0, 1.0));
  float d = hash12(i + vec2(1.0, 1.0));
  return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
}
`;

// ---------------------------------------------------------------------------
//  Terrain
// ---------------------------------------------------------------------------

export const TERRAIN_VS = `
precision highp float;
attribute vec3 aPos;
attribute vec3 aNormal;
attribute vec4 aSplat;      // r=ground g=rock b=sand/dirt a=snow
attribute vec3 aTint;       // per-vertex biome ground colour
attribute vec2 aExtra;      // x = ambient occlusion, y = road amount

uniform mat4 uViewProj;
uniform vec3 uChunkOffset;

varying vec3 vWorld;
varying vec3 vNormal;
varying vec4 vSplat;
varying vec3 vTint;
varying vec2 vExtra;

void main() {
  vec3 world = aPos + uChunkOffset;
  vWorld = world;
  vNormal = aNormal;
  vSplat = aSplat;
  vTint = aTint;
  vExtra = aExtra;
  gl_Position = uViewProj * vec4(world, 1.0);
}
`;

export const TERRAIN_FS = `
precision highp float;
${COMMON_UNIFORMS}
${SHADOW_FUNCS}
${HASH_NOISE}
${LIGHTING_FUNCS}

uniform vec3 uRockColor;
uniform vec3 uSandColor;
uniform vec3 uSnowColor;
uniform vec3 uRoadColor;
uniform float uWetness;

varying vec3 vWorld;
varying vec3 vNormal;
varying vec4 vSplat;
varying vec3 vTint;
varying vec2 vExtra;

void main() {
  vec3 N = normalize(vNormal);

  // Two scales of noise break up the flat vertex colours; this is the single
  // biggest readability win on large terrain at almost no cost.
  float n1 = vnoise(vWorld.xz * 0.11);
  float n2 = vnoise(vWorld.xz * 0.9);
  float n3 = vnoise(vWorld.xz * 3.7);

  // The biome tint arrives per vertex, so a chunk spanning meadow and forest
  // blends across the seam instead of switching abruptly.
  vec3 ground = vTint * (0.80 + 0.42 * (n1 * 0.65 + n2 * 0.35));
  ground *= 0.93 + 0.14 * n3;

  vec3 rock = uRockColor * (0.72 + 0.44 * vnoise(vWorld.xz * 0.55 + vWorld.y * 0.35));
  // Strata: horizontal banding by world height reads as sedimentary rock.
  rock *= 0.88 + 0.22 * sin(vWorld.y * 1.35 + n1 * 3.0);
  vec3 sand = uSandColor * (0.88 + 0.24 * n2);
  vec3 snow = uSnowColor * (0.94 + 0.12 * n1);

  vec4 w = vSplat;
  float total = max(w.r + w.g + w.b + w.a, 0.0001);
  w /= total;
  vec3 albedo = ground * w.r + rock * w.g + sand * w.b + snow * w.a;

  // Roads: packed dirt with wheel-rut noise. The blend starts late so the
  // path has soft, trodden-looking edges instead of a painted stripe.
  float road = vExtra.y;
  vec3 roadCol = uRoadColor * (0.85 + 0.3 * n2) * (0.94 + 0.1 * n3);
  albedo = mix(albedo, roadCol, smoothstep(0.40, 0.92, road) * 0.88);

  // Wet ground darkens and tightens; used during rain.
  float wet = clamp(uWetness * (0.35 + 0.65 * (w.r + road)), 0.0, 1.0);
  albedo = mix(albedo, albedo * 0.6, wet);

  float shadow = shadowFactor(vWorld, N) * cloudShadow(vWorld);
  float ao = vExtra.x;
  vec3 color = applyLighting(albedo, N, vWorld, shadow, ao, 0.16 + wet * 0.55);
  color = applyFog(color, vWorld);
  gl_FragColor = vec4(color, 1.0);
}
`;

// ---------------------------------------------------------------------------
//  Instanced geometry (characters, props, trees, rocks, structures)
//
//  Instance layout: 3 vec4 rows of a 4x3 affine transform + colour + params.
//  Storing 4x3 instead of 4x4 saves an attribute slot, which matters because
//  WebGL1 guarantees only 16.
// ---------------------------------------------------------------------------

export const INSTANCE_VS = `
precision highp float;
attribute vec3 aPos;
attribute vec3 aNormal;
attribute float aBlend; // 0 = primary colour, 1 = secondary

attribute vec4 aRow0;   // xyz = matrix col 0, w = translate.x
attribute vec4 aRow1;   // xyz = matrix col 1, w = translate.y
attribute vec4 aRow2;   // xyz = matrix col 2, w = translate.z
attribute vec4 aColor;  // rgb = tint, a = emissive amount
attribute vec4 aColor2; // secondary tint (bark vs leaves, wall vs roof)
attribute vec4 aParams; // x = sway amount, y = phase, z = ao, w = alpha

uniform mat4 uViewProj;
uniform float uTime;
uniform vec2 uWind;     // xz wind vector

varying vec3 vWorld;
varying vec3 vNormal;
varying vec4 vColor;
varying vec4 vParams;

void main() {
  mat3 rot = mat3(aRow0.xyz, aRow1.xyz, aRow2.xyz);
  vec3 local = aPos;

  // Vertex sway for foliage: displacement grows with local height so trunks
  // stay planted while canopies move.
  float sway = aParams.x;
  if (sway > 0.0) {
    float h = max(local.y, 0.0);
    float t = uTime * 1.3 + aParams.y;
    float amp = sway * h * h * 0.045;
    local.x += sin(t) * amp * (1.0 + uWind.x);
    local.z += cos(t * 0.83 + 1.7) * amp * (1.0 + uWind.y);
  }

  vec3 world = rot * local + vec3(aRow0.w, aRow1.w, aRow2.w);
  vWorld = world;
  // Non-uniform scale is common here (boxes stretched into limbs), so the
  // normal needs the inverse-transpose rather than the rotation alone.
  vec3 invScale = vec3(
    1.0 / max(dot(aRow0.xyz, aRow0.xyz), 1e-6),
    1.0 / max(dot(aRow1.xyz, aRow1.xyz), 1e-6),
    1.0 / max(dot(aRow2.xyz, aRow2.xyz), 1e-6));
  vNormal = normalize(rot * (aNormal * invScale));
  vColor = mix(aColor, aColor2, clamp(aBlend, 0.0, 1.0));
  vParams = aParams;
  gl_Position = uViewProj * vec4(world, 1.0);
}
`;

export const INSTANCE_FS = `
precision highp float;
${COMMON_UNIFORMS}
${SHADOW_FUNCS}
${HASH_NOISE}
${LIGHTING_FUNCS}

varying vec3 vWorld;
varying vec3 vNormal;
varying vec4 vColor;
varying vec4 vParams;

void main() {
  if (vParams.w < 0.02) discard;
  vec3 N = normalize(vNormal);
  vec3 albedo = vColor.rgb;

  // Subtle per-surface grain so large flat faces do not read as plastic.
  float grain = vnoise(vWorld.xz * 3.1 + vWorld.y * 2.3);
  albedo *= 0.94 + 0.12 * grain;

  float shadow = shadowFactor(vWorld, N) * cloudShadow(vWorld);
  vec3 color = applyLighting(albedo, N, vWorld, shadow, vParams.z, 0.16);
  color += vColor.rgb * vColor.a * 2.2;   // emissive
  color = applyFog(color, vWorld);
  gl_FragColor = vec4(color, vParams.w);
}
`;

// ---------------------------------------------------------------------------
//  Grass — instanced blades, heavily wind-driven, distance-faded
// ---------------------------------------------------------------------------

export const GRASS_VS = `
precision highp float;
attribute vec3 aPos;       // unit blade: x in [-0.5,0.5], y in [0,1]
attribute vec3 aNormal;
attribute vec4 aRow0;
attribute vec4 aRow1;
attribute vec4 aRow2;
attribute vec4 aColor;
attribute vec4 aParams;

uniform mat4 uViewProj;
uniform vec3 uCameraPos;
uniform float uTime;
uniform vec2 uWind;
uniform vec2 uFadeRange;   // x = start fade, y = fully gone
uniform vec3 uTrample;     // xz = trampler position, z unused
uniform float uTrampleRadius;

varying vec3 vWorld;
varying vec3 vNormal;
varying vec4 vColor;
varying float vFade;
varying float vHeight;

void main() {
  mat3 rot = mat3(aRow0.xyz, aRow1.xyz, aRow2.xyz);
  vec3 base = vec3(aRow0.w, aRow1.w, aRow2.w);
  vec3 local = aPos;
  float h = local.y;
  vHeight = h;

  float t = uTime * 1.9 + aParams.y;
  float gust = sin(uTime * 0.4 + base.x * 0.02 + base.z * 0.017) * 0.5 + 0.5;
  float bend = (0.16 + 0.5 * gust) * h * h;
  local.x += (sin(t) * 0.35 + uWind.x) * bend;
  local.z += (cos(t * 0.77) * 0.35 + uWind.y) * bend;

  vec3 world = rot * local + base;

  // Push blades away from anything walking through them.
  vec2 d = world.xz - uTrample.xz;
  float dist = length(d);
  if (dist < uTrampleRadius) {
    float push = (1.0 - dist / uTrampleRadius) * h;
    world.xz += normalize(d + vec2(0.0001)) * push * 0.55;
    world.y -= push * 0.35;
  }

  vWorld = world;
  vNormal = normalize(rot * aNormal);
  vColor = aColor;

  float camDist = distance(world, uCameraPos);
  vFade = 1.0 - smoothstep(uFadeRange.x, uFadeRange.y, camDist);
  // Collapse blades into the ground as they fade so popping is invisible.
  world.y -= (1.0 - vFade) * h * aParams.x;
  gl_Position = uViewProj * vec4(world, 1.0);
}
`;

export const GRASS_FS = `
precision highp float;
${COMMON_UNIFORMS}
${SHADOW_FUNCS}
${HASH_NOISE}
${LIGHTING_FUNCS}

varying vec3 vWorld;
varying vec3 vNormal;
varying vec4 vColor;
varying float vFade;
varying float vHeight;

void main() {
  if (vFade < 0.02) discard;
  vec3 N = normalize(vNormal);
  // Blades are double-sided; flip toward the viewer.
  vec3 V = normalize(uCameraPos - vWorld);
  if (dot(N, V) < 0.0) N = -N;

  // Darker at the base, brighter and yellower at the tip: classic grass AO.
  vec3 albedo = vColor.rgb * (0.5 + 0.7 * vHeight);
  float shadow = shadowFactor(vWorld, N) * cloudShadow(vWorld);
  float ao = 0.45 + 0.55 * vHeight;

  // Translucency — sunlight bleeding through the blade from behind.
  float back = max(0.0, dot(-N, uSunDir));
  vec3 trans = uSunColor * pow(back, 2.0) * 0.5 * vColor.rgb * vHeight;

  vec3 color = applyLighting(albedo, N, vWorld, shadow, ao, 0.1) + trans;
  color = applyFog(color, vWorld);
  gl_FragColor = vec4(color, 1.0);
}
`;

// ---------------------------------------------------------------------------
//  Shadow pass — depth only, shared by terrain and instanced geometry
// ---------------------------------------------------------------------------

export const SHADOW_INSTANCE_VS = `
precision highp float;
attribute vec3 aPos;
attribute vec4 aRow0;
attribute vec4 aRow1;
attribute vec4 aRow2;
attribute vec4 aParams;
uniform mat4 uLightMatrix;
uniform float uTime;
varying float vDepth;
void main() {
  mat3 rot = mat3(aRow0.xyz, aRow1.xyz, aRow2.xyz);
  vec3 local = aPos;
  float sway = aParams.x;
  if (sway > 0.0) {
    float h = max(local.y, 0.0);
    float t = uTime * 1.3 + aParams.y;
    float amp = sway * h * h * 0.045;
    local.x += sin(t) * amp;
    local.z += cos(t * 0.83 + 1.7) * amp;
  }
  vec3 world = rot * local + vec3(aRow0.w, aRow1.w, aRow2.w);
  gl_Position = uLightMatrix * vec4(world, 1.0);
  vDepth = gl_Position.z / gl_Position.w * 0.5 + 0.5;
}
`;

export const SHADOW_TERRAIN_VS = `
precision highp float;
attribute vec3 aPos;
uniform mat4 uLightMatrix;
uniform vec3 uChunkOffset;
varying float vDepth;
void main() {
  gl_Position = uLightMatrix * vec4(aPos + uChunkOffset, 1.0);
  vDepth = gl_Position.z / gl_Position.w * 0.5 + 0.5;
}
`;

export const SHADOW_FS = `
precision highp float;
varying float vDepth;
#ifdef SHADOW_PACKED
vec4 packDepth(float v) {
  vec4 enc = vec4(1.0, 255.0, 65025.0, 16581375.0) * v;
  enc = fract(enc);
  enc -= enc.yzww * vec4(1.0 / 255.0, 1.0 / 255.0, 1.0 / 255.0, 0.0);
  return enc;
}
#endif
void main() {
#ifdef SHADOW_PACKED
  gl_FragColor = packDepth(clamp(vDepth, 0.0, 1.0));
#else
  gl_FragColor = vec4(1.0);
#endif
}
`;

// ---------------------------------------------------------------------------
//  Sky — full-screen dome drawn at the far plane
// ---------------------------------------------------------------------------

export const SKY_VS = `
precision highp float;
attribute vec2 aPos;
uniform mat4 uInvViewProj;
varying vec3 vRay;
void main() {
  vec4 near = uInvViewProj * vec4(aPos, -1.0, 1.0);
  vec4 far = uInvViewProj * vec4(aPos, 1.0, 1.0);
  vRay = far.xyz / far.w - near.xyz / near.w;
  gl_Position = vec4(aPos, 0.999999, 1.0);
}
`;

export const SKY_FS = `
precision highp float;
${HASH_NOISE}
uniform vec3 uSunDir;
uniform vec3 uMoonDir;
uniform vec3 uSunColor;
uniform vec3 uSkyTop;
uniform vec3 uSkyHorizon;
uniform vec3 uGroundColor;
uniform float uTime;
uniform float uNight;        // 0 = day, 1 = night
uniform float uCloudCover;
uniform float uCloudSpeed;
uniform vec2 uCloudWind;
varying vec3 vRay;

float fbm2(vec2 p) {
  float s = 0.0, a = 0.5;
  for (int i = 0; i < 5; i++) {
    s += a * vnoise(p);
    p *= 2.03;
    a *= 0.5;
  }
  return s;
}

void main() {
  vec3 dir = normalize(vRay);
  float up = dir.y;

  // Base gradient with a compressed horizon band.
  float t = pow(clamp(up * 0.5 + 0.5, 0.0, 1.0), 0.55);
  vec3 sky = mix(uSkyHorizon, uSkyTop, smoothstep(0.35, 0.95, t));

  // Below the horizon fades into a ground haze rather than hard-cutting.
  sky = mix(uGroundColor * 0.7, sky, smoothstep(-0.12, 0.06, up));

  // Sun disc + halo.
  float sunDot = max(dot(dir, uSunDir), 0.0);
  float disc = smoothstep(0.9985, 0.9995, sunDot);
  float halo = pow(sunDot, 220.0) * 0.7 + pow(sunDot, 12.0) * 0.30 + pow(sunDot, 3.0) * 0.10;
  sky += uSunColor * halo * (1.0 - uNight * 0.85);
  sky += uSunColor * disc * 12.0 * (1.0 - uNight);

  // Moon.
  float moonDot = max(dot(dir, uMoonDir), 0.0);
  float moonDisc = smoothstep(0.9990, 0.9997, moonDot);
  sky += vec3(0.85, 0.90, 1.0) * moonDisc * 6.0 * uNight;
  sky += vec3(0.35, 0.45, 0.7) * pow(moonDot, 60.0) * 0.5 * uNight;

  // Stars: one jittered point per lattice cell, drawn as a round dot rather
  // than a lit cell — otherwise the night sky is a grid of squares.
  if (uNight > 0.02 && up > 0.0) {
    vec2 sp = dir.xz / max(abs(dir.y) + 0.14, 0.05) * 110.0;
    vec2 cell = floor(sp);
    vec2 f = fract(sp);
    float h = hash12(cell);
    if (h > 0.955) {
      vec2 pos = vec2(hash12(cell + 1.37), hash12(cell + 7.71));
      float d = length(f - pos);
      float mag = (h - 0.955) / 0.045;              // 0..1 brightness class
      float radius = mix(0.045, 0.10, mag);
      float dot = smoothstep(radius, 0.0, d);
      float twinkle = 0.6 + 0.4 * sin(uTime * 2.2 + h * 120.0);
      vec3 tint = mix(vec3(0.75, 0.82, 1.0), vec3(1.0, 0.94, 0.84), hash12(cell + 3.3));
      sky += tint * dot * (0.35 + mag * 1.5) * twinkle * uNight * smoothstep(0.0, 0.25, up);
    }
  }

  // Clouds: project the ray onto a plane above the camera and layer fbm.
  if (up > 0.008) {
    vec2 cp = dir.xz / max(up, 0.02) * 0.048 + uCloudWind * uCloudSpeed;
    float d1 = fbm2(cp);
    float d2 = fbm2(cp * 2.4 + vec2(11.3, 4.7));
    float density = d1 * 0.72 + d2 * 0.28;
    // Calibrated against fbm2's ~0.48 mean: at cover 0 the sky keeps a few
    // scattered banks rather than being surgically clear.
    float cover = mix(0.60, 0.24, uCloudCover);
    float cloud = smoothstep(cover, cover + 0.20, density);
    cloud *= smoothstep(0.008, 0.11, up);

    // Light the cloud from the sun side using the density gradient.
    float lit = smoothstep(cover - 0.08, cover + 0.30, density);
    vec3 cloudLit = mix(vec3(0.42, 0.45, 0.55), vec3(1.05, 1.0, 0.95), lit);
    cloudLit *= mix(vec3(0.28, 0.32, 0.45), uSunColor * 1.1, 1.0 - uNight);
    float edgeGlow = pow(max(dot(dir, uSunDir), 0.0), 8.0) * (1.0 - lit) * 0.8;
    cloudLit += uSunColor * edgeGlow * (1.0 - uNight);
    sky = mix(sky, cloudLit, cloud * 0.94);
  }

  gl_FragColor = vec4(sky, 1.0);
}
`;

// ---------------------------------------------------------------------------
//  Water
// ---------------------------------------------------------------------------

export const WATER_VS = `
precision highp float;
attribute vec3 aPos;
uniform mat4 uViewProj;
uniform vec3 uOffset;
uniform float uTileScale;
uniform float uTime;
varying vec3 vWorld;
varying float vWave;
void main() {
  vec3 world = vec3(aPos.x * uTileScale, aPos.y, aPos.z * uTileScale) + uOffset;
  // Two crossing gerstner-ish waves; enough motion to read as a surface.
  float w1 = sin(world.x * 0.13 + uTime * 1.1) * 0.16;
  float w2 = sin(world.z * 0.19 - uTime * 0.83) * 0.13;
  float w3 = sin((world.x + world.z) * 0.07 + uTime * 0.5) * 0.10;
  world.y += w1 + w2 + w3;
  vWave = w1 + w2 + w3;
  vWorld = world;
  gl_Position = uViewProj * vec4(world, 1.0);
}
`;

export const WATER_FS = `
precision highp float;
${COMMON_UNIFORMS}
${HASH_NOISE}
${LIGHTING_FUNCS}
uniform vec3 uWaterShallow;
uniform vec3 uWaterDeep;
uniform float uNight;
varying vec3 vWorld;
varying float vWave;

void main() {
  vec3 V = normalize(uCameraPos - vWorld);

  // Normal from analytic derivatives of the vertex waves plus ripple detail.
  float t = uTime;
  vec2 p = vWorld.xz;
  float nx = cos(p.x * 0.13 + t * 1.1) * 0.13 * 0.16
           + cos((p.x + p.y) * 0.07 + t * 0.5) * 0.07 * 0.10;
  float nz = cos(p.y * 0.19 - t * 0.83) * 0.19 * 0.13
           + cos((p.x + p.y) * 0.07 + t * 0.5) * 0.07 * 0.10;
  float rip = (vnoise(p * 2.3 + vec2(t * 0.6, -t * 0.4)) - 0.5) * 0.35;
  vec3 N = normalize(vec3(-nx * 4.0 + rip, 1.0, -nz * 4.0 + rip));

  float fres = pow(1.0 - max(dot(N, V), 0.0), 4.0);
  fres = clamp(fres * 0.9 + 0.06, 0.0, 1.0);

  vec3 body = mix(uWaterDeep, uWaterShallow, clamp(vWave * 2.0 + 0.5, 0.0, 1.0));
  vec3 reflectCol = mix(uSkyColor * 1.15, uFogColor, 0.3);
  vec3 color = mix(body, reflectCol, fres);

  // Specular glint — the thing that actually makes water look wet.
  vec3 H = normalize(uSunDir + V);
  float spec = pow(max(dot(N, H), 0.0), 200.0);
  color += uSunColor * spec * 3.0 * (1.0 - uNight * 0.7);

  // Sparkle: high-frequency noise gated by the specular lobe.
  float sparkle = smoothstep(0.72, 0.95, vnoise(p * 9.0 + vec2(t * 1.7, t * 1.1)));
  color += uSunColor * sparkle * pow(max(dot(N, H), 0.0), 40.0) * 1.4 * (1.0 - uNight);

  // Foam near the shore, approximated by wave height against the sample noise.
  float foam = smoothstep(0.62, 0.95, vnoise(p * 1.6 + vec2(t * 0.25, 0.0)) + vWave);
  color = mix(color, vec3(0.86, 0.90, 0.94), foam * 0.10);

  color = applyFog(color, vWorld);
  gl_FragColor = vec4(color, 0.90);
}
`;

// ---------------------------------------------------------------------------
//  Particles — soft additive/alpha billboards
// ---------------------------------------------------------------------------

export const PARTICLE_VS = `
precision highp float;
attribute vec2 aCorner;    // unit quad corner in [-0.5, 0.5]
attribute vec4 aCenter;    // xyz = world pos, w = size
attribute vec4 aColor;     // rgba
attribute vec2 aExtra;     // x = rotation, y = softness
uniform mat4 uViewProj;
uniform vec3 uCamRight;
uniform vec3 uCamUp;
varying vec2 vUV;
varying vec4 vColor;
varying float vSoft;
void main() {
  float c = cos(aExtra.x), s = sin(aExtra.x);
  vec2 corner = vec2(aCorner.x * c - aCorner.y * s, aCorner.x * s + aCorner.y * c);
  vec3 world = aCenter.xyz + (uCamRight * corner.x + uCamUp * corner.y) * aCenter.w;
  vUV = aCorner * 2.0;
  vColor = aColor;
  vSoft = aExtra.y;
  gl_Position = uViewProj * vec4(world, 1.0);
}
`;

export const PARTICLE_FS = `
precision highp float;
varying vec2 vUV;
varying vec4 vColor;
varying float vSoft;
void main() {
  float d = length(vUV);
  if (d > 1.0) discard;
  float a = pow(1.0 - d, mix(1.0, 3.0, vSoft));
  gl_FragColor = vec4(vColor.rgb, vColor.a * a);
}
`;

// ---------------------------------------------------------------------------
//  Post-processing: bright extract → blur → composite with ACES tonemapping
// ---------------------------------------------------------------------------

export const FULLSCREEN_VS = `
precision highp float;
attribute vec2 aPos;
varying vec2 vUV;
void main() {
  vUV = aPos * 0.5 + 0.5;
  gl_Position = vec4(aPos, 0.0, 1.0);
}
`;

export const BRIGHT_FS = `
precision highp float;
uniform sampler2D uTex;
uniform vec2 uTexel;
uniform float uThreshold;
varying vec2 vUV;
void main() {
  // 4-tap box downsample keeps the bright pass cheap and stable.
  vec3 c = texture2D(uTex, vUV + vec2(-uTexel.x, -uTexel.y)).rgb;
  c += texture2D(uTex, vUV + vec2(uTexel.x, -uTexel.y)).rgb;
  c += texture2D(uTex, vUV + vec2(-uTexel.x, uTexel.y)).rgb;
  c += texture2D(uTex, vUV + vec2(uTexel.x, uTexel.y)).rgb;
  c *= 0.25;
  float lum = dot(c, vec3(0.2126, 0.7152, 0.0722));
  float k = max(lum - uThreshold, 0.0) / max(lum, 0.0001);
  gl_FragColor = vec4(c * k, 1.0);
}
`;

export const BLUR_FS = `
precision highp float;
uniform sampler2D uTex;
uniform vec2 uDir;
varying vec2 vUV;
void main() {
  // 9-tap gaussian collapsed into 5 bilinear fetches.
  vec3 c = texture2D(uTex, vUV).rgb * 0.2270270270;
  c += texture2D(uTex, vUV + uDir * 1.3846153846).rgb * 0.3162162162;
  c += texture2D(uTex, vUV - uDir * 1.3846153846).rgb * 0.3162162162;
  c += texture2D(uTex, vUV + uDir * 3.2307692308).rgb * 0.0702702703;
  c += texture2D(uTex, vUV - uDir * 3.2307692308).rgb * 0.0702702703;
  gl_FragColor = vec4(c, 1.0);
}
`;

export const COMPOSITE_FS = `
precision highp float;
${HASH_NOISE}
uniform sampler2D uScene;
uniform sampler2D uBloom;
uniform vec2 uTexel;
uniform float uBloomStrength;
uniform float uExposure;
uniform float uVignette;
uniform float uSaturation;
uniform vec3 uTint;
uniform float uAberration;
uniform float uTime;
uniform float uDamage;        // red flash on taking a hit
uniform float uDeath;         // desaturate + darken on death
varying vec2 vUV;

// ACES filmic approximation (Narkowicz). Cheap and keeps highlights from
// clipping to flat white, which matters with a bright sun in frame.
vec3 aces(vec3 x) {
  const float a = 2.51, b = 0.03, c = 2.43, d = 0.59, e = 0.14;
  return clamp((x * (a * x + b)) / (x * (c * x + d) + e), 0.0, 1.0);
}

void main() {
  vec2 uv = vUV;
  vec2 center = uv - 0.5;
  float r2 = dot(center, center);

  // Barrel-ish chromatic aberration, strongest at the corners.
  vec3 scene;
  if (uAberration > 0.0001) {
    vec2 off = center * r2 * uAberration;
    scene.r = texture2D(uScene, uv + off).r;
    scene.g = texture2D(uScene, uv).g;
    scene.b = texture2D(uScene, uv - off).b;
  } else {
    scene = texture2D(uScene, uv).rgb;
  }

  vec3 bloom = texture2D(uBloom, uv).rgb;
  vec3 color = scene + bloom * uBloomStrength;

  color *= uExposure;
  color = aces(color);

  // Grade: saturation, then tint.
  float lum = dot(color, vec3(0.2126, 0.7152, 0.0722));
  color = mix(vec3(lum), color, uSaturation);
  color *= uTint;

  // Damage / death overlays.
  color = mix(color, vec3(0.55, 0.03, 0.03), uDamage * 0.55);
  color = mix(color, vec3(dot(color, vec3(0.33))) * vec3(0.85, 0.55, 0.5), uDeath);

  // Vignette.
  float vig = 1.0 - uVignette * smoothstep(0.15, 0.85, r2 * 2.0);
  color *= vig;

  // Dither to kill banding in the sky gradient — essential on 8-bit output.
  float dither = (hash12(gl_FragCoord.xy + fract(uTime) * 17.0) - 0.5) / 255.0;
  color += dither;

  gl_FragColor = vec4(color, 1.0);
}
`;
