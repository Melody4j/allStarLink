#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from allstarlink_realtime_etl import RealtimeETLProcessor


class TestDIMGeoUpdate(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite:///:memory:')
        with self.engine.connect() as conn:
            conn.execute(text('''
                CREATE TABLE dim_nodes (
                    node_id INTEGER PRIMARY KEY,
                    callsign TEXT,
                    owner TEXT,
                    affiliation TEXT,
                    affiliation_type TEXT,
                    country TEXT,
                    continent TEXT,
                    is_active INTEGER,
                    last_seen DATETIME,
                    node_rank TEXT,
                    mobility_type TEXT,
                    first_seen_at DATETIME,
                    update_time DATETIME,
                    latitude REAL,
                    longitude REAL,
                    is_mobile INTEGER
                )
            '''))
            conn.commit()

        self.processor = RealtimeETLProcessor(ods_interval_minutes=60)
        self.processor.engine = self.engine
        self.processor.df_last = pd.DataFrame({
            'node_id': [1, 2, 3, 4],
            'latitude': [40.7128, 34.0522, np.nan, 51.5074],
            'longitude': [-74.0060, -118.2437, np.nan, -0.1278],
            'is_active': [1, 1, 0, 1]
        })

    def test_node_offline_geo_preserve(self):
        # 测试节点下线时不更新DIM表的经纬度
        with self.engine.connect() as conn:
            conn.execute(text('''
                INSERT INTO dim_nodes (node_id, callsign, owner, affiliation, affiliation_type,
                                     country, continent, is_active, last_seen, node_rank,
                                     mobility_type, first_seen_at, update_time, latitude, longitude, is_mobile)
                VALUES (1, 'A', 'Owner1', 'Aff1', 'Personal', 'USA', 'North America', 1, 
                        '2023-01-01', 'Active', 'Fixed', '2023-01-01', '2023-01-01', 40.7128, -74.0060, 0)
            '''))
            conn.commit()

        df_now = pd.DataFrame({
            'node_id': [1, 2, 3, 4],
            'latitude': [np.nan, 34.0522, np.nan, 51.5074],
            'longitude': [np.nan, -118.2437, np.nan, -0.1278],
            'is_active': [0, 1, 0, 1],
            'callsign': ['A', 'B', 'C', 'D'],
            'owner': ['Owner1', 'Owner2', 'Owner3', 'Owner4'],
            'affiliation': ['Aff1', 'Aff2', 'Aff3', 'Aff4'],
            'last_seen': pd.to_datetime(['2023-01-01', '2023-01-01', '2023-01-01', '2023-01-01'])
        })

        self.processor._upsert_dim_nodes_preserve_geo(df_now)

        with self.engine.connect() as conn:
            result = conn.execute(
                text('SELECT node_id, latitude, longitude, is_active FROM dim_nodes WHERE node_id = 1'))
            row = result.fetchone()
            self.assertEqual(row[1], 40.7128)  # latitude保留原值
            self.assertEqual(row[2], -74.0060)  # longitude保留原值
            self.assertEqual(row[3], 0)  # is_active已更新为0


if __name__ == '__main__':
    unittest.main()
