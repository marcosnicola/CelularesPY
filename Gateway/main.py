"""API Gateway: punto único de entrada para todos los microservicios.

El Frontend SOLO habla con el Gateway (puerto 8080).
El Gateway enruta las peticiones al microservicio correspondiente.

Rutas:
  /celulares/*  → Microservicio Celulares (8001)
  /stock/*      → Microservicio Stock    (8002)
  /reportes/*   → Microservicio Reportes (8003)

Además orquesta operaciones multi-servicio:
  POST /celulares   → crea celular en Celulares, luego crea entrada en Stock
  DELETE /celulares → elimina de Celulares y de Stock
"""

import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx

app = FastAPI(
    title="API Gateway - Inventario de Celulares",
    description="Punto único de entrada. Enruta al microservicio correcto.",
    version="1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

CELULARES_URL = os.getenv("CELULARES_URL", "http://localhost:8001")
STOCK_URL     = os.getenv("STOCK_URL",     "http://localhost:8002")
REPORTES_URL  = os.getenv("REPORTES_URL",  "http://localhost:8003")


def _raise_from(r: httpx.Response):
    """Propaga el error del microservicio al cliente."""
    try:
        detail = r.json().get("detail", r.text)
    except Exception:
        detail = r.text
    raise HTTPException(status_code=r.status_code, detail=detail)


# ─────────────────────────────────────────────
#  Info del gateway
# ─────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "servicio": "API Gateway",
        "microservicios": {
            "celulares": f"{CELULARES_URL}",
            "stock":     f"{STOCK_URL}",
            "reportes":  f"{REPORTES_URL}",
        },
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    """Verifica el estado de todos los microservicios."""
    resultados = {}
    async with httpx.AsyncClient(timeout=3) as client:
        for nombre, url in [("celulares", CELULARES_URL), ("stock", STOCK_URL), ("reportes", REPORTES_URL)]:
            try:
                r = await client.get(f"{url}/health")
                resultados[nombre] = "ok" if r.status_code == 200 else "error"
            except httpx.RequestError:
                resultados[nombre] = "no disponible"
    return {"gateway": "ok", "microservicios": resultados}


# ─────────────────────────────────────────────
#  Rutas de Celulares
# ─────────────────────────────────────────────

@app.get("/celulares")
async def get_celulares():
    async with httpx.AsyncClient(timeout=5) as client:
        r = await client.get(f"{CELULARES_URL}/celulares")
    if r.status_code != 200:
        _raise_from(r)
    return r.json()


@app.get("/celulares/{celular_id}")
async def get_celular(celular_id: int):
    async with httpx.AsyncClient(timeout=5) as client:
        r = await client.get(f"{CELULARES_URL}/celulares/{celular_id}")
    if r.status_code != 200:
        _raise_from(r)
    return r.json()


@app.post("/celulares", status_code=201)
async def create_celular(request: Request):
    """Crea el celular y automáticamente registra su entrada de stock en 0."""
    body = await request.json()
    async with httpx.AsyncClient(timeout=5) as client:
        r = await client.post(f"{CELULARES_URL}/celulares", json=body)
        if r.status_code not in (200, 201):
            _raise_from(r)
        celular_id = r.json()["id"]
        # Crear entrada de stock para este nuevo celular
        await client.post(
            f"{STOCK_URL}/stock",
            json={"celular_id": celular_id, "cantidad": 0, "stock_minimo": 5},
        )
    return r.json()


@app.put("/celulares/{celular_id}")
async def update_celular(celular_id: int, request: Request):
    body = await request.json()
    async with httpx.AsyncClient(timeout=5) as client:
        r = await client.put(f"{CELULARES_URL}/celulares/{celular_id}", json=body)
    if r.status_code != 200:
        _raise_from(r)
    return r.json()


@app.delete("/celulares/{celular_id}")
async def delete_celular(celular_id: int):
    """Elimina el celular y su entrada de stock en una sola llamada."""
    async with httpx.AsyncClient(timeout=5) as client:
        r = await client.delete(f"{CELULARES_URL}/celulares/{celular_id}")
        if r.status_code != 200:
            _raise_from(r)
        await client.delete(f"{STOCK_URL}/stock/{celular_id}")
    return r.json()


# ─────────────────────────────────────────────
#  Rutas de Stock
# ─────────────────────────────────────────────

@app.get("/stock")
async def get_stock():
    async with httpx.AsyncClient(timeout=5) as client:
        r = await client.get(f"{STOCK_URL}/stock")
    return r.json()


@app.get("/stock/alertas")
async def get_alertas():
    async with httpx.AsyncClient(timeout=5) as client:
        r = await client.get(f"{STOCK_URL}/stock/alertas")
    return r.json()


@app.get("/stock/{celular_id}")
async def get_stock_celular(celular_id: int):
    async with httpx.AsyncClient(timeout=5) as client:
        r = await client.get(f"{STOCK_URL}/stock/{celular_id}")
    if r.status_code != 200:
        _raise_from(r)
    return r.json()


@app.patch("/stock/{celular_id}/agregar")
async def agregar_stock(celular_id: int, cantidad: int):
    async with httpx.AsyncClient(timeout=5) as client:
        r = await client.patch(
            f"{STOCK_URL}/stock/{celular_id}/agregar",
            params={"cantidad": cantidad},
        )
    if r.status_code != 200:
        _raise_from(r)
    return r.json()


@app.patch("/stock/{celular_id}/restar")
async def restar_stock(celular_id: int, cantidad: int):
    async with httpx.AsyncClient(timeout=5) as client:
        r = await client.patch(
            f"{STOCK_URL}/stock/{celular_id}/restar",
            params={"cantidad": cantidad},
        )
    if r.status_code != 200:
        _raise_from(r)
    return r.json()


@app.patch("/stock/{celular_id}/minimo")
async def actualizar_minimo(celular_id: int, stock_minimo: int):
    async with httpx.AsyncClient(timeout=5) as client:
        r = await client.patch(
            f"{STOCK_URL}/stock/{celular_id}/minimo",
            params={"stock_minimo": stock_minimo},
        )
    if r.status_code != 200:
        _raise_from(r)
    return r.json()


# ─────────────────────────────────────────────
#  Rutas de Reportes
# ─────────────────────────────────────────────

@app.get("/reportes/resumen")
async def reporte_resumen():
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"{REPORTES_URL}/reportes/resumen")
    if r.status_code != 200:
        _raise_from(r)
    return r.json()


@app.get("/reportes/por-marca")
async def reporte_por_marca():
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"{REPORTES_URL}/reportes/por-marca")
    if r.status_code != 200:
        _raise_from(r)
    return r.json()


@app.get("/reportes/top-stock")
async def reporte_top_stock():
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"{REPORTES_URL}/reportes/top-stock")
    if r.status_code != 200:
        _raise_from(r)
    return r.json()


@app.get("/reportes/precio-promedio-por-marca")
async def reporte_precio_promedio():
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"{REPORTES_URL}/reportes/precio-promedio-por-marca")
    if r.status_code != 200:
        _raise_from(r)
    return r.json()
