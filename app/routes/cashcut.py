from fastapi import APIRouter, HTTPException, status, Depends
from app.db.connection import get_conn
from app.core.security.deps import get_current_user
from decimal import Decimal, ROUND_HALF_UP
from app.schemas.cashcut_schema import CashcutClose

router = APIRouter(prefix="/cashcut", tags=["cashcut"])


@router.get("/preview")
def preview_cashcut(current_user: dict = Depends(get_current_user)):
    conn = get_conn()
    if conn is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al conectar a la base de datos")
    cursor = conn.cursor()

    try:
        # Fetch the latest cash cut timestamp
        cursor.execute("""
                       SELECT to_ts, cash_counted 
                       FROM cash_cuts 
                       WHERE box_id = %s    
                       ORDER BY to_ts DESC 
                       LIMIT 1
                       """, (current_user["box_id"],))
        latest_cut = cursor.fetchone()
        if latest_cut:
            from_ts = latest_cut[0]
            last_counted = latest_cut[1] 
        else:
            from_ts = "1970-01-01"  
            last_counted = Decimal("0.00")

        cursor.execute("SELECT now()")
        to_ts_row = cursor.fetchone()
        if to_ts_row is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al obtener la fecha actual")
        
        to_ts = to_ts_row[0]

        # Fetch total sales for the day
        cursor.execute("""
                       SELECT COALESCE(SUM(total), 0) as total, count(*) as sales_count
                       FROM sales 
                       WHERE box_id = %s AND created_at >= %s AND created_at < %s
                       """, (current_user["box_id"], from_ts, to_ts))
        sales_row = cursor.fetchone()
        if sales_row is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al obtener las ventas del día")
        
        total_sales = sales_row[0] or Decimal('0.00')
        sales_count = sales_row[1] or 0

        # Fetch total returns for the day
        cursor.execute("""SELECT COALESCE(SUM(total),0), COUNT(*) 
                          FROM returns 
                          WHERE box_id = %s AND created_at > %s AND created_at <= %s""",(current_user["box_id"],from_ts, to_ts))
        returns_row = cursor.fetchone() or (Decimal("0.00"),0)
        total_returns = returns_row[0] or Decimal("0.00")
        returns_count = returns_row[1] or 0

        cursor.execute("""SELECT s.payment_method, COALESCE(SUM(r.total),0) 
                          FROM returns r JOIN sales s ON r.sale_id = s.id 
                          WHERE r.box_id = %s AND r.created_at > %s AND r.created_at <= %s 
                          GROUP BY s.payment_method""", (current_user["box_id"], from_ts, to_ts))
        
        returns_pm_rows = cursor.fetchall()
        total_returns_cash = Decimal("0.00")
        total_returns_card = Decimal("0.00")
        total_returns_transfer = Decimal("0.00")

        for row in returns_pm_rows:
            method_return = row[0].upper()
            amount_return = row[1] or Decimal("0.00")

            if method_return == "EFECTIVO":
                total_returns_cash = amount_return
            if method_return == "TARJETA":
                total_returns_card = amount_return
            if method_return == "TRANSFERENCIA":
                total_returns_transfer = amount_return

        # Fetch total cash payments for the day
        cursor.execute("""
            SELECT payment_method, COALESCE(SUM(total), 0) 
            FROM sales 
            WHERE box_id = %s AND created_at > %s AND created_at <= %s 
            GROUP BY payment_method
        """, (current_user["box_id"], from_ts, to_ts))
        rows = cursor.fetchall()
        total_cash = Decimal("0.00")
        total_card = Decimal("0.00")
        total_transfer = Decimal("0.00")

        for row in rows:
            method = row[0].upper()
            amount = row[1] or Decimal("0.00")

            if method == "EFECTIVO":
                total_cash = amount
            elif method == "TARJETA":
                total_card = amount
            elif method == "TRANSFERENCIA":
                total_transfer = amount

        # Fetch total expenses for the period
        cursor.execute("""
            SELECT COALESCE(SUM(amount), 0), COUNT(*)
            FROM expenses
            WHERE box_id = %s
            AND created_at > %s
            AND created_at <= %s
        """, (current_user["box_id"], from_ts, to_ts))

        expenses_row = cursor.fetchone() or (Decimal("0.00"), 0)

        total_expenses = expenses_row[0] or Decimal("0.00")
        expenses_count = expenses_row[1] or 0

        
        net_total = total_sales - total_returns
        cash_expected = total_cash - total_returns_cash - total_expenses + last_counted

        return {
            "from_ts": str(from_ts),
            "to_ts": str(to_ts),
            "total_sales": str(total_sales),
            "sales_count": sales_count,
            "total_returns": str(total_returns),
            "returns_count": returns_count,
            "total_expenses": str(total_expenses),
            "expenses_count": expenses_count,
            "total_cash": str(total_cash),
            "total_card": str(total_card),
            "total_transfer": str(total_transfer),
            "total_returns_cash": str(total_returns_cash),
            "total_returns_card": str(total_returns_card),
            "total_returns_transfer": str(total_returns_transfer),
            "cash_expected": str(cash_expected),
            "total_sales": str(net_total)
        }

        
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    finally:
        cursor.close()
        conn.close()

