"""
This script calculates inequality metrics (concentration index and quantile ratio)
and flood risk metrics at a given administrative level. Quantile metrics use the
shared national population-weighted wealth-quintile classification.

Note: now using geoboundaries rather than GADM for admin boundaries.
"""

import logging

import rasterio
from rasterio.features import geometry_mask
import pandas as pd
import geopandas as gpd
import numpy as np
import shapely
from tqdm import tqdm

if __name__ == "__main__":

    try:
        admin_path: str = snakemake.input["admin_areas"]
        social_path: str = snakemake.input["social_file"]
        wealth_quintiles_path: str = snakemake.input["wealth_quintiles"]
        pop_path: str = snakemake.input["pop_file"]
        mask_path: str = snakemake.input["mask_file"]
        risk_path: str = snakemake.input["risk_file"]
        output_path: str = snakemake.output["regional_CI"]
        administrative_level: int = snakemake.wildcards.ADMIN_SLUG
        model: str = snakemake.wildcards.MODEL
        social_name: str = snakemake.wildcards.SOCIAL
    except NameError:
        raise ValueError("Must be run via snakemake.")
    
logging.basicConfig(format="%(asctime)s %(process)d %(filename)s %(message)s", level=logging.INFO)

# Update notation for GADM
admin_level = int(administrative_level.replace("ADM", ""))

logging.info(f"Calculating concentration indices at admin level {admin_level}.")

logging.info("Reading raster data.")
with rasterio.open(social_path) as social_src, rasterio.open(pop_path) as pop_src, \
     rasterio.open(mask_path) as mask_src, rasterio.open(risk_path) as risk_src, \
     rasterio.open(wealth_quintiles_path) as wealth_quintiles_src:
    raster_sources = {
        "social": social_src,
        "population": pop_src,
        "surface water": mask_src,
        "wealth quintiles": wealth_quintiles_src,
    }
    for raster_name, raster_src in raster_sources.items():
        if (
            raster_src.shape != risk_src.shape
            or raster_src.transform != risk_src.transform
            or raster_src.crs != risk_src.crs
        ):
            raise ValueError(
                f"{raster_name} raster does not align with the risk raster."
            )

    social = social_src.read(1)
    wealth_quintiles = wealth_quintiles_src.read(1)
    pop = pop_src.read(1)
    water_mask = mask_src.read(1)
    risk = risk_src.read(1)
    affine = risk_src.transform 

if social_name == "rwi":
    social[social==-999] = np.nan # convert -999 in RWI dataset to NaN
# Create the water mask
water_mask = np.where(water_mask>50, np.nan, 1) # WARNING WE ARE HARD CODING PERM_WATER > 50% mask here

logging.info(f"Reading level {administrative_level} admin boundaries")
layer_name = f"ADM{admin_level}"
admin_areas: gpd.GeoDataFrame = gpd.read_file(admin_path, layer=layer_name)
if layer_name == "ADM0":  
    # 🔧 Ensure one feature per country
    admin_areas = admin_areas.dissolve(by="shapeName", as_index=False)
    area_unique_id_col = "shapeName"
else:
    area_unique_id_col = "shapeID"
    admin_areas = admin_areas[[area_unique_id_col, "shapeName", "geometry"]].copy()
logging.info(f"There are {len(admin_areas)} admin areas to analyze.")


logging.info("Looping over admin regions and calculating concentration indices")
results = [] # List for collecting results
 # Loop over each admin region
