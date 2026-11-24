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
# OPERACIONES DE PRESUPUESTOS MENSUALES
# ============================================================================

def obtener_presupuestos(mes_anio: str | None = None) -> pd.DataFrame:
    """Consulta los presupuestos de un mes específico (YYYY-MM) o todos."""
    columnas = ["id", "mes_anio", "categoria", "monto_limite", "created_at"]
    try:
        supabase = obtener_cliente_supabase()
        query = supabase.table("presupuestos").select("*")
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
    """Elimina un registro de presupuesto por ID."""
    try:
        supabase = obtener_cliente_supabase()
        supabase.table("presupuestos").delete().eq("id", int(pres_id)).execute()
        return True, "Presupuesto eliminado."
    except Exception as e:
        return False, f"No se pudo eliminar el presupuesto: {e}"
