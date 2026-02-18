CREATE TABLE IF NOT EXISTS public.ocpi_evses
(
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    evse_id text COLLATE pg_catalog."default" NOT NULL,
    location_id uuid NOT NULL,
    description text COLLATE pg_catalog."default",
    CONSTRAINT ocpi_evses_pkey PRIMARY KEY (id),
    CONSTRAINT fk_evses_locations FOREIGN KEY (location_id)
        REFERENCES public.ocpi_locations (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
)

TABLESPACE pg_default;

ALTER TABLE public.ocpi_evses
    OWNER to postgres;
