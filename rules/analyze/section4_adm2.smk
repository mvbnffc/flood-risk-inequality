"""
Section 4 (revision) - flood protection for every admin unit with a river, and one table of
admin-unit risk by NATIONAL wealth quintile for the targeting analysis in the notebook.

New rules only. Add to the Snakefile:
    include: "rules/analyze/section4_adm2.smk"

Targets:
    snakemake -c1 section4_adm2_test     # RWA only
    snakemake -c4 -k section4_adm2       # all countries (ADM2, JRC, RWI)
    snakemake -c4 -R flood_protection_costs section4_fp_costs_adm0
                                         # re-run the paper's national (duc30) costs with the corrected formula

Files to copy back for the notebook:
    data/results/section4_adm2/section4_adm2_ADM2_jrc-flood_S-rwi.csv
    data/results/section4_adm2/section4_adm2_ADM2_jrc-flood_S-rwi_checks.csv

Chain for one country (ADM2, JRC):
    prepare_admin_flood_protection.py  -> {ISO3}_adaptation_fp_rp100_all-ADM2.tif + per-unit costs
    *_average_annual_risk_protected.py -> adapted risk for V-JRC / V-NRES / V-INFR (existing scripts,
                                          run with the adapted FLOPROS raster)
    section4_adm2_table.py             -> per-unit table (base, fp, dp, rl)
    section4_adm2_combine.py           -> one wide table for all countries, costs joined on shapeID

Countries without an ADM2 layer fall back to ADM1 (the admin_level column says which was used).
Dry-proofing and relocation (duc13) use the existing scenario rasters and the existing cost rules.
"""

import os
import sqlite3


def s4_level(iso, wanted):
    """Deepest available admin layer <= wanted in geobounds_{iso}.gpkg."""
    path = f"data/inputs/boundaries/{iso}/geobounds_{iso}.gpkg"
    order = ["ADM2", "ADM1"]
    candidates = order[order.index(wanted):] if wanted in order else [wanted]
    if not os.path.exists(path):
        return wanted
    try:
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        layers = {row[0] for row in con.execute("SELECT table_name FROM gpkg_contents")}
        con.close()
    except Exception:
        return wanted
    for level in candidates:
        if level in layers:
            return level
    return wanted


def s4_country_files(wildcards, kind):
    out = []
    for iso in config["iso_codes"]:
        level = s4_level(iso, wildcards.ADMIN_SLUG)
        if kind in ("units", "checks"):
            out.append(
                f"data/results/section4_adm2/countries/{iso}/"
                f"{iso}_{level}_{kind}_{wildcards.MODEL}-flood_S-{wildcards.SOCIAL}.csv"
            )
        elif kind == "fp":
            out.append(f"data/results/adaptation/costs/countries/{iso}/{iso}_adaptation-cost_fp_rp100_all-{level}.gpkg")
        elif kind == "dp":
            out.append(f"data/results/adaptation/costs/countries/{iso}/{iso}_adaptation-cost_dp_m-{wildcards.MODEL}_{level}.gpkg")
        elif kind == "rl":
            out.append(f"data/results/adaptation/costs/countries/{iso}/{iso}_adaptation-cost_rl_m-{wildcards.MODEL}_duc13_{level}.gpkg")
    return out


rule prepare_admin_flood_protection:
    """
    Raise FLOPROS to RP in every admin unit with a river; cost each river segment against
    the FLOPROS along it (Boulange et al. 2023, log2 of the ratio of return periods).
    """
    input:
        flopros="data/inputs/analysis/countries/{ISO3}/{ISO3}_flopros.tif",
        rivers="data/inputs/analysis/countries/{ISO3}/{ISO3}_river_network.gpkg",
        admin_areas="data/inputs/boundaries/{ISO3}/geobounds_{ISO3}.gpkg",
        gdppc="config/gdppc_data.csv",
    output:
        flood_protection="data/inputs/analysis/countries/{ISO3}/{ISO3}_adaptation_fp_rp{RP}_all-{ADMIN_SLUG}.tif",
        protection_cost="data/results/adaptation/costs/countries/{ISO3}/{ISO3}_adaptation-cost_fp_rp{RP}_all-{ADMIN_SLUG}.gpkg",
        segments="data/results/adaptation/costs/countries/{ISO3}/{ISO3}_adaptation-cost_fp_rp{RP}_all-{ADMIN_SLUG}_segments.csv",
    wildcard_constraints:
        ISO3="[A-Z][A-Z][A-Z]",
        RP="[0-9]+",
        ADMIN_SLUG="ADM1|ADM2",
    script:
        "../prepare/prepare_admin_flood_protection.py"


