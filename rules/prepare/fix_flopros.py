"""
Country FLOPROS raster without boundary artefacts.

The current {ISO3}_flopros.tif comes from rasterising every FLOPROS polygon into one global
raster (fill 0) and clipping it to the geoBoundaries outline. Because the two datasets draw
coastlines and borders differently, this leaves:
  - cells inside the country but outside every FLOPROS polygon (coastal strips, interior
    gaps) at 0, which the risk scripts treat as unprotected;
  - cells inside the country but inside a neighbouring country's FLOPROS polygon, which take
    the neighbour's protection standard.

FLOPROS itself never uses 0 as a protection standard: its minimum ("no protection") is a 2-year
return period, and units where no standard could be derived are "no data" (Scussolini et al.
2016). A MerL_Riv of 0 is therefore treated as no data here, like a missing polygon.

This script:
  1. keeps only the country's own FLOPROS polygons with data (MerL_Riv > 0; at least half of the
     polygon's area lies inside the country boundary);
  2. rasterises their merged river protection standard (MerL_Riv) on the population grid;
  3. fills every cell inside the country that no own polygon covers with the value of the
     nearest covered cell (Euclidean nearest neighbour; falls back to the national median
     if nothing is reachable);
  4. sets cells outside the country to 0, as the current clipped raster does.

Cells covered by an own polygon with data keep that polygon's value exactly, including low values.

A one-row log compares the result with the current {ISO3}_flopros.tif (read if present):
shares of in-country cells and of population whose protection changes, and the
population-weighted mean protection before and after.
"""

import logging
import os

import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.features import rasterize

OWN_SHARE = 0.5      # share of a FLOPROS polygon's area that must lie inside the country
WINDOW_MARGIN = 256  # cells around the gaps searched for nearest values


def nearest_fill(values, valid, target):
    """
    Give every target cell the value of the nearest valid cell (Euclidean, in cells).
    Returns (filled values, mask of target cells that could not be filled).
    Uses scipy's distance transform when available, otherwise 4-neighbour dilation.
    """
    values = values.copy()
    target = target & ~valid
    if not target.any() or not valid.any():
        return values, target
    try:
        from scipy import ndimage
    except ImportError:
        return _dilation_fill(values, valid, target)
    idx = ndimage.distance_transform_edt(~valid, return_distances=False, return_indices=True)
    rows, cols = idx[0][target], idx[1][target]
    values[target] = values[rows, cols]
    return values, np.zeros_like(target)


def _dilation_fill(values, valid, target, max_iter=100000):
    """Fallback without scipy: grow valid values into the target one cell per iteration."""
    valid = valid.copy()
    target = target.copy()
    dirs = [
        ((slice(1, None), slice(None)), (slice(None, -1), slice(None))),
        ((slice(None, -1), slice(None)), (slice(1, None), slice(None))),
        ((slice(None), slice(1, None)), (slice(None), slice(None, -1))),
        ((slice(None), slice(None, -1)), (slice(None), slice(1, None))),
    ]
    for _ in range(max_iter):
        if not target.any():
            break
        new = np.zeros_like(target)
        for ts, ss in dirs:
            cand = target[ts] & valid[ss] & ~new[ts]
            if cand.any():
                v = values[ts]
                v[cand] = values[ss][cand]
                n = new[ts]
                n |= cand
        if not new.any():
            break
        valid |= new
        target &= ~new
    return values, target


def fill_in_window(values, covered, gap, margin=WINDOW_MARGIN):
    """Run nearest_fill only inside the bounding box of the gaps (plus a margin)."""
    remaining = np.zeros_like(gap)
    if not gap.any():
        return values, remaining
    r = np.flatnonzero(gap.any(axis=1))
    c = np.flatnonzero(gap.any(axis=0))
    r0, r1 = max(r[0] - margin, 0), min(r[-1] + margin + 1, gap.shape[0])
    c0, c1 = max(c[0] - margin, 0), min(c[-1] + margin + 1, gap.shape[1])
    win = (slice(r0, r1), slice(c0, c1))
    filled, left = nearest_fill(values[win], covered[win], gap[win])
    values[win] = filled  # in place: the caller's array is updated
    remaining[win] = left
    return values, remaining


def summarise(old, new, in_country, covered, pop):
    """Shares of in-country cells / population affected, and population-weighted means."""
    w = np.where(np.isfinite(pop) & (pop > 0) & in_country, pop, 0).astype(np.float32)
    n_cells = int(in_country.sum())
    p_tot = float(w.sum(dtype=np.float64))

    def share(mask):
        return float(w[mask].sum(dtype=np.float64) / p_tot) if p_tot else np.nan

    out = {
        "cells_in_country": n_cells,
        "cell_share_own_polygons": float((in_country & covered).sum() / n_cells) if n_cells else np.nan,
        "cell_share_filled": float((in_country & ~covered).sum() / n_cells) if n_cells else np.nan,
        "pop_share_filled": share(~covered),
        "pop_mean_flopros_new": float((w * new).sum(dtype=np.float64) / p_tot) if p_tot else np.nan,
    }
    if old is not None:
        changed = in_country & (np.abs(old - new) > 1e-4)
        out.update({
            "cell_share_changed": float(changed.sum() / n_cells) if n_cells else np.nan,
            "pop_share_changed": share(changed),
            "pop_share_old_zero": share(in_country & (old == 0)),
            "pop_share_old_other_value_under_own_polygon": share(changed & covered),
            "pop_mean_flopros_old": float((w * old).sum(dtype=np.float64) / p_tot) if p_tot else np.nan,
        })
    return out


