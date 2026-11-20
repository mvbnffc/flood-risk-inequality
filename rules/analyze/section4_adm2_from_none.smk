"""
Section 4 scenario 2 - raise protection to RP100 starting from NO protection (2 years everywhere)
instead of from FLOPROS. Same scripts as section4_adm2.smk; every output carries "_from-none",
so the FLOPROS scenario (and Sections 2-3) are untouched.

Add to the Snakefile, after section4_adm2.smk (it uses s4_level from there):
    include: "rules/analyze/section4_adm2_from_none.smk"

Targets:
    snakemake -n section4_none_test                  # dry run, RWA only
    snakemake -c1 section4_none_test                 # RWA only
    snakemake -c4 -k --rerun-incomplete section4_none_both     # all countries, JRC and GIRI

Files to copy back for the notebook:
    data/results/section4_adm2/section4_adm2_ADM2_{jrc,giri}-flood_S-rwi_from-none.csv
    data/results/section4_adm2/section4_adm2_ADM2_{jrc,giri}-flood_S-rwi_from-none_checks.csv

Chain for one country (ADM2, JRC):
    flopros_none.py                    -> {ISO3}_flopros-none.tif (2 years inside the country)
    jrc_average_annual_risk_protected.py with the 2-year raster      -> baseline risk (from-none)
    prepare_admin_flood_protection.py with the 2-year raster         -> RP100 in every unit with a river + costs
    jrc_average_annual_risk_protected.py with that raised raster     -> adapted risk (from-none)
    section4_adm2_table.py / section4_adm2_combine.py                -> tables with "_from-none"
"""


def s4_none_country_files(wildcards, kind):
    out = []
    for iso in config["iso_codes"]:
        level = s4_level(iso, wildcards.ADMIN_SLUG)
        if kind in ("units", "checks"):
            out.append(
                f"data/results/section4_adm2/countries/{iso}/"
                f"{iso}_{level}_{kind}_{wildcards.MODEL}-flood_S-{wildcards.SOCIAL}_from-none.csv"
            )
        elif kind == "fp":
            out.append(f"data/results/adaptation/costs/countries/{iso}/{iso}_adaptation-cost_fp_rp100_all-{level}_from-none.gpkg")
    return out


rule flopros_none:
    """2-year protection everywhere in the country (no-protection baseline)."""
    input:
        flopros="data/inputs/analysis/countries/{ISO3}/{ISO3}_flopros.tif",
    output:
        flopros_none="data/inputs/analysis/countries/{ISO3}/{ISO3}_flopros-none.tif",
    wildcard_constraints:
        ISO3="[A-Z][A-Z][A-Z]",
    script:
        "../prepare/flopros_none.py"


rule jrc_average_annual_risk_from_none:
    """Baseline risk with no protection (existing protected-risk script, 2-year raster)."""
    input:
        flood_rp_10="data/results/flood_risk/countries/{ISO3}/{ISO3}_jrc-flood-risk_RP10_V-{VULN_CURVE}.tif",
        flood_rp_20="data/results/flood_risk/countries/{ISO3}/{ISO3}_jrc-flood-risk_RP20_V-{VULN_CURVE}.tif",
        flood_rp_50="data/results/flood_risk/countries/{ISO3}/{ISO3}_jrc-flood-risk_RP50_V-{VULN_CURVE}.tif",
        flood_rp_75="data/results/flood_risk/countries/{ISO3}/{ISO3}_jrc-flood-risk_RP75_V-{VULN_CURVE}.tif",
        flood_rp_100="data/results/flood_risk/countries/{ISO3}/{ISO3}_jrc-flood-risk_RP100_V-{VULN_CURVE}.tif",
        flood_rp_200="data/results/flood_risk/countries/{ISO3}/{ISO3}_jrc-flood-risk_RP200_V-{VULN_CURVE}.tif",
        flood_rp_500="data/results/flood_risk/countries/{ISO3}/{ISO3}_jrc-flood-risk_RP500_V-{VULN_CURVE}.tif",
        flopros="data/inputs/analysis/countries/{ISO3}/{ISO3}_flopros-none.tif",
    output:
        flood_aar_protected="data/results/flood_risk/countries/{ISO3}/{ISO3}_jrc-flood-risk_from-none_AAR_V-{VULN_CURVE}.tif",
    wildcard_constraints:
        ISO3="[A-Z][A-Z][A-Z]",
        VULN_CURVE="BER|JRC|EXP|NRES|INFR",
    script:
        "./jrc_average_annual_risk_protected.py"


