# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

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

import numpy as np
import pandas as pd
from pyoos.collectors.ndbc.ndbc_sos import NdbcSos
from pyoos.collectors.coops.coops_sos import CoopsSos
import requests

from utilities import (date_range, coops2df, coops2data, find_timevar, find_ij, nearxy, service_urls, mod_df, 
                       get_coordinates, get_Coops_longName, inline_map)

import cStringIO
from lxml import etree
import urllib2

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
jd_start,  jd_stop = jd_now - dt.timedelta(days=5), jd_now

start_date = jd_start.strftime('%Y-%m-%d %H:00')
stop_date = jd_stop.strftime('%Y-%m-%d %H:00')

jd_start = dt.datetime.strptime(start_date, '%Y-%m-%d %H:%M')
jd_stop = dt.datetime.strptime(stop_date, '%Y-%m-%d %H:%M')
print start_date,'to',stop_date

# <codecell>

#put the names in a dict for ease of access 
data_dict = {}
sos_name = 'Currents'
data_dict['currents'] = {"names":['currents',
                                  'surface_eastward_sea_water_velocity',
                                  '*surface_eastward_sea_water_velocity*'], 
                         "sos_name":['currents']}  

# <markdowncell>

# CSW Search

# <codecell>

endpoint = 'http://www.ngdc.noaa.gov/geoportal/csw' # NGDC Geoportal
csw = CatalogueServiceWeb(endpoint,timeout=60)

for oper in csw.operations:
    if oper.name == 'GetRecords':
        cnstr = oper.constraints['SupportedISOQueryables']['values']
        #print('\nISO Queryables:%s\n' % '\n'.join(cnstr))

# <markdowncell>

# Search

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

# DAP

# <codecell>

dap_urls = service_urls(csw.records)
#remove duplicates and organize
dap_urls = sorted(set(dap_urls))
print "Total DAP:",len(dap_urls)
#print the first 5...
print "\n".join(dap_urls[:])

# <markdowncell>

# SOS

# <codecell>

sos_urls = service_urls(csw.records,service='sos:url')
#remove duplicates and organize
#if len(sos_urls) ==0:
sos_urls.append("http://sdf.ndbc.noaa.gov/sos/server.php")  #?request=GetCapabilities&service=SOS

sos_urls = sorted(set(sos_urls))
print "Total SOS:",len(sos_urls)
print "\n".join(sos_urls)

# <markdowncell>

# SOS

# <codecell>

start_time = dt.datetime.strptime(start_date,'%Y-%m-%d %H:%M')
end_time = dt.datetime.strptime(stop_date,'%Y-%m-%d %H:%M')
iso_start = start_time.strftime('%Y-%m-%dT%H:%M:%SZ')
iso_end = end_time.strftime('%Y-%m-%dT%H:%M:%SZ')

# <markdowncell>

# #### CO-OPS

# <codecell>

coops_collector = CoopsSos()
coops_collector.start_time = start_time
coops_collector.end_time = end_time
coops_collector.variables = data_dict["currents"]["sos_name"]
coops_collector.server.identification.title
print coops_collector.start_time,":", coops_collector.end_time
ofrs = coops_collector.server.offerings
print(len(ofrs))

# <codecell>

print "Date: ",iso_start," to ", iso_end
box_str=','.join(str(e) for e in bounding_box)
print "Lat/Lon Box: ",box_str

url = (('http://opendap.co-ops.nos.noaa.gov/ioos-dif-sos/SOS?'
       'service=SOS&request=GetObservation&version=1.0.0&'
       'observedProperty=%s&bin=1&'
       'offering=urn:ioos:network:NOAA.NOS.CO-OPS:Currents&'
       'featureOfInterest=BBOX:%s&responseFormat=text/csv') % (sos_name, box_str))

print url
#obs_loc_df = pd.read_csv(url)

# <markdowncell>

# #### NDBC

# <codecell>

ndbc_collector = NdbcSos()
ndbc_collector.start_time = start_time
ndbc_collector.end_time = end_time
ndbc_collector.variables = data_dict["currents"]["sos_name"]
ndbc_collector.server.identification.title
print ndbc_collector.start_time,":", ndbc_collector.end_time
ofrs = ndbc_collector.server.offerings
print(len(ofrs))

# <codecell>

print "Date: ",iso_start," to ", iso_end
box_str=','.join(str(e) for e in bounding_box)
print "Lat/Lon Box: ",box_str

#how the query should look
'''
url = (('http://sdf.ndbc.noaa.gov/sos/server.php?'
       'request=GetObservation&service=SOS&'
       'version=1.0.0&'
       'offering=urn:ioos:network:noaa.nws.ndbc:all&'
       'featureofinterest=BBOX:%s&'
       'observedproperty=%s&'
       'responseformat=text/csv&'
       'eventtime=%s')% (box_str,sos_name,iso_start,iso_end))
'''

url = (('http://sdf.ndbc.noaa.gov/sos/server.php?'
       'request=GetObservation&service=SOS&'
       'version=1.0.0&'
       'offering=urn:ioos:network:noaa.nws.ndbc:all&'
       'featureofinterest=BBOX:%s&'
       'observedproperty=%s&'
       'responseformat=text/csv&')% (box_str,sos_name))


print url
obs_loc_df = pd.read_csv(url)

# <markdowncell>

# #### NDBC Station information

# <codecell>

