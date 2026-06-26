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

