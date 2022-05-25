from psutil import cpu_percent, disk_usage, virtual_memory
from platform import system, processor, machine


class Device(object):
    def __init__(self, manufacturer, model, sw_version, serial, model_id):
        self.model_id = model_id
        self.info = "deviceInformation"
        self.sw_version = sw_version
        self.manufacturer = manufacturer
        self.model = model
        self.os_name = system()
        self.processor_architecture = machine()
        self.processor_manufacturer = processor()

        # Cambiar a path donde se encuentra la base de datos
        self.total_storage = disk_usage("/").total
        self.total_memory = virtual_memory().total
        self.serial_number = serial

    def get_cpu_usage(self):
        return cpu_percent()
