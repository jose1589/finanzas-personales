"""Vista 🏦 Extractos Bancarios: sube un extracto, revisa la clasificación e importa en lote."""

import pandas as pd
import plotly.express as px
import streamlit as st

from database import agregar_movimientos_lote
from utils import METODOS_PAGO, exportar_csv, exportar_excel, formato_cop, hoy_colombia, leer_extracto


@st.cache_data(show_spinner="Leyendo el extracto...")
def _leer_extracto_cacheado(contenido: bytes, nombre: str, modo_sin_signo: str):
    """Cachea la lectura para que cambiar una celda de la tabla no vuelva a leer el archivo."""
    return leer_extracto(contenido, nombre, modo_sin_signo)


OPCIONES_MODO = {
    "signo": "Con «-» es gasto; cualquier otro monto es ingreso (recomendado)",
    "palabras": "Clasificar por palabras clave de la descripción",
}


def _fmt(valor: float) -> str:
    return formato_cop(valor, modo_decimales=st.session_state.get("modo_decimales", "auto"))


def _marcar_duplicados(df: pd.DataFrame, df_movs: pd.DataFrame) -> pd.DataFrame:
    """Marca movimientos que ya existen en Supabase (misma fecha, valor y tipo)."""
    existentes = set()
    if not df_movs.empty:
        existentes = {
            (f, round(float(v), 2), t)
            for f, v, t in zip(df_movs["fecha"], df_movs["valor"], df_movs["tipo"])
        }
    df = df.copy()
    df["posible_duplicado"] = [
        (f, round(float(v), 2), t) in existentes
        for f, v, t in zip(df["fecha"], df["valor"], df["tipo"])
    ]
    return df


