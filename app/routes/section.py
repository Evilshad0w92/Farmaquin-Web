from fastapi import APIRouter, HTTPException, status, Depends
from app.db.connection import get_conn
from app.schemas.provider_schema import ProviderCreate, ProviderResponse, ProviderUpdate
from app.schemas.section_schema import SectionResponse
from app.core.security.deps import get_current_user
import psycopg2

router = APIRouter(prefix="/sections", tags=["sections"])

@router.get("/", response_model=list[SectionResponse])
def get_sections(current_user: dict = Depends(get_current_user)):
    conn = get_conn()
    if conn is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al conectar a la base de datos")
    cursor = conn.cursor()

    try:
        cursor.execute("""SELECT id, name, description 
                          FROM sections 
                          ORDER BY name ASC""",)
        rows = cursor.fetchall()

        return [SectionResponse(id=row[0],
                                name=row[1],
                                description=row[2]) for row in rows]
    except psycopg2.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error de base de datos: {e}")
    finally:
        cursor.close()
        conn.close()