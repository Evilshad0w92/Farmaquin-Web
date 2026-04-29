from fastapi import HTTPException, status

# Base SELECT shared by all product-lookup functions.
# Branch-specific fields (stock, price_sell, active, section) come from branch_inventory (bi)
# so each cash register sees its own per-location values instead of the global products row.
_PRODUCT_SELECT = """
    SELECT p.id, p.barcode, p.name, p.formula,
           bi.stock, bi.price_sell, bi.active,
           d.type, COALESCE(d.value, 0) AS discount,
           p.lab_name, s.name, p.method, p.is_service
    FROM products p
    JOIN branch_inventory bi ON bi.product_id = p.id
    JOIN boxes b             ON b.location_id = bi.location_id
    LEFT JOIN discounts d    ON d.product_id = p.id
                             AND d.active = true
                             AND CURRENT_DATE BETWEEN d.start_date AND d.end_date
    LEFT JOIN sections s     ON s.id = bi.section_id
"""

def _row_to_product(row):
    # Column order matches _PRODUCT_SELECT: id, barcode, name, formula,
    # stock, price_sell, active, discount_type, discount_value,
    # lab_name, section_name, method, is_service
    return {
        "id":             row[0],
        "barcode":        row[1],
        "name":           row[2],
        "formula":        row[3],
        "stock":          row[4],
        "price_sell":     row[5],
        "active":         row[6],
        "discount_type":  row[7],
        "discount_value": row[8],
        "lab_name":       row[9],
        "section_name":   row[10],
        "method":         row[11],
        "is_service":     row[12],
    }

def get_product_by_id(product_id: int, current_qty: int, cursor, box_id: int):
    try:
        cursor.execute(
            _PRODUCT_SELECT + "WHERE p.id = %s AND b.id = %s",
            (product_id, box_id)
        )
        row = cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado")

        product = _row_to_product(row)

        if not product["active"]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El producto está inactivo")
        elif not product["is_service"] and product["stock"] < current_qty:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El producto no tiene suficiente stock disponible")

        return product

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al obtener el producto")

def get_product_by_barcode(barcode: str, current_qty: int, cursor, box_id: int):
    try:
        cursor.execute(
            _PRODUCT_SELECT + "WHERE p.barcode = %s AND b.id = %s AND bi.active = true",
            (barcode, box_id)
        )
        row = cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado")

        product = _row_to_product(row)

        if not product["active"]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El producto está inactivo")
        elif not product["is_service"] and product["stock"] < current_qty:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El producto no tiene suficiente stock disponible")

        return product

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al obtener el producto")

def search_product(query: str, cursor, box_id: int, limit: int = 10):
    try:
        cursor.execute(
            _PRODUCT_SELECT + """
            WHERE (p.name ILIKE %s OR p.formula ILIKE %s)
              AND b.id = %s
              AND bi.active = true
            LIMIT %s
            """,
            (f"%{query}%", f"%{query}%", box_id, limit)
        )
        rows = cursor.fetchall()
        if not rows:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado o inactivo")
        return [
            {
                "id":             row[0],
                "barcode":        row[1],
                "name":           row[2],
                "formula":        row[3],
                "stock":          row[4],
                "price_sell":     row[5],
                "discount_type":  row[7],
                "discount_value": row[8],
                "lab_name":       row[9],
                "section_name":   row[10],
                "method":         row[11],
                "is_service":     row[12],
            }
            for row in rows
        ]
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al obtener el producto")
