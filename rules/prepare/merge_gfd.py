"""
Script for creating a merged raster of the Google historical inundation datasets

Raw data comes in km^2 GeoJSON tiles classfied as high, medium, and low risk:
    High: wet at least 5% of the time
    Medium: wet at least 1% of the time
    Low: wet at least 0.5% of the time

This script merges the GeoJSONs into one global (km^2 resolution) GeoTiff with cell values
corresponding to the probability of flooding in each grid cell (high=0.05, medium=0.01, low=0.005)
"""

import logging
import glob
import os

import numpy as np
import rasterio
from tqdm import tqdm

if __name__ == "__main__":
    try:
        inland_input_path: str = snakemake.input["merge_inland_gfd_folder"]
        coastal_input_path: str = snakemake.input["merge_coastal_gfd_folder"]
        inland_output_path: str = snakemake.output["merge_inland_gfd_file"]
        coastal_output_path: str = snakemake.output["merge_coastal_gfd_file"]
    except:
        raise ValueError("Must be run via snakemake.")
    
# Set some analysis parameters
raster_resolution = 0.002245788210298803843 # degrees

logging.basicConfig(format="%(asctime)s %(process)d %(filename)s %(message)s", level=logging.INFO)

logging.info(f"Merging Global Flood Database files into global raster.")

#### Define functions for the analysis #####################
def get_global_extent(files):
    """Calculate the combined extent of all rasters."""
    min_left, min_bottom, max_right, max_top = float('inf'), float('inf'), float('-inf'), float('-inf')
    for file in files:
        with rasterio.open(file) as src:
            bounds = src.bounds
            min_left = min(min_left, bounds.left)
            min_bottom = min(min_bottom, bounds.bottom)
            max_right = max(max_right, bounds.right)
            max_top = max(max_top, bounds.top)
    return (min_left, min_bottom, max_right, max_top)

def calculate_offsets(raster_bounds, global_extent, transform):
    """Calculate the row and column offsets for the raster within the global raster."""
    # row_offset = int((raster_bounds.top - global_extent[3]) / -transform[4]) OLD DEBUG
    # col_offset = int((raster_bounds.left - global_extent[0]) / transform[0]) OLD DEBUG
    row_offset = round((raster_bounds.top - global_extent[3]) / -transform[4]) # NEW DEBUG
    col_offset = round((raster_bounds.left - global_extent[0]) / transform[0]) # NEW DEBUG
    return row_offset, col_offset

def pad_and_add_raster(src, global_raster, row_offset, col_offset, global_extent, transform):
    raster_array = src.read(1, out_dtype=np.int16)

    # Calculate the necessary padding
    top_padding = -row_offset
    left_padding = col_offset
    bottom_padding = max(global_raster.shape[0] - (raster_array.shape[0] + top_padding), 0)
    right_padding = max(global_raster.shape[1] - (raster_array.shape[1] + left_padding), 0)

    # Pad the raster array
    padded_raster = np.pad(
        raster_array,
        ((top_padding, bottom_padding), (left_padding, right_padding)),
        'constant',
        constant_values=(0, 0)  # Assuming 0 is the no-data value
    )

    # Add the padded raster to the global raster
    global_raster += padded_raster

###########################################################

logging.info("Reading raster file names.")
inland_raster_files = glob.glob(os.path.join(inland_input_path, "*.tif"))
coastal_raster_files = glob.glob(os.path.join(coastal_input_path, "*.tif"))

logging.info("Calculate global extents.")
inland_global_extent = get_global_extent(inland_raster_files)
inland_global_width = int((inland_global_extent[2] - inland_global_extent[0]) / raster_resolution)
inland_global_height = int((inland_global_extent[3] - inland_global_extent[1]) / raster_resolution)
coastal_global_extent = get_global_extent(coastal_raster_files)
coastal_global_width = int((coastal_global_extent[2] - coastal_global_extent[0]) / raster_resolution)
coastal_global_height = int((coastal_global_extent[3] - coastal_global_extent[1]) / raster_resolution)

logging.info("Initialize the global rasters")
inland_global_raster = np.zeros((inland_global_height, inland_global_width), dtype=np.int16)
coastal_global_raster = np.zeros((coastal_global_height, coastal_global_width), dtype=np.int16)

logging.info("Processing rasters and merging into global raster.")
for file in tqdm(inland_raster_files, desc='Inland GFD maps'):
    with rasterio.open(file) as src:
        row_offset, col_offset = calculate_offsets(src.bounds, inland_global_extent, src.transform)
        pad_and_add_raster(src, inland_global_raster, row_offset, col_offset, inland_global_extent, src.transform)
or file in tqdm(coastal_raster_files, desc='Coastal GFD maps'):
    with rasterio.open(file) as src:
        row_offset, col_offset = calculate_offsets(src.bounds, coastal_global_extent, src.transform)
        pad_and_add_raster(src, coastal_global_raster, row_offset, col_offset, coastal_global_extent, src.transform)


logging.info("Save the global rasters.")
with rasterio.open(inland_output_path,
                   'w',
                   driver='GTiff',
                   width=inland_global_width,
                   height=inland_global_height,
                   count=1,
                   dtype=inland_global_raster.dtype,
                   crs=src.crs,
                   transform=rasterio.transform.from_origin(inland_global_extent[0], inland_global_extent[3], raster_resolution, raster_resolution)
                   ) as dst:
    dst.write(inland_global_raster, 1)
with rasterio.open(coastal_output_path,
                   'w',
                   driver='GTiff',
                   width=coastal_global_width,
                   height=coastal_global_height,
                   count=1,
                   dtype=coastal_global_raster.dtype,
                   crs=src.crs,
                   transform=rasterio.transform.from_origin(coastal_global_extent[0], coastal_global_extent[3], raster_resolution, raster_resolution)
                   ) as dst:
    dst.write(coastal_global_raster, 1)

logging.info("Done.")

