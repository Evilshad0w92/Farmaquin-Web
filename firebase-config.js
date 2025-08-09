// Importaciones estándar de Firebase v9 (modular)
import { initializeApp } from 'firebase/app';
import { 
  getFirestore,
  collection,
  getDocs,
  addDoc,
  doc,
  updateDoc,
  deleteDoc,
  query,
  where,
  orderBy,
  writeBatch,
  increment,
  Timestamp
} from 'firebase/firestore';
import { 
  getAuth,
  signInWithEmailAndPassword,
  signOut,
  onAuthStateChanged
} from 'firebase/auth';

// Configuración directa (reemplaza con tus valores si son diferentes)
const firebaseConfig = {
  apiKey: "AIzaSyBAiT8MT5P0olLzNKVwQO31Vvo1wppwEFI",
  authDomain: "farmaquin-web.firebaseapp.com",
  projectId: "farmaquin-web",
  storageBucket: "farmaquin-web.appspot.com",
  messagingSenderId: "919280091257",
  appId: "1:919280091257:web:2062a9dfba9ec95d3d54a8",
  measurementId: "G-189PH4GZQ1"
};

// Inicialización de servicios Firebase
const app = initializeApp(firebaseConfig);
const db = getFirestore(app);
const auth = getAuth(app);

// Exportación de todos los servicios y funciones necesarias
export {
  // Instancias principales
  app,
  db,
  auth,
  
  // Funciones de Firestore
  collection,
  getDocs,
  addDoc,
  doc,
  updateDoc,
  deleteDoc,
  query,
  where,
  orderBy,
  writeBatch,
  increment,
  Timestamp,
  
  // Funciones de Autenticación
  signInWithEmailAndPassword,
  signOut,
  onAuthStateChanged
};

// Opcional: Inicialización condicional de Analytics
if (typeof window !== 'undefined' && firebaseConfig.measurementId) {
  import('firebase/analytics')
    .then(({ getAnalytics }) => {
      const analytics = getAnalytics(app);
      console.log('Firebase Analytics inicializado');
    })
    .catch((error) => {
      console.warn('Error al cargar Firebase Analytics:', error);
    });
}

// Para debug en desarrollo
if (process.env.NODE_ENV === 'development') {
  console.log('Firebase configurado correctamente');
  window.firebase = { app, db, auth };
}