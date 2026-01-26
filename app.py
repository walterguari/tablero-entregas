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
        height: 3.5em;
        font-weight: bold;
        border: 1px solid #e0e0e0;
    }
    .stMetric {
        background-color: #fff3e0;
        padding: 10px;
        border-radius: 5px;
        border: 1px solid #ffe0b2;
    }
    /* Estilo para los planos */
    .plano-img {
        border: 2px solid #333;
        border-radius: 10px;
        box-shadow: 5px 5px 15px rgba(0,0,0,0.2);
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

        col_tel = next((c for c in df.columns if "TELEFONO" in c or "CELULAR" in c or "TEL" in c), None)
        if col_tel: df["TELEFONO_CLEAN"] = df[col_tel]
        col_mail = next((c for c in df.columns if "CORREO" in c or "MAIL" in c), None)
        if col_mail: df["CORREO_CLEAN"] = df[col_mail]

        return df
    except Exception as e:
        st.error(f"Error: {e}")
        return pd.DataFrame()

df = load_data()

# --- MEMORIA DE ESTADO ---
if 'filtro_estado_stock' not in st.session_state: st.session_state.filtro_estado_stock = None
if 'modo_vista_agenda' not in st.session_state: st.session_state.modo_vista_agenda = 'mes'
if 'filtro_mantenimiento' not in st.session_state: st.session_state.filtro_mantenimiento = 'todos'

# ==========================================
# BARRA LATERAL
# ==========================================
if os.path.exists("logo.png.png"):
    st.sidebar.image("logo.png.png", use_container_width=True)
elif os.path.exists("logo.png"):
    st.sidebar.image("logo.png", use_container_width=True)
else:
    st.sidebar.warning("Sube el logo a GitHub")

st.sidebar.title("Navegación")
# AQUI AGREGAMOS LA NUEVA PESTAÑA AL MENU
opcion = st.sidebar.radio("Ir a:", ["📅 Planificación Entregas", "📦 Control de Stock", "🛠️ Control Mantenimiento", "🗺️ Plano del Salón"])
st.sidebar.markdown("---")

# ==========================================
# PESTAÑA 1: PLANIFICACIÓN DE ENTREGAS
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
        if c1.button(f"✅ Ya Entregados ({len(entregados)})", use_container_width=True):
            st.session_state.modo_vista_agenda = 'entregados'
        if c2.button(f"🚀 Programados ({len(programados)})", use_container_width=True):
            st.session_state.modo_vista_agenda = 'programados'
        if c3.button("📅 Filtrar por Mes / Día", use_container_width=True):
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
                    dia_filtro = st.date_input("📅 Filtrar día puntual", value=None, min_value=df_mes["FECHA_ENTREGA_DT"].min(), max_value=df_mes["FECHA_ENTREGA_DT"].max())
                
                if dia_filtro:
                    df_final = df_mes[df_mes["FECHA_ENTREGA_DT"].dt.date == dia_filtro]
                    titulo = f"Cronograma del {dia_filtro.strftime('%d/%m/%Y')} ({len(df_final)})"
                else:
                    df_final = df_mes
                    titulo = f"Cron
