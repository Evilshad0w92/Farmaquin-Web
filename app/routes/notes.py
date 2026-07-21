from fastapi import APIRouter, HTTPException, status, Depends
from app.db.connection import get_conn
from app.core.security.deps import get_current_user
from pydantic import BaseModel
import psycopg2

router = APIRouter(prefix="/notes", tags=["notes"])


class NoteUpdate(BaseModel):
    content: str


class TaskCreate(BaseModel):
    description: str


class TaskUpdate(BaseModel):
    description: str
    done: bool


def _get_location(cursor, box_id: int) -> int:
    cursor.execute("SELECT location_id FROM boxes WHERE id = %s", (box_id,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Caja no encontrada")
    return row[0]


@router.get("/board")
def get_board(current_user: dict = Depends(get_current_user)):
    conn = get_conn()
    if conn is None:
        raise HTTPException(status_code=500, detail="Error al conectar a la base de datos")
    cursor = conn.cursor()
    try:
        location_id = _get_location(cursor, current_user["box_id"])

        cursor.execute("""
            SELECT sn.user_id, u.name, sn.content, sn.updated_at
            FROM shift_notes sn
            JOIN users u ON u.id = sn.user_id
            WHERE sn.location_id = %s AND sn.content <> ''
            ORDER BY sn.updated_at DESC
        """, (location_id,))
        notes = [
            {"user_id": str(r[0]), "user_name": r[1], "content": r[2], "updated_at": str(r[3])}
            for r in cursor.fetchall()
        ]

        cursor.execute("""
            SELECT st.id, st.user_id, u.name, st.description, st.done, st.created_at
            FROM shift_tasks st
            JOIN users u ON u.id = st.user_id
            WHERE st.location_id = %s
            ORDER BY st.done ASC, st.created_at DESC
        """, (location_id,))
        tasks = [
            {"id": r[0], "user_id": str(r[1]), "user_name": r[2],
             "description": r[3], "done": r[4], "created_at": str(r[5])}
            for r in cursor.fetchall()
        ]

        return {"notes": notes, "tasks": tasks}
    except HTTPException:
        raise
    except psycopg2.Error as e:
        raise HTTPException(status_code=500, detail=f"Error de base de datos: {e}")
    finally:
        cursor.close()
        conn.close()


@router.get("/mine")
def get_mine(current_user: dict = Depends(get_current_user)):
    conn = get_conn()
    if conn is None:
        raise HTTPException(status_code=500, detail="Error al conectar a la base de datos")
    cursor = conn.cursor()
    try:
        user_id = current_user["sub"]
        location_id = _get_location(cursor, current_user["box_id"])

        cursor.execute(
            "SELECT content FROM shift_notes WHERE user_id = %s::uuid AND location_id = %s",
            (user_id, location_id)
        )
        row = cursor.fetchone()
        note = row[0] if row else ""

        cursor.execute("""
            SELECT id, description, done FROM shift_tasks
            WHERE user_id = %s::uuid AND location_id = %s
            ORDER BY done ASC, created_at DESC
        """, (user_id, location_id))
        tasks = [{"id": r[0], "description": r[1], "done": r[2]} for r in cursor.fetchall()]

        return {"note": note, "tasks": tasks}
    except HTTPException:
        raise
    except psycopg2.Error as e:
        raise HTTPException(status_code=500, detail=f"Error de base de datos: {e}")
    finally:
        cursor.close()
        conn.close()


@router.put("/mine")
def update_note(data: NoteUpdate, current_user: dict = Depends(get_current_user)):
    conn = get_conn()
    if conn is None:
        raise HTTPException(status_code=500, detail="Error al conectar a la base de datos")
    cursor = conn.cursor()
    try:
        user_id = current_user["sub"]
        location_id = _get_location(cursor, current_user["box_id"])

        cursor.execute("""
            INSERT INTO shift_notes (user_id, location_id, content, updated_at)
            VALUES (%s::uuid, %s, %s, NOW())
            ON CONFLICT (user_id, location_id)
            DO UPDATE SET content = EXCLUDED.content, updated_at = NOW()
        """, (user_id, location_id, data.content))
        conn.commit()
        return {"ok": True}
    except psycopg2.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error de base de datos: {e}")
    finally:
        cursor.close()
        conn.close()


@router.post("/tasks", status_code=201)
def add_task(data: TaskCreate, current_user: dict = Depends(get_current_user)):
    if not data.description.strip():
        raise HTTPException(status_code=400, detail="La descripción no puede estar vacía")
    conn = get_conn()
    if conn is None:
        raise HTTPException(status_code=500, detail="Error al conectar a la base de datos")
    cursor = conn.cursor()
    try:
        user_id = current_user["sub"]
        location_id = _get_location(cursor, current_user["box_id"])

        cursor.execute("""
            INSERT INTO shift_tasks (user_id, location_id, description)
            VALUES (%s::uuid, %s, %s) RETURNING id
        """, (user_id, location_id, data.description.strip()))
        row = cursor.fetchone()
        conn.commit()
        return {"id": row[0], "description": data.description.strip(), "done": False}
    except psycopg2.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error de base de datos: {e}")
    finally:
        cursor.close()
        conn.close()


@router.put("/tasks/{task_id}")
def update_task(task_id: int, data: TaskUpdate, current_user: dict = Depends(get_current_user)):
    conn = get_conn()
    if conn is None:
        raise HTTPException(status_code=500, detail="Error al conectar a la base de datos")
    cursor = conn.cursor()
    try:
        user_id = current_user["sub"]
        cursor.execute("""
            UPDATE shift_tasks SET description = %s, done = %s
            WHERE id = %s AND user_id = %s::uuid
        """, (data.description, data.done, task_id, user_id))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Tarea no encontrada")
        conn.commit()
        return {"ok": True}
    except HTTPException:
        conn.rollback()
        raise
    except psycopg2.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error de base de datos: {e}")
    finally:
        cursor.close()
        conn.close()


@router.delete("/tasks/{task_id}")
def delete_task(task_id: int, current_user: dict = Depends(get_current_user)):
    conn = get_conn()
    if conn is None:
        raise HTTPException(status_code=500, detail="Error al conectar a la base de datos")
    cursor = conn.cursor()
    try:
        user_id = current_user["sub"]
        cursor.execute(
            "DELETE FROM shift_tasks WHERE id = %s AND user_id = %s::uuid",
            (task_id, user_id)
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Tarea no encontrada")
        conn.commit()
        return {"ok": True}
    except HTTPException:
        conn.rollback()
        raise
    except psycopg2.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error de base de datos: {e}")
    finally:
        cursor.close()
        conn.close()
