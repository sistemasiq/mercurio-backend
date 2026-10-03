# Documento de Especficación Técnica: Módulo de Cierre de Caja (POS)

Este documento detalla el diseño arquitectónico, flujo funcional, casos de uso, máquina de estados, modelo de dominio, diseño de API REST y arquitectura frontend para el módulo de **Cierre de Caja** de la plataforma Mercurio. El diseño se integra con una arquitectura existente basada en **FastAPI (Backend)**, **PostgreSQL (Base de Datos)**, **Vue 3 + Quasar (Frontend)** y **Pinia (Estado Global)**.

---

## Paso 1: Análisis Funcional

El módulo de **Cierre de Caja** tiene como propósito consolidar la actividad financiera de un turno de trabajo o terminal de punto de venta (POS) específico, comparando los valores registrados por el sistema contra el efectivo y comprobantes físicos declarados por el cajero. Este proceso garantiza el control de flujo de efectivo, la detección oportuna de discrepancias y la auditoría de operaciones en tienda.

El módulo está estructurado en cuatro áreas funcionales principales bajo mi responsabilidad:

### 1. Pantalla de Cierre de Caja (Arqueo de Caja)
* **Propósito**: Permitir al cajero registrar la declaración del dinero físico y otros comprobantes en caja al finalizar su turno.
* **Consolidación Financiera (Backend)**:
  * Al iniciar el conteo, el backend calcula el **Monto Esperado** de forma dinámica e independiente para cada método de pago registrado en el catálogo del sistema (`MetodoPagoCatalogo`) que haya tenido movimientos en el turno activo:
    $$\text{Esperado}_{\text{método}} = \text{Fondo Inicial}_{\text{método}} + \sum(\text{Cobros}_{\text{método}}) - \sum(\text{Egresos/Retiros}_{\text{método}})$$
  * El frontend no realiza cálculos de saldo esperado ni comparaciones de discrepancias. El frontend únicamente suma las denominaciones físicas de efectivo declaradas y los montos capturados para otros métodos de pago.
* **Cierre a Ciegas (Blind Close)**: El cajero no ve el saldo esperado ni la diferencia calculada por el backend en ningún momento del conteo. Solo introduce los montos físicos.
* **Bloqueo de la Caja**: Al iniciar el proceso de conteo, el estado del turno pasa a `EN_CONTEO`, bloqueando la creación de nuevas ventas, devoluciones o retiros en el backend para esa caja física.

### 2. Flujo de Revisión Administrativa del Cierre (Firma Dual)
* **Propósito**: Registrar el cierre del turno mediante una estricta segregación de funciones, donde el administrador no realiza un segundo conteo ni valida físicamente el efectivo, sino que revisa las diferencias calculadas por el sistema, registra observaciones y deja evidencia administrativa del arqueo para autorizar el cierre definitivo.
* **Fase 1: Conteo Físico (Cajero)**:
  * El cajero declara el dinero físico en caja y presiona "Enviar Conteo", autenticándose mediante la introducción de su **PIN de seguridad de 6 dígitos**.
  * A partir de este momento, el conteo queda congelado, el cajero ya no puede modificar el arqueo y el turno cambia al estado `ESPERANDO_REVISION`.
* **Fase 2: Autenticación del Administrador (Modal de Elevación Temporal de Privilegios)**:
  * La sesión del cajero se mantiene activa de fondo. El POS muestra un **Overlay de Autenticación Administrativa** bloqueando la interacción general.
  * El administrador ingresa sus **credenciales oficiales de la plataforma (Usuario/Email y Contraseña)**.
  * El backend valida las credenciales y verifica que el administrador tenga permisos administrativos sobre la sucursal de la caja física. Si es exitoso, el backend emite un token de autorización temporal (de un solo uso) para consultar los datos del arqueo y el estado de la caja transiciona a `BALANCE_REVELADO`.
* **Fase 3: Consulta de Balance y Observaciones**:
  * La pantalla de la terminal POS revela el balance completo: montos declarados, montos esperados y la diferencia por método de pago.
  * Si la diferencia (declarado - esperado) es distinta de cero en cualquier método de pago, el campo **Observaciones** se vuelve obligatorio (mínimo 15 caracteres) para documentar el motivo conocido o el acuerdo administrativo alcanzado. Si no existe diferencia, las observaciones son opcionales.
* **Fase 4: Finalización del Proceso e Invalidation del Token Temporal**:
  * El administrador confirma el cierre presionando "Confirmar Cierre". No se vuelve a solicitar la contraseña.
  * El backend registra el turno en estado `CERRADO` definitivamente, genera automáticamente el comprobante en PDF e inicia su descarga local.
  * Al completarse el proceso, el frontend destruye el token de autorización temporal del administrador en la memoria reactiva del store de Pinia, el overlay se cierra, la sesión del cajero continúa activa de fondo sin alteraciones y la aplicación redirige automáticamente al Dashboard.

### 3. Historial de Arqueos
* **Propósito**: Permitir la consulta de todos los cierres históricos correspondientes a las sucursales asignadas al usuario.
* **Capacidades**:
  * **Detalle del Cierre**: Vista del comparativo esperado vs. declarado para cada método de pago y el desglose de efectivo por denominaciones.
  * **Trazabilidad**: Registra la hora de apertura, hora de inicio de conteo, hora de revisión administrativa, hora de cierre, cajero responsable y administrador autorizante.

---

## Paso 2: Reglas de Negocio

### Apertura de Caja (APE)
* **RN-APE-001 (Turno Único Activo por Cajero):** Un cajero solo puede tener un turno de caja activo en el sistema. No se le permitirá abrir un nuevo turno si ya cuenta con uno abierto en cualquier sucursal o terminal.
* **RN-APE-002 (Terminal Exclusiva):** Una terminal POS física solo puede tener un turno de caja activo a la vez.
* **RN-APE-003 (Fondo Inicial Obligatorio):** Todo proceso de apertura de caja requiere el registro obligatorio de un fondo inicial de efectivo (declaración manual, pudiendo ser cero pero nunca negativa).
* **RN-APE-004 (Restricción por Sucursal en Apertura):** Un usuario cajero solo puede abrir turnos de cajas físicas que pertenezcan a las sucursales asignadas a su perfil de usuario en el sistema.
* **RN-APE-005 (Apertura Obligatoria para Transar):** Mientras una caja física no tenga un turno en estado `OPERANDO`, el backend rechazará cualquier operación transaccional (ventas, check-in, check-out, alimentos, cobros o retiros parciales) asociada a dicha caja.
* **RN-APE-006 (Asociación Inmutable de Caja y Turno):** Un turno operativo permanece asociado a la misma caja física y al mismo cajero desde su apertura hasta su cierre definitivo. No se permite cambiar de caja ni transferir la propiedad del turno durante su ejecución.

### Operación y Concurrencia (OPE)
* **RN-OPE-001 (Asociación Directa de Cobro):** Los ingresos pertenecen estrictamente a la caja donde ocurre el cobro. Si un cliente realiza Check-In por "Caja 1" y Check-Out por "Caja 2", los montos de Check-In se registran en Caja 1 y los de Check-Out en Caja 2 de manera inmutable.
* **RN-OPE-002 (Sincronización en Tiempo Real):** Todas las cajas trabajan de forma concurrente. El sistema notificará vía WebSocket cambios de estado de los turnos para evitar colisiones operativas (ej. intentar cobrar en una caja que ha iniciado conteo).
* **RN-OPE-003 (Cálculo del Esperado Dinámico):** El cálculo del monto esperado en caja para un método de pago se realiza en backend sumando y restando los movimientos registrados para ese método de pago durante el turno activo.
* **RN-OPE-004 (Advertencia de Retiro Parcial):** Si el saldo acumulado en efectivo en caja supera un umbral máximo parametrizado por la sucursal, el POS mostrará una advertencia al cajero indicando que es obligatorio realizar un retiro parcial.
* **RN-OPE-005 (Consolidación y Privacidad en Dashboard):** El Dashboard Administrativo consolida la operación de todas las cajas de la sucursal, mientras que cada cajero en su terminal únicamente visualiza la información correspondiente a su turno activo.
* **RN-OPE-006 (Notificación de Bloqueo por WebSocket):** Cuando una caja cambia de estado de `OPERANDO` a `EN_CONTEO`, el sistema emitirá un evento vía WebSocket para notificar a las demás terminales de la sucursal, bloqueando intentos de cobros concurrentes sobre la caja en arqueo.

### Retiros Parciales (RET)
* **RN-RET-001 (Estructuración de Retiros):** Los retiros parciales de caja deben registrarse seleccionando obligatoriamente un Proveedor o un concepto de traslado (ej. "Envío a Blindado"), la Sucursal (derivada de la Caja) y el concepto contable.
* **RN-RET-002 (Evidencia Obligatoria):** Todo retiro parcial requiere el registro de una referencia física o URL de comprobante digitalizado.
* **RN-RET-003 (Inmutabilidad de Egresos):** Los registros de retiros parciales son inmutables. Inhabilitan la edición y el borrado físico de la salida de efectivo.

### Cierre y Conteo de Caja (CIE)
* **RN-CIE-001 (Bloqueo en Conteo):** Al cambiar el estado de un turno de caja a `EN_CONTEO`, el backend rechazará cualquier nueva transacción de venta, cobro o retiro parcial para ese turno de caja, congelando los saldos en tiempo real.
* **RN-CIE-002 (Ocultamiento del Esperado):** Durante el proceso de conteo físico, la pantalla del frontend ocultará el saldo esperado y las diferencias. El cajero solo introduce piezas físicas por denominación y comprobantes.
* **RN-CIE-003 (Cancelación Exclusiva por el Usuario en Conteo):** El proceso de cierre solo puede cancelarse si el cajero selecciona explícitamente la acción "Cancelar Cierre" en la pantalla antes de enviar el conteo.
* **RN-CIE-004 (Efectos de la Cancelación):** Al cancelar, se eliminan todos los conteos capturados en memoria, el turno de caja vuelve al estado `OPERANDO` y se desbloquea el POS. Si posteriormente se inicia el cierre, el conteo debe comenzar desde cero. No se permiten guardar borradores parciales.
* **RN-CIE-005 (Renderizado Dinámico de Métodos de Pago):** En la pantalla de conteo, solo se mostrarán para captura los métodos de pago que registraron movimientos reales durante el turno.
* **RN-CIE-006 (Sin Cancelación Automática):** No existen cancelaciones basadas en tiempo (timeout). El turno de caja permanecerá bloqueado en `EN_CONTEO` o `ESPERANDO_REVISION` el tiempo necesario hasta que se complete la acción correspondiente.

### Autorización Administrativa (VAL)
* **RN-VAL-001 (Validación de Conteo Congelado):** Una vez enviado el conteo por el cajero (estado `ESPERANDO_REVISION`), el arqueo ya no puede ser cancelado ni modificado por el cajero. Queda congelado hasta la revisión por el administrador.
* **RN-VAL-002 (Autenticación Robusta del Administrador):** Antes de revelar el balance del cierre, el administrador debe autenticarse en el sistema mediante sus credenciales oficiales (Usuario/Email y Contraseña).
* **RN-VAL-003 (Restricción de Sucursal para el Administrador):** El administrador únicamente puede autenticarse para autorizar turnos de cajas pertenecientes a las sucursales donde tenga permisos administrativos explícitamente asignados en el sistema (`UsuarioSucursal`). No puede recibir cierres de cajas de otras sucursales.
* **RN-VAL-004 (Desbloqueo de Balance):** El saldo esperado, declarado y las diferencias solo serán visibles para el administrador en la interfaz de usuario una vez que sus credenciales hayan sido validadas exitosamente y el estado pase a `BALANCE_REVELADO`.
* **RN-VAL-005 (Observación Obligatoria ante Diferencias):** Si existe una diferencia distinta de cero (positiva o negativa) en cualquier método de pago, el Administrador debe registrar obligatoriamente una observación explicativa (mínimo 15 caracteres).
* **RN-VAL-006 (Confirmación Final Única e Inmutable):** Tras autenticarse y registrar observaciones, el administrador finaliza la revisión presionando "Confirmar Cierre". No se solicita nuevamente la contraseña. No existe opción de reconteo o edición posterior; los montos declarados por el cajero son definitivos.
* **RN-VAL-007 (Cierre de Contexto Administrativo y Retorno):** Al presionar "Confirmar Cierre", el sistema cambia el estado del turno a `CERRADO`, genera el PDF e inicia su descarga en el navegador. De forma inmediata, se elimina el contexto temporal de autenticación administrativa y el sistema vuelve automáticamente a la interfaz de usuario del cajero, redirigiendo al Dashboard.

### Auditoría e Inmutabilidad (AUD)
* **RN-AUD-001 (Auditoría Estándar Obligatoria):** Todas las entidades transaccionales del módulo de caja deben incluir los campos de auditoría estándar.
* **RN-AUD-002 (Entidades de Auditoría Inmutable):** Las tablas `MovimientoCaja`, `RetiroParcial`, `TurnoCajaMetodoPago` y `TurnoCajaDesgloseEfectivo` son estrictamente inmutables.

---

## Paso 3: Casos de Uso

A continuación se detallan los casos de uso principales que gobiernan el ciclo de vida del Turno de Caja.

### CU-01: Apertura de Caja
* **Objetivo**: Inicializar un turno de caja física asociando un cajero y declarando el fondo inicial.
* **Actores**: Cajero.
* **Precondiciones**:
  * La caja física está configurada y activa en el sistema.
  * La caja física no cuenta con un turno activo (`TurnoCaja` en estado distinto a `OPERANDO`, `EN_CONTEO`, `ESPERANDO_REVISION` o `BALANCE_REVELADO`).
  * El cajero no tiene otro turno activo en el sistema.
  * El cajero pertenece a la sucursal de la caja física (`UsuarioSucursal`).
* **Flujo Principal**:
  1. El cajero ingresa a la terminal POS. El sistema detecta que no hay turno operativo activo para dicha caja.
  2. El sistema solicita obligatoriamente el ingreso del **Fondo Inicial de Efectivo**.
  3. El cajero introduce el monto en efectivo y presiona "Abrir Turno".
  4. El backend registra el turno (`TurnoCaja`), cambia su estado a `OPERANDO` y registra el fondo inicial.
