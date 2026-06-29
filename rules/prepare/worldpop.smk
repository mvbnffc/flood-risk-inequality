"""
Rules for prepping worldpop data
"""

rule build_wp_demographic_groups:
    input:
        wp_dir="data/inputs/worldpop/demographics/{ISO3}"
    output:
        total="data/inputs/analysis/countries/{ISO3}/{ISO3}_worldpop_total.tif",
        female="data/inputs/analysis/countries/{ISO3}/{ISO3}_worldpop_female.tif",
        male="data/inputs/analysis/countries/{ISO3}/{ISO3}_worldpop_male.tif",
        children_under5="data/inputs/analysis/countries/{ISO3}/{ISO3}_worldpop_children_under5.tif",
        school_age_5_14="data/inputs/analysis/countries/{ISO3}/{ISO3}_worldpop_school-age_5-14.tif",
        working_age_15_64="data/inputs/analysis/countries/{ISO3}/{ISO3}_worldpop_working-age_15-64.tif",
        female_15_49="data/inputs/analysis/countries/{ISO3}/{ISO3}_worldpop_female_15-49.tif",
        older_65plus="data/inputs/analysis/countries/{ISO3}/{ISO3}_worldpop_older_65plus.tif"
    script:
        "scripts/build_wp_demographic_groups.py"