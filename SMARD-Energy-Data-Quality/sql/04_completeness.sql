CREATE OR REPLACE VIEW v_completeness AS
WITH bounds AS (
    SELECT dataset, region, min(ts) AS t0, max(ts) AS t1
    FROM v_values GROUP BY dataset, region
), expected AS (
    SELECT b.dataset, b.region, g.ts
    FROM bounds b
    CROSS JOIN LATERAL generate_series(b.t0, b.t1, interval '1 hour') AS g(ts)
), present AS (
    SELECT DISTINCT dataset, region, ts
    FROM v_values
    WHERE value IS NOT NULL
)
SELECT e.dataset,
       e.region,
       e.ts::date        AS day,
       count(*)          AS expected_hours,
       count(p.ts)       AS present_hours
FROM expected e
LEFT JOIN present p
       ON p.dataset = e.dataset AND p.region = e.region AND p.ts = e.ts
GROUP BY e.dataset, e.region, e.ts::date;
