"""Microservicio Stock: maneja exclusivamente las cantidades del inventario.
No sabe nada del catálogo de celulares; solo guarda celular_id + cantidad.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
import os

app = FastAPI(
    title="Microservicio Stock",
    description="Gestión de cantidades del inventario. Sumar, restar y alertas de stock bajo.",
    version="1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = os.getenv("DB_PATH", "stock.db")
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""CREATE TABLE IF NOT EXISTS stock (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    celular_id  INTEGER UNIQUE NOT NULL,
    cantidad    INTEGER NOT NULL DEFAULT 0,
    stock_minimo INTEGER NOT NULL DEFAULT 5
)""")
conn.commit()


class StockEntry(BaseModel):
    celular_id: int
    cantidad: int = 0
    stock_minimo: int = 5


def row_to_dict(row):
    return {
        "id": row[0],
        "celular_id": row[1],
        "cantidad": row[2],
        "stock_minimo": row[3],
        "alerta": row[2] <= row[3],
    }


@app.get("/health")
def health():
    return {"status": "ok", "servicio": "stock"}


@app.get("/stock")
def get_stock():
    cursor.execute("SELECT * FROM stock ORDER BY celular_id")
    return [row_to_dict(r) for r in cursor.fetchall()]


@app.get("/stock/alertas")
def get_alertas():
    """Retorna celulares cuyo stock está en o por debajo del mínimo."""
    cursor.execute("SELECT * FROM stock WHERE cantidad <= stock_minimo ORDER BY cantidad")
    return [row_to_dict(r) for r in cursor.fetchall()]


@app.get("/stock/{celular_id}")
def get_stock_celular(celular_id: int):
    cursor.execute("SELECT * FROM stock WHERE celular_id=?", (celular_id,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Stock no encontrado para este celular")
    return row_to_dict(row)


@app.post("/stock", status_code=201)
def create_stock(entry: StockEntry):
    try:
        cursor.execute(
            "INSERT INTO stock (celular_id, cantidad, stock_minimo) VALUES (?,?,?)",
            (entry.celular_id, entry.cantidad, entry.stock_minimo),
        )
        conn.commit()
        return {"mensaje": "Stock creado", "celular_id": entry.celular_id, "cantidad": entry.cantidad}
    except Exception:
        raise HTTPException(status_code=400, detail="Ya existe una entrada de stock para este celular")


@app.patch("/stock/{celular_id}/agregar")
def agregar_stock(celular_id: int, cantidad: int):
    cursor.execute("SELECT * FROM stock WHERE celular_id=?", (celular_id,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Stock no encontrado")
    if cantidad <= 0:
        raise HTTPException(status_code=400, detail="La cantidad debe ser mayor a 0")
    nueva = row[2] + cantidad
    cursor.execute("UPDATE stock SET cantidad=? WHERE celular_id=?", (nueva, celular_id))
    conn.commit()
    return {
        "mensaje": "Stock incrementado",
        "celular_id": celular_id,
        "cantidad_anterior": row[2],
        "cantidad_nueva": nueva,
    }


@app.patch("/stock/{celular_id}/restar")
def restar_stock(celular_id: int, cantidad: int):
    cursor.execute("SELECT * FROM stock WHERE celular_id=?", (celular_id,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Stock no encontrado")
    if cantidad <= 0:
        raise HTTPException(status_code=400, detail="La cantidad debe ser mayor a 0")
    if row[2] < cantidad:
        raise HTTPException(
            status_code=400,
            detail=f"Stock insuficiente. Disponible: {row[2]}, solicitado: {cantidad}",
        )
    nueva = row[2] - cantidad
    cursor.execute("UPDATE stock SET cantidad=? WHERE celular_id=?", (nueva, celular_id))
    conn.commit()
    return {
        "mensaje": "Stock reducido",
        "celular_id": celular_id,
        "cantidad_anterior": row[2],
        "cantidad_nueva": nueva,
    }


@app.patch("/stock/{celular_id}/minimo")
def actualizar_minimo(celular_id: int, stock_minimo: int):
    cursor.execute("SELECT id FROM stock WHERE celular_id=?", (celular_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Stock no encontrado")
    cursor.execute("UPDATE stock SET stock_minimo=? WHERE celular_id=?", (stock_minimo, celular_id))
    conn.commit()
    return {"mensaje": "Stock mínimo actualizado", "celular_id": celular_id, "stock_minimo": stock_minimo}


@app.delete("/stock/{celular_id}")
def delete_stock(celular_id: int):
    cursor.execute("DELETE FROM stock WHERE celular_id=?", (celular_id,))
    conn.commit()
    return {"mensaje": f"Entrada de stock del celular {celular_id} eliminada"}
