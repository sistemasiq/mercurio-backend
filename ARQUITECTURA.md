# Arquitectura del Backend — Mercurio

Backend construido con **FastAPI** y **SQLAlchemy async** sobre **PostgreSQL**.

---

## Estructura de carpetas

```
app/
├── core/
│   └── config.py          # Variables de entorno (SECRET_KEY, DATABASE_URL, etc.)
├── db/
│   └── database.py        # Motor async, sesión y Base declarativa
├── dependencies/
│   └── __init__.py        # get_current_user — valida el JWT en cada request
├── exceptions/
│   └── __init__.py        # Excepciones HTTP reutilizables (NoEncontrado, CredencialesInvalidas)
├── models/                # Modelos ORM — representan las tablas de la DB
├── schemas/               # Schemas Pydantic — validan y serializan datos HTTP
├── services/              # Lógica de negocio — queries, cálculos, reglas
└── routes/                # Endpoints HTTP — reciben requests y devuelven responses
main.py                    # App FastAPI, registro de routers, CORS
```

---

## Capas y responsabilidades

```
Cliente HTTP
     │  JSON { "reservacion_id": "...", "monto": 500 }
     ▼
  ROUTE             recibe el request, inyecta sesión y usuario
     │
     ▼
  SCHEMA (Create)   valida que monto > 0, que los UUIDs existan, etc.
     │
     ▼
  SERVICE           hace la query, descuenta el saldo de la reservación
     │
     ▼
  MODEL (ORM)       escribe en las tablas pagos_reservacion y reservaciones
     │
     ▼
  PostgreSQL
     │
     ▼
  SCHEMA (Out)      serializa el resultado
     │
     ▼
  Cliente HTTP
     │  JSON { "id": "...", "monto": 500, "fecha_pago": "..." }
```

---

## Ejemplo completo — Pagos de Reservación

Este ejemplo muestra cómo se conectan las 4 capas usando el módulo `pagos_reservacion`.

### 1. Model (`app/models/pagos_reservacion.py`)

Define la tabla en la base de datos. El cliente nunca lo ve directamente.

```python
class PagosReservacionModel(Base):
    """Registro de cada pago realizado contra una reservación."""

    __tablename__ = "pagos_reservacion"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    reservacion_id = Column(PGUUID(as_uuid=True), nullable=False)
    metodo_pago_id = Column(PGUUID(as_uuid=True), nullable=False)
    monto = Column(Numeric(10, 2), nullable=False)
    fecha_pago = Column(DateTime, nullable=False)
    notas = Column(String(255), nullable=True)
    creado_por = Column(PGUUID(as_uuid=True), nullable=True)

    reservacion = relationship("ReservacionModel", back_populates="pagos")
    metodo_pago = relationship("MetodosPagoModel", back_populates="pagos")
```

### 2. Schema (`app/schemas/pagos_reservacion.py`)

Define qué datos acepta el request y qué devuelve la respuesta.

```python
class PagosReservacionCreate(BaseModel):
    reservacion_id: UUID
    metodo_pago_id: UUID
    monto: Decimal = Field(..., gt=0)   # obligatorio, mayor a 0
    notas: str | None = None            # opcional

class PagosReservacionUpdate(BaseModel):
    metodo_pago_id: UUID | None = None
    monto: Decimal | None = Field(None, gt=0)
    notas: str | None = None

class PagosReservacionOut(PagosReservacionBase):
    id: UUID
    fecha_pago: datetime    # el cliente no lo manda, el service lo genera
    creado_por: UUID | None = None

    model_config = {'from_attributes': True}
```

### 3. Service (`app/services/pagos_reservacion.py`)

Contiene la lógica: registra el pago y descuenta el saldo de la reservación.

