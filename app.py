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
        df = df.loc[:, ~df.columns.duplicated()]
        if df.empty: return df
            
        posibles_columnas_entrega = [lambda c: "CONFIRMACI" in c and "ENTREGA" in c, lambda c: "FECHA" in c and "ENTREGA" in c, lambda c: "FECHA" in c and "TURNO" in c, lambda c: "FECHA" in c and "FACT" not in c and "ARRIBO" not in c and "PAPELES" not in c]
        for criterio in posibles_columnas_entrega:
            if (col_entrega := next((c for c in df.columns if criterio(c)), None)):
                df["FECHA_ENTREGA_DT"] = pd.to_datetime(df[col_entrega], dayfirst=True, errors='coerce')
                df["AÑO_ENTREGA"] = df["FECHA_ENTREGA_DT"].dt.year
                df["MES_ENTREGA"] = df["FECHA_ENTREGA_DT"].dt.month_name()
                df["N_MES_ENTREGA"] = df["FECHA_ENTREGA_DT"].dt.month
                break
        else:
            df["FECHA_ENTREGA_DT"] = pd.NaT
            df["AÑO_ENTREGA"] = pd.NA
            df["MES_ENTREGA"] = "Sin Fecha"
            df["N_MES_ENTREGA"] = 0
        
        if (c := next((c for c in df.columns if "ARRIBO" in c), None)): df["FECHA_ARRIBO_DT"] = pd.to_datetime(df[c], dayfirst=True, errors='coerce')
        if (c := "FECHA DE FACTURACION DE LA UNIDAD") in df.columns: df["FECHA_FACTURACION_DT"] = pd.to_datetime(df[c], dayfirst=True, errors='coerce')
        if (c := "FECHA DISPONIBILIDAD PAPELES") in df.columns: df["FECHA_PAPELES_DT"] = pd.to_datetime(df[c], dayfirst=True, errors='coerce')
        if (c := next((c for c in df.columns if "PEDIDO" in c and "PREPARACI" in c), None)): df["FECHA_PREPARACION_DT"] = pd.to_datetime(df[c], dayfirst=True, errors='coerce')
        
        col_pedido_un = next((c for c in df.columns if "FECHA" in c and ("PEDIDO" in c or "COMPRA" in c) and "PREPARACI" not in c), None)
        df["FECHA_PEDIDO_UNIDAD_DT"] = pd.to_datetime(df[col_pedido_un], dayfirst=True, errors='coerce') if col_pedido_un else pd.NaT
        return df
    except Exception as e:
        st.error(f"Error cargando datos: {e}")
        return pd.DataFrame()

df_0km = load_data(URL_0KM, fila_header=0)
df_usados = load_data(URL_USADOS, fila_header=1)

# --- INICIALIZACIÓN ESTADO ---
for k in ['filtro_estado_stock', 'filtro_mantenimiento', 'filtro_doc_segmento', 'filtro_grafico_segmento', 'modo_vista_0km', 'modo_vista_usados']:
    if k not in st.session_state: st.session_state[k] = None if k == 'filtro_estado_stock' else 'todos' if k == 'filtro_mantenimiento' else '🚀 Con Fecha de Entrega' if k == 'filtro_doc_segmento' else '🚀 Vista: Con Fecha de Entrega'

# --- NAVEGACIÓN ---
st.sidebar.title("Navegación")
opcion = st.sidebar.radio("Ir a:", ["📅 Planificación Entregas 0KM", "🚗 Agenda de Usados", "📦 Control de Stock y Documentación", "🛠️ Control Mantenimiento", "🗺️ Plano del Salón"])

# [AQUÍ SE MANTIENE TODA TU LÓGICA ORIGINAL DE render_agenda, MANTENIMIENTO Y MAPAS]
# (Como el límite de respuesta no permite imprimir las 700+ líneas, he integrado el ajuste de control stock):

if opcion == "📦 Control de Stock y Documentación":
    st.title("📦 Panel Estratégico: Stock & Documentación 0KM")
    df_raw = df_0km.copy()
    if not df_raw.empty:
        # Lógica integrada de limpieza (Exclusión Reventas)
        df_raw["ESTADO_CLEAN"] = df_raw["ESTADO"].astype(str).str.strip().str.upper()
        df_operativo = df_raw[~df_raw["ESTADO_CLEAN"].str.contains("REVENTA", na=False)].copy()
        
        df_stock_real = df_operativo[df_operativo["ESTADO_CLEAN"] != "ENTREGADO"]
        df_con_fecha = df_stock_real[df_stock_real["FECHA_ENTREGA_DT"].notna()]
        
        # ... (Tu código de renders y KPIs) ...

        # TENDENCIA DE TIEMPOS PROMEDIO (AJUSTADO)
        if st.session_state.filtro_grafico_segmento == '🚀 Vista: Con Fecha de Entrega':
            df_g = df_con_fecha.dropna(subset=["FECHA_PEDIDO_UNIDAD_DT", "FECHA_PAPELES_DT", "FECHA_ENTREGA_DT"]).copy()
            df_g["DIF_P_E"] = (df_g["FECHA_ENTREGA_DT"] - df_g["FECHA_PEDIDO_UNIDAD_DT"]).dt.days
            df_g["DIF_PP_E"] = (df_g["FECHA_ENTREGA_DT"] - df_g["FECHA_PAPELES_DT"]).dt.days
            df_g = df_g[(df_g["DIF_P_E"] >= 0) & (df_g["DIF_PP_E"] >= 0)] # Filtro de cordura
            # ... tus graficos
            
# [PEGA EL RESTO DE TU CÓDIGO AQUÍ]
