# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <markdowncell>

# ># IOOS System Test: [Extreme Events Theme:](https://github.com/ioos/system-test/wiki/Development-of-Test-Themes#theme-2-extreme-events) Coastal Inundation

# <markdowncell>

# ### Can we compare observed and modeled current speeds at stations located within a bounding box? 
# This notebook is based on [IOOS System Test: Inundation](http://nbviewer.ipython.org/github/ioos/system-test/blob/master/Theme_2_Extreme_Events/Scenario_2A_Coastal_Inundation/Scenario_2A_Water_Level_Signell.ipynb)
# 
# Methodology:
# * Define temporal and spatial bounds of interest, as well as parameters of interest
# * Search for available service endpoints in the NGDC CSW catalog meeting search criteria
# * Extract OPeNDAP data endpoints from model datasets and SOS endpoints from observational datasets
# * Obtain observation data sets from stations within the spatial boundaries
# * Plot observation stations on a map (red marker if not enough data)
# * Using DAP (model) endpoints find all available models data sets that fall in the area of interest, for the specified time range, and extract a model grid cell closest to all the given station locations
# * Plot modelled and observed time series current data on same axes for comparison
# 

# <headingcell level=4>

# import required libraries

# <codecell>

import datetime as dt
from warnings import warn

import folium
from IPython.display import HTML
import iris
from iris.exceptions import CoordinateNotFoundError, ConstraintMismatchError
import matplotlib.pyplot as plt
from owslib.csw import CatalogueServiceWeb
from owslib import fes
import pandas as pd
from pyoos.collectors.ndbc.ndbc_sos import NdbcSos
from pyoos.collectors.coops.coops_sos import CoopsSos
import requests

from utilities import (date_range, coops2df, coops2data, find_timevar, find_ij, nearxy, service_urls, mod_df, 
                       get_coordinates, get_Coops_longName, inline_map)

import cStringIO
from lxml import etree
import urllib2

# <headingcell level=4>

# Speficy Temporal and Spatial conditions

# <codecell>

bounding_box_type = "box" 

# Bounding Box [lon_min, lat_min, lon_max, lat_max]
area = {'Hawaii': [-160.0, 18.0, -154., 23.0],
        'Gulf of Maine': [-72.0, 41.0, -69.0, 43.0],
        'New York harbor region': [-75., 39., -71., 41.5],
        'Puerto Rico': [-71, 14, -60, 24],
        'East Coast': [-77, 34, -70, 40],
        'North West': [-130, 38, -121, 50]}

bounding_box = area['North West']

#temporal range
jd_now = dt.datetime.utcnow()
jd_start,  jd_stop = jd_now - dt.timedelta(days=4), jd_now #+ dt.timedelta(days=3)

start_date = jd_start.strftime('%Y-%m-%d %H:00')
stop_date = jd_stop.strftime('%Y-%m-%d %H:00')

jd_start = dt.datetime.strptime(start_date, '%Y-%m-%d %H:%M')
jd_stop = dt.datetime.strptime(stop_date, '%Y-%m-%d %H:%M')
print start_date,'to',stop_date

# <headingcell level=4>

# Specify data names of interest

# <codecell>

#put the names in a dict for ease of access 
data_dict = {}
sos_name = 'Currents'
data_dict['currents'] = {"names":['currents','surface_eastward_sea_water_velocity','*surface_eastward_sea_water_velocity*'], 
                      "sos_name":['currents']}  

# <headingcell level=3>

# Search CSW for datasets of interest

# <codecell>

endpoint = 'http://www.ngdc.noaa.gov/geoportal/csw' # NGDC Geoportal
csw = CatalogueServiceWeb(endpoint,timeout=60)

for oper in csw.operations:
    if oper.name == 'GetRecords':
        cnstr = oper.constraints['SupportedISOQueryables']['values']
        print('\nISO Queryables:%s\n' % '\n'.join(cnstr))

# <codecell>

# convert User Input into FES filters
start,stop = date_range(start_date,stop_date)
bbox = fes.BBox(bounding_box)

#use the search name to create search filter
or_filt = fes.Or([fes.PropertyIsLike(propertyname='apiso:AnyText',literal=('*%s*' % val),
                    escapeChar='\\',wildCard='*',singleChar='?') for val in data_dict['currents']['names']])

