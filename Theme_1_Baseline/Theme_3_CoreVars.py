
# coding: utf-8

## Theme 3: Baseline Assessment of IOOS Core Biological Variables

# This notebook simply looks at the IOOS core biological variables (fish, phytoplankton, zooplankton) and looks broadly to first see if those terms are mapped to other vocabularies using Marine Metadata Interoperability vocabularies in order to create a master list of biological core variable terms that is then piped into a cell that counts the number of records that can be accessed via each data catalog. 

# In[1]:

# This cell sets the needed modules.  While the modules listed here may not
#  all be needed for this notebook, I've been using this list accross a few
#  different notebooks

import lxml
import pykml
from pykml import parser
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
import json
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
import SPARQLWrapper
from SPARQLWrapper import SPARQLWrapper, JSON
from SPARQLWrapper import SPARQLWrapper2
from zipfile import ZipFile
import xml.sax, xml.sax.handler

def service_urls(records,service_string='urn:x-esri:specification:ServiceType:odp:url'):
    urls=[]
    for key,rec in records.iteritems():
        #create a generator object, and iterate through it until the match is found
        #if not found, gets the default value (here "none")
        url = next((d['url'] for d in rec.references if d['scheme'] == service_string), None)
        if url is not None:
            urls.append(url)
    return urls


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

#These are lists of strings will use as a starting point for understanding 
#  available core IOOS Biological Variables available via the catalogs of 
#  interest

var_key = ['fish','phytoplankton','zooplankton']


# In[11]:

#This Cell uses MMI Services in order to map the broad variable terms to available terms within the IOOS system so that when searching endpoints for biological data, we will find any records that might have different terms

sparql = SPARQLWrapper("http://mmisw.org/sparql")

Q = []
RecVars = []
for K in var_key:
    A = """
PREFIX ioos: <http://mmisw.org/ont/ioos/parameter/>
SELECT DISTINCT ?parameter ?definition ?unit ?property ?value 
WHERE {?parameter a ioos:Parameter .
       ?parameter ?property ?value .
       ?parameter ioos:Term ?term . 
       ?parameter ioos:Definition ?definition . 
       ?parameter ioos:Units ?unit .
       FILTER (regex(str(?property), "(exactMatch|closeMatch|broadMatch)", "i") && regex(str(?value), """ + '"'+K+'"' +', "i") )'   
    B = """
      } 
ORDER BY ?parameter
"""
    queryStringLoop = A+B
    sparql.setQuery(queryStringLoop)
    sparql.setReturnFormat(JSON)
    j = sparql.query().convert()
    Q.append(j)
    for jt in j:
        j["head"]["vars"]
        k = j['results']
        k1 = k['bindings']
        for k in k1:
            k2 = k['value']
            k3 = k2['value']
            k4 = k3[34:]
            k4list = k4.encode('ascii') 
            RecVars.append(k4list)
Q1 = []
RecVars_core = []
for K in var_key:
    A = """
PREFIX ioos: <http://mmisw.org/ont/ioos/map_ioos_ioos>
SELECT DISTINCT ?parameter ?definition ?unit ?property ?value 
WHERE {?parameter a ioos:Parameter .
       ?parameter ?property ?value .
       ?parameter ioos:Term ?term . 
       ?parameter ioos:Definition ?definition . 
       ?parameter ioos:Units ?unit .
       FILTER (regex(str(?property), "(exactMatch|closeMatch|broadMatch)", "i") && regex(str(?value), """ + '"'+K+'"' +', "i") )'   
    B = """
      } 
ORDER BY ?parameter
"""
    queryStringLoop = A+B
    sparql.setQuery(queryStringLoop)
    sparql.setReturnFormat(JSON)
    j = sparql.query().convert()
    Q1.append(j)
    for jt in j:
        j["head"]["vars"]
        k = j['results']
        k1 = k['bindings']
        for k in k1:
            k2 = k['value']
            k3 = k2['value']
            k4 = k3[34:]
            k4list = k4.encode('ascii') 
            RecVars_core.append(k4list)

