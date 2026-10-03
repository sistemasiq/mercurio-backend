-- =============================================================================
-- schema_maestro.sql — Crea la base de datos completa de Mercury en un paso.
--
-- GENERADO por scripts/generar_schema_maestro.sh. NO editar a mano: agrega una
-- migración en sql/migrations/ y vuelve a correr el script.
--
-- Equivale a aplicar las 95 migraciones de sql/migrations/ en orden
-- (última: 072_comandas_mesa.sql).
-- Incluye el esquema y los datos de catálogo que esas migraciones insertan
-- (roles, permisos, etc.). No incluye datos de prueba: para eso está
-- sql/seed_local.sql.
--
-- Uso, sobre una BD VACÍA:
--   psql -v ON_ERROR_STOP=1 -h <host> -U <usuario> -d <bd> -f sql/schema_maestro.sql
-- =============================================================================

-- ---------------------------------------------------------------- Esquema
--
-- PostgreSQL database dump
--


-- Dumped from database version 16.14
-- Dumped by pg_dump version 16.14

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: app; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA app;


--
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;


--
-- Name: conceptos_retiro; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.conceptos_retiro AS ENUM (
    'Pago a proveedor',
    'Compra de insumos',
    'Depósito bancario',
    'Resguardo de efectivo',
    'Pago de servicios',
    'Gastos administrativos',
    'Gastos varios',
    'Devolución'
);


--
-- Name: motivo_movimiento_inventario; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.motivo_movimiento_inventario AS ENUM (
    'venta_comanda',
    'cancelacion_comanda',
    'entrada_manual',
    'merma',
    'compra',
    'conteo_fisico',
    'ajuste_fifo'
);


--
-- Name: tipo_cierre_enum; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.tipo_cierre_enum AS ENUM (
    'NORMAL',
    'EXTRAORDINARIO'
);


--
-- Name: tipo_movimiento_caja; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.tipo_movimiento_caja AS ENUM (
    'E',
    'O',
    'R',
    'RP',
    'C',
    'I'
);


--
-- Name: tipos_destinatario; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.tipos_destinatario AS ENUM (
    'Proveedor',
    'Empleado',
    'Administrador',
    'Cliente'
);


--
-- Name: get_rol(); Type: FUNCTION; Schema: app; Owner: -
--

CREATE FUNCTION app.get_rol() RETURNS text
    LANGUAGE sql STABLE
    AS $$ SELECT current_setting('app.rol', true); $$;


--
-- Name: get_sucursal_id(); Type: FUNCTION; Schema: app; Owner: -
--

CREATE FUNCTION app.get_sucursal_id() RETURNS uuid
    LANGUAGE sql STABLE
    AS $$ SELECT NULLIF(current_setting('app.sucursal_id', true), '')::UUID; $$;


--
-- Name: set_modificado(); Type: FUNCTION; Schema: app; Owner: -
--

CREATE FUNCTION app.set_modificado() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
    BEGIN
        NEW.modificado     := NOW();
        NEW.modificado_por := NULLIF(current_setting('app.user_id', true), '')::UUID;
        RETURN NEW;
    END;
    $$;


--
-- Name: usuario_en_sucursal(uuid); Type: FUNCTION; Schema: app; Owner: -
--

CREATE FUNCTION app.usuario_en_sucursal(p_sucursal_id uuid) RETURNS boolean
    LANGUAGE sql STABLE
    AS $$
        SELECT app.get_rol() = 'admin'
            OR app.get_sucursal_id() = p_sucursal_id;
    $$;


--
-- Name: usuario_tiene_rol(text[]); Type: FUNCTION; Schema: app; Owner: -
--

CREATE FUNCTION app.usuario_tiene_rol(p_roles text[]) RETURNS boolean
    LANGUAGE sql STABLE
    AS $$ SELECT app.get_rol() = ANY(p_roles); $$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: apertura_caja; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.apertura_caja (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    caja_id uuid NOT NULL,
    cajero_id uuid NOT NULL,
    turno_id uuid NOT NULL,
    fondo_inicial numeric(12,2) DEFAULT 0.00 NOT NULL,
    estado character varying(20) DEFAULT 'ABIERTA'::character varying NOT NULL,
    conteo_json text,
    monto_declarado numeric(12,2),
    token_admin_jti uuid,
    creado timestamp with time zone DEFAULT now() NOT NULL,
    creado_por uuid,
    modificado timestamp with time zone DEFAULT now(),
    modificado_por uuid,
    CONSTRAINT chk_apertura_estado CHECK (((estado)::text = ANY ((ARRAY['ABIERTA'::character varying, 'EN_CORTE'::character varying, 'CERRADA'::character varying])::text[]))),
    CONSTRAINT chk_fondo_no_negativo CHECK ((fondo_inicial >= (0)::numeric))
);


--
-- Name: cajas; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.cajas (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    sucursal_id uuid NOT NULL,
    codigo character varying(20) NOT NULL,
    nombre character varying(100) NOT NULL,
    creado timestamp with time zone DEFAULT now() NOT NULL,
    creado_por uuid,
    modificado timestamp with time zone,
    modificado_por uuid,
    numero smallint DEFAULT 0 NOT NULL,
    activo boolean DEFAULT true NOT NULL,
    impresora character varying(100)
);


--
-- Name: capas_costo_insumo; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.capas_costo_insumo (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    insumo_id uuid NOT NULL,
    cantidad_inicial numeric(12,3) NOT NULL,
    cantidad_restante numeric(12,3) NOT NULL,
    costo_unitario numeric(12,4) NOT NULL,
    origen character varying(20) NOT NULL,
    referencia_id uuid,
    creado timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT capas_costo_insumo_cantidad_inicial_check CHECK ((cantidad_inicial > (0)::numeric)),
    CONSTRAINT capas_costo_insumo_cantidad_restante_check CHECK ((cantidad_restante >= (0)::numeric))
);


--
-- Name: cargos_extra_estancia; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.cargos_extra_estancia (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    sucursal_id uuid NOT NULL,
    registros_id uuid NOT NULL,
    detalles_registro_id uuid NOT NULL,
    cantidad integer NOT NULL,
    precio numeric(10,2) NOT NULL,
    total numeric(10,2) NOT NULL,
    creado timestamp with time zone DEFAULT now() NOT NULL,
    creado_por uuid
);


--
-- Name: cierre_caja; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.cierre_caja (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    apertura_caja_id uuid NOT NULL,
    tipo_cierre public.tipo_cierre_enum DEFAULT 'NORMAL'::public.tipo_cierre_enum NOT NULL,
    monto_sistema numeric(12,2) NOT NULL,
    monto_cierre numeric(12,2) NOT NULL,
    cajero_id uuid,
    fecha_autorizacion_cajero timestamp with time zone,
    administrador_id uuid NOT NULL,
    fecha_autorizacion_admin timestamp with time zone DEFAULT now() NOT NULL,
    observaciones text,
    creado timestamp with time zone DEFAULT now() NOT NULL,
    creado_por uuid
);


--
-- Name: comandas; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.comandas (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    ticket_numero character varying(50) NOT NULL,
    estado_actual character varying(1) DEFAULT 'P'::character varying NOT NULL,
    total_final numeric(10,2) NOT NULL,
    sucursal_id uuid NOT NULL,
    fecha_hora timestamp with time zone DEFAULT now() NOT NULL,
    activo boolean DEFAULT true NOT NULL,
    motivo_cancelacion text,
    creado_por uuid,
    modificado timestamp with time zone DEFAULT now(),
    modificado_por uuid,
    reservacion_id uuid,
    nombre_cliente character varying(150),
    mesa character varying(20)
);


--
-- Name: compras; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.compras (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    sucursal_id uuid NOT NULL,
    proveedor_id uuid NOT NULL,
    estado character varying(10) DEFAULT 'P'::character varying NOT NULL,
    fecha_pedido timestamp with time zone DEFAULT now() NOT NULL,
    fecha_recepcion timestamp with time zone,
    total numeric(10,2) DEFAULT 0 NOT NULL,
    notas text,
    activo boolean DEFAULT true NOT NULL,
    creado timestamp with time zone DEFAULT now() NOT NULL,
    creado_por uuid,
    modificado timestamp with time zone DEFAULT now(),
    modificado_por uuid,
    iva numeric(10,2) DEFAULT 0 NOT NULL,
    folio character varying(20),
    CONSTRAINT compras_iva_check CHECK ((iva >= (0)::numeric))
);


--
-- Name: configuracion_lealtad; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.configuracion_lealtad (
    sucursal_id uuid NOT NULL,
    porcentaje_retorno numeric(5,2) DEFAULT 0 NOT NULL,
    dias_caducidad integer NOT NULL,
    valor_punto numeric(10,4) DEFAULT 1.00 NOT NULL,
    activo boolean DEFAULT true NOT NULL,
    creado timestamp with time zone DEFAULT now() NOT NULL,
    creado_por uuid,
    modificado timestamp with time zone DEFAULT now(),
    modificado_por uuid,
    otorga_puntos_comandas boolean DEFAULT true NOT NULL,
    otorga_puntos_reservaciones boolean DEFAULT true NOT NULL,
    otorga_puntos_checkin boolean DEFAULT true NOT NULL,
    minimo_canje integer DEFAULT 0 NOT NULL,
    CONSTRAINT configuracion_lealtad_dias_caducidad_check CHECK ((dias_caducidad > 0)),
    CONSTRAINT configuracion_lealtad_minimo_canje_check CHECK ((minimo_canje >= 0)),
    CONSTRAINT configuracion_lealtad_porcentaje_retorno_check CHECK (((porcentaje_retorno >= (0)::numeric) AND (porcentaje_retorno <= (100)::numeric))),
    CONSTRAINT configuracion_lealtad_valor_punto_check CHECK ((valor_punto > (0)::numeric))
);


--
-- Name: detalle_compras; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.detalle_compras (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    compra_id uuid NOT NULL,
    insumo_id uuid NOT NULL,
    unidad_medida_id uuid,
    cantidad numeric(12,3) NOT NULL,
    costo_unitario numeric(10,2) NOT NULL,
    subtotal numeric(10,2) GENERATED ALWAYS AS ((cantidad * costo_unitario)) STORED,
    presentacion_id uuid,
    cantidad_recibida numeric(12,3) DEFAULT 0 NOT NULL,
    CONSTRAINT chk_detalle_compras_una_unidad CHECK (((((unidad_medida_id IS NOT NULL))::integer + ((presentacion_id IS NOT NULL))::integer) = 1)),
    CONSTRAINT detalle_compras_cantidad_check CHECK ((cantidad > (0)::numeric)),
    CONSTRAINT detalle_compras_costo_unitario_check CHECK ((costo_unitario >= (0)::numeric))
);


--
-- Name: detalles_comanda; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.detalles_comanda (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    comanda_id uuid NOT NULL,
    producto_id uuid NOT NULL,
    cantidad integer NOT NULL,
    precio_unitario numeric(10,2) NOT NULL,
    importe numeric(10,2) NOT NULL,
    sucursal_id uuid NOT NULL,
    notas_especiales text,
    activo boolean DEFAULT true NOT NULL,
    nombre_combo_padre character varying(150),
    es_hijo_de uuid,
    es_hijo_combo boolean DEFAULT false NOT NULL,
    creado_por uuid,
    modificado timestamp with time zone DEFAULT now(),
    modificado_por uuid,
    id_combo_padre uuid
);


--
-- Name: detalles_registro; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.detalles_registro (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    sucursal_id uuid NOT NULL,
    registros_id uuid NOT NULL,
    ninos_id uuid NOT NULL,
    pulseras_id uuid NOT NULL,
    productos_id uuid NOT NULL,
    cantidad integer NOT NULL,
    precio numeric(10,2) NOT NULL,
    parentesco character varying(100) NOT NULL,
    entrada timestamp with time zone NOT NULL,
    salida_esperada timestamp with time zone NOT NULL,
    salida timestamp with time zone,
    activo boolean DEFAULT true NOT NULL,
    creado timestamp with time zone DEFAULT now() NOT NULL,
    creado_por uuid,
    modificado timestamp with time zone DEFAULT now(),
    modificado_por uuid
);


--
-- Name: extras; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.extras (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    sucursal_id uuid NOT NULL,
    nombre character varying(150) NOT NULL,
    descripcion text,
    precio numeric(10,2) NOT NULL,
    unidad character varying(50) DEFAULT 'evento'::character varying NOT NULL,
    activo boolean DEFAULT true NOT NULL,
    creado timestamp with time zone DEFAULT now() NOT NULL,
    creado_por uuid,
    modificado timestamp with time zone DEFAULT now(),
    modificado_por uuid
);


--
-- Name: folios_compra_sucursal; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.folios_compra_sucursal (
    sucursal_id uuid NOT NULL,
    serie text DEFAULT 'OC'::text NOT NULL,
    ultimo integer DEFAULT 0 NOT NULL
);


--
-- Name: folios_sucursal; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.folios_sucursal (
    sucursal_id uuid NOT NULL,
    serie text DEFAULT 'A'::text NOT NULL,
    ultimo integer DEFAULT 0 NOT NULL
);


