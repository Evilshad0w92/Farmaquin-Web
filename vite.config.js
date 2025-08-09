import { defineConfig } from 'vite'

export default defineConfig({
  optimizeDeps: {
    include: ['firebase/app', 'firebase/firestore', 'firebase/auth']
  }
})