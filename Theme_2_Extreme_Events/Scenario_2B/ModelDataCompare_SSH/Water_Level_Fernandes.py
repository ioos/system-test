
# coding: utf-8

# ### This notebook generates the map and table HTMLs for the SECOORA Model vs Observed Sea Surface Height
# 
# Based on IOOS system-test [notebook](http://nbviewer.ipython.org/github/ioos/system-test/blob/master/Theme_2_Extreme_Events/Scenario_2A/ModelDataCompare_Inundation/Water_Level_Signell.ipynb).

# In[ ]:

import os
import time

import iris
import pyoos
import owslib

from utilities import timeit

start_time = time.time()


# In[ ]:

import pytz
from datetime import datetime, timedelta

from utilities import CF_names

# Choose the date range.
stop = datetime(2014, 7, 7, 12)

stop = stop.replace(tzinfo=pytz.utc)
start = stop - timedelta(days=7)

# SECOORA region (NC, SC GA, FL).
bbox = [-87.40, 24.25, -74.70, 36.70]

# CF-names to look for (Sea Surface Height).
name_list = CF_names['water level']


# In[ ]:

import logging as log
reload(log)

fmt = '{:*^64}'.format
log.captureWarnings(True)
LOG_FILENAME = 'log'
LOG_FILENAME = os.path.join(LOG_FILENAME)
log.basicConfig(filename=LOG_FILENAME,
                filemode='w',
                format='%(asctime)s %(levelname)s: %(message)s',
                datefmt='%I:%M:%S',
                level=log.INFO,
                stream=None)

log.info(fmt(' Run information '))
log.info('Run date: {:%Y-%m-%d %H:%M:%S}'.format(datetime.utcnow()))
log.info('Download start: {:%Y-%m-%d %H:%M:%S}'.format(start))
log.info('Download stop: {:%Y-%m-%d %H:%M:%S}'.format(stop))
log.info('Bounding box: {0:3.2f}, {1:3.2f},'
         '{2:3.2f}, {3:3.2f}'.format(*bbox))
log.info(fmt(' Software version '))
log.info('Iris version: {}'.format(iris.__version__))
log.info('owslib version: {}'.format(owslib.__version__))
log.info('pyoos version: {}'.format(pyoos.__version__))


# In[ ]:

from owslib import fes
from utilities import fes_date_filter

kw = dict(wildCard='*',
          escapeChar='\\',
          singleChar='?',
          propertyname='apiso:AnyText')

or_filt = fes.Or([fes.PropertyIsLike(literal=('*%s*' % val), **kw)
                  for val in name_list])

not_filt = fes.Not([fes.PropertyIsLike(literal='*Averages*', **kw)])

begin, end = fes_date_filter(start, stop)
filter_list = [fes.And([fes.BBox(bbox), begin, end, or_filt, not_filt])]


# In[ ]:

from owslib.csw import CatalogueServiceWeb

endpoint = 'http://www.ngdc.noaa.gov/geoportal/csw'
csw = CatalogueServiceWeb(endpoint, timeout=60)
csw.getrecords2(constraints=filter_list, maxrecords=1000, esn='full')

log.info(fmt(' Catalog information '))
log.info("URL: {}".format(endpoint))
log.info("CSW version: {}".format(csw.version))
log.info("Number of datasets available: {}".format(len(csw.records.keys())))


# In[ ]:

from utilities import service_urls

dap_urls = service_urls(csw.records, service='odp:url')
sos_urls = service_urls(csw.records, service='sos:url')

log.info(fmt(' CSW URLs '))
for rec, item in csw.records.items():
    log.info('{}'.format(item.title))

log.info(fmt(' DAP URLs '))
for url in dap_urls:
    log.info('{}.html'.format(url))

log.info(fmt(' SOS URLs '))
for url in sos_urls:
    log.info('{}'.format(url))


# In[ ]:

from pyoos.collectors.coops.coops_sos import CoopsSos

collector = CoopsSos()
sos_name = 'water_surface_height_above_reference_datum'

