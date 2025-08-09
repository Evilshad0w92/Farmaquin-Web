import { defineConfig } from 'vite';

export default defineConfig({
  build: {
    target: 'esnext',
    rollupOptions: {
      external: [
        'firebase',
        'firebase/app',
        'firebase/firestore',
        'firebase/auth'
      ],
      output: {
        manualChunks: {
          firebase: ['firebase']
        }
      }
    }
  },
  optimizeDeps: {
    exclude: [
      'firebase',
      'firebase/app',
      'firebase/firestore',
      'firebase/auth'
    ],
    include: [
      'https://www.gstatic.com/firebasejs/9.22.0/firebase-app.js',
      'https://www.gstatic.com/firebasejs/9.22.0/firebase-firestore.js',
      'https://www.gstatic.com/firebasejs/9.22.0/firebase-auth.js'
    ]
  }
});