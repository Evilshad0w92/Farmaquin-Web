from fastapi import APIRouter, HTTPException, status, Depends
from app.db.connection import get_conn
from app.core.security.deps import get_current_user
import psycopg2

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("/alerts")
def get_alerts(current_user: dict = Depends(get_current_user)):
    conn = get_conn()
    if conn is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Error al conectar a la base de datos")
    cursor = conn.cursor()

    try:
        box_id = current_user["box_id"]

        # Products at or below their minimum stock level for this branch
        cursor.execute("""
            SELECT p.name, bi.stock, bi.min_stock
            FROM branch_inventory bi
            JOIN products p ON p.id = bi.product_id
            JOIN boxes b    ON b.location_id = bi.location_id
            WHERE b.id = %s
              AND bi.active = true
              AND p.is_service = false
              AND bi.stock <= bi.min_stock
            ORDER BY (bi.stock::float / NULLIF(bi.min_stock, 0)) ASC
            LIMIT 15
        """, (box_id,))
        low_stock = [
            {"name": r[0], "stock": r[1], "min_stock": r[2]}
            for r in cursor.fetchall()
        ]

        # Batches expiring within the next 60 days for this branch
        cursor.execute("""
            SELECT p.name, pb.lot, pb.expiration_date, pb.qty,
                   (pb.expiration_date - CURRENT_DATE) AS days_left
            FROM product_batches pb
            JOIN products p ON p.id = pb.product_id
            JOIN boxes b    ON b.location_id = pb.location_id
            WHERE b.id = %s
              AND pb.active = true
              AND pb.expiration_date IS NOT NULL
              AND pb.expiration_date <= CURRENT_DATE + INTERVAL '60 days'
            ORDER BY pb.expiration_date ASC
            LIMIT 15
        """, (box_id,))
        expiring = [
            {
                "name": r[0],
                "lot":  r[1],
                "expiration_date": str(r[2]),
                "qty":  r[3],
                "days_left": r[4].days if r[4] is not None else 0,
            }
            for r in cursor.fetchall()
        ]

        # Active discount promotions (any branch — discounts are global)
        cursor.execute("""
            SELECT d.name, d.type, d.value, d.end_date, p.name AS product_name
            FROM discounts d
            JOIN products p ON p.id = d.product_id
            WHERE d.active = true
              AND CURRENT_DATE BETWEEN d.start_date AND d.end_date
            ORDER BY d.end_date ASC
            LIMIT 10
        """)
        promotions = [
            {
                "name":         r[0],
                "type":         r[1],
                "value":        str(r[2]),
                "end_date":     str(r[3]),
                "product_name": r[4],
            }
            for r in cursor.fetchall()
        ]

        return {
            "low_stock":  low_stock,
            "expiring":   expiring,
            "promotions": promotions,
        }

    except psycopg2.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error de base de datos: {e}")
    finally:
        cursor.close()
        conn.close()