--
-- Name: fotos; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.fotos (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    registro_id uuid NOT NULL,
    tipo character(1) NOT NULL,
    storage_url text NOT NULL,
    activo boolean DEFAULT true NOT NULL,
    creado timestamp with time zone DEFAULT now() NOT NULL,
    creado_por uuid,
    modificado timestamp with time zone,
    modificado_por uuid,
    CONSTRAINT fotos_tipo_check CHECK ((tipo = ANY (ARRAY['I'::bpchar, 'L'::bpchar])))
);


--
-- Name: insumos; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.insumos (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    sucursal_id uuid NOT NULL,
    nombre character varying(150) NOT NULL,
    descripcion text,
    unidad_base_id uuid NOT NULL,
    unidad_compra_id uuid NOT NULL,
    stock_actual numeric(12,3) DEFAULT 0 NOT NULL,
    stock_minimo numeric(12,3) DEFAULT 0 NOT NULL,
    costo_unitario numeric(10,2),
    proveedor_principal_id uuid,
    activo boolean DEFAULT true NOT NULL,
    creado timestamp with time zone DEFAULT now() NOT NULL,
    creado_por uuid,
    modificado timestamp with time zone DEFAULT now(),
    modificado_por uuid,
    punto_reorden numeric(12,3),
    stock_maximo numeric(12,3)
);


--
-- Name: lotes_puntos; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.lotes_puntos (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    sucursal_id uuid NOT NULL,
    celular character varying(10) NOT NULL,
    comanda_id uuid,
    puntos_otorgados integer NOT NULL,
    puntos_disponibles integer NOT NULL,
    fecha_otorgado timestamp with time zone DEFAULT now() NOT NULL,
    fecha_caducidad timestamp with time zone NOT NULL,
    creado_por uuid,
    reservacion_id uuid,
    registro_id uuid,
    CONSTRAINT chk_lotes_puntos_una_referencia CHECK ((num_nonnulls(comanda_id, reservacion_id, registro_id) <= 1)),
    CONSTRAINT lotes_puntos_puntos_disponibles_check CHECK ((puntos_disponibles >= 0)),
    CONSTRAINT lotes_puntos_puntos_otorgados_check CHECK ((puntos_otorgados > 0))
);


--
-- Name: metodos_pago; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.metodos_pago (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    nombre character varying(100) NOT NULL,
    descripcion text,
    creado timestamp with time zone DEFAULT now() NOT NULL,
    creado_por uuid,
    modificado timestamp with time zone DEFAULT now(),
    modificado_por uuid,
    tipo character varying(1) DEFAULT 'O'::character varying NOT NULL,
    comision_porcentaje numeric(5,2),
    requiere_referencia boolean DEFAULT false NOT NULL,
    CONSTRAINT metodos_pago_comision_porcentaje_check CHECK (((comision_porcentaje IS NULL) OR (comision_porcentaje >= (0)::numeric))),
    CONSTRAINT metodos_pago_tipo_check CHECK (((tipo)::text = ANY ((ARRAY['E'::character varying, 'T'::character varying, 'C'::character varying, 'L'::character varying, 'O'::character varying])::text[])))
);


--
-- Name: movimientos_caja; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.movimientos_caja (
    id bigint NOT NULL,
    apertura_caja_id uuid NOT NULL,
    tipo_movimiento public.tipo_movimiento_caja NOT NULL,
    referencia_id uuid NOT NULL,
    metodo_pago_id uuid,
    monto numeric(12,2) NOT NULL,
    creado timestamp with time zone DEFAULT now() NOT NULL,
    creado_por uuid,
    CONSTRAINT movimientos_caja_monto_check CHECK ((monto > (0)::numeric))
);


--
-- Name: movimientos_caja_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.movimientos_caja_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: movimientos_caja_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.movimientos_caja_id_seq OWNED BY public.movimientos_caja.id;


--
-- Name: movimientos_inventario; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.movimientos_inventario (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    sucursal_id uuid NOT NULL,
    insumo_id uuid NOT NULL,
    tipo character varying(1) NOT NULL,
    cantidad numeric(12,3) NOT NULL,
    stock_resultante numeric(12,3) NOT NULL,
    motivo public.motivo_movimiento_inventario NOT NULL,
    referencia_id uuid,
    notas text,
    creado timestamp with time zone DEFAULT now() NOT NULL,
    creado_por uuid,
    costo_total numeric(14,4),
    CONSTRAINT movimientos_inventario_cantidad_check CHECK ((cantidad > (0)::numeric))
);


--
-- Name: movimientos_puntos; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.movimientos_puntos (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    sucursal_id uuid NOT NULL,
    celular character varying(10) NOT NULL,
    lote_id uuid,
    comanda_id uuid,
    tipo character varying(1) NOT NULL,
    puntos integer NOT NULL,
    saldo_resultante integer NOT NULL,
    notas text,
    creado timestamp with time zone DEFAULT now() NOT NULL,
    creado_por uuid,
    reservacion_id uuid,
    registro_id uuid,
    CONSTRAINT movimientos_puntos_tipo_check CHECK (((tipo)::text = ANY ((ARRAY['O'::character varying, 'R'::character varying, 'C'::character varying, 'A'::character varying])::text[])))
);


--
-- Name: ninos; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ninos (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    sucursal_id uuid NOT NULL,
    nombre_completo character varying(200) NOT NULL,
    edad integer NOT NULL,
    notas text,
    activo boolean DEFAULT true NOT NULL,
    creado timestamp with time zone DEFAULT now() NOT NULL,
    creado_por uuid,
    modificado timestamp with time zone DEFAULT now(),
    modificado_por uuid
);


--
-- Name: pagos_estancia; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pagos_estancia (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    sucursal_id uuid NOT NULL,
    registros_id uuid NOT NULL,
    metodos_pago_id uuid NOT NULL,
    monto numeric(10,2) NOT NULL,
    creado timestamp with time zone DEFAULT now() NOT NULL,
    creado_por uuid
);


