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
# * Data Automatically gets unzipped
# * Process data files, and store data in dictionary for access
# * Plot Water level data for the New Jersey area
# * Plot Barometric pressure data for the New Jersey area
# * Plot Gage Locations on a map, overlaid with the Hurricane Irene track line
# * Plot time series of maximum waterlevel
# * Plot locations of maximum waterlevel

# <markdowncell>

# ### import required libraries

# <codecell>

from bs4 import BeautifulSoup
import requests
import re
import csv
import os,zipfile
import pandas as pd
import json
import sys
import uuid
from netCDF4 import date2num
from IPython.display import HTML, Javascript, display
import folium
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as md
from utilities import (css_styles,inline_map)
css_styles()

# <markdowncell>

# <div class="success"><strong>Extract Data </strong> - Does the data dir exist, if not extract it </div>
# 

# <codecell>

def unzip(source_filename, dest_dir):
    with zipfile.ZipFile(source_filename) as zf:
        zf.extractall(dest_dir)

# <codecell>

if (os.path.isdir("./data_files/")):
    pass
else:
    print "Data Dir does not exist...extracting"
    unzip('sample_data_files.zip','./')

# <codecell>

files = os.listdir('./data_files/') 
print "Water Level Files:",len(files)
non_decimal = re.compile(r'[^\d.]+')

# <markdowncell>

# <div class="info"><strong>Process Data </strong> - Read the data files and create a dict of the fields </div>

# <codecell>

divid = str(uuid.uuid4())

pb = HTML(
"""
<div style="border: 1px solid black; width:500px">
  <div id="%s" style="background-color:blue; width:0%%">&nbsp;</div>
</div> 
""" % divid)

count =0
full_data = {}
display(pb)
for fi,file_name in enumerate(files):
    #print count,file_name
    count+=1

    actual_data = {'dates':[]}
    with open('./data_files/'+file_name) as f:
        content = f.readlines()
        
        titles_set = True
        titles = ['dates']        
        
        meta_data = {}
        
        
        fields = {
                  'Sensor location latitude':'lat',
                  'Sensor location longitude':'lon',
                  'Site id =':'name',
                  'Sensor elevation above NAVD 88 =':'elevation',
                  'Barometric sensor site (source of bp) =':'bp_source',
                  'Lowest recordable water elevation is':'lowest_wl'
                  }
        
        for i,ln in enumerate(content):            
            content[i] = ln.strip()
            if content[i].startswith('#'):
                for f in fields:
                    #search inside the array element
                    if f in content[i]:
                        if fields[f] == 'name':
                            meta_data[fields[f]] = content[i].split(f)[-1]
                        else:                                
                            val = (content[i].split(f)[-1])
                            meta_data[fields[f]] = float(non_decimal.sub('', val))
                            
                            if fields[f] =='lon':
                                meta_data[fields[f]] = -meta_data[fields[f]]

            else: 
                try:
                    data_row = content[i].split('\t')

                    if len(data_row[0])>1:
                        #print the data looks to be ok-ish                    
                        if titles_set:                                                
                            titles_set = False
                            for t in data_row:
                                if not 'date_time' in t:
                                    titles.append(t)                            
                                    actual_data[t]=[]

                        else:
                            if '.' in data_row:
                                data_row[0] = data_row[0].split('.')[0]
                            
                            try:
                                dt = datetime.datetime.strptime(data_row[0], '%m-%d-%Y %H:%M:%S')
                                actual_data['dates'].append(dt) 
                            except:
                                dt = datetime.datetime.strptime(data_row[0], '%m-%d-%Y %H:%M:%S.%f')
                                actual_data['dates'].append(dt)                                 

                            for i in range(1,len(data_row)):
                                try:
                                    val = data_row[i]                            
                                    actual_data[titles[i]].append(float(val))
                                except Exception, e:
                                    actual_data[titles[i]].append(numpy.nan)  
                except:
                    print 'error:',data_row
                    break

        full_data[file_name] = {'meta': meta_data,'data': actual_data}
        percent_complete = ((float(fi+1)/float(len(files)))*100.)
        display(Javascript("$('div#%s').width('%i%%')" % (divid, int(percent_complete))))

# <markdowncell>

# #### Show the available fields from the processed data files

# <codecell>

print "Data Fields:",titles

# <codecell>

#remove 'Sensor elevation above NAVD 88 (ft)'     
for i in range(0, len(full_data.keys())):
    data = full_data[full_data.keys()[i]]['data']     
    meta_elev = full_data[full_data.keys()[i]]['meta']['elevation']                            
    data['elevation'] = np.array(data['elevation']) - float(meta_elev)            

# <markdowncell>

# ## Plot all Water Level data in the NJ area

# <codecell>

