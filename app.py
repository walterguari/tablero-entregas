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
        
        # ELIMINAR COLUMNAS DUPLICADAS (Evita el ValueError de PyArrow)
        df = df.loc[:, ~df.columns.duplicated()]
        
        if df.empty:
            return df
            
        # PROCESAMIENTO FECHAS
        col_entrega = None
        posibles_columnas_entrega = [
            lambda c: "CONFIRMACI" in c and "ENTREGA" in c,
            lambda c: "FECHA" in c and "ENTREGA" in c,
            lambda c: "FECHA" in c and "TURNO" in c,
            lambda c: "FECHA" in c and "FACT" not in c and "ARRIBO" not in c and "PAPELES" not in c
        ]
        
        for criterio in posibles_columnas_entrega:
            col_entrega = next((c for c in df.columns if criterio(c)), None)
            if col_entrega:
                break
                
        if col_entrega:
            df["FECHA_ENTREGA_DT"] = pd.to_datetime(df[col_entrega], dayfirst=True, errors='coerce')
            df["AÑO_ENTREGA"] = df["FECHA_ENTREGA_DT"].dt.year
            df["MES_ENTREGA"] = df["FECHA_ENTREGA_DT"].dt.month_name()
            df["N_MES_ENTREGA"] = df["FECHA_ENTREGA_DT"].dt.month
        else:
            df["FECHA_ENTREGA_DT"] = pd.NaT
            df["AÑO_ENTREGA"] = pd.NA
            df["MES_ENTREGA"] = "Sin Fecha"
            df["N_MES_ENTREGA"] = 0
        
        col_arribo = next((c for c in df.columns if "ARRIBO" in c), None)
        if col_arribo:
            df["FECHA_ARRIBO_DT"] = pd.to_datetime(df[col_arribo], dayfirst=True, errors='coerce')
            df["AÑO_ARRIBO"] = df["FECHA_ARRIBO_DT"].dt.year

        col_fact = "FECHA DE FACTURACION DE LA UNIDAD"
        if col_fact in df.columns:
            df["FECHA_FACTURACION_DT"] = pd.to_datetime(df[col_fact], dayfirst=True, errors='coerce')

        col_papeles = "FECHA DISPONIBILIDAD PAPELES"
        if col_papeles in df.columns:
            df["FECHA_PAPELES_DT"] = pd.to_datetime(df[col_papeles], dayfirst=True, errors='coerce')

        # Fecha de Pedido de Preparación
        col_prep = next((c for c in df.columns if "PEDIDO" in c and "PREPARACI" in c), None)
        if col_prep:
            df["FECHA_PREPARACION_DT"] = pd.to_datetime(df[col_prep], dayfirst=True, errors='coerce')
        else:
            df["FECHA_PREPARACION_DT"] = pd.NaT

        # NUEVO: Buscar columna nativa de Fecha de Pedido de Unidad para las diferencias analíticas pedidas
        col_pedido_un = next((c for c in df.columns if "FECHA" in c and ("PEDIDO" in c or "COMPRA" in c) and "PREPARACI" not in c), None)
        if col_pedido_un:
            df["FECHA_PEDIDO_UNIDAD_DT"] = pd.to_datetime(df[col_pedido_un], dayfirst=True, errors='coerce')
        else:
            # Fallback seguro si no existe usa la de facturación o preparación
            df["FECHA_PEDIDO_UNIDAD_DT"] = pd.to_datetime(df[col_fact] if col_fact in df.columns else df[col_prep], dayfirst=True, errors='coerce')

        col_tel = next((c for c in df.columns if "TELEFONO" in c or "CELULAR" in c or "TEL" in c), None)
        if col_tel: 
            df["TELEFONO_CLEAN"] = df[col_tel]
            
        col_mail = next((c for c in df.columns if "CORREO" in c or "MAIL" in c), None)
        if col_mail: 
            df["CORREO_CLEAN"] = df[col_mail]

        return df
    except Exception as e:
        st.error(f"Error cargando datos: {e}")
        return pd.DataFrame()

df_0km = load_data(URL_0KM, fila_header=0)
df_usados = load_data(URL_USADOS, fila_header=1)

# --- MEMORIA DE ESTADO ---
if 'filtro_estado_stock' not in st.session_state: st.session_state.filtro_estado_stock = None
if 'filtro_estado_admin' not in st.session_state: st.session_state.filtro_estado_admin = None
if 'modo_vista_0km' not in st.session_state: st.session_state.modo_vista_0km = 'mes'
if 'modo_vista_usados' not in st.session_state: st.session_state.modo_vista_usados = 'mes'
if 'filtro_mantenimiento' not in st.session_state: st.session_state.filtro_mantenimiento = 'todos'
# Memoria para los botones de Con Fecha / SIN Fecha de la pestaña Documentación
if 'filtro_doc_segmento' not in st.session_state: st.session_state.filtro_doc_segmento = '🚀 Con Fecha de Entrega'
# Nueva memoria para los botones interactivos exclusivos de la sección gráfica de Tendencias
if 'filtro_grafico_segmento' not in st.session_state: st.session_state.filtro_grafico_segmento = '🚀 Vista: Con Fecha de Entrega'

# ==========================================
# BARRA LATERAL (LOGO Y NAVEGACIÓN)
# ==========================================
logo_paths = ["logo.png", "logo.png.png", "logo.jpg"]
for path in logo_paths:
    if os.path.exists(path):
        st.sidebar.image(path, use_container_width=True)
        break

st.sidebar.title("Navegación")
opcion = st.sidebar.radio("Ir a:", [
    "📅 Planificación Entregas 0KM", 
    "🚗 Agenda de Usados",
    "📦 Control de Stock y Documentación",
    "🛠️ Control Mantenimiento", 
    "🗺️ Plano del Salón"
])
st.sidebar.markdown("---")

