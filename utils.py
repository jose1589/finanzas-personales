import csv
import io
import re
import unicodedata
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pandas as pd

ZONA_HORARIA_COLOMBIA = ZoneInfo("America/Bogota")

METODOS_PAGO = ["Efectivo", "Transferencia", "Tarjeta", "Otro"]

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


# ============================================================================
# LECTURA DE EXTRACTOS BANCARIOS (PDF, XLSX, XLS, CSV)
# ============================================================================

# Palabras que indican INGRESO cuando el extracto no trae signo ni columna de crédito.
# Si ninguna aparece, el movimiento se clasifica como GASTO.
PALABRAS_INGRESO = [
    "abono", "consignacion", "recibida", "recibido", "nomina", "salario",
    "reembolso", "devolucion", "rendimiento", "intereses ganados", "deposito",
    "honorarios", "ingreso", "cdt", "dividendo",
]

CATEGORIAS_GASTO_KW = {
    "Alimentación": ["rappi", "ifood", "restaurante", "supermercado", "mercado", "d1", "ara",
                     "exito", "jumbo", "carulla", "olimpica", "cafe", "starbucks", "panaderia",
                     "frisby", "kfc", "mcdonald", "domicilios"],
    "Transporte": ["uber", "didi", "taxi", "cabify", "peaje", "gasolina", "terpel", "primax",
                   "transmilenio", "sitp", "parqueadero", "beat"],
    "Vivienda y Servicios": ["epm", "acueducto", "energia", "gas natural", "claro", "movistar",
                             "tigo", "internet", "arriendo", "administracion", "etb"],
    "Salud": ["farmacia", "drogueria", "clinica", "eps", "sanitas", "colsubsidio",
              "cruz verde", "laboratorio"],
    "Educación": ["universidad", "colegio", "matricula", "curso", "udemy", "platzi", "libreria"],
    "Entretenimiento": ["netflix", "spotify", "cine", "steam", "playstation", "xbox",
                        "youtube", "disney", "hbo"],
    "Ropa y Cuidado Personal": ["zara", "ropa", "falabella", "peluqueria", "stradivarius",
                                "adidas", "nike"],
    "Deudas y Créditos": ["cuota", "credito", "prestamo", "intereses", "sobregiro"],
}

CATEGORIAS_INGRESO_KW = {
    "Salario": ["nomina", "salario"],
    "Freelance / Honorarios": ["honorarios", "freelance"],
    "Inversiones": ["rendimiento", "cdt", "fiducia", "intereses ganados", "dividendo"],
    "Ventas": ["venta", "ventas"],
}

METODOS_KW = [
    ("Tarjeta", ["tarjeta", "visa", "mastercard", "amex"]),
    ("Transferencia", ["transferencia", "transf", "pse", "nequi", "daviplata", "bre-b", "abono"]),
    ("Efectivo", ["retiro", "cajero", "atm", "efectivo", "corresponsal"]),
]

RE_LINEA_FECHA = re.compile(r"^(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2})\s+(.+)$")
RE_MONTO = re.compile(
    r"(?<!\w)(?:\$\s?)?[+-]?"
    r"(?:\d{1,3}(?:[.,]\d{3})+(?:[.,]\d{1,2})?|\d+[.,]\d{1,2}|\d{3,})"
    r"(?:\s?(?:DB|CR))?[+-]?(?=\s|$)"
)


def normalizar_texto(texto) -> str:
    """Pasa a minúsculas, quita tildes y espacios repetidos."""
    base = unicodedata.normalize("NFKD", str(texto or ""))
    sin_tildes = base.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", sin_tildes.lower()).strip()


def _contiene_palabra(texto_norm: str, palabras: list[str]) -> bool:
    return any(re.search(rf"\b{re.escape(p)}\b", texto_norm) for p in palabras)


def sugerir_tipo(descripcion: str) -> str:
    """Clasifica por palabras clave cuando el extracto no trae signo. Por defecto: Gasto."""
    return "Ingreso" if _contiene_palabra(normalizar_texto(descripcion), PALABRAS_INGRESO) else "Gasto"


def sugerir_categoria(descripcion: str, tipo: str) -> str:
    texto = normalizar_texto(descripcion)
    if tipo == "Ingreso":
        for categoria, palabras in CATEGORIAS_INGRESO_KW.items():
            if _contiene_palabra(texto, palabras):
                return categoria
        return "Otros Ingresos"
    for categoria, palabras in CATEGORIAS_GASTO_KW.items():
        if _contiene_palabra(texto, palabras):
            return categoria
    return "Otros Gastos"


def sugerir_metodo(descripcion: str) -> str:
    texto = normalizar_texto(descripcion)
    for metodo, palabras in METODOS_KW:
        if _contiene_palabra(texto, palabras):
            return metodo
    return "Otro"


