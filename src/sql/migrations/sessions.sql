CREATE TABLE IF NOT EXISTS public.ocpi_sessions
(
    id text COLLATE pg_catalog."default" NOT NULL,
    auth_id text COLLATE pg_catalog."default" NOT NULL,
    auth_method character varying(20) COLLATE pg_catalog."default" NOT NULL,
    location_id text COLLATE pg_catalog."default" NOT NULL,
    evse_uid text COLLATE pg_catalog."default" NOT NULL,
    connector_id text COLLATE pg_catalog."default" NOT NULL,
    currency character varying(3) COLLATE pg_catalog."default" NOT NULL,
    status character varying(20) COLLATE pg_catalog."default" NOT NULL,
    session_id text COLLATE pg_catalog."default",
    created_at timestamp with time zone,
    CONSTRAINT ocpi_sessions_pkey PRIMARY KEY (id)
)

TABLESPACE pg_default;

ALTER TABLE public.ocpi_sessions
    OWNER to postgres;

-- Index: public.idx_sessions_id
CREATE INDEX IF NOT EXISTS idx_sessions_id
    ON public.ocpi_sessions USING btree
    (id COLLATE pg_catalog."default" ASC NULLS LAST)
    TABLESPACE pg_default;
-- Index: public.idx_sessions_status
CREATE INDEX IF NOT EXISTS idx_sessions_status
    ON public.ocpi_sessions USING btree
    (status COLLATE pg_catalog."default" ASC NULLS LAST)
    TABLESPACE pg_default;