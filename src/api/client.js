//Storages the website URL
const API_BASE_URL = "https://farmaquin-backend.onrender.com";

//When called, gets the value of "token" from localStorage,
// creates the HTTP header object with a JSON adding the Content-Type and options (if existed)
// if token is not null storages it on headers.Authorization for JWT authorization
// if response is ok returns the data sent from backend
export async function apiFetch(endpoint, options = {}) {
    
    const token = localStorage.getItem("token");
    const headers = {
        "Content-Type": "applications/json",
        ...(options.headers || {})
    };
    
    if(token){
        headers.Authorization = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {...options, headers});
    const contentType = response.headers.get("content-type") || "";
    const data = contentType.includes("application/json") ? await response.json() : await response.text();
    
    if(!response.ok){
        throw new Error(data.detail || data.error || "Error en la peticion");
    }
    return data;
}