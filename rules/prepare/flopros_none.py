"""
Section 4 scenario 2 ("from no protection"): a FLOPROS raster with 2-year protection everywhere
in the country (the FLOPROS minimum, which the risk integration treats the same as no protection).

Cells outside the country (0) and no-data cells keep their values, so the raster lines up exactly
with {ISO3}_flopros.tif.
"""

import numpy as np
import rasterio

NO_PROTECTION = 2.0

if __name__ == "__main__":
    try:
        flopros_path: str = snakemake.input["flopros"]
        out_path: str = snakemake.output["flopros_none"]
    except NameError:
        raise ValueError("Must be run via snakemake.")

    with rasterio.open(flopros_path) as src:
        flopros = src.read(1)
        profile = src.profile
        nodata = src.nodata

    inside = np.isfinite(flopros) & (flopros > 0)
    if nodata is not None:
        inside &= flopros != nodata
    out = np.where(inside, NO_PROTECTION, flopros).astype(flopros.dtype)

    with rasterio.open(out_path, "w", **profile) as dst:
        dst.write(out, 1)
    print(f"{out_path}: {int(inside.sum())} cells set to {NO_PROTECTION:g} years")
