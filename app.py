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
def load_data(url, fila_header=0):
    try:
        df = pd.read_csv(url, header=fila_header)
        df.columns = df.columns.str.strip().str.upper()
        
        # ELIMINAR COLUMNAS DUPLICADAS (Evita el ValueError de PyArrow)
        df = df.loc[:, ~df.columns.duplicated()]
        
        if df.empty:
            return df
            
        # PROCESAMIENTO FECHAS
        col_entrega = None
        posibles_columnas_entrega = [
            lambda c: "CONFIRMACI" in c and "ENTREGA" in c,
            lambda c: "FECHA" in c and "ENTREGA" in c,
            lambda c: "FECHA" in c and "TURNO" in c,
            lambda c: "FECHA" in c and "FACT" not in c and "ARRIBO" not in c and "PAPELES" not in c
        ]
        
        for criterio in posibles_columnas_entrega:
            col_entrega = next((c for c in df.columns if criterio(c)), None)
            if col_entrega:
                break
                
        if col_entrega:
            df["FECHA_ENTREGA_DT"] = pd.to_datetime(df[col_entrega], dayfirst=True, errors='coerce')
            df["AÑO_ENTREGA"] = df["FECHA_ENTREGA_DT"].dt.year
            df["MES_ENTREGA"] = df["FECHA_ENTREGA_DT"].dt.month_name()
            df["N_MES_ENTREGA"] = df["FECHA_ENTREGA_DT"].dt.month
        else:
            df["FECHA_ENTREGA_DT"] = pd.NaT
            df["AÑO_ENTREGA"] = pd.NA
            df["MES_ENTREGA"] = "Sin Fecha"
            df["N_MES_ENTREGA"] = 0
        
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

        # Fecha de Pedido de Preparación
        col_prep = next((c for c in df.columns if "PEDIDO" in c and "PREPARACI" in c), None)
        if col_prep:
            df["FECHA_PREPARACION_DT"] = pd.to_datetime(df[col_prep], dayfirst=True, errors='coerce')
        else:
            df["FECHA_PREPARACION_DT"] = pd.NaT

        col_tel = next((c for c in df.columns if "TELEFONO" in c or "CELULAR" in c or "TEL" in c), None)
        if col_tel: 
            df["TELEFONO_CLEAN"] = df[col_tel]
            
        col_mail = next((c for c in df.columns if "CORREO" in c or "MAIL" in c), None)
        if col_mail: 
            df["CORREO_CLEAN"] = df[col_mail]

        return df
    except Exception as e:
        st.error(f"Error cargando datos: {e}")
        return pd.DataFrame()

df_0km = load_data(URL_0KM, fila_header=0)
df_usados = load_data(URL_USADOS, fila_header=1)

# --- MEMORIA DE ESTADO ---
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
    "📦 Control de Stock y Documentación",
    "🛠️ Control Mantenimiento", 
    "🗺️ Plano del Salón"
])
st.sidebar.markdown("---")

