import streamlit as st
import pandas as pd
import os
import plotly.graph_objects as go
import plotly.figure_factory as ff
from datetime import datetime, timedelta
import math
from streamlit_calendar import calendar

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Portal Formación 2026", layout="wide", page_icon="🎓")

# --- ESTILOS ---
st.markdown("""
<style>
    div.stButton > button {width: 100%; border-radius: 8px; font-weight: bold; margin-bottom: 5px; height: 45px;}
    [data-testid="stSidebar"] img {display: block; margin: 0 auto 20px auto;}
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: #f0f2f6; border-radius: 4px 4px 0 0; padding: 10px 20px; }
    .stTabs [aria-selected="true"] { background-color: #ffffff; border-bottom: 2px solid #4CAF50; }
    .fc .fc-daygrid-day-frame { min-height: 120px !important; }
    .fc-daygrid-event { white-space: normal !important; align-items: flex-start !important; font-size: 0.8em !important; cursor: pointer !important; }
</style>
""", unsafe_allow_html=True)

# --- LOGIN ---
if 'acceso_concedido' not in st.session_state:
    st.session_state.acceso_concedido = False

def mostrar_login():
    st.markdown("<h2 style='text-align: center;'>🔒 Portal Privado</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        clave = st.text_input("Contraseña", type="password")
        if st.button("Ingresar", use_container_width=True, type="primary"):
            if clave == "CENOA2026":
                st.session_state.acceso_concedido = True
                st.rerun()
            else:
                st.error("🚫 Clave incorrecta.")

if not st.session_state.acceso_concedido:
    mostrar_login()
    st.stop()

# --- CARGA DE DATOS ---
SHEET_ID = "11yH6PUYMpt-m65hFH9t2tWSEgdRpLOCFR3OFjJtWToQ"
GID_GENERAL = "245378054"
GID_PLANIF = "829571230"

URL_GENERAL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_GENERAL}"
URL_PLANIF = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_PLANIF}"

