#!/usr/bin/python3

import time
import subprocess

import sys
import os
folder = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath("%s/.." % folder))

from pytradfri import Gateway
from pytradfri.api.aiocoap_api import APIFactory
from pytradfri.error import PytradfriError
from pytradfri.util import load_json, save_json
from display import display
import asyncio
import uuid
import logging

CONFIG_FILE = folder+'/lights.conf'
HOST = "home"

def Sort_Light(light_id, light_order):
    # light_order = [65537, 65538, 65541,65539, 65542]
    for idx, x in enumerate(light_order):
        if x == light_id:
            return idx
    return 20

async def run():

    conf = load_json(CONFIG_FILE)

    try:
        identity = conf[HOST].get('identity')
        psk = conf[HOST].get('key')
        ip = conf[HOST].get('ip')
        disp_time = conf[HOST].get('dipslay time')
        logging_level = conf[HOST].get('logging level')
        light_order = conf[HOST].get('light order')
        api_factory = APIFactory(host=ip, psk_id=identity, psk=psk)
    except KeyError:
        identity = uuid.uuid4().hex
        api_factory = APIFactory(host=ip, psk_id=identity)
    
    if logging_level > 5 or logging_level < 0:
        logging_level = 3
    
    logging.basicConfig(format="%(asctime)s %(message)s", level=logging_level*10)
    api = api_factory.request
    gateway = Gateway()
    
    #wait for network while booting
    while True:
        try:
            devices_command = gateway.get_devices()
            devices_command = await api(devices_command)
            break
        except:
            pass
        await asyncio.sleep(2)

    devices = await api(devices_command)        
    lights = [dev for dev in devices if dev.has_light_control]

    for x in lights:
        logging.info(f"{x.path[1]}")

    oled = display(len(lights), disp_time)

    lights_sortet =[]
    for x in lights:
        lights_sortet.append(x)
    
    for idx, x in enumerate(lights):
        lights_sortet[Sort_Light(lights[idx].path[1], light_order)] = x

    for x in lights_sortet:
        logging.info(f"{x.path[1]}")

    def observe_callback(updated_device):
        light = updated_device.light_control.lights[0]
        for i, x in enumerate(lights_sortet):
            if x.light_control.lights[0].device.name == light.device.name:
                print(light.device.name)
                oled.set_status(i,light.state, light.dimmer, updated_device.name)
                # oled.update()
                # oled.show_details(i, updated_device.name)
        logging.info("Received message for: %s" % light)

    def observe_err_callback(err):
        logging.error('observe error:', err)

    if lights:
        light = lights[0]
    else:
        logging.warning("No lights found!")
        light = None

    for light in lights:
        observe_command = light.observe(observe_callback, observe_err_callback)
        # Start observation as a second task on the loop.
        asyncio.ensure_future(api(observe_command))
        # Yield to allow observing to start.
        await asyncio.sleep(0)
    
    for x in range(0, len(lights_sortet)):
        if lights_sortet[x].light_control.lights[0].state == 0:
            oled.set_status(x,0, 0, lights_sortet[x].name)
        else:
            oled.set_status(x,1, lights_sortet[x].light_control.lights[0].dimmer, lights_sortet[x].name)

    oled.update()

    logging.info('obsevering startet')
    while True:
        oled.controler()
        await asyncio.sleep(0.01)
    await api_factory.shutdown()

asyncio.get_event_loop().run_until_complete(run())