def _texto_celda(valor) -> str:
    texto = "" if valor is None else str(valor).strip()
    return "" if texto.lower() in ("nan", "none", "nat") else texto


def _monto_signado(valor) -> float | None:
    """
    Convierte una celda de monto en número con signo.
    Negativo si lleva '-' (al inicio o al final), paréntesis o 'DB'.
    Retorna None si la celda no tiene un monto.
    """
    texto = _texto_celda(valor)
    if not texto:
        return None
    mayus = texto.upper()
    negativo = (
        texto.startswith("-")
        or texto.endswith("-")
        or texto.startswith("(")
        or mayus.endswith("DB")
        or " DB" in mayus
    )
    cantidad = abs(parsear_monto_cop(texto.replace("-", "").replace("+", "")))
    if cantidad == 0:
        return None
    return -cantidad if negativo else cantidad


def _parsear_fecha(valor):
    texto = _texto_celda(valor)
    if not texto:
        return None
    dayfirst = not re.match(r"\d{4}-\d{2}-\d{2}", texto)  # ISO va sin dayfirst
    fecha = pd.to_datetime(texto, dayfirst=dayfirst, errors="coerce")
    return None if pd.isna(fecha) else fecha.date()


def _detectar_encabezado(df_raw: pd.DataFrame) -> tuple[int, dict]:
    """Busca la fila de títulos y devuelve su índice y la posición de cada columna clave."""
    for idx in range(min(len(df_raw), 40)):
        mapa: dict[str, int] = {}
        for pos, celda in enumerate(df_raw.iloc[idx].tolist()):
            c = normalizar_texto(celda)
            if not c:
                continue
            if "fecha" in c and "fecha" not in mapa:
                mapa["fecha"] = pos
            elif "debito" in c and "debito" not in mapa:
                mapa["debito"] = pos
            elif "credito" in c and "credito" not in mapa:
                mapa["credito"] = pos
            elif (
                any(k in c for k in ("descripcion", "concepto", "detalle", "movimiento",
                                     "referencia", "establecimiento"))
                and "descripcion" not in mapa
            ):
                mapa["descripcion"] = pos
            elif (
                any(k in c for k in ("valor", "monto", "importe", "cuantia"))
                and "saldo" not in c
                and "valor" not in mapa
            ):
                mapa["valor"] = pos
        if "fecha" in mapa and ("valor" in mapa or "debito" in mapa or "credito" in mapa):
            return idx, mapa
    raise ValueError(
        "No encontré encabezados de fecha y valor (ej. 'Fecha', 'Descripción', 'Valor'). "
        "Revisa que el extracto tenga una fila de títulos."
    )


def _filas_a_movimientos(df_raw: pd.DataFrame, idx_enc: int, mapa: dict, avisos: list[str]) -> pd.DataFrame:
    datos = df_raw.iloc[idx_enc + 1:].reset_index(drop=True)
    con_debcred = "debito" in mapa or "credito" in mapa

    montos: list[float | None] = []
    usa_signo = False
    if con_debcred:
        avisos.append("Clasifiqué los movimientos según las columnas Débito (gasto) y Crédito (ingreso).")
    else:
        montos = [_monto_signado(v) for v in datos.iloc[:, mapa["valor"]].tolist()]
        usa_signo = any(m is not None and m < 0 for m in montos)
        if usa_signo:
            avisos.append("Clasifiqué por signo: valores negativos = gasto, positivos = ingreso.")
        else:
            avisos.append(
                "El extracto no trae signos ni columna de crédito: clasifiqué cada movimiento "
                "por su descripción. Revisa la columna Tipo antes de importar."
            )

    registros = []
    for i, fila in datos.iterrows():
        fecha = _parsear_fecha(fila.iloc[mapa["fecha"]])
        if fecha is None:
            continue
        descripcion = _texto_celda(fila.iloc[mapa["descripcion"]]) if "descripcion" in mapa else ""
        descripcion = " ".join(descripcion.split()) or "Movimiento sin descripción"

        if con_debcred:
            deb = abs(_monto_signado(fila.iloc[mapa["debito"]]) or 0.0) if "debito" in mapa else 0.0
            cred = abs(_monto_signado(fila.iloc[mapa["credito"]]) or 0.0) if "credito" in mapa else 0.0
            neto = cred - deb
            if neto == 0:
                continue
            tipo = "Ingreso" if neto > 0 else "Gasto"
            valor = abs(neto)
        else:
            signado = montos[i]
            if signado is None:
                continue
            if usa_signo:
                tipo = "Ingreso" if signado > 0 else "Gasto"
            else:
                tipo = sugerir_tipo(descripcion)
            valor = abs(signado)

        registros.append(
            {"fecha": fecha, "descripcion": descripcion, "tipo": tipo, "valor": round(float(valor), 2)}
        )

    return pd.DataFrame(registros, columns=["fecha", "descripcion", "tipo", "valor"])