rule jrc_average_annual_risk_adapted_fp_admin:
    """Existing protected-risk script, run with the admin-protection FLOPROS raster."""
    input:
        flood_rp_10="data/results/flood_risk/countries/{ISO3}/{ISO3}_jrc-flood-risk_RP10_V-{VULN_CURVE}.tif",
        flood_rp_20="data/results/flood_risk/countries/{ISO3}/{ISO3}_jrc-flood-risk_RP20_V-{VULN_CURVE}.tif",
        flood_rp_50="data/results/flood_risk/countries/{ISO3}/{ISO3}_jrc-flood-risk_RP50_V-{VULN_CURVE}.tif",
        flood_rp_75="data/results/flood_risk/countries/{ISO3}/{ISO3}_jrc-flood-risk_RP75_V-{VULN_CURVE}.tif",
        flood_rp_100="data/results/flood_risk/countries/{ISO3}/{ISO3}_jrc-flood-risk_RP100_V-{VULN_CURVE}.tif",
        flood_rp_200="data/results/flood_risk/countries/{ISO3}/{ISO3}_jrc-flood-risk_RP200_V-{VULN_CURVE}.tif",
        flood_rp_500="data/results/flood_risk/countries/{ISO3}/{ISO3}_jrc-flood-risk_RP500_V-{VULN_CURVE}.tif",
        flopros="data/inputs/analysis/countries/{ISO3}/{ISO3}_adaptation_fp_rp{RP}_all-{ADMIN_SLUG}.tif",
    output:
        flood_aar_protected="data/results/flood_risk/countries/{ISO3}/{ISO3}_jrc-flood-risk_adapted_AAR_V-{VULN_CURVE}_fp_rp{RP}_all-{ADMIN_SLUG}.tif",
    wildcard_constraints:
        ISO3="[A-Z][A-Z][A-Z]",
        VULN_CURVE="BER|JRC|EXP|NRES|INFR",
        RP="[0-9]+",
        ADMIN_SLUG="ADM1|ADM2",
    script:
        "./jrc_average_annual_risk_protected.py"


rule giri_average_annual_risk_adapted_fp_admin:
    """Existing protected-risk script, run with the admin-protection FLOPROS raster."""
    input:
        flood_rp_5="data/results/flood_risk/countries/{ISO3}/{ISO3}_giri-flood-risk_RP5_V-{VULN_CURVE}.tif",
        flood_rp_10="data/results/flood_risk/countries/{ISO3}/{ISO3}_giri-flood-risk_RP10_V-{VULN_CURVE}.tif",
        flood_rp_25="data/results/flood_risk/countries/{ISO3}/{ISO3}_giri-flood-risk_RP25_V-{VULN_CURVE}.tif",
        flood_rp_50="data/results/flood_risk/countries/{ISO3}/{ISO3}_giri-flood-risk_RP50_V-{VULN_CURVE}.tif",
        flood_rp_100="data/results/flood_risk/countries/{ISO3}/{ISO3}_giri-flood-risk_RP100_V-{VULN_CURVE}.tif",
        flood_rp_200="data/results/flood_risk/countries/{ISO3}/{ISO3}_giri-flood-risk_RP200_V-{VULN_CURVE}.tif",
        flood_rp_500="data/results/flood_risk/countries/{ISO3}/{ISO3}_giri-flood-risk_RP500_V-{VULN_CURVE}.tif",
        flood_rp_1000="data/results/flood_risk/countries/{ISO3}/{ISO3}_giri-flood-risk_RP1000_V-{VULN_CURVE}.tif",
        flopros="data/inputs/analysis/countries/{ISO3}/{ISO3}_adaptation_fp_rp{RP}_all-{ADMIN_SLUG}.tif",
    output:
        flood_aar_protected="data/results/flood_risk/countries/{ISO3}/{ISO3}_giri-flood-risk_adapted_AAR_V-{VULN_CURVE}_fp_rp{RP}_all-{ADMIN_SLUG}.tif",
    wildcard_constraints:
        ISO3="[A-Z][A-Z][A-Z]",
        VULN_CURVE="BER|JRC|EXP|NRES|INFR",
        RP="[0-9]+",
        ADMIN_SLUG="ADM1|ADM2",
    script:
        "./giri_average_annual_risk_protected.py"


