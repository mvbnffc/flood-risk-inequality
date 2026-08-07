"""
Calculate a flood risk concentration curve by ranking populated grid cells
from lowest to highest relative wealth.

The full-resolution concentration curve is calculated from the input rasters and
then interpolated to fixed cumulative population intervals for output to CSV.
"""

import logging

import rasterio
import numpy as np
import pandas as pd


if __name__ == "__main__":

    try:
        pop_path: str = snakemake.input["pop_file"]
        rwi_path: str = snakemake.input["rwi_file"]
        flood_path: str = snakemake.input["flood_file"]
        mask_path: str = snakemake.input["surface_water"]
        output_path: str = snakemake.output["curve"]
        n_points: int = snakemake.params["n_points"]

    except NameError:
        raise ValueError("Must be run via snakemake.")

    logging.basicConfig(
        format="%(asctime)s %(process)d %(filename)s %(message)s",
        level=logging.INFO,
    )

    logging.info("Calculating flood risk concentration curve.")

    # -------------------------------------------------------------------------
    # Read raster data
    # -------------------------------------------------------------------------

    logging.info("Reading raster data.")

    with rasterio.open(pop_path) as src:
        pop = src.read(1).astype(float)
        pop_meta = src.meta
        pop_transform = src.transform
        pop_crs = src.crs
        pop_nodata = src.nodata

    with rasterio.open(rwi_path) as src:
        rwi = src.read(1).astype(float)
        rwi_transform = src.transform
        rwi_crs = src.crs
        rwi_nodata = src.nodata

    with rasterio.open(flood_path) as src:
        flood = src.read(1).astype(float)
        flood_transform = src.transform
        flood_crs = src.crs
        flood_nodata = src.nodata

    with rasterio.open(mask_path) as src:
        surface_water = src.read(1).astype(float)
        mask_transform = src.transform
        mask_crs = src.crs
        mask_nodata = src.nodata

    # -------------------------------------------------------------------------
    # Check raster alignment
    # -------------------------------------------------------------------------

    logging.info("Checking raster alignment.")

    if not (
        pop.shape == rwi.shape == flood.shape == surface_water.shape
        and pop_transform == rwi_transform == flood_transform == mask_transform
        and pop_crs == rwi_crs == flood_crs == mask_crs
    ):
        raise ValueError("Input rasters are not aligned.")

    # -------------------------------------------------------------------------
    # Convert nodata to NaN
    # -------------------------------------------------------------------------

    logging.info("Masking nodata values.")

    if pop_nodata is not None:
        pop[pop == pop_nodata] = np.nan

    if rwi_nodata is not None:
        rwi[rwi == rwi_nodata] = np.nan

    if flood_nodata is not None:
        flood[flood == flood_nodata] = np.nan

    if mask_nodata is not None:
        surface_water[surface_water == mask_nodata] = np.nan

    # Retain your existing explicit handling of RWI nodata if needed
    rwi[rwi == -999] = np.nan

    # -------------------------------------------------------------------------
    # Mask invalid cells
    # -------------------------------------------------------------------------

    logging.info("Masking permanent surface water and invalid grid cells.")

    valid = (
        np.isfinite(pop)
        & np.isfinite(rwi)
        & np.isfinite(flood)
        & np.isfinite(surface_water)
        & (surface_water <= 50)
        & (pop > 0)
    )

    pop = pop[valid]
    rwi = rwi[valid]
    flood = flood[valid]

    if len(pop) == 0:
        raise ValueError("No valid populated grid cells remain after masking.")

    logging.info(f"Using {len(pop):,} populated grid cells.")

    # -------------------------------------------------------------------------
    # Calculate concentration curve
    # -------------------------------------------------------------------------

    logging.info("Calculating concentration curve.")

    # Sort population from lowest to highest relative wealth
    order = np.argsort(rwi)

    pop = pop[order]
    flood = flood[order]

    # Calculate flood-exposed population
    flood_pop = flood * pop

    total_pop = np.sum(pop)
    total_flood_pop = np.sum(flood_pop)

    if total_flood_pop <= 0:
        raise ValueError("No flood-exposed population found.")

    # Calculate cumulative population and flood exposure
    cum_pop = np.cumsum(pop)
    cum_flood_pop = np.cumsum(flood_pop)

    frac_pop = cum_pop / total_pop
    frac_flood = cum_flood_pop / total_flood_pop

    # Add (0, 0) to start of concentration curve
    frac_pop = np.insert(frac_pop, 0, 0)
    frac_flood = np.insert(frac_flood, 0, 0)

    # -------------------------------------------------------------------------
    # Interpolate concentration curve
    # -------------------------------------------------------------------------

    logging.info(
        f"Interpolating concentration curve to {n_points} output points."
    )

    x = np.linspace(0, 1, n_points)
    y = np.interp(x, frac_pop, frac_flood)

    # Ensure exact concentration curve endpoints
    x[0] = 0
    y[0] = 0

    x[-1] = 1
    y[-1] = 1

    # -------------------------------------------------------------------------
    # Write output
    # -------------------------------------------------------------------------

    logging.info("Writing concentration curve CSV.")

    output_df = pd.DataFrame(
        {
            "frac_pop": x,
            "frac_flood": y,
        }
    )

    output_df.to_csv(output_path, index=False)

    logging.info("Done.")