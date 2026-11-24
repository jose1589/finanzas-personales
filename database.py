from datetime import date
import pandas as pd
import streamlit as st
from supabase import Client, create_client


@st.cache_resource
def obtener_cliente_supabase() -> Client:
    """Inicializa y reutiliza la conexión con Supabase usando st.secrets."""
    try:
        url = st.secrets["SUPABASE_URL"].strip().rstrip("/")
        if url.endswith("/rest/v1"):
            url = url[: -len("/rest/v1")]
        key = st.secrets["SUPABASE_KEY"].strip()
    except KeyError as exc:
        st.error(
            "Faltan las credenciales SUPABASE_URL o SUPABASE_KEY en .streamlit/secrets.toml "
            "o en los Secrets de Streamlit Cloud."
        )
        raise exc
    return create_client(url, key)


# ============================================================================
# OPERACIONES DE MOVIMIENTOS
# ============================================================================

def obtener_movimientos() -> pd.DataFrame:
    """Consulta todos los movimientos ordenados del más reciente al más antiguo."""
    columnas = ["id", "fecha", "descripcion", "categoria", "tipo", "valor", "metodo_pago", "created_at"]
    try:
        supabase = obtener_cliente_supabase()
        respuesta = (
            supabase.table("movimientos")
            .select("*")
            .order("fecha", desc=True)
            .order("id", desc=True)
            .execute()
        )
        datos = respuesta.data or []
        if not datos:
            return pd.DataFrame(columns=columnas)

        df = pd.DataFrame(datos)
        df["fecha"] = pd.to_datetime(df["fecha"]).dt.date
        df["valor"] = pd.to_numeric(df["valor"], errors="coerce").fillna(0.0)
        return df
    except Exception as e:
        st.error(f"Error al consultar movimientos en Supabase: {e}")
        return pd.DataFrame(columns=columnas)


def agregar_movimiento(
    fecha_mov: date,
    descripcion: str,
    categoria: str,
    tipo: str,
    valor: float,
    metodo_pago: str,
) -> tuple[bool, str]:
    """Inserta un nuevo movimiento financiero de forma permanente."""
    try:
        supabase = obtener_cliente_supabase()
        payload = {
            "fecha": fecha_mov.isoformat(),
            "descripcion": descripcion.strip(),
            "categoria": categoria.strip(),
            "tipo": tipo,
            "valor": round(float(valor), 2),
            "metodo_pago": metodo_pago,
        }
        supabase.table("movimientos").insert(payload).execute()
        return True, "Movimiento registrado correctamente."
    except Exception as e:
        return False, f"No se pudo guardar el movimiento: {e}"


def agregar_movimientos_lote(registros: list[dict]) -> tuple[bool, str]:
    """
    Inserta varios movimientos (p. ej. desde un extracto bancario) por bloques de 500.
    Cada registro requiere: fecha (date), descripcion, categoria, tipo, valor, metodo_pago.
    """
    if not registros:
        return False, "No hay movimientos seleccionados para importar."

    payloads = []
    for reg in registros:
        if reg["tipo"] not in ("Ingreso", "Gasto"):
            return False, f"Tipo de movimiento inválido: {reg['tipo']}."
        valor = round(float(reg["valor"]), 2)
        if valor <= 0:
            return False, "Hay movimientos con valor menor o igual a cero. Corrígelos antes de importar."
        payloads.append(
            {
                "fecha": reg["fecha"].isoformat(),
                "descripcion": str(reg["descripcion"]).strip() or "Sin descripción",
                "categoria": str(reg["categoria"]).strip() or "Otros Gastos",
                "tipo": reg["tipo"],
                "valor": valor,
                "metodo_pago": reg["metodo_pago"],
            }
        )

    try:
        supabase = obtener_cliente_supabase()
        for inicio in range(0, len(payloads), 500):
            supabase.table("movimientos").insert(payloads[inicio:inicio + 500]).execute()
        return True, f"{len(payloads)} movimientos importados correctamente."
    except Exception as e:
        return False, (
            f"No se pudo completar la importación: {e}. "
            "Revisa el historial antes de reintentar, porque algunos bloques pudieron guardarse."
        )