for idx, region in tqdm(admin_areas.iterrows()):
    # Get the geometry for the current admin region
    geom = region["geometry"].__geo_interface__
    # Create a mask from the geometry
    mask_array = geometry_mask([geom],
                                transform=affine,
                                invert=True,
                                out_shape=social.shape)
    # Use the mask to clip each raster by setting values outside the region to nan
    social_clip = np.where(mask_array, social, np.nan)
    pop_clip = np.where(mask_array, pop, np.nan)
    risk_clip = np.where(mask_array, risk, np.nan)
    water_mask_clip = np.where(mask_array, water_mask, np.nan)
    wealth_quintiles_clip = np.where(mask_array, wealth_quintiles, 0)
    
    # Mask out areas where not all rasters are valid
    mask = (
        ~np.isnan(pop_clip) &
        ~np.isnan(social_clip) &
        ~np.isnan(risk_clip) &
        ~np.isnan(water_mask_clip) &
        np.isin(wealth_quintiles_clip, [1, 2, 3, 4, 5])
    )
    # Flatten data
    pop_flat = pop_clip[mask]
    social_flat = social_clip[mask]
    risk_flat = risk_clip[mask]
    wealth_quintiles_flat = wealth_quintiles_clip[mask]
    # Mask out zero-populatoin cells
    valid = pop_flat > 0
    pop_flat = pop_flat[valid]
    social_flat = social_flat[valid]
    risk_flat = risk_flat[valid]
    wealth_quintiles_flat = wealth_quintiles_flat[valid]

    # Calculate total flood risk (pop * risk) for the region
    total_flood_risk = np.nansum(pop_flat * risk_flat)

    # Prepare dataframe for metric calculation
    df = pd.DataFrame({
        'pop': pop_flat,
        'social': social_flat,
        'flood': risk_flat,
        'wealth_quintile': wealth_quintiles_flat,
    })

    # Define function
    def calculate_CI(df):
        # Sort dataframe by wealth
        df = df.sort_values(by="social", ascending=True)
        # Calculate cumulative population rank (to represent distribution of people)
        df['cum_pop'] = df['pop'].cumsum()
        # Calculate total pop of sample
        total_pop = df['pop'].sum()
        if total_pop == 0:
            return np.nan
        # Calculate fractional rank of each row
        df['rank'] = (df['cum_pop'] - 0.5*df['pop']) / total_pop
        try:
            # Calcualte weighted mean of flood risk
            weighted_mean_flood = np.average(df['flood'], weights=df['pop'])
        except ZeroDivisionError:
            return np.nan
        if weighted_mean_flood == 0:
            return np.nan
        # Calculate weighted sum of (flood * rank * pop)
        sum_xR = (df['flood'] * df['rank'] * df['pop']).sum()
        # Calculate Concentration Index
        CI = (2 * sum_xR) / (df['pop'].sum() * weighted_mean_flood) - 1
        return CI

    CI = calculate_CI(df)
    
    def calculate_quantile_ratio(df):
        """Calculate the national Q5:Q1 population-weighted exposure ratio."""
        bottom_df = df[df["wealth_quintile"] == 1]
        top_df = df[df["wealth_quintile"] == 5]

        if bottom_df.empty or top_df.empty:
            return np.nan

        bottom_weighted_avg = np.average(
            bottom_df["flood"],
            weights=bottom_df["pop"]
        )
        top_weighted_avg = np.average(
            top_df["flood"],
            weights=top_df["pop"]
        )

        return (
            top_weighted_avg / bottom_weighted_avg
            if bottom_weighted_avg != 0
            else np.nan
        )
    
    QR = calculate_quantile_ratio(df)

    def calculate_flood_risk_per_quantile(df):
        """Calculate flood risk using the shared national quintile labels."""
        if df.empty or df["pop"].sum() == 0:
            logging.warning("Total pop is ZERO - returning NaN risk.")
            return np.nan, np.nan, np.nan, np.nan, np.nan

        return tuple(
            np.sum(
                df.loc[df["wealth_quintile"] == quintile, "pop"]
                * df.loc[df["wealth_quintile"] == quintile, "flood"]
            )
            for quintile in [1, 2, 3, 4, 5]
        )
    
    Q1_risk, Q2_risk, Q3_risk, Q4_risk, Q5_risk = calculate_flood_risk_per_quantile(df)

    # Calculate the number of cells where population and rwi overlaps
    total_pop = np.nansum(pop_clip)
    pop_social = np.nansum(np.where(~np.isnan(social_clip), pop_clip, 0))

    results.append({
        area_unique_id_col: region[area_unique_id_col],
        "shapeName": region["shapeName"],
        "CI": CI,
        "QR": QR,
        "Population": total_pop,
        "Population Coverage (%)": (pop_social/total_pop)*100,
        "Total Flood Risk": total_flood_risk,
        "Q1 Flood Risk": Q1_risk,
        "Q2 Flood Risk": Q2_risk,
        "Q3 Flood Risk": Q3_risk,
        "Q4 Flood Risk": Q4_risk,
        "Q5 Flood Risk": Q5_risk,
        "geometry": region["geometry"]
    })

# Debug
if administrative_level == "ADM0":
    print("National CI is:", float(CI))

logging.info("Writing reults to GeoPackage.")
results_gdf = gpd.GeoDataFrame(results, geometry="geometry")
results_gdf.to_file(output_path, driver="GPKG")

logging.info("Done.")