--
-- Name: pagos_idempotencia; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pagos_idempotencia (
    clave text NOT NULL,
    sucursal_id uuid NOT NULL,
    usuario_id uuid NOT NULL,
    hash_payload text NOT NULL,
    comanda_id uuid NOT NULL,
    creado timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: pagos_ordenes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pagos_ordenes (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    comanda_id uuid NOT NULL,
    metodo_pago_id uuid NOT NULL,
    monto numeric(12,2) NOT NULL,
    notas_pago text,
    sucursal_id uuid NOT NULL,
    activo boolean DEFAULT true NOT NULL,
    creado timestamp with time zone DEFAULT now() NOT NULL,
    creado_por uuid,
    modificado timestamp with time zone,
    modificado_por uuid,
    ultimos4 character varying(4),
    CONSTRAINT pagos_ordenes_monto_check CHECK ((monto >= 0.00))
);


--
-- Name: pagos_reservacion; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pagos_reservacion (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    reservacion_id uuid NOT NULL,
    metodo_pago_id uuid NOT NULL,
    monto numeric(10,2) NOT NULL,
    fecha_pago timestamp with time zone DEFAULT now() NOT NULL,
    notas character varying(255),
    creado_por uuid,
    tipo character varying(20) DEFAULT 'pago'::character varying NOT NULL,
    CONSTRAINT pagos_reservacion_tipo_check CHECK (((tipo)::text = ANY ((ARRAY['anticipo'::character varying, 'pago'::character varying, 'liquidacion'::character varying])::text[])))
);


--
-- Name: paquete_productos; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.paquete_productos (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    paquete_id uuid NOT NULL,
    producto_id uuid NOT NULL,
    cantidad integer DEFAULT 1 NOT NULL,
    activo boolean DEFAULT true NOT NULL,
    creado timestamp with time zone DEFAULT now() NOT NULL,
    creado_por uuid,
    modificado timestamp with time zone DEFAULT now(),
    modificado_por uuid
);


--
-- Name: paquete_tipos_evento; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.paquete_tipos_evento (
    paquete_id uuid NOT NULL,
    tipo_evento_id uuid NOT NULL
);


--
-- Name: paquetes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.paquetes (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    sucursal_id uuid NOT NULL,
    nombre character varying(150) NOT NULL,
    descripcion text,
    min_invitados integer DEFAULT 1 NOT NULL,
    precio_base numeric(10,2) NOT NULL,
    precio_hora_pulsera numeric(10,2) DEFAULT 0 NOT NULL,
    activo boolean DEFAULT true NOT NULL,
    creado timestamp with time zone DEFAULT now() NOT NULL,
    creado_por uuid,
    modificado timestamp with time zone DEFAULT now(),
    modificado_por uuid,
    max_invitados integer DEFAULT 10 NOT NULL,
    duracion_horas numeric(5,2),
    destacado boolean DEFAULT false NOT NULL,
    anticipo_porcentaje numeric(5,2),
    CONSTRAINT chk_paquetes_rango_invitados CHECK (((min_invitados > 0) AND (max_invitados >= min_invitados))),
    CONSTRAINT paquetes_anticipo_porcentaje_check CHECK (((anticipo_porcentaje IS NULL) OR ((anticipo_porcentaje > (0)::numeric) AND (anticipo_porcentaje <= (100)::numeric)))),
    CONSTRAINT paquetes_duracion_horas_check CHECK (((duracion_horas IS NULL) OR (duracion_horas > (0)::numeric)))
);


--
-- Name: permisos; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.permisos (
    id integer NOT NULL,
    codigo character varying(100) NOT NULL,
    nombre character varying(150) NOT NULL,
    modulo character varying(50) NOT NULL,
    descripcion text
);


--
-- Name: permisos_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.permisos_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: permisos_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.permisos_id_seq OWNED BY public.permisos.id;


--
-- Name: pin_tokens; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pin_tokens (
    token text NOT NULL,
    usuario_id uuid NOT NULL,
    turno_id uuid NOT NULL,
    rol character varying(20) NOT NULL,
    creado timestamp with time zone DEFAULT now() NOT NULL,
    expira timestamp with time zone NOT NULL,
    usado boolean DEFAULT false NOT NULL
);


--
-- Name: presentaciones_insumo; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.presentaciones_insumo (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    insumo_id uuid NOT NULL,
    nombre character varying(100) NOT NULL,
    equivalencia_base numeric(12,3) NOT NULL,
    activo boolean DEFAULT true NOT NULL,
    creado timestamp with time zone DEFAULT now() NOT NULL,
    creado_por uuid,
    modificado timestamp with time zone DEFAULT now(),
    modificado_por uuid,
    CONSTRAINT presentaciones_insumo_equivalencia_base_check CHECK ((equivalencia_base > (0)::numeric))
);


--
-- Name: producto_combo; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.producto_combo (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    combo_id uuid NOT NULL,
    producto_id uuid NOT NULL,
    cantidad integer DEFAULT 1 NOT NULL,
    activo boolean DEFAULT true NOT NULL,
    creado timestamp with time zone DEFAULT now() NOT NULL,
    creado_por uuid,
    modificado timestamp with time zone DEFAULT now(),
    modificado_por uuid
);


--
-- Name: producto_insumos; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.producto_insumos (
    producto_id uuid NOT NULL,
    insumo_id uuid NOT NULL,
    cantidad numeric(12,3) NOT NULL,
    creado timestamp with time zone DEFAULT now() NOT NULL,
    creado_por uuid,
    modificado timestamp with time zone,
    modificado_por uuid,
    CONSTRAINT producto_insumos_cantidad_check CHECK ((cantidad > (0)::numeric))
);


--
-- Name: productos; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.productos (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    nombre character varying(150) NOT NULL,
    precio_unitario numeric(10,2) NOT NULL,
    tipo character varying(1) NOT NULL,
    sucursal_id uuid NOT NULL,
    descripcion text,
    imagen text,
    config_estancia jsonb,
    activo boolean DEFAULT true NOT NULL,
    creado timestamp with time zone DEFAULT now() NOT NULL,
    creado_por uuid,
    modificado timestamp with time zone DEFAULT now(),
    modificado_por uuid,
    es_combo boolean DEFAULT false NOT NULL,
    codigo character varying(50)
);


--
-- Name: proveedores; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.proveedores (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    sucursal_id uuid NOT NULL,
    nombre character varying(150) NOT NULL,
    contacto_nombre character varying(150),
    telefono character varying(20),
    email character varying(150),
    notas text,
    activo boolean DEFAULT true NOT NULL,
    creado timestamp with time zone DEFAULT now() NOT NULL,
    creado_por uuid,
    modificado timestamp with time zone DEFAULT now(),
    modificado_por uuid,
    rfc character varying(13),
    dias_entrega integer,
    CONSTRAINT proveedores_dias_entrega_check CHECK (((dias_entrega IS NULL) OR (dias_entrega >= 0)))
);


--
-- Name: pulseras; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pulseras (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    sucursal_id uuid NOT NULL,
    pulsera_rfid character varying(50) NOT NULL,
    activo boolean DEFAULT true NOT NULL,
    creado timestamp with time zone DEFAULT now() NOT NULL,
    creado_por uuid,
    modificado timestamp with time zone DEFAULT now(),
    modificado_por uuid,
    numero_lote character varying(50)
);


--
-- Name: refresh_tokens; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.refresh_tokens (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    usuario_id uuid NOT NULL,
    token_hash text NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    revocado boolean DEFAULT false NOT NULL,
    creado timestamp with time zone DEFAULT now() NOT NULL,
    sucursal_id uuid
);


--
-- Name: registros; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.registros (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    sucursal_id uuid NOT NULL,
    tutores_id uuid NOT NULL,
    total numeric(10,2) DEFAULT 0 NOT NULL,
    estado character varying(1) DEFAULT 'P'::character varying NOT NULL,
    activo boolean DEFAULT true NOT NULL,
    creado timestamp with time zone DEFAULT now() NOT NULL,
    creado_por uuid,
    modificado timestamp with time zone DEFAULT now(),
    modificado_por uuid,
    pulseras_tutor_id uuid,
    nombre_segundo_tutor character varying(200),
    reservacion_id uuid
);


--
-- Name: reservacion_extras; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.reservacion_extras (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    reservacion_id uuid NOT NULL,
    extra_id uuid NOT NULL,
    cantidad integer NOT NULL,
    precio_unitario numeric(10,2) NOT NULL,
    subtotal numeric(10,2) GENERATED ALWAYS AS (((cantidad)::numeric * precio_unitario)) STORED,
    creado timestamp with time zone DEFAULT now() NOT NULL,
    creado_por uuid
);


--
-- Name: reservacion_productos; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.reservacion_productos (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    reservacion_id uuid NOT NULL,
    producto_id uuid NOT NULL,
    cantidad integer NOT NULL,
    precio_unitario numeric(10,2) NOT NULL,
    subtotal numeric(10,2) GENERATED ALWAYS AS (((cantidad)::numeric * precio_unitario)) STORED,
    notas text,
    creado timestamp with time zone DEFAULT now() NOT NULL,
    creado_por uuid
);


--
-- Name: reservaciones; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.reservaciones (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    sucursal_id uuid NOT NULL,
    tipo_evento_id uuid NOT NULL,
    paquete_id uuid NOT NULL,
    nombre_cliente character varying(150) NOT NULL,
    apellidos_cliente character varying(150),
    telefono_cliente character varying(10) NOT NULL,
    email_cliente character varying(150),
    notas_cliente text,
    nombre_festejado character varying(150),
    edad_festejado integer,
    fecha_evento date NOT NULL,
    hora_inicio time without time zone NOT NULL,
    hora_fin time without time zone NOT NULL,
    numero_personas integer NOT NULL,
    precio_base numeric(10,2) NOT NULL,
    precio_personas_extra numeric(10,2) DEFAULT 0 NOT NULL,
    precio_extras numeric(10,2) DEFAULT 0 NOT NULL,
    descuento numeric(10,2) DEFAULT 0 NOT NULL,
    precio_total numeric(10,2) NOT NULL,
    anticipo numeric(10,2) DEFAULT 0 NOT NULL,
    saldo_pendiente numeric(10,2) GENERATED ALWAYS AS ((precio_total - anticipo)) STORED,
    estado character varying(20) DEFAULT 'pendiente'::character varying NOT NULL,
    notas text,
    activo boolean DEFAULT true NOT NULL,
    creado timestamp with time zone DEFAULT now() NOT NULL,
    creado_por uuid,
    modificado timestamp with time zone DEFAULT now(),
    modificado_por uuid,
    horas_reservadas integer DEFAULT 0 NOT NULL,
    precio_horas numeric(10,2) DEFAULT 0 NOT NULL,
    precio_productos numeric(10,2) DEFAULT 0 NOT NULL,
    comanda_enviada boolean DEFAULT false NOT NULL,
    folio character varying(20)
);


--
-- Name: reservaciones_folio_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.reservaciones_folio_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: retiros_parciales; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.retiros_parciales (
    id bigint NOT NULL,
    apertura_caja_id uuid NOT NULL,
    concepto public.conceptos_retiro NOT NULL,
    tipo_destinatario public.tipos_destinatario NOT NULL,
    monto numeric(12,2) NOT NULL,
    observaciones text,
    creado timestamp with time zone DEFAULT now() NOT NULL,
    creado_por uuid,
    CONSTRAINT retiros_parciales_monto_check CHECK ((monto > (0)::numeric))
);


--
-- Name: retiros_parciales_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.retiros_parciales_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: retiros_parciales_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.retiros_parciales_id_seq OWNED BY public.retiros_parciales.id;


--
-- Name: rol_permisos; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.rol_permisos (
    rol_id smallint NOT NULL,
    permiso_id integer NOT NULL
);


--
-- Name: roles; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.roles (
    id smallint NOT NULL,
    nombre character varying(50) NOT NULL,
    descripcion text,
    activo boolean DEFAULT true NOT NULL
);


--
-- Name: roles_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.roles_id_seq
    AS smallint
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: roles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.roles_id_seq OWNED BY public.roles.id;


--
-- Name: sucursal_metodos_pago; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sucursal_metodos_pago (
    sucursal_id uuid NOT NULL,
    metodo_pago_id uuid NOT NULL,
    activo boolean DEFAULT true NOT NULL,
    creado timestamp with time zone DEFAULT now() NOT NULL,
    creado_por uuid,
    modificado timestamp with time zone DEFAULT now(),
    modificado_por uuid
);


--
-- Name: sucursales; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sucursales (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    nombre character varying(150) NOT NULL,
    direccion text,
    telefono character varying(20),
    activo boolean DEFAULT true NOT NULL,
    creado timestamp with time zone DEFAULT now() NOT NULL,
    creado_por uuid,
    modificado timestamp with time zone,
    modificado_por uuid,
    correo character varying(150),
    clave character varying(50),
    ciudad character varying(100),
    estado character varying(100),
    codigo_postal character varying(10),
    zona_horaria character varying(50) DEFAULT 'America/Mexico_City'::character varying NOT NULL,
    hora_apertura time without time zone DEFAULT '09:00:00'::time without time zone NOT NULL,
    hora_cierre time without time zone DEFAULT '23:00:00'::time without time zone NOT NULL
);


--
-- Name: tipos_evento; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tipos_evento (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    nombre character varying(100) NOT NULL,
    descripcion text,
    activo boolean DEFAULT true NOT NULL,
    creado timestamp with time zone DEFAULT now() NOT NULL,
    creado_por uuid,
    modificado timestamp with time zone DEFAULT now(),
    modificado_por uuid,
    sucursal_id uuid NOT NULL
);


--
-- Name: tokens_revocados; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tokens_revocados (
    jti uuid NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    revocado_en timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: turnos; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.turnos (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    nombre character varying(50) NOT NULL,
    hora_inicio time without time zone NOT NULL,
    hora_fin time without time zone NOT NULL,
    creado timestamp with time zone DEFAULT now() NOT NULL,
    creado_por uuid,
    modificado timestamp with time zone,
    modificado_por uuid,
    activo boolean DEFAULT true NOT NULL,
    dias smallint[]
);


--
-- Name: tutores; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tutores (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    sucursal_id uuid NOT NULL,
    nombre_completo character varying(200) NOT NULL,
    telefono character varying(10) NOT NULL,
    activo boolean DEFAULT true NOT NULL,
    creado timestamp with time zone DEFAULT now() NOT NULL,
    creado_por uuid,
    modificado timestamp with time zone DEFAULT now(),
    modificado_por uuid
);


--
-- Name: unidades_medida; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.unidades_medida (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    codigo character varying(10) NOT NULL,
    nombre character varying(50) NOT NULL,
    tipo character varying(20) NOT NULL,
    factor_a_base numeric(14,6) NOT NULL,
    activo boolean DEFAULT true NOT NULL
);


--
-- Name: usuarios; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.usuarios (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    email character varying(254) NOT NULL,
    password_hash text NOT NULL,
    nombre_completo character varying(200) NOT NULL,
    activo boolean DEFAULT true NOT NULL,
    creado timestamp with time zone DEFAULT now() NOT NULL,
    creado_por uuid,
    modificado timestamp with time zone DEFAULT now() NOT NULL,
    modificado_por uuid,
    rol smallint NOT NULL,
    pin_hash character(60),
    apellidos character varying(150),
    telefono character varying(20),
    ultimo_acceso timestamp with time zone
);


--
-- Name: usuarios_sucursal; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.usuarios_sucursal (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    usuario_id uuid NOT NULL,
    sucursal_id uuid NOT NULL,
    activo boolean DEFAULT true NOT NULL,
    creado timestamp with time zone DEFAULT now() NOT NULL,
    creado_por uuid,
    modificado timestamp with time zone DEFAULT now() NOT NULL,
    modificado_por uuid
);


--
-- Name: ws_tickets; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ws_tickets (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    ticket_hash text NOT NULL,
    claims jsonb NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    usado boolean DEFAULT false NOT NULL,
    creado_en timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: movimientos_caja id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.movimientos_caja ALTER COLUMN id SET DEFAULT nextval('public.movimientos_caja_id_seq'::regclass);


--
-- Name: permisos id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.permisos ALTER COLUMN id SET DEFAULT nextval('public.permisos_id_seq'::regclass);


--
-- Name: retiros_parciales id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.retiros_parciales ALTER COLUMN id SET DEFAULT nextval('public.retiros_parciales_id_seq'::regclass);


--
-- Name: roles id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.roles ALTER COLUMN id SET DEFAULT nextval('public.roles_id_seq'::regclass);


--
-- Name: apertura_caja apertura_caja_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.apertura_caja
    ADD CONSTRAINT apertura_caja_pkey PRIMARY KEY (id);


--
-- Name: cajas cajas_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cajas
    ADD CONSTRAINT cajas_pkey PRIMARY KEY (id);


--
-- Name: capas_costo_insumo capas_costo_insumo_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.capas_costo_insumo
    ADD CONSTRAINT capas_costo_insumo_pkey PRIMARY KEY (id);


--
-- Name: cargos_extra_estancia cargos_extra_estancia_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cargos_extra_estancia
    ADD CONSTRAINT cargos_extra_estancia_pkey PRIMARY KEY (id);


--
-- Name: cierre_caja cierre_caja_apertura_caja_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cierre_caja
    ADD CONSTRAINT cierre_caja_apertura_caja_id_key UNIQUE (apertura_caja_id);


--
-- Name: cierre_caja cierre_caja_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cierre_caja
    ADD CONSTRAINT cierre_caja_pkey PRIMARY KEY (id);


--
-- Name: comandas comandas_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.comandas
    ADD CONSTRAINT comandas_pkey PRIMARY KEY (id);


--
-- Name: compras compras_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.compras
    ADD CONSTRAINT compras_pkey PRIMARY KEY (id);


--
-- Name: configuracion_lealtad configuracion_lealtad_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.configuracion_lealtad
    ADD CONSTRAINT configuracion_lealtad_pkey PRIMARY KEY (sucursal_id);


--
-- Name: detalle_compras detalle_compras_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.detalle_compras
    ADD CONSTRAINT detalle_compras_pkey PRIMARY KEY (id);


--
-- Name: detalles_comanda detalles_comanda_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.detalles_comanda
    ADD CONSTRAINT detalles_comanda_pkey PRIMARY KEY (id);


--
-- Name: detalles_registro detalles_registro_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.detalles_registro
    ADD CONSTRAINT detalles_registro_pkey PRIMARY KEY (id);


--
-- Name: extras extras_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extras
    ADD CONSTRAINT extras_pkey PRIMARY KEY (id);


--
-- Name: folios_compra_sucursal folios_compra_sucursal_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.folios_compra_sucursal
    ADD CONSTRAINT folios_compra_sucursal_pkey PRIMARY KEY (sucursal_id);


--
-- Name: folios_sucursal folios_sucursal_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.folios_sucursal
    ADD CONSTRAINT folios_sucursal_pkey PRIMARY KEY (sucursal_id);


--
-- Name: fotos fotos_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fotos
    ADD CONSTRAINT fotos_pkey PRIMARY KEY (id);


--
-- Name: insumos insumos_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.insumos
    ADD CONSTRAINT insumos_pkey PRIMARY KEY (id);


--
-- Name: lotes_puntos lotes_puntos_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lotes_puntos
    ADD CONSTRAINT lotes_puntos_pkey PRIMARY KEY (id);


--
-- Name: metodos_pago metodos_pago_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.metodos_pago
    ADD CONSTRAINT metodos_pago_pkey PRIMARY KEY (id);


--
-- Name: movimientos_caja movimientos_caja_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.movimientos_caja
    ADD CONSTRAINT movimientos_caja_pkey PRIMARY KEY (id);


--
-- Name: movimientos_inventario movimientos_inventario_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.movimientos_inventario
    ADD CONSTRAINT movimientos_inventario_pkey PRIMARY KEY (id);


--
-- Name: movimientos_puntos movimientos_puntos_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.movimientos_puntos
    ADD CONSTRAINT movimientos_puntos_pkey PRIMARY KEY (id);


--
-- Name: ninos ninos_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ninos
    ADD CONSTRAINT ninos_pkey PRIMARY KEY (id);


--
-- Name: pagos_estancia pagos_estancia_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pagos_estancia
    ADD CONSTRAINT pagos_estancia_pkey PRIMARY KEY (id);


--
-- Name: pagos_idempotencia pagos_idempotencia_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pagos_idempotencia
    ADD CONSTRAINT pagos_idempotencia_pkey PRIMARY KEY (clave);


--
-- Name: pagos_ordenes pagos_ordenes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pagos_ordenes
    ADD CONSTRAINT pagos_ordenes_pkey PRIMARY KEY (id);


--
-- Name: pagos_reservacion pagos_reservacion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pagos_reservacion
    ADD CONSTRAINT pagos_reservacion_pkey PRIMARY KEY (id);


--
-- Name: paquete_productos paquete_productos_paquete_id_producto_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.paquete_productos
    ADD CONSTRAINT paquete_productos_paquete_id_producto_id_key UNIQUE (paquete_id, producto_id);


--
-- Name: paquete_productos paquete_productos_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.paquete_productos
    ADD CONSTRAINT paquete_productos_pkey PRIMARY KEY (id);


--
-- Name: paquete_tipos_evento paquete_tipos_evento_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.paquete_tipos_evento
    ADD CONSTRAINT paquete_tipos_evento_pkey PRIMARY KEY (paquete_id, tipo_evento_id);


--
-- Name: paquetes paquetes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.paquetes
    ADD CONSTRAINT paquetes_pkey PRIMARY KEY (id);


--
-- Name: permisos permisos_codigo_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.permisos
    ADD CONSTRAINT permisos_codigo_key UNIQUE (codigo);


--
-- Name: permisos permisos_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.permisos
    ADD CONSTRAINT permisos_pkey PRIMARY KEY (id);


--
-- Name: pin_tokens pin_tokens_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pin_tokens
    ADD CONSTRAINT pin_tokens_pkey PRIMARY KEY (token);


--
-- Name: presentaciones_insumo presentaciones_insumo_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.presentaciones_insumo
    ADD CONSTRAINT presentaciones_insumo_pkey PRIMARY KEY (id);


--
-- Name: producto_combo producto_combo_combo_id_producto_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.producto_combo
    ADD CONSTRAINT producto_combo_combo_id_producto_id_key UNIQUE (combo_id, producto_id);


--
-- Name: producto_combo producto_combo_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.producto_combo
    ADD CONSTRAINT producto_combo_pkey PRIMARY KEY (id);


--
-- Name: producto_insumos producto_insumos_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.producto_insumos
    ADD CONSTRAINT producto_insumos_pkey PRIMARY KEY (producto_id, insumo_id);


--
-- Name: productos productos_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.productos
    ADD CONSTRAINT productos_pkey PRIMARY KEY (id);


--
-- Name: proveedores proveedores_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proveedores
    ADD CONSTRAINT proveedores_pkey PRIMARY KEY (id);


--
-- Name: pulseras pulseras_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pulseras
    ADD CONSTRAINT pulseras_pkey PRIMARY KEY (id);


--
-- Name: refresh_tokens refresh_tokens_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.refresh_tokens
    ADD CONSTRAINT refresh_tokens_pkey PRIMARY KEY (id);


--
-- Name: registros registros_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.registros
    ADD CONSTRAINT registros_pkey PRIMARY KEY (id);


--
-- Name: reservacion_extras reservacion_extras_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reservacion_extras
    ADD CONSTRAINT reservacion_extras_pkey PRIMARY KEY (id);


--
-- Name: reservacion_productos reservacion_productos_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reservacion_productos
    ADD CONSTRAINT reservacion_productos_pkey PRIMARY KEY (id);


--
-- Name: reservaciones reservaciones_folio_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reservaciones
    ADD CONSTRAINT reservaciones_folio_key UNIQUE (folio);


--
-- Name: reservaciones reservaciones_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reservaciones
    ADD CONSTRAINT reservaciones_pkey PRIMARY KEY (id);


--
-- Name: retiros_parciales retiros_parciales_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.retiros_parciales
    ADD CONSTRAINT retiros_parciales_pkey PRIMARY KEY (id);


--
-- Name: rol_permisos rol_permisos_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rol_permisos
    ADD CONSTRAINT rol_permisos_pkey PRIMARY KEY (rol_id, permiso_id);


--
-- Name: roles roles_nombre_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_nombre_key UNIQUE (nombre);


--
-- Name: roles roles_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_pkey PRIMARY KEY (id);


--
-- Name: sucursal_metodos_pago sucursal_metodos_pago_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sucursal_metodos_pago
    ADD CONSTRAINT sucursal_metodos_pago_pkey PRIMARY KEY (sucursal_id, metodo_pago_id);


--
-- Name: sucursales sucursales_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sucursales
    ADD CONSTRAINT sucursales_pkey PRIMARY KEY (id);


--
-- Name: tipos_evento tipos_evento_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tipos_evento
    ADD CONSTRAINT tipos_evento_pkey PRIMARY KEY (id);


--
-- Name: tokens_revocados tokens_revocados_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tokens_revocados
    ADD CONSTRAINT tokens_revocados_pkey PRIMARY KEY (jti);


--
-- Name: turnos turnos_nombre_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.turnos
    ADD CONSTRAINT turnos_nombre_key UNIQUE (nombre);


--
-- Name: turnos turnos_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.turnos
    ADD CONSTRAINT turnos_pkey PRIMARY KEY (id);


--
-- Name: tutores tutores_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tutores
    ADD CONSTRAINT tutores_pkey PRIMARY KEY (id);


--
-- Name: unidades_medida unidades_medida_codigo_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.unidades_medida
    ADD CONSTRAINT unidades_medida_codigo_key UNIQUE (codigo);


--
-- Name: unidades_medida unidades_medida_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.unidades_medida
    ADD CONSTRAINT unidades_medida_pkey PRIMARY KEY (id);


--
-- Name: cajas uq_cajas_codigo_sucursal; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cajas
    ADD CONSTRAINT uq_cajas_codigo_sucursal UNIQUE (codigo, sucursal_id);


--
-- Name: metodos_pago uq_metodos_pago_tipo; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.metodos_pago
    ADD CONSTRAINT uq_metodos_pago_tipo UNIQUE (tipo);


--
-- Name: pulseras uq_pulseras_rfid_sucursal; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pulseras
    ADD CONSTRAINT uq_pulseras_rfid_sucursal UNIQUE (pulsera_rfid, sucursal_id);


--
-- Name: refresh_tokens uq_refresh_token_hash; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.refresh_tokens
    ADD CONSTRAINT uq_refresh_token_hash UNIQUE (token_hash);


--
-- Name: usuarios_sucursal uq_usuario_sucursal; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuarios_sucursal
    ADD CONSTRAINT uq_usuario_sucursal UNIQUE (usuario_id, sucursal_id);


--
-- Name: usuarios uq_usuarios_email; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuarios
    ADD CONSTRAINT uq_usuarios_email UNIQUE (email);


--
-- Name: ws_tickets uq_ws_tickets_hash; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ws_tickets
    ADD CONSTRAINT uq_ws_tickets_hash UNIQUE (ticket_hash);


--
-- Name: usuarios usuarios_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuarios
    ADD CONSTRAINT usuarios_pkey PRIMARY KEY (id);


--
-- Name: usuarios_sucursal usuarios_sucursal_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuarios_sucursal
    ADD CONSTRAINT usuarios_sucursal_pkey PRIMARY KEY (id);


--
-- Name: ws_tickets ws_tickets_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ws_tickets
    ADD CONSTRAINT ws_tickets_pkey PRIMARY KEY (id);


--
-- Name: idx_apertura_cajero; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_apertura_cajero ON public.apertura_caja USING btree (cajero_id);


--
-- Name: idx_cajas_sucursal; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_cajas_sucursal ON public.cajas USING btree (sucursal_id);


--
-- Name: idx_capas_insumo_fifo; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_capas_insumo_fifo ON public.capas_costo_insumo USING btree (insumo_id, creado, id) WHERE (cantidad_restante > (0)::numeric);


--
-- Name: idx_cierre_apertura; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_cierre_apertura ON public.cierre_caja USING btree (apertura_caja_id);


--
-- Name: idx_comandas_sucursal_estado; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_comandas_sucursal_estado ON public.comandas USING btree (sucursal_id, estado_actual);


--
-- Name: idx_compras_sucursal_estado; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_compras_sucursal_estado ON public.compras USING btree (sucursal_id, estado);


--
-- Name: idx_compras_sucursal_folio; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_compras_sucursal_folio ON public.compras USING btree (sucursal_id, folio) WHERE (folio IS NOT NULL);


--
-- Name: idx_detalle_compras_compra; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_detalle_compras_compra ON public.detalle_compras USING btree (compra_id);


--
-- Name: idx_detalles_comanda_comanda; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_detalles_comanda_comanda ON public.detalles_comanda USING btree (comanda_id);


--
-- Name: idx_detalles_registro_sucursal_abiertos; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_detalles_registro_sucursal_abiertos ON public.detalles_registro USING btree (sucursal_id, registros_id) WHERE (salida IS NULL);


--
-- Name: idx_insumos_sucursal; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_insumos_sucursal ON public.insumos USING btree (sucursal_id);


--
-- Name: idx_lotes_puntos_celular_sucursal; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_lotes_puntos_celular_sucursal ON public.lotes_puntos USING btree (celular, sucursal_id);


--
-- Name: idx_lotes_puntos_vigencia; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_lotes_puntos_vigencia ON public.lotes_puntos USING btree (sucursal_id, celular, fecha_caducidad) WHERE (puntos_disponibles > 0);


--
-- Name: idx_movimientos_apertura; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_movimientos_apertura ON public.movimientos_caja USING btree (apertura_caja_id);


--
-- Name: idx_movimientos_apertura_metodo; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_movimientos_apertura_metodo ON public.movimientos_caja USING btree (apertura_caja_id, metodo_pago_id);


--
-- Name: idx_movimientos_inventario_insumo; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_movimientos_inventario_insumo ON public.movimientos_inventario USING btree (insumo_id, creado DESC);


--
-- Name: idx_movimientos_puntos_celular_sucursal; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_movimientos_puntos_celular_sucursal ON public.movimientos_puntos USING btree (celular, sucursal_id, creado);


--
-- Name: idx_pagos_idempotencia_comanda; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pagos_idempotencia_comanda ON public.pagos_idempotencia USING btree (comanda_id);


--
-- Name: idx_paquete_productos_paquete; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_paquete_productos_paquete ON public.paquete_productos USING btree (paquete_id);


--
-- Name: idx_pin_tokens_turno; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pin_tokens_turno ON public.pin_tokens USING btree (turno_id);


--
-- Name: idx_presentaciones_insumo_insumo; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_presentaciones_insumo_insumo ON public.presentaciones_insumo USING btree (insumo_id);


--
-- Name: idx_producto_combo_combo; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_producto_combo_combo ON public.producto_combo USING btree (combo_id);


--
-- Name: idx_producto_insumos_insumo; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_producto_insumos_insumo ON public.producto_insumos USING btree (insumo_id);


--
-- Name: idx_productos_sucursal; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_productos_sucursal ON public.productos USING btree (sucursal_id);


--
-- Name: idx_productos_sucursal_codigo; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_productos_sucursal_codigo ON public.productos USING btree (sucursal_id, codigo) WHERE (codigo IS NOT NULL);


--
-- Name: idx_proveedores_sucursal; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_proveedores_sucursal ON public.proveedores USING btree (sucursal_id);


--
-- Name: idx_refresh_tokens_expires; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_refresh_tokens_expires ON public.refresh_tokens USING btree (expires_at);


--
-- Name: idx_refresh_tokens_usuario; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_refresh_tokens_usuario ON public.refresh_tokens USING btree (usuario_id);


--
-- Name: idx_registros_reservacion_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_registros_reservacion_id ON public.registros USING btree (reservacion_id);


--
-- Name: idx_registros_sucursal_estado; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_registros_sucursal_estado ON public.registros USING btree (sucursal_id, estado);


--
-- Name: idx_reservaciones_sucursal_fecha; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_reservaciones_sucursal_fecha ON public.reservaciones USING btree (sucursal_id, fecha_evento) WHERE (activo = true);


--
-- Name: idx_retiros_apertura; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_retiros_apertura ON public.retiros_parciales USING btree (apertura_caja_id);


--
-- Name: idx_tokens_revocados_expires; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tokens_revocados_expires ON public.tokens_revocados USING btree (expires_at);


--
-- Name: idx_tutores_telefono_sucursal; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tutores_telefono_sucursal ON public.tutores USING btree (telefono, sucursal_id);


--
-- Name: idx_us_sucursal_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_us_sucursal_id ON public.usuarios_sucursal USING btree (sucursal_id);


--
-- Name: idx_us_usuario_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_us_usuario_id ON public.usuarios_sucursal USING btree (usuario_id);


--
-- Name: idx_usuarios_email_activo; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_usuarios_email_activo ON public.usuarios USING btree (email) WHERE (activo = true);


--
-- Name: idx_ws_tickets_expires; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ws_tickets_expires ON public.ws_tickets USING btree (expires_at);


--
-- Name: uq_apertura_caja_activa; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_apertura_caja_activa ON public.apertura_caja USING btree (caja_id) WHERE ((estado)::text <> 'CERRADA'::text);


--
-- Name: uq_apertura_cajero_activo; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_apertura_cajero_activo ON public.apertura_caja USING btree (cajero_id) WHERE ((estado)::text <> 'CERRADA'::text);


--
-- Name: uq_cajas_numero_sucursal_activo; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_cajas_numero_sucursal_activo ON public.cajas USING btree (numero, sucursal_id) WHERE (activo = true);


--
-- Name: uq_productos_nombre_sucursal; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_productos_nombre_sucursal ON public.productos USING btree (nombre, sucursal_id);


--
-- Name: uq_tipos_evento_nombre_sucursal; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_tipos_evento_nombre_sucursal ON public.tipos_evento USING btree (nombre, sucursal_id);


--
-- Name: sucursal_metodos_pago trg_sucursal_metodos_pago_modificado; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_sucursal_metodos_pago_modificado BEFORE UPDATE ON public.sucursal_metodos_pago FOR EACH ROW EXECUTE FUNCTION app.set_modificado();


--
-- Name: apertura_caja apertura_caja_caja_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.apertura_caja
    ADD CONSTRAINT apertura_caja_caja_id_fkey FOREIGN KEY (caja_id) REFERENCES public.cajas(id);


--
-- Name: apertura_caja apertura_caja_cajero_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.apertura_caja
    ADD CONSTRAINT apertura_caja_cajero_id_fkey FOREIGN KEY (cajero_id) REFERENCES public.usuarios(id);


--
-- Name: apertura_caja apertura_caja_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.apertura_caja
    ADD CONSTRAINT apertura_caja_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuarios(id);


--
-- Name: apertura_caja apertura_caja_modificado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.apertura_caja
    ADD CONSTRAINT apertura_caja_modificado_por_fkey FOREIGN KEY (modificado_por) REFERENCES public.usuarios(id);


--
-- Name: apertura_caja apertura_caja_turno_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.apertura_caja
    ADD CONSTRAINT apertura_caja_turno_id_fkey FOREIGN KEY (turno_id) REFERENCES public.turnos(id);


--
-- Name: cajas cajas_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cajas
    ADD CONSTRAINT cajas_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuarios(id);


--
-- Name: cajas cajas_modificado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cajas
    ADD CONSTRAINT cajas_modificado_por_fkey FOREIGN KEY (modificado_por) REFERENCES public.usuarios(id);


--
-- Name: cajas cajas_sucursal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cajas
    ADD CONSTRAINT cajas_sucursal_id_fkey FOREIGN KEY (sucursal_id) REFERENCES public.sucursales(id);


--
-- Name: capas_costo_insumo capas_costo_insumo_insumo_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.capas_costo_insumo
    ADD CONSTRAINT capas_costo_insumo_insumo_id_fkey FOREIGN KEY (insumo_id) REFERENCES public.insumos(id);


--
-- Name: cargos_extra_estancia cargos_extra_estancia_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cargos_extra_estancia
    ADD CONSTRAINT cargos_extra_estancia_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuarios(id);


--
-- Name: cargos_extra_estancia cargos_extra_estancia_detalles_registro_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cargos_extra_estancia
    ADD CONSTRAINT cargos_extra_estancia_detalles_registro_id_fkey FOREIGN KEY (detalles_registro_id) REFERENCES public.detalles_registro(id);


--
-- Name: cargos_extra_estancia cargos_extra_estancia_registros_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cargos_extra_estancia
    ADD CONSTRAINT cargos_extra_estancia_registros_id_fkey FOREIGN KEY (registros_id) REFERENCES public.registros(id);


--
-- Name: cargos_extra_estancia cargos_extra_estancia_sucursal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cargos_extra_estancia
    ADD CONSTRAINT cargos_extra_estancia_sucursal_id_fkey FOREIGN KEY (sucursal_id) REFERENCES public.sucursales(id);


--
-- Name: cierre_caja cierre_caja_administrador_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cierre_caja
    ADD CONSTRAINT cierre_caja_administrador_id_fkey FOREIGN KEY (administrador_id) REFERENCES public.usuarios(id);


--
-- Name: cierre_caja cierre_caja_apertura_caja_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cierre_caja
    ADD CONSTRAINT cierre_caja_apertura_caja_id_fkey FOREIGN KEY (apertura_caja_id) REFERENCES public.apertura_caja(id);


--
-- Name: cierre_caja cierre_caja_cajero_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cierre_caja
    ADD CONSTRAINT cierre_caja_cajero_id_fkey FOREIGN KEY (cajero_id) REFERENCES public.usuarios(id);


--
-- Name: cierre_caja cierre_caja_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cierre_caja
    ADD CONSTRAINT cierre_caja_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuarios(id);


--
-- Name: comandas comandas_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.comandas
    ADD CONSTRAINT comandas_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuarios(id);


--
-- Name: comandas comandas_modificado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.comandas
    ADD CONSTRAINT comandas_modificado_por_fkey FOREIGN KEY (modificado_por) REFERENCES public.usuarios(id);


--
-- Name: comandas comandas_reservacion_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.comandas
    ADD CONSTRAINT comandas_reservacion_id_fkey FOREIGN KEY (reservacion_id) REFERENCES public.reservaciones(id);


--
-- Name: comandas comandas_sucursal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.comandas
    ADD CONSTRAINT comandas_sucursal_id_fkey FOREIGN KEY (sucursal_id) REFERENCES public.sucursales(id);


--
-- Name: compras compras_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.compras
    ADD CONSTRAINT compras_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuarios(id);


--
-- Name: compras compras_modificado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.compras
    ADD CONSTRAINT compras_modificado_por_fkey FOREIGN KEY (modificado_por) REFERENCES public.usuarios(id);


--
-- Name: compras compras_proveedor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.compras
    ADD CONSTRAINT compras_proveedor_id_fkey FOREIGN KEY (proveedor_id) REFERENCES public.proveedores(id);


--
-- Name: compras compras_sucursal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.compras
    ADD CONSTRAINT compras_sucursal_id_fkey FOREIGN KEY (sucursal_id) REFERENCES public.sucursales(id);


--
-- Name: configuracion_lealtad configuracion_lealtad_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.configuracion_lealtad
    ADD CONSTRAINT configuracion_lealtad_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuarios(id) ON DELETE SET NULL;


--
-- Name: configuracion_lealtad configuracion_lealtad_modificado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.configuracion_lealtad
    ADD CONSTRAINT configuracion_lealtad_modificado_por_fkey FOREIGN KEY (modificado_por) REFERENCES public.usuarios(id) ON DELETE SET NULL;


--
-- Name: configuracion_lealtad configuracion_lealtad_sucursal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.configuracion_lealtad
    ADD CONSTRAINT configuracion_lealtad_sucursal_id_fkey FOREIGN KEY (sucursal_id) REFERENCES public.sucursales(id) ON DELETE CASCADE;


--
-- Name: detalle_compras detalle_compras_compra_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.detalle_compras
    ADD CONSTRAINT detalle_compras_compra_id_fkey FOREIGN KEY (compra_id) REFERENCES public.compras(id);


--
-- Name: detalle_compras detalle_compras_insumo_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.detalle_compras
    ADD CONSTRAINT detalle_compras_insumo_id_fkey FOREIGN KEY (insumo_id) REFERENCES public.insumos(id);


--
-- Name: detalle_compras detalle_compras_presentacion_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.detalle_compras
    ADD CONSTRAINT detalle_compras_presentacion_id_fkey FOREIGN KEY (presentacion_id) REFERENCES public.presentaciones_insumo(id);


--
-- Name: detalle_compras detalle_compras_unidad_medida_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.detalle_compras
    ADD CONSTRAINT detalle_compras_unidad_medida_id_fkey FOREIGN KEY (unidad_medida_id) REFERENCES public.unidades_medida(id);


--
-- Name: detalles_comanda detalles_comanda_comanda_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.detalles_comanda
    ADD CONSTRAINT detalles_comanda_comanda_id_fkey FOREIGN KEY (comanda_id) REFERENCES public.comandas(id) ON DELETE CASCADE;


--
-- Name: detalles_comanda detalles_comanda_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.detalles_comanda
    ADD CONSTRAINT detalles_comanda_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuarios(id);


--
-- Name: detalles_comanda detalles_comanda_es_hijo_de_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.detalles_comanda
    ADD CONSTRAINT detalles_comanda_es_hijo_de_fkey FOREIGN KEY (es_hijo_de) REFERENCES public.productos(id);


--
-- Name: detalles_comanda detalles_comanda_modificado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.detalles_comanda
    ADD CONSTRAINT detalles_comanda_modificado_por_fkey FOREIGN KEY (modificado_por) REFERENCES public.usuarios(id);


--
-- Name: detalles_comanda detalles_comanda_producto_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.detalles_comanda
    ADD CONSTRAINT detalles_comanda_producto_id_fkey FOREIGN KEY (producto_id) REFERENCES public.productos(id);


--
-- Name: detalles_comanda detalles_comanda_sucursal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.detalles_comanda
    ADD CONSTRAINT detalles_comanda_sucursal_id_fkey FOREIGN KEY (sucursal_id) REFERENCES public.sucursales(id);


--
-- Name: detalles_registro detalles_registro_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.detalles_registro
    ADD CONSTRAINT detalles_registro_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuarios(id);


--
-- Name: detalles_registro detalles_registro_modificado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.detalles_registro
    ADD CONSTRAINT detalles_registro_modificado_por_fkey FOREIGN KEY (modificado_por) REFERENCES public.usuarios(id);


--
-- Name: detalles_registro detalles_registro_ninos_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.detalles_registro
    ADD CONSTRAINT detalles_registro_ninos_id_fkey FOREIGN KEY (ninos_id) REFERENCES public.ninos(id);


--
-- Name: detalles_registro detalles_registro_productos_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.detalles_registro
    ADD CONSTRAINT detalles_registro_productos_id_fkey FOREIGN KEY (productos_id) REFERENCES public.productos(id);


--
-- Name: detalles_registro detalles_registro_pulseras_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.detalles_registro
    ADD CONSTRAINT detalles_registro_pulseras_id_fkey FOREIGN KEY (pulseras_id) REFERENCES public.pulseras(id);


--
-- Name: detalles_registro detalles_registro_registros_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.detalles_registro
    ADD CONSTRAINT detalles_registro_registros_id_fkey FOREIGN KEY (registros_id) REFERENCES public.registros(id);


--
-- Name: detalles_registro detalles_registro_sucursal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.detalles_registro
    ADD CONSTRAINT detalles_registro_sucursal_id_fkey FOREIGN KEY (sucursal_id) REFERENCES public.sucursales(id);


--
-- Name: extras extras_sucursal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extras
    ADD CONSTRAINT extras_sucursal_id_fkey FOREIGN KEY (sucursal_id) REFERENCES public.sucursales(id);


--
-- Name: pagos_ordenes fk_pagos_comanda; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pagos_ordenes
    ADD CONSTRAINT fk_pagos_comanda FOREIGN KEY (comanda_id) REFERENCES public.comandas(id) ON DELETE CASCADE;


--
-- Name: pagos_ordenes fk_pagos_metodo; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pagos_ordenes
    ADD CONSTRAINT fk_pagos_metodo FOREIGN KEY (metodo_pago_id) REFERENCES public.metodos_pago(id) ON DELETE RESTRICT;


--
-- Name: usuarios fk_usuarios_rol; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuarios
    ADD CONSTRAINT fk_usuarios_rol FOREIGN KEY (rol) REFERENCES public.roles(id);


--
-- Name: folios_compra_sucursal folios_compra_sucursal_sucursal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.folios_compra_sucursal
    ADD CONSTRAINT folios_compra_sucursal_sucursal_id_fkey FOREIGN KEY (sucursal_id) REFERENCES public.sucursales(id);


--
-- Name: folios_sucursal folios_sucursal_sucursal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.folios_sucursal
    ADD CONSTRAINT folios_sucursal_sucursal_id_fkey FOREIGN KEY (sucursal_id) REFERENCES public.sucursales(id);


--
-- Name: fotos fotos_registro_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fotos
    ADD CONSTRAINT fotos_registro_id_fkey FOREIGN KEY (registro_id) REFERENCES public.registros(id);


--
-- Name: insumos insumos_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.insumos
    ADD CONSTRAINT insumos_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuarios(id);


--
-- Name: insumos insumos_modificado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.insumos
    ADD CONSTRAINT insumos_modificado_por_fkey FOREIGN KEY (modificado_por) REFERENCES public.usuarios(id);


--
-- Name: insumos insumos_proveedor_principal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.insumos
    ADD CONSTRAINT insumos_proveedor_principal_id_fkey FOREIGN KEY (proveedor_principal_id) REFERENCES public.proveedores(id);


--
-- Name: insumos insumos_sucursal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.insumos
    ADD CONSTRAINT insumos_sucursal_id_fkey FOREIGN KEY (sucursal_id) REFERENCES public.sucursales(id);


--
-- Name: insumos insumos_unidad_base_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.insumos
    ADD CONSTRAINT insumos_unidad_base_id_fkey FOREIGN KEY (unidad_base_id) REFERENCES public.unidades_medida(id);


--
-- Name: insumos insumos_unidad_compra_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.insumos
    ADD CONSTRAINT insumos_unidad_compra_id_fkey FOREIGN KEY (unidad_compra_id) REFERENCES public.unidades_medida(id);


--
-- Name: lotes_puntos lotes_puntos_comanda_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lotes_puntos
    ADD CONSTRAINT lotes_puntos_comanda_id_fkey FOREIGN KEY (comanda_id) REFERENCES public.comandas(id);


--
-- Name: lotes_puntos lotes_puntos_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lotes_puntos
    ADD CONSTRAINT lotes_puntos_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuarios(id) ON DELETE SET NULL;


--
-- Name: lotes_puntos lotes_puntos_registro_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lotes_puntos
    ADD CONSTRAINT lotes_puntos_registro_id_fkey FOREIGN KEY (registro_id) REFERENCES public.registros(id);


--
-- Name: lotes_puntos lotes_puntos_reservacion_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lotes_puntos
    ADD CONSTRAINT lotes_puntos_reservacion_id_fkey FOREIGN KEY (reservacion_id) REFERENCES public.reservaciones(id);


--
-- Name: lotes_puntos lotes_puntos_sucursal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lotes_puntos
    ADD CONSTRAINT lotes_puntos_sucursal_id_fkey FOREIGN KEY (sucursal_id) REFERENCES public.sucursales(id);


--
-- Name: movimientos_caja movimientos_caja_apertura_caja_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.movimientos_caja
    ADD CONSTRAINT movimientos_caja_apertura_caja_id_fkey FOREIGN KEY (apertura_caja_id) REFERENCES public.apertura_caja(id);


--
-- Name: movimientos_caja movimientos_caja_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.movimientos_caja
    ADD CONSTRAINT movimientos_caja_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuarios(id);


--
-- Name: movimientos_caja movimientos_caja_metodo_pago_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.movimientos_caja
    ADD CONSTRAINT movimientos_caja_metodo_pago_id_fkey FOREIGN KEY (metodo_pago_id) REFERENCES public.metodos_pago(id);


--
-- Name: movimientos_inventario movimientos_inventario_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.movimientos_inventario
    ADD CONSTRAINT movimientos_inventario_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuarios(id);


--
-- Name: movimientos_inventario movimientos_inventario_insumo_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.movimientos_inventario
    ADD CONSTRAINT movimientos_inventario_insumo_id_fkey FOREIGN KEY (insumo_id) REFERENCES public.insumos(id);


--
-- Name: movimientos_inventario movimientos_inventario_sucursal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.movimientos_inventario
    ADD CONSTRAINT movimientos_inventario_sucursal_id_fkey FOREIGN KEY (sucursal_id) REFERENCES public.sucursales(id);


--
-- Name: movimientos_puntos movimientos_puntos_comanda_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.movimientos_puntos
    ADD CONSTRAINT movimientos_puntos_comanda_id_fkey FOREIGN KEY (comanda_id) REFERENCES public.comandas(id);


--
-- Name: movimientos_puntos movimientos_puntos_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.movimientos_puntos
    ADD CONSTRAINT movimientos_puntos_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuarios(id) ON DELETE SET NULL;


--
-- Name: movimientos_puntos movimientos_puntos_lote_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.movimientos_puntos
    ADD CONSTRAINT movimientos_puntos_lote_id_fkey FOREIGN KEY (lote_id) REFERENCES public.lotes_puntos(id);


--
-- Name: movimientos_puntos movimientos_puntos_registro_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.movimientos_puntos
    ADD CONSTRAINT movimientos_puntos_registro_id_fkey FOREIGN KEY (registro_id) REFERENCES public.registros(id);


--
-- Name: movimientos_puntos movimientos_puntos_reservacion_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.movimientos_puntos
    ADD CONSTRAINT movimientos_puntos_reservacion_id_fkey FOREIGN KEY (reservacion_id) REFERENCES public.reservaciones(id);


--
-- Name: movimientos_puntos movimientos_puntos_sucursal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.movimientos_puntos
    ADD CONSTRAINT movimientos_puntos_sucursal_id_fkey FOREIGN KEY (sucursal_id) REFERENCES public.sucursales(id);


--
-- Name: ninos ninos_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ninos
    ADD CONSTRAINT ninos_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuarios(id);


--
-- Name: ninos ninos_modificado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ninos
    ADD CONSTRAINT ninos_modificado_por_fkey FOREIGN KEY (modificado_por) REFERENCES public.usuarios(id);


--
-- Name: ninos ninos_sucursal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ninos
    ADD CONSTRAINT ninos_sucursal_id_fkey FOREIGN KEY (sucursal_id) REFERENCES public.sucursales(id);


--
-- Name: pagos_estancia pagos_estancia_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pagos_estancia
    ADD CONSTRAINT pagos_estancia_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuarios(id);


--
-- Name: pagos_estancia pagos_estancia_metodos_pago_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pagos_estancia
    ADD CONSTRAINT pagos_estancia_metodos_pago_id_fkey FOREIGN KEY (metodos_pago_id) REFERENCES public.metodos_pago(id);


--
-- Name: pagos_estancia pagos_estancia_registros_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pagos_estancia
    ADD CONSTRAINT pagos_estancia_registros_id_fkey FOREIGN KEY (registros_id) REFERENCES public.registros(id);


--
-- Name: pagos_estancia pagos_estancia_sucursal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pagos_estancia
    ADD CONSTRAINT pagos_estancia_sucursal_id_fkey FOREIGN KEY (sucursal_id) REFERENCES public.sucursales(id);


--
-- Name: pagos_idempotencia pagos_idempotencia_comanda_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pagos_idempotencia
    ADD CONSTRAINT pagos_idempotencia_comanda_id_fkey FOREIGN KEY (comanda_id) REFERENCES public.comandas(id);


--
-- Name: pagos_idempotencia pagos_idempotencia_sucursal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pagos_idempotencia
    ADD CONSTRAINT pagos_idempotencia_sucursal_id_fkey FOREIGN KEY (sucursal_id) REFERENCES public.sucursales(id);


--
-- Name: pagos_idempotencia pagos_idempotencia_usuario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pagos_idempotencia
    ADD CONSTRAINT pagos_idempotencia_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES public.usuarios(id);


--
-- Name: pagos_reservacion pagos_reservacion_metodo_pago_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pagos_reservacion
    ADD CONSTRAINT pagos_reservacion_metodo_pago_id_fkey FOREIGN KEY (metodo_pago_id) REFERENCES public.metodos_pago(id);


--
-- Name: pagos_reservacion pagos_reservacion_reservacion_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pagos_reservacion
    ADD CONSTRAINT pagos_reservacion_reservacion_id_fkey FOREIGN KEY (reservacion_id) REFERENCES public.reservaciones(id);


--
-- Name: paquete_productos paquete_productos_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.paquete_productos
    ADD CONSTRAINT paquete_productos_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuarios(id);


--
-- Name: paquete_productos paquete_productos_modificado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.paquete_productos
    ADD CONSTRAINT paquete_productos_modificado_por_fkey FOREIGN KEY (modificado_por) REFERENCES public.usuarios(id);


--
-- Name: paquete_productos paquete_productos_paquete_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.paquete_productos
    ADD CONSTRAINT paquete_productos_paquete_id_fkey FOREIGN KEY (paquete_id) REFERENCES public.paquetes(id) ON DELETE CASCADE;


--
-- Name: paquete_productos paquete_productos_producto_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.paquete_productos
    ADD CONSTRAINT paquete_productos_producto_id_fkey FOREIGN KEY (producto_id) REFERENCES public.productos(id);


--
-- Name: paquete_tipos_evento paquete_tipos_evento_paquete_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.paquete_tipos_evento
    ADD CONSTRAINT paquete_tipos_evento_paquete_id_fkey FOREIGN KEY (paquete_id) REFERENCES public.paquetes(id);


--
-- Name: paquete_tipos_evento paquete_tipos_evento_tipo_evento_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.paquete_tipos_evento
    ADD CONSTRAINT paquete_tipos_evento_tipo_evento_id_fkey FOREIGN KEY (tipo_evento_id) REFERENCES public.tipos_evento(id);


--
-- Name: paquetes paquetes_sucursal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.paquetes
    ADD CONSTRAINT paquetes_sucursal_id_fkey FOREIGN KEY (sucursal_id) REFERENCES public.sucursales(id);


--
-- Name: pin_tokens pin_tokens_turno_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pin_tokens
    ADD CONSTRAINT pin_tokens_turno_id_fkey FOREIGN KEY (turno_id) REFERENCES public.apertura_caja(id);


--
-- Name: pin_tokens pin_tokens_usuario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pin_tokens
    ADD CONSTRAINT pin_tokens_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES public.usuarios(id);


--
-- Name: presentaciones_insumo presentaciones_insumo_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.presentaciones_insumo
    ADD CONSTRAINT presentaciones_insumo_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuarios(id);


--
-- Name: presentaciones_insumo presentaciones_insumo_insumo_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.presentaciones_insumo
    ADD CONSTRAINT presentaciones_insumo_insumo_id_fkey FOREIGN KEY (insumo_id) REFERENCES public.insumos(id);


--
-- Name: presentaciones_insumo presentaciones_insumo_modificado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.presentaciones_insumo
    ADD CONSTRAINT presentaciones_insumo_modificado_por_fkey FOREIGN KEY (modificado_por) REFERENCES public.usuarios(id);


--
-- Name: producto_combo producto_combo_combo_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.producto_combo
    ADD CONSTRAINT producto_combo_combo_id_fkey FOREIGN KEY (combo_id) REFERENCES public.productos(id) ON DELETE CASCADE;


--
-- Name: producto_combo producto_combo_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.producto_combo
    ADD CONSTRAINT producto_combo_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuarios(id);


--
-- Name: producto_combo producto_combo_modificado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.producto_combo
    ADD CONSTRAINT producto_combo_modificado_por_fkey FOREIGN KEY (modificado_por) REFERENCES public.usuarios(id);


--
-- Name: producto_combo producto_combo_producto_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.producto_combo
    ADD CONSTRAINT producto_combo_producto_id_fkey FOREIGN KEY (producto_id) REFERENCES public.productos(id);


--
-- Name: producto_insumos producto_insumos_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.producto_insumos
    ADD CONSTRAINT producto_insumos_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuarios(id);


--
-- Name: producto_insumos producto_insumos_insumo_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.producto_insumos
    ADD CONSTRAINT producto_insumos_insumo_id_fkey FOREIGN KEY (insumo_id) REFERENCES public.insumos(id);


--
-- Name: producto_insumos producto_insumos_modificado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.producto_insumos
    ADD CONSTRAINT producto_insumos_modificado_por_fkey FOREIGN KEY (modificado_por) REFERENCES public.usuarios(id);


--
-- Name: producto_insumos producto_insumos_producto_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.producto_insumos
    ADD CONSTRAINT producto_insumos_producto_id_fkey FOREIGN KEY (producto_id) REFERENCES public.productos(id);


--
-- Name: productos productos_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.productos
    ADD CONSTRAINT productos_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuarios(id);


--
-- Name: productos productos_modificado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.productos
    ADD CONSTRAINT productos_modificado_por_fkey FOREIGN KEY (modificado_por) REFERENCES public.usuarios(id);


--
-- Name: productos productos_sucursal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.productos
    ADD CONSTRAINT productos_sucursal_id_fkey FOREIGN KEY (sucursal_id) REFERENCES public.sucursales(id);


--
-- Name: proveedores proveedores_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proveedores
    ADD CONSTRAINT proveedores_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuarios(id);


--
-- Name: proveedores proveedores_modificado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proveedores
    ADD CONSTRAINT proveedores_modificado_por_fkey FOREIGN KEY (modificado_por) REFERENCES public.usuarios(id);


--
-- Name: proveedores proveedores_sucursal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proveedores
    ADD CONSTRAINT proveedores_sucursal_id_fkey FOREIGN KEY (sucursal_id) REFERENCES public.sucursales(id);


--
-- Name: pulseras pulseras_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pulseras
    ADD CONSTRAINT pulseras_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuarios(id);


--
-- Name: pulseras pulseras_modificado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pulseras
    ADD CONSTRAINT pulseras_modificado_por_fkey FOREIGN KEY (modificado_por) REFERENCES public.usuarios(id);


--
-- Name: pulseras pulseras_sucursal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pulseras
    ADD CONSTRAINT pulseras_sucursal_id_fkey FOREIGN KEY (sucursal_id) REFERENCES public.sucursales(id);


--
-- Name: refresh_tokens refresh_tokens_sucursal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.refresh_tokens
    ADD CONSTRAINT refresh_tokens_sucursal_id_fkey FOREIGN KEY (sucursal_id) REFERENCES public.sucursales(id) ON DELETE SET NULL;


--
-- Name: refresh_tokens refresh_tokens_usuario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.refresh_tokens
    ADD CONSTRAINT refresh_tokens_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES public.usuarios(id) ON DELETE CASCADE;


--
-- Name: registros registros_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.registros
    ADD CONSTRAINT registros_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuarios(id);


--
-- Name: registros registros_modificado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.registros
    ADD CONSTRAINT registros_modificado_por_fkey FOREIGN KEY (modificado_por) REFERENCES public.usuarios(id);


--
-- Name: registros registros_pulseras_tutor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.registros
    ADD CONSTRAINT registros_pulseras_tutor_id_fkey FOREIGN KEY (pulseras_tutor_id) REFERENCES public.pulseras(id);


--
-- Name: registros registros_reservacion_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.registros
    ADD CONSTRAINT registros_reservacion_id_fkey FOREIGN KEY (reservacion_id) REFERENCES public.reservaciones(id);


--
-- Name: registros registros_sucursal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.registros
    ADD CONSTRAINT registros_sucursal_id_fkey FOREIGN KEY (sucursal_id) REFERENCES public.sucursales(id);


--
-- Name: registros registros_tutores_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.registros
    ADD CONSTRAINT registros_tutores_id_fkey FOREIGN KEY (tutores_id) REFERENCES public.tutores(id);


--
-- Name: reservacion_extras reservacion_extras_extra_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reservacion_extras
    ADD CONSTRAINT reservacion_extras_extra_id_fkey FOREIGN KEY (extra_id) REFERENCES public.extras(id);


--
-- Name: reservacion_extras reservacion_extras_reservacion_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reservacion_extras
    ADD CONSTRAINT reservacion_extras_reservacion_id_fkey FOREIGN KEY (reservacion_id) REFERENCES public.reservaciones(id);


--
-- Name: reservacion_productos reservacion_productos_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reservacion_productos
    ADD CONSTRAINT reservacion_productos_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuarios(id);


--
-- Name: reservacion_productos reservacion_productos_producto_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reservacion_productos
    ADD CONSTRAINT reservacion_productos_producto_id_fkey FOREIGN KEY (producto_id) REFERENCES public.productos(id);


--
-- Name: reservacion_productos reservacion_productos_reservacion_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reservacion_productos
    ADD CONSTRAINT reservacion_productos_reservacion_id_fkey FOREIGN KEY (reservacion_id) REFERENCES public.reservaciones(id);


--
-- Name: reservaciones reservaciones_paquete_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reservaciones
    ADD CONSTRAINT reservaciones_paquete_id_fkey FOREIGN KEY (paquete_id) REFERENCES public.paquetes(id);


--
-- Name: reservaciones reservaciones_sucursal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reservaciones
    ADD CONSTRAINT reservaciones_sucursal_id_fkey FOREIGN KEY (sucursal_id) REFERENCES public.sucursales(id);


--
-- Name: reservaciones reservaciones_tipo_evento_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reservaciones
    ADD CONSTRAINT reservaciones_tipo_evento_id_fkey FOREIGN KEY (tipo_evento_id) REFERENCES public.tipos_evento(id);


--
-- Name: retiros_parciales retiros_parciales_apertura_caja_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.retiros_parciales
    ADD CONSTRAINT retiros_parciales_apertura_caja_id_fkey FOREIGN KEY (apertura_caja_id) REFERENCES public.apertura_caja(id);


--
-- Name: retiros_parciales retiros_parciales_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.retiros_parciales
    ADD CONSTRAINT retiros_parciales_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuarios(id);


--
-- Name: rol_permisos rol_permisos_permiso_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rol_permisos
    ADD CONSTRAINT rol_permisos_permiso_id_fkey FOREIGN KEY (permiso_id) REFERENCES public.permisos(id) ON DELETE CASCADE;


--
-- Name: rol_permisos rol_permisos_rol_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rol_permisos
    ADD CONSTRAINT rol_permisos_rol_id_fkey FOREIGN KEY (rol_id) REFERENCES public.roles(id) ON DELETE CASCADE;


--
-- Name: sucursal_metodos_pago sucursal_metodos_pago_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sucursal_metodos_pago
    ADD CONSTRAINT sucursal_metodos_pago_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuarios(id) ON DELETE SET NULL;


--
-- Name: sucursal_metodos_pago sucursal_metodos_pago_metodo_pago_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sucursal_metodos_pago
    ADD CONSTRAINT sucursal_metodos_pago_metodo_pago_id_fkey FOREIGN KEY (metodo_pago_id) REFERENCES public.metodos_pago(id);


--
-- Name: sucursal_metodos_pago sucursal_metodos_pago_modificado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sucursal_metodos_pago
    ADD CONSTRAINT sucursal_metodos_pago_modificado_por_fkey FOREIGN KEY (modificado_por) REFERENCES public.usuarios(id) ON DELETE SET NULL;


--
-- Name: sucursal_metodos_pago sucursal_metodos_pago_sucursal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sucursal_metodos_pago
    ADD CONSTRAINT sucursal_metodos_pago_sucursal_id_fkey FOREIGN KEY (sucursal_id) REFERENCES public.sucursales(id) ON DELETE CASCADE;


--
-- Name: sucursales sucursales_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sucursales
    ADD CONSTRAINT sucursales_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuarios(id) ON DELETE SET NULL;


--
-- Name: sucursales sucursales_modificado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sucursales
    ADD CONSTRAINT sucursales_modificado_por_fkey FOREIGN KEY (modificado_por) REFERENCES public.usuarios(id) ON DELETE SET NULL;


--
-- Name: tipos_evento tipos_evento_sucursal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tipos_evento
    ADD CONSTRAINT tipos_evento_sucursal_id_fkey FOREIGN KEY (sucursal_id) REFERENCES public.sucursales(id);


--
-- Name: turnos turnos_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.turnos
    ADD CONSTRAINT turnos_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuarios(id);


--
-- Name: turnos turnos_modificado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.turnos
    ADD CONSTRAINT turnos_modificado_por_fkey FOREIGN KEY (modificado_por) REFERENCES public.usuarios(id);


--
-- Name: tutores tutores_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tutores
    ADD CONSTRAINT tutores_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuarios(id);


--
-- Name: tutores tutores_modificado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tutores
    ADD CONSTRAINT tutores_modificado_por_fkey FOREIGN KEY (modificado_por) REFERENCES public.usuarios(id);


--
-- Name: tutores tutores_sucursal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tutores
    ADD CONSTRAINT tutores_sucursal_id_fkey FOREIGN KEY (sucursal_id) REFERENCES public.sucursales(id);


--
-- Name: usuarios usuarios_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuarios
    ADD CONSTRAINT usuarios_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuarios(id) ON DELETE SET NULL;


--
-- Name: usuarios usuarios_modificado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuarios
    ADD CONSTRAINT usuarios_modificado_por_fkey FOREIGN KEY (modificado_por) REFERENCES public.usuarios(id) ON DELETE SET NULL;


--
-- Name: usuarios_sucursal usuarios_sucursal_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuarios_sucursal
    ADD CONSTRAINT usuarios_sucursal_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuarios(id) ON DELETE SET NULL;


--
-- Name: usuarios_sucursal usuarios_sucursal_modificado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuarios_sucursal
    ADD CONSTRAINT usuarios_sucursal_modificado_por_fkey FOREIGN KEY (modificado_por) REFERENCES public.usuarios(id) ON DELETE SET NULL;


--
-- Name: usuarios_sucursal usuarios_sucursal_sucursal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuarios_sucursal
    ADD CONSTRAINT usuarios_sucursal_sucursal_id_fkey FOREIGN KEY (sucursal_id) REFERENCES public.sucursales(id) ON DELETE CASCADE;


--
-- Name: usuarios_sucursal usuarios_sucursal_usuario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuarios_sucursal
    ADD CONSTRAINT usuarios_sucursal_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES public.usuarios(id) ON DELETE CASCADE;


--
-- Name: sucursal_metodos_pago; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.sucursal_metodos_pago ENABLE ROW LEVEL SECURITY;

--
-- Name: sucursal_metodos_pago sucursal_metodos_pago_select; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY sucursal_metodos_pago_select ON public.sucursal_metodos_pago FOR SELECT USING (true);


--
-- Name: sucursal_metodos_pago sucursal_metodos_pago_write; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY sucursal_metodos_pago_write ON public.sucursal_metodos_pago USING ((app.usuario_tiene_rol(ARRAY['admin'::text]) OR app.usuario_en_sucursal(sucursal_id))) WITH CHECK ((app.usuario_tiene_rol(ARRAY['admin'::text]) OR app.usuario_en_sucursal(sucursal_id)));


--
-- PostgreSQL database dump complete
--



-- ------------------------------------------------------ Datos de catálogo
--
-- PostgreSQL database dump
--


-- Dumped from database version 16.14
-- Dumped by pg_dump version 16.14

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Data for Name: metodos_pago; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.metodos_pago (id, nombre, descripcion, creado, creado_por, modificado, modificado_por, tipo, comision_porcentaje, requiere_referencia) VALUES ('d04d2db7-6bf6-4f77-891b-d827c9ed08e9', 'Efectivo', NULL, '2026-10-03 02:34:52.043315+00', NULL, '2026-10-03 02:34:52.043315+00', NULL, 'E', NULL, false);
INSERT INTO public.metodos_pago (id, nombre, descripcion, creado, creado_por, modificado, modificado_por, tipo, comision_porcentaje, requiere_referencia) VALUES ('9cd2bd40-bfa4-4b9b-9463-be59b7a56e18', 'Otro', NULL, '2026-10-03 02:34:52.043315+00', NULL, '2026-10-03 02:34:52.043315+00', NULL, 'O', NULL, false);
INSERT INTO public.metodos_pago (id, nombre, descripcion, creado, creado_por, modificado, modificado_por, tipo, comision_porcentaje, requiere_referencia) VALUES ('0c9eb0ae-e568-44e9-a2df-bbb0918a423c', 'Cupones', NULL, '2026-10-03 02:34:52.043315+00', NULL, '2026-10-03 02:34:52.043315+00', NULL, 'C', NULL, false);
INSERT INTO public.metodos_pago (id, nombre, descripcion, creado, creado_por, modificado, modificado_por, tipo, comision_porcentaje, requiere_referencia) VALUES ('7ccce8b9-f9c4-4b66-9e0a-e8fe76e3154f', 'Lealtad', NULL, '2026-10-03 02:34:52.043315+00', NULL, '2026-10-03 02:34:52.043315+00', NULL, 'L', NULL, false);
INSERT INTO public.metodos_pago (id, nombre, descripcion, creado, creado_por, modificado, modificado_por, tipo, comision_porcentaje, requiere_referencia) VALUES ('2748042c-81f6-422e-882e-13a659d884da', 'Tarjeta', NULL, '2026-10-03 02:34:52.043315+00', NULL, '2026-10-03 02:34:52.043315+00', NULL, 'T', NULL, false);


--
-- Data for Name: permisos; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (1, 'usuarios:listar', 'Listar usuarios', 'usuarios', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (2, 'usuarios:ver', 'Ver detalle de usuario', 'usuarios', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (3, 'usuarios:crear', 'Crear usuarios', 'usuarios', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (4, 'usuarios:editar', 'Editar usuarios', 'usuarios', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (5, 'usuarios:eliminar', 'Eliminar usuarios', 'usuarios', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (6, 'sucursales:listar', 'Listar sucursales', 'sucursales', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (7, 'sucursales:ver', 'Ver detalle de sucursal', 'sucursales', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (8, 'sucursales:crear', 'Crear sucursales', 'sucursales', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (9, 'sucursales:editar', 'Editar sucursales', 'sucursales', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (10, 'sucursales:eliminar', 'Eliminar sucursales', 'sucursales', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (32, 'permisos:ver', 'Ver configuración de permisos', 'permisos', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (33, 'permisos:editar', 'Editar permisos de roles', 'permisos', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (34, 'pos:acceder', 'Acceder al módulo POS', 'pos', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (38, 'inventario:ver', 'Ver inventario y stock', 'inventario', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (39, 'inventario:gestionar_productos', 'Crear y editar productos', 'inventario', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (40, 'inventario:eliminar_producto', 'Eliminar productos', 'inventario', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (41, 'inventario:registrar_movimiento', 'Registrar movimientos de stock', 'inventario', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (42, 'inventario:gestionar_proveedores', 'Gestionar proveedores', 'inventario', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (43, 'restaurante:ver_mesas', 'Ver estado de mesas', 'restaurante', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (44, 'restaurante:gestionar_mesas', 'Configurar mesas', 'restaurante', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (45, 'restaurante:ver_menu', 'Ver menú', 'restaurante', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (46, 'restaurante:gestionar_menu', 'Crear y editar el menú', 'restaurante', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (47, 'restaurante:ver_pedidos', 'Ver pedidos del turno', 'restaurante', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (48, 'restaurante:crear_pedido', 'Tomar pedidos', 'restaurante', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (49, 'restaurante:editar_pedido', 'Modificar pedidos activos', 'restaurante', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (50, 'restaurante:gestionar_cocina', 'Actualizar estado de comandas', 'restaurante', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (51, 'reportes:dashboard', 'Ver dashboard general', 'reportes', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (52, 'reportes:ventas', 'Ver reporte de ventas', 'reportes', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (53, 'reportes:inventario', 'Ver reporte de inventario', 'reportes', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (54, 'reportes:usuarios', 'Ver reporte de actividad de usuarios', 'reportes', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (55, 'reservaciones:listar', 'Listar reservaciones', 'reservaciones', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (56, 'reservaciones:ver', 'Ver detalle de reservación', 'reservaciones', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (57, 'reservaciones:crear', 'Crear reservaciones', 'reservaciones', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (58, 'reservaciones:editar', 'Editar reservaciones', 'reservaciones', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (59, 'reservaciones:eliminar', 'Eliminar reservaciones', 'reservaciones', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (60, 'reservaciones:gestionar_pagos', 'Gestionar pagos de una reservación', 'reservaciones', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (61, 'reservaciones:gestionar_extras', 'Gestionar extras de una reservación', 'reservaciones', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (62, 'paquetes:listar', 'Listar paquetes', 'paquetes', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (63, 'paquetes:ver', 'Ver detalle de paquete', 'paquetes', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (64, 'paquetes:crear', 'Crear paquetes', 'paquetes', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (65, 'paquetes:editar', 'Editar paquetes', 'paquetes', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (66, 'paquetes:eliminar', 'Eliminar paquetes', 'paquetes', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (67, 'tipos_evento:listar', 'Listar tipos de evento', 'tipos_evento', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (68, 'tipos_evento:ver', 'Ver detalle de tipo de evento', 'tipos_evento', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (69, 'tipos_evento:crear', 'Crear tipos de evento', 'tipos_evento', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (70, 'tipos_evento:editar', 'Editar tipos de evento', 'tipos_evento', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (71, 'tipos_evento:eliminar', 'Eliminar tipos de evento', 'tipos_evento', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (72, 'metodos_pago:listar', 'Listar métodos de pago', 'metodos_pago', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (73, 'metodos_pago:ver', 'Ver detalle de método de pago', 'metodos_pago', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (74, 'metodos_pago:crear', 'Crear métodos de pago', 'metodos_pago', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (75, 'metodos_pago:editar', 'Editar métodos de pago', 'metodos_pago', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (76, 'metodos_pago:eliminar', 'Eliminar métodos de pago', 'metodos_pago', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (77, 'extras:listar', 'Listar extras', 'extras', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (78, 'extras:ver', 'Ver detalle de extra', 'extras', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (79, 'extras:crear', 'Crear extras', 'extras', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (80, 'extras:editar', 'Editar extras', 'extras', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (81, 'extras:eliminar', 'Eliminar extras', 'extras', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (82, 'estancias:ver_activos', 'Ver niños en estancia activa', 'estancias', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (83, 'estancias:checkin', 'Registrar entrada de niños', 'estancias', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (84, 'estancias:checkout', 'Registrar salida de niños', 'estancias', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (85, 'estancias:gestionar_pagos', 'Registrar pagos extra de estancia', 'estancias', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (86, 'pulseras:listar', 'Listar pulseras e inventario', 'pulseras', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (87, 'pulseras:crear', 'Registrar pulseras nuevas', 'pulseras', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (88, 'pulseras:editar', 'Editar pulseras', 'pulseras', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (89, 'pulseras:eliminar', 'Eliminar pulseras', 'pulseras', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (94, 'inventario:gestionar_insumos', 'Crear y editar insumos', 'inventario', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (95, 'inventario:eliminar_insumo', 'Eliminar insumos', 'inventario', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (96, 'inventario:eliminar_proveedor', 'Eliminar proveedores', 'inventario', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (97, 'cajas:listar', 'Listar cajas de la sucursal', 'cajas', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (98, 'cajas:crear', 'Registrar una nueva caja física', 'cajas', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (99, 'turnos_caja:abrir', 'Abrir turno de caja', 'turnos_caja', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (100, 'turnos_caja:ver_activo', 'Ver turno activo y catálogos', 'turnos_caja', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (101, 'turnos_caja:conteo', 'Enviar conteo físico del cajero', 'turnos_caja', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (102, 'turnos_caja:revision_admin', 'Autenticar administrador para el balance', 'turnos_caja', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (103, 'turnos_caja:confirmar', 'Confirmar cierre definitivo del turno', 'turnos_caja', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (104, 'turnos_caja:cancelar', 'Cancelar conteo y regresar a ABIERTA', 'turnos_caja', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (105, 'turnos_caja:historial', 'Consultar historial de arqueos', 'turnos_caja', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (106, 'retiros_parciales:crear', 'Registrar retiro parcial de efectivo', 'retiros_parciales', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (107, 'retiros_parciales:listar', 'Listar retiros parciales del turno', 'retiros_parciales', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (108, 'inventario:ver_movimientos', 'Ver historial de movimientos de inventario', 'inventario', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (109, 'inventario:gestionar_compras', 'Crear y recibir órdenes de compra', 'inventario', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (110, 'horarios:listar', 'Ver la página de gestión de horarios', 'horarios', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (111, 'horarios:crear', 'Crear horarios de trabajo', 'horarios', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (112, 'horarios:editar', 'Editar horarios de trabajo', 'horarios', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (113, 'horarios:eliminar', 'Eliminar horarios de trabajo', 'horarios', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (114, 'cajas:editar', 'Editar datos de una caja física', 'cajas', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (115, 'cajas:eliminar', 'Desactivar una caja física', 'cajas', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (116, 'lealtad:gestionar_configuracion', 'Configurar % de retorno, caducidad y valor del punto por sucursal', 'lealtad', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (117, 'lealtad:ver_saldo', 'Consultar saldo y kardex de puntos de un cliente', 'lealtad', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (118, 'lealtad:redimir', 'Canjear puntos como descuento al cobrar', 'lealtad', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (119, 'lealtad:ver_reporte', 'Ver reporte agregado de puntos de lealtad', 'lealtad', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (120, 'reservaciones:gestionar_productos', 'Gestionar productos ad-hoc de una reservación', 'reservaciones', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (121, 'turnos_caja:ingreso_efectivo', 'Registrar ingreso de efectivo en el turno', 'turnos_caja', NULL);
INSERT INTO public.permisos (id, codigo, nombre, modulo, descripcion) VALUES (122, 'lealtad:ajustar', 'Ajustar manualmente el saldo de puntos de un cliente', 'lealtad', NULL);


--
-- Data for Name: roles; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.roles (id, nombre, descripcion, activo) VALUES (1, 'AdministradorSistema', 'Acceso total al sistema sin restricción de sucursal.', true);
INSERT INTO public.roles (id, nombre, descripcion, activo) VALUES (2, 'Administrador', 'Gestión completa de su sucursal asignada.', true);
INSERT INTO public.roles (id, nombre, descripcion, activo) VALUES (3, 'Cajero', 'Operaciones de caja y punto de venta.', true);
INSERT INTO public.roles (id, nombre, descripcion, activo) VALUES (4, 'Cocina', 'Gestión de órdenes y comandas de cocina.', true);
INSERT INTO public.roles (id, nombre, descripcion, activo) VALUES (5, 'Personal de atención de niños', 'Registra entradas/salidas de niños y cobra estancias en el módulo de Estancias.', true);


--
-- Data for Name: rol_permisos; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 1);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 2);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 3);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 4);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 5);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 6);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 7);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 8);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 9);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 10);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 32);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 33);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 1);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 2);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 3);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 4);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 5);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 32);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 34);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 38);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 39);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 41);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 42);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 43);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 44);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 45);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 46);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 47);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 48);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 49);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 50);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 51);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 52);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 53);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (3, 34);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (3, 41);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (3, 43);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (3, 45);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (3, 47);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (3, 48);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (3, 49);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (4, 43);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (4, 45);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (4, 47);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (4, 50);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 34);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 38);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 39);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 40);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 41);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 42);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 43);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 44);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 45);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 46);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 47);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 48);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 49);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 50);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 51);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 52);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 53);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 54);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 55);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 56);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 57);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 58);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 59);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 60);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 61);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 62);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 63);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 64);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 65);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 66);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 67);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 68);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 69);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 70);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 71);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 72);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 73);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 74);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 75);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 76);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 77);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 78);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 79);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 80);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 81);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 82);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 83);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 84);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 85);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 55);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 56);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 57);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 58);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 59);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 60);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 61);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 62);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 63);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 64);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 65);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 66);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 67);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 68);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 69);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 70);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 71);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 72);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 73);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 74);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 75);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 76);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 77);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 78);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 79);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 80);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 81);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 82);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 83);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 84);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 85);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (3, 55);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (3, 56);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (3, 57);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (3, 58);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (3, 60);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (3, 61);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (3, 82);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (3, 83);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (3, 84);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (3, 85);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (3, 62);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (3, 63);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (3, 67);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (3, 68);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (3, 72);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (3, 73);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (3, 77);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (3, 78);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 6);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 7);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 86);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 86);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 87);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 87);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 88);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 88);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 89);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 89);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 94);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 94);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 95);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 95);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 96);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 96);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 97);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 98);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 99);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 100);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 101);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 102);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 103);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 104);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 105);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 106);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 107);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 97);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 98);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 100);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 102);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 103);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 105);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 107);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (3, 97);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (3, 99);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (3, 100);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (3, 101);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (3, 104);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (3, 106);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (3, 107);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 108);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 108);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (3, 108);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (5, 82);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (5, 83);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (5, 84);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (5, 85);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 109);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 109);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 110);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 111);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 112);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 113);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 114);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 115);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 110);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 111);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 112);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 113);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 114);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 115);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 116);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 116);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 117);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 118);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 117);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 118);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (3, 117);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (3, 118);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 119);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 119);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (5, 86);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (5, 87);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (5, 88);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 120);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 120);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (3, 120);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 121);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (3, 121);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (1, 122);
INSERT INTO public.rol_permisos (rol_id, permiso_id) VALUES (2, 122);


