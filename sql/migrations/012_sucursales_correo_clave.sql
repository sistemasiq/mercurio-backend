-- 012_sucursales_correo_clave.sql
-- Recupera columnas de sucursales que usa branch_repository.py (correo, clave)
-- pero que nunca llegaron a esta línea de migraciones. Existían en el snapshot
-- de esquema de la rama origin/feature/eventos (commit 111ba92), nunca integradas.
ALTER TABLE public.sucursales ADD COLUMN IF NOT EXISTS correo VARCHAR(150);
ALTER TABLE public.sucursales ADD COLUMN IF NOT EXISTS clave VARCHAR(50);
