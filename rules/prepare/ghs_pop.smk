"""
Prepare (clip) GHSL Population Data
"""

rule clip_ghs_pop:
    """
    Clip GHS-POP raster to country boundary. 
    """
    input:
        raw_pop_file="data/inputs/ghs-pop/GHS_POP_E{YEAR}_GLOBE_R2023A_4326_3ss_V1_0.tif",
        boundary_file="data/inputs/boundaries/{ISO3}/geobounds_{ISO3}.geojson",
    output:
        trimmed_pop_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_ghs-pop_{YEAR}.tif",
    wildcard_constraints:
        YEAR="2000|2005|2010|2015|2020|"
    shell:
        """
        set -ex

        mkdir --parents $(dirname {output.trimmed_pop_file})
        
        # Clip raster using GeoJSON geometry
        gdalwarp \
            -cutline {input.boundary_file} \
            -crop_to_cutline \
            -of GTiff \
            -co BIGTIFF=YES \
            -tr 0.00083333333333333 0.00083333333333333 \
            -tap \
            -co compress=lzw \
            {input.raw_pop_file} \
            {output.trimmed_pop_file}
        """
""" 
Test with
snakemake -c1 data/inputs/analysis/KEN/KEN_ghs-pop_2020.tif
"""

rule interpolate_ghs_pop:
    """
    Linearly interpolate annual GHS-POP rasters between five-year layers.
    """
    input:
        pop_start=lambda wc: (
            f"data/inputs/analysis/countries/{wc.ISO3}/"
            f"{wc.ISO3}_ghs-pop_{(int(wc.YEAR) // 5) * 5}.tif"
        ),
        pop_end=lambda wc: (
            f"data/inputs/analysis/countries/{wc.ISO3}/"
            f"{wc.ISO3}_ghs-pop_{min(((int(wc.YEAR) // 5) + 1) * 5, 2020)}.tif"
        ),
    output:
        interpolated_pop=(
            "data/inputs/analysis/countries/{ISO3}/"
            "{ISO3}_ghs-pop_interpolated-{YEAR}.tif"
        ),
    wildcard_constraints:
        YEAR="2001|2002|2003|2004|2006|2007|2008|2009|"
             "2011|2012|2013|2014|2016|2017|2018|2019"
    run:
        import numpy as np
        import rasterio

        year = int(wildcards.YEAR)
        start_year = (year // 5) * 5
        end_year = min(start_year + 5, 2020)

        if start_year == end_year:
            weight = 0.0
        else:
            weight = (year - start_year) / (end_year - start_year)

        with rasterio.open(input.pop_start) as src_start:
            pop_start = src_start.read(1).astype(np.float32)
            profile = src_start.profile.copy()

            with rasterio.open(input.pop_end) as src_end:
                if (
                    src_start.shape != src_end.shape
                    or src_start.transform != src_end.transform
                    or src_start.crs != src_end.crs
                ):
                    raise ValueError(
                        f"Population rasters are not aligned: "
                        f"{input.pop_start} and {input.pop_end}"
                    )

                pop_end = src_end.read(1).astype(np.float32)

        interpolated = pop_start + weight * (pop_end - pop_start)

        # Population cannot be negative
        interpolated = np.maximum(interpolated, 0)

        profile.update(
            dtype="float32",
            compress="lzw",
            nodata=None
        )

        with rasterio.open(output.interpolated_pop, "w", **profile) as dst:
            dst.write(interpolated.astype(np.float32), 1)