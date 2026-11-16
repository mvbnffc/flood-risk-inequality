"""
River flood protection for every admin unit (ADM1 or ADM2) that has a river.

Unlike prepare_river_flood_protection.py, there is no urbanisation filter: every unit
with river network (the {ISO3}_river_network.gpkg, HydroRIVERS >= 500 km2 upstream area)
is protected to the design return period. Which units are worth protecting is decided
later (notebook), using the per-unit costs written here and the per-unit benefits from
the adapted risk rasters.

Costs are computed per river segment (river reach clipped to the admin unit) against the
FLOPROS protection along that segment:

    cost_segment = unit cost * length (km) * mean over points along the segment of
                   log2(RP_design / max(FLOPROS_point, 2))      (0 where FLOPROS >= RP)

following Boulange et al. (2023), FPL_future = FPL_current * 2^L, with unit cost per km
per doubling of the protection return period (min / standard / max = 0.7996 / 2.399 / 7.196
$ million). FLOPROS is sampled at roughly one point per raster cell along each segment
(points off the raster or on no-data are ignored).
FLOPROS = 0 (outside the FLOPROS polygons) is treated as unprotected, as in the risk scripts,
and baseline protection is floored at 2 years.

Outputs
    flood_protection   FLOPROS raster with protection raised to RP in every protected unit
                       (protection is only ever increased; no-data cells are left unchanged)
    protection_cost    GeoPackage, one row per admin unit: river length, length-weighted FLOPROS
                       and doublings, costs ($ million; same column names as
                       flood_protection_costs.py) and a 'protected' flag
    segments           CSV, one row per river segment (for checking)

A unit is protected if it has river length > 0 and a positive cost (some river with
FLOPROS below the design RP).
"""

import logging

import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.features import rasterize
import shapely
from pyproj import Geod
from shapely.geometry import LineString, MultiLineString

MIN_UNIT_COST = 0.7996  # $ million per km per doubling (Boulange et al. 2023, supplementary)
STANDARD_UNIT_COST = 2.399
MAX_UNIT_COST = 7.196
MIN_BASELINE_PROTECTION = 2.0  # years
MAX_POINTS_PER_SEGMENT = 5000


def geodetic_length_km(geom):
    """Geodetic length (km) of a LineString / MultiLineString in lon/lat (WGS84)."""
    geod = Geod(ellps="WGS84")
    lines = [geom] if isinstance(geom, LineString) else list(geom.geoms) if isinstance(geom, MultiLineString) else []
    total = 0.0
    for line in lines:
        coords = np.asarray(line.coords)
        if len(coords) < 2:
            continue
        _, _, dist = geod.inv(coords[:-1, 0], coords[:-1, 1], coords[1:, 0], coords[1:, 1])
        total += float(np.sum(dist))
    return total / 1000.0


def doublings(flopros_values, rp):
    """Number of doublings from baseline to design protection, per FLOPROS value (>= 0)."""
    base = np.maximum(np.where(np.isfinite(flopros_values), flopros_values, 0.0), MIN_BASELINE_PROTECTION)
    return np.where(rp > base, np.log2(rp / base), 0.0)


def pixel_values(arr, transform, xs, ys):
    """Raster values at points (x, y) in the raster CRS; NaN outside the raster."""
    cols, rows = ~transform * (np.asarray(xs, dtype=float), np.asarray(ys, dtype=float))
    cols = np.floor(cols).astype(np.int64)
    rows = np.floor(rows).astype(np.int64)
    inside = (rows >= 0) & (rows < arr.shape[0]) & (cols >= 0) & (cols < arr.shape[1])
    out = np.full(cols.shape, np.nan)
    out[inside] = arr[rows[inside], cols[inside]]
    return out


def segment_costs(length_km, mean_doublings, gdp_adjustment):
    """Costs ($ million) for arrays of segment length and mean doublings."""
    base = np.asarray(length_km, dtype=float) * np.asarray(mean_doublings, dtype=float)
    adj_unit = np.clip(STANDARD_UNIT_COST * gdp_adjustment, MIN_UNIT_COST, MAX_UNIT_COST) \
        if np.isfinite(gdp_adjustment) else np.nan
    return {
        "adaptation_cost": STANDARD_UNIT_COST * base,
        "adj_adaptation_cost": adj_unit * base,
        "min_adaptation_cost": MIN_UNIT_COST * base,
        "max_adaptation_cost": MAX_UNIT_COST * base,
    }


def raise_protection(flopros, unit_mask, rp, nodata, inplace=False):
    """Raise protection to rp inside unit_mask (only ever increases; no-data cells untouched)."""
    out = flopros if inplace else flopros.copy()
    valid = unit_mask & np.isfinite(out)
    if nodata is not None and np.isfinite(nodata) and nodata != 0:  # 0 = unprotected, so it is raised
        valid &= out != nodata
    out[valid] = np.maximum(out[valid], rp)
    return out


