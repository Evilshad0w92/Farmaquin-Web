// Versión compatible con producción usando CDN
const loadFirebase = async () => {
  const { initializeApp } = await import('https://www.gstatic.com/firebasejs/9.22.0/firebase-app.js');
  const { 
    getFirestore, collection, getDocs, addDoc, doc, updateDoc, 
    deleteDoc, query, where, orderBy, writeBatch, increment, Timestamp 
  } = await import('https://www.gstatic.com/firebasejs/9.22.0/firebase-firestore.js');
  const { 
    getAuth, signInWithEmailAndPassword, signOut, onAuthStateChanged 
  } = await import('https://www.gstatic.com/firebasejs/9.22.0/firebase-auth.js');

  const firebaseConfig = {
    apiKey: "tu-api-key",
    authDomain: "tu-proyecto.firebaseapp.com",
    projectId: "tu-proyecto",
    storageBucket: "tu-proyecto.appspot.com",
    messagingSenderId: "tu-messaging-sender-id",
    appId: "tu-app-id",
    measurementId: "tu-measurement-id"
  };

  const app = initializeApp(firebaseConfig);
  const db = getFirestore(app);
  const auth = getAuth(app);

  return {
    db,
    auth,
    // Firestore
    collection, getDocs, addDoc, doc, updateDoc, deleteDoc,
    query, where, orderBy, writeBatch, increment, Timestamp,
    // Auth
    signInWithEmailAndPassword, signOut, onAuthStateChanged
  };
};

export default loadFirebase;