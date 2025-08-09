import { 
  db, auth, collection, getDocs, addDoc, doc, updateDoc, deleteDoc,
  query, where, orderBy, writeBatch, increment, Timestamp,  // <- Asegúrate de incluir todas
  signInWithEmailAndPassword, signOut, onAuthStateChanged
} from './firebase-config.js';

// Estado global
const state = {
  user: null,
  products: [],
  currentSale: [],
  sales: [],
  currentSection: null
};

// Elementos del DOM
const elements = {
  // Navegación
  navInventario: document.getElementById('nav-inventario'),
  navVentas: document.getElementById('nav-ventas'),
  navRegistros: document.getElementById('nav-registros'),
  logoutBtn: document.getElementById('logout-btn'),
  authLink: document.getElementById('auth-link'),

  // Autenticación
  loginSection: document.getElementById('login-section'),
  loginForm: document.getElementById('login-form'),
  loginEmail: document.getElementById('login-email'),
  loginPassword: document.getElementById('login-password'),

  // Inventario
  inventarioSection: document.getElementById('inventario'),
  productList: document.getElementById('lista-productos'),
  showAddProductBtn: document.getElementById('show-add-product'),
  addProductSection: document.getElementById('add-product-section'),
  productForm: document.getElementById('product-form'),
  cancelAddProductBtn: document.getElementById('cancel-add-product'),
  searchProductInput: document.getElementById('search-product'),

  // Modal Editar Producto
  editProductModal: document.getElementById('edit-product-modal'),
  editProductForm: document.getElementById('edit-product-form'),
  closeModalBtn: document.querySelector('.close-modal'),
  editProductId: document.getElementById('edit-product-id'),
  editProductName: document.getElementById('edit-product-name'),
  editProductPrice: document.getElementById('edit-product-price'),
  editProductStock: document.getElementById('edit-product-stock'),

  // Punto de Venta
  puntoVentaSection: document.getElementById('punto-venta'),
  saleProductList: document.getElementById('sale-product-list'),
  saleItems: document.getElementById('sale-items'),
  saleTotalAmount: document.getElementById('sale-total-amount'),
  completeSaleBtn: document.getElementById('complete-sale'),
  searchSaleProductInput: document.getElementById('search-sale-product'),

  // Registro de Ventas
  registrosSection: document.getElementById('registros-ventas'),
  salesList: document.getElementById('sales-list'),
  searchSaleInput: document.getElementById('search-sale'),

  // Footer
  currentYear: document.getElementById('current-year')
};

// Inicialización
async function init() {
  console.log('Iniciando aplicación...');
  setupEventListeners();
  setupAuth();
  updateYear();
}

// Autenticación
function setupAuth() {
  onAuthStateChanged(auth, (user) => {
    state.user = user;
    console.log('Estado autenticación:', user ? user.email : 'No autenticado');
    updateUI();
    
    if (user) {
      loadInitialData();
      showSection('inventario');
    } else {
      showSection('login');
    }
  });
}

async function loadInitialData() {
  await Promise.all([
    loadProducts(),
    loadSales()
  ]);
}

async function handleLogin(email, password) {
  try {
    await signInWithEmailAndPassword(auth, email, password);
    return true;
  } catch (error) {
    console.error('Error de autenticación:', error);
    alert('Error al iniciar sesión: ' + error.message);
    return false;
  }
}

async function handleLogout() {
  try {
    await signOut(auth);
  } catch (error) {
    console.error('Error al cerrar sesión:', error);
  }
}

// Gestión de Productos
async function loadProducts(searchTerm = '') {
  try {
    let q;
    if (searchTerm) {
      q = query(
        collection(db, 'productos'),
        where('nombre', '>=', searchTerm),
        where('nombre', '<=', searchTerm + '\uf8ff')
      );
    } else {
      q = collection(db, 'productos');
    }

    const snapshot = await getDocs(q);
    state.products = snapshot.docs.map(doc => ({
      id: doc.id,
      ...doc.data()
    }));
    
    renderInventory();
    renderPOS();
  } catch (error) {
    console.error('Error cargando productos:', error);
    alert('Error al cargar productos');
  }
}

async function addNewProduct(productData) {
  try {
    await addDoc(collection(db, 'productos'), {
      ...productData,
      fechaCreacion: new Date()
    });
    
    alert('Producto agregado correctamente');
    elements.addProductSection.classList.add('hidden');
    elements.productForm.reset();
    await loadProducts();
  } catch (error) {
    console.error('Error agregando producto:', error);
    alert('Error al agregar producto');
  }
}

