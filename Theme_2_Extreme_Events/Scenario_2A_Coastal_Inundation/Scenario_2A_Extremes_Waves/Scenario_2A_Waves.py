# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <markdowncell>

# ># IOOS System Test: [Extreme Events Theme:](https://github.com/ioos/system-test/wiki/Development-of-Test-Themes#theme-2-extreme-events) Inundation

# <markdowncell>

# ### Can we estimate the return period of a wave height by obtaining long term wave height records from observed and modelled datasets?

# <headingcell level=4>

# import required libraries

# <codecell>

import matplotlib.pyplot as plt
from pylab import *
import sys
import csv
import json
from scipy.stats import genextreme
import scipy.stats as ss
import numpy as np

from owslib.csw import CatalogueServiceWeb
from owslib import fes
import random
import netCDF4
import pandas as pd
import datetime as dt
from pyoos.collectors.ndbc.ndbc_sos import NdbcSos
import cStringIO
import iris
import urllib2
import parser
from lxml import etree       #TODO suggest using bs4 instead for ease of access to XML objects

#generated for csw interface
#from fes_date_filter_formatter import fes_date_filter  #date formatter (R.Signell)
import requests              #required for the processing of requests
from utilities import * 

from IPython.display import HTML
import folium #required for leaflet mapping
import calendar #used to get number of days in a month and year

# <markdowncell>

# some functions from [Rich Signell Notebook](http://nbviewer.ipython.org/github/rsignell-usgs/notebook/blob/fef9438303b49a923024892db1ef3115e34d8271/CSW/IOOS_inundation.ipynb)

# <headingcell level=4>

# Speficy Temporal and Spatial conditions

# <codecell>

#bounding box of interest,[bottom right[lat,lon], top left[lat,lon]]
bounding_box_type = "box" 
bounding_box = [[-73.94,40.67],[-69.94,42]]

#temporal range
start_date = dt.datetime(1991,5,1).strftime('%Y-%m-%d %H:00')
end_date = dt.datetime(2014,5,10).strftime('%Y-%m-%d %H:00')
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
data_dict["waves"] = {"names":['sea_surface_wave_significant_height','significant_wave_height'], 
                      "sos_name":["waves"]}      

# <codecell>

def fes_date_filter(start_date='1900-01-01',stop_date='2100-01-01',constraint='overlaps'):
    if constraint == 'overlaps':
        start = fes.PropertyIsLessThanOrEqualTo(propertyname='apiso:TempExtent_begin', literal=stop_date)
        stop = fes.PropertyIsGreaterThanOrEqualTo(propertyname='apiso:TempExtent_end', literal=start_date)
    elif constraint == 'within':
        start = fes.PropertyIsGreaterThanOrEqualTo(propertyname='apiso:TempExtent_begin', literal=start_date)
        stop = fes.PropertyIsLessThanOrEqualTo(propertyname='apiso:TempExtent_end', literal=stop_date)
    return start,stop

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

print "\n".join(csw.records)

# <markdowncell>

# Dap URLS

# <codecell>

dap_urls = service_urls(csw.records,service_string='urn:x-esri:specification:ServiceType:odp:url')
#remove duplicates and organize
dap_urls = sorted(set(dap_urls))
print "Total DAP:",len(dap_urls)
#print the first 5...
print "\n".join(dap_urls[:])

# <markdowncell>

# SOS URLs

# <markdowncell>

# #### TODO: Fix waves not being found in catalog

# <codecell>

sos_urls = service_urls(csw.records,service_string='urn:x-esri:specification:ServiceType:sos:url')
#remove duplicates and organize
if len(sos_urls) ==0:
    sos_urls.append("http://sdf.ndbc.noaa.gov/sos/server.php")  #?request=GetCapabilities&service=SOS

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

collector = NdbcSos()
collector.start_time = start_time
collector.end_time = end_time
collector.variables = data_dict["waves"]["sos_name"]
collector.server.identification.title
print collector.start_time,":", collector.end_time

# <codecell>

