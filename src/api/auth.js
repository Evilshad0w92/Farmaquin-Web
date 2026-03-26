import { apiFetch } from "./client";

//When called with username and password parameters calls the apiFecth funtion from app/src/api/client.js
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