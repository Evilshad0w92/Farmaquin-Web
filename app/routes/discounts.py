from fastapi import APIRouter, HTTPException, status, Depends
from app.db.connection import get_conn
from app.core.security.deps import get_current_user
from pydantic import BaseModel
from typing import Optional
from datetime import date
import psycopg2

router = APIRouter(prefix="/discounts", tags=["discounts"])


class DiscountCreate(BaseModel):
    name: str
    type: str          # "PORCENTAJE" | "FIJO"
    value: float
    start_date: date
    end_date: date
    product_id: Optional[int] = None
    active: bool = True


class DiscountUpdate(BaseModel):
    name: str
    type: str
    value: float
    start_date: date
    end_date: date
    product_id: Optional[int] = None
    active: bool


@router.get("")
def list_discounts(current_user: dict = Depends(get_current_user)):
    conn = get_conn()
    if conn is None:
        raise HTTPException(status_code=500, detail="Error al conectar a la base de datos")
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT d.id, d.name, d.type, d.value, d.start_date, d.end_date, d.active,
                   d.product_id, p.name AS product_name
            FROM discounts d
            LEFT JOIN products p ON p.id = d.product_id
            ORDER BY d.active DESC, d.name
        """)
        rows = cursor.fetchall()
        return [
            {
                "id":           row[0],
                "name":         row[1],
                "type":         row[2],
                "value":        str(row[3]),
                "start_date":   str(row[4]),
                "end_date":     str(row[5]),
                "active":       row[6],
                "product_id":   row[7],
                "product_name": row[8],
            }
            for row in rows
        ]
    except psycopg2.Error as e:
        raise HTTPException(status_code=500, detail=f"Error de base de datos: {e}")
    finally:
        cursor.close()
        conn.close()


@router.post("", status_code=status.HTTP_201_CREATED)
def create_discount(data: DiscountCreate, current_user: dict = Depends(get_current_user)):
    if data.value <= 0:
        raise HTTPException(status_code=400, detail="El valor debe ser mayor a cero")
    if data.type == "PORCENTAJE" and data.value > 100:
        raise HTTPException(status_code=400, detail="El porcentaje no puede ser mayor a 100")
    if data.end_date < data.start_date:
        raise HTTPException(status_code=400, detail="La fecha de fin no puede ser anterior a la de inicio")

    conn = get_conn()
    if conn is None:
        raise HTTPException(status_code=500, detail="Error al conectar a la base de datos")
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO discounts (name, type, value, start_date, end_date, product_id, active)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (data.name, data.type, data.value, data.start_date, data.end_date, data.product_id, data.active))
        row = cursor.fetchone()
        conn.commit()
        return {"id": row[0], **data.model_dump()}
    except psycopg2.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error de base de datos: {e}")
    finally:
        cursor.close()
        conn.close()


@router.put("/{discount_id}")
def update_discount(discount_id: int, data: DiscountUpdate, current_user: dict = Depends(get_current_user)):
    if data.value <= 0:
        raise HTTPException(status_code=400, detail="El valor debe ser mayor a cero")
    if data.type == "PORCENTAJE" and data.value > 100:
        raise HTTPException(status_code=400, detail="El porcentaje no puede ser mayor a 100")
    if data.end_date < data.start_date:
        raise HTTPException(status_code=400, detail="La fecha de fin no puede ser anterior a la de inicio")

    conn = get_conn()
    if conn is None:
        raise HTTPException(status_code=500, detail="Error al conectar a la base de datos")
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE discounts
            SET name=%s, type=%s, value=%s, start_date=%s, end_date=%s, product_id=%s, active=%s
            WHERE id=%s
        """, (data.name, data.type, data.value, data.start_date, data.end_date, data.product_id, data.active, discount_id))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Descuento no encontrado")
        conn.commit()
        return {"ok": True}
    except HTTPException:
        conn.rollback()
        raise
    except psycopg2.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error de base de datos: {e}")
    finally:
        cursor.close()
        conn.close()


@router.delete("/{discount_id}")
def delete_discount(discount_id: int, current_user: dict = Depends(get_current_user)):
    conn = get_conn()
    if conn is None:
        raise HTTPException(status_code=500, detail="Error al conectar a la base de datos")
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE discounts SET active = false WHERE id = %s", (discount_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Descuento no encontrado")
        conn.commit()
        return {"ok": True}
    except HTTPException:
        conn.rollback()
        raise
    except psycopg2.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error de base de datos: {e}")
    finally:
        cursor.close()
        conn.close()