async function updateProduct(e) {
  e.preventDefault();
  
  const productData = {
    nombre: elements.editProductName.value,
    precio: parseFloat(elements.editProductPrice.value),
    stock: parseInt(elements.editProductStock.value),
    fechaActualizacion: new Date()
  };

  try {
    await updateDoc(doc(db, 'productos', elements.editProductId.value), productData);
    elements.editProductModal.classList.add('hidden');
    await loadProducts();
    alert('Producto actualizado correctamente');
  } catch (error) {
    console.error('Error actualizando producto:', error);
    alert('Error al actualizar producto');
  }
}

async function deleteProduct(productId) {
  if (!confirm('¿Estás seguro de eliminar este producto? Esta acción no se puede deshacer.')) return;
  
  try {
    await deleteDoc(doc(db, 'productos', productId));
    await loadProducts();
    alert('Producto eliminado correctamente');
  } catch (error) {
    console.error('Error eliminando producto:', error);
    alert('Error al eliminar producto');
  }
}

function openEditModal(product) {
  elements.editProductId.value = product.id;
  elements.editProductName.value = product.nombre;
  elements.editProductPrice.value = product.precio;
  elements.editProductStock.value = product.stock;
  elements.editProductModal.classList.remove('hidden');
}

// Punto de Venta
function addProductToSale(productId) {
  const product = state.products.find(p => p.id === productId);
  if (!product) return;

  // Verificar stock
  if (product.stock <= 0) {
    alert('No hay stock disponible de este producto');
    return;
  }

  const existingItem = state.currentSale.find(item => item.id === productId);
  
  if (existingItem) {
    if (existingItem.quantity >= product.stock) {
      alert('No hay suficiente stock disponible');
      return;
    }
    existingItem.quantity += 1;
  } else {
    state.currentSale.push({
      ...product,
      quantity: 1
    });
  }

  renderSaleCart();
}

function removeFromSale(productId) {
  const itemIndex = state.currentSale.findIndex(item => item.id === productId);
  if (itemIndex !== -1) {
    if (state.currentSale[itemIndex].quantity > 1) {
      state.currentSale[itemIndex].quantity -= 1;
    } else {
      state.currentSale.splice(itemIndex, 1);
    }
    renderSaleCart();
  }
}

async function completeSale() {
  if (state.currentSale.length === 0) {
    alert('No hay productos en la venta');
    return;
  }

  try {
    // Crear operación por lotes
    const batch = writeBatch(db);
    
    // 1. Crear referencia para nuevo documento de venta
    const saleRef = doc(collection(db, 'ventas'));
    
    // Datos de la venta
    const saleData = {
      productos: state.currentSale,
      total: state.currentSale.reduce((sum, item) => sum + (item.precio * item.quantity), 0),
      fecha: Timestamp.now(),
      vendedor: state.user?.email || 'anonimo'
    };
    
    // 2. Agregar operación al batch
    batch.set(saleRef, saleData);
    
    // 3. Actualizar stock de cada producto
    state.currentSale.forEach(item => {
      const productRef = doc(db, 'productos', item.id);
      batch.update(productRef, {
        stock: increment(-item.quantity)
      });
    });
    
    // 4. Ejecutar batch
    await batch.commit();
    
    // Actualizar estado local
    state.currentSale = [];
    renderSaleCart();
    await loadProducts();
    await loadSales();
    
    alert('Venta registrada con éxito');
  } catch (error) {
    console.error('Error al registrar venta:', error);
    alert('Error al registrar venta: ' + error.message);
  }
}

// Registro de Ventas
async function loadSales(searchTerm = '') {
  try {
    let q = query(collection(db, 'ventas'), orderBy('fecha', 'desc'));
    
    if (searchTerm) {
      q = query(
        collection(db, 'ventas'),
        where('vendedor', '>=', searchTerm),
        where('vendedor', '<=', searchTerm + '\uf8ff'),
        orderBy('fecha', 'desc')
      );
    }

    const snapshot = await getDocs(q);
    state.sales = snapshot.docs.map(doc => ({
      id: doc.id,
      ...doc.data(),
      fecha: doc.data().fecha.toDate().toLocaleString()
    }));
    
    renderSales();
  } catch (error) {
    console.error('Error cargando ventas:', error);
  }
}

function viewSaleDetails(saleId) {
  const sale = state.sales.find(s => s.id === saleId);
  if (!sale) return;

  let detailsHTML = `
    <h3>Venta #${sale.id.slice(0, 8)}</h3>
    <p><strong>Fecha:</strong> ${sale.fecha}</p>
    <p><strong>Total:</strong> $${sale.total.toFixed(2)}</p>
    <p><strong>Vendedor:</strong> ${sale.vendedor}</p>
    <h4>Productos:</h4>
    <ul class="sale-details-list">
  `;
  
  sale.productos.forEach(product => {
    detailsHTML += `
      <li>
        <span>${product.nombre}</span>
        <span>Cantidad: ${product.quantity}</span>
        <span>Precio: $${product.precio.toFixed(2)}</span>
        <span>Subtotal: $${(product.precio * product.quantity).toFixed(2)}</span>
      </li>
    `;
  });
  
  detailsHTML += `</ul>`;
  
  // Puedes implementar un modal más elegante aquí
  const modal = document.createElement('div');
  modal.className = 'sale-details-modal';
  modal.innerHTML = `
    <div class="modal-content">
      <span class="close-details">&times;</span>
      ${detailsHTML}
    </div>
  `;
  
  modal.querySelector('.close-details').addEventListener('click', () => {
    document.body.removeChild(modal);
  });
  
  document.body.appendChild(modal);
}

// Renderizado
function renderInventory() {
  elements.productList.innerHTML = state.products.map(product => `
    <div class="product-card" data-id="${product.id}">
      <h3>${product.nombre}</h3>
      <p>Precio: $${product.precio?.toFixed(2) || '0.00'}</p>
      <p>Stock: ${product.stock || 0}</p>
      <div class="product-actions">
        <button class="btn-edit">Editar</button>
        <button class="btn-delete">Eliminar</button>
      </div>
    </div>
  `).join('');
}

function renderPOS() {
  elements.saleProductList.innerHTML = state.products.map(product => `
    <div class="product-card" data-id="${product.id}">
      <h3>${product.nombre}</h3>
      <p>$${product.precio?.toFixed(2) || '0.00'}</p>
      <p>Stock: ${product.stock || 0}</p>
      <button class="btn btn-primary btn-add-to-sale">Agregar</button>
    </div>
  `).join('');
}

function renderSaleCart() {
  elements.saleItems.innerHTML = state.currentSale.map(item => `
    <div class="sale-item" data-id="${item.id}">
      <span>${item.nombre} x${item.quantity}</span>
      <span>$${(item.precio * item.quantity).toFixed(2)}</span>
      <div class="sale-item-actions">
        <button class="btn-remove">-</button>
        <button class="btn-add">+</button>
      </div>
    </div>
  `).join('');

  const total = state.currentSale.reduce((sum, item) => sum + (item.precio * item.quantity), 0);
  elements.saleTotalAmount.textContent = total.toFixed(2);
}

function renderSales() {
  elements.salesList.innerHTML = state.sales.map(sale => `
    <div class="sale-record" data-id="${sale.id}">
      <h3>Venta #${sale.id.slice(0, 8)}</h3>
      <p><strong>Fecha:</strong> ${sale.fecha}</p>
      <p><strong>Total:</strong> $${sale.total.toFixed(2)}</p>
      <p><strong>Vendedor:</strong> ${sale.vendedor}</p>
      <button class="btn-view-details">Ver Detalles</button>
    </div>
  `).join('');
}

// Navegación
function showSection(sectionId) {
  // Ocultar todas las secciones
  elements.loginSection.classList.add('hidden');
  elements.inventarioSection.classList.add('hidden');
  elements.puntoVentaSection.classList.add('hidden');
  elements.registrosSection.classList.add('hidden');
  elements.addProductSection.classList.add('hidden');

  // Mostrar la sección solicitada
  if (sectionId === 'login') {
    elements.loginSection.classList.remove('hidden');
  } else if (sectionId === 'inventario') {
    elements.inventarioSection.classList.remove('hidden');
  } else if (sectionId === 'ventas') {
    elements.puntoVentaSection.classList.remove('hidden');
  } else if (sectionId === 'registros') {
    elements.registrosSection.classList.remove('hidden');
  }

  state.currentSection = sectionId;
}

