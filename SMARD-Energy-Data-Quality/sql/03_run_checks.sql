TRUNCATE error_log RESTART IDENTITY;

WITH bounds AS (
    SELECT dataset, region, min(ts) AS t0, max(ts) AS t1
    FROM v_values GROUP BY dataset, region
), expected AS (
    SELECT b.dataset, b.region, g.ts
    FROM bounds b
    CROSS JOIN LATERAL generate_series(b.t0, b.t1, interval '1 hour') AS g(ts)
)
INSERT INTO error_log (dataset, ts, region, check_type, severity, severity_rank, details)
SELECT e.dataset, e.ts, e.region, 'Missing hour', 'High', 3, 'No row for this hour'
FROM expected e
LEFT JOIN v_values v
       ON v.dataset = e.dataset AND v.region = e.region AND v.ts = e.ts
WHERE v.ts IS NULL;

INSERT INTO error_log (dataset, ts, region, check_type, severity, severity_rank, value, details)
SELECT dataset, ts, region, 'Duplicate hour', 'Medium', 2, count(*),
       count(*) || ' rows for the same hour'
FROM v_values
GROUP BY dataset, ts, region
HAVING count(*) > 1;

INSERT INTO error_log (dataset, ts, region, check_type, severity, severity_rank, details)
SELECT dataset, ts, region, 'Empty value', 'Medium', 2, 'Row exists but the value is empty'
FROM v_values
WHERE value IS NULL;

INSERT INTO error_log (dataset, ts, region, check_type, severity, severity_rank, value, details)
SELECT dataset, ts, region, 'Negative value',
       CASE WHEN dataset = 'load' THEN 'High' ELSE 'Low' END,
       CASE WHEN dataset = 'load' THEN 3 ELSE 1 END,
       value,
       CASE WHEN dataset = 'load' THEN 'Load can never be negative'
            ELSE 'Negative price: real market event, worth a look' END
FROM v_values
WHERE value < 0;

WITH stats AS (
    SELECT region, date_trunc('month', ts) AS month,
           avg(value) AS mu, stddev(value) AS sd
    FROM v_values
    WHERE dataset = 'price'
    GROUP BY region, date_trunc('month', ts)
)
INSERT INTO error_log (dataset, ts, region, check_type, severity, severity_rank, value, details)
SELECT 'price', v.ts, v.region, 'Price spike',
       CASE WHEN abs(v.value - s.mu) > 5 * s.sd THEN 'High' ELSE 'Medium' END,
       CASE WHEN abs(v.value - s.mu) > 5 * s.sd THEN 3 ELSE 2 END,
       v.value,
       'Monthly average is ' || round(s.mu, 1) || ' EUR/MWh'
FROM v_values v
JOIN stats s ON s.region = v.region AND s.month = date_trunc('month', v.ts)
WHERE v.dataset = 'price'
  AND abs(v.value - s.mu) > 3 * s.sd;

SELECT check_type, severity, count(*) AS errors
FROM error_log
GROUP BY check_type, severity, severity_rank
ORDER BY check_type, severity_rank;
