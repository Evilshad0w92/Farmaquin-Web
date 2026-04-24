from fastapi import APIRouter, HTTPException, status, Depends
from app.db.connection import get_conn
from app.core.security.deps import get_current_user
from decimal import Decimal
from typing import Optional
import psycopg2
from datetime import date

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/sales")
def list_sales(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    current_user: dict = Depends(get_current_user)
):
    conn = get_conn()
    if conn is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al conectar a la base de datos")
    cursor = conn.cursor()

    try:
        box_id = current_user["box_id"]
        params = [box_id]
        sql = """
            SELECT s.id, s.total, s.payment_method, s.cash_received, s.change_given, s.created_at, u.name
            FROM sales s
            JOIN users u ON s.sold_by = u.id
            WHERE s.box_id = %s
        """
        if date_from:
            sql += " AND s.created_at >= %s"
            params.append(date_from)
        if date_to:
            sql += " AND s.created_at < (%s::date + INTERVAL '1 day')"
            params.append(date_to)
        sql += " ORDER BY s.created_at DESC LIMIT 500"

        cursor.execute(sql, params)
        rows = cursor.fetchall()

        return [
            {
                "id": row[0],
                "total": str(row[1] or "0.00"),
                "payment_method": row[2],
                "cash_received": str(row[3]) if row[3] is not None else None,
                "change_given": str(row[4]) if row[4] is not None else None,
                "created_at": str(row[5]),
                "sold_by": row[6],
            }
            for row in rows
        ]

    except psycopg2.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error de base de datos: {e}")
    finally:
        cursor.close()
        conn.close()


@router.get("/sales/print")
def sales_for_print(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    current_user: dict = Depends(get_current_user)
):
    """Returns all sales with their items for batch printing."""
    conn = get_conn()
    if conn is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al conectar a la base de datos")
    cursor = conn.cursor()

    try:
        box_id = current_user["box_id"]
        params = [box_id]
        date_filter = ""
        if date_from:
            date_filter += " AND s.created_at >= %s"
            params.append(date_from)
        if date_to:
            date_filter += " AND s.created_at < (%s::date + INTERVAL '1 day')"
            params.append(date_to)

        cursor.execute(f"""
            SELECT s.id, s.total, s.payment_method, s.cash_received, s.change_given, s.created_at, u.name
            FROM sales s
            JOIN users u ON s.sold_by = u.id
            WHERE s.box_id = %s {date_filter}
            ORDER BY s.created_at ASC
            LIMIT 500
        """, params)
        sales_rows = cursor.fetchall()

        if not sales_rows:
            return {"ticket_type": "sales_report", "sales": [], "total": "0.00", "sales_count": 0}

        sale_ids = [r[0] for r in sales_rows]
        cursor.execute(f"""
            SELECT si.sale_id, p.name, p.formula, si.qty, si.price, si.discount_amount,
                   (si.price - si.discount_amount) * si.qty AS line_total
            FROM sale_items si
            JOIN products p ON si.product_id = p.id
            WHERE si.sale_id = ANY(%s)
            ORDER BY si.sale_id, p.name
        """, (sale_ids,))
        items_rows = cursor.fetchall()

        items_by_sale = {}
        for row in items_rows:
            sid = row[0]
            if sid not in items_by_sale:
                items_by_sale[sid] = []
            items_by_sale[sid].append({
                "name": row[1],
                "formula": row[2] or "",
                "qty": row[3],
                "price": str(row[4] or "0.00"),
                "discount": str(row[5] or "0.00"),
                "total": str(row[6] or "0.00"),
            })

        sales = []
        grand_total = Decimal("0.00")
        for row in sales_rows:
            grand_total += Decimal(str(row[1] or 0))
            sales.append({
                "sale_id": row[0],
                "total": str(row[1] or "0.00"),
                "payment_method": row[2],
                "cash_received": str(row[3]) if row[3] is not None else None,
                "change_given": str(row[4]) if row[4] is not None else None,
                "created_at": str(row[5]),
                "sold_by": row[6],
                "items": items_by_sale.get(row[0], []),
            })

        return {
            "ticket_type": "sales_report",
            "date_from": str(date_from) if date_from else None,
            "date_to": str(date_to) if date_to else None,
            "sales_count": len(sales),
            "total": str(grand_total),
            "sales": sales,
        }

    except psycopg2.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error de base de datos: {e}")
    finally:
        cursor.close()
        conn.close()


