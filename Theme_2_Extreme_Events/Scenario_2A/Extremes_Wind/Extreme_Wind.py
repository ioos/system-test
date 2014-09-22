# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <markdowncell>

# ># IOOS System Test: [Extreme Events Theme:](https://github.com/ioos/system-test/wiki/Development-of-Test-Themes#theme-2-extreme-events) Coastal Inundation

# <markdowncell>

# ### Questions:
# 1. Can we discover and access long time series wind data from observed datasets?
# 2. Can we estimate the return period of a given wind speed by doing an extreme value analysis of the long term wind data?

# <markdowncell>

# ### Methodology:
# * Define temporal and spatial bounds of interest
# * Define standard names of variable of interest to search for in data sets
# * Search for available service endpoints in the NGDC CSW catalog meeting search criteria
# * Extract OPeNDAP data endpoints from model datasets and SOS endpoints from station observation datasets
# * Obtain long term observation data sets from a station within bounding box (10+ years)
# * Define a new temporal range to search for a particular event (Hurricane Sandy)
# * Using DAP (model) endpoints find all available model data sets in the bounding box, for the specified time range, and extract a model grid cell closest to the observation station
# * Show observation stations and model grid points on a map (red marker for model grid points)
# * Find the maximum wind speed during the event.
# * Perform return period analysis on the long time series observation data and see where the modeled data falls

# <markdowncell>

# #### import required libraries

# <codecell>

import os
from datetime import datetime, timedelta
from io import BytesIO

import uuid
import folium
import json

import matplotlib.pyplot as plt
from owslib.csw import CatalogueServiceWeb
from owslib import fes

from scipy.stats import genextreme
import numpy as np
import pandas as pd
from pyoos.collectors.ndbc.ndbc_sos import NdbcSos
from pyoos.collectors.coops.coops_sos import CoopsSos

from utilities import (fes_date_filter, service_urls, get_coordinates, insert_progress_bar, update_progress_bar,
                       inline_map, css_styles, gather_station_info, get_ncfiles_catalog, new_axes, set_legend, nearxy)

css_styles()

# <codecell>

bounding_box_type = "box"

# Bounding Box [lon_min, lat_min, lon_max, lat_max]
area = {'Hawaii': [-160.0, 18.0, -154., 23.0],
        'Gulf of Maine': [-72.0, 41.0, -69.0, 43.0],
        'New York harbor region': [-75., 39., -71., 41.5],
        'Puerto Rico': [-70, 14, -60, 22],
        'East Coast': [-77, 36, -73, 38],
        'North West': [-130, 38, -121, 50],
        'Gulf of Mexico': [-92, 28, -84, 31],
        'Arctic': [-179, 63, -140, 80],
        'North East': [-74, 40, -69, 42],
        'Virginia Beach': [-76, 34, -74, 38],
        'San Diego': [-119, 32, -117, 33.5]}

bounding_box = area['San Diego']

# Temporal range.
jd_now = datetime.utcnow()
jd_start,  jd_stop = jd_now - timedelta(days=(365*20)), jd_now

start_date = jd_start.strftime('%Y-%m-%d %H:00')
stop_date = jd_stop.strftime('%Y-%m-%d %H:00')

jd_start = datetime.strptime(start_date, '%Y-%m-%d %H:%M')
jd_stop = datetime.strptime(stop_date, '%Y-%m-%d %H:%M')

print('%s to %s ' % (start_date, stop_date))

# <markdowncell>

# #### Specify data names of interest to search on

# <codecell>

# Put the names in a dict for ease of access.
data_dict = {}
sos_name = 'Winds'
data_dict['winds'] = {
                 "u_names":['eastward_wind', 
                            'u-component_of_wind', 
                            'u_component_of_wind', 
                            'u_component_of_wind_height_above_ground', 
                            'u-component_of_wind_height_above_ground', 
                            'ugrd10m', 
                            'wind'], 
                 "v_names":['northward_wind', 
                            'v-component_of_wind', 
                            'v-component_of_wind_height_above_ground', 
                            'vgrd10m', 
                            'wind'],
                 "sos_name":['winds']}  

# <markdowncell>

# #### Define CSW endpoint

# <codecell>

endpoint = 'http://www.ngdc.noaa.gov/geoportal/csw'  # NGDC Geoportal.
csw = CatalogueServiceWeb(endpoint, timeout=60)

# <markdowncell>

# #### Search the catologue using the FES filters

# <codecell>

# Convert User Input into FES filters.
start, stop = fes_date_filter(start_date, stop_date)
bbox = fes.BBox(bounding_box)

