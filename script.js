// Datos de productos
const productos = [
    {
        id: 1,
        nombre: "Paracetamol 500mg",
        descripcion: "Alivia el dolor y reduce la fiebre",
        precio: 5.99,
        categoria: "Analgésico"
    },
    {
        id: 2,
        nombre: "Ibuprofeno 400mg",
        descripcion: "Antiinflamatorio no esteroideo",
        precio: 7.50,
        categoria: "Antiinflamatorio"
    },
    {
        id: 3,
        nombre: "Omeprazol 20mg",
        descripcion: "Protector gástrico",
        precio: 9.75,
        categoria: "Digestivo"
    }
];

function cargarProductos() {
    const contenedor = document.getElementById('lista-productos');
    
    productos.forEach(producto => {
        const divProducto = document.createElement('div');
        divProducto.className = 'producto';
        divProducto.innerHTML = `
            <h3>${producto.nombre}</h3>
            <p>${producto.descripcion}</p>
            <p><strong>Precio:</strong> $${producto.precio.toFixed(2)}</p>
            <p><strong>Categoría:</strong> ${producto.categoria}</p>
        `;
        contenedor.appendChild(divProducto);
    });
}

// Cargar productos cuando la página se cargue
window.onload = cargarProductos;