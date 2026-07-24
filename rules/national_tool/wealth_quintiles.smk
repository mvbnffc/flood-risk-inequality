"""
Rules for calculating population wealth quintiles using the RWI dataset.
"""

rule create_wealth_quintiles:
    input:
        boundary_file = "data/inputs/boundaries/{ISO3}/geobounds_{ISO3}.gpkg",
        pop_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_worldpop_total.tif",
        rwi_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_rwi.tif"
    output:
        wealth_quintiles="data/results/national_tooling/countries/{ISO3}/{ISO3}_wealth_quintiles.tif"
    script:
        "./build_wealth_quintiles.py"

rule admin_wealth_summary:
    input:
        admin_areas="data/inputs/boundaries/{ISO3}/geobounds_{ISO3}.gpkg",
        pop_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_worldpop_total.tif",
        wealth_quintiles="data/results/national_tooling/countries/{ISO3}/{ISO3}_wealth_quintiles.tif",
    output:
        admin_summary="data/results/national_tooling/countries/{ISO3}/{ISO3}_pop_wealth_summary_{ADMIN_SLUG}.gpkg"
    wildcard_constraints:
        ADMIN_SLUG="ADM0|ADM1|ADM2"
    script:
        "./sum_admin_wealth.py"
