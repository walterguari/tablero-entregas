import streamlit as st
import pandas as pd
import datetime
from datetime import timedelta
import os

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Portal Autociel", layout="wide", initial_sidebar_state="expanded")

# --- ESTILOS CSS ---
st.markdown("""
<style>
    div.stButton > button {
        width: 100%;
        border-radius: 12px;
        min-height: 4.5em;
        height: auto;
        font-weight: bold;
        border: 1px solid #e0e0e0;
        white-space: pre-wrap;
        word-wrap: break-word;
        padding: 10px;
    }
    .stMetric {
        background-color: #f0f4c3;
        padding: 10px;
        border-radius: 5px;
        border: 1px solid #dce775;
    }
</style>
""", unsafe_allow_html=True)

# --- CARGA DE DATOS ---
SHEET_ID_0KM = "15hIQ6WBxh1Ymhh9dxerKvEnoXJ_osH6a9BH-1TW9ZU8"
GID_0KM = "1504374770"
URL_0KM = f"https://docs.google.com/spreadsheets/d/{SHEET_ID_0KM}/export?format=csv&gid={GID_0KM}"

SHEET_ID_USADOS = "1Kxy6d8xRR0WlypTVZygL1KHbc_i1MlNnd_JcEhCbc3c"
GID_USADOS = "183300599"
URL_USADOS = f"https://docs.google.com/spreadsheets/d/{SHEET_ID_USADOS}/export?format=csv&gid={GID_USADOS}"

@st.cache_data(ttl=60)
def load_data(url, es_usados=False):
    try:
        df = pd.read_csv(url)
        
        # Limpieza rigurosa de encabezados eliminando saltos de línea y espacios múltiples
        nuevos_nombres = []
        for col in df.columns:
            if pd.isna(col) or str(col).strip() == "" or "Unnamed:" in str(col):
                nuevos_nombres.append(f"COL_VACIA_{len(nuevos_nombres)}")
            else:
                nuevos_nombres.append(" ".join(str(col).strip().upper().split()))
        df.columns = nuevos_nombres
        
        # ELIMINAR COLUMNAS DUPLICADAS (Evita el ValueError de PyArrow)
        df = df.loc[:, ~df.columns.duplicated()]
        
        # PROCESAMIENTO CLAVE DE FECHAS SEGÚN ORIGEN
        if es_usados:
            col_entrega = "FECHA CONFIRMADA DE ENTREGA (CONTACTO CON EL CLIENTE)"
        else:
            col_entrega = next((c for c in df.columns if "CONFIRMACI" in c and "ENTREGA" in c), None)
            if not col_entrega: 
                col_entrega = next((c for c in df.columns if "FECHA" in c and "FACT" not in c), None)    
        
        if col_entrega in df.columns:
            df["FECHA_ENTREGA_DT"] = pd.to_datetime(df[col_entrega], dayfirst=True, errors='coerce')
            df["AÑO_ENTREGA"] = df["FECHA_ENTREGA_DT"].dt.year
            df["MES_ENTREGA"] = df["FECHA_ENTREGA_DT"].dt.month_name()
            df["N_MES_ENTREGA"] = df["FECHA_ENTREGA_DT"].dt.month
            df["COL_ORIGINAL_FECHA_USADOS"] = col_entrega
        else:
            df["FECHA_ENTREGA_DT"] = pd.to_datetime([])
        
        col_arribo = next((c for c in df.columns if "ARRIBO" in c), None)
        if col_arribo:
            df["FECHA_ARRIBO_DT"] = pd.to_datetime(df[col_arribo], dayfirst=True, errors='coerce')
            df["AÑO_ARRIBO"] = df["FECHA_ARRIBO_DT"].dt.year

        return df
    except Exception as e:
        st.error(f"Error cargando datos: {e}")
        return pd.DataFrame()

# Cargas independientes parametrizadas
df_0km = load_data(URL_0KM, es_usados=False)
df_usados = load_data(URL_USADOS, es_usados=True)

# --- MEMORIA DE ESTADO ---
if 'filtro_estado_stock' not in st.session_state: st.session_state.filtro_estado_stock = None
if 'filtro_estado_admin' not in st.session_state: st.session_state.filtro_estado_admin = None
if 'filtro_doc_stock' not in st.session_state: st.session_state.filtro_doc_stock = None 
if 'modo_vista_0km' not in st.session_state: st.session_state.modo_vista_0km = 'mes'
if 'modo_vista_usados' not in st.session_state: st.session_state.modo_vista_usados = 'mes'
if 'filtro_mantenimiento' not in st.session_state: st.session_state.filtro_mantenimiento = 'todos'

