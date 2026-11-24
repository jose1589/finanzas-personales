import io
from datetime import date, datetime
from zoneinfo import ZoneInfo
import pandas as pd

ZONA_HORARIA_COLOMBIA = ZoneInfo("America/Bogota")

MESES_ES = {
    1: "Enero",
    2: "Febrero",
    3: "Marzo",
    4: "Abril",
    5: "Mayo",
    6: "Junio",
    7: "Julio",
    8: "Agosto",
    9: "Septiembre",
    10: "Octubre",
    11: "Noviembre",
    12: "Diciembre",
}


def hoy_colombia() -> date:
    """Retorna la fecha actual exacta en Colombia (UTC-5)."""
    return datetime.now(ZONA_HORARIA_COLOMBIA).date()


def formato_cop(valor: float | int | None) -> str:
    """Formatea un valor numérico en Pesos Colombianos legibles ($ 1.250.000)."""
    if valor is None or pd.isna(valor):
        return "$ 0"
    negativo = float(valor) < 0
    valor_redondeado = abs(round(float(valor)))
    texto_miles = f"{valor_redondeado:,}".replace(",", ".")
    return f"- $ {texto_miles}" if negativo else f"$ {texto_miles}"


def nombre_mes_anio(mes_anio: str) -> str:
    """Convierte 'YYYY-MM' a 'Noviembre 2026'."""
    try:
        anio_str, mes_str = mes_anio.split("-")
        nombre_mes = MESES_ES.get(int(mes_str), mes_str)
        return f"{nombre_mes} {anio_str}"
    except Exception:
        return mes_anio


def exportar_csv(df: pd.DataFrame) -> bytes:
    """Convierte un DataFrame a bytes CSV codificado en UTF-8 con BOM para Excel."""
    df_export = preparar_df_exportacion(df)
    return df_export.to_csv(index=False, sep=";").encode("utf-8-sig")


def exportar_excel(df: pd.DataFrame) -> bytes:
    """Convierte un DataFrame a archivo Excel (.xlsx) en memoria con formato limpio."""
    df_export = preparar_df_exportacion(df)
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_export.to_excel(writer, index=False, sheet_name="Movimientos")
        hoja = writer.sheets["Movimientos"]
        for col_idx, col_name in enumerate(df_export.columns, start=1):
            max_len = max(
                df_export[col_name].astype(str).map(len).max() if not df_export.empty else 10,
                len(str(col_name)),
            )
            col_letter = hoja.cell(row=1, column=col_idx).column_letter
            hoja.column_dimensions[col_letter].width = min(max_len + 4, 45)
    return buffer.getvalue()


def preparar_df_exportacion(df: pd.DataFrame) -> pd.DataFrame:
    """Estandariza columnas y nombres en español para exportación."""
    if df.empty:
        return pd.DataFrame(
            columns=["ID", "Fecha", "Descripción", "Categoría", "Tipo", "Valor (COP)", "Método de Pago"]
        )
    columnas = {
        "id": "ID",
        "fecha": "Fecha",
        "descripcion": "Descripción",
        "categoria": "Categoría",
        "tipo": "Tipo",
        "valor": "Valor (COP)",
        "metodo_pago": "Método de Pago",
    }
    cols_disponibles = [c for c in columnas if c in df.columns]
    df_limpio = df[cols_disponibles].copy()
    df_limpio.rename(columns=columnas, inplace=True)
    return df_limpio
