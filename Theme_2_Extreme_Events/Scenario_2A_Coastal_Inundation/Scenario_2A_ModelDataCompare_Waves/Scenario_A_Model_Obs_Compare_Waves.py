# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <markdowncell>

# ># IOOS System Test: [Extreme Events Theme:](https://github.com/ioos/system-test/wiki/Development-of-Test-Themes#theme-2-extreme-events) Coastal Inundation

# <markdowncell>

# ### Can we compare observed and modeled wave parameters? 
# This notebook is based on [IOOS System Test: Inundation](http://nbviewer.ipython.org/github/ioos/system-test/blob/master/Theme_2_Extreme_Events/Scenario_2A_Coastal_Inundation/Scenario_2A_Water_Level_Signell.ipynb)
# 
# Methodology:
# * Define temporal and spatial bounds of interest, as well as parameters of interest
# * Search for available service endpoints in the NGDC CSW catalog meeting search criteria
# * Extract OPeNDAP data endpoints from model datasets and SOS endpoints from observational datasets
# * Obtain observation data sets from stations within the spatial boundaries
# * Plot observation stations on a map (red marker if not enough data)
# * Using DAP (model) endpoints find all available models data sets that fall in the area of interest, for the specified time range, and extract a model grid cell closest to all the given station locations
# * Plot modelled and observed time series wave data on same axes for comparison
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
import requests

from utilities import fes_date_filter, coops2df, find_timevar, find_ij, nearxy, service_urls, mod_df, get_coordinates

# <headingcell level=4>

# Speficy Temporal and Spatial conditions

# <codecell>

bounding_box_type = "box" 
# Specify large bounding box around mid Atlantic coast
# [bottom right[lat,lon], top left[lat,lon]]
bounding_box = [[-77,34],[-70,40]]  

#temporal range - May 1 2014 - May 10 2014
start_date = dt.datetime(2014,5,1,0,50).strftime('%Y-%m-%d %H:%M')
end_date = dt.datetime(2014,5,10).strftime('%Y-%m-%d %H:00')
time_date_range = [start_date,end_date]  #start_date_end_date

jd_start = dt.datetime.strptime(start_date, '%Y-%m-%d %H:%M')
jd_stop = dt.datetime.strptime(end_date, '%Y-%m-%d %H:%M')

print start_date,'to',end_date

# <headingcell level=4>

# Specify data names of interest

# <codecell>

#put the names in a dict for ease of access 
data_dict = {}
sos_name = 'waves'
data_dict["waves"] = {"names":['sea_surface_wave_significant_height','significant_wave_height','sea_surface_wave_significant_height(m)', 'sea_surface_wave_significant_height (m)'], 
                      "sos_name":["waves"]}  

# <headingcell level=3>

# Search CSW for datasets of interest

# <codecell>

endpoint = 'http://www.ngdc.noaa.gov/geoportal/csw' # NGDC Geoportal
csw = CatalogueServiceWeb(endpoint,timeout=60)

for oper in csw.operations:
    if oper.name == 'GetRecords':
        print '\nISO Queryables:\n',oper.constraints['SupportedISOQueryables']['values']

# <codecell>

# convert User Input into FES filters
start,stop = fes_date_filter(start_date,end_date)
box = []
box.append(bounding_box[0][0])
box.append(bounding_box[0][1])
box.append(bounding_box[1][0])
box.append(bounding_box[1][1])
bbox = fes.BBox(box)

#use the search name to create search filter
or_filt = fes.Or([fes.PropertyIsLike(propertyname='apiso:AnyText',literal=('*%s*' % val),
                    escapeChar='\\',wildCard='*',singleChar='?') for val in data_dict["waves"]["names"]])
val = 'Averages'
not_filt = fes.Not([fes.PropertyIsLike(propertyname='apiso:AnyText',literal=('*%s*' % val),
                        escapeChar='\\',wildCard='*',singleChar='?')])
filter_list = [fes.And([ bbox, start, stop, or_filt, not_filt]) ]
# connect to CSW, explore it's properties
# try request using multiple filters "and" syntax: [[filter1,filter2]]
csw.getrecords2(constraints=filter_list,maxrecords=1000,esn='full')
print str(len(csw.records)) + " csw records found"

# <markdowncell>

# Dap URLS

# <codecell>

dap_urls = service_urls(csw.records)
#remove duplicates and organize
dap_urls = sorted(set(dap_urls))
print "Total DAP:",len(dap_urls)
#print the first 5...
print "\n".join(dap_urls[1:5])

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
end_time = dt.datetime.strptime(end_date,'%Y-%m-%d %H:%M')
iso_start = start_time.strftime('%Y-%m-%dT%H:%M:%SZ')
iso_end = end_time.strftime('%Y-%m-%dT%H:%M:%SZ')

# <codecell>

collector = NdbcSos()
print collector.server.identification.title
collector.start_time = start_time
collector.end_time = end_time
collector.variables = data_dict["waves"]["sos_name"]
collector.server.identification.title
print collector.start_time,":", collector.end_time
ofrs = collector.server.offerings

# <markdowncell>

# ###Find all SOS stations within the bounding box and time extent
# The time extent (iso_start) must be a match a timestamp in the data set. This buoy collects data hourly at the 50 minute mark.

# <codecell>

print "Date: ",iso_start," to ", iso_end
box_str=','.join(str(e) for e in box)
print "Lat/Lon Box: ",box_str

url=(sos_urls[0]+'?'
     'service=SOS&request=GetObservation&version=1.0.0&'
     'offering=urn:ioos:network:noaa.nws.ndbc:all&observedProperty=%s&'
     'responseFormat=text/csv&featureOfInterest=BBOX:%s') % ("waves",box_str)