def vista_extractos(df_movs: pd.DataFrame, df_cats: pd.DataFrame) -> None:
    st.title("🏦 Extractos Bancarios")
    st.caption(
        "Sube el extracto de tu banco en PDF, Excel o CSV. Revisa la clasificación "
        "antes de importar: ningún movimiento se guarda hasta que tú lo confirmes."
    )

    modo = st.radio(
        "Cómo clasificar los montos del extracto",
        options=list(OPCIONES_MODO.keys()),
        format_func=lambda k: OPCIONES_MODO[k],
        key="modo_sin_signo",
        help="Aplica a los extractos con una sola columna de valor (sin columnas Débito/Crédito).",
    )

    archivo = st.file_uploader(
        "Selecciona el extracto",
        type=["pdf", "xlsx", "xls", "csv"],
        key="uploader_extracto",
    )

    if archivo is None:
        st.info("Aún no has subido ningún extracto.")
        with st.expander("ℹ️ ¿Cómo funciona?", expanded=False):
            st.markdown(
                "- **PDF:** se leen las tablas del documento. Si no hay tablas, se leen sus líneas de texto. "
                "Los PDF escaneados (imágenes) no son compatibles.\n"
                "- **Excel o CSV:** se detecta la fila de títulos (Fecha, Descripción, Valor o Débito/Crédito).\n"
                "- **Clasificación:** por signo (negativo = gasto), por columnas Débito/Crédito, o por palabras "
                "clave como *abono*, *nómina* o *pago*.\n"
                "- Los movimientos que ya existen en tu historial (misma fecha, valor y tipo) llegan **desmarcados**."
            )
        return

    firma = f"{archivo.name}-{archivo.size}"
    if st.session_state.get("extracto_importado") == firma:
        st.success("Este extracto ya se importó en esta sesión. Sube otro archivo para continuar.")
        return

    try:
        df_leido, avisos = _leer_extracto_cacheado(archivo.getvalue(), archivo.name, modo)
    except Exception as exc:
        st.error(f"No pude leer el extracto: {exc}")
        return

    for aviso in avisos:
        st.info(aviso)

    df = _marcar_duplicados(df_leido, df_movs)
    duplicados = int(df["posible_duplicado"].sum())
    if duplicados:
        st.warning(
            f"⚠️ {duplicados} movimiento(s) ya existen en tu historial. "
            "Quedaron desmarcados para no duplicarlos."
        )

    # ---------------- Tabla editable de revisión ----------------
    tabla = pd.DataFrame(
        {
            "Importar": ~df["posible_duplicado"],
            "Fecha": df["fecha"],
            "Descripción": df["descripcion"],
            "Tipo": df["tipo"],
            "Categoría": df["categoria"],
            "Valor (COP)": df["valor"].astype(float),
            "Método de pago": df["metodo_pago"],
            "Duplicado": df["posible_duplicado"].map({True: "⚠️ Ya existe", False: ""}),
        }
    )

    opciones_cat = set(df["categoria"])
    if not df_cats.empty:
        opciones_cat |= set(df_cats["nombre"].astype(str))
    opciones_cat = sorted(opciones_cat)

    st.subheader("✏️ Revisa y corrige antes de importar")
    st.caption("Desmarca lo que no quieras guardar, o cambia el tipo, la categoría o el método de cada fila.")
    editado = st.data_editor(
        tabla,
        key=f"editor_{firma}",
        hide_index=True,
        use_container_width=True,
        num_rows="fixed",
        disabled=["Duplicado"],
        column_config={
            "Importar": st.column_config.CheckboxColumn("Importar", default=True),
            "Fecha": st.column_config.DateColumn("Fecha", format="YYYY-MM-DD"),
            "Descripción": st.column_config.TextColumn("Descripción", width="large"),
            "Tipo": st.column_config.SelectboxColumn("Tipo", options=["Ingreso", "Gasto"], required=True),
            "Categoría": st.column_config.SelectboxColumn("Categoría", options=opciones_cat, required=True),
            "Valor (COP)": st.column_config.NumberColumn("Valor (COP)", min_value=0.01, format="%.2f"),
            "Método de pago": st.column_config.SelectboxColumn("Método de pago", options=METODOS_PAGO),
        },
    )

    seleccion = editado[editado["Importar"] == True].reset_index(drop=True)  # noqa: E712

    # ---------------- Resumen del extracto seleccionado ----------------
    total_ing = float(seleccion.loc[seleccion["Tipo"] == "Ingreso", "Valor (COP)"].sum())
    total_gas = float(seleccion.loc[seleccion["Tipo"] == "Gasto", "Valor (COP)"].sum())
    balance = total_ing - total_gas

    st.subheader("📊 Resumen del extracto (seleccionado)")
    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Total Ingresos del extracto", _fmt(total_ing))
    r2.metric("Total Gastos del extracto", _fmt(total_gas))
    r3.metric("Balance neto del extracto", _fmt(balance))
    r4.metric("Movimientos seleccionados", f"{len(seleccion)} de {len(editado)}")

    if seleccion.empty:
        st.info("No hay movimientos seleccionados para importar.")
    else:
        gastos_cat = (
            seleccion[seleccion["Tipo"] == "Gasto"]
            .groupby("Categoría", as_index=False)["Valor (COP)"]
            .sum()
            .sort_values("Valor (COP)", ascending=False)
        )
        col_g, col_t = st.columns([3, 2])
        with col_g:
            if gastos_cat.empty:
                st.info("No hay gastos seleccionados en este extracto.")
            else:
                fig = px.bar(
                    gastos_cat,
                    x="Valor (COP)",
                    y="Categoría",
                    orientation="h",
                    text=gastos_cat["Valor (COP)"].apply(_fmt),
                    color_discrete_sequence=["#EF4444"],
                )
                fig.update_traces(textposition="outside", textfont_size=13)
                fig.update_layout(
                    yaxis=dict(autorange="reversed", title=""),
                    xaxis_title="Gasto (COP)",
                    font=dict(size=14),
                    height=max(260, 46 * len(gastos_cat)),
                    margin=dict(t=10, b=10, l=10, r=40),
                )
                st.plotly_chart(fig, use_container_width=True)
        with col_t:
            desglose = seleccion.groupby(["Tipo", "Categoría"], as_index=False)["Valor (COP)"].sum()
            desglose["Total"] = desglose["Valor (COP)"].apply(_fmt)
            st.dataframe(
                desglose[["Tipo", "Categoría", "Total"]],
                use_container_width=True,
                hide_index=True,
            )

    # ---------------- Exportar análisis ----------------
    export = pd.DataFrame(
        {
            "id": range(1, len(seleccion) + 1),
            "fecha": seleccion["Fecha"],
            "descripcion": seleccion["Descripción"],
            "categoria": seleccion["Categoría"],
            "tipo": seleccion["Tipo"],
            "valor": seleccion["Valor (COP)"],
            "metodo_pago": seleccion["Método de pago"],
        }
    )
    hoy = hoy_colombia().isoformat()
    c1, c2, _ = st.columns([1, 1, 2])
    with c1:
        st.download_button(
            "📥 Exportar análisis a Excel (.xlsx)",
            data=exportar_excel(export),
            file_name=f"analisis_extracto_{hoy}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            disabled=seleccion.empty,
        )
    with c2:
        st.download_button(
            "📄 Exportar análisis a CSV (.csv)",
            data=exportar_csv(export),
            file_name=f"analisis_extracto_{hoy}.csv",
            mime="text/csv",
            use_container_width=True,
            disabled=seleccion.empty,
        )

    # ---------------- Importación en lote ----------------
    if st.button(
        f"💾 Importar {len(seleccion)} movimiento(s) a Supabase",
        type="primary",
        use_container_width=True,
        disabled=seleccion.empty,
        key="btn_importar_extracto",
    ):
        registros = [
            {
                "fecha": pd.to_datetime(fila["Fecha"]).date(),
                "descripcion": fila["Descripción"],
                "categoria": fila["Categoría"],
                "tipo": fila["Tipo"],
                "valor": round(float(fila["Valor (COP)"]), 2),
                "metodo_pago": fila["Método de pago"],
            }
            for _, fila in seleccion.iterrows()
        ]
        ok, mensaje = agregar_movimientos_lote(registros)
        if ok:
            st.session_state["extracto_importado"] = firma
            st.toast(f"✅ {mensaje}")
            st.rerun()
        else:
            st.error(mensaje)
