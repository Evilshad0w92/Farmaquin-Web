import { apiFetch } from "./client";

//When called with username, password and boxId parameters calls the apiFecth funtion from app/src/api/client.js
// and return its reponse
export async function loginRequest(username, password, boxId) {
    return await apiFetch("/auth/login",{
        method: "POST",
        body: JSON.stringify({username, 
                              password, 
                              boxId: Number(boxId)}),
        headers: {"Content-Type": "application/json"},
    });    
}

export async function getMe() {
    return await apiFetch("/user/me", {
        method: "GET",
    })
}