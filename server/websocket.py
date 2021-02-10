#!/usr/bin/env python

from influxdb import InfluxDBClient
from subprocess import check_output
from datetime import datetime
import asyncio
import websockets
import traceback
import json
import time

clients = set()

def run_script(data_type):
    script_output = check_output(['sh', 'server_stats.sh', data_type]).decode("utf-8")
    return json.loads(script_output)

async def send_to_clients(data):
    for client in clients:
        await client.send(json.dumps(data))
    
async def ws_handler(websocket, path):
    clients.add(websocket)
    print(clients)
    await websocket.wait_closed()
    clients.remove(websocket)

start_server = websockets.serve(ws_handler, "localhost", 8081)
    
loop = asyncio.get_event_loop()
loop.run_until_complete(start_server)

async def get_and_send_data_async(json):
    while True:
        try:
            before=time.time()
            data = run_script(json["id"])
            await send_to_clients(data)
        except Exception:
            print(traceback.format_exc())
        finally:
            after=time.time()
            await asyncio.sleep(json["interval"] - (after - before))

async def store_data(json):
    while True:
        try:
            before=time.time()
            run_script(json["id"])
        except Exception:
            print(traceback.format_exc())
        finally:
            after=time.time()
            await asyncio.sleep(json["interval"] - (after - before))

def get_categories_and_run_in_intervals():
    categories = run_script("get_categories")
    for category in categories:
        loop.create_task(get_and_send_data_async(category))

def get_statistics_and_run_in_intervals():
    statistics = run_script("get_statistics")
    print(statistics)
    for statistic in statistics:
        loop.create_task(store_data(statistic))

get_statistics_and_run_in_intervals()
get_categories_and_run_in_intervals()

loop.run_forever()
