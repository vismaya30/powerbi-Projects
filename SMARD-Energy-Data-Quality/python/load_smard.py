import os
import sys

import pandas as pd
from sqlalchemy import create_engine, text

DB_URL = "postgresql+psycopg2://postgres:YOUR_PASSWORD@localhost:5432/smard"
DB_URL = os.environ.get("SMARD_DB_URL", DB_URL)

DATA_DIR = "data"
REGIONS = ["DE", "AT", "LU"]

PRICE_COLUMN = {"DE": "Deutschland/Luxemburg", "LU": "Deutschland/Luxemburg", "AT": "Österreich"}
LOAD_COLUMN = "Netzlast"


def read_smard_csv(path):
    df = pd.read_csv(path, sep=";", decimal=",", thousands=".", na_values=["-"], encoding="utf-8")
    ts = pd.to_datetime(df["Datum von"], format="%d.%m.%Y %H:%M", errors="coerce")
    if ts.isna().all():
        ts = pd.to_datetime(df["Datum von"], errors="coerce")
    if ts.isna().any():
        sys.exit(f"Could not read {ts.isna().sum()} dates in {path}. Example: {df['Datum von'].iloc[0]!r}")
    df["ts"] = ts
    return df


def find_column(df, part, path):
    matches = [c for c in df.columns if part.lower() in c.lower()]
    if not matches:
        sys.exit(f"No column contains '{part}' in {path}.\nThe real column names are:\n  "
                 + "\n  ".join(df.columns) + "\nChange the text in load_smard.py to match.")
    return matches[0]


def to_number(series):
    if series.dtype == object:
        series = series.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    return pd.to_numeric(series, errors="coerce")


def main():
    load_parts = []
    for region in REGIONS:
        path = os.path.join(DATA_DIR, f"load_{region}.csv")
        if not os.path.exists(path):
            print(f"!! {path} not found - skipping {region} load")
            continue
        df = read_smard_csv(path)
        col = find_column(df, LOAD_COLUMN, path)
        load_parts.append(pd.DataFrame({"ts": df.ts, "region": region, "load_mwh": to_number(df[col])}))
    load = pd.concat(load_parts, ignore_index=True)

    path = os.path.join(DATA_DIR, "prices.csv")
    df = read_smard_csv(path)
    price_parts = []
    for region in REGIONS:
        col = find_column(df, PRICE_COLUMN[region], path)
        price_parts.append(pd.DataFrame({"ts": df.ts, "region": region, "price_eur_mwh": to_number(df[col])}))
    prices = pd.concat(price_parts, ignore_index=True)

    engine = create_engine(DB_URL)
    if "YOUR_PASSWORD" in DB_URL:
        sys.exit("Please put your PostgreSQL password into DB_URL at the top of load_smard.py.")
    from sqlalchemy import inspect
    if not inspect(engine).has_table("load_hourly"):
        sys.exit("Table load_hourly does not exist. Run sql/01_create_tables.sql in pgAdmin first.")
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE load_hourly, price_hourly"))
        load.to_sql("load_hourly", conn, if_exists="append", index=False, chunksize=5000, method="multi")
        prices.to_sql("price_hourly", conn, if_exists="append", index=False, chunksize=5000, method="multi")
    print(f"Loaded {len(load):,} load rows and {len(prices):,} price rows.")


if __name__ == "__main__":
    main()
