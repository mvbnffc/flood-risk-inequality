"""
Prepare all coastal flooding datasets
"""

rule clip_deltares_coastal_flood:
    """
    Clip Deltares coastal flood raster to country boundary.
    """
    input:
        pop_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_ghs-pop.tif",
        raw_flood_file=lambda wc: (
            f"data/inputs/flood/Deltares_coastal/Deltares_coastal_MERIT90m_2018_rp{'%04d' % int(wc.RP)}.tif"
        ),
        boundary_file="data/inputs/boundaries/{ISO3}/geobounds_{ISO3}.geojson",
    output:
        trimmed_flood_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_deltares-coastal-flood_RP{RP}.tif",
    wildcard_constraints:
        RP="2|5|10|25|50|100|250"
    shell:
        """
        set -ex

        mkdir --parents $(dirname {output.trimmed_flood_file})
        
        # Clip raster using GeoJSON geometry
        gdalwarp \
            -cutline {input.boundary_file} \
            -crop_to_cutline \
            -tr 0.00083333333333333 0.00083333333333333 \
            -tap \
            -te_srs EPSG:4326 \
            -co BIGTIFF=YES \
            -te $(gdalinfo -json {input.pop_file} | jq -r '.cornerCoordinates | [.upperLeft[0], .lowerLeft[1], .lowerRight[0], .upperRight[1]] | join(" ")') \
            -of GTiff \
            -co compress=lzw \
            {input.raw_flood_file} \
            {output.trimmed_flood_file}
        """
""" 
Test with
snakemake -c1 data/inputs/analysis/KEN/KEN_deltares-coastal-flood_RP10.tif
"""

rule clip_wri_coastal_flood:
    """
    Clip and resample WRI flood map (using population dataset as reference)
    Note: we are using rwi_prep.py script as it works the same.
    """
    input:
        pop_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_ghs-pop.tif",
        rwi_file=lambda wc: (
            f"data/inputs/flood/WRI/inuncoast_historical_nosub_hist_rp{'%05d' % int(wc.RP)}.tif"
        ),
        boundary_file="data/inputs/boundaries/{ISO3}/geobounds_{ISO3}.geojson",
    wildcard_constraints:
        RP="2|5|10|25|50|100|250|500|1000"
    output:
        rwi_resampled = "data/inputs/analysis/countries/{ISO3}/{ISO3}_wri-coastal-flood_RP{RP}.tif"
    script:
        "./rwi_prep.py"