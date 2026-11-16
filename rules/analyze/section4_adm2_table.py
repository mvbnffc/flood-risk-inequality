"""
Section 4 (revision) - per admin unit, per scenario: population, people-weighted risk and
capital stock losses, with people grouped by NATIONAL wealth quintile.

This step only aggregates rasters to admin units. All targeting / prioritisation rules
(BCR, cost-effectiveness, equity weights, budgets) are applied afterwards in the notebook.

Scenarios: base (FLOPROS-protected baseline) and fp (every unit with a river protected to
RP100, prepare_admin_flood_protection.py).

Columns (one row per admin unit and scenario)
  pop, pop_Q1..pop_Q5     population in ranked cells (populated, land, valid social indicator
                          and valid people-risk in both scenarios), by NATIONAL wealth quintile
  pop_all                 all populated land cells (incl. cells without RWI)
  risk, risk_Q1..risk_Q5  people-weighted risk sum(pop * AAR) over ranked cells, the same
                          quantity as "Total Flood Risk" in inequality_metrics.py
  risk_rank               sum(pop * AAR * r), r = national fractional wealth rank
  loss_res, loss_nres, loss_infr, loss
                          capital stock losses (risk x capstock), as in capital_stock_losses.py

Because ranks are national and fixed across scenarios, every column adds up across units:
    national Q1 risk = sum over units of risk_Q1
    national CI (exact) = 2 * sum(risk_rank) / sum(risk) - 1
    national CI (from quintiles) ~ sum_q (2 R_q - 1) * risk_Qq / risk, R_q = 0.1, 0.3, ..., 0.9
The benefit of a measure in a unit is (base column - adapted column), so the national
quintile risk after adapting any subset of units S is base_Q - sum_{u in S} (base_Q,u - adapted_Q,u).

Ranks: cells are sorted by the social indicator; cells with identical values (RWI tiles are
~2.4 km, so ties are common) share the mid-point rank of their group. Quintiles use the same
cumulative-population rule as inequality_metrics.py.

The unit "_unassigned" collects cells inside the ADM0 boundary but outside every ADM1/ADM2
polygon, so unit totals add up to national totals.

The one-row checks file reports coverage, national CIs and totals (to reconcile with the
existing ADM0 outputs) and whether {ISO3}_ghs-pop.tif (used by the existing adapted-scenario
rules) is identical to {ISO3}_ghs-pop_2020.tif (used by the baseline rule and here throughout).
"""

import logging
import os
import time

import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.features import rasterize

if __name__ == "__main__":

    try:
        inp = snakemake.input
        admin_path: str = inp["admin_areas"]
        social_path: str = inp["social_file"]
        pop_path: str = inp["pop_file"]
        mask_path: str = inp["mask_file"]
        units_out: str = snakemake.output["units"]
        checks_out: str = snakemake.output["checks"]
        admin_level: str = snakemake.wildcards.ADMIN_SLUG
        country: str = snakemake.wildcards.ISO3
        model: str = snakemake.wildcards.MODEL
        social_name: str = snakemake.wildcards.SOCIAL
    except NameError:
        raise ValueError("Must be run via snakemake.")

logging.basicConfig(format="%(asctime)s %(process)d %(filename)s %(message)s", level=logging.INFO)
t0 = time.time()

# Scenario -> (people/residential risk, non-residential risk, infrastructure risk),
# as in the summarize_*_capital_stock_losses rules in flood_risk.smk.
SCENARIOS = {
    "base": ("base_res", "base_nres", "base_infr"),
    "fp": ("fp_res", "fp_nres", "fp_infr"),
}
CAPSTOCK_KEYS = ("res_capstock", "nres_capstock", "infr_capstock")

logging.info(f"Section 4 admin-unit table: {country} {admin_level} {model} {social_name}")


def read_band(path, ref):
    """Read band 1 as float32 and check it is on the reference grid."""
    with rasterio.open(path) as src:
        if src.shape != ref["shape"]:
            raise ValueError(f"{path} has shape {src.shape}, expected {ref['shape']}")
        if not src.transform.almost_equals(ref["transform"]):
            raise ValueError(f"{path} is not on the population grid")
        return src.read(1, out_dtype="float32")


logging.info("Reading population (reference grid).")
with rasterio.open(pop_path) as src:
    ref = {"shape": src.shape, "transform": src.transform, "crs": src.crs}
    pop = src.read(1, out_dtype="float32")
populated = np.isfinite(pop) & (pop > 0)

logging.info("Reading admin boundaries.")
adm0 = gpd.read_file(admin_path, layer="ADM0")
units = gpd.read_file(admin_path, layer=admin_level)
units = units[["shapeID", "shapeName", "geometry"]].copy()
units = units.dropna(subset=["geometry"])
units = units[~units.geometry.is_empty].reset_index(drop=True)
if ref["crs"] is not None and adm0.crs is not None and adm0.crs != ref["crs"]:
    adm0 = adm0.to_crs(ref["crs"])
