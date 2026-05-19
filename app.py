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
        # Limpieza estándar de encabezados (quitar espacios en blanco al inicio/final)
        df.columns = df.columns.str.strip().str.upper()
        
        # ELIMINAR COLUMNAS DUPLICADAS (Evita el ValueError de PyArrow)
        df = df.loc[:, ~df.columns.duplicated()]
        
        # IDENTIFICACIÓN ROBUSTA DE LA COLUMNA DE FECHA
        col_entrega = None
        
        if es_usados:
            # Intento 1: Buscar si alguna columna contiene "CONFIRMADA" y "ENTREGA" a la vez (evita fallos por paréntesis o saltos de línea)
            col_entrega = next((c for c in df.columns if "CONFIRMADA" in c and "ENTREGA" in c), None)
            
            # Intento 2: Caída de respaldo si lo escribieron sin "confirmada"
            if not col_entrega:
                col_entrega = next((c for c in df.columns if "FECHA" in c and "ENTREGA" in c), None)
            if not col_entrega:
                col_entrega = next((c for c in df.columns if "CONTACTO" in c and "CLIENTE" in c), None)
        else:
            # Lógica estándar para 0KM
            col_entrega = next((c for c in df.columns if "CONFIRMACI" in c and "ENTREGA" in c), None)
            if not col_entrega: 
                col_entrega = next((c for c in df.columns if "FECHA" in c and "FACT" not in c), None)    
        
        # Si encontramos la columna, procesamos las fechas
        if col_entrega and col_entrega in df.columns:
            df["FECHA_ENTREGA_DT"] = pd.to_datetime(df[col_entrega], dayfirst=True, errors='coerce')
            df["AÑO_ENTREGA"] = df["FECHA_ENTREGA_DT"].dt.year
            df["MES_ENTREGA"] = df["FECHA_ENTREGA_DT"].dt.month_name()
            df["N_MES_ENTREGA"] = df["FECHA_ENTREGA_DT"].dt.month
            
            # Guardamos el nombre real detectado para usarlo después en el renderizado operativo de la tabla
            df["COL_ORIGINAL_FECHA_USADOS"] = col_entrega
        
        # Mapeos secundarios comunes
        col_arribo = next((c for c in df.columns if "ARRIBO" in c), None)
        if col_arribo:
            df["FECHA_ARRIBO_DT"] = pd.to_datetime(df[col_arribo], dayfirst=True, errors='coerce')
            df["AÑO_ARRIBO"] = df["FECHA_ARRIBO_DT"].dt.year

        return df
    except Exception as e:
        st.error(f"Error cargando datos: {e}")
        return pd.DataFrame()

