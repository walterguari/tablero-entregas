import streamlit as st
import pandas as pd
import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Portal Concesionaria", layout="wide", initial_sidebar_state="expanded")

# --- CARGA DE DATOS ---
SHEET_ID = "15hIQ6WBxh1Ymhh9dxerKvEnoXJ_osH6a9BH-1TW9ZU8"
GID = "1504374770"
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

@st.cache_data(ttl=60)
def load_data():
    try:
        df = pd.read_csv(URL)
        # Limpieza general de columnas: Mayúsculas y sin espacios
        df.columns = df.columns.str.strip().str.upper()
        
        # --- BUSCADOR INTELIGENTE DE COLUMNAS ---
        # 1. FECHA DE ENTREGA
        col_entrega = next((c for c in df.columns if "CONFIRMACI" in c and "ENTREGA" in c), None)
        if not col_entrega:
            col_entrega = next((c for c in df.columns if "FECHA" in c and "FACT" not in c), None)
            
        if col_entrega:
            df["FECHA_ENTREGA_DT"] = pd.to_datetime(df[col_entrega], dayfirst=True, errors='coerce')
            df["AÑO_ENTREGA"] = df["FECHA_ENTREGA_DT"].dt.year
            df["MES_ENTREGA"] = df["FECHA_ENTREGA_DT"].dt.month_name()
            df["N_MES_ENTREGA"] = df["FECHA_ENTREGA_DT"].dt.month
            df["SEMANA_ENTREGA"] = df["FECHA_ENTREGA_DT"].dt.isocalendar().week
        
        # 2. FECHA DE ARRIBO (STOCK)
        col_arribo = next((c for c in df.columns if "ARRIBO" in c), None)
        if col_arribo:
            df["FECHA_ARRIBO_DT"] = pd.to_datetime(df[col_arribo], dayfirst=True, errors='coerce')
            df["AÑO_ARRIBO"] = df["FECHA_ARRIBO_DT"].dt.year
            df["MES_ARRIBO"] = df["FECHA_ARRIBO_DT"].dt.month_name()

        # 3. NORMALIZACIÓN DE COLUMNAS DE CONTACTO (Para que las encuentre siempre)
        # Busca Teléfono/Celular
        col_tel = next((c for c in df.columns if "TELEFONO" in c or "CELULAR" in c), None)
        if col_tel: df["TELEFONO_CLEAN"] = df[col_tel
