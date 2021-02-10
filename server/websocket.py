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
    
# async def calculate_and_store_disk_usage(parameter):
#     io_millis = run_script('disk_stats')
#     curr_io_millis = io_millis['io_millis']
    
#     prev_io_millis = await transaction.query_last_record_from_db('disk')
#     prev_millis = prev_io_millis['io_millis'] if 'io_millis' in prev_io_millis else 0
    
#     curr_time = datetime.utcnow()
#     prev_time = datetime.strptime(prev_io_millis['time'], '%Y-%m-%dT%H:%M:%SZ') if 'time' in prev_io_millis else datetime.utcnow()

#     disk_usage = (curr_io_millis - prev_millis) * 100 / ((curr_time - prev_time).total_seconds() * 1000)

#     data = [{
#         "measurement" : "disk",
#         "time": curr_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
#         "fields": {
#             "io_millis": curr_io_millis,
#             "disk_usage": disk_usage
#         }
#     }]
#     await transaction.write_to_db(data)

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
            data = run_script(json["id"])
            await send_to_clients(data)
        except Exception:
            print(traceback.format_exc())
        finally:
            await asyncio.sleep(json["interval"])

async def store_data(json):
    while True:
        try:
            run_script(json["id"])
        except Exception:
            print(traceback.format_exc())
        finally:
            await asyncio.sleep(json["interval"])

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
