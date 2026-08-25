import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // 0.0.0.0 (not 127.0.0.1) so the dev server also accepts
    // connections from other devices on the Tailscale network, e.g.
    // a phone hitting this PC's Tailscale IP.
    host: '0.0.0.0',
    port: 5173,
  },
})
