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
    shell:
        """
        mkdir -p $(dirname {output.flood_file})
        wget -0 {output.flood_file}.tmp "https://deltaresfloodssa.blob.core.windows.net/floods/v2021.06/global/MERIT/90m/GFM_global_MERITDEM90m_2018slr_rp{wildcards.RP}_masked.nc"
        mv {output.flood_file}.tmp {output.flood_file}
        """

