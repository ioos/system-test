
# coding: utf-8

# Outline of Notebook Elements:
# *  Theme Title
# *  Questions
# *  DISCOVERY Process (code and narrative)
# *  ACCESS Process (code and narrative)
# *  USE Process (code and narrative)
# *  Results and Conclusions (narrative)

## Theme: Baseline Question: What Model records and how many are available via each endpoint?

# In[12]:

import pandas as pd
from pandas import Series, DataFrame
import numpy as np
from numpy import random
import matplotlib.pyplot as plt
import matplotlib.cbook as cbook
import csv
import re
import cStringIO
import urllib2
import parser
import pdb
#import iris
import random
import datetime as dt
from datetime import datetime
from pylab import *
from owslib.csw import CatalogueServiceWeb
from owslib.wms import WebMapService
from owslib.csw import CatalogueServiceWeb
from owslib.sos import SensorObservationService
from owslib.etree import etree
from owslib import fes
import netCDF4

#This is a collection of lists that we will need to examine Catalogs 
endpoints = ['http://data.nodc.noaa.gov/geoportal/csw','https://data.noaa.gov/csw','http://cwic.csiss.gmu.edu/cwicv1/discovery','http://geoport.whoi.edu/geoportal/csw','https://edg.epa.gov/metadata/csw','http://www.ngdc.noaa.gov/geoportal/csw','http://cmgds.marine.usgs.gov/geonetwork/srv/en/csw','http://www.nodc.noaa.gov/geoportal/csw','http://cida.usgs.gov/gdp/geonetwork/srv/en/csw','http://geodiscover.cgdi.ca/wes/serviceManagerCSW/csw', 'http://geoport.whoi.edu/gi-cat/services/cswiso']

model_strings = ['roms','selfe','adcirc','ncom','hycom','fvcom']


# In[2]:

#This cell lists catalog endpoints.  As CSW's are discovered within the larger
#    IOOS Umbrealla, this list is updated by the IOOS Program Office here:
#    https://github.com/ioos/system-test/wiki/Service-Registries-and-Data-Catalogs

#endpoint = 'http://data.nodc.noaa.gov/geoportal/csw'  # NODC Geoportal: collection level
#endpoint = 'http://geodiscover.cgdi.ca/wes/serviceManagerCSW/csw'  # NRCAN 
#endpoint = 'http://geoport.whoi.edu/gi-cat/services/cswiso' # USGS Woods Hole GI_CAT
#endpoint = 'http://cida.usgs.gov/gdp/geonetwork/srv/en/csw' # USGS CIDA Geonetwork
#endpoint = 'http://www.nodc.noaa.gov/geoportal/csw'   # NODC Geoportal: granule level
#endpoint = 'http://cmgds.marine.usgs.gov/geonetwork/srv/en/csw'  # USGS Coastal & Marine Program Geonetwork
#endpoint = 'http://www.ngdc.noaa.gov/geoportal/csw' # NGDC Geoportal
#endpoint = 'http://www.ncdc.noaa.gov/cdo-web/api/v2/' #NCDC CDO Web Services
#endpoint = 'http://geo.gov.ckan.org/csw' #CKAN Testing Site for new Data.gov
#endpoint = 'https://edg.epa.gov/metadata/csw' #EPA
#endpoint = 'http://geoport.whoi.edu/geoportal/csw' #WHOI Geoportal
#endpoint = 'http://cwic.csiss.gmu.edu/cwicv1/discovery' #CWIC
#endpoint = 'http://portal.westcoastoceans.org/connect/' #West Coast Governors Alliance (Based on ESRI Geoportal back end
#print out version
#endpoint = 'http://gcmdsrv.gsfc.nasa.gov/csw' #NASA's Global Change Master Directory (GCMD) CSW Service (Requires Authorization)
#endpoint = 'http://gcmdsrv3.gsfc.nasa.gov/csw' #NASA's Global Change Master Directory (GCMD) CSW Service (Requires Authorization)
#endpoint = 'https://data.noaa.gov/csw' #data.noaa.gov csw

endpoints = ['http://www.nodc.noaa.gov/geoportal/csw',
             'http://www.ngdc.noaa.gov/geoportal/csw',
             'http://catalog.data.gov/csw-all',
             'http://cwic.csiss.gmu.edu/cwicv1/discovery',
             'http://geoport.whoi.edu/geoportal/csw',
             'https://edg.epa.gov/metadata/csw',
             'http://cmgds.marine.usgs.gov/geonetwork/srv/en/csw',
             'http://cida.usgs.gov/gdp/geonetwork/srv/en/csw',
             'http://geodiscover.cgdi.ca/wes/serviceManagerCSW/csw', 
             'http://geoport.whoi.edu/gi-cat/services/cswiso']


# In[3]:

def service_urls(records,service_string='urn:x-esri:specification:ServiceType:odp:url'):
    urls=[]
    for key,rec in records.iteritems():
        #create a generator object, and iterate through it until the match is found
        #if not found, gets the default value (here "none")
        url = next((d['url'] for d in rec.references if d['scheme'] == service_string), None)
        if url is not None:
            urls.append(url)
    return urls



# In[11]:

#This cell examines and provides information on the number of model records
#   available via each catalog endpoint
records1 = []
records2 = []
titles1 = []
titles2=[]
lenrecords1 = []
lentitles1 = []

for endpoint in endpoints:    
    csw = CatalogueServiceWeb(endpoint,timeout=100)
    for model_string in model_strings:
        try:
            csw.getrecords(keywords = [model_string], maxrecords = 100)
            records1.append(csw.results)
        except Exception, ex1:
            records1.append('Error')
        try:
            for rec in csw.records:    
                titles1.append(csw.records[rec].title)
        except Exception, ex1:    
                titles1.append('Error') 
    lentitles1.append(len(titles1[-1]))
    lenrecords1.append(len(records1[-1]))

zipvar1 = zip(endpoints, records1,lenrecords1, titles1,lentitles1)
df = DataFrame(data = zipvar1, columns = ['endpoints', 'records1','lenrecords1', 'titles1','lentitles1'])
df.head()


# In[ ]:



