"""
Combines river and coastal flood maps for a combined flood map.
The combined flood map is the maximum of the two flood maps.
"""

import logging

import rasterio
import numpy as np

if __name__ == "__main__":

    try:
        river_path: str = snakemake.input["river_flood_file"]
        coastal_path: str = snakemake.input["coast_flood_file"]
        output_path: str = snakemake.output["comb_flood_file"]
        return_period: int = snakemake.wildcards["RP"]
        vuln_dataset: str = snakemake.wildcards["VULN_CURVE"]
        country_code: str = snakemake.wildcards['ISO3']
        river_model: str = snakemake.wildcards['RIVER_MODEL']
        coastal_model: str = snakemake.wildcards['COAST_MODEL']
    except NameError:
        raise ValueError("Must be run via snakemake.")
    
logging.basicConfig(format="%(asctime)s %(process)d %(filename)s %(message)s", level=logging.INFO)

logging.info(f"Combining {river_model} river flood map with {coastal_model} coastal flood map in {country_code} at RP {return_period} using {vuln_dataset} vulnerability curve.")

logging.info("Reading raster data.")

with rasterio.open(river_path) as river_src:
    river = flood_src.read(1)
    river_transform = river_src.transform
    river_meta = river_src.meta

with rasterio.open(coastal_path) as coastal_src:
    coastal = flood_src.read(1)
    coastal_transform = coastal_src.transform
    coastal_meta = coastal_src.meta

logging.info("Combining flood maps.")
combined_flood = np.maximum(river, coastal)

# Update for compression
river_meta.update(
    compress='lzw',
    tiled=True,
    count=1,
    dtype='float32'
)

logging.info("Writing output raster.")
with rasterio.open(output_path, "w", **river_meta) as dst:
    dst.write(combined_flood.astype(np.float32), 1)

logging.info("Done.")