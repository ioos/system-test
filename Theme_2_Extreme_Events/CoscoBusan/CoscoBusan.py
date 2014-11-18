# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <codecell>

from utilities import * 
css_styles()

# <markdowncell>

# # IOOS System Test - Theme 2
# 
# ## CoscoBusan
# * November 7, 2007 at 8:27 AM the container ship M/V Cosco Busan strikes the San Francisco Bay Bridge tearing a 100 ft. long gash in its hull over the fuel tanks.
# * 50,000 gals of bunker fuel discharges into the Bay in approximately 10 seconds.
# * The USCG and DFG are notified of an incident and respond immediately, on-scene in 50 minutes.

# <codecell>

from pylab import *
from IPython.display import HTML

# <markdowncell>

# #### Geographic subset

# <codecell>

bounding_box = [ -123.38, 37.05, -121.53, 38.37]  # San Francisco Bay and surrounding waters

"Geographic subset: {!s}".format(bounding_box)

# <markdowncell>

# #### Temporal subset

# <codecell>

from datetime import datetime
start_date = datetime(2007,11,1)
start_date_string = start_date.strftime('%Y-%m-%d %H:00')

end_date = datetime(2007,11,14)
end_date_string = end_date.strftime('%Y-%m-%d %H:00')

"Temporal subset: ( {!s} to {!s} )".format(start_date_string, end_date_string)

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

# Geographic filters
geographic_filter = fes.BBox(bbox=bounding_box)

# Temporal filters
temporal_filter = fes_date_filter(start_date_string, end_date_string)

filters = fes.And([geographic_filter, temporal_filter])

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

titles = []
urls = []
service_types = []
servers = []
for url in bbox_endpoints:
    print "*", url
    try:
        csw = CatalogueServiceWeb(url, timeout=20)
        csw.getrecords2(constraints=[filters], maxrecords=200, esn='full')
        for record, item in csw.records.items():
            try:
                # Get title
                if len(item.title) > 80:
                   title = "{!s}...{!s}".format(item.title[0:40], item.title[-40:])
                else:
                    title = item.title
                service_url, scheme = next(((d['url'], d['scheme']) for d in item.references), None)
                if service_url:    
                    print "    [x] {!s}".format(title)
                    titles.append(item.title)
                    urls.append(service_url)
                    service_types.append(scheme)
                    servers.append(url)
            except:
                continue
    except BaseException as e:
        print "    [-] FAILED: {!s}".format(e)

# <markdowncell>

# #### What service are available?

# <codecell>

import pandas as pd
srvs = pd.DataFrame(zip(titles, urls, service_types, servers), columns=("Title", "URL", "Service Type", "Server"))
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

# <div class="error" style="text-align: center"><strong>52N SOS Link is not correct</strong> - <a href="https://github.com/ioos/system-test/issues/189">Issue #189</a><br />http://sos.cencoos.org/sos/sos/json should be referencing http://sos.cencoos.org/sos/sos as the SOS server.</div>

# <markdowncell>

# #### Set some variables to pull from SOS servers

# <codecell>

variables_to_query = ["sea_water_temperature", "surface_temperature_anomaly", "air_temperature"]

# <markdowncell>

# #### Pull out all observation from all SOS servers

# <codecell>

from pyoos.collectors.ioos.swe_sos import IoosSweSos
from pyoos.collectors.coops.coops_sos import CoopsSos
from pyoos.collectors.ndbc.ndbc_sos import NdbcSos
from owslib.ows import ExceptionReport
from datetime import timedelta
from copy import copy
from StringIO import StringIO

