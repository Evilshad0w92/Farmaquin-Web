import psycopg2
from psycopg2 import errors
from uuid import UUID
from fastapi import APIRouter, HTTPException, status
from fastapi import Depends
from app.db.connection import get_conn
from app.schemas.user_schema import UserCreate
from app.core.security.hashing import hash_password
from app.core.security.deps import get_current_user, requires_role


router = APIRouter()

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, current_user: dict = Depends(requires_role([2]))):

    hashed = hash_password(user.password)
    cursor = None
    conn = get_conn()
    if conn is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="No se pudo conectar a la base de datos")

    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username,name, role_id, password_hash) " \
                       "VALUES (%s,%s, %s, %s) " \
                       "RETURNING id, username, role_id, active,name", 
                       (user.username, user.name, user.role, hashed))
        row = cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al crear el usuario")  
        conn.commit()   
        return { 
            "id": row[0],
            "username": row[1],   
            "role_id": row[2],
            "active": row[3],
            "name": row[4]
            
        } 
    except errors.UniqueViolation:
        conn.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El nombre de usuario ya existe")
    
    finally:   
        if cursor:
            cursor.close()
        conn.close() 

@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return {"message": "Usuario autenticado", "user": current_user}  



@router.get("/{user_id}")
async def get_user(user_id: UUID):
    conn = get_conn()
    cursor = None
    if conn is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="No se pudo conectar a la base de datos")
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, role_id, active,name FROM users WHERE id = %s ", (str(user_id),))
        row = cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
        else:
            return {"message": "Usuario obtenido correctamente", "user": {
                "id": row[0],  
                "username": row[1],
                "role_id": row[2],
                "active": row[3],
                "name": row[4]
            }}

    except psycopg2.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al obtener el usuario")    
          
    finally:
        if cursor:
            cursor.close()
        conn.close()



@router.put("/{user_id}")
async def update_user(user_id: UUID):
    return {"mensaje": f"Usuario {user_id} actualizado"}    

@router.delete("/{user_id}")
async def delete_user(user_id: UUID):
    return {"mensaje": f"Usuario {user_id} eliminado"}   

