import json
import requests


class NetioPowerBox(object):
    """Driver For Netio PowerBOX
    - this driver has been tested on model 4KF
    """

    def __init__(self, ip: str):
        self.url = 'http://{}/netio.json'.format(ip)
        self.device_info = self._read_device_info()
        self.auth = ('netio', 'netio')

    def _read_device_info(self) -> dict:
        """
        Read basic information about the power strip. None of this information
        is dynamic, and the command thus only needs to be run upon startup
        of the driver. The information can afterwards be accessed in the dict
        self.device_info
        """
        data = self._read()
        agent = data['Agent']
        device_info = {
            'model': agent['Model'],
            'name': agent['DeviceName'],
            'mac': agent['MAC'],
            'sn': agent['SerialNumber'],
            'uptime': agent['Uptime'],
            'outputs': agent['NumOutputs'],
        }
        return device_info

    def _read(self) -> dict:
        r = requests.get(self.url)
        reply = r.json()
        return reply

    def plug_output_state(self, output: int, state: bool) -> bool:
        """
        Set the output state of plug N to either on or off
        :param output: The index of the plug to controlled
        :param state: Indicates whether to turn the pug on or off
        :return: True if command succeeded, false if it did not
        """
        if state:
            action = 1
        else:
            action = 0
        payload = {'Outputs': [{'ID': output, 'Action': action}]}
        r = requests.post(self.url, data=json.dumps(payload), auth=self.auth)
        success = r.status_code == 200
        return success

    def output_status(self, wanted_outputs: [int]) -> dict:
        """
        Read the status of a number of outputs
        The reply contains a list of outputs with the following measurement values:
        Current in mA
        PowerFacor of the output
        Phase of the output
        Total energy consumption in Wh since last reset
        Total energy consumption ever on the output
        Load: Current load in watts
        :param wanted_outputs: A list of indexes of the outputs to return
        :return: The wanted measurements + global measurements at index 0
        """
        data = self._read()

        outputs = {}
        outputs[0] = data['GlobalMeasure']

        for output in data['Outputs']:
            # print(output)
            output_id = output['ID']
            if output_id in wanted_outputs:
                outputs[output_id] = output
        return outputs


if __name__ == '__main__':
    npb = NetioPowerBox('10.54.4.98')
    # print(npb.device_info)

    outputs = npb.output_status([1])
    print(outputs[0])
    print()
    print(outputs[1])

    print(npb.plug_output_state(1, True))
