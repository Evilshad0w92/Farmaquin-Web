import { getMe, loginRequest } from "../api/auth";
import { saveSession, saveToken, saveUser } from "../utils/storage";

export function renderLogin(container, onLogingSuccess){
    //Places all the elements on the form
    container.innerHTML = `
    <div class = "login-page">
        <div class = "login-card">
            <h1>Farmaquin</h1>
            <p class = "login-subtitled">Iniciar Sesión</p>
            <form id = "login-form" class = "login-form">
                
                <label>Usuario</label>
                <input type = "text" id = "username" required />
                
                <label>Contraseña</label>
                <input type = "password" id = "password" required />

                <label>Caja</label>
                <input type = "number" id = "box_id" required min = "1" />

                <button type = "submit">Acceder</button>
                <p id = "login-error" class = "login error"></p>
            </form>
        </div>
    </div>
    `;

    const form = document.getElementById("login-form");
    const errorE1 = document.getElementById("login-error");

    //Uses the data input from the form to try to validate the user when the submit button is clicked
    form.addEventListener("submit", async(e) => {
        e.preventDefault();
        errorE1.textContent = "";

        const username = document.getElementById("username").value.trim().toUpperCase();
        const password = document.getElementById("password").value.trim();
        const boxId = document.getElementById("box_id").value.trim();

        try{
            const data = await loginRequest(username, password, boxId);
            saveToken(loginData.access_token);
            const meData = await getMe();
            saveUser(meData.user);

            onLogingSuccess();
        } catch (error) {
            errorE1.textContent = error.message || "No se pudo iniciar sesión";
        }
    });

}