rule giri_average_annual_risk_from_none:
    """Baseline risk with no protection (existing protected-risk script, 2-year raster)."""
    input:
        flood_rp_5="data/results/flood_risk/countries/{ISO3}/{ISO3}_giri-flood-risk_RP5_V-{VULN_CURVE}.tif",
        flood_rp_10="data/results/flood_risk/countries/{ISO3}/{ISO3}_giri-flood-risk_RP10_V-{VULN_CURVE}.tif",
        flood_rp_25="data/results/flood_risk/countries/{ISO3}/{ISO3}_giri-flood-risk_RP25_V-{VULN_CURVE}.tif",
        flood_rp_50="data/results/flood_risk/countries/{ISO3}/{ISO3}_giri-flood-risk_RP50_V-{VULN_CURVE}.tif",
        flood_rp_100="data/results/flood_risk/countries/{ISO3}/{ISO3}_giri-flood-risk_RP100_V-{VULN_CURVE}.tif",
        flood_rp_200="data/results/flood_risk/countries/{ISO3}/{ISO3}_giri-flood-risk_RP200_V-{VULN_CURVE}.tif",
        flood_rp_500="data/results/flood_risk/countries/{ISO3}/{ISO3}_giri-flood-risk_RP500_V-{VULN_CURVE}.tif",
        flood_rp_1000="data/results/flood_risk/countries/{ISO3}/{ISO3}_giri-flood-risk_RP1000_V-{VULN_CURVE}.tif",
        flopros="data/inputs/analysis/countries/{ISO3}/{ISO3}_flopros-none.tif",
    output:
        flood_aar_protected="data/results/flood_risk/countries/{ISO3}/{ISO3}_giri-flood-risk_from-none_AAR_V-{VULN_CURVE}.tif",
    wildcard_constraints:
        ISO3="[A-Z][A-Z][A-Z]",
        VULN_CURVE="BER|JRC|EXP|NRES|INFR",
    script:
        "./giri_average_annual_risk_protected.py"


rule prepare_admin_flood_protection_from_none:
    """Raise the 2-year raster to RP in every admin unit with a river; cost from 2 years."""
    input:
        flopros="data/inputs/analysis/countries/{ISO3}/{ISO3}_flopros-none.tif",
        rivers="data/inputs/analysis/countries/{ISO3}/{ISO3}_river_network.gpkg",
        admin_areas="data/inputs/boundaries/{ISO3}/geobounds_{ISO3}.gpkg",
        gdppc="config/gdppc_data.csv",
    output:
        flood_protection="data/inputs/analysis/countries/{ISO3}/{ISO3}_adaptation_fp_rp{RP}_all-{ADMIN_SLUG}_from-none.tif",
        protection_cost="data/results/adaptation/costs/countries/{ISO3}/{ISO3}_adaptation-cost_fp_rp{RP}_all-{ADMIN_SLUG}_from-none.gpkg",
        segments="data/results/adaptation/costs/countries/{ISO3}/{ISO3}_adaptation-cost_fp_rp{RP}_all-{ADMIN_SLUG}_from-none_segments.csv",
    wildcard_constraints:
        ISO3="[A-Z][A-Z][A-Z]",
        RP="[0-9]+",
        ADMIN_SLUG="ADM1|ADM2",
    script:
        "../prepare/prepare_admin_flood_protection.py"


