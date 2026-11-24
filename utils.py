import io
import re
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


def formato_cop(valor: float | int | None, modo_decimales: str = "auto") -> str:
    """
    Formatea un valor numérico en Pesos Colombianos con puntos para miles
    y coma para decimales (ej. $ 1.250.500,75).

    modo_decimales:
      - "auto": muestra 2 decimales con coma si tiene centavos; entero si es exacto.
      - "siempre": siempre muestra 2 decimales con coma (ej. $ 1.250.000,00).
      - "entero": redondea al peso más cercano sin decimales (ej. $ 1.250.000).
    """
    if valor is None or pd.isna(valor):
        return "$ 0,00" if modo_decimales == "siempre" else "$ 0"

    num = float(valor)
    negativo = num < 0
    num_abs = abs(num)

    if modo_decimales == "entero":
        entero = round(num_abs)
        parte_ent = f"{entero:,}".replace(",", ".")
        resultado = f"$ {parte_ent}"
    else:
        redondeado = round(num_abs, 2)
        entero = int(redondeado)
        centavos = int(round((redondeado - entero) * 100))
        if centavos == 100:
            entero += 1
            centavos = 0

        parte_ent = f"{entero:,}".replace(",", ".")
        if modo_decimales == "siempre" or centavos > 0:
            resultado = f"$ {parte_ent},{centavos:02d}"
        else:
            resultado = f"$ {parte_ent}"

    return f"- {resultado}" if negativo else resultado


def parsear_monto_cop(texto: str) -> float:
    """
    Convierte una cadena ingresada con puntos o comas (ej. '1.250.500,50' o '1250500.50')
    en un float válido. Retorna 0.0 si no es válido.
    """
    if not texto:
        return 0.0
    limpio = re.sub(r"[^0-9,.-]", "", str(texto).strip())
    if not limpio:
        return 0.0

    # Si tiene ambos separadores: el último suele ser el decimal
    if "," in limpio and "." in limpio:
        if limpio.rfind(",") > limpio.rfind("."):
            limpio = limpio.replace(".", "").replace(",", ".")
        else:
            limpio = limpio.replace(",", "")
    elif "," in limpio:
        # Si hay una sola coma con 1 o 2 dígitos al final, es decimal
        partes = limpio.split(",")
        if len(partes) == 2 and len(partes[1]) <= 2:
            limpio = limpio.replace(",", ".")
        else:
            limpio = limpio.replace(",", "")
    elif "." in limpio:
        partes = limpio.split(".")
        # Si hay múltiples puntos (ej. 1.500.000) o 3 dígitos tras el punto, son miles
        if len(partes) > 2 or (len(partes) == 2 and len(partes[1]) == 3):
            limpio = limpio.replace(".", "")

    try:
        return round(float(limpio), 2)
    except ValueError:
        return 0.0


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
    return df_export.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")


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
