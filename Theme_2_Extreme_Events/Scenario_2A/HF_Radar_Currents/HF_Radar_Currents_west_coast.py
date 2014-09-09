# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <markdowncell>

# ># IOOS System Test: [HF Radar](https://github.com/ioos/system-test/wiki/Development-of-Test-Themes) Coastal Inundation

# <markdowncell>

# ### Can we obtain HF radar current data at stations located within a bounding box?
# This notebook is based on IOOS System Test: Inundation

# <markdowncell>

# Methodology:
# 
# * Define temporal and spatial bounds of interest, as well as parameters of interest
# * Search for available OPeNDAP data endpoints
# * Obtain observation data sets from stations within the spatial boundaries from DAP endpoints
# * Extract time series for locations
# * Plot time series data, current rose, annual max values per station
# * Plot observation stations on a map 

# <codecell>

import datetime as dt
from warnings import warn

import os
import os.path

import iris
from iris.exceptions import CoordinateNotFoundError, ConstraintMismatchError

import netCDF4
from netCDF4 import num2date, date2num

import uuid
import folium
from IPython.display import HTML, Javascript, display

import matplotlib.pyplot as plt
from owslib.csw import CatalogueServiceWeb
from owslib import fes


from shapely.geometry import Point
import numpy as np
import pandas as pd
from pyoos.collectors.ndbc.ndbc_sos import NdbcSos
from pyoos.collectors.coops.coops_sos import CoopsSos
import requests

from utilities import (date_range, coops2df, coops2data, find_timevar, find_ij, nearxy, service_urls, mod_df, 
                       get_coordinates, get_Coops_longName, inline_map, get_coops_sensor_name,css_styles,
                       find_nearest, buildSFOUrls,findSFOIndexs,uv2ws,uv2wd,uv2wdws,isDataValid,cycleAndGetData)

import cStringIO
from lxml import etree
import urllib2
import time as ttime
from io import BytesIO

from shapely.geometry import LineString
from shapely.geometry import Point


css_styles()

# <markdowncell>

# <div class="warning"><strong>Bounding Box</strong> - Small bounding box for San Francisco Bay (named West)</div>

# <codecell>

bounding_box_type = "box" 

# Bounding Box [lon_min, lat_min, lon_max, lat_max]
area = {'Hawaii': [-160.0, 18.0, -154., 23.0],
        'Gulf of Maine': [-72.0, 41.0, -69.0, 43.0],
        'New York harbor region': [-75., 39., -71., 41.5],
        'Puerto Rico': [-71, 14, -60, 24],
        'East Coast': [-77, 34, -70, 40],
        'North West': [-130, 38, -121, 50],
        'West': [-123, 36, -121, 40]
        }

bounding_box = area['West']

#temporal range
jd_now = dt.datetime.utcnow()
jd_start,  jd_stop = jd_now - dt.timedelta(days=(7)), jd_now

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

# <codecell>

endpoint = 'http://www.ngdc.noaa.gov/geoportal/csw' # NGDC Geoportal
csw = CatalogueServiceWeb(endpoint,timeout=60)

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

# #### List end points available

# <codecell>

dap_urls = service_urls(csw.records)
#remove duplicates and organize
dap_urls = sorted(set(dap_urls))
print "Total DAP:",len(dap_urls)
#print the first 5...
print "\n".join(dap_urls[:])

# <codecell>

sos_urls = service_urls(csw.records,service='sos:url')
#remove duplicates and organize
sos_urls = sorted(set(sos_urls))
print "Total SOS:",len(sos_urls)
print "\n".join(sos_urls)

# <codecell>

start_time = dt.datetime.strptime(start_date,'%Y-%m-%d %H:%M')
end_time = dt.datetime.strptime(stop_date,'%Y-%m-%d %H:%M')
iso_start = start_time.strftime('%Y-%m-%dT%H:%M:%SZ')
iso_end = end_time.strftime('%Y-%m-%dT%H:%M:%SZ')

# <markdowncell>

# #### create a list of stations available

# <codecell>

st_list = {}

# <codecell>

