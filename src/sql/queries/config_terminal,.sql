SELECT serial_number, 

        l.description as "location description", 

       l.address as "location address", 

       l.location_id, 

       e.description as "evse description", 

       e.evse_id 

FROM public.ocpi_terminals t 

JOIN ocpi_locations l 

ON t.location_id = l.id 

JOIN ocpi_evses e 

ON t.evse_id = e.id 

where t.serial_number = '111-222-333'; 