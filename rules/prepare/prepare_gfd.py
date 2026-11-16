"""
This script prepares the GFD data for the global merge. For each event zip it:
    - reads band 1 (flooded) of every GeoTIFF in the zip. Earth Engine split the
      largest events into adjacent tiles on one grid when exporting (23 of the 913
      zips), so the tiles are mosaicked back into one raster per event
    - sets nodata and NaN cells (cells GFD did not map) to zero
    - writes the result as DFO_{id}.tif
    - copies the event JSON file
Tiles are read straight from the zips, so nothing is unzipped to disk.
"""

import logging
import glob
import os
import zipfile
from tqdm import tqdm

import numpy as np
import rasterio

if __name__ == "__main__":
    try:
        input_path: str = snakemake.input["raw_gfd_folder"]
        output_path: str = snakemake.output["merge_gfd_folder"]
    except:
        raise ValueError("Must be run via snakemake.")

logging.basicConfig(format="%(asctime)s %(process)d %(filename)s %(message)s", level=logging.INFO)

logging.info(f"Preparing the Global Flood Database maps for a global merge.")

#### Define functions for the analysis ####
def event_name(file_path):
    """
    Shorten a GFD file name to the event name by removing the segment starting
    from '_From'. Tiles of one event all shorten to the same name, e.g.
    DFO_1725_From_20010806_to_20010825-0000000000-0000065536.tif -> DFO_1725
    """
    return os.path.basename(file_path).split('_From')[0]

def process_zip(zip_path, output_folder):
    """
    Mosaic all tiles of one event (band 1 only), convert NaN/nodata to zero,
    write DFO_{id}.tif and copy the JSON. Returns the event name and number of tiles.
    """
    with zipfile.ZipFile(zip_path, "r") as zf:
        tif_members = sorted(f for f in zf.namelist() if f.lower().endswith(".tif"))
        json_members = [f for f in zf.namelist() if f.lower().endswith(".json")]

        if not tif_members:
            raise ValueError(f"No TIFF file found in {zip_path}")

        names = {event_name(member) for member in tif_members}
        if len(names) != 1:
            raise ValueError(f"{zip_path} holds files from more than one event: {names}")
        name = names.pop()

        # Copy the JSON file(s)
        for member in json_members:
            json_out_path = os.path.join(output_folder, "json", os.path.basename(member))
            with open(json_out_path, "wb") as json_out:
                json_out.write(zf.read(member))

    # GDAL reads the tiles directly from the zip
    tile_paths = [f"/vsizip/{os.path.abspath(zip_path)}/{member}" for member in tif_members]

    # Combined extent of all tiles (the tiles share one grid)
    bounds = []
    for path in tile_paths:
        with rasterio.open(path) as src:
            bounds.append(src.bounds)
            res_x, res_y = src.res
            crs = src.crs
    left = min(b.left for b in bounds)
    bottom = min(b.bottom for b in bounds)
    right = max(b.right for b in bounds)
    top = max(b.top for b in bounds)
    width = round((right - left) / res_x)
    height = round((top - bottom) / res_y)

    # Paste each tile into the event raster
    raster = None
    for path in tile_paths:
        with rasterio.open(path) as src:
            if src.res != (res_x, res_y):
                raise ValueError(f"Tiles in {zip_path} have different resolutions.")
            tile = src.read(1)  # Read the first band (flooded)

            # Replace no-data values and NaNs with zero
            nodata = src.nodata
            if nodata is not None:
                tile[tile == nodata] = 0
            tile = np.nan_to_num(tile)  # Converts NaN values to zero

            if raster is None:
                raster = np.zeros((height, width), dtype=tile.dtype)
            row = round((top - src.bounds.top) / res_y)
            col = round((src.bounds.left - left) / res_x)
            raster[row:row + src.height, col:col + src.width] = tile

    # Save the event raster
    output_file = os.path.join(output_folder, f"{name}.tif")
    with rasterio.open(output_file, 'w', driver='GTiff', height=height, width=width, count=1,
                       dtype=raster.dtype, crs=crs,
                       transform=rasterio.transform.from_origin(left, top, res_x, res_y),
                       compress='lzw', BIGTIFF='IF_SAFER') as dst:
        dst.write(raster, 1)

    return name, len(tif_members)

logging.info("Creating output directories (if they don't already exist)")
os.makedirs(output_path, exist_ok=True)
os.makedirs(os.path.join(output_path, "json"), exist_ok=True)

logging.info("Mosaicking tiles, converting NaNs and copying JSON files for each zipped event.")
zipped_files = sorted(glob.glob(os.path.join(input_path, "*.zip")))
done_events = set()
tiled_events = []
for zipped_file in tqdm(zipped_files):
    name, n_tiles = process_zip(zipped_file, output_path)
    if name in done_events:
        raise ValueError(f"{name} appears in more than one zip file.")
    done_events.add(name)
    if n_tiles > 1:
        tiled_events.append(f"{name} ({n_tiles} tiles)")

logging.info(f"Prepared {len(done_events)} events from {len(zipped_files)} zips.")
logging.info(f"{len(tiled_events)} events were mosaicked from tiles: {tiled_events}")

logging.info("Done.")
