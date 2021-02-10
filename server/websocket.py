#!/usr/bin/env python

from influxdb import InfluxDBClient
from subprocess import check_output
from datetime import datetime
from multiprocessing import Process
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
    print(clients)

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

async def run_tasks():
    tasks = []
    categories = run_script("get_categories")
    for category in categories:
        task = asyncio.ensure_future(get_and_send_data_async(category))
        tasks.append(task)

    statistics = run_script("get_statistics")
    for statistic in statistics:
        task = asyncio.ensure_future(store_data(statistic))
        tasks.append(task)

    await asyncio.gather(*tasks)
    
future = asyncio.ensure_future(run_tasks())
loop.run_until_complete(future)