rule wri_average_annual_risk_adapted_fp_admin:
    """Existing protected-risk script, run with the admin-protection FLOPROS raster."""
    input:
        flood_rp_2="data/results/flood_risk/countries/{ISO3}/{ISO3}_wri-flood-risk_RP2_V-{VULN_CURVE}.tif",
        flood_rp_5="data/results/flood_risk/countries/{ISO3}/{ISO3}_wri-flood-risk_RP5_V-{VULN_CURVE}.tif",
        flood_rp_10="data/results/flood_risk/countries/{ISO3}/{ISO3}_wri-flood-risk_RP10_V-{VULN_CURVE}.tif",
        flood_rp_25="data/results/flood_risk/countries/{ISO3}/{ISO3}_wri-flood-risk_RP25_V-{VULN_CURVE}.tif",
        flood_rp_50="data/results/flood_risk/countries/{ISO3}/{ISO3}_wri-flood-risk_RP50_V-{VULN_CURVE}.tif",
        flood_rp_100="data/results/flood_risk/countries/{ISO3}/{ISO3}_wri-flood-risk_RP100_V-{VULN_CURVE}.tif",
        flood_rp_250="data/results/flood_risk/countries/{ISO3}/{ISO3}_wri-flood-risk_RP250_V-{VULN_CURVE}.tif",
        flood_rp_500="data/results/flood_risk/countries/{ISO3}/{ISO3}_wri-flood-risk_RP500_V-{VULN_CURVE}.tif",
        flood_rp_1000="data/results/flood_risk/countries/{ISO3}/{ISO3}_wri-flood-risk_RP1000_V-{VULN_CURVE}.tif",
        flopros="data/inputs/analysis/countries/{ISO3}/{ISO3}_adaptation_fp_rp{RP}_all-{ADMIN_SLUG}.tif",
    output:
        flood_aar_protected="data/results/flood_risk/countries/{ISO3}/{ISO3}_wri-flood-risk_adapted_AAR_V-{VULN_CURVE}_fp_rp{RP}_all-{ADMIN_SLUG}.tif",
    wildcard_constraints:
        ISO3="[A-Z][A-Z][A-Z]",
        VULN_CURVE="BER|JRC|EXP|NRES|INFR",
        RP="[0-9]+",
        ADMIN_SLUG="ADM1|ADM2",
    script:
        "./wri_average_annual_risk_protected.py"