* **Flujos Alternativos / Excepciones**:
  * **Excepción 1**: El cajero ingresa un monto negativo $\rightarrow$ El sistema bloquea el envío y muestra error de validación.
  * **Excepción 2**: El cajero ya tiene otro turno abierto en otra terminal $\rightarrow$ El backend devuelve `400 Bad Request` y no permite la apertura.
* **Postcondiciones**:
  * Se crea el registro inmutable de `TurnoCaja` en estado `OPERANDO`.
  * La caja queda habilitada para registrar ventas, check-ins y egresos.
* **Reglas de Negocio Involucradas**: `RN-APE-001`, `RN-APE-002`, `RN-APE-003`, `RN-APE-004`.

### CU-02: Inicio del Conteo
* **Objetivo**: Congelar las operaciones financieras de la terminal POS e iniciar la declaración física de arqueo.
* **Actores**: Cajero.
* **Precondiciones**:
  * `TurnoCaja` activo en estado `OPERANDO`.
* **Flujo Principal**:
  1. El cajero presiona el botón "Iniciar Cierre" en el POS.
  2. El backend transiciona el estado del turno a `EN_CONTEO`.
  3. El backend rechaza cualquier transacción de cobro o egreso posterior para este turno.
  4. El WebSocket notifica el estado `EN_CONTEO` a los demás terminales.
  5. El POS renderiza la pantalla de captura a ciegas (ocultando saldo esperado y diferencias).
* **Flujos Alternativos**: N/A.
* **Postcondiciones**:
  * `TurnoCaja` en estado `EN_CONTEO`.
  * La terminal POS física queda bloqueada para ventas y retiros.
* **Reglas de Negocio Involucradas**: `RN-CIE-001`, `RN-CIE-002`, `RN-OPE-006`.

### CU-03: Cancelación del Conteo
* **Objetivo**: Abortar el proceso de cierre antes de enviar la declaración, devolviendo la caja a su estado operativo habitual.
* **Actores**: Cajero.
* **Precondiciones**:
  * `TurnoCaja` en estado `EN_CONTEO`.
* **Flujo Principal**:
  1. El cajero presiona el botón "Cancelar Cierre" en la pantalla de conteo.
  2. El backend descarta los montos del arqueo en memoria reactiva.
  3. El backend actualiza el estado del turno a `OPERANDO`.
  4. La terminal POS queda desbloqueada y lista para operar cobros regulares.
* **Postcondiciones**:
  * `TurnoCaja` regresa a estado `OPERANDO`.
  * No se almacena ningún borrador del conteo físico.
* **Reglas de Negocio Involucradas**: `RN-CIE-003`, `RN-CIE-004`.

### CU-04: Envío del Conteo
* **Objetivo**: Declarar el dinero físico y comprobantes encontrados en caja, congelando la información para su revisión.
* **Actores**: Cajero.
* **Precondiciones**:
  * `TurnoCaja` en estado `EN_CONTEO`.
* **Flujo Principal**:
  1. El cajero ingresa el desglose físico por denominaciones de efectivo (`EfectivoDesgloseForm.vue`) y los montos acumulados por método de pago dinámico (`MetodoPagoMontoForm.vue`).
  2. El cajero ingresa su **PIN de seguridad de 6 dígitos**.
  3. El cajero presiona "Enviar Conteo".
  4. El backend valida el PIN. Si es correcto, almacena de forma inmutable el desglose físico y totales declarados.
  5. El backend cambia el estado del turno a `ESPERANDO_REVISION`.
  6. El frontend bloquea la pantalla y despliega el **Overlay de Autenticación Administrativa**.
* **Errores Posibles**:
  * **Error 401 (PIN Inválido)**: El PIN no coincide con el del cajero asignado. Se solicita ingresar el PIN nuevamente.
  * **Error 400 (Campos Incompletos)**: No se capturaron todos los campos de métodos de pago con movimientos.
* **Postcondiciones**:
  * `TurnoCaja` cambia a estado `ESPERANDO_REVISION`.
  * La declaración física del cajero queda inmutable y congelada.
* **Reglas de Negocio Involucradas**: `RN-VAL-001`, `RN-CIE-005`.

### CU-05: Autenticación del Administrador
* **Objetivo**: Autenticar a un usuario con privilegios administrativos en el POS local para habilitar el balance del arqueo.
* **Actores**: Administrador de Sucursal.
* **Precondiciones**:
  * `TurnoCaja` en estado `ESPERANDO_REVISION`.
  * El cajero envió su conteo físico y la pantalla está bloqueada por el overlay de autenticación administrativa.
* **Flujo Principal**:
  1. El Administrador se presenta físicamente en la terminal.
  2. En el overlay, ingresa su **Usuario o Email** y **Contraseña** oficiales de la plataforma.
  3. El backend valida sus credenciales y verifica su asociación a la sucursal del turno (`UsuarioSucursal`).
  4. Si las credenciales son válidas, el backend emite un token de autorización temporal (de un solo uso) y transiciona el estado del turno a `BALANCE_REVELADO`.
  5. El frontend cierra el overlay de bloqueo y renderiza la pantalla comparativa.
* **Errores Posibles**:
  * **Error 401 (Credenciales Inválidas)**: Credenciales incorrectas de administrador.
  * **Error 403 (Sucursal No Autorizada)**: El administrador no está asignado a la sucursal donde pertenece la caja física.
* **Postcondiciones**:
  * El estado de `TurnoCaja` cambia a `BALANCE_REVELADO`.
  * Se habilita visualmente la información financiera en el POS.
* **Reglas de Negocio Involucradas**: `RN-VAL-002`, `RN-VAL-003`, `RN-VAL-004`.

### CU-06: Revelación del Balance
* **Objetivo**: Visualizar y contrastar el dinero reportado por el sistema contra la declaración física del cajero.
* **Actores**: Administrador de Sucursal.
* **Precondiciones**:
  * `TurnoCaja` en estado `BALANCE_REVELADO`.
* **Flujo Principal**:
  1. El sistema muestra de forma estructurada en el lado izquierdo de la pantalla:
     * El desglose esperado por método de pago.
     * El desglose declarado por el cajero.
     * La diferencia exacta (sobrante o faltante).
  2. Si existe cualquier diferencia distinta de cero, el sistema bloquea el botón "Confirmar Cierre" y solicita de forma requerida el registro de observaciones.
* **Postcondiciones**: N/A (Fase de visualización y captura de observaciones).
* **Reglas de Negocio Involucradas**: `RN-VAL-004`, `RN-VAL-005`.

### CU-07: Confirmación del Cierre
* **Objetivo**: Concluir y registrar formalmente el cierre del turno operativo de caja.
* **Actores**: Administrador de Sucursal.
* **Precondiciones**:
  * `TurnoCaja` en estado `BALANCE_REVELADO`.
  * Si hay diferencias, se capturaron observaciones válidas (mínimo 15 caracteres).
* **Flujo Principal**:
  1. El Administrador presiona el botón "Confirmar Cierre".
  2. El backend consolida los saldos en el registro de `TurnoCaja`.
  3. El backend actualiza el estado del turno a `CERRADO`.
  4. El backend invoca al generador de PDF de comprobantes.
