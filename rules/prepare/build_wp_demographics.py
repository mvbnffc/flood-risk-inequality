"""
Script for building WorldPop demographic group rasters

This script sums the WorldPop age-sex structure rasters into selected
demographic groups used in subsequent analysis.

The demographic group rasters are then reprojected/resampled onto the
country-level GHS-POP grid so that WorldPop, GHS-POP, and flood rasters
are spatially aligned.

The input WorldPop rasters are expected to follow the naming convention:

{iso}_{gender}_{age_group}_2015_CN_100m_R2025A_v1.tif

where the ISO3 code is lower case in the filename, while the Snakemake
wildcard ISO3 is upper case.
"""

import logging
import os
from pathlib import Path

import rasterio
import numpy as np
from rasterio.warp import reproject, Resampling


logging.basicConfig(
    format="%(asctime)s %(process)d %(filename)s %(message)s",
    level=logging.INFO
)


ALL_AGE_GROUPS = ["00", "01"] + [f"{age:02d}" for age in range(5, 90, 5)] + ["90"]

DEMOGRAPHIC_GROUPS = {
    "total": {
        "gender": "t",
        "ages": ALL_AGE_GROUPS,
    },
    "female": {
        "gender": "f",
        "ages": ALL_AGE_GROUPS,
    },
    "male": {
        "gender": "m",
        "ages": ALL_AGE_GROUPS,
    },
    "children_under5": {
        "gender": "t",
        "ages": ["00", "01"],
    },
    "school_age_5_14": {
        "gender": "t",
        "ages": ["05", "10"],
    },
    "working_age_15_64": {
        "gender": "t",
        "ages": [f"{age:02d}" for age in range(15, 65, 5)],
    },
    "female_15_49": {
        "gender": "f",
        "ages": [f"{age:02d}" for age in range(15, 50, 5)],
    },
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
    Check that all WorldPop source rasters align before summing.
    """

    if src.crs != reference_profile["crs"]:
        raise ValueError(f"CRS mismatch for {raster_path}")

    if src.transform != reference_profile["transform"]:
        raise ValueError(f"Transform mismatch for {raster_path}")

    if src.width != reference_profile["width"]:
        raise ValueError(f"Width mismatch for {raster_path}")

    if src.height != reference_profile["height"]:
        raise ValueError(f"Height mismatch for {raster_path}")


def sum_rasters_native_grid(raster_paths, output_path):
    """
    Sum a list of WorldPop rasters on their native grid.
    """

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    logging.info(f"Preparing temporary native-grid raster: {output_path}")

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

        logging.info("Checking WorldPop raster alignment.")
        for raster_path in raster_paths:
            with rasterio.open(raster_path) as src:
                check_raster_alignment(src, reference_profile, raster_path)

        logging.info("Summing WorldPop rasters block by block.")
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


def calculate_raster_sum(raster_path):
    """
    Calculate the sum of valid raster cells.
    """

    with rasterio.open(raster_path) as src:
        nodata = src.nodata
        total = 0.0

        for _, window in src.block_windows(1):
            array = src.read(1, window=window)

            if nodata is not None:
                valid = (array != nodata) & np.isfinite(array)
            else:
                valid = np.isfinite(array)

            if valid.any():
                total += float(array[valid].sum())

    return total


def align_to_reference_grid(input_path, reference_path, output_path):
    """
    Reproject and resample raster onto the GHS-POP reference grid.

    Resampling.sum is used because WorldPop rasters are population counts.
    This is more appropriate than nearest or bilinear resampling for extensive
    variables such as population counts.
    """

    input_path = Path(input_path)
    reference_path = Path(reference_path)
    output_path = Path(output_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    logging.info(f"Aligning {input_path} to GHS-POP reference grid.")
    logging.info(f"Reference grid: {reference_path}")
    logging.info(f"Aligned output: {output_path}")

    if not hasattr(Resampling, "sum"):
        raise RuntimeError(
            "Your rasterio/GDAL version does not support Resampling.sum. "
            "For population count rasters, please update rasterio/GDAL rather "
            "than using bilinear resampling."
        )

    with rasterio.open(reference_path) as ref_src:
        ref_crs = ref_src.crs
        ref_transform = ref_src.transform
        ref_width = ref_src.width
        ref_height = ref_src.height
        ref_nodata = ref_src.nodata

        output_nodata = -99999.0

        with rasterio.open(input_path) as src:
            output_meta = src.meta.copy()
            output_meta.update({
                "crs": ref_crs,
                "transform": ref_transform,
                "width": ref_width,
                "height": ref_height,
                "dtype": "float32",
                "nodata": output_nodata,
                "compress": "lzw",
                "BIGTIFF": "YES",
            })

            logging.info("Reprojecting/resampling using Resampling.sum.")
            with rasterio.open(output_path, "w", **output_meta) as dst:
                reproject(
                    source=rasterio.band(src, 1),
                    destination=rasterio.band(dst, 1),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    src_nodata=src.nodata,
                    dst_transform=ref_transform,
                    dst_crs=ref_crs,
                    dst_nodata=output_nodata,
                    resampling=Resampling.sum,
                    init_dest_nodata=True,
                )

    logging.info("Applying GHS-POP nodata mask to aligned WorldPop raster.")
    with rasterio.open(reference_path) as ref_src, rasterio.open(output_path, "r+") as dst:
        for _, window in ref_src.block_windows(1):
            ref_array = ref_src.read(1, window=window)
            out_array = dst.read(1, window=window)

            if ref_nodata is not None:
                ref_invalid = (ref_array == ref_nodata) | ~np.isfinite(ref_array)
            else:
                ref_invalid = ~np.isfinite(ref_array)

            out_array = out_array.astype(np.float32)
            out_array[ref_invalid] = output_nodata
            out_array[out_array < 0] = 0

            dst.write(out_array, 1, window=window)


if __name__ == "__main__":
    try:
        input_dir: Path = Path(snakemake.input["wp_dir"])
        reference_pop_path: Path = Path(snakemake.input["pop_file"])
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
logging.info(f"GHS-POP reference grid: {reference_pop_path}")

temp_dir = Path("data/tmp/worldpop_demographic_groups") / country
temp_dir.mkdir(parents=True, exist_ok=True)

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

    final_output_path = Path(output_paths[group_name])
    temp_native_path = temp_dir / f"{country}_worldpop_{group_name}_native.tif"

    sum_rasters_native_grid(
        raster_paths=raster_paths,
        output_path=temp_native_path,
    )

    native_sum = calculate_raster_sum(temp_native_path)
    logging.info(f"Native-grid sum for {group_name}: {native_sum}")

    align_to_reference_grid(
        input_path=temp_native_path,
        reference_path=reference_pop_path,
        output_path=final_output_path,
    )

    aligned_sum = calculate_raster_sum(final_output_path)
    logging.info(f"Aligned-grid sum for {group_name}: {aligned_sum}")

    if native_sum > 0:
        pct_diff = 100 * (aligned_sum - native_sum) / native_sum
        logging.info(f"Percent difference after alignment for {group_name}: {pct_diff:.4f}%")

    logging.info(f"Deleting temporary native-grid file for {group_name}.")
    os.remove(temp_native_path)

logging.info("Done.")