from app.schemas.auth_schema import LoginRequest, TokenResponse, BoxResponse
from app.core.security.hashing import verify_password
from app.db.connection import get_conn
from app.core.security.jwt import create_access_token
from fastapi import APIRouter, HTTPException, status
import psycopg2
router = APIRouter(prefix="/auth", tags=["auth"])



@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    conn = get_conn()
    cursor = None
    if conn is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="No se pudo conectar a la base de datos")
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, password_hash, role_id, active, name FROM users WHERE username = %s", (request.username,))
        row = cursor.fetchone()

        cursor.execute("SELECT id, active FROM boxes WHERE id = %s", (request.box_id,))
        box_row = cursor.fetchone()

        if row is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado")
        
        elif row[4] is False:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario inactivo")   
        
        elif not verify_password(request.password, row[2]):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Contraseña incorrecta")
        
        elif box_row is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Caja no encontrada")
        
        elif box_row[1] is False:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Caja inactiva")
        
        else:
            payload = {
                "sub": str(row[0]),
                "username": row[1],
                "name": row[5],
                "role_id": row[3],
                "box_id": box_row[0]
            }       
            token = create_access_token(payload)
            return TokenResponse(access_token=token, token_type="bearer")
        
    except psycopg2.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al autenticar al usuario")
    
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error interno en login {str(e)}")
    
    finally:
        if cursor:
            cursor.close() 
        conn.close() 


@router.get("/boxes", response_model=list[BoxResponse])
async def getBoxes():
    conn = get_conn()
    cursor = None
    if conn is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="No se pudo conectar a la base de datos")
    try:
        cursor = conn.cursor()
        cursor.execute("""SELECT id, name
                          FROM boxes
                          WHERE ACTIVE = true
                          ORDER BY name""",)
        rows = cursor.fetchall()

        if not rows:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se encontraron cajas activas")
        
        return [BoxResponse(box_id=row[0],
                            box_name=row[1])
            for row in rows
        ]
        
    except psycopg2.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al autenticar al usuario")
    
    finally:
        if cursor:
            cursor.close() 
        conn.close() 