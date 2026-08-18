rule tool_baseline_capital_stock_losses:
    """
    Rule summarizes capital stock losses per admin region
    """
    input:
        admin_areas = "data/inputs/boundaries/{ISO3}/geobounds_{ISO3}.gpkg",
        res_risk_file="data/results/flood_risk/countries/{ISO3}/{ISO3}_{MODEL}-flood-risk_{metric}_V-JRC.tif",
        nres_risk_file="data/results/flood_risk/countries/{ISO3}/{ISO3}_{MODEL}-flood-risk_{metric}_V-NRES.tif",
        infr_risk_file="data/results/flood_risk/countries/{ISO3}/{ISO3}_{MODEL}-flood-risk_{metric}_V-INFR.tif",
        res_capstock_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_res_capstock.tif",
        nres_capstock_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_nres_capstock.tif",
        infr_capstock_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_inf_capstock.tif",
        mask_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_surface_water.tif"
    output:
        regional_losses = "data/results/national_tooling/countries/{ISO3}/{ISO3}_{ADMIN_SLUG}_metrics_{MODEL}-flood_{metric}_baseline_capstock.gpkg",
    wildcard_constraints:
        metric="protected_AAR|RP10|RP20|RP50|RP75|RP100|RP200|RP500",
        MODEL="jrc",
        ADMIN_SLUG="ADM0|ADM1|ADM2"
    script:
        "./capital_stock_losses.py"
"""
Test with
snakemake -c1 data/results/national_tooling/countries/KEN/KEN_ADM2_metrics_jrc-flood_protected_AAR_baseline_capstock.gpkg 
"""

rule tool_adapted_capital_stock_losses:
    """
    Rule summarizes capital stock losses per admin region
    """
    input:
        admin_areas = "data/inputs/boundaries/{ISO3}/geobounds_{ISO3}.gpkg",
        res_risk_file="data/results/flood_risk/countries/{ISO3}/{ISO3}_{MODEL}-flood-risk_adapted_AAR_V-JRC_fp_rp{RP}_duc{urban_class}.tif",
        nres_risk_file="data/results/flood_risk/countries/{ISO3}/{ISO3}_{MODEL}-flood-risk_adapted_AAR_V-NRES_fp_rp{RP}_duc{urban_class}.tif",
        infr_risk_file="data/results/flood_risk/countries/{ISO3}/{ISO3}_{MODEL}-flood-risk_adapted_AAR_V-INFR_fp_rp{RP}_duc{urban_class}.tif",
        res_capstock_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_res_capstock.tif",
        nres_capstock_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_nres_capstock.tif",
        infr_capstock_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_inf_capstock.tif",
        mask_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_surface_water.tif"
    output:
        regional_losses = "data/results/national_tooling/countries/{ISO3}/{ISO3}_{ADMIN_SLUG}_metrics_{MODEL}-flood_AALs_adapted_fp_rp{RP}_duc{urban_class}_capstock.gpkg",
    wildcard_constraints:
        MODEL="jrc",
        ADMIN_SLUG="ADM0|ADM1|ADM2",
        urban_class="11|12|13|21|22|23|30"
    script:
        "./capital_stock_losses.py"
"""
Test with
snakemake -c1 data/results/national_tooling/countries/KEN/KEN_ADM2_metrics_jrc-flood_AALs_adapted_fp_rp100_duc30_capstock.gpkg 
"""

rule tool_relocated_capital_stock_losses:
    """
    Rule summarizes capital stock losses per admin region (relocation adaptation scenario)
    """
    input:
        admin_areas = "data/inputs/boundaries/{ISO3}/geobounds_{ISO3}.gpkg",
        res_risk_file="data/results/flood_risk/countries/{ISO3}/{ISO3}_{MODEL}-flood-risk_adapted_AAR_V-JRC_rl_duc{urban_class}.tif",
        nres_risk_file="data/results/flood_risk/countries/{ISO3}/{ISO3}_{MODEL}-flood-risk_protected_AAR_V-NRES.tif",
        infr_risk_file="data/results/flood_risk/countries/{ISO3}/{ISO3}_{MODEL}-flood-risk_protected_AAR_V-INFR.tif",
        res_capstock_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_res_capstock.tif",
        nres_capstock_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_nres_capstock.tif",
        infr_capstock_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_inf_capstock.tif",
        mask_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_surface_water.tif"
    output:
        regional_losses = "data/results/national_tooling/countries/{ISO3}/{ISO3}_{ADMIN_SLUG}_metrics_{MODEL}-flood_AALs_adapted_rl_duc{urban_class}_capstock.gpkg",
    wildcard_constraints:
        MODEL="jrc",
        ADMIN_SLUG="ADM0|ADM1|ADM2",
        urban_class="11|12|13|21|22|23|30"
    script:
        "./capital_stock_losses.py"
"""
Test with
snakemake -c1 data/results/national_tooling/countries/KEN/KEN_ADM2_metrics_jrc-flood_AALs_adapted_rl_duc11_capstock.gpkg 
"""


