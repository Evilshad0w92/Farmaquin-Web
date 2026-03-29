//Storages the website URL
const API_BASE_URL = "https://farmaquin-backend.onrender.com";

//When called, gets the value of "token" from localStorage,
// creates the HTTP header object with a JSON adding the Content-Type and options (if existed)
// if token is not null storages it on headers.Authorization for JWT authorization
// if response is ok returns the data sent from backend
export async function apiFetch(endpoint, options = {}) {
    
    const token = localStorage.getItem("token");
    const headers = {...(options.headers || {})
    };
    
    if (!headers.Authorization && token) {
        headers.Authorization = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {...options, headers});
    const contentType = response.headers.get("content-type") || "";
    let data;
    
    if(contentType.includes("application/json")){ 
        data = await response.json()
    } else {
        await response.text();
    }

    if (!response.ok) {
        if (typeof data === "string") {
            throw new Error(data);
        }

        if (data && typeof data.detail === "string") {
            throw new Error(data.detail);
        }

        if (Array.isArray(data?.detail)) {
            throw new Error(JSON.stringify(data.detail));
        }

        if (data && typeof data.error === "string") {
            throw new Error(data.error);
        }

        throw new Error(JSON.stringify(data));
    }

    return data;
}