--
-- Data for Name: usuarios; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.usuarios (id, email, password_hash, nombre_completo, activo, creado, creado_por, modificado, modificado_por, rol, pin_hash, apellidos, telefono, ultimo_acceso) VALUES ('00000000-0000-0000-0000-000000000001', 'sistema@mercury.internal', '$2b$12$1.UyHXPmALkBSPqgtfWzcunfWNDSfZpaRQiNC8fiCPy2VyNiEu6w6', 'Sistema (comandas automáticas)', true, '2026-10-03 02:34:51.238575+00', NULL, '2026-10-03 02:34:51.238575+00', NULL, 1, NULL, NULL, NULL, NULL);


--
-- Data for Name: turnos; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.turnos (id, nombre, hora_inicio, hora_fin, creado, creado_por, modificado, modificado_por, activo, dias) VALUES ('fb849920-786f-4ce0-bbda-908137e2d973', 'Turno Matutino', '08:00:00', '16:00:00', '2026-10-03 02:34:48.79116+00', NULL, NULL, NULL, true, NULL);
INSERT INTO public.turnos (id, nombre, hora_inicio, hora_fin, creado, creado_por, modificado, modificado_por, activo, dias) VALUES ('8fa9404e-421f-47e9-baf8-2d371dc5d920', 'Turno Vespertino', '16:00:00', '00:00:00', '2026-10-03 02:34:48.79116+00', NULL, NULL, NULL, true, NULL);
INSERT INTO public.turnos (id, nombre, hora_inicio, hora_fin, creado, creado_por, modificado, modificado_por, activo, dias) VALUES ('4e080523-bed4-4330-95d2-8dac421686d6', 'Turno Nocturno', '00:00:00', '08:00:00', '2026-10-03 02:34:48.79116+00', NULL, NULL, NULL, true, NULL);


