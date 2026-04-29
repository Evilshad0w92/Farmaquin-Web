from fastapi import APIRouter, HTTPException, status, Depends
from app.db.connection import get_conn
from app.core.security.deps import get_current_user
from app.schemas.inventory_schema import InventoryAdjustmentCreate, InventoryAdjustmentResponse, InventoryNewItemCreate, InventoryNewItemResponse, InventoryRestockCreate,InventoryRestockResponse, InventoryEditCreate, InventoryEditResponse, labListResponse, ProductBatchEditCreate, ProductBatchEditResponse
from decimal import Decimal, ROUND_HALF_UP
import psycopg2

router = APIRouter(prefix="/inventory", tags=["inventory"])

# Connectors that stay lowercase when they appear between words (Spanish)
_CONNECTORS = {"o", "y"}

def normalize_method(method: str) -> str:
    """Title-case each word in a via/method string, keeping 'o'/'y' connectors lowercase.

    Examples:
        'oral'                      -> 'Oral'
        'INTRAVENOSA'               -> 'Intravenosa'
        'intramuscular o intravenosa' -> 'Intramuscular o Intravenosa'
        'N/A'                       -> 'N/A'   (all-caps acronyms preserved)
    """
    if not method or not method.strip():
        return method
    words = method.strip().split()
    result = []
    for i, word in enumerate(words):
        bare   = word.rstrip(".,;:")
        suffix = word[len(bare):]
        lower  = bare.lower()
        if lower in _CONNECTORS and i > 0:
            result.append(lower + suffix)
        else:
            # Preserve all-caps acronyms (e.g. N/A: alpha chars "NA" are all uppercase)
            alpha = "".join(c for c in bare if c.isalpha())
            if alpha and alpha == alpha.upper() and len(alpha) > 1:
                result.append(word)
            else:
                result.append(bare.capitalize() + suffix)
    return " ".join(result)

