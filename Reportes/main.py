"""Microservicio Reportes: genera estadísticas del inventario.
Solo lectura — nunca escribe en ninguna base de datos.
Obtiene datos llamando a los microservicios Celulares y Stock por HTTP.
"""

from collections import defaultdict
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os

app = FastAPI(
    title="Microservicio Reportes",
    description="Estadísticas y reportes del inventario. Solo lectura.",
    version="1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

CELULARES_URL = os.getenv("CELULARES_URL", "http://localhost:8001")
STOCK_URL = os.getenv("STOCK_URL", "http://localhost:8002")


async def fetch_celulares():
    async with httpx.AsyncClient(timeout=5) as client:
        r = await client.get(f"{CELULARES_URL}/celulares")
        r.raise_for_status()
        return r.json()


async def fetch_stock():
    async with httpx.AsyncClient(timeout=5) as client:
        r = await client.get(f"{STOCK_URL}/stock")
        r.raise_for_status()
        return r.json()


@app.get("/health")
def health():
    return {"status": "ok", "servicio": "reportes"}


@app.get("/reportes/resumen")
async def reporte_resumen():
    """Resumen general del inventario: totales, valor, alertas."""
    try:
        celulares = await fetch_celulares()
        stock_list = await fetch_stock()
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"No se pudo contactar un servicio dependiente: {e}")

    stock_map = {s["celular_id"]: s for s in stock_list}

    total_modelos = len(celulares)
    total_unidades = sum(s["cantidad"] for s in stock_list)
    marcas = len({c["marca"] for c in celulares})
    valor_total = sum(
        c["precio"] * stock_map.get(c["id"], {}).get("cantidad", 0)
        for c in celulares
    )
    precio_promedio = (
        sum(c["precio"] for c in celulares) / total_modelos if total_modelos else 0
    )
    alertas = sum(1 for s in stock_list if s["cantidad"] <= s["stock_minimo"])

    return {
        "total_modelos": total_modelos,
        "total_unidades_en_stock": total_unidades,
        "marcas_distintas": marcas,
        "valor_total_inventario": round(valor_total, 2),
        "precio_promedio": round(precio_promedio, 2),
        "alertas_stock_bajo": alertas,
    }


@app.get("/reportes/por-marca")
async def reporte_por_marca():
    """Agrupa el inventario por marca: modelos, unidades y valor."""
    try:
        celulares = await fetch_celulares()
        stock_list = await fetch_stock()
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=str(e))

    stock_map = {s["celular_id"]: s["cantidad"] for s in stock_list}
    por_marca = defaultdict(lambda: {"modelos": 0, "unidades": 0, "valor": 0.0})

    for c in celulares:
        m = c["marca"]
        qty = stock_map.get(c["id"], 0)
        por_marca[m]["modelos"] += 1
        por_marca[m]["unidades"] += qty
        por_marca[m]["valor"] += round(c["precio"] * qty, 2)

    return [
        {"marca": marca, **datos}
        for marca, datos in sorted(por_marca.items())
    ]


@app.get("/reportes/top-stock")
async def reporte_top_stock():
    """Lista todos los modelos ordenados de mayor a menor stock."""
    try:
        celulares = await fetch_celulares()
        stock_list = await fetch_stock()
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=str(e))

    cel_map = {c["id"]: c for c in celulares}
    resultado = []
    for s in stock_list:
        cel = cel_map.get(s["celular_id"], {})
        resultado.append({
            "celular_id": s["celular_id"],
            "marca": cel.get("marca", "?"),
            "modelo": cel.get("modelo", "?"),
            "precio": cel.get("precio", 0),
            "cantidad": s["cantidad"],
            "stock_minimo": s["stock_minimo"],
            "alerta": s["cantidad"] <= s["stock_minimo"],
        })

    return sorted(resultado, key=lambda x: x["cantidad"], reverse=True)


@app.get("/reportes/precio-promedio-por-marca")
async def reporte_precio_promedio():
    """Precio promedio de los celulares por marca."""
    try:
        celulares = await fetch_celulares()
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=str(e))

    por_marca = defaultdict(list)
    for c in celulares:
        por_marca[c["marca"]].append(c["precio"])

    return [
        {
            "marca": marca,
            "precio_minimo": round(min(precios), 2),
            "precio_maximo": round(max(precios), 2),
            "precio_promedio": round(sum(precios) / len(precios), 2),
            "modelos": len(precios),
        }
        for marca, precios in sorted(por_marca.items())
    ]