# Use the search name to create search filter.
kw = dict(propertyname='apiso:AnyText', 
          escapeChar='\\',
          wildCard='*', 
          singleChar='?')

or_filt = fes.Or([fes.PropertyIsLike(literal='*%s*' % val, **kw) 
                  for val in data_dict['winds']['u_names']])

val = 'Averages'
not_filt = fes.Not([fes.PropertyIsLike(literal=('*%s*' % val), **kw)])

filter_list = [fes.And([bbox, start, stop, or_filt, not_filt])]
csw.getrecords2(constraints=filter_list, maxrecords=1000, esn='full')
print("%s csw records found" % len(csw.records))

# <markdowncell>

# #### DAP endpoints

# <codecell>

dap_urls = service_urls(csw.records)
# Remove duplicates and organize.
dap_urls = sorted(set(dap_urls))
print("Total DAP: %s" % len(dap_urls))
print("\n".join(dap_urls[0:10]))

# <markdowncell>

# #### SOS endpoints

# <codecell>

sos_urls = service_urls(csw.records, service='sos:url')
# Remove duplicates and organize.
sos_urls = sorted(set(sos_urls))
print("Total SOS: %s" % len(sos_urls))
print("\n".join(sos_urls[0:10]))

# <markdowncell>

# #### Update SOS time-date

# <codecell>

start_time = datetime.strptime(start_date, '%Y-%m-%d %H:%M')
end_time = datetime.strptime(stop_date, '%Y-%m-%d %H:%M')
iso_start = start_time.strftime('%Y-%m-%dT%H:%M:%SZ')
iso_end = end_time.strftime('%Y-%m-%dT%H:%M:%SZ')

# <markdowncell>

# <div class="success"><strong>Get list of stations</strong>
# - we get a list of the available stations from NOAA and COOPS</div>

# <markdowncell>

# #### Initialize Station Data List

# <codecell>

st_list = {}

# <markdowncell>

# #### Get CO-OPS Station Data

# <codecell>

coops_collector = CoopsSos()
# coops_collector.variables = data_dict["winds"]["sos_name"]
coops_collector.server.identification.title
# Don't specify start and end date in the filter and the most recent observation will be returned
coops_collector.filter(bbox=bounding_box, variables=data_dict["winds"]["sos_name"])

response = coops_collector.raw(responseFormat="text/csv")
obs_loc_df = pd.read_csv(BytesIO(response.encode('utf-8')),
                         parse_dates=True,
                         index_col='date_time')

# Save the station info in a larger global dict
st_list = gather_station_info(obs_loc_df, st_list, "coops")

# Now let's specify start and end times
coops_collector.start_time = start_time
coops_collector.end_time = end_time

ofrs = coops_collector.server.offerings

# Print the first 5 rows of the DataFrame
obs_loc_df.head()

# <markdowncell>

# #### Get NDBC Station Data

# <codecell>

ndbc_collector = NdbcSos()
ndbc_collector.variables = data_dict["winds"]["sos_name"]
ndbc_collector.server.identification.title
# Don't specify start and end date in the filter and the most recent observation will be returned
ndbc_collector.filter(bbox=bounding_box,
                 variables=data_dict["winds"]["sos_name"])

response = ndbc_collector.raw(responseFormat="text/csv")
obs_loc_df = pd.read_csv(BytesIO(response.encode('utf-8')),
                         parse_dates=True,
                         index_col='date_time')

# Save the station info in a larger global dict
st_list = gather_station_info(obs_loc_df, st_list, "ndbc")

# Now let's specify start and end times
ndbc_collector.start_time = start_time
ndbc_collector.end_time = end_time

ofrs = ndbc_collector.server.offerings

# Print the first 5 rows of the DataFrame
obs_loc_df.head()

# <markdowncell>

# ### Get historical data

# <markdowncell>

# <div class="error">
# <strong>Large Temporal Requests Need To Be Broken Down</strong> -
# When requesting a large temporal range outside the SOS limit, the sos
# request needs to be broken down.  See issues in
# [ioos](https://github.com/ioos/system-test/issues/81),
# [ioos](https://github.com/ioos/system-test/issues/101),
# [ioos](https://github.com/ioos/system-test/issues/116)
# and
# [pyoos](https://github.com/ioos/pyoos/issues/35).  Unfortunately winds
# is not available via DAP
# ([ioos](https://github.com/ioos/system-test/issues/116))</div>

# <markdowncell>

# <div class="error"><strong>Processing long time series</strong> -
# The CO-OPS Server responds really slow (> 30 secs, for what should be
# a 5 sec request) to multiple requests, so getting long time series
# data is almost impossible.</div>

# <markdowncell>