#This route is for searching products in the inventory, it allows searching by name, formula or barcode, and also filtering by low stock. It returns a list of products with their details.
@router.get("/search")
def search(query: str = "", low_stock: bool = False, current_user: dict = Depends(get_current_user)):
    conn = get_conn()
    if conn is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al conectar a la base de datos"
        )

    cursor = conn.cursor()

    try:
        box_id = current_user["box_id"]

        # LEFT JOIN branch_inventory so products not yet stocked at this branch
        # appear with stock=0 instead of being invisible.
        # CROSS JOIN the boxes subquery so we can filter by box without an inner join on bi.
        sql = """
            SELECT p.id, p.barcode, p.name, p.formula,
                   COALESCE(bi.stock, 0)      AS stock,
                   COALESCE(bi.price_sell, 0) AS price_sell,
                   p.lab_name, s.name, p.method,
                   COALESCE(bi.active, true)  AS active,
                   COALESCE(bi.unit_cost, 0)  AS unit_cost,
                   pr.name, pr.id, bi.section_id,
                   COALESCE(bi.min_stock, 0)  AS min_stock,
                   p.is_service
            FROM products p
            CROSS JOIN (SELECT location_id FROM boxes WHERE id = %s) AS loc
            LEFT JOIN branch_inventory bi ON bi.product_id = p.id AND bi.location_id = loc.location_id
            LEFT JOIN sections s          ON s.id = bi.section_id
            LEFT JOIN providers pr        ON pr.id = p.provider_id
            WHERE p.active = true
              AND (
                    p.name ILIKE %s
                    OR p.formula ILIKE %s
                    OR p.barcode ILIKE %s
              )
        """

        params = [box_id, f"%{query}%", f"%{query}%", f"%{query}%"]

        if low_stock:
            sql += " AND COALESCE(bi.stock, 0) <= COALESCE(bi.min_stock, 0)"

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
                "section_id": row[13],
                "min_stock": row[14],
                "is_service": row[15],
            }
            for row in rows
        ]

    except psycopg2.Error as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error de base de datos: {e}"
        )
    except HTTPException as e:
        raise e
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al buscar productos"
        )
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

        # Lock the branch_inventory row for this location to prevent concurrent adjustments
        cursor.execute("""
            SELECT bi.stock, bi.location_id
            FROM branch_inventory bi
            JOIN boxes b ON b.location_id = bi.location_id
            WHERE bi.product_id = %s AND b.id = %s
            FOR UPDATE
        """, (data.product_id, box_id))
        row = cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado")

        current_stock = row[0]
        location_id   = row[1]

        if data.quantity <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La cantidad debe ser mayor a cero")
        if data.adjustment_type == "SALIDA":
            if current_stock < data.quantity:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No hay suficiente stock para realizar el ajuste")
            new_stock = current_stock - data.quantity
        else:
            new_stock = current_stock + data.quantity

        # Apply the adjustment to this location's stock in branch_inventory
        cursor.execute(
            "UPDATE branch_inventory SET stock = %s WHERE product_id = %s AND location_id = %s",
            (new_stock, data.product_id, location_id)
        )

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

        # Resolve location_id from box
        cursor.execute("SELECT location_id FROM boxes WHERE id = %s", (box_id,))
        loc_row = cursor.fetchone()
        if not loc_row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Caja no encontrada")
        location_id = loc_row[0]

        # Verify the product exists in the global catalog
        cursor.execute("SELECT id FROM products WHERE id = %s AND active = true", (data.product_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado")

        # UPSERT: creates branch_inventory if this is the first restock at this location,
        # otherwise adds quantity to existing stock and updates cost/price.
        cursor.execute("""
            INSERT INTO branch_inventory (product_id, location_id, stock, unit_cost, price_sell, active)
            VALUES (%s, %s, %s, %s, %s, true)
            ON CONFLICT (product_id, location_id) DO UPDATE
            SET stock      = branch_inventory.stock + EXCLUDED.stock,
                unit_cost  = EXCLUDED.unit_cost,
                price_sell = EXCLUDED.price_sell
            RETURNING stock
        """, (data.product_id, location_id, data.quantity, unit_cost, data.sell_price))
        bi_row = cursor.fetchone()
        new_stock = bi_row[0]

        cursor.execute("""
            INSERT INTO inventory_restock (product_id, box_id, user_id, provider_id, unit_cost, price_sell, quantity)
            VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id, created_at
        """, (data.product_id, box_id, user_id, provider_id, unit_cost, data.sell_price, data.quantity))

        restock_row = cursor.fetchone()

        if restock_row is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al registrar el reabastecimiento de inventario")

        # Include location_id in batch so it's scoped to this branch
        cursor.execute("""
            INSERT INTO product_batches (product_id, qty, expiration_date, lot, location_id)
            VALUES (%s, %s, %s, %s, %s)
        """, (data.product_id, data.quantity, data.expiration_date, data.lot, location_id))

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

# This route creates a new product in the inventory and record as restock
@router.post("/create", response_model=InventoryNewItemResponse, status_code=status.HTTP_201_CREATED)
def create_inventory(data: InventoryNewItemCreate, current_user: dict = Depends(get_current_user)):
    conn = get_conn()
    if conn is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al conectar a la base de datos")
    cursor = conn.cursor()

    q = Decimal("0.01")

    try:
        box_id = current_user["box_id"]
        user_id = current_user["sub"]

        if data.stock <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La cantidad debe ser mayor a cero")
        elif data.unit_cost <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El costo debe ser mayor a cero")
        elif data.sell_price <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El precio de venta debe ser mayor a cero")
        elif data.sell_price < data.unit_cost:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El precio de venta no puede ser menor al costo")
        elif data.min_stock < 1:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El stock mínimo no puede ser menor a 1")

        # Normalize method to consistent Title Case before saving
        data.method = normalize_method(data.method)

        unit_cost = Decimal(str(data.unit_cost)).quantize(q, rounding=ROUND_HALF_UP)
        sell_price = Decimal(str(data.sell_price)).quantize(q, rounding=ROUND_HALF_UP)

        cursor.execute("""
            SELECT id, name
            FROM providers
            WHERE id = %s
        """, (data.provider_id,))
        provider_row = cursor.fetchone()
        if not provider_row:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Proveedor no encontrado")
        provider_id = provider_row[0]
        provider_name = provider_row[1]

        cursor.execute("""
            SELECT id, name
            FROM sections
            WHERE id = %s
        """, (data.section_id,))
        section_row = cursor.fetchone()
        if not section_row:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sección no encontrada")
        section_id = section_row[0]
        section_name = section_row[1]

        cursor.execute("""
            SELECT l.id, l.name
            FROM locations l
            JOIN boxes b ON l.id = b.location_id
            WHERE b.id = %s
        """, (box_id,))
        location_row = cursor.fetchone()
        if not location_row:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ubicación no encontrada")
        location_id = location_row[0]
        location_name = location_row[1]

        # Insert the global product record (catalog-level data shared across all branches)
        cursor.execute("""
            INSERT INTO products (
                barcode, name, formula, lab_name, method, cost, price_sell,
                stock, min_stock, section_id, provider_id, location_id, content, is_service
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, created_at
        """, (
            data.barcode, data.name, data.formula, data.lab_name, data.method,
            unit_cost, sell_price, data.stock, data.min_stock,
            section_id, provider_id, location_id, data.content, data.is_service
        ))
        product_row = cursor.fetchone()
        if product_row is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al crear el producto")

        # Create the branch_inventory record for this location with all per-location data
        cursor.execute("""
            INSERT INTO branch_inventory (product_id, location_id, stock, min_stock, section_id, unit_cost, price_sell, active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, true)
        """, (product_row[0], location_id, data.stock, data.min_stock, section_id, unit_cost, sell_price))

        cursor.execute("""
            INSERT INTO inventory_restock (
                product_id, box_id, user_id, provider_id, unit_cost, quantity, price_sell
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            product_row[0], box_id, user_id, provider_id, unit_cost, data.stock, sell_price
        ))

        # Include location_id in batch so it's scoped to this branch
        cursor.execute("""
            INSERT INTO product_batches (product_id, qty, expiration_date, lot, location_id)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            product_row[0], data.stock, data.expiration_date, data.lot, location_id
        ))

        cursor.execute("""
            INSERT INTO inventory_edit (
                product_id, name, formula, lab_name, method, cost, price_sell,
                min_stock, section_id, provider_id, location_id, box_id, user_id, content
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            product_row[0], data.name, data.formula, data.lab_name, data.method,
            unit_cost, sell_price, data.min_stock, section_id,
            provider_id, location_id, box_id, user_id, data.content
        ))

        conn.commit()

        return InventoryNewItemResponse(
            id=product_row[0],
            barcode=data.barcode,
            name=data.name,
            formula=data.formula,
            lab_name=data.lab_name,
            method=data.method,
            unit_cost=str(unit_cost),
            sell_price=str(sell_price),
            stock=data.stock,
            min_stock=data.min_stock,
            section_id=section_id,
            section_name=section_name,
            provider_id=provider_id,
            provider_name=provider_name,
            location_id=location_id,
            location_name=location_name,
            content=data.content,
            is_service=data.is_service,
            created_at=str(product_row[1]),
        )

    except HTTPException:
        conn.rollback()
        raise
    except psycopg2.Error as e:
        conn.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error de base de datos: {e}")
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al crear producto: {e}")
    finally:
        cursor.close()
        conn.close()

# This route updates a product in the inventory and record as restock
@router.put("/update", response_model=InventoryEditResponse)
def edit_inventory(data: InventoryEditCreate, current_user: dict = Depends(get_current_user)):
    conn = get_conn()
    if conn is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al conectar a la base de datos")
    cursor = conn.cursor()
    q = Decimal("0.01")

    try:
        box_id = current_user["box_id"]
        user_id = current_user["sub"]

        if data.name.strip() == "":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El nombre no puede estar vacío")
        elif data.formula.strip() == "":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La fórmula no puede estar vacía")
        elif data.method.strip() == "":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La vía de administración no puede estar vacía")
        elif data.unit_cost <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El costo debe ser mayor a cero")
        elif data.sell_price <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El precio de venta debe ser mayor a cero")
        elif data.sell_price < data.unit_cost:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El precio de venta no puede ser menor al costo")
        elif data.min_stock < 1:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El stock mínimo no puede ser menor a 1")

        # Normalize method to consistent Title Case before saving
        data.method = normalize_method(data.method)

        unit_cost = Decimal(str(data.unit_cost)).quantize(q, rounding=ROUND_HALF_UP)
        sell_price = Decimal(str(data.sell_price)).quantize(q, rounding=ROUND_HALF_UP)

        # Get provider information
        cursor.execute("""SELECT id, name
                          FROM providers
                          WHERE id = %s""", (data.provider_id,))
        provider_row = cursor.fetchone()
        if not provider_row:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Proveedor no encontrado")
        provider_id = provider_row[0]
        provider_name = provider_row[1]

        # Get section information
        cursor.execute("""SELECT id, name
                          FROM sections
                          WHERE id = %s""", (data.section_id,))
        section_row = cursor.fetchone()
        if not section_row:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sección no encontrada")
        section_id = section_row[0]
        section_name = section_row[1]

        # Get location information
        cursor.execute("""SELECT l.id, l.name
                          FROM locations l
                          JOIN boxes b ON l.id = b.location_id
                          WHERE b.id = %s""", (box_id,))
        location_row = cursor.fetchone()
        if not location_row:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ubicación no encontrada")
        location_id = location_row[0]
        location_name = location_row[1]

        # Lock the branch_inventory row for this location before updating
        cursor.execute("""
            SELECT bi.location_id
            FROM branch_inventory bi
            JOIN boxes b ON b.location_id = bi.location_id
            WHERE bi.product_id = %s AND b.id = %s
            FOR UPDATE
        """, (data.product_id, box_id))
        bi_row = cursor.fetchone()
        if not bi_row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado")
        location_id = bi_row[0]

        # Update global product fields (shared across all branches)
        cursor.execute("""
            UPDATE products
            SET name = %s, formula = %s, lab_name = %s, method = %s,
                provider_id = %s, content = %s, is_service = %s
            WHERE id = %s
        """, (data.name, data.formula, data.lab_name, data.method,
              provider_id, data.content, data.is_service, data.product_id))

        # Update branch-specific fields in branch_inventory for this location only
        cursor.execute("""
            UPDATE branch_inventory
            SET unit_cost = %s, price_sell = %s, min_stock = %s, section_id = %s
            WHERE product_id = %s AND location_id = %s
        """, (unit_cost, sell_price, data.min_stock, section_id, data.product_id, location_id))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No se pudo actualizar el producto")

        # Insert a record in the product's history
        cursor.execute("""INSERT INTO inventory_edit (product_id, name, formula, lab_name, method, cost, price_sell, min_stock, section_id, provider_id, location_id, box_id, user_id, content)
                          VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                          RETURNING id, created_at""", (data.product_id, data.name, data.formula, data.lab_name, data.method, unit_cost, sell_price, data.min_stock, section_id, provider_id, location_id, box_id, user_id, data.content))
        history_row = cursor.fetchone()
        if history_row is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al registrar el historial de edición")

        conn.commit()
        return InventoryEditResponse(
            id=history_row[0],
            product_id=data.product_id,
            name=data.name,
            formula=data.formula,
            lab_name=data.lab_name,
            method=data.method,
            unit_cost=float(unit_cost),
            sell_price=float(sell_price),
            min_stock=data.min_stock,
            section_id=section_id,
            provider_id=provider_id,
            content=data.content,
            is_service=data.is_service,
            created_at=str(history_row[1]),
        )

    except HTTPException:
        conn.rollback()
        raise
    except psycopg2.Error as e:
        conn.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error de base de datos: {e}")
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al actualizar producto: {e}")
    finally:
        cursor.close()
        conn.close()

@router.put("/batch/{batch_id}", response_model=ProductBatchEditResponse)
def edit_batch(batch_id: int, data: ProductBatchEditCreate, current_user: dict = Depends(get_current_user)):
    conn = get_conn()
    if conn is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al conectar a la base de datos")
    cursor = conn.cursor()

    try:
        box_id = current_user["box_id"]

        if data.qty <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La cantidad debe ser mayor a cero")

        if data.lot.strip() == "":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El lote no puede estar vacío")

        # Verify the batch belongs to this location using product_batches.location_id
        cursor.execute("""
            SELECT pb.id, pb.product_id, pb.created_at
            FROM product_batches pb
            JOIN boxes b ON b.location_id = pb.location_id
            WHERE pb.id = %s AND b.id = %s
            FOR UPDATE
        """, (batch_id, box_id))
        batch_row = cursor.fetchone()
        if not batch_row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lote no encontrado")

        product_id = batch_row[1]
        created_at = batch_row[2]

        cursor.execute("""
            UPDATE product_batches
            SET qty = %s, lot = %s, expiration_date = %s
            WHERE id = %s
        """, (data.qty, data.lot, data.expiration_date, batch_id))

        if cursor.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No se pudo actualizar el lote")

        conn.commit()

        return ProductBatchEditResponse(
            id=batch_id,
            product_id=product_id,
            qty=data.qty,
            lot=data.lot,
            expiration_date=data.expiration_date,
            created_at=str(created_at),
        )

    except HTTPException:
        conn.rollback()
        raise
    except psycopg2.Error as e:
        conn.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error de base de datos: {e}")
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al actualizar lote: {e}")
    finally:
        cursor.close()
        conn.close()


@router.delete("/batch/{batch_id}")
def delete_batch(batch_id: int, current_user: dict = Depends(get_current_user)):
    conn = get_conn()
    if conn is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al conectar a la base de datos")
    cursor = conn.cursor()

    try:
        box_id = current_user["box_id"]

        # Verify the batch belongs to this location using product_batches.location_id
        cursor.execute("""
            SELECT pb.id
            FROM product_batches pb
            JOIN boxes b ON b.location_id = pb.location_id
            WHERE pb.id = %s AND b.id = %s AND pb.active = true
            FOR UPDATE
        """, (batch_id, box_id))
        if cursor.fetchone() is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lote no encontrado o ya desactivado")

        cursor.execute("UPDATE product_batches SET active = false WHERE id = %s", (batch_id,))

        conn.commit()
        return {"ok": True}

    except HTTPException:
        conn.rollback()
        raise
    except psycopg2.Error as e:
        conn.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error de base de datos: {e}")
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al desactivar lote: {e}")
    finally:
        cursor.close()
        conn.close()


@router.get("/batches")
def search_batches(query: str = "", current_user: dict = Depends(get_current_user)):
    conn = get_conn()
    if conn is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al conectar a la base de datos")
    cursor = conn.cursor()

    try:
        box_id = current_user["box_id"]

        # Filter batches by location using product_batches.location_id
        cursor.execute("""
            SELECT pb.id, pb.product_id, p.name, p.formula, p.lab_name,
                   pb.lot, pb.qty, pb.expiration_date, pb.created_at
            FROM product_batches pb
            JOIN products p ON pb.product_id = p.id
            JOIN boxes b    ON b.location_id = pb.location_id
            WHERE b.id = %s
              AND pb.active = true
              AND (
                    p.name ILIKE %s
                    OR p.formula ILIKE %s
                    OR pb.lot ILIKE %s
              )
            ORDER BY pb.created_at DESC
            LIMIT 100
        """, (box_id, f"%{query}%", f"%{query}%", f"%{query}%"))

        rows = cursor.fetchall()

        return [
            {
                "id": row[0],
                "product_id": row[1],
                "product_name": row[2],
                "formula": row[3],
                "lab_name": row[4],
                "lot": row[5],
                "qty": row[6],
                "expiration_date": str(row[7]) if row[7] else None,
                "created_at": str(row[8]),
            }
            for row in rows
        ]

    except psycopg2.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error de base de datos: {e}")
    finally:
        cursor.close()
        conn.close()


@router.get("/labs", response_model=list[labListResponse])
def get_lab_names(current_user: dict = Depends(get_current_user)):
    conn = get_conn()
    if conn is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al conectar a la base de datos"
        )

    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT DISTINCT lab_name
            FROM products
            WHERE lab_name IS NOT NULL
              AND TRIM(lab_name) <> ''
            ORDER BY lab_name
        """)
        rows = cursor.fetchall()

        return [{"lab_name": row[0]} for row in rows]

    except psycopg2.Error as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error de base de datos: {e}"
        )
    finally:
        cursor.close()
        conn.close()


