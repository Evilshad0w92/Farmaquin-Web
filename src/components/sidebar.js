export function renderSidebar(){
    return `
        <aside class = "sidebar">
            <div class = "sidebar-logo">FarmaQuin</div>
            <nav class = "sidebar-nav">
                <button data-page = "dashboard">Inicio</button>
                <button data-page = "pos">POS</button>
                <button data-page = "returns">Devoluciones</button>
                <button data-page = "inventory">Inventario</button>
                <button data-page = "expenses">Gastos</button>
                <button data-page = "cashcut">Corte de Caja</button>
                <button data-page = "users">Usuarios</button>
                <button id = "logout-btn">Cerrar Sesion</button>
            </nav>
        </aside>
    `;
}