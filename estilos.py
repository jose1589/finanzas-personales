"""
Estilos responsivos y animaciones de la interfaz.

- CSS: tipografía fluida (clamp), grids adaptables (auto-fit) y sin recortes.
  Ya NO se fuerza un tamaño fijo a todos los elementos de Streamlit: eso era lo
  que recortaba textos y valores en COP.
- Animaciones: entrada suave con CSS y efecto ripple en botones con JavaScript.
  El JS corre en un iframe de altura 0 y accede al documento padre; si el
  navegador lo bloquea, la app sigue funcionando sin efectos.
"""

import streamlit as st
import streamlit.components.v1 as components

CSS_APP = """
<style>
    :root {
        --fp-texto: #0F172A;
        --fp-suave: #64748B;
        --fp-borde: #E2E8F0;
    }

    .block-container {
        padding-top: 1.2rem;
        padding-bottom: 3rem;
        max-width: 1340px;
    }

    /* Textos con tamaño fluido: crecen en PC y se achican en celular */
    .stApp p, .stApp label, .stApp .stMarkdown, .stApp .stCaption {
        font-size: clamp(0.95rem, 0.5vw + 0.82rem, 1.05rem);
        color: var(--fp-texto);
    }

    h1 {
        font-size: clamp(1.5rem, 1.2vw + 1.1rem, 2.05rem) !important;
        font-weight: 800 !important;
        letter-spacing: -0.02em;
        margin-bottom: 0.25rem !important;
        overflow-wrap: anywhere;
    }
    h2 {
        font-size: clamp(1.25rem, 0.8vw + 1rem, 1.5rem) !important;
        font-weight: 700 !important;
    }
    h3 {
        font-size: clamp(1.1rem, 0.6vw + 0.95rem, 1.25rem) !important;
        font-weight: 700 !important;
    }

    /* Columnas que se encogen sin desbordar */
    [data-testid="stHorizontalBlock"] > div {
        min-width: 0;
    }

    input, textarea, [data-baseweb="select"] > div {
        font-size: 1rem !important;
    }

    /* Botones táctiles con micro-interacción */
    .stButton > button, .stDownloadButton > button, [data-testid="stFormSubmitButton"] > button {
        font-size: clamp(0.95rem, 0.4vw + 0.87rem, 1.04rem) !important;
        font-weight: 600 !important;
        min-height: 46px !important;
        border-radius: 12px !important;
        padding: 0.55rem 1rem !important;
        line-height: 1.25 !important;
        white-space: normal !important;
        transition: transform 0.15s ease, box-shadow 0.15s ease, filter 0.15s ease;
    }
    .stButton > button:hover,
    .stDownloadButton > button:hover,
    [data-testid="stFormSubmitButton"] > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 14px rgba(15, 23, 42, 0.10);
    }
    .stButton > button:active,
    .stDownloadButton > button:active {
        transform: scale(0.98);
    }

    button[data-baseweb="tab"] {
        font-size: clamp(0.95rem, 0.3vw + 0.87rem, 1.05rem) !important;
        font-weight: 600 !important;
        padding: 0.7rem 0.9rem !important;
    }

    /* Métricas nativas: el valor baja de línea en vez de cortarse con "..." */
    [data-testid="stMetricLabel"] {
        font-size: 0.95rem !important;
        font-weight: 600 !important;
        color: #475569 !important;
        white-space: normal !important;
        overflow: visible !important;
    }
    [data-testid="stMetricValue"] {
        font-size: clamp(1.15rem, 1.2vw + 0.7rem, 1.55rem) !important;
        font-weight: 800 !important;
        white-space: normal !important;
        overflow: visible !important;
        overflow-wrap: anywhere;
    }

    /* Grid de tarjetas KPI: se acomoda solo según el ancho disponible */
    .kpi-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 1rem;
        margin: 0.5rem 0 1rem 0;
    }

    .kpi-card {
        background-color: #FFFFFF;
        border-radius: 16px;
        padding: 1.1rem 1.2rem;
        border: 1px solid var(--fp-borde);
        border-left-width: 6px;
        box-shadow: 0 4px 12px rgba(15, 23, 42, 0.05);
        min-width: 0;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        animation: fpSubir 0.55s ease both;
        animation-delay: calc(var(--i, 0) * 90ms);
    }
    .kpi-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 10px 20px rgba(15, 23, 42, 0.10);
    }
    .kpi-title {
        font-size: 0.85rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: var(--fp-suave);
        margin-bottom: 0.4rem;
        overflow-wrap: anywhere;
    }
    .kpi-value {
        font-size: clamp(1.2rem, 1.2vw + 0.9rem, 1.7rem);
        font-weight: 800;
        line-height: 1.25;
        overflow-wrap: anywhere;
    }
    .kpi-sub {
        font-size: 0.88rem;
        color: var(--fp-suave);
        margin-top: 0.4rem;
    }

    .border-ingreso { border-left-color: #10B981; }
    .border-gasto   { border-left-color: #EF4444; }
    .border-balance { border-left-color: #2563EB; }
    .border-neutro  { border-left-color: #64748B; }

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
        font-size: clamp(1rem, 0.6vw + 0.85rem, 1.15rem);
        font-weight: 700;
        color: #1E3A8A;
        overflow-wrap: anywhere;
    }

    /* Gráficos y tablas entran con una transición suave */
    [data-testid="stPlotlyChart"],
    [data-testid="stDataFrame"],
    [data-testid="stDataEditor"] {
        animation: fpAparecer 0.6s ease both;
    }

    @keyframes fpSubir {
        from { opacity: 0; transform: translateY(14px); }
        to   { opacity: 1; transform: translateY(0); }
    }
    @keyframes fpAparecer {
        from { opacity: 0; }
        to   { opacity: 1; }
    }

    /* Tablet: 2 columnas cómodas */
    @media (max-width: 1024px) {
        .kpi-value { font-size: clamp(1.15rem, 2vw + 0.6rem, 1.5rem); }
    }

    /* Celular: una columna y márgenes estrechos */
    @media (max-width: 640px) {
        .block-container {
            padding-top: 0.8rem;
            padding-left: 0.75rem;
            padding-right: 0.75rem;
        }
        .kpi-grid {
            grid-template-columns: 1fr;
            gap: 0.75rem;
        }
    }

    /* Respeta a quien desactiva animaciones en su sistema */
    @media (prefers-reduced-motion: reduce) {
        *, *::before, *::after {
            animation: none !important;
            transition: none !important;
        }
    }
</style>
"""

