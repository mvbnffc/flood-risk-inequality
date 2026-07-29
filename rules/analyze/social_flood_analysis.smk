"""
Rulebook for the social flood analyses (concentration curves and inequality metrics)
"""

import json
import os
import re

rule inequality_metrics:
    """
    This rule calcualtes two inequality metrics at the specified administrative level.
    Inequality metrics:
        - Concentration Index (CI) - understand the inequality of flood risk across the wealth distribution
        - Quantile Ratio (QR) - understand the tail inequality (20:80)
    """
    input:
        admin_areas = "data/inputs/boundaries/{ISO3}/geobounds_{ISO3}.gpkg",
        social_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_{SOCIAL}.tif",
        pop_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_ghs-pop.tif",
        mask_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_surface_water.tif",
        risk_file="data/results/flood_risk/countries/{ISO3}/{ISO3}_{MODEL}-flood-risk_{TYPE}_V-{VULN_CURVE}.tif",
    output:
        regional_CI = "data/results/social_flood/countries/{ISO3}/inequality_metrics/{ISO3}_{ADMIN_SLUG}_metrics_{MODEL}-flood_{TYPE}_V-{VULN_CURVE}_S-{SOCIAL}.gpkg",
    wildcard_constraints:
        MODEL="giri|jrc|wri|deltares-coastal",
        TYPE="AAR|RP100",
        SOCIAL="rwi|gdp",
        VULN_CURVE="BER|JRC|EXP",
        ADMIN_SLUG="ADM0|ADM1|ADM2"
    script:
        "./inequality_metrics.py"
"""
Test with
snakemake -c1 data/results/social_flood/countries/KEN/inequality_metrics/KEN_ADM0_metrics_jrc-flood_AAR_V-JRC_S-rwi.gpkg
"""

rule inequality_metrics_decomposed:
    """
    This rule calcualtes two inequality metrics at the specified administrative level decomposed by urbanization level
    Inequality metrics:
        - Concentration Index (CI) - understand the inequality of flood risk across the wealth distribution
        - Quantile Ratio (QR) - understand the tail inequality (20:80)
    """
    input:
        admin_areas = "data/inputs/boundaries/{ISO3}/geobounds_{ISO3}.gpkg",
        social_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_{SOCIAL}.tif",
        pop_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_ghs-pop.tif",
        urban_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_ghs-mod_fixed.tif",
        mask_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_surface_water.tif",
        risk_file="data/results/flood_risk/countries/{ISO3}/{ISO3}_{MODEL}-flood-risk_{TYPE}_V-{VULN_CURVE}.tif",
    output:
        regional_CI = "data/results/social_flood/countries/{ISO3}/inequality_metrics/{ISO3}_{ADMIN_SLUG}_decomposed_metrics_{MODEL}-flood_{TYPE}_V-{VULN_CURVE}_S-{SOCIAL}.gpkg",
    wildcard_constraints:
        MODEL="giri|jrc|wri|deltares-coastal",
        TYPE="AAR|RP100",
        SOCIAL="rwi|gdp",
        VULN_CURVE="BER|JRC|EXP",
        ADMIN_SLUG="ADM0|ADM1|ADM2"
    script:
        "./inequality_metrics_decomposed.py"
"""
Test with
snakemake -c1 data/results/social_flood/countries/KEN/inequality_metrics/KEN_ADM0_decomposed_metrics_jrc-flood_AAR_V-JRC_S-rwi.gpkg
"""

