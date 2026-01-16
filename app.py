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
        # Limpieza general de columnas
        df.columns = df.columns.str.strip().str.upper()
        
        # --- PROCESAMIENTO PARA ENTREGAS ---
        col_entrega = next((c for c in df.columns if "CONFIRMACI" in c and "ENTREGA" in c), None)
        if not col_entrega:
            col_entrega = next((c for c in df.columns if "FECHA" in c), None)
            
        if col_entrega:
            df["FECHA_ENTREGA_DT"] = pd.to_datetime(df[col_entrega], dayfirst=True, errors='coerce')
            df["AÑO_ENTREGA"] = df["FECHA_ENTREGA_DT"].dt.year
            df["MES_ENTREGA"] = df["FECHA_ENTREGA_DT"].dt.month_name()
            df["N_MES_ENTREGA"] = df["FECHA_ENTREGA_DT"].dt.month
            df["SEMANA_ENTREGA"] = df["FECHA_ENTREGA_DT"].dt.isocalendar().week

        # --- PROCESAMIENTO PARA STOCK (FECHA ARRIBO) ---
        # Buscamos la columna "FECHA ARRIBO" (basado en tu imagen)
        col_arribo = next((c for c in df.columns if "ARRIBO" in c), None)
        
        if col_arribo:
            df["FECHA_ARRIBO_DT"] = pd.to_datetime(df[col_arribo], dayfirst=True, errors='coerce')
            df["AÑO_ARRIBO"] = df["FECHA_ARRIBO_DT"].dt.year
            df["MES_ARRIBO"] = df["FECHA_ARRIBO_DT"].dt.month_name()
            df["N_MES_ARRIBO"] = df["FECHA_ARRIBO_DT"].dt.month
            
        return df
    except Exception as e:
        st.error(f"Error cargando datos: {e}")
        return pd.DataFrame()

df = load_data()

# --- MENÚ DE NAVEGACIÓN ---
st.sidebar.title("Navegación")
opcion = st.sidebar.radio("Ir a:", ["📅 Planificación Entregas", "📦 Control de Stock"])
st.sidebar.markdown("---")

# ==========================================
# VISTA 1: PLANIFICACIÓN DE ENTREGAS
# ==========================================
if opcion == "📅 Planificación Entregas":
    st.title("📅 Planificación de Entregas")
    st.sidebar.header("Filtros de Entrega")

    if not df.empty and "FECHA_ENTREGA_DT" in df.columns:
        # Filtro AÑO
        años = sorted(df["AÑO_ENTREGA"].dropna().unique().astype(int))
        año_sel = st.sidebar.selectbox("Año", options=años, index=len(años)-1)
        df_año = df[df["AÑO_ENTREGA"] == año_sel]
        
        # Filtro MES
        meses_nombres = df_año["MES_ENTREGA"].unique()
        meses_nums = df_año["N_MES_ENTREGA"].unique()
        mapa_meses = dict(zip(meses_nombres, meses_nums))
        
        if mapa_meses:
            mes_sel = st.sidebar.selectbox("Mes", options=sorted(mapa_meses.keys(), key=lambda x: mapa_meses[x]))
            df_final = df_año[df_año["MES_ENTREGA"] == mes_sel].copy()
            
            # Métricas
            c1, c2 = st.columns(2)
            c1.metric("Vehículos a Entregar", len(df_final))
            c2.metric("Semanas Activas", df_final["SEMANA_ENTREGA"].nunique())

            # Gráfico
            st.subheader("Distribución Semanal")
            conteo = df_final["SEMANA_ENTREGA"].value_counts().sort_index().reset_index()
            conteo.columns = ["Semana", "Cantidad"]
            st.bar_chart(conteo.set_index("Semana"))

            # Tabla Entregas
            st.subheader("Listado de Entregas")
            cols_entrega = ["FECHA_ENTREGA_DT", "HS DE ENTREGA AL CLIENTE", "CLIENTE", "MARCA", "MODELO", "VIN", "DESCRIPCION COLOR"]
            cols_reales = [c for c in cols_entrega if c in df_final.columns]
            
            st.dataframe(
                df_final[cols_reales].sort_values("FECHA_ENTREGA_DT"),
                use_container_width=True,
                hide_index=True,
                column_config={"FECHA_ENTREGA_DT": st.column_config.DateColumn("Fecha Entrega", format="DD/MM/YYYY")}
            )
        else:
            st.warning("No hay datos para el año seleccionado.")
    else:
        st.info("No se encontraron fechas de entrega para analizar.")

