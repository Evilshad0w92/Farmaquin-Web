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

// Configuración de Firebase
const firebaseConfig = {
  apiKey: "AIzaSyBAiT8MT5P0olLzNKVwQO31Vvo1wppwEFI",
  authDomain: "farmaquin-web.firebaseapp.com",
  projectId: "farmaquin-web",
  storageBucket: "farmaquin-web.appspot.com",
  messagingSenderId: "919280091257",
  appId: "1:919280091257:web:2062a9dfba9ec95d3d54a8",
  measurementId: "G-189PH4GZQ1"
};

// Inicialización de Firebase
const app = initializeApp(firebaseConfig);
const db = getFirestore(app);
const auth = getAuth(app);

// Exportación explícita de todos los módulos necesarios
export { 
  db,
  auth,
  // Firestore functions
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
  // Auth functions
  signInWithEmailAndPassword,
  signOut,
  onAuthStateChanged
};

// Para debug
console.log('Firebase configurado correctamente');
if (import.meta.env.MODE === 'development') {
  window.firebase = { db, auth };
}