datum = 'NAVD'
collector.set_datum(datum)
collector.end_time = stop
collector.start_time = start
collector.variables = [sos_name]

ofrs = collector.server.offerings
title = collector.server.identification.title
log.info(fmt(' Collector offerings '))
log.info('{}: {} offerings'.format(title, len(ofrs)))


# In[ ]:

from pandas import read_csv
from utilities import sos_request

params = dict(observedProperty=sos_name,
              eventTime=start.strftime('%Y-%m-%dT%H:%M:%SZ'),
              featureOfInterest='BBOX:{0},{1},{2},{3}'.format(*bbox),
              offering='urn:ioos:network:NOAA.NOS.CO-OPS:WaterLevelActive')

uri = 'http://opendap.co-ops.nos.noaa.gov/ioos-dif-sos/SOS'
url = sos_request(uri, **params)
observations = read_csv(url)

log.info('SOS URL request: {}'.format(url))


# #### Clean the dataframe (visualization purpose only)

# In[ ]:

from utilities import get_coops_longname, to_html

columns = {'datum_id': 'datum',
           'sensor_id': 'sensor',
           'station_id': 'station',
           'latitude (degree)': 'lat',
           'longitude (degree)': 'lon',
           'vertical_position (m)': 'height',
           'water_surface_height_above_reference_datum (m)': 'ssh above datum'}

observations.rename(columns=columns, inplace=True)

observations['datum'] = [s.split(':')[-1] for s in observations['datum']]
observations['sensor'] = [s.split(':')[-1] for s in observations['sensor']]
observations['station'] = [s.split(':')[-1] for s in observations['station']]
observations['name'] = [get_coops_longname(s) for s in observations['station']]

observations.set_index('name', inplace=True)
to_html(observations.head(), 'style.css')


# #### Generate a uniform 6-min time base for model/data comparison

# In[ ]:

import iris
from pandas import DataFrame
from owslib.ows import ExceptionReport
from utilities import coops2df, save_timeseries

iris.FUTURE.netcdf_promote = True

log.info(fmt(' Observations (station data) '))
fname = '{:%Y-%m-%d}-OBS_DATA.nc'.format(stop)

log.info(fmt(' Downloading to file {} '.format(fname)))
data = dict()
bad_datum = []
for station in observations.station:
    try:
        df = coops2df(collector, station)
        col = 'water_surface_height_above_reference_datum (m)'
        data.update({station: df[col]})
    except ExceptionReport as e:
        bad_datum.append(station)
        name = get_coops_longname(station)
        log.warning("[{}] {}:\n{}".format(station, name, e))
obs_data = DataFrame.from_dict(data)

# Split good and bad vertical datum stations.
pattern = '|'.join(bad_datum)
if pattern:
    non_navd = observations.station.str.contains(pattern)
    bad_datum = observations[non_navd]
    observations = observations[~non_navd]

comment = "Several stations from http://opendap.co-ops.nos.noaa.gov"
kw = dict(longitude=observations.lon,
          latitude=observations.lat,
          station_attr=dict(cf_role="timeseries_id"),
          cube_attr=dict(featureType='timeSeries',
                         Conventions='CF-1.6',
                         standard_name_vocabulary='CF-1.6',
                         cdm_data_type="Station",
                         comment=comment,
                         datum=datum,
                         url=url))

save_timeseries(obs_data, outfile=fname,
                standard_name=sos_name, **kw)

to_html(obs_data.head(), 'style.css')


# #### Loop discovered models and save the nearest time-series

# In[ ]:

get_ipython().magic('matplotlib inline')

import numpy as np
from iris.pandas import as_series
from iris.exceptions import (CoordinateNotFoundError, ConstraintMismatchError,
                             MergeError)

from utilities import (standardize_fill_value, plt_grid, get_cube,
                       get_model_name, make_tree, get_nearest_water,
                       add_station, ensure_timeseries)

# FIXME: Filtering out NECOFS  and estofs.
dap_urls = [url for url in dap_urls
            if 'NECOFS' not in url  # cartesian coords are not implemented.
            if 'estofs' not in url]  # download is taking forver today!