print "Date: ",iso_start," to ", iso_end
box_str=','.join(str(e) for e in box)
print "Lat/Lon Box: ",box_str
#grab the sos url and use it for the service
url=(sos_urls[0]+'?'
     'service=SOS&request=GetObservation&version=1.0.0&'
     'observedProperty=%s&offering=urn:ioos:network:noaa.nws.ndbc:all&'
     'featureOfInterest=BBOX:%s&responseFormat=text/tab-separated-values&eventTime=%s') % ("waves",box_str,iso_end)
print url
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
print "Num of fields:", c

# <codecell>

#create dict of stations
station_list = []
for i in range(1,len(data)):
    station_info = data[i].split("\t")
    if len(station_info)>1:
        station = dict()
        for field in station_list_dict.keys():        
            col = station_list_dict[field]["id"]
            if col < len(station_info):
                station[field] = station_info[col]     
        station["type"] = "obs"        
        station_list.append(station)

# <markdowncell>

# #### Add wis site infotmation to station list

# <codecell>

print len(station_list)    
print float(station_list[0]["longitude"])
print station_list[0]["latitude"]

# <codecell>

from shapely.geometry import Polygon,Point,LineString
import sqlite3 as lite

# <codecell>

#get the WIS stations that are in the bounding box
#generate polygon that matches that of the bounding box
poly = Polygon(get_coordinates(bounding_box,bounding_box_type))
db = r'/Users/rpsdev/Documents/d3/wis_data/wis_stations.db'
print poly
try:
    conn = lite.connect(db)
    cur = conn.cursor()
    cur.execute("SELECT NAME,LAT,LON FROM station_list")
    records = cur.fetchall()
    st_yr =int(collector.start_time.year)
    ed_yr =int(collector.end_time.year+1)
    min_station_line = -1
    min_station_line_set = True
    min_station_name = ""
    station_lat = float(station_list[0]["latitude"])
    station_lon = float(station_list[0]["longitude"])
    for r in records:
        #name,lat,lon
        station_is_contained = poly.contains(Point(float(r[1]),float(r[2])))
        #if the station is in the bounds, store it as such
        if station_is_contained:
            st_name = r[0]
            #find the closest station
            
            line = LineString([(float(r[1]),float(r[2])),(station_lat,station_lon)])
            if min_station_line_set:
                min_station_line = line.length
                min_station_record = r
            if line.length < min_station_line:
                min_station_record = r
                
    station = dict()
    station["latitude"] = float(min_station_record[1])
    station["longitude"] = float(min_station_record[2])
    st_name = min_station_record[0]
    station["long_name"] = "WIS:"+ st_name
    station["id"] = st_name
    station["station_id"] = st_name
    station["type"] = "model"
    station_data = dict()
    for yr in range(st_yr,ed_yr+1):
        #get the max value from the monthly max to give yearly max
        cur.execute("select MAX(hmax) from station_data where name="+ str(st_name) +" and date >="+str(yr)+"01 and date <="+str(yr)+"12")
        yearmax = cur.fetchall()
        yearmax = yearmax[0][0]
        if yearmax is None:
            print "year ", yr," is none"
        else:
            station_data[str(yr)] = {"max":yearmax,"num_samples":0,"date_string":""}
    station["data"] = station_data
    station_list.append(station)
except lite.Error:
    print "Error open db.\n"


# <codecell>

#print out the station name
print station_list[0]["sensor_id"]
print station_list[1]
print len(station_list) 

# <codecell>

def get_station_long_name(sta):
    """
    get longName for specific station
    """
    url=(sos_urls[0]+'?service=SOS&'
        'request=DescribeSensor&version=1.0.0&outputFormat=text/xml;subtype="sensorML/1.0.1"&'
        'procedure=%s') % sta    
    tree = etree.parse(urllib2.urlopen(url))
    root = tree.getroot()
    longName=root.xpath("//sml:identifier[@name='longName']/sml:Term/sml:value/text()", namespaces={'sml':"http://www.opengis.net/sensorML/1.0.1"})
    return longName