val = 'Averages'
not_filt = fes.Not([fes.PropertyIsLike(propertyname='apiso:AnyText',
                                       literal=('*%s*' % val),
                                       escapeChar='\\',
                                       wildCard='*',
                                       singleChar='?')])
filter_list = [fes.And([ bbox, start, stop, or_filt, not_filt]) ]
# connect to CSW, explore it's properties
# try request using multiple filters "and" syntax: [[filter1,filter2]]
csw.getrecords2(constraints=filter_list, maxrecords=1000, esn='full')
print str(len(csw.records)) + " csw records found"
for rec, item in csw.records.items():
    print(item.title)

# <markdowncell>

# Dap URLS

# <codecell>

dap_urls = service_urls(csw.records)
#remove duplicates and organize
dap_urls = sorted(set(dap_urls))
print "Total DAP:",len(dap_urls)
#print the first 5...
print "\n".join(dap_urls[0:8])

# <markdowncell>

# SOS URLs

# <codecell>

sos_urls = service_urls(csw.records,service='sos:url')
#remove duplicates and organize
#if len(sos_urls) ==0:
sos_urls.append("http://sdf.ndbc.noaa.gov/sos/server.php")  #?request=GetCapabilities&service=SOS

sos_urls = sorted(set(sos_urls))
print "Total SOS:",len(sos_urls)
print "\n".join(sos_urls)

# <markdowncell>

# ### SOS Requirements

# <codecell>

start_time = dt.datetime.strptime(start_date,'%Y-%m-%d %H:%M')
end_time = dt.datetime.strptime(stop_date,'%Y-%m-%d %H:%M')
iso_start = start_time.strftime('%Y-%m-%dT%H:%M:%SZ')
iso_end = end_time.strftime('%Y-%m-%dT%H:%M:%SZ')

# <codecell>

collector = CoopsSos()
collector.start_time = start_time
collector.end_time = end_time
collector.variables = data_dict["currents"]["sos_name"]
collector.server.identification.title
print collector.start_time,":", collector.end_time
ofrs = collector.server.offerings
print(len(ofrs))
#for p in ofrs[700:710]:
#    print(p)

# <markdowncell>

# ###Find all SOS stations within the bounding box and time extent
# The time extent (iso_start) must be a match a timestamp in the data set. This buoy collects data hourly at the 50 minute mark.

# <codecell>

print "Date: ",iso_start," to ", iso_end
box_str=','.join(str(e) for e in bounding_box)
print "Lat/Lon Box: ",box_str

url = (('http://opendap.co-ops.nos.noaa.gov/ioos-dif-sos/SOS?'
       'service=SOS&request=GetObservation&version=1.0.0&'
       'observedProperty=%s&bin=1&'
       'offering=urn:ioos:network:NOAA.NOS.CO-OPS:CurrentsActive&'
       'featureOfInterest=BBOX:%s&responseFormat=text/csv') % (sos_name, box_str))

print url
obs_loc_df = pd.read_csv(url)

# <codecell>

obs_loc_df = obs_loc_df.loc[obs_loc_df['bin (count)']==1,:]
obs_loc_df.head()

# <codecell>

obs_loc_df.loc[obs_loc_df['bin (count)']==1,:]

# <codecell>

# Index the data frame to filter repeats by bin #
stations = [sta.split(':')[-1] for sta in obs_loc_df['station_id']]

obs_lon = [sta for sta in obs_loc_df['longitude (degree)']]
obs_lat = [sta for sta in obs_loc_df['latitude (degree)']]

# <headingcell level=3>

# Request CSV response from collector and convert to Pandas DataFrames

# <codecell>

def coops2data2(collector, station_id, sos_name):
    """Extract the Observation Data from the collector."""
    collector.features = [station_id]
    collector.variables = [sos_name]
    long_name = get_Coops_longName(station_id)
    
#     # Get the data!
#     link = "http://tidesandcurrents.noaa.gov/api/datagetter?product="
#     link += sos_name + "&application=NOS.COOPS.TAC.WL&"
#     date1 = "begin_date="+jd_start.strftime('%Y%m%d')
#     date2 = "&end_date="+jd_stop.strftime('%Y%m%d')
#     units = "&units=metric"
#     station_request = "&station=%s" % station_id
#     station_request += "&time_zone=GMT&units=english&format=csv"
#     http_request = link + date1 + date2 + units + station_request
    
    url = (('http://opendap.co-ops.nos.noaa.gov/ioos-dif-sos/SOS?'
       'service=SOS&request=GetObservation&version=1.0.0'
       '&observedProperty=currents&offering=urn:ioos:station:NOAA.NOS.CO-OPS:%s'
       '&responseFormat=text/csv&eventTime=%s/%s') % (str(station_id),iso_start, iso_end))
    
    print url