@st.cache_data(ttl=60)
def load_data_general():
    try:
        df = pd.read_csv(URL_GENERAL)
        df.columns = df.columns.str.strip().str.upper()
        col_map = {}
        for c in df.columns:
            if "SECTOR" in c: col_map[c] = 'SECTOR'
            elif "ROL" in c or "CARGO" in c: col_map[c] = 'CARGO'
            elif "NOMBRE" in c or "COLABORADOR" in c: col_map[c] = 'COLABORADOR'
            elif "FORMACION" in c or "CURSO" in c: col_map[c] = 'CURSO'
            elif "CAPACITA" in c or "ESTADO" in c: col_map[c] = 'ESTADO_NUM'
            elif "NIVEL" in c: col_map[c] = 'NIVEL'
        
        df = df.rename(columns=col_map)
        df = df.loc[:, ~df.columns.duplicated()]
        
        if 'ESTADO_NUM' in df.columns:
            df['ESTADO_NUM'] = pd.to_numeric(df['ESTADO_NUM'], errors='coerce').fillna(0).astype(int)
        else:
            df['ESTADO_NUM'] = 0

        for c in ['SECTOR', 'CARGO', 'COLABORADOR', 'NIVEL']:
            if c in df.columns:
                df[c] = df[c].astype(str).str.strip().str.upper()
        return df
    except Exception as e:
        st.error(f"Error en Datos Generales: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60)
def load_planificacion():
    try:
        df_p = pd.read_csv(URL_PLANIF)
        df_p.columns = df_p.columns.str.strip().str.upper()
        if 'FECHA' in df_p.columns:
            df_p['FECHA_DT'] = pd.to_datetime(df_p['FECHA'], dayfirst=True, errors='coerce')
        return df_p.fillna("")
    except Exception:
        return pd.DataFrame()

df = load_data_general()
df_planif_raw = load_planificacion()

if df.empty or 'SECTOR' not in df.columns:
    st.error("⚠️ Error de formato en la hoja de cálculo.")
    st.stop()

# --- ESTADO DE SESIÓN ---
if 'sector_activo' not in st.session_state: st.session_state.sector_activo = "Todos"
if 'ultimo_cargo_sel' not in st.session_state: st.session_state.ultimo_cargo_sel = "Todos"
if 'colaborador_activo' not in st.session_state: st.session_state.colaborador_activo = 'Todos'
if 'nivel_seleccionado' not in st.session_state: st.session_state.nivel_seleccionado = 'Ambos'

# --- BARRA LATERAL ---
st.sidebar.title("🏢 Sectores")
if st.sidebar.button("VER TODO", type=("primary" if st.session_state.sector_activo == "Todos" else "secondary")):
    st.session_state.update({"sector_activo": "Todos", "ultimo_cargo_sel": "Todos", "colaborador_activo": "Todos"})
    st.rerun()

for sec in sorted(df['SECTOR'].unique()):
    df_s = df[df['SECTOR'] == sec]
    total_sec = len(df_s)
    realizados = (df_s['ESTADO_NUM'] == 1).sum() if 'ESTADO_NUM' in df_s.columns else 0
    avance = (realizados / total_sec * 100) if total_sec > 0 else 0
    
    color_sidebar = "#ef5350" if avance < 50 else "#ffa726" if avance < 90 else "#66bb6a"
    c1, c2 = st.sidebar.columns([1, 4])
    c1.markdown(f"<div style='margin-top:10px; width:15px; height:15px; background-color:{color_sidebar}; border-radius:50%;'></div>", unsafe_allow_html=True)
    if c2.button(f"{sec} ({avance:.0f}%)", key=f"sidebar_{sec}", type=("primary" if st.session_state.sector_activo == sec else "secondary")):
        st.session_state.update({"sector_activo": sec, "ultimo_cargo_sel": "Todos", "colaborador_activo": "Todos"})
        st.rerun()

st.sidebar.title("👮 Puestos")
df_roles = df[df['SECTOR'] == st.session_state.sector_activo] if st.session_state.sector_activo != "Todos" else df
roles = ["Todos"] + sorted(df_roles['CARGO'].unique().tolist()) if 'CARGO' in df_roles.columns else ["Todos"]

sel_rol = st.sidebar.selectbox("Seleccionar puesto:", roles, index=roles.index(st.session_state.ultimo_cargo_sel) if st.session_state.ultimo_cargo_sel in roles else 0)
if sel_rol != st.session_state.ultimo_cargo_sel:
    st.session_state.ultimo_cargo_sel = sel_rol
    st.session_state.colaborador_activo = 'Todos'
    st.rerun()

if st.sidebar.button("🔒 Salir"):
    st.session_state.acceso_concedido = False
    st.rerun()

# --- LÓGICA DE FILTRADO ---
df_main = df_roles[df_roles['CARGO'] == sel_rol] if sel_rol != "Todos" else df_roles

st.title(f"🎓 Gestión de Formación: {st.session_state.sector_activo} > {sel_rol}")
tab1, tab2, tab3 = st.tabs(["📊 Tablero de Control", "📅 Planificador & Gantt", "🗓️ Agenda Interactiva"])

with tab1:
    if not df_main.empty:
        st.write("### ⚖️ Nivel de Formación")
        niveles = ["Ambos", "NIVEL 1", "NIVEL 2"]
        sel_nivel = st.selectbox("Ver indicadores de:", niveles, index=niveles.index(st.session_state.nivel_seleccionado))
        if sel_nivel != st.session_state.nivel_seleccionado:
            st.session_state.nivel_seleccionado = sel_nivel
            st.rerun()

        st.divider()
        nombres = sorted(df_main['COLABORADOR'].unique())
        cols = st.columns(4)
        
        if cols[0].button(f"👥 Ver Todo ({len(nombres)})", type=("primary" if st.session_state.colaborador_activo == 'Todos' else "secondary")):
             st.session_state.colaborador_activo = 'Todos'
             st.rerun()
        
        for i, nom in enumerate(nombres):
            df_indiv = df_main[df_main['COLABORADOR'] == nom]
            if st.session_state.nivel_seleccionado != 'Ambos':
                df_indiv = df_indiv[df_indiv.get('NIVEL') == st.session_state.nivel_seleccionado]
            
            t_ind = len(df_indiv)
            ok_ind = (df_indiv['ESTADO_NUM'] == 1).sum() if 'ESTADO_NUM' in df_indiv.columns else 0
            p_ind = (ok_ind / t_ind * 100) if t_ind > 0 else 0
            emoji = "🟢" if p_ind == 100 else "🔴" if p_ind < 50 else "🟠"
            
            if cols[(i+1)%4].button(f"{emoji} {nom} ({p_ind:.0f}%)", key=f"btn_{i}", type=("primary" if st.session_state.colaborador_activo == nom else "secondary")):
                st.session_state.colaborador_activo = nom
                st.rerun()
        
        st.divider()
        df_view = df_main[df_main['COLABORADOR'] == st.session_state.colaborador_activo] if st.session_state.colaborador_activo != 'Todos' else df_main
        df_view_calc = df_view if st.session_state.nivel_seleccionado == 'Ambos' else df_view[df_view.get('NIVEL') == st.session_state.nivel_seleccionado]
        
        total = len(df_view_calc)
        ok = (df_view_calc['ESTADO_NUM'] == 1).sum() if 'ESTADO_NUM' in df_view_calc.columns else 0
        porc = (ok / total * 100) if total > 0 else 0
        
        st.markdown(f"<div style='background-color:#f0f2f6; padding:15px; border-radius:10px; border-left: 5px solid {'green' if porc==100 else 'orange' if porc>=50 else 'red'};'><h4>Avance {st.session_state.nivel_seleccionado}: {porc:.1f}% ({st.session_state.colaborador_activo})</h4></div>", unsafe_allow_html=True)
        
        c1, c2 = st.columns([1, 2])
        with c1:
            fig = go.Figure(go.Indicator(mode="gauge+number", value=porc, gauge={'axis':{'range':[None,100]}, 'bar':{'color': 'green' if porc==100 else 'orange'}}))
            fig.update_layout(height=250, margin=dict(t=30, b=20))
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.info(f"Completado: **{ok}** de **{total}** cursos.")
            st.dataframe(df_view_calc[['COLABORADOR','CURSO','NIVEL','ESTADO_NUM']], use_container_width=True, hide_index=True)

with tab2:
    fecha_fin = datetime(2026, 3, 20)
    fecha_hoy = datetime.now()
    dias_restantes = (fecha_fin - fecha_hoy).days
    
    if dias_restantes > 0:
        dias_h = sum(1 for i in range(dias_restantes + 1) if (fecha_hoy + timedelta(i)).weekday() < 5)
        semanas_r = max(1, math.ceil(dias_h / 5))
        df_pend = df_main[df_main['ESTADO_NUM'] == 0] if 'ESTADO_NUM' in df_main.columns else df_main
        df_plan = df_pend[df_pend['COLABORADOR'] == st.session_state.colaborador_activo] if st.session_state.colaborador_activo != 'Todos' else df_pend
        
        if not df_plan.empty:
            ritmo = math.ceil(len(df_plan) / semanas_r)
            st.metric("Meta Semanal", f"{ritmo} cursos/semana")
            df_gantt = []
            for i, row in enumerate(df_plan.itertuples()):
                n_s = (i // ritmo)
                ini = fecha_hoy + timedelta(weeks=n_s)
                df_gantt.append(dict(Task=f"{row.COLABORADOR[:10]}", Start=ini.strftime('%Y-%m-%d'), Finish=(ini + timedelta(days=4)).strftime('%Y-%m-%d'), Resource=getattr(row, 'NIVEL', 'N/A')))
            if df_gantt:
                fig_g = ff.create_gantt(df_gantt, index_col='Resource', show_colorbar=True, group_tasks=True)
                st.plotly_chart(fig_g, use_container_width=True)
        else:
            st.success("🎉 ¡Objetivo cumplido!")
    else:
        st.warning("⚠️ Fecha límite superada.")

with tab3:
    st.subheader("🗓️ Agenda de Cursos Interactiva")
    contenedor_detalles = st.empty()
    if df_planif_raw.empty:
        st.warning("⚠️ No hay datos en Planificación.")
    elif 'FECHA_DT' not in df_planif_raw.columns:
        st.error("❌ Revisa la columna FECHA en tu Excel.")
    else:
        df_cal = df_planif_raw.dropna(subset=['FECHA_DT']).copy()
        nombres_planif = ["Todos"] + sorted(df_cal['COLABORADOR'].unique().tolist())
        busqueda = st.selectbox("🔍 Filtrar por colaborador:", nombres_planif)

        if busqueda != "Todos":
            df_cal = df_cal[df_cal['COLABORADOR'] == busqueda]

        calendar_events = []
        for _, row in df_cal.iterrows():
            tipo = str(row.get('CURSO', '')).upper()
            color = "#28a745" if "PRESENCIAL" in tipo else "#3788d8"
            calendar_events.append({
                "title": f"{str(row.get('COLABORADOR', ''))[:10]} | {str(row.get('NOMBRE DEL CURSO', ''))[:15]}",
                "start": row['FECHA_DT'].strftime('%Y-%m-%d'),
                "backgroundColor": color,
                "allDay": True,
                "extendedProps": {
                    "horario": str(row.get('HORARIO', 'No definido')),
                    "link": str(row.get('LINK', '')),
                    "curso": str(row.get('NOMBRE DEL CURSO', '')),
                    "obs": str(row.get('OBSERVACIONES', 'Sin observaciones'))
                }
            })

        state = calendar(events=calendar_events, options={"locale": "es", "height": 600}, key="calendar_v4")
        
        if state.get("eventClick"):
            ev = state["eventClick"]["event"]
            with contenedor_detalles.container():
                st.info(f"📌 **Curso:** {ev['extendedProps']['curso']}")
                st.write(f"⌚ **Horario:** {ev['extendedProps']['horario']}")
                if ev['extendedProps']['link'].startswith("http"):
                    st.link_button("🚀 UNIRSE", ev['extendedProps']['link'])
