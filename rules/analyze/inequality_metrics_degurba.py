"""
This script calculates inequality metrics (concentration index and quantile ratio)
and flood risk metrics at a given administrative level. It decomposes the
concentration index by the three DEGURBA Level 1 settlement classes
(cities / towns and semi-dense areas / rural areas), aggregated from GHS-SMOD.

For each settlement class it reports:
  * the CI with NATIONAL wealth ranks, and its contribution to the overall CI
    (Clarke-style component decomposition; contributions sum exactly to the CI)
  * the CI with ranks recomputed WITHIN the class (intra-class sorting only)
  * the class's mean national wealth rank and mean flood risk per person
  * population and flood-risk shares, both computed on the same masked sample

It also reports the exact covariance decomposition of the overall CI:

    CI      = WITHIN + BETWEEN
    WITHIN  = (2/mu) * sum_g p_g * cov_g(flood, national rank)
    BETWEEN = (2/mu) * sum_g p_g * (mu_g - mu) * (r_g - r_bar)

No overlap term is required: the ranking variable is external and fixed, so the
covariance splits exactly. Note that WITHIN and BETWEEN depend mechanically on
how many classes the settlement layer is collapsed to - always report the class
count alongside them.

Note: now using geoboundaries rather than GADM for admin boundaries.
"""

import logging

import rasterio
from rasterio.features import geometry_mask
import pandas as pd
import geopandas as gpd
import numpy as np
from tqdm import tqdm

# DEGURBA Level 1 grouping of the GHS-SMOD Level 2 codes
DEGURBA = {
    11: "RUR",  # very low density rural
    12: "RUR",  # low density rural
    13: "RUR",  # rural cluster
    21: "TWN",  # suburban / peri-urban
    22: "TWN",  # semi-dense urban cluster
    23: "TWN",  # dense urban cluster
    30: "CTY",  # urban centre
}
CLASSES = ["RUR", "TWN", "CTY"]
CLASS_NAMES = {"RUR": "Rural areas",
               "TWN": "Towns & semi-dense areas",
               "CTY": "Cities"}
METRICS = ("Contribution", "CI", "CI Within", "Risk Share", "Pop Share",
           "Mean Rank", "Mean Flood")

if __name__ == "__main__":

    try:
        admin_path: str = snakemake.input["admin_areas"]
        social_path: str = snakemake.input["social_file"]
        pop_path: str = snakemake.input["pop_file"]
        mask_path: str = snakemake.input["mask_file"]
        urban_path: str = snakemake.input["urban_file"]
        risk_path: str = snakemake.input["risk_file"]
        output_path: str = snakemake.output["regional_CI"]
        administrative_level: int = snakemake.wildcards.ADMIN_SLUG
        model: str = snakemake.wildcards.MODEL
        social_name: str = snakemake.wildcards.SOCIAL
    except NameError:
        raise ValueError("Must be run via snakemake.")

logging.basicConfig(format="%(asctime)s %(process)d %(filename)s %(message)s", level=logging.INFO)

# Update notation for GADM
admin_level = int(administrative_level.replace("ADM", ""))

logging.info(f"Calculating concentration indices at admin level {admin_level}.")

logging.info("Reading raster data.")
with rasterio.open(social_path) as social_src, rasterio.open(pop_path) as pop_src, \
     rasterio.open(mask_path) as mask_src, rasterio.open(urban_path) as urban_src, \
     rasterio.open(risk_path) as risk_src:
    social = social_src.read(1)
    pop = pop_src.read(1)
    water_mask = mask_src.read(1)
    urban = urban_src.read(1).astype('float32')  # convert to float to avoid errors
    risk = risk_src.read(1)
    affine = risk_src.transform

if social_name == "rwi":
    social[social == -999] = np.nan  # convert -999 in RWI dataset to NaN
# Create the water mask
water_mask = np.where(water_mask > 50, np.nan, 1)  # WARNING WE ARE HARD CODING PERM_WATER > 50% mask here

# NOTE: the nearest-valid-cell fill for misaligned GHS-SMOD cells is currently
# disabled, so cells with an invalid urban code are dropped by the validity mask
# below. Coverage is reported per settlement class so any differential loss is
# visible in the output.


def wmean(x, w):
    """Population-weighted mean."""
    return np.average(x, weights=w)


def wcov(x, y, w):
    """Population-weighted covariance."""
    return np.average((x - wmean(x, w)) * (y - wmean(y, w)), weights=w)