def main():
    try:
        flopros_path: str = snakemake.input["flopros"]
        boundary_path: str = snakemake.input["boundary_file"]
        pop_path: str = snakemake.input["pop_file"]
        out_path: str = snakemake.output["flopros_fixed"]
        log_path: str = snakemake.output["log"]
        country: str = snakemake.wildcards.ISO3
    except NameError:
        raise ValueError("Must be run via snakemake.")

    logging.basicConfig(format="%(asctime)s %(process)d %(filename)s %(message)s", level=logging.INFO)
    logging.info(f"Fixing FLOPROS raster for {country}.")

    with rasterio.open(pop_path) as src:
        profile = src.profile.copy()
        shape, transform, crs = src.shape, src.transform, src.crs

    boundary = gpd.read_file(boundary_path)
    if crs is not None and boundary.crs != crs:
        boundary = boundary.to_crs(crs)
    boundary["geometry"] = boundary.geometry.buffer(0)
    country_geom = boundary.geometry.union_all() if hasattr(boundary.geometry, "union_all") else boundary.geometry.unary_union

    fl_crs = gpd.read_file(flopros_path, rows=1).crs
    bbox = tuple(gpd.GeoSeries([country_geom], crs=crs).to_crs(fl_crs).total_bounds) if (crs is not None and fl_crs != crs) else tuple(country_geom.bounds)
    polys = gpd.read_file(flopros_path, bbox=bbox)
    n_no_data = int((polys["MerL_Riv"].isna() | (polys["MerL_Riv"] <= 0)).sum())
    polys = polys[(polys["MerL_Riv"] > 0) & polys.geometry.notna()].copy()  # 0 = no data in FLOPROS
    if crs is not None and polys.crs != crs:
        polys = polys.to_crs(crs)
    polys["geometry"] = polys.geometry.buffer(0)
    polys = polys[~polys.geometry.is_empty & (polys.geometry.area > 0)]
    share_inside = polys.geometry.intersection(country_geom).area / polys.geometry.area
    own = polys[share_inside >= OWN_SHARE]
    logging.info(f"{len(polys)} FLOPROS polygons near {country}; {len(own)} belong to it.")
    fallback_all = False
    if len(own) == 0:
        logging.warning("No own FLOPROS polygons found; using all intersecting polygons.")
        own = polys[share_inside > 0]
        fallback_all = True

    logging.info("Rasterising own polygons and the country outline.")
    shapes = [(g, float(v)) for g, v in zip(own.geometry, own["MerL_Riv"])]
    values = rasterize(shapes, out_shape=shape, transform=transform, fill=0, dtype="float32") if shapes \
        else np.zeros(shape, dtype="float32")
    covered = rasterize([(g, 1) for g in own.geometry], out_shape=shape, transform=transform, fill=0, dtype="uint8").astype(bool) \
        if shapes else np.zeros(shape, dtype=bool)
    in_country = rasterize([(country_geom, 1)], out_shape=shape, transform=transform, fill=0, dtype="uint8").astype(bool)

    logging.info("Filling cells inside the country that no own polygon covers.")
    gap = in_country & ~covered
    values, remaining = fill_in_window(values, covered, gap)
    n_median = int(remaining.sum())
    if n_median:
        ref = values[in_country & covered]
        values[remaining] = float(np.median(ref)) if ref.size else 0.0
        logging.warning(f"{n_median} cells filled with the national median.")
    values[~in_country] = 0.0

    profile.update(dtype="float32", count=1, compress="lzw", nodata=None, BIGTIFF="IF_SAFER")
    with rasterio.open(out_path, "w", **profile) as dst:
        dst.write(values.astype(np.float32), 1)

    logging.info("Comparing with the current FLOPROS raster.")
    old_path = os.path.join(os.path.dirname(out_path), f"{country}_flopros.tif")
    old = None
    if os.path.exists(old_path):
        with rasterio.open(old_path) as src:
            if src.shape == shape:
                old = src.read(1).astype(np.float32)
                old[~np.isfinite(old)] = 0.0
    with rasterio.open(pop_path) as src:
        pop = src.read(1).astype(np.float32)
    log = {"ISO3": country, "n_polygons_near": len(polys), "n_polygons_no_data": n_no_data, "n_polygons_own": len(own),
           "fallback_all_polygons": fallback_all, "cells_filled_with_median": n_median}
    log.update(summarise(old, values, in_country, covered, pop))
    pd.DataFrame([log]).to_csv(log_path, index=False)
    logging.info(f"Done: {log}")


if __name__ == "__main__":
    main()