// Event Listeners
function setupEventListeners() {
  // Navegación
  elements.navInventario?.addEventListener('click', (e) => {
    e.preventDefault();
    showSection('inventario');
  });

  elements.navVentas?.addEventListener('click', (e) => {
    e.preventDefault();
    showSection('ventas');
  });

  elements.navRegistros?.addEventListener('click', (e) => {
    e.preventDefault();
    showSection('registros');
  });

  elements.logoutBtn?.addEventListener('click', (e) => {
    e.preventDefault();
    handleLogout();
  });

  // Autenticación
  elements.loginForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = elements.loginEmail.value;
    const password = elements.loginPassword.value;
    await handleLogin(email, password);
  });

  // Inventario
  elements.showAddProductBtn?.addEventListener('click', () => {
    elements.addProductSection.classList.remove('hidden');
  });

  elements.cancelAddProductBtn?.addEventListener('click', () => {
    elements.addProductSection.classList.add('hidden');
    elements.productForm.reset();
  });

  elements.productForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const productData = {
      nombre: document.getElementById('producto-nombre').value,
      precio: parseFloat(document.getElementById('producto-precio').value),
      stock: parseInt(document.getElementById('producto-stock').value)
    };
    await addNewProduct(productData);
  });

  elements.searchProductInput?.addEventListener('input', (e) => {
    loadProducts(e.target.value.trim().toLowerCase());
  });

  // Editar/Eliminar productos
  elements.productList?.addEventListener('click', (e) => {
    const productCard = e.target.closest('.product-card');
    if (!productCard) return;
    
    const productId = productCard.dataset.id;
    const product = state.products.find(p => p.id === productId);
    
    if (e.target.classList.contains('btn-edit')) {
      openEditModal(product);
    } else if (e.target.classList.contains('btn-delete')) {
      deleteProduct(productId);
    }
  });

  // Modal edición
  elements.editProductForm?.addEventListener('submit', updateProduct);
  elements.closeModalBtn?.addEventListener('click', () => {
    elements.editProductModal.classList.add('hidden');
  });
  
  elements.editProductModal?.addEventListener('click', (e) => {
    if (e.target === elements.editProductModal) {
      elements.editProductModal.classList.add('hidden');
    }
  });

  // Punto de Venta
  elements.saleProductList?.addEventListener('click', (e) => {
    if (e.target.classList.contains('btn-add-to-sale')) {
      const productCard = e.target.closest('.product-card');
      if (productCard) {
        addProductToSale(productCard.dataset.id);
      }
    }
  });

  elements.saleItems?.addEventListener('click', (e) => {
    const saleItem = e.target.closest('.sale-item');
    if (!saleItem) return;
    
    const productId = saleItem.dataset.id;
    
    if (e.target.classList.contains('btn-remove')) {
      removeFromSale(productId);
    } else if (e.target.classList.contains('btn-add')) {
      addProductToSale(productId);
    }
  });

  elements.completeSaleBtn?.addEventListener('click', completeSale);

  elements.searchSaleProductInput?.addEventListener('input', (e) => {
    const searchTerm = e.target.value.trim().toLowerCase();
    const products = elements.saleProductList.querySelectorAll('.product-card');
    
    products.forEach(product => {
      const name = product.querySelector('h3').textContent.toLowerCase();
      product.style.display = name.includes(searchTerm) ? 'block' : 'none';
    });
  });

  // Registro de Ventas
  elements.salesList?.addEventListener('click', (e) => {
    if (e.target.classList.contains('btn-view-details')) {
      const saleRecord = e.target.closest('.sale-record');
      if (saleRecord) {
        viewSaleDetails(saleRecord.dataset.id);
      }
    }
  });

  elements.searchSaleInput?.addEventListener('input', (e) => {
    loadSales(e.target.value.trim().toLowerCase());
  });
}

// UI Helpers
function updateUI() {
  if (state.user) {
    elements.authLink.classList.remove('hidden');
    elements.loginSection.classList.add('hidden');
  } else {
    elements.authLink.classList.add('hidden');
    elements.loginSection.classList.remove('hidden');
  }
}

function updateYear() {
  elements.currentYear.textContent = new Date().getFullYear();
}

// Iniciar aplicación
document.addEventListener('DOMContentLoaded', init);

// Debugging
if (import.meta.env.MODE === 'development') {
  window.app = {
    state,
    db,
    auth,
    helpers: {
      loadProducts,
      loadSales,
      addNewProduct,
      completeSale
    }
  };
}