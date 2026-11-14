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
        wget -nc https://aqueduct.wridata.org/AqueductFloods20/inuncoast_historical_nosub_hist_rp{wildcards.RP}_0.tif -O {output.flood_file}
        """

rule download_liscoast_coastal:
    """
    Download the LISCoAsT 100-year coastal flood maps from Zenodo, check the md5, and unzip.
    The zip is only downloaded if it isn't already there, so re-running just re-unzips.
    Set keep_zip=False to delete the 1 GB zip once it has been unzipped.
    """
    output:
        unzip_dir=directory("data/inputs/flood/LISCoAsT_coastal/Imaps_90x90")
    params:
        url="https://zenodo.org/records/8057902/files/Imaps_90x90.zip?download=1",
        md5="58f0aafc3179fa9918d3e18c2178c7b1",
        zip_file="data/inputs/flood/LISCoAsT_coastal/Imaps_90x90.zip",
        keep_zip=True
    shell:
        r"""
        set -e
        mkdir -p $(dirname {params.zip_file})
        if [ ! -f {params.zip_file} ]; then
            wget -O {params.zip_file}.tmp "{params.url}"
            echo "{params.md5}  {params.zip_file}.tmp" | md5sum -c -
            mv {params.zip_file}.tmp {params.zip_file}
        fi
        rm -rf {output.unzip_dir}.tmp
        unzip -q {params.zip_file} -d {output.unzip_dir}.tmp
        mv {output.unzip_dir}.tmp {output.unzip_dir}
        if [ "{params.keep_zip}" = "False" ]; then rm {params.zip_file}; fi
        """


rule liscoast_coastal_to_vrt:
    """
    Mosaic the unzipped LISCoAsT maps into a single VRT.
    Works whether the zip held one global raster or many tiles.
    Assumes GeoTIFFs; if the find command above shows another format, change file_pattern.
    Paths are kept relative so the VRT still works if the repo lives elsewhere (cluster vs laptop).
    """
    input:
        unzip_dir="data/inputs/flood/LISCoAsT_coastal/Imaps_90x90"
    output:
        vrt="data/inputs/flood/LISCoAsT_coastal/LISCoAsT_coastal_rp0100.vrt"
    params:
        file_pattern="*.tif"
    shell:
        r"""
        set -e
        find {input.unzip_dir} -type f -iname "{params.file_pattern}" | sort > {output.vrt}.filelist.txt
        test -s {output.vrt}.filelist.txt
        echo "Mosaicking $(wc -l < {output.vrt}.filelist.txt) rasters"
        gdalbuildvrt -input_file_list {output.vrt}.filelist.txt {output.vrt}
        """
"""
Test with
snakemake -c1 data/inputs/flood/LISCoAsT_coastal/LISCoAsT_coastal_rp0100.vrt
"""