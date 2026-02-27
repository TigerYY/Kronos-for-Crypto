import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  server: {
    host: '::',   // 同时监听 IPv4 (0.0.0.0) 和 IPv6 (::1)，兼容 macOS localhost 解析
    port: 5173,
  },
})
