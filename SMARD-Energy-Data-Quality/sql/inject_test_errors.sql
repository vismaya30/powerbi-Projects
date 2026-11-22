DELETE FROM load_hourly
WHERE region = 'AT' AND ts >= '2024-01-10 10:00' AND ts < '2024-01-10 15:00';

INSERT INTO load_hourly (ts, region, load_mwh)
SELECT ts, region, load_mwh FROM load_hourly
WHERE region = 'LU' AND ts >= '2024-02-15 00:00' AND ts < '2024-02-16 00:00';

UPDATE load_hourly SET load_mwh = -load_mwh
WHERE region = 'DE' AND ts = '2024-03-05 12:00';

UPDATE price_hourly SET price_eur_mwh = NULL
WHERE region = 'AT' AND ts >= '2024-06-20 00:00' AND ts < '2024-06-21 00:00';

UPDATE price_hourly SET price_eur_mwh = 2500
WHERE region = 'DE' AND ts = '2024-09-12 18:00';
