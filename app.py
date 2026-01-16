import streamlit as st
import pandas as pd
import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Planificación de Entregas", layout="wide")

# --- CARGA DE DATOS ---
# Usamos el enlace de exportación que arreglamos antes
SHEET_ID = "15hIQ6WBxh1Ymhh9dxerKvEnoXJ_osH6a9BH-1TW9ZU8"
GID = "1504374770"
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

@st.cache_data(ttl=60) # Se actualiza cada minuto para estar al día
def load_data():
    try:
        df = pd.read_csv(URL)
        # Limpieza de nombres de columnas (quita espacios extra)
        df.columns = df.columns.str.strip().str.upper()
        
        # BUSCADOR INTELIGENTE DE COLUMNA FECHA
        # Busca alguna columna que se llame 'FECHA', 'FECHA ENTREGA', etc.
        col_fecha = next((c for c in df.columns if "FECHA" in c), None)
        
        if col_fecha:
            df["FECHA_OFICIAL"] = pd.to_datetime(df[col_fecha], dayfirst=True, errors='coerce')
            # Extraemos Año, Mes y Semana
            df["AÑO"] = df["FECHA_OFICIAL"].dt.year
            df["MES"] = df["FECHA_OFICIAL"].dt.month_name()
            df["N_MES"] = df["FECHA_OFICIAL"].dt.month # Para ordenar
            # Calculamos la semana del año
            df["SEMANA"] = df["FECHA_OFICIAL"].dt.isocalendar().week
        else:
            st.error("⚠️ No encontré una columna que diga 'FECHA' en tu Excel.")
            
        return df
    except Exception as e:
        st.error(f"Error cargando datos: {e}")
        return pd.DataFrame()

df = load_data()

# --- SI HAY DATOS, MOSTRAMOS EL TABLERO ---
if not df.empty and "FECHA_OFICIAL" in df.columns:

    # --- DISEÑO: TÍTULO A LA IZQUIERDA, FILTROS A LA DERECHA ---
    col_titulo, col_filtros = st.columns([3, 1]) # Proporción: Título ancho, filtros angostos
    
    with col_titulo:
        st.title("🗓️ Planificación de Entregas")
        st.markdown("Vista general de unidades programadas.")

    with col_filtros:
        st.write("### 🔍 Filtros")
        
        # Filtro de AÑO
        años_disponibles = sorted(df["AÑO"].dropna().unique().astype(int))
        año_sel = st.selectbox("Seleccionar Año", options=años_disponibles, index=len(años_disponibles)-1)
        
        # Filtrar datos por año primero
        df_año = df[df["AÑO"] == año_sel]
        
        # Filtro de MES (Solo mostramos meses que tienen datos ese año)
        meses_disponibles = df_año["N_MES"].unique()
        meses_nombres = df_año["MES"].unique()
        # Creamos un diccionario para el selector
        mapa_meses = dict(zip(meses_nombres, meses_disponibles))
        
        mes_sel_nombre = st.selectbox("Seleccionar Mes", options=sorted(mapa_meses.keys(), key=lambda x: mapa_meses[x]))
        
        # APLICAR FILTROS FINALES
        df_final = df_año[df_año["MES"] == mes_sel_nombre].copy()

    st.divider()

    # --- MÉTRICAS DE RESUMEN ---
    total_entregas = len(df_final)
    marcas_mes = df_final["MARCA"].unique() if "MARCA" in df_final.columns else []
    
    c1, c2, c3 = st.columns(3)
    c1.metric("🚗 Total Entregas Mes", total_entregas)
    c2.metric("📅 Semanas Activas", df_final["SEMANA"].nunique())
    c3.metric("🏷️ Marcas", len(marcas_mes))

    # --- ANÁLISIS POR SEMANA (LO QUE PEDISTE) ---
    st.subheader(f"📊 Entregas por Semana - {mes_sel_nombre} {año_sel}")
    
    # Agrupamos por semana
    conteo_semanal = df_final["SEMANA"].value_counts().sort_index().reset_index()
    conteo_semanal.columns = ["Semana del Año", "Cantidad de Autos"]
    
    # Mostramos gráfico y tabla lado a lado
    col_graf, col_tabla = st.columns([2, 1])
    
    with col_graf:
        # Gráfico de barras simple
        st.bar_chart(conteo_semanal.set_index("Semana del Año"))
        
    with col_tabla:
        st.write("**Detalle numérico:**")
        st.dataframe(conteo_semanal, hide_index=True, use_container_width=True)

    # --- TABLA DETALLADA DE PLANIFICACIÓN ---
    st.subheader("📝 Detalle de Planificación")
    
    # Seleccionamos columnas clave para mostrar limpio
    cols_mostrar = [c for c in ["FECHA", "HORA", "CLIENTE", "MARCA", "MODELO", "CHASIS", "COLOR"] if c in df_final.columns]
    
    st.dataframe(
        df_final[cols_mostrar].sort_values(by="FECHA_OFICIAL"),
        use_container_width=True,
        hide_index=True
    )

else:
    st.warning("No hay datos para mostrar. Revisa que tu Excel tenga una columna llamada 'FECHA'.")
