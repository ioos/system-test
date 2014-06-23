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

from utilities import (date_range, coops2df, find_timevar, find_ij, nearxy, service_urls, mod_df, 
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
        'North West': [-129, 41, -123, 50]}

bounding_box = area['East Coast']

#temporal range
jd_now = dt.datetime.utcnow()
jd_start,  jd_stop = jd_now - dt.timedelta(days=20), jd_now + dt.timedelta(days=3)

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
data_dict['currents'] = {"names":['currents','surface_eastward_sea_water_velocity','*surface_eastward_sea_water_velocity*','surface_northward_sea_water_velocity'], 
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
dap_urls.append("http://sdf.ndbc.noaa.gov:8080/thredds/dodsC/hfradar_prvi_2km")
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

#collector = NdbcSos()
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

url = []
url.append(('http://sdf.ndbc.noaa.gov/sos/server.php?'
     'service=SOS&request=GetObservation&version=1.0.0&'
     'offering=urn:ioos:network:noaa.nws.ndbc:all&observedProperty=%s&'
     'responseFormat=text/csv&featureOfInterest=BBOX:%s&eventTime=latest') % (sos_name, box_str))

# url.append('http://opendap.co-ops.nos.noaa.gov/ioos-dif-sos/SOS?'
#        'service=SOS&request=GetObservation&version=1.0.0&'
#        'observedProperty=%s&offering=urn:ioos:network:noaa.nws.ndbc:all:'
#        '&featureOfInterest=BBOX:%s&responseFormat='
#        'text/csv&eventTime=%s') % (sos_name, box_str, iso_start)

url.append('http://tidesandcurrents.noaa.gov/api/datagetter?'
       'begin_date=20130101&end_date=20130101&station=8454000&product=currents&bin=1'
       '&datum=mllw&units=metric&time_zone=gmt&application=web_services&format=csv')

url.append(('http://opendap.co-ops.nos.noaa.gov/ioos-dif-sos/SOS?'
       'service=SOS&request=GetObservation&version=1.0.0&'
       'observedProperty=%s&bin=1&'
       'offering=urn:ioos:network:NOAA.NOS.CO-OPS:CurrentsActive&'
       'featureOfInterest=BBOX:%s&responseFormat=text/csv') % (sos_name, box_str))

url.append(('http://sdf.ndbc.noaa.gov/sos/server.php?'
     'service=SOS&request=GetObservation&version=1.0.0&'
     'offering=urn:ioos:network:noaa.nws.ndbc:all&observedProperty=%s&'
     'responseFormat=text/csv&featureOfInterest=BBOX:%s&eventTime=latest') % (sos_name, box_str))

# http://sdf.ndbc.noaa.gov/sos/server.php?request=GetObservation&service=SOS&version=1.0.0&
#     offering=urn:ioos:network:noaa.nws.ndbc:all&featureofinterest=BBOX:-89.5,28,-89,28.5&
#     observedproperty=Currents&responseformat=text/csv&eventtime=2008-07-17T00:00Z/2008-07-17T23:59Z
#url=(sos_urls[0]+'?'
#     'service=SOS&request=GetObservation&version=1.0.0&'
#     'offering=urn:ioos:station:wmo:%s&observedProperty=%s&'
#     'responseFormat=text/csv&eventTime=%s|%s&featureOfInterest=BBOX:%s') % (wmo_id,"waves",iso_start,iso_stop,box_str)

print url[1]
obs_loc_df = pd.read_csv(url[1])

# <codecell>

obs_loc_df.head()
#print obs_loc_df

# <codecell>

stations = [sta.split(':')[-1] for sta in obs_loc_df['station_id']]
print list(set(stations))
obs_lon = [sta for sta in obs_loc_df['longitude (degree)']]
obs_lat = [sta for sta in obs_loc_df['latitude (degree)']]
print list(set(obs_lon))
print list(set(obs_lat))

# <headingcell level=3>

# Request CSV response from SOS and convert to Pandas DataFrames

# <codecell>

ts_rng = pd.date_range(start=start_date, end=stop_date)
ts = pd.DataFrame(index=ts_rng)

obs_df = []

#for sta in stations:
#    b=coops2df(collector, sta, sos_name)
#    # limit interpolation to 10 points (10 @ 6min = 1 hour)
#    obs_df.append(pd.DataFrame(pd.concat([b, ts],axis=1)['Observed Data']))
#    obs_df[-1].name=b.name
obs_df = []
sta_names = []
sta_failed = []
# for sta in stations:
#     try:
collector.features = ['46088']
collector.variables = [sos_name]
response = collector.raw(responseFormat="text/csv")
data_df = pd.read_csv(cStringIO.StringIO(str(response)), parse_dates=True, index_col='date_time')
#    data_df['Observed Data']=data_df['water_surface_height_above_reference_datum (m)']-data_df['vertical_position (m)']
data_df['sea_water_speed (cm/s)'] = data_df['sea_water_speed (cm/s)']

# a = get_NDBC_station_long_name('46088')
if len(a) == 0:
    long_name = '46088'
else:
    long_name = a[0]
data_df.name = long_name
#         b = coops2df(collector, sta, sos_name)
#     except Exception as ex:
#         print "Error - " + str(ex)
#         continue
b = data_df
name = b.name
sta_names.append(name)
print(name)
if b.empty:
    sta_failed.append(name)
    b = DataFrame(np.arange(len(ts)) * np.NaN, index=ts.index, columns=['sea_water_speed (cm/s)'])
    b.name = name
# Limit interpolation to 10 points (10 @ 6min = 1 hour).
col = 'sea_water_speed (cm/s)'
concatenated = pd.concat([b, ts], axis=1).interpolate(limit=10)[col]
obs_df.append(pd.DataFrame(concatenated))
obs_df[-1].name = b.name    

# <codecell>

# Define minimum amount of data points to plot
min_data_pts = 20

#find center of bounding box
lat_center = abs(bounding_box[3] - bounding_box[1])/2 + bounding_box[1]
lon_center = abs(bounding_box[0]-bounding_box[2])/2 + bounding_box[0]
m = folium.Map(location=[lat_center, lon_center], zoom_start=6)

for n in range(len(obs_df)):
    #get the station data from the sos end point
    shortname = obs_df['station_id'][n].split(':')[-1]
    longname = obs_df[n].name
    lat = obs_df['latitude (degree)'][n]
    lon = obs_df['longitude (degree)'][n]
    popup_string = ('<b>Station:</b><br>'+ longname)
    if len(obs_df[n]) > min_data_pts:
        m.simple_marker([lat, lon], popup=popup_string)
    else:
        #popup_string += '<br>No Data Available'
        popup_string += '<br>Not enough data available<br>requested pts: ' + str(min_data_pts ) + '<br>Available pts: ' + str(len(obs_df[n]))
        m.circle_marker([lat, lon], popup=popup_string, fill_color='#ff0000', radius=10000, line_color='#ff0000')
print type(bounding_box)
m.line(get_coordinates(bounding_box, bounding_box_type), line_color='#FF0000', line_weight=5)

inline_map(m)

# <codecell>

# Plot Hs and Tp for each station
#for n in range(len(Hs_obs_df)):
#    if len(Hs_obs_df[n]) > min_data_pts:
#        fig, axes = plt.subplots(nrows=1, ncols=2, figsize=(20,5))
#        Hs_obs_df[n].plot(ax=axes[0], color='r')
#        axes[0].set_title(Hs_obs_df[n].name)
#        axes[0].set_ylabel('Hs (m)')
#        Tp_obs_df[n].plot(ax=axes[1])
#        axes[1].set_title(Tp_obs_df[n].name)
#        axes[1].set_ylabel('Tp (s)')



# <markdowncell>

# ###Get model output from OPeNDAP URLS
# Try to open all the OPeNDAP URLS using Iris from the British Met Office. If we can open in Iris, we know it's a model result.

# <codecell>

print data_dict['currents']['names']
name_in_list = lambda cube: cube.standard_name in data_dict['currents']['names'][0:2]
constraint = iris.Constraint(cube_func=name_in_list)
 

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

