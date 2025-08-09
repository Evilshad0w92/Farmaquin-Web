import { initializeApp } from "firebase/app";
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
} from "firebase/firestore";
import { 
  getAuth,
  signInWithEmailAndPassword,
  signOut,
  onAuthStateChanged
} from "firebase/auth";

// Configuración de Firebase (usa variables de entorno Vite)
const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
  measurementId: import.meta.env.VITE_FIREBASE_MEASUREMENT_ID
};

// Inicialización de Firebase
const app = initializeApp(firebaseConfig);
const db = getFirestore(app);
const auth = getAuth(app);

// Inicialización condicional de Analytics solo si está configurado
let analytics;
if (typeof window !== 'undefined' && firebaseConfig.measurementId) {
  import("firebase/analytics").then(({ getAnalytics }) => {
    analytics = getAnalytics(app);
  }).catch(error => {
    console.warn("Firebase Analytics no pudo cargarse:", error);
  });
}

// Exporta todas las funciones necesarias
export {
  app,
  db,
  auth,
  analytics,
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
  // Funciones de Auth
  signInWithEmailAndPassword,
  signOut,
  onAuthStateChanged
};

// Para depuración en desarrollo
if (import.meta.env.MODE === 'development') {
  console.log('Firebase configurado correctamente');
  console.log('App:', app);
  console.log('Database:', db);
  console.log('Auth:', auth);
}