def processStationInfo(obs_loc_df,st_list,source):
    st_data = obs_loc_df['station_id']
    lat_data = obs_loc_df['latitude (degree)']
    lon_data = obs_loc_df['longitude (degree)']

    for i in range(0,len(st_data)):
        station_name = st_data[i]
        if station_name in st_list:
            pass
        else:
            st_list[station_name] = {}
            st_list[station_name]["lat"] = lat_data[i]
            st_list[station_name]["source"] = source
            st_list[station_name]["lon"] = lon_data[i]
            print station_name

    print "number of stations in bbox",len(st_list.keys())
    return st_list

# <markdowncell>

# #COOPS Station Locations

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
       'offering=urn:ioos:network:NOAA.NOS.CO-OPS:CurrentsActive&'
       'featureOfInterest=BBOX:%s&responseFormat=text/csv') % (sos_name, box_str))

print url
obs_loc_df = pd.read_csv(url)

# <codecell>

st_list = processStationInfo(obs_loc_df,st_list,"coops")
print st_list

# <markdowncell>

# #NDBC Station Locations

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

url = (('http://sdf.ndbc.noaa.gov/sos/server.php?'
       'request=GetObservation&service=SOS&'
       'version=1.0.0&'
       'offering=urn:ioos:network:noaa.nws.ndbc:all&'
       'featureofinterest=BBOX:%s&'
       'observedproperty=%s&'
       'responseformat=text/csv&')% (box_str,sos_name))


print url
obs_loc_df = pd.read_csv(url)
st_list = processStationInfo(obs_loc_df,st_list,"ndbc")

# <codecell>

#function handles current requests
def coopsCurrentRequest(station_id,tides_dt_start,tides_dt_end):
    tides_data_options = "time_zone=gmt&application=ports_screen&format=json"
    tides_url = "http://tidesandcurrents.noaa.gov/api/datagetter?"   
    begin_datetime = "begin_date="+tides_dt_start
    end_datetime = "&end_date="+tides_dt_end
    current_dp = "&station="+station_id
    full_url = tides_url+begin_datetime+end_datetime+current_dp+"&application=web_services&product=currents&units=english&"+tides_data_options
    r = requests.get(full_url)
    try:
        r= r.json()
    except:
        return None
    if 'data' in r:
        r = r['data']
        data_dt = []
        data_spd = []
        data_dir = []
        for row in r:
            #convert from knots to cm/s
            data_spd.append(float(row['s'])*51.4444444)
            data_dir.append(float(row['d']))            
            date_time_val = dt.datetime.strptime(row['t'], '%Y-%m-%d %H:%M')
            data_dt.append(date_time_val)
            
        data = {}
        data['sea_water_speed (cm/s)'] = np.array(data_spd)
        data['direction_of_sea_water_velocity (degree)'] = np.array(data_dir)
        time = np.array(data_dt)
        
        df = pd.DataFrame(data=data,index=time,columns = ['sea_water_speed (cm/s)','direction_of_sea_water_velocity (degree)'] )    
        return df
    else:
        return None

# <markdowncell>

# <div class="warning"><strong>NDBC DAP</strong> - NDBC DAP does not have the most recent observations</div>

# <codecell>

def ndbcCurrentRequest(station_id,dt_start,dt_end):
    
    year_max = {}
    
    main_df = pd.DataFrame()
    for year in range(dt_start.year,(dt_end.year+1)):
        try:
            station_name = station_id.split(":")[-1]
            url = 'http://dods.ndbc.noaa.gov/thredds/dodsC/data/adcp/'+station_name+'/'+station_name+'a'+str(year)+'.nc'
            
            nc = netCDF4.Dataset(url, 'r')  
            #zero depth is the shallowist
            depth_dim = nc.variables['depth'][:]
            
            dir_dim = nc.variables['water_dir'][:]
            speed_dim = nc.variables['water_spd'][:]
            time_dim = nc.variables['time']
            
            data_dt = []
            
            data_spd = []
            data_dir = []
            for i in range(0,len(speed_dim)):
                data_spd.append(speed_dim[i][0][0][0])
                data_dir.append(dir_dim[i][0][0][0])
            
            dates = num2date(time_dim[:],units=time_dim.units,calendar='gregorian')
                
            data = {}
            data['sea_water_speed (cm/s)'] = np.array(data_spd)
            data['direction_of_sea_water_velocity (degree)'] = np.array(data_dir)
            time = np.array(dates)

            df = pd.DataFrame(data=data,index=time,columns = ['sea_water_speed (cm/s)','direction_of_sea_water_velocity (degree)'] )    
            main_df = main_df.append(df)            
        except Exception,e:
            print "no data for",station_name,year,"found:",e   
    
    return main_df

