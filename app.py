recordas este codigo: import streamlit as st
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
SHEET_ID = "15hIQ6WBxh1Ymhh9dxerKvEnoXJ_osH6a9BH-1TW9ZU8"
GID = "1504374770"
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

@st.cache_data(ttl=60)
def load_data():
    try:
        df = pd.read_csv(URL)
        df.columns = df.columns.str.strip().str.upper()
        
        # PROCESAMIENTO FECHAS
        col_entrega = next((c for c in df.columns if "CONFIRMACI" in c and "ENTREGA" in c), None)
        if not col_entrega: col_entrega = next((c for c in df.columns if "FECHA" in c and "FACT" not in c), None)   
        if col_entrega:
            df["FECHA_ENTREGA_DT"] = pd.to_datetime(df[col_entrega], dayfirst=True, errors='coerce')
            df["AÑO_ENTREGA"] = df["FECHA_ENTREGA_DT"].dt.year
            df["MES_ENTREGA"] = df["FECHA_ENTREGA_DT"].dt.month_name()
            df["N_MES_ENTREGA"] = df["FECHA_ENTREGA_DT"].dt.month
        
        col_arribo = next((c for c in df.columns if "ARRIBO" in c), None)
        if col_arribo:
            df["FECHA_ARRIBO_DT"] = pd.to_datetime(df[col_arribo], dayfirst=True, errors='coerce')
            df["AÑO_ARRIBO"] = df["FECHA_ARRIBO_DT"].dt.year

        col_fact = "FECHA DE FACTURACION DE LA UNIDAD"
        if col_fact in df.columns:
            df["FECHA_FACTURACION_DT"] = pd.to_datetime(df[col_fact], dayfirst=True, errors='coerce')

        col_papeles = "FECHA DISPONIBILIDAD PAPELES"
        if col_papeles in df.columns:
            df["FECHA_PAPELES_DT"] = pd.to_datetime(df[col_papeles], dayfirst=True, errors='coerce')

        col_tel = next((c for c in df.columns if "TELEFONO" in c or "CELULAR" in c or "TEL" in c), None)
        if col_tel: df["TELEFONO_CLEAN"] = df[col_tel]
        col_mail = next((c for c in df.columns if "CORREO" in c or "MAIL" in c), None)
        if col_mail: df["CORREO_CLEAN"] = df[col_mail]

        return df
    except Exception as e:
        st.error(f"Error cargando datos: {e}")
        return pd.DataFrame()

df = load_data()

# --- MEMORIA DE ESTADO ---
if 'filtro_estado_stock' not in st.session_state: st.session_state.filtro_estado_stock = None
if 'filtro_estado_admin' not in st.session_state: st.session_state.filtro_estado_admin = None
if 'filtro_doc_stock' not in st.session_state: st.session_state.filtro_doc_stock = None 
if 'modo_vista_agenda' not in st.session_state: st.session_state.modo_vista_agenda = 'mes'
if 'filtro_mantenimiento' not in st.session_state: st.session_state.filtro_mantenimiento = 'todos'

# ==========================================
# BARRA LATERAL (LOGO)
# ==========================================
if os.path.exists("logo.png.png"):
    st.sidebar.image("logo.png.png", use_container_width=True)
elif os.path.exists("logo.png"):
    st.sidebar.image("logo.png", use_container_width=True)
elif os.path.exists("logo.jpg"):
    st.sidebar.image("logo.jpg", use_container_width=True)
else:
    st.sidebar.warning("Falta logo en GitHub")

st.sidebar.title("Navegación")
opcion = st.sidebar.radio("Ir a:", [
    "📅 Planificación Entregas", 
    "📦 Control de Stock", 
    "🛠️ Control Mantenimiento", 
    "📄 Estado Documentación", 
    "🗺️ Plano del Salón"
])
st.sidebar.markdown("---")

