import { 
  auth,
  onAuthStateChanged,
  signInWithEmailAndPassword,
  signOut,
  db,
  collection,
  getDocs
} from './firebase-config.js';

// Estado global
const state = {
  user: null,
  products: [],
  elements: {
    // Autenticación
    loginSection: document.getElementById('login-section'),
    loginForm: document.getElementById('login-form'),
    loginEmail: document.getElementById('login-email'),
    loginPassword: document.getElementById('login-password'),
    authLink: document.getElementById('auth-link'),
    logoutBtn: document.getElementById('logout-btn'),
    
    // Navegación
    navInventario: document.getElementById('nav-inventario'),
    navVentas: document.getElementById('nav-ventas'),
    navRegistros: document.getElementById('nav-registros'),
    
    // Secciones
    inventarioSection: document.getElementById('inventario'),
    puntoVentaSection: document.getElementById('punto-venta'),
    registrosSection: document.getElementById('registros-ventas'),
    
    // Contenido
    productList: document.getElementById('lista-productos'),
    saleProductList: document.getElementById('sale-product-list'),
    salesList: document.getElementById('sales-list')
  }
};

// Verificación de elementos
function verifyElements() {
  for (const [key, element] of Object.entries(state.elements)) {
    if (!element && key !== 'products') {
      console.error(`Elemento no encontrado: ${key}`);
      return false;
    }
  }
  return true;
}

// Mostrar/ocultar secciones
function showSection(sectionId) {
  // Oculta todas las secciones
  state.elements.inventarioSection.classList.add('hidden');
  state.elements.puntoVentaSection.classList.add('hidden');
  state.elements.registrosSection.classList.add('hidden');
  state.elements.loginSection.classList.add('hidden');

  // Muestra la sección solicitada
  if (sectionId === 'inventario') {
    state.elements.inventarioSection.classList.remove('hidden');
    loadProducts();
  } else if (sectionId === 'ventas') {
    state.elements.puntoVentaSection.classList.remove('hidden');
    setupPOS();
  } else if (sectionId === 'registros') {
    state.elements.registrosSection.classList.remove('hidden');
    loadSales();
  } else if (sectionId === 'login') {
    state.elements.loginSection.classList.remove('hidden');
  }
}

// Cargar productos
async function loadProducts() {
  try {
    const querySnapshot = await getDocs(collection(db, 'productos'));
    state.products = querySnapshot.docs.map(doc => ({
      id: doc.id,
      ...doc.data()
    }));
    renderProducts();
  } catch (error) {
    console.error('Error cargando productos:', error);
  }
}

function renderProducts() {
  state.elements.productList.innerHTML = state.products
    .map(product => `
      <div class="product-card">
        <h3>${product.nombre}</h3>
        <p>Precio: $${product.precio}</p>
        <p>Stock: ${product.stock}</p>
      </div>
    `)
    .join('');
}

// Configuración de Punto de Venta
function setupPOS() {
  state.elements.saleProductList.innerHTML = state.products
    .map(product => `
      <div class="product-card">
        <h3>${product.nombre}</h3>
        <p>$${product.precio}</p>
        <button class="btn-add">Agregar</button>
      </div>
    `)
    .join('');
}

// Actualización de UI
function updateUI() {
  if (!verifyElements()) return;

  if (state.user) {
    state.elements.loginSection.classList.add('hidden');
    state.elements.authLink.classList.remove('hidden');
    showSection('inventario'); // Mostrar inventario por defecto
  } else {
    state.elements.loginSection.classList.remove('hidden');
    state.elements.authLink.classList.add('hidden');
  }
}

// Event listeners
function setupEventListeners() {
  if (!verifyElements()) return;

  // Login
  state.elements.loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      await signInWithEmailAndPassword(
        auth,
        state.elements.loginEmail.value,
        state.elements.loginPassword.value
      );
    } catch (error) {
      console.error('Error de login:', error);
      alert(error.message);
    }
  });

  // Logout
  state.elements.logoutBtn.addEventListener('click', async (e) => {
    e.preventDefault();
    try {
      await signOut(auth);
    } catch (error) {
      console.error('Error al cerrar sesión:', error);
    }
  });

  // Navegación
  state.elements.navInventario.addEventListener('click', (e) => {
    e.preventDefault();
    showSection('inventario');
  });

  state.elements.navVentas.addEventListener('click', (e) => {
    e.preventDefault();
    showSection('ventas');
  });

  state.elements.navRegistros.addEventListener('click', (e) => {
    e.preventDefault();
    showSection('registros');
  });
}

// Inicialización
function initApp() {
  console.log('Iniciando aplicación...');
  
  if (!verifyElements()) {
    console.error('Error: Elementos críticos no encontrados');
    return;
  }

  setupEventListeners();
  
  onAuthStateChanged(auth, (user) => {
    state.user = user;
    updateUI();
  });
}

// Iniciar cuando el DOM esté listo
if (document.readyState === 'complete') {
  initApp();
} else {
  document.addEventListener('DOMContentLoaded', initApp);
}