# <codecell>

print "Date: ",iso_start," to ", iso_end
date_range_string = iso_start+"/"+iso_end
#i.e date range    2011-03-01T00:00Z/2011-03-02T00:00Z
def ndbcSOSRequest(station,date_range):
    
    url = ('http://sdf.ndbc.noaa.gov/sos/server.php?'
     'request=GetObservation&service=SOS&version=1.0.0'
     '&offering=%s&'
     'observedproperty=Currents&responseformat=text/csv'
     '&eventtime=%s') % (station,date_range)

    obs_loc_df = pd.read_csv(url)
    return obs_loc_df

# <markdowncell>

# #### Get the observation data from the stations identified

# <codecell>

divid = str(uuid.uuid4())
pb = HTML(
"""
<div style="border: 1px solid black; width:500px">
  <div id="%s" style="background-color:blue; width:0%%">&nbsp;</div>
</div> 
""" % divid)
display(pb) 

count = 0
for station_index in st_list.keys(): 
        
    st =  station_index.split(":")[-1]
    tides_dt_start = jd_start.strftime('%Y%m%d %H:%M')
    tides_dt_end = jd_stop.strftime('%Y%m%d %H:%M')
    
    if st_list[station_index]['source'] == "coops":
        df = coopsCurrentRequest(st,tides_dt_start,tides_dt_end)
    elif st_list[station_index]['source'] == "ndbc":
        df = ndbcSOSRequest(station_index,date_range_string)
    
    if (df is not None) and (len(df)>0):
        st_list[station_index]['hasObsData'] = True
    else:
        st_list[station_index]['hasObsData'] = False
    st_list[station_index]['obsData'] = df
    
    
    print station_index, st_list[station_index]['source'],st_list[station_index]['hasObsData']
    
    count+=1
    percent_compelte = (float(count)/float(len(st_list.keys())))*100
    display(Javascript("$('div#%s').width('%i%%')" % (divid, int(percent_compelte))))
    

# <markdowncell>

# <div class="success"><strong>HF Radar</strong> - Gets the HF radar for the requested date range</div>

# <codecell>

