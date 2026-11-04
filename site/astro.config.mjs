// @ts-check
import { defineConfig } from 'astro/config';
import tailwindcss from '@tailwindcss/vite';

// PROMOTE_SLUG: build a single customer site at "/" (see `pipeline promote`).
// Otherwise all previews are built under /<slug>/ for one shared Pages project.
export default defineConfig({
  site: process.env.SITE_URL || 'https://preview.example.de',
  output: 'static',
  trailingSlash: 'ignore',
  build: { format: 'directory', inlineStylesheets: 'auto' },
  compressHTML: true,
  vite: { plugins: [tailwindcss()] },
});
