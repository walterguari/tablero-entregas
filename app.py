import streamlit as st
import pandas as pd
import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Portal Concesionaria", layout="wide", initial_sidebar_state="expanded")

# --- ESTILOS CSS PERSONALIZADOS (Para que los botones se vean mejor) ---
st.markdown("""
<style>
    div.stButton > button {
        width: 100%;
        border-radius: 10px;
        height: 3em;
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
        
        # --- PROCESAMIENTO FECHAS ---
        # 1. ENTREGA
        col_entrega = next((c for c in df.columns if "CONFIRMACI" in c and "ENTREGA" in c), None)
        if not col_entrega: col_entrega = next((c for c in df.columns if "FECHA" in c and "FACT" not in c), None)   
        if col_entrega:
            df["FECHA_ENTREGA_DT"] = pd.to_datetime(df[col_entrega], dayfirst=True, errors='coerce')
            df["AÑO_ENTREGA"] = df["FECHA_ENTREGA_DT"].dt.year
            df["MES_ENTREGA"] = df["FECHA_ENTREGA_DT"].dt.month_name()
            df["N_MES_ENTREGA"] = df["FECHA_ENTREGA_DT"].dt.month
            df["SEMANA_ENTREGA"] = df["FECHA_ENTREGA_DT"].dt.isocalendar().week
        
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

# --- GESTIÓN DE ESTADO (MEMORIA DE FILTRO) ---
if 'filtro_estado' not in st.session_state:
    st.session_state.filtro_estado = None

# --- MENÚ DE NAVEGACIÓN ---
st.sidebar.title("Navegación")
opcion = st.sidebar.radio("Ir a:", ["📅 Planificación Entregas", "📦 Control de Stock"])
st.sidebar.markdown("---")

# ==========================================
# VISTA 1: PLANIFICACIÓN DE ENTREGAS
# ==========================================
if opcion == "📅 Planificación Entregas":
    st.title("📅 Agenda de Entregas")
    st.sidebar.header("Filtros Agenda")

    if not df.empty and "FECHA_ENTREGA_DT" in df.columns:
        años = sorted(df["AÑO_ENTREGA"].dropna().unique().astype(int))
        año_sel = st.sidebar.selectbox("Año", options=años, index=len(años)-1)
        df_año = df[df["AÑO_ENTREGA"] == año_sel]
        
        meses_nombres = df_año["MES_ENTREGA"].unique()
        meses_nums = df_año["N_MES_ENTREGA"].unique()
        mapa_meses = dict(zip(meses_nombres, meses_nums))
        
        if mapa_meses:
            mes_sel = st.sidebar.selectbox("Mes", options=sorted(mapa_meses.keys(), key=lambda x: mapa_meses[x]))
            df_mes = df_año[df_año["MES_ENTREGA"] == mes_sel].copy()
            
            col_filtro, col_metricas = st.columns([1, 3])
            with col_filtro:
                st.markdown("##### 📆 Filtrar día")
                dia_filtro = st.date_input("Fecha", value=None, min_value=df_mes["FECHA_ENTREGA_DT"].min(), max_value=df_mes["FECHA_ENTREGA_DT"].max())
            
            if dia_filtro:
                df_final = df_mes[df_mes["FECHA_ENTREGA_DT"].dt.date == dia_filtro]
                titulo = f"Día {dia_filtro.strftime('%d/%m/%Y')}"
            else:
                df_final = df_mes
                titulo = f"Mes {mes_sel}"

            with col_metricas:
                c1, c2 = st.columns(2)
                c1.metric("Entregas", len(df_final))
                c2.metric("Canales", len(df_final["CANAL DE VENTA"].unique()) if "CANAL DE VENTA" in df_final.columns else 0)
            
            st.divider()
            st.subheader(f"📋 {titulo}")
            
            cols_agenda = ["FECHA_ENTREGA_DT", "HS DE ENTREGA AL CLIENTE", "CLIENTE", "MARCA", "MODELO", "CANAL DE VENTA", "TELEFONO_CLEAN", "CORREO_CLEAN", "VENDEDOR"]
            cols_reales = [c for c in cols_agenda if c in df_final.columns]
            
            st.dataframe(
                df_final[cols_reales].sort_values(["FECHA_ENTREGA_DT", "HS DE ENTREGA AL CLIENTE"]),
                use_container_width=True, hide_index=True,
                column_config={"FECHA_ENTREGA_DT": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY")}
            )
        else:
            st.warning("Sin datos este año.")

# ==========================================
# VISTA 2: CONTROL DE STOCK (BOTONES INTELIGENTES)
# ==========================================
elif opcion == "📦 Control de Stock":
    st.title("📦 Tablero de Stock")
    st.sidebar.header("Filtros") # Solo dejamos filtros globales
    
    df_stock = df.copy()

    if not df_stock.empty:
        # 1. FILTROS GLOBALES (Marca y Año)
        if "AÑO_ARRIBO" in df_stock.columns:
            if st.sidebar.checkbox("Filtrar Arribo"):
                años_arr = sorted(df_stock["AÑO_ARRIBO"].dropna().unique().astype(int))
                if años_arr:
                    año_sel = st.sidebar.selectbox("Año Arribo", años_arr, index=len(años_arr)-1)
                    df_stock = df_stock[df_stock["AÑO_ARRIBO"] == año_sel]

        if "MARCA" in df_stock.columns:
            marcas = st.sidebar.multiselect("Marca", df_stock["MARCA"].unique(), default=df_stock["MARCA"].unique())
            df_stock = df_stock[df_stock["MARCA"].isin(marcas)]

        # --- SECCIÓN DE BOTONES DE FILTRO (NUEVO) ---
        st.markdown("### 🔍 Filtrar por Estado")
        
        if "ESTADO" in df_stock.columns:
            # Calculamos totales actuales
            conteo = df_stock["ESTADO"].value_counts()
            
            # Diccionario de íconos según tus estados
            iconos = {
                "EN EXHIBICIÓN": "🏢",
                "EN EXHIBICION": "🏢",
                "SIN PRE ENTREGA": "🛠️",
                "CON PRE ENTREGA": "✨",
                "BLOQUEADO": "🔒",
                "ENTREGADO": "✅",
                "RESERVADO": "🔖",
                "STOCK": "📦",
                "PLAYA TALLER": "🔧"
            }

            # Creamos columnas para los botones (1 para "Todos" + 1 por cada estado)
            cols = st.columns(len(conteo) + 1)
            
            # Botón 1: VER TODOS
            with cols[0]:
                if st.button(f"📋 Todos ({len(df_stock)})", use_container_width=True):
                    st.session_state.filtro_estado = None # Limpia filtro

            # Botones Dinámicos: Uno por cada estado
            for i, (estado, cantidad) in enumerate(conteo.items()):
                # Buscamos el icono (convertimos a mayuscula para buscar mejor)
                icono = iconos.get(str(estado).upper(), "🚗") 
                label_boton = f"{icono} {estado} ({cantidad})"
                
                # Usamos modulo para distribuir si hay muchos estados
                col_destino = cols[i + 1] if (i + 1) < len(cols) else cols[-1]
                
                with col_destino:
                    if st.button(label_boton, use_container_width=True):
                        st.session_state.filtro_estado = estado

            # --- APLICAR FILTRO ---
            if st.session_state.filtro_estado:
                # Filtramos la tabla
                df_mostrar = df_stock[df_stock["ESTADO"] == st.session_state.filtro_estado]
                st.info(f"Mostrando: **{st.session_state.filtro_estado}** (Haz clic en 'Todos' para volver)")
            else:
                df_mostrar = df_stock # Muestra todo

        else:
            df_mostrar = df_stock

        st.markdown("---")

        # --- TABLA FINAL ---
        cols_stock = ["VIN", "MARCA", "MODELO", "DESCRIPCION COLOR", "FECHA DE FABRICACION", "ANTIGUEDAD DE STOCK", "ANTIGÜEDAD DE STOCK", "UBICACION", "DETALLE DEL ESTADO Y FECHA DE DISPONIBILIDAD DE UNIDAD", "ESTADO"]
        cols_reales = [c for c in cols_stock if c in df_mostrar.columns]
        
        st.dataframe(df_mostrar[cols_reales], use_container_width=True, hide_index=True)
