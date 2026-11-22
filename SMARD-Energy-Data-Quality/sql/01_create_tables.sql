DROP TABLE IF EXISTS load_hourly  CASCADE;
DROP TABLE IF EXISTS price_hourly CASCADE;

CREATE TABLE load_hourly (
    ts        timestamp   NOT NULL,
    region    varchar(5)  NOT NULL,
    load_mwh  numeric,
    day       date GENERATED ALWAYS AS (ts::date) STORED
);

CREATE TABLE price_hourly (
    ts             timestamp  NOT NULL,
    region         varchar(5) NOT NULL,
    price_eur_mwh  numeric,
    day            date GENERATED ALWAYS AS (ts::date) STORED
);