# <codecell>

def get_sos_data(collector,station_id,sos_name,date_time,field_of_interest):
    print "Station:",station_id
    collector.features = [station_id]
    collector.variables = [sos_name] 
    station_data = dict()
    #loop through the years and get the data needed
    st_yr =int(collector.start_time.year)
    ed_yr =int(collector.end_time.year+1)
    #only 31 days are allowed to be requested at once
    for year_station in range(st_yr,ed_yr):    
        year_station_data = []
        date_list = []
        for month in range (1,13):
                num_days = calendar.monthrange(year_station, month)[1]     

                st = dt.datetime(year_station,month,1,0,0,0)
                ed = dt.datetime(year_station,month,num_days,23,59,59)

                start_time1 = dt.datetime.strptime(str(st),'%Y-%m-%d %H:%M:%S')
                end_time1 = dt.datetime.strptime(str(ed),'%Y-%m-%d %H:%M:%S')
                
                collector.start_time = start_time1
                collector.end_time = end_time1
                 
                try:
                    response = collector.raw(responseFormat="text/csv")
                    #get the response then get the data
                    data =  response.split("\n")
                    first_row = True
                    if len(data)>2:
                        for d in data:
                            d_row = (d.split(","))
                            
                            if first_row:
                                #find the field of interest
                                idx1 = [d_row.index(i) for i in d_row if field_of_interest in i][0]
                                idx2 = [d_row.index(i) for i in d_row if date_time in i][0]
                                first_row = False
                            else:  
                                if idx1<len(d_row):
                                    year_station_data.append(d_row[idx1])
                                else:
                                    #print idx1,":",d_row
                                    pass
                                    
                                if idx2<len(d_row):
                                    date_list.append(d_row[idx2])
                                else:
                                    #print idx2,":",d_row
                                    pass
    
                    else:
                        #print "no data...:",year_station,":",month
                        pass
                except Exception, e: #should only fail if the data is not there
                    print e,":",year_station,":",month

        #caluclate the max values   
        p = np.array(year_station_data,dtype=np.float)     
        if len(p)>2:
            station_data[str(year_station)] = {"max":np.amax(p),"num_samples":len(p),"date_string":date_list[np.argmax(p)]}
            
                    
    #reset the collector once complete            
    collector.start_time = start_time
    collector.end_time = end_time    
    return station_data

# <codecell>

from pydap.client import open_url

# <codecell>

def get_model_data(dap_urls,st_lat,st_lon):
    # use only data within 0.04 degrees (about 4 km)
    max_dist=0.04 
    
    # use only data where the standard deviation of the time series exceeds 0.01 m (1 cm)
    # this eliminates flat line model time series that come from land points that 
    # should have had missing values.
    min_var=0.01
    for url in dap_urls:
        try:
           pass            
        except:
            pass
        

# <codecell>

#get model data for a station
get_model_data(dap_urls,41.138,-72.665)

# <codecell>

#Embeds the HTML source of the map directly into the IPython notebook.

def inline_map(map):   
    map._build_map()
    return HTML('<iframe srcdoc="{srcdoc}" style="width: 100%; height: 500px; border: none"></iframe>'.format(srcdoc=map.HTML.replace('"', '&quot;')))

map = folium.Map(location=[bounding_box[0][1], bounding_box[0][0]], zoom_start=6)

station_yearly_max = []
for s in station_list:
    #get the station data from the sos end point
    if s["type"] is "obs":
        #get the long name        
        station_num = str(s['station_id']).split(':')[-1]
        s["station_num"] = station_num
        s["long_name"] = get_station_long_name(s['station_id'])
        raw_data = get_sos_data(collector,station_num,"waves","date_time","sea_surface_wave_significant_height (m)")    
        s["data"] = raw_data
    if "latitude" in s:
        popup_string = '<b>Station:</b><br>'+str(s['station_id']) + "<br><b>Long Name:</b><br>"+str(s["long_name"])+"<br><br>"+str(s["type"])
        map.simple_marker([s["latitude"],s["longitude"]],popup=popup_string)
