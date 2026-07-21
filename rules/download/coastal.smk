"""
Rulebook for downloading coastal flood data
"""

"""
Download Deltares Coastal Flood Data

References
---------
DELTARES: https://planetarycomputer.microsoft.com/dataset/deltares-floods
"""

rule download_deltares_coastal:
    output:
        flood_file="data/inputs/flood/Deltares_coastal/Deltares_coastal_MERIT90m_2018_rp{RP}.nc"
    wildcard_constraints:
        RP="0002|0005|0010|0025|0050|0100|0250"
    params:
        blob="https://deltaresfloodssa.blob.core.windows.net/floods/v2021.06/global/MERITDEM/90m/GFM_global_MERITDEM90m_2018slr_rp{RP}_masked.nc"
    shell:
        r"""
        mkdir -p $(dirname {output.flood_file})
        TOKEN=$(curl -s "https://planetarycomputer.microsoft.com/api/sas/v1/token/deltares-floods" \
                | python -c "import sys, json; print(json.load(sys.stdin)['token'])")
        wget -O {output.flood_file}.tmp "{params.blob}?${{TOKEN}}"
        mv {output.flood_file}.tmp {output.flood_file}
        """

rule deltares_nc_to_gtiff:
    input:
        nc="data/inputs/flood/Deltares_coastal/Deltares_coastal_MERIT90m_2018_rp{RP}.nc"
    output:
        tif="data/inputs/flood/Deltares_coastal/Deltares_coastal_MERIT90m_2018_rp{RP}.tif"
    wildcard_constraints:
        RP="0002|0005|0010|0025|0050|0100|0250"
    threads: 4
    shell:
        r"""
        gdal_translate \
            -of GTiff \
            -a_srs EPSG:4326 \
            -co BIGTIFF=YES \
            -co TILED=YES \
            -co COMPRESS=DEFLATE \
            -co PREDICTOR=3 \
            -co NUM_THREADS=ALL_CPUS \
            NETCDF:"{input.nc}":inun \
            {output.tif}
        """

"""
Download WRI Global Coastal Flood Data

References
---------
WRI: https://www.wri.org/data/aqueduct-floods-hazard-maps
"""

rule download_wri_coastal_flood:
    output:
        flood_file="data/inputs/flood/WRI/inuncoast_historical_nosub_hist_rp0{RP}.tif"
    wildcard_constraints:
        RP="0002|0005|0010|0025|0050|0100|0250|0500|1000"
    shell:
        """
        mkdir -p $(dirname {output.flood_file})
        wget -nc https://aqueduct.wridata.org/AqueductFloods20/inuncoast_historical_nosub_hist_rp0{wildcards.RP}.tif -O {output.flood_file}
        """

