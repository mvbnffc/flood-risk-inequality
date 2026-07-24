"""
This script sums WorldPop demographic groups for each administrative region.
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
        population_paths = {
            "total_population": snakemake.input["total_pop"],
            "female_population": snakemake.input["female_pop"],
            "male_population": snakemake.input["male_pop"],
            "children_under5_population": (
                snakemake.input["children_under5_pop"]
            ),
            "school_age_5_14_population": (
                snakemake.input["school_age_5_14_pop"]
            ),
            "working_age_15_64_population": (
                snakemake.input["working_age_15_64_pop"]
            ),
            "female_15_49_population": (
                snakemake.input["female_15_49_pop"]
            ),
            "older_65plus_population": (
                snakemake.input["older_65plus_pop"]
            ),
        }
        output_path: str = snakemake.output["population_summary"]
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
    f"Calculating population demographic summaries for {country} at admin "
    f"level {admin_level}."
)

logging.info("Creating output directories (if they don't already exist).")
out_dir = os.path.dirname(output_path)
os.makedirs(out_dir, exist_ok=True)


logging.info("Reading population demographic rasters.")

population_layers = {}
raster_shape = None
raster_transform = None
raster_crs = None

for population_name, population_path in population_paths.items():
    with rasterio.open(population_path) as src:
        population = (
            src.read(1, masked=True).astype("float64").filled(np.nan)
        )

        if raster_shape is None:
            raster_shape = src.shape
            raster_transform = src.transform
            raster_crs = src.crs
        else:
            if src.shape != raster_shape:
                raise ValueError(
                    f"{population_name} raster does not match the total "
                    "population raster shape."
                )
            if src.transform != raster_transform:
                raise ValueError(
                    f"{population_name} raster does not match the total "
                    "population raster transform."
                )
            if src.crs != raster_crs:
                raise ValueError(
                    f"{population_name} raster does not match the total "
                    "population raster CRS."
                )

    population_layers[population_name] = np.where(
        np.isfinite(population) & (population >= 0),
        population,
        0
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


logging.info("Rasterising admin boundaries to the population grid.")

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

flat_region_ids = region_ids.ravel()
valid_region_mask = flat_region_ids >= 0
flat_region_ids = flat_region_ids[valid_region_mask]


logging.info("Summing population demographic groups by admin region.")

results_gdf = admin_areas.copy()
results_gdf["ISO3"] = country
results_gdf["admin_level"] = layer_name

for population_name, population in population_layers.items():
    population_totals = np.bincount(
        flat_region_ids,
        weights=population.ravel()[valid_region_mask],
        minlength=len(admin_areas)
    )
    results_gdf[population_name] = population_totals


logging.info("Writing population demographic summary to GeoPackage.")

results_gdf.to_file(output_path, driver="GPKG")

logging.info("Done.")