#url=(sos_urls[0]+'?'
#     'service=SOS&request=GetObservation&version=1.0.0&'
#     'offering=urn:ioos:station:wmo:%s&observedProperty=%s&'
#     'responseFormat=text/csv&eventTime=%s|%s&featureOfInterest=BBOX:%s') % (wmo_id,"waves",iso_start,iso_stop,box_str)

print url
obs_loc_df = pd.read_csv(url)

# <codecell>

obs_loc_df.head()

# <codecell>

stations = [sta.split(':')[-1] for sta in obs_loc_df['station_id']]
obs_lon = [sta for sta in obs_loc_df['longitude (degree)']]
obs_lat = [sta for sta in obs_loc_df['latitude (degree)']]

# <headingcell level=3>

# Request CSV response from SOS and convert to Pandas DataFrames

# <codecell>

ts_rng = pd.date_range(start=start_date, end=end_date)
ts = pd.DataFrame(index=ts_rng)

Hs_obs_df = []
Tp_obs_df = []

for sta in stations:
    b=coops2df(collector, sta, sos_name)
    # limit interpolation to 10 points (10 @ 6min = 1 hour)
    Hs_obs_df.append(pd.DataFrame(pd.concat([b, ts],axis=1)['Observed Wave Height Data']))
    Hs_obs_df[-1].name=b.name
    Tp_obs_df.append(pd.DataFrame(pd.concat([b, ts],axis=1)['Observed Peak Period Data']))
    Tp_obs_df[-1].name=b.name
    

# <codecell>

# Define minimum amount of data points to plot
min_data_pts = 20

#Embeds the HTML source of the map directly into the IPython notebook.
def inline_map(map):   
    map._build_map()
    return HTML('<iframe srcdoc="{srcdoc}" style="width: 100%; height: 500px; border: none"></iframe>'.format(srcdoc=map.HTML.replace('"', '&quot;')))

#find center of bounding box
lat_center = abs(bounding_box[1][1] - bounding_box[0][1])/2 + bounding_box[0][1]
lon_center = abs(bounding_box[0][0]-bounding_box[1][0])/2 + bounding_box[0][0]
map = folium.Map(location=[lat_center, lon_center], zoom_start=5)

for n in range(len(obs_loc_df)):
    #get the station data from the sos end point
    shortname = obs_loc_df['station_id'][n].split(':')[-1]
    longname = Hs_obs_df[n].name
    lat = obs_loc_df['latitude (degree)'][n]
    lon = obs_loc_df['longitude (degree)'][n]
    popup_string = ('<b>Station:</b><br>'+ longname)
    if len(Hs_obs_df[n]) > min_data_pts:
        map.simple_marker([lat, lon], popup=popup_string)
    else:
        #popup_string += '<br>No Data Available'
        popup_string += '<br>Not enough data available<br>requested pts: ' + str(min_data_pts ) + '<br>Available pts: ' + str(len(Hs_obs_df[n]))
        map.circle_marker([lat, lon], popup=popup_string, fill_color='#ff0000', radius=10000, line_color='#ff0000')

map.line(get_coordinates(bounding_box,bounding_box_type), line_color='#FF0000', line_weight=5)

inline_map(map)

# <codecell>

# Plot Hs and Tp for each station
for n in range(len(Hs_obs_df)):
    if len(Hs_obs_df[n]) > min_data_pts:
        fig, axes = plt.subplots(nrows=1, ncols=2, figsize=(20,5))
        Hs_obs_df[n].plot(ax=axes[0], color='r')
        axes[0].set_title(Hs_obs_df[n].name)
        axes[0].set_ylabel('Hs (m)')
        Tp_obs_df[n].plot(ax=axes[1])
        axes[1].set_title(Tp_obs_df[n].name)
        axes[1].set_ylabel('Tp (s)')



# <markdowncell>

# ###Get model output from OPeNDAP URLS
# Try to open all the OPeNDAP URLS using Iris from the British Met Office. If we can open in Iris, we know it's a model result.

# <codecell>

print data_dict['waves']['names']
name_in_list = lambda cube: cube.standard_name in data_dict['waves']['names']
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
                    # Only use if model cell is within 0.01 degree of requested
                    # location.
                    if dd[n] <= max_dist:
                        arr = a[istart:istop, j[n], i[n]].data
                        if arr.std() >= min_var:
                            c = mod_df(arr, timevar, istart, istop,
                                       mod_name, ts)
                            name = Hs_obs_df[n].name
                            Hs_obs_df[n] = pd.concat([Hs_obs_df[n], c], axis=1)
                            Hs_obs_df[n].name = name
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
                            name = Hs_obs_df[n].name
                            Hs_obs_df[n] = pd.concat([Hs_obs_df[n], c], axis=1)
                            Hs_obs_df[n].name = name
            elif len(r) == 1:
                print('[Data]:', url)
    except (ValueError, RuntimeError, CoordinateNotFoundError,
            ConstraintMismatchError) as e:
        warn("\n%s\n" % e)
        pass

# <markdowncell>

# #### Plot Modeled vs Obs Wave Height

# <codecell>

for n in range(len(Hs_obs_df)):
    if Hs_obs_df[n]['Observed Wave Height Data'].count() > min_data_pts:
        ax = Hs_obs_df[n].plot(figsize=(14, 6), title=Hs_obs_df[n].name, legend=False)
        plt.setp(ax.lines[0], linewidth=4.0, color='0.7', zorder=1, marker='.')
        ax.legend()
        ax.set_ylabel('m')