rule inequality_metrics_protected:
    """
    This rule calcualtes two inequality metrics at the specified administrative level. FLOPROS protection is ON.
    Inequality metrics:
        - Concentration Index (CI) - understand the inequality of flood risk across the wealth distribution
        - Quantile Ratio (QR) - understand the tail inequality (20:80)
    """
    input:
        admin_areas = "data/inputs/boundaries/{ISO3}/geobounds_{ISO3}.gpkg",
        social_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_{SOCIAL}.tif",
        pop_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_ghs-pop.tif",
        mask_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_surface_water.tif",
        risk_file="data/results/flood_risk/countries/{ISO3}/{ISO3}_{MODEL}-flood-risk_protected_AAR_V-{VULN_CURVE}.tif",
    output:
        regional_CI = "data/results/social_flood/countries/{ISO3}/inequality_metrics/{ISO3}_{ADMIN_SLUG}_metrics_{MODEL}-flood_protected_AAR_V-{VULN_CURVE}_S-{SOCIAL}.gpkg",
    wildcard_constraints:
        MODEL="giri|jrc|wri|deltares-coastal",
        VULN_CURVE="BER|JRC|EXP",
        SOCIAL="rwi|gdp",
        ADMIN_SLUG="ADM0|ADM1|ADM2"
    script:
        "./inequality_metrics.py"
"""
Test with
snakemake -c1 data/results/social_flood/countries/KEN/inequality_metrics/KEN_ADM0_metrics_jrc-flood_protected_AAR_V-JRC_S-rwi.gpkg
"""

rule inequality_metrics_protected_decomposed:
    """
    This rule calcualtes two inequality metrics at the specified administrative level. FLOPROS protection is ON.
    Inequality metrics:
        - Concentration Index (CI) - understand the inequality of flood risk across the wealth distribution
        - Quantile Ratio (QR) - understand the tail inequality (20:80)
    """
    input:
        admin_areas = "data/inputs/boundaries/{ISO3}/geobounds_{ISO3}.gpkg",
        social_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_{SOCIAL}.tif",
        urban_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_ghs-mod_fixed.tif",
        pop_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_ghs-pop.tif",
        mask_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_surface_water.tif",
        risk_file="data/results/flood_risk/countries/{ISO3}/{ISO3}_{MODEL}-flood-risk_protected_AAR_V-{VULN_CURVE}.tif",
    output:
        regional_CI = "data/results/social_flood/countries/{ISO3}/inequality_metrics/{ISO3}_{ADMIN_SLUG}_decomposed_metrics_{MODEL}-flood_protected_AAR_V-{VULN_CURVE}_S-{SOCIAL}.gpkg",
    wildcard_constraints:
        MODEL="giri|jrc|wri|deltares-coastal",
        VULN_CURVE="BER|JRC|EXP",
        SOCIAL="rwi|gdp",
        ADMIN_SLUG="ADM0|ADM1|ADM2"
    script:
        "./inequality_metrics_decomposed.py"
"""
Test with
snakemake -c1 data/results/social_flood/countries/KEN/inequality_metrics/KEN_ADM0_decomposed_metrics_jrc-flood_protected_AAR_V-JRC_S-rwi.gpkg
"""

rule inequality_metrics_admin_decomposed:
    """
    This rule calculates the natioanl CI and its geospatial decomposition at the specified administrative level. FLOPROS protection is ON.
    Inequality metrics:
        - Concentration Index (CI) - understand the inequality of flood risk across the wealth distribution
    """
    input:
        admin_areas = "data/inputs/boundaries/{ISO3}/geobounds_{ISO3}.gpkg",
        social_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_{SOCIAL}.tif",
        urban_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_ghs-mod_fixed.tif",
        pop_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_ghs-pop.tif",
        mask_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_surface_water.tif",
        risk_file="data/results/flood_risk/countries/{ISO3}/{ISO3}_{MODEL}-flood-risk_protected_AAR_V-{VULN_CURVE}.tif",
    output:
        regional_CI = "data/results/social_flood/countries/{ISO3}/inequality_metrics/{ISO3}_{ADMIN_SLUG}_admin-decomposed_metrics_{MODEL}-flood_protected_AAR_V-{VULN_CURVE}_S-{SOCIAL}.gpkg",
    wildcard_constraints:
        MODEL="giri|jrc|wri|deltares-coastal",
        VULN_CURVE="BER|JRC|EXP",
        SOCIAL="rwi|gdp",
        ADMIN_SLUG="ADM1|ADM2"
    script:
        "./inequality_metrics_admin_decomposed.py"
