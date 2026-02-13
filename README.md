# Flood risk inequality in low- and middle-income countries and the benefits of adaptation

This repository contains the code used in:

> **Bernhofen et al. — Flood risk inequality in low- and middle-income countries and the benefits of adaptation**

The repository allows full reproduction of the analysis and figures in the paper.

---

## How to use this repository

There are **two ways** to reproduce the paper.

### Option A — Reproduce figures only (recommended, fast)

Download the processed datasets from Zenodo and run the notebooks.

This reproduces **all figures and tables in the paper** and is the intended route for readers and reviewers.

Time required: ~15–30 minutes

Steps:
1. Download processed results from Zenodo  
   → [ZENODO LINK HERE]

2. Copy the "Results" folder into top level directory

3. Run the notebooks in order:

`notebooks/1_observed_figures.ipynb`

`notebooks/2_modelled_figures.ipynb`

`notebooks/3_observed-modelled_figure.ipynb`

`notebooks/4_adaptation_figures.ipynb`

`notebooks/S_sensitivity_analysis.ipynb`

### Option B — Full pipeline reproduction (slow, HPC)

Re-run the entire analysis from raw data using Snakemake.

This regenerates all intermediate datasets including hazard processing, exposure analysis, and adaptation modelling.

⚠️ This workflow was designed for a Linux HPC cluster and requires substantial compute.

Typical runtime:
- ~1–3 days
- 32–300 GB RAM for some steps
- Parallel execution recommended

---

## Installation

### 1. Clone the repository
```bash
git clone https://github.com/[user]/flood-risk-inequality.git
cd flood-risk-inequality
```

### 2. Clone the repository
We recommend micromamba but conda also works
```bash
micromamba create -f environment.yml
micromamba activate flood-risk-inequality
```

--- 

## Running the full pipeline
The analysis follows a [Snakemake](https://snakemake.readthedocs.io/) workflow.

**Hardware used for development:**
- Linux HPC cluster (8 cores, 300 GB RAM)
- Total wall-clock time: X days (with parallelisation)

The snakemake rules required to replicate the analysis in the paper can be found in `rules/analyze/paper_bulk_anaysis.smk`
Note: the timings listed below assume the rules are run sequentially (some preceding rules will generate the data needed for subsequent analyses)

The workflow downloads and prepares all necessary data in `data/inputs/` and results are stored in `data/results/`

**Steps:**
1. Activate the flood-risk-inequality environment and use navigate to flood-risk-inequality directory from command line

2. Run analysis to calculate observed flooding metrics at national scale
```bash
snakemake -c8 observed_metrics_for_all_countries
```
*Runtime: ~X hours*

3. Run analysis to calculate decomposed (across urban areas) observed flood metrics at national scale
```bash
snakemake -c8 observed_metrics_decomposed_for_all_countries
```
*Runtime: ~X hours*

4. Clip all individual observed events
```bash
snakemake -c8 clip_all_gfd_events
```
*Runtime: ~X hours*

5. Run analysis calculating all metrics for individual observed events
```bash
snakemake -c8 metrics_all_gfd_events
```
*Runtime: ~X hours*

6. Run analysis for modelled flooding, calculating metrics at the national scale 
```bash
snakemake -c8 flood_model_metrics_ADM0_all_countries
```
*Runtime: ~X hours*

7. Run analysis for modelled flooding, calculating the decomposed metrics at the ADM1 level
```bash
snakemake -c8 flood_model_admin_CI_decomposed
```
*Runtime: ~X hours*

8. Run flood risk and adaptation assessment for all flood models
```bash
snakemake -c8 bulk_flood_risk_and_adaptation_analysis
```
*Runtime: ~X hours*

9. Run metric analysis for adaptation scenarios
```bash
snakemake -c8 bulk_social_metrics_adaptation
```
*Runtime: ~X hours*

10. Run sensitivity analysis
```bash
snakemake -c8 flood_model_sensitivity_run
```
*Runtime: ~X hours*

**All outputs are written to `data/results/`. The notebooks in `notebooks/` read from this directory to produce all figures and tables.**
