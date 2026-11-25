/**
 * GLSL for the procedural planet, atmosphere and star materials.
 *
 * Every surface these shaders produce is invented. We have resolved images of
 * exactly zero exoplanet surfaces, so the inputs here (base and accent colour,
 * cloud fraction, banding) are chosen by the backend from measured bulk
 * properties — radius, density, equilibrium temperature — and then rendered as a
 * plausible *illustration* of that class of world. The UI labels every such
 * image as an artistic rendering; see `ArtisticNotice`.
 *
 * Texturing is procedural rather than image-based so that six thousand planets
 * cost no download and no texture memory.
 */

/**
 * 3D simplex noise.
 *
 * Ashima Arts / Stefan Gustavson implementation, MIT licensed. Used unchanged;
 * reimplementing it would be strictly worse.
 */
const SIMPLEX_NOISE = /* glsl */ `
vec3 mod289(vec3 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec4 mod289(vec4 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec4 permute(vec4 x) { return mod289(((x * 34.0) + 1.0) * x); }
vec4 taylorInvSqrt(vec4 r) { return 1.79284291400159 - 0.85373472095314 * r; }

float snoise(vec3 v) {
  const vec2 C = vec2(1.0 / 6.0, 1.0 / 3.0);
  const vec4 D = vec4(0.0, 0.5, 1.0, 2.0);

  vec3 i  = floor(v + dot(v, C.yyy));
  vec3 x0 = v - i + dot(i, C.xxx);

  vec3 g = step(x0.yzx, x0.xyz);
  vec3 l = 1.0 - g;
  vec3 i1 = min(g.xyz, l.zxy);
  vec3 i2 = max(g.xyz, l.zxy);

  vec3 x1 = x0 - i1 + C.xxx;
  vec3 x2 = x0 - i2 + C.yyy;
  vec3 x3 = x0 - D.yyy;

  i = mod289(i);
  vec4 p = permute(permute(permute(
             i.z + vec4(0.0, i1.z, i2.z, 1.0))
           + i.y + vec4(0.0, i1.y, i2.y, 1.0))
           + i.x + vec4(0.0, i1.x, i2.x, 1.0));

  float n_ = 0.142857142857;
  vec3 ns = n_ * D.wyz - D.xzx;

  vec4 j = p - 49.0 * floor(p * ns.z * ns.z);

  vec4 x_ = floor(j * ns.z);
  vec4 y_ = floor(j - 7.0 * x_);

  vec4 x = x_ * ns.x + ns.yyyy;
  vec4 y = y_ * ns.x + ns.yyyy;
  vec4 h = 1.0 - abs(x) - abs(y);

  vec4 b0 = vec4(x.xy, y.xy);
  vec4 b1 = vec4(x.zw, y.zw);

  vec4 s0 = floor(b0) * 2.0 + 1.0;
  vec4 s1 = floor(b1) * 2.0 + 1.0;
  vec4 sh = -step(h, vec4(0.0));

  vec4 a0 = b0.xzyw + s0.xzyw * sh.xxyy;
  vec4 a1 = b1.xzyw + s1.xzyw * sh.zzww;

  vec3 p0 = vec3(a0.xy, h.x);
  vec3 p1 = vec3(a0.zw, h.y);
  vec3 p2 = vec3(a1.xy, h.z);
  vec3 p3 = vec3(a1.zw, h.w);

  vec4 norm = taylorInvSqrt(vec4(dot(p0, p0), dot(p1, p1), dot(p2, p2), dot(p3, p3)));
  p0 *= norm.x;
  p1 *= norm.y;
  p2 *= norm.z;
  p3 *= norm.w;

  vec4 m = max(0.6 - vec4(dot(x0, x0), dot(x1, x1), dot(x2, x2), dot(x3, x3)), 0.0);
  m = m * m;
  return 42.0 * dot(m * m, vec4(dot(p0, x0), dot(p1, x1), dot(p2, x2), dot(p3, x3)));
}

float fbm(vec3 p, int octaves) {
  float sum = 0.0;
  float amplitude = 0.5;
  float frequency = 1.0;
  // GLSL ES 1.0 requires a constant loop bound, hence the break.
  for (int i = 0; i < 8; i++) {
    if (i >= octaves) break;
    sum += amplitude * snoise(p * frequency);
    frequency *= 2.03;
    amplitude *= 0.5;
  }
  return sum;
}

float ridged(vec3 p, int octaves) {
  float sum = 0.0;
  float amplitude = 0.5;
  float frequency = 1.0;
  for (int i = 0; i < 8; i++) {
    if (i >= octaves) break;
    sum += amplitude * (1.0 - abs(snoise(p * frequency)));
    frequency *= 2.07;
    amplitude *= 0.5;
  }
  return sum;
}
`;

