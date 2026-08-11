import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  base: '/',
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://127.0.0.1:18000',
      '/health': 'http://127.0.0.1:18000',
    },
  },
})