"""
Test with
snakemake -c1 data/results/social_flood/countries/KEN/inequality_metrics/KEN_ADM1_admin-decomposed_metrics_jrc-flood_protected_AAR_V-JRC_S-rwi.gpkg
"""

rule inequality_metrics_flood_protection:
    """
    This rule calcualtes two inequality metrics at the specified administrative level for the flood protection adaptation scenario.
    Adaptation parameters required as input are RP protection and min level of urbanization to protect.
    Inequality metrics:
        - Concentration Index (CI) - understand the inequality of flood risk across the wealth distribution
        - Quantile Ratio (QR) - understand the tail inequality (20:80)
    """
    input:
        admin_areas = "data/inputs/boundaries/{ISO3}/geobounds_{ISO3}.gpkg",
        social_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_{SOCIAL}.tif",
        pop_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_ghs-pop.tif",
        mask_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_surface_water.tif",
        risk_file="data/results/flood_risk/countries/{ISO3}/{ISO3}_{MODEL}-flood-risk_adapted_AAR_V-{VULN_CURVE}_fp_rp{RP}_duc{urban_class}.tif",
    output:
        regional_CI = "data/results/social_flood/countries/{ISO3}/inequality_metrics/{ISO3}_{ADMIN_SLUG}_metrics_{MODEL}-flood_adapted_AAR_V-{VULN_CURVE}_S-{SOCIAL}_fp_rp{RP}_duc{urban_class}.gpkg",
    wildcard_constraints:
        MODEL="giri|jrc|wri",
        VULN_CURVE="BER|JRC|EXP",
        SOCIAL="rwi|gdp",
        urban_class="11|12|13|21|22|23|30",
        ADMIN_SLUG="ADM0|ADM1|ADM2"
    script:
        "./inequality_metrics.py"
"""
Test with
snakemake -c1 data/results/social_flood/countries/KEN/inequality_metrics/KEN_ADM0_metrics_jrc-flood_adapted_AAR_V-JRC_S-rwi_fp_rp100_duc23.gpkg
"""

rule inequality_metrics_flood_protection_admin_decomposed:
    """
    This rule calculates the natioanl CI and its geospatial decomposition at the specified administrative level for the river flood protection scenario
    Inequality metrics:
        - Concentration Index (CI) - understand the inequality of flood risk across the wealth distribution
    """
    input:
        admin_areas = "data/inputs/boundaries/{ISO3}/geobounds_{ISO3}.gpkg",
        social_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_{SOCIAL}.tif",
        urban_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_ghs-mod_fixed.tif",
        pop_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_ghs-pop.tif",
        mask_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_surface_water.tif",
        risk_file="data/results/flood_risk/countries/{ISO3}/{ISO3}_{MODEL}-flood-risk_adapted_AAR_V-{VULN_CURVE}_fp_rp{RP}_duc{urban_class}.tif",
    output:
        regional_CI = "data/results/social_flood/countries/{ISO3}/inequality_metrics/{ISO3}_{ADMIN_SLUG}_admin-decomposed_metrics_{MODEL}-flood_adapted_AAR_V-{VULN_CURVE}_S-{SOCIAL}_fp_rp{RP}_duc{urban_class}.gpkg",
    wildcard_constraints:
        MODEL="giri|jrc|wri",
        VULN_CURVE="BER|JRC|EXP",
        SOCIAL="rwi|gdp",
        urban_class="11|12|13|21|22|23|30",
        ADMIN_SLUG="ADM1|ADM2"
    script:
        "./inequality_metrics_admin_decomposed.py"
"""
Test with
snakemake -c1 data/results/social_flood/countries/KEN/inequality_metrics/KEN_ADM1_admin-decomposed_metrics_jrc-flood_adapted_AAR_V-JRC_S-rwi_fp_rp100_duc30.gpkg
"""