log.info(fmt(' Models (simulated data) '))
for k, url in enumerate(dap_urls):
    with timeit(log):
        log.info('\n[Reading url {}/{}]: {}'.format(k+1, len(dap_urls), url))
        try:
            cube = get_cube(url, name_list=name_list, bbox=bbox,
                            time=(start, stop), units=iris.unit.Unit('meters'))
            if cube.ndim == 1:  # We Need a better way to identify model data.
                log.warning('url {} is probably a timeSeries!'.format(url))
                continue
        except (RuntimeError, ValueError, MergeError,
                ConstraintMismatchError, CoordinateNotFoundError) as e:
            log.warning('Cannot get cube for: {}\n{}'.format(url, e))
            continue

        mod_name, model_full_name = get_model_name(cube, url)

        fname = '{:%Y-%m-%d}-{}.nc'.format(stop, mod_name)
        log.info(fmt(' Downloading to file {} '.format(fname)))
        try:  # Make tree.
            tree, lon, lat = make_tree(cube)
            fig, ax = plt_grid(lon, lat)
        except CoordinateNotFoundError as e:
            log.warning('Cannot make KDTree for: {}'.format(mod_name))
            continue
        # Get model series at observed locations.
        raw_series = dict()
        for station, obs in observations.iterrows():
            a = obs_data[obs['station']]
            try:
                kw = dict(k=10, max_dist=0.04, min_var=0.01)
                args = cube, tree, obs.lon, obs.lat
                series, dist, idx = get_nearest_water(*args, **kw)
            # RuntimeError may occurs, but you should run it again!
            except ValueError as e:
                log.warning(e)
                continue
            if not series:
                status = "Found Land"
            else:
                raw_series.update({obs['station']: series})
                series = as_series(series)
                status = "Found Water"
                ax.plot(lon[idx], lat[idx], 'g.')

            log.info('[{}] {}'.format(status, obs.name))

        if raw_series:  # Save cube.
            for station, cube in raw_series.items():
                cube = standardize_fill_value(cube)
                cube = add_station(cube, station)
            try:
                cube = iris.cube.CubeList(raw_series.values()).merge_cube()
            except MergeError as e:
                log.warning(e)

            ensure_timeseries(cube)
            iris.save(cube, fname)
            del cube

        size = len(raw_series)
        ax.set_title('{}: Points found {}'.format(mod_name, size))
        ax.plot(observations.lon, observations.lat, 'ro',
                zorder=1, label='Observation', alpha=0.25)
        ax.set_extent([bbox[0], bbox[2], bbox[1], bbox[3]])

    log.info('[{}]: {}'.format(mod_name, url))


# #### Load saved files and interpolate to the observations time interval

# In[ ]:

from glob import glob
from operator import itemgetter

from pandas import Panel
from utilities import nc2df

fname = '{:%Y-%m-%d}-OBS_DATA.nc'.format(stop)
OBS_DATA = nc2df(fname)
index = OBS_DATA.index

dfs = dict(OBS_DATA=OBS_DATA)
for fname in glob("*.nc"):
    if 'OBS_DATA' in fname:
        continue
    else:
        model = fname.split('.')[0].split('-')[-1]
        df = nc2df(fname)
        kw = dict(method='time', limit=30)
        df = df.reindex(index).interpolate(**kw).ix[index]
        dfs.update({model: df})

dfs = Panel.fromDict(dfs).swapaxes(0, 2)

# Clusters.
big_list = []
for fname in glob("*.nc"):
    if 'OBS_DATA' in fname:
        continue
    nc = iris.load_cube(fname)
    model = fname.split('-')[-1].split('.')[0]
    lons = nc.coord(axis='X').points
    lats = nc.coord(axis='Y').points
    stations = nc.coord('station name').points
    models = [model]*lons.size
    lista = zip(models, lons.tolist(), lats.tolist(), stations.tolist())
    big_list.extend(lista)

big_list.sort(key=itemgetter(3))
df = DataFrame(big_list, columns=['name', 'lon', 'lat', 'station'])
df.set_index('station', drop=True, inplace=True)
groups = df.groupby(df.index)


