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
        inland_input_path: str = snakemake.input["merge_inland_gfd_folder"]
        coastal_input_path: str = snakemake.input["merge_coastal_gfd_folder"]
        inland_2000_output_path: str = snakemake.output["merge_inland_2000_gfd_file"]
        inland_2001_output_path: str = snakemake.output["merge_inland_2001_gfd_file"]
        inland_2002_output_path: str = snakemake.output["merge_inland_2002_gfd_file"]
        inland_2003_output_path: str = snakemake.output["merge_inland_2003_gfd_file"]
        inland_2004_output_path: str = snakemake.output["merge_inland_2004_gfd_file"]
        inland_2005_output_path: str = snakemake.output["merge_inland_2005_gfd_file"]
        inland_2006_output_path: str = snakemake.output["merge_inland_2006_gfd_file"]
        inland_2007_output_path: str = snakemake.output["merge_inland_2007_gfd_file"]
        inland_2008_output_path: str = snakemake.output["merge_inland_2008_gfd_file"]
        inland_2009_output_path: str = snakemake.output["merge_inland_2009_gfd_file"]
        inland_2010_output_path: str = snakemake.output["merge_inland_2010_gfd_file"]
        inland_2011_output_path: str = snakemake.output["merge_inland_2011_gfd_file"]
        inland_2012_output_path: str = snakemake.output["merge_inland_2012_gfd_file"]
        inland_2013_output_path: str = snakemake.output["merge_inland_2013_gfd_file"]
        inland_2014_output_path: str = snakemake.output["merge_inland_2014_gfd_file"]
        inland_2015_output_path: str = snakemake.output["merge_inland_2015_gfd_file"]
        inland_2016_output_path: str = snakemake.output["merge_inland_2016_gfd_file"]
        inland_2017_output_path: str = snakemake.output["merge_inland_2017_gfd_file"]
        inland_2018_output_path: str = snakemake.output["merge_inland_2018_gfd_file"]
        coastal_2000_output_path: str = snakemake.output["merge_coastal_2000_gfd_file"]
        coastal_2001_output_path: str = snakemake.output["merge_coastal_2001_gfd_file"]
        coastal_2002_output_path: str = snakemake.output["merge_coastal_2002_gfd_file"]
        coastal_2003_output_path: str = snakemake.output["merge_coastal_2003_gfd_file"]
        coastal_2004_output_path: str = snakemake.output["merge_coastal_2004_gfd_file"]
        coastal_2005_output_path: str = snakemake.output["merge_coastal_2005_gfd_file"]
        coastal_2006_output_path: str = snakemake.output["merge_coastal_2006_gfd_file"]
        coastal_2007_output_path: str = snakemake.output["merge_coastal_2007_gfd_file"]
        coastal_2008_output_path: str = snakemake.output["merge_coastal_2008_gfd_file"]
        coastal_2009_output_path: str = snakemake.output["merge_coastal_2009_gfd_file"]
        coastal_2010_output_path: str = snakemake.output["merge_coastal_2010_gfd_file"]
        coastal_2011_output_path: str = snakemake.output["merge_coastal_2011_gfd_file"]
        coastal_2012_output_path: str = snakemake.output["merge_coastal_2012_gfd_file"]
        coastal_2013_output_path: str = snakemake.output["merge_coastal_2013_gfd_file"]
        coastal_2014_output_path: str = snakemake.output["merge_coastal_2014_gfd_file"]
        coastal_2015_output_path: str = snakemake.output["merge_coastal_2015_gfd_file"]
        coastal_2016_output_path: str = snakemake.output["merge_coastal_2016_gfd_file"]
        coastal_2017_output_path: str = snakemake.output["merge_coastal_2017_gfd_file"]
        coastal_2018_output_path: str = snakemake.output["merge_coastal_2018_gfd_file"]
    except:
        raise ValueError("Must be run via snakemake.")
    
# Set some analysis parameters
raster_resolution = 0.002245788210298803843 # degrees

logging.basicConfig(format="%(asctime)s %(process)d %(filename)s %(message)s", level=logging.INFO)

logging.info(f"Merging Global Flood Database files into annual global rasters.")

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

###########################################################

logging.info("Reading raster file names.")
inland_raster_files = glob.glob(os.path.join(inland_input_path, "*.tif"))
coastal_raster_files = glob.glob(os.path.join(coastal_input_path, "*.tif"))