@router.get("/expenses")
def list_expenses(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    current_user: dict = Depends(get_current_user)
):
    conn = get_conn()
    if conn is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al conectar a la base de datos")
    cursor = conn.cursor()

    try:
        box_id = current_user["box_id"]
        params = [box_id]
        sql = """
            SELECT e.id, e.amount, e.description, e.expense_type, e.created_at, u.name
            FROM expenses e
            JOIN users u ON e.user_id = u.id
            WHERE e.box_id = %s AND e.active = TRUE
        """
        if date_from:
            sql += " AND e.created_at >= %s"
            params.append(date_from)
        if date_to:
            sql += " AND e.created_at < (%s::date + INTERVAL '1 day')"
            params.append(date_to)
        sql += " ORDER BY e.created_at DESC LIMIT 500"

        cursor.execute(sql, params)
        rows = cursor.fetchall()

        return [
            {
                "id": row[0],
                "amount": str(row[1] or "0.00"),
                "description": row[2],
                "expense_type": row[3],
                "created_at": str(row[4]),
                "registered_by": row[5],
            }
            for row in rows
        ]

    except psycopg2.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error de base de datos: {e}")
    finally:
        cursor.close()
        conn.close()


@router.get("/purchases")
def list_purchases(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    current_user: dict = Depends(get_current_user)
):
    conn = get_conn()
    if conn is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al conectar a la base de datos")
    cursor = conn.cursor()

    try:
        box_id = current_user["box_id"]
        params = [box_id]
        sql = """
            SELECT ir.id, p.name, p.formula, pr.name, ir.quantity, ir.unit_cost, ir.price_sell, ir.created_at, u.name
            FROM inventory_restock ir
            JOIN products p ON ir.product_id = p.id
            JOIN providers pr ON ir.provider_id = pr.id
            JOIN users u ON ir.user_id = u.id
            WHERE ir.box_id = %s
        """
        if date_from:
            sql += " AND ir.created_at >= %s"
            params.append(date_from)
        if date_to:
            sql += " AND ir.created_at < (%s::date + INTERVAL '1 day')"
            params.append(date_to)
        sql += " ORDER BY ir.created_at DESC LIMIT 500"

        cursor.execute(sql, params)
        rows = cursor.fetchall()

        return [
            {
                "id": row[0],
                "product_name": row[1],
                "formula": row[2],
                "provider_name": row[3],
                "quantity": row[4],
                "unit_cost": str(row[5] or "0.00"),
                "price_sell": str(row[6] or "0.00"),
                "created_at": str(row[7]),
                "registered_by": row[8],
            }
            for row in rows
        ]

    except psycopg2.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error de base de datos: {e}")
    finally:
        cursor.close()
        conn.close()


@router.get("/cashcuts")
def list_cashcuts(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    current_user: dict = Depends(get_current_user)
):
    conn = get_conn()
    if conn is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al conectar a la base de datos")
    cursor = conn.cursor()

    try:
        box_id = current_user["box_id"]
        params = [box_id]
        sql = """
            SELECT cc.id, cc.from_ts, cc.to_ts, cc.net_total, cc.total_cash, cc.total_card,
                   cc.total_transfer, cc.total_expenses, cc.cash_expected, cc.cash_counted,
                   cc.difference, cc.sales_count, cc.comment, u.name
            FROM cash_cuts cc
            JOIN users u ON cc.closed_by = u.id
            WHERE cc.box_id = %s
        """
        if date_from:
            sql += " AND cc.to_ts >= %s"
            params.append(date_from)
        if date_to:
            sql += " AND cc.to_ts < (%s::date + INTERVAL '1 day')"
            params.append(date_to)
        sql += " ORDER BY cc.to_ts DESC LIMIT 200"

        cursor.execute(sql, params)
        rows = cursor.fetchall()

        return [
            {
                "id": row[0],
                "from_ts": str(row[1]),
                "to_ts": str(row[2]),
                "net_total": str(row[3] or "0.00"),
                "total_cash": str(row[4] or "0.00"),
                "total_card": str(row[5] or "0.00"),
                "total_transfer": str(row[6] or "0.00"),
                "total_expenses": str(row[7] or "0.00"),
                "cash_expected": str(row[8] or "0.00"),
                "cash_counted": str(row[9] or "0.00"),
                "difference": str(row[10] or "0.00"),
                "sales_count": row[11] or 0,
                "comment": row[12] or "",
                "closed_by": row[13],
            }
            for row in rows
        ]

    except psycopg2.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error de base de datos: {e}")
    finally:
        cursor.close()
        conn.close()


