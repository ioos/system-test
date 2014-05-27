# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <markdowncell>

# ># IOOS System Test: [Extreme Events Theme:](https://github.com/ioos/system-test/wiki/Development-of-Test-Themes#theme-2-extreme-events) Inundation

# <markdowncell>

# ### Can we compare observed and modeled wave parameters? 
# This notebook is based on [IOOS System Test: Inundation](http://nbviewer.ipython.org/github/rsignell-usgs/notebook/blob/fef9438303b49a923024892db1ef3115e34d8271/CSW/IOOS_inundation.ipynb) by Rich Signell

# <headingcell level=4>

# import required libraries

# <codecell>

import sys
import csv
import random
import parser
import cStringIO

import matplotlib.pyplot as plt
from pylab import *
from pyoos.collectors.ndbc.ndbc_sos import NdbcSos
from owslib.csw import CatalogueServiceWeb
from owslib import fes
import netCDF4
import pandas as pd
import datetime as dt
import dateutil.parser as duparser
import iris
import urllib2
from lxml import etree       #TODO suggest using bs4 instead for ease of access to XML objects
import requests              #required for the processing of requests
from bs4 import *            #required for the xml parsing of getcaps and get obs
from IPython.display import HTML
import folium #required for leaflet mapping
import sqlite3 as lite

from utilities import dateRange
from utilities import get_coordinates # required for mapping the coordinates
from utilities import service_urls

# <markdowncell>

# some functions from [Rich Signell Notebook](http://nbviewer.ipython.org/github/rsignell-usgs/notebook/blob/fef9438303b49a923024892db1ef3115e34d8271/CSW/IOOS_inundation.ipynb)

# <headingcell level=4>

# Speficy Temporal and Spatial conditions

# <codecell>

#bounding box of interest,[bottom right[lat,lon], top left[lat,lon]]
bounding_box_type = "box" 
bounding_box = [[-77,34],[-70,44]]

#temporal range
start_date = dt.datetime(2014,5,1,0,50).strftime('%Y-%m-%d %H:%M')
end_date = dt.datetime(2014,5,10).strftime('%Y-%m-%d %H:00')
time_date_range = [start_date,end_date]  #start_date_end_date

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
#endpoint = 'http://data.nodc.noaa.gov/geoportal/csw'  # NODC Geoportal: collection level 
csw = CatalogueServiceWeb(endpoint,timeout=60)

for oper in csw.operations:
    if oper.name == 'GetRecords':
        print '\nISO Queryables:\n',oper.constraints['SupportedISOQueryables']['values']

# <codecell>

# convert User Input into FES filters
start,stop = dateRange(start_date,end_date)
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

def get_station_long_name(sta):
    """
    get longName for specific station
    """
    #http://sdf.ndbc.noaa.gov/sos/server.php?request=DescribeSensor&service=SOS&version=1.0.0&outputformat=text/xml;subtype=%22sensorML/1.0.1%22&procedure=urn:ioos:station:wmo:41012
    url=(sos_urls[0]+'?service=SOS&version=1.0.0&'
        'request=DescribeSensor&version=1.0.0&outputFormat=text/xml;subtype="sensorML/1.0.1"&'
        'procedure=urn:ioos:station:wmo:%s') % sta    
    tree = etree.parse(urllib2.urlopen(url))
    root = tree.getroot()
    longName=root.xpath("//sml:identifier[@name='longName']/sml:Term/sml:value/text()", namespaces={'sml':"http://www.opengis.net/sensorML/1.0.1"})
    return longName

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
#obs_lon = [sta for sta in obs_loc_df['longitude (degree)']]
#obs_lat = [sta for sta in obs_loc_df['latitude (degree)']]

# <headingcell level=3>

# Request CSV response from SOS and convert to Pandas DataFrames

# <codecell>

def coops2df(collector, coops_id, sos_name):
    collector.features = [coops_id]
    collector.variables = [sos_name]
    response = collector.raw(responseFormat="text/csv")
    data_df = pd.read_csv(cStringIO.StringIO(str(response)), parse_dates=True, index_col='date_time')
#    data_df['Observed Data']=data_df['water_surface_height_above_reference_datum (m)']-data_df['vertical_position (m)']
    data_df['Observed Wave Height Data'] = data_df['sea_surface_wave_significant_height (m)']
    data_df['Observed Peak Period Data'] = data_df['sea_surface_wave_peak_period (s)']

    a = get_station_long_name(coops_id)
    if len(a) == 0:
        long_name = coops_id
    else:
        long_name = a[0]
        
    data_df.name = long_name
    return data_df

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
#for station in stations:
    #get the station data from the sos end point
    
    shortname = obs_loc_df['station_id'][n].split(':')[-1]
    longname = Hs_obs_df[n].name
    lat = obs_loc_df['latitude (degree)'][n]
    lon = obs_loc_df['longitude (degree)'][n]
    popup_string = ('<b>Station:</b><br>'+ longname)
    if len(Hs_obs_df[n]) > min_data_pts:
        map.simple_marker([lat, lon], popup=popup_string)
    else:
        popup_string += '<br>No Data Available'
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
        Tp_obs_df[n].plot(ax=axes[1])
        axes[1].set_title(Tp_obs_df[n].name)



# <markdowncell>

# ###Get model output from OPeNDAP URLS
# Try to open all the OPeNDAP URLS using Iris from the British Met Office. If we can open in Iris, we know it's a model result.