# ==========================================
# VISTA 2: CONTROL DE STOCK (NUEVA HOJA)
# ==========================================
elif opcion == "📦 Control de Stock":
    st.title("📦 Tablero de Stock y Arribos")
    st.sidebar.header("Filtros de Stock")
    
    df_stock = df.copy()

    if not df_stock.empty:
        # --- FILTROS DE STOCK ---
        
        # 1. Filtro Fecha Arribo (Opcional)
        if "AÑO_ARRIBO" in df_stock.columns:
            usar_filtro_fecha = st.sidebar.checkbox("Filtrar por Fecha de Arribo")
            if usar_filtro_fecha:
                años_arribo = sorted(df_stock["AÑO_ARRIBO"].dropna().unique().astype(int))
                if años_arribo:
                    año_arribo_sel = st.sidebar.selectbox("Año Arribo", años_arribo, index=len(años_arribo)-1)
                    df_stock = df_stock[df_stock["AÑO_ARRIBO"] == año_arribo_sel]
                    
                    meses_arribo = df_stock["MES_ARRIBO"].unique()
                    if len(meses_arribo) > 0:
                        mes_arribo_sel = st.sidebar.selectbox("Mes Arribo", meses_arribo)
                        df_stock = df_stock[df_stock["MES_ARRIBO"] == mes_arribo_sel]

        # 2. Filtro MARCA
        if "MARCA" in df_stock.columns:
            todas_marcas = df_stock["MARCA"].unique()
            marcas_sel = st.sidebar.multiselect("Marca", options=todas_marcas, default=todas_marcas)
            df_stock = df_stock[df_stock["MARCA"].isin(marcas_sel)]

        # 3. Filtro ESTADO
        if "ESTADO" in df_stock.columns:
            todos_estados = df_stock["ESTADO"].unique()
            estados_sel = st.sidebar.multiselect("Estado", options=todos_estados, default=todos_estados)
            df_stock = df_stock[df_stock["ESTADO"].isin(estados_sel)]

        # --- ETIQUETA DE CANTIDAD ---
        st.markdown(f"### 🚗 Unidades en lista: **{len(df_stock)}**")
        
        # --- TABLA CON COLUMNAS SOLICITADAS ---
        # Definimos las columnas exactas que pediste en la imagen
        cols_stock_pedidas = [
            "VIN", 
            "MARCA", 
            "MODELO", 
            "DESCRIPCION COLOR", 
            "FECHA DE FABRICACION", 
            "ANTIGÜEDAD DE STOCK", # Ojo: puede variar si lleva acento o no en tu CSV
            "ANTIGUEDAD DE STOCK", # Probamos ambas opciones
            "UBICACION", 
            "DETALLE DEL ESTADO Y FECHA DE DISPONIBILIDAD DE UNIDAD"
        ]
        
        # Filtramos solo las que existen para que no de error
        cols_finales_stock = [c for c in cols_stock_pedidas if c in df_stock.columns]
        
        # Agregamos Fecha Arribo si existe
        col_arribo_orig = next((c for c in df.columns if "ARRIBO" in c and "FECHA" in c), None)
        if col_arribo_orig and col_arribo_orig not in cols_finales_stock:
             cols_finales_stock.insert(4, col_arribo_orig)

        st.dataframe(
            df_stock[cols_finales_stock],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.warning("No hay datos disponibles.")