st_data = obs_loc_df['station_id']
lat_data = obs_loc_df['latitude (degree)']
lon_data = obs_loc_df['longitude (degree)']

st_list = {}
for i in range(0,len(st_data)):
    station_name = st_data[i]
    if station_name in st_list:
        pass
    else:
        st_list[station_name] = {}
        st_list[station_name]["lat"] = lat_data[i]
        st_list[station_name]["lon"] = lon_data[i]
        print station_name

print "number of stations in bbox",len(st_list.keys())

# <markdowncell>

# #### NDBC Map

# <codecell>

def ndbc2data2(collector,station_id,sos_name,iso_start, iso_end):
    """Extract the Observation Data from the collector."""
    collector.features = [station_id]
    collector.variables = [sos_name]
    
    url = (('http://sdf.ndbc.noaa.gov/sos/server.php?'
       'request=GetObservation&service=SOS&'
       'version=1.0.0&'
       'offering=%s&'
       'featureofinterest=BBOX:%s&'
       'observedproperty=%s&'
       'responseformat=text/csv&'
       'eventtime=%s/%s')% (station_id,box_str,sos_name,iso_start,iso_end))
   
    
    print url
    data_df = pd.read_csv(url, parse_dates=True, index_col='date_time')
    data_df.name = station_id
    return data_df

# <markdowncell>

# #### Get Obs Data

# <codecell>

#add to existing data struct
for st in st_list:
    try:
        print "working on ",st
        df = ndbc2data2(ndbc_collector, st, sos_name,iso_start, iso_end)
        if df.empty:
            st_list[name]["hasdata"] = False
            print st,"empty..."
            pass
        else:
            name = df.name
            st_list[name]["hasdata"] = True
            st_list[name]["data"] = df
            st_list[name]["type"] = "obs"
            st_list[name]["bins"] = max(df['bin (count)'].values)  
        break    
    except Exception as e:
        print "Error" + str(e)
        continue
      

# <codecell>

def get_dap_data(dap_urls,constraint,obs_lat,obs_lon,ts):
    # Use only data within 0.04 degrees (about 4 km).
    obs_df = []
    obs_or_model = False
    max_dist = 1.4
    # Use only data where the standard deviation of the time series exceeds 0.01 m (1 cm).
    # This eliminates flat line model time series that come from land points that should have had missing values.
    min_var = 0.01
    data_idx = []
    for url in dap_urls:
        print url
        try:
            a = iris.load_cube(url, constraint)
            # convert to units of meters
            # a.convert_units('m')     # this isn't working for unstructured data
            # take first 20 chars for model name
            mod_name = a.attributes['title'][0:20]
            print mod_name
            
            if 'from HF-Radar' in a.attributes['summary']:
                 obs_or_model = True
            
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
                    try:
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
                                try:
                                    len(j)
                                except:
                                    j = [j]

                                try:
                                    len(i)
                                except:
                                    i = [i]

                                arr = a[istart:istop, j[n], i[n]].data
                                print arr
                                if arr.std() >= min_var:                                
                                    c = mod_df(arr, timevar, istart, istop,mod_name, ts)
                                    name = obs_df[n].name
                                    obs_df[n] = pd.concat([obs_df[n], c], axis=1)
                                    obs_df[n].name = name
                                    data_idx.append(obs_df)
                    except:
                        pass
                                
                elif len(r) == 2:
                    try:
                        print('[Unstructured grid model]:', url)
                        # Find the closest point from an unstructured grid model.
                        index, dd = nearxy(lon.flatten(), lat.flatten(),obs_lon, obs_lat)
                        for n in range(nsta):
                            # Only use if model cell is within 0.1 degree of requested
                            # location.
                            if dd[n] <= max_dist:
                                arr = a[istart:istop, index[n]].data
                                if arr.std() >= min_var:
                                    c = mod_df(arr, timevar, istart, istop,mod_name, ts)
                                    name = obs_df[n].name
                                    obs_df[n] = pd.concat([obs_df[n], c], axis=1)
                                    obs_df[n].name = name
                                    data_idx.append(obs_df)
                    except:
                        pass
                elif len(r) == 1:
                    print('[Data]:', url)
        except (ValueError, RuntimeError, CoordinateNotFoundError,
                ConstraintMismatchError) as e:
            warn("\n%s\n" % e)
            pass
        
    return data_idx,obs_or_model

# <codecell>

print data_dict['currents']['names']
name_in_list = lambda cube: cube.standard_name in data_dict['currents']['names']
constraint = iris.Constraint(cube_func=name_in_list)

ts_rng = pd.date_range(start=jd_start, end=jd_stop, freq='6Min')
ts = pd.DataFrame(index=ts_rng)

lat_list = []
lon_list = []
for st in st_list:
    station = st_list[st]
    lat_list.append(station["lat"])
    lon_list.append(station["lon"])

# <codecell>

try:
    dap_data,obs_or_model = get_dap_data(dap_urls,constraint, lat_list, lon_list,ts)
except Exception as e:
    print "Error: " + str(e)

# <markdowncell>

# #### Map

# <codecell>

station =  st_list[st_list.keys()[0]]
map = folium.Map(location=[station["lat"], station["lon"]], zoom_start=5)
map.line(get_coordinates(bounding_box, bounding_box_type), line_color='#FF0000', line_weight=5)
for st in st_list:
    map.simple_marker([st_list[st]["lat"], st_list[st]["lon"]], popup=st)

# <codecell>

inline_map(map)

# <codecell>


