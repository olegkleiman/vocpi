CREATE TABLE IF NOT EXISTS public.ocpi_sessions_updates
(
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    session_id text COLLATE pg_catalog."default",
    total_cost numeric(20,4),
    kwh numeric(10,3),
    updated_at timestamp with time zone,
    status text COLLATE pg_catalog."default",
    CONSTRAINT ocpi_sessions_updates_pkey PRIMARY KEY (id)
)

TABLESPACE pg_default;

ALTER TABLE public.ocpi_sessions_updates
    OWNER to postgres;
