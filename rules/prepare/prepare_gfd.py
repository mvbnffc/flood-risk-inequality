"""
This script prepares the GFD data for further analysis by extracting the data,
dealing with NaNs, renaming the files, and copying the relevant JSON files.
"""

import logging
import sys
import glob
import os
import shutil

import numpy as np
import rasterio
import zipfile

if __name__ == "__main__":
    try:
        input_path: str = snakemake.input["raw_gfd_folder"]
        inland_output_path: str = snakemake.output["merge_inland_gfd_folder"]
        coastal_output_path: str = snakemake.output["merge_coastal_gfd_folder"]
    except:
        raise ValueError("Must be run via snakemake.")

logging.basicConfig(format="%(asctime)s %(process)d %(filename)s %(message)s", level=logging.INFO)

logging.info(f"Preparing the Global Flood Database maps for a global merge.")

#### Define functions for the analysis ####
def extract_files(zip_path):
    """Extract the first TIFF and JSON file from a ZIP without loading them into memory."""
    unzip_folder = os.path.join(input_path, "unzipped")
    os.makedirs(unzip_folder, exist_ok=True)

    logging.info(f"Opening ZIP: {zip_path}")

    with zipfile.ZipFile(zip_path, "r") as zf:
        tif_files = [
            file for file in zf.namelist()
            if file.lower().endswith(".tif")
        ]
        json_files = [
            file for file in zf.namelist()
            if file.lower().endswith(".json")
        ]

        if not tif_files:
            raise ValueError(f"No TIFF file found in {zip_path}")
        if not json_files:
            raise ValueError(f"No JSON file found in {zip_path}")

        tif_file = tif_files[0]
        json_file = json_files[0]

        output_tif = os.path.join(
            unzip_folder,
            os.path.basename(tif_file),
        )
        output_json = os.path.join(
            unzip_folder,
            os.path.basename(json_file),
        )

        logging.info(
            f"Extracting {tif_file} "
            f"({zf.getinfo(tif_file).file_size / 1024**3:.2f} GB)"
        )

        with zf.open(tif_file, "r") as src, open(output_tif, "wb") as dst:
            shutil.copyfileobj(src, dst, length=16 * 1024 * 1024)

        logging.info(f"Extracting {json_file}")

        with zf.open(json_file, "r") as src, open(output_json, "wb") as dst:
            shutil.copyfileobj(src, dst)

        logging.info(f"Finished extracting {zip_path}")

def shorten_filename(file_path):
    """
    Given a file path, shorten the basename by removing the segment starting
    from '_From' and return the new filename with the original extension.
    """
    base_name = os.path.basename(file_path)
    # Split on '_From' to drop any additional date range info
    name_part = base_name.split('_From')[0]
    # Extract the file extension (e.g., '.tif')
    _, ext = os.path.splitext(base_name)
    return name_part + ext

def process_raster(file, output_folder):
    with rasterio.open(file) as src:
        raster = src.read(1)  # Read the first band

        # Replace no-data values and NaNs with zero
        nodata = src.nodata
        if nodata is not None:
            raster[raster == nodata] = 0
        raster = np.nan_to_num(raster)  # Converts NaN values to zero

        # Adjust filename for saving
        shortened_name = shorten_filename(file)
        output_file = os.path.join(output_folder, shortened_name)

        # Save the modified raster
        with rasterio.open(output_file, 'w', driver='GTiff', height=raster.shape[0], width=raster.shape[1], count=1, dtype=raster.dtype, crs=src.crs, transform=src.transform, compress='lzw') as dst:
            dst.write(raster, 1)

logging.info("Creating output directories (if they don't already exist)")
os.makedirs(inland_output_path, exist_ok=True)
os.makedirs(coastal_output_path, exist_ok=True)


logging.info("Extract the rasters (and JSON files) from the zipped folder.")
zipped_files = glob.glob(os.path.join(input_path, "*.zip"))
for zipped_file in zipped_files:
    extract_files(zipped_file)

logging.info("Loop over TIF files and converting NaNs - skipping those for specified in config folder.")
# Splitting GFD ID's into coastal and inland
coastal_files = []
inland_files = []
skip_files = []
with open("config/gfd_inland.txt", "r") as f:
    for line in f.readlines():
        inland_files.append(line.strip())
with open("config/gfd_coastal.txt", "r") as f:
    for line in f.readlines():
        coastal_files.append(line.strip())
tif_files = glob.glob(os.path.join(input_path, "unzipped", "*.tif"))
json_files = glob.glob(os.path.join(input_path, "unzipped", "*.json"))

for file in tif_files:
    if any(inland_id in os.path.basename(file) for inland_id in inland_files):
        process_raster(file, inland_output_path)
    if any(coastal_id in os.path.basename(file) for coastal_id in coastal_files):
        process_raster(file, coastal_output_path)

logging.info("Copying relevant JSON files.")
# Create json folder
os.makedirs(os.path.join(inland_output_path, "json"), exist_ok=True)
os.makedirs(os.path.join(coastal_output_path, "json"), exist_ok=True)
# Also want to extract the JSON files.
for file in json_files:
    if any (inland_id in os.path.basename(file) for inland_id in inland_files):
        with open(file, 'r') as json_in:
            json_out_path = os.path.join(inland_output_path, "json", os.path.basename(file))
            with open(json_out_path, 'w') as json_out:
                json_out.write(json_in.read())
    if any (coastal_id in os.path.basename(file) for coastal_id in coastal_files):
        with open(file, 'r') as json_in:
            json_out_path = os.path.join(coastal_output_path, "json", os.path.basename(file))
            with open(json_out_path, 'w') as json_out:
                json_out.write(json_in.read())

logging.info("Done.")

