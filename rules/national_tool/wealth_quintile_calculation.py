"""
This script creates a population wealth quintile map for plotting / mapping.

Where populated cells do not overlap a valid RWI cell, the script assigns
those cells the population-weighted average RWI of their ADM2 region.

The resulting RWI surface is then used to calculate national
population-weighted wealth quintiles.
"""

import logging

import rasterio
import numpy as np
import geopandas as gpd
from rasterio.features import rasterize
from rasterio.warp import transform_geom


if __name__ == "__main__":

    try:
        admin_path: str = snakemake.input["boundary_file"]
        pop_path: str = snakemake.input["pop_file"]
        rwi_path: str = snakemake.input["rwi_file"]
        output_path: str = snakemake.output["wealth_quintiles"]
        country: str = snakemake.wildcards.ISO3
    except NameError:
        raise ValueError("Must be run via snakemake.")


logging.basicConfig(
    format="%(asctime)s %(process)d %(filename)s %(message)s",
    level=logging.INFO
)

logging.info(f"Mapping population wealth quintiles in {country}.")

logging.info("Loading population and RWI raster data.")

with rasterio.open(rwi_path) as src_rwi:
    rwi_data = src_rwi.read(1).astype(np.float32)
    rwi_nodata = src_rwi.nodata
    rwi_crs = src_rwi.crs
    rwi_transform = src_rwi.transform

with rasterio.open(pop_path) as src_pop:
    pop_data = src_pop.read(1).astype(np.float32)
    profile = src_pop.meta.copy()
    profile.update(
        dtype=rasterio.int16,
        compress="lzw",
        nodata=0,
        count=1
    )
    pop_nodata = src_pop.nodata
    pop_crs = src_pop.crs
    pop_transform = src_pop.transform
    pop_shape = pop_data.shape

assert rwi_data.shape == pop_data.shape, "RWI and population rasters must match in shape."
assert rwi_transform == pop_transform, "RWI and population rasters must have the same transform."
assert rwi_crs == pop_crs, "RWI and population rasters must have the same CRS."


logging.info("Creating valid population and RWI masks.")

if pop_nodata is not None:
    valid_pop_mask = (pop_data != pop_nodata) & np.isfinite(pop_data) & (pop_data > 0)
else:
    valid_pop_mask = np.isfinite(pop_data) & (pop_data > 0)

if rwi_nodata is not None:
    valid_rwi_mask = (rwi_data != rwi_nodata) & np.isfinite(rwi_data)
else:
    valid_rwi_mask = np.isfinite(rwi_data)

valid_pop_rwi_mask = valid_pop_mask & valid_rwi_mask
missing_rwi_pop_mask = valid_pop_mask & ~valid_rwi_mask

logging.info(f"Populated cells with valid RWI: {valid_pop_rwi_mask.sum()}")
logging.info(f"Populated cells missing RWI: {missing_rwi_pop_mask.sum()}")


logging.info("Calculating national unweighted mean RWI for fallback.")
national_rwi_mean = float(np.mean(rwi_data[valid_rwi_mask]))

logging.info(f"National unweighted mean RWI: {national_rwi_mean}")

layer_name = "ADM2"

admin_areas: gpd.GeoDataFrame = gpd.read_file(admin_path, layer="ADM2")

area_unique_id_col = "shapeID"
admin_areas = admin_areas[[area_unique_id_col, "shapeName", "geometry"]].copy()

admin_areas = admin_areas.dropna(subset=["geometry"]).copy()
admin_areas = admin_areas[~admin_areas.geometry.is_empty].copy()

if admin_areas.crs is None:
    raise ValueError(f"Admin boundaries have no CRS: {admin_path}")

if admin_areas.crs != pop_crs:
    logging.info("Reprojecting admin boundaries to population raster CRS.")
    admin_areas = admin_areas.to_crs(pop_crs)

logging.info(f"There are {len(admin_areas)} admin areas to analyze.")


logging.info("Rasterising admin boundaries to the population grid.")

# Raster values need to be numeric, so create an integer admin ID.
admin_areas = admin_areas.reset_index(drop=True)
admin_areas["admin_raster_id"] = np.arange(1, len(admin_areas) + 1, dtype=np.int32)

