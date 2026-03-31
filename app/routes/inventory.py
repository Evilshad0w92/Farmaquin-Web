from fastapi import APIRouter, HTTPException, status, Depends
from app.db.connection import get_conn
from app.core.security.deps import get_current_user
from app.schemas.inventory_schema import InventoryAdjustmentCreate, InventoryAdjustmentResponse, InventoryRestockCreate,InventoryRestockResponse
from decimal import Decimal, ROUND_HALF_UP
import psycopg2

router = APIRouter(prefix="/inventory", tags=["inventory"])

#This route is for searching products in the inventory, it allows searching by name, formula or barcode, and also filtering by low stock. It returns a list of products with their details.
@router.get("/search")
def search(query: str = "", low_stock: bool = False, current_user: dict = Depends(get_current_user)):
    conn = get_conn()
    if conn is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al conectar a la base de datos")       
    cursor = conn.cursor()

    try:
        box_id = current_user["box_id"]
        sql = """SELECT p.id, p.barcode, p.name, p.formula, p.stock, p.price_sell, p.lab_name, s.name, p.method, p.active, p.cost, pr.name, pr.id
                 FROM products p JOIN boxes b ON p.location_id = b.location_id 
                                 LEFT JOIN sections s ON p.section_id = s.id
                                 LEFT JOIN providers pr ON p.provider_id = pr.id
                 WHERE b.id = %s AND (p.name ILIKE %s OR p.formula ILIKE %s OR p.barcode ILIKE %s)"""
        params = [box_id, f"%{query}%", f"%{query}%", f"%{query}%"]
        if low_stock:
            sql += " AND p.stock < 5"
        sql += " ORDER BY p.name LIMIT 20"
        
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        return [
            {
                "id": row[0],
                "barcode": row[1],
                "name": row[2],
                "formula": row[3],
                "stock": row[4],
                "price_sell": str(row[5]),
                "lab_name": row[6],
                "section_name": row[7],
                "method": row[8],
                "active": row[9],
                "cost": str(row[10]),
                "provider_name": row[11],
                "provider_id": row[12],
            }
            for row in rows
        ]
    except psycopg2.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail= f"Error de base de datos: {e}")  
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al buscar productos")
    finally:
        cursor.close()
        conn.close()


# This route is for adjusting the inventory of a product, it allows increasing or decreasing the stock of a product by a specified quantity and reason. It also records the adjustment in the inventory_adjustments table with the user and box information.
@router.post("/adjustment", response_model=InventoryAdjustmentResponse, status_code=status.HTTP_201_CREATED)
def adjust_inventory(data: InventoryAdjustmentCreate, current_user: dict = Depends(get_current_user)):
    conn = get_conn()
    if conn is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al conectar a la base de datos")   
    cursor = conn.cursor()

    try:
        box_id = current_user["box_id"]
        user_id = current_user["sub"]
        cursor.execute("""SELECT p.stock
                          FROM products p JOIN boxes b ON p.location_id = b.location_id
                          WHERE p.id = %s AND b.id = %s
                          FOR UPDATE""", (data.product_id, box_id))
        row = cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado")
        
        current_stock = row[0]
        
        if data.quantity <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La cantidad debe ser mayor a cero")    
        if data.adjustment_type == "SALIDA":
            if current_stock < data.quantity:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No hay suficiente stock para realizar el ajuste")
            new_stock = current_stock - data.quantity
        else:
            new_stock = current_stock + data.quantity

        cursor.execute("UPDATE products SET stock = %s WHERE id = %s", (new_stock, data.product_id))

        cursor.execute("""INSERT INTO inventory_adjustments (product_id, box_id, user_id, adjustment_type, quantity, reason) 
                          VALUES (%s, %s, %s, %s, %s, %s) RETURNING id, created_at""", (data.product_id, box_id, user_id, data.adjustment_type, data.quantity, data.reason))
        
        adjustment_row = cursor.fetchone()

        if adjustment_row is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al registrar el ajuste de inventario") 
        conn.commit()

        return InventoryAdjustmentResponse(
            id=adjustment_row[0],
            product_id=data.product_id,
            adjustment_type=data.adjustment_type,
            quantity=data.quantity,
            reason=data.reason,
            new_stock=new_stock,
            created_at=str(adjustment_row[1]),
        )
    except HTTPException:
        conn.rollback()
        raise
    except psycopg2.Error as e:
        conn.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail= f"Error de base de datos: {e}")  
    finally:
        cursor.close()
        conn.close()

# This route is for restocking the inventory of a product, it allows increasing the stock of a product by a specified quantity, unit cost and provider. It also records the restock in the inventory_restocks table with the user and box information.
@router.post("/restock", response_model=InventoryRestockResponse, status_code=status.HTTP_201_CREATED)
def restock_inventory(data: InventoryRestockCreate, current_user: dict = Depends(get_current_user)):
    conn = get_conn()
    if conn is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al conectar a la base de datos")   
    cursor = conn.cursor()
    q = Decimal("0.01")

    try:
        box_id = current_user["box_id"]
        user_id = current_user["sub"]
        if data.quantity <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La cantidad debe ser mayor a cero")
        
        unit_cost = Decimal(str(data.unit_cost)).quantize(q, rounding=ROUND_HALF_UP)

        if unit_cost <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El costo  debe ser mayor a cero")  
        
        # Get provider information
        cursor.execute("""SELECT id, name 
                       FROM providers 
                       WHERE id = %s""", (data.provider_id,))
        
        provider_row = cursor.fetchone()

        if provider_row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proveedor no encontrado")

        provider_id = provider_row[0]
        provider_name = provider_row[1]

        #Get current stock 
        cursor.execute("""SELECT p.stock
                          FROM products p JOIN boxes b ON p.location_id = b.location_id
                          WHERE p.id = %s AND b.id = %s FOR UPDATE""", (data.product_id, box_id))
        row = cursor.fetchone()
        
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado")
        
        current_stock = row[0]
        new_stock = current_stock + data.quantity

        # Update product stock and insert restock record in a transaction
        cursor.execute("""UPDATE products SET stock = %s, cost = %s, price_sell = %s WHERE id = %s""", (new_stock, unit_cost, data.sell_price, data.product_id))

        cursor.execute("""INSERT INTO inventory_restock (product_id, box_id, user_id, provider_id, unit_cost, price_sell, quantity) 
                          VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id, created_at""", (data.product_id, box_id, user_id, provider_id, unit_cost, data.sell_price, data.quantity))
        
        restock_row = cursor.fetchone()

        if restock_row is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al registrar el reabastecimiento de inventario") 
        conn.commit()

        return InventoryRestockResponse(
            id=restock_row[0],
            product_id=data.product_id,
            quantity=data.quantity,
            unit_cost=str(unit_cost),
            sell_price=str(data.sell_price),
            provider_id=provider_id,
            provider_name=provider_name,
            new_stock=new_stock,
            created_at=str(restock_row[1]),
        )
    except HTTPException:
        conn.rollback()
        raise
    except psycopg2.Error as e:
        conn.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail= f"Error de base de datos: {e}")
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al resurtir inventario: {e}")    
    finally:
        cursor.close()
        conn.close()

