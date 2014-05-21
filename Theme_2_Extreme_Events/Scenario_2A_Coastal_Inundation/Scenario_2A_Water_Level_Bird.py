# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <markdowncell>

# ># IOOS System Test: [Extreme Events Theme:](https://github.com/ioos/system-test/wiki/Development-of-Test-Themes#theme-2-extreme-events) Inundation

# <markdowncell>

# ### Can we estimate the return period of a water level by comparing modeled and/or observed water levels with NOAA exceedance probability plots?

# <headingcell level=4>

# import required libraries

# <codecell>

import matplotlib.pyplot as plt
from pylab import *
import sys
import csv
import json
from scipy.stats import genextreme
import numpy as np

from owslib.csw import CatalogueServiceWeb
from owslib import fes
import random
import netCDF4
import pandas as pd
import datetime as dt
from pyoos.collectors.coops.coops_sos import CoopsSos
import cStringIO
#import iris
import urllib2
import parser
from lxml import etree       #TODO suggest using bs4 instead for ease of access to XML objects

#generated for csw interface
import requests              #required for the processing of requests
from utilities import * 

# <markdowncell>

# some functions from [Rich Signell Notebook](http://nbviewer.ipython.org/github/rsignell-usgs/notebook/blob/fef9438303b49a923024892db1ef3115e34d8271/CSW/IOOS_inundation.ipynb)

# <headingcell level=4>

# Speficy Temporal and Spatial conditions

# <codecell>

from IPython.display import HTML
import folium #required for leaflet mapping

#bounding box of interest,[bottom right[lat,lon], top left[lat,lon]]
bounding_box_type = "box" 
bounding_box = [[-73.94,40.67],[-69.94,42]]

#temporal range
start_date = dt.datetime(1991,5,1).strftime('%Y-%m-%d %H:00')
end_date = dt.datetime(2014,5,7).strftime('%Y-%m-%d %H:00')
time_date_range = [start_date,end_date]  #start_date_end_date

print start_date,'to',end_date

# <codecell>

endpoint = 'http://www.ngdc.noaa.gov/geoportal/csw' # NGDC Geoportal
csw = CatalogueServiceWeb(endpoint,timeout=60)

for oper in csw.operations:
    if oper.name == 'GetRecords':
        #print '\nISO Queryables:\n',oper.constraints['SupportedISOQueryables']['values']
        pass
        
#put the names in a dict for ease of access 
data_dict = {}
data_dict["water"] = {"names":['water_surface_height_above_reference_datum',
    'sea_surface_height_above_geoid','sea_surface_elevation',
    'sea_surface_height_above_reference_ellipsoid','sea_surface_height_above_sea_level',
    'sea_surface_height','water level'], "sos_name":['water_surface_height_above_reference_datum']}      

# <codecell>

def dateRange(start_date='1900-01-01',stop_date='2100-01-01',constraint='overlaps'):
    if constraint == 'overlaps':
        start = fes.PropertyIsLessThanOrEqualTo(propertyname='apiso:TempExtent_begin', literal=stop_date)
        stop = fes.PropertyIsGreaterThanOrEqualTo(propertyname='apiso:TempExtent_end', literal=start_date)
    elif constraint == 'within':
        start = fes.PropertyIsGreaterThanOrEqualTo(propertyname='apiso:TempExtent_begin', literal=start_date)
        stop = fes.PropertyIsLessThanOrEqualTo(propertyname='apiso:TempExtent_end', literal=stop_date)
    return start,stop

# <codecell>

# convert User Input into FES filters
start,stop = dateRange(start_date,end_date)
box = []
box.append(bounding_box[0][0])
box.append(bounding_box[0][1])
box.append(bounding_box[1][0])
box.append(bounding_box[1][1])
bbox = fes.BBox(box)

or_filt = fes.Or([fes.PropertyIsLike(propertyname='apiso:AnyText',literal=('*%s*' % val),
                    escapeChar='\\',wildCard='*',singleChar='?') for val in name_list])
val = 'Averages'
not_filt = fes.Not([fes.PropertyIsLike(propertyname='apiso:AnyText',literal=('*%s*' % val),
                        escapeChar='\\',wildCard='*',singleChar='?')])

# <codecell>

filter_list = [fes.And([ bbox, start, stop, or_filt, not_filt]) ]
# connect to CSW, explore it's properties
# try request using multiple filters "and" syntax: [[filter1,filter2]]
csw.getrecords2(constraints=filter_list,maxrecords=1000,esn='full')

# <codecell>

def service_urls(records,service_string='urn:x-esri:specification:ServiceType:odp:url'):
    """
    extract service_urls of a specific type (DAP, SOS) from records
    """
    urls=[]
    for key,rec in records.iteritems():
        #create a generator object, and iterate through it until the match is found
        #if not found, gets the default value (here "none")
        url = next((d['url'] for d in rec.references if d['scheme'] == service_string), None)
        if url is not None:
            urls.append(url)
    return urls

# <codecell>

