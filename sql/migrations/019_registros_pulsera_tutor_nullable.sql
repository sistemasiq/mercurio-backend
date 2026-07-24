-- 019_registros_pulsera_tutor_nullable.sql
-- La columna registros.pulseras_tutor_id se agregó como NULLABLE en la
-- migración 018 (la feature de pulsera de tutor en el flujo de check-in
-- aún no está implementada en ningún lado del código). En algún momento se
-- aplicó manualmente un ALTER TABLE ... SET NOT NULL en la BD que nunca se
-- reflejó en una migración, lo cual rompía todo POST /api/estancias
-- (creación de registros/check-in) porque el código nunca llena esa
-- columna. Esta migración revierte eso hasta que la feature se implemente
-- de punta a punta.
ALTER TABLE public.registros
    ALTER COLUMN pulseras_tutor_id DROP NOT NULL;