rule inequality_metrics_relocation:
    """
    This rule calcualtes two inequality metrics at the specified administrative level for the relocation adaptation scenario.
    Adaptation parameter required as input is the max level of urbanization to relocate people from.
    Inequality metrics:
        - Concentration Index (CI) - understand the inequality of flood risk across the wealth distribution
        - Quantile Ratio (QR) - understand the tail inequality (20:80)
    """
    input:
        admin_areas = "data/inputs/boundaries/{ISO3}/geobounds_{ISO3}.gpkg",
        social_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_{SOCIAL}.tif",
        pop_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_ghs-pop.tif",
        mask_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_surface_water.tif",
        risk_file="data/results/flood_risk/countries/{ISO3}/{ISO3}_{MODEL}-flood-risk_adapted_AAR_V-{VULN_CURVE}_rl_duc{urban_class}.tif",
    output:
        regional_CI = "data/results/social_flood/countries/{ISO3}/inequality_metrics/{ISO3}_{ADMIN_SLUG}_metrics_{MODEL}-flood_adapted_AAR_V-{VULN_CURVE}_S-{SOCIAL}_rl_duc{urban_class}.gpkg",
    wildcard_constraints:
        MODEL="giri|jrc|wri",
        VULN_CURVE="BER|JRC|EXP",
        SOCIAL="rwi|gdp",
        urban_class="11|12|13|21|22|23|30",
        ADMIN_SLUG="ADM0|ADM1|ADM2"
    script:
        "./inequality_metrics.py"
"""
Test with
snakemake -c1 data/results/social_flood/countries/KEN/inequality_metrics/KEN_ADM0_metrics_jrc-flood_adapted_AAR_V-JRC_S-rwi_rl_duc23.gpkg
"""

rule inequality_metrics_relocation_admin_decomposed:
    """
    This rule calculates the natioanl CI and its geospatial decomposition at the specified administrative level for the relocation scenario
    Inequality metrics:
        - Concentration Index (CI) - understand the inequality of flood risk across the wealth distribution
    """
    input:
        admin_areas = "data/inputs/boundaries/{ISO3}/geobounds_{ISO3}.gpkg",
        social_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_{SOCIAL}.tif",
        urban_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_ghs-mod_fixed.tif",
        pop_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_ghs-pop.tif",
        mask_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_surface_water.tif",
        risk_file="data/results/flood_risk/countries/{ISO3}/{ISO3}_{MODEL}-flood-risk_adapted_AAR_V-{VULN_CURVE}_rl_duc{urban_class}.tif",
    output:
        regional_CI = "data/results/social_flood/countries/{ISO3}/inequality_metrics/{ISO3}_{ADMIN_SLUG}_admin-decomposed_metrics_{MODEL}-flood_adapted_AAR_V-{VULN_CURVE}_S-{SOCIAL}_rl_duc{urban_class}.gpkg",
    wildcard_constraints:
        MODEL="giri|jrc|wri",
        VULN_CURVE="BER|JRC|EXP",
        SOCIAL="rwi|gdp",
        urban_class="11|12|13|21|22|23|30",
        ADMIN_SLUG="ADM0|ADM1|ADM2"
    script:
        "./inequality_metrics_admin_decomposed.py"
"""
Test with
snakemake -c1 data/results/social_flood/countries/KEN/inequality_metrics/KEN_ADM0_metrics_admin-decomposed_jrc-flood_adapted_AAR_V-JRC_S-rwi_rl_duc23.gpkg
"""

