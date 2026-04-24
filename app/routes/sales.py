from fastapi import APIRouter, HTTPException, status, Depends
from app.db.connection import get_conn
from app.schemas.sales_schema import SaleCreate, SaleResponse, SaleItemResponse
from app.core.security.deps import get_current_user
from app.schemas.ticket_schema import TicketResponse, TicketItem
from decimal import Decimal, ROUND_HALF_UP
import psycopg2

router = APIRouter(prefix="/sales", tags=["sales"])

def calc_discount(unit_price: Decimal, discount_type: str | None, discount_value: Decimal) -> Decimal:
    if not discount_type:
        return Decimal("0.00")
    
    dtype = discount_type.upper()

    if dtype == "PORCENTAJE":
        return (unit_price * (discount_value / Decimal("100"))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    elif dtype == "FIJO":
        return discount_value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return Decimal("0.00")

@router.post("/", response_model=SaleResponse, status_code=status.HTTP_201_CREATED)
def create_sale(sale: SaleCreate, current_user: dict = Depends(get_current_user)):
    sold_by = current_user["sub"]
    box_id = current_user["box_id"]

    conn = get_conn()
    if conn is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al conectar a la base de datos")   
    cursor = conn.cursor()

    q = Decimal("0.01")
    try:
        # Crear la venta en 0
        cursor.execute("INSERT INTO sales (total, sold_by, payment_method, box_id) VALUES (%s, %s, %s, %s) " \
                       "RETURNING id, created_at", (Decimal("0.00"), sold_by, sale.payment_method, box_id))
        sale_row = cursor.fetchone()
        if sale_row is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al crear la venta")    
        sale_id = sale_row[0]
        created_at = sale_row[1]
        payment_method = sale.payment_method
        total = Decimal("0.00")
        item_out : list[SaleItemResponse] = []

        # Procesar cada item
        for item in sale.items:
            product_id = item.product_id
            quantity = item.quantity            

            #Bloqueo products 
            cursor.execute("""
                            SELECT p.id, p.barcode, p.name, p.formula, p.stock, p.price_sell, p.active, p.is_service
                            FROM products p JOIN boxes b ON p.location_id = b.location_id
                            WHERE p.id = %s
                            AND b.id= %s FOR UPDATE""",(product_id, current_user["box_id"]))
            product_row = cursor.fetchone()

            if product_row is None:
                raise HTTPException(status_code=404, detail=f"Producto con ID {product_id} no encontrado")

            if product_row[6] is False:
                raise HTTPException(status_code=400, detail=f"El producto {product_row[2]} está inactivo")

            is_service = product_row[7]

            if not is_service and product_row[4] < quantity:
                raise HTTPException(status_code=409, detail=f"Stock insuficiente para {product_row[2]}")

            # Descuento 
            cursor.execute("SELECT type, COALESCE(value, 0) " \
                            "FROM discounts " \
                            "WHERE product_id = %s " \
                            "AND active = true " \
                            "AND CURRENT_DATE BETWEEN start_date AND end_date LIMIT 1", (product_id,))
            discount_row = cursor.fetchone()
            discount_type = discount_row[0] if discount_row else None
            discount_value = discount_row[1] if discount_row else 0

            stock_before = product_row[4]
            unit_price = product_row[5]
            if not isinstance(unit_price, Decimal):
                unit_price = Decimal(str(unit_price))

            if not isinstance(discount_value, Decimal):
                discount_value = Decimal(str(discount_value))

            discount_amount = (calc_discount(unit_price, discount_type, discount_value)).quantize(q, rounding=ROUND_HALF_UP)    
            unit_price_final = (unit_price - discount_amount).quantize(q, rounding=ROUND_HALF_UP)
            line_total = (unit_price_final * quantity).quantize(q, rounding=ROUND_HALF_UP)
            
            # Insertar item de venta
            cursor.execute("INSERT INTO sale_items (sale_id, product_id, qty, price, discount_amount,stock_before) " \
                           "VALUES (%s, %s, %s, %s, %s, %s)", (sale_id, product_id, quantity, unit_price, discount_amount, stock_before))  
            
            # Actualizar stock solo si no es un servicio
            if not is_service:
                cursor.execute("UPDATE products SET stock = stock - %s WHERE id = %s", (quantity, product_id))

            total += line_total

            item_out.append(SaleItemResponse(
                product_id=product_row[0],
                barcode=product_row[1],
                name=product_row[2],
                formula=product_row[3],
                quantity=item.quantity,
                stock_before=product_row[4],
                unit_price=str(unit_price),
                discount_amount=str(discount_amount),
                price_after_discount=str(unit_price_final),
                line_total=str(line_total)
            ))
        total = total.quantize(q, rounding=ROUND_HALF_UP)

        
        cash_received = None
        change_given = None

        if sale.payment_method.upper() == "EFECTIVO":
            if sale.cash_received is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Debes inidicar el efectivo recibido")
            cash_received = Decimal(str(sale.cash_received)).quantize(q, rounding=ROUND_HALF_UP)
            if cash_received < total:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El efectivo recibido no puede ser menor al total")

            change_given = (cash_received - total).quantize(q, rounding=ROUND_HALF_UP)

        # Actualizar total de la venta
        cursor.execute("UPDATE sales SET total = %s, cash_received = %s, change_given = %s WHERE id = %s", (total, cash_received, change_given, sale_id))
        conn.commit()   
        return SaleResponse(
            sale_id=sale_id,
            total=str(total),
            payment_method=payment_method,
            cash_received=str(cash_received),
            change_given=str(change_given),
            created_at=str(created_at),
            items=item_out
        )
    except HTTPException:
        conn.rollback()
        raise
    except psycopg2.Error as e:
        conn.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error de base de datos: {e}")   
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al crear la venta: {e}")  
    finally:
        cursor.close()
        conn.close()

@router.get("/{sale_id}", response_model=SaleResponse)
def get_sale(sale_id: int, current_user: dict = Depends(get_current_user)):
    box_id = current_user["box_id"]

    conn = get_conn()
    if conn is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail="Error al conectar a la base de datos")

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

        cursor.execute("""SELECT s.id, s.total, s.payment_method, s.created_at, s.cash_received, s.change_given
                          FROM sales s JOIN boxes b ON s.box_id = b.id
                          WHERE s.id = %s AND b.location_id = %s""", (sale_id, user_location_id))
        
        sales_row = cursor.fetchone()
        
        if sales_row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Venta no encontrada")
        
        cursor.execute("""SELECT si.product_id, p.barcode, p.name, p.formula, si.qty, si.price, si.discount_amount, si.stock_before
                          FROM sale_items si JOIN products p ON si.product_id = p.id
                          WHERE si.sale_id = %s""", (sale_id,))
        
        rows = cursor.fetchall()
        items_out: list[SaleItemResponse] = []

        for row in rows:
            product_id = row[0]
            barcode = row[1]
            name = row[2]
            formula = row[3]
            qty = row[4]
            unit_price = Decimal(str(row[5])).quantize(q, rounding=ROUND_HALF_UP)
            discount_amount = Decimal(str(row[6])).quantize(q, rounding=ROUND_HALF_UP)
            stock_before = row[7]

            price_after_discount = (unit_price - discount_amount).quantize(q, rounding=ROUND_HALF_UP)
            line_total = (price_after_discount * qty).quantize(q, rounding=ROUND_HALF_UP)

            items_out.append(SaleItemResponse(
                product_id= product_id,
                barcode = barcode,
                name = name,
                formula = formula,
                quantity = qty,
                stock_before = stock_before,
                unit_price = str(unit_price),
                discount_amount = str(discount_amount),
                price_after_discount = str(price_after_discount),
                line_total = str(line_total)
            ))
        return SaleResponse(
            sale_id = sales_row[0],
            total=str(Decimal(str(sales_row[1])).quantize(q, rounding=ROUND_HALF_UP)),
            payment_method=sales_row[2],
            cash_received=str(sales_row[4]) if sales_row[4] is not None else None,
            change_given=str(sales_row[5]) if sales_row[5] is not None else None,
            created_at=str(sales_row[3]),
            items=items_out    
        )

    except HTTPException:
        raise 
    except psycopg2.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail=f"Error de base de datos: {e}")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail=f"Error al obtener la venta: {e}")
    finally:
        cursor.close()
        conn.close()

