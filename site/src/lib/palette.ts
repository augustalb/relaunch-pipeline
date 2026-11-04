// Deterministic per-site colour scheme (seeded by slug) so previews don't all look identical.
export type Palette = { brand: string; brandDark: string; brandSoft: string; accent: string; name: string };

const PALETTES: Palette[] = [
  { name: 'ocean',   brand: '#0f4c81', brandDark: '#0a3357', brandSoft: '#e6eef7', accent: '#f4b400' },
  { name: 'forest',  brand: '#166534', brandDark: '#0f4a26', brandSoft: '#e7f3ea', accent: '#f59e0b' },
  { name: 'signal',  brand: '#b91c1c', brandDark: '#7f1d1d', brandSoft: '#fdeaea', accent: '#111827' },
  { name: 'teal',    brand: '#0f766e', brandDark: '#0b544e', brandSoft: '#e4f3f1', accent: '#fb923c' },
  { name: 'indigo',  brand: '#3730a3', brandDark: '#272174', brandSoft: '#ebeafb', accent: '#facc15' },
  { name: 'slate',   brand: '#1e293b', brandDark: '#0f172a', brandSoft: '#e9edf3', accent: '#22c55e' },
];

export function paletteFor(seed: string, override?: string): Palette {
  if (override) {
    const p = PALETTES.find((x) => x.name === override);
    if (p) return p;
  }
  let h = 0;
  for (const ch of seed) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
  return PALETTES[h % PALETTES.length];
}

export function paletteStyle(p: Palette): string {
  return `--brand:${p.brand};--brand-dark:${p.brandDark};--brand-soft:${p.brandSoft};--accent:${p.accent}`;
}
