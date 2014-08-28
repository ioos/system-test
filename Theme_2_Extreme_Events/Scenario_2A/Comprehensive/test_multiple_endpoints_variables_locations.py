# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <markdowncell>

# ># IOOS System Test: [Extreme Events Theme:](https://github.com/ioos/system-test/wiki/Development-of-Test-Themes#theme-2-extreme-events) Inundation

# <markdowncell>

# ### This is a single "spin-off notebook" for the basic oceanography variables (wind, waves, currents, and water level) to test all CSW end points for multiple geographies. 
# 
# ### Questions
# * Is data available for the basic oceanography variables in the CSW endpoints for multiple locations?
# * Let's take it one step further. Is the data recent (< 1 month)?
# 
# ####Methodology:
# 
# * Define temporal and spatial bounds of interest
# * Show bounding boxes being tested on a map
# * Define standard names of variables of interest to search for in data sets
# * Search for available service endpoints in the CSW catalogs meeting the search criteria for each variable
# * Plot the results in a horizontal bar graph

# <markdowncell>

# ### import required libraries

# <codecell>

import matplotlib.pyplot as plt
import numpy as np

from owslib.csw import CatalogueServiceWeb
from owslib import fes

import folium
import pandas as pd
import datetime as dt
from utilities import fes_date_filter, service_urls, get_coordinates, inline_map, css_styles, insert_progress_bar, update_progress_bar
css_styles()

# <markdowncell>

# ### Define spatial bounds of interest

# <codecell>

bounding_box_type = "box" 

# Bounding Box [lon_min, lat_min, lon_max, lat_max]
locations = {'Hawaii': [-160.0, 18.0, -154., 23.0],
             'Caribbean': [-75, 12, -55, 26],
             'East Coast': [-77, 30, -70, 40],
             'North West': [-130, 38, -121, 50],
             'Gulf of Mexico': [-94, 26, -84, 32],
             'Arctic': [-179, 63, 179, 80],
             'North East': [-74, 40, -67, 46]}

# <markdowncell>

# ### Plot the bounding boxes

# <codecell>

lat_center = 45
lon_center = -90
m = folium.Map(location=[lat_center, lon_center], zoom_start=2)

# Loop through bounding boxes
for location, bounding_box in locations.iteritems():
    # Create popup string for the bounding box
    popup_string = location
    m.line(get_coordinates(bounding_box, bounding_box_type), line_color='#FF0000', line_weight=5)

inline_map(m)

# <markdowncell>

# ### Define standard names of variable of interest to search for in data sets

# <markdowncell>

# <div class="warning"><strong></strong> - We need to specify all the names we know for each variable, names that will get used in the CSW search, and also to find data in the datasets that are returned. This is ugly and fragile. There hopefully will be a better way in the future...</div>

# <codecell>

# put the names in a dict for ease of access 
names_dict = {}
names_dict["waves"] = {"names": ['sea_surface_wave_significant_height',
                                 'significant_wave_height',
                                 'significant_height_of_wave',
                                 'sea_surface_wave_significant_height(m)',
                                 'sea_surface_wave_significant_height (m)',
                                 'water_surface_height'], 
                      "sos_name": ["waves"]} 

names_dict['winds'] = {"names": ['eastward_wind', 'u-component_of_wind', 'u-component_of_wind_height_above_ground', 'ugrd10m', 'wind'], 
                       "v_names": ['northward_wind', 'v-component_of_wind', 'v-component_of_wind_height_above_ground', 'vgrd10m', 'wind'],
                       "sos_name": ['winds']}  

names_dict['currents'] = {"names": ['eastward_sea_water_velocity_assuming_no_tide','surface_eastward_sea_water_velocity',
                                    '*surface_eastward_sea_water_velocity*', 'eastward_sea_water_velocity'], 
                          "v_names": ['northward_sea_water_velocity_assuming_no_tide','surface_northward_sea_water_velocity',
                                     '*surface_northward_sea_water_velocity*', 'northward_sea_water_velocity'],
                          "sos_name": ['currents']}

