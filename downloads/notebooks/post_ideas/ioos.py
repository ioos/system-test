"""
Utility functions for IOOS notebooks.

"""

from __future__ import division


import requests
from datetime import datetime, timedelta

import numpy as np
import numpy.ma as ma

from shapely.geometry import Point
from netCDF4 import Dataset, num2date
from pandas import DataFrame, read_csv


__all__ = ['buildSFOUrls',
           'findSFOIndexs',
           'uv2ws',
           'uv2wd',
           'isDataValid',
           'cycleAndGetData',
           'find_nearest',
           'processStationInfo',
           'coopsCurrentRequest',
           'ndbcSOSRequest',
           'get_hr_radar_dap_data',
           'extractSFOModelData']


def buildSFOUrls(jd_start,  jd_stop):
    """
    Multiple files for time step, were only looking at Nowcast (past) values
    times are 3z, 9z, 15z, 21z

    """
    url_list = []
    time_list = ['03z', '09z', '15z', '21z']
    delta = jd_stop-jd_start
    for i in range((delta.days)+1):
        model_file_date = jd_start + timedelta(days=i)
        base_url = ('http://opendap.co-ops.nos.noaa.gov/'
                    'thredds/dodsC/NOAA/SFBOFS/MODELS/')
        val_month, val_year, val_day = '', '', ''
        # Month.
        if model_file_date.month < 10:
            val_month = "0" + str(model_file_date.month)
        else:
            val_month = str(model_file_date.month)
        # Year.
        val_year = str(model_file_date.year)
        # Day.
        if model_file_date.day < 10:
            val_day = "0" + str(model_file_date.day)
        else:
            val_day = str(model_file_date.day)
        file_name = '/nos.sfbofs.stations.nowcast.'
        file_name += val_year + val_month + val_day
        for t in time_list:
            t_val = '.t' + t + '.nc'
            url_list.append(base_url + val_year + val_month +
                            file_name + t_val)
    return url_list


def findSFOIndexs(lats, lons, lat_lon_list):
    index_list, dist_list = [], []
    for val in lat_lon_list:
        point1 = Point(val[1], val[0])
        dist = 999999999
        index = -1
        for k in range(0, len(lats)):
            point2 = Point(lons[k], lats[k])
            val = point1.distance(point2)
            if val < dist:
                index = k
                dist = val
        index_list.append(index)
        dist_list.append(dist)
    sorted_list = sorted(zip(index_list, dist_list))
    index_list = [x[0] for x in sorted_list]
    dist_list = [x[1] for x in sorted_list]
    return index_list, dist_list


def uv2ws(u, v):
    return np.sqrt(u**2 + v**2)


def uv2wd(u, v):
    """
    NOTE: This is direction TOWARDS. u/v are mathematical vectors so direction
          is where they are pointing
    NOTE: arctan2(u,v) automatically handles the 90 degree rotation so North
          is zero, arctan2(v, u), mathematical version, has 0 at east.

    """
    wd = np.degrees(np.arctan2(u, v))
    return np.where(wd >= 0, wd, wd+360)


def isDataValid(u, v):
    """
    Count the non nan stations.

    """
    num_not_nan = np.count_nonzero(~np.isnan(u))
    if num_not_nan > 10:
        return True
    else:
        return False


def cycleAndGetData(u_var, v_var, date_idx, lat_idx, lon_idx):
    lat_list = [0, -1, 1, 0, -1, -1, 0, -1, 1]
    lon_list = [0, 0, 1, 1, 1, -1, -1, -1, 0]

    for i in range(0, len(lat_list)):
        u_vals = u_var[date_idx, lat_idx + lat_list[i], lon_idx + lon_list[i]]
        v_vals = v_var[date_idx, lat_idx + lat_list[i], lon_idx + lon_list[i]]

        if isinstance(u_vals, ma.masked_array):
            # Try and get the data using a filled array.
            u_vals = u_vals.filled(np.nan)
            v_vals = v_vals.filled(np.nan)

        # Convert from m/s to cm/s.
        if u_var.units == "m s-1":
            u_vals = (u_vals) * 100.0
            v_vals = (v_vals) * 100.0

        # If the data is not valid lets carry on searching.
        if isDataValid(u_vals, v_vals):
            return [u_vals, v_vals,
                    lat_idx + lat_list[i],
                    lon_idx + lon_list[i]]
    return [u_vals, v_vals, lat_idx + lat_list[i], lon_idx + lon_list[i]]


def find_nearest(obs_lat, obs_lon, lats, lons):
    """
    Find the closest point, distance in degrees
    (coordinates of the points in degrees).

    """
    point1 = Point(obs_lon, obs_lat)
    dist = 999999999
    index_i, index_j = -1, -1
    for i in range(0, len(lats)):
        for j in range(0, len(lons)):
            point2 = Point(lons[j], lats[i])
            val = point1.distance(point2)
            if val < dist:
                index_i = i
                index_j = j
                dist = val
    return [index_i, index_j, dist]


def processStationInfo(obs_loc_df, source, st_list=None):
    """
    Create a list of stations available.

    """
    if not st_list:
        st_list = dict()
    st_data = obs_loc_df['station_id']
    lat_data = obs_loc_df['latitude (degree)']
    lon_data = obs_loc_df['longitude (degree)']

    for k, station_name in enumerate(st_data):
        if station_name in st_list:
            pass
        else:
            st_list[station_name] = dict()
            st_list[station_name]["lat"] = lat_data[k]
            st_list[station_name]["source"] = source
            st_list[station_name]["lon"] = lon_data[k]
            print(station_name)

    print("Number of stations in bbox {}".format(len(st_list.keys())))
    return st_list


def coopsCurrentRequest(station_id, tides_dt_start, tides_dt_end):
    """
    Function handles current requests.

    """
    tides_data_options = "time_zone=gmt&application=ports_screen&format=json"
    tides_url = "http://tidesandcurrents.noaa.gov/api/datagetter?"
    begin_datetime = "begin_date=" + tides_dt_start
    end_datetime = "&end_date=" + tides_dt_end
    current_dp = "&station=" + station_id
    full_url = (tides_url + begin_datetime + end_datetime+current_dp +
                "&application=web_services&product=currents&units=english&" +
                tides_data_options)
    r = requests.get(full_url)
    try:
        r = r.json()
    except:
        return None
    if 'data' in r:
        r = r['data']
        data_dt = []
        data_spd = []
        data_dir = []
        for row in r:
            # Convert from knots to cm/s.
            data_spd.append(float(row['s']) * 51.4444444)
            data_dir.append(float(row['d']))
            date_time_val = datetime.strptime(row['t'], '%Y-%m-%d %H:%M')
            data_dt.append(date_time_val)

        data = dict()
        data['sea_water_speed (cm/s)'] = np.array(data_spd)
        data['direction_of_sea_water_velocity (degree)'] = np.array(data_dir)
        time = np.array(data_dt)
        columns = ['sea_water_speed (cm/s)',
                   'direction_of_sea_water_velocity (degree)']
        df = DataFrame(data=data, index=time, columns=columns)
        return df
    else:
        return None


def ndbcSOSRequest(station, date_range):
    url = ('http://sdf.ndbc.noaa.gov/sos/server.php?'
           'request=GetObservation&service=SOS&version=1.0.0'
           '&offering=%s&'
           'observedproperty=Currents&responseformat=text/csv'
           '&eventtime=%s') % (station, date_range)
    obs_loc_df = read_csv(url)
    return obs_loc_df


