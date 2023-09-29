"""Weather info driver"""

import time
import json
import socket
import datetime
import requests

try:
    # Slightly complicated install, do not demand for entire module
    import atmos
except ImportError:
    pass


def _virtual_temperature(temperature, dew_point, pressure):
    abs_temp = temperature + 273.15
    tmp1 = 10 ** (7.5 * dew_point / (237.7 + dew_point))
    tmp2 = tmp1 / (0.01 * pressure)  # Unit should be hPa, but we use Pa
    tv = abs_temp / (1 - (0.379 * 6.11 * tmp2))
    return tv


def dew_point_and_abs_humidity(temperature, humidity, pressure):
    """
    Calculates dew point and absolute humidity given atmospheric conditions.
    """
    atmos_params = {
        'RH': humidity,
        'RH_unit': 'fraction',
        'T': temperature,
        'T_unit': 'degC',
        'p': pressure,
        'p_unit': 'Pa',
    }

    dew_point = atmos.calculate('Td', Td_unit='degC', **atmos_params)
    absolute_humidity = atmos.calculate('AH', AH_unit='g/meter**3', **atmos_params)
    # print('Calculated dew point: {:.1f}C'.format(dew_point))
    # print('Calculated absolute humidity: {:.1f}g/m3'.format(absolute_humidity))
    data = {
        'dew_point': dew_point,  # degree C
        'absolute_humidity': absolute_humidity,  # g/m3
    }
    return data


def equaivalent_humidity(outside_temp, outside_hum, inside_temp, pressure):
    """
    Given outside atmospheric conditaions, calculate the relative humidity
    inside of the outside air is heated (or cooled) to the inside tempererature.
    """
    dew_and_abs = dew_point_and_abs_humidity(outside_temp, outside_hum, pressure)
    # Calculate inside virtual temperature if outside air was to be
    # heated to inside temp
    tv = _virtual_temperature(inside_temp, dew_and_abs['dew_point'], pressure)
    atmos_params = {
        'AH': dew_and_abs['absolute_humidity'],
        'AH_unit': 'g/meter**3',
        'Tv': tv,
        'Tv_unit': 'K',
        'p': pressure,
        'p_unit': 'Pa',
        'debug': True,
    }

    # Humidity is returned as percentage
    indoor_humidity = atmos.calculate('RH', **atmos_params)
    return indoor_humidity[0]


class WheatherInformation(object):
    def __init__(self, x_pos, y_pos, **kwargs):
        self.kwargs = kwargs
        self.x_pos = x_pos
        self.y_pos = y_pos
        self.clear_data()

    def clear_data(self):
        self.weather_data = {
            'time': None,  # Time of latest update
            'temperature': None,
            'humidity': None,
            'precepitation': None,
            'wind': None,
            'wind_gust': None,
            'wind_direction': None,  # 0 North, 90 west, 180 south, 280 east
            'pressure': None,
            'sunrise': None,
            'sunset': None,
            'uv_index': None,
            'visibility': None,
            'cloud_percentage': None,
        }

    def dk_dmi(self):
        params = {
            'cmd': 'obj',
            'south': self.y_pos - 0.25,
            'north': self.y_pos + 0.25,
            'west': self.x_pos - 0.25,
            'east': self.x_pos + 0.25,
        }
        url = 'https://www.dmi.dk/NinJo2DmiDk/ninjo2dmidk'
        error = 0
        while -1 < error < 30:
            try:
                response = requests.get(url, params=params)
                error = -1
                data = response.json()
            except requests.exceptions.ConnectionError:
                error = error + 1
                print('Connection error to: {}'.format(url))
                time.sleep(60)
            except json.decoder.JSONDecodeError:
                error = error + 1
                print('JSON decode error: {}'.format(url))
                time.sleep(60)
            except socket.gaierror:
                error = error + 1
                print('Temporary failure in name resolution. {}'.format(url))
                time.sleep(60)

        pri_list = self.kwargs.get('dmi_prio', {})
        if pri_list is {}:
            print('Error no dmi position configured!')
            exit()
        # 06180: Lufthavn
        # 06186: Landbohøjskolen
        print(data)

        if not pri_list[0] in data:
            print('Did not find priority 0 in data-list, give up!')
            return
        dmi_time_field = data[pri_list[0]]['time'][0:12]
        self.weather_data['time'] = datetime.datetime.strptime(
            dmi_time_field, '%Y%m%d%H%M'
        )

        # List of genral values mapped to (key, unit-scale)
        value_map = {
            'temperature': ('Temperature2m', 1),
            'humidity': ('RelativeHumidity', 0.01),
            'precepitation': ('PrecAmount10min', 1),
            'wind': ('WindSpeed10m', 1),
            'wind_gust': ('WindGustLast10Min', 1),
            'wind_direction': ('WindDirection10m', 1),
            'pressure': ('PressureMSL', 1),
        }

        for dmi_site in sorted(pri_list.keys()):
            dmi_values = data[pri_list[dmi_site]]['values']
            for global_key, dmi_key in value_map.items():
                dmi_value = dmi_values.get(dmi_key[0])
                if self.weather_data[global_key] is None and dmi_value is not None:
                    self.weather_data[global_key] = dmi_value * dmi_key[1]

    def global_openweather(self):
        params = {
            'lat': self.y_pos,
            'lon': self.x_pos,
            'units': 'metric',
            'appid': self.kwargs['open_weather_appid'],
        }

        # 'dew_point': 'dew_point'
        value_map = {
            'temperature': 'temp',
            'humidity': ('humidity', 0.01),
            # 'precepitation': Not in data
            'wind': ('wind_speed', 1),
            # 'wind_gust': Not in data
            'wind_direction': ('wind_deg', 1),
            'pressure': ('pressure', 100),
            'sunrise': ('sunrise', 1),
            'sunset': ('sunset', 1),
            'uv_index': ('uvi', 1),
            'visibility': ('visibility', 1),
            'cloud_percentage': ('clouds', 1),
        }
        url = 'https://api.openweathermap.org/data/2.5/onecall'
        # This code is used twice, refactor (and do it right, so
        # it will recover after extended loss of internet)?
        error = 0
        while -1 < error < 30:
            try:
                response = requests.get(url, params=params)
                error = -1
                data = response.json()
            except requests.exceptions.ConnectionError:
                error = error + 1
                print('Connection error to: {}'.format(url))
                time.sleep(60)
            except json.decoder.JSONDecodeError:
                error = error + 1
                print('JSON decode error: {}'.format(url))
                time.sleep(60)
            except socket.gaierror:
                error = error + 1
                print('Temporary failure in name resolution. {}'.format(url))
                time.sleep(60)

        # See also keys 'hourly' and 'daily'
        current = data['current']
        # time_field = datetime.datetime.fromtimestamp(current['dt'])

        for global_key, openweather_key in value_map.items():
            value = current.get(openweather_key[0])
            if self.weather_data[global_key] is None and value is not None:
                self.weather_data[global_key] = value * openweather_key[1]


if __name__ == '__main__':
    dmi_prio = {0: '06186', 1: '06180'}

    appid = ''

    vejr = WheatherInformation(
        y_pos=55.660105, x_pos=12.589183, dmi_prio=dmi_prio, open_weather_appid=appid
    )
    vejr.dk_dmi()
    print(vejr.weather_data)

    indoor_hum = equaivalent_humidity(
        outside_temp=vejr.weather_data['temperature'],
        outside_hum=vejr.weather_data['humidity'],
        pressure=vejr.weather_data['pressure'],
        inside_temp=24,
    )
    print(indoor_hum)

    # vejr.global_openweather()
    # print(vejr.weather_data)
