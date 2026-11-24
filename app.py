import calendar
import os
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
    guardar_meta_ahorro,
    guardar_presupuesto,
    obtener_categorias,
    obtener_metas_ahorro,
    obtener_movimientos,
    obtener_presupuestos,
)
from utils import (
    exportar_csv,
    exportar_excel,
    formato_cop,
    hoy_colombia,
    nombre_mes_anio,
    parsear_monto_cop,
)

# ============================================================================
# CONFIGURACIÓN DE PÁGINA Y ESTILOS RESPONSIVOS (PC, TABLET Y CELULAR)
# ============================================================================

LOGO_PATH = os.path.join(os.path.dirname(__file__), "assets", "logo_finanzas.png")

st.set_page_config(
    page_title="Finanzas Personales COP",
    page_icon=LOGO_PATH if os.path.exists(LOGO_PATH) else "💰",
    layout="wide",
    initial_sidebar_state="collapsed",
)

CUSTOM_CSS = """
<style>
    /* Tipografía global más grande y cómoda de leer */
    html, body, [class*="css"] {
        font-size: 17px !important;
        color: #0F172A;
    }

    .block-container {
        padding-top: 1.2rem;
        padding-bottom: 3rem;
        max-width: 1340px;
    }

    /* Encabezados amplios y claros */
    h1 {
        font-size: 2.05rem !important;
        font-weight: 800 !important;
        letter-spacing: -0.02em;
        margin-bottom: 0.25rem !important;
    }
    h2 {
        font-size: 1.5rem !important;
        font-weight: 700 !important;
    }
    h3 {
        font-size: 1.25rem !important;
        font-weight: 700 !important;
    }

    /* Etiquetas, textos de ayuda e inputs más grandes y táctiles */
    label, .stMarkdown p, .stCaption {
        font-size: 1.02rem !important;
    }
    input, textarea, select, [data-baseweb="select"] > div {
        font-size: 1.05rem !important;
        min-height: 46px !important;
    }

    /* Botones cómodos y táctiles para celular, tablet y PC */
    .stButton > button, .stDownloadButton > button, [data-testid="stFormSubmitButton"] > button {
        font-size: 1.04rem !important;
        font-weight: 600 !important;
        min-height: 48px !important;
        border-radius: 12px !important;
        padding: 0.55rem 1.1rem !important;
    }

    /* Pestañas (Tabs) grandes y fáciles de tocar */
    button[data-baseweb="tab"] {
        font-size: 1.05rem !important;
        font-weight: 600 !important;
        padding: 0.7rem 1.1rem !important;
    }

    /* Métricas nativas ampliadas */
    [data-testid="stMetricLabel"] {
        font-size: 1.0rem !important;
        font-weight: 600 !important;
        color: #475569 !important;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.55rem !important;
        font-weight: 800 !important;
    }

    /* Grid Responsivo para Tarjetas KPI (4 col PC | 2 col Tablet | 1 col Celular) */
    .kpi-grid {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 1rem;
        margin-top: 0.5rem;
        margin-bottom: 1rem;
    }

    .kpi-card {
        background-color: #FFFFFF;
        border-radius: 16px;
        padding: 1.25rem 1.35rem;
        border: 1px solid #E2E8F0;
        box-shadow: 0 4px 12px rgba(15, 23, 42, 0.05);
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 18px rgba(15, 23, 42, 0.08);
    }
    .kpi-title {
        font-size: 0.92rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: #64748B;
        margin-bottom: 0.4rem;
    }
    .kpi-value {
        font-size: 1.72rem;
        font-weight: 800;
        line-height: 1.25;
        word-break: break-word;
    }
    .kpi-sub {
        font-size: 0.9rem;
        color: #64748B;
        margin-top: 0.4rem;
    }

    .border-ingreso { border-left: 6px solid #10B981; }
    .border-gasto   { border-left: 6px solid #EF4444; }
    .border-balance { border-left: 6px solid #2563EB; }
    .border-neutro  { border-left: 6px solid #64748B; }

    .text-ingreso { color: #059669; }
    .text-gasto   { color: #DC2626; }
    .text-balance { color: #1D4ED8; }
    .text-neutro  { color: #0F172A; }

    /* Caja de vista previa de valor monetario */
    .preview-cop-box {
        background: linear-gradient(135deg, #EFF6FF 0%, #F8FAFC 100%);
        border: 1.5px solid #BFDBFE;
        border-radius: 12px;
        padding: 0.85rem 1.1rem;
        margin: 0.4rem 0 0.8rem 0;
        font-size: 1.15rem;
        font-weight: 700;
        color: #1E3A8A;
    }

    /* Tarjeta de salud financiera */
    .health-banner {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 16px;
        padding: 1.15rem 1.35rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
    }

    /* TABLET (641px a 1024px): 2 columnas cómodas */
    @media (max-width: 1024px) {
        .kpi-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }
        .kpi-value {
            font-size: 1.55rem;
        }
    }

    /* CELULAR (hasta 640px): 1 columna ancha y controles táctiles grandes */
    @media (max-width: 640px) {
        html, body, [class*="css"] {
            font-size: 16px !important;
        }
        .block-container {
            padding-top: 0.8rem;
            padding-left: 0.75rem;
            padding-right: 0.75rem;
        }
        h1 {
            font-size: 1.65rem !important;
        }
        .kpi-grid {
            grid-template-columns: 1fr;
            gap: 0.75rem;
        }
        .kpi-value {
            font-size: 1.5rem;
        }
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

METODOS_PAGO = ["Efectivo", "Transferencia", "Tarjeta", "Otro"]


# ============================================================================
# HELPER DE FORMATO MONETARIO SEGÚN PREFERENCIA DEL USUARIO
# ============================================================================

def fmt_cop(valor: float | int | None) -> str:
    """Formatea COP respetando la preferencia elegida por el usuario en sesión."""
    modo = st.session_state.get("modo_decimales", "auto")
    return formato_cop(valor, modo_decimales=modo)


# ============================================================================
# COMPONENTES REUTILIZABLES DE INTERFAZ
# ============================================================================

def render_kpi_grid(tarjetas: list[dict]) -> None:
    """
    Renderiza tarjetas KPI en un grid CSS adaptable:
    4 columnas en PC, 2x2 en Tablet, 1 columna en Celular.
    """
    bloques = []
    for t in tarjetas:
        bloques.append(
            f'<div class="kpi-card border-{t["estilo"]}">'
            f'<div class="kpi-title">{t["titulo"]}</div>'
            f'<div class="kpi-value text-{t["estilo"]}">{t["valor"]}</div>'
            f'<div class="kpi-sub">{t["subtitulo"]}</div>'
            f'</div>'
        )
    html = f'<div class="kpi-grid">{"".join(bloques)}</div>'
    st.markdown(html, unsafe_allow_html=True)


def estilizar_tabla_movimientos(df: pd.DataFrame):
    """Aplica formato COP con puntos/comas y colores diferenciados para Ingresos y Gastos."""
    df_vista = df[["id", "fecha", "descripcion", "categoria", "tipo", "valor", "metodo_pago"]].copy()
    df_vista["valor_fmt"] = df_vista.apply(
        lambda r: f"+ {fmt_cop(r['valor'])}" if r["tipo"] == "Ingreso" else f"- {fmt_cop(r['valor'])}",
        axis=1,
    )
    df_vista = df_vista[["id", "fecha", "descripcion", "categoria", "tipo", "valor_fmt", "metodo_pago"]]
    df_vista.columns = ["ID", "Fecha", "Descripción", "Categoría", "Tipo", "Valor (COP)", "Método de pago"]

    def color_tipo(val: str) -> str:
        if val == "Ingreso" or str(val).startswith("+"):
            return "color: #059669; font-weight: 700;"
        if val == "Gasto" or str(val).startswith("-"):
            return "color: #DC2626; font-weight: 700;"
        return ""

    return df_vista.style.map(color_tipo, subset=["Tipo", "Valor (COP)"])


def obtener_plantillas_frecuentes(df_movs: pd.DataFrame, limite: int = 4) -> list[dict]:
    """Detecta los movimientos más frecuentes para registrarlos en 1 clic (estilo Wallet)."""
    if df_movs.empty:
        return []
    agrupado = (
        df_movs.groupby(["descripcion", "categoria", "tipo", "metodo_pago"], as_index=False)
        .agg(conteo=("id", "count"), valor_promedio=("valor", "median"))
        .sort_values(["conteo", "valor_promedio"], ascending=[False, False])
        .head(limite)
    )
    return agrupado.to_dict(orient="records")


def render_formulario_registro(
    df_categorias: pd.DataFrame,
    df_movs: pd.DataFrame,
    key_prefix: str = "dash",
) -> None:
    """Formulario cómodo con soporte de decimales, vista previa COP y plantillas en 1 clic."""
    st.subheader("➕ Registrar nuevo movimiento")

    # Estado inicial del monto en sesión para permitir botones rápidos y plantillas
    state_monto_key = f"{key_prefix}_monto_val"
    state_desc_key = f"{key_prefix}_desc_val"
    state_tipo_key = f"{key_prefix}_tipo_radio"
    state_cat_key = f"{key_prefix}_cat_sel"
    state_met_key = f"{key_prefix}_met_sel"

    if state_monto_key not in st.session_state:
        st.session_state[state_monto_key] = 10000.00
    if state_desc_key not in st.session_state:
        st.session_state[state_desc_key] = ""

    # Plantillas rápidas basadas en historial real (estilo Wallet / Monefy)
    plantillas = obtener_plantillas_frecuentes(df_movs, limite=4)
    if plantillas:
        st.caption("⚡ **Plantillas frecuentes (toca una para rellenar datos):**")
        cols_pl = st.columns(len(plantillas))
        for idx, pl in enumerate(plantillas):
            icono = "🔴" if pl["tipo"] == "Gasto" else "🟢"
            etiqueta = f"{icono} {pl['descripcion'][:18]} ({fmt_cop(pl['valor_promedio'])})"
            if cols_pl[idx].button(etiqueta, key=f"{key_prefix}_pl_{idx}", use_container_width=True):
                st.session_state[state_tipo_key] = pl["tipo"]
                st.session_state[state_monto_key] = float(pl["valor_promedio"])
                st.session_state[state_desc_key] = pl["descripcion"]
                st.session_state[state_cat_key] = pl["categoria"]
                st.session_state[state_met_key] = pl["metodo_pago"]
                st.rerun()

    tipo_seleccionado = st.radio(
        "Tipo de movimiento",
        options=["Gasto", "Ingreso"],
        horizontal=True,
        key=state_tipo_key,
    )

    cats_filtradas = (
        df_categorias.loc[df_categorias["tipo"] == tipo_seleccionado, "nombre"].tolist()
        if not df_categorias.empty
        else []
    )
    if not cats_filtradas:
        cats_filtradas = ["General"]

    # Botones de suma rápida para agilizar captura desde celular/tablet
    st.caption("💵 **Sumar rápido al monto:**")
    b1, b2, b3, b4, b5 = st.columns(5)
    incrementos = [
        ("+$ 5.000", 5000.0),
        ("+$ 10.000", 10000.0),
        ("+$ 20.000", 20000.0),
        ("+$ 50.000", 50000.0),
        ("Limpiar", 0.0),
    ]
    for col_btn, (label_btn, inc_val) in zip([b1, b2, b3, b4, b5], incrementos):
        if col_btn.button(label_btn, key=f"{key_prefix}_inc_{label_btn}", use_container_width=True):
            if inc_val == 0.0:
                st.session_state[state_monto_key] = 0.0
            else:
                st.session_state[state_monto_key] = round(float(st.session_state[state_monto_key]) + inc_val, 2)
            st.rerun()

    col1, col2 = st.columns(2)
    with col1:
        valor = st.number_input(
            "Valor en pesos colombianos (COP — admite decimales)",
            min_value=0.0,
            step=1000.0,
            format="%.2f",
            key=state_monto_key,
        )
        # Vista previa instantánea con puntos de miles y coma decimal
        st.markdown(
            f'<div class="preview-cop-box">👁️ Vista previa legible: <span>{formato_cop(valor, "siempre")} COP</span></div>',
            unsafe_allow_html=True,
        )

        # Asegurar índice válido si cambió de Gasto a Ingreso
        idx_cat = 0
        if state_cat_key in st.session_state and st.session_state[state_cat_key] in cats_filtradas:
            idx_cat = cats_filtradas.index(st.session_state[state_cat_key])
        categoria = st.selectbox("Categoría", options=cats_filtradas, index=idx_cat)

    with col2:
        fecha_mov = st.date_input(
            "Fecha del movimiento",
            value=hoy_colombia(),
            format="YYYY-MM-DD",
            key=f"{key_prefix}_fecha_input",
        )
        idx_met = 0
        if state_met_key in st.session_state and st.session_state[state_met_key] in METODOS_PAGO:
            idx_met = METODOS_PAGO.index(st.session_state[state_met_key])
        metodo_pago = st.selectbox("Método de pago", options=METODOS_PAGO, index=idx_met)

        descripcion = st.text_input(
            "Descripción del movimiento",
            placeholder="Ej: Almuerzo, Pago de nómina, Transporte, Servicios...",
            key=state_desc_key,
        )

    if st.button(
        "💾 Guardar movimiento",
        type="primary",
        use_container_width=True,
        key=f"{key_prefix}_btn_guardar",
    ):
        if not descripcion.strip():
            st.warning("Por favor escribe una descripción para el movimiento.")
        elif valor <= 0:
            st.warning("El valor debe ser mayor que $ 0,00.")
        else:
            exito, mensaje = agregar_movimiento(
                fecha_mov=fecha_mov,
                descripcion=descripcion,
                categoria=categoria,
                tipo=tipo_seleccionado,
                valor=round(float(valor), 2),
                metodo_pago=metodo_pago,
            )
            if exito:
                st.session_state[state_monto_key] = 0.0
                st.session_state[state_desc_key] = ""
                st.toast(f"✅ {mensaje}")
                st.rerun()
            else:
                st.error(mensaje)


# ============================================================================
# VISTAS PRINCIPALES DE LA APLICACIÓN
# ============================================================================

def vista_dashboard(df_movs: pd.DataFrame, df_cats: pd.DataFrame) -> None:
    """Vista 1: Panel de control principal, salud financiera, registro rápido y resumen mensual."""
    hoy = hoy_colombia()

    # Cálculos globales exactos
    total_ingresos = float(df_movs.loc[df_movs["tipo"] == "Ingreso", "valor"].sum()) if not df_movs.empty else 0.0
    total_gastos = float(df_movs.loc[df_movs["tipo"] == "Gasto", "valor"].sum()) if not df_movs.empty else 0.0
    balance_disponible = total_ingresos - total_gastos
    cantidad_movs = len(df_movs)

    # Tarjetas KPI responsivas (PC 4 col / Tablet 2x2 / Celular 1 col)
    render_kpi_grid(
        [
            {
                "titulo": "Total Ingresos",
                "valor": fmt_cop(total_ingresos),
                "subtitulo": "Acumulado histórico",
                "estilo": "ingreso",
            },
            {
                "titulo": "Total Gastos",
                "valor": fmt_cop(total_gastos),
                "subtitulo": "Acumulado histórico",
                "estilo": "gasto",
            },
            {
                "titulo": "Balance Disponible",
                "valor": fmt_cop(balance_disponible),
                "subtitulo": "Ingresos menos gastos",
                "estilo": "balance" if balance_disponible >= 0 else "gasto",
            },
            {
                "titulo": "Movimientos",
                "valor": f"{cantidad_movs:,}".replace(",", "."),
                "subtitulo": "Registros guardados",
                "estilo": "neutro",
            },
        ]
    )

    # Formulario de registro rápido abierto por defecto
    with st.expander("📝 Registrar ingreso o gasto diario", expanded=True):
        render_formulario_registro(df_cats, df_movs, key_prefix="dashboard")

    st.divider()

    # Selector de mes para el resumen financiero mensual y salud financiera
    mes_actual_str = f"{hoy.year}-{hoy.month:02d}"
    meses_disponibles = {mes_actual_str}
    if not df_movs.empty:
        for f in df_movs["fecha"]:
            meses_disponibles.add(f"{f.year}-{f.month:02d}")
    lista_meses = sorted(list(meses_disponibles), reverse=True)

    col_tit, col_sel = st.columns([2, 1])
    with col_tit:
        st.subheader("📅 Resumen Financiero y Salud del Mes")
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

    # Indicadores inteligentes inspirados en Monarch Money / Copilot
    dias_totales_mes = calendar.monthrange(anio_sel, mes_sel)[1]
    dia_referencia = hoy.day if (anio_sel == hoy.year and mes_sel == hoy.month) else dias_totales_mes
    dia_referencia = max(dia_referencia, 1)
    gasto_diario_prom = gastos_mes / dia_referencia
    proyeccion_cierre = gasto_diario_prom * dias_totales_mes
    tasa_ahorro = ((ingresos_mes - gastos_mes) / ingresos_mes * 100) if ingresos_mes > 0 else 0.0

    m1, m2, m3 = st.columns(3)
    m1.metric("Ingresos del mes", fmt_cop(ingresos_mes))
    m2.metric("Gastos del mes", fmt_cop(gastos_mes))
    m3.metric(
        "Balance del mes",
        fmt_cop(balance_mes),
        delta=f"Tasa de ahorro: {tasa_ahorro:.1f}%".replace(".", ",") if ingresos_mes > 0 else None,
    )

    s1, s2, s3 = st.columns(3)
    s1.metric("Gasto diario promedio", fmt_cop(gasto_diario_prom))
    s2.metric("Proyección gasto fin de mes", fmt_cop(proyeccion_cierre))
    estado_salud = (
        "🟢 Excelente ahorro" if tasa_ahorro >= 20
        else ("🟡 Ahorro moderado" if tasa_ahorro > 0 else "🔴 Gasto supera ingreso")
    )
    s3.metric("Diagnóstico del mes", estado_salud if (ingresos_mes > 0 or gastos_mes > 0) else "⚪ Sin movimientos")

    # Indicador de Presupuesto Mensual General
    df_pres_mes = obtener_presupuestos(mes_elegido)
    pres_general = df_pres_mes[df_pres_mes["categoria"] == "General"] if not df_pres_mes.empty else pd.DataFrame()
    if not pres_general.empty:
        limite_general = float(pres_general.iloc[0]["monto_limite"])
        disponible_pres = limite_general - gastos_mes
        porcentaje = (gastos_mes / limite_general) if limite_general > 0 else 0.0

        st.markdown(f"**🎯 Presupuesto mensual ({nombre_mes_anio(mes_elegido)}):**")
        p1, p2, p3 = st.columns(3)
        p1.metric("Presupuesto asignado", fmt_cop(limite_general))
        p2.metric("Gastado en el mes", fmt_cop(gastos_mes))
        p3.metric("Disponible del presupuesto", fmt_cop(disponible_pres))

        st.progress(min(porcentaje, 1.0))
        if disponible_pres < 0:
            st.error(f"⚠️ Has excedido tu presupuesto mensual por {fmt_cop(abs(disponible_pres))}.")
        elif porcentaje >= 0.8:
            st.warning(f"⚡ Has consumido el {porcentaje * 100:.1f}% de tu presupuesto mensual.")
        else:
            st.info(f"✅ Te queda el {(1 - porcentaje) * 100:.1f}% disponible de tu presupuesto.")

    st.divider()

    # Gráficos de Ingresos frente a Gastos
    col_g1, col_g2 = st.columns(2)

    with col_g1:
        st.subheader("📊 Ingresos vs Gastos (Mes)")
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
            text=df_comp_mes["Valor"].apply(fmt_cop),
            color_discrete_map={"Ingresos": "#10B981", "Gastos": "#EF4444"},
        )
        fig_bar.update_traces(textposition="outside", textfont_size=14)
        fig_bar.update_layout(
            showlegend=False,
            yaxis_title="Monto (COP)",
            xaxis_title="",
            font=dict(size=15),
            height=380,
            margin=dict(t=35, b=20, l=20, r=20),
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
            fig_pie.update_traces(textinfo="percent+label", textfont_size=15)
            fig_pie.update_layout(
                font=dict(size=15),
                height=380,
                margin=dict(t=35, b=20, l=20, r=20),
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
    """Vista 2: Tabla completa con filtros rápidos, búsqueda, edición, eliminación y exportación."""
    st.title("📋 Historial y Gestión de Movimientos")

    if df_movs.empty:
        st.info("Aún no tienes movimientos registrados en la base de datos.")
        return

    hoy = hoy_colombia()
    fecha_min = df_movs["fecha"].min()
    fecha_max = df_movs["fecha"].max()

    # Filtros rápidos de período en 1 clic (estilo Fintonic / Mobills)
    st.caption("⏱️ **Filtro rápido de período:**")
    qp1, qp2, qp3, qp4, qp5 = st.columns(5)
    if "hist_desde" not in st.session_state:
        st.session_state["hist_desde"] = fecha_min
    if "hist_hasta" not in st.session_state:
        st.session_state["hist_hasta"] = fecha_max

    if qp1.button("Hoy", use_container_width=True):
        st.session_state["hist_desde"] = max(hoy, fecha_min)
        st.session_state["hist_hasta"] = min(hoy, fecha_max)
    if qp2.button("Últimos 7 días", use_container_width=True):
        st.session_state["hist_desde"] = max(hoy - timedelta(days=7), fecha_min)
        st.session_state["hist_hasta"] = fecha_max
    if qp3.button("Este mes", use_container_width=True):
        inicio_mes = hoy.replace(day=1)
        st.session_state["hist_desde"] = max(inicio_mes, fecha_min)
        st.session_state["hist_hasta"] = fecha_max
    if qp4.button("Últimos 30 días", use_container_width=True):
        st.session_state["hist_desde"] = max(hoy - timedelta(days=30), fecha_min)
        st.session_state["hist_hasta"] = fecha_max
    if qp5.button("Todo el historial", use_container_width=True):
        st.session_state["hist_desde"] = fecha_min
        st.session_state["hist_hasta"] = fecha_max

    # Barra de búsqueda y filtros detallados
    with st.expander("🔍 Búsqueda y filtros detallados", expanded=True):
        f1, f2, f3 = st.columns(3)
        with f1:
            val_desde = min(max(st.session_state["hist_desde"], fecha_min), fecha_max)
            fecha_desde = st.date_input("Desde", value=val_desde, min_value=fecha_min, max_value=fecha_max)
        with f2:
            val_hasta = min(max(st.session_state["hist_hasta"], fecha_min), fecha_max)
            fecha_hasta = st.date_input("Hasta", value=val_hasta, min_value=fecha_min, max_value=fecha_max)
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
    r2.metric("Ingresos filtrados", fmt_cop(ing_filt))
    r3.metric("Gastos filtrados", fmt_cop(gas_filt))
    r4.metric("Balance filtrado", fmt_cop(bal_filt))

    # Botones de exportación a Excel y CSV
    col_exp1, col_exp2, _ = st.columns([1, 1, 2])
    with col_exp1:
        st.download_button(
            label="📥 Exportar a Excel (.xlsx)",
            data=exportar_excel(df_filtrado),
            file_name=f"movimientos_financieros_{hoy.isoformat()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    with col_exp2:
        st.download_button(
            label="📄 Exportar a CSV (.csv)",
            data=exportar_csv(df_filtrado),
            file_name=f"movimientos_financieros_{hoy.isoformat()}.csv",
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
            f"{row['descripcion']} ({fmt_cop(row['valor'])})"
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

        ec1, ec2 = st.columns(2)
        with ec1:
            nuevo_valor = st.number_input(
                "Valor (COP — admite decimales)",
                min_value=0.01,
                step=1000.0,
                value=float(registro["valor"]),
                format="%.2f",
                key=f"edit_val_{id_seleccionado}",
            )
            st.markdown(
                f'<div class="preview-cop-box">👁️ Vista previa: <span>{formato_cop(nuevo_valor, "siempre")} COP</span></div>',
                unsafe_allow_html=True,
            )
            nueva_cat = st.selectbox(
                "Categoría",
                options=cats_tipo,
                index=cats_tipo.index(registro["categoria"]),
                key=f"edit_cat_{id_seleccionado}",
            )
        with ec2:
            nueva_fecha = st.date_input("Fecha", value=registro["fecha"], key=f"edit_fecha_{id_seleccionado}")
            idx_metodo = (
                METODOS_PAGO.index(registro["metodo_pago"])
                if registro["metodo_pago"] in METODOS_PAGO
                else 0
            )
            nuevo_metodo = st.selectbox(
                "Método de pago",
                options=METODOS_PAGO,
                index=idx_metodo,
                key=f"edit_met_{id_seleccionado}",
            )
            nueva_desc = st.text_input(
                "Descripción",
                value=registro["descripcion"],
                key=f"edit_desc_{id_seleccionado}",
            )

        if st.button(
            "💾 Guardar cambios",
            type="primary",
            use_container_width=True,
            key=f"btn_save_edit_{id_seleccionado}",
        ):
            if not nueva_desc.strip():
                st.warning("La descripción no puede quedar vacía.")
            else:
                ok, msg = actualizar_movimiento(
                    mov_id=id_seleccionado,
                    fecha_mov=nueva_fecha,
                    descripcion=nueva_desc,
                    categoria=nueva_cat,
                    tipo=nuevo_tipo,
                    valor=round(float(nuevo_valor), 2),
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
            f"**{registro['descripcion']}** por **{fmt_cop(registro['valor'])}**."
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
    """Vista 3: Análisis estadístico diario, semanal, mensual, anual, por método de pago y balance."""
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
            line=dict(color="#2563EB", width=3.5),
            marker=dict(size=8),
            fill="tozeroy",
            fillcolor="rgba(37, 99, 235, 0.12)",
        )
    )
    fig_evolucion.update_layout(
        xaxis_title="Fecha",
        yaxis_title="Balance (COP)",
        hovermode="x unified",
        font=dict(size=15),
        height=390,
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
                text=gastos_cat["valor"].apply(fmt_cop),
                color="valor",
                color_continuous_scale="Reds",
            )
            fig_cat.update_layout(
                yaxis=dict(autorange="reversed", title=""),
                xaxis_title="Total Gastado (COP)",
                coloraxis_showscale=False,
                font=dict(size=15),
                height=390,
                margin=dict(t=20, b=20, l=20, r=40),
            )
            fig_cat.update_traces(textposition="outside", textfont_size=14)
            st.plotly_chart(fig_cat, use_container_width=True)

        with cg2:
            tabla_cat = gastos_cat.copy()
            tabla_cat["Total (COP)"] = tabla_cat["valor"].apply(fmt_cop)
            tabla_cat["Participación"] = tabla_cat["Porcentaje"].apply(lambda p: f"{p:.1f}%".replace(".", ","))
            st.dataframe(
                tabla_cat[["categoria", "Total (COP)", "Participación"]].rename(
                    columns={"categoria": "Categoría"}
                ),
                use_container_width=True,
                hide_index=True,
            )

    st.divider()

    # 3. Análisis por Método de Pago (estilo Spendee / Wallet)
    st.subheader("💳 Movimientos por Método de Pago")
    met_pivot = (
        df_periodo.pivot_table(
            index="metodo_pago",
            columns="tipo",
            values="valor",
            aggfunc="sum",
            fill_value=0.0,
        )
        .reset_index()
    )
    for col in ["Ingreso", "Gasto"]:
        if col not in met_pivot.columns:
            met_pivot[col] = 0.0
    met_pivot["Balance"] = met_pivot["Ingreso"] - met_pivot["Gasto"]

    cm1, cm2 = st.columns(2)
    with cm1:
        fig_met = px.pie(
            met_pivot,
            names="metodo_pago",
            values="Gasto",
            hole=0.48,
            title="Distribución de Gastos por Método de Pago",
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig_met.update_traces(textinfo="percent+label", textfont_size=14)
        fig_met.update_layout(font=dict(size=15), height=360)
        st.plotly_chart(fig_met, use_container_width=True)

    with cm2:
        tabla_met = met_pivot.copy()
        for c in ["Ingreso", "Gasto", "Balance"]:
            tabla_met[c] = tabla_met[c].apply(fmt_cop)
        tabla_met.columns = ["Método de Pago", "Ingresos", "Gastos", "Balance Neto"]
        st.dataframe(tabla_met, use_container_width=True, hide_index=True)

    st.divider()

    # 4. Pestañas de Resúmenes Temporales (Diario, Semanal, Mensual, Anual)
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
        fig_d.update_layout(xaxis_title="Fecha", yaxis_title="Monto (COP)", font=dict(size=15), height=380)
        st.plotly_chart(fig_d, use_container_width=True)

        tabla_d = diario_pivot[["fecha", "Ingreso", "Gasto", "Neto_Dia"]].sort_values("fecha", ascending=False).copy()
        for col in ["Ingreso", "Gasto", "Neto_Dia"]:
            tabla_d[col] = tabla_d[col].apply(fmt_cop)
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
        fig_s.update_layout(xaxis_title="Semana", yaxis_title="Monto (COP)", font=dict(size=15), height=380)
        st.plotly_chart(fig_s, use_container_width=True)

        tabla_s = sem_pivot.sort_values("Semana", ascending=False).copy()
        for col in ["Ingreso", "Gasto", "Balance"]:
            tabla_s[col] = tabla_s[col].apply(fmt_cop)
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
        fig_m.update_layout(xaxis_title="Mes", yaxis_title="Monto (COP)", font=dict(size=15), height=380)
        st.plotly_chart(fig_m, use_container_width=True)

        tabla_m = mes_pivot.sort_values("Mes", ascending=False).copy()
        tabla_m["Mes"] = tabla_m["Mes"].apply(nombre_mes_anio)
        for col in ["Ingreso", "Gasto", "Balance"]:
            tabla_m[col] = tabla_m[col].apply(fmt_cop)
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
        fig_a.update_layout(xaxis_title="Año", yaxis_title="Monto (COP)", font=dict(size=15), height=380)
        st.plotly_chart(fig_a, use_container_width=True)

        tabla_a = an_pivot.sort_values("Año", ascending=False).copy()
        for col in ["Ingreso", "Gasto", "Balance"]:
            tabla_a[col] = tabla_a[col].apply(fmt_cop)
        tabla_a.columns = ["Año", "Ingresos", "Gastos", "Balance Anual"]
        st.dataframe(tabla_a, use_container_width=True, hide_index=True)


def vista_presupuestos_categorias(df_movs: pd.DataFrame, df_cats: pd.DataFrame) -> None:
    """Vista 4: Presupuestos mensuales, Metas de Ahorro (Alcancías), Categorías y Respaldos."""
    st.title("⚙️ Presupuestos, Metas y Categorías")

    tab_pres, tab_metas, tab_cats, tab_backup = st.tabs(
        [
            "🎯 Presupuestos Mensuales",
            "🏆 Metas de Ahorro",
            "🏷️ Categorías Personalizadas",
            "💾 Copia de Seguridad",
        ]
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
                min_value=0.0,
                step=50000.0,
                value=1000000.0,
                format="%.2f",
            )
            st.caption(f"Vista previa: **{formato_cop(monto_pres, 'siempre')}**")

        if st.button("💾 Guardar presupuesto", type="primary", use_container_width=True):
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
                        f"**{cat_p}** — Límite: `{fmt_cop(limite_p)}` | "
                        f"Gastado: `{fmt_cop(gastado_p)}` | "
                        f"Disponible: **`{fmt_cop(restante_p)}`**"
                    )
                    st.progress(min(ratio_p, 1.0))
                with col_del:
                    if st.button("🗑️", key=f"del_pres_{int(row_p['id'])}", help="Eliminar presupuesto"):
                        ok, msg = eliminar_presupuesto(int(row_p["id"]))
                        if ok:
                            st.toast(msg)
                            st.rerun()

    # ------------------------------------------------------------------------
    # TAB 2: METAS DE AHORRO (ALCANCÍAS VIRTUALES - ESTILO NUBANK / SIMPLIFI)
    # ------------------------------------------------------------------------
    with tab_metas:
        st.subheader("🏆 Crear nueva meta de ahorro")
        st.caption("Organiza tus objetivos financieros (ej. Fondo de emergencia, Moto, Viaje, Computador).")

        cm1, cm2, cm3 = st.columns(3)
        with cm1:
            nombre_meta = st.text_input("Nombre de la meta", placeholder="Ej: Fondo de emergencia")
        with cm2:
            objetivo_meta = st.number_input(
                "Monto objetivo (COP)",
                min_value=1000.0,
                step=50000.0,
                value=1000000.0,
                format="%.2f",
            )
            st.caption(f"Objetivo: **{formato_cop(objetivo_meta, 'siempre')}**")
        with cm3:
            ahorro_inicial = st.number_input(
                "Ahorro inicial (COP)",
                min_value=0.0,
                step=10000.0,
                value=0.0,
                format="%.2f",
            )
            st.caption(f"Inicial: **{formato_cop(ahorro_inicial, 'siempre')}**")

        if st.button("➕ Crear meta de ahorro", type="primary", use_container_width=True):
            ok, msg = guardar_meta_ahorro(nombre_meta, objetivo_meta, ahorro_inicial)
            if ok:
                st.toast(f"✅ {msg}")
                st.rerun()
            else:
                st.warning(msg)

        st.divider()
        st.subheader("📈 Progreso de tus metas")
        df_metas = obtener_metas_ahorro()
        if df_metas.empty:
            st.info("Aún no has creado ninguna meta de ahorro.")
        else:
            for _, row_m in df_metas.iterrows():
                m_id = int(row_m["id"])
                m_nombre = row_m["nombre_meta"]
                m_actual = float(row_m["monto_actual"])
                m_obj = float(row_m["monto_objetivo"])
                faltante = max(m_obj - m_actual, 0.0)
                pct = (m_actual / m_obj) if m_obj > 0 else 0.0

                st.markdown(
                    f"### 🎯 {m_nombre} ({pct * 100:.1f}%)\n"
                    f"Ahorrado: **`{fmt_cop(m_actual)}`** de **`{fmt_cop(m_obj)}`** · "
                    f"Falta: **`{fmt_cop(faltante)}`**"
                )
                st.progress(min(pct, 1.0))

                ab1, ab2, ab3 = st.columns([2, 1, 1])
                with ab1:
                    abono = st.number_input(
                        f"Monto a abonar o retirar ({m_nombre})",
                        min_value=0.0,
                        step=10000.0,
                        value=50000.0,
                        format="%.2f",
                        key=f"abono_input_{m_id}",
                    )
                with ab2:
                    if st.button("➕ Abonar", key=f"btn_abonar_{m_id}", use_container_width=True):
                        ok, msg = guardar_meta_ahorro(m_nombre, m_obj, m_actual + abono, meta_id=m_id)
                        if ok:
                            st.toast(f"✅ Abonado {fmt_cop(abono)} a {m_nombre}")
                            st.rerun()
                with ab3:
                    if st.button("🗑️ Eliminar", key=f"btn_del_meta_{m_id}", use_container_width=True):
                        ok, msg = eliminar_presupuesto(m_id)
                        if ok:
                            st.toast(msg)
                            st.rerun()
                st.divider()

    # ------------------------------------------------------------------------
    # TAB 3: CATEGORÍAS PERSONALIZADAS
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
    # TAB 4: COPIA DE SEGURIDAD COMPLETA
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
# PUNTO DE ENTRADA, ENCABEZADO VISUAL Y NAVEGACIÓN MULTI-DISPOSITIVO
# ============================================================================

def main() -> None:
    if "modo_decimales" not in st.session_state:
        st.session_state["modo_decimales"] = "auto"

    # Barra lateral con configuración de visualización
    with st.sidebar:
        if os.path.exists(LOGO_PATH):
            st.image(LOGO_PATH, width=85)
        st.markdown("## Finanzas COP")
        st.caption("Control financiero personal")

        st.divider()
        st.markdown("### 🔢 Formato de decimales")
        opciones_fmt = {
            "auto": "Automático ($ 1.500,50 o $ 1.500)",
            "siempre": "Siempre 2 decimales ($ 1.500,00)",
            "entero": "Sin decimales ($ 1.500)",
        }
        st.session_state["modo_decimales"] = st.selectbox(
            "Visualización de números",
            options=list(opciones_fmt.keys()),
            format_func=lambda k: opciones_fmt[k],
            index=list(opciones_fmt.keys()).index(st.session_state["modo_decimales"]),
        )
        st.divider()
        st.caption("☁️ Sincronizado con Supabase")

    # Encabezado moderno con logotipo y fecha
    col_logo, col_head, col_fmt = st.columns([1, 6, 3])
    with col_logo:
        if os.path.exists(LOGO_PATH):
            st.image(LOGO_PATH, width=72)
    with col_head:
        st.title("Control Financiero Personal")
        st.caption(f"Pesos Colombianos (COP) · Hoy: {hoy_colombia().strftime('%d/%m/%Y')}")
    with col_fmt:
        opciones_rapidas_fmt = {
            "auto": "Decimales: Auto (,00)",
            "siempre": "Decimales: Siempre (,00)",
            "entero": "Decimales: Entero",
        }
        st.session_state["modo_decimales"] = st.selectbox(
            "Formato numérico",
            options=list(opciones_rapidas_fmt.keys()),
            format_func=lambda k: opciones_rapidas_fmt[k],
            index=list(opciones_rapidas_fmt.keys()).index(st.session_state["modo_decimales"]),
            label_visibility="collapsed",
        )

    # Navegación superior táctil (funciona perfecto en Celular, Tablet y PC sin abrir sidebar)
    secciones = [
        "📊 Dashboard",
        "📋 Historial",
        "📈 Estadísticas",
        "⚙️ Presupuestos y Metas",
    ]
    seccion = st.radio(
        "Sección",
        options=secciones,
        horizontal=True,
        label_visibility="collapsed",
    )

    st.divider()

    df_movs = obtener_movimientos()
    df_cats = obtener_categorias()

    if seccion == "📊 Dashboard":
        vista_dashboard(df_movs, df_cats)
    elif seccion == "📋 Historial":
        vista_historial_gestion(df_movs, df_cats)
    elif seccion == "📈 Estadísticas":
        vista_estadisticas(df_movs)
    elif seccion == "⚙️ Presupuestos y Metas":
        vista_presupuestos_categorias(df_movs, df_cats)


if __name__ == "__main__":
    main()