rule tool_dry_proofing_capital_stock_losses:
    """
    Rule summarizes capital stock losses per admin region (relocation adaptation scenario)
    """
    input:
        admin_areas = "data/inputs/boundaries/{ISO3}/geobounds_{ISO3}.gpkg",
        res_risk_file="data/results/flood_risk/countries/{ISO3}/{ISO3}_{MODEL}-flood-risk_adapted_AAR_V-JRC_dp.tif",
        nres_risk_file="data/results/flood_risk/countries/{ISO3}/{ISO3}_{MODEL}-flood-risk_protected_AAR_V-NRES.tif",
        infr_risk_file="data/results/flood_risk/countries/{ISO3}/{ISO3}_{MODEL}-flood-risk_protected_AAR_V-INFR.tif",
        res_capstock_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_res_capstock.tif",
        nres_capstock_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_nres_capstock.tif",
        infr_capstock_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_inf_capstock.tif",
        mask_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_surface_water.tif"
    output:
        regional_losses = "data/results/national_tooling/countries/{ISO3}/{ISO3}_{ADMIN_SLUG}_metrics_{MODEL}-flood_AALs_adapted_dp_capstock.gpkg",
    wildcard_constraints:
        MODEL="jrc",
        ADMIN_SLUG="ADM0|ADM1|ADM2",
        urban_class="11|12|13|21|22|23|30"
    script:
        "./capital_stock_losses.py"
"""
Test with
snakemake -c1 data/results/national_tooling/countries/KEN/KEN_ADM2_metrics_jrc-flood_AALs_adapted_dp_capstock.gpkg 
"""

rule tool_inequality_metrics_protected:
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
        regional_CI = "data/results/national_tooling/countries/{ISO3}/{ISO3}_{ADMIN_SLUG}_metrics_{MODEL}-flood_protected_AAR_V-{VULN_CURVE}_S-{SOCIAL}.gpkg",
    wildcard_constraints:
        MODEL="jrc",
        VULN_CURVE="JRC|EXP",
        SOCIAL="gdp",
        ADMIN_SLUG="ADM0|ADM1|ADM2"
    script:
        "./inequality_metrics.py"
"""
Test with
snakemake -c1 data/results/national_tooling/countries/KEN/KEN_ADM0_metrics_jrc-flood_protected_AAR_V-JRC_S-rwi.gpkg
"""

rule tool_inequality_metrics_flood_protection:
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
        regional_CI = "data/results/national_tooling/countries/{ISO3}/{ISO3}_{ADMIN_SLUG}_metrics_{MODEL}-flood_adapted_AAR_V-{VULN_CURVE}_S-{SOCIAL}_fp_rp{RP}_duc{urban_class}.gpkg",
    wildcard_constraints:
        MODEL="jrc",
        VULN_CURVE="JRC|EXP",
        SOCIAL="rwi",
        urban_class="11|12|13|21|22|23|30",
        ADMIN_SLUG="ADM0|ADM1|ADM2"
    script:
        "./inequality_metrics.py"
"""
Test with
snakemake -c1 data/results/national_tooling/countries/KEN/KEN_ADM0_metrics_jrc-flood_adapted_AAR_V-JRC_S-rwi_fp_rp100_duc23.gpkg
"""

rule tool_inequality_metrics_relocation:
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
        regional_CI = "data/results/national_tooling/countries/{ISO3}/{ISO3}_{ADMIN_SLUG}_metrics_{MODEL}-flood_adapted_AAR_V-{VULN_CURVE}_S-{SOCIAL}_rl_duc{urban_class}.gpkg",
    wildcard_constraints:
        MODEL="jrc",
        VULN_CURVE="JRC|EXP",
        SOCIAL="rwi",
        urban_class="11|12|13|21|22|23|30",
        ADMIN_SLUG="ADM0|ADM1|ADM2"
    script:
        "./inequality_metrics.py"
"""
Test with
snakemake -c1 data/results/national_tooling/countries/KEN/KEN_ADM0_metrics_jrc-flood_adapted_AAR_V-JRC_S-rwi_rl_duc23.gpkg
"""

rule tool_inequality_metrics_dry_proofing:
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
        regional_CI = "data/results/national_tooling/countries/{ISO3}/{ISO3}_{ADMIN_SLUG}_metrics_{MODEL}-flood_adapted_AAR_V-{VULN_CURVE}_S-{SOCIAL}_dp.gpkg",
    wildcard_constraints:
        MODEL="jrc",
        VULN_CURVE="JRC|EXP",
        SOCIAL="rwi",
        ADMIN_SLUG="ADM0|ADM1|ADM2"
    script:
        "./inequality_metrics.py"
"""
Test with
snakemake -c1 data/results/national_tooling/countries/KEN/KEN_ADM0_metrics_jrc-flood_adapted_AAR_V-JRC_S-rwi_dp.gpkg
"""