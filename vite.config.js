import { defineConfig } from 'vite';

export default defineConfig({
  build: {
    target: 'esnext',
    rollupOptions: {
      external: [
        // Elimina todas las referencias a firebase aquí
        // Solo mantén otras dependencias externas si son necesarias
      ],
      output: {
        manualChunks: (id) => {
          // Elimina cualquier referencia a firebase en manualChunks
          if (id.includes('node_modules')) {
            return 'vendor';
          }
        }
      }
    }
  },
  optimizeDeps: {
    exclude: [
      // Elimina las exclusiones de firebase
    ]
  }
});