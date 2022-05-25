import asyncio
import logging
import os

from azure.iot.device import MethodResponse
from azure.iot.device.aio import IoTHubDeviceClient, ProvisioningDeviceClient

import pnp_helper
from command import kpi_handler, reboot_handler
from component import DHT11, Analog, LCD, OnOff

from device import Device

logging.basicConfig(level=logging.ERROR)

# TODO: move helpers to a separate file

# Device Setup
root_device = Device(
    manufacturer="CKPD",
    model="RPI Home Basic",
    sw_version="1.0",
    serial="RPI-BASIC-001",
    model_id="dtmi:com:example:rpihome;2"
)

# Components setup
dht11 = DHT11(name="dht11")
fc28 = Analog(name="fc28", label="soil_moisture")


async def send_telemetry_from_temp_controller(device_client, telemetry_msg, component_name=None):
    msg = pnp_helper.create_telemetry(telemetry_msg, component_name)
    await device_client.send_message(msg)
    print("Sent message: {}".format(msg))
    await asyncio.sleep(5)


async def execute_command_listener(
    device_client,
    component_name=None,
    method_name=None,
    user_command_handler=None,
    create_user_response_handler=None,
):
    """
    Coroutine for executing listeners. These will listen for command requests.
    They will take in a user provided handler and call the user provided handler
    according to the command request received.
    :param device_client: The device client
    :param component_name: The name of the device like "sensor"
    :param method_name: (optional) The specific method name to listen for. Eg could be "blink", "turnon" etc.
    If not provided the listener will listen for all methods.
    :param user_command_handler: (optional) The user provided handler that needs to be executed after receiving "command requests".
    If not provided nothing will be executed on receiving command.
    :param create_user_response_handler: (optional) The user provided handler that will create a response.
    If not provided a generic response will be created.
    :return:
    """
    while True:
        if component_name and method_name:
            command_name = component_name + "*" + method_name
        elif method_name:
            command_name = method_name
        else:
            command_name = None

        command_request = await device_client.receive_method_request(command_name)
        values = command_request.payload
        print("Command request received with payload: {}".format(values))

        if user_command_handler:
            await user_command_handler(values)
        else:
            print("No handler provided to execute")

        (response_status, response_payload) = pnp_helper.create_response_payload_with_status(
            command_request, method_name, create_user_response=create_user_response_handler
        )

        command_response = MethodResponse.create_from_method_request(
            command_request, response_status, response_payload
        )

        try:
            await device_client.send_method_response(command_response)
        except Exception:
            print(
                "responding to the {command} command failed".format
                (
                    command=method_name
                )
            )

# PROPERTY TASKS


async def execute_property_listener(device_client):
    while True:
        patch = await device_client.receive_twin_desired_properties_patch()  # blocking call
        print(patch)
        properties_dict = pnp_helper.create_reported_properties_from_desired(
            patch)

        await device_client.patch_twin_reported_properties(properties_dict)


def stdin_listener():
    """
    Listener for quitting the sample
    """
    while True:
        selection = input("Press Q to quit\n")
        if selection == "Q" or selection == "q":
            print("Quitting...")
            break


async def provision_device(provisioning_host, id_scope, registration_id, symmetric_key, model_id):
    provisioning_device_client = ProvisioningDeviceClient.create_from_symmetric_key(
        provisioning_host=provisioning_host,
        registration_id=registration_id,
        id_scope=id_scope,
        symmetric_key=symmetric_key,
    )

    provisioning_device_client.provisioning_payload = {"modelId": model_id}
    return await provisioning_device_client.register()


