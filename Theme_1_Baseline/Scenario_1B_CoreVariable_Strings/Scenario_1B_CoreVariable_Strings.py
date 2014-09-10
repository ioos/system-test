# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <codecell>

from utilities import css_styles
css_styles()

# <markdowncell>

# # IOOS System Test - Theme 1 - Scenario B - [Description](https://github.com/ioos/system-test/wiki/Development-of-Test-Themes#theme-1-baseline-assessment)
# 
# ## Core Variable Strings
# 
# This notebook looks at the IOOS core variables and uses the Marine Metadata Interoperability SPARQL endpoint to convert them to CF Standard names.  Each IOOS CSW server is then queryied for CF standard name that is associated with an IOOS Core Variable.
# 
# ## Questions
# 1. Using a list of Core IOOS Variables and the MMI SPARQL service, can we search and quantify records from CSW endpoints that relate to core variables?

# <markdowncell>

# #### Get a list of the IOOS Core Variables from MMI

# <codecell>

# Using RDF
from rdflib import Graph, Literal, BNode, Namespace, RDF, URIRef
g = Graph()
g.load("http://mmisw.org/ont/ioos/core_variable")
core_var_uri      = URIRef('http://mmisw.org/ont/ioos/core_variable/Core_Variable')
core_var_name_uri = URIRef('http://mmisw.org/ont/ioos/core_variable/name')
core_var_def_uri  = URIRef('http://mmisw.org/ont/ioos/core_variable/definition')

core_variables = []
for cv in g.subjects(predicate=RDF.type, object=core_var_uri):
    name = g.value(subject=cv, predicate=core_var_name_uri).value
    definition = g.value(subject=cv, predicate=core_var_def_uri).value
    core_variables.append((name, definition))

# <codecell>

import pandas as pd
core_variables_names = [x for x,y in core_variables]
pd.DataFrame.from_records(core_variables, columns=("Name", "Definition",))

# <markdowncell>

# <div class="error"><strong>Programmatic access to Core Variables</strong> - This isn't straight forward and should be abstracted into a library. See: https://github.com/ioos/system-test/issues/128</div>

# <markdowncell>

# #### Query MMI for CF standard names related to the IOOS Core Variables

# <codecell>

from SPARQLWrapper import SPARQLWrapper, JSON
sparql = SPARQLWrapper("http://mmisw.org/sparql")

query = """
PREFIX ioos: <http://mmisw.org/ont/ioos/parameter/>
SELECT DISTINCT ?cat ?parameter ?property ?value 
WHERE {?parameter a ioos:Parameter .
       ?parameter ?property ?value .
       ?cat skos:narrowMatch ?parameter .
       FILTER  (regex(str(?property), "Match", "i") && regex(str(?value), "cf", "i") )
      } 
ORDER BY ?cat ?parameter
"""
    
sparql.setQuery(query)
sparql.setReturnFormat(JSON)
j = sparql.query().convert()

cf_standard_uris  = list(set([ x["value"]["value"] for x in j.get("results").get("bindings") ]))
cf_standard_names = map(lambda x: x.split("/")[-1], cf_standard_uris)
pd.DataFrame.from_records(zip(cf_standard_names, cf_standard_uris), columns=("CF Name", "CF URI",))

# <markdowncell>

# ### Searching CSW servers on variable names

# <codecell>

# https://github.com/ioos/system-test/wiki/Service-Registries-and-Data-Catalogs
known_csw_servers = ['http://data.nodc.noaa.gov/geoportal/csw',
                     'http://www.nodc.noaa.gov/geoportal/csw',
                     'http://www.ngdc.noaa.gov/geoportal/csw',
                     'http://cwic.csiss.gmu.edu/cwicv1/discovery',
                     'http://geoport.whoi.edu/geoportal/csw',
                     'https://edg.epa.gov/metadata/csw',
                     'http://cmgds.marine.usgs.gov/geonetwork/srv/en/csw',
                     'http://cida.usgs.gov/gdp/geonetwork/srv/en/csw',
                     'http://geodiscover.cgdi.ca/wes/serviceManagerCSW/csw',
                     'http://geoport.whoi.edu/gi-cat/services/cswiso',
                     'https://data.noaa.gov/csw',
                     ]