def calculate_CI(df):
    '''
    Calculates the concentration index (CI) for the given dataframe and
    decomposes it across the three DEGURBA settlement classes.

    Uses Clarke (2002) component decomposition for the contributions: each class
    CI is computed against the NATIONAL wealth ranking, so the contributions sum
    exactly to the overall CI. In addition each class CI is recomputed with the
    wealth ranking taken WITHIN the class, which isolates intra-class sorting.

    Returns:
        CI        - overall concentration index
        per_class - {class: {metric: value}} for RUR / TWN / CTY
        decomp    - {"within", "between", "total", "r_bar"}
    '''
    blank = ({c: {m: np.nan for m in METRICS} for c in CLASSES},
             {k: np.nan for k in ("within", "between", "total", "r_bar")})

    # Sort dataframe by wealth
    df = df.sort_values(by="social", ascending=True).copy()
    # Calculate total pop of sample
    total_pop = df['pop'].sum()
    if total_pop <= 0:
        return np.nan, *blank
    # Calculate cumulative population rank (to represent distribution of people)
    df['cum_pop'] = df['pop'].cumsum()
    # Calculate fractional rank of each row
    df['rank'] = (df['cum_pop'] - 0.5 * df['pop']) / total_pop

    # Calculate weighted mean of flood risk
    mu = wmean(df['flood'], df['pop'])
    if not np.isfinite(mu) or mu == 0:
        return np.nan, *blank

    # Mean fractional rank (~0.5, but compute it rather than assume)
    r_bar = wmean(df['rank'], df['pop'])
    # Calculate weighted sum of (flood * rank * pop)
    sum_xR = (df['flood'] * df['rank'] * df['pop']).sum()
    # Calculate Concentration Index
    CI = (2 * sum_xR) / (total_pop * mu) - 1

    per_class = {}
    within = 0.0
    between = 0.0
    for g, sub in df.groupby("degurba"):
        w = sub['pop'].values
        f = sub['flood'].values
        r = sub['rank'].values
        pop_g = w.sum()
        if pop_g <= 0:
            continue
        mu_g = wmean(f, w)
        r_g = wmean(r, w)
        p_g = pop_g / total_pop
        risk_share = (pop_g * mu_g) / (total_pop * mu)

        # CI of the class against the national wealth ranking
        if mu_g > 0:
            sub_CI = (2 * (f * r * w).sum()) / (pop_g * mu_g) - 1
            contribution = sub_CI * risk_share
        else:
            sub_CI, contribution = np.nan, 0.0

        # CI of the class with the ranking recomputed inside the class
        if mu_g > 0 and len(sub) > 1:
            order = np.argsort(sub['social'].values, kind="mergesort")
            w_o, f_o = w[order], f[order]
            rank_in = (np.cumsum(w_o) - 0.5 * w_o) / pop_g
            sub_CI_within = (2 * (f_o * rank_in * w_o).sum()) / (pop_g * mu_g) - 1
        else:
            sub_CI_within = np.nan

        # Exact covariance decomposition of the overall CI
        within += p_g * wcov(f, r, w)
        between += p_g * (mu_g - mu) * (r_g - r_bar)

        per_class[g] = {
            "Contribution": contribution,
            "CI": sub_CI,
            "CI Within": sub_CI_within,
            "Risk Share": risk_share,
            "Pop Share": p_g,
            "Mean Rank": r_g,
            "Mean Flood": mu_g,
        }

    # Ensure all settlement classes are represented in the output
    for c in CLASSES:
        if c not in per_class:
            per_class[c] = {m: np.nan for m in METRICS}

    decomp = {
        "within": (2 / mu) * within,
        "between": (2 / mu) * between,
        "total": (2 / mu) * (within + between),
        "r_bar": r_bar,
    }
    return CI, per_class, decomp


def print_ci(ci_total, per_class, decomp):
    df = (pd.DataFrame.from_dict(per_class, orient="index")
            .reindex(CLASSES)
            .rename(index=CLASS_NAMES)
            .rename_axis("Settlement class"))
    df["Risk Share %"] = 100 * df["Risk Share"]
    df["Pop Share %"] = 100 * df["Pop Share"]
    df.drop(columns=["Risk Share", "Pop Share"], inplace=True)
    df["% of total CI"] = np.where(
        ci_total == 0, np.nan, 100 * df["Contribution"] / ci_total
    )

    print(f"\n\033[1mOverall concentration index (CI):\033[0m {ci_total:+.6f}")
    print(f"  within-class  {decomp['within']:+.6f}"
          f"   between-class {decomp['between']:+.6f}"
          f"   (sum {decomp['total']:+.6f})\n")
    print(df.to_markdown(floatfmt=".4f"))


logging.info(f"Reading level {administrative_level} admin boundaries")
layer_name = f"ADM{admin_level}"
admin_areas: gpd.GeoDataFrame = gpd.read_file(admin_path, layer=layer_name)
if layer_name == "ADM0":
    area_unique_id_col = "shapeName"
else:
    area_unique_id_col = "shapeID"
