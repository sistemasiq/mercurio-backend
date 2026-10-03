FROM python:3.12-slim

# postgresql-client: el entrypoint usa psql para inicializar una BD vacía con
# sql/schema_maestro.sql antes de arrancar la API.
RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Sin privilegios de root en tiempo de ejecución.
RUN useradd --create-home --uid 10001 woowkids \
    && chmod +x docker/entrypoint.sh \
    && chown -R woowkids:woowkids /app
USER woowkids

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/openapi.json', timeout=4)"

ENTRYPOINT ["docker/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
