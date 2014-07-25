# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <codecell>

from utilities import css_styles
css_styles()

# <markdowncell>

# # IOOS System Test - Theme 1 - Scenario A - [Description](https://github.com/ioos/system-test/wiki/Development-of-Test-Themes#theme-1-baseline-assessment)
# 
# ## Model Strings
# 
# ## Questions
# 1. What Model records and how many are available via each endpoint?

# <markdowncell>

# ## Q1 - What Model records and how many are available via each endpoint?

# <codecell>

# https://github.com/ioos/system-test/wiki/Service-Registries-and-Data-Catalogs
known_csw_servers = endpoints = ['http://data.nodc.noaa.gov/geoportal/csw',
                                 'https://data.noaa.gov/csw',
                                 'http://cwic.csiss.gmu.edu/cwicv1/discovery',
                                 'http://geoport.whoi.edu/geoportal/csw',
                                 'https://edg.epa.gov/metadata/csw',
                                 'http://www.ngdc.noaa.gov/geoportal/csw',
                                 'http://cmgds.marine.usgs.gov/geonetwork/srv/en/csw',
                                 'http://www.nodc.noaa.gov/geoportal/csw',
                                 'http://cida.usgs.gov/gdp/geonetwork/srv/en/csw',
                                 'http://geodiscover.cgdi.ca/wes/serviceManagerCSW/csw',
                                 'http://geoport.whoi.edu/gi-cat/services/cswiso']

# <codecell>

known_model_strings = ['roms', 'selfe', 'adcirc', 'ncom', 'hycom', 'fvcom', 'pom', 'wrams', 'wrf']

# <markdowncell>

# ### Searching for models via CSW 'keyword'

# <markdowncell>

# #### Construct CSW Filters

# <codecell>

from owslib import fes

model_name_filters = []
for model in known_model_strings:
    title_filter   = fes.PropertyIsLike(propertyname='apiso:Title',   literal='*%s*' % model, wildCard='*')
    subject_filter = fes.PropertyIsLike(propertyname='apiso:Subject', literal='*%s*' % model, wildCard='*')
    model_name_filters.append(fes.Or([title_filter, subject_filter]))

# <markdowncell>

# #### Query each CSW catalog for revery model_name_filter constructed above

# <codecell>

from owslib.csw import CatalogueServiceWeb

model_results = []

for x in range(len(model_name_filters)):
    model_name          = known_model_strings[x]
    single_model_filter = model_name_filters[x]
    for url in known_csw_servers:
        try:
            csw = CatalogueServiceWeb(url, timeout=20)
            csw.getrecords2(constraints=[single_model_filter], maxrecords=1000, esn='full')
            for record, item in csw.records.items():
                for d in item.references:
                    result = dict(model=model_name,
                                  scheme=d['scheme'],
                                  url=d['url'],
                                  server=url)
                    model_results.append(result)
        except BaseException as e:
            print "- FAILED: %s - %s" % (url, e.msg)

# <markdowncell>

# #### Load results into a Pandas DataFrame

# <codecell>

import pandas as pd
from IPython.display import HTML

df = pd.DataFrame(model_results)
df.head()

# <markdowncell>

# #### Total number of services

# <codecell>

total_services = pd.DataFrame(df.groupby("scheme").size(), columns=("Total",))
HTML(total_services.to_html())

# <markdowncell>

# #### The number of service types for each model type

# <codecell>

model_service_summary = pd.DataFrame(df.groupby(["model", "scheme"], sort=True).size(), columns=("Total",))
HTML(model_service_summary.to_html())

# <markdowncell>

# #### Models per CSW server

# <codecell>

records_per_csw = pd.DataFrame(df.groupby(["model", "server", "scheme"]).size(), columns=("Total",))
HTML(records_per_csw.to_html())

# <codecell>