# FUNCIÓN AGENDA EN BI-VISTAS (COMPARTIDA)
def render_agenda(df_target, session_key_vista, titulo_seccion, es_usado=False):
    st.title(titulo_seccion)
    if not df_target.empty and "FECHA_ENTREGA_DT" in df_target.columns:
        años = sorted(df_target["AÑO_ENTREGA"].dropna().unique().astype(int))
        if años:
            año_sel = st.sidebar.selectbox("Seleccionar Año", options=años, index=len(años)-1, key=f"sel_año_{session_key_vista}")
            df_año = df_target[df_target["AÑO_ENTREGA"] == año_sel]
            
            hoy = datetime.date.today()
            entregados = df_año[df_año["FECHA_ENTREGA_DT"].dt.date < hoy]
            programados = df_año[df_año["FECHA_ENTREGA_DT"].dt.date >= hoy]
            
            c1, c2, c3 = st.columns(3)
            type_ent = "primary" if st.session_state[session_key_vista] == 'entregados' else "secondary"
            type_prog = "primary" if st.session_state[session_key_vista] == 'programados' else "secondary"
            type_mes = "primary" if st.session_state[session_key_vista] == 'mes' else "secondary"

            if c1.button(f"✅ Ya Entregados ({len(entregados)})", use_container_width=True, type=type_ent, key=f"btn_ent_{session_key_vista}"):
                st.session_state[session_key_vista] = 'entregados'
            if c2.button(f"🚀 Programados ({len(programados)})", use_container_width=True, type=type_prog, key=f"btn_prog_{session_key_vista}"):
                st.session_state[session_key_vista] = 'programados'
            if c3.button("📅 Filtrar por Mes / Día", use_container_width=True, type=type_mes, key=f"btn_mes_{session_key_vista}"):
                st.session_state[session_key_vista] = 'mes'
            st.divider()

            df_final = pd.DataFrame()
            titulo = ""
            
            if st.session_state[session_key_vista] == 'entregados':
                st.info(f"Historial de entregas {año_sel}.")
                df_final = entregados
                titulo = f"Historial Entregado - {año_sel}"
            elif st.session_state[session_key_vista] == 'programados':
                st.info(f"Próximas entregas a partir de hoy.")
                df_final = programados
                titulo = f"Agenda Pendiente - {año_sel}"
            else:
                st.sidebar.header("Filtrar Mes")
                meses_nombres = df_año["MES_ENTREGA"].unique()
                meses_nums = df_año["N_MES_ENTREGA"].unique()
                mapa_meses = dict(zip(meses_nombres, meses_nums))
                if mapa_meses:
                    mes_sel = st.sidebar.selectbox("Mes", options=sorted(mapa_meses.keys(), key=lambda x: mapa_meses[x]), key=f"sel_mes_{session_key_vista}")
                    df_mes = df_año[df_año["MES_ENTREGA"] == mes_sel].copy()
                    col_filtro, col_vacio = st.columns([1, 3])
                    with col_filtro:
                        dia_filtro = st.date_input("📅 Filtrar día", value=None, min_value=df_mes["FECHA_ENTREGA_DT"].min(), max_value=df_mes["FECHA_ENTREGA_DT"].max(), key=f"date_{session_key_vista}")
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
                config_columnas = {}
                
                if es_usado:
                    cols_agenda = ["FECHA_ENTREGA_DT", "HORA", "CLIENTE", "ESTADO DEL TRAMITE", "TIPO DE UNIDAD", "ESTADO DE UNIDAD", "MARCA", "MODELO", "DOMINIO", "TELEFONO_CLEAN", "VENDEDOR (BOLETO)"]
                    config_columnas = {
                        "FECHA_ENTREGA_DT": st.column_config.DateColumn("Fecha Confirmada de Entrega", format="DD/MM/YYYY"),
                        "HORA": st.column_config.TextColumn("Hora"),
                        "CLIENTE": st.column_config.TextColumn("Cliente"),
                        "ESTADO DEL TRAMITE": st.column_config.TextColumn("Estado del Trámite"),
                        "TIPO DE UNIDAD": st.column_config.TextColumn("Tipo de Unidad"),
                        "ESTADO DE UNIDAD": st.column_config.TextColumn("Estado de Unidad"),
                        "MARCA": st.column_config.TextColumn("Marca"),
                        "MODELO": st.column_config.TextColumn("Modelo"),
                        "DOMINIO": st.column_config.TextColumn("Dominio"),
                        "TELEFONO_CLEAN": st.column_config.TextColumn("Teléfono"),
                        "VENDEDOR (BOLETO)": st.column_config.TextColumn("Vendedor (Boleto)")
                    }
                else:
                    col_admin = next((c for c in df_target.columns if "ESTADO" in c and "ADMIN" in c), None)
                    cols_agenda = ["FECHA_ENTREGA_DT", "HS DE ENTREGA AL CLIENTE", "CLIENTE"]
                    if col_admin: cols_agenda.append(col_admin)
                    cols_agenda.extend(["MARCA", "MODELO", "VIN", "CANAL DE VENTA", "TELEFONO_CLEAN", "VENDEDOR"])
                    config_columnas = {
                        "FECHA_ENTREGA_DT": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY"),
                        "HS DE ENTREGA AL CLIENTE": st.column_config.TextColumn("Hora"),
                        col_admin: st.column_config.TextColumn("Estado Admin") if col_admin else None
                    }
                
                cols_reales = [c for c in cols_agenda if c in df_final.columns]
                df_render = df_final[cols_reales].loc[:, ~df_final[cols_reales].columns.duplicated()]
                st.dataframe(df_render.sort_values(cols_reales[0] if cols_reales else "CLIENTE"), use_container_width=True, hide_index=True, column_config=config_columnas)
            else:
                if st.session_state[session_key_vista] != 'mes': st.info("No hay vehículos aquí.")
            
            # --- SECCIÓN GRÁFICO ---
            st.markdown("---")
            tipo_unidades = "0KM" if not es_usado else "Usados"
            st.subheader(f"📊 Volumen de Entregas por Mes {tipo_unidades}")
            opciones_grafico = ["Todos los años"] + [str(a) for a in años]
            año_grafico_sel = st.selectbox("Seleccionar período para el gráfico:", options=opciones_grafico, index=opciones_grafico.index(str(año_sel)), key=f"grafico_filtro_{session_key_vista}")

            if año_grafico_sel == "Todos los años":
                df_grafico = df_target.dropna(subset=["N_MES_ENTREGA"]).copy()
                subtitulo_grafico = "(Histórico Consolidado)"
            else:
                df_grafico = df_target[(df_target["AÑO_ENTREGA"] == int(año_grafico_sel))].dropna(subset=["N_MES_ENTREGA"]).copy()
                subtitulo_grafico = f"({año_grafico_sel})"

            st.caption(f"Visualizando: {subtitulo_grafico}")
            if not df_grafico.empty:
                orden_meses = ["01-Enero", "02-Febrero", "03-Marzo", "04-Abril", "05-Mayo", "06-Junio", "07-Julio", "08-Agosto", "09-Septiembre", "10-Octubre", "11-Noviembre", "12-Diciembre"]
                meses_es = {1: "01-Enero", 2: "02-Febrero", 3: "03-Marzo", 4: "04-Abril", 5: "05-Mayo", 6: "06-Junio", 7: "07-Julio", 8: "08-Agosto", 9: "09-Septiembre", 10: "10-Octubre", 11: "11-Noviembre", 12: "12-Diciembre"}
                df_grouped = df_grafico.groupby("N_MES_ENTREGA").size().reset_index(name="Cantidad de Entregas")
                df_grouped["Mes"] = df_grouped["N_MES_ENTREGA"].map(meses_es)
                df_grouped = df_grouped.set_index("Mes").reindex(orden_meses).fillna(0)
                df_grouped = df_grouped[df_grouped["Cantidad de Entregas"] > 0]
                st.bar_chart(df_grouped["Cantidad de Entregas"], use_container_width=True)
            else:
                st.info("No hay datos disponibles para el gráfico.")
        else:
            st.sidebar.warning("No se encontraron años.")
    else:
        st.error("Set de datos vacío o con errores.")