--
-- Data for Name: unidades_medida; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.unidades_medida (id, codigo, nombre, tipo, factor_a_base, activo) VALUES ('57a25a9c-f0e4-452d-8501-9aab6a6ed557', 'g', 'Gramo', 'masa', 1.000000, true);
INSERT INTO public.unidades_medida (id, codigo, nombre, tipo, factor_a_base, activo) VALUES ('1445fd90-e0e5-49ae-b2dc-1de51885dea7', 'kg', 'Kilogramo', 'masa', 1000.000000, true);
INSERT INTO public.unidades_medida (id, codigo, nombre, tipo, factor_a_base, activo) VALUES ('228e3f2f-bd9e-47dd-83cb-bbc5d72aedf9', 'ml', 'Mililitro', 'volumen', 1.000000, true);
INSERT INTO public.unidades_medida (id, codigo, nombre, tipo, factor_a_base, activo) VALUES ('562d35f8-5785-462c-9ab6-31a8b0d97280', 'l', 'Litro', 'volumen', 1000.000000, true);
INSERT INTO public.unidades_medida (id, codigo, nombre, tipo, factor_a_base, activo) VALUES ('1ea9e189-a74a-4b40-9969-086787c378bd', 'pza', 'Pieza', 'pieza', 1.000000, true);


--
-- Name: permisos_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.permisos_id_seq', 122, true);


--
-- Name: roles_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.roles_id_seq', 5, true);


--
-- PostgreSQL database dump complete
--


