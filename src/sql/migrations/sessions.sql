CREATE TABLE IF NOT EXISTS public.ocpi_sessions
(
    id text COLLATE pg_catalog."default" NOT NULL,
    start_date_time timestamp with time zone NOT NULL,
    end_date_time timestamp with time zone,
    auth_id text COLLATE pg_catalog."default" NOT NULL,
    auth_method character varying(20) COLLATE pg_catalog."default" NOT NULL,
    location_id text COLLATE pg_catalog."default" NOT NULL,
    evse_uid text COLLATE pg_catalog."default" NOT NULL,
    connector_id text COLLATE pg_catalog."default" NOT NULL,
    currency character varying(3) COLLATE pg_catalog."default" NOT NULL,
    status character varying(20) COLLATE pg_catalog."default" NOT NULL,
    created_at timestamp with time zone NOT NULL,
    session_id text COLLATE pg_catalog."default",
    total_price numeric(12,4),
    "kWh" numeric(10,3),
    party_id text COLLATE pg_catalog."default",
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
-- Index: public.idx_sessions_start_date
CREATE INDEX IF NOT EXISTS idx_sessions_start_date
    ON public.ocpi_sessions USING btree
    (start_date_time ASC NULLS LAST)
    TABLESPACE pg_default;
-- Index: public.idx_sessions_status
CREATE INDEX IF NOT EXISTS idx_sessions_status
    ON public.ocpi_sessions USING btree
    (status COLLATE pg_catalog."default" ASC NULLS LAST)
    TABLESPACE pg_default;