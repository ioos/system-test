"""
Utility functions for Scenario_A_Extreme_Winds.ipynb
"""
from IPython.display import HTML, Javascript, display
import uuid
import fnmatch
import lxml.html
from io import BytesIO
from lxml import etree
from urllib import urlopen
from warnings import warn
from windrose import WindroseAxes
import numpy as np

# Scientific stack.
import matplotlib.pyplot as plt
from owslib import fes
from owslib.ows import ExceptionReport
from pandas import DataFrame, read_csv
from netCDF4 import MFDataset, date2index, num2date


def insert_progress_bar(title='Please wait...', color='blue'):
    """Inserts a simple progress bar into the IPython notebook."""
    print(title)
    divid = str(uuid.uuid4())
    pb = HTML(
        """
        <div style="border: 1px solid black; width:500px">
          <div id="%s" style="background-color:red; width:0%%">&nbsp;</div>
        </div>
        """ % divid)
    display(pb)
    return divid


def update_progress_bar(divid, percent_compelte):
    """Updates the simple progress bar into the IPython notebook."""
    display(Javascript("$('div#%s').width('%i%%')" % (divid, int(percent_compelte))))


def fes_date_filter(start_date='1900-01-01', stop_date='2100-01-01',
                    constraint='overlaps'):
    """Hopefully something like this will be implemented in fes soon."""
    if constraint == 'overlaps':
        propertyname = 'apiso:TempExtent_begin'
        start = fes.PropertyIsLessThanOrEqualTo(propertyname=propertyname,
                                                literal=stop_date)
        propertyname = 'apiso:TempExtent_end'
        stop = fes.PropertyIsGreaterThanOrEqualTo(propertyname=propertyname,
                                                  literal=start_date)
    elif constraint == 'within':
        propertyname = 'apiso:TempExtent_begin'
        start = fes.PropertyIsGreaterThanOrEqualTo(propertyname=propertyname,
                                                   literal=start_date)
        propertyname = 'apiso:TempExtent_end'
        stop = fes.PropertyIsLessThanOrEqualTo(propertyname=propertyname,
                                               literal=stop_date)
    return start, stop


def service_urls(records, service='odp:url'):
    """Extract service_urls of a specific type (DAP, SOS) from records."""
    service_string = 'urn:x-esri:specification:ServiceType:' + service
    urls = []
    for key, rec in records.items():
        # Create a generator object, and iterate through it until the match is
        # found if not found, gets the default value (here "none").
        url = next((d['url'] for d in rec.references if
                    d['scheme'] == service_string), None)
        if url is not None:
            urls.append(url)
    return urls


def get_station_longName(station, provider):
    """Get longName for specific station using DescribeSensor
    request."""
    if provider.upper() == 'NDBC':
        url = ('http://sdf.ndbc.noaa.gov/sos/server.php?service=SOS&'
               'request=DescribeSensor&version=1.0.0&outputFormat=text/xml;subtype="sensorML/1.0.1"&'
               'procedure=urn:ioos:station:wmo:%s') % station
    elif provider.upper() == 'COOPS':
        url = ('http://opendap.co-ops.nos.noaa.gov/ioos-dif-sos/SOS?service=SOS&'
               'request=DescribeSensor&version=1.0.0&'
               'outputFormat=text/xml;subtype="sensorML/1.0.1"&'
               'procedure=urn:ioos:station:NOAA.NOS.CO-OPS:%s') % station
    try:
        tree = etree.parse(urlopen(url))
        root = tree.getroot()
        namespaces = {'sml': "http://www.opengis.net/sensorML/1.0.1"}
        longName = root.xpath("//sml:identifier[@name='longName']/sml:Term/sml:value/text()", namespaces=namespaces)
        if len(longName) == 0:
            # Just return the station id
            return station
        else:
            return longName[0]
    except Exception as e:
        warn(e)
        # Just return the station id
        return station


def collector2df(collector, station, sos_name, provider='COOPS'):
    """Request CSV response from SOS and convert to Pandas DataFrames."""
    collector.features = [station]
    collector.variables = [sos_name]

    long_name = get_station_longName(station, provider)
    try:

        response = collector.raw(responseFormat="text/csv")
        data_df = read_csv(BytesIO(response.encode('utf-8')),
                           parse_dates=True,
                           index_col='date_time')
        col = 'wind_speed (m/s)'
        data_df['Observed Data'] = data_df[col]
    except ExceptionReport as e:
        # warn("Station %s is not NAVD datum. %s" % (long_name, e))
        print(str(e))
        data_df = DataFrame()  # Assigning an empty DataFrame for now.

    data_df.name = long_name
    data_df.provider = provider
    return data_df


def get_coordinates(bounding_box, bounding_box_type=''):
    """Create bounding box coordinates for the map."""
    coordinates = []
    if bounding_box_type == "box":
        coordinates.append([bounding_box[1], bounding_box[0]])
        coordinates.append([bounding_box[1], bounding_box[2]])
        coordinates.append([bounding_box[3], bounding_box[2]])
        coordinates.append([bounding_box[3], bounding_box[0]])
        coordinates.append([bounding_box[1], bounding_box[0]])
    return coordinates


