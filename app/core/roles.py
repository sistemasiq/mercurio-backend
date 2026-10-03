"""Nombres de los dos roles estructurales del sistema.

A diferencia del resto de los roles (que son datos: filas en la tabla
``roles``, editables desde el Catálogo de Roles), estos dos tienen
comportamiento especial hardcodeado en el backend:

- ``ROL_SISTEMA``: acceso total, sin restricción de sucursal, no se le
  puede quitar ningún permiso.
- ``ROL_ADMINISTRADOR``: se asigna a una o varias sucursales por un
  puente (``usuarios_sucursal``), no por el campo simple ``branch_id``.

Todo rol nuevo (incluidos los creados desde la UI) se comporta como
Cajero/Cocina: requiere una sucursal fija y es gestionable por un
Administrador de esa sucursal.
"""

ROL_SISTEMA = "AdministradorSistema"
ROL_ADMINISTRADOR = "Administrador"

ROLES_SIN_SUCURSAL_FIJA = (ROL_SISTEMA, ROL_ADMINISTRADOR)
