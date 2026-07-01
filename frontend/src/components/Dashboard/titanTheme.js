/**
 * Titan Track — calm "study" palette.
 *
 * The old look leaned on fully-saturated accents (#34D399, #FBBF24, #60A5FA…)
 * as *fills* on near-black, which reads as neon and tires the eyes over a long
 * session. These tokens are the same hues pulled ~halfway toward gray and
 * slightly dimmed, so color signals status without shouting. `mute()` does the
 * same to arbitrary track colors that live in the database.
 */

// Muted status accents (sage / clay / dusty-blue / soft-violet).
export const TONES = {
  text:      '#E4E4E7',
  textDim:   '#A1A1AA',
  textFaint: '#71717A',
  line:      '#1E1E24',

  mastered:  '#6FA88C', // was #34D399 (sage green)
  progress:  '#C2A56B', // was #FBBF24 (warm clay)
  ready:     '#7C93B0', // was #60A5FA (dusty blue)
  violet:    '#9A8FB5', // was #A78BFA (soft violet)
  rose:      '#B08597', // was #EC4899 (muted rose)
  danger:    '#C97A7A', // was #F87171 (muted red)
  locked:    '#3F3F46',

  // Calm sage ramp for the activity heatmap (replaces the bright GitHub greens).
  heat: ['#15151A', '#2A4337', '#3A5E4E', '#4E7E68', '#6FA88C'],
};

function _hexToRgb(hex) {
  let h = String(hex || '').replace('#', '').trim();
  if (h.length === 3) h = h.split('').map((c) => c + c).join('');
  if (h.length < 6) return { r: 124, g: 147, b: 176 }; // fall back to TONES.ready
  return {
    r: parseInt(h.slice(0, 2), 16),
    g: parseInt(h.slice(2, 4), 16),
    b: parseInt(h.slice(4, 6), 16),
  };
}

const _clamp = (n) => Math.max(0, Math.min(255, Math.round(n)));

/**
 * Desaturate a hex color toward its own gray, and dim it slightly, so
 * database-driven track colors (#22C55E, #EC4899, …) match the calm palette
 * instead of glowing. `amount` is how far toward gray (0 = original, 1 = gray).
 */
export function mute(hex, amount = 0.55, dim = 0.9) {
  const { r, g, b } = _hexToRgb(hex);
  const gray = 0.3 * r + 0.59 * g + 0.11 * b;
  const mix = (c) => _clamp((c + (gray - c) * amount) * dim);
  return `rgb(${mix(r)}, ${mix(g)}, ${mix(b)})`;
}

/** A translucent fill of a (muted) color — for soft tinted backgrounds. */
export function softFill(hex, alpha = 0.1) {
  const { r, g, b } = _hexToRgb(hex);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}
