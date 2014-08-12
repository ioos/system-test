
# coding: utf-8

# ># IOOS System Test: [Extreme Events Theme:](https://github.com/ioos/system-test/wiki/Development-of-Test-Themes#theme-2-extreme-events) Coastal Inundation

# ### Can we obtain observed current data at stations located within a bounding box?
# This notebook is based on IOOS System Test: Inundation

# Methodology:
# 
# * Define temporal and spatial bounds of interest, as well as parameters of interest
# * Search for available service endpoints in the NGDC CSW catalog meeting search criteria
# * Search for available OPeNDAP data endpoints
# * Obtain observation data sets from stations within the spatial boundaries (from CO-OPS and NDBC)
# * Extract time series for identified stations
# * Plot time series data, current rose, annual max values per station
# * Plot observation stations on a map 

# #### import required libraries

# In[39]:

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

import numpy as np
import pandas as pd
from pyoos.collectors.ndbc.ndbc_sos import NdbcSos
from pyoos.collectors.coops.coops_sos import CoopsSos
import requests

from utilities import (fes_date_filter, coops2df, coops2data, find_timevar, find_ij, nearxy, service_urls, mod_df, 
                       get_coordinates, get_Coops_longName, inline_map, get_coops_sensor_name,css_styles)

import cStringIO
from lxml import etree
import urllib2
import time as ttime
from io import BytesIO

#for pltting
from windrose import WindroseAxes
import matplotlib.cm as cm
from numpy import arange

css_styles()


# <div class="warning"><strong>Temporal Bounds</strong> - Anything longer than one year kills the CO-OPS service</div>

# In[2]:

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
jd_start,  jd_stop = jd_now - dt.timedelta(days=(365*10)), jd_now

start_date = jd_start.strftime('%Y-%m-%d %H:00')
stop_date = jd_stop.strftime('%Y-%m-%d %H:00')

jd_start = dt.datetime.strptime(start_date, '%Y-%m-%d %H:%M')
jd_stop = dt.datetime.strptime(stop_date, '%Y-%m-%d %H:%M')
print start_date,'to',stop_date


# In[3]:

#put the names in a dict for ease of access 
data_dict = {}
sos_name = 'Currents'
data_dict['currents'] = {"names":['currents',
                                  'surface_eastward_sea_water_velocity',
                                  '*surface_eastward_sea_water_velocity*'], 
                         "sos_name":['currents']}  


# CSW Search

# In[4]:

endpoint = 'http://www.ngdc.noaa.gov/geoportal/csw' # NGDC Geoportal
csw = CatalogueServiceWeb(endpoint,timeout=60)


# Search

# In[5]:

# convert User Input into FES filters
start,stop = fes_date_filter(start_date,stop_date)
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


# DAP

# In[6]:

dap_urls = service_urls(csw.records)
#remove duplicates and organize
dap_urls = sorted(set(dap_urls))
print "Total DAP:",len(dap_urls)
#print the first 5...
print "\n".join(dap_urls[:])


# Get SOS links, NDBC is not available so add it...

# In[7]:

sos_urls = service_urls(csw.records,service='sos:url')
#remove duplicates and organize
sos_urls = sorted(set(sos_urls))
print "Total SOS:",len(sos_urls)
print "\n".join(sos_urls)


# #### Update SOS timedate

# In[8]:

start_time = dt.datetime.strptime(start_date,'%Y-%m-%d %H:%M')
end_time = dt.datetime.strptime(stop_date,'%Y-%m-%d %H:%M')
iso_start = start_time.strftime('%Y-%m-%dT%H:%M:%SZ')
iso_end = end_time.strftime('%Y-%m-%dT%H:%M:%SZ')


# <div class="success"><strong>Get list of stations</strong> - we get a list of the available stations from NOAA and COOPS</div>

# #### Initalize Station Data List

# In[9]:

st_list = {}


# In[10]:

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


# #### Get CO-OPS Station Data

