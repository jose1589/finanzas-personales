from datetime import timedelta
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from database import (
    actualizar_movimiento,
    agregar_categoria,
    agregar_movimiento,
    eliminar_categoria,
    eliminar_movimiento,
    eliminar_presupuesto,
    guardar_presupuesto,
    obtener_categorias,
    obtener_movimientos,
    obtener_presupuestos,
)
from utils import (
    exportar_csv,
    exportar_excel,
    formato_cop,
    hoy_colombia,
    nombre_mes_anio,
)

# ============================================================================
# CONFIGURACIÓN DE PÁGINA Y ESTILOS RESPONSIVOS
# ============================================================================

st.set_page_config(
    page_title="Control Financiero Personal",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="auto",
)

CUSTOM_CSS = """
<style>
    /* Contenedor principal limpio y adaptable */
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2.5rem;
        max-width: 1280px;
    }

    /* Tarjetas de indicadores financieros (KPI) */
    .kpi-card {
        background-color: #FFFFFF;
        border-radius: 14px;
        padding: 1.1rem 1.25rem;
        border: 1px solid #E2E8F0;
        box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
        margin-bottom: 0.75rem;
        transition: transform 0.15s ease;
    }
    .kpi-card:hover {
        transform: translateY(-2px);
    }
    .kpi-title {
        font-size: 0.82rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: #64748B;
        margin-bottom: 0.35rem;
    }
    .kpi-value {
        font-size: 1.55rem;
        font-weight: 700;
        line-height: 1.2;
        word-break: break-word;
    }
    .kpi-sub {
        font-size: 0.78rem;
        color: #64748B;
        margin-top: 0.35rem;
    }
    .border-ingreso { border-left: 5px solid #10B981; }
    .border-gasto   { border-left: 5px solid #EF4444; }
    .border-balance { border-left: 5px solid #2563EB; }
    .border-neutro  { border-left: 5px solid #64748B; }

    .text-ingreso { color: #059669; }
    .text-gasto   { color: #DC2626; }
    .text-balance { color: #1D4ED8; }
    .text-neutro  { color: #0F172A; }

    /* Ajustes para pantallas de celular */
    @media (max-width: 768px) {
        .block-container {
            padding-top: 1rem;
            padding-left: 0.85rem;
            padding-right: 0.85rem;
        }
        .kpi-value {
            font-size: 1.3rem;
        }
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

METODOS_PAGO = ["Efectivo", "Transferencia", "Tarjeta", "Otro"]


# ============================================================================
# COMPONENTES REUTILIZABLES DE INTERFAZ
# ============================================================================

def render_kpi_card(titulo: str, valor: str, subtitulo: str, estilo: str) -> None:
    """Renderiza una tarjeta KPI moderna y responsiva."""
    st.markdown(
        f"""
        <div class="kpi-card border-{estilo}">
            <div class="kpi-title">{titulo}</div>
            <div class="kpi-value text-{estilo}">{valor}</div>
            <div class="kpi-sub">{subtitulo}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def estilizar_tabla_movimientos(df: pd.DataFrame):
    """Aplica formato COP y colores diferenciados para Ingresos y Gastos."""
    df_vista = df[["id", "fecha", "descripcion", "categoria", "tipo", "valor", "metodo_pago"]].copy()
    df_vista["valor_fmt"] = df_vista.apply(
        lambda r: f"+ {formato_cop(r['valor'])}" if r["tipo"] == "Ingreso" else f"- {formato_cop(r['valor'])}",
        axis=1,
    )
    df_vista = df_vista[["id", "fecha", "descripcion", "categoria", "tipo", "valor_fmt", "metodo_pago"]]
    df_vista.columns = ["ID", "Fecha", "Descripción", "Categoría", "Tipo", "Valor (COP)", "Método de pago"]

    def color_tipo(val: str) -> str:
        if val == "Ingreso" or str(val).startswith("+"):
            return "color: #059669; font-weight: 600;"
        if val == "Gasto" or str(val).startswith("-"):
            return "color: #DC2626; font-weight: 600;"
        return ""

    return df_vista.style.map(color_tipo, subset=["Tipo", "Valor (COP)"])


