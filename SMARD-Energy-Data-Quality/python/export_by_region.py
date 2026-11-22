import os
import sys

import pandas as pd
from openpyxl.styles import Font
from sqlalchemy import create_engine, text


DB_URL = "postgresql+psycopg2://postgres:YOUR_PASSWORD@localhost:5432/smard"
DB_URL = os.environ.get("SMARD_DB_URL", DB_URL)

OUT_DIR = "export"


def main():
    if "YOUR_PASSWORD" in DB_URL:
        sys.exit("Please put your PostgreSQL password into DB_URL at the top of export_by_region.py.")
    engine = create_engine(DB_URL)
    os.makedirs(OUT_DIR, exist_ok=True)
    with engine.connect() as conn:
        regions = [r[0] for r in conn.execute(text("SELECT DISTINCT region FROM load_hourly ORDER BY region"))]
        for region in regions:
            clean = pd.read_sql(text("SELECT ts, region, load_mwh FROM v_load_clean "
                                     "WHERE region = :r ORDER BY ts"), conn, params={"r": region})
            errors = pd.read_sql(text("SELECT ts, dataset, check_type, severity, value, details "
                                      "FROM error_log WHERE region = :r ORDER BY severity_rank DESC, ts"),
                                 conn, params={"r": region})
            path = os.path.join(OUT_DIR, f"smard_{region}.xlsx")
            with pd.ExcelWriter(path, engine="openpyxl") as xw:
                clean.to_excel(xw, sheet_name="clean_load", index=False)
                errors.to_excel(xw, sheet_name="errors", index=False)
                for ws in xw.book.worksheets:
                    ws.freeze_panes = "A2"
                    ws.auto_filter.ref = ws.dimensions
                    for cell in ws[1]:
                        cell.font = Font(bold=True)
                    for col in "ABCDEF":
                        ws.column_dimensions[col].width = 20
            print(f"{path}: {len(clean):,} clean hours, {len(errors):,} errors")


if __name__ == "__main__":
    main()