export const PLANET_VERTEX = /* glsl */ `
varying vec3 vObjectPosition;
varying vec3 vWorldNormal;
varying vec3 vWorldPosition;

void main() {
  vObjectPosition = position;
  vWorldNormal = normalize(mat3(modelMatrix) * normal);
  vec4 worldPosition = modelMatrix * vec4(position, 1.0);
  vWorldPosition = worldPosition.xyz;
  gl_Position = projectionMatrix * viewMatrix * worldPosition;
}
`;

export const PLANET_FRAGMENT = /* glsl */ `
precision highp float;

uniform float uTime;
uniform vec3 uBaseColor;
uniform vec3 uAccentColor;
uniform vec3 uLightDirection;
uniform vec3 uLightColor;
uniform float uCloudCoverage;
uniform float uBanded;
uniform float uRoughness;
uniform float uEmissive;
uniform float uNoiseScale;
uniform float uSeed;
uniform float uAmbient;
uniform int uOctaves;

varying vec3 vObjectPosition;
varying vec3 vWorldNormal;
varying vec3 vWorldPosition;

${SIMPLEX_NOISE}

void main() {
  vec3 noisePosition = normalize(vObjectPosition) * uNoiseScale + uSeed;

  // Rocky and icy worlds get continent-like patches; gas giants get latitudinal
  // bands warped by a slower noise field, which is what actually makes Jupiter
  // read as Jupiter rather than as a mottled ball.
  float terrain = fbm(noisePosition, uOctaves);
  float warp = fbm(noisePosition * 0.45 + 13.7, 3);
  float latitude = normalize(vObjectPosition).y;
  float bands = sin(latitude * 11.0 + warp * 3.4);

  float pattern = mix(
    smoothstep(-0.12, 0.28, terrain),
    smoothstep(-0.35, 0.35, bands),
    uBanded
  );

  vec3 surface = mix(uBaseColor, uAccentColor, pattern);

  // Ridged noise adds mountain-scale relief to solid surfaces only. On a gas
  // giant there is no surface to be rough.
  float relief = ridged(noisePosition * 2.4, 4) - 0.5;
  surface *= 1.0 + relief * 0.18 * (1.0 - uBanded);

  // Clouds drift slowly in longitude, independent of the surface beneath.
  if (uCloudCoverage > 0.01) {
    vec3 cloudPosition = noisePosition * 1.6;
    cloudPosition.x += uTime * 0.012;
    float clouds = fbm(cloudPosition, 4) * 0.5 + 0.5;
    float threshold = 1.0 - uCloudCoverage;
    float cover = smoothstep(threshold - 0.12, threshold + 0.16, clouds);
    surface = mix(surface, vec3(0.96, 0.97, 1.0), cover * 0.82);
  }

  vec3 normal = normalize(vWorldNormal);
  vec3 lightDirection = normalize(uLightDirection);

  // Wrapped diffuse: a hard terminator looks wrong at these scales and hides
  // half the surface detail for no gain in realism.
  float lambert = dot(normal, lightDirection);
  float diffuse = clamp((lambert + 0.25) / 1.25, 0.0, 1.0);

  vec3 viewDirection = normalize(cameraPosition - vWorldPosition);
  vec3 halfVector = normalize(lightDirection + viewDirection);
  float specularPower = mix(96.0, 6.0, clamp(uRoughness, 0.0, 1.0));
  float specular = pow(max(dot(normal, halfVector), 0.0), specularPower)
    * (1.0 - clamp(uRoughness, 0.0, 1.0)) * 0.6;

  vec3 color = surface * uLightColor * diffuse;
  color += uLightColor * specular * step(0.0, lambert);
  color += surface * uAmbient;
  color += surface * uEmissive;

  // Night-side rim: a faint scattered edge so the unlit limb stays readable
  // against a black background.
  float rim = pow(1.0 - max(dot(normal, viewDirection), 0.0), 3.0);
  color += uBaseColor * rim * 0.12;

  gl_FragColor = vec4(color, 1.0);
  #include <colorspace_fragment>
}
`;

