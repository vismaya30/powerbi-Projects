DROP TABLE IF EXISTS error_log CASCADE;

CREATE TABLE error_log (
    error_id       serial PRIMARY KEY,
    detected_at    timestamp DEFAULT now(),
    dataset        text,
    ts             timestamp,
    region         varchar(5),
    check_type     text,
    severity       text,
    severity_rank  int,
    value          numeric,
    details        text,
    day            date GENERATED ALWAYS AS (ts::date) STORED
);

CREATE OR REPLACE VIEW v_values AS
SELECT 'load'  AS dataset, ts, region, load_mwh      AS value FROM load_hourly
UNION ALL
SELECT 'price' AS dataset, ts, region, price_eur_mwh AS value FROM price_hourly;
