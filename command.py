async def reboot_handler(values):
    if values:
        print("Rebooting after delay of {} secs".format(values))


async def kpi_handler(values):
    if values:
        print("Will return the Kpi report {}".format(values))
