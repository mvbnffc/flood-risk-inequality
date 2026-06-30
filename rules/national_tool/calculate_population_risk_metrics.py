"""
This script calculates population flood-risk metrics for a country and sums them per admin region.

It calculates exposed population for:
- all binary RP exposure maps;
- binary AAR exposure maps, protected and unprotected;
- all population demographic layers;
- each wealth quintile, using the total population raster and wealth quintile raster.

The output is a long-format GeoPackage with one row per:

    admin region x risk map x population group
"""

import logging
import os

import rasterio
from rasterio.features import rasterize
import pandas as pd
import geopandas as gpd
import numpy as np


if __name__ == "__main__":

    try:
        admin_path: str = snakemake.input["admin_areas"]

        RP10_path: str = snakemake.input["RP10_file"]
        RP20_path: str = snakemake.input["RP20_file"]
        RP50_path: str = snakemake.input["RP50_file"]
        RP75_path: str = snakemake.input["RP75_file"]
        RP100_path: str = snakemake.input["RP100_file"]
        RP200_path: str = snakemake.input["RP200_file"]
        RP500_path: str = snakemake.input["RP500_file"]
        AAR_path: str = snakemake.input["AAR_file"]
        AAR_protected_path: str = snakemake.input["AAR_protected_file"]

        total_pop_path: str = snakemake.input["total_pop"]
        female_pop_path: str = snakemake.input["female_pop"]
        male_pop_path: str = snakemake.input["male_pop"]
        children_under5_pop_path: str = snakemake.input["children_under5_pop"]
        school_age_5_14_pop_path: str = snakemake.input["school_age_5_14_pop"]
        working_age_15_64_pop_path: str = snakemake.input["working_age_15_64_pop"]
        female_15_49_pop_path: str = snakemake.input["female_15_49_pop"]
        older_65plus_pop_path: str = snakemake.input["older_65plus_pop"]

        wealth_quintiles_path: str = snakemake.input["wealth_quintiles"]
        mask_path: str = snakemake.input["mask_file"]

        output_path: str = snakemake.output["regional_population_risk"]

        administrative_level: str = snakemake.wildcards.ADMIN_SLUG
        country: str = snakemake.wildcards.ISO3

    except NameError:
        raise ValueError("Must be run via snakemake.")


logging.basicConfig(format="%(asctime)s %(process)d %(filename)s %(message)s", level=logging.INFO)

# Update notation for GADM / GeoBoundaries
admin_level = int(administrative_level.replace("ADM", ""))

logging.info(f"Calculating population risk metrics for {country} at admin level {admin_level}.")


logging.info("Reading raster data.")

with rasterio.open(RP10_path) as RP10_src:
    affine = RP10_src.transform
    raster_crs = RP10_src.crs
    raster_shape = RP10_src.shape

    RP10 = RP10_src.read(1, masked=True).astype("float64").filled(np.nan)

with rasterio.open(RP20_path) as RP20_src:
    RP20 = RP20_src.read(1, masked=True).astype("float64").filled(np.nan)

with rasterio.open(RP50_path) as RP50_src:
    RP50 = RP50_src.read(1, masked=True).astype("float64").filled(np.nan)

with rasterio.open(RP75_path) as RP75_src:
    RP75 = RP75_src.read(1, masked=True).astype("float64").filled(np.nan)

with rasterio.open(RP100_path) as RP100_src:
    RP100 = RP100_src.read(1, masked=True).astype("float64").filled(np.nan)

with rasterio.open(RP200_path) as RP200_src:
    RP200 = RP200_src.read(1, masked=True).astype("float64").filled(np.nan)

with rasterio.open(RP500_path) as RP500_src:
    RP500 = RP500_src.read(1, masked=True).astype("float64").filled(np.nan)

with rasterio.open(AAR_path) as AAR_src:
    AAR = AAR_src.read(1, masked=True).astype("float64").filled(np.nan)

with rasterio.open(AAR_protected_path) as AAR_protected_src:
    AAR_protected = AAR_protected_src.read(1, masked=True).astype("float64").filled(np.nan)