* **Postcondiciones**:
  * `TurnoCaja` en estado `CERRADO`.
  * Se genera el comprobante de cierre de forma definitiva.
* **Reglas de Negocio Involucradas**: `RN-VAL-005`, `RN-VAL-006`.

### CU-08: Descarga del Comprobante e Invalidation de Contexto
* **Objetivo**: Descargar el archivo de comprobante generado y retornar la terminal a la sesión normal del cajero sin dejar credenciales administrativas activas.
* **Actores**: Sistema (POS/Frontend).
* **Precondiciones**:
  * Confirmación de cierre exitosa por el backend (retorna el blob del PDF).
* **Flujo Principal**:
  1. El frontend recibe el blob del PDF del comprobante de cierre.
  2. El frontend inicia de forma automática la descarga del archivo PDF en el navegador local del POS.
  3. El frontend elimina de su store reactivo (`turnoCajaStore.ts`) el token de autorización temporal del administrador.
  4. El sistema cierra el modal/overlay de privilegios, volviendo a la sesión del cajero y redirige al Dashboard.
* **Postcondiciones**:
  * Comprobante descargado localmente.
  * Terminal POS limpia de privilegios administrativos, lista para la siguiente jornada.
* **Reglas de Negocio Involucradas**: `RN-VAL-007`.

### CU-09: Consulta de Historial
* **Objetivo**: Visualizar y auditar los cierres de caja históricos.
* **Actores**: Administrador / Auditor.
* **Precondiciones**:
  * El usuario tiene sesión activa con permisos de Administrador o Auditor.
* **Flujo Principal**:
  1. El usuario navega a la sección "Historial de Arqueos".
  2. Selecciona filtros: Rango de fechas, Caja física, Cajero o Sucursal.
  3. El sistema valida las sucursales asignadas al perfil del usuario.
  4. El sistema devuelve la lista de turnos cerrados correspondientes.
* **Postcondiciones**: N/A.
* **Reglas de Negocio Involucradas**: `RN-OPE-005`.

---

## Paso 4: Máquina de Estados del TurnoCaja

El flujo de estados para un turno operativo de caja (`TurnoCaja`) es estrictamente secuencial y lineal para evitar estados inconsistentes. Los nombres de los estados del backend y del frontend están unificados 1-a-1.

```mermaid
stateDiagram-v2
    [*] --> OPERANDO : Apertura de Caja (Fondo Inicial)
    
    OPERANDO --> EN_CONTEO : Cajero inicia cierre (Bloquea Caja)
    
    EN_CONTEO --> OPERANDO : Cajero presiona "Cancelar Cierre" (Borra conteos, desbloquea caja)
    
    EN_CONTEO --> ESPERANDO_REVISION : Cajero ingresa PIN y envía conteo (Congela conteo)
    
    ESPERANDO_REVISION --> BALANCE_REVELADO : Administrador ingresa credenciales válidas (Revela balance)
    
    BALANCE_REVELADO --> CERRADO : Administrador captura observaciones (si hay dif) y confirma cierre (Descarga PDF, elimina contexto de admin, vuelve a cajero, redirige)
    
    CERRADO --> [*] : Turno Finalizado Definitivamente
```

---

## Paso 5: Modelo de Dominio Conceptual

### Justificación Comercial del Diseño del Modelo
* **Turno Operativo Temporal:** `TurnoCaja` se modela con los atributos `fecha_operacion`, `hora_inicio` y `hora_fin` (asociados a un catálogo de turnos configurables) para permitir la máxima flexibilidad operativa sin atarse a enums rígidos de horarios.
* **Caja (Terminal Física):** Representa una terminal física o punto de venta del local. Cada turno pertenece exactamente a una caja física, y toda transacción financiera queda vinculada a dicha caja de manera unívoca durante la vida del turno, asegurando la trazabilidad del dinero físico al hardware y ubicación donde fue recolectado.
* **Extensibilidad de Métodos de Pago:** La entidad `TurnoCajaMetodoPago` desnormaliza los desgloses financieros para que el sistema pueda operar con un catálogo dinámico (`MetodoPagoCatalogo`), permitiendo agregar métodos de pago como cupones o criptomonedas en el futuro sin modificar el esquema de base de datos.
* **Desglose de Monedas y Billetes:** `TurnoCajaDesgloseEfectivo` guarda las piezas declaradas físicamente en el conteo de efectivo para auditoría forense.

### Diagrama de Clases Conceptual

```mermaid
classDiagram
    direction TB
    class Sucursal {
        id: Integer
        nombre: String
        activa: Boolean
        fecha_creacion: DateTime
        usuario_creacion: Integer
    }
    class Usuario {
        id: Integer
        nombre: String
        rol: String
        pin_hash: String
        email: String
        password_hash: String
        activo: Boolean
    }
    class UsuarioSucursal {
        usuario_id: Integer
        sucursal_id: Integer
    }
    class Caja {
        id: Integer
        nombre: String
        codigo: String
        sucursal_id: Integer
        activa: Boolean
    }
    class TurnoCatalogo {
        id: Integer
        nombre: String
        hora_inicio: Time
        hora_fin: Time
        activo: Boolean
    }
    class MetodoPagoCatalogo {
        id: Integer
        nombre: String
        codigo: String
        requiere_desglose_efectivo: Boolean
        activo: Boolean
    }
    class DenominacionCatalogo {
        id: Integer
        valor_nominal: Decimal
        tipo: String
        activa: Boolean
    }
    class TurnoCaja {
        id: Integer
        caja_id: Integer
        cajero_id: Integer
        turno_catalogo_id: Integer
        fecha_operacion: Date
        estado: String (OPERANDO, EN_CONTEO, ESPERANDO_REVISION, BALANCE_REVELADO, CERRADO)
        fondo_inicial_efectivo: Decimal
        fecha_hora_apertura: DateTime
        usuario_apertura_id: Integer
        fecha_hora_cierre: DateTime
        administrador_cierre_id: Integer
        observaciones: String
        fecha_creacion: DateTime
        usuario_creacion: Integer
        fecha_actualizacion: DateTime
        usuario_actualizacion: Integer
    }
    class TurnoCajaMetodoPago {
        <<Inmutable>>
        id: Integer
        turnocaja_id: Integer
        metodo_pago_id: Integer
        monto_esperado: Decimal
        monto_declarado: Decimal
        diferencia: Decimal
        cantidad_comprobantes: Integer
        fecha_creacion: DateTime
        usuario_creacion: Integer
    }
    class TurnoCajaDesgloseEfectivo {
        <<Inmutable>>
        id: Integer
        turnocaja_id: Integer
        denominacion_id: Integer
        cantidad_piezas: Integer
        total_monto: Decimal
        fecha_creacion: DateTime
        usuario_creacion: Integer
    }
    class MovimientoCaja {
        <<Inmutable>>
        id: Integer
        turnocaja_id: Integer
        monto: Decimal
        metodo_pago_id: Integer
        tipo_movimiento: String
        concepto_movimiento: String
        referencia_origen_id: Integer
        fecha_creacion: DateTime
        usuario_creacion: Integer
    }
    class RetiroParcial {
        <<Inmutable>>
        id: Integer
        turnocaja_id: Integer
        monto: Decimal
        concepto_egreso_id: Integer
        proveedor_id: Integer
        evidencia_url: String
        fecha_creacion: DateTime
        usuario_creacion: Integer
    }
    class ConceptoEgreso {
        id: Integer
        nombre: String
        activo: Boolean
    }
    class Proveedor {
        id: Integer
        nombre: String
        activo: Boolean
    }

    Usuario "1" --* "*" UsuarioSucursal
    Sucursal "1" --* "*" UsuarioSucursal
    Sucursal "1" --> "*" Caja
    Caja "1" --> "*" TurnoCaja
    Usuario "1" --> "*" TurnoCaja : Cajero / Administrador
    TurnoCatalogo "1" --> "*" TurnoCaja
    TurnoCaja "1" --> "*" MovimientoCaja
    TurnoCaja "1" --> "*" RetiroParcial
    TurnoCaja "1" --> "*" TurnoCajaMetodoPago
    TurnoCaja "1" --> "*" TurnoCajaDesgloseEfectivo
    TurnoCajaMetodoPago "*" --> "1" MetodoPagoCatalogo
    TurnoCajaDesgloseEfectivo "*" --> "1" DenominacionCatalogo
    MovimientoCaja "*" --> "1" MetodoPagoCatalogo
    RetiroParcial "*" --> "1" ConceptoEgreso
    RetiroParcial "*" --> "0..1" Proveedor
```

