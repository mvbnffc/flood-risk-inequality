"""
Rules for summarizing metrics for the national tool
"""

rule calculate_population_risk_metrics:
    input:
        admin_areas="data/inputs/boundaries/{ISO3}/geobounds_{ISO3}.gpkg",
        RP10_file="data/results/flood_risk/countries/{ISO3}/{ISO3}_jrc-flood-risk_RP10_V-EXP.tif",
        RP20_file="data/results/flood_risk/countries/{ISO3}/{ISO3}_jrc-flood-risk_RP20_V-EXP.tif",
        RP50_file="data/results/flood_risk/countries/{ISO3}/{ISO3}_jrc-flood-risk_RP50_V-EXP.tif",
        RP75_file="data/results/flood_risk/countries/{ISO3}/{ISO3}_jrc-flood-risk_RP75_V-EXP.tif",
        RP100_file="data/results/flood_risk/countries/{ISO3}/{ISO3}_jrc-flood-risk_RP100_V-EXP.tif",
        RP200_file="data/results/flood_risk/countries/{ISO3}/{ISO3}_jrc-flood-risk_RP200_V-EXP.tif",
        RP500_file="data/results/flood_risk/countries/{ISO3}/{ISO3}_jrc-flood-risk_RP500_V-EXP.tif",
        AAR_file="data/results/flood_risk/countries/{ISO3}/{ISO3}_jrc-flood-risk_AAR_V-EXP.tif",
        AAR_protected_file="data/results/flood_risk/countries/{ISO3}/{ISO3}_jrc-flood-risk_protected_AAR_V-EXP.tif",
        total_pop="data/inputs/analysis/countries/{ISO3}/{ISO3}_worldpop_total.tif",
        female_pop="data/inputs/analysis/countries/{ISO3}/{ISO3}_worldpop_female.tif",
        male_pop="data/inputs/analysis/countries/{ISO3}/{ISO3}_worldpop_male.tif",
        children_under5_pop="data/inputs/analysis/countries/{ISO3}/{ISO3}_worldpop_children_under5.tif",
        school_age_5_14_pop="data/inputs/analysis/countries/{ISO3}/{ISO3}_worldpop_school-age_5-14.tif",
        working_age_15_64_pop="data/inputs/analysis/countries/{ISO3}/{ISO3}_worldpop_working-age_15-64.tif",
        female_15_49_pop="data/inputs/analysis/countries/{ISO3}/{ISO3}_worldpop_female_15-49.tif",
        older_65plus_pop="data/inputs/analysis/countries/{ISO3}/{ISO3}_worldpop_older_65plus.tif",
        wealth_quintiles="data/results/national_tooling/countries/{ISO3}/{ISO3}_wealth_quintiles.tif",
        mask_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_surface_water.tif"
    output:
        regional_population_risk="data/results/national_tooling/countries/{ISO3}/{ISO3}_{ADMIN_SLUG}_jrc_population_risk_metrics.gpkg"
    script:
        "./calculate_population_risk_metrics.py"

rule admin_population_demographic_summary:
    input:
        admin_areas="data/inputs/boundaries/{ISO3}/geobounds_{ISO3}.gpkg",
        total_pop="data/inputs/analysis/countries/{ISO3}/{ISO3}_worldpop_total.tif",
        female_pop="data/inputs/analysis/countries/{ISO3}/{ISO3}_worldpop_female.tif",
        male_pop="data/inputs/analysis/countries/{ISO3}/{ISO3}_worldpop_male.tif",
        children_under5_pop="data/inputs/analysis/countries/{ISO3}/{ISO3}_worldpop_children_under5.tif",
        school_age_5_14_pop="data/inputs/analysis/countries/{ISO3}/{ISO3}_worldpop_school-age_5-14.tif",
        working_age_15_64_pop="data/inputs/analysis/countries/{ISO3}/{ISO3}_worldpop_working-age_15-64.tif",
        female_15_49_pop="data/inputs/analysis/countries/{ISO3}/{ISO3}_worldpop_female_15-49.tif",
        older_65plus_pop="data/inputs/analysis/countries/{ISO3}/{ISO3}_worldpop_older_65plus.tif",
    output:
        population_summary="data/results/national_tooling/countries/{ISO3}/{ISO3}_{ADMIN_SLUG}_population_demographic_summary.gpkg"
    wildcard_constraints:
        ADMIN_SLUG="ADM0|ADM1|ADM2"
    script:
        "./sum_admin_population_demographics.py"
