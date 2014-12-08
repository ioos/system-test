# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <markdowncell>

# ># IOOS System Test: Rapid Deployment gages from USGS
# 
# ###Can we obtain water level data from the rapid deployment gages, deployment for Hurricane Irene? 
# This notebook is based on IOOS System Test: Inundation
# 
# #### Methodology:
# 
# * USGS gage data (ASCII Text Files) obtained from http://ga.water.usgs.gov/flood/hurricane/irene/sites/datafiles/ and 90% of data zipped up for use in the notebook (large files were removed for efficiency)
# * Station data Automatically gets unzipped
# * Process data files (195 stations), and store data in dictionary for access
# * Plot Water level data for the New Jersey area
# * Plot Barometric pressure data for the New Jersey area
# * Plot Gage Locations on a map, overlaid with the Hurricane Irene track line
# * Plot time series of maximum waterlevel
# * Plot locations of maximum waterlevel

# <markdowncell>

# ### import required libraries

# <codecell>

import re
import os
import csv
import uuid
import zipfile

from datetime import datetime

import folium
import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.dates as md
import matplotlib.pyplot as plt

from IPython.display import HTML, Javascript, display

from utilities import css_styles, inline_map
css_styles()

# <markdowncell>

# <div class="success"><strong>Extract Data </strong> - Does the data dir exist, if not extract it </div>

# <codecell>

def unzip(source_filename, dest_dir):
    with zipfile.ZipFile(source_filename) as zf:
        zf.extractall(dest_dir)

# <codecell>

if os.path.isdir("data_files"):
    pass
else:
    print("Data Dir does not exist... Extracting.")
    unzip('sample_data_files.zip', os.getcwd())

# <codecell>

files = os.listdir('data_files') 
print("Water Level Files: %s" % len(files))

# <markdowncell>

# <div class="info"><strong>Process Data </strong> - Read the data files and create a dict of the fields </div>

# <codecell>

def parse_metadata(fname):
    meta_data = {}
    non_decimal = re.compile(r'[^\d.]+')
    fields = {'Sensor location latitude': 'lat',
              'Sensor location longitude': 'lon',
              'Site id =': 'name',
              'Sensor elevation above NAVD 88 =': 'elevation',
              'Barometric sensor site (source of bp) =': 'bp_source',
              'Lowest recordable water elevation is': 'lowest_wl'}
    with open(os.path.join('data_files', fname)) as f:
        content = f.readlines()
        for k, ln in enumerate(content):
            content[k] = ln.strip()
            if content[k].startswith('#'):
                for fd in fields:
                    if fd in content[k]:
                        if fields[fd] == 'name':
                            meta_data[fields[fd]] = content[k].split(fd)[-1]
                        else:
                            val = (content[k].split(fd)[-1])
                            val = float(non_decimal.sub('', val))
                            meta_data[fields[fd]] = val
                        if fields[fd] == 'lon':
                            meta_data[fields[fd]] = -meta_data[fields[fd]]
    return meta_data

# <codecell>

divid = str(uuid.uuid4())

pb = HTML("""
<div style="border: 1px solid black; width:500px">
  <div id="%s" style="background-color:blue; width:0%%">&nbsp;</div>
</div> 
""" % divid)

display(pb)
full_data = {}
for count, fname in enumerate(files):
    meta_data = parse_metadata(fname)
    kw = dict(parse_dates=True, sep='\t', skiprows=29, index_col=0)
    actual_data = pd.read_csv(os.path.join('data_files', fname), **kw)
    full_data[fname] = {'meta': meta_data,
                        'data': actual_data}
    
    percent_complete = ((float(count+1) / float(len(files))) * 100.)
    display(Javascript("$('div#%s').width('%i%%')" %
                       (divid, int(percent_complete))))

# <markdowncell>

# #### Show the available fields from the processed data files

# <codecell>

print("Data Fields: {}, {}, {}".format(actual_data.index.name,
                                       *actual_data.columns))

# <markdowncell>

# # Remove 'Sensor elevation above NAVD 88 (ft)'

# <codecell>

for key, value in full_data.iteritems():
    offset = float(value['meta']['elevation'])
    value['data']['elevation'] -= offset

# <markdowncell>

# ## Plot all Water Level data in the NJ area

# <codecell>