#     response = collector.raw(responseFormat="text/csv")
#     data_df = read_csv(BytesIO(response.encode('utf-8')),
#                            parse_dates=True,
#                            index_col='date_time')
#     data_df = pd.read_csv(http_request,
#                           parse_dates=True,
#                           index_col='Date Time')
    data_df = pd.read_csv(url, parse_dates=True, index_col='date_time')
#     col = 'sea_water_speed (cm/s)'
#     data_df['Observed Data'] = data_df[col]
    data_df.name = long_name
    return data_df

# <codecell>

# ts_rng = pd.date_range(start=start_date, end=stop_date)
# ts = pd.DataFrame(index=ts_rng)

obs_df = []
sta_names = []
sta_failed = []
for sta in stations:
    try:
        df = coops2data2(collector, sta, sos_name)
    except Exception as e:
        print "Error" + str(e)
        continue
#     print b
    name = df.name
    sta_names.append(name)
    if df.empty:
        sta_failed.append(name)
        df = DataFrame(np.arange(len(ts)) * np.NaN, index=ts.index, columns=['Observed Data'])
        df.name = name
    # Limit interpolation to 10 points (10 @ 6min = 1 hour).
#     col = 'sea_water_speed (cm/s)'
#     concatenated = pd.concat([b, ts], axis=1).interpolate(limit=10)[col]
#     obs_df.append(pd.DataFrame(concatenated))
#     pieces = pd.concat([df['sea_water_speed (cm/s)'], df[3:7]])
#     obs_df.append(pd.DataFrame(df[col]))
    # Now split up the data frame into bins
#     num_bins = max(df['bin (count)'].values)
    obs_df.append(df)
    obs_df[-1].name = name



# <codecell>

# print df
num_bins = max(df['bin (count)'].values)
new_df = []

for n in range(num_bins):
    new_df.append(obs_df[0].loc[obs_df[0]['bin (count)']==(n+1),'sea_water_speed (cm/s)'])
    
    new_df[-1].name = obs_df[0].name

print new_df[0:1]
# print max(obs_df[0]['bin (count)'].values)
# obs_df[0].loc[obs_df[0]['bin (count)']==1,:]
# print new_df[0:2]
for df2 in new_df:
    ax = df2.plot(figsize=(14, 6), title=df2.name, legend=False)
    plt.setp(ax.lines[0], linewidth=4.0, zorder=1)
    ax.legend()
    ax.set_ylabel('Current Speed (cm/s)')
    

# <codecell>

start = df.index.searchsorted(jd_start)
stop = df.index.searchsorted(jd_start+dt.timedelta(minutes=6))
sliced = df.ix[start:stop]
print sliced

# <codecell>

for df in obs_df:
    ax = df.plot(figsize=(14, 6), title=df.name, legend=False)
    plt.setp(ax.lines[0], linewidth=4.0, zorder=1)
    ax.legend()
    ax.set_ylabel('Current Speed (cm/s)')

# <codecell>

min_data_pts = 0
#find center of bounding box
lat_center = abs(bounding_box[3] - bounding_box[1])/2 + bounding_box[1]
lon_center = abs(bounding_box[0]-bounding_box[2])/2 + bounding_box[0]
m = folium.Map(location=[lat_center, lon_center], zoom_start=6)

for n in range(len(stations)):
    #get the station data from the sos end point
    name = stations[n]
#     shortname = obs_df['station_id'][n].split(':')[-1]
    longname = obs_df[n].name
    lat = obs_lat[n]
    lon = obs_lon[n]
    popup_string = ('<b>Station:</b><br>'+ longname)
#     if len(obs_df[n]) > min_data_pts:
    m.simple_marker([lat, lon], popup=popup_string)
