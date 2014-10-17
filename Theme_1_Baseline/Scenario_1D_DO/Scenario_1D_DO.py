# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <codecell>

from utilities import * 
css_styles()

# <markdowncell>

# # IOOS System Test - Theme 1 - Scenario D - [Description](https://github.com/ioos/system-test/wiki/Development-of-Test-Themes#theme1)
# 
# ## Exploring Dissolved Oxygen Data
# 
# ## Questions
# 1. Can we discover, access, and overlay salinity information in sensors?
# 2. Can we discover, access, and overlay salinity information from models?
# 3. Is data from different sensors and satellite data (or models) directly comparable? Same units? Same scales?
# 4. If not, how much work is necessary to aggregate these streams?
# 5. Is metadata for these data intelligable?

# <markdowncell>

# ## Q1 - Can we discover, access, and overlay salinity information?

# <codecell>

from pylab import *
from IPython.display import HTML

# <markdowncell>

# Define space and time constraints

# <markdowncell>

# Kachemak Bay, because it will narrow the result set, and temperature and salinity are key variables in defining thresholds for harmful algal blooms (HABs) leading to paralytic Shellfish Poisoning (PSP) warnings.

# <markdowncell>

# #### Query MMI for CF standard names related to the IOOS Core Variables

# <codecell>

import pandas as pd
pd.set_option('display.max_columns', 20)
pd.set_option('display.max_rows', 500)
from SPARQLWrapper import SPARQLWrapper, JSON
sparql = SPARQLWrapper("http://mmisw.org/sparql")

query = """
PREFIX ioos: <http://mmisw.org/ont/ioos/parameter/>
SELECT DISTINCT ?cat ?parameter ?property ?value 
WHERE {?parameter a ioos:Parameter .
       ?parameter ?property ?value .
       ?cat skos:narrowMatch ?parameter .
       FILTER  (regex(str(?property), "Match", "i") && regex(str(?value), "cf", "i") )
      } 
ORDER BY ?cat ?parameter
"""
    
sparql.setQuery(query)
sparql.setReturnFormat(JSON)
j = sparql.query().convert()

cf_standard_uris  = list(set([ x["value"]["value"] for x in j.get("results").get("bindings") ]))
cf_standard_names = map(lambda x: x.split("/")[-1], cf_standard_uris)
pd.DataFrame.from_records(zip(cf_standard_names, cf_standard_uris), columns=("CF Name", "CF URI",))

# <markdowncell>

# #### Geographic subset

# <codecell>

bounding_box = [ -81.03, 27.59, -66.14, 44.92]  # East Coast

"Geographic subset: {!s}".format(bounding_box)

# <markdowncell>

# #### Temporal subset

# <codecell>

from datetime import datetime
start_date = datetime(2014,1,1)
start_date_string = start_date.strftime('%Y-%m-%d %H:00')

end_date = datetime(2014,8,1)
end_date_string = end_date.strftime('%Y-%m-%d %H:00')

"Temporal subset: ( {!s} to {!s} )".format(start_date_string, end_date_string)

# <markdowncell>

# #### Set variable subset

# <codecell>

variables_to_query = [ x for x in cf_standard_names if "oxygen" in x ]
custom_variables   = ['dissolved_oxygen', 'oxygen']  # Do we need any, or are they all extractable from MMI?

variables_to_query += custom_variables
"Variable subset: {!s}".format(" , ".join(variables_to_query))

# <markdowncell>

# #### Define all known the CSW endpoints

# <codecell>

# https://github.com/ioos/system-test/wiki/Service-Registries-and-Data-Catalogs
known_csw_servers = ['http://data.nodc.noaa.gov/geoportal/csw',
                     'http://www.nodc.noaa.gov/geoportal/csw',
                     'http://www.ngdc.noaa.gov/geoportal/csw',
                     'http://cwic.csiss.gmu.edu/cwicv1/discovery',
                     'http://geoport.whoi.edu/geoportal/csw',
                     'https://edg.epa.gov/metadata/csw',
                     'http://cmgds.marine.usgs.gov/geonetwork/srv/en/csw',
                     'http://cida.usgs.gov/gdp/geonetwork/srv/en/csw',
                     'http://geodiscover.cgdi.ca/wes/serviceManagerCSW/csw',
                     'http://geoport.whoi.edu/gi-cat/services/cswiso',
                     'https://data.noaa.gov/csw',
                     ]

# <markdowncell>

# #### Construct CSW Filters

# <codecell>

from owslib import fes
def fes_date_filter(start_date='1900-01-01',stop_date='2100-01-01',constraint='overlaps'):
    if constraint == 'overlaps':
        start = fes.PropertyIsGreaterThanOrEqualTo(propertyname='apiso:TempExtent_end', literal=start_date)
        stop = fes.PropertyIsLessThanOrEqualTo(propertyname='apiso:TempExtent_begin', literal=stop_date)
    elif constraint == 'within':
        start = fes.PropertyIsGreaterThanOrEqualTo(propertyname='apiso:TempExtent_begin', literal=start_date)
        stop = fes.PropertyIsLessThanOrEqualTo(propertyname='apiso:TempExtent_end', literal=stop_date)
    return fes.And([start, stop])

# <codecell>

# Standard Name filters
cf_name_filters = []
for cf_name in variables_to_query:
    text_filter   = fes.PropertyIsLike(propertyname='apiso:AnyText', literal="*%s*" % cf_name, wildCard='*')
    cf_name_filters.append(text_filter)
