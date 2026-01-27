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
        background-color: #f0f4c3; /* Color suave para métricas admin */
        padding: 10px;
        border-radius: 5px;
        border: 1px solid #dce775;
    }
    .plano-img {
        border-radius: 10px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
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
        # 1. ENTREGA
        col_entrega = next((c for c in df.columns if "CONFIRMACI" in c and "ENTREGA" in c), None)
        if not col_entrega: col_entrega = next((c for c in df.columns if "FECHA" in c and "FACT" not in c), None)   
        if col_entrega:
            df["FECHA_ENTREGA_DT"] = pd.to_datetime(df[col_entrega], dayfirst=True, errors='coerce')
            df["AÑO_ENTREGA"] = df["FECHA_ENTREGA_DT"].dt.year
            df["MES_ENTREGA"] = df["FECHA_ENTREGA_DT"].dt.month_name()
            df["N_MES_ENTREGA"] = df["FECHA_ENTREGA_DT"].dt.month
        
        # 2. ARRIBO
        col_arribo = next((c for c in df.columns if "ARRIBO" in c), None)
        if col_arribo:
            df["FECHA_ARRIBO_DT"] = pd.to_datetime(df[col_arribo], dayfirst=True, errors='coerce')
            df["AÑO_ARRIBO"] = df["FECHA_ARRIBO_DT"].dt.year

        # 3. FACTURACION (Para Doc)
        col_fact = "FECHA DE FACTURACION DE LA UNIDAD"
        if col_fact in df.columns:
            df["FECHA_FACTURACION_DT"] = pd.to_datetime(df[col_fact], dayfirst=True, errors='coerce')

        # 4. DISPONIBILIDAD PAPELES (Para Doc)
        col_papeles = "FECHA DISPONIBILIDAD PAPELES"
        if col_papeles in df.columns:
            df["FECHA_PAPELES_DT"] = pd.to_datetime(df[col_papeles], dayfirst=True, errors='coerce')

        col_tel = next((c for c in df.columns if "TELEFONO" in c or "CELULAR" in c or "TEL" in c), None)
        if col_tel: df["TELEFONO_CLEAN"] = df[col_tel]
        col_mail = next((c for c in df.columns if "CORREO" in c or "MAIL" in c), None)
        if col_mail: df["CORREO_CLEAN"] = df[col_mail]

        return df
    except Exception as e:
        st.error(f"Error cargando datos: {e}")
        return pd.DataFrame()

df = load_data()

# --- MEMORIA DE ESTADO ---
if 'filtro_estado_stock' not in st.session_state: st.session_state.filtro_estado_stock = None
if 'filtro_estado_admin' not in st.session_state: st.session_state.filtro_estado_admin = None
if 'filtro_doc_rapido' not in st.session_state: st.session_state.filtro_doc_rapido = None # Nuevo filtro inteligente
if 'modo_vista_agenda' not in st.session_state: st.session_state.modo_vista_agenda = 'mes'
if 'filtro_mantenimiento' not in st.session_state: st.session_state.filtro_mantenimiento = 'todos'

# ==========================================
# BARRA LATERAL (LOGO)
# ==========================================
if os.path.exists("logo.png.png"):
    st.sidebar.image("logo.png.png", use_container_width=True)
elif os.path.exists("logo.png"):
    st.sidebar.image("logo.png", use_container_width=True)
elif os.path.exists("logo.jpg"):
    st.sidebar.image("logo.jpg", use_container_width=True)
else:
    st.sidebar.warning("Falta logo en GitHub")

st.sidebar.title("Navegación")
opcion = st.sidebar.radio("Ir a:", [
    "📅 Planificación Entregas", 
    "📦 Control de Stock", 
    "🛠️ Control Mantenimiento", 
    "📄 Estado Documentación", 
    "🗺️ Plano del Salón"
])
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
                    titulo = f"Cronograma Mensual - {mes_sel} ({len(df_final)})"
            else:
                st.warning("No hay datos mensuales.")

        if not df_final.empty:
            st.subheader(f"📋 {titulo}")
            cols_agenda = ["FECHA_ENTREGA_DT", "HS DE ENTREGA AL CLIENTE", "CLIENTE", "MARCA", "MODELO", "VIN", "CANAL DE VENTA", "TELEFONO_CLEAN", "CORREO_CLEAN", "VENDEDOR"]
            cols_reales = [c for c in cols_agenda if c in df_final.columns]
            st.dataframe(
                df_final[cols_reales].sort_values(["FECHA_ENTREGA_DT", "HS DE ENTREGA AL CLIENTE"]),
                use_container_width=True, hide_index=True,
                column_config={"FECHA_ENTREGA_DT": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY")}
            )
        else:
            if st.session_state.modo_vista_agenda != 'mes': st.info("No hay vehículos aquí.")

# ==========================================
# PESTAÑA 2: CONTROL DE STOCK
# ==========================================
elif opcion == "📦 Control de Stock":
    st.title("📦 Tablero de Stock")
    
    df_stock = df.copy()

    if not df_stock.empty:
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

        st.markdown("### 🔍 Estado del Inventario")
        
        if "ESTADO" in df_stock.columns:
            conteo = df_stock["ESTADO"].value_counts()
            iconos = {"EN EXHIBICIÓN": "🏢", "EN EXHIBICION": "🏢", "SIN PRE ENTREGA": "🛠️", 
                      "CON PRE ENTREGA": "✨", "BLOQUEADO": "🔒", "ENTREGADO": "✅", "RESERVADO": "🔖"}

            cols = st.columns(len(conteo) + 1)
            with cols[0]:
                if st.button(f"📋 Todos ({len(df_stock)})", use_container_width=True, key="btn_stock_todos"):
                    st.session_state.filtro_estado_stock = None

            for i, (estado, cantidad) in enumerate(conteo.items()):
                icono = iconos.get(str(estado).upper(), "🚗")
                col_destino = cols[i+1] if (i+1) < len(cols) else cols[-1]
                with col_destino:
                    if st.button(f"{icono} {estado} ({cantidad})", use_container_width=True, key=f"btn_stock_{i}"):
                        st.session_state.filtro_estado_stock = estado

            if st.session_state.filtro_estado_stock:
                df_mostrar = df_stock[df_stock["ESTADO"] == st.session_state.filtro_estado_stock]
                st.info(f"Filtro activo: **{st.session_state.filtro_estado_stock}**")
            else:
                df_mostrar = df_stock
        else:
            df_mostrar = df_stock

        st.markdown("---")
        cols_stock = ["VIN", "MARCA", "MODELO", "DESCRIPCION COLOR", "FECHA DE FABRICACION", "ANTIGUEDAD DE STOCK", "ANTIGÜEDAD DE STOCK", "UBICACION", "DETALLE DEL ESTADO Y FECHA DE DISPONIBILIDAD DE UNIDAD", "ESTADO"]
        cols_reales = [c for c in cols_stock if c in df_mostrar.columns]
        st.dataframe(df_mostrar[cols_reales], use_container_width=True, hide_index=True)

# ==========================================
# PESTAÑA 3: CONTROL MANTENIMIENTO
# ==========================================
elif opcion == "🛠️ Control Mantenimiento":
    st.title("🛠️ Planificación de Taller")
    
    if not df.empty and "FECHA_ARRIBO_DT" in df.columns:
        st.sidebar.header("Filtros")
        marcas = st.sidebar.multiselect("Filtrar Marca", df["MARCA"].unique())
        
        hoy = pd.Timestamp.now().normalize()
        inicio_semana = hoy - timedelta(days=hoy.weekday())
        fin_semana = inicio_semana + timedelta(days=6)

        df_mant = df.copy()
        
        if "ESTADO" in df_mant.columns:
            df_mant = df_mant[df_mant["ESTADO"].astype(str).str.strip().str.upper() != "ENTREGADO"]
        if marcas:
            df_mant = df_mant[df_mant["MARCA"].isin(marcas)]
            
        cols_control = {
            30: next((c for c in df.columns if "30" in c and "REALIZADO" in c), None),
            60: next((c for c in df.columns if "60" in c and "REALIZADO" in c), None),
            90: next((c for c in df.columns if "90" in c and "REALIZADO" in c), None),
            180: next((c for c in df.columns if "180" in c and "REALIZADO" in c), None),
            360: next((c for c in df.columns if "360" in c and "REALIZADO" in c), None),
            540: next((c for c in df.columns if "540" in c and "REALIZADO" in c), None),
        }

        lista_hoy = []
        lista_semana = []
        lista_atrasados = []
        
        for index, row in df_mant.iterrows():
            if pd.isnull(row["FECHA_ARRIBO_DT"]): continue
            fecha_arribo = row["FECHA_ARRIBO_DT"]
            
            motivos_hoy = []
            motivos_semana = []
            motivos_atrasados = []
            
            for intervalo, columna in cols_control.items():
                if not columna: continue
                fecha_vencimiento = fecha_arribo + timedelta(days=intervalo)
                estado_celda = str(row[columna]).strip().upper()
                
                if estado_celda in ["OK", "N/A", "SI"]: continue
                
                if fecha_vencimiento == hoy:
                    motivos_hoy.append(f"Control {intervalo} días")
                if inicio_semana <= fecha_vencimiento <= fin_semana:
                    motivos_semana.append(f"Control {intervalo} días ({fecha_vencimiento.strftime('%d/%m')})")
                if hoy >= fecha_vencimiento:
                    motivos_atrasados.append(f"Falta {intervalo} días (Venció: {fecha_vencimiento.strftime('%d/%m')})")

            if motivos_hoy:
                r = row.copy()
                r["TAREA"] = ", ".join(motivos_hoy)
                lista_hoy.append(r)
            if motivos_semana:
                r = row.copy()
                r["TAREA"] = ", ".join(motivos_semana)
                lista_semana.append(r)
            if motivos_atrasados:
                r = row.copy()
                r["TAREA"] = motivos_atrasados[-1]
                lista_atrasados.append(r)

        c1, c2, c3 = st.columns(3)
        if c1.button(f"📅 Vence HOY ({len(lista_hoy)})", use_container_width=True):
            st.session_state.filtro_mantenimiento = 'hoy'
        if c2.button(f"📆 Vence Esta Semana ({len(lista_semana)})", use_container_width=True):
            st.session_state.filtro_mantenimiento = 'semana'
        if c3.button(f"🚨 Todo Pendiente ({len(lista_atrasados)})", use_container_width=True):
            st.session_state.filtro_mantenimiento = 'todos'

        st.divider()

        df_final = pd.DataFrame()
        titulo = ""
        mensaje = ""
        
        if st.session_state.filtro_mantenimiento == 'hoy':
            df_final = pd.DataFrame(lista_hoy)
            titulo = "🚗 Vehículos que vencen HOY"
            mensaje = f"Lista para {hoy.strftime('%d/%m/%Y')}."
        elif st.session_state.filtro_mantenimiento == 'semana':
            df_final = pd.DataFrame(lista_semana)
            titulo = "🗓️ Planificación Semanal"
            mensaje = f"Del {inicio_semana.strftime('%d/%m')} al {fin_semana.strftime('%d/%m')}."
        else:
            df_final = pd.DataFrame(lista_atrasados)
            titulo = "⚠️ Listado de Atrasados / Pendientes"
            mensaje = "Vehículos que ya cumplieron el plazo y NO tienen 'OK'."

        if not df_final.empty:
            st.subheader(titulo)
            st.info(mensaje)
            cols_base = ["VIN", "MARCA", "MODELO", "FECHA_ARRIBO_DT", "TAREA", "UBICACION"]
            cols_reales = [c for c in cols_base if c in df_final.columns]
            st.dataframe(df_final[cols_reales], use_container_width=True, hide_index=True, column_config={"FECHA_ARRIBO_DT": st.column_config.DateColumn("Fecha Arribo", format="DD/MM/YYYY")})
        else:
            if st.session_state.filtro_mantenimiento != 'todos': st.success(f"✅ ¡Nada pendiente en: {titulo}!")
            else: st.success("✅ ¡Felicitaciones! No hay mantenimientos atrasados.")

    else:
        st.warning("No se encontraron datos de Fecha de Arribo.")

# ==========================================
# PESTAÑA 4: ESTADO DOCUMENTACIÓN
# ==========================================
elif opcion == "📄 Estado Documentación":
    st.title("📄 Estado de Documentación")
    
    df_doc = df.copy()
    
    if not df_doc.empty:
        # Filtros laterales
        st.sidebar.header("Filtros Documentación")
        if "MARCA" in df_doc.columns:
            marca_filter = st.sidebar.multiselect("Filtrar Marca", df_doc["MARCA"].unique())
            if marca_filter:
                df_doc = df_doc[df_doc["MARCA"].isin(marca_filter)]

        # Buscador VIN / Cliente
        search = st.text_input("🔎 Buscar por VIN o CLIENTE", placeholder="Escribe para buscar...").upper()
        if search:
            mask = df_doc.apply(lambda row: row.astype(str).str.contains(search, case=False).any(), axis=1)
            df_doc = df_doc[mask]
        
        st.markdown("---")

        # --- FILTROS RÁPIDOS INTELIGENTES (NUEVO) ---
        st.subheader("⚡ Acciones Rápidas")
        
        # Lógica de conteo para filtros rápidos
        count_papeles_listos = 0
        count_pendiente_gestor = 0
        count_facturado_mes = 0
        
        hoy = pd.Timestamp.now()
        
        # Pre-cálculos para los contadores
        if "FECHA_PAPELES_DT" in df_doc.columns:
            count_papeles_listos = len(df_doc[df_doc["FECHA_PAPELES_DT"].notnull()])
            
        if "FECHA_FACTURACION_DT" in df_doc.columns and "FECHA_PAPELES_DT" in df_doc.columns:
            # Facturado pero SIN papeles
            count_pendiente_gestor = len(df_doc[
                (df_doc["FECHA_FACTURACION_DT"].notnull()) & 
                (df_doc["FECHA_PAPELES_DT"].isnull())
            ])
            
        if "FECHA_FACTURACION_DT" in df_doc.columns:
            # Facturado en el mes actual
            count_facturado_mes = len(df_doc[
                (df_doc["FECHA_FACTURACION_DT"].dt.month == hoy.month) &
                (df_doc["FECHA_FACTURACION_DT"].dt.year == hoy.year)
            ])

        # Botones de Filtros Rápidos
        col_rap1, col_rap2, col_rap3 = st.columns(3)
        
        if col_rap1.button(f"🟢 Papeles Listos ({count_papeles_listos})", use_container_width=True):
            st.session_state.filtro_doc_rapido = 'papeles_listos'
            st.session_state.filtro_estado_admin = None # Reset otro filtro
            
        if col_rap2.button(f"🏃 Pendiente Gestoría ({count_pendiente_gestor})", use_container_width=True):
            st.session_state.filtro_doc_rapido = 'pendiente_gestor'
            st.session_state.filtro_estado_admin = None
            
        if col_rap3.button(f"📅 Facturado Este Mes ({count_facturado_mes})", use_container_width=True):
            st.session_state.filtro_doc_rapido = 'facturado_mes'
            st.session_state.filtro_estado_admin = None

        st.divider()

        # --- BOTONES DE ESTADO ADMINISTRATIVO ---
        st.subheader("📂 Filtrar por Estado Administrativo")
        
        if "ESTADO ADMINISTRATIVO" in df_doc.columns:
            conteo_adm = df_doc["ESTADO ADMINISTRATIVO"].value_counts()
            
            iconos_adm = {
                "PENDIENTE": "⏳", "A FACTURAR": "💲", "FACTURADO": "🧾",
                "PATENTAMIENTO": "📝", "PRENDA": "🔒", "FINALIZADO": "✅",
                "OK": "✅", "EN TRAMITE": "🏃"
            }

            cols = st.columns(len(conteo_adm) + 1)
            
            with cols[0]:
                if st.button(f"📋 Todos ({len(df_doc)})", use_container_width=True, key="btn_doc_todos"):
                    st.session_state.filtro_estado_admin = None
                    st.session_state.filtro_doc_rapido = None # Reset rápido
            
            for i, (estado, cantidad) in enumerate(conteo_adm.items()):
                icono = iconos_adm.get(str(estado).upper(), "📂")
                col_destino = cols[i+1] if (i+1) < len(cols) else cols[-1]
                
                with col_destino:
                    if st.button(f"{icono} {estado} ({cantidad})", use_container_width=True, key=f"btn_doc_{i}"):
                        st.session_state.filtro_estado_admin = estado
                        st.session_state.filtro_doc_rapido = None # Reset rápido

        # --- APLICACIÓN DE FILTROS ---
        
        # 1. Filtro Rápido
        if st.session_state.filtro_doc_rapido == 'papeles_listos':
            if "FECHA_PAPELES_DT" in df_doc.columns:
                df_doc = df_doc[df_doc["FECHA_PAPELES_DT"].notnull()]
                st.success("Mostrando vehículos con **Papeles Disponibles**.")
                
        elif st.session_state.filtro_doc_rapido == 'pendiente_gestor':
            if "FECHA_FACTURACION_DT" in df_doc.columns and "FECHA_PAPELES_DT" in df_doc.columns:
                df_doc = df_doc[(df_doc["FECHA_FACTURACION_DT"].notnull()) & (df_doc["FECHA_PAPELES_DT"].isnull())]
                st.warning("Mostrando vehículos **Facturados pero sin Papeles**.")
                
        elif st.session_state.filtro_doc_rapido == 'facturado_mes':
            if "FECHA_FACTURACION_DT" in df_doc.columns:
                df_doc = df_doc[
                    (df_doc["FECHA_FACTURACION_DT"].dt.month == hoy.month) &
                    (df_doc["FECHA_FACTURACION_DT"].dt.year == hoy.year)
                ]
                st.info(f"Mostrando facturación de **{hoy.strftime('%B')}**.")

        # 2. Filtro Estado Administrativo (si no hay filtro rápido activo o se sobreescribió)
        elif st.session_state.filtro_estado_admin:
            df_doc = df_doc[df_doc["ESTADO ADMINISTRATIVO"] == st.session_state.filtro_estado_admin]
            st.info(f"Filtro activo: **{st.session_state.filtro_estado_admin}**")

        st.markdown("<br>", unsafe_allow_html=True) # Espacio

        # 4. Tabla de Resultados
        cols_solicitadas = [
            "FECHA DE FACTURACION DE LA UNIDAD", "VIN", "CLIENTE", "MARCA", 
            "ESTADO ADMINISTRATIVO", "MODELO", "UBICACION", "ESTADO", 
            "DETALLE DEL ESTADO Y FECHA DE DISPONIBILIDAD DE UNIDAD", 
            "ACCESORIOS", "FECHA QUE EL GESTOR RETIRA DOC", 
            "FECHA PREVISTA DE ENTREGA", "FECHA DISPONIBILIDAD PAPELES"
        ]
        
        cols_reales = [c for c in cols_solicitadas if c in df_doc.columns]
        
        if not df_doc.empty:
            st.dataframe(
                df_doc[cols_reales],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "FECHA DE FACTURACION DE LA UNIDAD": st.column_config.DateColumn("F. Facturación", format="DD/MM/YYYY"),
                    "FECHA QUE EL GESTOR RETIRA DOC": st.column_config.DateColumn("F. Retiro Gestor", format="DD/MM/YYYY"),
                    "FECHA PREVISTA DE ENTREGA": st.column_config.DateColumn("F. Prevista Entrega", format="DD/MM/YYYY"),
                    "FECHA DISPONIBILIDAD PAPELES": st.column_config.DateColumn("F. Disp. Papeles", format="DD/MM/YYYY"),
                }
            )
        else:
            st.warning("No se encontraron resultados.")

# ==========================================
# PESTAÑA 5: PLANO DEL SALÓN (VISTA SUPERIOR)
# ==========================================
elif opcion == "🗺️ Plano del Salón":
    st.title("🗺️ Distribución del Salón")
    st.markdown("Vista superior esquemática de las áreas de Peugeot y Citroën.")
    
    tab_peugeot, tab_citroen = st.tabs(["🦁 Peugeot", "🔴 Citroën"])
    
    with tab_peugeot:
        if os.path.exists("mapa_peugeot.jpg"):
            st.image("mapa_peugeot.jpg", use_container_width=True, caption="Salón Peugeot")
        elif os.path.exists("Peugeot (2).jpeg"):
             st.image("Peugeot (2).jpeg", use_container_width=True, caption="Salón Peugeot")
        elif os.path.exists("plano_peugeot.png"):
             st.image("plano_peugeot.png", use_container_width=True, caption="Salón Peugeot")
        else:
            st.warning("⚠️ No se encuentra la imagen del plano Peugeot. Sube 'mapa_peugeot.jpg' a GitHub.")
            
    with tab_citroen:
        if os.path.exists("mapa_citroen.jpg"):
            st.image("mapa_citroen.jpg", use_container_width=True, caption="Salón Citroën")
        elif os.path.exists("Citroen.jpeg"):
             st.image("Citroen.jpeg", use_container_width=True, caption="Salón Citroën")
        elif os.path.exists("plano_citroen.png"):
             st.image("plano_citroen.png", use_container_width=True, caption="Salón Citroën")
        else:
            st.warning("⚠️ No se encuentra la imagen del plano Citroën. Sube 'mapa_citroen.jpg' a GitHub.")
