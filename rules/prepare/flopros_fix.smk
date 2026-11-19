"""
FLOPROS without boundary artefacts (own-country polygons, gaps filled with the nearest value).

New rules only; nothing existing changes. Add to the Snakefile:
    include: "rules/prepare/flopros_fix.smk"

Step 1 - build and inspect (does not touch any existing output):
    snakemake -c1 flopros_fixed_test     # DOM and LKA
    snakemake -c4 -k flopros_fixed_all   # all countries
    -> data/inputs/analysis/countries/{ISO3}/{ISO3}_flopros-fixed.tif
    -> data/results/flopros_fix/flopros_fix_summary.csv   (copy this back)
       one row per country: cells and population whose FLOPROS changes, and the effect on the
       baseline (JRC): national people-weighted risk and CI with the current vs fixed FLOPROS

Step 2 - switch the pipeline to the fixed rasters (only after reviewing step 1):
    include: "rules/prepare/flopros_switch.smk"
That replaces {ISO3}_flopros.tif with the fixed version, so every risk raster that uses
FLOPROS (all scenarios and models) is rebuilt the next time a target needs it.
"""


rule fix_flopros:
    """
    Rasterise the country's own FLOPROS polygons on the population grid and fill cells inside the
    country that they don't cover with the nearest covered value. See fix_flopros.py.
    """
    input:
        flopros="data/inputs/flopros/Scussolini_etal_Suppl_info/FLOPROS_shp_V1/FLOPROS_shp_V1.shp",
        boundary_file="data/inputs/boundaries/{ISO3}/geobounds_{ISO3}.geojson",
        pop_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_ghs-pop_2020.tif",
    output:
        flopros_fixed="data/inputs/analysis/countries/{ISO3}/{ISO3}_flopros-fixed.tif",
        log="data/results/flopros_fix/countries/{ISO3}_flopros-fixed_log.csv",
    wildcard_constraints:
        ISO3="[A-Z][A-Z][A-Z]",
    script:
        "./fix_flopros.py"


rule flopros_fix_impact:
    """
    Baseline risk and CI (JRC, V-JRC, RWI) with the current vs the fixed FLOPROS, using the same
    integration as jrc_average_annual_risk_protected.py. See flopros_fix_impact.py.
    """
    input:
        flopros_old="data/inputs/analysis/countries/{ISO3}/{ISO3}_flopros.tif",
        flopros_fixed="data/inputs/analysis/countries/{ISO3}/{ISO3}_flopros-fixed.tif",
        rp10="data/results/flood_risk/countries/{ISO3}/{ISO3}_jrc-flood-risk_RP10_V-JRC.tif",
        rp20="data/results/flood_risk/countries/{ISO3}/{ISO3}_jrc-flood-risk_RP20_V-JRC.tif",
        rp50="data/results/flood_risk/countries/{ISO3}/{ISO3}_jrc-flood-risk_RP50_V-JRC.tif",
        rp75="data/results/flood_risk/countries/{ISO3}/{ISO3}_jrc-flood-risk_RP75_V-JRC.tif",
        rp100="data/results/flood_risk/countries/{ISO3}/{ISO3}_jrc-flood-risk_RP100_V-JRC.tif",
        rp200="data/results/flood_risk/countries/{ISO3}/{ISO3}_jrc-flood-risk_RP200_V-JRC.tif",
        rp500="data/results/flood_risk/countries/{ISO3}/{ISO3}_jrc-flood-risk_RP500_V-JRC.tif",
        pop_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_ghs-pop_2020.tif",
        social_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_rwi.tif",
        mask_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_surface_water.tif",
        boundary_file="data/inputs/boundaries/{ISO3}/geobounds_{ISO3}.geojson",
    output:
        impact="data/results/flopros_fix/countries/{ISO3}_flopros-fixed_impact_jrc.csv",
    wildcard_constraints:
        ISO3="[A-Z][A-Z][A-Z]",
    script:
        "./flopros_fix_impact.py"


rule flopros_fix_summary:
    """One row per country: what changes in FLOPROS, and what that does to the baseline."""
    input:
        logs=lambda wc: expand("data/results/flopros_fix/countries/{ISO3}_flopros-fixed_log.csv", ISO3=config["iso_codes"]),
        impacts=lambda wc: expand("data/results/flopros_fix/countries/{ISO3}_flopros-fixed_impact_jrc.csv", ISO3=config["iso_codes"]),
    output:
        "data/results/flopros_fix/flopros_fix_summary.csv",
    run:
        import pandas as pd
        logs = pd.concat([pd.read_csv(f) for f in input.logs], ignore_index=True)
        impacts = pd.concat([pd.read_csv(f) for f in input.impacts], ignore_index=True)
        logs.merge(impacts, on="ISO3", how="left", suffixes=("", "_impact")).to_csv(output[0], index=False)


rule flopros_fixed_all:
    input:
        "data/results/flopros_fix/flopros_fix_summary.csv",


rule flopros_fixed_test:
    input:
        "data/results/flopros_fix/countries/DOM_flopros-fixed_log.csv",
        "data/results/flopros_fix/countries/DOM_flopros-fixed_impact_jrc.csv",
        "data/results/flopros_fix/countries/LKA_flopros-fixed_log.csv",
        "data/results/flopros_fix/countries/LKA_flopros-fixed_impact_jrc.csv",
