export function renderPOS(container){
    container.innerHTML = `
        <div class = "page">
            <h2>Punto de Venta</h2>
            <div class = "pos-layout">
                <div class = "pos-left card">
                    <label for = "barcode-input">Codigo de barras</label>
                    <input type = "text" id = "barcode-input" placeholder = "Escanea el producto"/>

                    <label for = "search-input">Buscar producto</label>
                    <input type = "text" id = "search-input" placeholder = "Buscar por nombre"/>

                    <div class = "pos-results" id = "pos-results">
                        <p>Sin resultados</p>
                    </div>
                </div>

                <div class = "pos-right card">
                    <h3>Carrito</h3>
                    <div class = "cart-items">
                        <p>No hay productos agregados</p>
                    </div>

                    <label for = "payment-method">Metodo de pago</label>
                    <select id = "payment-method">
                        <option value = "EFECTIVO" selected>Efectivo</option>
                        <option value = "TARJETA">Tarjeta</option>
                        <option value = "TRANSFERENCIA">Transferencia</option>
                    </select>

                    <label for = "total-input">Total</label>
                    <input type = "text" id = "total-input" class="money-input readonly-display" value = "0.00" readonly/>

                    <label for = "cash-input">Efectivo recibido</label>
                    <input type = "text" id = "cash-input" class="money-input" inputmode = "decimal" placeholder = "0.00"/>

                    <label for = "change-input">Cambio</label>
                    <input type = "text" id = "change-input" class="money-input readonly-display" value = "0.00" readonly/>

                    <div class = "pos-actions">
                        <button id = "btn-complete-sale">Aceptar</button>
                        <button id = "btn-clear-cart" class = "secondary">Limpiar</button>
                    </div>
                    
                    <p id = "pos-error" class = "login-error"></p>
                </div>
            </div>
        </div>
    `
}