# ==========================================
# BARRA LATERAL (LOGO Y NAVEGACIÓN)
# ==========================================
logo_paths = ["logo.png", "logo.png.png", "logo.jpg"]
for path in logo_paths:
    if os.path.exists(path):
        st.sidebar.image(path, use_container_width=True)
        break

st.sidebar.title("Navegación")
opcion = st.sidebar.radio("Ir a:", [
    "📅 Planificación Entregas 0KM", 
    "🚗 Agenda de Usados",
    "📦 Control de Stock 0KM", 
    "🛠️ Control Mantenimiento", 
    "📄 Estado Documentación 0KM", 
    "🗺️ Plano del Salón"
])
st.sidebar.markdown("---")

# FUNCIÓN DE AGENDA OPTIMIZADA
def render_agenda(df_target, session_key_vista, titulo_seccion, es_usados=False):
    st.title(titulo_seccion)
    if not df_target.empty and "FECHA_ENTREGA_DT" in df_target.columns:
        df_valid = df_target.dropna(subset=["FECHA_ENTREGA_DT"])
        años = sorted(df_valid["AÑO_ENTREGA"].dropna().unique().astype(int))
        if años:
            año_sel = st.sidebar.selectbox("Seleccionar Año", options=años, index=len(años)-1, key=f"sel_año_{session_key_vista}")
            df_año = df_valid[df_valid["AÑO_ENTREGA"] == año_sel]
            
            hoy = datetime.date.today()
            entregados = df_año[df_año["FECHA_ENTREGA_DT"].dt.date < hoy]
            programados = df_año[df_año["FECHA_ENTREGA_DT"].dt.date >= hoy]
            
            c1, c2, c3 = st.columns(3)
            type_ent = "primary" if st.session_state[session_key_vista] == 'entregados' else "secondary"
            type_prog = "primary" if st.session_state[session_key_vista] == 'programados' else "secondary"
            type_mes = "primary" if st.session_state[session_key_vista] == 'mes' else "secondary"

            if c1.button(f"✅ Ya Entregados ({len(entregados)})", use_container_width=True, type=type_ent, key=f"btn_ent_{session_key_vista}"):
                st.session_state[session_key_vista] = 'entregados'
            if c2.button(f"🚀 Programados ({len(programados)})", use_container_width=True, type=type_prog, key=f"btn_prog_{session_key_vista}"):
                st.session_state[session_key_vista] = 'programados'
            if c3.button("📅 Filtrar por Mes / Día", use_container_width=True, type=type_mes, key=f"btn_mes_{session_key_vista}"):
                st.session_state[session_key_vista] = 'mes'
            st.divider()

            df_final = pd.DataFrame()
            titulo = ""
            
            if st.session_state[session_key_vista] == 'entregados':
                st.info(f"Historial de entregas {año_sel}.")
                df_final = entregados
                titulo = f"Historial Entregado - {año_sel}"
            elif st.session_state[session_key_vista] == 'programados':
                st.info(f"Próximas entregas a partir de hoy.")
                df_final = programados
                titulo = f"Agenda Pendiente - {año_sel}"
            else:
                st.sidebar.header("Filtrar Mes")
                meses_nombres = df_año["MES_ENTREGA"].unique()
                meses_nums = df_año["N_MES_ENTREGA"].unique()
                mapa_meses = dict(zip(meses_nombres, meses_nums))
                if mapa_meses:
                    mes_sel = st.sidebar.selectbox("Mes", options=sorted(mapa_meses.keys(), key=lambda x: mapa_meses[x]), key=f"sel_mes_{session_key_vista}")
                    df_mes = df_año[df_año["MES_ENTREGA"] == mes_sel].copy()
                    col_filtro, col_vacio = st.columns([1, 3])
                    with col_filtro:
                        dia_filtro = st.date_input("📅 Filtrar día", value=None, min_value=df_mes["FECHA_ENTREGA_DT"].min(), max_value=df_mes["FECHA_ENTREGA_DT"].max(), key=f"date_{session_key_vista}")
                    if dia_filtro:
                        df_final = df_mes[df_mes["FECHA_ENTREGA_DT"].dt.date == dia_filtro]
                        titulo = f"Cronograma del {dia_filtro.strftime('%d/%m/%Y')} ({len(df_final)})"
                    else:
                        df_final = df_mes
                        titulo = f"Cronograma Mensual - {mes_sel} ({len(df_final)})"
                else:
                    st.warning("No hay datos mensuales.")

            if not df_final.empty:
                st.subheader(f"📋 {titulo}")
                
                col_config_table = {}
                
                # --- ORDEN Y COLUMNAS ESPECÍFICAS SEGÚN PESTAÑA ---
                if es_usados:
                    col_fecha_original = df_final["COL_ORIGINAL_FECHA_USADOS"].iloc[0]
                    cols_agenda = [
                        col_fecha_original,
                        "HORA",
                        "CLIENTE",
                        "ESTADO DEL TRAMITE",
                        "TIPO DE UNIDAD",
                        "ESTADO DE UNIDAD",
                        "MARCA",
                        "MODELO",
                        "DOMINIO",
                        "TELEFONO",
                        "CORREO ELECTRONICO",
                        "VENDEDOR (BOLETO)"
                    ]
                    col_sort_hora = "HORA"
                    col_config_table[col_fecha_original] = st.column_config.TextColumn("Fecha Confirmada")
                else:
                    col_admin = next((c for c in df_target.columns if "ESTADO" in c and "ADMIN" in c), None)
                    cols_agenda = ["FECHA_ENTREGA_DT", "HS DE ENTREGA AL CLIENTE", "CLIENTE"]
                    if col_admin: 
                        cols_agenda.append(col_admin)
                    cols_agenda.extend(["MARCA", "MODELO", "VIN", "CANAL DE VENTA", "TELEFONO_CLEAN", "CORREO_CLEAN", "VENDEDOR"])
                    col_sort_hora = "HS DE ENTREGA AL CLIENTE"
                    col_config_table["FECHA_ENTREGA_DT"] = st.column_config.DateColumn("Fecha", format="DD/MM/YYYY")
                
                cols_reales = [c for c in cols_agenda if c in df_final.columns]
                df_render = df_final[cols_reales].loc[:, ~df_final[cols_reales].columns.duplicated()]
                
                sort_cols = ["FECHA_ENTREGA_DT"]
                if col_sort_hora in df_render.columns:
                    sort_cols.append(col_sort_hora)
                
                st.dataframe(
                    df_render.sort_values(sort_cols), 
                    use_container_width=True, 
                    hide_index=True,
                    column_config=col_config_table
                )
            else:
                if st.session_state[session_key_vista] != 'mes': 
                    st.info("No hay vehículos aquí.")
        else:
            st.sidebar.warning("No se encontraron años en los datos.")
    else:
        st.error("No se pudo cargar la fecha de entrega o los datos están vacíos.")

