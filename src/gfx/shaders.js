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
uniform vec3 uSkyColor;      // zenith irradiance
uniform vec3 uHorizonColor;  // horizon-band irradiance
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

// ---------------------------------------------------------------------------
//  Surfaces
//
//  There are no image assets, so materials are defined by how they weight four
//  channels of one procedurally generated tiling texture (see textures.js).
//  Everything is projected triplanar in world space: no mesh carries UVs, which
//  is what lets a box, a terrain chunk and a sword all share this code.
// ---------------------------------------------------------------------------

const SURFACE_UNIFORMS = `
uniform sampler2D uSurfTex;   // r grain, g blotch, b fibre, a crack
uniform sampler2D uNormTex;   // rgb tangent-space normal, a roughness variation
uniform float uDetailFade;    // metres over which detail fades out
`;

const SURFACE_FUNCS = `
// Triplanar weights. The fourth power makes the blend region narrow, so flat
// ground is effectively a single projection and only cliffs pay for three.
vec3 triWeights(vec3 n) {
  vec3 w = abs(n);
  w = w * w; w = w * w;
  return w / max(w.x + w.y + w.z, 1e-4);
}

vec4 triplanar(sampler2D tex, vec3 p, vec3 w, float scale) {
#ifdef CHEAP_SURFACE
  // One projection, picked by the dominant axis. Visually close on anything
  // that is not a cliff face, and a third of the fetches.
  vec2 uv = w.y > max(w.x, w.z) ? p.xz : (w.x > w.z ? p.zy : p.xy);
  return texture2D(tex, uv * scale);
#else
  return texture2D(tex, p.zy * scale) * w.x
       + texture2D(tex, p.xz * scale) * w.y
       + texture2D(tex, p.xy * scale) * w.z;
#endif
}

/**
 * Triplanar normal mapping, whiteout blend. Each projection's tangent-space
 * normal is folded into the geometric normal by adding its XY to the two world
 * axes that projection does not own — which avoids needing stored tangents.
 */
vec3 triplanarNormal(vec3 p, vec3 N, vec3 w, float scale, float strength) {
  if (strength < 0.01) return N;
#ifdef CHEAP_SURFACE
  vec2 uv = w.y > max(w.x, w.z) ? p.xz : (w.x > w.z ? p.zy : p.xy);
  vec3 t = texture2D(uNormTex, uv * scale).xyz * 2.0 - 1.0;
  vec3 r = w.y > max(w.x, w.z)
    ? vec3(t.x + N.x, abs(t.z) * N.y, t.y + N.z)
    : (w.x > w.z ? vec3(abs(t.z) * N.x, t.y + N.y, t.x + N.z)
                 : vec3(t.x + N.x, t.y + N.y, abs(t.z) * N.z));
  return normalize(mix(N, normalize(r), strength));
#else
  vec3 tx = texture2D(uNormTex, p.zy * scale).xyz * 2.0 - 1.0;
  vec3 ty = texture2D(uNormTex, p.xz * scale).xyz * 2.0 - 1.0;
  vec3 tz = texture2D(uNormTex, p.xy * scale).xyz * 2.0 - 1.0;
  vec3 nx = vec3(abs(tx.z) * N.x, tx.y + N.y, tx.x + N.z);
  vec3 ny = vec3(ty.x + N.x, abs(ty.z) * N.y, ty.y + N.z);
  vec3 nz = vec3(tz.x + N.x, tz.y + N.y, abs(tz.z) * N.z);
  vec3 r = normalize(nx * w.x + ny * w.y + nz * w.z);
  return normalize(mix(N, r, strength));
#endif
}

/**
 * Modulate an albedo by the four surface channels.
 * Each channel is centred on 0.5 so a zero weight is exactly a no-op, and the
 * crack channel multiplies rather than adds so fissures read as shadow.
 */
vec3 surfaceAlbedo(vec3 albedo, vec4 s, vec4 weights, vec3 dryTint) {
  float grain = (s.r - 0.5) * weights.x;
  float blotch = (s.g - 0.5) * weights.y;
  float fibre = (s.b - 0.5) * weights.z;
  float crack = (0.5 - s.a) * weights.w;
  vec3 c = albedo * (1.0 + grain * 1.05 + blotch * 1.45 + fibre * 1.15);
  // Value modulation alone still reads as one painted colour. Real ground goes
  // *hue* as well as brightness — sun-bleached patches, damp hollows, dust —
  // so the blotch channel also pulls the albedo toward a second tint.
  c = mix(c, c * dryTint, clamp(blotch * 2.2, -0.65, 0.65) * 0.5 + 0.5);
  return c * (1.0 - clamp(crack, 0.0, 1.0) * 1.55);
}
`;