#directly access the dap endpoint to get data
def get_hr_radar_dap_data(dap_urls,st_list,jd_start,  jd_stop):
    # Use only data within 1.00 degrees
    obs_df = []
    obs_or_model = False
    max_dist = 1.0
    # Use only data where the standard deviation of the time series exceeds 0.01 m (1 cm).
    # This eliminates flat line model time series that come from land points that should have had missing values.
    min_var = 0.1
    data_idx = []
    
    df_list = []
    for url in dap_urls:         
        #only look at 6km hf radar
        if 'http://hfrnet.ucsd.edu/thredds/dodsC/HFRNet/USWC/' in url and "6km" in url and "GNOME" in url:                                  
            print url
            #get url
            nc = netCDF4.Dataset(url, 'r')
            lat_dim = nc.variables['lat']  
            lon_dim = nc.variables['lon']  
            time_dim = nc.variables['time']
            u_var = None
            v_var = None
            for key in nc.variables.iterkeys():
                 key_dim = nc.variables[key]  
                 try:
                    if key_dim.standard_name == "surface_eastward_sea_water_velocity":
                        u_var = key_dim 
                    elif key_dim.standard_name == "surface_northward_sea_water_velocity":                        
                        v_var = key_dim                        
                    elif key_dim.standard_name == "time":
                        time = key_dim                        
                 except:
                    #only if the standard name is not available
                    pass
                
            #manage dates            
            dates = num2date(time_dim[:],units=time_dim.units,calendar='gregorian')
            date_idx = []
            date_list = []
            for i, date in enumerate(dates):
                if jd_start < date < jd_stop:
                    date_idx.append(i)                        
                    date_list.append(date)
            #manage location
            for st in st_list:
                station = st_list[st]
                f_lat = station['lat']
                f_lon = station['lon']
                
                ret = find_nearest(f_lat,f_lon, lat_dim[:],lon_dim[:])
                lat_idx = ret[0]
                lon_idx = ret[1]
                dist_deg = ret[2]
                #print "lat,lon,dist=",ret
                
                if len(u_var.dimensions) == 3:
                    #3dimensions
                    ret = cycleAndGetData(u_var,v_var,date_idx,lat_idx,lon_idx)   
                    u_vals = ret[0]
                    v_vals = ret[1]
                    
                    lat_idx = ret[2]
                    lon_idx = ret[3]
                    
                    print "lat,lon,dist=",ret[2],ret[3]                                                 
                try:                                                              
                    #turn vectors in the speed and direction
                    ws = uv2ws(u_vals,v_vals) 
                    wd = uv2wd(u_vals,v_vals) 

                    data_spd = []
                    data_dir = []
                    data = {}
                    data['sea_water_speed (cm/s)'] = np.array(ws)
                    data['direction_of_sea_water_velocity (degree)'] = np.array(wd)
                    time = np.array(date_list)
                
                    df = pd.DataFrame(data=data,index=time,columns = ['sea_water_speed (cm/s)','direction_of_sea_water_velocity (degree)'] )    
                    df_list.append({"name":st,
                                    "data":df,
                                    "lat":lat_dim[lat_idx],
                                    "lon":lon_dim[lon_idx],
                                   "ws_pts":np.count_nonzero(~np.isnan(ws)),
                                   "wd_pts":np.count_nonzero(~np.isnan(wd)),
                                   "dist":dist_deg,
                                   'from':url
                                   })
                except Exception,e:
                    print "\t\terror:",e                       
        else:
            pass
        
    return df_list     

# <codecell>

df_list = get_hr_radar_dap_data(dap_urls,st_list,jd_start,  jd_stop)

# <markdowncell>

# <div class="success"><strong>Model Data</strong> - get model data from the SFO ports operational model</div>

# <codecell>

def extractSFOModelData(lat_lon_list,name_list):
    print "Extract SFOModelData from http://opendap.co-ops.nos.noaa.gov/thredds/ "
    urls = buildSFOUrls(jd_start,  jd_stop)
    index = -1   
    #setup struct
    df_list = {}
    for n in name_list:
        df_list[n] = {}        
    
    data_dates = []
    for i, url in enumerate(urls):
        try:
            #print url
            nc = netCDF4.Dataset(url, 'r')   
        except:
            #print  "\tNot Available"
            break
            
        if i == 0:
            lats = nc.variables['lat'][:]
            lons = nc.variables['lon'][:]
            lons = lons-360
            index_list,dist_list = findSFOIndexs(lats,lons,lat_lon_list)

        #Extract the model data using and MF dataset
        time_dim = nc.variables['time']
        u_dim = nc.variables['u']
        v_dim = nc.variables['v']

        u_var = u_dim[:,0,index_list] 
        v_var = v_dim[:,0,index_list]

        #create the dates            
        dates = num2date(time_dim[:],units=time_dim.units,calendar='gregorian')                
        #data_dates.append(dates)
        
        for i, n in enumerate(name_list):
            #get lat and lon
            df_list[n]['lat'] = lats[index_list[i]]
            df_list[n]['lon'] = lons[index_list[i]]
            #create speed and direction, convert 
            ws = uv2ws(u_var[:,i]*100,v_var[:,i]*100) 
            wd = uv2wd(u_var[:,i]*100,v_var[:,i]*100) 

            data = {}
            data['sea_water_speed (cm/s)'] = ws
            data['direction_of_sea_water_velocity (degree)'] = wd
            columns = ['sea_water_speed (cm/s)','direction_of_sea_water_velocity (degree)']
            
            df = pd.DataFrame(data=data, index=dates, columns=columns)
            #create struct
            if 'data' in df_list[n]:
                df_list[n]['data'] = df_list[n]['data'].append(df)        
            else:
                df_list[n]['data'] = df

    return df_list

# <markdowncell>

# <div class="success"><strong>Station Model Data</strong> - For the stations find the model data at the same location</div>

# <codecell>