names_dict['water_level'] = {"names": ['water_surface_height_above_reference_datum',
                                       'sea_surface_height_above_geoid','sea_surface_elevation',
                                       'sea_surface_height_above_reference_ellipsoid','sea_surface_height_above_sea_level',
                                       'sea_surface_height','water level']}

# <markdowncell>

# ### Define the csw endpoints we know about

# <markdowncell>

# <div class="info">This cell lists catalog endpoints. The list is updated by the IOOS Program Office here: https://github.com/ioos/system-test/wiki/Service-Registries-and-Data-Catalogs </div>

# <codecell>

endpoints = ['http://www.nodc.noaa.gov/geoportal/csw',
             'http://data.nodc.noaa.gov/geoportal/csw',
             'http://www.ngdc.noaa.gov/geoportal/csw',
             'http://catalog.data.gov/csw-all',
             'https://data.noaa.gov/csw',
             'http://geoport.whoi.edu/geoportal/csw',
             'https://edg.epa.gov/metadata/csw',
             'http://cmgds.marine.usgs.gov/geonetwork/srv/en/csw',
             'http://cida.usgs.gov/gdp/geonetwork/srv/en/csw',
             'http://geodiscover.cgdi.ca/wes/serviceManagerCSW/csw',
             'http://geoport.whoi.edu/gi-cat/services/cswiso',
             'http://cwic.csiss.gmu.edu/cwicv1/discovery']

# Set the maximum number of records the CSW will return
max_records = 1000

# <markdowncell>

# ### Is data available for the basic oceanography variables in the CSW endpoints for multiple locations?
# 
# #### Check the CSW endpoints for each variable and location

# <markdowncell>

# <div class="warning"><strong>This next cell takes a long time to process!</strong>  <br>Go grab a coffee</div>

# <codecell>

# Add a waitbar to monitor status
divid = insert_progress_bar(title='Searching catalogs. Please wait...', color='red')

# Save all of the results in a list of Dataframes
results = {}
all_data = []

count = 0
# Loop through the csw endpoints
for endpoint in endpoints:
    print '\n' + endpoint

    csw = CatalogueServiceWeb(endpoint, timeout=60)
    # loop through the variables
    for var_name in names_dict:
#         print '\n' + var_name.upper()
        num_recs = []
        for location, bounding_box in locations.iteritems():
#             print location
            
            bbox = fes.BBox(bounding_box)
            #use the search name to create search filter
            or_filt = fes.Or([fes.PropertyIsLike(propertyname='apiso:AnyText',
                                                 literal='*%s*' % val,
                                                 escapeChar='\\',
                                                 wildCard='*',
                                                 singleChar='?') for val in names_dict[var_name]["names"]])
            filter_list = [fes.And([ bbox, or_filt])]
            # try request using multiple filters "and" syntax: [[filter1,filter2]]
            try:
                csw.getrecords2(constraints=filter_list, maxrecords=max_records, esn='full')
            except Exception as e:
                print '\t' + 'ERROR - ' + str(e)
                num_recs.append(np.NaN)
            else:
#                 print '\t' + str(len(csw.records)) + " csw records found"
                num_recs.append(len(csw.records))
            
        results[var_name] = np.array(num_recs)

    # Save the results
    all_data.append(pd.DataFrame(results, index=locations.keys()))
    all_data[-1].name = endpoint
                     
    # Update progress bar
    count += 1
    percent_compelte = (float(count)/float(len(endpoints)))*100
    update_progress_bar(divid, percent_compelte)
#                 # Print titles
#                 for rec, item in csw.records.items():
#                     print(item.title)
        

# <markdowncell>

# #### Let's plot the results in a bar graph

# <codecell>

for df in all_data:
    fig, ax = plt.subplots()
    df.plot(ax=ax, kind="barh", figsize=(10, 8,), title=df.name)
    ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))
    ax.set_xlim([0, max_records])
    ax.set_xlabel('Number of records')