# ==========================================
# RENDERIZADO DE LAS PESTAÑAS
# ==========================================
if opcion == "📅 Planificación Entregas 0KM":
    render_agenda(df_0km, 'modo_vista_0km', "📅 Agenda de Entregas 0KM", es_usados=False)

elif opcion == "🚗 Agenda de Usados":
    render_agenda(df_usados, 'modo_vista_usados', "🚗 Agenda de Entregas Usados", es_usados=True)

elif opcion == "📦 Control de Stock 0KM":
    st.title("📦 Tablero de Stock 0KM")
    df_stock = df_0km.copy()
    if not df_stock.empty:
        st.sidebar.header("Filtros Stock")
        if "AÑO_ARRIBO" in df_stock.columns:
            if st.sidebar.checkbox("Filtrar Arribo"):
                años_arr = sorted(df_stock["AÑO_ARRIBO"].dropna().unique().astype(int))
                if años_arr:
                    año_sel = st.sidebar.selectbox("Año Arribo", años_arr, index=len(años_arr)-1)
                    df_stock = df_stock[df_stock["AÑO_ARRIBO"] == año_sel]
        if "MARCA" in df_stock.columns:
            marcas = st.sidebar.multiselect("Marca", df_stock["MARCA"].unique(), default=df_stock["MARCA"].unique())
            df_stock = df_stock[df_stock["MARCA"].isin(marcas)]

        st.markdown("### 🔍 Estado del Inventario")
        if "ESTADO" in df_stock.columns:
            conteo = df_stock["ESTADO"].value_counts()
            iconos = {"EN EXHIBICIÓN": "🏢", "EN EXHIBICION": "🏢", "SIN PRE ENTREGA": "🛠️", "CON PRE ENTREGA": "✨", "BLOQUEADO": "🔒", "ENTREGADO": "✅", "RESERVADO": "🔖"}
            cols = st.columns(len(conteo) + 1)
            with cols[0]:
                type_todos = "primary" if st.session_state.filtro_estado_stock is None else "secondary"
                if st.button(f"📋 Todos ({len(df_stock)})", use_container_width=True, key="btn_stock_todos", type=type_todos):
                    st.session_state.filtro_estado_stock = None
            for i, (estado, cantidad) in enumerate(conteo.items()):
                icono = iconos.get(str(estado).upper(), "🚗")
                col_destino = cols[i+1] if (i+1) < len(cols) else cols[-1]
                with col_destino:
                    type_btn = "primary" if st.session_state.filtro_estado_stock == estado else "secondary"
                    if st.button(f"{icono} {estado} ({cantidad})", use_container_width=True, key=f"btn_stock_{i}", type=type_btn):
                        st.session_state.filtro_estado_stock = estado
            if st.session_state.filtro_estado_stock:
                df_mostrar = df_stock[df_stock["ESTADO"] == st.session_state.filtro_estado_stock]
                st.info(f"Filtro activo: **{st.session_state.filtro_estado_stock}**")
            else:
                df_mostrar = df_stock
        else:
            df_mostrar = df_stock
        st.markdown("---")
        cols_stock = ["VIN", "MARCA", "MODELO", "DESCRIPCION COLOR", "FECHA DE FABRICACION", "ANTIGUEDAD DE STOCK", "ANTIGÜEDAD DE STOCK", "UBICACION", "DETALLE DEL ESTADO Y FECHA DE DISPONIBILIDAD DE UNIDAD", "ESTADO"]
        cols_reales = [c for c in cols_stock if c in df_mostrar.columns]
        st.dataframe(df_mostrar[cols_reales], use_container_width=True, hide_index=True)