# <markdowncell>

# #### Subset which variables we should query by

# <codecell>

# Query on Waves
variables_to_query = [ x for x in cf_standard_names if "sea_surface_height" in x ]
custom_variables   = [u"sea_surface_height", u"sea_surface_elevation"]

variables_to_query += custom_variables
variables_to_query

# <markdowncell>

# <div class="error"><strong>Missing CF Standard Names</strong> - "sea_surface_height" and "sea_surface_elevation" are valid CF Aliases but are not returned by MMI when running the SPARQL query.  We added them here manually. See: https://github.com/ioos/system-test/issues/129</div>

# <markdowncell>

# #### Construct CSW Filters

# <codecell>

from owslib import fes

cf_name_filters = []
for cf_name in variables_to_query:
    text_filter   = fes.PropertyIsLike(propertyname='apiso:AnyText', literal="*%s*" % cf_name, wildCard='*')
    cf_name_filters.append(text_filter)

# <markdowncell>

# #### Query each CSW catalog for the cf_name_filters constructed above

# <codecell>

from owslib.csw import CatalogueServiceWeb
from utilities import normalize_service_urn

var_results = []

for x in range(len(cf_name_filters)):
    var_name          = variables_to_query[x]
    single_var_filter = cf_name_filters[x]
    for url in known_csw_servers:
        try:
            csw = CatalogueServiceWeb(url, timeout=20)
            csw.getrecords2(constraints=[single_var_filter], maxrecords=1000, esn='full')
            for record, item in csw.records.items():
                for d in item.references:
                    result = dict(variable=var_name,
                                  scheme=normalize_service_urn(d['scheme']),
                                  url=d['url'],
                                  server=url,
                                  title=record.title())
                    var_results.append(result)
        except BaseException, e:
            print "- FAILED: %s - %s" % (url, e)

# <markdowncell>

# <div class="error"><strong>Paginating CSW Records</strong> - Some servers have a maximum amount of records you can retrieve at once. See: https://github.com/ioos/system-test/issues/126</div>

# <markdowncell>

# #### Load results into a Pandas DataFrame

# <codecell>

%matplotlib inline
import pandas as pd
pd.set_option('display.max_columns', 20)
pd.set_option('display.max_rows', 500)

from IPython.display import HTML

df = pd.DataFrame(var_results)
df = df.drop_duplicates()

# <markdowncell>

# #### Results by variable

# <codecell>

by_variable = pd.DataFrame(df.groupby("variable").size(), columns=("Number of services",))
by_variable.sort('Number of services', ascending=False).plot(kind="barh", figsize=(10,8,))

# <markdowncell>

# #### The number of service types for each variable

# <codecell>

import math

var_service_summary = pd.DataFrame(df.groupby(["variable", "scheme"], sort=True).size(), columns=("Number of services",))
#HTML(model_service_summary.to_html())
var_service_plotter = var_service_summary.unstack("variable")
var_service_plot = var_service_plotter.plot(kind='barh', subplots=True, figsize=(12,120), sharey=True)

# <markdowncell>

# #### Variabes per CSW server

# <codecell>

variables_per_csw = pd.DataFrame(df.groupby(["variable", "server"]).size(), columns=("Number of services",))
#HTML(records_per_csw.to_html())
var_csw_plotter = variables_per_csw.unstack("variable")
var_csw_plot = var_csw_plotter.plot(kind='barh', subplots=True, figsize=(12,30,), sharey=True)

# <markdowncell>

# #### Variables per CSW server

# <codecell>

csws_per_variable = pd.DataFrame(df.groupby(["variable", "server"]).size(), columns=("Number of variables",))
#HTML(records_per_csw.to_html())
csw_var_plotter = csws_per_variable.unstack("server")
csw_var_plot = csw_var_plotter.plot(kind='barh', subplots=True, figsize=(12,30,), sharey=True)

# <codecell>


