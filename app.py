import streamlit as st
import pandas as pd

# Configuración básica de la página
st.set_page_config(page_title="Tablero de Entregas", layout="wide")

st.title("🚗 Programación de Entregas 0km")

# --- CONEXIÓN CON GOOGLE SHEETS ---
# Aquí usaremos un truco simple para leerlo si es público o si publicaste en la web como CSV.
# Reemplaza la URL de abajo con la tuya de "Publicar en la web > CSV"
sheet_url = "TU_URL_DE_PUBLICACION_AQUI_EN_FORMATO_CSV"

@st.cache_data(ttl=300) # Actualiza cada 5 minutos
def cargar_datos():
    try:
        # Leemos el archivo
        df = pd.read_csv(sheet_url)
        
        # Limpiamos los nombres de las columnas (quitamos espacios extra)
        df.columns = df.columns.str.strip()
        
        return df
    except Exception as e:
        st.error(f"Error al cargar datos: {e}")
        return pd.DataFrame()

df = cargar_datos()

if not df.empty:
    # --- FILTROS ---
    st.sidebar.header("Filtrar Entregas")
    
    # Asumiendo que tus columnas se llaman 'MARCA' y 'FECHA' (ajusta los nombres si son distintos)
    if "MARCA" in df.columns:
        marcas = df["MARCA"].unique()
        filtro_marca = st.sidebar.multiselect("Marca", options=marcas, default=marcas)
        df = df[df["MARCA"].isin(filtro_marca)]

    # --- TABLERO ---
    # Mostramos solo las columnas importantes. Ajusta los nombres exactos según tu Sheet.
    columnas_a_mostrar = ["FECHA", "HORA", "CLIENTE", "MARCA", "MODELO", "CHASIS"]
    
    # Verificamos que las columnas existan antes de mostrarlas para que no de error
    cols_existentes = [c for c in columnas_a_mostrar if c in df.columns]
    
    st.dataframe(df[cols_existentes], use_container_width=True, hide_index=True)

else:
    st.info("Esperando datos... Verifica la conexión con el Sheet.")