fig, ax = plt.subplots(figsize=(16, 3))

fig.suptitle('Water Elevation', fontsize=14)

for key, value in full_data.iteritems():
    try:
        if 'SSS-NJ' in key:
            df = value['data']                     
            ax.plot(df.index, df['elevation'])
            ax.set_xlabel('Date', fontsize=14)
            ax.set_ylabel('Elevation (ft)', fontsize=14) 
    except Exception as e:
        print(e)

# <markdowncell>

# ## Plot all Pressure data in the NJ area

# <codecell>

fig, ax = plt.subplots(figsize=(16, 3))

fig.suptitle('nearest_barometric_sensor_psi', fontsize=14)

for key, value in full_data.iteritems():
    try:
        if 'SSS-NJ' in key:
            df = value['data']                     
            ax.plot(df.index, df['nearest_barometric_sensor_psi'])
            ax.set_xlabel('Date', fontsize=14)
            ax.set_ylabel('Nearest barometric sensor (psi)', fontsize=14) 
    except Exception as e:
        print(e)

# <markdowncell>

# ## Map the Gage locations

# <codecell>

map = folium.Map(width=800, height=500, location=[30, -73], zoom_start=4)

# Generate the color map for the storms.
color_list = {"Tropical Storm": '#4AD200',
              "Category 1 Hurricane": '#CFD900',
              "Category 2 Hurricane": '#E16400',
              "Category 3 Hurricane": '#ff0000'}


# Add the track line.
with open('track.csv', 'rb') as csvfile:
    spamreader = csv.reader(csvfile, delimiter=',', quotechar='|')
    for row in spamreader:
        lon, lat = row[3], row[2]
        popup = "{} : {} <br> {}".format(row[0], row[1], row[6])
        map.circle_marker([lat, lon], popup=popup,
                          fill_color=color_list[row[6]],
                          radius=10000, line_color='#000000')

# Add the station.
for st in full_data:
    lat = full_data[st]['meta']['lat']
    lon = full_data[st]['meta']['lon']
    map.simple_marker([lat, lon], popup=st, clustered_marker=True)    

map.add_layers_to_map()
inline_map(map)

# <markdowncell>

# ## Generate Plot Of Maximum Water Levels from each gage

# <codecell>

dt, dv = [], []

fig, ax = plt.subplots(figsize=(16, 3))
fig.suptitle('Max Water Level (ft), 2011', fontsize=14)

for key, value in full_data.iteritems():
    df = value['data']                     
    z = df['elevation'].values
    
    idx = np.argmax(z)
    val = z[idx]
    t = df.index[idx]
    
    dt.append(t)
    dv.append(val)
    
    data_dict = {'elevation': dv,
                 'dates': dt}
    
    df = pd.DataFrame(data=data_dict, index=dt, columns=['elevation', 'dates'])   
    
    ax.scatter(df.index, df['elevation'])
    ax.set_xlabel('Date', fontsize=14)
    ax.set_ylabel('Water Level (ft)', fontsize=14) 


ax.set_ylim(0, 20)
ax.set_xlim(md.date2num(datetime(2011, 8, 25, 20)),
            md.date2num(datetime(2011, 8, 30)))
ax.xaxis.set_major_formatter(md.DateFormatter('%B,%d\n%H:%M'))

# <markdowncell>

# ## Generate Plot of maximum water level and its location

# <codecell>

mpl.rcParams['legend.fontsize'] = 10

x, y, zz, bpz = [], [], [], []

fig, ax = plt.subplots(figsize=(10, 10))

for key, value in full_data.iteritems():
    df = value['data']
    z = df['elevation'].values
    bp = df['nearest_barometric_sensor_psi'].values
    lon = value['meta']['lon']
    lat = value['meta']['lat']
    
    idx = np.argmax(z)
    bpz.append(bp[idx])
    zz.append(z[idx])
    x.append(lon)
    y.append(lat)

bpz = np.array(bpz) * 10.
pts = ax.scatter(x, y, c=zz, s=bpz)
ax.set_xlabel('Lon')
ax.set_ylabel('Lat')
title = ("Plot Showing Locations of Maximum Water Level\n"
         "Color coded by Maximum water level (ft)\n"
         "Sized by barometric pressure (psi)")
ax.set_title(title)
cb = fig.colorbar(pts)