sos_dfs = []
for sos in sos_servers:
    if "co-ops" in sos.lower() or "ndbc" in sos.lower():
        
        # CSV Output
    
        if "co-ops" in sos.lower():
            # Use the COOPS collector
            collector = CoopsSos()
        elif "ndbc" in sos.lower():
            # Use the NDBC collector
            collector = NdbcSos()
        for v in variables_to_query:
            collector.filter(variables=[v])
            collector.filter(bbox=bounding_box)
            new_start = copy(start_date)
            new_end   = copy(start_date)

            # Hold dataframe for periodic concat
            v_frame = None

            while new_end < end_date:
                new_end = min(end_date, new_start + timedelta(days=1))
                collector.filter(start=new_start)
                collector.filter(end=new_end)
                try:
                    print "Collecting from {!s}: ({!s} -> {!s})".format(sos, new_start, new_end)
                    data = collector.raw()
                    new_frame = pd.DataFrame.from_csv(StringIO(data))
                    new_frame = new_frame.reset_index()
                    if v_frame is None:
                        v_frame = new_frame
                    else:
                        v_frame = pd.concat([v_frame, new_frame])
                        v_frame = v_frame.drop_duplicates()
                except ExceptionReport as e:
                    print "  [-] Error obtaining {!s} from {!s} - Message from server: {!s}".format(v, sos, e)
                    continue
                finally:
                    new_start = new_end

            if v_frame is not None:
                sos_dfs.append(v_frame)
    
    else:
        # Use the generic IOOS SWE collector
        try:
            collector = IoosSweSos(sos)
        except BaseException as e:
            print "[-]  Could not process {!s}.  Reason: {!s}".format(sos, e)
            continue
            
        for v in variables_to_query:
            collector.filter(variables=[v])
            collector.filter(bbox=bounding_box)
            collector.filter(start=start_date)
            collector.filter(end=end_date)
            collector.filter(variables=[v])
            try:
                data = collector.collect()
                print data
            except BaseException as e:
                print "[-]  Could not process {!s}.  Reason: {!s}".format(sos, e)
                continue
    

# <markdowncell>

# <div class="success" style="text-align: center"><strong>NOTE</strong><br />We are only plotting the first variable retrieved back from the SOS server.  The following graphs could be in a loop.</div>

# <codecell>

pd.set_option('display.max_rows', 10)

# <markdowncell>

# #### Number of measurments per sensor

# <codecell>

pd.DataFrame(sos_dfs[0].groupby("sensor_id").size(), columns=("Number of measurments",))

# <codecell>

graphing_frame = sos_dfs[0].pivot(index='date_time', columns='sensor_id', values=sos_dfs[0].columns[-1])
graphing_frame

# <codecell>

%matplotlib inline

for col in graphing_frame.columns:
    fig, axes = plt.subplots(figsize=(20,5))
    graphing_frame[col].dropna().plot(title=col, color='m')
    axes.set_xlabel("Time (UTC)")
    axes.set_ylabel(sos_dfs[0].columns[-1])

# <markdowncell>

# # DAP

# <codecell>

def find_dap(x):
    d = x.lower()
    if ("dap" in d or "dods" in d) and "tabledap" not in d and "sos" not in d:
        return x
    return None

# <codecell>

import os
dap_servers = filter(None, srvs["URL"].map(find_dap))
dap_servers = map(lambda x: os.path.splitext(x)[0], dap_servers)
dap_servers

# <markdowncell>

# #### Try to temperature data from all of the DAP endpoints at the time of the spill

# <codecell>

import pytz
spill_time = datetime(2007, 11, 7, 8, 47, tzinfo=pytz.timezone("US/Pacific"))
"Spill time: {!s}".format(spill_time)

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
    except Exception as e:
        print "    [-]  Could not load: {!s}".format(e)
        continue
    
    print "    [-]  Identified as a Grid"
    print "    [-]  {!s}".format(cube.attributes["title"])
    try:
        if len(cube.shape) > 2:
            try:
                cube.coord(axis='T').rename('time')
            except:
                pass
            time_dim   = cube.coord('time')
            time_value = time_dim.units.date2num(spill_time)
            time_index = time_dim.nearest_neighbour_index(time_value)
            time_pts   = time_dim.points[time_index]
    
            if len(cube.shape) == 4:
                cube = cube.extract(iris.Constraint(time=time_pts))
                cube = cube[-1, ::1, ::1]
            elif len(cube.shape) == 3:
                cube = cube.extract(iris.Constraint(time=time_pts))
                cube = cube[::1, ::1]
        elif len(cube.shape) == 2:
            cube = cube[::1, ::1]
        else:
            raise ValueError("Dimensions do not adhere to plotting requirements")
        iris_grid_plot(cube, cube.attributes["title"])
            
    except ValueError as e:
        print "    [-]  Could not plot: {!s}".format(e)
        continue    
    

# <codecell>