rule inequality_metrics_dry_proofing:
    """
    This rule calcualtes two inequality metrics at the specified administrative level for the dry proofing adaptation scenario.
    Inequality metrics:
        - Concentration Index (CI) - understand the inequality of flood risk across the wealth distribution
        - Quantile Ratio (QR) - understand the tail inequality (20:80)
    """
    input:
        admin_areas = "data/inputs/boundaries/{ISO3}/geobounds_{ISO3}.gpkg",
        social_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_{SOCIAL}.tif",
        pop_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_ghs-pop.tif",
        mask_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_surface_water.tif",
        risk_file="data/results/flood_risk/countries/{ISO3}/{ISO3}_{MODEL}-flood-risk_adapted_AAR_V-{VULN_CURVE}_dp.tif",
    output:
        regional_CI = "data/results/social_flood/countries/{ISO3}/inequality_metrics/{ISO3}_{ADMIN_SLUG}_metrics_{MODEL}-flood_adapted_AAR_V-{VULN_CURVE}_S-{SOCIAL}_dp.gpkg",
    wildcard_constraints:
        MODEL="giri|jrc|wri",
        VULN_CURVE="BER|JRC|EXP",
        SOCIAL="rwi|gdp",
        ADMIN_SLUG="ADM0|ADM1|ADM2"
    script:
        "./inequality_metrics.py"
"""
Test with
snakemake -c1 data/results/social_flood/countries/KEN/inequality_metrics/KEN_ADM0_metrics_jrc-flood_adapted_AAR_V-JRC_S-rwi_dp.gpkg
"""

rule inequality_metrics_dry_proofing_admin_decomposed:
    """
    This rule calculates the natioanl CI and its geospatial decomposition at the specified administrative level for the dry-proofing scenario
    Inequality metrics:
        - Concentration Index (CI) - understand the inequality of flood risk across the wealth distribution
    """
    input:
        admin_areas = "data/inputs/boundaries/{ISO3}/geobounds_{ISO3}.gpkg",
        social_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_{SOCIAL}.tif",
        pop_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_ghs-pop.tif",
        urban_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_ghs-mod_fixed.tif",
        mask_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_surface_water.tif",
        risk_file="data/results/flood_risk/countries/{ISO3}/{ISO3}_{MODEL}-flood-risk_adapted_AAR_V-{VULN_CURVE}_dp.tif",
    output:
        regional_CI = "data/results/social_flood/countries/{ISO3}/inequality_metrics/{ISO3}_{ADMIN_SLUG}_admin-decomposed_metrics_{MODEL}-flood_adapted_AAR_V-{VULN_CURVE}_S-{SOCIAL}_dp.gpkg",
    wildcard_constraints:
        MODEL="giri|jrc|wri",
        VULN_CURVE="BER|JRC|EXP",
        SOCIAL="rwi|gdp",
        ADMIN_SLUG="ADM0|ADM1|ADM2"
    script:
        "./inequality_metrics_admin_decomposed.py"
"""
Test with
snakemake -c1 data/results/social_flood/countries/KEN/inequality_metrics/KEN_ADM0_metrics_admin-decomposed_jrc-flood_adapted_AAR_V-JRC_S-rwi_dp.gpkg
"""

rule inequality_metrics_observed:
    """
    This rule calcualtes two inequality metrics at the specified administrative level. For observed flooding datasets
    Inequality metrics:
        - Concentration Index (CI) - understand the inequality of flood risk across the wealth distribution
        - Quantile Ratio (QR) - understand the tail inequality (20:80)
    """
    input:
        admin_areas = "data/inputs/boundaries/{ISO3}/geobounds_{ISO3}.gpkg",
        social_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_{SOCIAL}.tif",
        pop_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_ghs-pop_{POP_YEAR}.tif",
        mask_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_surface_water.tif",
        risk_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_{MODEL}_{FLOOD_YEAR}_{TYPE}-flood.tif",
    output:
        regional_CI = "data/results/social_flood/countries/{ISO3}/inequality_metrics/{ISO3}_{ADMIN_SLUG}_metrics_{MODEL}_{FLOOD_YEAR}_{TYPE}-flood_S-{SOCIAL}_P-{POP_YEAR}.gpkg",
    wildcard_constraints:
        TYPE="coastal|inland",
        FLOOD_YEAR="all|early|late|2000|2001|2002|2003|2004|2005|2006|2007|2008|2009|2010|2011|2012|2013|2014|2015|2016|2017|2018",
        POP_YEAR="2000|interpolated-2001|interpolated-2002|interpolated-2003|interpolated-2004|"
                 "2005|interpolated-2006|interpolated-2007|interpolated-2008|interpolated-2009|"
                 "2010|interpolated-2011|interpolated-2012|interpolated-2013|interpolated-2014|"
                 "2015|interpolated-2016|interpolated-2017|interpolated-2018|2020",
        MODEL="gfd",
        SOCIAL="rwi|gdp",
        ADMIN_SLUG="ADM0|ADM1|ADM2"
    script:
        "./inequality_metrics.py"
