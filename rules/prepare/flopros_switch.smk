"""
Switch the pipeline to the fixed FLOPROS rasters (step 2 of flopros_fix.smk).

Include ONLY after reviewing data/results/flopros_fix/flopros_fix_summary.csv:
    include: "rules/prepare/flopros_switch.smk"

{ISO3}_flopros.tif is then made from {ISO3}_flopros-fixed.tif instead of by clip_flopros.
Snakemake sees the new rule and newer input, so every risk raster that reads FLOPROS (baseline
and adapted, all models) is rebuilt the next time a target needs it. To keep the current raster
for comparison, copy {ISO3}_flopros.tif elsewhere before running.

To undo: remove the include line (and re-run clip_flopros with -R clip_flopros).
"""

ruleorder: use_fixed_flopros > clip_flopros


rule use_fixed_flopros:
    input:
        "data/inputs/analysis/countries/{ISO3}/{ISO3}_flopros-fixed.tif",
    output:
        "data/inputs/analysis/countries/{ISO3}/{ISO3}_flopros.tif",
    wildcard_constraints:
        ISO3="[A-Z][A-Z][A-Z]",
    shell:
        "cp {input} {output}"
