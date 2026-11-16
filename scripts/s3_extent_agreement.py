"""
Section 3 (revision): who lives where observed and modelled flood extents agree or disagree.

For every populated 90 m cell the script asks two questions:
    observed  - flooded at least once in the GFD record 2000-2018 (all causes; count layer > 0)
    modelled  - flooded in the river + coastal map, max(river, coastal) > 0, at the given return period
and puts the people living there into one of three groups:
    observed only   - observed flooded, no modelled flooding within the tolerance distance
    modelled only   - modelled flooded, no observed flooding within the tolerance distance
    both            - every other flooded cell
For each group it records people, people in each national wealth fifth, people in rural / peri-urban /
urban areas (GHS degree of urbanisation, same classes as inequality_metrics_degurba.py) and the
population-weighted mean national wealth rank (0 = poorest, 1 = richest), and person-floods
(people x number of times flooded in the GFD record, i.e. the quantity behind the observed CI).

Run from the repository root on the cluster:
    python scripts/s3_extent_agreement.py              # all countries in config/config.yaml, skips finished ones
    python scripts/s3_extent_agreement.py LKA GMB      # only these countries

Output: data/results/social_flood/extent_agreement/{ISO3}_extent_agreement_P-2010.csv
Reads existing inputs only. Does not touch the Snakemake rules or any existing results.
"""

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
import yaml
from rasterio.windows import Window

ROOT = Path(__file__).resolve().parents[1]
INPUTS = ROOT / "data" / "inputs" / "analysis" / "countries"
OUT_DIR = ROOT / "data" / "results" / "social_flood" / "extent_agreement"

POP_YEAR = 2010            # same population year as the observed analysis
TOLERANCES = [0, 3]        # in 90 m cells; 3 cells (~270 m) is about one MODIS pixel
BLOCK_ROWS = 2048          # rows read at a time (keeps India well within memory)
COMBOS = {
    "RP100": [("jrc", "deltares-coastal"), ("giri", "deltares-coastal"),
              ("jrc", "liscoast-coastal"), ("giri", "liscoast-coastal")],
    "RP10": [("jrc", "deltares-coastal"), ("giri", "deltares-coastal")],   # LISCoAsT has RP100 only
}
SETTLEMENT = {11: 1, 12: 1, 13: 1, 21: 2, 22: 2, 23: 2, 30: 3}   # 1 rural, 2 peri-urban, 3 urban
GROUPS = ["observed only", "modelled only", "both"]


def path(iso, name):
    return INPUTS / iso / f"{iso}_{name}.tif"


def read_block(src, r0, r1):
    """Rows r0:r1 (clipped to the raster) as an array, plus the nodata value."""
    r0c, r1c = max(r0, 0), min(r1, src.height)
    a = src.read(1, window=Window.from_slices((r0c, r1c), (0, src.width)))
    # pad with zeros where the halo runs off the raster edge
    if r0c > r0 or r1c < r1:
        a = np.pad(a, ((r0c - r0, r1 - r1c), (0, 0)))
    return a


def wet(src, r0, r1):
    """True where the flood map has water (> 0, ignoring nodata and NaN)."""
    a = read_block(src, r0, r1).astype("float32")
    bad = ~np.isfinite(a)
    if src.nodata is not None:
        bad |= a == np.float32(src.nodata)
    a[bad] = 0
    return a > 0


def dilate(mask, cells):
    """Square dilation by `cells` in each direction (separable, numpy only)."""
    if cells == 0:
        return mask
    out = mask.copy()
    for k in range(1, cells + 1):
        out[k:, :] |= mask[:-k, :]
        out[:-k, :] |= mask[k:, :]
    tmp = out.copy()
    for k in range(1, cells + 1):
        out[:, k:] |= tmp[:, :-k]
        out[:, :-k] |= tmp[:, k:]
    return out


