CREATE TABLE ocpi_partners (
    id UUID PRIMARY KEY,
    country_code CHAR(2) NOT NULL,
    party_id CHAR(3) NOT NULL,
    role VARCHAR(10) NOT NULL, -- EMSP or CPO
    base_url TEXT NOT NULL,
    token TEXT NOT NULL,
    version VARCHAR(10) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT now(),

    UNIQUE (country_code, party_id, role)
);