def sample_segments(lines, step):
    """
    Points roughly every `step` (raster CRS units) along each line.
    Returns (segment index per point, x, y).
    """
    lengths = np.array([line.length for line in lines], dtype=float)
    n_points = np.clip(np.ceil(lengths / step).astype(np.int64) + 1, 2, MAX_POINTS_PER_SEGMENT)
    seg_idx = np.repeat(np.arange(len(lines)), n_points)
    # Fractions 0..1 along each line (cell-centred spacing would also work; ends included)
    fractions = np.concatenate([np.linspace(0.0, 1.0, n) for n in n_points]) if len(lines) else np.array([])
    try:
        geoms = np.asarray(lines, dtype=object)[seg_idx]
        pts = shapely.line_interpolate_point(geoms, fractions, normalized=True)
        xs, ys = shapely.get_x(pts), shapely.get_y(pts)
    except AttributeError:  # shapely < 2
        pts = [lines[i].interpolate(f, normalized=True) for i, f in zip(seg_idx, fractions)]
        xs = np.array([p.x for p in pts])
        ys = np.array([p.y for p in pts])
    return seg_idx, xs, ys


def main():
    try:
        flopros_path: str = snakemake.input["flopros"]
        river_path: str = snakemake.input["rivers"]
        admin_path: str = snakemake.input["admin_areas"]
        gdppc_path: str = snakemake.input["gdppc"]
        raster_out: str = snakemake.output["flood_protection"]
        cost_out: str = snakemake.output["protection_cost"]
        segments_out: str = snakemake.output["segments"]
        country: str = snakemake.wildcards.ISO3
        rp = float(snakemake.wildcards.RP)
        admin_level: str = snakemake.wildcards.ADMIN_SLUG
    except NameError:
        raise ValueError("Must be run via snakemake.")

    logging.basicConfig(format="%(asctime)s %(process)d %(filename)s %(message)s", level=logging.INFO)
    logging.info(f"Admin flood protection for {country}: every {admin_level} unit with a river to RP{rp:g}.")

    with rasterio.open(flopros_path) as src:
        flopros = src.read(1).astype(np.float32)
        profile = src.profile.copy()
        transform = src.transform
        raster_crs = src.crs
        nodata = src.nodata
    step = abs(transform.a)

    logging.info("Reading admin units and rivers.")
    admin = gpd.read_file(admin_path, layer=admin_level)[["shapeID", "shapeName", "geometry"]]
    admin = admin.dropna(subset=["geometry"])
    admin = admin[~admin.geometry.is_empty].reset_index(drop=True)
    if raster_crs is not None and admin.crs != raster_crs:
        admin = admin.to_crs(raster_crs)
    invalid = ~admin.geometry.is_valid
    if invalid.any():
        admin.loc[invalid, "geometry"] = admin.loc[invalid, "geometry"].buffer(0)
    rivers = gpd.read_file(river_path)
    if raster_crs is not None and rivers.crs != raster_crs:
        rivers = rivers.to_crs(raster_crs)
    keep = [c for c in ("HYRIV_ID", "UPLAND_SKM", "ORD_STRA") if c in rivers.columns]
    logging.info(f"{len(admin)} {admin_level} units, {len(rivers)} river reaches.")

    logging.info("Clipping rivers to admin units.")
    if len(rivers) > 0:
        segments = gpd.overlay(rivers[keep + ["geometry"]], admin, how="intersection", keep_geom_type=True)
        segments = segments.explode(index_parts=False).reset_index(drop=True)
        segments = segments[~segments.geometry.is_empty & (segments.geometry.length > 0)].reset_index(drop=True)
    else:
        segments = admin.iloc[0:0].copy()
    logging.info(f"{len(segments)} river segments.")

    gdp_df = pd.read_csv(gdppc_path, encoding="utf-8-sig")
    try:
        country_gdp = gdp_df.loc[gdp_df["ISO"].eq(country), "GDP_pc"].iloc[0]
        global_gdp = gdp_df.loc[gdp_df["ISO"].eq("WORLD"), "GDP_pc"].iloc[0]
        gdp_adjustment = float(country_gdp) / float(global_gdp)
    except IndexError:
        logging.warning(f"No GDP per capita for {country}; adjusted costs set to NaN.")
        gdp_adjustment = np.nan

    if len(segments) > 0:
        logging.info("Segment lengths and FLOPROS along each segment.")
        seg_ll = segments.to_crs(4326) if (segments.crs is not None and not segments.crs.is_geographic) else segments
        segments["length_km"] = seg_ll.geometry.apply(geodetic_length_km).to_numpy()
        lines = list(segments.geometry)
        seg_idx, xs, ys = sample_segments(lines, step)
        values = pixel_values(flopros, transform, xs, ys)
        if nodata is not None and np.isfinite(nodata) and nodata != 0:
            values[values == nodata] = np.nan
        # Points off the raster / on no-data are ignored; a segment with no valid point is
        # treated as unprotected (baseline floored at 2 years).
        ok = np.isfinite(values).astype(float)
        d = doublings(values, rp)
        n_seg = len(segments)
        n_ok = np.bincount(seg_idx, weights=ok, minlength=n_seg)
        segments["n_points"] = np.bincount(seg_idx, minlength=n_seg)
        segments["n_points_valid"] = n_ok.astype(int)
        with np.errstate(invalid="ignore", divide="ignore"):
            segments["flopros_mean"] = np.where(
                n_ok > 0, np.bincount(seg_idx, weights=np.nan_to_num(values) * ok, minlength=n_seg) / n_ok, np.nan)
            segments["doublings"] = np.where(
                n_ok > 0, np.bincount(seg_idx, weights=d * ok, minlength=n_seg) / n_ok, doublings(np.array([0.0]), rp)[0])
        segments["flopros_min"] = pd.Series(values).groupby(seg_idx).min().reindex(range(n_seg)).to_numpy()
        segments["flopros_max"] = pd.Series(values).groupby(seg_idx).max().reindex(range(n_seg)).to_numpy()
        for col, val in segment_costs(segments["length_km"], segments["doublings"], gdp_adjustment).items():
            segments[col] = val
    else:
        for col in ("length_km", "n_points", "n_points_valid", "flopros_mean", "flopros_min", "flopros_max", "doublings",
                    "adaptation_cost", "adj_adaptation_cost", "min_adaptation_cost", "max_adaptation_cost"):
            segments[col] = pd.Series(dtype=float)

    logging.info("Summing per admin unit.")
    seg_tab = pd.DataFrame(segments.drop(columns="geometry"))
    seg_tab["lw_flopros"] = seg_tab["length_km"] * seg_tab["flopros_mean"]
    seg_tab["lw_doublings"] = seg_tab["length_km"] * seg_tab["doublings"]
    cost_cols = ["adaptation_cost", "adj_adaptation_cost", "min_adaptation_cost", "max_adaptation_cost"]
    per_unit = seg_tab.groupby("shapeID").agg(
        river_len_km=("length_km", "sum"),
        n_segments=("length_km", "size"),
        lw_flopros=("lw_flopros", "sum"),
        lw_doublings=("lw_doublings", "sum"),
        **{c: (c, "sum") for c in cost_cols},
    ).reset_index()
    per_unit["flopros_lw"] = per_unit["lw_flopros"] / per_unit["river_len_km"]
    per_unit["doublings_lw"] = per_unit["lw_doublings"] / per_unit["river_len_km"]
    per_unit = per_unit.drop(columns=["lw_flopros", "lw_doublings"])

    units = admin.merge(per_unit, on="shapeID", how="left")
    for c in ["river_len_km", "n_segments"] + cost_cols:
        units[c] = units[c].fillna(0)
    if not np.isfinite(gdp_adjustment):
        units["adj_adaptation_cost"] = np.nan
    units["protected"] = ((units["river_len_km"] > 0) & (units["min_adaptation_cost"] > 0)).astype(int)
    logging.info(f"{int(units['protected'].sum())} of {len(units)} units protected; "
                 f"total cost (min/standard/max) = {units['min_adaptation_cost'].sum():.1f} / "
                 f"{units['adaptation_cost'].sum():.1f} / {units['max_adaptation_cost'].sum():.1f} $ million.")

    logging.info("Writing adapted FLOPROS raster.")
    protected_geoms = [g for g in units.loc[units["protected"] == 1, "geometry"]]
    if protected_geoms:
        unit_mask = rasterize(
            [(g, 1) for g in protected_geoms],
            out_shape=flopros.shape, transform=transform, fill=0, dtype="uint8",
        ).astype(bool)
        adapted = raise_protection(flopros, unit_mask, rp, nodata, inplace=True)
        del unit_mask
    else:
        adapted = flopros
    profile.update(dtype=rasterio.float32, compress="lzw", BIGTIFF="IF_SAFER")
    with rasterio.open(raster_out, "w", **profile) as dst:
        dst.write(adapted.astype(np.float32), 1)

    logging.info("Writing costs.")
    gpd.GeoDataFrame(units, geometry="geometry", crs=admin.crs).to_file(cost_out, driver="GPKG")
    seg_tab.drop(columns=["lw_flopros", "lw_doublings"]).to_csv(segments_out, index=False)
    logging.info("Done.")


if __name__ == "__main__":
    main()
