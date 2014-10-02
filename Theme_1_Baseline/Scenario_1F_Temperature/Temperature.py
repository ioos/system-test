# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <markdowncell>

# ># IOOS System Test: [Baseline Assessment Theme:](https://github.com/ioos/system-test/wiki/Development-of-Test-Themes) Water Temperature

# <markdowncell>

# ### Can we find high resolution water temperature data? 
# 
# #### Questions
# 1. Is it possible to discover and access water temperature information in sensors or satellite (obs)?
# 2. Is it possible to discover and access water temperature information from models?
# 3. Can obs and model data be compared?
# 4. Is data high enough resolution (spatial and temporal) to support recreational activities?
# 5. Can we see effects of upwelling/downwelling in the temperature data?
# 6. What can we say about the spatial resolution of the data? Is that high enough that we can provide better resolution than the obs data to recreational users? 
# 
# #### Methodology
# * Define temporal and spatial bounds of interest, as well as parameters of interest
# * Search for available service endpoints in the NGDC CSW catalog meeting search criteria
# * Extract OPeNDAP data endpoints from model datasets and SOS endpoints from observational datasets
# * Obtain observation data sets from stations within the spatial boundaries
# * Plot observation stations on a map (red marker if not enough data)
# * Using DAP (model) endpoints find all available models data sets that fall in the area of interest, for the specified time range, and extract a model grid cell closest to all the given station locations
# * Plot modelled and observed time series temperature data on same axes for comparison.
# * Plot the model grid points and observation stations on the same map to show the spatial resolution

# <headingcell level=4>

# import required libraries

# <codecell>

import datetime as dt
import numpy as np
from warnings import warn
from io import BytesIO
import folium
import netCDF4
from IPython.display import HTML
import iris
from iris.exceptions import CoordinateNotFoundError, ConstraintMismatchError
iris.FUTURE.netcdf_promote = True
import matplotlib.pyplot as plt
from owslib.csw import CatalogueServiceWeb
from owslib import fes
import pandas as pd
from pyoos.collectors.coops.coops_sos import CoopsSos
from operator import itemgetter

from utilities import (fes_date_filter, collector2df, find_timevar, find_ij, nearxy, service_urls, mod_df, 
                       get_coordinates, get_station_longName, get_NERACOOS_SOS_data, inline_map, css_styles)

css_styles()

# <codecell>

%matplotlib inline

# <headingcell level=4>

# Speficy Temporal and Spatial conditions

# <codecell>

bounding_box_type = "box" 

# Bounding Box [lon_min, lat_min, lon_max, lat_max]
area = {'Hawaii': [-160.0, 18.0, -154., 23.0],
        'Gulf of Maine': [-72.0, 41.5, -67.0, 46.0],
        'New York harbor region': [-75., 39., -71., 41.5],
        'Puerto Rico': [-75, 12, -55, 26],
        'East Coast': [-77, 34, -70, 40],
        'North West': [-130, 38, -121, 50],
        'Gulf of Mexico': [-92, 28, -84, 31],
        'Arctic': [-179, 63, -140, 80],
        'North East': [-74, 40, -69, 42],
        'Virginia Beach': [-78, 33, -74, 38]}

bounding_box = area['Gulf of Maine']

#temporal range - last 7 days and next 2 days (forecast data)
jd_now = dt.datetime.utcnow()
jd_start,  jd_stop = jd_now - dt.timedelta(days=7), jd_now + dt.timedelta(days=2)

start_date = jd_start.strftime('%Y-%m-%d %H:00')
end_date = jd_stop.strftime('%Y-%m-%d %H:00')

print start_date,'to',end_date

# <headingcell level=4>

# Specify data names of interest

# <codecell>