cf_name_filters = fes.Or(cf_name_filters)

# Geographic filters
geographic_filter = fes.BBox(bbox=bounding_box)

# Temporal filters
temporal_filter = fes_date_filter(start_date_string, end_date_string)

filters = fes.And([cf_name_filters, geographic_filter, temporal_filter])

# <markdowncell>

# ##### The actual CSW filter POST envelope looks like this

# <codecell>

from owslib.etree import etree
print etree.tostring(filters.toXML(), pretty_print=True)

# <markdowncell>

# ##### Filter out CSW servers that do not support a BBOX query

# <codecell>

from owslib.csw import CatalogueServiceWeb
bbox_endpoints = []
for url in known_csw_servers:
    queryables = []
    try:
        csw = CatalogueServiceWeb(url, timeout=20)
    except BaseException:
        print "Failure - %s - Timed out" % url
    if "BBOX" in csw.filters.spatial_operators:
        print "Success - %s - BBOX Query supported" % url
        bbox_endpoints.append(url)    
    else:
        print "Failure - %s - BBOX Query NOT supported" % url

# <markdowncell>

# #### Query CSW Servers using filters

# <codecell>

urls = []
service_types = []
servers = []
for url in bbox_endpoints:
    print "*", url
    try:
        csw = CatalogueServiceWeb(url, timeout=20)
        csw.getrecords2(constraints=[filters], maxrecords=200, esn='full')
        for record, item in csw.records.items():
            # Get URLs
            service_url, scheme = next(((d['url'], d['scheme']) for d in item.references), None)
            if service_url:
                if len(item.title) > 100:
                    title = "{!s}...{!s}".format(item.title[0:50], item.title[-50:])
                else:
                    title = item.title    
                print "    [x] {!s}".format(title)
                
                urls.append(service_url)
                service_types.append(scheme)
                servers.append(url)
    except BaseException as e:
        print "    [-] FAILED: {!s}".format(e)

# <markdowncell>

# #### What service are available?

# <codecell>

srvs = pd.DataFrame(zip(urls, service_types, servers), columns=("URL", "Service Type", "Server"))
srvs = srvs.drop_duplicates()
pd.set_option('display.max_rows', 10)
srvs

# <markdowncell>

# #### What types of service are available

# <codecell>

pd.DataFrame(srvs.groupby("Service Type").size(), columns=("Number of services",))

# <markdowncell>

# <div class="error" style="text-align: center"><strong>SOS and DAP Servers are not properly identified</strong><br />One can not tell (programatically) what the "urn:x-esri:specification:ServiceType:distribution:url" scheme actually is.</div>

# <markdowncell>

# # SOS

# <codecell>

def find_sos(x):
    d = x.lower()
    if "sos" in d and "dods" not in d:
        return x
    return None

# <codecell>

sos_servers = filter(None, srvs["URL"].map(find_sos))
sos_servers

# <markdowncell>

# <div class="error" style="text-align: center"><strong>No SOS Servers Found</strong><br />There are no SOS servers that are found using the CSW filters</div>

# <markdowncell>

# # DAP

# <codecell>

def find_dap(x):
    d = x.lower()
    if ("dap" in d or "dods" in d) and "tabledap" not in d:
        return x
    return None

# <codecell>

import os
dap_servers = filter(None, srvs["URL"].map(find_dap))
dap_servers = map(lambda x: os.path.splitext(x)[0], dap_servers)
dap_servers

# <markdowncell>

# #### Try to extract salinity data from all of the DAP endpoints

# <codecell>

import iris
import iris.plot as iplt
import matplotlib.pyplot as plt
%matplotlib inline

variables = lambda cube: cube.standard_name in variables_to_query
constraint = iris.Constraint(cube_func=variables)


def iris_grid_plot(cube_slice, name=None):
    plt.figure(figsize=(12, 8))
    lat = cube_slice.coord(axis='Y').points
    lon = cube_slice.coord(axis='X').points
    time = cube_slice.coord('time')[0]
    plt.subplot(111, aspect=(1.0 / cos(mean(lat) * pi / 180.0)))
    plt.pcolormesh(lon, lat, ma.masked_invalid(cube_slice.data));
    plt.colorbar()
    plt.grid()
    date = time.units.num2date(time.points)
    date_str = date[0].strftime('%Y-%m-%d %H:%M:%S %Z')
    plt.title('%s: %s: %s' % (name, cube_slice.long_name, date_str));
    plt.show()

for dap in dap_servers:
    print "[*]  {!s}".format(dap)
    try:
        cube = iris.load_cube(dap, constraint)
    except BaseException as e:
        print "    [-]  Could not load: {!s}".format(e)
        continue
    
    print "    [-]  Identified as a Grid"
    print "    [-]  {!s}".format(cube.attributes["title"])
    try:
        try:
            cube.coord(axis='T').rename('time')
        except:
            pass
        if len(cube.shape) == 4:
            cube = cube[0, -1, ::1, ::1]
        elif len(cube.shape) == 3:
            cube = cube[0, ::1, ::1]
        elif len(cube.shape) == 2:
            cube = cube[::1, ::1]
        else:
            raise ValueError("Dimensions do not adhere to plotting requirements")
        iris_grid_plot(cube, cube.attributes["title"])
            
    except ValueError as e:
        print "    [-]  Could not plot: {!s}".format(e)
        continue    
    

# <codecell>