# Create the map and add the bounding box line
map.line(get_coordinates(bounding_box,bounding_box_type), line_color='#FF0000', line_weight=5)

inline_map(map)

# <codecell>

import prettyplotlib as ppl
fig, ax = plt.subplots(1)

# Show the whole color range
for s in station_list:
    if "data" in s:
        years = s["data"].keys()
        xx = []
        yx = []
        for y in years:                
            val = s["data"][y]["max"]            
            if val is not None:
                try:
                    #round to 2dp                    
                    val = "%.2f" % val
                    yx.append(val)
                    xx.append(int(y))
                except:
                    pass
                    
        #ppl.scatter(ax, xx, yx,alpha=0.8,edgecolor='black',linewidth=0.15 ,label=str(s["station_num"])+":"+str(s["long_name"][0]))
        ppl.scatter(ax, xx, yx,alpha=0.8,edgecolor='black',linewidth=0.15 ,label=str(s["long_name"]))  
     
        
ax.legend(loc=1)
ax.set_title('Annual Max sea surface wave significant height (m) (Observed & Model)')
ax.set_xlabel('Year')
ax.set_ylabel('sea surface wave significant height (m)')

ax.set_xticks(numpy.arange(st_yr,ed_yr,2))
fig.set_size_inches(14,8)

# Shink current axis by 20%
box = ax.get_position()
ax.set_position([box.x0, box.y0, box.width * 0.8, box.height])
# Put a legend to the right of the current axis
ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))

# <headingcell level=3>

# Extreme Value Analysis:

# <codecell>

annual_max = yx
data_levels = []
for i in annual_max:
    data_levels.append(float(i))
annual_max = data_levels    

# <headingcell level=4>

# Fit data to GEV distribution

# <codecell>

def gev_pdf(x):
    return genextreme.pdf(x, xi, loc=mu, scale=sigma)

# <codecell>

mle = genextreme.fit(sorted(annual_max), 0)
mu = mle[1]
sigma = mle[2]
xi = mle[0]
print "The mean, sigma, and shape parameters are %s, %s, and %s, resp." % (mu, sigma, xi)

# <headingcell level=4>

# Probability Density Plot

# <codecell>

min_x = min(annual_max_levels)-0.5
max_x = max(annual_max_levels)+0.5
x = np.linspace(min_x, max_x, num=100)
y = [gev_pdf(z) for z in x]

fig = plt.figure(figsize=(12,6))
axes = fig.add_axes([0.1, 0.1, 0.8, 0.8])
xlabel = (s["long_name"] + " - Annual max Wave Height (m)")
axes.set_title("Probability Density & Normalized Histogram")
axes.set_xlabel(xlabel)
axes.plot(x, y, color='Red')
axes.hist(annual_max_levels, bins=arange(min_x, max_x, abs((max_x-min_x)/10)), normed=1, color='Yellow')

# <headingcell level=4>

# Return Value Plot

# <codecell>

fig = plt.figure(figsize=(20,6))
axes = fig.add_axes([0.1, 0.1, 0.8, 0.8])
T=np.r_[1:500]
sT = genextreme.isf(1./T, 0, mu, sigma)
axes.semilogx(T, sT, 'r'), hold
N=np.r_[1:len(annual_max_levels)+1]; 
Nmax=max(N);
axes.plot(Nmax/N, sorted(annual_max_levels)[::-1], 'bo')
title = s["long_name"][0] 
axes.set_title(title)
axes.set_xlabel('Return Period (yrs)')
axes.set_ylabel('Return Value') 
axes.grid(True)

# <headingcell level=4>

# Compute Confidence Intervals

# <codecell>

def conf_int_scipy(x, ci=0.95):
  low_per = 100*(1-ci)/2.
  high_per = 100*ci + low_per
  mn = x.mean()
  cis = ss.scoreatpercentile(x, low_per, high_per)
  return mn, cis

# <codecell>


