"""Cliente de consola que consume el microservicio Backend (API de celulares).

URL del backend configurable por variable de entorno API_URL.
- En local (sin Docker): http://127.0.0.1:8000
- Dentro de docker-compose: http://backend:8000
"""

import os
import requests

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
BASE_URL = f"{API_URL}/celulares"


def get_items():
    response = requests.get(BASE_URL)
    print("\n--- INVENTARIO ACTUAL ---")
    data = response.json()
    if not data:
        print("(sin celulares registrados)")
        return
    for c in data:
        print(f"[{c['id']}] {c['marca']} {c['modelo']} - ${c['precio']} "
              f"| {c['color']} | {c['almacenamiento']}GB / {c['ram']}GB RAM "
              f"| stock: {c['stock']}")


def get_item():
    item_id = int(input("Ingrese el ID del celular: "))
    response = requests.get(f"{BASE_URL}/{item_id}")
    print("\n--- DETALLES DEL CELULAR ---")
    print(response.json())


def create_item():
    print("\n--- REGISTRAR NUEVO CELULAR ---")
    try:
        payload = {
            "marca": input("Marca (ej. Samsung): "),
            "modelo": input("Modelo (ej. Galaxy S23): "),
            "precio": float(input("Precio: ")),
            "color": input("Color: "),
            "almacenamiento": int(input("Almacenamiento en GB: ")),
            "ram": int(input("RAM en GB: ")),
            "stock": int(input("Stock disponible: ")),
        }
        response = requests.post(BASE_URL, json=payload)
        if response.status_code in (200, 201):
            print("\nCelular registrado exitosamente:")
            print(response.json())
        else:
            print(f"\nError {response.status_code}: {response.json()}")
    except ValueError:
        print("Error: Asegúrate de ingresar números válidos para Precio, Almacenamiento, RAM y Stock.")


def update_item():
    print("\n--- ACTUALIZAR CELULAR ---")
    try:
        item_id = int(input("Ingrese el ID del celular a actualizar: "))
        payload = {
            "marca": input("Nueva Marca: "),
            "modelo": input("Nuevo Modelo: "),
            "precio": float(input("Nuevo Precio: ")),
            "color": input("Nuevo Color: "),
            "almacenamiento": int(input("Nuevo Almacenamiento en GB: ")),
            "ram": int(input("Nueva RAM en GB: ")),
            "stock": int(input("Nuevo Stock: ")),
        }
        response = requests.put(f"{BASE_URL}/{item_id}", json=payload)
        if response.status_code == 200:
            print("\nCelular actualizado exitosamente:")
            print(response.json())
        else:
            print(f"\nError {response.status_code}: {response.json()}")
    except ValueError:
        print("Error: Ingresaste letras donde iba un número. Intenta de nuevo.")


def delete_item():
    print("\n--- ELIMINAR CELULAR ---")
    item_id = int(input("Ingrese el ID del celular a eliminar: "))
    response = requests.delete(f"{BASE_URL}/{item_id}")
    print("\nRespuesta del servidor:", response.json())


def menu():
    print(f"\nConectado a: {API_URL}")
    while True:
        print("\n--- MENU DE INVENTARIO DE CELULARES ---")
        print("1. Ver todos los celulares")
        print("2. Ver un celular por ID")
        print("3. Registrar un celular")
        print("4. Actualizar un celular")
        print("5. Eliminar un celular")
        print("6. Salir")

        opcion = input("Seleccione una opcion: ")

        if opcion == "1":
            get_items()
        elif opcion == "2":
            get_item()
        elif opcion == "3":
            create_item()
        elif opcion == "4":
            update_item()
        elif opcion == "5":
            delete_item()
        elif opcion == "6":
            print("Cerrando el sistema de inventario...")
            break
        else:
            print("Opcion invalida, intente de nuevo.")


if __name__ == "__main__":
    menu()