const LIGHTING_FUNCS = `
float cloudShadow(vec3 worldPos) {
  vec2 uv = worldPos.xz * uCloudParams.z + uCloudParams.xy;
  float c = texture2D(uCloudTex, uv).r;
  float s = smoothstep(0.42, 0.72, c);
  return mix(1.0, 1.0 - uCloudParams.w, s);
}

// GGX normal distribution + Smith height-correlated visibility, Schlick Fresnel.
// This is what makes a steel pauldron and a linen cloak respond differently to
// the same sun instead of both being matte paint.
vec3 specularGGX(vec3 N, vec3 V, vec3 L, vec3 F0, float rough) {
  vec3 H = normalize(L + V);
  float ndl = max(dot(N, L), 0.0);
  float ndv = max(dot(N, V), 1e-4);
  float ndh = max(dot(N, H), 0.0);
  float vdh = max(dot(V, H), 0.0);
  float a = max(rough * rough, 0.003);
  float a2 = a * a;
  float d = ndh * ndh * (a2 - 1.0) + 1.0;
  float D = a2 / (3.14159265 * d * d);
  float k = a * 0.5;
  float G = (ndl / (ndl * (1.0 - k) + k)) * (ndv / (ndv * (1.0 - k) + k));
  vec3 F = F0 + (1.0 - F0) * pow(1.0 - vdh, 5.0);
  return D * G * F / max(4.0 * ndl * ndv, 1e-4) * ndl;
}

/**
 * The shared surface response.
 *
 *   brdf.x roughness   brdf.y metalness   brdf.z rim strength
 *
 * Diffuse stays wrapped rather than Lambert: the terminator softness is doing
 * real work hiding a low polygon count, and losing it makes characters read as
 * faceted. Specular is physical, because that is the part the eye reads as
 * material.
 */
vec3 applyLighting(vec3 albedo, vec3 N, vec3 worldPos, float shadow, float ao, vec3 brdf) {
  vec3 V = normalize(uCameraPos - worldPos);
  float rough = clamp(brdf.x, 0.03, 1.0);
  float metal = clamp(brdf.y, 0.0, 1.0);
  vec3 F0 = mix(vec3(0.04), albedo, metal);
  vec3 diffAlbedo = albedo * (1.0 - metal);

  float ndl = dot(N, uSunDir);
  // The wrap used to be 0.35, which was the right call when every surface was
  // an untextured facet and the softness was hiding the polygon count. It is
  // the wrong call now: a wrap that wide flattens the diffuse response to
  // d(shading)/d(ndl) = 0.74, so a 20-degree normal-map tilt moved the shading
  // by four percent and every bump map in the game was invisible. Narrowing it
  // is what makes the normal maps actually do something.
  float wrapped = max(0.0, (ndl + 0.22) / 1.22);
  vec3 direct = uSunColor * wrapped * shadow;
  vec3 spec = specularGGX(N, V, uSunDir, F0, rough) * uSunColor * shadow;

  // Ambient irradiance from a three-band sky: zenith, horizon, ground.
  //
  // A two-band zenith-to-ground lerp has no term for the horizon, and the
  // horizon band is where most of the sky's energy sits at exactly the hours
  // that matter. At dusk the strip above the treeline is several times
  // brighter than the zenith and it is the *only* light a forest floor still
  // receives once the sun is down; ignoring it is why shadowed geometry fell
  // to near-black under a sky that was still burning orange. It also splits
  // the ambient by hue — cool from above, warm from the side — so a trunk and
  // the ground beside it stop being the same flat wash.
  float hemi = N.y * 0.5 + 0.5;
  vec3 vertical = mix(uGroundColor, uSkyColor, hemi);
  // Every surface collects some of the band; a side-on one collects most.
  float band = 0.34 + 0.30 * (1.0 - abs(N.y));
  vec3 ambIrr = mix(vertical, uHorizonColor, band);

  // The sky is an extended source, but it is not an isotropic one. A large
  // share of its energy sits in the aureole around the key — circumsolar by
  // day, circumlunar by night — and a surface still collects that share when
  // the key itself is occluded.
  //
  // Modelling it is not a refinement, it is what makes shadow readable. Both
  // terms above are *stationary* at N = up: the derivative of hemi and of band
  // with respect to a small tilt of a level surface is zero, so on gently
  // varying ground every hummock, rut and normal-map bump returns the identical
  // ambient value. Under a lit key that costs nothing, because the direct term
  // carries the shape. In shadow the ambient *is* the shape, and at night —
  // where there is no lit atmosphere to fill in and ambient is nearly all the
  // light there is — it is why shadowed ground reads as one flat wash no matter
  // what the terrain under it is doing. A dot product against the key restores
  // the first-order response to tilt that the hemisphere function cannot have.
  //
  // Referenced to a level normal, so it contributes exactly nothing to flat
  // ground at any hour: this shapes the ambient, it does not lift it.
  //
  // The floor is what the anti-key half of the sky is still worth, and it has
  // to be set by that and not by taste, because it is the only part of this
  // term that can take light away. A floor of f says the aureole carries
  // (1 - f) of all sky energy; at 0.55 that is 45%, which is far more than a
  // clear night sky puts within a few degrees of the moon. 0.70 is the honest
  // number and it is also the safe one: at night the ambient is nearly all the
  // light there is, so the faces this bound applies to — steep ground turned
  // more than about 80 degrees off the key, which is already the darkest thing
  // in frame — are exactly the ones with no room left before they crush to
  // black. Nothing is lost by raising it. The gently varying ground this term
  // exists for sits far inside both bounds, where the response is linear and
  // the clamp never engages at all.
  float aureole = clamp(1.0 + 0.80 * (dot(N, uSunDir) - uSunDir.y), 0.70, 1.60);
  vec3 ambient = ambIrr * aureole * ao;

  // Ambient specular. Without this, metal in shadow is just dark plastic — the
  // sky is the main light source for a polished surface most of the time. It
  // reflects the horizon more than the zenith at the glancing angles where it
  // is strongest, which is what makes a low sun read on a blade.
  float ndv = max(dot(N, V), 0.0);
  vec3 ambF = F0 + (max(vec3(1.0 - rough), F0) - F0) * pow(1.0 - ndv, 5.0);
  vec3 ambSpec = mix(uSkyColor, uHorizonColor, 0.55) * ambF * (1.0 - rough * 0.82) * ao;

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
    float pndl = max(dot(N, L), 0.0) * 0.75 + 0.25;
    point += uPointColors[i] * pndl * atten;
    point += uPointColors[i] * specularGGX(N, V, L, F0, rough) * atten * 0.6;
  }

  // Rim: sky light wrapping around the silhouette.
  float rim = pow(1.0 - ndv, 3.0) * brdf.z;

  // The rim is sky wrapping the silhouette, so it takes the same three-band
  // sky the ambient does — at dusk that is a warm edge, not a blue one.
  vec3 rimCol = mix(uSkyColor, uHorizonColor, 0.6);
  return diffAlbedo * (direct + ambient + point) + spec + ambSpec + rimCol * rim * 0.6;
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
  // Aerial perspective takes its colour from the sky standing behind it, and
  // the sky is not one colour: the band right at the horizon carries far more
  // scattered light than the air a few degrees above it. Flattening that into
  // one tone is what collapses the far half of a landscape into a single
  // value — the haze over a valley floor and the haze against the ridge above
  // it come out identical, and every landform past the mid distance stops
  // separating from its neighbour.
  float upness = clamp(dir.y * 1.6 + 0.34, 0.0, 1.0);
  vec3 fogCol = uFogColor * mix(1.12, 0.80, upness);
  fogCol = mix(fogCol, uFogSunColor, pow(sunAmount, 6.0));
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

// ---------------------------------------------------------------------------
//  Scene buffer encoding
//
//  With a half-float scene target these are the identity. Without one, the
//  opaque passes write a Reinhard-compressed value and the composite inverts
//  it, which keeps highlight *ordering* through an 8-bit buffer instead of
//  clipping everything above 1.0 to flat white before the tone mapper runs.
//  The midtone precision cost is real but far smaller than the loss of every
//  specular highlight, sun disc and ember in the frame.
// ---------------------------------------------------------------------------

const SCENE_ENCODE = `
vec3 encodeScene(vec3 c) {
#ifdef LDR_SCENE
  return c / (1.0 + c);
#else
  return c;
#endif
}
`;

const SCENE_DECODE = `
vec3 decodeScene(vec3 c) {
#ifdef LDR_SCENE
  return c / max(1.0 - c, 0.002);
#else
  return c;
#endif
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
attribute vec2 aExtra;      // x = multi-scale relief (0.74 = flat), y = road

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
${SCENE_ENCODE}
${COMMON_UNIFORMS}
${SURFACE_UNIFORMS}
${SHADOW_FUNCS}
${HASH_NOISE}
${SURFACE_FUNCS}
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
  vec3 triW = triWeights(N);
  float camDist = length(vWorld - uCameraPos);
  // Detail fades with distance: past the fade range the high-frequency texture
  // is smaller than a pixel and only produces shimmer, so it is worth nothing
  // and costs aliasing.
  float detail = 1.0 - smoothstep(uDetailFade * 0.45, uDetailFade, camDist);

  // Two scales of noise break up the flat vertex colours; this is the single
  // biggest readability win on large terrain at almost no cost.
  float n1 = vnoise(vWorld.xz * 0.11);
  float n2 = vnoise(vWorld.xz * 0.9);
  float n3 = vnoise(vWorld.xz * 3.7);

  // Three texture frequencies with staggered fade distances.
  //
  // Two was not enough, and the reason is geometric: the ground is seen at a
  // grazing angle, so the band of the frame between "at your feet" and "the
  // horizon" is most of the visible ground and almost all of it sits past the
  // close-range fade. With only a macro and a fine pass that whole band goes
  // smooth. The mid pass is sized to still be a few pixels across at a hundred
  // metres, which is exactly where the other two have nothing left to say.
  vec4 macro = triplanar(uSurfTex, vWorld, triW, 0.030);
  vec4 mid = triplanar(uSurfTex, vWorld, triW, 0.105);
  vec4 fine = triplanar(uSurfTex, vWorld, triW, 0.33);
  float midFade = 1.0 - smoothstep(uDetailFade * 1.6, uDetailFade * 4.2, camDist);
  vec4 surf = mix(macro, mid, 0.62 * midFade);
  surf = mix(surf, fine, 0.45 * detail);

  // The biome tint arrives per vertex, so a chunk spanning meadow and forest
  // blends across the seam instead of switching abruptly.
  vec3 ground = vTint * (0.80 + 0.42 * (n1 * 0.65 + n2 * 0.35));
  ground *= 0.93 + 0.14 * n3;

  vec3 rock = uRockColor * (0.72 + 0.44 * vnoise(vWorld.xz * 0.55 + vWorld.y * 0.35));
  // Strata: horizontal banding by world height reads as sedimentary rock.
  rock *= 0.88 + 0.22 * sin(vWorld.y * 1.35 + n1 * 3.0);
  vec3 sand = uSandColor * (0.88 + 0.24 * n2);
  vec3 snow = uSnowColor * (0.80 + 0.40 * (n1 * 0.6 + n2 * 0.4)) * (0.94 + 0.14 * n3);

  vec4 w = vSplat;
  float total = max(w.r + w.g + w.b + w.a, 0.0001);
  w /= total;

  // Each terrain layer weights the surface channels differently: turf takes
  // grain and blotch, rock takes cracks hard, sand is almost pure grain, snow
  // is soft blotch with a faint crust. This is what stops all four looking like
  // the same material in four colours.
  ground = surfaceAlbedo(ground, surf, vec4(0.42, 0.62, 0.10, 0.16),
    vec3(1.22, 1.02, 0.62));   // sun-bleached straw in the dry patches
  rock = surfaceAlbedo(rock, surf, vec4(0.40, 0.50, 0.04, 0.85),
    vec3(0.86, 0.94, 0.88));   // lichen green-grey in the damp
  sand = surfaceAlbedo(sand, surf, vec4(0.58, 0.30, 0.06, 0.12),
    vec3(1.10, 0.96, 0.78));
  snow = surfaceAlbedo(snow, surf, vec4(0.30, 0.40, 0.03, 0.22),
    vec3(0.90, 0.96, 1.10));   // blue in the compacted hollows
  vec3 albedo = ground * w.r + rock * w.g + sand * w.b + snow * w.a;

  // Two scales of relief, because the ground is almost always seen at a
  // grazing angle. At that angle the close-range texture is compressed into a
  // few pixels vertically and mips away to nothing, so the detail that
  // survives — and therefore the detail that matters — is the macro one. The
  // fine pass only earns its cost within a few metres of the camera.
  float bump = (1.30 * w.r + 1.90 * w.g + 1.05 * w.b + 0.70 * w.a);
  N = triplanarNormal(vWorld, N, triW, 0.030, bump * 0.85);
  N = triplanarNormal(vWorld, N, triW, 0.105, bump * 0.95 * midFade);
  N = triplanarNormal(vWorld, N, triW, 0.33, bump * detail);

  // Relief response. vExtra.x is the terrain's own convexity at three scales,
  // so it knows a ridge from a hollow, and ground is not one material laid
  // flat: hollows collect damp soil and leaf litter and sit in their own
  // shade, shoulders and ridges are wind-scoured, drier and paler. Tying the
  // albedo to it as well as the ambient is what makes the shape of the land
  // readable at midday, when the light itself has nothing to say about it.
  float relief = clamp((vExtra.x - 0.74) * 2.6, -1.0, 1.0);
  albedo *= 1.0 + relief * 0.15;
  albedo = mix(albedo, albedo * vec3(0.86, 0.93, 0.98), max(-relief, 0.0) * 0.40);

  // Roads: packed dirt with wheel-rut noise. The blend starts late so the
  // path has soft, trodden-looking edges instead of a painted stripe.
  float road = vExtra.y;
  vec3 roadCol = uRoadColor * (0.85 + 0.3 * n2) * (0.94 + 0.1 * n3);
  albedo = mix(albedo, roadCol, smoothstep(0.40, 0.92, road) * 0.88);

  // Wet ground darkens and tightens; used during rain.
  float wet = clamp(uWetness * (0.35 + 0.65 * (w.r + road)), 0.0, 1.0);
  albedo = mix(albedo, albedo * 0.6, wet);

  float shadow = shadowFactor(vWorld, N) * cloudShadow(vWorld);
  // Cavity from the crack channel: a cheap stand-in for occlusion inside the
  // fissures, and it costs one multiply.
  float cavity = mix(1.0, clamp(surf.a * 1.5 + 0.25, 0.0, 1.0), 0.55 * detail);
  float ao = vExtra.x * cavity;

  // Rough where it is dry and broken, glossy where it is wet or icy.
  float rough = clamp(0.94 - 0.10 * w.b - 0.16 * w.a - wet * 0.55
    + (surf.a - 0.5) * 0.20, 0.06, 1.0);
  vec3 color = applyLighting(albedo, N, vWorld, shadow, ao,
    vec3(rough, 0.0, 0.16 + wet * 0.55));
  color = applyFog(color, vWorld);
  gl_FragColor = vec4(encodeScene(color), 1.0);
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
attribute vec4 aMaterial; // x = primary material id, y = secondary id,
                          // z = roughness multiplier, w = detail scale multiplier

uniform mat4 uViewProj;
uniform float uTime;
uniform vec2 uWind;     // xz wind vector

// Material table. Resolved here rather than in the fragment shader for two
// reasons: material is constant across an instance so per-vertex is exact, and
// GLSL ES 1.00 forbids indexing a uniform array by a non-constant expression in
// a fragment shader, which a per-instance id necessarily is.
uniform vec4 uMatSurf[12];  // channel weights: grain, blotch, fibre, crack
uniform vec4 uMatBrdf[12];  // roughness, metalness, bump strength, texture scale

varying vec3 vWorld;
varying vec3 vNormal;
varying vec4 vColor;
varying vec4 vParams;
varying vec4 vSurf;
varying vec4 vBrdf;

// Loop index counts as a constant-index-expression, which is what makes this
// legal where a direct dynamic index is not.
void lookupMaterial(float id, out vec4 surf, out vec4 brdf) {
  surf = uMatSurf[0];
  brdf = uMatBrdf[0];
  for (int i = 1; i < 12; i++) {
    if (abs(float(i) - id) < 0.5) { surf = uMatSurf[i]; brdf = uMatBrdf[i]; }
  }
}

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
  float blend = clamp(aBlend, 0.0, 1.0);
  vColor = mix(aColor, aColor2, blend);

  // The same blend that picks bark or leaves picks their materials, so one
  // instanced tree gets fibrous cracked bark on the trunk and soft blotchy
  // foliage in the canopy from a single draw call.
  vec4 surfA, brdfA, surfB, brdfB;
  lookupMaterial(aMaterial.x, surfA, brdfA);
  lookupMaterial(aMaterial.y, surfB, brdfB);
  vSurf = mix(surfA, surfB, blend);
  vBrdf = mix(brdfA, brdfB, blend);
  vBrdf.x = clamp(vBrdf.x * max(aMaterial.z, 0.01), 0.02, 1.0);
  vBrdf.w *= max(aMaterial.w, 0.01);

  vParams = aParams;
  gl_Position = uViewProj * vec4(world, 1.0);
}
`;

export const INSTANCE_FS = `
precision highp float;
${SCENE_ENCODE}
${COMMON_UNIFORMS}
${SURFACE_UNIFORMS}
${SHADOW_FUNCS}
${HASH_NOISE}
${SURFACE_FUNCS}
${LIGHTING_FUNCS}

