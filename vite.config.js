export default {
  // Configuración para exponer variables de entorno
  define: {
    'import.meta.env': JSON.stringify(process.env)
  }
}