elif opcion == "🛠️ Control Mantenimiento":
    st.title("🛠️ Planificación de Taller")
    if not df_0km.empty and "FECHA_ARRIBO_DT" in df_0km.columns:
        st.sidebar.header("Filtros")
        marcas = st.sidebar.multiselect("Filtrar Marca", df_0km["MARCA"].unique())
        hoy = pd.Timestamp.now().normalize()
        inicio_semana = hoy - timedelta(days=hoy.weekday())
        fin_semana = inicio_semana + timedelta(days=6)
        df_mant = df_0km.copy()
        if "ESTADO" in df_mant.columns:
            df_mant = df_mant[df_mant["ESTADO"].astype(str).str.strip().str.upper() != "ENTREGADO"]
        if marcas:
            df_mant = df_mant[df_mant["MARCA"].isin(marcas)]
        cols_control = {
            30: next((c for c in df_0km.columns if "30" in c and "REALIZADO" in c), None),
            60: next((c for c in df_0km.columns if "60" in c and "REALIZADO" in c), None),
            90: next((c for c in df_0km.columns if "90" in c and "REALIZADO" in c), None),
            180: next((c for c in df_0km.columns if "180" in c and "REALIZADO" in c), None),
            360: next((c for c in df_0km.columns if "360" in c and "REALIZADO" in c), None),
            540: next((c for c in df_0km.columns if "540" in c and "REALIZADO" in c), None),
        }
        lista_hoy, lista_semana, lista_atrasados = [], [], []
        for index, row in df_mant.iterrows():
            if pd.isnull(row["FECHA_ARRIBO_DT"]): continue
            fecha_arribo = row["FECHA_ARRIBO_DT"]
            motivos_hoy, motivos_semana, motivos_atrasados = [], [], []
            for intervalo, columna in cols_control.items():
                if not columna: continue
                fecha_vencimiento = fecha_arribo + timedelta(days=intervalo)
                estado_celda = str(row[columna]).strip().upper()
                if estado_celda in ["OK", "N/A", "SI"]: continue
                if fecha_vencimiento == hoy: motivos_hoy.append(f"Control {intervalo} días")
                if inicio_semana <= fecha_vencimiento <= fin_semana: motivos_semana.append(f"Control {intervalo} días ({fecha_vencimiento.strftime('%d/%m')})")
                if hoy >= fecha_vencimiento: motivos_atrasados.append(f"Falta {intervalo} días (Venció: {fecha_vencimiento.strftime('%d/%m')})")
            if motivos_hoy:
                r = row.copy(); r["TAREA"] = ", ".join(motivos_hoy); lista_hoy.append(r)
            if motivos_semana:
                r = row.copy(); r["TAREA"] = ", ".join(motivos_semana); lista_semana.append(r)
            if motivos_atrasados:
                r = row.copy(); r["TAREA"] = motivos_atrasados[-1]; lista_atrasados.append(r)
        
        c1, c2, c3 = st.columns(3)
        t_hoy = "primary" if st.session_state.filtro_mantenimiento == 'hoy' else "secondary"
        t_sem = "primary" if st.session_state.filtro_mantenimiento == 'semana' else "secondary"
        t_tod = "primary" if st.session_state.filtro_mantenimiento == 'todos' else "secondary"

        if c1.button(f"📅 Vence HOY ({len(lista_hoy)})", use_container_width=True, type=t_hoy): st.session_state.filtro_mantenimiento = 'hoy'
        if c2.button(f"📆 Vence Esta Semana ({len(lista_semana)})", use_container_width=True, type=t_sem): st.session_state.filtro_mantenimiento = 'semana'
        if c3.button(f"🚨 Todo Pendiente ({len(lista_atrasados)})", use_container_width=True, type=t_tod): st.session_state.filtro_mantenimiento = 'todos'
        st.divider()
        
        df_final = pd.DataFrame()
        if st.session_state.filtro_mantenimiento == 'hoy':
            df_final = pd.DataFrame(lista_hoy); titulo = "🚗 Vehículos que vencen HOY"
        elif st.session_state.filtro_mantenimiento == 'semana':
            df_final = pd.DataFrame(lista_semana); titulo = "🗓️ Planificación Semanal"
        else:
            df_final = pd.DataFrame(lista_atrasados); titulo = "⚠️ Listado de Atrasados / Pendientes"
        
        if not df_final.empty:
            st.subheader(titulo)
            cols_base = ["VIN", "MARCA", "MODELO", "FECHA_ARRIBO_DT", "TAREA", "UBICACION"]
            cols_reales = [c for c in cols_base if c in df_final.columns]
            st.dataframe(df_final[cols_reales], use_container_width=True, hide_index=True, column_config={"FECHA_ARRIBO_DT": st.column_config.DateColumn("Fecha Arribo", format="DD/MM/YYYY")})
        else:
            if st.session_state.filtro_mantenimiento != 'todos': st.success("✅ ¡Nada pendiente!")
            else: st.success("✅ ¡Felicitaciones! No hay mantenimientos atrasados.")
    else:
        st.warning("No se encontraron datos.")

