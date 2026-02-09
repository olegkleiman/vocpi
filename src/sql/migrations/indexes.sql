CREATE INDEX idx_tokens_partner
ON ocpi_partners(country_code, party_id);

CREATE INDEX idx_tokens_valid
ON ocpi_tokens (valid);

CREATE INDEX idx_auth_token
ON ocpi_token_authorizations (token_uid);