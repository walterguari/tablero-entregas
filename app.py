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

        # 3. NORMALIZACIÓN DE COLUMNAS DE CONTACTO
        # Busca Teléfono/Celular
        col_tel = next((c for c in df.columns if "TELEFONO" in c or "CELULAR" in c), None)
        if col_tel: 
            df["TELEFONO_CLEAN"] = df[col_tel]
        
        # Busca Correo/Mail
        col_mail = next((c for c in df.columns if "CORREO" in c or "MAIL" in c or "EMAIL" in c), None)
        if col_mail: 
            df["CORREO_CLEAN"] = df[col_mail]

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
# VISTA 1: PLANIFICACIÓN DE ENTREGAS (AGENDA)
# ==========================================
if opcion == "📅 Planificación Entregas":
    st.title("📅 Agenda de Entregas")
    
    st.sidebar.header("Filtros de Agenda")

    if not df.empty and "FECHA_ENTREGA_DT" in df.columns:
        # 1. Filtro AÑO (Sidebar)
        años = sorted(df["AÑO_ENTREGA"].dropna().unique().astype(int))
        año_sel = st.sidebar.selectbox("Año", options=años, index=len(años)-1)
        df_año = df[df["AÑO_ENTREGA"] == año_sel]
        
        # 2. Filtro MES (Sidebar)
        meses_nombres = df_año["MES_ENTREGA"].unique()
        meses_nums = df_año["N_MES_ENTREGA"].unique()
        mapa_meses = dict(zip(meses_nombres, meses_nums))
        
        if mapa_meses:
            mes_sel = st.sidebar.selectbox("Mes", options=sorted(mapa_meses.keys(), key=lambda x: mapa_meses[x]))
            df_mes = df_año[df_año["MES_ENTREGA"] == mes_sel].copy()
            
            # 3. FILTRO DE DÍA ESPECÍFICO (En pantalla principal)
            col_filtro_dia, col_metricas = st.columns([1, 3])
            
            with col_filtro_dia:
                st.markdown("##### 📆 Filtrar día puntual")
                dia_filtro = st.date_input("Seleccionar Fecha", value=None, min_value=df_mes["FECHA_ENTREGA_DT"].min(), max_value=df_mes["FECHA_ENTREGA_DT"].max())
            
            # Aplicamos filtro de día si el usuario seleccionó uno
            if dia_filtro:
                df_final = df_mes[df_mes["FECHA_ENTREGA_DT"].dt.date == dia_filtro]
                titulo_tabla = f"Cronograma del día {dia_filtro.strftime('%d/%m/%Y')}"
            else:
                df_final = df_mes # Mostramos todo el mes si no elige día
                titulo_tabla = f"Cronograma Mensual - {mes_sel}"

            # --- VISUALIZACIÓN ---
            with col_metricas:
                c1, c2, c3 = st.columns(3)
                c1.metric("Entregas Programadas", len(df_final))
                c2.metric("Canales de Venta", len(df_final["CANAL DE VENTA"].unique()) if "CANAL DE VENTA" in df_final.columns else 0)
            
            st.divider()
            
            # --- TABLA CRONOGRAMA ---
            st.subheader(f"📋 {titulo_tabla}")
            
            # Definimos las columnas solicitadas
            cols_agenda = [
                "FECHA_ENTREGA_DT",
                "HS DE ENTREGA AL CLIENTE",
                "CLIENTE",
                "CANAL DE VENTA",
                "TELEFONO_CLEAN",
                "CORREO_CLEAN",
                "VENDEDOR"
            ]
            
            # Mapeo para nombres bonitos
            config_columnas = {
                "FECHA_ENTREGA_DT": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY"),
                "HS DE ENTREGA AL CLIENTE": "Hora Entrega",
                "TELEFONO_CLEAN": "Teléfono",
                "CORREO_CLEAN": "Correo",
                "CANAL DE VENTA": "Canal",
                "VENDEDOR": "Vendedor"
            }
            
            # Filtramos solo las columnas que realmente existan
            cols_reales = [c for c in cols_agenda if c in df_final.columns]
            
            st.dataframe(
                df_final[cols_reales].sort_values(["FECHA_ENTREGA_DT", "HS DE ENTREGA AL CLIENTE"]),
                use_container_width=True,
                hide_index=True,
                column_config=config_columnas
            )
            
        else:
            st.warning("No hay datos para el año seleccionado.")
    else:
        st.info("No se encontraron fechas de entrega configuradas.")

# ==========================================
# VISTA 2: CONTROL DE STOCK
# ==========================================
elif opcion == "📦 Control de Stock":
    st.title("📦 Tablero de Stock")
    st.sidebar.header("Filtros de Stock")
    
    df_stock = df.copy()

    if not df_stock.empty:
        # Filtros laterales
        if "AÑO_ARRIBO" in df_stock.columns:
            usar_filtro = st.sidebar.checkbox("Filtrar por Fecha Arribo")
            if usar_filtro:
                años_arr = sorted(df_stock["AÑO_ARRIBO"].dropna().unique().astype(int))
                if años_arr:
                    año_sel = st.sidebar.selectbox("Año Arribo", años_arr, index=len(años_arr)-1)
                    df_stock = df_stock[df_stock["AÑO_ARRIBO"] == año_sel]

        if "MARCA" in df_stock.columns:
            marcas = st.sidebar.multiselect("Marca", df_stock["MARCA"].unique(), default=df_stock["MARCA"].unique())
            df_stock = df_stock[df_stock["MARCA"].isin(marcas)]
            
        if "ESTADO" in df_stock.columns:
             estados = st.sidebar.multiselect("Estado", df_stock["ESTADO"].unique())
             if estados: df_stock = df_stock[df_stock["ESTADO"].isin(estados)]

        st.markdown(f"### Unidades listadas: **{len(df_stock)}**")
        
        # Columnas Stock
        cols_stock = ["VIN", "MARCA", "MODELO", "DESCRIPCION COLOR", "FECHA DE FABRICACION", "ANTIGUEDAD DE STOCK", "UBICACION", "DETALLE DEL ESTADO Y FECHA DE DISPONIBILIDAD DE UNIDAD"]
        cols_reales = [c for c in cols_stock if c in df_stock.columns]
        
        st.dataframe(df_stock[cols_reales], use_container_width=True, hide_index=True)