# In[11]:

coops_collector = CoopsSos()
coops_collector.start_time = start_time
coops_collector.end_time = end_time
coops_collector.variables = data_dict["currents"]["sos_name"]
coops_collector.server.identification.title
print coops_collector.start_time,":", coops_collector.end_time
ofrs = coops_collector.server.offerings
print(len(ofrs))


# #### gets a list of the active stations from coops

# In[12]:

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


# #### COOPS Station Information

# In[13]:

st_list = processStationInfo(obs_loc_df,st_list,"coops")


# In[14]:

print st_list


# #### Get NDBC Station Data

# In[15]:

ndbc_collector = NdbcSos()
ndbc_collector.start_time = start_time
ndbc_collector.end_time = end_time
ndbc_collector.variables = data_dict["currents"]["sos_name"]
ndbc_collector.server.identification.title
print ndbc_collector.start_time,":", ndbc_collector.end_time
ofrs = ndbc_collector.server.offerings
print(len(ofrs))


# In[16]:

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


# #### NDBC Station information

# In[17]:

st_list = processStationInfo(obs_loc_df,st_list,"ndbc")
print st_list


# In[18]:

print st_list[st_list.keys()[0]]['lat']
print st_list[st_list.keys()[0]]['lon']


# #### NDBC Data Access

# In[19]:

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


# #### The function only support who date time differences

# In[20]:

def isInteger(n):
    """Return True if argument is a whole number, False if argument has a fractional part."""
    if n%2 == 0 or (n+1)%2 == 0:
        return True
    return False


# <div class="error"><strong>Large Temporal Requests Need To Be Broken Down</strong> - When requesting a large temporal range outside the SOS limit, the sos request needs to be broken down. see issues in [ioos](https://github.com/ioos/system-test/issues/81),  [ioos](https://github.com/ioos/system-test/issues/101),  [ioos](https://github.com/ioos/system-test/issues/116) and [pyoos](https://github.com/ioos/pyoos/issues/35). Unfortunatly currents is not available via DAP ([ioos](https://github.com/ioos/system-test/issues/116))</div>

# <div class="error"><strong>Large Temporal Requests Need To Be Broken Down</strong> - Obtaining long time series from COOPS via SOS is not ideal and the opendap links are not available, so we use the tides and currents api to get the currents in json format. The api response provides in default bin, unless a bin is specified (i.e bin=1)</div>

# In[21]:

def breakdownCurrentRequest(collector,station_id,max_days,sos_name,divid):
    responseFormat = "csv"
    
    #loop through the years and get the data needed
    st_time =(collector.start_time)
    ed_time =(collector.end_time)
    #only max_days days are allowed to be requested at once
    #end-start gives days in date time object
    dt_diff = ed_time - st_time
    num_days = dt_diff.days
    print num_days
    num_requests = num_days/max_days
    print "Num requests:", num_requests
    #if its whole days
    master_df = pd.DataFrame()
    
    print num_requests
    if isInteger(num_requests):
        #need to add one to the range
        
        for i in range(1,num_requests+1):
            
            percent_compelte = (float(i)/float(num_requests))*100
            display(Javascript("$('div#%s').width('%i%%')" % (divid, int(percent_compelte))))
                        
            st_days = (i-1)*max_days
            ed_days = i*max_days
            req_st = st_time + dt.timedelta(days=st_days)
            req_end = st_time + dt.timedelta(days=ed_days)
            
            iso_start = req_st.strftime('%Y-%m-%dT%H:%M:%SZ')
            iso_end = req_end.strftime('%Y-%m-%dT%H:%M:%SZ')
            
            tides_dt_start = req_st.strftime('%Y%m%d %H:%M')
            tides_dt_end = req_end.strftime('%Y%m%d %H:%M')
                    
            if isinstance(collector, CoopsSos):
                #print "coops"
                try:
                    #CANNOT USE THIS AS ITS NOT READY 
                    #df = coops2df(collector, station_id, sos_name, iso_start, iso_end,procedure) or #df = coopsCurrentRequest2(collector,station_id,req_st,req_end)    
                    df = coopsCurrentRequest(station_id,tides_dt_start,tides_dt_end)    
                    #if the frame is not empty add it
                    if df is not None:
                        master_df.append(df)                       
                        #wait on the request
                        ttime.sleep(5)
                except Exception,e:
                    print"error getting data",str(e)
            elif isinstance(collector, NdbcSos):
                #print "ndbc"
                try:    
                    #df = ndbcCurrentRequest2(collector,station_id,req_st,req_end)                    
                    #if the frame is not empty add it
                    if df is not None:
                        master_df.append(df)                       
                except Exception,e:
                    print"error getting data",str(e)
                       
        return master_df


