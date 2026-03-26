from fastapi import FastAPI
from app.db.connection import get_conn
from app.routes import auth, pos, returns, users, sales, cashcut, expenses
from fastapi.staticfiles import StaticFiles

app = FastAPI(title = 'Farmaquin ERP')
app.mount("/static",StaticFiles(directory = "app/static"), name = "static")

app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(auth.router)
app.include_router(pos.router)
app.include_router(sales.router)
app.include_router(cashcut.router)
app.include_router(returns.router)
app.include_router(expenses.router)

@app.get("/")
def inicio():
    return {"mensaje": "ERP Activo"}

