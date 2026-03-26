from fastapi import Depends, HTTPException, status

def _row_to_product(row):
    return {"id": row[0],
            "barcode": row[1],
            "name": row[2], 
            "formula": row[3],  
            "stock": row[4],
            "price_sell": row[5],
            "active": row[6],
            "discount_type": row[7], 
            "discount_value": row[8]}

def get_product_by_id(product_id: int, current_qty: int, cursor, box_id: int):
    try:
        cursor.execute("""SELECT p.id, p.barcode, p.name, p.formula, p.stock, p.price_sell, p.active , d.type, COALESCE(d.value, 0) discount 
                          FROM products p LEFT JOIN discounts d ON p.id = d.product_id AND d.active = true AND CURRENT_DATE BETWEEN d.start_date AND d.end_date
                                          LEFT JOIN boxes b ON p.location_id = b.location_id 
                          WHERE-- p.id =%s AND b.id = %s""", (product_id, box_id))
        row = cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Producto no encontrado")
        
        product = _row_to_product(row)  

        if not product["active"]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"El producto está inactivo")   
        elif product["stock"] < current_qty:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"El producto no tiene suficiente stock disponible")
        
        return product 

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al obtener el producto")

def get_product_by_barcode(barcode: str, current_qty: int, cursor, box_id: int):
    try:
        cursor.execute("""SELECT p.id, p.barcode, p.name, p.formula, p.stock, p.price_sell, p.active, d.type, COALESCE(d.value, 0) discount 
                          FROM products p LEFT JOIN discounts d ON p.id = d.product_id AND d.active = true AND CURRENT_DATE BETWEEN d.start_date AND d.end_date 
                                          LEFT JOIN boxes b ON p.location_id = b.location_id 
                          WHERE p.barcode =%s AND b.id = %s""", (barcode, box_id))
        row = cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Producto no encontrado")
        
        product = _row_to_product(row)  

        if not product["active"]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"El producto está inactivo")   
        elif product["stock"] < current_qty:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"El producto no tiene suficiente stock disponible")
        
        return product 
    
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al obtener el producto")


def search_product(query: str, cursor, box_id: int , limit: int = 10):
    try:
        cursor.execute("""SELECT p.id, p.barcode, p.name, p.formula, p.stock, p.price_sell, p.active, d.type, COALESCE(d.value, 0) discount  
                          FROM products p LEFT JOIN discounts d ON p.id = d.product_id AND d.active = true AND CURRENT_DATE BETWEEN d.start_date AND d.end_date
                                          LEFT JOIN boxes b ON p.location_id = b.location_id
                          WHERE p.name ILIKE %s AND b.id = %s AND p.active = true LIMIT %s""", (f"%{query}%", box_id, limit))
        rows = cursor.fetchall()
        if not rows:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Producto no encontrado o inactivo")
        return [{"id": row[0],
                 "barcode": row[1],
                 "name": row[2], 
                 "formula": row[3], 
                 "stock": row[4], 
                 "price_sell": row[5], 
                 "discount_type": row[7], 
                 "discount_value": row[8]} 
                 for row in rows]
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al obtener el producto")
    