# <div class="warning"><strong>Pyoos</strong> - Should be able to use the collector but does not work?</div>

# In[22]:

def ndbcCurrentRequest2(collector,station_id,dt_start,dt_end):
    try:
        #uses date time object
        collector = NdbcSos()
        collector.variables = ['currents']
        collector.filter(start=dt_start, end=dt_start,features=[station_id])
        response = collector.raw(responseFormat="text/csv")
        obs_loc_df = pd.read_csv(BytesIO(response.encode('utf-8')),
                               parse_dates=True,
                               index_col='date_time')

        return obs_loc_df
    except:
        return None


# <div class="warning"><strong>Pyoos</strong> - Should be able to use the collector, but does not work?</div>

# In[23]:

def coopsCurrentRequest2(collector,station_id,dt_start,dt_end):
    try:
        #uses date time object
        collector = CoopsSos()
        collector.variables = ['currents']

        station_name = station_id.split(":")
        station_name = station_name[-1]

        collector.filter(start=dt_start, end=dt_start,features=[station_name])
        response = collector.raw(responseFormat="text/csv")
        obs_loc_df = pd.read_csv(BytesIO(response.encode('utf-8')),
                               parse_dates=True,
                               index_col='date_time')

        return obs_loc_df
    except:
        return None


# In[24]:

def coopsCurrentRequest(station_id,tides_dt_start,tides_dt_end):
    tides_data_options = "time_zone=gmt&application=ports_screen&format=json"
    tides_url = "http://tidesandcurrents.noaa.gov/api/datagetter?"   
    begin_datetime = "begin_date="+tides_dt_start
    end_datetime = "&end_date="+tides_dt_end
    current_dp = "&station="+station_id
    full_url = tides_url+begin_datetime+end_datetime+current_dp+"&application=web_services&product=currents&units=english&"+tides_data_options
    t0 = ttime.time()
    r = requests.get(full_url)
    t1 = ttime.time()
    total = t1-t0
    print "time request",total
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
            data_spd.append(float(row['s']))
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


# <div class="info"><strong>Use NDBC DAP endpoints to get timeseries data</strong> - The DAP server for currents is available for NDBC data, we use that to get long time series data.</div>

# In[25]:

def ndbcCurrentRequest(station_id,dt_start,dt_end):
    
    year_max = {}
    
    main_df = pd.DataFrame()
    for year in range(dt_start.year,(dt_end.year+1)):
        percent_compelte = (float(year-dt_start.year)/float((dt_end.year)-dt_start.year))*100.
        display(Javascript("$('div#%s').width('%i%%')" % (divid, int(percent_compelte))))
        
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


# <div class="info"><strong>Progress Information For Large Requests</strong> - Shows the user a progress bar for each stations as its processed. Click [here]('http://www.tidesandcurrents.noaa.gov/cdata/StationList?type=Current+Data&filter=active') to show more information on the CO-OPS locations</div>

# <div class="error"><strong>Processing long time series</strong> - The CO-OPS Server responds really slow (> 30secs, for what should be a 5 sec request) to multiple requests, so getting long time series data is almost impossible.</div>