export const ATMOSPHERE_VERTEX = /* glsl */ `
varying vec3 vWorldNormal;
varying vec3 vWorldPosition;

void main() {
  vWorldNormal = normalize(mat3(modelMatrix) * normal);
  vec4 worldPosition = modelMatrix * vec4(position, 1.0);
  vWorldPosition = worldPosition.xyz;
  gl_Position = projectionMatrix * viewMatrix * worldPosition;
}
`;

/**
 * Atmospheric shell.
 *
 * Rendered on a slightly larger back-faced sphere with additive blending. The
 * Fresnel term concentrates the glow at the limb, and multiplying by the
 * incident light keeps the day side bright and the night side dark, which is the
 * single cue that most reliably reads as "this world has air".
 */
export const ATMOSPHERE_FRAGMENT = /* glsl */ `
precision highp float;

uniform vec3 uColor;
uniform vec3 uLightDirection;
uniform float uOpacity;
uniform float uPower;

varying vec3 vWorldNormal;
varying vec3 vWorldPosition;

void main() {
  vec3 normal = normalize(vWorldNormal);
  vec3 viewDirection = normalize(cameraPosition - vWorldPosition);

  // Back faces are rendered, so the normal points away from the camera.
  float fresnel = pow(clamp(dot(normal, viewDirection) * -1.0, 0.0, 1.0), uPower);
  float incident = clamp(dot(normal * -1.0, normalize(uLightDirection)) + 0.35, 0.0, 1.0);

  gl_FragColor = vec4(uColor, fresnel * incident * uOpacity);
  #include <colorspace_fragment>
}
`;

export const STAR_VERTEX = PLANET_VERTEX;

/**
 * Stellar photosphere.
 *
 * Granulation and a limb-darkening falloff, both animated slowly. Stars are
 * rendered emissive and rely on bloom in post-processing for their glow rather
 * than on a large transparent halo, which keeps them crisp when the camera is
 * close.
 */
export const STAR_FRAGMENT = /* glsl */ `
precision highp float;

uniform float uTime;
uniform vec3 uColor;
uniform vec3 uHotColor;
uniform float uIntensity;
uniform float uSeed;

varying vec3 vObjectPosition;
varying vec3 vWorldNormal;
varying vec3 vWorldPosition;

${SIMPLEX_NOISE}

void main() {
  vec3 noisePosition = normalize(vObjectPosition) * 3.1 + uSeed;
  float granulation = fbm(noisePosition + vec3(0.0, uTime * 0.03, 0.0), 4);
  float cells = ridged(noisePosition * 2.2 + uTime * 0.02, 3);

  vec3 color = mix(uColor, uHotColor, smoothstep(-0.2, 0.45, granulation));
  color *= 0.82 + cells * 0.4;

  // Limb darkening: the photosphere is optically thick, so we see cooler, higher
  // layers towards the edge of the disc.
  vec3 normal = normalize(vWorldNormal);
  vec3 viewDirection = normalize(cameraPosition - vWorldPosition);
  float mu = max(dot(normal, viewDirection), 0.0);
  float limb = 0.42 + 0.58 * pow(mu, 0.55);

  gl_FragColor = vec4(color * limb * uIntensity, 1.0);
  #include <colorspace_fragment>
}
`;

/** Soft radial falloff for the star's outer corona billboard. */
export const CORONA_FRAGMENT = /* glsl */ `
precision highp float;

uniform vec3 uColor;
uniform float uOpacity;

varying vec2 vUv;

void main() {
  float distance = length(vUv - 0.5) * 2.0;
  float falloff = pow(max(1.0 - distance, 0.0), 2.6);
  gl_FragColor = vec4(uColor, falloff * uOpacity);
  #include <colorspace_fragment>
}
`;

export const CORONA_VERTEX = /* glsl */ `
varying vec2 vUv;

void main() {
  vUv = uv;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}
`;