elif opcion == "📄 Estado Documentación 0KM":
    st.title("📄 Estado de Documentación 0KM")
    df_doc = df_0km.copy()
    if not df_doc.empty:
        st.sidebar.header("Filtros Documentación")
        if "MARCA" in df_doc.columns:
            marca_filter = st.sidebar.multiselect("Filtrar Marca", df_doc["MARCA"].unique())
            if marca_filter: df_doc = df_doc[df_doc["MARCA"].isin(marca_filter)]
        search = st.text_input("🔎 Buscar por VIN o CLIENTE", placeholder="Escribe para buscar...").upper()
        if search:
            mask = df_doc.apply(lambda row: row.astype(str).str.contains(search, case=False).any(), axis=1)
            df_doc = df_doc[mask]
        st.markdown("---")
        cols_solicitadas = ["FECHA DE FACTURACION DE LA UNIDAD", "VIN", "CLIENTE", "MARCA", "MODELO", "UBICACION", "ESTADO"]
        cols_reales = [c for c in cols_solicitadas if c in df_doc.columns]
        
        df_doc_render = df_doc[cols_reales].loc[:, ~df_doc[cols_reales].columns.duplicated()]
        st.dataframe(df_doc_render, use_container_width=True, hide_index=True)

elif opcion == "🗺️ Plano del Salón":
    st.title("🗺️ Distribución del Salón")
    tab_peugeot, tab_citroen = st.tabs(["🦁 Peugeot", "🔴 Citroën"])
    with tab_peugeot:
        if os.path.exists("mapa_peugeot.jpg"): st.image("mapa_peugeot.jpg", use_container_width=True)
        else: st.warning("Sube 'mapa_peugeot.jpg'")
    with tab_citroen:
        if os.path.exists("mapa_citroen.jpg"): st.image("mapa_citroen.jpg", use_container_width=True)
        else: st.warning("Sube 'mapa_citroen.jpg'")
