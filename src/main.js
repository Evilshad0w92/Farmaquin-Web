import "./styles/main.css";
import "./styles/login.css";
import "./styles/layout.css";

import { renderLogin } from "./pages/login";
import { renderDashboard } from "./pages/dashboard";
import { renderSidebar } from "./components/sidebar";
import { renderHeader } from "./components/header";
import { getToken, clearSession } from "./utils/storage";

const app = document.querySelector("#app");

//renders the page layout,by default: dashboard, and replace its content depending on the page sent 
function renderLayout(page = "dashboard"){
    app.innerHTML = `
        <div class = "app-shell">
            ${renderSidebar()}
            <div class = "main-area">
                ${renderHeader()}
                <main id = "page-content" class = "page-content"></main>
            </div>
        </div>
    `;

    const content = document.getElementById("page-content");

    if(page === "dashboard"){
        renderDashboard(content);
    }

    //Reads the button clicked with atribute data-page and calls renderLayout to refresh to the corresponding layout
    document.querySelectorAll("[data-page]").forEach((btn) => {
        btn.addEventListener("click", () => {
            renderLayout(btn.dataset.page);
        });
    });

    const logoutBtn = document.getElementById("logout-btn");
    logoutBtn?.addEventListener("click", () => {
        clearSession();
        initApp();
    });
}

function initApp(){
    const token = getToken();

    if(!token){
        renderLogin(app, () => renderLayout("dashboard"));
        return;
    }
}

initApp();