CREATE TABLE ocpi_tokens (
    uid TEXT PRIMARY KEY,

    partner_id UUID NOT NULL,

    type VARCHAR(20) NOT NULL,        -- RFID, APP_USER, OTHER
    contract_id TEXT NOT NULL,
    issuer TEXT NOT NULL,

    valid BOOLEAN NOT NULL,
    whitelist VARCHAR(20) NOT NULL,   -- ALWAYS, ALLOWED, NEVER

    language CHAR(2),
    visual_number TEXT,

    last_updated TIMESTAMP NOT NULL,

    CONSTRAINT fk_token_partner
      FOREIGN KEY (partner_id)
      REFERENCES ocpi_partners (id)
);