#put the names in a dict for ease of access 
# put the names in a dict for ease of access 
data_dict = {}
sos_name = 'sea_water_temperature'
data_dict["temp"] = {"names": ['sea_water_temperature',
                               'water_temperature',
                               'sea_water_potential_temperature',
                               'water temperature',
                               'potential temperature',
                               '*sea_water_temperature',
                               'Sea-Surface Temperature',
                               'sea_surface_temperature',
                               'SST'], 
                      "sos_name":["sea_water_temperature"]}  

# <headingcell level=3>

# Search CSW for datasets of interest

# <codecell>

endpoint = 'http://www.ngdc.noaa.gov/geoportal/csw' # NGDC Geoportal
csw = CatalogueServiceWeb(endpoint,timeout=60)

# <codecell>

# convert User Input into FES filters
start, stop = fes_date_filter(start_date,end_date)
bbox = fes.BBox(bounding_box)

#use the search name to create search filter
or_filt = fes.Or([fes.PropertyIsLike(propertyname='apiso:AnyText',
                                     literal='*%s*' % val,
                                     escapeChar='\\',
                                     wildCard='*',
                                     singleChar='?') for val in data_dict["temp"]["names"]])

# <markdowncell>

# <div class="warning"><strong>ROMS model output often has Averages and History files. </strong> The Averages files are usually averaged over a tidal cycle or more, while the History files are snapshots at that time instant.  We are not interested in averaged data for this test, so in the cell below we remove any Averages files here by removing any datasets that have the term "Averages" in the metadata text.  A better approach would be to look at the `cell_methods` attributes propagated through to some term in the ISO metadata, but this is not implemented yet, as far as I know </div>

# <codecell>

val = 'Averages'
not_filt = fes.Not([fes.PropertyIsLike(propertyname='apiso:AnyText',
                                       literal=('*%s*' % val),
                                       escapeChar='\\',
                                       wildCard='*',
                                       singleChar='?')])

# try request using multiple filters "and" syntax: [[filter1,filter2]]
filter_list = [fes.And([ bbox, start, stop, or_filt, not_filt]) ]

csw.getrecords2(constraints=filter_list,maxrecords=1000,esn='full')
print str(len(csw.records)) + " csw records found"

# <markdowncell>

# #### Dap URLs

# <codecell>

dap_urls = service_urls(csw.records)
#remove duplicates and organize
dap_urls = sorted(set(dap_urls))
print "Total DAP:",len(dap_urls)
print "\n".join(dap_urls[0:10])

# <markdowncell>

# #### SOS URLs

# <codecell>

sos_urls = service_urls(csw.records,service='sos:url')
#remove duplicates and organize
sos_urls = sorted(set(sos_urls))

print "Total SOS:",len(sos_urls)
print "\n".join(sos_urls[0:5])

# <markdowncell>

# ###Get most recent observations from NOAA COOPS stations in bounding box

# <codecell>

start_time = dt.datetime.strptime(start_date,'%Y-%m-%d %H:%M')
end_time = dt.datetime.strptime(end_date,'%Y-%m-%d %H:%M')
iso_start = start_time.strftime('%Y-%m-%dT%H:%M:%SZ')
iso_end = end_time.strftime('%Y-%m-%dT%H:%M:%SZ')

# Define the Coops collector
collector = CoopsSos()
print collector.server.identification.title
collector.variables = data_dict["temp"]["sos_name"]
collector.server.identification.title

# Don't specify start and end date in the filter and the most recent observation will be returned
collector.filter(bbox=bounding_box,
                 variables=data_dict["temp"]["sos_name"])

response = collector.raw(responseFormat="text/csv")
obs_loc_df = pd.read_csv(BytesIO(response.encode('utf-8')),
                         parse_dates=True,
                         index_col='date_time')

# Now let's specify start and end times
collector.start_time = start_time
collector.end_time = end_time

ofrs = collector.server.offerings

# <codecell>

obs_loc_df.head()

# <codecell>

station_ids = [sta.split(':')[-1] for sta in obs_loc_df['station_id']]
obs_lon = [sta for sta in obs_loc_df['longitude (degree)']]
obs_lat = [sta for sta in obs_loc_df['latitude (degree)']]