async def main():
    switch = os.getenv("IOTHUB_DEVICE_SECURITY_TYPE")
    if switch == "DPS":
        provisioning_host = (
            os.getenv("IOTHUB_DEVICE_DPS_ENDPOINT")
            if os.getenv("IOTHUB_DEVICE_DPS_ENDPOINT")
            else "global.azure-devices-provisioning.net"
        )
        id_scope = os.getenv("IOTHUB_DEVICE_DPS_ID_SCOPE")
        registration_id = os.getenv("IOTHUB_DEVICE_DPS_DEVICE_ID")
        symmetric_key = os.getenv("IOTHUB_DEVICE_DPS_DEVICE_KEY")

        registration_result = await provision_device(
            provisioning_host, id_scope, registration_id, symmetric_key, root_device.model_id
        )

        if registration_result.status == "assigned":
            print("Device was assigned")
            print(registration_result.registration_state.assigned_hub)
            print(registration_result.registration_state.device_id)
            device_client = IoTHubDeviceClient.create_from_symmetric_key(
                symmetric_key=symmetric_key,
                hostname=registration_result.registration_state.assigned_hub,
                device_id=registration_result.registration_state.device_id,
                product_info=root_device.model_id,
            )
        else:
            raise RuntimeError(
                "Could not provision device. Aborting Plug and Play device connection."
            )

    elif switch == "connectionString":
        conn_str = os.getenv("IOTHUB_DEVICE_CONNECTION_STRING")
        print("Connecting using Connection String " + conn_str)
        device_client = IoTHubDeviceClient.create_from_connection_string(
            conn_str, product_info=root_device.model_id
        )
    else:
        raise RuntimeError(
            "At least one choice needs to be made for complete functioning of this sample."
        )

    # Connect the client.
    await device_client.connect()

    ################################################
    # Update readable properties from various components

    properties_root = pnp_helper.create_reported_properties(
        serialNumber=root_device.serial_number
    )

    properties_dht11 = pnp_helper.create_reported_properties(
        dht11.name, lastTemp=98.34, lastHumidity=45.67
    )

    properties_fc28 = pnp_helper.create_reported_properties(
        fc28.name, lastSoilMoisture=48.92
    )

    # DEVICE PROPERTIES
    properties_device_info = pnp_helper.create_reported_properties(
        root_device.info,
        swVersion=root_device.sw_version,
        manufacturer=root_device.manufacturer,
        model=root_device.model,
        osName=root_device.os_name,
        processorArchitecture=root_device.processor_architecture,
        processorManufacturer=root_device.processor_manufacturer,
        totalStorage=root_device.total_storage,
        totalMemory=root_device.total_memory,
    )

    property_updates = asyncio.gather(
        device_client.patch_twin_reported_properties(properties_root),
        device_client.patch_twin_reported_properties(properties_dht11),
        device_client.patch_twin_reported_properties(properties_fc28),
        device_client.patch_twin_reported_properties(properties_device_info),
    )

    # Get all the listeners running
    print("Listening for command requests and property updates")

    listeners = asyncio.gather(
        execute_command_listener(
            device_client, method_name="reboot", user_command_handler=reboot_handler
        ),
        # TODO Add more listeners here AND DELETE KPI LISTENER
        execute_command_listener(
            device_client,
            dht11.name,
            method_name="kpiReport",
            user_command_handler=kpi_handler,
            create_user_response_handler=dht11.kpi_report,
        ),

        execute_command_listener(
            device_client,
            fc28.name,
            method_name="kpiReport",
            user_command_handler=kpi_handler,
            create_user_response_handler=fc28.kpi_report,
        ),

        execute_property_listener(device_client),
    )

    # Function to send telemetry every 8 seconds
    async def send_telemetry():
        print("Sending telemetry from various components")

        while True:
            dht11_msg = dht11.read()
            await send_telemetry_from_temp_controller(
                device_client, dht11_msg, dht11.name
            )

            # Current temperature in Celsius
            fc28_msg = fc28.read(lambda x: x)
            await send_telemetry_from_temp_controller(
                device_client, fc28_msg, fc28.name
            )

            cpu_msg = {"cpu": root_device.get_cpu_usage()}
            await send_telemetry_from_temp_controller(device_client, cpu_msg)

    send_telemetry_task = asyncio.ensure_future(send_telemetry())

    # Run the stdin listener in the event loop
    loop = asyncio.get_running_loop()
    user_finished = loop.run_in_executor(None, stdin_listener)
    # # Wait for user to indicate they are done listening for method calls
    await user_finished

    if not listeners.done():
        listeners.set_result("DONE")

    if not property_updates.done():
        property_updates.set_result("DONE")

    listeners.cancel()
    property_updates.cancel()

    send_telemetry_task.cancel()

    # Finally, shut down the client
    await device_client.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
