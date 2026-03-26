export function renderDashboard(container){
    container.innerHTML =`
        <div class = "page">
            <h2>Inicio</h2>
            <div class = "cards">
                <div class = "card">
                    <h3>POS</h3>
                    <p>Registrar ventas y cobrar</p>
                </div>
                <div class = "card">
                    <h3>Inventario</h3>
                    <p>Consultar y administrar productos</p>
                </div>
                <div class = "card">
                    <h3>Administracion</h3>
                    <p>Gastos, Cortes y usuarios</p>
                </div>
            </div>
        </div>
    `;
}