import { getBoxes, getMe, loginRequest } from "../api/auth";
import { saveToken, saveUser } from "../utils/storage";

export async function renderLogin(container, onLogingSuccess){
    container.innerHTML = `
    <div class = "login-page">
        <div class = "login-card">
            <h1>Farmaquin</h1>
            <p class = "login-subtitle">Iniciar Sesión</p>
            <form id = "login-form" class = "login-form">
                
                <label>Usuario</label>
                <input type = "text" id = "username" required />
                
                <label>Contraseña</label>
                <input type = "password" id = "password" required />

                <label>Caja</label>
                <select id = "box_id" required>
                    <option value = "">Cargando cajas...</option>
                </select>
                <button type = "submit">Acceder</button>
                <p id = "login-error" class = "login-error"></p>
            </form>
        </div>
    </div>
    `;

    const form = document.getElementById("login-form");
    const errorEl = document.getElementById("login-error");
    
    //fill the box select with the db boxes
    const boxSelect = document.getElementById("box_id");
    try{
        const boxes = await getBoxes();
        boxSelect.innerHTML = `<option value = "">Selecciona una caja</option>`

        boxes.forEach((box) => {
            const option = document.createElement("option");
            option.value = box.box_id;
            option.textContent = box.box_name;
            boxSelect.appendChild(option);            
        });
    } catch (error) {
        boxSelect.innerHTML = `<option value = "">No se pudieron cargar las cajas</option>`;
        errorEl.textContent = error.message || "Error al cargar las cajas";
    }


    //Uses the data input from the form to try to validate the user when the submit button is clicked
    form.addEventListener("submit", async(e) => {
        e.preventDefault();
        errorEl.textContent = "";

        const username = document.getElementById("username").value.trim().toLowerCase();
        const password = document.getElementById("password").value.trim();
        const boxId = document.getElementById("box_id").value;

        try {
            const data = await loginRequest(username, password, boxId);
            saveToken(data.access_token);

            try {
                const meData = await getMe(data.access_token);
                console.log("ME RESPONSE:", meData);

                saveUser(meData.user);
                onLogingSuccess();
            } catch (meError) {
                if (typeof meError === "string") {
                    errorEl.textContent = meError;
                } else if (meError?.message && typeof meError.message === "string") {
                    errorEl.textContent = meError.message;
                } else {
                    errorEl.textContent = JSON.stringify(meError);
                }
            }

        } catch (loginError) {
            if (typeof loginError === "string") {
                errorEl.textContent = loginError;
            } else if (loginError?.message && typeof loginError.message === "string") {
                errorEl.textContent = loginError.message;
            } else {
                errorEl.textContent = JSON.stringify(loginError);
            }
        }
    });

}