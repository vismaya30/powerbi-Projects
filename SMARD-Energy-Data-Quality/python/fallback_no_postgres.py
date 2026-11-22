import os
import sys

import pandas as pd

from load_smard import DATA_DIR, LOAD_COLUMN, PRICE_COLUMN, REGIONS, find_column, read_smard_csv, to_number

OUT_DIR = "csv_for_powerbi"


def read_all():
    parts = []
    for region in REGIONS:
        path = os.path.join(DATA_DIR, f"load_{region}.csv")
        if os.path.exists(path):
            df = read_smard_csv(path)
            parts.append(pd.DataFrame({"dataset": "load", "ts": df.ts, "region": region,
                                       "value": to_number(df[find_column(df, LOAD_COLUMN, path)])}))
    path = os.path.join(DATA_DIR, "prices.csv")
    df = read_smard_csv(path)
    for region in REGIONS:
        parts.append(pd.DataFrame({"dataset": "price", "ts": df.ts, "region": region,
                                   "value": to_number(df[find_column(df, PRICE_COLUMN[region], path)])}))
    return pd.concat(parts, ignore_index=True)


def inject_test_errors(v):
    ts = v.ts
    is_load, is_price = v.dataset == "load", v.dataset == "price"

    v = v[~(is_load & (v.region == "AT") & (ts >= "2024-01-10 10:00") & (ts < "2024-01-10 15:00"))]

    dup = v[(v.dataset == "load") & (v.region == "LU") & (v.ts >= "2024-02-15") & (v.ts < "2024-02-16")]
    v = pd.concat([v, dup], ignore_index=True)

    m = (v.dataset == "load") & (v.region == "DE") & (v.ts == "2024-03-05 12:00")
    v.loc[m, "value"] = -v.loc[m, "value"]

    m = (v.dataset == "price") & (v.region == "AT") & (v.ts >= "2024-06-20") & (v.ts < "2024-06-21")
    v.loc[m, "value"] = None

    m = (v.dataset == "price") & (v.region == "DE") & (v.ts == "2024-09-12 18:00")
    v.loc[m, "value"] = 2500
    return v


def expected_hours(v):
    rows = []
    for (dataset, region), g in v.groupby(["dataset", "region"]):
        hours = pd.date_range(g.ts.min(), g.ts.max(), freq="h")
        rows.append(pd.DataFrame({"dataset": dataset, "region": region, "ts": hours}))
    return pd.concat(rows, ignore_index=True)


def run_checks(v):
    errors = []

    def add(df, check, severity, rank, details, value=None):
        if df.empty:
            return
        out = df[["dataset", "ts", "region"]].copy()
        out["check_type"], out["severity"], out["severity_rank"] = check, severity, rank
        out["value"] = value if value is not None else None
        out["details"] = details
        errors.append(out)

    exp = expected_hours(v)
    merged = exp.merge(v[["dataset", "region", "ts"]].drop_duplicates(), how="left", indicator=True)
    add(merged[merged._merge == "left_only"], "Missing hour", "High", 3, "No row for this hour")

    counts = v.groupby(["dataset", "ts", "region"]).size().reset_index(name="n")
    dups = counts[counts.n > 1]
    add(dups, "Duplicate hour", "Medium", 2, dups.n.astype(str) + " rows for the same hour", dups.n)

    add(v[v.value.isna()], "Empty value", "Medium", 2, "Row exists but the value is empty")

    neg_load = v[(v.value < 0) & (v.dataset == "load")]
    neg_price = v[(v.value < 0) & (v.dataset == "price")]
    add(neg_load, "Negative value", "High", 3, "Load can never be negative", neg_load.value)
    add(neg_price, "Negative value", "Low", 1, "Negative price: real market event, worth a look", neg_price.value)

    p = v[v.dataset == "price"].copy()
    p["month"] = p.ts.dt.to_period("M")
    stats = p.groupby(["region", "month"]).value.agg(mu="mean", sd="std").reset_index()
    p = p.merge(stats, on=["region", "month"])
    dist = (p.value - p.mu).abs()
    for sev, rank, mask in [("Medium", 2, (dist > 3 * p.sd) & (dist <= 5 * p.sd)), ("High", 3, dist > 5 * p.sd)]:
        sp = p[mask]
        add(sp, "Price spike", sev, rank, "Monthly average is " + sp.mu.round(1).astype(str) + " EUR/MWh", sp.value)

    log = pd.concat(errors, ignore_index=True)
    log.insert(0, "error_id", range(1, len(log) + 1))
    log["day"] = log.ts.dt.date
    return log


def completeness(v):
    exp = expected_hours(v)
    present = v[v.value.notna()][["dataset", "region", "ts"]].drop_duplicates().assign(has=1)
    m = exp.merge(present, how="left")
    m["day"] = m.ts.dt.date
    return (m.groupby(["dataset", "region", "day"])
             .agg(expected_hours=("ts", "size"), present_hours=("has", "sum")).reset_index()
             .astype({"present_hours": int}))


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    v = read_all()
    if "--inject" in sys.argv:
        v = inject_test_errors(v)
        print("Test errors injected.")
    log = run_checks(v)
    comp = completeness(v)

    v.assign(day=v.ts.dt.date).to_csv(f"{OUT_DIR}/smard_values.csv", index=False)
    log.to_csv(f"{OUT_DIR}/error_log.csv", index=False)
    comp.to_csv(f"{OUT_DIR}/completeness.csv", index=False)

    print(f"Rows checked: {len(v):,}   Errors found: {len(log):,}")
    summary = log.groupby(["check_type", "severity", "severity_rank"]).size().reset_index(name="errors")
    print(summary.sort_values(["check_type", "severity_rank"]).drop(columns="severity_rank").to_string(index=False))
    pct = comp.present_hours.sum() / comp.expected_hours.sum()
    print(f"% complete hours: {pct:.2%}")
    print(f"Wrote {OUT_DIR}/smard_values.csv, error_log.csv, completeness.csv")


if __name__ == "__main__":
    main()
