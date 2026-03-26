import { getUser } from "../utils/storage";

export function renderHeader(){
    const user = getUser();

    return `
        <header class = "topbar">
            <div>
                <strong>${user?.username || "Usuario"}</strong>
            </div>
            <div>ERP / POS Farmacia</div>
        </header>
    `;
}