# Ripple en botones: se engancha una sola vez al documento padre (no al iframe)
JS_ANIMACIONES = """
<script>
(function () {
  try {
    const win = window.parent;
    const doc = win.document;
    if (win.__finanzasRipple) { return; }
    win.__finanzasRipple = true;

    const estilo = doc.createElement("style");
    estilo.textContent = `
      .fp-ripple {
        position: absolute; border-radius: 50%; pointer-events: none;
        transform: scale(0); background: rgba(255, 255, 255, 0.5);
        animation: fpRipple 0.6s linear;
      }
      @keyframes fpRipple { to { transform: scale(3.5); opacity: 0; } }
    `;
    doc.head.appendChild(estilo);

    doc.addEventListener("click", function (e) {
      const boton = e.target && e.target.closest ? e.target.closest("button") : null;
      if (!boton || boton.disabled) { return; }
      const r = boton.getBoundingClientRect();
      const tam = Math.max(r.width, r.height);
      const onda = doc.createElement("span");
      onda.className = "fp-ripple";
      onda.style.width = onda.style.height = tam + "px";
      onda.style.left = (e.clientX - r.left - tam / 2) + "px";
      onda.style.top = (e.clientY - r.top - tam / 2) + "px";
      if (win.getComputedStyle(boton).position === "static") {
        boton.style.position = "relative";
      }
      boton.style.overflow = "hidden";
      boton.appendChild(onda);
      setTimeout(function () { onda.remove(); }, 650);
    }, true);
  } catch (err) {
    // Sin acceso al documento padre: la app sigue funcionando sin animaciones JS.
  }
})();
</script>
"""


def aplicar_estilos() -> None:
    """Inyecta el CSS responsivo. Llamar una vez, justo después de set_page_config."""
    st.markdown(CSS_APP, unsafe_allow_html=True)


def activar_animaciones_js() -> None:
    """Activa el efecto ripple con JavaScript. Llamar una vez por ejecución de la página."""
    components.html(JS_ANIMACIONES, height=0)
