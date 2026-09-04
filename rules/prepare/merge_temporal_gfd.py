"""
Script for creating a merged annual rasters of the Global Flood Databse - for inland and coastal flooding.
"""

import logging
import glob
import os

import numpy as np
import rasterio
from tqdm import tqdm

if __name__ == "__main__":
    try:
        input_path: str = snakemake.input["merge_gfd_folder"]
        year_ids: str = snakemake.input["epoch_ids"]
        flood_ids: str = snakemake.input["flood_ids"]
        output_path:  str = snakemake.output["merge_temporal_gfd_file"]
        flood_type: str = snakemake.wildcards["TYPE"]
        epoch: str = snakemake.wildcards["YEAR"]
    except:
        raise ValueError("Must be run via snakemake.")
    
# Set some analysis parameters
raster_resolution = 0.002245788210298803843 # degrees

logging.basicConfig(format="%(asctime)s %(process)d %(filename)s %(message)s", level=logging.INFO)

logging.info(f"Merging Global Flood Database {flood_type} files into {epoch} global raster.")

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

def read_ids(path):
    with open(path, "r") as f:
        return {
            line.strip()
            for line in f
            if line.strip()
        }

###########################################################
###########################################################

logging.info("Reading raster file names.")
raster_files = glob.glob(os.path.join(input_path, "*.tif"))

if not raster_files:
    raise FileNotFoundError(f"No prepared GFD rasters found in {input_path}")

# Use all prepared rasters to define a common global grid for every
# year and flood type.
logging.info("Calculating global extent.")
global_extent = get_global_extent(raster_files)

global_width = int(
    np.ceil(
        (global_extent[2] - global_extent[0]) / raster_resolution
    )
)
global_height = int(
    np.ceil(
        (global_extent[3] - global_extent[1]) / raster_resolution
    )
)

with rasterio.open(raster_files[0]) as template_src:
    global_crs = template_src.crs

logging.info("Reading year and flood-type event IDs.")
epoch_ids = read_ids(year_ids)
type_ids = read_ids(flood_ids)
gfd_ids = epoch_ids & type_ids

expected_filenames = {
    f"DFO_{gfd_id}.tif"
    for gfd_id in gfd_ids
}

available_files = {
    os.path.basename(file): file
    for file in raster_files
}

missing_files = expected_filenames - available_files.keys()
if missing_files:
    raise FileNotFoundError(
        f"{len(missing_files)} expected GFD rasters were not found. "
        f"Examples: {sorted(missing_files)[:10]}"
    )

selected_raster_files = [
    available_files[filename]
    for filename in sorted(expected_filenames)
]

logging.info(
    f"Selected {len(selected_raster_files)} rasters for "
    f"{epoch} {flood_type} flooding."
)

logging.info("Initializing global raster.")
global_raster = np.zeros(
    (global_height, global_width),
    dtype=np.int16,
)

for file in tqdm(selected_raster_files):
    with rasterio.open(file) as src:
        row_offset, col_offset = calculate_offsets(
            src.bounds,
            global_extent,
            src.transform,
        )
        pad_and_add_raster(
            src,
            global_raster,
            row_offset,
            col_offset,
            global_extent,
            src.transform,
        )

logging.info("Saving global raster.")
with rasterio.open(
    output_path,
    "w",
    driver="GTiff",
    width=global_width,
    height=global_height,
    count=1,
    dtype=global_raster.dtype,
    crs=global_crs,
    transform=rasterio.transform.from_origin(
        global_extent[0],
        global_extent[3],
        raster_resolution,
        raster_resolution,
    ),
    compress="deflate",
    predictor=2,
) as dst:
    dst.write(global_raster, 1)

logging.info("Done.")

