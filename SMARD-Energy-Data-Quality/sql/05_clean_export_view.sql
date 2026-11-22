CREATE OR REPLACE VIEW v_load_clean AS
SELECT DISTINCT ON (region, ts) ts, region, load_mwh
FROM load_hourly
WHERE load_mwh IS NOT NULL AND load_mwh >= 0
ORDER BY region, ts;