# <div class="info">
# <strong>Use NDBC DAP endpoints to get time-series data</strong> -
# The DAP server for met data is available for NDBC, we use that
# to get long time series data.</div>

# <codecell>

divid = insert_progress_bar(title='Please wait...', color='red')
# Used to define the number of days allowable by the service.
coops_point_max_days = ndbc_point_max_days = 30
print("start & end dates: %s, %s\n" % (jd_start, jd_stop))
num_stations = len(st_list.keys())
count = 0
for station in st_list.keys():
    count += 1
    # Set it so we can use it later.
    st = station.split(":")[-1]
    print('[%s]: %s' % (st_list[station]['source'], st))

    if st_list[station]['source'] == 'coops':
        # Coops fails for large requests.
        master_df = pd.DataFrame()
    elif st_list[station]['source'] == 'ndbc':
        # Use the dap catalog to get the data.
        master_df = get_ncfiles_catalog(station, jd_start, jd_stop)

    if not master_df.empty:
        st_list[station]['hasObsData'] = True
    else:
        st_list[station]['hasObsData'] = False

    st_list[station]['obsData'] = master_df
    
    percent_complete = (float(count)/float(num_stations)) * 100
    update_progress_bar(divid, percent_complete)

# <markdowncell>

# ### Plot the station data

# <codecell>

for station in st_list.keys():
    if st_list[station]['hasObsData']:
        df = st_list[station]['obsData']
        fig, axes = plt.subplots(1, 1, figsize=(18, 4))
        df['wind_speed (m/s)'].plot(title='Station:' + station, legend=True, color='b')
        

# <markdowncell>

# #### Plot wind rose

# <codecell>

# Remove any existing plots...
filelist = [f for f in os.listdir("./images") if f.endswith(".png")]
for f in filelist:
    os.remove("./images/{}".format(f))

# Do work...
for station in st_list.keys():    
    if st_list[station]['hasObsData']:
        df = st_list[station]['obsData']
        try:
            # A stacked histogram with normed (displayed in percent) results.
            ax = new_axes()  # Wind rose polar axes
            ax.set_title("Station " + station.split(":")[-1] +
                         "\nstacked histogram with normed (displayed in %)")
            wind_speed = df['wind_speed (m/s)'].values
            wind_direction = df['wind_from_direction (degree)'].values
            ax.bar(wind_direction, wind_speed, normed=True, opening=0.8, edgecolor='white')
            set_legend(ax, 'Wind Speed (m/s)')

            fig = plt.gcf()
            fig.set_size_inches(8, 8)
            fname = './images/%s.png' % station.split(":")[-1]
            fig.savefig(fname, dpi=100)
        except Exception as e:
            print("Error when plotting %s" % e)

# <markdowncell>

# #### Define a couple plotting functions

# <codecell>

def plot_probability_density(annual_max, station_id):
    mle = genextreme.fit(sorted(annual_max), 0)
    mu = mle[1]
    sigma = mle[2]
    xi = mle[0]
    min_x = min(annual_max)-0.5
    max_x = max(annual_max)+0.5
    x = np.linspace(min_x, max_x, num=100)
    y = [genextreme.pdf(z, xi, loc=mu, scale=sigma) for z in x]

    fig = plt.figure(figsize=(12,6))
    axes = fig.add_axes([0.1, 0.1, 0.8, 0.8])
    xlabel = (station_id + " - Annual Max Wind Speed (m/s)")
    axes.set_title("Probability Density & Normalized Histogram")
    axes.set_xlabel(xlabel)
    axes.plot(x, y, color='Red')
    axes.hist(annual_max, bins=arange(min_x, max_x, abs((max_x-min_x)/10)), normed=1, color='Yellow')

# <codecell>

def plot_return_values(annual_max, station_id):
    fig, axes = plt.subplots(figsize=(20,6))
    T=np.r_[1:500]
    mle = genextreme.fit(sorted(annual_max), 0)
    mu = mle[1]
    sigma = mle[2]
    xi = mle[0]
#     print "The mean, sigma, and shape parameters are %s, %s, and %s, resp." % (mu, sigma, xi)
    sT = genextreme.isf(1./T, 0, mu, sigma)
    axes.semilogx(T, sT, 'r'), hold
    N=np.r_[1:len(annual_max)+1]; 
    Nmax=max(N);
    axes.plot(Nmax/N, sorted(annual_max)[::-1], 'bo')
    title = station_id
    axes.set_title(title)
    axes.set_xlabel('Return Period (yrs)')
    axes.set_ylabel('Wind Speed (m/s)') 
    axes.grid(True)

# <markdowncell>

# #### Get the Annual Maximums and plot Probability Density

