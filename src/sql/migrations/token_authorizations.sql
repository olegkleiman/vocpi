CREATE TABLE ocpi_token_authorizations (
    id UUID PRIMARY KEY,
    token_uid TEXT NOT NULL,

    location_id TEXT,
    evse_uid TEXT,
    connector_id TEXT,

    result VARCHAR(20) NOT NULL, -- ACCEPTED / REJECTED / BLOCKED
    reason TEXT,

    requested_at TIMESTAMP NOT NULL DEFAULT now(),

    CONSTRAINT fk_auth_token
      FOREIGN KEY (token_uid)
      REFERENCES ocpi_tokens (uid)
);