from app.core.config import settings

print(f"--- Diagnóstico de Configuración ---")
print(f"Database URL cargada: '{settings.database_url}'")
print(f"Tipo de objeto: {type(settings.database_url)}")