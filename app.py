import streamlit as st
import pandas as pd
import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Portal Concesionaria", layout="wide", initial_sidebar_state="expanded")

# --- ESTILOS CSS (Botones y Métricas) ---
st.markdown("""
<style>
    div.stButton > button {width: 100%; border-radius: 10px; height: 3em;}
    [data-testid="stMetricValue"] {font-size: 2rem;}
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
        
        # --- PROCESAMIENTO FECHAS ---
        # 1. ENTREGA
        col_entrega = next((c for c in df.columns if "CONFIRMACI" in c and "ENTREGA" in c), None)
        if not col_entrega: col_entrega = next((c for c in df.columns if "FECHA" in c and "FACT" not in c), None)   
        if col_entrega:
            df["FECHA_ENTREGA_DT"] = pd.to_datetime(df[col_entrega], dayfirst=True, errors='coerce')
            df["AÑO_ENTREGA"] = df["FECHA_ENTREGA_DT"].dt.year
            df["MES_ENTREGA"] = df["FECHA_ENTREGA_DT"].dt.month_name()
            df["N_MES_ENTREGA"] = df["FECHA_ENTREGA_DT"].dt.month
        
        # 2. STOCK (ARRIBO)
        col_arribo = next((c for c in df.columns if "ARRIBO" in c), None)
        if col_arribo:
            df["FECHA_ARRIBO_DT"] = pd.to_datetime(df[col_arribo], dayfirst=True, errors='coerce')
            df["AÑO_ARRIBO"] = df["FECHA_ARRIBO_DT"].dt.year

        # 3. CONTACTO
        col_tel = next((c for c in df.columns if "TELEFONO" in c or "CELULAR" in c or "TEL" in c), None)
        if col_tel: df["TELEFONO_CLEAN"] = df[col_tel]
        col_mail = next((c for c in df.columns if "CORREO" in c or "MAIL" in c), None)
        if col_mail: df["CORREO_CLEAN"] = df[col_mail]

        return df
    except Exception as e:
        st.error(f"Error: {e}")
        return pd.DataFrame()

df = load_data()

# --- GESTIÓN DE ESTADO (MEMORIA) ---
if 'filtro_estado' not in st.session_state: st.session_state.filtro_estado = None

# --- MENÚ ---
st.sidebar.title("Navegación")
opcion = st.sidebar.radio("Ir a:", ["📅 Planificación Entregas", "📦 Control de Stock"])
st.sidebar.markdown("---")

# ==========================================
# VISTA 1: PLANIFICACIÓN DE ENTREGAS
# ==========================================
if opcion == "📅 Planificación Entregas":
    st.title("📅 Agenda de Entregas")
    
    # 1. Filtro Global de Año
    if not df.empty and "FECHA_ENTREGA_DT" in df.columns:
        años = sorted(df["AÑO_ENTREGA"].dropna().unique().astype(int))
        año_sel = st.sidebar.selectbox("Seleccionar Año", options=años, index=len(años)-1)
        
        # DataFrame del Año seleccionado
        df_año = df[df["AÑO_ENTREGA"] == año_sel]
        
        # --- CÁLCULO DE KPIs (LO NUEVO) ---
        hoy = datetime.date.today()
        
        # Filtramos dentro del año seleccionado
        entregados = df_año[df_año["FECHA_ENTREGA_DT"].dt.date < hoy]
        programados = df_año[df_año["FECHA_ENTREGA_DT"].dt.date >= hoy]
        
        # Mostramos las etiquetas grandes arriba
        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric("✅ Ya Entregados (Año)", len(entregados))
        kpi2.metric("🚀 Programados (Hoy+)", len(programados), delta=len(programados))
        kpi3.metric("📊 Total Anual", len(df_año))
        
        st.divider()

        # 2. Filtros de Detalle (Mes y Día)
        st.sidebar.header("Filtrar Mes")
        meses_nombres = df_año["MES_ENTREGA"].unique()
        meses_nums = df_año["N_MES_ENTREGA"].unique()
        mapa_meses = dict(zip(meses_nombres, meses_nums))
        
        if mapa_meses:
            mes_sel = st.sidebar.selectbox("Mes", options=sorted(mapa_meses.keys(), key=lambda x: mapa_meses[x]))
            df_mes = df_año[df_año["MES_ENTREGA"] == mes_sel].copy()
            
            # Filtro de día específico
            col_filtro, col_vacio = st.columns([1, 3])
            with col_filtro:
                dia_filtro = st.date_input("📅 Filtrar día puntual", value=None, 
                                          min_value=df_mes["FECHA_ENTREGA_DT"].min(), 
                                          max_value=df_mes["FECHA_ENTREGA_DT"].max())
            
            if dia_filtro:
                df_final = df_mes[df_mes["FECHA_ENTREGA_DT"].dt.date == dia_filtro]
                titulo = f"Cronograma del {dia_filtro.strftime('%d/%m/%Y')}"
            else:
                df_final = df_mes
                titulo = f"Cronograma Mensual - {mes_sel}"
            
            st.subheader(f"📋 {titulo}")
            
            # Tabla
            cols_agenda = ["FECHA_ENTREGA_DT", "HS DE ENTREGA AL CLIENTE", "CLIENTE", "MARCA", "MODELO", "CANAL DE VENTA", "TELEFONO_CLEAN", "CORREO_CLEAN", "VENDEDOR"]
            cols_reales = [c for c in cols_agenda if c in df_final.columns]
            
            st.dataframe(
                df_final[cols_reales].sort_values(["FECHA_ENTREGA_DT", "HS DE ENTREGA AL CLIENTE"]),
                use_container_width=True, hide_index=True,
                column_config={"FECHA_ENTREGA_DT": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY")}
            )
        else:
            st.warning("No hay datos para este año.")

# ==========================================
# VISTA 2: CONTROL DE STOCK
# ==========================================
elif opcion == "📦 Control de Stock":
    st.title("📦 Tablero de Stock")
    
    df_stock = df.copy()

    if not df_stock.empty:
        # Filtros Globales (Barra lateral)
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

        # --- BOTONES DE ESTADO ---
        st.markdown("### 🔍 Estado del Inventario")
        if "ESTADO" in df_stock.columns:
            conteo = df_stock["ESTADO"].value_counts()
            iconos = {"EN EXHIBICIÓN": "🏢", "EN EXHIBICION": "🏢", "SIN PRE ENTREGA": "🛠️", 
                      "CON PRE ENTREGA": "✨", "BLOQUEADO": "🔒", "ENTREGADO": "✅", "RESERVADO": "🔖"}

            cols = st.columns(len(conteo) + 1)
            with cols[0]:
                if st.button(f"📋 Todos ({len(df_stock)})", use_container_width=True):
                    st.session_state.filtro_estado = None

            for i, (estado, cantidad) in enumerate(conteo.items()):
                icono = iconos.get(str(estado).upper(), "🚗")
                col_destino = cols[i+1] if (i+1) < len(cols) else cols[-1]
                with col_destino:
                    if st.button(f"{icono} {estado} ({cantidad})", use_container_width=True):
                        st.session_state.filtro_estado = estado

            if st.session_state.filtro_estado:
                df_mostrar = df_stock[df_stock["ESTADO"] == st.session_state.filtro_estado]
                st.info(f"Filtro activo: **{st.session_state.filtro_estado}**")
            else:
                df_mostrar = df_stock
        else:
            df_mostrar = df_stock

        st.markdown("---")
        cols_stock = ["VIN", "MARCA", "MODELO", "DESCRIPCION COLOR", "FECHA DE FABRICACION", "ANTIGUEDAD DE STOCK", "ANTIGÜEDAD DE STOCK", "UBICACION", "DETALLE DEL ESTADO Y FECHA DE DISPONIBILIDAD DE UNIDAD", "ESTADO"]
        cols_reales = [c for c in cols_stock if c in df_mostrar.columns]
        st.dataframe(df_mostrar[cols_reales], use_container_width=True, hide_index=True)
