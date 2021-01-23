#!/usr/bin/env python
 
from influxdb import InfluxDBClient
import json

class Transaction:

    TIME_PERIOD = '5m'

    def __init__(self):
        self.db_client = InfluxDBClient(host='localhost', port=8086, database='system_stats')
        self.db_client.create_database('system_stats')

    async def query_usage_from_db(self, table, fields):
        query = 'SELECT ' + ','.join(fields) + ' FROM ' + table + ' WHERE time > now() - ' + Transaction.TIME_PERIOD
        data = self.db_client.query(query) 
        data.raw['series'][0]['type'] = 'status'
        data.raw['series'][0]['max'] = 100
        data.raw['series'][0]['suffix'] = '%'
        return json.dumps(data.raw['series'][0])

    async def query_last_record_from_db(self, table):
        query = 'SELECT * FROM ' + table + ' GROUP BY * ORDER BY DESC LIMIT 1'
        data = self.db_client.query(query) 
        return next(iter(list(data.get_points())), {})

    async def write_to_db(self, data):
        self.db_client.write_points(data)