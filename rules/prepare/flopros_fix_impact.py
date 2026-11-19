"""
How much the FLOPROS fix changes the baseline (JRC, V-JRC vulnerability, RWI ranks).

For one country, recomputes the protected average annual risk with the current
{ISO3}_flopros.tif and with {ISO3}_flopros-fixed.tif, using the same truncated-curve
integration as jrc_average_annual_risk_protected.py, and reports:
  - national people-weighted risk (sum pop x AAR) before / after;
  - national concentration index before / after (ranked by RWI, as inequality_metrics.py);
  - poorest and richest fifth's share of risk before / after;
  - share of baseline risk and population in cells whose FLOPROS changes.

Only populated cells inside the country, on land (surface water <= 50) and with RWI are used,
as in inequality_metrics.py. Nothing is written except the one-row CSV.
"""

import logging

import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.features import rasterize

RPS = np.array([500, 200, 100, 75, 50, 20, 10, 2], dtype=np.float64)  # as in the JRC protected-risk script
AEP = 1.0 / RPS
CHUNK = 20_000_000


def truncated_aar(risk, T):
    """
    Vectorised version of integrate_truncated_risk in jrc_average_annual_risk_protected.py.
    risk: (8, n) risk at RPS (descending RP, RP2 = 0); T: (n,) protection return period.
    """
    T = np.nan_to_num(T.astype(np.float64))
    out = np.zeros(T.shape)
    full = T <= RPS[-1]
    if full.any():
        out[full] = np.trapezoid(risk[:, full].astype(np.float64), x=AEP[:, None], axis=0)
    for i in range(1, RPS.size):
        sel = (T > RPS[-1]) & (T < RPS[0]) & (T <= RPS[i - 1]) & (T > RPS[i])
        if not sel.any():
            continue
        t = T[sel]
        r = risk[:, sel].astype(np.float64)
        r_t = r[i - 1] + (r[i] - r[i - 1]) * (t - RPS[i - 1]) / (RPS[i] - RPS[i - 1])
        rr = np.vstack([r[:i], r_t[None]])
        aa = np.vstack([np.repeat(AEP[:i, None], t.size, axis=1), (1.0 / t)[None]])
        out[sel] = np.trapezoid(rr, x=aa, axis=0)
    out[risk[0] <= 0] = 0.0
    return out


def chunked_aar(risk, T):
    out = np.empty(T.shape)
    for s in range(0, T.size, CHUNK):
        out[s:s + CHUNK] = truncated_aar(risk[:, s:s + CHUNK], T[s:s + CHUNK])
    return out


def ci_and_shares(pop, rank_order, ranks, quint, aar):
    h = pop * aar
    tot = h.sum()
    ci = 2.0 * (h * ranks).sum() / tot - 1.0 if tot > 0 else np.nan
    q1 = h[quint == 1].sum() / tot if tot > 0 else np.nan
    q5 = h[quint == 5].sum() / tot if tot > 0 else np.nan
    return tot, ci, q1, q5


def main():
    try:
        inp = snakemake.input
        out_path: str = snakemake.output["impact"]
        country: str = snakemake.wildcards.ISO3
    except NameError:
        raise ValueError("Must be run via snakemake.")

    logging.basicConfig(format="%(asctime)s %(process)d %(filename)s %(message)s", level=logging.INFO)
    logging.info(f"FLOPROS fix impact for {country}.")

    with rasterio.open(inp["pop_file"]) as src:
        shape, transform, crs = src.shape, src.transform, src.crs
        pop = src.read(1).astype(np.float32)
    boundary = gpd.read_file(inp["boundary_file"])
    if crs is not None and boundary.crs != crs:
        boundary = boundary.to_crs(crs)
    in_country = rasterize([(g, 1) for g in boundary.geometry.buffer(0)], out_shape=shape,
                           transform=transform, fill=0, dtype="uint8").astype(bool)
    with rasterio.open(inp["mask_file"]) as src:
        water = src.read(1)
    with rasterio.open(inp["social_file"]) as src:
        social = src.read(1).astype(np.float32)
    social[social == -999] = np.nan
    ok = in_country & np.isfinite(pop) & (pop > 0) & ~(water > 50) & np.isfinite(social)
    del water, in_country
    idx = np.flatnonzero(ok)
    del ok
    p = pop.ravel()[idx].astype(np.float64)
    s = social.ravel()[idx]
    del pop, social

    def at_idx(path):
        with rasterio.open(path) as src:
            return src.read(1).astype(np.float32).ravel()[idx]

    f_old = at_idx(inp["flopros_old"])
    f_new = at_idx(inp["flopros_fixed"])
    keys = ["rp500", "rp200", "rp100", "rp75", "rp50", "rp20", "rp10"]
    risk = np.zeros((8, idx.size), dtype=np.float32)
    for k, key in enumerate(keys):
        risk[k] = at_idx(inp[key])
    del idx

    logging.info("Integrating risk with the current and fixed FLOPROS.")
    a_old = chunked_aar(risk, f_old)
    a_new = chunked_aar(risk, f_new)
    del risk
    valid = np.isfinite(a_old) & np.isfinite(a_new)
    p, s, f_old, f_new, a_old, a_new = p[valid], s[valid], f_old[valid], f_new[valid], a_old[valid], a_new[valid]

    order = np.argsort(s, kind="stable")
    cum = np.cumsum(p[order])
    total = cum[-1]
    ranks = np.empty_like(p)
    ranks[order] = (cum - 0.5 * p[order]) / total
    quint = np.empty(p.size, dtype=np.int8)
    quint[order] = np.clip(np.ceil(5.0 * cum / total), 1, 5).astype(np.int8)

    t0, c0, q10, q50 = ci_and_shares(p, order, ranks, quint, a_old)
    t1, c1, q11, q51 = ci_and_shares(p, order, ranks, quint, a_new)
    changed = np.abs(f_old - f_new) > 1e-4
    h0 = p * a_old
    row = {
        "ISO3": country,
        "pop_share_changed": p[changed].sum() / p.sum(),
        "risk_share_changed": h0[changed].sum() / h0.sum() if h0.sum() > 0 else np.nan,
        "risk_old": t0, "risk_new": t1, "risk_change_pct": 100.0 * (t1 / t0 - 1.0) if t0 > 0 else np.nan,
        "CI_old": c0, "CI_new": c1, "CI_change": c1 - c0,
        "Q1_risk_share_old": q10, "Q1_risk_share_new": q11,
        "Q5_risk_share_old": q50, "Q5_risk_share_new": q51,
    }
    pd.DataFrame([row]).to_csv(out_path, index=False)
    logging.info(f"Done: {row}")


if __name__ == "__main__":
    main()
