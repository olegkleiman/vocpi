DROP TABLE IF EXISTS ocpi_sessions CASCADE;

CREATE TABLE ocpi_sessions (
    id VARCHAR PRIMARY KEY,
    start_date_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_date_time TIMESTAMP WITH TIME ZONE,
    kwh FLOAT NOT NULL DEFAULT 0.0,
    auth_id VARCHAR NOT NULL,
    auth_method VARCHAR(20) NOT NULL,
    location_id VARCHAR NOT NULL,
    evse_uid VARCHAR NOT NULL,
    connector_id VARCHAR NOT NULL,
    currency VARCHAR(3) NOT NULL,
    status VARCHAR(20) NOT NULL,
    last_updated TIMESTAMP WITH TIME ZONE NOT NULL,
    token_uid VARCHAR REFERENCES ocpi_tokens(VARCHAR),
    partner_id UUID NOT NULL REFERENCES ocpi_partners(id)
);

CREATE INDEX IF NOT EXISTS idx_sessions_id ON ocpi_sessions(id);
CREATE INDEX idx_sessions_token_uid ON ocpi_sessions(token_uid);
CREATE INDEX idx_sessions_partner_id ON ocpi_sessions(partner_id);
CREATE INDEX idx_sessions_status ON ocpi_sessions(status);
CREATE INDEX idx_sessions_start_date ON ocpi_sessions(start_date_time);
