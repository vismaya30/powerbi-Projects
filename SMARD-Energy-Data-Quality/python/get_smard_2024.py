import os
from datetime import datetime, timezone

import pandas as pd
import requests

BASE = "https://www.smard.de/app/chart_data"
YEAR = 2024
TZ = "Europe/Berlin"


def fetch(series_id, region):
    index = requests.get(f"{BASE}/{series_id}/{region}/index_hour.json", timeout=30).json()["timestamps"]
    start = int(datetime(YEAR - 1, 12, 24, tzinfo=timezone.utc).timestamp() * 1000)
    end = int(datetime(YEAR + 1, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
    rows = []
    for week in index:
        if start <= week < end:
            url = f"{BASE}/{series_id}/{region}/{series_id}_{region}_hour_{week}.json"
            rows += requests.get(url, timeout=30).json()["series"]
    s = pd.DataFrame(rows, columns=["ms", "value"]).drop_duplicates("ms")
    s.index = pd.to_datetime(s.ms, unit="ms", utc=True)
    return s.value


def to_local_rows(values):
    local = values.tz_convert(TZ)
    local = local[local.index.year == YEAR]
    out = pd.DataFrame({"von": local.index.strftime("%d.%m.%Y %H:%M"),
                        "bis": (local.index + pd.Timedelta(hours=1)).tz_convert(TZ).strftime("%d.%m.%Y %H:%M")})
    return out.reset_index(drop=True), local.reset_index(drop=True)


def german(x):
    if pd.isna(x):
        return "-"
    return f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def write(path, columns):
    frame = None
    for header, series in columns.items():
        times, vals = to_local_rows(series)
        if frame is None:
            frame = times.rename(columns={"von": "Datum von", "bis": "Datum bis"})
        frame[header] = vals.map(german).values
    frame.to_csv(path, sep=";", index=False, encoding="utf-8")
    print(f"wrote {path}: {len(frame)} rows")


def main():
    os.makedirs("data", exist_ok=True)
    print("Downloading 2024 prices ...")
    write("data/prices.csv", {
        "Deutschland/Luxemburg [€/MWh] Originalauflösungen": fetch(4169, "DE-LU"),
        "Österreich [€/MWh] Originalauflösungen": fetch(4170, "AT"),
    })
    for region in ["DE", "AT", "LU"]:
        print(f"Downloading 2024 load {region} ...")
        write(f"data/load_{region}.csv", {
            "Gesamt (Netzlast) [MWh] Originalauflösungen": fetch(410, region),
        })


if __name__ == "__main__":
    main()