# In[ ]:

import folium
import vincent
from utilities import get_coordinates, inline_map

lon_center, lat_center = np.array(bbox).reshape(2, 2).mean(axis=0)
ssh = folium.Map(width=750, height=500,
                 location=[lat_center, lon_center], zoom_start=5)

# Create the map and add the bounding box line.
kw = dict(line_color='#FF0000', line_weight=2)
ssh.line(get_coordinates(bbox), **kw)

# Clusters.
for station, info in groups:
    station = get_coops_longname(station)
    for lat, lon, name in zip(info.lat, info.lon, info.name):
        location = lat, lon
        popup = '<b>{}</b>\n{}'.format(station, name)
        ssh.simple_marker(location=location, popup=popup,
                          clustered_marker=True)

# Model and observations.
for station in dfs:
    sta_name = get_coops_longname(station)
    df = dfs[station].dropna(axis=1, how='all')
    # FIXME: This is bad!  But I cannot represent NaN with Vega!
    df.fillna(value='null', inplace=True)
    vis = vincent.Line(df, width=500, height=150)
    vis.axis_titles(x='Time', y='Sea surface height (m)')
    vis.legend(title=sta_name)
    vis.name = sta_name
    json = 'station_{}.json'.format(station)
    vis.to_json(json)
    obs = observations[observations['station'] == station].squeeze()
    popup = (vis, json)
    if (df.columns == 'OBS_DATA').all():
        kw = dict(popup=popup, marker_color="blue", marker_icon="ok")
    else:
        if 'SABGOM' in df.columns:
            kw = dict(popup=popup, marker_color="green", marker_icon="ok-sign")
        else:
            kw = dict(popup=popup, marker_color="green", marker_icon="ok")
    ssh.simple_marker(location=[obs['lat'], obs['lon']], **kw)

# Bad datum.
if isinstance(bad_datum, DataFrame):
    for station, obs in bad_datum.iterrows():
        popup = '<b>Station:</b> {}<br><b>Datum:</b> {}<br>'
        popup = popup.format(station, obs['datum'])
        kw = dict(popup=popup, marker_color="red", marker_icon="question-sign")
        ssh.simple_marker(location=[obs['lat'], obs['lon']], **kw)

ssh.create_map(path=os.path.join('ssh.html'))
inline_map('ssh.html')


# In[ ]:

elapsed = time.time() - start_time
log.info(elapsed)
log.info('EOF')


# ### Compute bias

# In[ ]:

import os
import sys
root = os.path.abspath(os.path.join(os.getcwd(), os.pardir))
sys.path.append(root)

from utilities import nc2df


# In[ ]:

fname = '{:%Y-%m-%d}-OBS_DATA.nc'.format(stop)

OBS_DATA = nc2df(fname)
index = OBS_DATA.index


# In[ ]:

from glob import glob
from pandas import Panel

dfs = dict(OBS_DATA=OBS_DATA)
for fname in glob("*.nc"):
    if 'OBS_DATA' in fname:
        pass
    else:
        model = fname.split('.')[0].split('-')[-1]
        df = nc2df(fname)
        if False:
            kw = dict(method='time')
            df = df.reindex(index).interpolate(**kw).ix[index]
        dfs.update({model: df})

dfs = Panel.fromDict(dfs).swapaxes(0, 2)


# In[ ]:

from pandas import DataFrame

means = dict()
for station, df in dfs.iteritems():
    df.dropna(axis=1, how='all', inplace=True)
    mean = df.mean()
    df = df - mean + mean['OBS_DATA']
    means.update({station: mean['OBS_DATA'] - mean.drop('OBS_DATA')})

bias = DataFrame.from_dict(means).dropna(axis=1, how='all')
bias = bias.applymap('{:.2f}'.format).replace('nan', '--')

columns = dict()
[columns.update({station: get_coops_longname(station)}) for
 station in bias.columns.values]

bias.rename(columns=columns, inplace=True)

to_html(bias.T, 'style.css')


# In[ ]:

with open(LOG_FILENAME) as f:
    print(''.join(f.readlines()))