"""
Test with
snakemake -c1 data/results/social_flood/countries/KEN/inequality_metrics/KEN_ADM0_metrics_gfd_all_coastal-flood_S-rwi_P-2015.gpkg
"""

rule inequality_metrics_observed_decomposed:
    """
    This rule calcualtes two inequality metrics at the specified administrative level. For observed flooding datasets
    Inequality metrics:
        - Concentration Index (CI) - understand the inequality of flood risk across the wealth distribution
        - Quantile Ratio (QR) - understand the tail inequality (20:80)
    """
    input:
        admin_areas = "data/inputs/boundaries/{ISO3}/geobounds_{ISO3}.gpkg",
        social_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_{SOCIAL}.tif",
        pop_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_ghs-pop.tif",
        urban_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_ghs-mod_fixed.tif",
        mask_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_surface_water.tif",
        risk_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_{MODEL}-flood.tif",
    output:
        regional_CI = "data/results/social_flood/countries/{ISO3}/inequality_metrics/{ISO3}_{ADMIN_SLUG}_decomposed_metrics_{MODEL}-flood_S-{SOCIAL}.gpkg",
    wildcard_constraints:
        MODEL="gfd",
        SOCIAL="rwi|gdp",
        ADMIN_SLUG="ADM0|ADM1|ADM2"
    script:
        "./inequality_metrics_decomposed.py"
"""
Test with
snakemake -c1 data/results/social_flood/countries/KEN/inequality_metrics/KEN_ADM0_decomposed_metrics_gfd-flood_S-rwi.gpkg
"""

rule inequality_metrics_observed_admin_decomposed:
    """
    This rule calculates the natioanl CI and its geospatial decomposition at the specified administrative level for the observed flooding
    Inequality metrics:
        - Concentration Index (CI) - understand the inequality of flood risk across the wealth distribution
    """
    input:
        admin_areas = "data/inputs/boundaries/{ISO3}/geobounds_{ISO3}.gpkg",
        social_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_{SOCIAL}.tif",
        urban_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_ghs-mod_fixed.tif",
        pop_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_ghs-pop.tif",
        mask_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_surface_water.tif",
        risk_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_{MODEL}-flood.tif",
    output:
        regional_CI = "data/results/social_flood/countries/{ISO3}/inequality_metrics/{ISO3}_{ADMIN_SLUG}_admin-decomposed_metrics_{MODEL}-flood_S-{SOCIAL}.gpkg",
    wildcard_constraints:
        MODEL="gfd",
        SOCIAL="rwi|gdp",
        ADMIN_SLUG="ADM1|ADM2"
    script:
        "./inequality_metrics_admin_decomposed.py"
"""
Test with
snakemake -c1 data/results/social_flood/countries/KEN/inequality_metrics/KEN_ADM1_admin-decomposed_metrics_gfd-flood_S-rwi.gpkg
"""

