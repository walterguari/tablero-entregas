import streamlit as st
import pandas as pd
import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Planificación Entregas", layout="wide", initial_sidebar_state="expanded")

# --- CARGA DE DATOS ---
SHEET_ID = "15hIQ6WBxh1Ymhh9dxerKvEnoXJ_osH6a9BH-1TW9ZU8"
GID = "1504374770"
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

@st.cache_data(ttl=60)
def load_data():
    try:
        df = pd.read_csv(URL)
        # Limpiamos nombres de columnas: mayúsculas y sin espacios al inicio/final
        df.columns = df.columns.str.strip().str.upper()
        
        # --- BÚSQUEDA DE LA COLUMNA FECHA ---
        # Buscamos específicamente "FECHA DE CONFIRMACIÓN" o "FECHA"
        col_fecha = next((c for c in df.columns if "CONFIRMACI" in c and "ENTREGA" in c), None)
        if not col_fecha:
            col_fecha = next((c for c in df.columns if "FECHA" in c), None)

        if col_fecha:
            # Convertimos a formato fecha
            df["FECHA_OFICIAL"] = pd.to_datetime(df[col_fecha], dayfirst=True, errors='coerce')
            # Creamos columnas auxiliares para filtrar
            df["AÑO"] = df["FECHA_OFICIAL"].dt.year
            df["MES"] = df["FECHA_OFICIAL"].dt.month_name()
            df["N_MES"] = df["FECHA_OFICIAL"].dt.month
            df["SEMANA"] = df["FECHA_OFICIAL"].dt.isocalendar().week
            df["DIA_SEMANA"] = df["FECHA_OFICIAL"].dt.day_name()
        
        return df
    except Exception as e:
        st.error(f"Error cargando datos: {e}")
        return pd.DataFrame()

df = load_data()

# --- BARRA LATERAL (FILTROS) ---
st.sidebar.header("🔍 Filtros de Planificación")

if not df.empty and "FECHA_OFICIAL" in df.columns:
    # 1. Filtro AÑO
    años_disponibles = sorted(df["AÑO"].dropna().unique().astype(int))
    año_sel = st.sidebar.selectbox("Seleccionar Año", options=años_disponibles, index=len(años_disponibles)-1)
    
    # Filtramos primero por año
    df_año = df[df["AÑO"] == año_sel]
    
    # 2. Filtro MES (Dinámico según el año)
    meses_disponibles = df_año["N_MES"].unique()
    meses_nombres = df_año["MES"].unique()
    mapa_meses = dict(zip(meses_nombres, meses_disponibles))
    
    # Ordenamos los meses cronológicamente
    if mapa_meses:
        mes_sel_nombre = st.sidebar.selectbox("Seleccionar Mes", options=sorted(mapa_meses.keys(), key=lambda x: mapa_meses[x]))
        df_final = df_año[df_año["MES"] == mes_sel_nombre].copy()
    else:
        st.sidebar.warning("No hay datos de meses para este año.")
        df_final = pd.DataFrame() # Tabla vacía
    
    st.sidebar.markdown("---")
    st.sidebar.info(f"Mostrando datos de: **{mes_sel_nombre} {año_sel}**")

else:
    st.sidebar.warning("Esperando datos...")
    df_final = pd.DataFrame()

# --- PANTALLA PRINCIPAL ---
st.title("📅 Tablero de Entregas")

if not df_final.empty:
    # Métricas superiores
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Vehículos a Entregar", len(df_final))
    col2.metric("Semanas con Actividad", df_final["SEMANA"].nunique())
    # Intentamos contar marcas si existe la columna
    if "MARCA" in df_final.columns:
