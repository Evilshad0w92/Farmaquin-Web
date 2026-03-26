from typing import Iterable
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.security.jwt import decode_access_token

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) :
    token = credentials.credentials
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido o expirado")
    return payload

def requires_role(allowed_roles: Iterable[int]):
    def _role_guard(current_user: dict = Depends(get_current_user)):
        role_id = current_user.get("role_id")
        if not isinstance(role_id, int): 
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El token no contiene un role_id válido")
        if role_id == 1:
            return current_user
        if role_id not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permiso para acceder a este recurso")        
        return current_user
    return _role_guard
