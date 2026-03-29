
//gets access token from data and storage it on localStorage to be able to use them on multiple windows
export function saveToken(token){
    localStorage.setItem("token", token);
}

//gets the user and storage it on localStorage
export function saveUser(user){
    localStorage.setItem("user", JSON.stringify(user));
}

//when called, returns the value of the item "token" from localStorage
export function getToken(){
    return localStorage.getItem("token");
}

//when called, gets the value of the item "user" from localStorage 
// and saves it on the variable raw
// if raw has something returns the JSON parsed, else returns null 
export function getUser(){
    const raw = localStorage.getItem("user");
    return raw ? JSON.parse(raw) : null;
}

//when called, clears the token and user from localStorage
export function clearSession(){
    localStorage.removeItem("token");
    localStorage.removeItem("user");
}