---

## Paso 6: Diseño de la API REST

Los endpoints de la API respetan de manera estricta la convención de Mercurio (recursos en plural, path params `{recurso_id}` y acciones como `POST /api/recurso/{id}/accion`). 

### 1. Obtener Turno Activo de la Caja
* **Ruta**: `GET /api/turnos-caja/activo`
* **Propósito**: Recuperar la información del turno actualmente operativo en el POS.
* **Autorización Requerida**: Sesión activa de cajero.
* **Request**: Vacío.
* **Response (`200 OK`)**:
  ```json
  {
    "id": 105,
    "caja_id": 3,
    "cajero_id": 12,
    "estado": "OPERANDO",
    "fecha_operacion": "2026-07-20",
    "fondo_inicial_efectivo": 1500.00,
    "fecha_hora_apertura": "2026-07-20T08:02:11Z"
  }
  ```
* **Códigos HTTP y Errores**:
  * `200 OK`: Turno recuperado con éxito.
  * `404 Not Found`: No existe ningún turno operativo abierto para esta terminal.
  * `401 Unauthorized`: Usuario no autenticado.

### 2. Apertura de Turno de Caja (Apertura)
* **Ruta**: `POST /api/turnos-caja`
* **Propósito**: Crear una nueva instancia de turno operativo de caja.
* **Autorización Requerida**: Sesión activa de cajero.
* **Request**:
  ```json
  {
    "caja_id": 3,
    "turno_catalogo_id": 1,
    "fondo_inicial_efectivo": 1500.00
  }
  ```
* **Response (`201 Created`)**:
  ```json
  {
    "id": 105,
    "estado": "OPERANDO",
    "fecha_hora_apertura": "2026-07-20T08:02:11Z"
  }
  ```
* **Validaciones**:
  * `fondo_inicial_efectivo` debe ser mayor o igual a 0.00.
  * El cajero debe pertenecer a la sucursal de la caja física (`UsuarioSucursal`).
* **Códigos HTTP y Errores**:
  * `201 Created`: Apertura exitosa.
  * `400 Bad Request`: El cajero ya cuenta con un turno activo en el sistema, o la terminal ya tiene un turno abierto (`RN-APE-001`, `RN-APE-002`).
  * `403 Forbidden`: El cajero no pertenece a la sucursal del POS.
* **Cambios de Estado**: Caja pasa a `OPERANDO`.

### 3. Iniciar Conteo (Bloqueo de Caja)
* **Ruta**: `POST /api/turnos-caja/{turno_id}/iniciar-conteo`
* **Propósito**: Bloquear la terminal e iniciar el proceso de arqueo físico.
* **Autorización Requerida**: Sesión activa de cajero (propietario del turno).
* **Request**: Vacío.
* **Response (`200 OK`)**:
  ```json
  {
    "id": 105,
    "estado": "EN_CONTEO"
  }
  ```
* **Códigos HTTP y Errores**:
  * `200 OK`: Transición de bloqueo exitosa.
  * `409 Conflict`: El turno no se encuentra en estado `OPERANDO`.
* **Cambios de Estado**: Transiciona a `EN_CONTEO`. A partir de este momento, el backend rechazará transacciones comerciales asociadas a este turno (`RN-CIE-001`).

### 4. Cancelar Conteo
* **Ruta**: `POST /api/turnos-caja/{turno_id}/cancelar`
* **Propósito**: Abortar el arqueo físico y desbloquear la caja antes del envío del conteo.
* **Autorización Requerida**: Sesión activa de cajero (propietario del turno).
* **Request**: Vacío.
* **Response (`200 OK`)**:
  ```json
  {
    "id": 105,
    "estado": "OPERANDO"
  }
  ```
* **Códigos HTTP y Errores**:
  * `200 OK`: Cancelación exitosa.
  * `409 Conflict`: El turno ya no se encuentra en estado `EN_CONTEO` (ej. ya fue enviado o cerrado).
* **Cambios de Estado**: Transiciona a `OPERANDO`. Se borran de base de datos o de memoria todos los datos temporales del arqueo.

### 5. Registrar Conteo del Cajero (Enviar Conteo)
* **Ruta**: `POST /api/turnos-caja/{turno_id}/conteo`
* **Propósito**: Enviar el arqueo físico realizado por el cajero y congelar el conteo.
* **Autorización Requerida**: Sesión activa de cajero.
* **Request**:
  ```json
  {
    "cajero_pin": "123456",
    "desglose_efectivo": [
      {
        "denominacion_id": 1,
        "cantidad_piezas": 10
      },
      {
        "denominacion_id": 2,
        "cantidad_piezas": 5
      }
    ],
    "declaracion_metodos_pago": [
      {
        "metodo_pago_id": 2,
        "monto_declarado": 500.00,
        "cantidad_comprobantes": 3
      }
    ]
  }
  ```
* **Response (`200 OK`)**:
  ```json
  {
    "id": 105,
    "estado": "ESPERANDO_REVISION"
  }
  ```
* **Validaciones**:
  * El PIN debe ser numérico y coincidir con el PIN hasheado del cajero del turno.
  * La lista de métodos de pago declarados debe incluir a todos los métodos de pago que registraron movimientos reales durante el turno.
* **Códigos HTTP y Errores**:
  * `200 OK`: Declaración recibida y congelada.
  * `401 Unauthorized`: PIN del cajero inválido.
  * `409 Conflict`: El turno no está en estado `EN_CONTEO`.
* **Cambios de Estado**: Transiciona a `ESPERANDO_REVISION`.

### 6. Autenticar Administrador y Revelar Balance
* **Ruta**: `POST /api/turnos-caja/{turno_id}/revision-admin`
* **Propósito**: Autenticar credenciales del administrador y revelar los saldos esperados y las diferencias calculadas en backend.
* **Autorización Requerida**: Sesión activa de cajero + Credenciales de Administrador en Body.
* **Request**:
  ```json
  {
    "admin_usuario": "admin.centro@mercurio.com",
    "admin_password": "AdminSecurePassword123"
  }
  ```