rule jrc_average_annual_risk_adapted_fp_admin_from_none:
    """Adapted risk (RP100 in every unit with a river, no protection elsewhere)."""
    input:
        flood_rp_10="data/results/flood_risk/countries/{ISO3}/{ISO3}_jrc-flood-risk_RP10_V-{VULN_CURVE}.tif",
        flood_rp_20="data/results/flood_risk/countries/{ISO3}/{ISO3}_jrc-flood-risk_RP20_V-{VULN_CURVE}.tif",
        flood_rp_50="data/results/flood_risk/countries/{ISO3}/{ISO3}_jrc-flood-risk_RP50_V-{VULN_CURVE}.tif",
        flood_rp_75="data/results/flood_risk/countries/{ISO3}/{ISO3}_jrc-flood-risk_RP75_V-{VULN_CURVE}.tif",
        flood_rp_100="data/results/flood_risk/countries/{ISO3}/{ISO3}_jrc-flood-risk_RP100_V-{VULN_CURVE}.tif",
        flood_rp_200="data/results/flood_risk/countries/{ISO3}/{ISO3}_jrc-flood-risk_RP200_V-{VULN_CURVE}.tif",
        flood_rp_500="data/results/flood_risk/countries/{ISO3}/{ISO3}_jrc-flood-risk_RP500_V-{VULN_CURVE}.tif",
        flopros="data/inputs/analysis/countries/{ISO3}/{ISO3}_adaptation_fp_rp{RP}_all-{ADMIN_SLUG}_from-none.tif",
    output:
        flood_aar_protected="data/results/flood_risk/countries/{ISO3}/{ISO3}_jrc-flood-risk_adapted_AAR_V-{VULN_CURVE}_fp_rp{RP}_all-{ADMIN_SLUG}_from-none.tif",
    wildcard_constraints:
        ISO3="[A-Z][A-Z][A-Z]",
        VULN_CURVE="BER|JRC|EXP|NRES|INFR",
        RP="[0-9]+",
        ADMIN_SLUG="ADM1|ADM2",
    script:
        "./jrc_average_annual_risk_protected.py"


rule giri_average_annual_risk_adapted_fp_admin_from_none:
    """Adapted risk (RP100 in every unit with a river, no protection elsewhere)."""
    input:
        flood_rp_5="data/results/flood_risk/countries/{ISO3}/{ISO3}_giri-flood-risk_RP5_V-{VULN_CURVE}.tif",
        flood_rp_10="data/results/flood_risk/countries/{ISO3}/{ISO3}_giri-flood-risk_RP10_V-{VULN_CURVE}.tif",
        flood_rp_25="data/results/flood_risk/countries/{ISO3}/{ISO3}_giri-flood-risk_RP25_V-{VULN_CURVE}.tif",
        flood_rp_50="data/results/flood_risk/countries/{ISO3}/{ISO3}_giri-flood-risk_RP50_V-{VULN_CURVE}.tif",
        flood_rp_100="data/results/flood_risk/countries/{ISO3}/{ISO3}_giri-flood-risk_RP100_V-{VULN_CURVE}.tif",
        flood_rp_200="data/results/flood_risk/countries/{ISO3}/{ISO3}_giri-flood-risk_RP200_V-{VULN_CURVE}.tif",
        flood_rp_500="data/results/flood_risk/countries/{ISO3}/{ISO3}_giri-flood-risk_RP500_V-{VULN_CURVE}.tif",
        flood_rp_1000="data/results/flood_risk/countries/{ISO3}/{ISO3}_giri-flood-risk_RP1000_V-{VULN_CURVE}.tif",
        flopros="data/inputs/analysis/countries/{ISO3}/{ISO3}_adaptation_fp_rp{RP}_all-{ADMIN_SLUG}_from-none.tif",
    output:
        flood_aar_protected="data/results/flood_risk/countries/{ISO3}/{ISO3}_giri-flood-risk_adapted_AAR_V-{VULN_CURVE}_fp_rp{RP}_all-{ADMIN_SLUG}_from-none.tif",
    wildcard_constraints:
        ISO3="[A-Z][A-Z][A-Z]",
        VULN_CURVE="BER|JRC|EXP|NRES|INFR",
        RP="[0-9]+",
        ADMIN_SLUG="ADM1|ADM2",
    script:
        "./giri_average_annual_risk_protected.py"