with rasterio.open(total_pop_path) as total_pop_src:
    total_pop = total_pop_src.read(1, masked=True).astype("float64").filled(np.nan)

with rasterio.open(female_pop_path) as female_pop_src:
    female_pop = female_pop_src.read(1, masked=True).astype("float64").filled(np.nan)

with rasterio.open(male_pop_path) as male_pop_src:
    male_pop = male_pop_src.read(1, masked=True).astype("float64").filled(np.nan)

with rasterio.open(children_under5_pop_path) as children_under5_pop_src:
    children_under5_pop = children_under5_pop_src.read(1, masked=True).astype("float64").filled(np.nan)

with rasterio.open(school_age_5_14_pop_path) as school_age_5_14_pop_src:
    school_age_5_14_pop = school_age_5_14_pop_src.read(1, masked=True).astype("float64").filled(np.nan)

with rasterio.open(working_age_15_64_pop_path) as working_age_15_64_pop_src:
    working_age_15_64_pop = working_age_15_64_pop_src.read(1, masked=True).astype("float64").filled(np.nan)

with rasterio.open(female_15_49_pop_path) as female_15_49_pop_src:
    female_15_49_pop = female_15_49_pop_src.read(1, masked=True).astype("float64").filled(np.nan)

with rasterio.open(older_65plus_pop_path) as older_65plus_pop_src:
    older_65plus_pop = older_65plus_pop_src.read(1, masked=True).astype("float64").filled(np.nan)

with rasterio.open(wealth_quintiles_path) as wealth_quintiles_src:
    wealth_quintiles = wealth_quintiles_src.read(1, masked=True).astype("float64").filled(np.nan)

with rasterio.open(mask_path) as mask_src:
    water_mask = mask_src.read(1, masked=True).astype("float64").filled(np.nan)


logging.info("Pre-computing masks.")

# Boolean mask instead of NaN.
# Matches the convention in the capital-stock script:
# water occurrence > 50 is excluded.
water_mask = np.where(water_mask > 50, False, True)

# Remove negative population values, if any exist.
total_pop = np.where(total_pop < 0, np.nan, total_pop)
female_pop = np.where(female_pop < 0, np.nan, female_pop)
male_pop = np.where(male_pop < 0, np.nan, male_pop)
children_under5_pop = np.where(children_under5_pop < 0, np.nan, children_under5_pop)
school_age_5_14_pop = np.where(school_age_5_14_pop < 0, np.nan, school_age_5_14_pop)
working_age_15_64_pop = np.where(working_age_15_64_pop < 0, np.nan, working_age_15_64_pop)
female_15_49_pop = np.where(female_15_49_pop < 0, np.nan, female_15_49_pop)
older_65plus_pop = np.where(older_65plus_pop < 0, np.nan, older_65plus_pop)

# Wealth quintiles should be integer values 1 to 5.
wealth_quintiles = np.rint(wealth_quintiles)


logging.info(f"Reading level {administrative_level} admin boundaries.")

layer_name = f"ADM{admin_level}"
admin_areas: gpd.GeoDataFrame = gpd.read_file(admin_path, layer=layer_name)

if admin_areas.crs != raster_crs:
    logging.info("Reprojecting admin boundaries to match raster CRS.")
    admin_areas = admin_areas.to_crs(raster_crs)

if layer_name == "ADM0":
    area_unique_id_col = "shapeName"
    admin_areas = admin_areas[[area_unique_id_col, "geometry"]]
else:
    area_unique_id_col = "shapeID"
    admin_areas = admin_areas[[area_unique_id_col, "shapeName", "geometry"]]

logging.info(f"There are {len(admin_areas)} admin areas to analyze.")


# Create a single raster where each pixel contains the region ID it belongs to.
region_ids = rasterize(
    [(geom, idx) for idx, geom in enumerate(admin_areas.geometry)],
    out_shape=raster_shape,
    transform=affine,
    fill=-1,
    dtype=np.int32
)


logging.info("Preparing risk maps and population layers.")

