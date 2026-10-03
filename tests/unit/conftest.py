"""Variables de entorno mínimas para que `app.core.config.Settings()` se
instancie al importar módulos de servicio en los tests unitarios (no hay
`.env` en los worktrees). No se usa una base de datos real: los tests
unitarios mockean los repositories."""

import os

os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost:5432/test")
os.environ.setdefault("MINIO_ACCESS_KEY", "test-access-key")
os.environ.setdefault("MINIO_SECRET_KEY", "test-secret-key")