#print records that are available
print "number of datasets available: ",len(csw.records.keys())

# <markdowncell>

# Print all the records (should you want too)

# <codecell>

#print "\n".join(csw.records)

# <markdowncell>

# Dap URLS

# <codecell>

dap_urls = service_urls(csw.records,service_string='urn:x-esri:specification:ServiceType:odp:url')
#remove duplicates and organize
dap_urls = sorted(set(dap_urls))
print "Total DAP:",len(dap_urls)
#print the first 5...
print "\n".join(dap_urls[0:5])

# <markdowncell>

# SOS URLs

# <codecell>

sos_urls = service_urls(csw.records,service_string='urn:x-esri:specification:ServiceType:sos:url')
#remove duplicates and organize
sos_urls = sorted(set(sos_urls))
print "Total SOS:",len(sos_urls)
print "\n".join(sos_urls)

# <markdowncell>

# ### SOS Requirements

# <codecell>

#use the get caps to get station start and get time

# <codecell>

start_time = dt.datetime.strptime(start_date,'%Y-%m-%d %H:%M')
end_time = dt.datetime.strptime(end_date,'%Y-%m-%d %H:%M')

# <codecell>

iso_start = start_time.strftime('%Y-%m-%dT%H:%M:%SZ')
iso_end = end_time.strftime('%Y-%m-%dT%H:%M:%SZ')

collector = CoopsSos()
collector.set_datum('NAVD')
collector.server.identification.title
collector.start_time = start_time
collector.end_time = end_time
collector.variables = [data_dict["water"]["sos_name"]]

# <codecell>

print "Date: ",iso_start," to ", iso_end
box_str=','.join(str(e) for e in box)
print "Lat/Lon Box: ",box_str
#grab the sos url and use it for the service
url=(sos_urls[0].split("?")[0]+'?'
     'service=SOS&request=GetObservation&version=1.0.0&'
     'observedProperty=%s&offering=urn:ioos:network:NOAA.NOS.CO-OPS:WaterLevelActive&'
     'featureOfInterest=BBOX:%s&responseFormat=text/tab-separated-values&eventTime=%s') % (sos_name,box_str,iso_end)

r = requests.get(url)
data = r.text
#get the headers for the cols
data = data.split("\n")
headers =  data[0]
station_list_dict = dict()
#parse the headers so i can create a dict
c = 0
for h in headers.split("\t"):
    field = h.split(":")[0].split(" ")[0]
    station_list_dict[field] = {"id":c}
    c+=1

# <codecell>

def get_coops_longName(sta):
    """
    get longName for specific station from COOPS SOS using DescribeSensor request
    """
    url=(sos_urls[0].split("?")[0]+'?service=SOS&'
        'request=DescribeSensor&version=1.0.0&outputFormat=text/xml;subtype="sensorML/1.0.1"&'
        'procedure=%s') % sta
    tree = etree.parse(urllib2.urlopen(url))
    root = tree.getroot()
    longName=root.xpath("//sml:identifier[@name='longName']/sml:Term/sml:value/text()", namespaces={'sml':"http://www.opengis.net/sensorML/1.0.1"})
    return longName

# <codecell>

#finds the max value given a json object
def findMaxVal(data):
    dates_array = []
    vals_array = []
    for x in data:
        dates_array.append(str(x["t"]))
        vals_array.append(x["v"])
    
    p = np.array(vals_array,dtype=np.float)
    x = np.arange(len(p))
    max_val = np.amax(p)
    max_idx = np.argmax(p)
    return (max_val,len(p),dates_array[max_idx])

# <codecell>

def coops2data(collector,station_id,sos_name):
    collector.features = [station_id]
    collector.variables = [sos_name]
    station_data = dict()
    #loop through the years and get the data needed
    for year_station in range(int(collector.start_time.year),collector.end_time.year+1):      
        link = "http://tidesandcurrents.noaa.gov/api/datagetter?product="+sos_name+"&application=NOS.COOPS.TAC.WL&"
        date1 = "begin_date="+str(year_station)+"0101"
        date2 = "&end_date="+str(year_station)+"1231"
        datum = "&datum=MLLW"
        station_request = "&station="+station_id+"&time_zone=GMT&units=english&format=json"
        http_request = link+date1+date2+datum+station_request
        d_r = requests.get(http_request,timeout=10)
        if "Great Lake station" in d_r.text:
            pass
        else:
            key_list =  d_r.json().keys()
            if "data" in key_list:
                data = d_r.json()['data']
                max_value,num_samples,date_string = findMaxVal(data)
                station_data[str(year_station)] =  {"max":max_value,"num_samples":num_samples,"date_string":date_string}
                #print "\tyear:",year_station," MaxValue:",max_value
    return station_data

# <codecell>

#create dict of stations
station_list = []
for i in range(1,len(data)):
    station_info = data[i].split("\t")
    station = dict()
    for field in station_list_dict.keys():        
        col = station_list_dict[field]["id"]
        if col < len(station_info):
            station[field] = station_info[col]     
    station_list.append(station)        