logging.info("Calculate global extents.")
inland_global_extent = get_global_extent(inland_raster_files)
inland_global_width = int(np.ceil((inland_global_extent[2] - inland_global_extent[0])) / raster_resolution)
inland_global_height = int(np.ceil((inland_global_extent[3] - inland_global_extent[1])) / raster_resolution)
coastal_global_extent = get_global_extent(coastal_raster_files)
coastal_global_width = int(np.ceil((coastal_global_extent[2] - coastal_global_extent[0])) / raster_resolution)
coastal_global_height = int(np.ceil((coastal_global_extent[3] - coastal_global_extent[1])) / raster_resolution)

logging.info("Initialize the global rasters")
inland_global_raster = np.zeros((inland_global_height, inland_global_width), dtype=np.int16)
coastal_global_raster = np.zeros((coastal_global_height, coastal_global_width), dtype=np.int16)

logging.info("Sorting inland and coastal annual GFD files.")
# Splitting GFD ID's into coastal and inland
annual_dict = {}
for i in range(2000, 2019):
    annual_dict[i] = []
    with open(f"config/gfd_{i}.txt", "r") as f:
        for line in f.readlines():
            annual_dict[i].append(line.strip())

logging.info("Processing annual rasters and merging into global raster.")
for i in range(2000, 2019):
    logging.info(f"Processing {i} GFD maps.")
    for file in tqdm(inland_raster_files, desc=f'Inland GFD maps {i}'):
        if any(annual_id in os.path.basename(file) for annual_id in annual_dict[i]):
            with rasterio.open(file) as src:
                row_offset, col_offset = calculate_offsets(src.bounds, inland_global_extent, src.transform)
                pad_and_add_raster(src, inland_global_raster, row_offset, col_offset, inland_global_extent, src.transform)
    for file in tqdm(coastal_raster_files, desc=f'Coastal GFD maps {i}'):
        if any(annual_id in os.path.basename(file) for annual_id in annual_dict[i]):
            with rasterio.open(file) as src:
                row_offset, col_offset = calculate_offsets(src.bounds, coastal_global_extent, src.transform)
                pad_and_add_raster(src, coastal_global_raster, row_offset, col_offset, coastal_global_extent, src.transform)

    logging.info("Save the global rasters.")
    with rasterio.open(inland_2000_output_path if i == 2000 else inland_2001_output_path if i == 2001 else inland_2002_output_path if i == 2002 else inland_2003_output_path if i == 2003 else inland_2004_output_path if i == 2004 else inland_2005_output_path if i == 2005 else inland_2006_output_path if i == 2006 else inland_2007_output_path if i == 2007 else inland_2008_output_path if i == 2008 else inland_2009_output_path if i == 2009 else inland_2010_output_path if i == 2010 else inland_2011_output_path if i == 2011 else inland_2012_output_path if i == 2012 else inland_2013_output_path if i == 2013 else inland_2014_output_path if i == 2014 else inland_2015_output_path if i == 2015 else inland_2016_output_path if i == 2016 else inland_2017_output_path if i == 2017 else inland_2018_output_path,
                       'w',
                       driver='GTiff',
                       width=inland_global_width,
                       height=inland_global_height,
                       count=1,
                       dtype=inland_global_raster.dtype,
                       crs=src.crs,
                       transform=rasterio.transform.from_origin(inland_global_extent[0], inland_global_extent[3], raster_resolution, raster_resolution),
                       compress="deflate",
                       predictor=2,
                       ) as dst:
        dst.write(inland_global_raster, 1)
    with rasterio.open(coastal_2000_output_path if i == 2000 else coastal_2001_output_path if i == 2001 else coastal_2002_output_path if i == 2002 else coastal_2003_output_path if i == 2003 else coastal_2004_output_path if i == 2004 else coastal_2005_output_path if i == 2005 else coastal_2006_output_path if i == 2006 else coastal_2007_output_path if i == 2007 else coastal_2008_output_path if i == 2008 else coastal_2009_output_path if i == 2009 else coastal_2010_output_path if i == 2010 else coastal_2011_output_path if i == 2011 else coastal_2012_output_path if i == 2012 else coastal_2013_output_path if i == 2013 else coastal_2014_output_path if i == 2014 else coastal_2015_output_path if i == 2015 else coastal_2016_output_path if i == 2016 else coastal_2017_output_path if i == 2017 else coastal_2018_output_path,
                       'w',
                       driver='GTiff',
                       width=coastal_global_width,
                       height=coastal_global_height,
                       count=1,
                       dtype=coastal_global_raster.dtype,
                       crs=src.crs,
                       transform=rasterio.transform.from_origin(coastal_global_extent[0], coastal_global_extent[3], raster_resolution, raster_resolution),
                       compress="deflate",
                       predictor=2,
                       ) as dst:
        dst.write(coastal_global_raster, 1)

logging.info("Done.")