def _tabla_desde_csv(contenido: bytes) -> pd.DataFrame:
    texto = contenido.decode("latin-1")
    for codificacion in ("utf-8-sig", "latin-1"):
        try:
            texto = contenido.decode(codificacion)
            break
        except UnicodeDecodeError:
            continue
    muestra = texto[:4096]
    try:
        separador = csv.Sniffer().sniff(muestra, delimiters=";,\t|").delimiter
    except csv.Error:
        separador = ";" if muestra.count(";") > muestra.count(",") else ","
    filas = list(csv.reader(io.StringIO(texto), delimiter=separador))
    return pd.DataFrame(filas)


def _tabla_desde_pdf(contenido: bytes, avisos: list[str]) -> pd.DataFrame:
    """Intenta leer tablas del PDF; si no hay, usa las líneas de texto (best-effort)."""
    try:
        import pdfplumber
    except ImportError as exc:
        raise RuntimeError(
            "Falta la librería pdfplumber. Instala las dependencias con: pip install -r requirements.txt"
        ) from exc

    filas: list[list[str]] = []
    textos: list[str] = []
    with pdfplumber.open(io.BytesIO(contenido)) as pdf:
        for pagina in pdf.pages:
            for tabla in pagina.extract_tables() or []:
                for fila in tabla:
                    if fila:
                        filas.append([" ".join(str(c or "").split()) for c in fila])
            textos.append(pagina.extract_text() or "")

    if filas:
        df_tabla = pd.DataFrame(filas).fillna("").astype(str)
        try:
            _detectar_encabezado(df_tabla)
            return df_tabla
        except ValueError:
            pass

    if not "".join(textos).strip():
        try:
            from pypdf import PdfReader

            lector = PdfReader(io.BytesIO(contenido))
            textos = [p.extract_text() or "" for p in lector.pages]
        except Exception:
            textos = []
    if not "".join(textos).strip():
        raise ValueError(
            "El PDF no tiene texto seleccionable (parece un escaneo o una imagen). "
            "Descarga el extracto en Excel o CSV desde tu banca en línea."
        )

    avisos.append("No encontré una tabla clara en el PDF; leí sus líneas de texto. Revisa con cuidado la vista previa.")
    filas_texto = [["Fecha", "Descripción", "Valor"]]
    for linea in "\n".join(textos).splitlines():
        m = RE_LINEA_FECHA.match(linea.strip())
        if not m:
            continue
        fecha_txt, resto = m.group(1), m.group(2)
        montos = list(RE_MONTO.finditer(resto))
        if not montos:
            continue
        # Si hay dos montos (valor y saldo), el valor del movimiento es el penúltimo
        elegido = montos[-2] if len(montos) >= 2 else montos[-1]
        descripcion = resto[: elegido.start()].strip(" -")
        filas_texto.append([fecha_txt, descripcion, elegido.group(0)])
    return pd.DataFrame(filas_texto)


def leer_extracto(contenido: bytes, nombre: str) -> tuple[pd.DataFrame, list[str]]:
    """
    Lee un extracto bancario (PDF, XLSX, XLS o CSV) y devuelve:
      - DataFrame con columnas: fecha, descripcion, tipo (Ingreso/Gasto), valor, categoria, metodo_pago
      - lista de avisos para mostrar al usuario
    Lanza ValueError con un mensaje legible si no puede interpretar el archivo.
    """
    extension = nombre.lower().rsplit(".", 1)[-1]
    avisos: list[str] = []

    if extension == "pdf":
        df_raw = _tabla_desde_pdf(contenido, avisos)
    elif extension == "csv":
        df_raw = _tabla_desde_csv(contenido)
    elif extension in ("xlsx", "xls"):
        df_raw = pd.read_excel(io.BytesIO(contenido), header=None, dtype=str)
    else:
        raise ValueError("Formato no compatible. Usa PDF, XLSX, XLS o CSV.")

    df_raw = df_raw.fillna("").astype(str)
    idx_enc, mapa = _detectar_encabezado(df_raw)
    movs = _filas_a_movimientos(df_raw, idx_enc, mapa, avisos)
    if movs.empty:
        raise ValueError("No encontré movimientos válidos. Revisa que cada fila tenga fecha y valor.")

    movs["categoria"] = [sugerir_categoria(d, t) for d, t in zip(movs["descripcion"], movs["tipo"])]
    movs["metodo_pago"] = [sugerir_metodo(d) for d in movs["descripcion"]]

    ingresos = int((movs["tipo"] == "Ingreso").sum())
    gastos = int((movs["tipo"] == "Gasto").sum())
    avisos.append(f"Detecté {len(movs)} movimientos: {ingresos} ingresos y {gastos} gastos.")
    return movs.reset_index(drop=True), avisos