@router.get("/{sale_id}/ticket", response_model=TicketResponse)
def get_sale_ticket(sale_id: int, current_user: dict = Depends(get_current_user)):

    conn = get_conn()
    if conn is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al conectar con la base de datos")
    cursor = conn.cursor()
    q = Decimal("0.01")

    try:

        # venta + caja + sucursal + usuario

        cursor.execute("""SELECT s.id, s.total, s.payment_method, s.created_at, s.cash_received, s.change_given, u.name, l.name, l.address
                          FROM sales s
                          JOIN users u ON s.sold_by = u.id
                          JOIN boxes b ON s.box_id = b.id
                          JOIN locations l ON b.location_id = l.id
                          WHERE s.id = %s""", (sale_id,))

        row = cursor.fetchone()

        if row is None:
            raise HTTPException(404, "Venta no encontrada")

        total = Decimal(str(row[1]))
        payment_method = row[2]
        created_at = row[3]
        cash_received = row[4]
        change_given = row[5]
        employee = row[6]
        location_name = row[7]
        location_address = row[8]

        # items

        cursor.execute("""SELECT si.qty, p.name, si.price, si.discount_amount
                          FROM sale_items si
                          JOIN products p ON si.product_id = p.id
                          WHERE si.sale_id = %s""", (sale_id,))

        rows = cursor.fetchall()

        items = []

        total_base = Decimal("0.00")
        total_discount = Decimal("0.00")

        for row in rows:

            qty = row[0]
            name = row[1]
            price = Decimal(str(row[2]))
            discount = Decimal(str(row[3]))

            base = price * qty
            disc = discount * qty
            total_line = (price - discount) * qty

            total_base += base
            total_discount += disc

            items.append(
                TicketItem(
                    quantity=qty,
                    description=name,
                    price=str(price),
                    discount=str(disc),
                    total=str(total_line)
                )
            )

        return TicketResponse(

            logo_url="/static/logo.png",

            location_name=location_name,
            location_address=location_address,

            employee=employee,
            payment_method=payment_method,
            created_at=str(created_at),

            items=items,

            total_base=str(total_base.quantize(q)),
            total_discount=str(total_discount.quantize(q)),
            total=str(total.quantize(q)),

            cash_received=str(cash_received) if cash_received else None,
            change_given=str(change_given) if change_given else None,
        )

    finally:
        cursor.close()
        conn.close()