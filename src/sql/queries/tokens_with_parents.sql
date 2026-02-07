SELECT * 
FROM public.ocpi_tokens t
JOIN ocpi_partners p
ON p.id = t.partner_id
WHERE t.uid = 'c3c3c6a6-5f1a-4f6d-bc8b-6b6f4b1e8d91'
	AND p.country_code = 'IL'
	AND p.role = 'emsp'
	AND p.party_id = 'ABC'
    AND t.type = 'RFID'
ORDER BY uid ASC 
