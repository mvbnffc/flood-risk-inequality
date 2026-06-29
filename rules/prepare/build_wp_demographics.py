"""
Script for building WorldPop demographic group rasters

This script sums the WorldPop age-sex structure rasters into selected
demographic groups used in subsequent analysis.

The input rasters are expected to follow the WorldPop naming convention:

{iso}_{gender}_{age_group}_{year}_{type}_{resolution}_{release}_{version}.tif

where the ISO3 code is lower case in the filename, while the Snakemake
wildcard ISO3 is upper case.
"""

import logging
import sys
import os
from pathlib import Path

import rasterio
import numpy as np


logging.basicConfig(
    format="%(asctime)s %(process)d %(filename)s %(message)s",
    level=logging.INFO
)


ALL_AGE_GROUPS = ["00", "01"] + [f"{age:02d}" for age in range(5, 90, 5)] + ["90"]

DEMOGRAPHIC_GROUPS = {
    # Total population, all ages, both genders
    "total": {
        "gender": "t",
        "ages": ALL_AGE_GROUPS,
    },

    # Female population, all ages
    "female": {
        "gender": "f",
        "ages": ALL_AGE_GROUPS,
    },

    # Male population, all ages
    "male": {
        "gender": "m",
        "ages": ALL_AGE_GROUPS,
    },

    # Children under 5:
    # 00 = 0 to 12 months
    # 01 = 1 to 4 years
    "children_under5": {
        "gender": "t",
        "ages": ["00", "01"],
    },

    # School-age children:
    # 05 = 5 to 9 years
    # 10 = 10 to 14 years
    "school_age_5_14": {
        "gender": "t",
        "ages": ["05", "10"],
    },

    # Working-age population:
    # 15 = 15 to 19 years
    # ...
    # 60 = 60 to 64 years
    "working_age_15_64": {
        "gender": "t",
        "ages": [f"{age:02d}" for age in range(15, 65, 5)],
    },

    # Female population aged 15 to 49:
    # 15 = 15 to 19 years
    # ...
    # 45 = 45 to 49 years
    "female_15_49": {
        "gender": "f",
        "ages": [f"{age:02d}" for age in range(15, 50, 5)],
    },

    # Older population aged 65+
    "older_65plus": {
        "gender": "t",
        "ages": [f"{age:02d}" for age in range(65, 90, 5)] + ["90"],
    },
}


def get_worldpop_path(
    input_dir: Path,
    iso3: str,
    gender: str,
    age_group: str
) -> Path:
    """
    Build the expected WorldPop raster path.
    """

    filename = (
        f"{iso3.lower()}_{gender}_{age_group}_2015_CN_"
        f"100m_R2025A_v1.tif"
    )

    path = input_dir / filename

    if not path.exists():
        raise FileNotFoundError(f"Missing expected WorldPop raster: {path}")

    return path


def check_raster_alignment(src, reference_profile, raster_path):
    """
    Check that all rasters align before summing.
    """

    if src.crs != reference_profile["crs"]:
        raise ValueError(f"CRS mismatch for {raster_path}")

    if src.transform != reference_profile["transform"]:
        raise ValueError(f"Transform mismatch for {raster_path}")

    if src.width != reference_profile["width"]:
        raise ValueError(f"Width mismatch for {raster_path}")

    if src.height != reference_profile["height"]:
        raise ValueError(f"Height mismatch for {raster_path}")


def sum_rasters(raster_paths, output_path):
    """
    Sum a list of rasters and save the result.
    """

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    logging.info(f"Preparing output raster: {output_path}")

    with rasterio.open(raster_paths[0]) as src0:
        reference_profile = src0.profile.copy()

        output_nodata = src0.nodata
        if output_nodata is None:
            output_nodata = -99999.0

        output_profile = src0.profile.copy()
        output_profile.update({
            "dtype": "float32",
            "nodata": output_nodata,
            "compress": "lzw",
            "BIGTIFF": "YES",
        })

        logging.info("Checking raster alignment.")
        for raster_path in raster_paths:
            with rasterio.open(raster_path) as src:
                check_raster_alignment(src, reference_profile, raster_path)

        logging.info("Summing rasters block by block.")
        with rasterio.open(output_path, "w", **output_profile) as dst:
            for _, window in src0.block_windows(1):
                summed = None
                all_nodata = None

                for raster_path in raster_paths:
                    with rasterio.open(raster_path) as src:
                        array = src.read(1, window=window, masked=True).astype(np.float32)

                        mask = np.ma.getmaskarray(array)

                        if summed is None:
                            summed = np.zeros(array.shape, dtype=np.float32)
                            all_nodata = mask.copy()
                        else:
                            all_nodata = all_nodata & mask

                        summed += array.filled(0).astype(np.float32)

                summed[all_nodata] = output_nodata
                dst.write(summed.astype(np.float32), 1, window=window)


if __name__ == "__main__":
    try:
        input_dir: Path = Path(snakemake.input["wp_dir"])
        country: str = snakemake.wildcards["ISO3"]

        output_paths = {
            "total": snakemake.output["total"],
            "female": snakemake.output["female"],
            "male": snakemake.output["male"],
            "children_under5": snakemake.output["children_under5"],
            "school_age_5_14": snakemake.output["school_age_5_14"],
            "working_age_15_64": snakemake.output["working_age_15_64"],
            "female_15_49": snakemake.output["female_15_49"],
            "older_65plus": snakemake.output["older_65plus"],
        }

    except NameError:
        raise ValueError("Must be run via snakemake.")

logging.info(f"Building WorldPop demographic group rasters for {country}.")
logging.info(f"Input directory: {input_dir}")

for group_name, group_info in DEMOGRAPHIC_GROUPS.items():
    logging.info(f"Processing demographic group: {group_name}")

    gender = group_info["gender"]
    age_groups = group_info["ages"]

    raster_paths = [
        get_worldpop_path(
            input_dir=input_dir,
            iso3=country,
            gender=gender,
            age_group=age_group
        )
        for age_group in age_groups
    ]

    logging.info(f"Number of rasters to sum for {group_name}: {len(raster_paths)}")

    output_path = output_paths[group_name]

    sum_rasters(
        raster_paths=raster_paths,
        output_path=output_path,
    )

logging.info("Done.")