#     else:
#         #popup_string += '<br>No Data Available'
#         popup_string += '<br>Not enough data available<br>requested pts: ' + str(min_data_pts ) + '<br>Available pts: ' + str(len(obs_df[n]))
#         m.circle_marker([lat, lon], popup=popup_string, fill_color='#ff0000', radius=10000, line_color='#ff0000')
print type(bounding_box)
m.line(get_coordinates(bounding_box, bounding_box_type), line_color='#FF0000', line_weight=5)

inline_map(m)

# <markdowncell>

# ###Get model output from OPeNDAP URLS
# Try to open all the OPeNDAP URLS using Iris from the British Met Office. If we can open in Iris, we know it's a model result.

# <codecell>

print data_dict['currents']['names']
name_in_list = lambda cube: cube.standard_name in data_dict['currents']['names']
constraint = iris.Constraint(cube_func=name_in_list)
 

# <codecell>

# Use only data within 0.04 degrees (about 4 km).
max_dist = 0.04
# Use only data where the standard deviation of the time series exceeds 0.01 m (1 cm).
# This eliminates flat line model time series that come from land points that should have had missing values.
min_var = 0.01
for url in dap_urls:
    try:
        a = iris.load_cube(url, constraint)
        # convert to units of meters
        # a.convert_units('m')     # this isn't working for unstructured data
        # take first 20 chars for model name
        mod_name = a.attributes['title'][0:20]
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
            nsta = len(obs_lon)
            if len(r) == 3:
                print('[Structured grid model]:', url)
                d = a[0, :, :].data
                # Find the closest non-land point from a structured grid model.
                if len(lon.shape) == 1:
                    lon, lat = np.meshgrid(lon, lat)
                j, i, dd = find_ij(lon, lat, d, obs_lon, obs_lat)
                for n in range(nsta):
                    # Only use if model cell is within 0.1 degree of requested
                    # location.
                    if dd[n] <= max_dist:
                        arr = a[istart:istop, j[n], i[n]].data
                        if arr.std() >= min_var:
                            c = mod_df(arr, timevar, istart, istop,
                                       mod_name, ts)
                            name = obs_df[n].name
                            obs_df[n] = concat([obs_df[n], c], axis=1)
                            obs_df[n].name = name
            elif len(r) == 2:
                print('[Unstructured grid model]:', url)
                # Find the closest point from an unstructured grid model.
                index, dd = nearxy(lon.flatten(), lat.flatten(),
                                   obs_lon, obs_lat)
                for n in range(nsta):
                    # Only use if model cell is within 0.1 degree of requested
                    # location.
                    if dd[n] <= max_dist:
                        arr = a[istart:istop, index[n]].data
                        if arr.std() >= min_var:
                            c = mod_df(arr, timevar, istart, istop,
                                       mod_name, ts)
                            name = obs_df[n].name
                            obs_df[n] = concat([obs_df[n], c], axis=1)
                            obs_df[n].name = name
            elif len(r) == 1:
                print('[Data]:', url)
    except (ValueError, RuntimeError, CoordinateNotFoundError,
            ConstraintMismatchError) as e:
        warn("\n%s\n" % e)
        pass

# <codecell>

print obs_df

# <codecell>

# Use only data within 0.04 degrees (about 4 km).
max_dist = 0.04
# Use only data where the standard deviation of the time series exceeds 0.01 m (1 cm).
# This eliminates flat line model time series that come from land points that should have had missing values.
min_var = 0.01
for url in dap_urls:
    print url
    try:
        a = iris.load_cube(url, constraint)
        # convert to units of meters
        # a.convert_units('m')     # this isn't working for unstructured data
        # take first 20 chars for model name
        mod_name = a.attributes['title'][0:20]
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
            nsta = len(obs_lon)
            if len(r) == 3:
                print('[Structured grid model]:', url)
                d = a[0, :, :].data
                # Find the closest non-land point from a structured grid model.
                if len(lon.shape) == 1:
                    lon, lat = np.meshgrid(lon, lat)
                j, i, dd = find_ij(lon, lat, d, obs_lon, obs_lat)
                for n in range(nsta):
                    # Only use if model cell is within 0.01 degree of requested
                    # location.
                    if dd[n] <= max_dist:
                        arr = a[istart:istop, j[n], i[n]].data
                        if arr.std() >= min_var:
                            c = mod_df(arr, timevar, istart, istop,
                                       mod_name, ts)
                            name = obs_df[n].name
                            obs_df[n] = pd.concat([obs_df[n], c], axis=1)
                            obs_df[n].name = name
            elif len(r) == 2:
                print('[Unstructured grid model]:', url)
                # Find the closest point from an unstructured grid model.
                index, dd = nearxy(lon.flatten(), lat.flatten(),
                                   obs_lon, obs_lat)
                for n in range(nsta):
                    # Only use if model cell is within 0.1 degree of requested
                    # location.
                    if dd[n] <= max_dist:
                        arr = a[istart:istop, index[n]].data
                        if arr.std() >= min_var:
                            c = mod_df(arr, timevar, istart, istop,
                                       mod_name, ts)
                            name = obs_df[n].name
                            obs_df[n] = pd.concat([obs_df[n], c], axis=1)
                            obs_df[n].name = name
            elif len(r) == 1:
                print('[Data]:', url)
    except (ValueError, RuntimeError, CoordinateNotFoundError,
            ConstraintMismatchError) as e:
        warn("\n%s\n" % e)
        pass