# <codecell>

#Embeds the HTML source of the map directly into the IPython notebook.
def inline_map(map):   
    map._build_map()
    return HTML('<iframe srcdoc="{srcdoc}" style="width: 100%; height: 500px; border: none"></iframe>'.format(srcdoc=map.HTML.replace('"', '&quot;')))

map = folium.Map(location=[40, -99], zoom_start=4)

station_yearly_max = []
for s in station_list:
    #get the long name
    s["long_name"] =get_coops_longName(s['station_id'])
    #get the data
    station_num = str(s['station_id']).split(':')[-1]
    s["station_num"] = station_num
    #this is different than sos name, hourly height is hourly water level
    data = coops2data(collector,station_num,"hourly_height")    
    s["data"] = data
    if "latitude" in s:
        popup_string = '<b>Station:</b><br>'+str(s['station_id']) + "<br><b>Long Name:</b><br>"+str(s["long_name"])
        map.simple_marker([s["latitude"],s["longitude"]],popup=popup_string)
   
    #break after the first one    
    break
# Create the map and add the bounding box line
map.line(get_coordinates(bounding_box,bounding_box_type), line_color='#FF0000', line_weight=5)

inline_map(map)

# <codecell>

import prettyplotlib as ppl
import matplotlib.pyplot as plt
# Set the random seed for consistency
np.random.seed(12)

fig, ax = plt.subplots(1)

# Show the whole color range
for s in station_list:
    if "data" in s:
        years = s["data"].keys()
        xx = []
        yx = []
        for y in years:    
            xx.append(int(y))
            val = s["data"][y]["max"]
            yx.append(val)    
        ppl.scatter(ax, xx, yx,alpha=0.8,edgecolor='black',linewidth=0.15 ,label=str(s["station_num"]))


ppl.legend(ax, loc='right', ncol=1)

ax.set_title('`scatter` of waterlevel values')
fig.set_size_inches(14,8)

# <markdowncell>

# * plot time series of station values

# <codecell>


# <markdowncell>

# * create dict of station,year,max val

# <codecell>


# <markdowncell>

# * waves and currents and different notebook

# <markdowncell>

# * work on getting the rest of the ngdc data points on to the map/analysed

# <codecell>


# <markdowncell>

# * two objects for obs and model data for ease of access

# <codecell>


# <headingcell level=3>

# Extreme Value Analysis:

# <headingcell level=4>

# First read in data (water levels from stations.json) * temp station yearly max data source

# <codecell>

filename = 'stations.json'
with open(filename) as data_file:    
    data = json.load(data_file)
    
# Arbitrarily grab a station
station = 'station-8449130'
annual_max_levels = []
for years, values in data[station].iteritems():
    # Just grab the fields that contain data
    try:
        float(years)
    except ValueError:
        continue
    annual_max_levels.append(values['max'])
    #print years, values

# <codecell>

fig = plt.figure(figsize=(12,6))
axes = fig.add_axes([0.1, 0.1, 0.8, 0.8]) # left, bottom, width, height (range 0 to 1)
axes.plot(annual_max_levels)
axes.set_title('Nantucket Annual Maximum Sea Level')
axes.set_ylabel('water level (m)')
axes.set_xlabel('num years')

# <headingcell level=4>

# Fit data to GEV distribution

# <codecell>

def sea_levels_gev_pdf(x):
    return genextreme.pdf(x, xi, loc=mu, scale=sigma)

# <codecell>

mle = genextreme.fit(sorted(annual_max_levels), 0)
mu = mle[1]
sigma = mle[2]
xi = mle[0]
print "The mean, sigma, and shape parameters are %s, %s, and %s, resp." % (mu, sigma, xi)

# <headingcell level=4>

# Probability Density Plot

# <codecell>

x = np.linspace(2, 7, num=100)
y = [sea_levels_gev_pdf(z) for z in x]

fig = plt.figure(figsize=(12,6))
axes = fig.add_axes([0.1, 0.1, 0.8, 0.8])
axes.set_title("Probability Density & Normalized Histogram")
axes.set_xlabel("Nantucket Annual Maximum Sea Level (m)")
axes.plot(x, y, color='Red')
axes.hist(annual_max_levels, bins=arange(2,7,0.5), normed=1, color='Yellow')

# <headingcell level=4>

# Return Value Plot

# <codecell>

fig = plt.figure(figsize=(12,6))
axes = fig.add_axes([0.1, 0.1, 0.8, 0.8])
T=np.r_[1:500]
sT = genextreme.isf(1./T, 0, mu, sigma)
axes.semilogx(T,sT), hold
N=np.r_[1:len(annual_max_levels)+1]; 
Nmax=max(N);
axes.plot(Nmax/N, sorted(annual_max_levels)[::-1],'.')
axes.set_title('Return values in the GEV distribution')
axes.set_xlabel('Return period')
axes.set_ylabel('Return value') 
axes.grid(True)

# <headingcell level=4>

# Compute Confidence Intervals

# <codecell>


# <codecell>