# Pasamos el parámetro para diferenciar las planillas en la carga operativa
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
        # Filtrar filas que tengan una fecha válida para evitar que colapse el selector de año
        df_valid = df_target.dropna(subset=["FECHA_ENTREGA_DT"])
        años = sorted(df_valid["AÑO_ENTREGA"].unique().astype(int))
        
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
                
                # --- PROCESAMIENTO DINÁMICO DE COLUMNAS PARA EVITAR VALUERROR ---
                if es_usados:
                    # Obtenemos la columna real que se usó para procesar la fecha original
                    col_fecha_real_usados = df_final["COL_ORIGINAL_FECHA_USADOS"].iloc[0]
                    
                    # Buscamos por aproximación las columnas solicitadas por el usuario
                    col_hora = next((c for c in df_final.columns if "HORA" in c), "HORA")
                    col_cliente = next((c for c in df_final.columns if "CLIENTE" in c), "CLIENTE")
                    col_tramite = next((c for c in df_final.columns if "TRAMITE" in c or "TRÁMITE" in c), "ESTADO DEL TRAMITE")
                    col_tipo_u = next((c for c in df_final.columns if "TIPO" in c and "UNIDAD" in c), "TIPO DE UNIDAD")
                    col_est_u = next((c for c in df_final.columns if "ESTADO" in c and "UNIDAD" in c), "ESTADO DE UNIDAD")
                    col_marca = next((c for c in df_final.columns if "MARCA" in c), "MARCA")
                    col_modelo = next((c for c in df_final.columns if "MODELO" in c), "MODELO")
                    col_dominio = next((c for c in df_final.columns if "DOMINIO" in c or "PATENTE" in c), "DOMINIO")
                    col_tel = next((c for c in df_final.columns if "TELEFONO" in c or "TEL" in c), "TELEFONO")
                    col_mail = next((c for c in df_final.columns if "CORREO" in c or "MAIL" in c or "ELECTRONICO" in c), "CORREO ELECTRONICO")
                    col_vend = next((c for c in df_final.columns if "VENDEDOR" in c or "BOLETO" in c), "VENDEDOR (BOLETO)")

                    cols_agenda = [
                        col_fecha_real_usados, 
                        col_hora, 
                        col_cliente, 
                        col_tramite, 
                        col_tipo_u, 
                        col_est_u, 
                        col_marca, 
                        col_modelo, 
                        col_dominio, 
                        col_tel, 
                        col_mail, 
                        col_vend
                    ]
                    col_sort_hora = col_hora
                else:
                    # Estructura clásica para 0KM
                    col_admin = next((c for c in df_target.columns if "ESTADO" in c and "ADMIN" in c), None)
                    cols_agenda = ["FECHA_ENTREGA_DT", "HS DE ENTREGA AL CLIENTE", "CLIENTE"]
                    if col_admin: 
                        cols_agenda.append(col_admin)
                    cols_agenda.extend(["MARCA", "MODELO", "VIN", "CANAL DE VENTA", "TELEFONO_CLEAN", "CORREO_CLEAN", "VENDEDOR"])
                    col_sort_hora = "HS DE ENTREGA AL CLIENTE"
                
                # Filtrar solo las que existan físicamente en el DataFrame cargado
                cols_reales = [c for c in cols_agenda if c in df_final.columns]
                
                df_render = df_final[cols_reales].loc[:, ~df_final[cols_reales].columns.duplicated()]
                
                sort_cols = ["FECHA_ENTREGA_DT"]
                if col_sort_hora in df_render.columns:
                    sort_cols.append(col_sort_hora)
                
                st.dataframe(
                    df_render.sort_values(sort_cols), 
                    use_container_width=True, 
                    hide_index=True
                )
            else:
                if st.session_state[session_key_vista] != 'mes': 
                    st.info("No hay vehículos planificados en este rango.")
        else:
            st.sidebar.warning("No se encontraron fechas válidas para armar los años de entrega de Usados.")
            # Panel de diagnóstico oculto por si necesitas auditar los nombres reales que llegan del Excel
            with st.expander("🔍 Diagnóstico técnico: Ver encabezados reales de la planilla de Usados"):
                st.write(list(df_target.columns))
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
            motivos_hoy, motifs_semana, motivos_atrasados = [], [], []
            for intervalo, columna in cols_control.items():
                if not columna: continue
                fecha_vencimiento = fecha_arribo + timedelta(days=intervalo)
                estado_celda = str(row[columna]).strip().upper()
                if estado_celda in ["OK", "N/A", "SI"]: continue
                if fecha_vencimiento == hoy: motivos_hoy.append(f"Control {intervalo} días")
                if inicio_semana <= fecha_vencimiento <= fin_semana: motifs_semana.append(f"Control {intervalo} días ({fecha_vencimiento.strftime('%d/%m')})")
                if hoy >= fecha_vencimiento: motivos_atrasados.append(f"Falta {intervalo} días (Venció: {fecha_vencimiento.strftime('%d/%m')})")
            if motivos_hoy:
                r = row.copy(); r["TAREA"] = ", ".join(motivos_hoy); lista_hoy.append(r)
            if motifs_semana:
                r = row.copy(); r["TAREA"] = ", ".join(motifs_semana); lista_semana.append(r)
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

        col_target_admin = None
        if "ESTADO DE ADMINISTRATIVO" in df_doc.columns: col_target_admin = "ESTADO DE ADMINISTRATIVO"
        elif "ESTADO ADMINISTRATIVO" in df_doc.columns: col_target_admin = "ESTADO ADMINISTRATIVO"
        elif "DETALLE DEL ESTADO Y FECHA DE DISPONIBILIDAD DE UNIDAD" in df_doc.columns: col_target_admin = "DETALLE DEL ESTADO Y FECHA DE DISPONIBILIDAD DE UNIDAD"

        st.subheader("📂 1. Estado Administrativo")
        df_base_botones = df_doc.copy()

        estados_clave = [
            ("Atopatentado sin cliente", "⚫", "Atopatentado sin"),
            ("Autopatentado firma 08", "✍️", "firma"),
            ("En caso legales", "⚖️", "legales"),
            ("No retirará la unidad", "🚫", "retirará"),
            ("Entrega al gestor", "📂", "gestor"),
            ("Entrega al Reventa", "🤝", "Reventa"),
            ("Se envía a Salta", "🚚", "Salta"),
            ("Firma titular", "📝", "titular")
        ]

        admin_buttons = []
        admin_buttons.append({
            "label": f"📋 Ver Todos ({len(df_base_botones)})",
            "key": "btn_doc_reset_admin",
            "filter_val": None,
            "count": len(df_base_botones)
        })

        if col_target_admin:
            mask_ok = df_base_botones[col_target_admin].astype(str).str.contains("Ok doc", case=False, na=False)
            if "ESTADO" in df_base_botones.columns:
                mask_no_entregado = df_base_botones["ESTADO"].astype(str).str.upper() != "ENTREGADO"
                mask_entregado = df_base_botones["ESTADO"].astype(str).str.upper() == "ENTREGADO"
                
                cant_ok_stock = len(df_base_botones[mask_ok & mask_no_entregado])
                cant_ok_entregados = len(df_base_botones[mask_ok & mask_entregado])

                if cant_ok_stock > 0:
                    admin_buttons.append({
                        "label": f"✅ Ok Doc (En Stock) ({cant_ok_stock})",
                        "key": "btn_est_ok_stock",
                        "filter_val": "SPECIAL_OK_STOCK",
                        "count": cant_ok_stock
                    })
                
                if cant_ok_entregados > 0:
                    admin_buttons.append({
                        "label": f"✅📜 Ok Doc (Entregados) ({cant_ok_entregados})",
                        "key": "btn_est_ok_entregado",
                        "filter_val": "SPECIAL_OK_ENTREGADO",
                        "count": cant_ok_entregados
                    })

            for label_btn, icono, keyword in estados_clave:
                cant = len(df_base_botones[df_base_botones[col_target_admin].astype(str).str.contains(keyword, case=False, na=False)])
                if cant > 0: 
                    admin_buttons.append({
                        "label": f"{icono} {label_btn} ({cant})",
                        "key": f"btn_est_{keyword}",
                        "filter_val": keyword,
                        "count": cant
                    })

        if admin_buttons:
            cols_a = st.columns(3)
            for idx, btn_data in enumerate(admin_buttons):
                col_to_use = cols_a[idx % 3]
                with col_to_use:
                    is_active = (st.session_state.filtro_estado_admin == btn_data["filter_val"])
                    btn_type = "primary" if is_active else "secondary"
                    if st.button(btn_data["label"], use_container_width=True, key=btn_data["key"], type=btn_type):
                        st.session_state.filtro_estado_admin = btn_data["filter_val"]

        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("📦 2. Estado Físico (Stock)")
        
        df_para_stock_botones = df_doc.copy()
        if st.session_state.filtro_estado_admin and col_target_admin:
            val_a = st.session_state.filtro_estado_admin
            if val_a == "SPECIAL_OK_STOCK":
                df_para_stock_botones = df_para_stock_botones[df_para_stock_botones[col_target_admin].astype(str).str.contains("Ok doc", case=False, na=False) & (df_para_stock_botones["ESTADO"].astype(str).str.upper() != "ENTREGADO")]
            elif val_a == "SPECIAL_OK_ENTREGADO":
                df_para_stock_botones = df_para_stock_botones[df_para_stock_botones[col_target_admin].astype(str).str.contains("Ok doc", case=False, na=False) & (df_para_stock_botones["ESTADO"].astype(str).str.upper() == "ENTREGADO")]
            else:
                df_para_stock_botones = df_para_stock_botones[df_para_stock_botones[col_target_admin].astype(str).str.contains(val_a, case=False, na=False)]

        stock_buttons = []
        stock_buttons.append({
            "label": f"♾️ Cualquiera ({len(df_para_stock_botones)})",
            "key": "btn_stock_reset_doc",
            "filter_val": None,
            "count": len(df_para_stock_botones)
        })

        if "ESTADO" in df_doc.columns:
            all_stock_states = ["EN EXHIBICIÓN", "SIN PRE ENTREGA", "CON PRE ENTREGA", "BLOQUEADO", "ENTREGADO", "RESERVADO", "DISPONIBLE"]
            unique_in_db = df_doc["ESTADO"].dropna().str.upper().unique().tolist()
            for u in unique_in_db:
                if u not in all_stock_states: all_stock_states.append(u)

            iconos_stock = {"EN EXHIBICIÓN": "🏢", "EN EXHIBICION": "🏢", "SIN PRE ENTREGA": "🛠️", "CON PRE ENTREGA": "✨", "BLOQUEADO": "🔒", "ENTREGADO": "✅", "RESERVADO": "🔖", "DISPONIBLE": "🟢"}

            for estado in all_stock_states:
                cant = len(df_para_stock_botones[df_para_stock_botones["ESTADO"].astype(str).str.upper() == estado])
                if cant > 0:
                    icon = iconos_stock.get(estado, "🚗")
                    stock_buttons.append({"label": f"{icon} {estado.title()} ({cant})", "key": f"btn_st_doc_{estado}", "filter_val": estado, "count": cant})

        if stock_buttons:
            cols_s = st.columns(4)
            for idx, btn_data in enumerate(stock_buttons):
                col_to_use = cols_s[idx % 4]
                with col_to_use:
                    is_active = (st.session_state.filtro_doc_stock == btn_data["filter_val"])
                    btn_type = "primary" if is_active else "secondary"
                    if st.button(btn_data["label"], use_container_width=True, key=btn_data["key"], type=btn_type):
                        st.session_state.filtro_doc_stock = btn_data["filter_val"]

        st.divider()
        if st.session_state.filtro_estado_admin and col_target_admin:
            val_admin = st.session_state.filtro_estado_admin
            if val_admin == "SPECIAL_OK_STOCK":
                df_doc = df_doc[df_doc[col_target_admin].astype(str).str.contains("Ok doc", case=False, na=False) & (df_doc["ESTADO"].astype(str).str.upper() != "ENTREGADO")]
            elif val_admin == "SPECIAL_OK_ENTREGADO":
                df_doc = df_doc[df_doc[col_target_admin].astype(str).str.contains("Ok doc", case=False, na=False) & (df_doc["ESTADO"].astype(str).str.upper() == "ENTREGADO")]
            else:
                df_doc = df_doc[df_doc[col_target_admin].astype(str).str.contains(val_admin, case=False, na=False)]

        if st.session_state.filtro_doc_stock and "ESTADO" in df_doc.columns:
            df_doc = df_doc[df_doc["ESTADO"].astype(str).str.upper() == str(st.session_state.filtro_doc_stock).upper()]

        st.markdown(f"### 🔍 Resultados: {len(df_doc)} vehículos")
        cols_solicitadas = ["FECHA DE FACTURACION DE LA UNIDAD", "VIN", "CLIENTE", "MARCA", "ESTADO DE ADMINISTRATIVO", "ESTADO ADMINISTRATIVO", "MODELO", "UBICACION", "ESTADO", "DETALLE DEL ESTADO Y FECHA DE DISPONIBILIDAD DE UNIDAD", "ACCESORIOS", "FECHA QUE EL GESTOR RETIRA DOC", "FECHA PREVISTA DE ENTREGA", "FECHA DISPONIBILIDAD PAPELES"]
        cols_reales = [c for c in cols_solicitadas if c in df_doc.columns]
        
        df_doc_render = df_doc[cols_reales].loc[:, ~df_doc[cols_reales].columns.duplicated()]
        
        if not df_doc_render.empty:
            st.dataframe(df_doc_render, use_container_width=True, hide_index=True, column_config={"FECHA DE FACTURACION DE LA UNIDAD": st.column_config.DateColumn("F. Factura", format="DD/MM/YYYY")})
        else:
            st.warning("No hay vehículos que cumplan con AMBOS criterios.")

elif opcion == "🗺️ Plano del Salón":
    st.title("🗺️ Distribución del Salón")
    tab_peugeot, tab_citroen = st.tabs(["🦁 Peugeot", "🔴 Citroën"])
    with tab_peugeot:
        if os.path.exists("mapa_peugeot.jpg"): st.image("mapa_peugeot.jpg", use_container_width=True)
        elif os.path.exists("Peugeot (2).jpeg"): st.image("Peugeot (2).jpeg", use_container_width=True)
        else: st.warning("Sube 'mapa_peugeot.jpg'")
    with tab_citroen:
        if os.path.exists("mapa_citroen.jpg"): st.image("mapa_citroen.jpg", use_container_width=True)
        elif os.path.exists("Citroen.jpeg"): st.image("Citroen.jpeg", use_container_width=True)
        else: st.warning("Sube 'mapa_citroen.jpg'")
