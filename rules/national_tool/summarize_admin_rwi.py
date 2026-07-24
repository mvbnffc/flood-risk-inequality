"""
This script calculates average and population-weighted RWI values for each
administrative region.
"""

import logging
import os

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.features import rasterize


if __name__ == "__main__":

    try:
        admin_path: str = snakemake.input["admin_areas"]
        pop_rwi_path: str = snakemake.input["pop_rwi_assignment"]
        pop_path: str = snakemake.input["pop_file"]
        output_path: str = snakemake.output["admin_rwi_summary"]
        country: str = snakemake.wildcards.ISO3
        administrative_level: str = snakemake.wildcards.ADMIN_SLUG
    except NameError:
        raise ValueError("Must be run via snakemake.")


logging.basicConfig(
    format="%(asctime)s %(process)d %(filename)s %(message)s",
    level=logging.INFO
)

admin_level = int(administrative_level.replace("ADM", ""))
layer_name = f"ADM{admin_level}"

logging.info(
    f"Calculating RWI summary metrics for {country} at admin level "
    f"{admin_level}."
)

logging.info("Creating output directories (if they don't already exist).")
out_dir = os.path.dirname(output_path)
os.makedirs(out_dir, exist_ok=True)


logging.info("Reading RWI assignment and population rasters.")

with rasterio.open(pop_rwi_path) as rwi_src:
    rwi = rwi_src.read(1, masked=True).astype("float64").filled(np.nan)
    raster_shape = rwi_src.shape
    raster_transform = rwi_src.transform
    raster_crs = rwi_src.crs

with rasterio.open(pop_path) as pop_src:
    population = (
        pop_src.read(1, masked=True).astype("float64").filled(np.nan)
    )
    pop_shape = pop_src.shape
    pop_transform = pop_src.transform
    pop_crs = pop_src.crs

if pop_shape != raster_shape:
    raise ValueError("RWI assignment and population rasters must match in shape.")
if pop_transform != raster_transform:
    raise ValueError(
        "RWI assignment and population rasters must have the same transform."
    )
if pop_crs != raster_crs:
    raise ValueError(
        "RWI assignment and population rasters must have the same CRS."
    )

valid_data_mask = (
    np.isfinite(rwi)
    & np.isfinite(population)
    & (population > 0)
)


logging.info(f"Reading level {administrative_level} admin boundaries.")

admin_areas: gpd.GeoDataFrame = gpd.read_file(
    admin_path,
    layer=layer_name
)
admin_areas = admin_areas.reset_index(drop=True)

if layer_name == "ADM0":
    admin_areas = admin_areas[["shapeName", "geometry"]]
    admin_areas = admin_areas.dissolve(by="shapeName", as_index=False)
else:
    admin_areas = admin_areas[
        ["shapeID", "shapeName", "geometry"]
    ].copy()

admin_areas = admin_areas.dropna(subset=["geometry"]).copy()
admin_areas = admin_areas[~admin_areas.geometry.is_empty].copy()
admin_areas = admin_areas.reset_index(drop=True)

if admin_areas.crs is None:
    raise ValueError(f"Admin boundaries have no CRS: {admin_path}")

admin_areas_for_raster = admin_areas
if admin_areas.crs != raster_crs:
    logging.info("Reprojecting admin boundaries to match raster CRS.")
    admin_areas_for_raster = admin_areas.to_crs(raster_crs)

logging.info(f"There are {len(admin_areas)} admin areas to analyze.")


logging.info("Rasterising admin boundaries to the RWI grid.")

region_ids = rasterize(
    [
        (geometry, region_id)
        for region_id, geometry
        in enumerate(admin_areas_for_raster.geometry)
    ],
    out_shape=raster_shape,
    transform=raster_transform,
    fill=-1,
    dtype=np.int32
)


logging.info("Calculating regional RWI metrics.")

average_rwi = np.full(len(admin_areas), np.nan, dtype=np.float64)
population_weighted_rwi = np.full(
    len(admin_areas),
    np.nan,
    dtype=np.float64
)

for region_id in range(len(admin_areas)):
    region_mask = (region_ids == region_id) & valid_data_mask

    if not np.any(region_mask):
        logging.warning(
            f"No valid populated RWI cells found for "
            f"{admin_areas.iloc[region_id]['shapeName']}."
        )
        continue

    region_rwi = rwi[region_mask]
    region_population = population[region_mask]

    average_rwi[region_id] = np.mean(region_rwi)
    population_weighted_rwi[region_id] = np.average(
        region_rwi,
        weights=region_population
    )


logging.info("Writing RWI metrics to GeoPackage.")

results_gdf = admin_areas.copy()
results_gdf["average_rwi"] = average_rwi
results_gdf["population_weighted_rwi"] = population_weighted_rwi
results_gdf.to_file(output_path, driver="GPKG")

logging.info("Done.")