@router.get("/methods")
def get_methods(current_user: dict = Depends(get_current_user)):
    conn = get_conn()
    if conn is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al conectar a la base de datos")
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT DISTINCT method FROM products
            WHERE method IS NOT NULL AND TRIM(method) <> ''
            ORDER BY method
        """)
        return [{"method": row[0]} for row in cursor.fetchall()]
    except psycopg2.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error de base de datos: {e}")
    finally:
        cursor.close()
        conn.close()


@router.get("/barcode/{barcode}")
def check_barcode(barcode: str, current_user: dict = Depends(get_current_user)):
    """Returns the product if the barcode already exists in the global catalog (any branch)."""
    conn = get_conn()
    if conn is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al conectar a la base de datos")
    cursor = conn.cursor()
    try:
        box_id = current_user["box_id"]
        cursor.execute("""
            SELECT p.id, p.barcode, p.name, p.formula, p.lab_name,
                   COALESCE(bi.stock, 0)      AS stock,
                   COALESCE(bi.price_sell, 0) AS price_sell,
                   COALESCE(bi.unit_cost, 0)  AS unit_cost,
                   p.provider_id, bi.section_id,
                   COALESCE(bi.min_stock, 0)  AS min_stock,
                   p.is_service, p.method
            FROM products p
            CROSS JOIN (SELECT location_id FROM boxes WHERE id = %s) AS loc
            LEFT JOIN branch_inventory bi ON bi.product_id = p.id AND bi.location_id = loc.location_id
            WHERE LOWER(p.barcode) = LOWER(%s) AND p.active = true
        """, (box_id, barcode))
        row = cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado")
        return {
            "id":          row[0],
            "barcode":     row[1],
            "name":        row[2],
            "formula":     row[3],
            "lab_name":    row[4],
            "stock":       row[5],
            "price_sell":  str(row[6]),
            "cost":        str(row[7]),
            "provider_id": row[8],
            "section_id":  row[9],
            "min_stock":   row[10],
            "is_service":  row[11],
            "method":      row[12],
        }
    except HTTPException:
        raise
    except psycopg2.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error de base de datos: {e}")
    finally:
        cursor.close()
        conn.close()