#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Calculate zonal statistics (sum) based on Landscan population
for Guatemalan municipios.

@author: Nate Currit
"""

import rasterio
from rasterio.mask import mask
import numpy as np
import fiona
from rasterstats import zonal_stats
from glob import glob
import csv

pop_dir = "data/"
zones = "data/GTM_adm2.shp"
# urban_region = "data/urban.tif"
rural_region = "data/rural.tif"


def get_pop_rasters():
    """
    Returns a sorted list of population rasters.

    Returns the list of population rasters, each of which is an
    ArcInfo Binary Grid. The population data is Landscan data.
    Sorting is done according to data year.

    Returns
        list of strings, each string the path to a file.

    """
    rasters = glob(pop_dir + "lspop*/hdr.adf")
    return sorted(rasters)


def main():
    # Open the Central America study site bounding box used to ensure
    # all rasters are clipped to the same sized region
    # note: there is only 1 box in boundingbox
    with fiona.open("data/ca_boundingbox.shp", "r") as boundingbox:
        clip_box = [box["geometry"] for box in boundingbox]

    # Open the features used to calculate zonal statistics
    # In this case the features are 354 Guatemalan municipios
    with fiona.open(zones) as z_src:
        features = list(z_src)

    # Open the raster that masks urban/rural areas:
    # 0 = urban, 1 = rural, 3 = nodata
    with rasterio.open(rural_region) as rural:
        r_img, r_transform = mask(rural, clip_box, crop=True)

    # Open the CSV file for writing, first setting the header
    with open("rural_urban_pop.csv", 'w') as dst:
            w = csv.DictWriter(dst, ['id', 'name', 'year', 'rural_pop',
                                     'urban_pop'])
            w.writeheader()

            # For each population raster...
            pop_rasters = get_pop_rasters()
            for pop_raster in pop_rasters:
                # Open the raster
                with rasterio.open(pop_raster) as pop:
                    # Read the 3D numpy array (band, row, column)
                    # clipped according to the coordinates of clip_box
                    p_img, p_transform = mask(pop, clip_box, crop=True)
                    # If r_img equals 1 (rural), assign p_img, else assign 0
                    rural_pop = np.where(r_img == 1, p_img, 0)
                    # If r_img equals 0 (urban), assign p_img, else assign 0
                    urban_pop = np.where(r_img == 0, p_img, 0)

                    # Sum the rural population pixels for each municipio
                    # in features
                    rural_stats = zonal_stats(features, rural_pop[0],
                                              affine=p_transform,
                                              stats=['sum'])
                    # Sum the urban population pixels for each municipio
                    # in features
                    urban_stats = zonal_stats(features, urban_pop[0],
                                              affine=p_transform,
                                              stats=['sum'])

                    # Extract the year from the population filename
                    year = pop_raster.split("lspop", 1)[1].split("/hdr.adf")[0]

                    # Create a list of dictionaries where each dictionary
                    # contains the id, name, year, rural population and
                    # urban population of each municipio
                    output = []
                    for f, rs, us in zip(features, rural_stats, urban_stats):
                        t = {}
                        t['id'] = f['properties']['ID_2']
                        t['name'] = f['properties']['NAME_2']
                        t['year'] = year
                        t['rural_pop'] = rs['sum']
                        t['urban_pop'] = us['sum']
                        output.append(t)

                # Write the list of dictionaries to the open CSV file
                w.writerows(output)


if __name__ == "__main__":
    main()
