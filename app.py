# ==========================================
# 1. PLANIFICACIÓN ENTREGAS
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
        type_ent = "primary" if st.session_state.modo_vista_agenda == 'entregados' else "secondary"
        type_prog = "primary" if st.session_state.modo_vista_agenda == 'programados' else "secondary"
        type_mes = "primary" if st.session_state.modo_vista_agenda == 'mes' else "secondary"

        if c1.button(f"✅ Ya Entregados ({len(entregados)})", use_container_width=True, type=type_ent):
            st.session_state.modo_vista_agenda = 'entregados'
        if c2.button(f"🚀 Programados ({len(programados)})", use_container_width=True, type=type_prog):
            st.session_state.modo_vista_agenda = 'programados'
        if c3.button("📅 Filtrar por Mes / Día", use_container_width=True, type=type_mes):
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
                    dia_filtro = st.date_input("📅 Filtrar día", value=None, min_value=df_mes["FECHA_ENTREGA_DT"].min(), max_value=df_mes["FECHA_ENTREGA_DT"].max())
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
            
            # --- MODIFICACIÓN: DETECTAR LA COLUMNA ADMINISTRATIVA ---
            col_admin = next((c for c in df.columns if "ESTADO" in c and "ADMIN" in c), None)
            
            # Definimos el orden de las columnas
            cols_agenda = ["FECHA_ENTREGA_DT", "HS DE ENTREGA AL CLIENTE", "CLIENTE"]
            
            # Si encontramos la columna administrativa, la insertamos aquí
            if col_admin:
                cols_agenda.append(col_admin)
            
            # Agregamos el resto de columnas
            cols_agenda.extend(["MARCA", "MODELO", "VIN", "CANAL DE VENTA", "TELEFONO_CLEAN", "CORREO_CLEAN", "VENDEDOR"])
            
            cols_reales = [c for c in cols_agenda if c in df_final.columns]
            
            st.dataframe(
                df_final[cols_reales].sort_values(["FECHA_ENTREGA_DT", "HS DE ENTREGA AL CLIENTE"]), 
                use_container_width=True, 
                hide_index=True, 
                column_config={
                    "FECHA_ENTREGA_DT": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY"),
                    col_admin: st.column_config.TextColumn("Estado Admin") # Opcional: Renombramos el encabezado para que se vea limpio
                }
            )
        else:
            if st.session_state.modo_vista_agenda != 'mes': st.info("No hay vehículos aquí.")
