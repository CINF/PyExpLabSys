import base64
import requests


class PowerView(object):
    def __init__(self, address):
        self.address = 'http://' + address + '/api/'
        self.rooms = self._find_rooms()  # Fast, does not talk to shades
        self.shades = {}

    def _decode_name(self, encoded_name):
        """
        Decodes the base64 to a human-readable string.
        """
        name = base64.b64decode(encoded_name).decode()
        return name

    def _find_rooms(self):
        """
        Find configured rooms, this is an internal operatioin that
        does not need contact to the shades.
        """
        r = requests.get(self.address + 'rooms')
        rooms = {}
        rooms_raw = r.json()
        for room in rooms_raw['roomData']:
            rooms[room['id']] = self._decode_name(room['name'])
        return rooms

    def _jog_shade(self, shade_id):
        """
        Jog the shade to visually identify it.
        """
        msg = '{}shades/{}'.format(self.address, shade_id)
        payload = {"shade": {"motion": "jog"}}
        r = requests.put(msg, json=payload)
        success = r.status_code == 200
        return success

    def hub_info(self):
        """
        Find configured rooms, this is an internal operatioin that
        does not need contact to the shades.
        """
        r = requests.get(self.address + 'userdata')
        hub_raw = r.json()
        print(hub_raw)

    def find_all_shades(self):
        """
        Find all configured shades. If contact can be established, each shade
        will be populated with current info.
        """
        r = requests.get(self.address + 'shades?')
        shades_raw = r.json()
        for shade in shades_raw['shadeData']:
            name = self._decode_name(shade['name'])
            shade['name'] = name
            self.shades[shade['id']] = shade
        return True

    def update_battery_level(self, shade_id):
        """
        Update battery level. Possibly a redundant function.
        """
        msg = '{}shades/{}?updateBatteryLevel=true'
        r = requests.get(msg.format(self.address, shade_id))
        print(r.json())

    def update_shade(self, shade_id):
        """
        Update shade informatioin. Internal state must be initialized
        by find_all_shades() before this function can be used to
        update individual shades.
        """
        if shade_id not in self.shades:
            print('Shade unknown - run find_all_shades()')
            return False

        msg = '{}shades/{}?refresh=true'
        r = requests.get(msg.format(self.address, shade_id))
        shade = r.json()
        assert 'shade' in shade
        shade = shade['shade']
        name = self._decode_name(shade['name'])
        shade['name'] = name
        self.shades[shade['id']] = shade

    def move_shade(self, shade_id, raw_pos=None, percent_pos=None):
        """
        Move shade to specified position. If no position is given, the
        shade will jog for visual identification.
        :param shade_id: The shade to move.
        :param raw_pos: The Wanted position, 0 closed, 2^16-1 is fully open.
        :param percent_pos: Openness in percent, 0 closed, 100 open.
        """
        if raw_pos is None and percent_pos is None:
            self._jog_shade(shade_id)
            return True

        if percent_pos is not None:
            raw_pos = int(percent_pos / 100.0 * 2 ** 16) - 1
        assert 0 < raw_pos < 2 ** 16
        payload = {'shade': {'positions': {'posKind1': 1, 'position1': raw_pos}}}
        msg = '{}shades/{}'.format(self.address, shade_id)
        requests.put(msg, json=payload)
        return True

    def print_current_shade_status(self, shade_id):
        shade = self.shades.get(shade_id)
        room_name = self.rooms[shade['roomId']]
        if shade is None:
            print('Shade unknown')
        elif 'positions' not in shade:
            msg = 'Shade {} in room {} is not currently witin range'
            print(msg.format(shade['name'], room_name))
        else:
            msg = 'Shade {} in room {} is {:.0f}% open. Battery is {}'
            print(
                msg.format(
                    shade['name'],
                    room_name,
                    100.0 * shade['positions']['position1'] / 2 ** 16,
                    shade['batteryStrength'],
                )
            )


if __name__ == '__main__':
    pv = PowerView('192.168.1.76')

    pv.find_all_shades()
    pv.move_shade(32852, percent_pos=85)
    # pv.update_shade(8690)
    pv.print_current_shade_status(8690)
    pv.print_current_shade_status(32852)
