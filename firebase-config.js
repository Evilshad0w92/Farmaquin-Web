// Configuración directa (reemplaza con tus valores reales)
const firebaseConfig = {
  apiKey: "AIzaSyBAiT8MT5P0olLzNKVwQO31Vvo1wppwEFI",
  authDomain: "farmaquin-web.firebaseapp.com",
  projectId: "farmaquin-web",
  storageBucket: "farmaquin-web.appspot.com",
  messagingSenderId: "919280091257",
  appId: "1:919280091257:web:2062a9dfba9ec95d3d54a8",
  measurementId: "G-189PH4GZQ1"
};

// Carga dinámica de Firebase
const loadFirebase = async () => {
  const { initializeApp } = await import('https://www.gstatic.com/firebasejs/9.22.0/firebase-app.js');
  const { 
    getFirestore, collection, getDocs, addDoc, doc, updateDoc, 
    deleteDoc, query, where, orderBy, writeBatch, increment, Timestamp 
  } = await import('https://www.gstatic.com/firebasejs/9.22.0/firebase-firestore.js');
  const { 
    getAuth, signInWithEmailAndPassword, signOut, onAuthStateChanged 
  } = await import('https://www.gstatic.com/firebasejs/9.22.0/firebase-auth.js');

  const app = initializeApp(firebaseConfig);
  const db = getFirestore(app);
  const auth = getAuth(app);

  return {
    db, auth,
    // Firestore
    collection, getDocs, addDoc, doc, updateDoc, deleteDoc,
    query, where, orderBy, writeBatch, increment, Timestamp,
    // Auth
    signInWithEmailAndPassword, signOut, onAuthStateChanged
  };
};

export default loadFirebase;