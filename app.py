import streamlit as st
import pandas as pd
import datetime
from datetime import timedelta
import os
from streamlit_gsheets import GSheetsConnection

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
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
</style>
""", unsafe_allow_html=True)

# --- CONFIGURACIÓN DE ORÍGENES DE DATOS ---
SHEET_ID_0KM = "15hIQ6WBxh1Ymhh9dxerKvEnoXJ_osH6a9BH-1TW9ZU8"
GID_0KM = "1504374770"
URL_0KM = f"https://docs.google.com/spreadsheets/d/{SHEET_ID_0KM}/export?format=csv&gid={GID_0KM}"

# URL limpia para el conector de Google Sheets
URL_COMPLETA_USADOS = "https://docs.google.com/spreadsheets/d/1Kxy6d8xRR0WlypTVZygL1KHbc_i1MlNnd_JcEhCbc3c/edit"

# --- FUNCIONES DE CARGA ---
@st.cache_data(ttl=60)
def load_data_0km(url):
    try:
        df = pd.read_csv(url, header=0)
        if df is None or df.empty: return pd.DataFrame()
        df.columns = df.columns.str.strip().str.upper()
        df = df.loc[:, ~df.columns.duplicated()]
        return df
    except Exception as e:
        st.error(f"Error cargando datos 0KM: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60)
def load_data_usados_gsheets(url_base):
    try:
        # Usamos el conector robusto de Streamlit para interpretar la pestaña "Ciel"
        conn = st.connection("gsheets", type=GSheetsConnection)
        
        # Leemos indicando el nombre exacto de la pestaña y que los encabezados están en la fila 2 (header=1)
        df = conn.read(spreadsheet=url_base, worksheet="Ciel", header=1)
        
        if df is None or df.empty:
            return pd.DataFrame()
            
        # Limpieza de nombres de columnas y eliminación de fragmentos nulos por combinación
        df.columns = [str(c).strip().upper() for c in df.columns]
        df = df.loc[:, ~df.columns.str.contains('^UNNAMED')]
        df = df.loc[:, ~df.columns.duplicated()]
        df = df.dropna(how='all')
        
        return df
    except Exception as e:
        st.error(f"Error cargando pestaña 'Ciel' desde Google Sheets: {e}")
        return pd.DataFrame()

# --- PROCESAMIENTO GENERAL DE LOS DATASETS ---
def procesar_columnas_comunes(df):
    if df.empty: return df
    
    # Procesamiento de Fechas de Entrega
    col_entrega = None
    posibles_columnas_entrega = [
        lambda c: "CONFIRMACI" in c and "ENTREGA" in c,
        lambda c: "FECHA" in c and "ENTREGA" in c,
        lambda c: "FECHA" in c and "TURNO" in c,
        lambda c: "FECHA" in c and "FACT" not in c and "ARRIBO" not in c and "PAPELES" not in c
    ]
    for criterio in posibles_columnas_entrega:
        col_entrega = next((c for c in df.columns if criterio(c)), None)
        if col_entrega: break
            
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
        
    # Procesamiento de Arribos
    col_arribo = next((c for c in df.columns if "ARRIBO" in c), None)
    if col_arribo:
        df["FECHA_ARRIBO_DT"] = pd.to_datetime(df[col_arribo], dayfirst=True, errors='coerce')
        df["AÑO_ARRIBO"] = df["FECHA_ARRIBO_DT"].dt.year

    # Procesamiento de Papeles, Facturación y Pedidos
    col_fact = "FECHA DE FACTURACION DE LA UNIDAD"
    if col_fact in df.columns: df["FECHA_FACTURACION_DT"] = pd.to_datetime(df[col_fact], dayfirst=True, errors='coerce')
    col_papeles = "FECHA DISPONIBILIDAD PAPELES"
    if col_papeles in df.columns: df["FECHA_PAPELES_DT"] = pd.to_datetime(df[col_papeles], dayfirst=True, errors='coerce')
    
    col_prep = next((c for c in df.columns if "PEDIDO" in c and "PREPARACI" in c), None)
    df["FECHA_PREPARACION_DT"] = pd.to_datetime(df[col_prep], dayfirst=True, errors='coerce') if col_prep else pd.NaT

    col_pedido_un = next((c for c in df.columns if "FECHA" in c and ("PEDIDO" in c or "COMPRA" in c) and "PREPARACI" not in c), None)
    if col_pedido_un:
        df["FECHA_PEDIDO_UNIDAD_DT"] = pd.to_datetime(df[col_pedido_un], dayfirst=True, errors='coerce')
    else:
        df["FECHA_PEDIDO_UNIDAD_DT"] = pd.to_datetime(df[col_fact] if col_fact in df.columns else df["FECHA_PREPARACION_DT"], dayfirst=True, errors='coerce')

    col_tel = next((c for c in df.columns if "TELEFONO" in c or "CELULAR" in c or "TEL" in c), None)
    if col_tel: df["TELEFONO_CLEAN"] = df[col_tel]
    col_mail = next((c for c in df.columns if "CORREO" in c or "MAIL" in c), None)
    if col_mail: df["CORREO_CLEAN"] = df[col_mail]
    
    return df

# Carga y ejecución estructurada
raw_0km = load_data_0km(URL_0KM)
raw_usados = load_data_usados_gsheets(URL_COMPLETA_USADOS)

df_0km = procesar_columnas_comunes(raw_0km)
df_usados = procesar_columnas_comunes(raw_usados)

# --- MEMORIA DE ESTADO ---
if 'filtro_estado_stock' not in st.session_state: st.session_state.filtro_estado_stock = None
if 'filtro_estado_admin' not in st.session_state: st.session_state.filtro_estado_admin = None
if 'modo_vista_0km' not in st.session_state: st.session_state.modo_vista_0km = 'mes'
if 'modo_vista_usados' not in st.session_state: st.session_state.modo_vista_usados = 'mes'
if 'filtro_mantenimiento' not in st.session_state: st.session_state.filtro_mantenimiento = 'todos'
if 'filtro_doc_segmento' not in st.session_state: st.session_state.filtro_doc_segmento = '🚀 Con Fecha de Entrega'
if 'filtro_grafico_segmento' not in st.session_state: st.session_state.filtro_grafico_segmento = '🚀 Vista: Con Fecha de Entrega'

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

# FUNCIÓN AGENDA EN BI-VISTAS (COMPARTIDA)
def render_agenda(df_target, session_key_vista, titulo_seccion, es_usado=False):
    st.title(titulo_seccion)
    if not df_target.empty:
        # --- BLOQUE NUEVO: TARJETAS KPI DE RESUMEN SUPERIOR (COMO TU IMAGEN) ---
        hoy_dt = datetime.date.today()
        
        # Evitar fallos si no hay columna procesada de fecha de entrega
        if "FECHA_ENTREGA_DT" in df_target.columns:
            entregados_total = df_target[df_target["FECHA_ENTREGA_DT"].dt.date < hoy_dt]
            programados_total = df_target[df_target["FECHA_ENTREGA_DT"].dt.date >= hoy_dt]
            sin_fecha_total = df_target[df_target["FECHA_ENTREGA_DT"].isna()]
        else:
            entregados_total, programados_total, sin_fecha_total = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
            
        st.markdown("### 📊 Indicadores Operativos de la Agenda")
        kpi_col1, kpi_col2, kpi_col3 = st.columns(3)
        kpi_col1.metric("✅ Historial Entregados", len(entregados_total), help="Unidades cuya fecha confirmada es anterior a hoy.")
        kpi_col2.metric("🚀 Próximas Entregas", len(programados_total), help="Turnos agendados para hoy en adelante.")
        kpi_col3.metric("🚨 Unidades Sin Fecha", len(sin_fecha_total), help="Vehículos activos en el sistema que no registran día pactado.")
        st.markdown("---")
        
        # --- FILTROS DE NAVEGACIÓN SECUNDARIOS ---
        if "FECHA_ENTREGA_DT" in df_target.columns and df_target["AÑO_ENTREGA"].notna().any():
            años = sorted(df_target["AÑO_ENTREGA"].dropna().unique().astype(int))
            año_sel = st.sidebar.selectbox("Seleccionar Año", options=años, index=len(años)-1, key=f"sel_año_{session_key_vista}")
            df_año = df_target[df_target["AÑO_ENTREGA"] == año_sel]
            
            entregados = df_año[df_año["FECHA_ENTREGA_DT"].dt.date < hoy_dt]
            programados = df_año[df_año["FECHA_ENTREGA_DT"].dt.date >= hoy_dt]
            
            c1, c2, c3 = st.columns(3)
            type_ent = "primary" if st.session_state[session_key_vista] == 'entregados' else "secondary"
            type_prog = "primary" if st.session_state[session_key_vista] == 'programados' else "secondary"
            type_mes = "primary" if st.session_state[session_key_vista] == 'mes' else "secondary"

            if c1.button(f"✅ Segmento: Entregados Año ({len(entregados)})", use_container_width=True, type=type_ent, key=f"btn_ent_{session_key_vista}"):
                st.session_state[session_key_vista] = 'entregados'
            if c2.button(f"🚀 Segmento: Programados Año ({len(programados)})", use_container_width=True, type=type_prog, key=f"btn_prog_{session_key_vista}"):
                st.session_state[session_key_vista] = 'programados'
            if c3.button("📅 Vista Detallada: Mes / Día", use_container_width=True, type=type_mes, key=f"btn_mes_{session_key_vista}"):
                st.session_state[session_key_vista] = 'mes'
            st.divider()

            df_final = pd.DataFrame()
            titulo = ""
            
            if st.session_state[session_key_vista] == 'entregados':
                st.info(f"Historial de entregas consolidadas del año {año_sel}.")
                df_final = entregados
                titulo = f"Historial Entregado - {año_sel}"
            elif st.session_state[session_key_vista] == 'programados':
                st.info(f"Próximos turnos de entrega pactados a partir de hoy.")
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
                        dia_filtro = st.date_input("📅 Filtrar día específico", value=None, min_value=df_mes["FECHA_ENTREGA_DT"].min(), max_value=df_mes["FECHA_ENTREGA_DT"].max(), key=f"date_{session_key_vista}")
                    if dia_filtro:
                        df_final = df_mes[df_mes["FECHA_ENTREGA_DT"].dt.date == dia_filtro]
                        titulo = f"Cronograma del {dia_filtro.strftime('%d/%m/%Y')} ({len(df_final)})"
                    else:
                        df_final = df_mes
                        titulo = f"Cronograma Mensual - {mes_sel} ({len(df_final)})"
                else:
                    st.warning("No hay datos mensuales registrados.")

            if not df_final.empty:
                st.subheader(f"📋 {titulo}")
                config_columnas = {}
                
                if es_usado:
                    # Mapeo estructurado para la pestaña Ciel que arranca de fila 2
                    cols_agenda = ["FECHA_ENTREGA_DT", "HORA", "CLIENTE", "ESTADO DEL TRAMITE", "TIPO DE UNIDAD", "ESTADO DE UNIDAD", "MARCA", "MODELO", "DOMINIO", "TELEFONO_CLEAN", "VENDEDOR (BOLETO)"]
                    config_columnas = {
                        "FECHA_ENTREGA_DT": st.column_config.DateColumn("Fecha Confirmada", format="DD/MM/YYYY"),
                        "HORA": st.column_config.TextColumn("Hora"),
                        "CLIENTE": st.column_config.TextColumn("Cliente"),
                        "ESTADO DEL TRAMITE": st.column_config.TextColumn("Estado Trámite"),
                        "TIPO DE UNIDAD": st.column_config.TextColumn("Tipo Unidad"),
                        "ESTADO DE UNIDAD": st.column_config.TextColumn("Estado Físico"),
                        "MARCA": st.column_config.TextColumn("Marca"),
                        "MODELO": st.column_config.TextColumn("Modelo"),
                        "DOMINIO": st.column_config.TextColumn("Dominio"),
                        "TELEFONO_CLEAN": st.column_config.TextColumn("WhatsApp / Tel"),
                        "VENDEDOR (BOLETO)": st.column_config.TextColumn("Asesor Comercial")
                    }
                else:
                    col_admin = next((c for c in df_target.columns if "ESTADO" in c and "ADMIN" in c), None)
                    cols_agenda = ["FECHA_ENTREGA_DT", "HS DE ENTREGA AL CLIENTE", "CLIENTE"]
                    if col_admin: cols_agenda.append(col_admin)
                    cols_agenda.extend(["MARCA", "MODELO", "VIN", "CANAL DE VENTA", "TELEFONO_CLEAN", "VENDEDOR"])
                    config_columnas = {
                        "FECHA_ENTREGA_DT": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY"),
                        "HS DE ENTREGA AL CLIENTE": st.column_config.TextColumn("Hora"),
                        col_admin: st.column_config.TextColumn("Estado Admin") if col_admin else None
                    }
                
                cols_reales = [c for c in cols_agenda if c in df_final.columns]
                df_render = df_final[cols_reales].loc[:, ~df_final[cols_reales].columns.duplicated()]
                st.dataframe(df_render.sort_values(cols_reales[0] if cols_reales else "CLIENTE"), use_container_width=True, hide_index=True, column_config=config_columnas)
            else:
                if st.session_state[session_key_vista] != 'mes': st.info("No se registran operaciones en este segmento.")
            
            # --- GRÁFICOS MENSAL ---
            st.markdown("---")
            tipo_unidades = "0KM" if not es_usado else "Usados"
            st.subheader(f"📊 Volumen de Entregas por Mes {tipo_unidades}")
            opciones_grafico = ["Todos los años"] + [str(a) for a in años]
            año_grafico_sel = st.selectbox("Seleccionar período para el gráfico:", options=opciones_grafico, index=opciones_grafico.index(str(año_sel)), key=f"grafico_filtro_{session_key_vista}")

            if año_grafico_sel == "Todos los años":
                df_grafico = df_target.dropna(subset=["N_MES_ENTREGA"]).copy()
                subtitulo_grafico = "(Histórico Consolidado)"
            else:
                df_grafico = df_target[(df_target["AÑO_ENTREGA"] == int(año_grafico_sel))].dropna(subset=["N_MES_ENTREGA"]).copy()
                subtitulo_grafico = f"({año_grafico_sel})"

            st.caption(f"Visualizando: {subtitulo_grafico}")
            if not df_grafico.empty:
                orden_meses = ["01-Enero", "02-Febrero", "03-Marzo", "04-Abril", "05-Mayo", "06-Junio", "07-Julio", "08-Agosto", "09-Septiembre", "10-Octubre", "11-Noviembre", "12-Diciembre"]
                meses_es = {1: "01-Enero", 2: "02-Febrero", 3: "03-Marzo", 4: "04-Abril", 5: "05-Mayo", 6: "06-Junio", 7: "07-Julio", 8: "08-Agosto", 9: "09-Septiembre", 10: "10-Octubre", 11: "11-Noviembre", 12: "12-Diciembre"}
                df_grouped = df_grafico.groupby("N_MES_ENTREGA").size().reset_index(name="Cantidad de Entregas")
                df_grouped["Mes"] = df_grouped["N_MES_ENTREGA"].map(meses_es)
                df_grouped = df_grouped.set_index("Mes").reindex(orden_meses).fillna(0)
                df_grouped = df_grouped[df_grouped["Cantidad de Entregas"] > 0]
                st.bar_chart(df_grouped["Cantidad de Entregas"], use_container_width=True)
            else:
                st.info("No hay datos históricos para el rango seleccionado.")
        else:
            st.sidebar.warning("No se encontraron registros de años cronológicos.")
    else:
        st.error("Error en la lectura del origen de datos. Compruebe la estructura de la planilla o los permisos.")

# ==========================================
# LÓGICA DE MENÚS (0KM, USADOS, STOCK, ETC.)
# ==========================================
if opcion == "📅 Planificación Entregas 0KM":
    render_agenda(df_0km, 'modo_vista_0km', "📅 Agenda de Entregas 0KM", es_usado=False)

elif opcion == "🚗 Agenda de Usados":
    render_agenda(df_usados, 'modo_vista_usados', "🚗 Agenda de Entregas Usados (Hoja: Ciel)", es_usado=True)

elif opcion == "📦 Control de Stock y Documentación":
    st.title("📦 Panel Estratégico: Stock & Documentación 0KM")
    df_raw = df_0km.copy()
    
    if not df_raw.empty:
        st.sidebar.header("Filtros Generals")
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

        df_raw["ESTADO_CLEAN"] = df_raw["ESTADO"].astype(str).str.strip().str.upper()
        df_base_limpia = df_raw[df_raw["ESTADO"].notna() & (df_raw["ESTADO_CLEAN"] != "NAN") & (df_raw["ESTADO_CLEAN"] != "")]

        df_entregados_hist = df_base_limpia[df_base_limpia["ESTADO_CLEAN"] == "ENTREGADO"]
        df_stock_real = df_base_limpia[df_base_limpia["ESTADO_CLEAN"] != "ENTREGADO"]
        df_con_fecha = df_stock_real[df_stock_real["FECHA_ENTREGA_DT"].notna()]
        df_sin_fecha_base = df_stock_real[df_stock_real["FECHA_ENTREGA_DT"].isna()]

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
            mask_base_sin_fecha = mask_tiene_cliente | mask_tiene_pedido
            
            if col_target_admin:
                df_sin_fecha_base["ADMIN_UPPER"] = df_sin_fecha_base[col_target_admin].astype(str).str.strip().str.upper()
                mask_excluir_estados = (
                    df_sin_fecha_base["ADMIN_UPPER"].str.contains("LEGALES", na=False) |
                    df_sin_fecha_base["ADMIN_UPPER"].str.contains("SIN CLIENTE", na=False) |
                    df_sin_fecha_base["ADMIN_UPPER"].str.contains("REVENTA", na=False)
                )
                df_sin_fecha = df_sin_fecha_base[mask_base_sin_fecha & ~mask_excluir_estados]
            else:
                df_sin_fecha = df_sin_fecha_base[mask_base_sin_fecha]
        else:
            if col_target_admin:
                df_sin_fecha_base["ADMIN_UPPER"] = df_sin_fecha_base[col_target_admin].astype(str).str.strip().str.upper()
                mask_excluir_estados = (
                    df_sin_fecha_base["ADMIN_UPPER"].str.contains("LEGALES", na=False) |
                    df_sin_fecha_base["ADMIN_UPPER"].str.contains("SIN CLIENTE", na=False) |
                    df_sin_fecha_base["ADMIN_UPPER"].str.contains("REVENTA", na=False)
                )
                df_sin_fecha = df_sin_fecha_base[df_sin_fecha_base["FECHA_PREPARACION_DT"].notna() & ~mask_excluir_estados]
            else:
                df_sin_fecha = df_sin_fecha_base[df_sin_fecha_base["FECHA_PREPARACION_DT"].notna()]

        st.markdown("### 📈 Resumen del Embudo Operativo 0KM")
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("🏢 Total Stock Real", len(df_stock_real))
        kpi2.metric("🚀 Con Fecha de Entrega", len(df_con_fecha))
        kpi3.metric("🚨 SIN Fecha de Entrega", len(df_sin_fecha))
        kpi4.metric("✅ Entregados Históricos", len(df_entregados_hist))
        st.markdown("---")

        def renderizar_tabla_tiempos_operativa(df_segmento, key_origen):
            hoy_actual = pd.Timestamp.now().normalize()
            df_tabla = df_segmento.copy()
            if not df_tabla.empty:
                df_tabla["FECHA_PREPARACION_DT"] = df_tabla["FECHA_PREPARACION_DT"].fillna(hoy_actual)
                df_tabla["DIAS_PASADOS"] = (hoy_actual - df_tabla["FECHA_PREPARACION_DT"]).dt.days
                def alertar_semaforo(dias):
                    if dias >= 6: return f"🔴 Crítico ({dias} días)"
                    elif dias >= 3: return f"⚠️ Demorado ({dias} días)"
                    return f"🟢 Al Día ({dias} días)"
                df_tabla["ALERTA_OPERATIVA"] = df_tabla["DIAS_PASADOS"].apply(alertar_semaforo)
            else:
                df_tabla["DIAS_PASADOS"] = pd.Series(dtype=int)
                df_tabla["ALERTA_OPERATIVA"] = pd.Series(dtype=str)

            col_vendedor = "VENDEDOR" if "VENDEDOR" in df_tabla.columns else ("VENDEDOR (BOLETO)" if "VENDEDOR (BOLETO)" in df_tabla.columns else "VENDEDOR")
            col_canal = "CANAL DE VENTA" if "CANAL DE VENTA" in df_tabla.columns else "CANAL DE VENTA"
            cols_estructuradas = ["VIN", "CLIENTE", col_vendedor, col_canal, "MARCA", "MODELO", "FECHA_PREPARACION_DT", "FECHA_ENTREGA_DT", "DIAS_PASADOS", "ALERTA_OPERATIVA"]
            cols_reales_tabla = [c for c in cols_estructuradas if c in df_tabla.columns]
            df_render_maestro = df_tabla[cols_reales_tabla].loc[:, ~df_tabla[cols_reales_tabla].columns.duplicated()]
            
            if not df_render_maestro.empty:
                st.dataframe(
                    df_render_maestro.sort_values(by="DIAS_PASADOS" if "DIAS_PASADOS" in df_render_maestro.columns else "CLIENTE", ascending=False),
                    use_container_width=True, hide_index=True,
                    column_config={
                        "FECHA_PREPARACION_DT": st.column_config.DateColumn("Fecha Pedido Preparación", format="DD/MM/YYYY"),
                        "FECHA_ENTREGA_DT": st.column_config.DateColumn("Fecha Confirmación Entrega", format="DD/MM/YYYY"),
                        "DIAS_PASADOS": st.column_config.NumberColumn("Tiempo Transcurrido (Días)", format="%d"),
                        "ALERTA_OPERATIVA": st.column_config.TextColumn("Alerta Operativa")
                    }
                )
            else:
                st.success("✅ Todo al día para esta combinación de estados en el sistema.")

        tab_sub_fisico, tab_sub_documental = st.tabs(["🏢 Estado Físico de Unidad", "📄 Estado de Documentación"])

        with tab_sub_fisico:
            if "ESTADO" in df_stock_real.columns:
                conteo_fisico = df_stock_real["ESTADO_CLEAN"].value_counts()
                iconos_stock = {"EN EXHIBICIÓN": "🏢", "EN EXHIBICION": "🏢", "SIN PRE ENTREGA": "🛠️", "CON PRE ENTREGA": "✨", "BLOQUEADO": "🔒", "RESERVADO": "🔖", "DISPONIBLE": "🟢"}
                cols_f = st.columns(len(conteo_fisico) + 1)
                with cols_f[0]:
                    type_t = "primary" if st.session_state.filtro_estado_stock is None else "secondary"
                    if st.button(f"📋 Todos Real Stock ({len(df_stock_real)})", use_container_width=True, key="btn_f_todos_puro", type=type_t):
                        st.session_state.filtro_estado_stock = None
                for idx, (est, cant) in enumerate(conteo_fisico.items()):
                    ic = iconos_stock.get(str(est), "🚗")
                    col_dst = cols_f[idx+1] if (idx+1) < len(cols_f) else cols_f[-1]
                    with col_dst:
                        type_b = "primary" if st.session_state.filtro_estado_stock == est else "secondary"
                        if st.button(f"{ic} {est.title()} ({cant})", use_container_width=True, key=f"btn_f_item_{idx}", type=type_b):
                            st.session_state.filtro_estado_stock = est

            df_resultado_fisico = df_stock_real.copy()
            if st.session_state.filtro_estado_stock:
                df_resultado_fisico = df_resultado_fisico[df_resultado_fisico["ESTADO_CLEAN"] == st.session_state.filtro_estado_stock]
            st.markdown("<br>", unsafe_allow_html=True)
            renderizar_tabla_tiempos_operativa(df_resultado_fisico, "tabla_fisica_pura")

        with tab_sub_documental:
            col_b1, col_b2 = st.columns(2)
            type_b1 = "primary" if st.session_state.filtro_doc_segmento == '🚀 Con Fecha de Entrega' else "secondary"
            type_b2 = "primary" if st.session_state.filtro_doc_segmento == '🚨 SIN Fecha de Entrega' else "secondary"
            with col_b1:
                if st.button(f"🚀 Con Fecha de Entrega ({len(df_con_fecha)})", use_container_width=True, type=type_b1, key="btn_doc_con_fecha"):
                    st.session_state.filtro_doc_segmento = '🚀 Con Fecha de Entrega'
            with col_b2:
                if st.button(f"🚨 SIN Fecha de Entrega ({len(df_sin_fecha)})", use_container_width=True, type=type_b2, key="btn_doc_sin_fecha"):
                    st.session_state.filtro_doc_segmento = '🚨 SIN Fecha de Entrega'
                    
            st.markdown("<br>", unsafe_allow_html=True)
            if st.session_state.filtro_doc_segmento == '🚀 Con Fecha de Entrega':
                df_tabla_doc_act = df_con_fecha.copy()
                if not df_tabla_doc_act.empty:
                    df_tabla_doc_act["DIF_PEDIDO_ENTREGA"] = (df_tabla_doc_act["FECHA_ENTREGA_DT"] - df_tabla_doc_act["FECHA_PEDIDO_UNIDAD_DT"]).dt.days
                    df_tabla_doc_act["DIF_PAPELES_ENTREGA"] = (df_tabla_doc_act["FECHA_ENTREGA_DT"] - df_tabla_doc_act["FECHA_PAPELES_DT"]).dt.days
                    df_tabla_doc_act["DIF_PEDIDO_ENTREGA"] = df_tabla_doc_act["DIF_PEDIDO_ENTREGA"].fillna(0).astype(int)
                    df_tabla_doc_act["DIF_PAPELES_ENTREGA"] = df_tabla_doc_act["DIF_PAPELES_ENTREGA"].fillna(0).astype(int)
                else:
                    df_tabla_doc_act["DIF_PEDIDO_ENTREGA"] = pd.Series(dtype=int)
                    df_tabla_doc_act["DIF_PAPELES_ENTREGA"] = pd.Series(dtype=int)
                cols_a_mostrar = ["MARCA", "VIN", "CLIENTE", col_canal_native, col_vendedor_native, "DIF_PEDIDO_ENTREGA", "DIF_PAPELES_ENTREGA"]
                cols_reales_a = [c for c in cols_a_mostrar if c in df_tabla_doc_act.columns]
                st.dataframe(df_tabla_doc_act[cols_reales_a].loc[:, ~df_tabla_doc_act[cols_reales_a].columns.duplicated()], use_container_width=True, hide_index=True)
            else:
                df_tabla_doc_pend = df_sin_fecha.copy()
                if not df_tabla_doc_pend.empty:
                    df_tabla_doc_pend["DIF_PEDIDO_HOY"] = (hoy_dt - df_tabla_doc_pend["FECHA_PEDIDO_UNIDAD_DT"]).dt.days
                    df_tabla_doc_pend["DIF_PAPELES_HOY"] = (hoy_dt - df_tabla_doc_pend["FECHA_PAPELES_DT"]).dt.days
                    df_tabla_doc_pend["DIF_PEDIDO_HOY"] = df_tabla_doc_pend["DIF_PEDIDO_HOY"].fillna(0).astype(int)
                    df_tabla_doc_pend["DIF_PAPELES_HOY"] = df_tabla_doc_pend["DIF_PAPELES_HOY"].fillna(0).astype(int)
                else:
                    df_tabla_doc_pend["DIF_PEDIDO_HOY"] = pd.Series(dtype=int)
                    df_tabla_doc_pend["DIF_PAPELES_HOY"] = pd.Series(dtype=int)
                cols_b_mostrar = ["MARCA", "VIN", "CLIENTE", "TELEFONO_CLEAN", col_canal_native, col_vendedor_native, "DIF_PEDIDO_HOY", "DIF_PAPELES_HOY"]
                cols_reales_b = [c for c in cols_b_mostrar if c in df_tabla_doc_pend.columns]
                st.dataframe(df_tabla_doc_pend[cols_reales_b].loc[:, ~df_tabla_doc_pend[cols_reales_b].columns.duplicated()], use_container_width=True, hide_index=True)
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
        if "ESTADO" in df_mant.columns: df_mant = df_mant[df_mant["ESTADO"].astype(str).str.strip().str.upper() != "ENTREGADO"]
        if marcas: df_mant = df_mant[df_mant["MARCA"].isin(marcas)]
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
                if fecha_vencimiento == hoy: motivos_hoy.append(f"Control {intervalo} dias")
                if inicio_semana <= fecha_vencimiento <= fin_semana: motifs_semana.append(f"Control {intervalo} dias ({fecha_vencimiento.strftime('%d/%m')})")
                if hoy >= fecha_vencimiento: motifs_atrasados.append(f"Falta {intervalo} dias (Vencio: {fecha_vencimiento.strftime('%d/%m')})")
            if motivos_hoy: r = row.copy(); r["TAREA"] = ", ".join(motivos_hoy); lista_hoy.append(r)
            if motifs_semana: r = row.copy(); r["TAREA"] = ", ".join(motifs_semana); lista_semana.append(r)
            if motifs_atrasados: r = row.copy(); r["TAREA"] = motifs_atrasados[-1]; lista_atrasados.append(r)
        
        c1, c2, c3 = st.columns(3)
        t_hoy = "primary" if st.session_state.filtro_mantenimiento == 'hoy' else "secondary"
        t_sem = "primary" if st.session_state.filtro_mantenimiento == 'semana' else "secondary"
        t_tod = "primary" if st.session_state.filtro_mantenimiento == 'todos' else "secondary"

        if c1.button(f"📅 Vence HOY ({len(lista_hoy)})", use_container_width=True, type=t_hoy): st.session_state.filtro_mantenimiento = 'hoy'
        if c2.button(f"📆 Vence Esta Semana ({len(lista_semana)})", use_container_width=True, type=t_sem): st.session_state.filtro_mantenimiento = 'semana'
        if c3.button(f"🚨 Todo Pendiente ({len(lista_atrasados)})", use_container_width=True, type=t_tod): st.session_state.filtro_mantenimiento = 'todos'
        st.divider()
        
        df_final = pd.DataFrame()
        if st.session_state.filtro_mantenimiento == 'hoy': df_final = pd.DataFrame(lista_hoy); titulo = "🚗 Vehiculos que vencen HOY"
        elif st.session_state.filtro_mantenimiento == 'semana': df_final = pd.DataFrame(lista_semana); titulo = "🗓️ Planificacion Semanal"
        else: df_final = pd.DataFrame(lista_atrasados); titulo = "⚠️ Listado de Atrasados / Pendientes"
        
        if not df_final.empty:
            cols_base = ["VIN", "MARCA", "MODELO", "FECHA_ARRIBO_DT", "TAREA", "UBICACION"]
            st.dataframe(df_final[[c for c in cols_base if c in df_final.columns]], use_container_width=True, hide_index=True)

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
