CREATE TABLE IF NOT EXISTS public.ocpi_cdrs
(
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    session_request_id text COLLATE pg_catalog."default",
    cdr_id text COLLATE pg_catalog."default",
    cdr_json jsonb,
    session_id text COLLATE pg_catalog."default",
    CONSTRAINT ocpi_cdrs_pkey PRIMARY KEY (id)
)

TABLESPACE pg_default;

ALTER TABLE public.ocpi_cdrs
    OWNER to postgres;
