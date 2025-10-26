-- SQL para actualizar el enum de exercise_type en Supabase
-- Ejecutar en SQL Editor de Supabase Dashboard
-- IMPORTANTE: Ejecutar cada bloque por separado

-- PASO 1: Añadir el nuevo valor 'compose' al enum existente
ALTER TYPE exercise_type ADD VALUE 'compose';

-- PASO 2: Hacer commit de la transacción (ejecutar este bloque después del anterior)
COMMIT;

-- PASO 3: Verificar que se añadió correctamente (ejecutar después del commit)
SELECT enum_range(null::exercise_type);