Q2 = []
RecVars_bio = []
for K in var_key:
    A = """
PREFIX ioos: <http://mmisw.org/ont/mmi/resourcetype/parameter>
SELECT DISTINCT ?parameter ?definition ?unit ?property ?value 
WHERE {?parameter a ioos:Parameter .
       ?parameter ?property ?value .
       ?parameter ioos:Term ?term . 
       ?parameter ioos:Definition ?definition . 
       ?parameter ioos:Units ?unit .
       FILTER (regex(str(?property), "(exactMatch|closeMatch|broadMatch)", "i") && regex(str(?value), """ + '"'+K+'"' +', "i") )'   
    B = """
      } 
ORDER BY ?parameter
"""
    queryStringLoop = A+B
    sparql.setQuery(queryStringLoop)
    sparql.setReturnFormat(JSON)
    j = sparql.query().convert()
    Q2.append(j)
    for jt in j:
        j["head"]["vars"]
        k = j['results']
        k1 = k['bindings']
        for k in k1:
            k2 = k['value']
            k3 = k2['value']
            k4 = k3[34:]
            k4list = k4.encode('ascii') 
            RecVars_bio.append(k4list)
            
Q3 = []
RecVars_aqua1 = []
for K in var_key:
    A = """
PREFIX ioos: <http://mmisw.org/ont/CUAHSI/AquaBiologicalCompound>
SELECT DISTINCT ?parameter ?definition ?unit ?property ?value 
WHERE {?parameter a ioos:Parameter .
       ?parameter ?property ?value .
       ?parameter ioos:Term ?term . 
       ?parameter ioos:Definition ?definition . 
       ?parameter ioos:Units ?unit .
       FILTER (regex(str(?property), "(exactMatch|closeMatch|broadMatch)", "i") && regex(str(?value), """ + '"'+K+'"' +', "i") )'   
    B = """
      } 
ORDER BY ?parameter
"""
    queryStringLoop = A+B
    sparql.setQuery(queryStringLoop)
    sparql.setReturnFormat(JSON)
    j = sparql.query().convert()
    Q3.append(j)
    for jt in j:
        j["head"]["vars"]
        k = j['results']
        k1 = k['bindings']
        for k in k1:
            k2 = k['value']
            k3 = k2['value']
            k4 = k3[34:]
            k4list = k4.encode('ascii') 
            RecVars_aqua1.append(k4list)

Q4 = []
RecVars_aqua2 = []
for K in var_key:
    A = """
PREFIX ioos: <http://mmisw.org/ont/CUAHSI/AquaBioCore>
SELECT DISTINCT ?parameter ?definition ?unit ?property ?value 
WHERE {?parameter a ioos:Parameter .
       ?parameter ?property ?value .
       ?parameter ioos:Term ?term . 
       ?parameter ioos:Definition ?definition . 
       ?parameter ioos:Units ?unit .
       FILTER (regex(str(?property), "(exactMatch|closeMatch|broadMatch)", "i") && regex(str(?value), """ + '"'+K+'"' +', "i") )'   
    B = """
      } 
ORDER BY ?parameter
"""
    queryStringLoop = A+B
    sparql.setQuery(queryStringLoop)
    sparql.setReturnFormat(JSON)
    j = sparql.query().convert()
    Q4.append(j)
    for jt in j:
        j["head"]["vars"]
        k = j['results']
        k1 = k['bindings']
        for k in k1:
            k2 = k['value']
            k3 = k2['value']
            k4 = k3[34:]
            k4list = k4.encode('ascii') 
            RecVars_aqua2.append(k4list)
            
RecVarsMerg = RecVars+RecVars_core+RecVars_bio+RecVars_aqua1+RecVars_aqua1+var_key
print RecVarsMerg


# In[10]:

#This cell searches the endpoints using the revised list of variable strings from the previous cell and returns basic information on the number of records and the titles of data sets available via each endpoint

variables1 = []
records1 = []
titles1 = []
lenrecords1 = []
lentitles1 = []

for endpoint in endpoints[:3]:
    csw = CatalogueServiceWeb(endpoint,timeout=60)
    for v in RecVarsMerg[:2]:
        try:
            csw.getrecords(keywords = [v], maxrecords = 60, esn = 'full')
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
df = DataFrame(data = zipvar1, columns = ['endpoints','records1','lenrecords1', 'titles1','lentitles1'])
df.head()


# ##Conclusions
# 
# On first pass, it looks like core biological variable terms 