* **Response (`200 OK`)**:
  ```json
  {
    "temporal_auth_token": "token_temporal_admin_abc123",
    "balance": [
      {
        "metodo_pago_id": 1,
        "nombre": "Efectivo",
        "monto_esperado": 2350.00,
        "monto_declarado": 2350.00,
        "diferencia": 0.00,
        "cantidad_comprobantes": 0
      },
      {
        "metodo_pago_id": 2,
        "nombre": "Tarjeta Crédito",
        "monto_esperado": 500.00,
        "monto_declarado": 450.00,
        "diferencia": -50.00,
        "cantidad_comprobantes": 3
      }
    ]
  }
  ```
* **Validaciones**:
  * Credenciales de administrador correctas.
  * El administrador debe pertenecer a la misma sucursal de la caja física del turno (`RN-VAL-003`).
* **Códigos HTTP y Errores**:
  * `200 OK`: Autenticación exitosa y balance revelado.
  * `401 Unauthorized`: Credenciales de administrador incorrectas.
  * `403 Forbidden`: El administrador no pertenece a esta sucursal.
  * `409 Conflict`: El turno no se encuentra en estado `ESPERANDO_REVISION`.
* **Cambios de Estado**: Transiciona a `BALANCE_REVELADO`.

### 7. Confirmar Cierre y Descargar Comprobante
* **Ruta**: `POST /api/turnos-caja/{turno_id}/confirmar`
* **Propósito**: Consolidar el cierre definitivo de la caja y obtener el comprobante de cierre (PDF).
* **Autorización Requerida**: Token de elevación temporal del administrador en Headers (`Authorization: Bearer token_temporal_admin_abc123`).
* **Request**:
  ```json
  {
    "observaciones": "Faltante de $50 pesos por voucher extraviado de Tarjeta."
  }
  ```
* **Response (`200 OK`)**: Archivo binario (PDF) con cabecera `Content-Type: application/pdf` y `Content-Disposition: attachment; filename="comprobante_cierre_105.pdf"`.
* **Validaciones**:
  * Si la suma absoluta de las diferencias del balance es distinta de cero, el campo `observaciones` es obligatorio y debe tener al menos 15 caracteres (`RN-VAL-005`).
* **Códigos HTTP y Errores**:
  * `200 OK`: Cierre registrado y PDF generado.
  * `400 Bad Request`: Observaciones faltantes o muy cortas para un cierre con diferencias.
  * `401 Unauthorized`: Token temporal inválido o expirado.
  * `409 Conflict`: El turno no está en estado `BALANCE_REVELADO`.
* **Cambios de Estado**: Transiciona a `CERRADO` definitivamente. Se destruye el token temporal en el backend.

### 8. Obtener Historial de Arqueos (Vista Administrativa)
* **Ruta**: `GET /api/turnos-caja/historial`
* **Propósito**: Consultar cierres históricos para sucursales asignadas.
* **Autorización Requerida**: Administrador o Auditor.
* **Request Params**:
  * `fecha_desde` (Date, ISO-8601, opcional)
  * `fecha_hasta` (Date, ISO-8601, opcional)
  * `caja_id` (Integer, opcional)
  * `usuario_id` (Integer, opcional)
  * `sucursal_id` (Integer, opcional)
* **Response (`200 OK`)**:
  ```json
  [
    {
      "id": 105,
      "caja_codigo": "CAJA-03",
      "cajero_nombre": "Juan Pérez",
      "administrador_nombre": "Carlos Gómez",
      "fecha_operacion": "2026-07-20",
      "diferencia_total": -50.00,
      "fecha_hora_cierre": "2026-07-20T18:05:00Z"
    }
  ]
  ```
* **Validaciones**:
  * El backend filtrará implícitamente los resultados para mostrar únicamente registros correspondientes a las sucursales asignadas al Administrador/Auditor solicitante (`UsuarioSucursal`), independientemente de si se envió el parámetro `sucursal_id`.

---

## Paso 7: Arquitectura Frontend (Vue 3 + Quasar + Pinia)

El frontend respetará de forma estricta la arquitectura multicapa definida para el proyecto:

$$\text{Componente (UI)} \rightarrow \text{Service (Lógica/Mapeos)} \rightarrow \text{Api (Axios/Cliente HTTP)} \rightarrow \text{Backend}$$

### 1. Páginas (`src/pages/`)
* **`CierreCajaPage.vue`**:
  * *Responsabilidad*: Pantalla única de cierre a dos columnas.
  * *Comportamiento por Fases de la UI*:
    * **Fase 1: Conteo (Estado `EN_CONTEO`)**:
      * *Lado Izquierdo*: Formulario de arqueo físico. Renderiza `EfectivoDesgloseForm.vue` y los componentes `MetodoPagoMontoForm.vue` dinámicos.
      * *Lado Derecho*: Solicitud de PIN del Cajero y botón "Enviar Conteo". Botón visible para "Cancelar Cierre".
    * **Fase 2: Esperando Revisión (Estado `ESPERANDO_REVISION`)**:
      * *Lado Izquierdo*: Se bloquea visualmente y muestra que el conteo ha sido enviado y está congelado.
      * *Lado Derecho*: Muestra formulario de inicio de sesión temporal para el Administrador (campos Usuario/Email y Contraseña) en un overlay para desbloquear la información.
    * **Fase 3: Revisión y Balance (Estado `BALANCE_REVELADO`)**:
      * *Lado Izquierdo*: Se desbloquea y revela el balance comparativo (Esperado, Declarado, Diferencia y Comprobantes).
      * *Lado Derecho*: Muestra el campo de observaciones (obligatorio si hay diferencia) y el botón "Finalizar Recepción" para consolidar, descargar el comprobante en PDF, eliminar el contexto administrativo temporal de la memoria y retornar a la interfaz del cajero.

### 2. Componentes Especializados (`src/components/`)
* **`EfectivoDesgloseForm.vue`**:
  * *Responsabilidad*: Grilla interactiva con las denominaciones configuradas para efectivo. Calcula el total declarado de efectivo en el frontend.
  * *Propiedades*: `modelValue` (arreglo de desglose de efectivo).
* **`MetodoPagoMontoForm.vue`**:
  * *Responsabilidad*: Componente genérico para capturar el total y cantidad de comprobantes de métodos no monetarios.
  * *Propiedades*: `metodoPago`, `modelValue`.

