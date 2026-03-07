CREATE TABLE IF NOT EXISTS public.ocpi_tariff_elements
(
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    tariff_id text COLLATE pg_catalog."default" NOT NULL,
    restrictions jsonb,
    price_components jsonb,
    CONSTRAINT ocpi_tariff_elements_pkey PRIMARY KEY (id),
    CONSTRAINT fk_ocpi_tariffs_tariff_id FOREIGN KEY (tariff_id)
        REFERENCES public.ocpi_tariffs (tariff_id) MATCH SIMPLE
        ON UPDATE CASCADE
        ON DELETE CASCADE
)

TABLESPACE pg_default;

ALTER TABLE public.ocpi_tariff_elements
    OWNER to postgres;

-- Index: public.idx_ocpi_tariff_elements_tariff_id
CREATE INDEX IF NOT EXISTS idx_ocpi_tariff_elements_tariff_id
    ON public.ocpi_tariff_elements USING btree
    (tariff_id COLLATE pg_catalog."default" ASC NULLS LAST)
    TABLESPACE pg_default;