# ==========================================
# 1. PLANIFICACIÓN ENTREGAS
# ==========================================
if opcion == "📅 Planificación Entregas":
    st.title("📅 Agenda de Entregas")
    if not df.empty and "FECHA_ENTREGA_DT" in df.columns:
        años = sorted(df["AÑO_ENTREGA"].dropna().unique().astype(int))
        año_sel = st.sidebar.selectbox("Seleccionar Año", options=años, index=len(años)-1)
        df_año = df[df["AÑO_ENTREGA"] == año_sel]
        
        hoy = datetime.date.today()
        entregados = df_año[df_año["FECHA_ENTREGA_DT"].dt.date < hoy]
        programados = df_año[df_año["FECHA_ENTREGA_DT"].dt.date >= hoy]
        
        c1, c2, c3 = st.columns(3)
        # Lógica de color (primary si está activo)
        type_ent = "primary" if st.session_state.modo_vista_agenda == 'entregados' else "secondary"
        type_prog = "primary" if st.session_state.modo_vista_agenda == 'programados' else "secondary"
        type_mes = "primary" if st.session_state.modo_vista_agenda == 'mes' else "secondary"

        if c1.button(f"✅ Ya Entregados ({len(entregados)})", use_container_width=True, type=type_ent):
            st.session_state.modo_vista_agenda = 'entregados'
        if c2.button(f"🚀 Programados ({len(programados)})", use_container_width=True, type=type_prog):
            st.session_state.modo_vista_agenda = 'programados'
        if c3.button("📅 Filtrar por Mes / Día", use_container_width=True, type=type_mes):
            st.session_state.modo_vista_agenda = 'mes'
        st.divider()

        df_final = pd.DataFrame()
        titulo = ""
        
        if st.session_state.modo_vista_agenda == 'entregados':
            st.info(f"Historial de entregas {año_sel}.")
            df_final = entregados
            titulo = f"Historial Entregado - {año_sel}"
        elif st.session_state.modo_vista_agenda == 'programados':
            st.info(f"Próximas entregas a partir de hoy.")
            df_final = programados
            titulo = f"Agenda Pendiente - {año_sel}"
        else:
            st.sidebar.header("Filtrar Mes")
            meses_nombres = df_año["MES_ENTREGA"].unique()
            meses_nums = df_año["N_MES_ENTREGA"].unique()
            mapa_meses = dict(zip(meses_nombres, meses_nums))
            if mapa_meses:
                mes_sel = st.sidebar.selectbox("Mes", options=sorted(mapa_meses.keys(), key=lambda x: mapa_meses[x]))
                df_mes = df_año[df_año["MES_ENTREGA"] == mes_sel].copy()
                col_filtro, col_vacio = st.columns([1, 3])
                with col_filtro:
                    dia_filtro = st.date_input("📅 Filtrar día", value=None, min_value=df_mes["FECHA_ENTREGA_DT"].min(), max_value=df_mes["FECHA_ENTREGA_DT"].max())
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
            cols_agenda = ["FECHA_ENTREGA_DT", "HS DE ENTREGA AL CLIENTE", "CLIENTE", "MARCA", "MODELO", "VIN", "CANAL DE VENTA", "TELEFONO_CLEAN", "CORREO_CLEAN", "VENDEDOR"]
            cols_reales = [c for c in cols_agenda if c in df_final.columns]
            st.dataframe(df_final[cols_reales].sort_values(["FECHA_ENTREGA_DT", "HS DE ENTREGA AL CLIENTE"]), use_container_width=True, hide_index=True, column_config={"FECHA_ENTREGA_DT": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY")})
        else:
            if st.session_state.modo_vista_agenda != 'mes': st.info("No hay vehículos aquí.")

# ==========================================
# 2. CONTROL DE STOCK
# ==========================================
elif opcion == "📦 Control de Stock":
    st.title("📦 Tablero de Stock")
    df_stock = df.copy()
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

# ==========================================
# 3. CONTROL MANTENIMIENTO
# ==========================================
elif opcion == "🛠️ Control Mantenimiento":
    st.title("🛠️ Planificación de Taller")
    if not df.empty and "FECHA_ARRIBO_DT" in df.columns:
        st.sidebar.header("Filtros")
        marcas = st.sidebar.multiselect("Filtrar Marca", df["MARCA"].unique())
        hoy = pd.Timestamp.now().normalize()
        inicio_semana = hoy - timedelta(days=hoy.weekday())
        fin_semana = inicio_semana + timedelta(days=6)
        df_mant = df.copy()
        if "ESTADO" in df_mant.columns:
            df_mant = df_mant[df_mant["ESTADO"].astype(str).str.strip().str.upper() != "ENTREGADO"]
        if marcas:
            df_mant = df_mant[df_mant["MARCA"].isin(marcas)]
        cols_control = {
            30: next((c for c in df.columns if "30" in c and "REALIZADO" in c), None),
            60: next((c for c in df.columns if "60" in c and "REALIZADO" in c), None),
            90: next((c for c in df.columns if "90" in c and "REALIZADO" in c), None),
            180: next((c for c in df.columns if "180" in c and "REALIZADO" in c), None),
            360: next((c for c in df.columns if "360" in c and "REALIZADO" in c), None),
            540: next((c for c in df.columns if "540" in c and "REALIZADO" in c), None),
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

# ==========================================
# 4. ESTADO DOCUMENTACIÓN (CONTEO DINÁMICO + OCULTAR CEROS + COLOR)
# ==========================================
elif opcion == "📄 Estado Documentación":
    st.title("📄 Estado de Documentación")
    
    df_doc = df.copy()
    
    if not df_doc.empty:
        # Filtros laterales (Base)
        st.sidebar.header("Filtros Documentación")
        if "MARCA" in df_doc.columns:
            marca_filter = st.sidebar.multiselect("Filtrar Marca", df_doc["MARCA"].unique())
            if marca_filter: df_doc = df_doc[df_doc["MARCA"].isin(marca_filter)]

        search = st.text_input("🔎 Buscar por VIN o CLIENTE", placeholder="Escribe para buscar...").upper()
        if search:
            mask = df_doc.apply(lambda row: row.astype(str).str.contains(search, case=False).any(), axis=1)
            df_doc = df_doc[mask]
        
        st.markdown("---")

        # ----------------------------------------------------
        # NIVEL 1: ESTADO FÍSICO (STOCK)
        # ----------------------------------------------------
        st.subheader("📦 1. Estado Físico (Stock)")
        
        # 1. Definir Dataframe para calcular los conteos de ESTE nivel (Stock)
        #    Para que sea interactivo, debe respetar el filtro del OTRO nivel (Admin) si está activo.
        df_for_stock_counts = df_doc.copy()
        
        col_target_admin = None
        if "ESTADO DE ADMINISTRATIVO" in df_doc.columns: col_target_admin = "ESTADO DE ADMINISTRATIVO"
        elif "ESTADO ADMINISTRATIVO" in df_doc.columns: col_target_admin = "ESTADO ADMINISTRATIVO"
        elif "DETALLE DEL ESTADO Y FECHA DE DISPONIBILIDAD DE UNIDAD" in df_doc.columns: col_target_admin = "DETALLE DEL ESTADO Y FECHA DE DISPONIBILIDAD DE UNIDAD"

        if st.session_state.filtro_estado_admin and col_target_admin:
             df_for_stock_counts = df_for_stock_counts[df_for_stock_counts[col_target_admin].astype(str).str.contains(st.session_state.filtro_estado_admin, case=False, regex=False, na=False)]

        # 2. Generar lista de botones válidos (Cantidad > 0)
        stock_buttons = []
        
        # Botón "Cualquiera" siempre visible, muestra el total de la selección actual del nivel opuesto
        stock_buttons.append({
            "label": f"♾️ Cualquiera ({len(df_for_stock_counts)})",
            "key": "btn_stock_reset_doc",
            "filter_val": None,
            "count": len(df_for_stock_counts)
        })

        if "ESTADO" in df_doc.columns:
            # Orden de preferencia o todos los unicos
            all_stock_states = ["EN EXHIBICIÓN", "SIN PRE ENTREGA", "CON PRE ENTREGA", "BLOQUEADO", "ENTREGADO", "RESERVADO", "DISPONIBLE"]
            # Aseguramos que existan en el df original para no buscar fantasmas, pero agregamos otros que aparezcan
            unique_in_db = df_doc["ESTADO"].dropna().str.upper().unique().tolist()
            for u in unique_in_db:
                if u not in all_stock_states: all_stock_states.append(u)

            iconos_stock = {
                "EN EXHIBICIÓN": "🏢", "EN EXHIBICION": "🏢", "SIN PRE ENTREGA": "🛠️", 
                "CON PRE ENTREGA": "✨", "BLOQUEADO": "🔒", "ENTREGADO": "✅", 
                "RESERVADO": "🔖", "DISPONIBLE": "🟢"
            }

            for estado in all_stock_states:
                # Contamos en el DF filtrado por admin
                cant = len(df_for_stock_counts[df_for_stock_counts["ESTADO"].astype(str).str.upper() == estado])
                if cant > 0: # REGLA 3: Solo mostrar si > 0
                    icon = iconos_stock.get(estado, "🚗")
                    stock_buttons.append({
                        "label": f"{icon} {estado.title()} ({cant})",
                        "key": f"btn_st_doc_{estado}",
                        "filter_val": estado, # Usamos el valor real del DB si es posible, o normalizamos
                        "count": cant
                    })

        # 3. Renderizar Botones Stock en Grid
        if stock_buttons:
            # Usamos 4 columnas como base
            cols_s = st.columns(4)
            for idx, btn_data in enumerate(stock_buttons):
                col_to_use = cols_s[idx % 4]
                with col_to_use:
                    # REGLA 1: Color Primary si está activo
                    # Normalizamos para comparar (en caso de mayusculas/minusculas)
                    is_active = False
                    if st.session_state.filtro_doc_stock is None and btn_data["filter_val"] is None:
                        is_active = True
                    elif st.session_state.filtro_doc_stock and btn_data["filter_val"]:
                        if str(st.session_state.filtro_doc_stock).upper() == str(btn_data["filter_val"]).upper():
                            is_active = True
                    
                    btn_type = "primary" if is_active else "secondary"
                    
                    if st.button(btn_data["label"], use_container_width=True, key=btn_data["key"], type=btn_type):
                        st.session_state.filtro_doc_stock = btn_data["filter_val"]

        st.markdown("<br>", unsafe_allow_html=True)

        # ----------------------------------------------------
        # NIVEL 2: ESTADO ADMINISTRATIVO
        # ----------------------------------------------------
        st.subheader("📂 2. Estado Administrativo")
        
        # 1. Definir Dataframe para calcular conteos de ESTE nivel (Admin)
        #    Debe respetar el filtro del nivel anterior (Stock) si está activo.
        df_for_admin_counts = df_doc.copy()
        if st.session_state.filtro_doc_stock and "ESTADO" in df_doc.columns:
             # Normalizamos comparación de stock
             df_for_admin_counts = df_for_admin_counts[df_for_admin_counts["ESTADO"].astype(str).str.upper() == str(st.session_state.filtro_doc_stock).upper()]

        estados_clave = [
            ("Atopatentado sin cliente", "⚫", "Atopatentado sin"),
            ("Autopatentado firma 08", "✍️", "firma"),
            ("En caso legales", "⚖️", "legales"),
            ("No retirará la unidad", "🚫", "retirará"),
            ("Ok documentación", "✅", "Ok doc"),
            ("Entrega al gestor", "📂", "gestor"),
            ("Entrega al Reventa", "🤝", "Reventa"),
            ("Se envía a Salta", "🚚", "Salta"),
            ("Firma titular", "📝", "titular")
        ]

        admin_buttons = []
        
        # Botón Reset
        admin_buttons.append({
            "label": f"📋 Ver Todos los Trámites ({len(df_for_admin_counts)})",
            "key": "btn_doc_reset_admin",
            "filter_val": None,
            "count": len(df_for_admin_counts)
        })

        if col_target_admin:
            for label_btn, icono, keyword in estados_clave:
                # Contar usando contains en el DF filtrado por stock
                cant = len(df_for_admin_counts[df_for_admin_counts[col_target_admin].astype(str).str.contains(keyword, case=False, regex=False, na=False)])
                
                if cant > 0: # REGLA 3: Solo mostrar si > 0
                    admin_buttons.append({
                        "label": f"{icono} {label_btn} ({cant})",
                        "key": f"btn_est_{keyword}",
                        "filter_val": keyword,
                        "count": cant
                    })

        # Renderizar Botones Admin
        if admin_buttons:
            cols_a = st.columns(3) # 3 columnas para admin
            for idx, btn_data in enumerate(admin_buttons):
                col_to_use = cols_a[idx % 3]
                with col_to_use:
                    is_active = (st.session_state.filtro_estado_admin == btn_data["filter_val"])
                    btn_type = "primary" if is_active else "secondary"
                    
                    if st.button(btn_data["label"], use_container_width=True, key=btn_data["key"], type=btn_type):
                        st.session_state.filtro_estado_admin = btn_data["filter_val"]

        # --- APLICACIÓN DE FILTROS ---
        st.divider()
        
        # 1. Aplicar Filtro Stock
        if st.session_state.filtro_doc_stock and "ESTADO" in df_doc.columns:
            df_doc = df_doc[df_doc["ESTADO"].astype(str).str.upper() == str(st.session_state.filtro_doc_stock).upper()]
            # No mostramos mensaje aqui para no saturar, el botón primary ya indica el filtro

        # 2. Aplicar Filtro Administrativo
        if st.session_state.filtro_estado_admin and col_target_admin:
            df_doc = df_doc[df_doc[col_target_admin].astype(str).str.contains(st.session_state.filtro_estado_admin, case=False, regex=False, na=False)]

        # TABLA RESULTANTE
        st.markdown(f"### 🔍 Resultados: {len(df_doc)} vehículos")
        
        cols_solicitadas = ["FECHA DE FACTURACION DE LA UNIDAD", "VIN", "CLIENTE", "MARCA", "ESTADO DE ADMINISTRATIVO", "ESTADO ADMINISTRATIVO", "MODELO", "UBICACION", "ESTADO", "DETALLE DEL ESTADO Y FECHA DE DISPONIBILIDAD DE UNIDAD", "ACCESORIOS", "FECHA QUE EL GESTOR RETIRA DOC", "FECHA PREVISTA DE ENTREGA", "FECHA DISPONIBILIDAD PAPELES"]
        cols_reales = [c for c in cols_solicitadas if c in df_doc.columns]
        
        if not df_doc.empty:
            st.dataframe(df_doc[cols_reales], use_container_width=True, hide_index=True, column_config={"FECHA DE FACTURACION DE LA UNIDAD": st.column_config.DateColumn("F. Factura", format="DD/MM/YYYY")})
        else:
            st.warning("No hay vehículos que cumplan con AMBOS criterios.")

# ==========================================
# 5. PLANO SALÓN
# ==========================================
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
