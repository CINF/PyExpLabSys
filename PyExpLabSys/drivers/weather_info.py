import datetime
import requests


class WheatherInformation(object):

    def __init__(self, x_pos, y_pos, **kwargs):
        self.kwargs = kwargs
        self.x_pos = x_pos
        self.y_pos = y_pos

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
            'cloud_percentage': None
        }

    def dk_dmi(self):
        params = {
            'cmd': 'obj',
            'south': self.y_pos - 0.15,
            'north': self.y_pos + 0.15,
            'west': self.x_pos - 0.15,
            'east': self.x_pos + 0.15
        }
        url = 'https://www.dmi.dk/NinJo2DmiDk/ninjo2dmidk'
        response = requests.get(url, params=params)
        data = response.json()

        pri_list = self.kwargs.get('dmi_prio', {})
        if pri_list is {}:
            print('Error no dmi position configured!')
            exit()
        # 06180: Lufthavn
        # 06186: Landbohøjskolen
        print(pri_list)
        dmi_time_field = data[pri_list[0]]['time'][0:12]
        self.weather_data['time'] = datetime.datetime.strptime(
            dmi_time_field, '%Y%m%d%H%M')

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
                if (
                        self.weather_data[global_key] is None and
                        dmi_value is not None
                ):
                    self.weather_data[global_key] = dmi_value * dmi_key[1]

    def global_openweather(self):
        params = {
            'lat': self.y_pos,
            'lon': self.x_pos,
            'units': 'metric',
            'appid': self.kwargs['open_weather_appid']
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
            'cloud_percentage': ('clouds', 1)
        }
        url = 'https://api.openweathermap.org/data/2.5/onecall'
        response = requests.get(url, params=params)
        data = response.json()
        # See also keys 'hourly' and 'daily'
        current = data['current']
        # time_field = datetime.datetime.fromtimestamp(current['dt'])

        for global_key, openweather_key in value_map.items():
            value = current.get(openweather_key[0])
            if (
                    self.weather_data[global_key] is None and
                    value is not None
            ):
                self.weather_data[global_key] = value * openweather_key[1]


if __name__ == '__main__':
    dmi_prio = {
        0: '06186',
        1: '06180'
    }

    appid = ''

    vejr = WheatherInformation(
        y_pos=55.660105,
        x_pos=12.589183,
        dmi_prio=dmi_prio,
        open_weather_appid=appid
    )
    print(vejr.dk_dmi())