# ==========================================
# MODELO PRINCIPAL: UNIFICADO STOCK & DOCS
# ==========================================
if opcion == "📅 Planificación Entregas 0KM":
    render_agenda(df_0km, 'modo_vista_0km', "📅 Agenda de Entregas 0KM", es_usado=False)

elif opcion == "🚗 Agenda de Usados":
    render_agenda(df_usados, 'modo_vista_usados', "🚗 Agenda de Entregas Usados", es_usado=True)

elif opcion == "📦 Control de Stock y Documentación":
    st.title("📦 Panel Estratégico: Stock & Documentación 0KM")
    df_raw = df_0km.copy()
    
    if not df_raw.empty:
        # --- FILTROS SIDEBAR ---
        st.sidebar.header("Filtros Generals")
        if "MARCA" in df_raw.columns:
            marcas_sel = st.sidebar.multiselect("Filtrar Marca", df_raw["MARCA"].unique(), default=df_raw["MARCA"].unique())
            df_raw = df_raw[df_raw["MARCA"].isin(marcas_sel)]
            
        search = st.text_input("🔎 BUSCADOR DIRECTO (VIN, CLIENTE o MODELO)", placeholder="Escribe para buscar...").upper()
        if search:
            mask = df_raw.apply(lambda row: row.astype(str).str.contains(search, case=False).any(), axis=1)
            df_raw = df_raw[mask]

        col_target_admin = None
        if "ESTADO DE ADMINISTRATIVO" in df_raw.columns: col_target_admin = "ESTADO DE ADMINISTRATIVO"
        elif "ESTADO ADMINISTRATIVO" in df_raw.columns: col_target_admin = "ESTADO ADMINISTRATIVO"
        elif "DETALLE DEL ESTADO Y FECHA DE DISPONIBILIDAD DE UNIDAD" in df_raw.columns: col_target_admin = "DETALLE DEL ESTADO Y FECHA DE DISPONIBILIDAD DE UNIDAD"

        # Estandarización estricta de la columna ESTADO
        df_raw["ESTADO_CLEAN"] = df_raw["ESTADO"].astype(str).str.strip().str.upper()
        df_base_limpia = df_raw[df_raw["ESTADO"].notna() & (df_raw["ESTADO_CLEAN"] != "NAN") & (df_raw["ESTADO_CLEAN"] != "")]

        # Separación Base Métricas
        df_entregados_hist = df_base_limpia[df_base_limpia["ESTADO_CLEAN"] == "ENTREGADO"]
        df_stock_real = df_base_limpia[df_base_limpia["ESTADO_CLEAN"] != "ENTREGADO"]
        df_con_fecha = df_stock_real[df_stock_real["FECHA_ENTREGA_DT"].notna()]
        df_sin_fecha_base = df_stock_real[df_stock_real["FECHA_ENTREGA_DT"].isna()]

        # --- REGLA OPERATIVA DE FILTRADO Y EXCLUSIONES PARA LA TARJETA 3 (🚨 SIN FECHA) ---
        col_cliente = "CLIENTE" if "CLIENTE" in df_sin_fecha_base.columns else None
        if col_cliente:
            df_sin_fecha_base["CLIENTE_UPPER"] = df_sin_fecha_base[col_cliente].astype(str).str.strip().str.upper()
            mask_tiene_cliente = (
                df_sin_fecha_base[col_cliente].notna() & 
                (df_sin_fecha_base["CLIENTE_UPPER"] != "") & 
                (df_sin_fecha_base["CLIENTE_UPPER"] != "NAN") & 
                (df_sin_fecha_base["CLIENTE_UPPER"] != "UNIDAD SIN CLIENTE ASIGNADO")
            )
            mask_tiene_pedido = df_sin_fecha_base["FECHA_PREPARACION_DT"].notna()
            
            mask_base_sin_fecha = mask_tiene_cliente | mask_tiene_pedido
            
            if col_target_admin:
                df_sin_fecha_base["ADMIN_UPPER"] = df_sin_fecha_base[col_target_admin].astype(str).str.strip().str.upper()
                mask_excluir_estados = (
                    df_sin_fecha_base["ADMIN_UPPER"].str.contains("LEGALES", na=False) |
                    df_sin_fecha_base["ADMIN_UPPER"].str.contains("SIN CLIENTE", na=False) |
                    df_sin_fecha_base["ADMIN_UPPER"].str.contains("REVENTA", na=False)
                )
                df_sin_fecha = df_sin_fecha_base[mask_base_sin_fecha & ~mask_excluir_estados]
            else:
                df_sin_fecha = df_sin_fecha_base[mask_base_sin_fecha]
        else:
            if col_target_admin:
                df_sin_fecha_base["ADMIN_UPPER"] = df_sin_fecha_base[col_target_admin].astype(str).str.strip().str.upper()
                mask_excluir_estados = (
                    df_sin_fecha_base["ADMIN_UPPER"].str.contains("LEGALES", na=False) |
                    df_sin_fecha_base["ADMIN_UPPER"].str.contains("SIN CLIENTE", na=False) |
                    df_sin_fecha_base["ADMIN_UPPER"].str.contains("REVENTA", na=False)
                )
                df_sin_fecha = df_sin_fecha_base[df_sin_fecha_base["FECHA_PREPARACION_DT"].notna() & ~mask_excluir_estados]
            else:
                df_sin_fecha = df_sin_fecha_base[df_sin_fecha_base["FECHA_PREPARACION_DT"].notna()]

        # --- BLOQUE 1: RENDERING KPI CARDS ---
        st.markdown("### 📈 Resumen del Embudo Operativo")
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("🏢 Total Stock Real", len(df_stock_real), help="Unidades vivas cargadas en stock. Excluye vacíos y entregados.")
        kpi2.metric("🚀 Con Fecha de Entrega", len(df_con_fecha), help="Vehículos en stock que poseen fecha confirmada de entrega.")
        kpi3.metric("🚨 SIN Fecha de Entrega", len(df_sin_fecha), help="Clientes reales o con pedido en espera, sin turno asignado. Excluye Legales, Autopatentados sin cliente y Reventas.")
        kpi4.metric("✅ Entregados Históricos", len(df_entregados_hist), help="Total acumulado histórico de vehículos entregados.")
        
        st.markdown("---")

        # =========================================================
        # 📂 FUNCIÓN ENCAPSULADA DE RENDERIZACIÓN PARA LA TABLA MAESTRA CRÍTICA (PESTAÑA FÍSICA)
        # =========================================================
        def renderizar_tabla_tiempos_operativa(df_segmento, key_origen):
            hoy_actual = pd.Timestamp.now().normalize()
            df_tabla = df_segmento.copy()
            
            if not df_tabla.empty:
                df_tabla["FECHA_PREPARACION_DT"] = df_tabla["FECHA_PREPARACION_DT"].fillna(hoy_actual)
                df_tabla["DIAS_PASADOS"] = (hoy_actual - df_tabla["FECHA_PREPARACION_DT"]).dt.days
                
                def alertar_semaforo(dias):
                    if dias >= 6: return f"🔴 Crítico ({dias} días)"
                    elif dias >= 3: return f"⚠️ Demorado ({dias} días)"
                    return f"🟢 Al Día ({dias} días)"
                    
                df_tabla["ALERTA_OPERATIVA"] = df_tabla["DIAS_PASADOS"].apply(alertar_semaforo)
            else:
                df_tabla["DIAS_PASADOS"] = pd.Series(dtype=int)
                df_tabla["ALERTA_OPERATIVA"] = pd.Series(dtype=str)

            col_vendedor = "VENDEDOR" if "VENDEDOR" in df_tabla.columns else ("VENDEDOR (BOLETO)" if "VENDEDOR (BOLETO)" in df_tabla.columns else "VENDEDOR")
            col_canal = "CANAL DE VENTA" if "CANAL DE VENTA" in df_tabla.columns else "CANAL DE VENTA"
            
            cols_estructuradas = [
                "VIN", "CLIENTE", col_vendedor, col_canal, "MARCA", "MODELO", 
                "FECHA_PREPARACION_DT", "FECHA_ENTREGA_DT", "DIAS_PASADOS", "ALERTA_OPERATIVA"
            ]
            
            cols_reales_tabla = [c for c in cols_estructuradas if c in df_tabla.columns]
            df_render_maestro = df_tabla[cols_reales_tabla].loc[:, ~df_tabla[cols_reales_tabla].columns.duplicated()]
            
            if not df_render_maestro.empty:
                st.dataframe(
                    df_render_maestro.sort_values(by="DIAS_PASADOS" if "DIAS_PASADOS" in df_render_maestro.columns else "CLIENTE", ascending=False),
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "FECHA_PREPARACION_DT": st.column_config.DateColumn("Fecha Pedido Preparación", format="DD/MM/YYYY"),
                        "FECHA_ENTREGA_DT": st.column_config.DateColumn("Fecha Confirmación Entrega", format="DD/MM/YYYY"),
                        "DIAS_PASADOS": st.column_config.NumberColumn("Tiempo Transcurrido (Días)", format="%d"),
                        "ALERTA_OPERATIVA": st.column_config.TextColumn("Alerta Operativa"),
                        col_vendedor: st.column_config.TextColumn("Vendedor"),
                        col_canal: st.column_config.TextColumn("Canal de Venta")
                    }
                )
            else:
                st.success("✅ Todo al día para esta combinación de estados en el sistema.")

        # =========================================================
        # 📂 LAS DOS GRANDES SUB-PESTAÑAS DE INTERFAZ DEL PANEL
        # =========================================================
        tab_sub_fisico, tab_sub_documental = st.tabs(["🏢 Estado Físico de Unidad", "📄 Estado de Documentación"])

        # ---------------------------------------------------------
        # PESTAÑA A: ESTADO FÍSICO DE UNIDAD (CON BOTONES ADENTRO)
        # ---------------------------------------------------------
        with tab_sub_fisico:
            if "ESTADO" in df_stock_real.columns:
                conteo_fisico = df_stock_real["ESTADO_CLEAN"].value_counts()
                iconos_stock = {"EN EXHIBICIÓN": "🏢", "EN EXHIBICION": "🏢", "SIN PRE ENTREGA": "🛠️", "CON PRE ENTREGA": "✨", "BLOQUEADO": "🔒", "RESERVADO": "🔖", "DISPONIBLE": "🟢"}
                
                cols_f = st.columns(len(conteo_fisico) + 1)
                with cols_f[0]:
                    type_t = "primary" if st.session_state.filtro_estado_stock is None else "secondary"
                    if st.button(f"📋 Todos Real Stock ({len(df_stock_real)})", use_container_width=True, key="btn_f_todos_puro", type=type_t):
                        st.session_state.filtro_estado_stock = None
                        
                for idx, (est, cant) in enumerate(conteo_fisico.items()):
                    ic = iconos_stock.get(str(est), "🚗")
                    col_dst = cols_f[idx+1] if (idx+1) < len(cols_f) else cols_f[-1]
                    with col_dst:
                        type_b = "primary" if st.session_state.filtro_estado_stock == est else "secondary"
                        if st.button(f"{ic} {est.title()} ({cant})", use_container_width=True, key=f"btn_f_item_{idx}", type=type_b):
                            st.session_state.filtro_estado_stock = est

            # Filtrado Puro Independiente Físico
            df_resultado_fisico = df_stock_real.copy()
            if st.session_state.filtro_estado_stock:
                df_resultado_fisico = df_resultado_fisico[df_resultado_fisico["ESTADO_CLEAN"] == st.session_state.filtro_estado_stock]

            st.markdown("<br>", unsafe_allow_html=True)
            label_f_act = st.session_state.filtro_estado_stock if st.session_state.filtro_estado_stock else "Todos Real Stock"
            st.markdown(f"##### 📋 Tabla de Control Operativo y Alertas de Tiempos — Estado Físico: `{label_f_act}`")
            renderizar_tabla_tiempos_operativa(df_resultado_fisico, "tabla_fisica_pura")


        # ---------------------------------------------------------
        # PESTAÑA B: ESTADO DE DOCUMENTACIÓN (GRÁFICOS MENSUALES CORREGIDOS)
        # ---------------------------------------------------------
        with tab_sub_documental:
            # Doble botonera operativa de tablas
            st.markdown("##### Seleccionar segmento operativo a visualizar (Documentación):")
            col_b1, col_b2 = st.columns(2)
            
            type_b1 = "primary" if st.session_state.filtro_doc_segmento == '🚀 Con Fecha de Entrega' else "secondary"
            type_b2 = "primary" if st.session_state.filtro_doc_segmento == '🚨 SIN Fecha de Entrega' else "secondary"
            
            with col_b1:
                if st.button(f"🚀 Con Fecha de Entrega ({len(df_con_fecha)})", use_container_width=True, type=type_b1, key="btn_doc_con_fecha"):
                    st.session_state.filtro_doc_segmento = '🚀 Con Fecha de Entrega'
            with col_b2:
                if st.button(f"🚨 SIN Fecha de Entrega ({len(df_sin_fecha)})", use_container_width=True, type=type_b2, key="btn_doc_sin_fecha"):
                    st.session_state.filtro_doc_segmento = '🚨 SIN Fecha de Entrega'
                    
            st.markdown("<br>", unsafe_allow_html=True)
            hoy_dt = pd.Timestamp.now().normalize()
            
            col_vendedor_native = "VENDEDOR" if "VENDEDOR" in df_stock_real.columns else ("VENDEDOR (BOLETO)" if "VENDEDOR (BOLETO)" in df_stock_real.columns else "VENDEDOR")
            col_canal_native = "CANAL DE VENTA" if "CANAL DE VENTA" in df_stock_real.columns else "CANAL DE VENTA"

            # -----------------------------------------------------
            # ESCENARIO A: 🚀 CON FECHA DE ENTREGA SELECTOR ACTIVO
            # -----------------------------------------------------
            if st.session_state.filtro_doc_segmento == '🚀 Con Fecha de Entrega':
                st.markdown(f"##### 📋 Tabla de Control Operativo — `{st.session_state.filtro_doc_segmento}`")
                
                df_tabla_doc_act = df_con_fecha.copy()
                
                if not df_tabla_doc_act.empty:
                    df_tabla_doc_act["DIF_PEDIDO_ENTREGA"] = (df_tabla_doc_act["FECHA_ENTREGA_DT"] - df_tabla_doc_act["FECHA_PEDIDO_UNIDAD_DT"]).dt.days
                    df_tabla_doc_act["DIF_PAPELES_ENTREGA"] = (df_tabla_doc_act["FECHA_ENTREGA_DT"] - df_tabla_doc_act["FECHA_PAPELES_DT"]).dt.days
                    df_tabla_doc_act["DIF_PEDIDO_ENTREGA"] = df_tabla_doc_act["DIF_PEDIDO_ENTREGA"].fillna(0).astype(int)
                    df_tabla_doc_act["DIF_PAPELES_ENTREGA"] = df_tabla_doc_act["DIF_PAPELES_ENTREGA"].fillna(0).astype(int)
                else:
                    df_tabla_doc_act["DIF_PEDIDO_ENTREGA"] = pd.Series(dtype=int)
                    df_tabla_doc_act["DIF_PAPELES_ENTREGA"] = pd.Series(dtype=int)
                    
                cols_a_mostrar = ["MARCA", "VIN", "CLIENTE", col_canal_native, col_vendedor_native, "DIF_PEDIDO_ENTREGA", "DIF_PAPELES_ENTREGA"]
                cols_reales_a = [c for c in cols_a_mostrar if c in df_tabla_doc_act.columns]
                df_final_render_a = df_tabla_doc_act[cols_reales_values := cols_reales_a].loc[:, ~df_tabla_doc_act[cols_reales_values].columns.duplicated()]
                
                if not df_final_render_a.empty:
                    st.dataframe(
                        df_final_render_a.sort_values(by="CLIENTE"),
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "MARCA": st.column_config.TextColumn("Marca"),
                            "VIN": st.column_config.TextColumn("VIN"),
                            "CLIENTE": st.column_config.TextColumn("Cliente"),
                            col_canal_native: st.column_config.TextColumn("Canal de Venta"),
                            col_vendedor_native: st.column_config.TextColumn("Vendedor"),
                            "DIF_PEDIDO_ENTREGA": st.column_config.NumberColumn(
                                "Días Pedido ➔ Entrega", 
                                format="%d", 
                                help="Días totales transcurridos desde que se pidió la unidad hasta la fecha de entrega pactada con el cliente."
                            ),
                            "DIF_PAPELES_ENTREGA": st.column_config.NumberColumn(
                                "Días Papeles Disp. ➔ Entrega", 
                                format="%d", 
                                help="Días de demora desde que los papeles estuvieron disponibles en la concesionaria hasta el día de la entrega."
                            )
                        }
                    )
                else:
                    st.info("No hay vehículos con fecha de entrega planificada.")

            # -----------------------------------------------------
            # ESCENARIO B: 🚨 SIN FECHA DE ENTREGA SELECTOR ACTIVO
            # -----------------------------------------------------
            else:
                st.markdown(f"##### 📋 Tabla de Alertas y Seguimiento — `{st.session_state.filtro_doc_segmento}`")
                
                df_tabla_doc_pend = df_sin_fecha.copy()
                
                if not df_tabla_doc_pend.empty:
                    df_tabla_doc_pend["DIF_PEDIDO_HOY"] = (hoy_dt - df_tabla_doc_pend["FECHA_PEDIDO_UNIDAD_DT"]).dt.days
                    df_tabla_doc_pend["DIF_PAPELES_HOY"] = (hoy_dt - df_tabla_doc_pend["FECHA_PAPELES_DT"]).dt.days
                    df_tabla_doc_pend["DIF_PEDIDO_HOY"] = df_tabla_doc_pend["DIF_PEDIDO_HOY"].fillna(0).astype(int)
                    df_tabla_doc_pend["DIF_PAPELES_HOY"] = df_tabla_doc_pend["DIF_PAPELES_HOY"].fillna(0).astype(int)
                else:
                    df_tabla_doc_pend["DIF_PEDIDO_HOY"] = pd.Series(dtype=int)
                    df_tabla_doc_pend["DIF_PAPELES_HOY"] = pd.Series(dtype=int)
                    
                cols_b_mostrar = ["MARCA", "VIN", "CLIENTE", "TELEFONO_CLEAN", col_canal_native, col_vendedor_native, "DIF_PEDIDO_HOY", "DIF_PAPELES_HOY"]
                cols_reales_b = [c for c in cols_b_mostrar if c in df_tabla_doc_pend.columns]
                df_final_render_b = df_tabla_doc_pend[cols_reales_values_b := cols_reales_b].loc[:, ~df_tabla_doc_pend[cols_reales_values_b].columns.duplicated()]
                
                if not df_final_render_b.empty:
                    st.dataframe(
                        df_final_render_b.sort_values(by="DIF_PEDIDO_HOY", ascending=False),
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "MARCA": st.column_config.TextColumn("Marca"),
                            "VIN": st.column_config.TextColumn("VIN"),
                            "CLIENTE": st.column_config.TextColumn("Cliente"),
                            "TELEFONO_CLEAN": st.column_config.TextColumn("Teléfono"),
                            col_canal_native: st.column_config.TextColumn("Canal de Venta"),
                            col_vendedor_native: st.column_config.TextColumn("Vendedor"),
                            "DIF_PEDIDO_HOY": st.column_config.NumberColumn(
                                "Días Pedido ➔ Hoy", 
                                format="%d", 
                                help="Días acumulados desde la fecha de pedido de la unidad hasta el día de hoy, sin haber coordinado aún la entrega."
                            ),
                            "DIF_PAPELES_HOY": st.column_config.NumberColumn(
                                "Días Papeles Disp. ➔ Hoy", 
                                format="%d", 
                                help="Días que lleva el vehículo con los papeles listos y disponibles en la empresa hasta el día de hoy sin agendar entrega."
                            )
                        }
                    )
                else:
                    st.success("✅ ¡Excelente! No se registran clientes sin fecha de entrega asignada.")

            # --- SECCIÓN: TENDENCIA DE TIEMPOS PROMEDIO (AJUSTADO A MENSAL VISUAL) ---
            st.markdown("---")
            st.markdown("### 📈 Tendencia de Tiempos Promedio")
            
            col_g_btn1, col_g_btn2 = st.columns(2)
            type_g1 = "primary" if st.session_state.filtro_grafico_segmento == '🚀 Vista: Con Fecha de Entrega' else "secondary"
            type_g2 = "primary" if st.session_state.filtro_grafico_segmento == '🚨 Vista: SIN Fecha de Entrega' else "secondary"
            
            with col_g_btn1:
                if st.button("🚀 Vista: Con Fecha de Entrega", use_container_width=True, type=type_g1, key="btn_graf_con_fecha"):
                    st.session_state.filtro_grafico_segmento = '🚀 Vista: Con Fecha de Entrega'
            with col_g_btn2:
                if st.button("🚨 Vista: SIN Fecha de Entrega", use_container_width=True, type=type_g2, key="btn_graf_sin_fecha"):
                    st.session_state.filtro_grafico_segmento = '🚨 Vista: SIN Fecha de Entrega'
            
            st.markdown("<br>", unsafe_allow_html=True)
            g_line1, g_line2 = st.columns(2)

            # --- SUB-RENDERING GRÁFICO 1 Y 2: CON FECHA DE ENTREGA ---
            if st.session_state.filtro_grafico_segmento == '🚀 Vista: Con Fecha de Entrega':
                df_g_con = df_con_fecha.copy()
                if not df_g_con.empty:
                    df_g_con = df_g_con.dropna(subset=["FECHA_ENTREGA_DT"])
                    df_g_con["DIF_PEDIDO_ENTREGA"] = (df_g_con["FECHA_ENTREGA_DT"] - df_g_con["FECHA_PEDIDO_UNIDAD_DT"]).dt.days
                    df_g_con["DIF_PAPELES_ENTREGA"] = (df_g_con["FECHA_ENTREGA_DT"] - df_g_con["FECHA_PAPELES_DT"]).dt.days
                    df_g_con["AÑO_MES_X"] = df_g_con["FECHA_ENTREGA_DT"].dt.strftime('%Y-%m')
                    df_graf_base = df_g_con.dropna(subset=["AÑO_MES_X"]).sort_values("AÑO_MES_X")
                    
                    with g_line1:
                        st.markdown("##### Gráfico 1: Promedio Días Pedido ➔ Entrega")
                        with st.expander("ℹ️ Ayuda: ¿Qué mide este gráfico? (Pedido ➔ Entrega)", expanded=False):
                            st.caption("**EJE X (Año-Mes):** Se extraerá de la Fecha de Entrega al Cliente.\n\n"
                                       "**Por qué:** Nos permite agrupar y evaluar la eficiencia de las unidades que efectivamente se cerraron y entregaron en ese mes específico.\n\n"
                                       "**EJE Y (Días):** Promedio de días transcurridos generales.")
                        
                        df_g1 = df_graf_base.dropna(subset=["DIF_PEDIDO_ENTREGA"]).groupby("AÑO_MES_X")["DIF_PEDIDO_ENTREGA"].mean().reset_index(name="Promedio Días")
                        if not df_g1.empty:
                            st.bar_chart(df_g1.set_index("AÑO_MES_X")["Promedio Días"], use_container_width=True)
                        else:
                            st.caption("Faltan datos cronológicos.")
                            
                    with g_line2:
                        st.markdown("##### Gráfico 2: Promedio Días Papeles Disp. ➔ Entrega")
                        with st.expander("ℹ️ Ayuda: ¿Qué mide este gráfico? (Papeles Disp. ➔ Entrega)", expanded=False):
                            st.caption("**EJE X (Año-Mes):** Se extraerá de la Fecha de Entrega al Cliente.\n\n"
                                       "**Recomendación:** Usar la Fecha de Entrega al Cliente es lo ideal aquí para medir el rendimiento de entrega del equipo de administración/gestoría durante ese mes evaluado.\n\n"
                                       "**EJE Y (Días):** Promedio de días de demora desde la liberación del trámite.")
                        
                        df_g2 = df_graf_base.dropna(subset=["DIF_PAPELES_ENTREGA"]).groupby("AÑO_MES_X")["DIF_PAPELES_ENTREGA"].mean().reset_index(name="Promedio Días")
                        if not df_g2.empty:
                            st.bar_chart(df_g2.set_index("AÑO_MES_X")["Promedio Días"], use_container_width=True)
                        else:
                            st.caption("Faltan datos cronológicos.")
                else:
                    st.info("Sin registros con fecha de entrega para calcular tendencias.")

            # --- SUB-RENDERING GRÁFICO 3 Y 4: CASOS PENDIENTES ACTIVOS ---
            else:
                df_g_pend = df_sin_fecha.copy()
                if not df_g_pend.empty:
                    df_g_pend["DIF_PEDIDO_HOY"] = (hoy_dt - df_g_pend["FECHA_PEDIDO_UNIDAD_DT"]).dt.days
                    df_g_pend["DIF_PAPELES_HOY"] = (hoy_dt - df_g_pend["FECHA_PAPELES_DT"]).dt.days
                    
                    with g_line1:
                        st.markdown("##### Gráfico 3: Promedio Días Pedido ➔ Hoy (Sin Entrega)")
                        with st.expander("ℹ️ Ayuda: ¿Qué mide este gráfico? (Pedido ➔ Hoy)", expanded=False):
                            st.caption("**EJE X (Año-Mes):** Se extraerá de la Fecha de Pedido de la Unidad.\n\n"
                                       "**Por qué:** Te mostrará de manera visual si te están quedando autos remanentes 'viejos'. Por ejemplo, verás una barra o punto alto en meses pasados (ej. 2026-01), alertándote de que hay pedidos de principios de año que acumulando días siguen sin fecha de entrega.\n\n"
                                       "**EJE Y (Días):** Promedio de días de retraso acumulados hasta HOY.")
                        
                        df_g_pend["AÑO_MES_PEDIDO"] = df_g_pend["FECHA_PEDIDO_UNIDAD_DT"].dt.strftime('%Y-%m')
                        df_g3 = df_g_pend.dropna(subset=["AÑO_MES_PEDIDO", "DIF_PEDIDO_HOY"]).groupby("AÑO_MES_PEDIDO")["DIF_PEDIDO_HOY"].mean().reset_index(name="Promedio Días").sort_values("AÑO_MES_PEDIDO")
                        if not df_g3.empty:
                            st.bar_chart(df_g3.set_index("AÑO_MES_PEDIDO")["Promedio Días"], use_container_width=True)
                        else:
                            st.caption("Faltan registros con fecha de pedido.")
                            
                    with g_line2:
                        st.markdown("##### Gráfico 4: Promedio Días Papeles Disp. ➔ Hoy (Sin Entrega)")
                        with st.expander("ℹ️ Ayuda: ¿Qué mide este gráfico? (Papeles Disp. ➔ Hoy)", expanded=False):
                            st.caption("**EJE X (Año-Mes):** Se extraerá de la Fecha de Disponibilidad de Papeles.\n\n"
                                       "**Por qué:** Te indicará en qué mes se liberaron administrativamente esos papeles que hoy en día siguen acumulando demoras sin poder coordinar la entrega con el cliente.\n\n"
                                       "**EJE Y (Días):** Promedio de días estancados administrativamente hasta HOY.")
                        
                        df_g_pend["AÑO_MES_PAPELES"] = df_g_pend["FECHA_PAPELES_DT"].dt.strftime('%Y-%m')
                        df_g4 = df_g_pend.dropna(subset=["AÑO_MES_PAPELES", "DIF_PAPELES_HOY"]).groupby("AÑO_MES_PAPELES")["DIF_PAPELES_HOY"].mean().reset_index(name="Promedio Días").sort_values("AÑO_MES_PAPELES")
                        if not df_g4.empty:
                            st.bar_chart(df_g4.set_index("AÑO_MES_PAPELES")["Promedio Días"], use_container_width=True)
                        else:
                            st.caption("Faltan registros con papeles liberados.")
                else:
                    st.info("Sin registros pendientes para graficar el envejecimiento.")

    else:
        st.error("Set de datos vacío.")