if ref["crs"] is not None and units.crs is not None and units.crs != ref["crs"]:
    units = units.to_crs(ref["crs"])
n_units = len(units)
logging.info(f"{n_units} {admin_level} units.")

in_country = rasterize(
    [(geom, 1) for geom in adm0.geometry if geom is not None and not geom.is_empty],
    out_shape=ref["shape"], transform=ref["transform"], fill=0, dtype="uint8",
).astype(bool)
unit_raster = rasterize(
    [(geom, i) for i, geom in enumerate(units.geometry)],
    out_shape=ref["shape"], transform=ref["transform"], fill=-1, dtype="int32",
)

logging.info("Reading water mask.")
water = read_band(mask_path, ref)
land = ~(water > 50)  # same hard-coded threshold as the existing scripts; NaN counts as land
del water

checks = {"ISO3": country, "admin_level": admin_level, "model": model, "social": social_name,
          "n_units": n_units}

logging.info("Checking {ISO3}_ghs-pop.tif against the population file used here.")
alt_pop_path = os.path.join(os.path.dirname(pop_path), f"{country}_ghs-pop.tif")
checks["pop_alt_file_exists"] = os.path.exists(alt_pop_path)
checks["pop_alt_identical"] = np.nan
checks["pop_alt_total_ratio"] = np.nan
if checks["pop_alt_file_exists"] and os.path.abspath(alt_pop_path) != os.path.abspath(pop_path):
    with rasterio.open(alt_pop_path) as src:
        if src.shape == ref["shape"]:
            alt = src.read(1, out_dtype="float32")
            m = in_country & land
            alt_total = alt[m & (alt > 0)].sum(dtype=np.float64)
            pop_total = pop[m & populated].sum(dtype=np.float64)
            checks["pop_alt_identical"] = bool(np.array_equal(alt, pop, equal_nan=True))
            checks["pop_alt_total_ratio"] = alt_total / pop_total if pop_total > 0 else np.nan
            del alt, m
        else:
            checks["pop_alt_identical"] = False

logging.info("Selecting candidate cells (in country, on land, populated or with capital stock).")
has_cap = np.zeros(ref["shape"], dtype=bool)
for key in CAPSTOCK_KEYS:
    arr = read_band(inp[key], ref)
    has_cap |= arr > 0
    del arr
candidate = in_country & land & (populated | has_cap)
del has_cap, in_country, land
idx = np.flatnonzero(candidate)
del candidate
logging.info(f"{idx.size} candidate cells.")

pop_c = pop.ravel()[idx]
populated_c = populated.ravel()[idx]
del pop, populated
unit_c = unit_raster.ravel()[idx]
del unit_raster

social = read_band(social_path, ref)
social[social == -999] = np.nan  # RWI no-data
social_c = social.ravel()[idx]
del social

logging.info("Reading risk and capital stock rasters.")
vec = {}
needed = sorted({k for keys in SCENARIOS.values() for k in keys} | set(CAPSTOCK_KEYS))
for key in needed:
    arr = read_band(inp[key], ref)
    vec[key] = arr.ravel()[idx]
    del arr
del idx

logging.info("Defining ranked cells and national wealth ranks.")
people_ok = populated_c & np.isfinite(social_c)
risk_ok = np.ones(people_ok.shape, dtype=bool)
for keys in SCENARIOS.values():
    risk_ok &= np.isfinite(vec[keys[0]])
ranked = people_ok & risk_ok
base_ok = people_ok & np.isfinite(vec["base_res"])

pop_all_total = pop_c[populated_c].sum(dtype=np.float64)
checks["pop_country"] = pop_all_total
checks["pop_ranked_share"] = pop_c[ranked].sum(dtype=np.float64) / pop_all_total if pop_all_total > 0 else np.nan
checks["pop_missing_social_share"] = (
    pop_c[populated_c & ~np.isfinite(social_c)].sum(dtype=np.float64) / pop_all_total if pop_all_total > 0 else np.nan
)
checks["pop_nan_adapted_risk_share"] = (
    pop_c[base_ok & ~risk_ok].sum(dtype=np.float64) / pop_all_total if pop_all_total > 0 else np.nan
)
del people_ok, risk_ok, base_ok

