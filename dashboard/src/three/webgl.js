/**
 * WebGL capability probe + the shared GLSL noise the scenes build on.
 *
 * The probe exists because every 3D surface in this app is decoration over a
 * working page: a machine without WebGL (locked-down enterprise browser,
 * software-rendering VM, driver blocklist) must still get the full dashboard,
 * just without the ambient scene. Callers check this BEFORE mounting a
 * <Canvas>, since a Canvas that fails to acquire a context throws during
 * render rather than returning null.
 */

let cached = null

export function hasWebGL() {
  if (cached !== null) return cached
  if (typeof document === 'undefined') { cached = false; return cached }
  try {
    const canvas = document.createElement('canvas')
    const gl = canvas.getContext('webgl2') || canvas.getContext('webgl') || canvas.getContext('experimental-webgl')
    cached = Boolean(gl && typeof gl.getParameter === 'function')
    // Release the probe context immediately — browsers cap simultaneous
    // contexts (~16) and a leaked one costs a real slot for the session.
    if (gl && gl.getExtension) gl.getExtension('WEBGL_lose_context')?.loseContext()
    return cached
  } catch {
    cached = false
    return cached
  }
}

/**
 * Gradient (Perlin-style) 2D noise + fbm, hash-based so it needs no texture
 * upload. Shared as a string so the nebula and the hero core sample the exact
 * same field — the background and the focal object visibly belong to one
 * world instead of two unrelated effects.
 */
export const NOISE_GLSL = /* glsl */`
vec2 hash2(vec2 p) {
  p = vec2(dot(p, vec2(127.1, 311.7)), dot(p, vec2(269.5, 183.3)));
  return -1.0 + 2.0 * fract(sin(p) * 43758.5453123);
}

float gnoise(vec2 p) {
  vec2 i = floor(p);
  vec2 f = fract(p);
  vec2 u = f * f * (3.0 - 2.0 * f);
  return mix(
    mix(dot(hash2(i + vec2(0.0, 0.0)), f - vec2(0.0, 0.0)),
        dot(hash2(i + vec2(1.0, 0.0)), f - vec2(1.0, 0.0)), u.x),
    mix(dot(hash2(i + vec2(0.0, 1.0)), f - vec2(0.0, 1.0)),
        dot(hash2(i + vec2(1.0, 1.0)), f - vec2(1.0, 1.0)), u.x),
    u.y);
}

// 3 octaves is the deliberate ceiling: this runs per-pixel over the whole
// viewport three times (domain warping), so octave count is the single
// biggest cost lever in the ambient scene.
float fbm(vec2 p) {
  float v = 0.0;
  float a = 0.5;
  mat2 rot = mat2(0.8, 0.6, -0.6, 0.8);
  for (int i = 0; i < 3; i++) {
    v += a * gnoise(p);
    p = rot * p * 2.03;
    a *= 0.5;
  }
  return v;
}
`

/** Simplex-ish 3D noise for vertex displacement (cheap, gradient-free). */
export const NOISE3_GLSL = /* glsl */`
vec3 hash3(vec3 p) {
  p = vec3(dot(p, vec3(127.1, 311.7, 74.7)),
           dot(p, vec3(269.5, 183.3, 246.1)),
           dot(p, vec3(113.5, 271.9, 124.6)));
  return -1.0 + 2.0 * fract(sin(p) * 43758.5453123);
}

float gnoise3(vec3 p) {
  vec3 i = floor(p);
  vec3 f = fract(p);
  vec3 u = f * f * (3.0 - 2.0 * f);
  return mix(
    mix(mix(dot(hash3(i + vec3(0,0,0)), f - vec3(0,0,0)),
            dot(hash3(i + vec3(1,0,0)), f - vec3(1,0,0)), u.x),
        mix(dot(hash3(i + vec3(0,1,0)), f - vec3(0,1,0)),
            dot(hash3(i + vec3(1,1,0)), f - vec3(1,1,0)), u.x), u.y),
    mix(mix(dot(hash3(i + vec3(0,0,1)), f - vec3(0,0,1)),
            dot(hash3(i + vec3(1,0,1)), f - vec3(1,0,1)), u.x),
        mix(dot(hash3(i + vec3(0,1,1)), f - vec3(0,1,1)),
            dot(hash3(i + vec3(1,1,1)), f - vec3(1,1,1)), u.x), u.y),
    u.z);
}
`
