# Plan de Implementación: Módulo Cierre de Caja (Backend)

> **Propósito**: Documento de validación técnica para el equipo. Cubre base de datos, archivos de código y endpoints del módulo de Cierre de Caja en el backend de Mercurio.
>
> **Stack**: FastAPI + asyncpg (sin ORM/SQLAlchemy), migraciones SQL manuales en `sql/migrations/`, arquitectura Router → Service → Repository.

---

## Índice

1. [Correcciones al SQL propuesto](#1-correcciones-al-sql-propuesto)
2. [Migración 020: Catálogos y alteraciones](#2-migración-020-catálogos-y-alteraciones)
3. [Migración 021: Tablas core del módulo](#3-migración-021-tablas-core-del-módulo)
4. [Migración 022: Permisos del módulo](#4-migración-022-permisos-del-módulo)
5. [Archivos de código a crear](#5-archivos-de-código-a-crear)
6. [Endpoints](#6-endpoints)
7. [Integración con flujos existentes](#7-integración-con-flujos-existentes)
8. [Orden recomendado de implementación](#8-orden-recomendado-de-implementación)

---

## 1. Correcciones al SQL propuesto

El SQL enviado por el compañero tiene **3 bugs** que deben corregirse antes de ejecutar cualquier migración.

### Bug 1: `total_monto` como columna generada con subconsulta (inválido en PostgreSQL)

PostgreSQL **no permite subconsultas** dentro de `GENERATED ALWAYS AS`. El SQL propuesto falla en runtime:

```sql
-- ❌ Inválido — PostgreSQL rechaza esto con ERROR
total_monto NUMERIC(12,2) GENERATED ALWAYS AS (
    cantidad_piezas * (SELECT valor_nominal FROM denominaciones_catalogo WHERE id = denominacion_id)
) STORED
```

**Solución**: Eliminar la columna generada. El `total_monto` se calcula en el servicio Python multiplicando `cantidad_piezas × denominacion.valor_nominal` antes de devolver la respuesta, o mediante un JOIN en la consulta SELECT.

```sql
-- ✅ Solo almacenar la cantidad
cantidad_piezas INT NOT NULL DEFAULT 0 CHECK (cantidad_piezas >= 0)
-- total_monto = cantidad_piezas × denominacion.valor_nominal  (calculado en servicio/query)
```

### Bug 2: `caja_id INT` — tipo inconsistente con la convención del proyecto

Todas las claves foráneas a entidades principales en el proyecto usan `UUID`. Usar `INT` rompe la convención y generaría incompatibilidades con la tabla `cajas` que se creará.

```sql
-- ❌ Incorrecto
caja_id INT NOT NULL,

-- ✅ Correcto
caja_id UUID NOT NULL REFERENCES public.cajas(id),
```

### Bug 3: Campos de auditoría con nombre incorrecto

El proyecto usa `creado` / `creado_por` / `modificado` / `modificado_por`. El SQL propuesto usa `fecha_creacion` / `usuario_creacion`, que no existe en ninguna otra tabla del proyecto.

```sql
-- ❌ Incorrecto (no existe este patrón en el proyecto)
fecha_creacion   TIMESTAMPTZ NOT NULL DEFAULT now(),
usuario_creacion UUID REFERENCES usuarios(id)

-- ✅ Correcto (patrón estándar del proyecto)
creado           TIMESTAMPTZ NOT NULL DEFAULT now(),
creado_por       UUID        REFERENCES public.usuarios(id)
```

---

## 2. Migración 020: Catálogos y alteraciones

**Archivo**: `sql/migrations/020_corte_caja_catalogos.sql`

Esta migración es segura para ejecutar primero porque solo añade columnas a tablas existentes y crea tablas de catálogo independientes.

### 2.1 Alteraciones a tablas existentes

```sql
-- metodos_pago: código corto único (EFE, TC, TD) y bandera de efectivo físico
ALTER TABLE public.metodos_pago
    ADD COLUMN IF NOT EXISTS codigo                    VARCHAR(10) UNIQUE,
    ADD COLUMN IF NOT EXISTS requiere_desglose_efectivo BOOLEAN NOT NULL DEFAULT FALSE;

-- usuarios: PIN de 6 dígitos para autenticación del cajero al enviar conteo
-- CHAR(60) = longitud exacta de un hash bcrypt (mismo tipo que password_hash)
ALTER TABLE public.usuarios
    ADD COLUMN IF NOT EXISTS pin_hash CHAR(60);
```

### 2.2 Tabla: `cajas` (terminales POS físicas)

```sql
CREATE TABLE IF NOT EXISTS public.cajas (
    id             UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    sucursal_id    UUID         NOT NULL REFERENCES public.sucursales(id),
    nombre         VARCHAR(100) NOT NULL,
    codigo         VARCHAR(20)  NOT NULL UNIQUE,  -- ej: "CAJA-01"
    activa         BOOLEAN      NOT NULL DEFAULT TRUE,
    creado         TIMESTAMPTZ  NOT NULL DEFAULT now(),
    creado_por     UUID         REFERENCES public.usuarios(id),
    modificado     TIMESTAMPTZ  DEFAULT now(),
    modificado_por UUID         REFERENCES public.usuarios(id)
);

CREATE INDEX IF NOT EXISTS idx_cajas_sucursal ON public.cajas(sucursal_id);
```

### 2.3 Tabla: `turnos_catalogo` (horarios configurables)

```sql
-- SMALLSERIAL: catálogo pequeño, nunca superará ~20 filas (mañana, tarde, noche)
CREATE TABLE IF NOT EXISTS public.turnos_catalogo (
    id          SMALLSERIAL  PRIMARY KEY,
    nombre      VARCHAR(50)  NOT NULL,
    hora_inicio TIME         NOT NULL,
    hora_fin    TIME         NOT NULL,
    activo      BOOLEAN      NOT NULL DEFAULT TRUE,
    creado      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    creado_por  UUID         REFERENCES public.usuarios(id)
);
```

### 2.4 Tabla: `denominaciones` (billetes y monedas)

```sql
-- CHAR(1) para tipo: 'B'=billete, 'M'=moneda
-- Mismo patrón compacto que el resto del proyecto ('P','A','C' en registros)
CREATE TABLE IF NOT EXISTS public.denominaciones (
    id            SMALLSERIAL   PRIMARY KEY,
    valor_nominal NUMERIC(10,2) NOT NULL,
    tipo          CHAR(1)       NOT NULL CHECK (tipo IN ('B','M')),
    activa        BOOLEAN       NOT NULL DEFAULT TRUE,
    creado        TIMESTAMPTZ   NOT NULL DEFAULT now()
);

-- Seed: denominaciones oficiales MXN
INSERT INTO public.denominaciones (valor_nominal, tipo) VALUES
    (1000, 'B'), (500, 'B'), (200, 'B'), (100, 'B'), (50, 'B'), (20, 'B'),
    (10,   'M'), (5,   'M'), (2,   'M'), (1,   'M'), (0.50, 'M')
ON CONFLICT DO NOTHING;
```

### 2.5 Tabla: `conceptos_egreso`

```sql
CREATE TABLE IF NOT EXISTS public.conceptos_egreso (
    id      SMALLSERIAL  PRIMARY KEY,
    nombre  VARCHAR(100) NOT NULL,
    activo  BOOLEAN      NOT NULL DEFAULT TRUE,
    creado  TIMESTAMPTZ  NOT NULL DEFAULT now()
);
```

### 2.6 Tabla: `proveedores` (para retiros parciales)

```sql
-- Ej: "Blindado Loomis", "Traslado a bóveda banco"
CREATE TABLE IF NOT EXISTS public.proveedores (
    id      SMALLSERIAL  PRIMARY KEY,
    nombre  VARCHAR(150) NOT NULL,
    activo  BOOLEAN      NOT NULL DEFAULT TRUE,
    creado  TIMESTAMPTZ  NOT NULL DEFAULT now()
);
```

---

## 3. Migración 021: Tablas core del módulo

**Archivo**: `sql/migrations/021_corte_caja_core.sql`

### Decisión de diseño: Estados como `CHAR(2)`

Los estados del turno se almacenan compactos en BD y se mapean a nombres legibles en el servicio para las respuestas de la API. Este es el mismo patrón que el proyecto ya usa con `VARCHAR(1)` en `registros` y `comandas`.

| BD (`CHAR(2)`) | API (string) | Descripción |
|---|---|---|
| `'OP'` | `OPERANDO` | Turno abierto, aceptando transacciones |
| `'CT'` | `EN_CONTEO` | Caja bloqueada, cajero contando físico |
| `'ER'` | `ESPERANDO_REVISION` | Conteo enviado, esperando admin |
| `'BR'` | `BALANCE_REVELADO` | Admin autenticado, balance visible |
| `'CX'` | `CERRADO` | Turno finalizado definitivamente |

### 3.1 Tabla: `turnos_caja` (entidad central)

```sql
CREATE TABLE IF NOT EXISTS public.turnos_caja (
    id                       UUID           PRIMARY KEY DEFAULT gen_random_uuid(),
    caja_id                  UUID           NOT NULL REFERENCES public.cajas(id),
    cajero_id                UUID           NOT NULL REFERENCES public.usuarios(id),
    turno_catalogo_id        SMALLINT       REFERENCES public.turnos_catalogo(id),
    fecha_operacion          DATE           NOT NULL DEFAULT CURRENT_DATE,
    estado                   CHAR(2)        NOT NULL DEFAULT 'OP',

    fondo_inicial_efectivo   NUMERIC(12,2)  NOT NULL DEFAULT 0.00,
    fecha_hora_apertura      TIMESTAMPTZ    NOT NULL DEFAULT now(),
    fecha_hora_inicio_conteo TIMESTAMPTZ,   -- se llena al pasar a 'CT'
    fecha_hora_revision      TIMESTAMPTZ,   -- se llena al pasar a 'BR'
    fecha_hora_cierre        TIMESTAMPTZ,   -- se llena al pasar a 'CX'

    administrador_cierre_id  UUID           REFERENCES public.usuarios(id),
    observaciones            TEXT,

    -- jti del JWT temporal del admin (de un solo uso; NULL antes y después de su uso)
    token_admin_jti          UUID,

    creado                   TIMESTAMPTZ    NOT NULL DEFAULT now(),
    creado_por               UUID           REFERENCES public.usuarios(id),
    modificado               TIMESTAMPTZ    DEFAULT now(),
    modificado_por           UUID           REFERENCES public.usuarios(id),

    CONSTRAINT chk_estado_turno   CHECK (estado IN ('OP','CT','ER','BR','CX')),
    CONSTRAINT chk_fondo_positivo CHECK (fondo_inicial_efectivo >= 0)
);

-- RN-APE-001: un cajero no puede tener dos turnos activos simultáneos
CREATE UNIQUE INDEX IF NOT EXISTS uq_turnos_cajero_activo
    ON public.turnos_caja(cajero_id) WHERE estado != 'CX';

-- RN-APE-002: una caja no puede tener dos turnos activos simultáneos
CREATE UNIQUE INDEX IF NOT EXISTS uq_turnos_caja_activa
    ON public.turnos_caja(caja_id) WHERE estado != 'CX';

CREATE INDEX IF NOT EXISTS idx_turnos_caja_cajero ON public.turnos_caja(cajero_id);
```

### 3.2 Tabla: `turnocaja_desglose_efectivo` (INMUTABLE)

```sql
-- BIGSERIAL: tabla de detalle con muchas filas, no necesita ser referenciada externamente
CREATE TABLE IF NOT EXISTS public.turnocaja_desglose_efectivo (
    id              BIGSERIAL   PRIMARY KEY,
    turnocaja_id    UUID        NOT NULL REFERENCES public.turnos_caja(id),
    denominacion_id SMALLINT    NOT NULL REFERENCES public.denominaciones(id),
    cantidad_piezas INT         NOT NULL DEFAULT 0 CHECK (cantidad_piezas >= 0),
    -- total_monto NO se almacena (ver Bug 1). Se calcula como:
    -- cantidad_piezas × denominacion.valor_nominal (en servicio o via JOIN al consultar)
    creado          TIMESTAMPTZ NOT NULL DEFAULT now(),
    creado_por      UUID        REFERENCES public.usuarios(id),
    CONSTRAINT uq_desglose_denominacion UNIQUE (turnocaja_id, denominacion_id)
);
```

### 3.3 Tabla: `turnocaja_metodo_pago` (INMUTABLE)

```sql
CREATE TABLE IF NOT EXISTS public.turnocaja_metodo_pago (
    id                    BIGSERIAL     PRIMARY KEY,
    turnocaja_id          UUID          NOT NULL REFERENCES public.turnos_caja(id),
    metodo_pago_id        UUID          NOT NULL REFERENCES public.metodos_pago(id),
    monto_esperado        NUMERIC(12,2) NOT NULL,
    monto_declarado       NUMERIC(12,2) NOT NULL,
    -- Esta sí es válida: solo usa columnas de la misma fila (sin subconsulta)
    diferencia            NUMERIC(12,2) GENERATED ALWAYS AS (monto_declarado - monto_esperado) STORED,
    cantidad_comprobantes INT           NOT NULL DEFAULT 0,
    creado                TIMESTAMPTZ   NOT NULL DEFAULT now(),
    creado_por            UUID          REFERENCES public.usuarios(id),
    CONSTRAINT uq_metodo_por_turno UNIQUE (turnocaja_id, metodo_pago_id)
);
```

### 3.4 Tabla: `movimientos_caja` (INMUTABLE — libro mayor del turno)

Esta tabla es el insumo principal para calcular el `monto_esperado` al momento del cierre. Cada cobro, pago o egreso registrado en la caja debe generar una fila aquí.

```sql
-- CHAR(1) para tipo: 'I'=ingreso, 'E'=egreso
CREATE TABLE IF NOT EXISTS public.movimientos_caja (
    id             BIGSERIAL     PRIMARY KEY,
    turnocaja_id   UUID          NOT NULL REFERENCES public.turnos_caja(id),
    metodo_pago_id UUID          NOT NULL REFERENCES public.metodos_pago(id),
    tipo           CHAR(1)       NOT NULL CHECK (tipo IN ('I','E')),
    concepto       VARCHAR(50)   NOT NULL,  -- 'cobro_estancia', 'retiro_parcial', etc.
    monto          NUMERIC(12,2) NOT NULL CHECK (monto > 0),
    referencia_id  UUID,                    -- id del origen (pagos_estancia.id, etc.)
    creado         TIMESTAMPTZ   NOT NULL DEFAULT now(),
    creado_por     UUID          REFERENCES public.usuarios(id)
);

CREATE INDEX IF NOT EXISTS idx_movimientos_turno
    ON public.movimientos_caja(turnocaja_id);
CREATE INDEX IF NOT EXISTS idx_movimientos_turno_metodo
    ON public.movimientos_caja(turnocaja_id, metodo_pago_id);
```

**Fórmula del monto esperado** (aplicada en el servicio al momento de enviar el conteo):

```
Esperado(método) = fondo_inicial_efectivo (solo si método es efectivo)
                 + SUM(movimientos tipo='I' del método)
                 - SUM(movimientos tipo='E' del método)
                 - SUM(retiros_parciales del método)
```

### 3.5 Tabla: `retiros_parciales` (INMUTABLE)

```sql
CREATE TABLE IF NOT EXISTS public.retiros_parciales (
    id                 BIGSERIAL     PRIMARY KEY,
    turnocaja_id       UUID          NOT NULL REFERENCES public.turnos_caja(id),
    metodo_pago_id     UUID          NOT NULL REFERENCES public.metodos_pago(id),
    monto              NUMERIC(12,2) NOT NULL CHECK (monto > 0),
    concepto_egreso_id SMALLINT      REFERENCES public.conceptos_egreso(id),
    proveedor_id       SMALLINT      REFERENCES public.proveedores(id),
    evidencia_url      TEXT,
    creado             TIMESTAMPTZ   NOT NULL DEFAULT now(),
    creado_por         UUID          REFERENCES public.usuarios(id)
);

CREATE INDEX IF NOT EXISTS idx_retiros_turno ON public.retiros_parciales(turnocaja_id);
```

---

## 4. Migración 022: Permisos del módulo

**Archivo**: `sql/migrations/022_permisos_corte_caja.sql`

Siguiendo el patrón de `006_permisos_eventos_estancias.sql`.

| Código | Nombre | Módulo | Rol(es) |
|---|---|---|---|
| `cajas:listar` | Listar cajas | cajas | Administrador, Cajero |
| `cajas:ver` | Ver caja | cajas | Administrador |
| `cajas:crear` | Crear caja | cajas | Administrador |
| `cajas:editar` | Editar caja | cajas | Administrador |
| `turnos_caja:abrir` | Abrir turno de caja | turnos_caja | Cajero |
| `turnos_caja:ver_activo` | Ver turno activo | turnos_caja | Cajero |
| `turnos_caja:iniciar_conteo` | Iniciar conteo | turnos_caja | Cajero |
| `turnos_caja:enviar_conteo` | Enviar conteo físico | turnos_caja | Cajero |
| `turnos_caja:cancelar` | Cancelar conteo | turnos_caja | Cajero |
| `turnos_caja:historial` | Ver historial de cierres | turnos_caja | Administrador |
| `retiros_parciales:listar` | Listar retiros de turno | retiros_parciales | Cajero, Administrador |
| `retiros_parciales:crear` | Registrar retiro parcial | retiros_parciales | Cajero |

---

## 5. Archivos de código a crear

### 5.1 Modelos de dominio: `app/models/turno_caja.py`

Dataclasses puros (sin ORM). Incluye el `Enum` de estados con el mapeo CHAR(2) → nombre legible para la API, y dataclasses para cada entidad del módulo: `TurnoCaja`, `MovimientoCaja`, `RetiroParcial`, `TurnocajaMetodoPago`, `TurnocajaDesgloseEfectivo`.

```python
class EstadoTurno(str, Enum):
    OPERANDO           = 'OP'
    EN_CONTEO          = 'CT'
    ESPERANDO_REVISION = 'ER'
    BALANCE_REVELADO   = 'BR'
    CERRADO            = 'CX'

ESTADO_DISPLAY = {
    'OP': 'OPERANDO', 'CT': 'EN_CONTEO', 'ER': 'ESPERANDO_REVISION',
    'BR': 'BALANCE_REVELADO', 'CX': 'CERRADO'
}
```

### 5.2 Schemas Pydantic: `app/schemas/turno_caja.py`

**Requests:**

| Schema | Campos clave |
|---|---|
| `AbrirTurnoRequest` | `caja_id: UUID`, `turno_catalogo_id: int \| None`, `fondo_inicial_efectivo: Decimal ≥ 0` |
| `DesgloseEfectivoItem` | `denominacion_id: int`, `cantidad_piezas: int ≥ 0` |
| `DeclaracionMetodoPagoItem` | `metodo_pago_id: UUID`, `monto_declarado: Decimal`, `cantidad_comprobantes: int` |
| `ConteoRequest` | `cajero_pin: str (regex ^\d{6}$)`, `desglose_efectivo: list[DesgloseEfectivoItem]`, `declaracion_metodos_pago: list[DeclaracionMetodoPagoItem]` |
| `RevisionAdminRequest` | `admin_usuario: str`, `admin_password: str (min 8 chars)` |
| `ConfirmarCierreRequest` | `observaciones: str \| None` |
| `RetiroParcialRequest` | `metodo_pago_id: UUID`, `monto: Decimal > 0`, `concepto_egreso_id: int`, `proveedor_id: int \| None`, `evidencia_url: str` |

**Responses:**

| Schema | Campos clave |
|---|---|
| `TurnoCajaOut` | `id`, `estado` (nombre completo, no CHAR2), `fecha_hora_apertura`, `fondo_inicial_efectivo` |
| `BalanceMetodoPagoOut` | `metodo_pago_id`, `nombre`, `monto_esperado`, `monto_declarado`, `diferencia`, `cantidad_comprobantes` |
| `RevisionAdminOut` | `temporal_auth_token: str`, `balance: list[BalanceMetodoPagoOut]` |
| `RetiroParcialOut` | `id`, `monto`, `concepto`, `proveedor`, `evidencia_url`, `creado` |

### 5.3 Repositories

#### `app/repositories/cajas.py`
- `obtener(conn, caja_id) -> dict | None`
- `listar_por_sucursal(conn, sucursal_id) -> list[dict]`
- `crear(conn, sucursal_id, nombre, codigo, creado_por) -> dict`
- `actualizar(conn, caja_id, updates) -> dict | None`
- `pertenece_a_sucursal(conn, caja_id, sucursal_id) -> bool`

#### `app/repositories/turnos_caja.py` ← el más complejo
- `obtener_activo_por_cajero(conn, cajero_id) -> dict | None` — WHERE estado != 'CX'
- `obtener_activo_por_caja(conn, caja_id) -> dict | None` — WHERE estado != 'CX'
- `crear(conn, caja_id, cajero_id, turno_catalogo_id, fondo_inicial, creado_por) -> dict`
- `actualizar_estado(conn, turno_id, nuevo_estado, extra_fields={}) -> dict`
- `guardar_desglose_efectivo(conn, turnocaja_id, items, creado_por) -> None`
- `guardar_metodos_pago(conn, turnocaja_id, items_con_esperado, creado_por) -> None`
- `calcular_esperado_por_metodo(conn, turnocaja_id) -> list[dict]` — query que agrupa `movimientos_caja` por `metodo_pago_id`, suma ingresos y resta egresos, suma `fondo_inicial_efectivo` al método con `requiere_desglose_efectivo = TRUE`
- `obtener_metodos_con_movimientos(conn, turnocaja_id) -> list[dict]`
- `guardar_token_admin(conn, turno_id, jti: UUID) -> None`
- `verificar_token_admin(conn, turno_id, jti: UUID) -> bool`
- `invalidar_token_admin(conn, turno_id) -> None` — SET token_admin_jti = NULL
- `historial(conn, sucursal_ids, filtros) -> list[dict]`

#### `app/repositories/movimientos_caja.py`
- `registrar(conn, turnocaja_id, metodo_pago_id, tipo, concepto, monto, referencia_id, creado_por) -> None`

#### `app/repositories/retiros_parciales.py`
- `crear(conn, turnocaja_id, metodo_pago_id, monto, concepto_egreso_id, proveedor_id, evidencia_url, creado_por) -> dict`
- `listar_por_turno(conn, turnocaja_id) -> list[dict]`

### 5.4 Servicios: `app/services/turno_caja.py`

| Función | Transición de estado | Validaciones clave |
|---|---|---|
| `abrir_turno()` | → `'OP'` | Sin turno activo del cajero (RN-APE-001), sin turno activo en caja (RN-APE-002), fondo ≥ 0 (RN-APE-003), cajero pertenece a sucursal de la caja (RN-APE-004) |
| `iniciar_conteo()` | `'OP'` → `'CT'` | Estado correcto, cajero es propietario del turno |
| `cancelar_conteo()` | `'CT'` → `'OP'` | Solo desde `'CT'` — una vez enviado el conteo ya no se puede cancelar (RN-CIE-003) |
| `enviar_conteo()` | `'CT'` → `'ER'` | Verifica PIN con bcrypt, calcula `monto_esperado` dinámicamente de `movimientos_caja`, valida que se declararon todos los métodos con movimientos reales |
| `autenticar_admin_y_revelar()` | `'ER'` → `'BR'` | Valida credenciales del admin, verifica que admin pertenece a la sucursal de la caja (RN-VAL-003), emite JWT temporal (exp=30min), guarda `jti` en BD |
| `confirmar_cierre()` | `'BR'` → `'CX'` | Valida JWT temporal contra `token_admin_jti` de BD, observaciones ≥ 15 chars si hay diferencias (RN-VAL-005), invalida token, genera PDF |
| `obtener_metodos_activos()` | — | Retorna métodos con movimientos reales para el frontend del conteo |

**Token temporal del admin**: Se reutiliza `security.create_access_token()` con payload `{"tipo": "admin_cierre", "turno_id": "...", "admin_id": "..."}` y `expires_delta=timedelta(minutes=30)`. El `jti` del JWT se almacena en `turnos_caja.token_admin_jti`. Al confirmar, se valida el jti y se hace `NULL` para invalidación permanente. El header requerido es `Authorization: Bearer <token_temporal>`.

### 5.5 Servicio PDF: `app/services/pdf_turno_caja.py`

- `generar_pdf(turno_data: dict) -> bytes`
- Genera el comprobante de cierre con: datos del turno, cajero, administrador, desglose por método de pago y diferencias.
- Librería a usar: `reportlab` (agregar a `requirements.txt` si no está).

### 5.6 Routers

**`app/api/routers/cajas.py`** — Registrar en `app/main.py`

**`app/api/routers/turnos_caja.py`** — Registrar en `app/main.py`

---

## 6. Endpoints

---

### Grupo A: Cajas físicas `/api/cajas`

---

#### `GET /api/cajas`

| | |
|---|---|
| **Permiso** | `cajas:listar` |
| **Query params** | `sucursal_id: UUID` (opcional) |
| **Response 200** | `list[CajaOut]` |

```json
[{ "id": "...", "nombre": "Caja Principal", "codigo": "CAJA-01", "sucursal_id": "...", "activa": true }]
```

---

#### `GET /api/cajas/{caja_id}`

| | |
|---|---|
| **Permiso** | `cajas:ver` |
| **Response 200** | `CajaOut` |
| **Error 404** | Caja no encontrada |

---

#### `POST /api/cajas`

| | |
|---|---|
| **Permiso** | `cajas:crear` |
| **Response 201** | `CajaOut` |
| **Error 400** | Código de caja ya existe |
| **Error 403** | Admin no pertenece a esa sucursal |

```json
// Request
{ "sucursal_id": "...", "nombre": "Caja Principal", "codigo": "CAJA-01" }
```

---

#### `PATCH /api/cajas/{caja_id}`

| | |
|---|---|
| **Permiso** | `cajas:editar` |
| **Response 200** | `CajaOut` |
| **Error 404** | Caja no encontrada |

```json
// Request (todos opcionales)
{ "nombre": "Caja Nueva", "codigo": "CAJA-01-B", "activa": false }
```

---

### Grupo B: Catálogos de soporte

Endpoints de solo lectura para que el frontend construya formularios dinámicos.

---

#### `GET /api/turnos-catalogo`

| | |
|---|---|
| **Permiso** | `turnos_caja:abrir` |
| **Response 200** | `[{ "id", "nombre", "hora_inicio", "hora_fin" }]` — solo activos |

---

#### `GET /api/denominaciones`

| | |
|---|---|
| **Permiso** | `turnos_caja:ver_activo` |
| **Response 200** | `[{ "id", "valor_nominal", "tipo" }]` — solo activas, orden DESC por valor |

---

#### `GET /api/conceptos-egreso`

| | |
|---|---|
| **Permiso** | `retiros_parciales:crear` |
| **Response 200** | `[{ "id", "nombre" }]` — solo activos |

---

#### `GET /api/proveedores`

| | |
|---|---|
| **Permiso** | `retiros_parciales:crear` |
| **Response 200** | `[{ "id", "nombre" }]` — solo activos |

---

### Grupo C: Ciclo de vida del turno `/api/turnos-caja`

---

#### `GET /api/turnos-caja/activo`

> La terminal POS llama este endpoint al cargar para saber si hay turno abierto y en qué estado está.

| | |
|---|---|
| **Permiso** | `turnos_caja:ver_activo` |
| **Autenticación** | JWT del cajero — se usa `cajero_id` del token |
| **Error 404** | No hay turno activo para este cajero |

```json
// Response 200
{
  "id": "...",
  "caja_id": "...",
  "cajero_id": "...",
  "estado": "OPERANDO",
  "fondo_inicial_efectivo": 1500.00,
  "fecha_operacion": "2026-07-22",
  "fecha_hora_apertura": "2026-07-22T08:02:11Z"
}
```

---

#### `POST /api/turnos-caja` — Apertura de turno

> Crea un nuevo turno operativo. Aplica reglas RN-APE-001 a 004.

| | |
|---|---|
| **Permiso** | `turnos_caja:abrir` |
| **Transición** | → `OPERANDO` |

```json
// Request
{
  "caja_id": "...",
  "turno_catalogo_id": 1,
  "fondo_inicial_efectivo": 1500.00
}

// Response 201
{ "id": "...", "estado": "OPERANDO", "fecha_hora_apertura": "2026-07-22T08:02:11Z" }
```

| Código | Motivo |
|---|---|
| `400` | Cajero ya tiene un turno activo en otra terminal (RN-APE-001) |
| `400` | La caja ya tiene un turno activo (RN-APE-002) |
| `400` | `fondo_inicial_efectivo` negativo (RN-APE-003) |
| `403` | Cajero no pertenece a la sucursal de la caja (RN-APE-004) |

---

#### `GET /api/turnos-caja/{turno_id}/metodos-pago`

> Devuelve los métodos de pago que registraron movimientos reales en el turno. El frontend usa esto para renderizar los campos dinámicos del conteo (RN-CIE-005).

| | |
|---|---|
| **Permiso** | `turnos_caja:ver_activo` |
| **Estado requerido** | `EN_CONTEO` |
| **Error 409** | Turno no está en `EN_CONTEO` |

```json
// Response 200
[
  { "metodo_pago_id": "...", "nombre": "Efectivo", "requiere_desglose_efectivo": true },
  { "metodo_pago_id": "...", "nombre": "Tarjeta Crédito", "requiere_desglose_efectivo": false }
]
```

---

#### `POST /api/turnos-caja/{turno_id}/iniciar-conteo`

> Bloquea la caja para nuevas transacciones. Emite evento WebSocket a la sucursal (RN-OPE-006).

| | |
|---|---|
| **Permiso** | `turnos_caja:iniciar_conteo` |
| **Estado requerido** | `OPERANDO` |
| **Transición** | `OPERANDO` → `EN_CONTEO` |
| **Request** | Vacío |
| **Error 409** | Turno no está en `OPERANDO` |

```json
// Response 200
{ "id": "...", "estado": "EN_CONTEO" }
```

> **Nota**: Al confirmar la transición, emitir evento WebSocket vía `ws_manager` notificando a las terminales de la sucursal que la caja está bloqueada.

---

#### `POST /api/turnos-caja/{turno_id}/cancelar`

> Aborta el conteo y devuelve la caja a operación normal. Solo disponible desde `EN_CONTEO` — una vez enviado el conteo no hay vuelta atrás (RN-CIE-003, RN-VAL-001).

| | |
|---|---|
| **Permiso** | `turnos_caja:cancelar` |
| **Estado requerido** | `EN_CONTEO` |
| **Transición** | `EN_CONTEO` → `OPERANDO` |
| **Request** | Vacío |
| **Error 409** | Turno no está en `EN_CONTEO` |

```json
// Response 200
{ "id": "...", "estado": "OPERANDO" }
```

---

#### `POST /api/turnos-caja/{turno_id}/conteo`

> Registra la declaración física del cajero. Valida PIN, calcula el esperado dinámicamente y congela el conteo.

| | |
|---|---|
| **Permiso** | `turnos_caja:enviar_conteo` |
| **Estado requerido** | `EN_CONTEO` |
| **Transición** | `EN_CONTEO` → `ESPERANDO_REVISION` |

```json
// Request
{
  "cajero_pin": "123456",
  "desglose_efectivo": [
    { "denominacion_id": 1, "cantidad_piezas": 5 },
    { "denominacion_id": 2, "cantidad_piezas": 3 }
  ],
  "declaracion_metodos_pago": [
    { "metodo_pago_id": "...", "monto_declarado": 450.00, "cantidad_comprobantes": 3 }
  ]
}

// Response 200
{ "id": "...", "estado": "ESPERANDO_REVISION" }
```

| Código | Motivo |
|---|---|
| `401` | PIN del cajero incorrecto |
| `400` | Faltan métodos de pago que tuvieron movimientos reales en el turno |
| `409` | Turno no está en `EN_CONTEO` |

> **Nota de implementación**: El `monto_esperado` por método se calcula aquí en el momento del envío, consultando `movimientos_caja` y `retiros_parciales`. Inmediatamente después se insertan las filas en `turnocaja_metodo_pago` y `turnocaja_desglose_efectivo`.

---

#### `POST /api/turnos-caja/{turno_id}/revision-admin`

> Autentica al administrador y revela el balance completo. Emite token temporal de un solo uso.

| | |
|---|---|
| **Autenticación** | JWT del cajero (sesión activa) + credenciales del admin en body |
| **Estado requerido** | `ESPERANDO_REVISION` |
| **Transición** | `ESPERANDO_REVISION` → `BALANCE_REVELADO` |

```json
// Request
{
  "admin_usuario": "admin@mercurio.com",
  "admin_password": "SecurePass123"
}

// Response 200
{
  "temporal_auth_token": "<JWT firmado exp=30min>",
  "balance": [
    {
      "metodo_pago_id": "...",
      "nombre": "Efectivo",
      "monto_esperado": 2350.00,
      "monto_declarado": 2350.00,
      "diferencia": 0.00,
      "cantidad_comprobantes": 0
    },
    {
      "metodo_pago_id": "...",
      "nombre": "Tarjeta Crédito",
      "monto_esperado": 500.00,
      "monto_declarado": 450.00,
      "diferencia": -50.00,
      "cantidad_comprobantes": 3
    }
  ]
}
```

| Código | Motivo |
|---|---|
| `401` | Credenciales del administrador incorrectas |
| `403` | El administrador no pertenece a la sucursal de esta caja (RN-VAL-003) |
| `409` | Turno no está en `ESPERANDO_REVISION` |

> **Nota de implementación**: Reutiliza `security.create_access_token()` con payload `{"tipo": "admin_cierre", "turno_id": "...", "admin_id": "..."}` y `expires_delta=timedelta(minutes=30)`. El `jti` generado por `create_access_token()` se guarda en `turnos_caja.token_admin_jti`.

---

#### `POST /api/turnos-caja/{turno_id}/confirmar`

> Consolida el cierre definitivo. Devuelve el PDF del comprobante como archivo binario.

| | |
|---|---|
| **Autenticación especial** | `Authorization: Bearer <temporal_auth_token>` — el token temporal del admin, **no** el JWT del cajero |
| **Estado requerido** | `BALANCE_REVELADO` |
| **Transición** | `BALANCE_REVELADO` → `CERRADO` |

```json
// Request
{ "observaciones": "Faltante de $50 por voucher extraviado de Tarjeta." }
```

```
// Response 200 — Binario PDF
Content-Type: application/pdf
Content-Disposition: attachment; filename="comprobante_cierre_105.pdf"
```

Devuelto con: `fastapi.Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": ...})`

| Código | Motivo |
|---|---|
| `400` | Hay diferencias y `observaciones` está vacío o tiene menos de 15 caracteres (RN-VAL-005) |
| `401` | Token temporal inválido, expirado o ya usado |
| `409` | Turno no está en `BALANCE_REVELADO` |

> **Nota de implementación**: Tras confirmar el cierre, hacer `UPDATE turnos_caja SET token_admin_jti = NULL` para invalidar el token permanentemente.

---

#### `GET /api/turnos-caja/historial`

> Consulta de cierres históricos. Filtrada automáticamente por las sucursales asignadas al usuario autenticado, sin importar qué `sucursal_id` envíe en los params.

| | |
|---|---|
| **Permiso** | `turnos_caja:historial` (Administrador o Auditor) |
| **Query params** | `fecha_desde?` (Date), `fecha_hasta?` (Date), `caja_id?` (UUID), `sucursal_id?` (UUID), `cajero_id?` (UUID) |

```json
// Response 200
[
  {
    "id": "...",
    "caja_codigo": "CAJA-01",
    "cajero_nombre": "Juan Pérez",
    "administrador_nombre": "Carlos Gómez",
    "fecha_operacion": "2026-07-22",
    "diferencia_total": -50.00,
    "fecha_hora_cierre": "2026-07-22T18:05:00Z"
  }
]
```

---

### Grupo D: Retiros parciales `/api/turnos-caja/{turno_id}/retiros`

---

#### `GET /api/turnos-caja/{turno_id}/retiros`

| | |
|---|---|
| **Permiso** | `retiros_parciales:listar` |
| **Estado requerido** | Cualquiera excepto `CERRADO` |
| **Response 200** | `list[RetiroParcialOut]` |

```json
[{
  "id": 15,
  "monto": 2000.00,
  "concepto": "Envío a Blindado",
  "proveedor": "Loomis",
  "evidencia_url": "https://...",
  "creado": "2026-07-22T14:30:00Z"
}]
```

---

#### `POST /api/turnos-caja/{turno_id}/retiros`

> Registra un egreso parcial de efectivo. Inmutable una vez creado (RN-RET-003). Solo disponible mientras la caja está operando.

| | |
|---|---|
| **Permiso** | `retiros_parciales:crear` |
| **Estado requerido** | `OPERANDO` — no se permiten retiros con la caja en conteo (RN-CIE-001) |
| **Response 201** | `RetiroParcialOut` |

```json
// Request
{
  "metodo_pago_id": "...",
  "monto": 2000.00,
  "concepto_egreso_id": 1,
  "proveedor_id": 2,
  "evidencia_url": "https://storage.../comprobante.jpg"
}
```

| Código | Motivo |
|---|---|
| `400` | `evidencia_url` vacía (RN-RET-002) |
| `409` | Turno no está en `OPERANDO` |

> **Nota de implementación**: Al crear el retiro, también insertar en `movimientos_caja` con `tipo='E'` y `concepto='retiro_parcial'`. Esto hace que el saldo esperado disminuya correctamente al cierre.

---

## 7. Integración con flujos existentes

Los servicios de cobro ya existentes (`pagos_estancia`, check-outs) deben también escribir en `movimientos_caja` para que el cálculo del esperado sea correcto.

**En `app/services/pagos_estancia.py`** (y cualquier otro servicio que registre cobros):

```python
# Al registrar un cobro exitoso, agregar:
await movimientos_caja.registrar(
    conn,
    turnocaja_id=turno_activo_id,   # obtener con turnos_caja.obtener_activo_por_caja()
    metodo_pago_id=metodo_pago_id,
    tipo='I',                        # ingreso
    concepto='cobro_estancia',
    monto=monto,
    referencia_id=pago_id,           # id del registro en pagos_estancia
    creado_por=usuario_id
)
```

Esto requiere que el endpoint de cobro conozca el `turnocaja_id` activo de la caja. Se obtiene consultando `turnos_caja.obtener_activo_por_caja(conn, caja_id)` antes de registrar el pago.

> **Importante**: Si el turno está en estado `EN_CONTEO`, `ESPERANDO_REVISION`, `BALANCE_REVELADO` o `CERRADO`, el backend debe rechazar el cobro con `409 Conflict` (RN-CIE-001 / RN-APE-005).

---

## 8. Orden recomendado de implementación

### Fase 1: Base de datos

1. `sql/migrations/020_corte_caja_catalogos.sql` — catálogos + ALTER TABLE (sin dependencias)
2. `sql/migrations/021_corte_caja_core.sql` — tablas core (depende de 020)
3. `sql/migrations/022_permisos_corte_caja.sql` — permisos del módulo

### Fase 2: Capa de dominio y schemas

4. `app/models/turno_caja.py` — dataclasses + Enum de estados
5. `app/schemas/turno_caja.py` — schemas Pydantic completos

### Fase 3: Repositories

6. `app/repositories/cajas.py`
7. `app/repositories/movimientos_caja.py` — función `registrar()` solamente
8. `app/repositories/retiros_parciales.py`
9. `app/repositories/turnos_caja.py` — el más complejo, depende de los anteriores

### Fase 4: Servicios y PDF

10. `app/services/turno_caja.py` — lógica de negocio completa
11. `app/services/pdf_turno_caja.py` — generador del comprobante

### Fase 5: Routers y registro

12. `app/api/routers/cajas.py` — registrar en `app/main.py`
13. `app/api/routers/turnos_caja.py` — registrar en `app/main.py`

### Fase 6: Integración

14. Modificar `app/services/pagos_estancia.py` para escribir en `movimientos_caja`
15. Agregar validación de estado `EN_CONTEO`/`CERRADO` en endpoints de cobro existentes

---

## Apéndice: Diagrama de estados por endpoint

```
POST /api/turnos-caja                         ──────────────────────► OPERANDO
POST /api/turnos-caja/{id}/iniciar-conteo     OPERANDO ────────────► EN_CONTEO
POST /api/turnos-caja/{id}/cancelar           EN_CONTEO ───────────► OPERANDO
POST /api/turnos-caja/{id}/conteo             EN_CONTEO ───────────► ESPERANDO_REVISION
POST /api/turnos-caja/{id}/revision-admin     ESPERANDO_REVISION ──► BALANCE_REVELADO
POST /api/turnos-caja/{id}/confirmar          BALANCE_REVELADO ────► CERRADO
```