# <headingcell level=3>

# Request CSV response from COOPS SOS and convert to Pandas DataFrames

# <codecell>

ts_rng = pd.date_range(start=start_date, end=end_date)
ts = pd.DataFrame(index=ts_rng)

# Save all of the observation data into a list of dataframes
obs_df = []
station_long_names = []
for sta in station_ids:
    raw_df = collector2df(collector, sta, sos_name)
    
    col = 'Observed Data'
    concatenated = pd.concat([raw_df, ts], axis=1)[col]
    obs_df.append(pd.DataFrame(concatenated))
    obs_df[-1].name = raw_df.name
    obs_df[-1].provider = raw_df.provider
    
    # Keep a master list of long names
    station_long_names.append(raw_df.name)

# <markdowncell>

# ###Get observations from NERACOOS buoys in bounding box

# <codecell>

#Loop through the NERACOOS SOS endpoints and get the data into a DataFrame
for get_caps_url in sos_urls:
    if 'neracoos' in get_caps_url:
        # Function for extracting NERACOOS data from SOS (see utilities.py)
        raw_df = get_NERACOOS_SOS_data(get_caps_url, 'http://mmisw.org/ont/cf/parameter/sea_water_temperature', iso_start, iso_end)
        if not raw_df.empty:
            col = 'Observed Data'
#             concatenated = pd.concat([raw_df, ts], axis=1)[col]
            concatenated = raw_df.merge(ts, how='outer', left_index=True, right_index=True)
            obs_df.append(pd.DataFrame(concatenated))
            obs_df[-1].name = raw_df.name
            obs_df[-1].provider = raw_df.provider
            
            obs_lat.append(float(raw_df.latitude))
            obs_lon.append(float(raw_df.longitude))
            station_long_names.append(raw_df.name)

# <markdowncell>

# ### Plot the Observation Stations on Map
# #### Purple markers are NERACOOS buoys, blue markers are CO-OPS stations

# <codecell>

min_data_pts = 20

# Find center of bounding box
lat_center = abs(bounding_box[3]-bounding_box[1])/2 + bounding_box[1]
lon_center = abs(bounding_box[0]-bounding_box[2])/2 + bounding_box[0]
m = folium.Map(location=[lat_center, lon_center], zoom_start=6)

# Add WMS layer for water temperature
m.add_wms_layer(wms_name="Daily Gridded Global Sea Surface Temperature Analysis",
                  wms_url="http://nowcoast.noaa.gov/wms/com.esri.wms.Esrimap/analyses?service=wms&version=1.1.1&request=GetCapabilities",
                  wms_format="image/png",
                  wms_layers= "NCEP_RAS_ANAL_RTG_SST"
                  )    
    
m.add_layers_to_map()

n = 0
for df in obs_df:
    #get the station data from the sos end point
    longname = df.name
    lat = obs_lat[n]
    lon = obs_lon[n]
    if 'NERACOOS' in df.provider:
        color = 'purple'
    else:
        color = 'blue'
    popup_string = ('<b>Station:</b><br>'+ str(longname))
    m.simple_marker([lat, lon], popup=popup_string, marker_color=color)
    n += 1

m.line(get_coordinates(bounding_box,bounding_box_type), line_color='#FF0000', line_weight=5)
inline_map(m)

# <markdowncell>

# ### Plot water temperature for each station

# <codecell>

for df in obs_df:
    if len(df) > min_data_pts:
        fig, axes = plt.subplots(figsize=(20,5))
        df['Observed Data'].plot()
        axes.set_title(df.name)
        axes.set_ylabel('Temperature (C)')

# <markdowncell>

# ###Get model output from OPeNDAP URLS
# Try to open all the OPeNDAP URLS using Iris from the British Met Office. If we can open in Iris, we know it's a model result.

# <codecell>

name_in_list = lambda cube: cube.standard_name in data_dict['temp']['names']
constraint = iris.Constraint(cube_func=name_in_list)

