// Importaciones de Firebase (SDK modular)
import { initializeApp } from "firebase/app";
import { getFirestore } from "firebase/firestore";
import { getAuth } from "firebase/auth";

// Tu configuración de Firebase
const firebaseConfig = {
  apiKey: "AIzaSyBAiT8MT5P0olLzNKVwQO31Vvo1wppwEFI",
  authDomain: "farmaquin-web.firebaseapp.com",
  projectId: "farmaquin-web",
  storageBucket: "farmaquin-web.appspot.com",
  messagingSenderId: "919280091257",
  appId: "1:919280091257:web:2062a9dfba9ec95d3d54a8",
  measurementId: "G-189PH4GZQ1"
};

// Inicializa Firebase
const app = initializeApp(firebaseConfig);

// Inicializa los servicios que necesites
const db = getFirestore(app);
const auth = getAuth(app);

// Exporta los servicios que usarás en tu app
export { db, auth };