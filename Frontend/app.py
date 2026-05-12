"""Microservicio Frontend: interfaz web para el sistema de inventario de celulares.

Solo habla con el API Gateway (puerto 8080).
Nunca llama directamente a Celulares, Stock ni Reportes.
"""

import os
import pandas as pd
import requests
import streamlit as st

API_URL  = os.getenv("API_URL", "http://127.0.0.1:8080")

st.set_page_config(page_title="Inventario de Celulares", page_icon="📱", layout="wide")

st.markdown("""
<style>
    .main-title {
        font-size: 2.4rem; font-weight: 700;
        background: linear-gradient(90deg, #4F46E5, #06B6D4);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }
    .subtitle { color: #6B7280; margin-bottom: 1rem; font-size: 0.95rem; }
    .alerta-chip {
        background: #FEF2F2; color: #DC2626; border: 1px solid #FECACA;
        border-radius: 6px; padding: 2px 8px; font-size: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">Gestion de Inventario de Celulares</div>', unsafe_allow_html=True)
st.markdown(
    f'<div class="subtitle">Conectado al API Gateway en <code>{API_URL}</code> · '
    f'Microservicios: Celulares · Stock · Reportes</div>',
    unsafe_allow_html=True,
)


# ── Helpers HTTP ──────────────────────────────────────────────────────────────

def get(path):
    return requests.get(f"{API_URL}{path}", timeout=6)

def post(path, data):
    return requests.post(f"{API_URL}{path}", json=data, timeout=6)

def put(path, data):
    return requests.put(f"{API_URL}{path}", json=data, timeout=6)

def delete(path):
    return requests.delete(f"{API_URL}{path}", timeout=6)

def patch(path, params=None):
    return requests.patch(f"{API_URL}{path}", params=params, timeout=6)


def safe_get(path):
    try:
        r = get(path)
        r.raise_for_status()
        return r.json(), None
    except requests.exceptions.RequestException as e:
        return [], str(e)


def check_gateway():
    try:
        r = requests.get(f"{API_URL}/health", timeout=3)
        return r.status_code == 200, r.json() if r.status_code == 200 else {}
    except requests.exceptions.RequestException:
        return False, {}


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.header("Estado de los servicios")
    ok, health_data = check_gateway()
    if ok:
        st.success("Gateway conectado")
        servicios = health_data.get("microservicios", {})
        for svc, estado in servicios.items():
            icon = "✅" if estado == "ok" else "❌"
            st.markdown(f"{icon} **{svc.capitalize()}**: {estado}")
    else:
        st.error("Gateway no disponible")
        st.caption("Ejecuta: docker-compose up")

    st.divider()
    st.markdown("**Arquitectura**")
    st.markdown("```\nFrontend (8501)\n    ↓\nAPI Gateway (8080)\n    ↓     ↓     ↓\n[C]  [S]  [R]\n8001 8002 8003\n```")
    st.caption("[C] Celulares  [S] Stock  [R] Reportes")


# ── Tabs ──────────────────────────────────────────────────────────────────────

tab_inv, tab_add, tab_edit, tab_stock, tab_rep, tab_del = st.tabs(
    ["Inventario", "Registrar", "Actualizar", "Stock", "Reportes", "Eliminar"]
)


# ── TAB: Inventario ───────────────────────────────────────────────────────────

with tab_inv:
    if st.button("Refrescar", key="refresh_inv"):
        st.rerun()

    celulares, err1 = safe_get("/celulares")
    stock_list, err2 = safe_get("/stock")

    if err1:
        st.error(f"Error obteniendo celulares: {err1}")
    else:
        stock_map = {s["celular_id"]: s for s in stock_list}

        total = len(celulares)
        unidades = sum(s["cantidad"] for s in stock_list)
        valor = sum(c["precio"] * stock_map.get(c["id"], {}).get("cantidad", 0) for c in celulares)
        alertas = sum(1 for s in stock_list if s["cantidad"] <= s["stock_minimo"])

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Modelos", total)
        c2.metric("Unidades en stock", unidades)
        c3.metric("Valor del inventario", f"${valor:,.2f}")
        c4.metric("Alertas stock bajo", alertas, delta=None if alertas == 0 else f"{alertas} criticos", delta_color="inverse")

        st.divider()

        if not celulares:
            st.info("Sin celulares. Agrega uno en la pestaña 'Registrar'.")
        else:
            rows = []
            for c in celulares:
                s = stock_map.get(c["id"], {})
                rows.append({
                    "ID": c["id"], "Marca": c["marca"], "Modelo": c["modelo"],
                    "Precio": c["precio"], "Color": c["color"],
                    "Almacenamiento (GB)": c["almacenamiento"], "RAM (GB)": c["ram"],
                    "Stock": s.get("cantidad", "—"),
                    "Stock Mín.": s.get("stock_minimo", "—"),
                    "Alerta": "⚠️" if s.get("alerta") else "",
                })
            df = pd.DataFrame(rows)

            f1, f2 = st.columns(2)
            marcas_opts = ["Todas"] + sorted(df["Marca"].unique().tolist())
            marca_f = f1.selectbox("Filtrar marca", marcas_opts)
            buscar = f2.text_input("Buscar modelo")

            view = df.copy()
            if marca_f != "Todas":
                view = view[view["Marca"] == marca_f]
            if buscar:
                view = view[view["Modelo"].str.contains(buscar, case=False, na=False)]

            st.dataframe(
                view, use_container_width=True, hide_index=True,
                column_config={"Precio": st.column_config.NumberColumn(format="$%.2f")},
            )


# ── TAB: Registrar ────────────────────────────────────────────────────────────

with tab_add:
    st.subheader("Registrar nuevo celular")
    st.caption("El Gateway creará automáticamente la entrada de stock en 0 unidades.")

    with st.form("form_add", clear_on_submit=True):
        c1, c2 = st.columns(2)
        marca  = c1.text_input("Marca", placeholder="Samsung")
        modelo = c2.text_input("Modelo", placeholder="Galaxy S24")
        c3, c4 = st.columns(2)
        precio = c3.number_input("Precio (USD)", min_value=0.0, step=10.0, format="%.2f")
        color  = c4.text_input("Color", placeholder="Negro")
        c5, c6 = st.columns(2)
        almacenamiento = c5.number_input("Almacenamiento (GB)", min_value=1, value=128)
        ram = c6.number_input("RAM (GB)", min_value=1, value=8)
        ok = st.form_submit_button("Registrar celular", use_container_width=True)

        if ok:
            if not marca or not modelo or not color:
                st.warning("Marca, modelo y color son obligatorios.")
            else:
                try:
                    r = post("/celulares", {
                        "marca": marca, "modelo": modelo, "precio": precio,
                        "color": color, "almacenamiento": int(almacenamiento), "ram": int(ram),
                    })
                    if r.status_code in (200, 201):
                        cid = r.json().get("id")
                        st.success(f"Celular registrado con ID {cid}. Stock inicial: 0 unidades.")
                    else:
                        st.error(f"Error {r.status_code}: {r.text}")
                except requests.exceptions.RequestException as e:
                    st.error(f"No se pudo conectar al gateway: {e}")


# ── TAB: Actualizar ───────────────────────────────────────────────────────────

with tab_edit:
    st.subheader("Actualizar datos del celular")
    celulares, err = safe_get("/celulares")
    if err:
        st.error(err)
    elif not celulares:
        st.info("No hay celulares registrados.")
    else:
        opciones = {f"[{c['id']}] {c['marca']} {c['modelo']}": c for c in celulares}
        sel = st.selectbox("Selecciona el celular", list(opciones.keys()), key="sel_edit")
        cel = opciones[sel]

        with st.form("form_edit"):
            c1, c2 = st.columns(2)
            marca  = c1.text_input("Marca", value=cel["marca"])
            modelo = c2.text_input("Modelo", value=cel["modelo"])
            c3, c4 = st.columns(2)
            precio = c3.number_input("Precio", min_value=0.0, value=float(cel["precio"]), step=10.0, format="%.2f")
            color  = c4.text_input("Color", value=cel["color"])
            c5, c6 = st.columns(2)
            almacenamiento = c5.number_input("Almacenamiento (GB)", min_value=1, value=int(cel["almacenamiento"]))
            ram = c6.number_input("RAM (GB)", min_value=1, value=int(cel["ram"]))
            ok = st.form_submit_button("Guardar cambios", use_container_width=True)

            if ok:
                try:
                    r = put(f"/celulares/{cel['id']}", {
                        "marca": marca, "modelo": modelo, "precio": precio,
                        "color": color, "almacenamiento": int(almacenamiento), "ram": int(ram),
                    })
                    if r.status_code == 200:
                        st.success("Celular actualizado correctamente.")
                    else:
                        st.error(f"Error {r.status_code}: {r.text}")
                except requests.exceptions.RequestException as e:
                    st.error(str(e))


# ── TAB: Stock ────────────────────────────────────────────────────────────────

with tab_stock:
    st.subheader("Gestión de Stock")

    celulares, _ = safe_get("/celulares")
    stock_list, _ = safe_get("/stock")
    alertas_list, _ = safe_get("/stock/alertas")

    if alertas_list:
        cel_map = {c["id"]: c for c in celulares}
        nombres = [
            f"{cel_map.get(a['celular_id'], {}).get('marca','?')} "
            f"{cel_map.get(a['celular_id'], {}).get('modelo','?')} "
            f"(stock: {a['cantidad']})"
            for a in alertas_list
        ]
        st.warning(f"**{len(alertas_list)} alerta(s) de stock bajo:** " + " · ".join(nombres))

    st.divider()

    col_agr, col_res = st.columns(2)

    with col_agr:
        st.markdown("**Agregar unidades**")
        if not celulares:
            st.info("Sin celulares.")
        else:
            opciones = {f"[{c['id']}] {c['marca']} {c['modelo']}": c["id"] for c in celulares}
            sel_a = st.selectbox("Celular", list(opciones.keys()), key="sel_agregar")
            cant_a = st.number_input("Cantidad a agregar", min_value=1, value=10, key="cant_a")
            if st.button("Agregar al stock", use_container_width=True, key="btn_agregar"):
                try:
                    r = patch(f"/stock/{opciones[sel_a]}/agregar", {"cantidad": int(cant_a)})
                    if r.status_code == 200:
                        d = r.json()
                        st.success(f"Stock: {d['cantidad_anterior']} → {d['cantidad_nueva']} unidades")
                        st.rerun()
                    else:
                        st.error(f"Error: {r.json().get('detail', r.text)}")
                except requests.exceptions.RequestException as e:
                    st.error(str(e))

    with col_res:
        st.markdown("**Restar unidades**")
        if not celulares:
            st.info("Sin celulares.")
        else:
            opciones = {f"[{c['id']}] {c['marca']} {c['modelo']}": c["id"] for c in celulares}
            sel_r = st.selectbox("Celular", list(opciones.keys()), key="sel_restar")
            cant_r = st.number_input("Cantidad a restar", min_value=1, value=1, key="cant_r")
            if st.button("Restar del stock", use_container_width=True, key="btn_restar"):
                try:
                    r = patch(f"/stock/{opciones[sel_r]}/restar", {"cantidad": int(cant_r)})
                    if r.status_code == 200:
                        d = r.json()
                        st.success(f"Stock: {d['cantidad_anterior']} → {d['cantidad_nueva']} unidades")
                        st.rerun()
                    else:
                        st.error(f"Error: {r.json().get('detail', r.text)}")
                except requests.exceptions.RequestException as e:
                    st.error(str(e))

    st.divider()
    st.markdown("**Estado actual del stock**")
    if stock_list and celulares:
        cel_map = {c["id"]: c for c in celulares}
        rows = []
        for s in stock_list:
            cel = cel_map.get(s["celular_id"], {})
            rows.append({
                "ID": s["celular_id"],
                "Modelo": f"{cel.get('marca','?')} {cel.get('modelo','?')}",
                "Stock actual": s["cantidad"],
                "Stock mínimo": s["stock_minimo"],
                "Estado": "⚠️ Bajo" if s["alerta"] else "✅ OK",
            })
        df_stock = pd.DataFrame(rows)
        st.dataframe(df_stock, use_container_width=True, hide_index=True)
    else:
        st.info("Sin datos de stock.")


# ── TAB: Reportes ─────────────────────────────────────────────────────────────

with tab_rep:
    st.subheader("Reportes del inventario")
    st.caption("Datos calculados por el Microservicio Reportes en tiempo real.")

    if st.button("Generar reportes", use_container_width=False):
        with st.spinner("Consultando microservicio de reportes..."):
            resumen, e1   = safe_get("/reportes/resumen")
            por_marca, e2 = safe_get("/reportes/por-marca")
            top, e3       = safe_get("/reportes/top-stock")
            precios, e4   = safe_get("/reportes/precio-promedio-por-marca")

        if e1:
            st.error(f"No se pudo obtener el reporte: {e1}")
        else:
            st.markdown("#### Resumen general")
            r = resumen  # es un dict, no lista
            col1, col2, col3 = st.columns(3)
            col1.metric("Modelos registrados", r.get("total_modelos", 0))
            col1.metric("Marcas distintas",    r.get("marcas_distintas", 0))
            col2.metric("Unidades en stock",   r.get("total_unidades_en_stock", 0))
            col2.metric("Alertas stock bajo",  r.get("alertas_stock_bajo", 0))
            col3.metric("Valor del inventario", f"${r.get('valor_total_inventario', 0):,.2f}")
            col3.metric("Precio promedio",      f"${r.get('precio_promedio', 0):,.2f}")

            st.divider()

            col_a, col_b = st.columns(2)

            with col_a:
                st.markdown("#### Por marca")
                if por_marca:
                    df_marca = pd.DataFrame(por_marca)
                    df_marca.columns = ["Marca", "Modelos", "Unidades", "Valor ($)"]
                    st.dataframe(df_marca, use_container_width=True, hide_index=True)

            with col_b:
                st.markdown("#### Precio promedio por marca")
                if precios:
                    df_precios = pd.DataFrame(precios)
                    st.dataframe(df_precios, use_container_width=True, hide_index=True)

            st.markdown("#### Top stock (mayor a menor)")
            if top:
                df_top = pd.DataFrame(top)
                df_top["Estado"] = df_top["alerta"].map({True: "⚠️ Bajo", False: "✅ OK"})
                df_top = df_top.drop(columns=["alerta"])
                st.dataframe(df_top, use_container_width=True, hide_index=True)
    else:
        st.info("Presiona 'Generar reportes' para obtener las estadísticas del inventario.")


# ── TAB: Eliminar ─────────────────────────────────────────────────────────────

with tab_del:
    st.subheader("Eliminar celular")
    st.caption("El Gateway eliminará el celular y su entrada de stock automáticamente.")

    celulares, err = safe_get("/celulares")
    if err:
        st.error(err)
    elif not celulares:
        st.info("No hay celulares para eliminar.")
    else:
        opciones = {f"[{c['id']}] {c['marca']} {c['modelo']}": c["id"] for c in celulares}
        sel = st.selectbox("Selecciona el celular", list(opciones.keys()), key="sel_del")
        confirmar = st.checkbox("Confirmo que deseo eliminar este celular y su stock")
        if st.button("Eliminar", disabled=not confirmar, type="primary"):
            try:
                r = delete(f"/celulares/{opciones[sel]}")
                if r.status_code == 200:
                    st.success(r.json().get("mensaje", "Eliminado"))
                    st.rerun()
                else:
                    st.error(f"Error {r.status_code}: {r.text}")
            except requests.exceptions.RequestException as e:
                st.error(str(e))