def render_formulario_registro(df_categorias: pd.DataFrame, key_prefix: str = "dash") -> None:
    """Renderiza el formulario de registro diario de ingresos y gastos."""
    st.subheader("➕ Registrar nuevo movimiento")

    tipo_seleccionado = st.radio(
        "Tipo de movimiento",
        options=["Gasto", "Ingreso"],
        horizontal=True,
        key=f"{key_prefix}_tipo_radio",
    )

    cats_filtradas = (
        df_categorias.loc[df_categorias["tipo"] == tipo_seleccionado, "nombre"].tolist()
        if not df_categorias.empty
        else []
    )
    if not cats_filtradas:
        cats_filtradas = ["General"]

    with st.form(key=f"{key_prefix}_form_movimiento", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            valor = st.number_input(
                "Valor en pesos colombianos (COP)",
                min_value=1,
                step=1000,
                value=10000,
                format="%d",
            )
            categoria = st.selectbox("Categoría", options=cats_filtradas)

        with col2:
            fecha_mov = st.date_input(
                "Fecha del movimiento",
                value=hoy_colombia(),
                format="YYYY-MM-DD",
            )
            metodo_pago = st.selectbox("Método de pago", options=METODOS_PAGO)

        descripcion = st.text_input(
            "Descripción del movimiento",
            placeholder="Ej: Almuerzo, Pago de nómina, Transporte, Servicios...",
        )

        enviado = st.form_submit_button(
            "💾 Guardar movimiento",
            type="primary",
            use_container_width=True,
        )

        if enviado:
            if not descripcion.strip():
                st.warning("Por favor escribe una descripción para el movimiento.")
            elif valor <= 0:
                st.warning("El valor debe ser mayor que $ 0.")
            else:
                exito, mensaje = agregar_movimiento(
                    fecha_mov=fecha_mov,
                    descripcion=descripcion,
                    categoria=categoria,
                    tipo=tipo_seleccionado,
                    valor=valor,
                    metodo_pago=metodo_pago,
                )
                if exito:
                    st.toast(f"✅ {mensaje}")
                    st.rerun()
                else:
                    st.error(mensaje)


# ============================================================================
# VISTAS PRINCIPALES DE LA APLICACIÓN
# ============================================================================

def vista_dashboard(df_movs: pd.DataFrame, df_cats: pd.DataFrame) -> None:
    """Vista 1: Panel de control principal, registro rápido y resumen mensual."""
    st.title("💰 Panel de Control Financiero")
    st.caption(f"Moneda: Peso Colombiano (COP) · Fecha actual: {hoy_colombia().strftime('%d/%m/%Y')}")

    # Cálculos globales exactos
    total_ingresos = float(df_movs.loc[df_movs["tipo"] == "Ingreso", "valor"].sum()) if not df_movs.empty else 0.0
    total_gastos = float(df_movs.loc[df_movs["tipo"] == "Gasto", "valor"].sum()) if not df_movs.empty else 0.0
    balance_disponible = total_ingresos - total_gastos
    cantidad_movs = len(df_movs)

    # Tarjetas KPI principales
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_kpi_card("Total Ingresos", formato_cop(total_ingresos), "Acumulado histórico", "ingreso")
    with c2:
        render_kpi_card("Total Gastos", formato_cop(total_gastos), "Acumulado histórico", "gasto")
    with c3:
        estilo_bal = "balance" if balance_disponible >= 0 else "gasto"
        render_kpi_card("Balance Disponible", formato_cop(balance_disponible), "Ingresos - Gastos", estilo_bal)
    with c4:
        render_kpi_card("Movimientos", f"{cantidad_movs:,}".replace(",", "."), "Registros guardados", "neutro")

    st.divider()

    # Formulario de registro rápido en contenedor expandible abierto por defecto
    with st.expander("📝 Registro rápido de ingreso o gasto", expanded=True):
        render_formulario_registro(df_cats, key_prefix="dashboard")

    st.divider()

    # Selector de mes para el resumen financiero mensual y presupuesto
    hoy = hoy_colombia()
    mes_actual_str = f"{hoy.year}-{hoy.month:02d}"

    meses_disponibles = {mes_actual_str}
    if not df_movs.empty:
        for f in df_movs["fecha"]:
            meses_disponibles.add(f"{f.year}-{f.month:02d}")
    lista_meses = sorted(list(meses_disponibles), reverse=True)

    col_tit, col_sel = st.columns([2, 1])
    with col_tit:
        st.subheader("📅 Resumen Financiero del Mes")
    with col_sel:
        mes_elegido = st.selectbox(
            "Seleccionar mes",
            options=lista_meses,
            format_func=nombre_mes_anio,
            label_visibility="collapsed",
        )

    anio_sel, mes_sel = map(int, mes_elegido.split("-"))
    if not df_movs.empty:
        df_mes = df_movs[
            df_movs["fecha"].apply(lambda d: d.year == anio_sel and d.month == mes_sel)
        ]
    else:
        df_mes = pd.DataFrame(columns=df_movs.columns)

    ingresos_mes = float(df_mes.loc[df_mes["tipo"] == "Ingreso", "valor"].sum()) if not df_mes.empty else 0.0
    gastos_mes = float(df_mes.loc[df_mes["tipo"] == "Gasto", "valor"].sum()) if not df_mes.empty else 0.0
    balance_mes = ingresos_mes - gastos_mes

    m1, m2, m3 = st.columns(3)
    m1.metric("Ingresos del mes", formato_cop(ingresos_mes))
    m2.metric("Gastos del mes", formato_cop(gastos_mes))
    m3.metric(
        "Balance del mes",
        formato_cop(balance_mes),
        delta=f"{((balance_mes / ingresos_mes) * 100):.1f}% ahorro" if ingresos_mes > 0 else None,
    )

    # Indicador de Presupuesto Mensual General
    df_pres_mes = obtener_presupuestos(mes_elegido)
    pres_general = df_pres_mes[df_pres_mes["categoria"] == "General"] if not df_pres_mes.empty else pd.DataFrame()
    if not pres_general.empty:
        limite_general = float(pres_general.iloc[0]["monto_limite"])
        disponible_pres = limite_general - gastos_mes
        porcentaje = (gastos_mes / limite_general) if limite_general > 0 else 0.0

        st.markdown(f"**🎯 Presupuesto mensual ({nombre_mes_anio(mes_elegido)}):**")
        p1, p2, p3 = st.columns(3)
        p1.metric("Presupuesto asignado", formato_cop(limite_general))
        p2.metric("Gastado en el mes", formato_cop(gastos_mes))
        p3.metric("Disponible del presupuesto", formato_cop(disponible_pres))

        st.progress(min(porcentaje, 1.0))
        if disponible_pres < 0:
            st.error(f"⚠️ Has excedido tu presupuesto mensual por {formato_cop(abs(disponible_pres))}.")
        elif porcentaje >= 0.8:
            st.warning(f"⚡ Has consumido el {porcentaje * 100:.1f}% de tu presupuesto mensual.")
        else:
            st.info(f"✅ Te queda el {(1 - porcentaje) * 100:.1f}% disponible de tu presupuesto.")

    st.divider()

    # Gráficos de Ingresos frente a Gastos
    col_g1, col_g2 = st.columns(2)

    with col_g1:
        st.subheader("📊 Ingresos vs Gastos (Mes seleccionado)")
        df_comp_mes = pd.DataFrame(
            {
                "Tipo": ["Ingresos", "Gastos"],
                "Valor": [ingresos_mes, gastos_mes],
            }
        )
        fig_bar = px.bar(
            df_comp_mes,
            x="Tipo",
            y="Valor",
            color="Tipo",
            text=df_comp_mes["Valor"].apply(formato_cop),
            color_discrete_map={"Ingresos": "#10B981", "Gastos": "#EF4444"},
        )
        fig_bar.update_traces(textposition="outside")
        fig_bar.update_layout(
            showlegend=False,
            yaxis_title="Monto (COP)",
            xaxis_title="",
            height=360,
            margin=dict(t=30, b=20, l=20, r=20),
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_g2:
        st.subheader("🍩 Distribución Histórica")
        if total_ingresos == 0 and total_gastos == 0:
            st.info("Aún no hay movimientos registrados para mostrar el gráfico.")
        else:
            fig_pie = px.pie(
                names=["Ingresos", "Gastos"],
                values=[total_ingresos, total_gastos],
                hole=0.5,
                color=["Ingresos", "Gastos"],
                color_discrete_map={"Ingresos": "#10B981", "Gastos": "#EF4444"},
            )
            fig_pie.update_traces(textinfo="percent+label")
            fig_pie.update_layout(
                height=360,
                margin=dict(t=30, b=20, l=20, r=20),
            )
            st.plotly_chart(fig_pie, use_container_width=True)

    # Últimos 10 movimientos registrados
    st.subheader("🕒 Últimos movimientos registrados")
    if df_movs.empty:
        st.info("No hay movimientos registrados todavía. Usa el formulario superior para agregar el primero.")
    else:
        st.dataframe(
            estilizar_tabla_movimientos(df_movs.head(10)),
            use_container_width=True,
            hide_index=True,
        )


def vista_historial_gestion(df_movs: pd.DataFrame, df_cats: pd.DataFrame) -> None:
    """Vista 2: Tabla completa con búsqueda, filtros, edición, eliminación y exportación."""
    st.title("📋 Historial y Gestión de Movimientos")

    if df_movs.empty:
        st.info("Aún no tienes movimientos registrados en la base de datos.")
        return

    # Barra de búsqueda y filtros
    with st.expander("🔍 Buscar y filtrar movimientos", expanded=True):
        f1, f2, f3 = st.columns(3)
        with f1:
            fecha_min = df_movs["fecha"].min()
            fecha_max = df_movs["fecha"].max()
            fecha_desde = st.date_input("Desde", value=fecha_min, min_value=fecha_min, max_value=fecha_max)
        with f2:
            fecha_hasta = st.date_input("Hasta", value=fecha_max, min_value=fecha_min, max_value=fecha_max)
        with f3:
            busqueda = st.text_input("Buscar descripción", placeholder="Palabra clave...")

        f4, f5, f6 = st.columns(3)
        with f4:
            filtro_tipo = st.selectbox("Tipo", options=["Todos", "Ingreso", "Gasto"])
        with f5:
            categorias_unicas = ["Todas"] + sorted(df_movs["categoria"].unique().tolist())
            filtro_cat = st.selectbox("Categoría", options=categorias_unicas)
        with f6:
            filtro_metodo = st.selectbox("Método de pago", options=["Todos"] + METODOS_PAGO)

    # Aplicar filtros
    df_filtrado = df_movs.copy()
    df_filtrado = df_filtrado[(df_filtrado["fecha"] >= fecha_desde) & (df_filtrado["fecha"] <= fecha_hasta)]

    if filtro_tipo != "Todos":
        df_filtrado = df_filtrado[df_filtrado["tipo"] == filtro_tipo]
    if filtro_cat != "Todas":
        df_filtrado = df_filtrado[df_filtrado["categoria"] == filtro_cat]
    if filtro_metodo != "Todos":
        df_filtrado = df_filtrado[df_filtrado["metodo_pago"] == filtro_metodo]
    if busqueda.strip():
        df_filtrado = df_filtrado[
            df_filtrado["descripcion"].str.contains(busqueda.strip(), case=False, na=False)
        ]

    # Resumen de resultados filtrados
    ing_filt = float(df_filtrado.loc[df_filtrado["tipo"] == "Ingreso", "valor"].sum())
    gas_filt = float(df_filtrado.loc[df_filtrado["tipo"] == "Gasto", "valor"].sum())
    bal_filt = ing_filt - gas_filt

    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Registros encontrados", len(df_filtrado))
    r2.metric("Ingresos filtrados", formato_cop(ing_filt))
    r3.metric("Gastos filtrados", formato_cop(gas_filt))
    r4.metric("Balance filtrado", formato_cop(bal_filt))

    # Botones de exportación a Excel y CSV
    col_exp1, col_exp2, _ = st.columns([1, 1, 2])
    with col_exp1:
        st.download_button(
            label="📥 Exportar a Excel (.xlsx)",
            data=exportar_excel(df_filtrado),
            file_name=f"movimientos_financieros_{hoy_colombia().isoformat()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    with col_exp2:
        st.download_button(
            label="📄 Exportar a CSV (.csv)",
            data=exportar_csv(df_filtrado),
            file_name=f"movimientos_financieros_{hoy_colombia().isoformat()}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    st.divider()

    # Tabla principal estilizada
    if df_filtrado.empty:
        st.warning("Ningún movimiento coincide con los filtros seleccionados.")
    else:
        st.dataframe(
            estilizar_tabla_movimientos(df_filtrado),
            use_container_width=True,
            hide_index=True,
        )

    st.divider()

    # Sección para Editar o Eliminar un registro existente
    st.subheader("✏️ Editar o Eliminar un Movimiento")
    opciones_movs = {
        int(row["id"]): (
            f"#{int(row['id'])} | {row['fecha']} | {row['tipo']} | "
            f"{row['descripcion']} ({formato_cop(row['valor'])})"
        )
        for _, row in df_filtrado.iterrows()
    }

    if not opciones_movs:
        st.info("Selecciona un rango con movimientos para editar o eliminar.")
        return

    id_seleccionado = st.selectbox(
        "Selecciona el movimiento que deseas corregir o eliminar",
        options=list(opciones_movs.keys()),
        format_func=lambda k: opciones_movs[k],
    )

    registro = df_filtrado[df_filtrado["id"] == id_seleccionado].iloc[0]

    tab_editar, tab_eliminar = st.tabs(["✏️ Corregir registro", "🗑️ Eliminar registro"])

    with tab_editar:
        nuevo_tipo = st.radio(
            "Tipo de movimiento",
            options=["Gasto", "Ingreso"],
            index=0 if registro["tipo"] == "Gasto" else 1,
            horizontal=True,
            key=f"edit_tipo_{id_seleccionado}",
        )

        cats_tipo = (
            df_cats.loc[df_cats["tipo"] == nuevo_tipo, "nombre"].tolist()
            if not df_cats.empty
            else []
        )
        if registro["categoria"] not in cats_tipo:
            cats_tipo.append(registro["categoria"])

        with st.form(key=f"form_editar_{id_seleccionado}"):
            ec1, ec2 = st.columns(2)
            with ec1:
                nuevo_valor = st.number_input(
                    "Valor (COP)",
                    min_value=1,
                    step=1000,
                    value=int(round(float(registro["valor"]))),
                    format="%d",
                )
                nueva_cat = st.selectbox(
                    "Categoría",
                    options=cats_tipo,
                    index=cats_tipo.index(registro["categoria"]),
                )
            with ec2:
                nueva_fecha = st.date_input("Fecha", value=registro["fecha"])
                idx_metodo = (
                    METODOS_PAGO.index(registro["metodo_pago"])
                    if registro["metodo_pago"] in METODOS_PAGO
                    else 0
                )
                nuevo_metodo = st.selectbox("Método de pago", options=METODOS_PAGO, index=idx_metodo)

            nueva_desc = st.text_input("Descripción", value=registro["descripcion"])

            if st.form_submit_button("💾 Guardar cambios", type="primary", use_container_width=True):
                if not nueva_desc.strip():
                    st.warning("La descripción no puede quedar vacía.")
                else:
                    ok, msg = actualizar_movimiento(
                        mov_id=id_seleccionado,
                        fecha_mov=nueva_fecha,
                        descripcion=nueva_desc,
                        categoria=nueva_cat,
                        tipo=nuevo_tipo,
                        valor=nuevo_valor,
                        metodo_pago=nuevo_metodo,
                    )
                    if ok:
                        st.toast(f"✅ {msg}")
                        st.rerun()
                    else:
                        st.error(msg)

    with tab_eliminar:
        st.warning(
            f"Estás a punto de eliminar permanentemente el registro **#{id_seleccionado}**: "
            f"**{registro['descripcion']}** por **{formato_cop(registro['valor'])}**."
        )
        confirmar_borrado = st.checkbox(
            "Confirmo que deseo eliminar este movimiento de forma permanente",
            key=f"chk_del_{id_seleccionado}",
        )
        if st.button(
            "🗑️ Eliminar movimiento",
            type="primary",
            disabled=not confirmar_borrado,
            key=f"btn_del_{id_seleccionado}",
        ):
            ok, msg = eliminar_movimiento(id_seleccionado)
            if ok:
                st.toast(f"🗑️ {msg}")
                st.rerun()
            else:
                st.error(msg)


def vista_estadisticas(df_movs: pd.DataFrame) -> None:
    """Vista 3: Análisis estadístico diario, semanal, mensual, anual y evolución del balance."""
    st.title("📈 Estadísticas y Análisis Financiero")

    if df_movs.empty:
        st.info("Registra algunos ingresos y gastos para visualizar tus estadísticas interactivas.")
        return

    df = df_movs.copy()
    df["fecha_dt"] = pd.to_datetime(df["fecha"])

    # Filtro de período para análisis
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        fecha_inicio = st.date_input("Fecha inicial de análisis", value=df["fecha"].min())
    with col_p2:
        fecha_fin = st.date_input("Fecha final de análisis", value=df["fecha"].max())

    df_periodo = df[(df["fecha"] >= fecha_inicio) & (df["fecha"] <= fecha_fin)].copy()
    if df_periodo.empty:
        st.warning("No hay datos en el rango de fechas seleccionado.")
        return

    # 1. Evolución del Balance Acumulado
    st.subheader("📉 Evolución del Balance Disponible")
    diario_pivot = (
        df_periodo.pivot_table(
            index="fecha",
            columns="tipo",
            values="valor",
            aggfunc="sum",
            fill_value=0.0,
        )
        .reset_index()
        .sort_values("fecha")
    )
    if "Ingreso" not in diario_pivot.columns:
        diario_pivot["Ingreso"] = 0.0
    if "Gasto" not in diario_pivot.columns:
        diario_pivot["Gasto"] = 0.0

    diario_pivot["Neto_Dia"] = diario_pivot["Ingreso"] - diario_pivot["Gasto"]
    diario_pivot["Balance_Acumulado"] = diario_pivot["Neto_Dia"].cumsum()

    fig_evolucion = go.Figure()
    fig_evolucion.add_trace(
        go.Scatter(
            x=diario_pivot["fecha"],
            y=diario_pivot["Balance_Acumulado"],
            mode="lines+markers",
            name="Balance Acumulado",
            line=dict(color="#2563EB", width=3),
            fill="tozeroy",
            fillcolor="rgba(37, 99, 235, 0.12)",
        )
    )
    fig_evolucion.update_layout(
        xaxis_title="Fecha",
        yaxis_title="Balance (COP)",
        hovermode="x unified",
        height=380,
        margin=dict(t=20, b=20, l=20, r=20),
    )
    st.plotly_chart(fig_evolucion, use_container_width=True)

    st.divider()

    # 2. Categorías en las que más dinero se gasta
    st.subheader("🏷️ Categorías en las que más dinero gastas")
    df_gastos = df_periodo[df_periodo["tipo"] == "Gasto"]
    if df_gastos.empty:
        st.info("No hay gastos registrados en este período.")
    else:
        gastos_cat = (
            df_gastos.groupby("categoria", as_index=False)["valor"]
            .sum()
            .sort_values("valor", ascending=False)
        )
        total_g_periodo = gastos_cat["valor"].sum()
        gastos_cat["Porcentaje"] = (gastos_cat["valor"] / total_g_periodo) * 100

        cg1, cg2 = st.columns([3, 2])
        with cg1:
            fig_cat = px.bar(
                gastos_cat,
                x="valor",
                y="categoria",
                orientation="h",
                text=gastos_cat["valor"].apply(formato_cop),
                color="valor",
                color_continuous_scale="Reds",
            )
            fig_cat.update_layout(
                yaxis=dict(autorange="reversed", title=""),
                xaxis_title="Total Gastado (COP)",
                coloraxis_showscale=False,
                height=380,
                margin=dict(t=20, b=20, l=20, r=40),
            )
            fig_cat.update_traces(textposition="outside")
            st.plotly_chart(fig_cat, use_container_width=True)

        with cg2:
            tabla_cat = gastos_cat.copy()
            tabla_cat["Total (COP)"] = tabla_cat["valor"].apply(formato_cop)
            tabla_cat["Participación"] = tabla_cat["Porcentaje"].apply(lambda p: f"{p:.1f}%")
            st.dataframe(
                tabla_cat[["categoria", "Total (COP)", "Participación"]].rename(
                    columns={"categoria": "Categoría"}
                ),
                use_container_width=True,
                hide_index=True,
            )

    st.divider()

    # 3. Pestañas de Resúmenes Temporales (Diario, Semanal, Mensual, Anual)
    st.subheader("🗓️ Resúmenes Temporales (Diario, Semanal, Mensual y Anual)")
    t_diario, t_semanal, t_mensual, t_anual = st.tabs(
        ["📅 Diario", "📆 Semanal", "🗓️ Mensual", "📊 Anual"]
    )

    with t_diario:
        df_diario_melt = diario_pivot.melt(
            id_vars=["fecha"],
            value_vars=["Ingreso", "Gasto"],
            var_name="Tipo",
            value_name="Valor",
        )
        fig_d = px.bar(
            df_diario_melt,
            x="fecha",
            y="Valor",
            color="Tipo",
            barmode="group",
            color_discrete_map={"Ingreso": "#10B981", "Gasto": "#EF4444"},
            title="Ingresos y Gastos Diarios",
        )
        fig_d.update_layout(xaxis_title="Fecha", yaxis_title="Monto (COP)", height=380)
        st.plotly_chart(fig_d, use_container_width=True)

        tabla_d = diario_pivot[["fecha", "Ingreso", "Gasto", "Neto_Dia"]].sort_values("fecha", ascending=False).copy()
        for col in ["Ingreso", "Gasto", "Neto_Dia"]:
            tabla_d[col] = tabla_d[col].apply(formato_cop)
        tabla_d.columns = ["Fecha", "Ingresos", "Gastos", "Balance del Día"]
        st.dataframe(tabla_d, use_container_width=True, hide_index=True)

    with t_semanal:
        df_sem = df_periodo.copy()
        df_sem["Semana"] = df_sem["fecha_dt"].dt.to_period("W-SUN").apply(lambda p: str(p.start_time.date()))
        sem_pivot = (
            df_sem.pivot_table(
                index="Semana",
                columns="tipo",
                values="valor",
                aggfunc="sum",
                fill_value=0.0,
            )
            .reset_index()
            .sort_values("Semana")
        )
        for col in ["Ingreso", "Gasto"]:
            if col not in sem_pivot.columns:
                sem_pivot[col] = 0.0
        sem_pivot["Balance"] = sem_pivot["Ingreso"] - sem_pivot["Gasto"]

        fig_s = px.bar(
            sem_pivot.melt(id_vars=["Semana"], value_vars=["Ingreso", "Gasto"], var_name="Tipo", value_name="Valor"),
            x="Semana",
            y="Valor",
            color="Tipo",
            barmode="group",
            color_discrete_map={"Ingreso": "#10B981", "Gasto": "#EF4444"},
            title="Resumen Semanal (Inicio de semana: Lunes)",
        )
        fig_s.update_layout(xaxis_title="Semana", yaxis_title="Monto (COP)", height=380)
        st.plotly_chart(fig_s, use_container_width=True)

        tabla_s = sem_pivot.sort_values("Semana", ascending=False).copy()
        for col in ["Ingreso", "Gasto", "Balance"]:
            tabla_s[col] = tabla_s[col].apply(formato_cop)
        tabla_s.columns = ["Semana (Inicio)", "Ingresos", "Gastos", "Balance Semanal"]
        st.dataframe(tabla_s, use_container_width=True, hide_index=True)

    with t_mensual:
        df_mes_ag = df_periodo.copy()
        df_mes_ag["Mes"] = df_mes_ag["fecha_dt"].dt.strftime("%Y-%m")
        mes_pivot = (
            df_mes_ag.pivot_table(
                index="Mes",
                columns="tipo",
                values="valor",
                aggfunc="sum",
                fill_value=0.0,
            )
            .reset_index()
            .sort_values("Mes")
        )
        for col in ["Ingreso", "Gasto"]:
            if col not in mes_pivot.columns:
                mes_pivot[col] = 0.0
        mes_pivot["Balance"] = mes_pivot["Ingreso"] - mes_pivot["Gasto"]

        fig_m = px.bar(
            mes_pivot.melt(id_vars=["Mes"], value_vars=["Ingreso", "Gasto"], var_name="Tipo", value_name="Valor"),
            x="Mes",
            y="Valor",
            color="Tipo",
            barmode="group",
            color_discrete_map={"Ingreso": "#10B981", "Gasto": "#EF4444"},
            title="Comparativo Mensual de Ingresos y Gastos",
        )
        fig_m.update_layout(xaxis_title="Mes", yaxis_title="Monto (COP)", height=380)
        st.plotly_chart(fig_m, use_container_width=True)

        tabla_m = mes_pivot.sort_values("Mes", ascending=False).copy()
        tabla_m["Mes"] = tabla_m["Mes"].apply(nombre_mes_anio)
        for col in ["Ingreso", "Gasto", "Balance"]:
            tabla_m[col] = tabla_m[col].apply(formato_cop)
        tabla_m.columns = ["Mes", "Ingresos", "Gastos", "Balance Mensual"]
        st.dataframe(tabla_m, use_container_width=True, hide_index=True)

    with t_anual:
        df_an = df_periodo.copy()
        df_an["Año"] = df_an["fecha_dt"].dt.year.astype(str)
        an_pivot = (
            df_an.pivot_table(
                index="Año",
                columns="tipo",
                values="valor",
                aggfunc="sum",
                fill_value=0.0,
            )
            .reset_index()
            .sort_values("Año")
        )
        for col in ["Ingreso", "Gasto"]:
            if col not in an_pivot.columns:
                an_pivot[col] = 0.0
        an_pivot["Balance"] = an_pivot["Ingreso"] - an_pivot["Gasto"]

        fig_a = px.bar(
            an_pivot.melt(id_vars=["Año"], value_vars=["Ingreso", "Gasto"], var_name="Tipo", value_name="Valor"),
            x="Año",
            y="Valor",
            color="Tipo",
            barmode="group",
            color_discrete_map={"Ingreso": "#10B981", "Gasto": "#EF4444"},
            title="Resumen Anual",
        )
        fig_a.update_layout(xaxis_title="Año", yaxis_title="Monto (COP)", height=380)
        st.plotly_chart(fig_a, use_container_width=True)

        tabla_a = an_pivot.sort_values("Año", ascending=False).copy()
        for col in ["Ingreso", "Gasto", "Balance"]:
            tabla_a[col] = tabla_a[col].apply(formato_cop)
        tabla_a.columns = ["Año", "Ingresos", "Gastos", "Balance Anual"]
        st.dataframe(tabla_a, use_container_width=True, hide_index=True)


def vista_presupuestos_categorias(df_movs: pd.DataFrame, df_cats: pd.DataFrame) -> None:
    """Vista 4: Gestión de presupuestos mensuales, categorías personalizadas y respaldos."""
    st.title("⚙️ Presupuestos, Categorías y Respaldos")

    tab_pres, tab_cats, tab_backup = st.tabs(
        ["🎯 Presupuestos Mensuales", "🏷️ Categorías Personalizadas", "💾 Copia de Seguridad"]
    )

    # ------------------------------------------------------------------------
    # TAB 1: PRESUPUESTOS MENSUALES
    # ------------------------------------------------------------------------
    with tab_pres:
        st.subheader("Configurar presupuesto mensual")
        hoy = hoy_colombia()
        mes_defecto = f"{hoy.year}-{hoy.month:02d}"

        opciones_meses = [
            f"{(hoy + timedelta(days=30 * i)).year}-{(hoy + timedelta(days=30 * i)).month:02d}"
            for i in range(-3, 7)
        ]
        opciones_meses = sorted(list(set(opciones_meses)), reverse=True)

        cats_gasto = ["General"]
        if not df_cats.empty:
            cats_gasto += df_cats.loc[df_cats["tipo"] == "Gasto", "nombre"].tolist()

        with st.form("form_presupuesto"):
            cp1, cp2, cp3 = st.columns(3)
            with cp1:
                mes_pres = st.selectbox(
                    "Mes",
                    options=opciones_meses,
                    index=opciones_meses.index(mes_defecto) if mes_defecto in opciones_meses else 0,
                    format_func=nombre_mes_anio,
                )
            with cp2:
                cat_pres = st.selectbox(
                    "Alcance (General o Categoría de gasto)",
                    options=cats_gasto,
                )
            with cp3:
                monto_pres = st.number_input(
                    "Límite mensual (COP)",
                    min_value=0,
                    step=50000,
                    value=1000000,
                    format="%d",
                )

            if st.form_submit_button("💾 Guardar presupuesto", type="primary", use_container_width=True):
                ok, msg = guardar_presupuesto(mes_pres, cat_pres, monto_pres)
                if ok:
                    st.toast(f"✅ {msg}")
                    st.rerun()
                else:
                    st.error(msg)

        st.divider()
        st.subheader("📊 Ejecución de presupuestos del mes")

        mes_consulta = st.selectbox(
            "Ver ejecución del mes",
            options=opciones_meses,
            index=opciones_meses.index(mes_defecto) if mes_defecto in opciones_meses else 0,
            format_func=nombre_mes_anio,
            key="sel_mes_ejecucion",
        )

        df_pres = obtener_presupuestos(mes_consulta)
        if df_pres.empty:
            st.info(f"No hay presupuestos configurados para {nombre_mes_anio(mes_consulta)}.")
        else:
            anio_c, mes_c = map(int, mes_consulta.split("-"))
            if not df_movs.empty:
                gastos_mes_df = df_movs[
                    (df_movs["tipo"] == "Gasto")
                    & (df_movs["fecha"].apply(lambda d: d.year == anio_c and d.month == mes_c))
                ]
            else:
                gastos_mes_df = pd.DataFrame(columns=["categoria", "valor"])

            for _, row_p in df_pres.iterrows():
                cat_p = row_p["categoria"]
                limite_p = float(row_p["monto_limite"])
                if cat_p == "General":
                    gastado_p = float(gastos_mes_df["valor"].sum()) if not gastos_mes_df.empty else 0.0
                else:
                    gastado_p = (
                        float(gastos_mes_df.loc[gastos_mes_df["categoria"] == cat_p, "valor"].sum())
                        if not gastos_mes_df.empty
                        else 0.0
                    )

                restante_p = limite_p - gastado_p
                ratio_p = (gastado_p / limite_p) if limite_p > 0 else 0.0

                col_info, col_del = st.columns([5, 1])
                with col_info:
                    st.markdown(
                        f"**{cat_p}** — Límite: `{formato_cop(limite_p)}` | "
                        f"Gastado: `{formato_cop(gastado_p)}` | "
                        f"Disponible: **`{formato_cop(restante_p)}`**"
                    )
                    st.progress(min(ratio_p, 1.0))
                with col_del:
                    if st.button("🗑️", key=f"del_pres_{int(row_p['id'])}", help="Eliminar presupuesto"):
                        ok, msg = eliminar_presupuesto(int(row_p["id"]))
                        if ok:
                            st.toast(msg)
                            st.rerun()

    # ------------------------------------------------------------------------
    # TAB 2: CATEGORÍAS PERSONALIZADAS
    # ------------------------------------------------------------------------
    with tab_cats:
        st.subheader("➕ Crear nueva categoría")
        with st.form("form_nueva_categoria", clear_on_submit=True):
            cc1, cc2 = st.columns([2, 1])
            with cc1:
                nombre_nueva_cat = st.text_input(
                    "Nombre de la categoría",
                    placeholder="Ej: Mascotas, Suscripciones, Gimnasio, Bonos...",
                )
            with cc2:
                tipo_nueva_cat = st.selectbox("Tipo", options=["Gasto", "Ingreso"])

            if st.form_submit_button("➕ Agregar categoría", type="primary", use_container_width=True):
                ok, msg = agregar_categoria(nombre_nueva_cat, tipo_nueva_cat)
                if ok:
                    st.toast(f"✅ {msg}")
                    st.rerun()
                else:
                    st.warning(msg)

        st.divider()
        col_cg, col_ci = st.columns(2)
        with col_cg:
            st.markdown("### 🔴 Categorías de Gasto")
            cats_g = df_cats[df_cats["tipo"] == "Gasto"] if not df_cats.empty else pd.DataFrame()
            for _, row_c in cats_g.iterrows():
                c_txt, c_btn = st.columns([4, 1])
                c_txt.write(f"• {row_c['nombre']}")
                if c_btn.button("🗑️", key=f"del_cat_{int(row_c['id'])}", help="Eliminar categoría"):
                    ok, msg = eliminar_categoria(int(row_c["id"]))
                    if ok:
                        st.toast(msg)
                        st.rerun()

        with col_ci:
            st.markdown("### 🟢 Categorías de Ingreso")
            cats_i = df_cats[df_cats["tipo"] == "Ingreso"] if not df_cats.empty else pd.DataFrame()
            for _, row_c in cats_i.iterrows():
                c_txt, c_btn = st.columns([4, 1])
                c_txt.write(f"• {row_c['nombre']}")
                if c_btn.button("🗑️", key=f"del_cat_{int(row_c['id'])}", help="Eliminar categoría"):
                    ok, msg = eliminar_categoria(int(row_c["id"]))
                    if ok:
                        st.toast(msg)
                        st.rerun()

    # ------------------------------------------------------------------------
    # TAB 3: COPIA DE SEGURIDAD COMPLETA
    # ------------------------------------------------------------------------
    with tab_backup:
        st.subheader("💾 Descargar copia de seguridad completa")
        st.write(
            "Tus datos ya están almacenados de forma permanente en la nube de **Supabase**. "
            "Adicionalmente, puedes descargar una copia local completa de todos tus movimientos en Excel o CSV:"
        )
        cb1, cb2 = st.columns(2)
        with cb1:
            st.download_button(
                label="📥 Descargar respaldo completo (Excel .xlsx)",
                data=exportar_excel(df_movs),
                file_name=f"respaldo_finanzas_completo_{hoy_colombia().isoformat()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        with cb2:
            st.download_button(
                label="📄 Descargar respaldo completo (CSV .csv)",
                data=exportar_csv(df_movs),
                file_name=f"respaldo_finanzas_completo_{hoy_colombia().isoformat()}.csv",
                mime="text/csv",
                use_container_width=True,
            )


# ============================================================================
# PUNTO DE ENTRADA Y NAVEGACIÓN LATERAL
# ============================================================================

def main() -> None:
    with st.sidebar:
        st.markdown("## 💰 Finanzas COP")
        st.caption("Control financiero personal")
        seccion = st.radio(
            "Navegación",
            options=[
                "📊 Dashboard",
                "📋 Historial y Gestión",
                "📈 Estadísticas",
                "⚙️ Presupuestos y Categorías",
            ],
            label_visibility="collapsed",
        )
        st.divider()
        st.caption("☁️ Base de datos sincronizada con Supabase.")

    df_movs = obtener_movimientos()
    df_cats = obtener_categorias()

    if seccion == "📊 Dashboard":
        vista_dashboard(df_movs, df_cats)
    elif seccion == "📋 Historial y Gestión":
        vista_historial_gestion(df_movs, df_cats)
    elif seccion == "📈 Estadísticas":
        vista_estadisticas(df_movs)
    elif seccion == "⚙️ Presupuestos y Categorías":
        vista_presupuestos_categorias(df_movs, df_cats)


if __name__ == "__main__":
    main()
