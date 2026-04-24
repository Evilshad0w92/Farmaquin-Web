from fastapi import FastAPI
from app.db.connection import get_conn
from fastapi.middleware.cors import CORSMiddleware
from app.routes import auth, pos, returns, users, sales, cashcut, expenses, inventory, provider, section, reports
from fastapi.staticfiles import StaticFiles

app = FastAPI(title = 'Farmaquin ERP')
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://farmaquin.netlify.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static",StaticFiles(directory = "app/static"), name = "static")

app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(auth.router)
app.include_router(pos.router)
app.include_router(sales.router)
app.include_router(cashcut.router)
app.include_router(returns.router)
app.include_router(expenses.router)
app.include_router(inventory.router)
app.include_router(provider.router)
app.include_router(section.router)
app.include_router(reports.router)

@app.get("/")
def inicio():
    return {"mensaje": "ERP Activo"}