# <codecell>

def z_coord(cube):
    """Heuristic way to return the dimensionless vertical coordinate."""
    try:
        z = cube.coord(axis='Z')
    except CoordinateNotFoundError:
        z = cube.coords(axis='Z')
        for coord in cube.coords(axis='Z'):
            if coord.ndim == 1:
                z = coord
    return z


# <codecell>

# Create list of model DataFrames for each station
model_df = []
for df in obs_df:
    model_df.append(pd.DataFrame(index=ts.index))
    model_df[-1].name = df.name

# Use only data within 0.10 degrees (about 10 km)
max_dist = 0.10

# Use only data where the standard deviation of the time series exceeds 0.01 m (1 cm).
# This eliminates flat line model time series that come from land points that should have had missing values.
min_var = 0.01
for url in dap_urls:
    if 'SOS' in url:
        continue
    try:
        print url
        a = iris.load_cube(url, constraint)
        # take first 30 chars for model name
        mod_name = a.attributes['title'][0:30]
        r = a.shape
        timevar = find_timevar(a)
        lat = a.coord(axis='Y').points
        lon = a.coord(axis='X').points
        
        jd = timevar.units.num2date(timevar.points)
        start = timevar.units.date2num(jd_start)
        istart = timevar.nearest_neighbour_index(start)
        stop = timevar.units.date2num(jd_stop)
        istop = timevar.nearest_neighbour_index(stop)

        # Only proceed if we have data in the range requested.
        if istart != istop:
            nsta = len(station_long_names)

            if len(r) == 4:
                print('[Structured grid model]:', url)
#                 zc = a.coord(axis='Z').points
#                 zlev = max(enumerate(zc),key=itemgetter(1))[0]
                z = z_coord(a)
                if z:
                    positive = z.attributes.get('positive', None)
                    if positive == 'up':
                        zlev = np.unique(z.points.argmax(axis=0))[0]
                    else:
                        zlev = np.unique(z.points.argmin(axis=0))[0]
#                     c = cube[idx, ...].copy()
                else:
                    zlev = None
                positive = a.coord(axis='Z').attributes.get('positive', None)
                if positive == 'up':
                    zlev = np.argmax(a.coord(axis='Z').points)
                else:
                    zlev = np.argmin(a.coord(axis='Z').points)
                
                d = a[0, 0, :, :].data
                # Find the closest non-land point from a structured grid model.
                if len(lon.shape) == 1:
                    lon, lat = np.meshgrid(lon, lat)
                j, i, dd = find_ij(lon, lat, d, obs_lon, obs_lat)
                for n in range(nsta):
                    # Only use if model cell is within 0.01 degree of requested
                    # location.
                    if dd[n] <= max_dist:
                        arr = a[istart:istop, zlev, j[n], i[n]].data
                        if arr.std() >= min_var:
                            c = mod_df(arr, timevar, istart, istop,
                                       mod_name, ts)
                            name = obs_df[n].name
                            model_df[n] = pd.concat([model_df[n], c], axis=1)
                            model_df[n].name = name
            elif len(r) == 3:
                print('[Unstructured grid model]:', url)
#                 zc = a.coord(axis='Z').points
#                 zlev = max(enumerate(zc),key=itemgetter(1))[0]
#                 positive = a.coord(axis='Z').attributes.get('positive', None)
#                 if positive == 'up':
#                     zlev = np.argmax(a.coord(axis='Z').points)
#                 else:
#                     zlev = np.argmin(a.coord(axis='Z').points)
                z = z_coord(a)
                if z:
                    positive = z.attributes.get('positive', None)
                    if positive == 'up':
                        zlev = np.unique(z.points.argmax(axis=0))[0]
                    else:
                        zlev = np.unique(z.points.argmin(axis=0))[0]