# #### get CO-OPS station data

# In[26]:

#used to define the number of days allowable by the service
coops_point_max_days = 30
ndbc_point_max_days = 30

print "start & end dates:",jd_start, jd_stop,"\n"

for station_index in st_list.keys():    
    #set it so we can use it later
    st =  station_index.split(":")[-1]
    print station_index, st_list[station_index]['source']
    divid = str(uuid.uuid4())
    pb = HTML(
    """
    <div style="border: 1px solid black; width:500px">
      <div id="%s" style="background-color:blue; width:0%%">&nbsp;</div>
    </div> 
    """ % divid)
    display(pb) 
    
    if st_list[station_index]['source'] == 'coops':  
        #coops fails for large requests
        master_df = []
        #master_df = breakdownCurrentRequest(coops_collector,st,coops_point_max_days,sos_name,divid)
    elif st_list[station_index]['source'] == 'ndbc':
        #use the dap catalog to get the data
        master_df = ndbcCurrentRequest(station_index,jd_start,jd_stop)
    if len(master_df)>0:
        st_list[station_index]['hasObsData'] = True
    st_list[station_index]['obsData'] = master_df   


# In[27]:

#check theres data in there
print st_list[st_list.keys()[2]]


# ### Plot the pandas data frames for the stations

# <div class="error"><strong>Station Data Plot</strong> - There might be an issue with some of the NDBC station data...</div>

# In[28]:

for station_index in st_list.keys():
    df = st_list[station_index]['obsData']    
    if len(df) >1:
        st_list[station_index]['hasObsData'] = True
        print "num rows:",len(df)
        fig = plt.figure(figsize=(18, 3))
        plt.scatter(df.index, df['sea_water_speed (cm/s)'])
        fig.suptitle('Station:'+station_index, fontsize=20)
        plt.xlabel('Date', fontsize=18)
        plt.ylabel('sea_water_speed (cm/s)', fontsize=16)
    else:
        st_list[station_index]['hasObsData'] = False        


# #### Find the min and max data values

# <div class="warning"><strong>Station Data Plot</strong> - Some stations might not plot due to the data</div>

# In[35]:

#...and adjust the legend box
def set_legend(ax):
    l = ax.legend()
    plt.setp(l.get_texts(), fontsize=8)
def new_axes():
    fig = plt.figure(figsize=(8, 8), dpi=80, facecolor='w', edgecolor='w')
    rect = [0.1, 0.1, 0.8, 0.8]
    ax = WindroseAxes(fig, rect, axisbg='w')
    fig.add_axes(ax)
    return ax      


# In[36]:

##build current roses
filelist = [ f for f in os.listdir("./images") if f.endswith(".png") ]
for f in filelist:
    os.remove("./images/"+f)