def get_hr_radar_dap_data(dap_urls, st_list, jd_start, jd_stop):
    """
    Directly access the DAP endpoint to get data.

    """
    df_list = []
    for url in dap_urls:
        # Only look at 6 km hf radar.
        if ('http://hfrnet.ucsd.edu/thredds/dodsC/HFRNet/USWC/' in url and
           "6km" in url and "GNOME" in url):
            print(url)
            # Get URL.
            nc = Dataset(url, 'r')
            lat_dim = nc.variables['lat']
            lon_dim = nc.variables['lon']
            time_dim = nc.variables['time']
            u_var, v_var = None, None
            standard_name_u = "surface_eastward_sea_water_velocity"
            standard_name_v = "surface_northward_sea_water_velocity"
            for key in nc.variables.keys():
                key_dim = nc.variables[key]
                try:
                    if key_dim.standard_name == standard_name_u:
                        u_var = key_dim
                    elif key_dim.standard_name == standard_name_v:
                        v_var = key_dim
                    elif key_dim.standard_name == "time":
                        time = key_dim
                except:
                    # Only if the standard name is not available.
                    pass
            # Manage dates.
            dates = num2date(time_dim[:], units=time_dim.units,
                             calendar='gregorian')
            date_idx = []
            date_list = []
            for i, date in enumerate(dates):
                if jd_start < date < jd_stop:
                    date_idx.append(i)
                    date_list.append(date)
            # Manage location.
            for st in st_list:
                station = st_list[st]
                f_lat = station['lat']
                f_lon = station['lon']

                ret = find_nearest(f_lat, f_lon, lat_dim[:], lon_dim[:])
                lat_idx = ret[0]
                lon_idx = ret[1]
                dist_deg = ret[2]

                if len(u_var.dimensions) == 3:
                    # 3D.
                    ret = cycleAndGetData(u_var, v_var, date_idx,
                                          lat_idx, lon_idx)
                    u_vals = ret[0]
                    v_vals = ret[1]

                    lat_idx = ret[2]
                    lon_idx = ret[3]

                    print("lat, lon, dist = {} {}".format(ret[2], ret[3]))
                try:
                    # Turn vectors in the speed and direction.
                    ws = uv2ws(u_vals, v_vals)
                    wd = uv2wd(u_vals, v_vals)

                    data = dict()
                    data['sea_water_speed (cm/s)'] = ws
                    data['direction_of_sea_water_velocity (degree)'] = wd
                    time = np.array(date_list)
                    columns = ['sea_water_speed (cm/s)',
                               'direction_of_sea_water_velocity (degree)']
                    df = DataFrame(data=data, index=time, columns=columns)
                    df_list.append({"name": st,
                                    "data": df,
                                    "lat": lat_dim[lat_idx],
                                    "lon": lon_dim[lon_idx],
                                    "ws_pts": np.count_nonzero(~np.isnan(ws)),
                                    "wd_pts": np.count_nonzero(~np.isnan(wd)),
                                    "dist": dist_deg,
                                    "from": url})
                except Exception as e:
                    print("\t\terror: {}".format(e))
        else:
            pass
    return df_list


def extractSFOModelData(lat_lon_list, name_list, jd_start,  jd_stop):
    urls = buildSFOUrls(jd_start,  jd_stop)

    df_list = dict()

    for n in name_list:
        df_list[n] = dict()
    for k, url in enumerate(urls):
        try:
            nc = Dataset(url, 'r')
        except Exception as e:
            print(e)
            break
        if k == 0:
            lats = nc.variables['lat'][:]
            lons = nc.variables['lon'][:]
            lons = lons-360
            index_list, dist_list = findSFOIndexs(lats, lons, lat_lon_list)
        # Extract the model data using and MF dataset.
        time_dim = nc.variables['time']
        u_dim = nc.variables['u']
        v_dim = nc.variables['v']

        u_var = u_dim[:, 0, index_list]
        v_var = v_dim[:, 0, index_list]

        # Create the dates.
        dates = num2date(time_dim[:], units=time_dim.units,
                         calendar='gregorian')

        for k, n in enumerate(name_list):
            # Get lat and lon.
            df_list[n]['lat'] = lats[index_list[k]]
            df_list[n]['lon'] = lons[index_list[k]]
            # Create speed and direction, convert.
            ws = uv2ws(u_var[:, k] * 100, v_var[:, k] * 100)
            wd = uv2wd(u_var[:, k] * 100, v_var[:, k] * 100)
            data = dict()
            data['sea_water_speed (cm/s)'] = ws
            data['direction_of_sea_water_velocity (degree)'] = wd
            columns = ['sea_water_speed (cm/s)',
                       'direction_of_sea_water_velocity (degree)']
            df = DataFrame(data=data, index=dates, columns=columns)
            # Create structure.
            if 'data' in df_list[n]:
                df_list[n]['data'] = df_list[n]['data'].append(df)
            else:
                df_list[n]['data'] = df
    return df_list