rule section4_adm2_table:
    """
    Per admin unit and scenario: population, people-weighted risk by NATIONAL wealth quintile,
    exact rank sum, and capital stock losses. See section4_adm2_table.py.
    """
    input:
        admin_areas="data/inputs/boundaries/{ISO3}/geobounds_{ISO3}.gpkg",
        social_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_{SOCIAL}.tif",
        pop_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_ghs-pop_2020.tif",
        mask_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_surface_water.tif",
        res_capstock="data/inputs/analysis/countries/{ISO3}/{ISO3}_res_capstock.tif",
        nres_capstock="data/inputs/analysis/countries/{ISO3}/{ISO3}_nres_capstock.tif",
        infr_capstock="data/inputs/analysis/countries/{ISO3}/{ISO3}_inf_capstock.tif",
        base_res="data/results/flood_risk/countries/{ISO3}/{ISO3}_{MODEL}-flood-risk_protected_AAR_V-JRC.tif",
        base_nres="data/results/flood_risk/countries/{ISO3}/{ISO3}_{MODEL}-flood-risk_protected_AAR_V-NRES.tif",
        base_infr="data/results/flood_risk/countries/{ISO3}/{ISO3}_{MODEL}-flood-risk_protected_AAR_V-INFR.tif",
        fp_res="data/results/flood_risk/countries/{ISO3}/{ISO3}_{MODEL}-flood-risk_adapted_AAR_V-JRC_fp_rp100_all-{ADMIN_SLUG}.tif",
        fp_nres="data/results/flood_risk/countries/{ISO3}/{ISO3}_{MODEL}-flood-risk_adapted_AAR_V-NRES_fp_rp100_all-{ADMIN_SLUG}.tif",
        fp_infr="data/results/flood_risk/countries/{ISO3}/{ISO3}_{MODEL}-flood-risk_adapted_AAR_V-INFR_fp_rp100_all-{ADMIN_SLUG}.tif",
        dp_res="data/results/flood_risk/countries/{ISO3}/{ISO3}_{MODEL}-flood-risk_adapted_AAR_V-JRC_dp.tif",
        rl_res="data/results/flood_risk/countries/{ISO3}/{ISO3}_{MODEL}-flood-risk_adapted_AAR_V-JRC_rl_duc13.tif",
    output:
        units="data/results/section4_adm2/countries/{ISO3}/{ISO3}_{ADMIN_SLUG}_units_{MODEL}-flood_S-{SOCIAL}.csv",
        checks="data/results/section4_adm2/countries/{ISO3}/{ISO3}_{ADMIN_SLUG}_checks_{MODEL}-flood_S-{SOCIAL}.csv",
    wildcard_constraints:
        ISO3="[A-Z][A-Z][A-Z]",
        MODEL="giri|jrc|wri",
        SOCIAL="rwi|frwi",
        ADMIN_SLUG="ADM1|ADM2",
    script:
        "./section4_adm2_table.py"


rule section4_adm2_combine:
    """One wide table for all countries, with the admin-unit costs joined on shapeID."""
    input:
        units=lambda wc: s4_country_files(wc, "units"),
        checks=lambda wc: s4_country_files(wc, "checks"),
        fp_costs=lambda wc: s4_country_files(wc, "fp"),
        dp_costs=lambda wc: s4_country_files(wc, "dp"),
        rl_costs=lambda wc: s4_country_files(wc, "rl"),
    params:
        iso_codes=lambda wc: config["iso_codes"],
    output:
        units="data/results/section4_adm2/section4_adm2_{ADMIN_SLUG}_{MODEL}-flood_S-{SOCIAL}.csv",
        checks="data/results/section4_adm2/section4_adm2_{ADMIN_SLUG}_{MODEL}-flood_S-{SOCIAL}_checks.csv",
    wildcard_constraints:
        MODEL="giri|jrc|wri",
        SOCIAL="rwi|frwi",
        ADMIN_SLUG="ADM1|ADM2",
    script:
        "./section4_adm2_combine.py"


rule section4_adm2:
    input:
        "data/results/section4_adm2/section4_adm2_ADM2_jrc-flood_S-rwi.csv",


rule section4_adm2_test:
    input:
        "data/results/section4_adm2/countries/RWA/RWA_ADM2_units_jrc-flood_S-rwi.csv",
        "data/results/adaptation/costs/countries/RWA/RWA_adaptation-cost_fp_rp100_all-ADM2.gpkg",
        "data/results/adaptation/costs/countries/RWA/RWA_adaptation-cost_dp_m-jrc_ADM2.gpkg",
        "data/results/adaptation/costs/countries/RWA/RWA_adaptation-cost_rl_m-jrc_duc13_ADM2.gpkg",


rule section4_fp_costs_adm0:
    """The paper's national flood protection costs (RP100, duc30), for re-running with the corrected formula."""
    input:
        lambda wc: expand(
            "data/results/adaptation/costs/countries/{ISO3}/{ISO3}_adaptation-cost_fp_rp100_duc30_ADM0.gpkg",
            ISO3=config["iso_codes"],
        ),