def actualizar_movimiento(
    mov_id: int,
    fecha_mov: date,
    descripcion: str,
    categoria: str,
    tipo: str,
    valor: float,
    metodo_pago: str,
) -> tuple[bool, str]:
    """Actualiza un movimiento existente identificado por su ID."""
    try:
        supabase = obtener_cliente_supabase()
        payload = {
            "fecha": fecha_mov.isoformat(),
            "descripcion": descripcion.strip(),
            "categoria": categoria.strip(),
            "tipo": tipo,
            "valor": round(float(valor), 2),
            "metodo_pago": metodo_pago,
        }
        supabase.table("movimientos").update(payload).eq("id", int(mov_id)).execute()
        return True, "Movimiento actualizado correctamente."
    except Exception as e:
        return False, f"No se pudo actualizar el movimiento: {e}"


def eliminar_movimiento(mov_id: int) -> tuple[bool, str]:
    """Elimina permanentemente un movimiento por su ID."""
    try:
        supabase = obtener_cliente_supabase()
        supabase.table("movimientos").delete().eq("id", int(mov_id)).execute()
        return True, "Movimiento eliminado correctamente."
    except Exception as e:
        return False, f"No se pudo eliminar el movimiento: {e}"


# ============================================================================
# OPERACIONES DE CATEGORÍAS
# ============================================================================

def obtener_categorias() -> pd.DataFrame:
    """Obtiene todas las categorías registradas en Supabase."""
    columnas = ["id", "nombre", "tipo", "created_at"]
    try:
        supabase = obtener_cliente_supabase()
        respuesta = (
            supabase.table("categorias")
            .select("*")
            .order("tipo", desc=False)
            .order("nombre", desc=False)
            .execute()
        )
        datos = respuesta.data or []
        if not datos:
            return pd.DataFrame(columns=columnas)
        return pd.DataFrame(datos)
    except Exception as e:
        st.error(f"Error al cargar categorías: {e}")
        return pd.DataFrame(columns=columnas)


def agregar_categoria(nombre: str, tipo: str) -> tuple[bool, str]:
    """Crea una nueva categoría personalizada para Ingreso o Gasto."""
    nombre_limpio = nombre.strip()
    if not nombre_limpio:
        return False, "El nombre de la categoría no puede estar vacío."
    try:
        supabase = obtener_cliente_supabase()
        supabase.table("categorias").insert({"nombre": nombre_limpio, "tipo": tipo}).execute()
        return True, f"Categoría '{nombre_limpio}' agregada."
    except Exception as e:
        if "duplicate" in str(e).lower() or "unique" in str(e).lower():
            return False, f"La categoría '{nombre_limpio}' ya existe para {tipo}."
        return False, f"Error al crear categoría: {e}"


def eliminar_categoria(cat_id: int) -> tuple[bool, str]:
    """Elimina una categoría por su ID."""
    try:
        supabase = obtener_cliente_supabase()
        supabase.table("categorias").delete().eq("id", int(cat_id)).execute()
        return True, "Categoría eliminada."
    except Exception as e:
        return False, f"No se pudo eliminar la categoría: {e}"


# ============================================================================
# OPERACIONES DE PRESUPUESTOS MENSUALES Y METAS DE AHORRO
# ============================================================================

def obtener_presupuestos(mes_anio: str | None = None) -> pd.DataFrame:
    """Consulta los presupuestos mensuales (excluyendo metas de ahorro)."""
    columnas = ["id", "mes_anio", "categoria", "monto_limite", "created_at"]
    try:
        supabase = obtener_cliente_supabase()
        query = supabase.table("presupuestos").select("*").neq("mes_anio", "META")
        if mes_anio:
            query = query.eq("mes_anio", mes_anio)
        respuesta = query.order("mes_anio", desc=True).order("categoria", desc=False).execute()
        datos = respuesta.data or []
        if not datos:
            return pd.DataFrame(columns=columnas)
        df = pd.DataFrame(datos)
        df["monto_limite"] = pd.to_numeric(df["monto_limite"], errors="coerce").fillna(0.0)
        return df
    except Exception as e:
        st.error(f"Error al consultar presupuestos: {e}")
        return pd.DataFrame(columns=columnas)