```python
async def listar_por_reservacion(session: AsyncSession, reservacion_id: UUID) -> list[PagosReservacionModel]:
    result = await session.execute(
        select(PagosReservacionModel).where(PagosReservacionModel.reservacion_id == reservacion_id)
    )
    return result.scalars().all()


async def obtener(session: AsyncSession, pago_id: UUID) -> PagosReservacionModel:
    row = await session.get(PagosReservacionModel, pago_id)
    if not row:
        raise NoEncontrado("Pago")
    return row


async def crear(session: AsyncSession, body: PagosReservacionCreate) -> PagosReservacionModel:
    now = datetime.now(timezone.utc)
    pago = PagosReservacionModel(**body.model_dump(), fecha_pago=now)
    session.add(pago)

    # descuenta el monto del saldo de la reservación
    reservacion = await session.get(ReservacionModel, body.reservacion_id)
    if reservacion:
        reservacion.saldo_pendiente -= body.monto
        reservacion.modificado = now.isoformat()

    await session.commit()
    await session.refresh(pago)
    return pago


async def actualizar(session: AsyncSession, pago_id: UUID, body: PagosReservacionUpdate) -> PagosReservacionModel:
    row = await obtener(session, pago_id)
    monto_anterior = row.monto
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(row, field, value)

    # ajusta saldo si cambió el monto
    if body.monto is not None:
        reservacion = await session.get(ReservacionModel, row.reservacion_id)
        if reservacion:
            reservacion.saldo_pendiente += monto_anterior - body.monto
            reservacion.modificado = datetime.now(timezone.utc).isoformat()

    await session.commit()
    await session.refresh(row)
    return row


async def eliminar(session: AsyncSession, pago_id: UUID) -> None:
    row = await obtener(session, pago_id)

    # regresa el monto al saldo de la reservación
    reservacion = await session.get(ReservacionModel, row.reservacion_id)
    if reservacion:
        reservacion.saldo_pendiente += row.monto
        reservacion.modificado = datetime.now(timezone.utc).isoformat()

    await session.delete(row)
    await session.commit()
```

### 4. Route (`app/routes/pagos_reservacion.py`)

Recibe el request, inyecta dependencias y llama al service. No contiene lógica.

```python
router = APIRouter(prefix="/api/pagos-reservacion", tags=["Pagos de Reservación"])


@router.get("/reservacion/{reservacion_id}", response_model=list[PagosReservacionOut])
async def listar_pagos_reservacion(
    reservacion_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
):
    return await svc.listar_por_reservacion(session, reservacion_id)


@router.get("/{pago_id}", response_model=PagosReservacionOut)
async def obtener_pago(
    pago_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
):
    return await svc.obtener(session, pago_id)


@router.post("", response_model=PagosReservacionOut, status_code=status.HTTP_201_CREATED)
async def crear_pago(
    body: PagosReservacionCreate,
    session: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
):
    return await svc.crear(session, body)


@router.patch("/{pago_id}", response_model=PagosReservacionOut)
async def actualizar_pago(
    pago_id: UUID,
    body: PagosReservacionUpdate,
    session: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
):
    return await svc.actualizar(session, pago_id, body)


@router.delete("/{pago_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_pago(
    pago_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: str = Depends(get_current_user),
):
    await svc.eliminar(session, pago_id)
```

### 5. Registro en `main.py`

```python
from app.routes.pagos_reservacion import router as pagos_reservacion_router

app.include_router(pagos_reservacion_router)
```

---

## Qué hace cada capa en resumen

| Capa | Archivo | Responsabilidad |
|---|---|---|
| **Model** | `app/models/` | Define la tabla y sus columnas en PostgreSQL |
| **Schema** | `app/schemas/` | Valida el request, serializa el response |
| **Service** | `app/services/` | Lógica de negocio, queries, cálculos |
| **Route** | `app/routes/` | Recibe HTTP, inyecta dependencias, llama al service |

> La route no sabe nada de la DB. El service no sabe nada de HTTP. Cada capa tiene una sola responsabilidad.

---

## Autenticación

Todas las rutas (excepto `/api/auth/login`) requieren un JWT en el header:

```
Authorization: Bearer <token>
```

`get_current_user` en `app/dependencies/` decodifica el token y devuelve el email del usuario. Si el token es inválido o falta, lanza `401 Unauthorized`.

---

## Módulos del sistema

| Módulo | Tabla | Descripción |
|---|---|---|
| `sucursal` | `sucursales` | Sedes donde se realizan eventos |
| `tipos_evento` | `tipos_evento` | Catálogo: cumpleaños, boda, graduación, etc. |
| `metodos_pago` | `metodos_pago` | Catálogo: efectivo, tarjeta, transferencia, etc. |
| `extras` | `extras` | Servicios adicionales (globales o por sucursal) |
| `paquetes` | `paquetes` | Paquetes de servicio por sucursal |
| `paquete_tipos_evento` | `paquete_tipos_evento` | Relación paquete ↔ tipo de evento |
| `reservaciones` | `reservaciones` | Reservaciones de eventos |
| `reservacion_extras` | `reservacion_extras` | Extras seleccionados por reservación |
| `pagos_reservacion` | `pagos_reservacion` | Pagos registrados contra una reservación |

---

## Convenciones

- **Soft delete**: los registros nunca se borran físicamente, se marca `activo = False`
- **Fechas**: se guardan como `String` en formato ISO 8601 (`2024-06-22T10:00:00+00:00`)
- **UUIDs**: todas las PKs son UUID v4 generados automáticamente
- **Precios**: se usan `Numeric(10, 2)` en DB y `Decimal` en schemas para evitar errores de punto flotante
