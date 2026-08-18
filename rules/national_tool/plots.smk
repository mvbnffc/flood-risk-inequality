rule concentration_curve:
    """
    Calculate national flood exposure concentration curve and output a CSV of those points for plotting in national tool
    """
    input:
        pop_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_worldpop_total.tif",
        rwi_file="data/results/national_tooling/countries/{ISO3}/{ISO3}_pop_rwi_values.tif",
        surface_water="data/inputs/analysis/countries/{ISO3}/{ISO3}_surface_water.tif",
        flood_file="data/results/flood_risk/countries/{ISO3}/{ISO3}_jrc-flood-risk_protected_AAR_V-{VULN_CURVE}.tif",
    output:
        curve="data/results/national_tooling/countries/{ISO3}/concentration_curves/{ISO3}_jrc_protected_V-{VULN_CURVE}_concentration_curve.csv",
    wildcard_constraints:
        VULN_CURVE="EXP|JRC",
    params:
        n_points=101,
    script:
        "./calculate_concentration_curve.py"