# Keep shapeName as a label column even when it is not the unique id (ADM1+)
keep_cols = [area_unique_id_col]
if "shapeName" in admin_areas.columns and "shapeName" not in keep_cols:
    keep_cols.append("shapeName")
keep_cols.append("geometry")
admin_areas = admin_areas[keep_cols]
# shapeID is the unique key above ADM0; shapeName is a label only and may repeat
n_dup_id = int(admin_areas[area_unique_id_col].duplicated().sum())
if n_dup_id:
    logging.warning(
        f"{n_dup_id} duplicated values in {area_unique_id_col} - output rows will "
        f"not be uniquely identifiable."
    )
if "shapeName" in admin_areas.columns:
    n_dup_name = int(admin_areas["shapeName"].duplicated().sum())
    if n_dup_name:
        logging.info(
            f"{n_dup_name} repeated shapeName values (expected above ADM0); "
            f"join on {area_unique_id_col}, not shapeName."
        )
logging.info(f"There are {len(admin_areas)} admin areas to analyze.")

logging.info("Looping over admin regions and calculating concentration indices")
results = []  # List for collecting results
# Loop over each admin region
for idx, region in tqdm(admin_areas.iterrows()):
    # Get the geometry for the current admin region
    geom = region["geometry"].__geo_interface__
    # Create a mask from the geometry
    mask_array = geometry_mask([geom],
                               transform=affine,
                               invert=True,
                               out_shape=social.shape)
    # Use the mask to clip each raster by setting values outside the region to nan
    social_clip = np.where(mask_array, social, np.nan)
    pop_clip = np.where(mask_array, pop, np.nan)
    urban_clip = np.where(mask_array, urban, np.nan)
    risk_clip = np.where(mask_array, risk, np.nan)
    water_mask_clip = np.where(mask_array, water_mask, np.nan)

    # Mask out areas where not all rasters are valid
    mask = (
        ~np.isnan(pop_clip) &
        ~np.isnan(social_clip) &
        ~np.isnan(risk_clip) &
        ~np.isnan(urban_clip) &
        ~np.isnan(water_mask_clip)
    )
    # Flatten data
    pop_flat = pop_clip[mask]
    social_flat = social_clip[mask]
    urban_flat = urban_clip[mask]
    risk_flat = risk_clip[mask]
    # Mask out zero-population cells
    valid = pop_flat > 0
    pop_flat = pop_flat[valid]
    urban_flat = urban_flat[valid]
    social_flat = social_flat[valid]
    risk_flat = risk_flat[valid]

    # Calculate total flood risk (pop * risk) for the region
    total_flood_risk = np.nansum(pop_flat * risk_flat)

    # Prepare dataframe for metric calculation, mapping SMOD codes to DEGURBA L1
    df = pd.DataFrame({
        'pop': pop_flat,
        'social': social_flat,
        'flood': risk_flat,
        'urban': urban_flat.astype(int)
    })
    df["degurba"] = df["urban"].map(DEGURBA)
    # Drop any cell whose SMOD code is outside the seven valid classes
    df = df[df["degurba"].notna()]

    CI, per_class, decomp = calculate_CI(df)
    if admin_level == 0:
        print_ci(CI, per_class, decomp)

    # Population totals. The unmasked totals are the full admin-area population;
    # the masked totals match the sample the CI is actually computed on, so the
    # two should be compared when judging coverage.
    total_pop_unmasked = np.nansum(pop_clip)
    total_pop_masked = df['pop'].sum()
    pop_by_class_unmasked = {
        c: np.nansum(np.where(np.isin(urban_clip, [k for k, v in DEGURBA.items() if v == c]),
                              pop_clip, 0))
        for c in CLASSES
    }
    pop_by_class_masked = df.groupby("degurba")['pop'].sum().reindex(CLASSES).fillna(0)

    row = {
        area_unique_id_col: region[area_unique_id_col],
        "shapeName": region.get("shapeName", None),
        "CI": CI,
        "CI Within": decomp["within"],
        "CI Between": decomp["between"],
        "Mean Rank": decomp["r_bar"],
        "Population": total_pop_unmasked,
        "Population (masked)": total_pop_masked,
        "Population Coverage (%)": (total_pop_masked / total_pop_unmasked) * 100
        if total_pop_unmasked > 0 else np.nan,
        "Total Flood Risk": total_flood_risk,
    }
    for c in CLASSES:
        row[f"{c} Population"] = pop_by_class_unmasked[c]
        row[f"{c} Population (masked)"] = pop_by_class_masked[c]
        for m in METRICS:
            row[f"{c} {m}"] = per_class[c][m]
    row["geometry"] = region["geometry"]
    results.append(row)

logging.info("Writing results to GeoPackage.")
results_gdf = gpd.GeoDataFrame(results, geometry="geometry")
results_gdf.to_file(output_path, driver="GPKG")

logging.info("Done.")
