"""
Prepare the GFD Flood data. This involves:
    - 1 preparing data for merge (burn files to global extent)
    - 2 merging into a single global flood frequency file
    - 3 clipping and resampling for country of interest
"""

rule prepare_gfd_merge:
    """
    This rule extracts the relevant GFD raster bands (flood occurance and permanent water)
    and converts NaN values to zero - which prepares the files for a global merge.
    It also filters the relevant GFD maps and sorts them by inland or coastal. 
    """
    input:
        raw_gfd_folder="data/inputs/gfd/raw/"
    output:
        merge_gfd_folder=directory("data/inputs/gfd/prep/")
    script:
        "./prepare_gfd.py"

rule merge_gfd:
    """
    This rule merges GFD rasters into one global file
    """
    input:
        merge_gfd_folder="data/inputs/gfd/prep/{TYPE}/"
    output:
        merge_gfd_file="data/inputs/gfd/merged/gfd_all_{TYPE}.tif"
    wildcard_constraints:
        TYPE="inland|coastal"
    script:
        "./merge_gfd.py"

rule merge_temporal_gfd:
    """
    This rule merges GFD rasters into annual files for coastal and inland flooding
    """
    input:
        merge_gfd_folder="data/inputs/gfd/prep/{TYPE}/"
    output:
        merge_temporal_gfd_file="data/inputs/gfd/merged/gfd_{YEAR}_{TYPE}.tif"
    wildcard_constraints:
        TYPE="inland|coastal",
        YEAR="early|late|2000|2001|2002|2003|2004|2005|2006|2007|2008|2009|2010|2011|2012|2013|2014|2015|2016|2017|2018"
    script:
        "./merge_temporal_gfd.py"

rule clip_gfd:
    """
    Clip GFD flood raster to country boundary.
    """
    input:
        raw_flood_file="data/inputs/gfd/merged/gfd_{YEAR}_{TYPE}.tif",
        boundary_file="data/inputs/boundaries/{ISO3}/geobounds_{ISO3}.geojson",
        pop_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_ghs-pop_2020.tif",
    output:
        trimmed_flood_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_gfd_{YEAR}_{TYPE}-flood.tif",
    wildcard_constraints:
        TYPE="inland|coastal",
        YEAR="all|early|late|2000|2001|2002|2003|2004|2005|2006|2007|2008|2009|2010|2011|2012|2013|2014|2015|2016|2017|2018"
    shell:
        """
        set -ex

        mkdir --parents $(dirname {output.trimmed_flood_file})
        
        # Clip raster using GeoJSON geometry
        gdalwarp \
            -cutline {input.boundary_file} \
            -crop_to_cutline \
            -tr 0.00083333333333333 0.00083333333333333 \
            -tap \
            -te_srs EPSG:4326 \
            -te $(gdalinfo -json {input.pop_file} | jq -r '.cornerCoordinates | [.upperLeft[0], .lowerLeft[1], .lowerRight[0], .upperRight[1]] | join(" ")') \
            -of GTiff \
            -co BIGTIFF=YES \
            -co compress=lzw \
            {input.raw_flood_file} \
            {output.trimmed_flood_file}
        """
""" 
Test with
snakemake -c1 data/inputs/analysis/countries/KEN/KEN_gfd_all_coastal-flood.tif
"""

rule clip_gfd_event:
    """
    Will Clip GFD flood raster to country boundary for specific event.
    """
    input:
        raw_flood_file="data/inputs/gfd/prep/DFO_{event_id}.tif",
        adm0_file="data/inputs/boundaries/global/geoBoundariesCGAZ_ADM0.gpkg",
    output:
        flood_event_dir=directory("data/inputs/analysis/events/DFO_{event_id}/"),
        country_json="data/inputs/analysis/events/DFO_{event_id}/countries.json"
    script:
        "./gfd_events.py"

""" 
Test with
snakemake -c1 data/inputs/analysis/events/DFO_1586/
"""

# Run clip_gfd_event rule for all events in the prep folder
# Find all events in the prep folder
events = glob_wildcards("data/inputs/gfd/prep/DFO_{event_id}.tif").event_id

rule clip_all_gfd_events:
    input:
        expand("data/inputs/analysis/events/DFO_{event_id}/", event_id=events)