# FUNCIÓN DE AGENDA OPTIMIZADA
def render_agenda(df_target, session_key_vista, titulo_seccion, es_usado=False):
    st.title(titulo_seccion)
    if not df_target.empty and "FECHA_ENTREGA_DT" in df_target.columns:
        años = sorted(df_target["AÑO_ENTREGA"].dropna().unique().astype(int))
        if años:
            año_sel = st.sidebar.selectbox("Seleccionar Año", options=años, index=len(años)-1, key=f"sel_año_{session_key_vista}")
            df_año = df_target[df_target["AÑO_ENTREGA"] == año_sel]
            
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
                
                config_columnas = {}
                
                if es_usado:
                    cols_agenda = [
                        "FECHA_ENTREGA_DT", 
                        "HORA", 
                        "CLIENTE", 
                        "ESTADO DEL TRAMITE", 
                        "TIPO DE UNIDAD", 
                        "ESTADO DE UNIDAD", 
                        "MARCA", 
                        "MODELO", 
                        "DOMINIO", 
                        "TELEFONO_CLEAN", 
                        "VENDEDOR (BOLETO)"
                    ]
                    
                    config_columnas = {
                        "FECHA_ENTREGA_DT": st.column_config.DateColumn("Fecha Confirmada de Entrega", format="DD/MM/YYYY"),
                        "HORA": st.column_config.TextColumn("Hora"),
                        "CLIENTE": st.column_config.TextColumn("Cliente"),
                        "ESTADO DEL TRAMITE": st.column_config.TextColumn("Estado del Trámite"),
                        "TIPO DE UNIDAD": st.column_config.TextColumn("Tipo de Unidad"),
                        "ESTADO DE UNIDAD": st.column_config.TextColumn("Estado de Unidad"),
                        "MARCA": st.column_config.TextColumn("Marca"),
                        "MODELO": st.column_config.TextColumn("Modelo"),
                        "DOMINIO": st.column_config.TextColumn("Dominio"),
                        "TELEFONO_CLEAN": st.column_config.TextColumn("Teléfono"),
                        "VENDEDOR (BOLETO)": st.column_config.TextColumn("Vendedor (Boleto)")
                    }
                else:
                    col_admin = next((c for c in df_target.columns if "ESTADO" in c and "ADMIN" in c), None)
                    cols_agenda = ["FECHA_ENTREGA_DT", "HS DE ENTREGA AL CLIENTE", "CLIENTE"]
                    if col_admin: 
                        cols_agenda.append(col_admin)
                    cols_agenda.extend(["MARCA", "MODELO", "VIN", "CANAL DE VENTA", "TELEFONO_CLEAN", "VENDEDOR"])
                    
                    config_columnas = {
                        "FECHA_ENTREGA_DT": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY"),
                        "HS DE ENTREGA AL CLIENTE": st.column_config.TextColumn("Hora"),
                        col_admin: st.column_config.TextColumn("Estado Admin") if col_admin else None
                    }
                
                cols_reales = [c for c in cols_agenda if c in df_final.columns]
                df_render = df_final[cols_reales].loc[:, ~df_final[cols_reales].columns.duplicated()]
                
                st.dataframe(
                    df_render.sort_values(cols_reales[0] if cols_reales else "CLIENTE"), 
                    use_container_width=True, 
                    hide_index=True, 
                    column_config=config_columnas
                )
            else:
                if st.session_state[session_key_vista] != 'mes': 
                    st.info("No hay vehículos aquí.")
            
            # --- SECCIÓN GRÁFICO ---
            st.markdown("---")
            tipo_unidades = "0KM" if not es_usado else "Usados"
            
            st.subheader(f"📊 Volumen de Entregas por Mes {tipo_unidades}")
            
            opciones_grafico = ["Todos los años"] + [str(a) for a in años]
            año_grafico_sel = st.selectbox(
                "Seleccionar período para el gráfico:", 
                options=opciones_grafico, 
                index=opciones_grafico.index(str(año_sel)),
                key=f"grafico_filtro_{session_key_vista}"
            )

            if año_grafico_sel == "Todos los años":
                df_grafico = df_target.dropna(subset=["N_MES_ENTREGA"]).copy()
                subtitulo_grafico = "(Histórico Consolidado)"
            else:
                df_grafico = df_target[(df_target["AÑO_ENTREGA"] == int(año_grafico_sel))].dropna(subset=["N_MES_ENTREGA"]).copy()
                subtitulo_grafico = f"({año_grafico_sel})"

            st.caption(f"Visualizando: {subtitulo_grafico}")

            if not df_grafico.empty:
                orden_meses = [
                    "01-Enero", "02-Febrero", "03-Marzo", "04-Abril", "05-Mayo", "06-Junio",
                    "07-Julio", "08-Agosto", "09-Septiembre", "10-Octubre", "11-Noviembre", "12-Diciembre"
                ]
                meses_es = {
                    1: "01-Enero", 2: "02-Febrero", 3: "03-Marzo", 4: "04-Abril", 5: "05-Mayo", 6: "06-Junio",
                    7: "07-Julio", 8: "08-Agosto", 9: "09-Septiembre", 10: "10-Octubre", 11: "11-Noviembre", 12: "12-Diciembre"
                }
                
                df_grouped = df_grafico.groupby("N_MES_ENTREGA").size().reset_index(name="Cantidad de Entregas")
                df_grouped["Mes"] = df_grouped["N_MES_ENTREGA"].map(meses_es)
                
                df_grouped = df_grouped.set_index("Mes").reindex(orden_meses).fillna(0)
                df_grouped = df_grouped[df_grouped["Cantidad de Entregas"] > 0]
                
                st.bar_chart(df_grouped["Cantidad de Entregas"], use_container_width=True)
            else:
                st.info("No hay datos disponibles para el período seleccionado en el gráfico.")

        else:
            st.sidebar.warning("No se encontraron años en los datos.")
    else:
        st.error("No se pudo cargar la fecha de entrega o los datos están vacíos.")

