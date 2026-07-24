"""
This script calculates the wealth quintile population totals for each subnational administrative region.
"""

import logging
import sys
import glob
import os

import numpy as np
import rasterio
from tqdm import tqdm
from rasterio.features import geometry_mask, rasterize
from rasterio.mask import mask
import geopandas as gpd
from collections import Counter
from pyproj import Geod
from shapely.geometry import LineString, MultiLineString

if __name__ == "__main__":
    try:
        admin_path: str = snakemake.input["admin_areas"]
        pop_path: str = snakemake.input["pop_file"]
        wealth_path: str = snakemake.input["wealth_quintiles"]
        output_path: str = snakemake.output["admin_summary"]
        country: str = snakemake.wildcards["ISO3"]
        administrative_level: int = snakemake.wildcards.ADMIN_SLUG
    except:
        raise ValueError("Must be run via snakemake.")

logging.basicConfig(format="%(asctime)s %(process)d %(filename)s %(message)s", level=logging.INFO)

# Update notation for GADM
admin_level = int(administrative_level.replace("ADM", ""))

logging.info(f"Calculating the the pop wealth quintiles at admin Level {admin_level} for {country}.")

logging.info("Creating output directories (if they don't already exist)")
out_dir = os.path.dirname(output_path)
os.makedirs(out_dir, exist_ok=True)

logging.info("Load files.")
with rasterio.open(pop_path) as pop_src, rasterio.open(wealth_path) as rwi_src:
    pop = pop_src.read(1)
    wealth = rwi_src.read(1)
    profile = pop_src.profile.copy()
    affine = pop_src.transform

logging.info(f"Reading level {administrative_level} admin boundaries")
layer_name = f"ADM{admin_level}"
admin_areas: gpd.GeoDataFrame = gpd.read_file(admin_path, layer=layer_name)
admin_areas = admin_areas.reset_index(drop=True)
if layer_name == "ADM0":  
    # 🔧 Ensure one feature per country
    admin_areas = admin_areas.dissolve(by="shapeName", as_index=False)
    area_unique_id_col = "shapeName"
else:
    area_unique_id_col = "shapeID"
    admin_areas = admin_areas[[area_unique_id_col, "shapeName", "geometry"]].copy()
logging.info(f"There are {len(admin_areas)} admin areas to analyze.")

# OPTIMIZATION: vectorize geometry masking
# Create a single raster where each pixel contains the region ID it belongs to
region_ids = rasterize(
    [(geom, i) for i, geom in enumerate(admin_areas.geometry)],
    out_shape=pop.shape,
    transform=affine,
    fill=-1,  # -1 for pixels not in any region
    dtype=np.int32
)

logging.info("Looping over admin regions and calculating dry-proofing costs.")
results = [] # List for collecting results
 # Loop over each admin region
for i, region in tqdm(admin_areas.iterrows(), total=len(admin_areas)):
    # Create boolean mask for this specific region
    region_mask = (region_ids == i)
    
    if not np.any(region_mask):  # Skip if no valid pixels in this region
        results.append({
            area_unique_id_col: region[area_unique_id_col],
            "shapeName": region["shapeName"],
            "area_dry-proofed": 0.0,
            "average_unit_cost": np.nan,
            "max_unit_cost": np.nan,
            "std_unit_cost": np.nan,
            "sum_res_capstock": np.nan,
            "geometry": region["geometry"]
        })
        continue

    # Calculate quintile totals for the region
    q1_total = np.nansum(pop[region_mask][wealth[region_mask] == 1])
    q2_total = np.nansum(pop[region_mask][wealth[region_mask] == 2])
    q3_total = np.nansum(pop[region_mask][wealth[region_mask] == 3])
    q4_total = np.nansum(pop[region_mask][wealth[region_mask] == 4])
    q5_total = np.nansum(pop[region_mask][wealth[region_mask] == 5])
    

    # Append risk metrics to results list
    if layer_name == "ADM0":
        results.append({
         area_unique_id_col: region[area_unique_id_col],
         "q1_total": q1_total,
         "q2_total": q2_total,
         "q3_total": q3_total,
         "q4_total": q4_total,
         "q5_total": q5_total,
         "geometry": region["geometry"]
         })
    else:
        results.append({
            area_unique_id_col: region[area_unique_id_col],
            "shapeName": region["shapeName"],
            "q1_total": q1_total,
            "q2_total": q2_total,
            "q3_total": q3_total,
            "q4_total": q4_total,
            "q5_total": q5_total,
            "geometry": region["geometry"]
        })

logging.info("Writing reults to GeoPackage.")
results_gdf = gpd.GeoDataFrame(results, geometry="geometry")
results_gdf.to_file(output_path, driver="GPKG")

logging.info("Done.")