def get_event_iso3s(wildcards):
    """Return a list of valid ISO3 codes for an event by reading its properties file."""
    raw_id = str(wildcards.event_id)

    # Keep only digits (cluster whitespace issue fix)
    cleaned = re.sub(r"\D", "", raw_id)

    # Build the directory name
    event_dir = "DFO_" + cleaned

    # Build the path
    props_path = os.path.join(
        "data", "inputs", "analysis", "events", event_dir, "countries.json"
    )

    # Final safety: strip ALL spaces from the full path
    props_path = props_path.replace(" ", "")

    with open(props_path, "r") as f:
        props = json.load(f)

    return props["valid"]


rule dfo_event_analysis:
    """
    This rule carries out a risk assessment for individual dfo events.
    Reporting various metrics and returning a CSV file of results.
    """
    input:
        rwi_file = lambda wc: expand("data/inputs/analysis/countries/{ISO3}/{ISO3}_rwi.tif", ISO3=get_event_iso3s(wc)),
        pop_file = lambda wc: expand("data/inputs/analysis/countries/{ISO3}/{ISO3}_ghs-pop.tif", ISO3=get_event_iso3s(wc)),
        mask_file = lambda wc: expand("data/inputs/analysis/countries/{ISO3}/{ISO3}_surface_water.tif", ISO3=get_event_iso3s(wc)),
        urban_file= lambda wc: expand("data/inputs/analysis/countries/{ISO3}/{ISO3}_ghs-mod_fixed.tif", ISO3=get_event_iso3s(wc)),
        flood_file = lambda wc: expand("data/inputs/analysis/events/DFO_{event_id}/{ISO3}_{event_id}.tif", ISO3=get_event_iso3s(wc), event_id=wc.event_id),
        country_json="data/inputs/analysis/events/DFO_{event_id}/countries.json"
    output:
        results = "data/results/social_flood/events/DFO_{event_id}/DFO_{event_id}_results.csv"
    params:
        iso3_list = lambda wc: get_event_iso3s(wc)
    script:
        "./dfo_event_risk_analysis.py"

"""
Test with
snakemake -c1 data/results/social_flood/events/DFO_1595/DFO_1595_results.csv
"""


"""
Bulk run temporal observed floods.
"""

configfile: "config/config.yaml"

FLOOD_YEARS = [str(year) for year in range(2000, 2019)]

POP_YEAR_BY_FLOOD_YEAR = {
    year: year if int(year) % 5 == 0 else f"interpolated-{year}"
    for year in FLOOD_YEARS
}

TEMPORAL_INEQUALITY_TARGETS = [
    (
        f"data/results/social_flood/countries/{iso3}/inequality_metrics/"
        f"{iso3}_ADM0_metrics_gfd_{flood_year}_{flood_type}-flood_"
        f"S-rwi_P-{POP_YEAR_BY_FLOOD_YEAR[flood_year]}.gpkg"
    )
    for iso3 in config["iso_codes"]
    for flood_type in ["coastal", "inland"]
    for flood_year in FLOOD_YEARS
]


rule inequality_metrics_observed_temporal:
    input:
        TEMPORAL_INEQUALITY_TARGETS

FLOOD_TYPES = ['coastal', 'inland']
POP_YEARS = ['2000', '2005', '2010', '2015', '2020']

rule pop_temporal_observed:
    input:
        expand("data/results/social_flood/countries/{ISO3}/inequality_metrics/{ISO3}_ADM0_metrics_gfd_all_{TYPE}-flood_S-rwi_P-{POP_YEAR}.gpkg",
            ISO3=config['iso_codes'], TYPE=FLOOD_TYPES, POP_YEAR=POP_YEARS)

rule static_pop_temporal_observed:
    input:
        expand("data/results/social_flood/countries/{ISO3}/inequality_metrics/{ISO3}_ADM0_metrics_gfd_{FLOOD_YEAR}_{TYPE}-flood_S-rwi_P-2000.gpkg",
            ISO3=config['iso_codes'], FLOOD_YEAR=FLOOD_YEARS, TYPE=FLOOD_TYPES)