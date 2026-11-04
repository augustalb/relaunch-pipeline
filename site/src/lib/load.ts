import type { PreviewFile } from './types';

// Preview data written by the pipeline (git-ignored).
const files = import.meta.glob<PreviewFile>('../data/previews/*.json', { eager: true, import: 'default' });
// Industry templates are loaded straight from the industry packs: industries/<name>/site/Template.astro
const templates = import.meta.glob('../../../industries/*/site/Template.astro', { eager: true });

export function allPreviews(): PreviewFile[] {
  return Object.values(files).filter((f) => f && f.meta && f.content);
}

export function templateFor(industry: string): any {
  const key = `../../../industries/${industry}/site/Template.astro`;
  const mod: any = templates[key];
  if (!mod) throw new Error(`No Astro template for industry "${industry}" (expected industries/${industry}/site/Template.astro)`);
  return mod.default;
}

export const PROMOTE_SLUG: string | undefined = import.meta.env.PROMOTE_SLUG || process.env.PROMOTE_SLUG || undefined;