r_idx = np.flatnonzero(ranked)
p = pop_c[r_idx].astype(np.float64)
n_ranked = r_idx.size
rank = np.full(n_ranked, np.nan)
quint = np.ones(n_ranked, dtype=np.int64)
if n_ranked > 0:
    s = social_c[r_idx]
    order = np.argsort(s, kind="stable")
    s_sorted = s[order]
    p_sorted = p[order]
    cum = np.cumsum(p_sorted)
    total = cum[-1]
    # Quintiles: same cumulative-population rule as inequality_metrics.py
    q_sorted = np.clip(np.ceil(5.0 * cum / total), 1, 5).astype(np.int64)
    # Fractional rank, ties share the mid-point rank of their group
    new_group = np.empty(n_ranked, dtype=bool)
    new_group[0] = True
    new_group[1:] = s_sorted[1:] != s_sorted[:-1]
    starts = np.flatnonzero(new_group)
    group_pop = np.add.reduceat(p_sorted, starts)
    group_before = cum[starts] - p_sorted[starts]
    r_group = (group_before + 0.5 * group_pop) / total
    gid = np.cumsum(new_group) - 1
    rank[order] = r_group[gid]
    quint[order] = q_sorted
    del s, order, s_sorted, p_sorted, cum, q_sorted, new_group, starts, group_pop, group_before, r_group, gid
del social_c

n_bins = n_units + 1  # last bin = "_unassigned"
u_c = np.where(unit_c >= 0, unit_c, n_units).astype(np.int64)
del unit_c
ur = u_c[r_idx]
uq = ur * 5 + (quint - 1)
checks["unassigned_pop_share"] = p[ur == n_units].sum() / p.sum() if n_ranked > 0 else np.nan


def bsum(ids, weights, n):
    return np.bincount(ids, weights=weights, minlength=n)


ids = list(units["shapeID"]) + ["_unassigned"]
names = list(units["shapeName"]) + ["_unassigned"]

pop_cols = {"pop": bsum(ur, p, n_bins)}
pop_q = bsum(uq, p, 5 * n_bins).reshape(n_bins, 5)
for q in range(5):
    pop_cols[f"pop_Q{q + 1}"] = pop_q[:, q]
pop_cols["pop_all"] = bsum(u_c[populated_c], pop_c[populated_c].astype(np.float64), n_bins)
del populated_c, pop_c

caps_ok = np.ones(u_c.shape, dtype=bool)
for key in CAPSTOCK_KEYS:
    caps_ok &= np.isfinite(vec[key])

logging.info("Aggregating per unit and scenario.")
frames = []
for scen, (k_res, k_nres, k_infr) in SCENARIOS.items():
    df = pd.DataFrame({"shapeID": ids, "shapeName": names})
    df["admin_level"] = admin_level
    df["scenario"] = scen
    for col, values in pop_cols.items():
        df[col] = values

    # People-weighted risk (ranked cells only)
    risk_r = p * vec[k_res][r_idx]
    df["risk"] = bsum(ur, risk_r, n_bins)
    risk_q = bsum(uq, risk_r, 5 * n_bins).reshape(n_bins, 5)
    for q in range(5):
        df[f"risk_Q{q + 1}"] = risk_q[:, q]
    df["risk_rank"] = bsum(ur, risk_r * rank, n_bins)
    del risk_r

    # Capital stock losses (zero where any of the six rasters is NaN, as in capital_stock_losses.py)
    valid = caps_ok & np.isfinite(vec[k_res]) & np.isfinite(vec[k_nres]) & np.isfinite(vec[k_infr])
    l_res = np.where(valid, vec[k_res] * vec["res_capstock"], 0.0).astype(np.float32)
    l_nres = np.where(valid, vec[k_nres] * vec["nres_capstock"], 0.0).astype(np.float32)
    l_infr = np.where(valid, vec[k_infr] * vec["infr_capstock"], 0.0).astype(np.float32)
    del valid
    df["loss_res"] = bsum(u_c, l_res, n_bins)
    df["loss_nres"] = bsum(u_c, l_nres, n_bins)
    df["loss_infr"] = bsum(u_c, l_infr, n_bins)
    df["loss"] = df["loss_res"] + df["loss_nres"] + df["loss_infr"]
    del l_res, l_nres, l_infr

    tot_risk = df["risk"].sum()
    checks[f"risk_{scen}"] = tot_risk
    checks[f"CI_{scen}"] = 2.0 * df["risk_rank"].sum() / tot_risk - 1.0 if tot_risk > 0 else np.nan
    checks[f"loss_{scen}"] = df["loss"].sum()
    frames.append(df)
    logging.info(f"{scen}: national CI = {checks[f'CI_{scen}']:.4f}, losses = {checks[f'loss_{scen}']:.4e}")

pd.concat(frames, ignore_index=True).to_csv(units_out, index=False)
checks["runtime_s"] = round(time.time() - t0, 1)
pd.DataFrame([checks]).to_csv(checks_out, index=False)
logging.info("Done.")