@router.get("/cashcut/{cut_id}")
def get_cashcut_for_reprint(cut_id: int, current_user: dict = Depends(get_current_user)):
    """Returns a cash cut's full data formatted for reprinting."""
    conn = get_conn()
    if conn is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al conectar a la base de datos")
    cursor = conn.cursor()

    try:
        box_id = current_user["box_id"]

        cursor.execute("""
            SELECT cc.id, cc.from_ts, cc.to_ts, cc.net_total, cc.total_cash, cc.total_card,
                   cc.total_transfer, cc.total_returns, cc.total_returns_cash, cc.total_returns_card,
                   cc.total_returns_transfer, cc.total_expenses, cc.cash_expected, cc.cash_counted,
                   cc.difference, cc.sales_count, cc.comment, u.name
            FROM cash_cuts cc
            JOIN users u ON cc.closed_by = u.id
            WHERE cc.id = %s AND cc.box_id = %s
        """, (cut_id, box_id))

        row = cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Corte no encontrado")

        from_ts = row[1]
        to_ts = row[2]

        cursor.execute("""
            SELECT id, total, payment_method, created_at
            FROM sales
            WHERE box_id = %s AND created_at > %s AND created_at <= %s
            ORDER BY created_at ASC
        """, (box_id, from_ts, to_ts))
        sales_detail = [
            {"sale_id": r[0], "total": str(r[1] or "0.00"), "payment_method": r[2], "created_at": str(r[3])}
            for r in cursor.fetchall()
        ]

        cursor.execute("""
            SELECT p.name, SUM(si.qty), SUM((si.price - si.discount_amount) * si.qty)
            FROM sale_items si
            JOIN sales s ON si.sale_id = s.id
            JOIN products p ON si.product_id = p.id
            WHERE s.box_id = %s AND s.created_at > %s AND s.created_at <= %s
            GROUP BY p.name ORDER BY p.name
        """, (box_id, from_ts, to_ts))
        products_summary = [
            {"description": r[0], "quantity": int(r[1] or 0), "total": str(r[2] or "0.00")}
            for r in cursor.fetchall()
        ]

        return {
            "ticket_type": "cashcut",
            "cut_id": row[0],
            "from_ts": str(from_ts),
            "to_ts": str(to_ts),
            "total_sales": str(row[3] or "0.00"),
            "total_cash": str(row[4] or "0.00"),
            "total_card": str(row[5] or "0.00"),
            "total_transfer": str(row[6] or "0.00"),
            "total_returns": str(row[7] or "0.00"),
            "total_returns_cash": str(row[8] or "0.00"),
            "total_returns_card": str(row[9] or "0.00"),
            "total_returns_transfer": str(row[10] or "0.00"),
            "total_expenses": str(row[11] or "0.00"),
            "cash_expected": str(row[12] or "0.00"),
            "cash_counted": str(row[13] or "0.00"),
            "difference": str(row[14] or "0.00"),
            "sales_count": row[15] or 0,
            "comment": row[16] or "",
            "closed_by": row[17],
            "sales_detail": sales_detail,
            "products_summary": products_summary,
        }

    except HTTPException:
        raise
    except psycopg2.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error de base de datos: {e}")
    finally:
        cursor.close()
        conn.close()
