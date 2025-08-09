// Importación modificada
import loadFirebase from './firebase-config.js';

// Cambia todas tus llamadas a Firebase para usar el objeto cargado
let firebase;

async function init() {
  firebase = await loadFirebase();
  // Ahora usa firebase.db, firebase.auth, etc.
  setupEventListeners();
  setupAuth();
  updateYear();
}

// Ejemplo de modificación en las funciones
async function loadProducts(searchTerm = '') {
  try {
    let q;
    if (searchTerm) {
      q = firebase.query(
        firebase.collection(firebase.db, 'productos'),
        firebase.where('nombre', '>=', searchTerm),
        firebase.where('nombre', '<=', searchTerm + '\uf8ff')
      );
    } else {
      q = firebase.collection(firebase.db, 'productos');
    }

    const snapshot = await firebase.getDocs(q);
    state.products = snapshot.docs.map(doc => ({
      id: doc.id,
      ...doc.data()
    }));
    
    renderInventory();
    renderPOS();
  } catch (error) {
    console.error('Error cargando productos:', error);
  }
}