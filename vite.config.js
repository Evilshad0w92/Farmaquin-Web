import { defineConfig } from 'vite';

export default defineConfig({
  optimizeDeps: {
    include: [
      'firebase',
      'firebase/app',
      'firebase/firestore',
      'firebase/auth'
    ]
  },
  build: {
    commonjsOptions: {
      include: [/firebase/, /node_modules/]
    }
  }
});