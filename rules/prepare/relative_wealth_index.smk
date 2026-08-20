"""
Prepare (clip and resample) the RWI data
"""

rule clip_and_resample_rwi:
    """
    Resample the and clip the rwi (using population data as reference)
    """
    input:
        pop_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_ghs-pop_2020.tif",
        rwi_file="data/inputs/rwi/rwi.tif",
        boundary_file="data/inputs/boundaries/{ISO3}/geobounds_{ISO3}.geojson",
    output:
        rwi_resampled = "data/inputs/analysis/countries/{ISO3}/{ISO3}_rwi.tif"
    script:
        "./rwi_prep.py"
""" 
Test with
snakemake -c1 data/inputs/analysis/KEN/KEN_rwi.tif
"""

rule temp_rwi_fix:
    """
    Temp rule that we are using to reassign unassigned pop cells to the average RWI value of the regions subnational ADM2
    """
    input:
        boundary_file = "data/inputs/boundaries/{ISO3}/geobounds_{ISO3}.gpkg",
        pop_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_ghs-pop_2020.tif",
        rwi_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_rwi.tif"
    output:
        wealth_quintiles="data/inputs/analysis/countries/{ISO3}/{ISO3}_wealth_quintiles.tif",
        pop_rwi_assignment="data/inputs/analysis/countries/{ISO3}/{ISO3}_frwi.tif"
    script:
        "./build_wealth_quintiles.py"