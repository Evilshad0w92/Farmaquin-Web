from fastapi import APIRouter, HTTPException, status, Depends
from app.db.connection import get_conn
from app.schemas.return_schema import ReturnCreate, ReturnResponse, ReturnItemResponse
from app.schemas.ticket_schema import TicketReturnResponse, TicketItemReturn
from app.core.security.deps import get_current_user
from decimal import Decimal, ROUND_HALF_UP
import psycopg2

router = APIRouter(prefix="/returns", tags=["returns"])


@router.post("/", response_model=ReturnResponse, status_code=status.HTTP_201_CREATED)
def create_return(data: ReturnCreate, current_user: dict = Depends(get_current_user)):

    conn = get_conn()
    if conn is None:
        raise HTTPException(500, "Error DB")

    cursor = conn.cursor()

    try:

        box_id = current_user["box_id"]
        user_id = current_user["sub"]

        cursor.execute("""SELECT location_id 
                          FROM boxes 
                          WHERE id = %s""", (box_id,))
                          
        user_box_row = cursor.fetchone()

        if user_box_row is None:
            raise HTTPException(400, "Caja del usuario no encontrada")

        user_location_id = user_box_row[0]

        cursor.execute("""SELECT s.id, s.box_id 
                          FROM sales s 
                          JOIN boxes b ON b.id = s.box_id 
                          WHERE s.id = %s 
                          AND b.location_id = %s""",(data.sale_id, user_location_id)
        )
        sale_row = cursor.fetchone()
        if sale_row is None:
            raise HTTPException(404, "Venta no encontrada")

        total = Decimal("0.00")
        q = Decimal("0.01")

        items_out = []

        # crear encabezado en 0
        cursor.execute(
            """
            INSERT INTO returns (sale_id, box_id, processed_by, total, reason)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, created_at
            """,
            (data.sale_id, box_id, user_id, Decimal("0.00"), data.reason)
        )
        return_row = cursor.fetchone()
        if return_row is None:
            raise HTTPException(500, "No se pudo encontrar la devolucion")

        return_id = return_row[0]
        created_at = return_row[1]

        # procesar items
        for item in data.items:

            product_id = item.product_id
            qty = item.quantity

            cursor.execute("""SELECT si.qty, si.price, p.barcode, p.name, p.formula
                              FROM sale_items si
                              JOIN products p ON p.id = si.product_id
                              WHERE si.sale_id = %s AND si.product_id = %s""", (data.sale_id, product_id))

            sale_item = cursor.fetchone()

            if sale_item is None:
                raise HTTPException(404, "Producto no está en la venta")

            sold_qty = sale_item[0]
            price = Decimal(str(sale_item[1]))
            barcode = sale_item[2]
            name = sale_item[3]
            formula = sale_item[4]

            cursor.execute("""SELECT COALESCE(SUM(ri.qty),0)
                              FROM return_items ri
                              JOIN returns r ON r.id = ri.return_id
                              WHERE r.sale_id = %s
                              AND ri.product_id = %s""",(data.sale_id, product_id))

            returned_row = cursor.fetchone()
            returned_qty = returned_row[0] if returned_row is not None else 0

            available = sold_qty - returned_qty

            if available == 0:
                raise HTTPException(409,f"Ya se devolvio la totalidad de ese producto en la venta")
                
            elif qty > available:
                raise HTTPException(409,f"No puedes devolver {qty}, solo {available}")

            subtotal = (price * qty).quantize(q, rounding=ROUND_HALF_UP)

            # insertar return_items
            cursor.execute(
                """
                INSERT INTO return_items
                (return_id, product_id, qty, price, subtotal)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (return_id, product_id, qty, price, subtotal)
            )

            # regresar stock
            cursor.execute(
                """
                UPDATE products
                SET stock = stock + %s
                WHERE id = %s
                """,
                (qty, product_id)
            )

            total += subtotal

            items_out.append(
                ReturnItemResponse(
                    product_id=product_id,
                    barcode = barcode,
                    name = name,
                    formula = formula,
                    quantity = qty,
                    price=str(price),
                    subtotal=str(subtotal)
                )
            )

        total = total.quantize(q)

        # actualizar total
        cursor.execute(
            "UPDATE returns SET total = %s WHERE id = %s",
            (total, return_id)
        )

        conn.commit()

        return ReturnResponse(
            return_id=return_id,
            sale_id=data.sale_id,
            total=str(total),
            reason=data.reason,
            created_at=str(created_at),
            items=items_out
        )

    except HTTPException:
        conn.rollback()
        raise

    except psycopg2.Error as e:
        conn.rollback()
        raise HTTPException(500, f"DB error: {e}")

    except Exception as e:
        conn.rollback()
        raise HTTPException(500, str(e))

    finally:
        cursor.close()
        conn.close()

@router.get("/{returns_id}", response_model=ReturnResponse)
def get_returns(returns_id: int, current_user: dict = Depends(get_current_user)):
    box_id = current_user["box_id"]

    conn = get_conn()
    if conn is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail= "Error al conectar a la base de datos")
    
    cursor = conn.cursor()
    q = Decimal("0.01")

    try:
        cursor.execute("""SELECT location_id
                          FROM boxes
                          WHERE id = %s""", (box_id,))
        user_box_row = cursor.fetchone()

        if user_box_row is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Caja no encontrada")
        
        user_location_id = user_box_row[0]
        
        cursor.execute("""SELECT r.id, r.sale_id, r.processed_by, r.total, r.reason, r.created_at
                          FROM returns r JOIN boxes b ON r.box_id = b.id
                          WHERE r.id = %s AND b.location_id = %s""",(returns_id, user_location_id))
        
        returns_row = cursor.fetchone()

        if returns_row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Retorno de producto no encontrado")
        
        cursor.execute("""SELECT ri.product_id, p.barcode, p.name, p.formula, ri.qty, ri.price, ri.subtotal
                          FROM return_items ri JOIN products p ON ri.product_id = p.id
                          WHERE ri.return_id = %s""", (returns_id,))
        
        rows = cursor.fetchall()
        items_out: list[ReturnItemResponse] = []

        for row in rows:
            product_id = row[0]
            barcode = row[1]
            name = row[2]
            formula = row[3]
            qty = row[4]
            price = Decimal(str(row[5])).quantize(q, rounding=ROUND_HALF_UP)
            subtotal = Decimal(str(row[6])).quantize(q, rounding=ROUND_HALF_UP)

            items_out.append(ReturnItemResponse(
                product_id = product_id,
                barcode = barcode,
                name = name,
                formula = formula,
                quantity = qty,
                price = str(price),
                subtotal = str(subtotal)
            ))
        
        return ReturnResponse(
                return_id = returns_row[0],
                sale_id = returns_row[1],
                total = str(Decimal(str(returns_row[3])).quantize(q, rounding=ROUND_HALF_UP)),
                reason = returns_row[4],
                created_at = str(returns_row[5]),
                items = items_out
        )


    except HTTPException:
        raise 
    except psycopg2.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail=f"Error de base de datos: {e}")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail=f"Error al obtener la devolucion: {e}")
    finally:
        cursor.close()
        conn.close()


@router.get("/{returns_id}/ticket", response_model=TicketReturnResponse)
def get_return_ticket(returns_id: int, current_user: dict = Depends(get_current_user)):

    conn = get_conn()
    if conn is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al conectar con la base de datos"
        )

    cursor = conn.cursor()
    q = Decimal("0.01")

    try:
        cursor.execute("""
            SELECT r.id, r.total, r.created_at, u.name, l.name, l.address
            FROM returns r
            JOIN users u ON r.processed_by = u.id
            JOIN boxes b ON r.box_id = b.id
            JOIN locations l ON b.location_id = l.id
            WHERE r.id = %s
        """, (returns_id,))
        row = cursor.fetchone()

        if row is None:
            raise HTTPException(status_code=404, detail="Retorno no encontrado")

        total = Decimal(str(row[1])).quantize(q, rounding=ROUND_HALF_UP)
        created_at = row[2]
        employee = row[3]
        location_name = row[4]
        location_address = row[5]

        cursor.execute("""
            SELECT ri.qty, p.name, ri.price, ri.subtotal
            FROM return_items ri
            JOIN products p ON ri.product_id = p.id
            WHERE ri.return_id = %s
        """, (returns_id,))
        rows = cursor.fetchall()

        items = []
        total_base = Decimal("0.00")

        for row in rows:
            qty = row[0]
            name = row[1]
            price = Decimal(str(row[2])).quantize(q, rounding=ROUND_HALF_UP)
            total_line = Decimal(str(row[3])).quantize(q, rounding=ROUND_HALF_UP)

            total_base += total_line

            items.append(
                TicketItemReturn(
                    quantity=qty,
                    description=name,
                    price=str(price),
                    total=str(total_line)
                )
            )

        return TicketReturnResponse(
            logo_url="/static/logo.png",
            location_name=location_name,
            location_address=location_address,
            employee=employee,
            created_at=str(created_at),
            items=items,
            total_base=str(total_base.quantize(q, rounding=ROUND_HALF_UP)),
            total=str(total)
        )

    except HTTPException:
        raise
    except psycopg2.Error as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error de base de datos: {e}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener ticket de devolución: {e}"
        )
    finally:
        cursor.close()
        conn.close()