elif opcion == "🛠️ Control Mantenimiento":
    st.title("🛠️ Planificación de Taller")
    if not df_0km.empty and "FECHA_ARRIBO_DT" in df_0km.columns:
        st.sidebar.header("Filtros")
        marcas = st.sidebar.multiselect("Filtrar Marca", df_0km["MARCA"].unique())
        hoy = pd.Timestamp.now().normalize()
        inicio_semana = hoy - timedelta(days=hoy.weekday())
        fin_semana = inicio_semana + timedelta(days=6)
        df_mant = df_0km.copy()
        if "ESTADO" in df_mant.columns:
            df_mant = df_mant[df_mant["ESTADO"].astype(str).str.strip().str.upper() != "ENTREGADO"]
        if marcas:
            df_mant = df_mant[df_mant["MARCA"].isin(marcas)]
        cols_control = {
            30: next((c for c in df_0km.columns if "30" in c and "REALIZADO" in c), None),
            60: next((c for c in df_0km.columns if "60" in c and "REALIZADO" in c), None),
            90: next((c for c in df_0km.columns if "90" in c and "REALIZADO" in c), None),
            180: next((c for c in df_0km.columns if "180" in c and "REALIZADO" in c), None),
            360: next((c for c in df_0km.columns if "360" in c and "REALIZADO" in c), None),
            540: next((c for c in df_0km.columns if "540" in c and "REALIZADO" in c), None),
        }
        lista_hoy, lista_semana, lista_atrasados = [], [], []
        for index, row in df_mant.iterrows():
            if pd.isnull(row["FECHA_ARRIBO_DT"]): continue
            fecha_arribo = row["FECHA_ARRIBO_DT"]
            motivos_hoy, motifs_semana, motifs_atrasados = [], [], []
            for intervalo, columna in cols_control.items():
                if not columna: continue
                fecha_vencimiento = fecha_arribo + timedelta(days=intervalo)
                estado_celda = str(row[columna]).strip().upper()
                if estado_celda in ["OK", "N/A", "SI"]: continue
                if fecha_vencimiento == hoy: motivos_hoy.append(f"Control {intervalo} días")
                if inicio_semana <= fecha_vencimiento <= fin_semana: motifs_semana.append(f"Control {intervalo} días ({fecha_vencimiento.strftime('%d/%m')})")
                if hoy >= fecha_vencimiento: motifs_atrasados.append(f"Falta {intervalo} días (Venció: {fecha_vencimiento.strftime('%d/%m')})")
            if motivos_hoy:
                r = row.copy(); r["TAREA"] = ", ".join(motivos_hoy); lista_hoy.append(r)
            if motifs_semana:
                r = row.copy(); r["TAREA"] = ", ".join(motifs_semana); lista_semana.append(r)
            if motifs_atrasados:
                r = row.copy(); r["TAREA"] = motifs_atrasados[-1]; lista_atrasados.append(r)
        
        c1, c2, c3 = st.columns(3)
        t_hoy = "primary" if st.session_state.filtro_mantenimiento == 'hoy' else "secondary"
        t_sem = "primary" if st.session_state.filtro_mantenimiento == 'semana' else "secondary"
        t_tod = "primary" if st.session_state.filtro_mantenimiento == 'todos' else "secondary"

        if c1.button(f"📅 Vence HOY ({len(lista_hoy)})", use_container_width=True, type=t_hoy): st.session_state.filtro_mantenimiento = 'hoy'
        if c2.button(f"📆 Vence Esta Semana ({len(lista_semana)})", use_container_width=True, type=t_sem): st.session_state.filtro_mantenimiento = 'semana'
        if c3.button(f"🚨 Todo Pendiente ({len(lista_atrasados)})", use_container_width=True, type=t_tod): st.session_state.filtro_mantenimiento = 'todos'
        st.divider()
        
        df_final = pd.DataFrame()
        if st.session_state.filtro_mantenimiento == 'hoy':
            df_final = pd.DataFrame(lista_hoy); titulo = "🚗 Vehículos que vencen HOY"
        elif st.session_state.filtro_mantenimiento == 'semana':
            df_final = pd.DataFrame(lista_semana); titulo = "🗓️ Planificación Semanal"
        else:
            df_final = pd.DataFrame(lista_atrasados); titulo = "⚠️ Listado de Atrasados / Pendientes"
        
        if not df_final.empty:
            st.subheader(titulo)
            cols_base = ["VIN", "MARCA", "MODELO", "FECHA_ARRIBO_DT", "TAREA", "UBICACION"]
            cols_reales = [c for c in cols_base if c in df_final.columns]
            st.dataframe(df_final[cols_reales], use_container_width=True, hide_index=True, column_config={"FECHA_ARRIBO_DT": st.column_config.DateColumn("Fecha Arribo", format="DD/MM/YYYY")})
        else:
            if st.session_state.filtro_mantenimiento != 'todos': st.success("✅ ¡Nada pendiente!")
            else: st.success("✅ ¡Felicitaciones! No hay mantenimientos atrasados.")
    else:
        st.warning("No se encontraron datos.")

elif opcion == "🗺️ Plano del Salón":
    st.title("🗺️ Distribución del Salón")
    tab_peugeot, tab_citroen = st.tabs(["🦁 Peugeot", "🔴 Citroën"])
    with tab_peugeot:
        if os.path.exists("mapa_peugeot.jpg"): st.image("mapa_peugeot.jpg", use_container_width=True)
        elif os.path.exists("Peugeot (2).jpeg"): st.image("Peugeot (2).jpeg", use_container_width=True)
        else: st.warning("Sube 'mapa_peugeot.jpg'")
    with tab_citroen:
        if os.path.exists("mapa_citroen.jpg"): st.image("mapa_citroen.jpg", use_container_width=True)
        elif os.path.exists("Citroen.jpeg"): st.image("Citroen.jpeg", use_container_width=True)
        else: st.warning("Sube 'mapa_citroen.jpg'")     Fíjate que este código tiene más de 700 líneas y yo te estoy pidiendo que ajustes a lo que te pedí anteriormente a este código y me estás dando mucho menos código es decir mucho menos filas y Estamos perdiendo información.