risk_maps = {
    "RP10": RP10,
    "RP20": RP20,
    "RP50": RP50,
    "RP75": RP75,
    "RP100": RP100,
    "RP200": RP200,
    "RP500": RP500,
    "AAR": AAR,
    "AAR_protected": AAR_protected,
}

population_layers = {
    "total": total_pop,
    "female": female_pop,
    "male": male_pop,
    "children_under5": children_under5_pop,
    "school_age_5_14": school_age_5_14_pop,
    "working_age_15_64": working_age_15_64_pop,
    "female_15_49": female_15_49_pop,
    "older_65plus": older_65plus_pop,
}


logging.info("Calculating population risk metrics across admin regions.")

results = []

# Flatten region IDs once.
flat_region_ids = region_ids.flatten()

# Filter pixels that fall inside an admin region.
valid_region_mask = flat_region_ids >= 0
flat_region_ids_valid = flat_region_ids[valid_region_mask]

for risk_name, risk_arr in risk_maps.items():

    logging.info(f"Processing risk map: {risk_name}")

    # Binary exposure map:
    # any value > 0 is treated as exposed.
    exposed_mask = risk_arr > 0
    risk_valid_mask = ~np.isnan(risk_arr)

    for pop_name, pop_arr in population_layers.items():

        logging.info(f"Processing population layer: {pop_name}")

        # Pre-compute global validity mask.
        global_valid_mask = (
            risk_valid_mask &
            ~np.isnan(pop_arr) &
            water_mask
        )

        total_pop_arr = pop_arr.copy()
        exposed_pop_arr = np.where(exposed_mask, pop_arr, 0)

        # Set invalid areas to 0 for faster summing.
        total_pop_arr[~global_valid_mask] = 0
        exposed_pop_arr[~global_valid_mask] = 0

        total_pixel_arr = global_valid_mask.astype(np.float64)
        exposed_pixel_arr = (global_valid_mask & exposed_mask).astype(np.float64)

        # Flatten arrays.
        flat_total_pop = total_pop_arr.flatten()
        flat_exposed_pop = exposed_pop_arr.flatten()
        flat_total_pixels = total_pixel_arr.flatten()
        flat_exposed_pixels = exposed_pixel_arr.flatten()

        # Filter valid regions.
        flat_total_pop = flat_total_pop[valid_region_mask]
        flat_exposed_pop = flat_exposed_pop[valid_region_mask]
        flat_total_pixels = flat_total_pixels[valid_region_mask]
        flat_exposed_pixels = flat_exposed_pixels[valid_region_mask]

        # Sum by region using numpy's bincount.
        total_population = np.bincount(
            flat_region_ids_valid,
            weights=flat_total_pop,
            minlength=len(admin_areas)
        )

        exposed_population = np.bincount(
            flat_region_ids_valid,
            weights=flat_exposed_pop,
            minlength=len(admin_areas)
        )

        total_pixels = np.bincount(
            flat_region_ids_valid,
            weights=flat_total_pixels,
            minlength=len(admin_areas)
        )

        exposed_pixels = np.bincount(
            flat_region_ids_valid,
            weights=flat_exposed_pixels,
            minlength=len(admin_areas)
        )

        unexposed_population = total_population - exposed_population

        population_exposure_share = np.divide(
            exposed_population,
            total_population,
            out=np.zeros_like(exposed_population, dtype=np.float64),
            where=total_population > 0
        )

        pixel_exposure_share = np.divide(
            exposed_pixels,
            total_pixels,
            out=np.zeros_like(exposed_pixels, dtype=np.float64),
            where=total_pixels > 0
        )

        results_gdf = admin_areas.copy()
        results_gdf["ISO3"] = country
        results_gdf["admin_level"] = layer_name
        results_gdf["risk_map"] = risk_name
        results_gdf["population_group"] = pop_name
        results_gdf["population_group_type"] = "demographic"
        results_gdf["total_population"] = total_population
        results_gdf["exposed_population"] = exposed_population
        results_gdf["unexposed_population"] = unexposed_population
        results_gdf["population_exposure_share"] = population_exposure_share
        results_gdf["total_pixels"] = total_pixels
        results_gdf["exposed_pixels"] = exposed_pixels
        results_gdf["pixel_exposure_share"] = pixel_exposure_share

        results.append(results_gdf)

    logging.info("Processing wealth quintiles.")

    for quintile in [1, 2, 3, 4, 5]:

        pop_name = f"wealth_q{quintile}"

        logging.info(f"Processing wealth quintile: {quintile}")

        quintile_mask = (
            ~np.isnan(total_pop) &
            ~np.isnan(wealth_quintiles) &
            (wealth_quintiles == quintile)
        )

        wealth_pop_arr = np.where(quintile_mask, total_pop, 0)

        # Pre-compute global validity mask.
        global_valid_mask = (
            risk_valid_mask &
            quintile_mask &
            water_mask
        )

        total_pop_arr = wealth_pop_arr.copy()
        exposed_pop_arr = np.where(exposed_mask, wealth_pop_arr, 0)

        # Set invalid areas to 0 for faster summing.
        total_pop_arr[~global_valid_mask] = 0
        exposed_pop_arr[~global_valid_mask] = 0

        total_pixel_arr = global_valid_mask.astype(np.float64)
        exposed_pixel_arr = (global_valid_mask & exposed_mask).astype(np.float64)

        # Flatten arrays.
        flat_total_pop = total_pop_arr.flatten()
        flat_exposed_pop = exposed_pop_arr.flatten()
        flat_total_pixels = total_pixel_arr.flatten()
        flat_exposed_pixels = exposed_pixel_arr.flatten()

        # Filter valid regions.
        flat_total_pop = flat_total_pop[valid_region_mask]
        flat_exposed_pop = flat_exposed_pop[valid_region_mask]
        flat_total_pixels = flat_total_pixels[valid_region_mask]
        flat_exposed_pixels = flat_exposed_pixels[valid_region_mask]

        # Sum by region using numpy's bincount.
        total_population = np.bincount(
            flat_region_ids_valid,
            weights=flat_total_pop,
            minlength=len(admin_areas)
        )

        exposed_population = np.bincount(
            flat_region_ids_valid,
            weights=flat_exposed_pop,
            minlength=len(admin_areas)
        )

        total_pixels = np.bincount(
            flat_region_ids_valid,
            weights=flat_total_pixels,
            minlength=len(admin_areas)
        )

        exposed_pixels = np.bincount(
            flat_region_ids_valid,
            weights=flat_exposed_pixels,
            minlength=len(admin_areas)
        )

        unexposed_population = total_population - exposed_population

        population_exposure_share = np.divide(
            exposed_population,
            total_population,
            out=np.zeros_like(exposed_population, dtype=np.float64),
            where=total_population > 0
        )

        pixel_exposure_share = np.divide(
            exposed_pixels,
            total_pixels,
            out=np.zeros_like(exposed_pixels, dtype=np.float64),
            where=total_pixels > 0
        )

        results_gdf = admin_areas.copy()
        results_gdf["ISO3"] = country
        results_gdf["admin_level"] = layer_name
        results_gdf["risk_map"] = risk_name
        results_gdf["population_group"] = pop_name
        results_gdf["population_group_type"] = "wealth_quintile"
        results_gdf["total_population"] = total_population
        results_gdf["exposed_population"] = exposed_population
        results_gdf["unexposed_population"] = unexposed_population
        results_gdf["population_exposure_share"] = population_exposure_share
        results_gdf["total_pixels"] = total_pixels
        results_gdf["exposed_pixels"] = exposed_pixels
        results_gdf["pixel_exposure_share"] = pixel_exposure_share

        results.append(results_gdf)


logging.info("Writing results to GeoPackage.")

final_results_gdf = gpd.GeoDataFrame(
    pd.concat(results, ignore_index=True),
    geometry="geometry",
    crs=admin_areas.crs
)

os.makedirs(os.path.dirname(output_path), exist_ok=True)

if os.path.exists(output_path):
    os.remove(output_path)

final_results_gdf.to_file(output_path, driver="GPKG")

logging.info("Done.")