"""Map national population-weighted wealth quintiles within DEGURBA classes.

Uses filled RWI and fixed SMOD, like the existing diagnostic wealth map.
Q1 is poorest within the class; zero denotes nodata or another class.
Equal RWI values stay together, so population shares need not be exactly 20%.
These are wealth diagnostics, not maps of flood inequality. No flood or water
mask is applied, and ranks are national within-class, not ADM1/ADM2 ranks.
"""

import logging

import numpy as np
import rasterio


CLASS_CODES = {"RUR": (11, 12, 13), "TWN": (21, 22, 23), "CTY": (30,)}


def weighted_quintiles(wealth, population):
    """Return tied-value quintiles and cutoffs for a valid populated sample."""
    population = np.asarray(population, dtype=np.float64)
    if len(wealth) == 0:
        return np.empty(0, dtype=np.int16), np.empty(0)
    order = np.argsort(wealth, kind="stable")
    cumulative = np.cumsum(population[order], dtype=np.float64)
    indices = np.searchsorted(cumulative, cumulative[-1] * np.array([.2, .4, .6, .8]))
    thresholds = wealth[order][indices]
    return (np.searchsorted(thresholds, wealth, side="left") + 1).astype(np.int16), thresholds


def main(snakemake):
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    with rasterio.open(snakemake.input.pop_file) as pop_src, \
         rasterio.open(snakemake.input.rwi_file) as rwi_src, \
         rasterio.open(snakemake.input.urban_file) as urban_src:
        for src in (rwi_src, urban_src):
            if (src.shape, src.transform, src.crs) != (pop_src.shape, pop_src.transform, pop_src.crs):
                raise ValueError("Population, RWI and SMOD rasters must share a grid and CRS.")
        pop = pop_src.read(1, masked=True)
        wealth = rwi_src.read(1, masked=True)
        urban = urban_src.read(1, masked=True)
        valid = (~np.ma.getmaskarray(pop) & ~np.ma.getmaskarray(wealth)
                 & ~np.ma.getmaskarray(urban) & np.isfinite(pop.data)
                 & np.isfinite(wealth.data) & np.isfinite(urban.data)
                 & (pop.data > 0) & (wealth.data != -999))
        profile = pop_src.profile.copy()
        profile.update(dtype="int16", count=1, nodata=0, compress="lzw")
        outputs = {"RUR": snakemake.output.rural, "TWN": snakemake.output.towns,
                   "CTY": snakemake.output.cities}
        for group, codes in CLASS_CODES.items():
            sample = valid & np.isin(urban.data, codes)
            quintiles, thresholds = weighted_quintiles(wealth.data[sample], pop.data[sample])
            result = np.zeros(pop.shape, dtype=np.int16)
            result[sample] = quintiles
            logging.info("%s: %s populated cells; RWI cutoffs %s", group, sample.sum(), thresholds)
            weights = pop.data[sample].astype(np.float64)
            total = weights.sum()
            shares = [weights[quintiles == q].sum() / total if total else 0 for q in range(1, 6)]
            logging.info("%s: quintile population shares %s", group, shares)
            with rasterio.open(outputs[group], "w", **profile) as dst:
                dst.write(result, 1)
                dst.update_tags(settlement_class=group, ranking="national within settlement class",
                                population_year=snakemake.wildcards.POP_YEAR,
                                quintile_legend="1=poorest, 5=richest, 0=nodata",
                                rwi_cutoffs=",".join(str(v) for v in thresholds))


if __name__ == "__main__":
    main(snakemake)