# <codecell>

# Create time index for model DataFrame
ts_rng = pd.date_range(start=jd_start, end=jd_stop, freq='6Min')
ts = pd.DataFrame(index=ts_rng)

#Get the station lat/lon into lists and create list of model DataFrames for each station
obs_lon = []
obs_lat = []
model_df = []
for sta in station_list:
    obs_lon.append(float(sta['longitude']))
    obs_lat.append(float(sta['latitude']))
    model_df.append(pd.DataFrame(index=ts.index))
    model_df[-1].name = sta['long_name']

# Use only data within 0.04 degrees (about 4 km).
max_dist = 0.04
# Use only data where the standard deviation of the time series exceeds 0.01 m (1 cm).
# This eliminates flat line model time series that come from land points that should have had missing values.
min_var = 0.01
for url in dap_urls:
    try:
        print 'Attemping to load {0}'.format(url)
        a = iris.load_cube(url, constraint)
        # convert to units of meters
        # a.convert_units('m')     # this isn't working for unstructured data
        # take first 20 chars for model name
        mod_name = a.attributes['title'][0:20]
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
            nsta = len(station_list)
            if len(r) == 3:
                print('[Structured grid model]:', url)
                d = a[0, :, :].data
                # Find the closest non-land point from a structured grid model.
                if len(lon.shape) == 1:
                    lon, lat = np.meshgrid(lon, lat)
                j, i, dd = find_ij(lon, lat, d, obs_lon, obs_lat)
                for n in range(nsta):
                    # Only use if model cell is within 0.01 degree of requested
                    # location.
                    if dd[n] <= max_dist:
                        arr = a[istart:istop, j[n], i[n]].data
                        if arr.std() >= min_var:
                            c = mod_df(arr, timevar, istart, istop,
                                       mod_name, ts)
                            name = station_list[n]['long_name']
                            model_df[n] = pd.concat([model_df[n], c], axis=1)
                            model_df[n].name = name
                            
            elif len(r) == 2:
                print('[Unstructured grid model]:', url)
                # Find the closest point from an unstructured grid model.
                index, dd = nearxy(lon.flatten(), lat.flatten(),
                                   obs_lon, obs_lat)
                for n in range(nsta):
                    # Only use if model cell is within 0.1 degree of requested
                    # location.
                    if dd[n] <= max_dist:
                        arr = a[istart:istop, index[n]].data
                        if arr.std() >= min_var:
                            c = mod_df(arr, timevar, istart, istop,
                                       mod_name, ts)
                            name = station_list[n]['long_name']
                            model_df[n] = pd.concat([model_df[n], c], axis=1)
                            model_df[n].name = name
            elif len(r) == 1:
                print('[Data]:', url)
    except (ValueError, RuntimeError, CoordinateNotFoundError,
            ConstraintMismatchError) as e:
        warn("\n%s\n" % e)
        pass

# <codecell>

print obs_df

# <markdowncell>

# #### Plot Modeled vs Obs Wave Height

# <codecell>

for n in range(len(Hs_obs_df)):
    if Hs_obs_df[n]['Observed Wave Height Data'].count() > min_data_pts:
        ax = Hs_obs_df[n].plot(figsize=(14, 6), title=Hs_obs_df[n].name, legend=False)
        plt.setp(ax.lines[0], linewidth=4.0, color='0.7', zorder=1, marker='.')
        ax.legend()
        ax.set_ylabel('m')

