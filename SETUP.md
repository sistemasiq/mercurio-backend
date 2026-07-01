# Setup de calidad + git hooks — Mercury BackEnd

Pasos para dejar funcionando Ruff + mypy + pytest + pre-commit + commitlint.

## 1. Copiar archivos a la raíz del repo

```
pyproject.toml
requirements-dev.txt
.pre-commit-config.yaml
commitlint.config.js
```

## 2. Crear entorno virtual e instalar dependencias

```bash
python -m venv .venv
source .venv/bin/activate         # en Fedora/Linux

# Dependencias de desarrollo (calidad + testing)
pip install -r requirements-dev.txt
```

> Las dependencias de la app (fastapi, uvicorn, asyncpg, pydantic-settings, etc.)
> van en `requirements.txt` aparte, a medida que se necesiten.

## 3. Instalar los hooks de pre-commit

```bash
pre-commit install                      # hook pre-commit (ruff, mypy, etc.)
pre-commit install --hook-type commit-msg   # hook commit-msg (commitlint)
```

Esto deja los dos hooks activos en `.git/hooks/`.

> commitlint corre sobre Node. Necesitas tener `node`/`npx` disponible en el sistema
> (el hook lo descarga vía pre-commit, pero requiere Node instalado en la máquina).

## 4. Probar

```bash
# Correr todos los hooks manualmente sobre todo el repo:
pre-commit run --all-files

# Probar la validación de mensaje:
git commit -m "agrega login"     # debe FALLAR (sin tipo conventional)
git commit -m "feat: agregar endpoint de login con jwt"   # debe PASAR
```

```bash
ruff check . --fix      # lint con autofix
ruff format .           # formato
mypy app                # type-check
pytest                  # tests
```

## Qué hace cada cosa

- **pyproject.toml** — Config central de Ruff (lint+formato, línea 100, reglas E/W/F/I/B/UP/N/ASYNC/RUF), mypy en modo estricto con plugin de pydantic, y pytest con modo asyncio automático.
- **requirements-dev.txt** — Ruff, mypy, pytest, pytest-asyncio, httpx (tests de endpoints) y pre-commit.
- **.pre-commit-config.yaml** — Hooks: ruff + ruff-format, mypy, higiene de archivos y commitlint en el mensaje. Al commitear, si algo falla el commit se aborta.
- **commitlint.config.js** — Conventional commits: todos los tipos, sin scope, subject en minúscula sin punto final. Idéntico al frontend.
