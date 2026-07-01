from app.core.config import settings  # Importamos la configuración que ya hiciste
from sqlalchemy import create_engine, text

# Usamos la URL que Pydantic leyó del .env
DATABASE_URL = settings.database_url

try:
    print(f"Intentando conectar a: {DATABASE_URL}")
    engine = create_engine(DATABASE_URL, connect_args={"connect_timeout": 20})
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version();"))
        print("¡Conexión exitosa!")
        print("Versión de BD:", result.scalar())
except Exception as e:
    print("--- ERROR DETECTADO ---")
    print(e)