fig = plt.figure(figsize=(16, 3))
fig.suptitle('Water Elevation', fontsize=14)
for i in range(0, len(full_data.keys())):
    num = i
    try:
        if 'SSS-NJ' in full_data.keys()[num]:            
            data = full_data[full_data.keys()[num]]['data']                     
            df = pd.DataFrame(data=data,index=data['dates'],columns = titles )    
            plt.plot(df.index, df[titles[1]])
            plt.xlabel('Date', fontsize=14)
            plt.ylabel(titles[1]+' (ft)', fontsize=14) 
    except Exception, e:
        print e
        pass

# <markdowncell>

# ## Plot all Pressure data in the NJ area

# <codecell>

fig = plt.figure(figsize=(16, 3))
fig.suptitle(titles[2], fontsize=14)
for i in range(0, len(full_data.keys())):
    num = i
    try:
        if 'SSS-NJ' in full_data.keys()[num]:
            #print full_data[full_data.keys()[num]]['meta']
            data = full_data[full_data.keys()[num]]['data']                        
            df = pd.DataFrame(data=data,index=full_data[full_data.keys()[num]]['data']['dates'],columns = titles )    
            plt.plot(df.index, df[titles[2]])

            plt.xlabel('Date', fontsize=14)
            plt.ylabel(titles[2], fontsize=14) 
    except Exception, e:
        print e
        pass

# <markdowncell>

# ## Map the Gage locations

# <codecell>

map = folium.Map(width=800,height=500,location=[30, -73], zoom_start=4)

#generate the color map for the storms
color_list = {"Tropical Storm":'#4AD200',
              "Category 1 Hurricane":'#CFD900',
              "Category 2 Hurricane":'#E16400',
              "Category 3 Hurricane":'#ff0000'}


#add the track line
with open('track.csv', 'rb') as csvfile:
    spamreader = csv.reader(csvfile, delimiter=',', quotechar='|')
    for row in spamreader:
        lat = row[2]
        lon = row[3]
        popup = row[0]+" : "+row[1] + "<br>"+ row[6]        
        map.circle_marker([lat, lon], popup=popup, fill_color=color_list[row[6]], radius=10000, line_color='#000000')

#add the station
for st in full_data:
    lat =  full_data[st]['meta']['lat']
    lon = full_data[st]['meta']['lon']
    map.simple_marker([lat, lon], popup=st,clustered_marker=True)    
map.add_layers_to_map()

inline_map(map)  

# <markdowncell>

# ## Generate Plot Of Maximum Water Levels from each gage

# <codecell>

dt = []
dv = []

fig = plt.figure(figsize=(16, 3))
fig.suptitle('Max Water Level (ft), 2011', fontsize=14)
for i in range(0, len(full_data.keys())):
    num = i
    z = np.array(full_data[full_data.keys()[num]]['data']['elevation'])
    val = np.max(z)
    idx = np.argmax(z)
    t = np.array(full_data[full_data.keys()[num]]['data']['dates'])[idx]
    
    dt.append(t)
    dv.append(val)
    
    data_dict = {'elevation':dv,'dates':dt}
    
    df = pd.DataFrame(data=data_dict,index=dt,columns=['elevation','dates'])   
    
    plt.scatter(df.index,df['elevation'])
    plt.xlabel('Date', fontsize=14)
    plt.ylabel('Water Level'+' (ft)', fontsize=14) 


ax = plt.gca()
plt.ylim((0,20))
ax.xaxis.set_major_formatter(md.DateFormatter('%B,%d\n%H:%M'))

# <markdowncell>

# ## Generate Plot of maximum water level and its location

# <codecell>

mpl.rcParams['legend.fontsize'] = 10

x = []
y = []
zz = []
bpz = []

fig = plt.figure(figsize=(10, 10))
ax = fig.add_subplot(111)

for i in range(0, len(full_data.keys())):
    num = i

    z = np.array(full_data[full_data.keys()[num]]['data']['elevation'])
    bp = np.array(full_data[full_data.keys()[num]]['data']['nearest_barometric_sensor_psi'])
    lat = full_data[full_data.keys()[num]]['meta']['lat']
    lon = full_data[full_data.keys()[num]]['meta']['lon']
    val = np.max(z)    
    idx = np.argmax(z)
    
    bpz.append(bp[idx])
    zz.append(val)    
    x.append(lon)
    y.append(lat)
    
bpz = np.array(bpz)*10
pts = ax.scatter(x, y, c=zz, s=bpz)
ax.set_xlabel('Lon')
ax.set_ylabel('Lat')
ax.set_title("Plot Showing Locations of Maximum Water Level\nColor coded by Maximum water level (ft)\n Sized by barometric pressure (psi)")
cb = fig.colorbar(pts)
plt.show()

# <codecell>


