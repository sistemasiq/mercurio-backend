# mercurio-backend

## Contenedor todo en uno

Una sola imagen con el sistema completo: frontend, API, PostgreSQL y MinIO. Todos los datos viven en el volumen `/data`. La publican los releases de este repo y de `mercurio-frontend`.

```bash
docker login ghcr.io          # los paquetes son privados: token con read:packages
docker run -d --name woowkids -p 8080:80 -v woowkids_data:/data ghcr.io/sistemasiq/woowkids:latest
```

Abre http://localhost:8080 y entra con `admin@woowkids.com` / `admin1234`. La consola de MinIO es opcional: agrega `-p 9001:9001`.

Los valores por defecto son genéricos. Cámbialos con `-e`:
- `POSTGRES_PASSWORD`, `SECRET_KEY`, `MINIO_SECRET_KEY`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`;
- `COOKIE_SECURE=true` si va detrás de HTTPS;
- `CORS_ORIGINS` con la URL pública;
- `SEED_DEMO=true` para cargar datos de prueba la primera vez.

Tags: `latest` y `f<frontend>-b<backend>` (por ejemplo `f1.0.0-b1.0.0`). Para producción a escala usa las imágenes separadas con `docker-compose.yml`.
