SELECT id,
       token_uid,
       location_id,
       evse_uid,
       connector_id,
       result,
       reason,
       requested_at
FROM public.ocpi_token_authorizations
WHERE result = 'ALLOWED'
LIMIT 1000;