## Stations we know contain all three data types of interest
st_known =['urn:ioos:station:NOAA.NOS.CO-OPS:s09010','urn:ioos:station:NOAA.NOS.CO-OPS:s08010']
lat_lon_list = []
name_list = []
for st in st_list:
    if st in st_known:
        lat = st_list[st]['lat']
        lon = st_list[st]['lon']    
        name_list.append(st)
        lat_lon_list.append([lat,lon])
        
model_data = extractSFOModelData(lat_lon_list,name_list)

# <codecell>

for station_index in st_list.keys():
    df = st_list[station_index]['obsData']  
    if st_list[station_index]['hasObsData']:
        fig = plt.figure(figsize=(16, 3))
        plt.plot(df.index, df['sea_water_speed (cm/s)'])
        fig.suptitle('Station:'+station_index, fontsize=14)
        plt.xlabel('Date', fontsize=14)
        plt.ylabel('sea_water_speed (cm/s)', fontsize=14)   
        
        if station_index in model_data:
            df_model = model_data[station_index]['data']
            plt.plot(df_model.index, df_model['sea_water_speed (cm/s)'])
        # post those stations not already added        
        for ent in df_list:  

            if ent['ws_pts'] >4:   
                if station_index == ent['name'] :
                    df = ent['data']   
                    plt.plot(df.index, df['sea_water_speed (cm/s)'])
                    ent['valid'] = True 
                    
    l = plt.legend(('Station Obs','Model','HF Radar'), loc='upper left')

# <markdowncell>

# Model data is not in the NGDC catalog

# <codecell>

#add map title
htmlContent = ('<p><h4>Location Map: Blue: Station Obs, Green: Model Data, Red: HF Radar</h4></p>') 
station =  st_list[st_list.keys()[0]]
map = folium.Map(location=[station["lat"], station["lon"]], zoom_start=10)
map.line(get_coordinates(bounding_box, bounding_box_type), line_color='#FF0000', line_weight=5)

#plot the obs station, 
for st in st_list:  
    lat = st_list[st]['lat']
    lon = st_list[st]['lon']
    
    popupString = '<b>Obs Location:</b><br>'+st+'<br><b>Source:</b><br>'+st_list[st]['source']
    
    if 'hasObsData' in st_list[st] and st_list[st]['hasObsData'] == False:
        map.circle_marker([lat,lon], popup=popupString, 
                          radius=1000,
                          line_color='#FF0000',
                          fill_color='#FF0000', 
                          fill_opacity=0.2)
        
    elif st_list[st]['source'] == "coops":
        map.simple_marker([lat,lon], popup=popupString,marker_color="darkblue",marker_icon="star")
    elif st_list[st]['source'] == "ndbc":
        map.simple_marker([lat,lon], popup=popupString,marker_color="darkblue",marker_icon="star")

try:
    for ent in df_list:

        lat = ent['lat']
        lon = ent['lon']
        popupstring = "HF Radar: ["+ str(lat)+":"+str(lon)+"]" + "<br>for<br>" + ent['name']
        map.circle_marker([lat,lon], popup=popupstring, 
                          radius=500,
                          line_color='#FF0000',
                          fill_color='#FF0000', 
                          fill_opacity=0.5)
except:
    pass

try:
    for st in model_data:

        lat = model_data[st]['lat']
        lon = model_data[st]['lon']
        popupstring = "HF Radar: ["+ str(lat)+":"+str(lon)+"]" + "<br>for<br>" + ent['name']
        map.circle_marker([lat,lon], popup=popupstring, 
                          radius=500,
                          line_color='#66FF33',
                          fill_color='#66FF33', 
                          fill_opacity=0.5)
except:
    pass

display(HTML(htmlContent))

## adds the HF radar tile layers
jd_now = dt.datetime.utcnow()
map.add_tile_layer(tile_name='hfradar 2km',
                   tile_url='http://hfradar.ndbc.noaa.gov/tilesavg.php?s=10&e=100&x={x}&y={y}&z={z}&t='+str(jd_now.year)+'-'+str(jd_now.month)+'-'+str(jd_now.day)+' '+str(jd_now.hour-2)+':00:00&rez=2')

map.add_layers_to_map()

inline_map(map)  

# <codecell>