def run_country(iso):
    files = {
        "pop": path(iso, f"ghs-pop_{POP_YEAR}"), "rwi": path(iso, "frwi"), "duc": path(iso, "ghs-mod_fixed"),
        "water": path(iso, "surface_water"),
        # count layer (times flooded). The gfd_binary_* layers are built with A>1 (flooded 2+ times), so not used here
        "gfd_count": path(iso, "gfd_all_combined-flood"),
    }
    for rp, combos in COMBOS.items():
        for river, coast in combos:
            files[f"{river}_{rp}"] = path(iso, f"{river}-flood_{rp}")
            files[f"{coast}_{rp}"] = path(iso, f"{coast}-flood_{rp}")
    missing = [str(p) for p in files.values() if not p.exists()]
    if missing:
        print(f"{iso}: skipped, missing {len(missing)} input(s), e.g. {missing[0]}")
        return None

    src = {k: rasterio.open(p) for k, p in files.items()}
    shapes = {k: (s.height, s.width) for k, s in src.items()}
    if len(set(shapes.values())) != 1:
        print(f"{iso}: skipped, rasters are not on the same grid: {shapes}")
        return None
    height, width = shapes["pop"]

    # ---- Pass 1: national wealth ranks (population-weighted, as in the CI scripts) ----
    rwi_vals, pop_vals = [], []
    for r0 in range(0, height, BLOCK_ROWS):
        r1 = min(r0 + BLOCK_ROWS, height)
        pop = read_block(src["pop"], r0, r1).astype("float64")
        rwi = read_block(src["rwi"], r0, r1).astype("float32")
        duc = read_block(src["duc"], r0, r1)
        water = read_block(src["water"], r0, r1)
        ok = (pop > 0) & np.isfinite(rwi) & (rwi != -999) & (water <= 50) & np.isin(duc, list(SETTLEMENT))
        rwi_vals.append(rwi[ok])
        pop_vals.append(pop[ok])
    rwi_vals = np.concatenate(rwi_vals)
    pop_vals = np.concatenate(pop_vals)
    # rank of each distinct wealth value = (people poorer + half the people at that value) / everyone
    values, inverse = np.unique(rwi_vals, return_inverse=True)
    pop_at = np.bincount(inverse, weights=pop_vals)
    rank_of_value = (np.cumsum(pop_at) - 0.5 * pop_at) / pop_at.sum()
    del rwi_vals, pop_vals, inverse

    # ---- Pass 2: classify people by extent agreement ----
    halo = max(TOLERANCES)
    keys = [(rp, f"{r}+{c}", tol) for rp, combos in COMBOS.items() for r, c in combos for tol in TOLERANCES]
    # per key and group: people, Q1..Q5, rural, peri-urban, urban, rank*people, person-floods (people x times flooded)
    acc = {(k, g): np.zeros(11) for k in keys for g in GROUPS}
    totals = {"total_people_observed": 0.0, "total_person_floods_observed": 0.0}

    for r0 in range(0, height, BLOCK_ROWS):
        r1 = min(r0 + BLOCK_ROWS, height)
        h0, h1 = r0 - halo, r1 + halo                 # block plus halo for the dilation
        inner = slice(halo, halo + (r1 - r0))

        pop = read_block(src["pop"], r0, r1).astype("float64")
        rwi = read_block(src["rwi"], r0, r1).astype("float32")
        duc = read_block(src["duc"], r0, r1)
        water = read_block(src["water"], r0, r1)
        count = read_block(src["gfd_count"], r0, r1).astype("float64")
        count[~np.isfinite(count) | (count < 0)] = 0
        ok = (pop > 0) & np.isfinite(rwi) & (rwi != -999) & (water <= 50) & np.isin(duc, list(SETTLEMENT))
        if not ok.any():
            continue

        land = read_block(src["water"], h0, h1) <= 50
        gfd = read_block(src["gfd_count"], h0, h1).astype("float32")
        obs = np.isfinite(gfd) & (gfd > 0) & land

        p = pop[ok]
        rank = rank_of_value[np.searchsorted(values, rwi[ok])]
        fifth = np.minimum((rank * 5).astype(int), 4)
        d = duc[ok]
        cls = np.select([np.isin(d, [11, 12, 13]), np.isin(d, [21, 22, 23])], [1, 2], 3).astype(np.int8)
        c = count[ok]
        o_in = obs[inner][ok]
        totals["total_people_observed"] += p[o_in].sum()
        totals["total_person_floods_observed"] += (p * c)[o_in].sum()

        near_obs_by_tol = {tol: dilate(obs, tol)[inner][ok] for tol in TOLERANCES}
        wet_cache = {}
        for rp, combos in COMBOS.items():
            for river, coast in combos:
                for name in (f"{river}_{rp}", f"{coast}_{rp}"):
                    if name not in wet_cache:
                        wet_cache[name] = wet(src[name], h0, h1)
                mod = (wet_cache[f"{river}_{rp}"] | wet_cache[f"{coast}_{rp}"]) & land
                m_in = mod[inner][ok]
                for tol in TOLERANCES:
                    near_mod = dilate(mod, tol)[inner][ok]
                    near_obs = near_obs_by_tol[tol]
                    groups = {"observed only": o_in & ~near_mod, "modelled only": m_in & ~near_obs}
                    groups["both"] = (o_in | m_in) & ~groups["observed only"] & ~groups["modelled only"]
                    for g, sel in groups.items():
                        ps = p[sel]
                        a = acc[((rp, f"{river}+{coast}", tol), g)]
                        a[0] += ps.sum()
                        a[1:6] += np.bincount(fifth[sel], weights=ps, minlength=5)
                        a[6:9] += np.bincount(cls[sel], weights=ps, minlength=4)[1:]
                        a[9] += (rank[sel] * ps).sum()
                        a[10] += (ps * c[sel]).sum()

    for s in src.values():
        s.close()

    rows = []
    for (key, g), a in acc.items():
        rp, combo, tol = key
        rows.append({"ISO3": iso, "rp": rp, "combo": combo, "tolerance_cells": tol, "group": g,
                     "people": a[0], **{f"people_Q{i}": a[i] for i in range(1, 6)},
                     "people_rural": a[6], "people_periurban": a[7], "people_urban": a[8],
                     "mean_rank": a[9] / a[0] if a[0] > 0 else np.nan, "person_floods": a[10],
                     **totals})
    return pd.DataFrame(rows)


if __name__ == "__main__":
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    isos = sys.argv[1:] or yaml.safe_load(open(ROOT / "config" / "config.yaml"))["iso_codes"]
    for iso in isos:
        out = OUT_DIR / f"{iso}_extent_agreement_P-{POP_YEAR}.csv"
        if out.exists():
            print(f"{iso}: already done")
            continue
        t0 = time.time()
        df = run_country(iso)
        if df is not None:
            tmp = out.with_suffix(".tmp")
            df.to_csv(tmp, index=False)
            tmp.replace(out)
            print(f"{iso}: done in {time.time() - t0:.0f} s")
