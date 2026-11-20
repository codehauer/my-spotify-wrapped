import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { viteSingleFile } from 'vite-plugin-singlefile'

// The production build is ONE self-contained HTML file (scripts, styles and fonts
// inlined) that the Python CLI fills with your statistics. It is written into the
// Python package so `spotify-wrapped web` works without Node.js.
export default defineConfig({
  plugins: [react(), viteSingleFile()],
  build: {
    outDir: '../src/spotify_wrapped/web_template',
    emptyOutDir: true,
    assetsInlineLimit: Number.MAX_SAFE_INTEGER,
  },
})