# <markdowncell>

# ### Is the data recent (< 1 month)?
# 
# #### Let's add a temporal extent to the search

# <codecell>

#temporal range - last 28 days and next 3 days (forecast data)
jd_now = dt.datetime.utcnow()
jd_start,  jd_stop = jd_now - dt.timedelta(days=28), jd_now + dt.timedelta(days=3)

start_date = jd_start.strftime('%Y-%m-%d %H:00')
stop_date = jd_stop.strftime('%Y-%m-%d %H:00')

print start_date + ' to ' + stop_date

# <codecell>

# Add a waitbar to monitor status
divid = insert_progress_bar(title='Searching catalogs. Please wait...', color='red')

# Save all of the results in a list of Dataframes
results = {}
recent_data = []

count = 0
# Loop through the csw endpoints
for endpoint in endpoints:
    print '\n' + endpoint

    csw = CatalogueServiceWeb(endpoint, timeout=60)
    # loop through the variables
    for var_name in names_dict:
#         print '\n' + var_name.upper()
        num_recs = []
        for location, bounding_box in locations.iteritems():
#             print location
            # convert User Input into FES filters
            start, stop = fes_date_filter(start_date, stop_date)
            bbox = fes.BBox(bounding_box)

            #use the search name to create search filter
            or_filt = fes.Or([fes.PropertyIsLike(propertyname='apiso:AnyText',
                                                 literal='*%s*' % val,
                                                 escapeChar='\\',
                                                 wildCard='*',
                                                 singleChar='?') for val in names_dict[var_name]["names"]])
            filter_list = [fes.And([ bbox, start, stop, or_filt])]
            # try request using multiple filters "and" syntax: [[filter1,filter2]]
            try:
                csw.getrecords2(constraints=filter_list, maxrecords=max_records, esn='full')
            except Exception as e:
                print '\t' + 'ERROR - ' + str(e)
                num_recs.append(np.NaN)
            else:
#                 print '\t' + str(len(csw.records)) + " csw records found"
                num_recs.append(len(csw.records))
            
        results[var_name] = np.array(num_recs)

    # Save the results
    recent_data.append(pd.DataFrame(results, index=locations.keys()))
    recent_data[-1].name = endpoint
                     
    # Update progress bar
    count += 1
    percent_compelte = (float(count)/float(len(endpoints)))*100
    update_progress_bar(divid, percent_compelte)
#                 # Print titles
#                 for rec, item in csw.records.items():
#                     print(item.title)
        

# <markdowncell>

# #### Once again, let's plot the results in a bar graph

# <codecell>

for df in recent_data:
    fig, ax = plt.subplots()
    df.plot(ax=ax, kind="barh", figsize=(10, 8,), title=df.name, stacked=True)
    ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))
    ax.set_xlim([0, max_records])
    ax.set_xlabel('Number of records')

# <markdowncell>

# ### Reorganize the data by variable name and plot

# <codecell>

# Create a list of Dataframes by variable name
variables_df = []

for var_name in names_dict:
    temp_df = pd.DataFrame()
    for df in recent_data:
        # Loop through the endpoint dataframes and build a data frame for each variable
        test_df = df[np.isfinite(df[var_name])]
        if not test_df.empty:
            temp_df[df.name] = df[var_name]
    variables_df.append(temp_df)
    variables_df[-1].name = var_name

# <codecell>

for df in variables_df:
    fig, ax = plt.subplots()
    
    df.plot(ax=ax, kind="barh", figsize=(10, 8,), title=df.name, colormap="Set1", stacked=True)
    ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))
#     ax.set_xlim([0, max_records])
    ax.set_xlabel('Number of records')

# <markdowncell>

# ### Conclusions
# * The core oceanographic variables are available from numerous CSW endpoints
# * But if you are looking for recent (< 1 month) data, the NGDC and NODC CSW is the best bet
# * Each of the locations tested seemed to have good data coverage except currents in the Arctic

