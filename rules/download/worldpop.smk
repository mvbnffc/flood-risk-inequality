"""
Download WorlPop Population Data

References
---------
WorldPop: https://hub.worldpop.org/
"""

rule download_wp_demographics:
    output:
        folder=directory("data/inputs/worldpop/demographics/{ISO3}")
    params:
        url=lambda wildcards: (
            "https://data.worldpop.org/GIS/AgeSex_structures/Global_2015_2030/"
            f"R2025A/2024/{wildcards.ISO3}/v1/100m/"
            f"{wildcards.ISO3.lower()}_agesex_structures_2024_CN_100m_R2025A_v1.zip"
        ),
        zip_name=lambda wildcards: (
            f"{wildcards.ISO3.lower()}_agesex_structures_2024_CN_100m_R2025A_v1.zip"
        )
    shell:
        """
        mkdir -p {output.folder}

        wget -nc "{params.url}" -O "{output.folder}/{params.zip_name}"

        unzip -o "{output.folder}/{params.zip_name}" -d {output.folder}
        """