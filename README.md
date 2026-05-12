# Gestion de Inventario de Celulares - Microservicios

Proyecto de la materia **Desarrollo de Software Distribuido 1**.

## Arquitectura

```
                 ┌──────────────┐
                 │   Frontend   │  Streamlit  (puerto 8501)
                 └──────┬───────┘
                        │ HTTP
                        ▼
                 ┌──────────────┐
                 │ API Gateway  │  FastAPI    (puerto 8080)
                 └──┬─────┬──┬──┘
          HTTP /    │     │  \ HTTP
                    ▼     ▼   ▼
           ┌──────────┐ ┌───────┐ ┌──────────┐
           │Celulares │ │ Stock │ │Reportes  │
           │FastAPI   │ │FastAPI│ │FastAPI   │
           │SQLite    │ │SQLite │ │(solo lee)│
           │ :8001    │ │ :8002 │ │  :8003   │
           └──────────┘ └───────┘ └──────────┘
```

### Responsabilidades de cada servicio

| Servicio | Puerto | Qué hace | Base de datos |
|---|---|---|---|
| **Celulares** | 8001 | CRUD del catálogo (marca, modelo, precio, color, RAM, almacenamiento) | `celulares.db` |
| **Stock** | 8002 | Maneja cantidades: agregar, restar, alertas de stock bajo | `stock.db` |
| **Reportes** | 8003 | Estadísticas de solo lectura. Llama a Celulares y Stock por HTTP | Sin DB propia |
| **Gateway** | 8080 | Punto único de entrada. Enruta al servicio correcto. Orquesta acciones multi-servicio | Sin DB propia |
| **Frontend** | 8501 | Interfaz web Streamlit. Solo habla con el Gateway | Sin DB propia |

## Estructura del proyecto

```
CelularesPY/
|
|-- Celulares/            # Microservicio 1: catalogo
|   |-- main.py
|   |-- requirements.txt
|   `-- Dockerfile
|
|-- Stock/                # Microservicio 2: inventario
|   |-- main.py
|   |-- requirements.txt
|   `-- Dockerfile
|
|-- Reportes/             # Microservicio 3: estadisticas
|   |-- main.py
|   |-- requirements.txt
|   `-- Dockerfile
|
|-- Gateway/              # API Gateway
|   |-- main.py
|   |-- requirements.txt
|   `-- Dockerfile
|
|-- Frontend/             # Interfaz web
|   |-- app.py
|   |-- requirements.txt
|   `-- Dockerfile
|
|-- docker-compose.yml    # Orquesta los 5 servicios
|-- README.md
`-- .gitignore
```

## Como ejecutar con Docker

### Requisito
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalado con WSL2.

### Comando único
Desde la carpeta raiz del proyecto:

```bash
docker-compose up --build
```

### URLs una vez levantado

| Servicio | URL | Descripcion |
|---|---|---|
| Interfaz web | http://localhost:8501 | Streamlit (usar en presentacion) |
| Gateway Swagger | http://localhost:8080/docs | Todos los endpoints desde un solo lugar |
| Celulares Swagger | http://localhost:8001/docs | Endpoints del catalogo |
| Stock Swagger | http://localhost:8002/docs | Endpoints de inventario |
| Reportes Swagger | http://localhost:8003/docs | Endpoints de estadisticas |

Para detener todo:
```bash
docker-compose down
```

## Como ejecutar sin Docker (desarrollo local)

Abrir **5 terminales** (una por servicio):

```bash
# Terminal 1 - Celulares
cd Celulares && pip install -r requirements.txt && uvicorn main:app --port 8001 --reload

# Terminal 2 - Stock
cd Stock && pip install -r requirements.txt && uvicorn main:app --port 8002 --reload

# Terminal 3 - Reportes
cd Reportes && pip install -r requirements.txt && uvicorn main:app --port 8003 --reload

# Terminal 4 - Gateway
cd Gateway && pip install -r requirements.txt && uvicorn main:app --port 8080 --reload

# Terminal 5 - Frontend
cd Frontend && pip install -r requirements.txt && streamlit run app.py
```

## Endpoints del Gateway (los que usa el Frontend)

### Celulares
| Método | Ruta | Descripcion |
|---|---|---|
| GET | `/celulares` | Listar todos |
| GET | `/celulares/{id}` | Obtener uno |
| POST | `/celulares` | Crear (tambien crea entrada de stock en 0) |
| PUT | `/celulares/{id}` | Actualizar datos del catalogo |
| DELETE | `/celulares/{id}` | Eliminar (tambien elimina su stock) |

### Stock
| Método | Ruta | Descripcion |
|---|---|---|
| GET | `/stock` | Ver todo el stock |
| GET | `/stock/alertas` | Celulares con stock por debajo del minimo |
| GET | `/stock/{celular_id}` | Stock de un celular |
| PATCH | `/stock/{id}/agregar?cantidad=N` | Sumar N unidades |
| PATCH | `/stock/{id}/restar?cantidad=N` | Restar N unidades |

### Reportes
| Método | Ruta | Descripcion |
|---|---|---|
| GET | `/reportes/resumen` | Totales generales |
| GET | `/reportes/por-marca` | Agrupado por marca |
| GET | `/reportes/top-stock` | Ordenado por cantidad de stock |
| GET | `/reportes/precio-promedio-por-marca` | Precios por marca |

## Reparto de trabajo (4 integrantes)

| Equipo | Personas | Archivos | Que explican |
|---|---|---|---|
| Microservicios backend | 2 | `Celulares/`, `Stock/`, `Reportes/` | Cada servicio, su DB, sus endpoints, sus Dockerfiles |
| Gateway + Frontend | 2 | `Gateway/`, `Frontend/`, `docker-compose.yml` | Como el Gateway enruta y orquesta, como Streamlit consume la API, como docker-compose une todo |

## Tips para la presentacion

1. Iniciar mostrando el diagrama de arquitectura de este README.
2. Ejecutar `docker-compose up --build` en vivo para que vean los 5 contenedores arrancando.
3. Abrir el **Gateway Swagger** (`/docs`) y hacer un POST de celular: explicar que el Gateway llama internamente a Celulares Y a Stock.
4. Abrir la **interfaz Streamlit** y hacer el CRUD completo en la pestaña Inventario.
5. Ir a la pestana Stock y agregar unidades al celular recien creado.
6. Ir a la pestana Reportes y mostrar las estadisticas calculadas por el Microservicio Reportes.
7. **Demo clave**: ejecutar `docker stop stock_service` y mostrar que la pestaña Stock del Frontend muestra error, pero la pestana Inventario (que solo usa Celulares) sigue funcionando. Eso es independencia de microservicios.
8. Volver a levantar con `docker start stock_service`.
