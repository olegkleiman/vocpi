CREATE TABLE IF NOT EXISTS public.ocpi_terminals
(
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    serial_number text COLLATE pg_catalog."default",
    location_id uuid,
    evse_id uuid,
    terminal_id text COLLATE pg_catalog."default",
    user_name text COLLATE pg_catalog."default",
    user_password text COLLATE pg_catalog."default",
    description text COLLATE pg_catalog."default",
    CONSTRAINT ocpi_terminals_pkey PRIMARY KEY (id),
    CONSTRAINT fk_terminal_evse FOREIGN KEY (evse_id)
        REFERENCES public.ocpi_evses (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT fk_terminal_location FOREIGN KEY (location_id)
        REFERENCES public.ocpi_locations (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
)

TABLESPACE pg_default;

ALTER TABLE public.ocpi_terminals
    OWNER to postgres;
