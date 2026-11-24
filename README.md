# 💰 Control Financiero Personal (Python + Streamlit + Supabase)

## 1. Configurar la Base de Datos en Supabase
1. Abre tu proyecto en Supabase (`https://supabase.com/dashboard/project/xtasmmswigqbauvcrmip`).
2. Ve a **SQL Editor** -> **New query**, pega el contenido de `schema.sql` y presiona **Run**.
3. Ve a **Project Settings** (ícono de engranaje) -> **API** (o **API Keys**) y copia tu clave **`anon` / `public`** (NO la contraseña de la cuenta ni de PostgreSQL).
4. Pega esa clave en `.streamlit/secrets.toml` reemplazando `PEGA_AQUI_TU_ANON_PUBLIC_KEY`.

## 2. Ejecución Local
```bash
python -m venv .venv
# Windows:
.venv\Scripts\Activate.ps1
# macOS / Linux:
source .venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
```

## 3. Publicación en Streamlit Cloud
1. Sube esta carpeta a un repositorio privado en GitHub (`.gitignore` protege `.streamlit/secrets.toml`).
2. Entra a https://share.streamlit.io, conecta tu repositorio y selecciona `app.py`.
3. En **Advanced settings -> Secrets**, pega:
```toml
SUPABASE_URL = "https://xtasmmswigqbauvcrmip.supabase.co"
SUPABASE_KEY = "TU_CLAVE_ANON_PUBLICA"
```