### 3. Stores de Pinia (`src/stores/`)
* **`turnoCajaStore.ts`**:
  * *Responsabilidad*: Almacena el estado global del turno activo en la pantalla de cierre, alineando sus fases de forma unívoca con los estados del backend.
  * *Estado Reactivo*:
    * `fase`: Estado de la UI (`'OPERANDO' | 'EN_CONTEO' | 'ESPERANDO_REVISION' | 'BALANCE_REVELADO' | 'CERRADO'`).
    * `turnoActivo`: Datos generales del turno (`TurnoCaja`).
    * `metodosPagoActivos`: Catálogo de métodos de pago con movimientos reales.
    * `desgloseEfectivoBorrador`: Arreglo de piezas por denominación.
    * `declaracionMetodosBorrador`: Arreglo de montos por método.
    * `balanceRevelado`: Datos de diferencias y esperados devueltos por el backend tras validar las credenciales del administrador.
  * *Acciones*:
    * `cargarTurnoActivo()`: Solicita el turno y los métodos de pago dinámicos.
    * `iniciarConteo()`: Llama al backend para transicionar el turno a `EN_CONTEO` y bloquea el POS local.
    * `enviarConteoCajero(cajeroPin)`: Valida el PIN del cajero en backend y pasa el turno a `ESPERANDO_REVISION`.
    * `autenticarAdministrador(usuario, password)`: Envía las credenciales del administrador al backend. Si son válidas y pertenecen a la sucursal del turno, desbloquea los saldos, obtiene el balance y cambia la fase a `BALANCE_REVELADO`.
    * `cancelarProcesoCierre()`: Limpia borradores, llama al backend para regresar el estado del turno a `OPERANDO` y desbloquea el POS. Solo es ejecutable si el estado es `EN_CONTEO`.
    * `confirmarCierreDefinitivo(observaciones)`: Envía la confirmación del cierre (estado `CERRADO`), recibe el PDF de comprobante, procesa su descarga local. Posteriormente, destruye en el cliente el contexto temporal de la sesión administrativa (sin cerrar la sesión principal del cajero) y redirige al Dashboard.

### 4. API (`src/api/`)
* **`turnoCajaApi.ts`**:
  * *Responsabilidad*: Encapsula el cliente Axios de la aplicación.
  * *Endpoints*:
    * `GET /api/turnos-caja/activo`: Recupera el turno operativo abierto en el POS.
    * `GET /api/turnos-caja/{turno_id}/metodos-pago`: Obtiene los métodos de pago que tuvieron movimientos reales.
    * `POST /api/turnos-caja/{turno_id}/iniciar-conteo`: Transiciona el turno a `EN_CONTEO` y congela ventas.
    * `POST /api/turnos-caja/{turno_id}/conteo`: Envía el conteo físico y PIN del cajero (transiciona a `ESPERANDO_REVISION`).
    * `POST /api/turnos-caja/{turno_id}/revision-admin`: Envía credenciales de administrador (usuario, contraseña) para cambiar a `BALANCE_REVELADO` y recuperar saldos esperados y diferencias.
    * `POST /api/turnos-caja/{turno_id}/confirmar`: Envía confirmación del cierre con observaciones (cambia a `CERRADO` y devuelve el PDF).
    * `POST /api/turnos-caja/{turno_id}/cancelar`: Restablece el turno de caja al estado `OPERANDO`.

---

## Paso 8: Flujos de UI (Pantalla Única)

Toda la interacción del proceso de cierre ocurre en una pantalla única a dos columnas (`src/pages/CierreCajaPage.vue`). El flujo progresa modificando dinámicamente los componentes y estados visibles en el mismo layout de Quasar, guiando al usuario por las fases de seguridad del negocio.

### Fase 1: Conteo Físico (Estado `EN_CONTEO`)
* **Componentes Visibles**:
  * **Columna Izquierda (Formulario de Declaración)**:
    * Componente `EfectivoDesgloseForm.vue`: Tabla interactiva con inputs de texto para la cantidad de piezas por denominación (MXN: $1000, $500, $200, $100, $50, $20 en billetes; $10, $5, $2, $1, $0.50 en monedas).
    * Componentes `MetodoPagoMontoForm.vue` generados dinámicamente para métodos no monetarios (ej. Tarjetas, Cupones, Puntos) que registraron transacciones reales. Muestra el nombre del método y provee dos inputs: "Monto Declarado ($)" y "Cantidad de Comprobantes".
  * **Columna Derecha (Acciones y Autenticación)**:
    * Tarjeta de Resumen: Muestra el "Total Declarado" sumado en tiempo real en el frontend. Oculta saldos esperados y diferencias (Blind Close).
    * Input de Seguridad: Campo "PIN del Cajero" (tipo password, limitado a 6 caracteres).
    * Botón "Enviar Conteo" (color `primary` de Quasar, deshabilitado si no hay datos en el conteo de efectivo o si el PIN no tiene 6 dígitos).
    * Botón "Cancelar Cierre" (color `grey-7`, plano, visible para volver a operar).
* **Acciones Disponibles**:
  * Modificar piezas de denominaciones y montos de tarjetas/cupones.
  * Capturar el PIN del Cajero.
  * Presionar "Enviar Conteo" para registrar los datos.
  * Presionar "Cancelar Cierre". Dispara un diálogo `q-dialog` confirmando la acción. Si acepta, descarta los datos y redirige a `OPERANDO` restableciendo el POS.
* **Validaciones del Frontend**:
  * Los inputs de cantidad de piezas de efectivo solo aceptan números enteros no negativos.
  * Los montos declarados de tarjetas/vales aceptan decimales no negativos.
* **Estados de Carga y Fallos**:
  * Skeleton loaders en el lado izquierdo mientras la API carga la configuración de denominaciones y los métodos de pago dinámicos.
  * Si la llamada inicial de carga falla, se muestra un banner superior rojo (`q-banner`) con un botón "Reintentar".

### Fase 2: Esperando Revisión (Estado `ESPERANDO_REVISION`)
* **Componentes Visibles**:
  * **Columna Izquierda (Bloqueada)**:
    * El formulario de declaración se renderiza bajo un overlay semi-translúcido gris con el texto "Declaración Enviada con Éxito. Esperando presencia del Administrador para Revisión". Todos los inputs de cantidad y montos quedan deshabilitados en modo de solo lectura.
  * **Columna Derecha (Credenciales del Administrador)**:
    * Oculta el PIN del cajero y el botón de enviar.
    * Muestra el formulario **"Inicio de Sesión - Autorización de Turno"** con campos: "Usuario o Correo Electrónico del Administrador" y "Contraseña".
    * Botón "Iniciar Revisión" (color `primary` de Quasar, con un spinner de carga).
    * Se oculta el botón "Cancelar Cierre"; una vez enviado el conteo, el cajero ya no puede cancelar de manera autónoma (`RN-VAL-001`).
* **Acciones Disponibles**:
  * El Administrador introduce sus credenciales oficiales en el formulario de la terminal POS y presiona "Iniciar Revisión".
* **Validaciones del Frontend**:
  * Verifica formato de email en el campo de usuario.
  * Bloquea el envío si la contraseña tiene menos de 8 caracteres.
* **Estados de Carga y Fallos**:
  * Al presionar "Iniciar Revisión", el botón entra en estado de carga (`loading` en `q-btn`) y el formulario de credenciales se bloquea temporalmente.
  * Si las credenciales son incorrectas o el administrador no pertenece a la sucursal, se muestra una alerta `q-notify` de Quasar de color rojo con el mensaje de error correspondiente. Los inputs se limpian y se desbloquean para un nuevo intento.

