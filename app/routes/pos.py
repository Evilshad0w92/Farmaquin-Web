from app.core.security.deps import get_current_user
from app.db.connection import get_conn
from fastapi import APIRouter, HTTPException, status, Depends
from app.services.product_service import get_product_by_barcode, search_product
from decimal import Decimal, ROUND_HALF_UP

router = APIRouter(prefix="/pos", tags=["pos"])

@router.get("/scan")
def scan(barcode: str, quantity: int = 1, current_user: dict = Depends(get_current_user)):
    conn = get_conn()
    if conn is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al conectar a la base de datos")       
    cursor = conn.cursor()
    
    try:
        box_id = current_user["box_id"]
        product = get_product_by_barcode(barcode, quantity, cursor, box_id)
        unit_price = product["price_sell"]
        discount_value = product["discount_value"]
        discount_amount = Decimal(0)

        if not isinstance(unit_price, Decimal):
            unit_price = Decimal(str(unit_price))
        if not isinstance(discount_value, Decimal):
            discount_value = Decimal(str(discount_value))

        q = Decimal("0.01")
        if product["discount_type"] == "PORCENTAJE":
            discount_amount = unit_price * (product["discount_value"] / Decimal("100"))
        elif product["discount_type"] == "FIJO":
            discount_amount = discount_value
        
        discount_amount = discount_amount.quantize(q, rounding=ROUND_HALF_UP)

        unit_price_final = unit_price - discount_amount
        line_total = unit_price_final * quantity

        
        unit_price = unit_price.quantize(q, rounding=ROUND_HALF_UP)
        line_total = line_total.quantize(q, rounding=ROUND_HALF_UP)
        unit_price_final = unit_price_final.quantize(q, rounding=ROUND_HALF_UP)

        return {
            "id": product["id"],
            "barcode": barcode,
            "name": product["name"],
            "formula": product["formula"],
            "stock": product["stock"],
            "quantity": quantity,
            "unit_price": str(unit_price),
            "discount_amount": str(discount_amount),
            "price_after_discount": str(unit_price_final),
            "line_total": str(line_total),}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al escanear el producto: {e}")
    finally:
        cursor.close()
        conn.close()

@router.get("/search")
def search(query: str, current_user: dict = Depends(get_current_user)):
    conn = get_conn()
    if conn is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al conectar a la base de datos")       
    cursor = conn.cursor()
    
    try:
        box_id = current_user["box_id"]
        return search_product(query, cursor, box_id)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al buscar el producto")
    finally:
        cursor.close()
        conn.close()