def guardar_presupuesto(mes_anio: str, categoria: str, monto_limite: float) -> tuple[bool, str]:
    """Crea o actualiza un presupuesto mensual (General o por categoría)."""
    try:
        supabase = obtener_cliente_supabase()
        payload = {
            "mes_anio": mes_anio,
            "categoria": categoria,
            "monto_limite": round(float(monto_limite), 2),
        }
        supabase.table("presupuestos").upsert(
            payload, on_conflict="mes_anio,categoria"
        ).execute()
        return True, f"Presupuesto guardado para {categoria} ({mes_anio})."
    except Exception as e:
        return False, f"Error al guardar presupuesto: {e}"


def eliminar_presupuesto(pres_id: int) -> tuple[bool, str]:
    """Elimina un registro de presupuesto o meta por ID."""
    try:
        supabase = obtener_cliente_supabase()
        supabase.table("presupuestos").delete().eq("id", int(pres_id)).execute()
        return True, "Registro eliminado."
    except Exception as e:
        return False, f"No se pudo eliminar: {e}"


def obtener_metas_ahorro() -> pd.DataFrame:
    """
    Obtiene las metas de ahorro almacenadas en la tabla presupuestos
    bajo mes_anio = 'META' con formato 'NombreMeta|MontoActual'.
    """
    columnas = ["id", "nombre_meta", "monto_actual", "monto_objetivo"]
    try:
        supabase = obtener_cliente_supabase()
        respuesta = (
            supabase.table("presupuestos")
            .select("*")
            .eq("mes_anio", "META")
            .order("id", desc=False)
            .execute()
        )
        datos = respuesta.data or []
        if not datos:
            return pd.DataFrame(columns=columnas)

        filas = []
        for item in datos:
            raw_cat = str(item.get("categoria", "Meta|0"))
            if "|" in raw_cat:
                nombre_m, actual_str = raw_cat.rsplit("|", 1)
                try:
                    actual_val = float(actual_str)
                except ValueError:
                    actual_val = 0.0
            else:
                nombre_m = raw_cat
                actual_val = 0.0

            filas.append(
                {
                    "id": item["id"],
                    "nombre_meta": nombre_m,
                    "monto_actual": actual_val,
                    "monto_objetivo": float(item.get("monto_limite", 0.0)),
                }
            )
        return pd.DataFrame(filas)
    except Exception as e:
        st.error(f"Error al cargar metas de ahorro: {e}")
        return pd.DataFrame(columns=columnas)


def guardar_meta_ahorro(
    nombre_meta: str,
    monto_objetivo: float,
    monto_actual: float = 0.0,
    meta_id: int | None = None,
) -> tuple[bool, str]:
    """Crea o actualiza una meta de ahorro virtual en Supabase."""
    nombre_limpio = nombre_meta.strip().replace("|", "-")
    if not nombre_limpio:
        return False, "Escribe un nombre para la meta de ahorro."
    if monto_objetivo <= 0:
        return False, "El monto objetivo debe ser mayor que $ 0."

    try:
        supabase = obtener_cliente_supabase()
        categoria_codificada = f"{nombre_limpio}|{round(float(monto_actual), 2)}"
        payload = {
            "mes_anio": "META",
            "categoria": categoria_codificada,
            "monto_limite": round(float(monto_objetivo), 2),
        }
        if meta_id is not None:
            supabase.table("presupuestos").update(payload).eq("id", int(meta_id)).execute()
        else:
            supabase.table("presupuestos").insert(payload).execute()
        return True, f"Meta '{nombre_limpio}' guardada correctamente."
    except Exception as e:
        return False, f"No se pudo guardar la meta: {e}"