### Fase 3: Revisión y Balance (Estado `BALANCE_REVELADO`)
* **Componentes Visibles**:
  * **Columna Izquierda (Balance Desbloqueado)**:
    * Desaparece el overlay gris de bloqueo.
    * Muestra una grilla comparativa estructurada por método de pago. Columnas: Método de Pago, Monto Esperado, Monto Declarado, Diferencia y Comprobantes.
    * Las filas con diferencia igual a cero se marcan en color de texto neutro. Las filas con diferencias distintas de cero (faltante o sobrante) muestran el monto de la diferencia en negrita y color rojo (negativo) o verde (positivo).
  * **Columna Derecha (Observaciones y Confirmación)**:
    * Formulario de observaciones administrativas. Contiene un input `q-input` de tipo área de texto ("Observaciones de la Sucursal") con un contador de caracteres.
    * Si la suma de las diferencias es distinta de cero, el input muestra el indicador rojo de "Requerido".
    * Botón "Confirmar Cierre" (color `negative` si hay diferencias, o `primary` si está cuadrado; se deshabilita si hay diferencias y la longitud de las observaciones es menor a 15 caracteres).
* **Acciones Disponibles**:
  * Capturar observaciones.
  * Presionar "Confirmar Cierre" para consolidar el proceso contable.
* **Estados de Carga y Fallos**:
  * Al presionar "Confirmar Cierre", el botón entra en estado de carga.
  * Si la API confirma con éxito y devuelve el PDF del comprobante, el frontend descarga de manera silenciosa y automática el archivo, limpia las variables reactivas de autorización temporal, cierra el overlay administrativo y redirige al cajero al Dashboard.
  * Si la API falla al confirmar el cierre (ej. error de red en el backend), se retienen los datos en pantalla y se muestra una notificación de error persistente ofreciendo la opción "Reintentar".

---

## Paso 9: Plan de Implementación (Fases de Desarrollo)

Este plan divide el desarrollo del módulo de Cierre de Caja en 4 fases secuenciales. Cada fase puede ser codificada, desplegada en entornos de desarrollo y probada de manera independiente.

### Fase 1: Estructura de Base de Datos y Modelos (Backend)
* **Objetivo**: Diseñar y desplegar la estructura de persistencia en PostgreSQL y los modelos en FastAPI.
* **Orden Recomendado**:
  1. Diseñar la migración con Alembic para agregar las tablas `MetodoPagoCatalogo`, `DenominacionCatalogo`, `TurnoCaja`, `TurnoCajaMetodoPago` y `TurnoCajaDesgloseEfectivo`.
  2. Implementar los modelos de SQLAlchemy correspondientes en el backend.
  3. Definir los esquemas de Pydantic para los requests y responses.
* **Pruebas Unitarias**:
  * Validar la restricción de inmutabilidad en base de datos para `TurnoCajaMetodoPago` y `TurnoCajaDesgloseEfectivo` (bloquear UPDATE y DELETE a nivel de ORM o mediante triggers).
* **Criterios de Aceptación**:
  * Las tablas se crean con sus claves foráneas correctas.
  * Se pueden poblar los catálogos de denominaciones oficiales y métodos de pago mediante scripts de seed.

### Fase 2: Servicios Contables y Endpoints de Operación (Backend)
* **Objetivo**: Desarrollar la lógica contable del backend para calcular el saldo esperado y las APIs de transición del cajero.
* **Orden Recomendado**:
  1. Implementar la función de servicio en FastAPI que calcula el saldo esperado de la caja sumando y restando los registros de la tabla `MovimientoCaja` y `RetiroParcial` de forma dinámica por método de pago.
  2. Desarrollar el endpoint `POST /api/turnos-caja/{turno_id}/iniciar-conteo`.
  3. Desarrollar el endpoint `POST /api/turnos-caja/{turno_id}/conteo` (validación de PIN de cajero y guardado inmutable de la declaración física).
  4. Desarrollar el endpoint `POST /api/turnos-caja/{turno_id}/cancelar`.
* **Pruebas de Integración (APIs)**:
  * Simular registros de ventas en efectivo y tarjeta, iniciar conteo y verificar que el endpoint `/conteo` rechace PINs incorrectos y guarde la información.
  * Verificar que una vez transicionado a `ESPERANDO_REVISION`, el endpoint `/cancelar` devuelva un código `409 Conflict`.
* **Criterios de Aceptación**:
  * El cálculo del esperado es preciso frente a retiros y cobros descentralizados.
  * El backend bloquea nuevas transacciones financieras cuando la caja está en `EN_CONTEO` o `ESPERANDO_REVISION`.

### Fase 3: Elevación de Privilegios, Confirmación y PDF (Backend)
* **Objetivo**: Implementar la autenticación del administrador, la validación final del cierre y la exportación de comprobantes.
* **Orden Recomendado**:
  1. Desarrollar el endpoint `/revision-admin` que valida el Usuario y Contraseña del Administrador y verifica la restricción de sucursal (`RN-VAL-003`), emitiendo el token temporal encriptado.
  2. Desarrollar el endpoint `/confirmar` que recibe las observaciones y el token temporal, valida el mínimo de 15 caracteres si hay diferencias y cambia el estado a `CERRADO`.
  3. Implementar el servicio generador de PDF (usando ReportLab o WeasyPrint) que construye el comprobante de cierre de caja detallado.
* **Pruebas de Integración**:
  * Validar que `/revision-admin` rechace administradores de otras sucursales.
  * Validar que `/confirmar` rechace solicitudes sin observaciones cuando el arqueo tenga diferencias.
* **Criterios de Aceptación**:
  * El token temporal de administrador se invalida inmediatamente después de confirmar el cierre.
  * La confirmación del cierre genera un archivo PDF binario correcto.

### Fase 4: Componentes, Store de Pinia e Integración de UI (Frontend)
* **Objetivo**: Desarrollar la interfaz del POS en Vue 3 con Quasar y conectar con las APIs.
* **Orden Recomendado**:
  1. Desarrollar la API de Axios `/src/api/turnoCajaApi.ts`.
  2. Desarrollar el store de Pinia `/src/stores/turnoCajaStore.ts` mapeando las fases de la UI 1-a-1.
  3. Implementar el componente especializado de efectivo (`EfectivoDesgloseForm.vue`) y el componente genérico de métodos dinámicos (`MetodoPagoMontoForm.vue`).
  4. Diseñar la maquetación de dos columnas de la página única `CierreCajaPage.vue` con sus overlays y fases.
  5. Integrar la descarga automática del PDF en el navegador tras la llamada exitosa de confirmación y el retorno seguro a la sesión del cajero.
  6. Configurar la suscripción WebSocket para notificar el bloqueo de la terminal al cambiar a `EN_CONTEO`.
* **Pruebas de Integración y End-to-End**:
  * Validar con Cypress o Vitest el flujo completo: Captura de efectivo $\rightarrow$ PIN cajero $\rightarrow$ Bloqueo $\rightarrow$ Autenticación admin en modal $\rightarrow$ Muestra balance $\rightarrow$ Error de observaciones requerido si hay diferencias $\rightarrow$ Envío exitoso $\rightarrow$ Descarga PDF $\rightarrow$ Cierre de modal y redirección al Dashboard.
* **Criterios de Aceptación**:
  * Cierre a ciegas estricto para el cajero.
  * El modal se cierra limpiando la memoria del token administrativo temporal de inmediato.
  * El POS descarga el archivo PDF localmente de forma automática.