# <codecell>

for station in st_list.keys():    
    annual_max = []
    if st_list[station]['hasObsData']:
        df = st_list[station]['obsData']
        grouped = df.groupby(lambda x: x.year)
        for year, group in grouped:
            # This is where you could check that there is enough data in the year
            # For example, if there is only
            annual_max.append(group['wind_speed (m/s)'].max())
        print  "Station {0} has {1} years of data".format(station.split(":")[-1], len(annual_max))
        if len(annual_max) > 10:  # Need AT LEAST 10 years of data
            plot_probability_density(annual_max, station.split(":")[-1])
            plot_return_values(annual_max, station.split(":")[-1])
    st_list[station]['annual_max'] = annual_max

# <markdowncell>

# ##Get WIS Hindcast data
# ###All of the WIS stations annual maximum data was downloaded and saved to a json file (WIS_extremes.txt)
# The Wave Information Studies (WIS) is a US Army Corps of Engineers (USACE) sponsored project that generates consistent, hourly, long-term (20+ years) wave climatologies along all US coastlines, including the Great Lakes and US island territories. The WIS program originated in the Great Lakes in the mid 1970’s and migrated to the Atlantic, Gulf of Mexico and Pacific Oceans.

# <codecell>

with open("./WIS_stations.txt") as json_file:
    location_data = json.load(json_file)
    
wis_lats = []
wis_lons = []
wis_stations = []
for station in location_data:
    wis_lats.append(location_data[station]['lat'])
    wis_lons.append(location_data[station]['lon'])
    wis_stations.append(station)

station_lats = []
station_lons = []
for station in st_list.keys():    
    if st_list[station]['hasObsData']:
        station_lats.append(st_list[station]['lat'])
        station_lons.append(st_list[station]['lon'])
        
ind, dd = nearxy(wis_lons, wis_lats, station_lons, station_lats)       

# Now get read the wis data
with open("./WIS_extremes.txt") as extremes_file:
    wis_extremes = json.load(extremes_file)

# Get the extremes from the closest station
wis_station_id = wis_stations[ind[0]]
wis_lat = wis_lats[ind[0]]
wis_lon = wis_lons[ind[0]]

wis_maximums = []
wis_directions = []
for year in wis_extremes[wis_station_id].keys():
    wis_maximums.append(wis_extremes[wis_station_id][year]['ws_at_max'])
    wis_directions.append(wis_extremes[wis_station_id][year]['wdir_at_max'])

# <markdowncell>

# #### Return Value Plot

# <codecell>

plot_return_values(wis_maximums, 'WIS ' + str(wis_station_id))

# <markdowncell>

# ### Create interactive map with wind rose images on icons

# <codecell>

station = st_list[st_list.keys()[0]]
m = folium.Map(location=[station["lat"], station["lon"]], zoom_start=4)
m.line(get_coordinates(bounding_box, bounding_box_type),
       line_color='#FF0000', line_weight=5)

for st in st_list:
    hasObs = st_list[st]['hasObsData']
    if hasObs:
        fname = './images/%s.png' % st.split(":")[-1]
        if os.path.isfile(fname):
            popup = ('Obs Location:<br>%s<br><img border=120 src="'
                     './images/%s.png" width="242" height="242">' %
                     (st, st.split(":")[-1]))
            m.simple_marker([st_list[st]["lat"], st_list[st]["lon"]],
                            popup=popup,
                            marker_color="green",
                            marker_icon="ok")
        else:
            popup = 'Obs Location:<br>%s' % st
            m.simple_marker([st_list[st]["lat"], st_list[st]["lon"]],
                            popup=popup,
                            marker_color="green",
                            marker_icon="ok")
    else:
        popup = 'Obs Location:<br>%s' % st
        m.simple_marker([st_list[st]["lat"], st_list[st]["lon"]],
                        popup=popup,
                        marker_color="red",
                        marker_icon="remove")
        
# Add WIS lat/lon
m.simple_marker([wis_lat, wis_lon],
                    popup='WIS Station' + str(wis_station_id),
                    marker_color="purple",
                    marker_icon="ok")
inline_map(m)

# <markdowncell>

# ### Conclusions
# 
# * It is possible to discover and access long time series wind data from observed datasets. Some endpoints make it easier than others. Co-ops stations limit data requests to 31 days, making it difficult to get long time series data, but NDBC has an OpenDap Server that makes it much easier.
# 
# * The wind speeds and directions were used to create wind rose plots and return value analysis plots. The amount of data available depends on the location. There are long data records (> 10 yrs) in the mid Atlantic and parts of the West Coast.
# 

# <codecell>


