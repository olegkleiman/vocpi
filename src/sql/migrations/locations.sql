create table ocpi_locations (
    id UUID primary key DEFAULT gen_random_uuid(),
    -- foreign key column
    partner_id UUID NOT NULL,
    location_id text,
    description text,
    address text,

    -- Define the constraint
    CONSTRAINT fk_location_partner 
        FOREIGN KEY (partner_id)
        REFERENCES public.ocpi_partners (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
);