admin_shapes = [
    (geom, int(admin_id))
    for geom, admin_id in zip(admin_areas.geometry, admin_areas["admin_raster_id"])
]

admin_raster = rasterize(
    admin_shapes,
    out_shape=pop_shape,
    transform=pop_transform,
    fill=0,
    dtype="int32",
)

logging.info("Filling missing populated RWI cells using admin-level mean RWI.")

rwi_filled = rwi_data.copy()

admin_ids_with_missing_rwi = np.unique(admin_raster[missing_rwi_pop_mask])
admin_ids_with_missing_rwi = admin_ids_with_missing_rwi[admin_ids_with_missing_rwi != 0]

filled_cell_count = 0
national_fallback_cell_count = 0

for admin_id in admin_ids_with_missing_rwi:

    admin_mask = admin_raster == admin_id

    # Cells in this admin region that have a valid RWI value.
    # This is NOT population-weighted.
    admin_valid_rwi_mask = admin_mask & valid_rwi_mask

    # Populated cells in this admin region that are missing RWI.
    admin_missing_mask = admin_mask & missing_rwi_pop_mask

    if admin_missing_mask.sum() == 0:
        continue

    admin_name = admin_areas.loc[
        admin_areas["admin_raster_id"] == admin_id,
        "shapeName"
    ].iloc[0]

    if admin_valid_rwi_mask.sum() > 0:
        admin_mean_rwi = float(np.mean(rwi_data[admin_valid_rwi_mask]))
    else:
        logging.warning(
            f"No valid RWI cells in {layer_name} area {admin_name}. "
            "Using national unweighted mean RWI."
        )
        admin_mean_rwi = national_rwi_mean
        national_fallback_cell_count += int(admin_missing_mask.sum())

    rwi_filled[admin_missing_mask] = admin_mean_rwi
    filled_cell_count += int(admin_missing_mask.sum())

logging.info(f"Filled missing RWI cells using unweighted {layer_name} means: {filled_cell_count}")
logging.info(f"Filled missing RWI cells using national fallback: {national_fallback_cell_count}")


logging.info("Handling populated missing-RWI cells outside rasterised admin areas.")

outside_admin_missing_mask = missing_rwi_pop_mask & (admin_raster == 0)

if outside_admin_missing_mask.sum() > 0:
    logging.warning(
    f"{outside_admin_missing_mask.sum()} populated cells with missing RWI "
    f"fell outside rasterised {layer_name} boundaries. "
    "Assigning national unweighted mean RWI."
)


logging.info("Calculating population-weighted national RWI quintile thresholds.")

valid_quintile_mask = valid_pop_mask & np.isfinite(rwi_filled)

rwi_valid = rwi_filled[valid_quintile_mask]
population_valid = pop_data[valid_quintile_mask]

sorted_indices = np.argsort(rwi_valid)
rwi_sorted = rwi_valid[sorted_indices]
population_sorted = population_valid[sorted_indices]

cumulative_population = np.cumsum(population_sorted)
total_population = cumulative_population[-1]

quintile_thresholds = []

for q in [0.2, 0.4, 0.6, 0.8]:
    idx = np.searchsorted(cumulative_population, q * total_population)
    quintile_thresholds.append(rwi_sorted[idx])

logging.info(f"Quintile thresholds: {quintile_thresholds}")


logging.info("Applying population-weighted quintile thresholds to population map.")

quintile_map = np.zeros(pop_data.shape, dtype=np.int16)

quintile_map[
    (rwi_filled <= quintile_thresholds[0]) & valid_pop_mask
] = 1

quintile_map[
    (rwi_filled > quintile_thresholds[0])
    & (rwi_filled <= quintile_thresholds[1])
    & valid_pop_mask
] = 2

quintile_map[
    (rwi_filled > quintile_thresholds[1])
    & (rwi_filled <= quintile_thresholds[2])
    & valid_pop_mask
] = 3

quintile_map[
    (rwi_filled > quintile_thresholds[2])
    & (rwi_filled <= quintile_thresholds[3])
    & valid_pop_mask
] = 4

quintile_map[
    (rwi_filled > quintile_thresholds[3]) & valid_pop_mask
] = 5


logging.info("Writing wealth quintile raster.")
with rasterio.open(output_path, "w", **profile) as dst:
    dst.write(quintile_map, 1)

logging.info("Done.")