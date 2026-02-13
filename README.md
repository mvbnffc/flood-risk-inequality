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
    notebooks/1_observed_figures.ipynb
    notebooks/2_modelled_figures.ipynb
    notebooks/3_observed-modelled_figure.ipynb
    notebooks/4_adaptation_figures.ipynb
    notebooks/S_sensitivity_analysis.ipynb

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
We recommend micromambam but conda also works
```bash
micromamba create -f envs/environment.yml
micromamba activate flood-risk-inequality
```
