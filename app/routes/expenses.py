from fastapi import APIRouter, HTTPException, status, Depends
from decimal import Decimal, ROUND_HALF_UP
import psycopg2

from app.db.connection import get_conn
from app.schemas.expense_schema import ExpenseCreate, ExpenseResponse, ExpenseUpdate
from app.core.security.deps import get_current_user

router = APIRouter(prefix="/expenses", tags=["expenses"])


@router.post("/", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
def create_expense(expense: ExpenseCreate, current_user: dict = Depends(get_current_user)):
    conn = get_conn()
    if conn is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al conectar a la base de datos"
        )

    cursor = conn.cursor()
    q = Decimal("0.01")

    try:
        user_id = current_user["sub"]
        box_id = current_user["box_id"]
        amount = Decimal(str(expense.amount)).quantize(q, rounding=ROUND_HALF_UP)

        cursor.execute("""
            INSERT INTO expenses(amount, description, user_id, expense_type, box_id)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, amount, description, created_at, expense_type
        """, (amount, expense.description, user_id, expense.expense_type, box_id))

        row = cursor.fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No se pudo registrar el gasto"
            )

        conn.commit()

        return ExpenseResponse(
            id=row[0],
            amount=str(Decimal(str(row[1])).quantize(q, rounding=ROUND_HALF_UP)),
            description=row[2],
            created_at=str(row[3]),
            expense_type=row[4]
        )

    except HTTPException:
        conn.rollback()
        raise
    except psycopg2.Error as e:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error de base de datos: {e}"
        )
    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al registrar el gasto: {e}"
        )
    finally:
        cursor.close()
        conn.close()


@router.get("/search")
def search(query: str = "", current_user: dict = Depends(get_current_user)):
    conn = get_conn()
    if conn is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al conectar a la base de datos"
        )

    cursor = conn.cursor()
    q = Decimal("0.01")

    try:
        box_id = current_user["box_id"]

        cursor.execute("""
            SELECT id, amount, description, created_at, expense_type
            FROM expenses
            WHERE box_id = %s
              AND (description ILIKE %s OR expense_type ILIKE %s) AND active = TRUE
        """, (box_id, f"%{query}%", f"%{query}%"))

        rows = cursor.fetchall()

        return [
            ExpenseResponse(
                id=row[0],
                amount=str(Decimal(str(row[1])).quantize(q, rounding=ROUND_HALF_UP)),
                description=row[2],
                created_at=str(row[3]),
                expense_type=row[4]
            )
            for row in rows
        ]

    except psycopg2.Error as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error de base de datos: {e}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al buscar gastos: {e}"
        )
    finally:
        cursor.close()
        conn.close()


@router.post("/update", response_model=ExpenseResponse, status_code=status.HTTP_200_OK)
def update_expense(expense: ExpenseUpdate, current_user: dict = Depends(get_current_user)):
    conn = get_conn()
    if conn is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al conectar a la base de datos"
        )

    cursor = conn.cursor()
    q = Decimal("0.01")

    try:
        box_id = current_user["box_id"]
        amount = Decimal(str(expense.amount)).quantize(q, rounding=ROUND_HALF_UP)

        cursor.execute("""
            UPDATE expenses
            SET amount = %s, description = %s, expense_type = %s
            WHERE id = %s AND box_id = %s
            RETURNING id, amount, description, created_at, expense_type
        """, (amount, expense.description, expense.expense_type, expense.id, box_id))

        row = cursor.fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Gasto no encontrado o no pertenece a esta caja"
            )

        conn.commit()

        return ExpenseResponse(
            id=row[0],
            amount=str(Decimal(str(row[1])).quantize(q, rounding=ROUND_HALF_UP)),
            description=row[2],
            created_at=str(row[3]),
            expense_type=row[4]
        )

    except HTTPException:
        conn.rollback()
        raise
    except psycopg2.Error as e:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error de base de datos: {e}"
        )
    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar el gasto: {e}"
        )
    finally:
        cursor.close()
        conn.close()

@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(expense_id: int, current_user: dict = Depends(get_current_user)):
    conn = get_conn()
    if conn is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al conectar a la base de datos"
        )

    cursor = conn.cursor()

    try:
        box_id = current_user["box_id"]

        cursor.execute("""
            UPDATE expenses
            SET active = FALSE 
            WHERE id = %s AND box_id = %s AND active = TRUE
            RETURNING id
        """, (expense_id, box_id))

        row = cursor.fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Gasto no encontrado o no pertenece a esta caja"
            )

        conn.commit()
        return

    except HTTPException:
        conn.rollback()
        raise
    except psycopg2.Error as e:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error de base de datos: {e}"
        )
    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar el gasto: {e}"
        )
    finally:
        cursor.close()
        conn.close()