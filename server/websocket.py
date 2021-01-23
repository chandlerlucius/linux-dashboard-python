#!/usr/bin/env python

from influxdb import InfluxDBClient
from subprocess import check_output
from datetime import datetime
import asyncio
import websockets
import traceback
import json
import time
from transaction import Transaction

clients = set()
transaction = Transaction()

async def run_async_function_with_interval(function, parameter, interval):
    while True:
        try:
            await function(parameter)
        except Exception:
            print(traceback.format_exc())
        finally:
            await asyncio.sleep(1)

async def get_and_send_data(data_function):
        data = await data_function()
        await send_to_clients(data)

async def get_cpu_usage():
    return await transaction.query_usage_from_db('cpu', ['cpu_usage'])

async def get_mem_usage():
    return await transaction.query_usage_from_db('memory', ['mem_usage', 'swap_usage'])

async def get_disk_usage():
    return await transaction.query_usage_from_db('disk', ['disk_usage'])

async def run_script(function):
    return check_output(['sh', 'server_stats.sh', function]).decode("utf-8")
    
async def calculate_and_store_cpu_usage(parameter):
    curr_cpu_idle_total = run_script('cpu_idle_total')
    curr_cpu_idle_total_json = json.loads(curr_cpu_idle_total)
    curr_cpu_idle = curr_cpu_idle_total_json['cpu_idle']
    curr_cpu_total = curr_cpu_idle_total_json['cpu_total']

    prev_cpu_idle_total_dict = await transaction.query_last_record_from_db('cpu')
    prev_cpu_idle = prev_cpu_idle_total_dict['cpu_idle'] if 'cpu_idle' in prev_cpu_idle_total_dict else 0
    prev_cpu_total = prev_cpu_idle_total_dict['cpu_total'] if 'cpu_total' in prev_cpu_idle_total_dict else 0

    cpu_total = curr_cpu_total - prev_cpu_total
    cpu_idle = curr_cpu_idle - prev_cpu_idle
    cpu_usage = (cpu_total - cpu_idle) * 100 / cpu_total

    current = [{
        "measurement" : "cpu",
        "time": datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
        "fields": {
            "cpu_idle": curr_cpu_idle,
            "cpu_total": curr_cpu_total,
            "cpu_usage": cpu_usage
        }
    }]
    await transaction.write_to_db(current)

async def calculate_and_store_mem_usage(parameter):
    curr_mem_available_total = run_script('mem_available_total')
    curr_mem_available_total_json = json.loads(curr_mem_available_total)
    curr_mem_available = curr_mem_available_total_json['mem_available']
    curr_mem_total = curr_mem_available_total_json['mem_total']
    curr_swap_available = curr_mem_available_total_json['swap_available']
    curr_swap_total = curr_mem_available_total_json['swap_total']

    db_client = InfluxDBClient(host='localhost', port=8086, database='system_stats')
    db_client.create_database('system_stats')

    mem_usage = (curr_mem_total - curr_mem_available) / curr_mem_total * 100 if curr_mem_total > 0 else 1
    swap_usage = (curr_swap_total - curr_swap_available) / curr_swap_total * 100 if curr_swap_total > 0 else 1

    current = [{
        "measurement" : "memory",
        "time": datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
        "fields": {
            "mem_available": curr_mem_available,
            "mem_total": curr_mem_total,
            "mem_usage": mem_usage,
            "swap_available": curr_swap_available,
            "swap_total": curr_swap_total,
            "swap_usage": swap_usage
        }
    }]
    await transaction.write_to_db(current)
    
async def calculate_and_store_disk_usage(parameter):
    io_millis = check_output(['sh', 'server_stats.sh', 'disk_info']).decode("utf-8")
    io_millis_json = json.loads(io_millis)
    curr_io_millis = io_millis_json['io_millis']
    
    prev_io_millis_dict = await transaction.query_last_record_from_db('disk')
    prev_millis = prev_io_millis_dict['io_millis'] if 'io_millis' in prev_io_millis_dict else 0
    
    curr_time = datetime.utcnow()
    prev_time = datetime.strptime(prev_io_millis_dict['time'], '%Y-%m-%dT%H:%M:%SZ') if 'time' in prev_io_millis_dict else datetime.utcnow()

    disk_usage = (curr_io_millis - prev_millis) * 100 / ((curr_time - prev_time).total_seconds() * 1000)

    current = [{
        "measurement" : "disk",
        "time": curr_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
        "fields": {
            "io_millis": curr_io_millis,
            "disk_usage": disk_usage
        }
    }]
    await transaction.write_to_db(current)

async def send_to_clients(json):
    for client in clients:
        await client.send(json)
    
async def counter(websocket, path):
    clients.add(websocket)
    print(clients)
    await websocket.wait_closed()
    clients.remove(websocket)

start_server = websockets.serve(counter, "localhost", 8081)
    
loop = asyncio.get_event_loop()
loop.run_until_complete(start_server)
loop.create_task(run_async_function_with_interval(get_and_send_data, get_cpu_usage, 1))
loop.create_task(run_async_function_with_interval(get_and_send_data, get_mem_usage, 1))
loop.create_task(run_async_function_with_interval(get_and_send_data, get_disk_usage, 1))
loop.create_task(run_async_function_with_interval(calculate_and_store_cpu_usage, 1, 1))
loop.create_task(run_async_function_with_interval(calculate_and_store_mem_usage, 1, 1))
loop.create_task(run_async_function_with_interval(calculate_and_store_disk_usage, 1, 1))
loop.run_forever()
