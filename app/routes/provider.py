from fastapi import APIRouter, HTTPException, status, Depends
from app.db.connection import get_conn
from app.schemas.provider_schema import ProviderCreate, ProviderResponse, ProviderUpdate
from app.core.security.deps import get_current_user
import psycopg2

router = APIRouter(prefix="/providers", tags=["providers"])

# This route is for creating a new provider and returns the created provider with its id and details.
@router.post("/", response_model=ProviderResponse, status_code=status.HTTP_201_CREATED)
def create_provider(data: ProviderCreate, current_user: dict = Depends(get_current_user)):
    conn = get_conn()
    if conn is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al conectar a la base de datos")       
    cursor = conn.cursor()

    try:
        cursor.execute("""INSERT INTO providers (name, contact, email, phone) 
                          VALUES (%s, %s, %s, %s) RETURNING id, name, contact, email, phone""", 
                       (data.name.strip(), data.contact.strip() if data.contact else None, data.email.strip() if data.email else None, data.phone.strip() if data.phone else None))
        row = cursor.fetchone()

        if row is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al crear el proveedor")
        conn.commit()

        return ProviderResponse(id=row[0],
                                name=row[1],
                                contact=row[2],
                                email=row[3],
                                phone=row[4])
    except psycopg2.Error as e:
        conn.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail= f"Error de base de datos: {e}")  
    except HTTPException as e:
        raise e
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al crear proveedor")
    finally:
        cursor.close()
        conn.close()

# This route returns an array of providers with their details.
@router.get("/", response_model=list[ProviderResponse])
def get_providers(current_user: dict = Depends(get_current_user)):
    conn = get_conn()
    if conn is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al conectar a la base de datos")
    cursor = conn.cursor()

    try:
        cursor.execute("""SELECT id, name, contact, email, phone 
                          FROM providers 
                          ORDER BY name ASC""",)
        rows = cursor.fetchall()

        return [ProviderResponse(id=row[0],
                                name=row[1],
                                contact=row[2],
                                email=row[3],
                                phone=row[4]) for row in rows]
    except psycopg2.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error de base de datos: {e}")
    finally:
        cursor.close()
        conn.close()

# This route returns a provider with its details by its id
@router.get("/{provider_id}", response_model=ProviderResponse)     
def get_provider(provider_id: int, current_user: dict = Depends(get_current_user)):
    conn = get_conn()
    if conn is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al conectar a la base de datos")
    cursor = conn.cursor()

    try:
        cursor.execute("""SELECT id, name, contact, email, phone 
                          FROM providers 
                          WHERE id = %s""", (provider_id,))
        row = cursor.fetchone()

        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proveedor no encontrado")

        return ProviderResponse(id=row[0],
                                name=row[1],
                                contact=row[2],
                                email=row[3],
                                phone=row[4])
    except psycopg2.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error de base de datos: {e}")
    finally:
        cursor.close()
        conn.close()   

# This route is allows changing the name, contact, email and phone of the provider and returns the updated provider with its details.
@router.put("/{provider_id}", response_model=ProviderResponse)
def update_provider(provider_id: int, data: ProviderUpdate, current_user: dict = Depends
(get_current_user)):
    conn = get_conn()
    if conn is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al conectar a la base de datos")
    cursor = conn.cursor()

    try:
        cursor.execute("""UPDATE providers 
                          SET name = %s, contact = %s, email = %s, phone = %s 
                          WHERE id = %s RETURNING id, name, contact, email, phone""", 
                       (data.name.strip(), data.contact.strip() if data.contact else None, data.email.strip() if data.email else None, data.phone.strip() if data.phone else None, provider_id))
        row = cursor.fetchone()

        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proveedor no encontrado")
        conn.commit()

        return ProviderResponse(id=row[0],
                                name=row[1],
                                contact=row[2],
                                email=row[3],
                                phone=row[4])
    except psycopg2.Error as e:
        conn.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error de base de datos: {e}")
    except HTTPException as e:
        raise e
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al actualizar proveedor")
    finally:
        cursor.close()
        conn.close()

# This route allows deleting a provider by its id
@router.delete("/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_provider(provider_id: int, current_user: dict = Depends(get_current_user)):
    conn = get_conn()
    if conn is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al conectar a la base de datos")
    cursor = conn.cursor()

    try:
        cursor.execute("""DELETE 
                          FROM providers 
                          WHERE id = %s RETURNING id""", (provider_id,))
        row = cursor.fetchone()

        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proveedor no encontrado")
        conn.commit()
        return
    except psycopg2.Error as e:
        conn.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error de base de datos: {e}")
    except HTTPException as e:
        raise e
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al eliminar proveedor")
    finally:
        cursor.close()
        conn.close()