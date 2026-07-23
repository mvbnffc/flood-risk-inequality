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
        merge_inland_gfd_folder=directory("data/inputs/gfd/prep/inland/"),
        merge_coastal_gfd_folder=directory("data/inputs/gfd/prep/coastal/")
    script:
        "./prepare_gfd.py"

rule merge_gfd:
    """
    This rule merges GFD rasters into one global file
    """
    input:
        merge_inland_gfd_folder="data/inputs/gfd/prep/inland/",
        merge_coastal_gfd_folder="data/inputs/gfd/prep/coastal/"
    output:
        merge_inland_gfd_file="data/inputs/gfd/merged/gfd_inland.tif",
        merge_coastal_gfd_file="data/inputs/gfd/merged/gfd_coastal.tif"
    script:
        "./merge_gfd.py"

rule merge_temporal_gfd:
    """
    This rule merges GFD rasters into annual files for coastal and inland flooding
    """
    input:
        merge_inland_gfd_folder="data/inputs/gfd/prep/inland/",
        merge_coastal_gfd_folder="data/inputs/gfd/prep/coastal/"
    output:
        merge_inland_2000_gfd_file="data/inputs/gfd/merged/gfd_2000_inland.tif",
        merge_inland_2001_gfd_file="data/inputs/gfd/merged/gfd_2001_inland.tif",
        merge_inland_2002_gfd_file="data/inputs/gfd/merged/gfd_2002_inland.tif",
        merge_inland_2003_gfd_file="data/inputs/gfd/merged/gfd_2003_inland.tif",
        merge_inland_2004_gfd_file="data/inputs/gfd/merged/gfd_2004_inland.tif",
        merge_inland_2005_gfd_file="data/inputs/gfd/merged/gfd_2005_inland.tif",
        merge_inland_2006_gfd_file="data/inputs/gfd/merged/gfd_2006_inland.tif",
        merge_inland_2007_gfd_file="data/inputs/gfd/merged/gfd_2007_inland.tif",
        merge_inland_2008_gfd_file="data/inputs/gfd/merged/gfd_2008_inland.tif",
        merge_inland_2009_gfd_file="data/inputs/gfd/merged/gfd_2009_inland.tif",
        merge_inland_2010_gfd_file="data/inputs/gfd/merged/gfd_2010_inland.tif",
        merge_inland_2011_gfd_file="data/inputs/gfd/merged/gfd_2011_inland.tif",
        merge_inland_2012_gfd_file="data/inputs/gfd/merged/gfd_2012_inland.tif",
        merge_inland_2013_gfd_file="data/inputs/gfd/merged/gfd_2013_inland.tif",
        merge_inland_2014_gfd_file="data/inputs/gfd/merged/gfd_2014_inland.tif",
        merge_inland_2015_gfd_file="data/inputs/gfd/merged/gfd_2015_inland.tif",
        merge_inland_2016_gfd_file="data/inputs/gfd/merged/gfd_2016_inland.tif",
        merge_inland_2017_gfd_file="data/inputs/gfd/merged/gfd_2017_inland.tif",
        merge_inland_2018_gfd_file="data/inputs/gfd/merged/gfd_2018_inland.tif",
        merge_coastal_2000_gfd_file="data/inputs/gfd/merged/gfd_2000_coastal.tif",
        merge_coastal_2001_gfd_file="data/inputs/gfd/merged/gfd_2001_coastal.tif",
        merge_coastal_2002_gfd_file="data/inputs/gfd/merged/gfd_2002_coastal.tif",
        merge_coastal_2003_gfd_file="data/inputs/gfd/merged/gfd_2003_coastal.tif",
        merge_coastal_2004_gfd_file="data/inputs/gfd/merged/gfd_2004_coastal.tif",
        merge_coastal_2005_gfd_file="data/inputs/gfd/merged/gfd_2005_coastal.tif",
        merge_coastal_2006_gfd_file="data/inputs/gfd/merged/gfd_2006_coastal.tif",
        merge_coastal_2007_gfd_file="data/inputs/gfd/merged/gfd_2007_coastal.tif",
        merge_coastal_2008_gfd_file="data/inputs/gfd/merged/gfd_2008_coastal.tif",
        merge_coastal_2009_gfd_file="data/inputs/gfd/merged/gfd_2009_coastal.tif",
        merge_coastal_2010_gfd_file="data/inputs/gfd/merged/gfd_2010_coastal.tif",
        merge_coastal_2011_gfd_file="data/inputs/gfd/merged/gfd_2011_coastal.tif",
        merge_coastal_2012_gfd_file="data/inputs/gfd/merged/gfd_2012_coastal.tif",
        merge_coastal_2013_gfd_file="data/inputs/gfd/merged/gfd_2013_coastal.tif",
        merge_coastal_2014_gfd_file="data/inputs/gfd/merged/gfd_2014_coastal.tif",
        merge_coastal_2015_gfd_file="data/inputs/gfd/merged/gfd_2015_coastal.tif",
        merge_coastal_2016_gfd_file="data/inputs/gfd/merged/gfd_2016_coastal.tif",
        merge_coastal_2017_gfd_file="data/inputs/gfd/merged/gfd_2017_coastal.tif",
        merge_coastal_2018_gfd_file="data/inputs/gfd/merged/gfd_2018_coastal.tif"

    script:
        "./merge_temporal_gfd.py"

rule clip_gfd:
    """
    Clip GFD flood raster to country boundary.
    """
    input:
        raw_flood_file="data/inputs/gfd/merged/gfd.tif",
        boundary_file="data/inputs/boundaries/{ISO3}/geobounds_{ISO3}.geojson",
        pop_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_ghs-pop.tif",
    output:
        trimmed_flood_file="data/inputs/analysis/countries/{ISO3}/{ISO3}_gfd-flood.tif",
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
snakemake -c1 data/inputs/analysis/countries/KEN/KEN_gfd-flood.tif
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