#                     c = cube[idx, ...].copy()
                else:
                    zlev = None
                # Find the closest point from an unstructured grid model.
                index, dd = nearxy(lon.flatten(), lat.flatten(),
                                   obs_lon, obs_lat)
                for n in range(nsta):
                    # Only use if model cell is within 0.1 degree of requested
                    # location.
                    if dd[n] <= max_dist:
                        arr = a[istart:istop, zlev, index[n]].data
                        if arr.std() >= min_var:
                            c = mod_df(arr, timevar, istart, istop,
                                       mod_name, ts)
                            name = obs_df[n].name
                            model_df[n] = pd.concat([model_df[n], c], axis=1)
                            model_df[n].name = name
            elif len(r) == 1:
                print('[Data]:', url)
    except (ValueError, RuntimeError, CoordinateNotFoundError,
            ConstraintMismatchError) as e:
        warn("\n%s\n" % e)
    except MemoryError as e:
        warn("Ran out of memory while attempting to load model '%s'! %s\n" % (url, e))

# <markdowncell>

# ### Plot Modeled vs Obs Water Temperature

# <codecell>

for count, df in enumerate(obs_df):
    if not model_df[count].empty and not df.empty:
        fig, ax = plt.subplots(figsize=(20,5))
        
        # Plot the model data
        model_df[count].plot(ax=ax, title=model_df[count].name, legend=True)
        
        # Overlay the obs data (resample to hourly instead of 6 mins!)
#         df['Observed Data'].resample('H', how='mean').plot(ax=ax, title=df.name, color='k', linewidth=2, legend=True)
        df['Observed Data'].plot(ax=ax, title=df.name, color='k', linewidth=2, legend=True)
        ax.set_ylabel('Sea Water Temperature (C)')
        ax.legend(loc='right')
        plt.show()

# <markdowncell>

# ### Let's look at the spatial resolution of the obs and model data
# 
# #### Let's just look at one model, COAWST Forecast System : USGS : US East Coast

# <codecell>

m = folium.Map(location=[lat_center, lon_center], zoom_start=6)

url = 'http://geoport.whoi.edu/thredds/dodsC/coawst_4/use/fmrc/coawst_4_use_best.ncd'
nc_ds = netCDF4.Dataset(url)
# print nc_ds.variables
time  = nc_ds.variables['time']
lat  = nc_ds.variables['lat_rho'][:]
lon  = nc_ds.variables['lon_rho'][:]
nc_ds.close()

# Now flatten the lat lon arrays to 1-D
flat_lat = [x for sublist in lat for x in sublist]
flat_lon = [x for sublist in lon for x in sublist]


for lat, lon in zip(flat_lat, flat_lon):
    if (lon > bounding_box[0] and lon < bounding_box[2]) and (lat > bounding_box[1] and lat < bounding_box[3]):
        m.circle_marker([lat, lon]) #popup=str(lat)+','+str(lon))

# Now overlay the obs stattions                
n = 0
for df in obs_df:
    #get the station data from the sos end point
    longname = df.name
    lat = obs_lat[n]
    lon = obs_lon[n]
    if 'NERACOOS' in df.provider:
        color = 'purple'
    else:
        color = 'blue'
    popup_string = ('<b>Station:</b><br>'+ str(longname))
    m.simple_marker([lat, lon], popup=popup_string, marker_color=color)
    n += 1
    
m.line(get_coordinates(bounding_box,bounding_box_type), line_color='#FF0000', line_weight=5)

inline_map(m)

# <markdowncell>

# ### Conclusions
# 
# 1. Observed water temperature data can be obtained through CO-OPS stations
# 2. It is possible to obtain modeled forecast water temperature data, just not in all locations.
# 3. It is possible to compare the obs and model data by downsampling the observed data.
# 4. The observed data is available in high resolution (6 mins), making it useful to support recreational activities like surfing.
# 5. When combined with wind direction and speed, it may be possible to see the effects of upwelling/downwelling on water temperature.
# 6. The model definitely has better spatial resolution than the observation stations