station_min_max = {}
for station_index in st_list.keys():
    all_spd_data = {}
    all_dir_data = {}
    all_time_spd = []
    all_time_dir = []
    df = st_list[station_index]['obsData']
    if len(df) >1:
        try:      
            spd_data= df['sea_water_speed (cm/s)'].values
            spd_data = np.array(spd_data)    

            dir_data= df['direction_of_sea_water_velocity (degree)'].values
            dir_data = np.array(dir_data)
            
            time_data= df.index.tolist()
            time_data = np.array(time_data)           
    
            for idx in range(0,len(spd_data)):                                    
                if spd_data[idx] > 998:                
                    continue
                elif np.isnan(spd_data[idx]):
                    continue
                elif dir_data[idx] == 0:  
                    continue
                else:                                    
                    dt_year = time_data[idx].year
                    dt_year = str(dt_year)
                    if dt_year not in all_spd_data.keys():
                        all_spd_data[dt_year] = []
                        all_dir_data[dt_year] = []
                    #convert to knots
                    knot_val = (spd_data[idx]*0.0194384449)                   
                    knot_val = "%.4f" % knot_val
                    knot_val = float(knot_val)
                    
                    all_spd_data[dt_year].append(knot_val)
                    all_dir_data[dt_year].append(dir_data[idx])                    
                                                            
                    all_time_spd.append(knot_val)
                    all_time_dir.append(dir_data[idx])        
            
            all_time_spd = np.array(all_time_spd,dtype=np.float)
            all_time_dir = np.array(all_time_dir,dtype=np.float)
            
            station_min_max[station_index]= {}
            for year in all_spd_data.keys():                
                year_spd = np.array(all_spd_data[year])
                year_dir = np.array(all_dir_data[year])                                
                station_min_max[station_index][year] = {}                
                station_min_max[station_index][year]['pts'] = len(year_spd)
                station_min_max[station_index][year]['spd_min'] = np.min(year_spd)
                station_min_max[station_index][year]['spd_max'] = np.max(year_spd)                
                dir_min = np.argmin(year_spd)
                dir_max = np.argmax(year_spd)                
                station_min_max[station_index][year]['dir_at_min'] = year_dir[dir_min]
                station_min_max[station_index][year]['dir_at_max'] = year_dir[dir_max]
          
            try:
                #A stacked histogram with normed (displayed in percent) results                                
                ax = new_axes()
                ax.set_title(station_index.split(":")[-1]+" stacked histogram with normed (displayed in %)\n results (spd in knots), All Time")     
                ax.bar(all_time_dir, all_time_spd, normed=True, opening=0.8, edgecolor='white')
                set_legend(ax) 
                
                fig = matplotlib.pyplot.gcf()
                fig.set_size_inches(8,8)
                fig.savefig('./images/'+station_index.split(":")[-1]+'.png',dpi=100)
                
            except:
                print "error when plotting",e
                pass

        except Exception,e:
            print "error",e
            pass
      


# In[40]:

#plot the min and max from each station
fields = ['spd_']

for idx in range(0,len(fields)):
    d_field = fields[idx]
    
    fig, axes = plt.subplots(1, 1, figsize=(18,5))   
    for st in station_min_max:        
        x = []
        y_min = []
        y_max = []
        
        for year in station_min_max[st]:
            x.append(year)            
            y_max.append(station_min_max[st][year][d_field+'max'])     
        
        marker_size = station_min_max[st][year]['pts']/80
        marker_size+=20
        station_label = st.split(":")[-1]
       
        axes.scatter(np.array(x), np.array(y_max),label=station_label,s=marker_size,c=numpy.random.rand(3,1),marker="o")      
        axes.set_xlim([2000,2015])
        axes.set_title("Yearly Max Speed Per Station, Marker Scaled Per Annual Pts (bigger = more pts per year)");
        axes.set_ylabel("speed (knots)")
        axes.set_xlabel("Year")
        plt.legend(loc='upper left');
        


# #### Produce Interactive Map

# In[41]:

station =  st_list[st_list.keys()[0]]
map = folium.Map(location=[station["lat"], station["lon"]], zoom_start=4)
map.line(get_coordinates(bounding_box, bounding_box_type), line_color='#FF0000', line_weight=5)

#plot the obs station, 
for st in st_list:     
    hasObs = st_list[st]['hasObsData']
    if hasObs: 
        if os.path.isfile('./images/'+st.split(":")[-1]+'.png'):
            map.simple_marker([st_list[st]["lat"], st_list[st]["lon"]], popup='Obs Location:<br>'+st+'<br><img border=120 src="./images/'+st.split(":")[-1]+'.png" width="242" height="242">',marker_color="green",marker_icon="ok")
        else:
            map.simple_marker([st_list[st]["lat"], st_list[st]["lon"]], popup='Obs Location:<br>'+st,marker_color="green",marker_icon="ok")
    else:            
        map.simple_marker([st_list[st]["lat"], st_list[st]["lon"]], popup='Obs Location:<br>'+st,marker_color="red",marker_icon="remove")
inline_map(map)        