rule section4_adm2_table_from_none:
    """Per-unit table (base = no protection, fp = RP100 in units with a river)."""
    input:
        admin_areas="data/inputs/boundaries/{ISO3}/geobounds_{ISO3}.gpkg",
        social_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_{SOCIAL}.tif",
        pop_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_ghs-pop_2020.tif",
        mask_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_surface_water.tif",
        res_capstock="data/inputs/analysis/countries/{ISO3}/{ISO3}_res_capstock.tif",
        nres_capstock="data/inputs/analysis/countries/{ISO3}/{ISO3}_nres_capstock.tif",
        infr_capstock="data/inputs/analysis/countries/{ISO3}/{ISO3}_inf_capstock.tif",
        base_res="data/results/flood_risk/countries/{ISO3}/{ISO3}_{MODEL}-flood-risk_from-none_AAR_V-JRC.tif",
        base_nres="data/results/flood_risk/countries/{ISO3}/{ISO3}_{MODEL}-flood-risk_from-none_AAR_V-NRES.tif",
        base_infr="data/results/flood_risk/countries/{ISO3}/{ISO3}_{MODEL}-flood-risk_from-none_AAR_V-INFR.tif",
        fp_res="data/results/flood_risk/countries/{ISO3}/{ISO3}_{MODEL}-flood-risk_adapted_AAR_V-JRC_fp_rp100_all-{ADMIN_SLUG}_from-none.tif",
        fp_nres="data/results/flood_risk/countries/{ISO3}/{ISO3}_{MODEL}-flood-risk_adapted_AAR_V-NRES_fp_rp100_all-{ADMIN_SLUG}_from-none.tif",
        fp_infr="data/results/flood_risk/countries/{ISO3}/{ISO3}_{MODEL}-flood-risk_adapted_AAR_V-INFR_fp_rp100_all-{ADMIN_SLUG}_from-none.tif",
    output:
        units="data/results/section4_adm2/countries/{ISO3}/{ISO3}_{ADMIN_SLUG}_units_{MODEL}-flood_S-{SOCIAL}_from-none.csv",
        checks="data/results/section4_adm2/countries/{ISO3}/{ISO3}_{ADMIN_SLUG}_checks_{MODEL}-flood_S-{SOCIAL}_from-none.csv",
    wildcard_constraints:
        ISO3="[A-Z][A-Z][A-Z]",
        MODEL="giri|jrc",
        SOCIAL="rwi|frwi",
        ADMIN_SLUG="ADM1|ADM2",
    script:
        "./section4_adm2_table.py"


rule section4_adm2_combine_from_none:
    """One wide table for all countries (no-protection baseline), costs joined on shapeID."""
    input:
        units=lambda wc: s4_none_country_files(wc, "units"),
        checks=lambda wc: s4_none_country_files(wc, "checks"),
        fp_costs=lambda wc: s4_none_country_files(wc, "fp"),
    params:
        iso_codes=lambda wc: config["iso_codes"],
    output:
        units="data/results/section4_adm2/section4_adm2_{ADMIN_SLUG}_{MODEL}-flood_S-{SOCIAL}_from-none.csv",
        checks="data/results/section4_adm2/section4_adm2_{ADMIN_SLUG}_{MODEL}-flood_S-{SOCIAL}_from-none_checks.csv",
    wildcard_constraints:
        MODEL="giri|jrc",
        SOCIAL="rwi|frwi",
        ADMIN_SLUG="ADM1|ADM2",
    script:
        "./section4_adm2_combine.py"


rule section4_none_both:
    input:
        "data/results/section4_adm2/section4_adm2_ADM2_jrc-flood_S-rwi_from-none.csv",
        "data/results/section4_adm2/section4_adm2_ADM2_giri-flood_S-rwi_from-none.csv",


rule section4_none_test:
    input:
        "data/results/section4_adm2/countries/RWA/RWA_ADM2_units_jrc-flood_S-rwi_from-none.csv",
        "data/results/adaptation/costs/countries/RWA/RWA_adaptation-cost_fp_rp100_all-ADM2_from-none.gpkg",
