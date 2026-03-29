import { apiFetch } from "./client";

//When called returns the list of active boxes
export async function getBoxes() {
    return await apiFetch("/auth/boxes",{ method: "GET"});    
}

//When called with username, password and boxId parameters calls the apiFecth funtion from app/src/api/client.js and return its reponse
export async function loginRequest(username, password, boxId) {
    const payload = {
        username,
        password,
        box_id: Number(boxId)
    };

    return await apiFetch("/auth/login", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(payload),
    });    
}

export async function getMe(token) {
    return await apiFetch("/users/me", {
        method: "GET",
        headers: {
            Authorization: `Bearer ${token}`
        }
    });
}