@router.post("/close")
def close_cashcut(data: CashcutClose, current_user: dict = Depends(get_current_user)):
    conn = get_conn()
    if conn is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al conectar a la base de datos")
    cursor = conn.cursor()

    try:
        # Fetch the latest cash cut timestamp
        cursor.execute("""
                       SELECT to_ts, cash_counted 
                       FROM cash_cuts 
                       WHERE box_id = %s 
                       ORDER BY to_ts DESC  
                       LIMIT 1
                       """, (current_user["box_id"],))
        latest_cut = cursor.fetchone()
        if latest_cut:
            from_ts = latest_cut[0]
            last_counted = latest_cut[1]
        else:
            from_ts = "1970-01-01"  
            last_counted = Decimal("0.00")

        cursor.execute("SELECT now()")
        to_ts_row = cursor.fetchone()
        if to_ts_row is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al obtener la fecha actual")
        to_ts = to_ts_row[0]

        # Fetch total sales for the day
        cursor.execute("""
                       SELECT COALESCE(SUM(total), 0) as total, count(*) as sales_count 
                       FROM sales  
                       WHERE box_id = %s AND created_at >= %s AND created_at < %s 
                       """, (current_user["box_id"], from_ts, to_ts))
        sales_row = cursor.fetchone()
        if sales_row is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al obtener las ventas del día")

        total_sales = sales_row[0] or Decimal('0.00')
        sales_count = sales_row[1] or 0

        # Fetch total returns for the day
        cursor.execute("""SELECT COALESCE(SUM(total),0), COUNT(*) 
                          FROM returns 
                          WHERE box_id = %s AND created_at > %s AND created_at <= %s """,(current_user["box_id"],from_ts, to_ts))
        returns_row = cursor.fetchone() or (Decimal("0.00"),0)
        total_returns = returns_row[0] or Decimal("0.00")
        returns_count = returns_row[1] or 0

        cursor.execute("""SELECT s.payment_method, COALESCE(SUM(r.total),0) 
                          FROM returns r JOIN sales s ON r.sale_id = s.id 
                          WHERE r.box_id = %s AND r.created_at > %s AND r.created_at <= %s 
                          GROUP BY s.payment_method""", (current_user["box_id"], from_ts, to_ts))
        
        returns_pm_rows = cursor.fetchall()
        total_returns_cash = Decimal("0.00")
        total_returns_card = Decimal("0.00")
        total_returns_transfer = Decimal("0.00")

        for row in returns_pm_rows:
            method_return = row[0].upper()
            amount_return = row[1] or Decimal("0.00")

            if method_return == "EFECTIVO":
                total_returns_cash = amount_return
            if method_return == "TARJETA":
                total_returns_card = amount_return
            if method_return == "TRANSFERENCIA":
                total_returns_transfer = amount_return

        # Fetch total cash payments for the day
        cursor.execute("""
            SELECT payment_method, COALESCE(SUM(total), 0) 
            FROM sales 
            WHERE box_id = %s AND created_at > %s AND created_at <= %s 
            GROUP BY payment_method
        """, (current_user["box_id"], from_ts, to_ts))
        rows = cursor.fetchall()

        total_cash = Decimal("0.00")
        total_card = Decimal("0.00")
        total_transfer = Decimal("0.00")

        for row in rows:
            method = row[0].upper()
            amount = row[1] or Decimal("0.00")

            if method == "EFECTIVO":
                total_cash = amount
            elif method == "TARJETA":
                total_card = amount
            elif method == "TRANSFERENCIA":
                total_transfer = amount

        # Fetch total expenses for the day
        cursor.execute("""SELECT COALESCE(SUM(amount), 0), COUNT(*) 
                          FROM expenses 
                          WHERE box_id = %s 
                          AND created_at > %s 
                           AND created_at <= %s""", (current_user["box_id"], from_ts, to_ts))

        expenses_row = cursor.fetchone() or (Decimal("0.00"), 0)

        total_expenses = expenses_row[0] or Decimal("0.00")
        expenses_count = expenses_row[1] or 0  
        
        cash_counted = Decimal(str(data.cash_counted))
        cash_expected = total_cash - total_returns_cash - total_expenses + last_counted
        difference =  cash_counted - cash_expected
        net_total = total_sales - total_returns

        # Insert new cash cut record
        cursor.execute("""INSERT INTO cash_cuts(from_ts, to_ts,
                                                total, total_cash, total_card, total_transfer,
                                                total_returns, total_returns_cash, total_returns_card, total_returns_transfer,
                                                total_expenses,net_total,sales_count, cash_expected, cash_counted, difference, comment, closed_by, box_id) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) 
            RETURNING id""", (from_ts, to_ts, 
                              total_sales, total_cash, total_card, total_transfer, 
                              total_returns, total_returns_cash, total_returns_card, total_returns_transfer, 
                              total_expenses, net_total, sales_count, cash_expected, cash_counted, difference, data.comment, current_user["sub"], current_user["box_id"]
        ))
        cut_id_row = cursor.fetchone()
        if cut_id_row is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al cerrar el corte de caja")
        cut_id = cut_id_row[0]
        
        conn.commit()   
        return {
            "cut_id": cut_id,
            "from_ts": str(from_ts),
            "to_ts": str(to_ts),
            "total_sales": str(total_sales),
            "sales_count": sales_count,
            "total_cash": str(total_cash),
            "total_card": str(total_card),
            "total_transfer": str(total_transfer),

            "total_returns": str(total_returns),
            "returns_count": returns_count,
            "total_returns_cash": str(total_returns_cash),
            "total_returns_card": str(total_returns_card),
            "total_returns_transfer": str(total_returns_transfer),
            "total_sales": str(net_total),
            "cash_expeted": str(cash_expected),
            "cash_counted": str(cash_counted),
            "difference": str(difference),
            "comment": data.comment
        }
    
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    finally:
        cursor.close()
        conn.close()