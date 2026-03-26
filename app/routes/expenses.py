from fastapi import APIRouter, HTTPException, status, Depends
from decimal import Decimal, ROUND_HALF_UP
import psycopg2

from app.db.connection import get_conn
from app.schemas.expense_schema import ExpenseCreate, ExpenseResponse
from app.core.security.deps import get_current_user

router = APIRouter(prefix="/expenses", tags=["expenses"])

@router.post("/", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
def create_expense(expense: ExpenseCreate, current_user: dict = Depends(get_current_user)):
    conn = get_conn()
    if conn is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al conectar a la base de datos")
    cursor = conn.cursor()
    q = Decimal("0.01")

    try:
        user_id = current_user["sub"]
        box_id = current_user["box_id"]
        amount = Decimal(str(expense.amount)).quantize(q, rounding = ROUND_HALF_UP)

        cursor.execute("""INSERT INTO expenses(amount, description, user_id, expense_type, box_id)
                          VALUES (%s, %s, %s, %s, %s)
                          RETURNING id, amount, description, created_at, expense_type""", (amount, expense.description, user_id, expense.expense_type, box_id))
                
        row = cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail= "No se pudo registrar el gasto")
        conn.commit()

        return ExpenseResponse(
            id = row[0], 
            amount = str(Decimal(str(row[1])).quantize(q, rounding=ROUND_HALF_UP)), 
            description = row[2], 
            created_at = str(row[3]), 
            expense_type = row[4]
        )
    except HTTPException:
        conn.rollback()
        raise
    except psycopg2.Error as e:
        conn.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error de base de datos: {e}")
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al registrar el gasto {e}")
    finally:
        cursor.close()
        conn.close()



