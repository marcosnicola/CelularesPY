from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
import os

app = FastAPI(
    title="API Celulares",
    description="Microservicio de Gestión de Inventario de Celulares - CRUD con FastAPI + SQLite",
    version="1.0",
)

# CORS: permite que el microservicio Frontend consuma esta API desde otro origen
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = os.getenv("DB_PATH", "celulares.db")
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""CREATE TABLE IF NOT EXISTS celulares (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    marca TEXT NOT NULL,
    modelo TEXT NOT NULL,
    precio REAL NOT NULL,
    color TEXT NOT NULL,
    almacenamiento INTEGER NOT NULL,
    ram INTEGER NOT NULL,
    stock INTEGER NOT NULL
)""")
conn.commit()


class Celular(BaseModel):
    marca: str
    modelo: str
    precio: float
    color: str
    almacenamiento: int
    ram: int
    stock: int


def row_to_dict(row):
    return {
        "id": row[0],
        "marca": row[1],
        "modelo": row[2],
        "precio": row[3],
        "color": row[4],
        "almacenamiento": row[5],
        "ram": row[6],
        "stock": row[7],
    }


@app.get("/")
def root():
    return {
        "servicio": "API Celulares",
        "version": "1.0",
        "docs": "/docs",
        "endpoints": ["/celulares", "/celulares/{id}"],
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/celulares")
def get_celulares():
    cursor.execute("SELECT * FROM celulares")
    return [row_to_dict(row) for row in cursor.fetchall()]


@app.get("/celulares/{celular_id}")
def get_celular(celular_id: int):
    cursor.execute("SELECT * FROM celulares WHERE id=?", (celular_id,))
    celular = cursor.fetchone()
    if not celular:
        raise HTTPException(status_code=404, detail="Celular no encontrado")
    return row_to_dict(celular)


@app.post("/celulares", status_code=201)
def create_celular(celular: Celular):
    cursor.execute(
        """INSERT INTO celulares (marca, modelo, precio, color, almacenamiento, ram, stock)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (celular.marca, celular.modelo, celular.precio, celular.color,
         celular.almacenamiento, celular.ram, celular.stock),
    )
    conn.commit()
    return {"mensaje": "Celular creado", "id": cursor.lastrowid, "celular": celular}


@app.put("/celulares/{celular_id}")
def update_celular(celular_id: int, celular: Celular):
    cursor.execute(
        """UPDATE celulares SET marca=?, modelo=?, precio=?, color=?,
           almacenamiento=?, ram=?, stock=? WHERE id=?""",
        (celular.marca, celular.modelo, celular.precio, celular.color,
         celular.almacenamiento, celular.ram, celular.stock, celular_id),
    )
    conn.commit()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Celular no encontrado")
    return {"mensaje": "Celular actualizado", "id": celular_id, "celular": celular}


@app.delete("/celulares/{celular_id}")
def delete_celular(celular_id: int):
    cursor.execute("DELETE FROM celulares WHERE id=?", (celular_id,))
    conn.commit()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Celular no encontrado")
    return {"mensaje": f"Celular {celular_id} eliminado"}


# Ejecutar local sin Docker:
#   uvicorn main:app --reload
# Documentación interactiva (Swagger): http://127.0.0.1:8000/docs
