import { 
    db, 
    auth, 
    signInWithEmailAndPassword, 
    signOut,
    onAuthStateChanged,
    collection,
    addDoc,
    getDocs,
    query,
    where
} from './firebase.js';

// Elementos del DOM
const elementos = {
    listaProductos: document.getElementById('lista-productos'),
    buscarInput: document.getElementById('buscar-producto'),
    loginContainer: document.getElementById('login-container'),
    adminPanel: document.getElementById('admin-panel'),
    loginEmail: document.getElementById('login-email'),
    loginPassword: document.getElementById('login-password'),
    productoNombre: document.getElementById('producto-nombre'),
    productoDescripcion: document.getElementById('producto-descripcion'),
    productoPrecio: document.getElementById('producto-precio'),
    productoCategoria: document.getElementById('producto-categoria'),
    carritoContainer: document.getElementById('carrito-container'),
    itemsCarrito: document.getElementById('items-carrito'),
    totalCarrito: document.getElementById('total-carrito'),
    authLink: document.getElementById('auth-link')
};

// Estado del carrito
let carrito = [];

// Cargar productos desde Firestore
async function cargarProductos() {
    try {
        elementos.listaProductos.innerHTML = '<p>Cargando productos...</p>';
        
        const querySnapshot = await getDocs(collection(db, "productos"));
        elementos.listaProductos.innerHTML = '';
        
        querySnapshot.forEach((doc) => {
            renderizarProducto(doc.data());
        });
    } catch (error) {
        console.error("Error al cargar productos: ", error);
        elementos.listaProductos.innerHTML = '<p>Error al cargar productos</p>';
    }
}

// Renderizar un producto en el DOM
function renderizarProducto(producto) {
    const divProducto = document.createElement('div');
    divProducto.className = 'producto';
    divProducto.innerHTML = `
        <h3>${producto.nombre}</h3>
        <p>${producto.descripcion}</p>
        <p><strong>Precio:</strong> $${producto.precio.toFixed(2)}</p>
        <p><strong>Categoría:</strong> ${producto.categoria}</p>
        <button class="btn-agregar" data-id="${producto.id}">Añadir al carrito</button>
    `;
    elementos.listaProductos.appendChild(divProducto);
    
    // Agregar evento al botón
    divProducto.querySelector('.btn-agregar').addEventListener('click', () => {
        agregarProductoAlCarrito(producto);
    });
}

// Buscar productos
async function buscarProductos() {
    const termino = elementos.buscarInput.value.toLowerCase();
    if (!termino) return cargarProductos();
    
    try {
        elementos.listaProductos.innerHTML = '<p>Buscando productos...</p>';
        
        const q = query(
            collection(db, "productos"),
            where("nombre", ">=", termino),
            where("nombre", "<=", termino + '\uf8ff')
        );
        
        const querySnapshot = await getDocs(q);
        elementos.listaProductos.innerHTML = '';
        
        querySnapshot.forEach((doc) => {
            renderizarProducto(doc.data());
        });
    } catch (error) {
        console.error("Error al buscar productos: ", error);
        elementos.listaProductos.innerHTML = '<p>Error al buscar productos</p>';
    }
}

// Manejo de autenticación
function setupAuth() {
    onAuthStateChanged(auth, (user) => {
        if (user) {
            // Usuario logueado
            elementos.loginContainer.style.display = 'none';
            elementos.adminPanel.style.display = 'block';
            elementos.authLink.style.display = 'none';
        } else {
            // No hay usuario
            elementos.loginContainer.style.display = 'block';
            elementos.adminPanel.style.display = 'none';
            elementos.authLink.style.display = 'block';
        }
    });
}

async function iniciarSesion() {
    try {
        await signInWithEmailAndPassword(
            auth,
            elementos.loginEmail.value,
            elementos.loginPassword.value
        );
    } catch (error) {
        alert(`Error al iniciar sesión: ${error.message}`);
    }
}

function cerrarSesion() {
    signOut(auth);
}

// Administración de productos
async function agregarProducto() {
    try {
        const producto = {
            nombre: elementos.productoNombre.value,
            descripcion: elementos.productoDescripcion.value,
            precio: parseFloat(elementos.productoPrecio.value),
            categoria: elementos.productoCategoria.value,
            fechaCreacion: new Date()
        };
        
        await addDoc(collection(db, "productos"), producto);
        alert("Producto agregado correctamente");
        cargarProductos();
        
        // Limpiar formulario
        elementos.productoNombre.value = '';
        elementos.productoDescripcion.value = '';
        elementos.productoPrecio.value = '';
        elementos.productoCategoria.value = '';
    } catch (error) {
        alert(`Error al agregar producto: ${error.message}`);
    }
}

// Carrito de compras
function agregarProductoAlCarrito(producto) {
    carrito.push(producto);
    actualizarCarrito();
}

function actualizarCarrito() {
    elementos.itemsCarrito.innerHTML = '';
    let total = 0;
    
    carrito.forEach((producto, index) => {
        const divItem = document.createElement('div');
        divItem.className = 'item-carrito';
        divItem.innerHTML = `
            <span>${producto.nombre}</span>
            <span>$${producto.precio.toFixed(2)}</span>
            <button class="btn-eliminar" data-index="${index}">X</button>
        `;
        elementos.itemsCarrito.appendChild(divItem);
        total += producto.precio;
        
        // Agregar evento al botón eliminar
        divItem.querySelector('.btn-eliminar').addEventListener('click', () => {
            eliminarDelCarrito(index);
        });
    });
    
    elementos.totalCarrito.textContent = total.toFixed(2);
}

function eliminarDelCarrito(index) {
    carrito.splice(index, 1);
    actualizarCarrito();
}

async function finalizarCompra() {
    if (carrito.length === 0) {
        alert("El carrito está vacío");
        return;
    }
    
    try {
        await addDoc(collection(db, "ventas"), {
            productos: carrito,
            total: carrito.reduce((sum, p) => sum + p.precio, 0),
            fecha: new Date(),
            usuario: auth.currentUser ? auth.currentUser.email : "invitado"
        });
        
        alert("Compra realizada con éxito");
        carrito = [];
        actualizarCarrito();
    } catch (error) {
        alert(`Error al finalizar compra: ${error.message}`);
    }
}

// Event Listeners
document.addEventListener('DOMContentLoaded', () => {
    setupAuth();
    cargarProductos();
    
    // Botón de búsqueda
    document.querySelector('.busqueda button').addEventListener('click', buscarProductos);
    
    // Formulario de producto
    document.querySelector('.formulario-producto button').addEventListener('click', agregarProducto);
    
    // Botón de login
    document.querySelector('#login-container button').addEventListener('click', iniciarSesion);
    
    // Botón de logout
    document.querySelector('#admin-panel button:last-child').addEventListener('click', cerrarSesion);
    
    // Botón de finalizar compra
    document.querySelector('#carrito-container button').addEventListener('click', finalizarCompra);
});