varying vec3 vWorld;
varying vec3 vNormal;
varying vec4 vColor;
varying vec4 vParams;
varying vec4 vSurf;
varying vec4 vBrdf;

void main() {
  if (vParams.w < 0.02) discard;
  vec3 N = normalize(vNormal);
  vec3 triW = triWeights(N);
  float camDist = length(vWorld - uCameraPos);
  float detail = 1.0 - smoothstep(uDetailFade * 0.35, uDetailFade * 0.85, camDist);

  float scale = vBrdf.w;
  vec4 surf = triplanar(uSurfTex, vWorld, triW, scale);
  // Away from the camera the texture collapses toward its mean, which is what
  // the mip chain would give anyway — doing it explicitly avoids the shimmer.
  surf = mix(vec4(0.5), surf, detail);

  // Worn surfaces go warmer and slightly desaturated, which is what dust,
  // oxidation and use actually do to leather, steel and cloth alike.
  vec3 albedo = surfaceAlbedo(vColor.rgb, surf, vSurf, vec3(1.10, 1.02, 0.90));
  N = triplanarNormal(vWorld, N, triW, scale, vBrdf.z * detail);

  // Roughness varies across a surface: scuffed pauldrons, worn leather.
  float rough = clamp(vBrdf.x + (surf.a - 0.5) * 0.28 * detail, 0.03, 1.0);
  float cavity = mix(1.0, clamp(surf.a * 1.4 + 0.3, 0.0, 1.0), 0.5 * detail);

  float shadow = shadowFactor(vWorld, N) * cloudShadow(vWorld);
  vec3 color = applyLighting(albedo, N, vWorld, shadow, vParams.z * cavity,
    vec3(rough, vBrdf.y, 0.16));
  color += vColor.rgb * vColor.a * 2.2;   // emissive
  color = applyFog(color, vWorld);
  gl_FragColor = vec4(encodeScene(color), vParams.w);
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
${SCENE_ENCODE}
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

  // Grass is matte and slightly waxy at the tip; no metal, a little rim.
  vec3 color = applyLighting(albedo, N, vWorld, shadow, ao,
    vec3(0.86 - 0.16 * vHeight, 0.0, 0.10)) + trans;
  color = applyFog(color, vWorld);
  gl_FragColor = vec4(encodeScene(color), 1.0);
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
${SCENE_ENCODE}
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

// Three octaves, not five, and the second layer below sits at 1.4x rather than
// 2.4x. Both cuts are about the sampling rate, not the look.
//
// The cloud plane is read through a 1/elevation projection, so a feature's
// angular size collapses as the ray flattens: at five octaves the finest one
// was around a pixel a few degrees above the skyline. Detail below the sampling
// rate is not detail, it is aliasing — it shimmers when the camera turns, and
// it is worth nothing to a player. Three octaves plus a 1.4x layer keeps the
// smallest component near five pixels of a 900-wide frame even down at three
// degrees of elevation, and still spans six spatial scales between about three
// and thirty degrees, which is what carries the shape of a cumulus field.
float fbm2(vec2 p) {
  float s = 0.0, a = 0.5;
  for (int i = 0; i < 3; i++) {
    s += a * vnoise(p);
    p *= 2.03;
    a *= 0.5;
  }
  return s;
}

void main() {
  vec3 dir = normalize(vRay);
  float up = dir.y;

  // Base gradient, shaped by air mass rather than by elevation.
  //
  // What a clear sky does between the zenith and the horizon is set by how much
  // atmosphere the ray crosses, and that grows as 1/sin(elevation): the colour
  // and brightness change fastest in the first ten degrees and are nearly done
  // by forty-five. The old curve — smoothstep over pow(up*0.5+0.5, 0.55) —
  // spread the transition evenly across the whole hemisphere instead, which put
  // it 58% of the way from uSkyHorizon to uSkyTop *at the horizon itself*. The
  // consequence was that the horizon colour the keyframes author with some care
  // was never actually drawn: [0.86, 0.40, 0.23] at dusk reached the screen as a
  // muddy mauve, and no sunset in the game ever glowed along the skyline.
  //
  // The keyframes say this is the intent: every one of them authors its fog
  // colour and its horizon colour as near enough the same, which only makes
  // sense if the sky at the horizon is meant to be the colour distant terrain
  // fades into. SKY_KEYS at dusk holds fog 0.62/0.36/0.27 against a horizon of
  // 0.86/0.40/0.23, and this curve lands the skyline on 0.61/0.32/0.27 — the
  // two now meet. The old curve put 0.39/0.53/0.76 there instead, so every
  // frame carried a seam where the fogged far field ran into a sky several
  // shades bluer than itself.
  //
  // 0.22 is the softening that keeps the zenith finite (a true 1/sin diverges),
  // and 0.30 the optical depth — together they land the band in the lowest
  // fifteen degrees, which is where the eye reads distance.
  float airMass = 1.0 / (max(up, 0.0) + 0.22);
  vec3 sky = mix(uSkyHorizon, uSkyTop, clamp(exp(-0.30 * (airMass - 1.0)), 0.0, 1.0));

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

  // Clouds: project the ray onto a deck above the camera and layer fbm.
  //
  // dir.xz / up is where the ray meets a plane one unit up, so the scale that
  // multiplies it is (deck height / cloud size). At 0.048 that put one noise
  // period roughly forty kilometres across a two-kilometre deck: the entire
  // visible sky was a single sample of the field, and the shader could not draw
  // a cloud at any cover setting — overcast and storm differed from clear only
  // by a flat wash of grey. 1.2 puts a period at a kilometre on a deck twelve
  // hundred metres up, which is what a fair-weather cumulus field measures.
  //
  // The +0.20 is the deck's own horizon. A flat layer recedes to infinity as
  // the ray flattens, and hiding that singularity is what the old six-degree
  // fade was for — it erased the clouds from the one part of the sky where a
  // deck is most visible, leaving a bare ring around the whole world. Giving
  // the projection a finite floor makes it converge into a compressed band
  // instead, so the fade only has to cover the last degree and a half. It is
  // also what bounds the compression: 0.20 stops the deck foreshortening past
  // about six to one, which is what keeps the near-skyline band above the
  // sampling rate rather than collapsing into noise.
  if (up > 0.0) {
    vec2 cp = dir.xz / (up + 0.20) * 1.2 + uCloudWind * uCloudSpeed;
    float d1 = fbm2(cp);
    float d2 = fbm2(cp * 1.4 + vec2(11.3, 4.7));
    float density = d1 * 0.72 + d2 * 0.28;
    // Against this field's 0.44 mean and 0.10 deviation, and read through the
    // projection below rather than over a flat sample: clear-weather cloud
    // (cover 0.30) leaves a bit over half the sky open in broken banks,
    // overcast closes it to a handful of breaks, and rain and storm shut it
    // completely. The old pair
    // never reached a closed deck — it did not have to, because a sky that was
    // one sample of the noise was uniform whatever the threshold did. With the
    // field actually resolved, a storm that still showed blue between the
    // clouds would be a worse sky than the flat wash it replaced.
    float cover = mix(0.56, 0.06, uCloudCover);
    float cloud = smoothstep(cover, cover + 0.20, density);
    cloud *= smoothstep(0.0, 0.025, up);

    // Light the cloud from its own density, not from the coverage threshold.
    //
    // Keying the ramp to the coverage threshold meant weather moved it under
    // the field: closing the deck for a storm also slid every sample to the top
    // end and the sky came out as a sheet of white. What makes one part of a
    // cloud brighter than another is how much of it the light crossed, so the
    // window is fixed and reads the same at every cover — thin edges dark,
    // piled tops bright, in clear weather and in a storm alike.
    //
    // It has to span the range the field actually produces, which is 0.44 mean
    // and 0.10 deviation, not the 0.33 this was first calibrated against. Two
    // deviations either side is 0.26 to 0.66. A narrower window costs the cloud
    // its modelling and gives back a cut-out: at 0.24-0.47 every sample that
    // was cloud at all in clear weather came out at the top of the ramp, so
    // fair-weather cumulus drew as flat white shapes with no shading anywhere
    // inside them — a tenth of the visible sky at exactly one colour, and
    // three fifths of it under an overcast. Widening it takes that to about a
    // thirtieth in every weather. Nothing here changes the noise: the same
    // field is simply read across its whole range instead of its top fifth.
    float lit = smoothstep(0.26, 0.66, density);
    vec3 cloudLit = mix(vec3(0.42, 0.45, 0.55), vec3(1.05, 1.0, 0.95), lit);
    cloudLit *= mix(vec3(0.28, 0.32, 0.45), uSunColor * 1.1, 1.0 - uNight);
    // A deep deck passes less light than a few fair-weather banks: the reason a
    // storm reads as a storm is that the whole sky goes down, not up. 0.66 and
    // not 0.52 because the wider ramp above already carries part of that fall
    // on its own — a closed deck sits lower in the field's distribution — and
    // the two together were dimming a storm twice. This pair holds the mean
    // cloud radiance within a few percent of what the narrow window gave in
    // every weather, and spends the difference on variation instead.
    cloudLit *= mix(1.0, 0.66, uCloudCover);
    float edgeGlow = pow(max(dot(dir, uSunDir), 0.0), 8.0) * (1.0 - lit) * 0.8;
    cloudLit += uSunColor * edgeGlow * (1.0 - uNight);
    sky = mix(sky, cloudLit, cloud * 0.94);
  }

  gl_FragColor = vec4(encodeScene(sky), 1.0);
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
${SCENE_ENCODE}
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
  gl_FragColor = vec4(encodeScene(color), 0.90);
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
${SCENE_ENCODE}
varying vec2 vUV;
varying vec4 vColor;
varying float vSoft;
void main() {
  float d = length(vUV);
  if (d > 1.0) discard;
  float a = pow(1.0 - d, mix(1.0, 3.0, vSoft));
  gl_FragColor = vec4(encodeScene(vColor.rgb), vColor.a * a);
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
${SCENE_DECODE}
uniform sampler2D uTex;
uniform vec2 uTexel;
uniform float uThreshold;
varying vec2 vUV;
void main() {
  // 4-tap box downsample keeps the bright pass cheap and stable. Decoding
  // first is the whole point: the values worth blooming are the ones above 1.
  vec3 c = decodeScene(texture2D(uTex, vUV + vec2(-uTexel.x, -uTexel.y)).rgb);
  c += decodeScene(texture2D(uTex, vUV + vec2(uTexel.x, -uTexel.y)).rgb);
  c += decodeScene(texture2D(uTex, vUV + vec2(-uTexel.x, uTexel.y)).rgb);
  c += decodeScene(texture2D(uTex, vUV + vec2(uTexel.x, uTexel.y)).rgb);
  c *= 0.25;
  float lum = dot(c, vec3(0.2126, 0.7152, 0.0722));
  float k = max(lum - uThreshold, 0.0) / max(lum, 0.0001);
  gl_FragColor = vec4(c * k, 1.0);
}
`;

// ---------------------------------------------------------------------------
//  Ambient occlusion
//
//  Reconstructs view-space position from the scene depth texture and samples a
//  hemisphere around each pixel. This is the single cheapest thing that makes
//  objects look like they are *in* the world rather than pasted onto it: the
//  contact darkening where a trunk meets the ground, under a roof eave, in the
//  folds of a cloak. Without it every surface receives identical ambient light
//  and the whole frame reads as a diorama.
//
//  Half resolution, eight taps, spiral kernel rotated per pixel by a hash. The
//  rotation turns banding into noise, and the blur pass turns noise into
//  softness — which is the right trade at this sample count.
//
//  The eight taps are split across two radii. One radius can only find one
//  size of feature: a metre-wide kernel finds the hollow and the shaded side
//  of a boulder and completely misses the contact line where that boulder
//  meets the ground, the fold under a cloak hem, the gap beneath a step. Those
//  short-range creases are what make an object sit *in* the scene rather than
//  on top of it, and they are also the only occlusion fine enough to still
//  vary from one patch of screen to the next.
// ---------------------------------------------------------------------------

/**
 * World mask: 1 where the frame contains geometry, 0 where it is open sky.
 *
 * The image-fidelity metrics are supposed to grade the world, not the weather.
 * Cropping to a fixed fraction of the screen was the first attempt at that and
 * it does not work: the camera pitches up by about 11 degrees, so the true
 * horizon sits around 67% of screen height and a third to a half of any
 * "lower 62%" window is sky by construction. Depth knows exactly which pixels
 * are sky, so it is depth that decides.
 */
export const WORLD_MASK_FS = `
precision highp float;
uniform sampler2D uDepthTex;
varying vec2 vUV;
void main() {
  float d = texture2D(uDepthTex, vUV).r;
  // Anything at (or within a hair of) the far plane never had geometry written
  // to it. The epsilon is generous because a 24-bit depth buffer's far values
  // are extremely non-linear and the sky sits right at the top of that range.
  gl_FragColor = vec4(d < 0.99995 ? 1.0 : 0.0, 0.0, 0.0, 1.0);
}
`;

export const AO_FS = `
precision highp float;
${HASH_NOISE}
uniform sampler2D uDepthTex;
uniform vec2 uTexel;
uniform vec2 uNearFar;
uniform vec2 uProjScale;   // tan(fov/2) * aspect, tan(fov/2)
uniform float uRadius;     // world-space sample radius, metres
uniform float uStrength;
varying vec2 vUV;

float linearDepth(vec2 uv) {
  float d = texture2D(uDepthTex, uv).r * 2.0 - 1.0;
  float n = uNearFar.x, f = uNearFar.y;
  return (2.0 * n * f) / (f + n - d * (f - n));
}

vec3 viewPos(vec2 uv, float z) {
  vec2 ndc = uv * 2.0 - 1.0;
  return vec3(ndc * uProjScale * z, -z);
}

/**
 * Mean horizon occlusion of four spiral taps at one scale.
 *
 * The world radius the kernel stands for drives the range check, which is what
 * keeps a tight kernel from reporting a distant silhouette as a crease and
 * drawing a halo around it.
 */
float occludeAt(vec2 uv0, vec3 p, vec3 N, vec2 rad, vec2 rot, float world) {
  float occ = 0.0;
  for (int i = 0; i < 4; i++) {
    float fi = float(i);
    float a = fi * 2.3999632;              // golden angle: even coverage, no lattice
    float r = sqrt((fi + 0.5) / 4.0);
    vec2 d = vec2(cos(a), sin(a));
    vec2 off = vec2(d.x * rot.x - d.y * rot.y, d.x * rot.y + d.y * rot.x) * r * rad;
    vec2 uv = uv0 + off;
    float sz = linearDepth(uv);
    vec3 sp = viewPos(uv, sz);
    vec3 v = sp - p;
    float len = length(v);
    if (len < 1e-5) continue;
    float ndv = dot(N, v / len);
    // Range check: a sample far in front is a different object, not a fold.
    float range = world / (world + max(len - world, 0.0));
    occ += max(ndv - 0.06, 0.0) * range;
  }
  return occ * 0.25;
}

void main() {
  float z = linearDepth(vUV);
  // Sky pixels sit at the far plane and must not be occluded, or the horizon
  // grows a dark halo.
  if (z >= uNearFar.y * 0.985) { gl_FragColor = vec4(1.0); return; }

  vec3 p = viewPos(vUV, z);
  // Normal from the depth field. The min-of-two-deltas picks the neighbour on
  // the same surface, which stops silhouettes from producing garbage normals.
  vec3 pR = viewPos(vUV + vec2(uTexel.x, 0.0), linearDepth(vUV + vec2(uTexel.x, 0.0)));
  vec3 pL = viewPos(vUV - vec2(uTexel.x, 0.0), linearDepth(vUV - vec2(uTexel.x, 0.0)));
  vec3 pU = viewPos(vUV + vec2(0.0, uTexel.y), linearDepth(vUV + vec2(0.0, uTexel.y)));
  vec3 pD = viewPos(vUV - vec2(0.0, uTexel.y), linearDepth(vUV - vec2(0.0, uTexel.y)));
  vec3 dx = abs(pR.z - p.z) < abs(pL.z - p.z) ? (pR - p) : (p - pL);
  vec3 dy = abs(pU.z - p.z) < abs(pD.z - p.z) ? (pU - p) : (p - pD);
  vec3 N = normalize(cross(dx, dy));

  float ang = hash12(gl_FragCoord.xy) * 6.2831853;
  vec2 rot = vec2(cos(ang), sin(ang));
  // UV radius subtended by a world-space sphere of uRadius at this depth. The
  // per-axis divide is what keeps the kernel circular on a non-square screen.
  vec2 rad = uRadius / (max(z, 0.5) * uProjScale) * 0.5;
  rad = min(rad, vec2(0.06));   // cap: a huge kernel up close is just noise

  // The tight scale is a quarter of the radius, floored at roughly one texel:
  // below that it would sample its own pixel and report nothing. Its range
  // check shrinks with it, so it stays a crease finder and never turns into an
  // outline around distant geometry.
  float tightWorld = uRadius * 0.24;
  vec2 radTight = max(rad * 0.24, uTexel * 1.2);

  // The tight kernel is rotated a further quarter turn so its four taps do not
  // land along the same directions as the wide one's.
  vec2 rotT = vec2(-rot.y, rot.x);
  // Weights: the wide scale keeps roughly the strength the single-scale
  // version had on open ground, and the tight one adds to it only where there
  // is something within a handful of centimetres to occlude. So the broad
  // wash barely moves and contacts get half again as dark.
  float occ = occludeAt(vUV, p, N, rad, rot, uRadius) * 1.86
            + occludeAt(vUV, p, N, radTight, rotT, tightWorld) * 1.56;
  occ = clamp(1.0 - occ * uStrength, 0.0, 1.0);
  gl_FragColor = vec4(occ, occ, occ, 1.0);
}
`;

// Depth-aware 4-tap blur for the AO buffer: cross-surface bleeding is what
// makes cheap AO look like dirt smeared over the image.
export const AO_BLUR_FS = `
precision highp float;
uniform sampler2D uTex;
uniform sampler2D uDepthTex;
uniform vec2 uDir;
uniform vec2 uNearFar;
varying vec2 vUV;

float linearDepth(vec2 uv) {
  float d = texture2D(uDepthTex, uv).r * 2.0 - 1.0;
  float n = uNearFar.x, f = uNearFar.y;
  return (2.0 * n * f) / (f + n - d * (f - n));
}

void main() {
  float z0 = linearDepth(vUV);
  float sum = texture2D(uTex, vUV).r;
  float wsum = 1.0;
  for (int i = 1; i <= 3; i++) {
    float fi = float(i);
    for (float sgn = -1.0; sgn <= 1.0; sgn += 2.0) {
      vec2 uv = vUV + uDir * fi * sgn;
      float w = exp(-abs(linearDepth(uv) - z0) * 1.4) * exp(-fi * fi * 0.20);
      sum += texture2D(uTex, uv).r * w;
      wsum += w;
    }
  }
  float v = sum / wsum;
  gl_FragColor = vec4(v, v, v, 1.0);
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
${SCENE_DECODE}
${HASH_NOISE}
uniform sampler2D uScene;
uniform sampler2D uBloom;
uniform vec2 uTexel;
uniform float uBloomStrength;
uniform float uExposure;
uniform float uVignette;
uniform float uSaturation;
uniform float uContrast;      // S-curve strength around the scene's midtone
uniform float uContrastPivot; // where that midtone sits for this time of day
uniform vec3 uTint;
uniform float uAberration;
uniform float uTime;
uniform float uDamage;        // red flash on taking a hit
uniform float uDeath;         // desaturate + darken on death
uniform sampler2D uAO;
uniform float uAOAmount;      // 0 disables the fetch entirely
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
  scene = decodeScene(scene);

  // Occlusion multiplies the scene rather than only its ambient term. That is
  // not physically right — it dims direct light too — but the error sits in
  // creases that are dark anyway, and it costs one texture fetch instead of a
  // second geometry pass.
  if (uAOAmount > 0.001) {
    float ao = texture2D(uAO, uv).r;
    // Multi-bounce lift (Jimenez et al.). Single-scattering occlusion assumes
    // the light that enters a crease never leaves it, which is why strong AO
    // reads as smeared dirt: it drives interiors to a colourless hole. Light
    // actually bounces off the walls of the crease, so the darkening saturates
    // well above black and carries the surface's own colour with it. The
    // radiance already in the buffer stands in for albedo — a bright surface
    // bounces, a dark one does not — which lets the occlusion be strong enough
    // to model contact without punching holes in the shadows.
    vec3 alb = clamp(scene / (scene + 1.0), vec3(0.04), vec3(1.0));
    vec3 f1 = 2.0404 * alb - 0.3324;
    vec3 f2 = -4.7951 * alb + 0.6417;
    vec3 f3 = 2.7552 * alb + 0.6903;
    vec3 mb = max(vec3(ao), ((ao * f1 + f2) * ao + f3) * ao);
    scene *= mix(vec3(1.0), mb, uAOAmount);
  }

  vec3 bloom = texture2D(uBloom, uv).rgb;
  vec3 color = scene + bloom * uBloomStrength;

  color *= uExposure;
  color = aces(color);

  // Grade: saturation, then tint, then a contrast curve.
  float lum = dot(color, vec3(0.2126, 0.7152, 0.0722));
  color = mix(vec3(lum), color, uSaturation);
  color *= uTint;

  // Contrast about the scene's midtone. ACES alone leaves flat subjects — a
  // noon meadow, a snowfield — sitting in a narrow band; this is the print
  // curve that pulls the shadows down and the highlights up.
  //
  // Applied to luminance and fed back as a gain so every channel scales
  // together: an RGB-space contrast would drag saturation along with it and
  // turn a strong curve into an oversaturated one.
  //
  // The pivot has to follow the exposure, which is why it is a uniform. A
  // fixed 0.30 is right for daylight and wrong after dark: at night nearly
  // every pixel sits below it, so the S-curve stops being an S and becomes a
  // plain multiply that squeezes the whole image into a handful of 8-bit
  // levels. That is precisely how a moonlit ridge ends up reading as paper.
  float pivot = max(uContrastPivot, 0.02);
  float l0 = max(dot(color, vec3(0.2126, 0.7152, 0.0722)), 1e-4);
  float l1 = (l0 - pivot) * uContrast + pivot;
  // Soft toe. This used to clamp to l0 * 0.35, which below the crossover is a
  // near-3x *compression* of the shadows: the range a night or forest-interior
  // frame actually lives in got folded into two or three output levels, and
  // the bottom of it fell straight through the black point. A 0.72 slope still
  // maps black to black — nothing is lifted into milk, no black-level offset —
  // but it leaves the near-blacks separable from each other.
  l1 = max(l1, l0 * 0.72);
  color = clamp(color * (l1 / l0), 0.0, 1.0);

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