# ==========================================
# RENDERIZADO DE LAS PESTAÑAS
# ==========================================
if opcion == "📅 Planificación Entregas 0KM":
    render_agenda(df_0km, 'modo_vista_0km', "📅 Agenda de Entregas 0KM", es_usado=False)

elif opcion == "🚗 Agenda de Usados":
    render_agenda(df_usados, 'modo_vista_usados', "🚗 Agenda de Entregas Usados", es_usado=True)

elif opcion == "📦 Control de Stock y Documentación":
    st.title("📦 Panel Estratégico: Stock & Documentación 0KM")
    
    df_raw = df_0km.copy()
    
    if not df_raw.empty:
        # --- FILTROS SIDEBAR ---
        st.sidebar.header("Filtros Generales")
        if "MARCA" in df_raw.columns:
            marcas_sel = st.sidebar.multiselect("Filtrar Marca", df_raw["MARCA"].unique(), default=df_raw["MARCA"].unique())
            df_raw = df_raw[df_raw["MARCA"].isin(marcas_sel)]
            
        search = st.text_input("🔎 BUSCADOR DIRECTO (VIN, CLIENTE o MODELO)", placeholder="Escribe para buscar...").upper()
        if search:
            mask = df_raw.apply(lambda row: row.astype(str).str.contains(search, case=False).any(), axis=1)
            df_raw = df_raw[mask]

        col_target_admin = None
        if "ESTADO DE ADMINISTRATIVO" in df_raw.columns: col_target_admin = "ESTADO DE ADMINISTRATIVO"
        elif "ESTADO ADMINISTRATIVO" in df_raw.columns: col_target_admin = "ESTADO ADMINISTRATIVO"
        elif "DETALLE DEL ESTADO Y FECHA DE DISPONIBILIDAD DE UNIDAD" in df_raw.columns: col_target_admin = "DETALLE DEL ESTADO Y FECHA DE DISPONIBILIDAD DE UNIDAD"

        # Estandarizamos y limpiamos la columna ESTADO
        df_raw["ESTADO_CLEAN"] = df_raw["ESTADO"].astype(str).str.strip().str.upper()
        df_base_limpia = df_raw[df_raw["ESTADO"].notna() & (df_raw["ESTADO_CLEAN"] != "NAN") & (df_raw["ESTADO_CLEAN"] != "")]

        # Separación Base Metricas
        df_entregados_hist = df_base_limpia[df_base_limpia["ESTADO_CLEAN"] == "ENTREGADO"]
        df_stock_real = df_base_limpia[df_base_limpia["ESTADO_CLEAN"] != "ENTREGADO"]
        df_con_fecha = df_stock_real[df_stock_real["FECHA_ENTREGA_DT"].notna()]
        df_sin_fecha_base = df_stock_real[df_stock_real["FECHA_ENTREGA_DT"].isna()]

        # Regla cruzada estricta para Tarjeta 3 (SIN Fecha)
        col_cliente = "CLIENTE" if "CLIENTE" in df_sin_fecha_base.columns else None
        if col_cliente:
            df_sin_fecha_base["CLIENTE_UPPER"] = df_sin_fecha_base[col_cliente].astype(str).str.strip().str.upper()
            mask_tiene_cliente = (
                df_sin_fecha_base[col_cliente].notna() & 
                (df_sin_fecha_base["CLIENTE_UPPER"] != "") & 
                (df_sin_fecha_base["CLIENTE_UPPER"] != "NAN") & 
                (df_sin_fecha_base["CLIENTE_UPPER"] != "UNIDAD SIN CLIENTE ASIGNADO")
            )
            mask_tiene_pedido = df_sin_fecha_base["FECHA_PREPARACION_DT"].notna()
            df_sin_fecha = df_sin_fecha_base[mask_tiene_cliente | mask_tiene_pedido]
        else:
            df_sin_fecha = df_sin_fecha_base[df_sin_fecha_base["FECHA_PREPARACION_DT"].notna()]

        # --- BLOQUE 1: RENDERING KPI CARDS ---
        st.markdown("### 📈 Resumen del Embudo Operativo")
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("🏢 Total Stock Real", len(df_stock_real), help="Unidades vivas cargadas en stock. Excluye vacíos y entregados.")
        kpi2.metric("🚀 Con Fecha de Entrega", len(df_con_fecha), help="Vehículos en stock que poseen fecha confirmada de entrega.")
        kpi3.metric("🚨 SIN Fecha de Entrega", len(df_sin_fecha), help="Clientes reales en espera sin turno de entrega asignado.")
        kpi4.metric("✅ Entregados Históricos", len(df_entregados_hist), help="Total acumulado histórico de vehículos entregados.")
        
        st.markdown("---")

        # =========================================================
        # 📂 CONSTRUCCIÓN DE LAS PESTAÑAS ANIDADAS DINÁMICAS
        # =========================================================
        
        # 🏢 PESTAÑAS PRINCIPALES: Estado Físico de Unidad
        st.markdown("### 🏢 Estado Físico de Unidad")
        
        estados_existentes_clean = sorted(df_stock_real["ESTADO_CLEAN"].unique().tolist())
        titulos_pestañas_fisicas = [f"📋 Todos Real Stock ({len(df_stock_real)})"]
        
        # Mapeo estético de nombres de estado
        mapa_nombres_fisicos = {"EN EXHIBICIÓN": "En Exhibición", "EN EXHIBICION": "En Exhibición", "SIN PRE ENTREGA": "Sin Pre Entrega", "CON PRE ENTREGA": "Con Pre Entrega", "BLOQUEADO": "Bloqueado", "RESERVADO": "Reservado", "DISPONIBLE": "Disponible"}
        
        for est in estados_existentes_clean:
            cant = len(df_stock_real[df_stock_real["ESTADO_CLEAN"] == est])
            nombre_label = mapa_nombres_fisicos.get(est, est.title())
            titulos_pestañas_fisicas.append(f"{nombre_label} ({cant})")
            
        tabs_fisicas = st.tabs(titulos_pestañas_fisicas)
        
        # Definición estandarizada de estados de documentación para el sub-filtrado
        estados_clave_doc = [
            ("Ok Doc", "Ok doc"),
            ("Atopatentado sin cliente", "Atopatentado sin"),
            ("Autopatentado firma 08", "firma"),
            ("En caso legales", "legales"),
            ("Entrega al gestor", "gestor"),
            ("Firma titular", "titular")
        ]

        hoy_dt = pd.Timestamp.now().normalize()

        # Recorremos cada Pestaña Física Principal
        for idx_f, tab_f in enumerate(tabs_fisicas):
            with tab_f:
                # Segmentamos el DataFrame según la pestaña física seleccionada
                if idx_f == 0:
                    df_física_actual = df_stock_real.copy()
                else:
                    estado_clean_sel = estados_existentes_clean[idx_f - 1]
                    df_física_actual = df_stock_real[df_stock_real["ESTADO_CLEAN"] == estado_clean_sel].copy()
                
                # 📄 SUB-PESTAÑAS INTERNAS: Estado de Documentación
                st.markdown("#### 📄 Estado de Documentación")
                
                titulos_doc_tabs = [f"♾️ Cualquier Papel ({len(df_física_actual)})"]
                sub_filtros_validos = [None] # El primero corresponde a "Cualquier Papel"
                
                if col_target_admin:
                    for label_b, keyword in estados_clave_doc:
                        cant_d = len(df_física_actual[df_física_actual[col_target_admin].astype(str).str.contains(keyword, case=False, na=False)])
                        if cant_d > 0:
                            titulos_doc_tabs.append(f"{label_b} ({cant_d})")
                            sub_filtros_validos.append(keyword)
                            
                tabs_documentales = st.tabs(titulos_doc_tabs)
                
                # Recorremos cada Sub-Pestaña de Documentación
                for idx_d, tab_d in enumerate(tabs_documentales):
                    with tab_d:
                        # Aplicamos el filtro documental sobre los datos físicos actuales
                        keyword_actual = sub_filtros_validos[idx_d]
                        if keyword_actual and col_target_admin:
                            df_final_celda = df_física_actual[df_física_actual[col_target_admin].astype(str).str.contains(keyword_actual, case=False, na=False)].copy()
                        else:
                            df_final_celda = df_física_actual.copy()
                            
                        # --- CÁLCULO E INYECCIÓN DE TABLAS OPERATIVAS Y ALERTAS DE TALLER ---
                        df_op_con_fecha = df_final_celda[df_final_celda["FECHA_ENTREGA_DT"].notna()]
                        df_op_sin_fecha = df_final_celda[df_final_celda["FECHA_ENTREGA_DT"].isna()]
                        
                        if col_cliente:
                            df_op_sin_fecha["CLIENTE_UPPER"] = df_op_sin_fecha[col_cliente].astype(str).str.strip().str.upper()
                            mask_op_c = (
                                df_op_sin_fecha[col_cliente].notna() & 
                                (df_op_sin_fecha["CLIENTE_UPPER"] != "") & 
                                (df_op_sin_fecha["CLIENTE_UPPER"] != "NAN") & 
                                (df_op_sin_fecha["CLIENTE_UPPER"] != "UNIDAD SIN CLIENTE ASIGNADO")
                            )
                            mask_op_p = df_op_sin_fecha["FECHA_PREPARACION_DT"].notna()
                            df_op_pendientes = df_op_sin_fecha[mask_op_c | mask_op_p]
                        else:
                            df_op_pendientes = df_op_sin_fecha[df_op_sin_fecha["FECHA_PREPARACION_DT"].notna()]
                            
                        df_op_alerta_prep = df_op_pendientes[df_op_pendientes["FECHA_PREPARACION_DT"].notna()]
                        df_op_sin_fecha_sin_pedido = df_op_pendientes[df_op_pendientes["FECHA_PREPARACION_DT"].isna()]
                        
                        # Pequeño selector de radio horizontal para cambiar la vista de la tabla de forma compacta dentro de la pestaña
                        vista_tabla = st.radio(
                            "Seleccionar segmento operativo a visualizar en la tabla:",
                            options=[
                                f"🚨 Sin Fecha y Sin Pedido ({len(df_op_sin_fecha_sin_pedido)})",
                                f"🛠️ Alerta: En Preparación ({len(df_op_alerta_prep)})",
                                f"🚀 Con Fecha Confirmada ({len(df_op_con_fecha)})"
                            ],
                            horizontal=True,
                            key=f"radio_op_{idx_f}_{idx_d}"
                        )
                        
                        # Decision de renderizado basada en el Radio Box
                        if "🚨" in vista_tabla:
                            df_tabla_render = df_op_sin_fecha_sin_pedido
                            titulo_seccion_tabla = "Clientes Sin Fecha de Entrega y Bloqueados en Administración"
                            ordenar_por = "ANTIGÜEDAD DE STOCK" if "ANTIGÜEDAD DE STOCK" in df_tabla_render.columns else "CLIENTE"
                        elif "🛠️" in vista_tabla:
                            df_tabla_render = df_op_alerta_prep.copy()
                            if not df_tabla_render.empty:
                                df_tabla_render["DIAS_EN_TALLER"] = (hoy_dt - df_tabla_render["FECHA_PREPARACION_DT"]).dt.days
                                def asignar_emoji(dias):
                                    if dias >= 3: return f"🔴 {dias} días"
                                    elif dias >= 1: return f"⚠️ {dias} días"
                                    return f"🟢 {dias} días"
                                df_tabla_render["Alerta Tiempo"] = df_tabla_render["DIAS_EN_TALLER"].apply(asignar_emoji)
                            titulo_seccion_tabla = "Alerta de Taller: Pedidos autorizados listos para preparación"
                            ordenar_por = "DIAS_EN_TALLER" if not df_tabla_render.empty else "CLIENTE"
                        else:
                            df_tabla_render = df_op_con_fecha
                            titulo_seccion_tabla = "Agenda Confirmada Planificada para Entrega"
                            ordenar_por = "FECHA_ENTREGA_DT"
                            
                        st.markdown(f"##### 📋 {titulo_seccion_tabla} ({len(df_tabla_render)} unidades)")
                        
                        cols_mostrar_maestra = [
                            "VIN", "CLIENTE", "MARCA", "MODELO", "ESTADO", 
                            col_target_admin, "FECHA_PREPARACION_DT", "Alerta Tiempo", 
                            "FECHA_ENTREGA_DT", "UBICACION", "ANTIGÜEDAD DE STOCK", "ANTIGUEDAD DE STOCK"
                        ]
                        cols_reales_maestra = [c for c in cols_mostrar_maestra if c in df_tabla_render.columns]
                        df_final_maestro = df_tabla_render[cols_reales_maestra].loc[:, ~df_tabla_render[cols_reales_maestra].columns.duplicated()]
                        
                        if not df_final_maestro.empty:
                            asc = False if ordenar_por == "DIAS_EN_TALLER" else True
                            st.dataframe(
                                df_final_maestro.sort_values(ordenar_por, ascending=asc),
                                use_container_width=True,
                                hide_index=True,
                                column_config={
                                    "FECHA_PREPARACION_DT": st.column_config.DateColumn("F. Pedido Preparación", format="DD/MM/YYYY"),
                                    "FECHA_ENTREGA_DT": st.column_config.DateColumn("F. Entrega", format="DD/MM/YYYY"),
                                    "Alerta Tiempo": st.column_config.TextColumn("Alerta Taller (Días)"),
                                    col_target_admin: st.column_config.TextColumn("Estado Administrativo")
                                }
                            )
                        else:
                            st.success("✅ Todo al día para esta combinación de estados.")

        # --- ANALÍTICA GRÁFICA DE SOPORTE (Abajo de todo el modulo) ---
        st.markdown("---")
        st.markdown("### 📊 Analítica del Stock Pendiente de Entrega")
        g1, g2 = st.columns(2)
        with g1:
            st.markdown("##### Dónde están las trabas (Estado Administrativo)")
            if col_target_admin and not df_sin_fecha_base.empty:
                df_g1 = df_sin_fecha_base.copy()
                df_g1["Resumen Admin"] = df_g1[col_target_admin].fillna("Sin Especificar").astype(str).apply(
                    lambda x: next((name for label, name, kw in estados_clave_doc if kw in x.lower()), "Otros Trámites")
                )
                conteo_g1 = df_g1["Resumen Admin"].value_counts()
                st.bar_chart(conteo_g1, use_container_width=True)
            else:
                st.info("Sin datos pendientes.")
        with g2:
            st.markdown("##### Estado Físico de lo Pendiente")
            if "ESTADO" in df_sin_fecha_base.columns and not df_sin_fecha_base.empty:
                conteo_g2 = df_sin_fecha_base["ESTADO_CLEAN"].value_counts()
                st.bar_chart(conteo_g2, use_container_width=True)
            else:
                st.info("Sin datos pendientes.")
    else:
        st.error("Set de datos vacío.")

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
            motivos_hoy, motifs_semana, motifs_atrasados = [], [], []
            for intervalo, columna in cols_control.items():
                if not columna: continue
                fecha_vencimiento = fecha_arribo + timedelta(days=intervalo)
                estado_celda = str(row[columna]).strip().upper()
                if estado_celda in ["OK", "N/A", "SI"]: continue
                if fecha_vencimiento == hoy: motives_hoy = "Control"
                if fecha_vencimiento == hoy: motivos_hoy.append(f"Control {intervalo} días")
                if inicio_semana <= fecha_vencimiento <= fin_semana: motifs_semana.append(f"Control {intervalo} días ({fecha_vencimiento.strftime('%d/%m')})")
                if hoy >= fecha_vencimiento: motifs_atrasados.append(f"Falta {intervalo} días (Venció: {fecha_vencimiento.strftime('%d/%m')})")
            if motivos_hoy:
                r = row.copy(); r["TAREA"] = ", ".join(motivos_hoy); lista_hoy.append(r)
            if motifs_semana:
                r = row.copy(); r["TAREA"] = ", ".join(motifs_semana); lista_semana.append(r)
            if motifs_atrasados:
                r = row.copy(); r["TAREA"] = motifs_atrasados[-1]; lista_atrasados.append(r)
        
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
