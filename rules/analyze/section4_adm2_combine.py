"""
Section 4 (revision) - combine the per-country admin-unit tables into one wide table.

One row per (ISO3, admin unit). Scenario columns are suffixed _base and _fp
(e.g. risk_Q1_base, loss_fp). Population columns come from the baseline rows
(they are identical across scenarios). The flood protection costs at the same admin
level are joined on shapeID, with their column names prefixed:
    fp_min_adaptation_cost, fp_adaptation_cost, ..., fp_river_len_km, fp_protected
                                          ($ millions, from prepare_admin_flood_protection.py)

Cost GeoPackages are read with sqlite3 so geometry is not parsed.
"""

import logging
import sqlite3

import pandas as pd

if __name__ == "__main__":

    try:
        unit_paths = list(snakemake.input["units"])
        check_paths = list(snakemake.input["checks"])
        fp_paths = list(snakemake.input["fp_costs"])
        iso_codes = list(snakemake.params["iso_codes"])
        units_out = snakemake.output["units"]
        checks_out = snakemake.output["checks"]
    except NameError:
        raise ValueError("Must be run via snakemake.")

logging.basicConfig(format="%(asctime)s %(process)d %(filename)s %(message)s", level=logging.INFO)

COST_COLS = {
    "fp": ["river_len_km", "n_segments", "flopros_lw", "doublings_lw", "protected",
           "adaptation_cost", "adj_adaptation_cost", "min_adaptation_cost", "max_adaptation_cost"],
}


def read_gpkg_table(path):
    """Read the attribute table of a single-layer GeoPackage without geometry."""
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        table = con.execute(
            "SELECT table_name FROM gpkg_contents WHERE data_type = 'features'"
        ).fetchone()[0]
        df = pd.read_sql_query(f'SELECT * FROM "{table}"', con)
    finally:
        con.close()
    geom_cols = [c for c in df.columns if c.lower() in ("geom", "geometry")]
    return df.drop(columns=geom_cols)


frames = []
for iso, u_path, fp_path in zip(iso_codes, unit_paths, fp_paths):
    logging.info(f"Combining {iso}")
    long = pd.read_csv(u_path)
    long["shapeID"] = long["shapeID"].astype(str)
    pop_cols = [c for c in long.columns if c.startswith("pop")]
    id_cols = ["shapeID", "shapeName", "admin_level", "scenario"]
    metric_cols = [c for c in long.columns if c not in id_cols + pop_cols]

    base = long[long["scenario"] == "base"][["shapeID", "shapeName", "admin_level"] + pop_cols]
    wide = long.pivot(index="shapeID", columns="scenario", values=metric_cols)
    wide.columns = [f"{metric}_{scen}" for metric, scen in wide.columns]
    df = base.merge(wide.reset_index(), on="shapeID", how="left")

    for prefix, path in (("fp", fp_path),):
        costs = read_gpkg_table(path)
        costs["shapeID"] = costs["shapeID"].astype(str)
        keep = [c for c in COST_COLS[prefix] if c in costs.columns]
        costs = costs[["shapeID"] + keep].groupby("shapeID", as_index=False).sum(min_count=1)
        costs = costs.rename(columns={c: f"{prefix}_{c}" for c in keep})
        df = df.merge(costs, on="shapeID", how="left")

    df.insert(0, "ISO3", iso)
    frames.append(df)

out = pd.concat(frames, ignore_index=True)
out.to_csv(units_out, index=False)
logging.info(f"Wrote {len(out)} units for {len(frames)} countries.")

checks = pd.concat([pd.read_csv(p) for p in check_paths], ignore_index=True)
checks.to_csv(checks_out, index=False)
logging.info("Done.")
