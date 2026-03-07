CREATE TABLE IF NOT EXISTS public.ocpi_tariffs
(
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    tariff_id text COLLATE pg_catalog."default" NOT NULL,
    currency character varying(3) COLLATE pg_catalog."default" NOT NULL,
    CONSTRAINT ocpi_tariffs_pkey PRIMARY KEY (id),
    CONSTRAINT uq_ocpi_tariffs_tariff_id UNIQUE (tariff_id)
)

TABLESPACE pg_default;

ALTER TABLE public.ocpi_tariffs
    OWNER to postgres;

-- Index: public.idx_ocpi_tariffs_tariff_id
CREATE INDEX IF NOT EXISTS idx_ocpi_tariffs_tariff_id
    ON public.ocpi_tariffs USING btree
    (tariff_id COLLATE pg_catalog."default" ASC NULLS LAST)
    TABLESPACE pg_default;