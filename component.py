from random import randint


"""
Generic single analog device class
"""


class Analog(object):
    def __init__(self, name, pin=18, label="value"):
        """
        :param name: name of the sensor
        :param pin: pin number
        :param label: label of the sensor
        """
        self.name = name
        self.pin = pin
        self.value = None

        self.labels = {
            "value": label,
            "max_value": "max_" + label,
            "min_value": "min_" + label,
            "avg_value": "avg_" + label
        }

    def read(self, transform):
        """
        :param transform: transform function to be applied to the value
        :return: a dictionary with the value and the label
        """
        r = randint(10, 90)
        self.value = transform(r)

        response_data = {
            self.labels["value"]: self.value
        }
        return response_data

    # THIS IS UNNECESSARY DUE TO IOT CENTRAL IS ABLE TO DO THIS
    # USE IT JUS AS EXAMPLE FRO FUTURE IMPLEMENTATIONS
    def kpi_report(self, payload):
        response_data = {
            self.labels["max_value"]: self.value,
            self.labels["min_value"]: self.value,
            self.labels["avg_value"]: self.value
        }
        return response_data


class DHT11(object):
    def __init__(self, name, pin=18):
        self.name = name
        self.pin = pin
        self.temperature = None
        self.humidity = None

    def read(self):
        """
        Reads the temperature and humidity from the sensor

        :return: A dictionary with the following keys:
            - temperature
            - humidity
        """
        self.temperature = randint(10, 30)
        self.humidity = randint(10, 90)

        response_data = {
            "temperature": self.temperature,
            "humidity": self.humidity
        }
        return response_data

    def kpi_report(self, payload):
        response_data = {
            "max_temp": self.temperature,
            "min_temp": self.temperature,
            "avg_temp": self.temperature,
            "max_humidity": self.humidity,
            "min_humidity": self.humidity,
            "avg_humidity": self.humidity
        }
        return response_data


class LCD(object):
    def __init__(self, name, pin=18):
        self.name = name
        self.pin = pin
        self.state = False

    def report(self):
        response_data = {
            "state": self.state
        }
        return response_data


"""
On/Off devices class
"""


class OnOff(object):
    def __init__(self, name, pin=18):
        self.name = name
        self.pin = pin
        self.state = False

    def report(self):
        response_data = {
            "state": self.state
        }
        return response_data

    def update(self):
        # TODO: update the state of the device
        self.state = not self.state