def inline_map(m):
    """From http://nbviewer.ipython.org/gist/rsignell-usgs/
    bea6c0fe00a7d6e3249c."""
    m._build_map()
    srcdoc = m.HTML.replace('"', '&quot;')
    embed = HTML('<iframe srcdoc="{srcdoc}" '
                 'style="width: 100%; height: 500px; '
                 'border: none"></iframe>'.format(srcdoc=srcdoc))
    return embed


def css_styles():
    return HTML("""
        <style>
        .info {
            background-color: #fcf8e3; border-color: #faebcc;
                border-left: 5px solid #8a6d3b; padding: 0.5em; color: #8a6d3b;
        }
        .success {
            background-color: #d9edf7; border-color: #bce8f1;
                border-left: 5px solid #31708f; padding: 0.5em; color: #31708f;
        }
        .error {
            background-color: #f2dede; border-color: #ebccd1;
                border-left: 5px solid #a94442; padding: 0.5em; color: #a94442;
        }
        .warning {
            background-color: #fcf8e3; border-color: #faebcc;
                border-left: 5px solid #8a6d3b; padding: 0.5em; color: #8a6d3b;
        }
        </style>
    """)


def gather_station_info(obs_loc_df, st_list, source):
    st_data = obs_loc_df['station_id']
    lat_data = obs_loc_df['latitude (degree)']
    lon_data = obs_loc_df['longitude (degree)']
    for k in range(0, len(st_data)):
        station_name = st_data[k]
        if station_name in st_list:
            continue
        else:
            st_list[station_name] = {}
            st_list[station_name]["lat"] = lat_data[k]
            st_list[station_name]["source"] = source
            st_list[station_name]["lon"] = lon_data[k]
    return st_list


def get_ncfiles_catalog(station_id, jd_start, jd_stop):
    station_name = station_id.split(":")[-1]
    uri = 'http://dods.ndbc.noaa.gov/thredds/dodsC/data/stdmet'
    url = ('%s/%s/' % (uri, station_name))
    urls = _url_lister(url)
    filetype = "*.nc"
    file_list = [filename for filename in fnmatch.filter(urls, filetype)]
    files = [fname.split('/')[-1] for fname in file_list]
    urls = ['%s/%s/%s' % (uri, station_name, fname) for fname in files]

    try:
        nc = MFDataset(urls)

        time_dim = nc.variables['time']
        calendar = 'gregorian'
        idx_start = date2index(jd_start, time_dim, calendar=calendar,
                               select='nearest')
        idx_stop = date2index(jd_stop, time_dim, calendar=calendar,
                              select='nearest')

        dir_dim = np.array(nc.variables['wind_dir'][idx_start:idx_stop, 0, 0], dtype=float)
        speed_dim = np.array(nc.variables['wind_spd'][idx_start:idx_stop, 0, 0])
        # Replace fill values with NaN
        speed_dim[speed_dim == nc.variables['wind_spd']._FillValue] = np.nan

        if dir_dim.ndim != 1:
            dir_dim = dir_dim[:, 0]
            speed_dim = speed_dim[:, 0]
        time_dim = nc.variables['time']
        dates = num2date(time_dim[idx_start:idx_stop],
                         units=time_dim.units,
                         calendar='gregorian').squeeze()
        mask = np.isfinite(speed_dim)

        data = dict()
        data['wind_speed (m/s)'] = speed_dim[mask]
        data['wind_from_direction (degree)'] = dir_dim[mask]
        time = dates[mask]

        # columns = ['wind_speed (m/s)',
        #            'wind_from_direction (degree)']
        df = DataFrame(data=data, index=time)
        return df
    except Exception as e:
        print str(e)
        df = DataFrame()
        return df


def new_axes():
    fig = plt.figure(figsize=(8, 8), dpi=80, facecolor='w', edgecolor='w')
    rect = [0.1, 0.1, 0.8, 0.8]
    ax = WindroseAxes(fig, rect, axisbg='w')
    fig.add_axes(ax)
    return ax


def set_legend(ax, label=''):
    """Adjust the legend box."""
    l = ax.legend(title=label)
    plt.setp(l.get_texts(), fontsize=8)


def _url_lister(url):
    urls = []
    connection = urlopen(url)
    dom = lxml.html.fromstring(connection.read())
    for link in dom.xpath('//a/@href'):
        urls.append(link)
    return urls


def nearxy(x, y, xi, yi):
    """Find the indices x[i] of arrays (x,y) closest to the points (xi, yi)."""
    ind = np.ones(len(xi), dtype=int)
    dd = np.ones(len(xi), dtype='float')
    for i in np.arange(len(xi)):
        dist = np.sqrt((x-xi[i])**2 + (y-yi[i])**2)
        ind[i] = dist.argmin()
        dd[i] = dist[ind[i]]
    return ind, dd
