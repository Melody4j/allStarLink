#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AllStarLink 准实时ETL爬虫
实现"每分钟爬取、内存对比异动、按需写入数据库"的准实时ETL流程

# Data Architecture
1. ODS (ods_asl_nodes_snapshot): 全量快照表，按指定间隔写入
2. DWD (dwd_node_events_fact): 事件事实表，仅在节点状态/位置变化时即时写入
3. DIM (dim_nodes): 实体维度表，实时Upsert最新属性

# Core Logic (Plan C: Pandas In-Memory Diff)
- 全局状态缓存：内存中保留df_last变量
- 异动检测逻辑：向量化比对df_now和df_last
- 按需写入：仅将变动数据写入DWD和DIM
- 归档策略：按配置间隔全量写入ODS
"""

import time
import datetime
import argparse
import signal
import sys
import threading
import traceback
import re
from typing import Optional, Dict, List, Tuple

import requests
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text, MetaData, Table
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.pool import QueuePool
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# 数据库配置
DB_CONFIG = {
    'host': '121.41.230.15',
    'user': 'root',
    'password': '0595',
    'database': 'allStarLink',
    'charset': 'utf8mb4'
}

# API端点
API_URL = "https://www.allstarlink.org/nodelist/nodelist-server.php"
MAP_DATA_URL = "https://stats.allstarlink.org/api/stats/mapData"

# 地理位移阈值（度）
GEO_MOVE_THRESHOLD = 0.005

# 数据库连接字符串
DATABASE_URL = f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}/{DB_CONFIG['database']}?charset={DB_CONFIG['charset']}"


class RealtimeETLProcessor:
    """准实时ETL处理器"""

    def __init__(self, ods_interval_minutes: int = 60):
        """
        初始化ETL处理器

        Args:
            ods_interval_minutes: ODS快照写入间隔（分钟），默认60分钟
        """
        # 数据库连接池
        self.engine = create_engine(
            DATABASE_URL,
            pool_pre_ping=True,
            pool_recycle=3600,
            pool_size=5,
            max_overflow=10,
            poolclass=QueuePool
        )

        # 配置参数
        self.ods_interval_minutes = ods_interval_minutes

        # 全局状态缓存 - 核心内存状态
        self.df_last: Optional[pd.DataFrame] = None

        # 运行状态控制
        self.running = True
        self.last_ods_write: Optional[datetime.datetime] = None

        # 性能监控
        self.stats = {
            'total_cycles': 0,
            'successful_cycles': 0,
            'failed_cycles': 0,
            'last_error': None,
            'total_status_changes': 0,
            'total_geo_moves': 0,
            'total_ods_writes': 0
        }

        logger.info(f"RealtimeETLProcessor initialized with ODS interval: {ods_interval_minutes} minutes")

    def extract_raw_data(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """提取原始数据"""
        logger.debug("Starting data extraction...")

        try:
            # 1. 抓取节点列表数据
            response_nodes = requests.get(API_URL, timeout=30)
            response_nodes.raise_for_status()
            nodes_data = response_nodes.json()
            df_nodes = pd.DataFrame(nodes_data)

            # 2. 抓取地图数据
            response_map = requests.get(MAP_DATA_URL, timeout=30)
            response_map.raise_for_status()

            # 解析地图数据
            map_lines = response_map.text.strip().split('\n')[1:]  # 跳过表头
            map_records = []

            for line in map_lines:
                if not line.strip():
                    continue
                parts = line.split('\t')
                if len(parts) >= 4:
                    try:
                        node_id = int(parts[0].strip())
                        lat = float(parts[2].strip())
                        lon = float(parts[3].strip())

                        # 验证坐标有效性
                        if (-90 <= lat <= 90 and -180 <= lon <= 180 and
                            not (lat == 0.0 and lon == 0.0)):
                            map_records.append({
                                'node_id': node_id,
                                'latitude': lat,
                                'longitude': lon
                            })
                    except (ValueError, IndexError):
                        continue

            df_map = pd.DataFrame(map_records)

            logger.debug(f"Extracted {len(df_nodes)} nodes, {len(df_map)} geo records")
            return df_nodes, df_map

        except Exception as e:
            logger.error(f"Data extraction failed: {e}")
            raise

    def get_continent_country(self, lat, lon):
        """根据经纬度获取洲和国家信息"""
        if pd.isna(lat) or pd.isna(lon) or (lat == 0.0 and lon == 0.0):
            return 'Unknown', 'Unknown'

        try:
            continent = 'Unknown'
            country = 'Unknown'

            # 北美洲详细划分
            if 15 <= lat <= 85 and -180 <= lon <= -50:
                continent = 'North America'
                if 24 <= lat <= 49 and -125 <= lon <= -66:
                    if lat >= 49 or lon <= -95:
                        country = 'Canada' if lat >= 49 else 'United States'
                    else:
                        country = 'United States'
                elif 14 <= lat <= 32 and -118 <= lon <= -86:
                    country = 'Mexico'
                elif 10 <= lat <= 30 and -90 <= lon <= -60:
                    country = 'Central America'
                elif 60 <= lat <= 85:
                    country = 'Canada'

            # 南美洲
            elif -56 <= lat <= 15 and -82 <= lon <= -34:
                continent = 'South America'
                if -35 <= lat <= 5 and -74 <= lon <= -48:
                    country = 'Brazil'
                elif -55 <= lat <= -21 and -74 <= lon <= -53:
                    country = 'Argentina'
                else:
                    country = 'South America'

            # 欧洲详细划分
            elif 35 <= lat <= 72 and -10 <= lon <= 70:
                continent = 'Europe'
                if 36 <= lat <= 70 and -10 <= lon <= 32:
                    if 49 <= lat <= 60 and -8 <= lon <= 2:
                        country = 'United Kingdom'
                    elif 42 <= lat <= 51 and -5 <= lon <= 10:
                        country = 'France'
                    elif 47 <= lat <= 55 and 6 <= lon <= 17:
                        country = 'Germany'
                    elif 55 <= lat <= 69 and 4 <= lon <= 32:
                        country = 'Scandinavia'
                    else:
                        country = 'Europe'
                elif 41 <= lat <= 70 and 19 <= lon <= 70:
                    country = 'Eastern Europe'

            # 亚洲详细划分
            elif -11 <= lat <= 80 and 25 <= lon <= 180:
                continent = 'Asia'
                if 20 <= lat <= 54 and 73 <= lon <= 135:
                    country = 'China'
                elif 24 <= lat <= 46 and 123 <= lon <= 146:
                    country = 'Japan'
                elif 50 <= lat <= 80 and 19 <= lon <= 180:
                    country = 'Russia'
                elif 6 <= lat <= 37 and 68 <= lon <= 98:
                    country = 'India'
                elif -11 <= lat <= 20 and 95 <= lon <= 141:
                    country = 'Southeast Asia'
                elif 12 <= lat <= 42 and 26 <= lon <= 45:
                    country = 'Middle East'
                else:
                    country = 'Asia'

            # 非洲
            elif -35 <= lat <= 38 and -18 <= lon <= 52:
                continent = 'Africa'
                if -35 <= lat <= -22 and 16 <= lon <= 33:
                    country = 'South Africa'
                elif -26 <= lat <= 38 and -18 <= lon <= 52:
                    country = 'Africa'

            # 大洋洲
            elif -48 <= lat <= -9 and 110 <= lon <= 180:
                continent = 'Oceania'
                if -44 <= lat <= -9 and 113 <= lon <= 154:
                    country = 'Australia'
                elif -47 <= lat <= -34 and 166 <= lon <= 179:
                    country = 'New Zealand'
                else:
                    country = 'Oceania'

            # 南极洲
            elif lat < -60:
                continent = 'Antarctica'
                country = 'Antarctica'

            return continent, country

        except Exception as e:
            logger.warning(f"地理信息获取异常 lat={lat}, lon={lon}: {e}")
            return 'Unknown', 'Unknown'

    def classify_affiliation_type(self, affiliation, callsign):
        """对affiliation进行分类"""
        if pd.isna(affiliation):
            return 'Personal'

        affiliation = str(affiliation).lower().strip()
        callsign = str(callsign).lower().strip() if not pd.isna(callsign) else ''

        # 冲突处理：affiliation与callsign完全一致时标记为Personal
        if affiliation == callsign and affiliation != '':
            return 'Personal'

        # 组织关键词匹配
        org_keywords = ['club', 'arc', 'network', 'system', 'link', 'org', 'group', 'hub']
        for keyword in org_keywords:
            if keyword in affiliation:
                return 'Organization'

        # 域名后缀匹配（排除频率值）
        domain_pattern = r'\.(org|net|com|edu|gov)$'
        if re.search(domain_pattern, affiliation) and not re.match(r'^\d+(\.\d+)?$', affiliation):
            return 'Organization'

        return 'Personal'

    def transform_and_standardize(self, df_nodes: pd.DataFrame, df_map: pd.DataFrame) -> pd.DataFrame:
        """数据转换和标准化"""
        logger.debug("Starting data transformation...")

        try:
            # 1. 重命名和类型转换
            df_nodes = df_nodes.rename(columns={'name': 'node_id'})
            df_nodes['node_id'] = df_nodes['node_id'].astype(int)

            # 2. 左连接获取地理信息
            df_merged = df_nodes.merge(df_map, on='node_id', how='left')

            # 3. 核心字段计算 - 向量化处理
            df_merged['is_active'] = (~df_merged['latitude'].isna()).astype(int)

            # 4. 标准化字段映射
            df_final = df_merged.rename(columns={
                'User_ID': 'owner',
                'callsign': 'callsign',
                'node_frequency': 'frequency',
                'node_tone': 'tone',
                'Location': 'location',
                'SiteName': 'site',
                'Affiliation': 'affiliation',
                'regseconds': 'regseconds'
            })

            # 5. 时间字段处理
            df_final['last_seen'] = pd.to_datetime(df_final['regseconds'], unit='s', errors='coerce')

            # 6. 向量化地理增强
            logger.debug("Enhancing geographical data...")
            geo_data = df_final[['latitude', 'longitude']].apply(
                lambda row: self.get_continent_country(row['latitude'], row['longitude']),
                axis=1, result_type='expand'
            )
            df_final[['continent', 'country']] = geo_data

            # 7. 向量化组织分类
            logger.debug("Classifying organization types...")
            df_final['affiliation_type'] = df_final.apply(
                lambda row: self.classify_affiliation_type(row['affiliation'], row['callsign']),
                axis=1
            )

            # 8. Features字段生成
            def generate_features(row):
                features = []
                if row.get('access_webtransceiver') == '1':
                    features.append('Webtransceiver')
                if row.get('access_telephoneportal') == '1':
                    features.append('Telephone Portal')
                return ', '.join(features)

            df_final['features'] = df_final.apply(generate_features, axis=1)

            # 9. 选择核心字段用于状态比较
            core_columns = [
                'node_id', 'owner', 'callsign', 'frequency', 'tone',
                'location', 'site', 'affiliation', 'last_seen', 'features',
                'latitude', 'longitude', 'is_active', 'country', 'continent', 'affiliation_type'
            ]

            df_standardized = df_final[core_columns].copy()

            # 10. 数据清洗
            df_standardized = df_standardized.fillna({
                'owner': '',
                'callsign': '',
                'frequency': '',
                'tone': '',
                'location': '',
                'site': '',
                'affiliation': '',
                'features': '',
                'country': 'Unknown',
                'continent': 'Unknown',
                'affiliation_type': 'Personal'
            })

            logger.debug(f"Transformation completed, {len(df_standardized)} records")
            return df_standardized

        except Exception as e:
            logger.error(f"Data transformation failed: {e}")
            raise

    def detect_and_save_changes(self, df_now: pd.DataFrame) -> Dict:
        """核心异动检测和保存逻辑"""
        logger.debug("Starting change detection...")

        changes_summary = {
            'status_changes': 0,
            'geo_moves': 0,
            'dim_updates': 0,
            'new_nodes': 0
        }

        try:
            # 如果是首次运行，初始化状态缓存
            if self.df_last is None:
                logger.info("First run: initializing memory cache")
                self.df_last = df_now.copy()
                changes_summary['new_nodes'] = len(df_now)

                # 首次运行时，全量更新DIM表
                self._upsert_dim_nodes(df_now)
                changes_summary['dim_updates'] = len(df_now)

                return changes_summary

            # ========== 核心异动检测逻辑 ==========
            # 使用pandas向量化操作进行内存比对

            # 1. 合并当前数据和缓存数据
            df_comparison = pd.merge(
                df_now[['node_id', 'is_active', 'latitude', 'longitude']],
                self.df_last[['node_id', 'is_active', 'latitude', 'longitude']],
                on='node_id',
                how='outer',  # 外连接，包含新增和删除的节点
                suffixes=('_now', '_last'),
                indicator=True
            )

            # 2. 状态变动检测（向量化）
            status_change_mask = (
                (df_comparison['_merge'] == 'both') &  # 存在于两个数据集
                (df_comparison['is_active_now'] != df_comparison['is_active_last'])
            )
            df_status_changes = df_comparison[status_change_mask]

            # 3. 地理位移检测（向量化）
            # 先填充NaN值为0以便计算
            df_comparison['lat_now'] = pd.to_numeric(df_comparison['latitude_now'], errors='coerce').fillna(0)
            df_comparison['lon_now'] = pd.to_numeric(df_comparison['longitude_now'], errors='coerce').fillna(0)
            df_comparison['lat_last'] = pd.to_numeric(df_comparison['latitude_last'], errors='coerce').fillna(0)
            df_comparison['lon_last'] = pd.to_numeric(df_comparison['longitude_last'], errors='coerce').fillna(0)

            # 计算坐标差异
            df_comparison['lat_diff'] = np.abs(df_comparison['lat_now'] - df_comparison['lat_last'])
            df_comparison['lon_diff'] = np.abs(df_comparison['lon_now'] - df_comparison['lon_last'])

            # 地理位移条件
            geo_move_mask = (
                (df_comparison['_merge'] == 'both') &
                ((df_comparison['lat_diff'] > GEO_MOVE_THRESHOLD) |
                 (df_comparison['lon_diff'] > GEO_MOVE_THRESHOLD)) &
                (df_comparison['lat_now'] != 0) & (df_comparison['lon_now'] != 0) &  # 当前坐标有效
                (df_comparison['lat_last'] != 0) & (df_comparison['lon_last'] != 0)  # 历史坐标有效
            )
            df_geo_moves = df_comparison[geo_move_mask]

            # 4. 新增节点检测
            new_nodes_mask = df_comparison['_merge'] == 'left_only'
            df_new_nodes = df_comparison[new_nodes_mask]

            # ========== 按需写入数据库 ==========

            current_time = datetime.datetime.now()

            # 5. 写入DWD事件表（仅变动数据）
            events = []

            # 状态变化事件
            for _, row in df_status_changes.iterrows():
                events.append({
                    'node_id': int(row['node_id']),
                    'event_type': 'status_change',
                    'attr_name': 'is_active',
                    'old_value': str(int(row['is_active_last'])),
                    'new_value': str(int(row['is_active_now'])),
                    'event_time': current_time
                })

            # 地理位移事件
            for _, row in df_geo_moves.iterrows():
                old_coord = f"{row['latitude_last']},{row['longitude_last']}"
                new_coord = f"{row['latitude_now']},{row['longitude_now']}"
                events.append({
                    'node_id': int(row['node_id']),
                    'event_type': 'geo_move',
                    'attr_name': 'coordinates',
                    'old_value': old_coord,
                    'new_value': new_coord,
                    'event_time': current_time
                })

            # 批量写入事件
            if events:
                df_events = pd.DataFrame(events)
                df_events.to_sql(
                    'dwd_node_events_fact',
                    con=self.engine,
                    if_exists='append',
                    index=False,
                    method='multi'
                )
                logger.info(f"Inserted {len(events)} events to DWD")

            # 6. 更新DIM表（仅变动节点）
            changed_node_ids = set()
            changed_node_ids.update(df_status_changes['node_id'].tolist())
            changed_node_ids.update(df_geo_moves['node_id'].tolist())
            changed_node_ids.update(df_new_nodes['node_id'].tolist())

            if changed_node_ids:
                df_changed = df_now[df_now['node_id'].isin(changed_node_ids)]
                self._upsert_dim_nodes(df_changed)
                changes_summary['dim_updates'] = len(changed_node_ids)
                logger.info(f"Updated {len(changed_node_ids)} nodes in DIM")

            # 7. 更新状态缓存 - 异常处理确保不清空缓存
            self.df_last = df_now.copy()

            # 8. 统计摘要
            changes_summary['status_changes'] = len(df_status_changes)
            changes_summary['geo_moves'] = len(df_geo_moves)
            changes_summary['new_nodes'] = len(df_new_nodes)

            # 9. 更新全局统计
            self.stats['total_status_changes'] += changes_summary['status_changes']
            self.stats['total_geo_moves'] += changes_summary['geo_moves']

            logger.info(f"Change detection completed: {changes_summary}")
            return changes_summary

        except Exception as e:
            logger.error(f"Change detection failed: {e}")
            logger.error(traceback.format_exc())
            # 异常时不清空df_last缓存
            raise

    def _upsert_dim_nodes(self, df: pd.DataFrame):
        """更新DIM表（使用ON DUPLICATE KEY UPDATE）"""
        try:
            # 准备DIM表数据
            df_dim = df.copy()
            df_dim['update_time'] = datetime.datetime.now()

            # 添加DIM表需要的字段（优先使用已处理的数据）
            if 'affiliation_type' not in df_dim.columns:
                df_dim['affiliation_type'] = 'Personal'
            if 'country' not in df_dim.columns:
                df_dim['country'] = 'Unknown'
            if 'continent' not in df_dim.columns:
                df_dim['continent'] = 'Unknown'
            df_dim['node_rank'] = 'Active'  # 默认活跃节点
            df_dim['mobility_type'] = 'Fixed'  # 默认固定节点
            df_dim['first_seen_at'] = df_dim['last_seen']  # 使用last_seen作为首次时间
            df_dim['is_mobile'] = 0  # 默认非移动节点

            # 选择DIM表字段（匹配实际表结构）
            dim_columns = [
                'node_id', 'callsign', 'owner', 'affiliation', 'affiliation_type',
                'country', 'continent', 'is_active', 'last_seen', 'node_rank',
                'mobility_type', 'first_seen_at', 'update_time', 'latitude',
                'longitude', 'is_mobile'
            ]

            df_dim_final = df_dim[dim_columns].copy()

            # 分批处理
            batch_size = 1000
            for i in range(0, len(df_dim_final), batch_size):
                batch_df = df_dim_final.iloc[i:i + batch_size]

                # 使用自定义upsert方法
                batch_df.to_sql(
                    'dim_nodes',
                    con=self.engine,
                    if_exists='append',
                    index=False,
                    method=self._mysql_upsert_method
                )

        except Exception as e:
            logger.error(f"DIM upsert failed: {e}")
            raise

    def _mysql_upsert_method(self, pd_table, conn, keys, data_iter):
        """MySQL UPSERT实现"""
        data = [dict(zip(keys, row)) for row in data_iter]

        stmt = insert(pd_table.table).values(data)
        update_dict = {c.name: c for c in stmt.inserted if c.name != 'node_id'}
        on_duplicate_key_stmt = stmt.on_duplicate_key_update(update_dict)

        result = conn.execute(on_duplicate_key_stmt)
        return result.rowcount

    def should_write_ods(self) -> bool:
        """检查是否应该写入ODS快照"""
        if self.last_ods_write is None:
            return True

        elapsed_minutes = (datetime.datetime.now() - self.last_ods_write).total_seconds() / 60
        return elapsed_minutes >= self.ods_interval_minutes

    def write_ods_snapshot(self, df: pd.DataFrame):
        """写入ODS快照表（按配置间隔写入）"""
        try:
            batch_id = datetime.datetime.now().strftime('%Y%m%d%H%M')

            df_ods = df.copy()
            df_ods['batch_id'] = batch_id
            df_ods['created_at'] = datetime.datetime.now()

            # 根据实际ODS表结构选择字段（安全映射）
            ods_columns_mapping = {
                'batch_id': 'batch_id',
                'node_id': 'node_id',
                'owner': 'owner',
                'callsign': 'callsign',
                'frequency': 'frequency',
                'tone': 'tone',
                'location': 'location',
                'site': 'site',
                'affiliation': 'affiliation',
                'last_seen': 'last_seen',
                'features': 'features',
                'latitude': 'latitude',
                'longitude': 'longitude',
                'country': 'country',
                'continent': 'continent',
                'is_active': 'is_active',
                'created_at': 'created_at'
            }

            # 安全字段选择 - 只包含表中实际存在的字段
            df_ods_final = pd.DataFrame()
            for col_name, df_col in ods_columns_mapping.items():
                if df_col in df_ods.columns:
                    df_ods_final[col_name] = df_ods[df_col]

            # 特殊处理数值字段
            numeric_columns = ['latitude', 'longitude', 'is_active']
            for col in numeric_columns:
                if col in df_ods_final.columns:
                    # 将NaN转换为None（SQL的NULL）
                    df_ods_final[col] = df_ods_final[col].where(df_ods_final[col].notna(), None)
                    # 确保数值类型正确
                    if col in ['latitude', 'longitude']:
                        df_ods_final[col] = pd.to_numeric(df_ods_final[col], errors='coerce')
                    elif col == 'is_active':
                        df_ods_final[col] = df_ods_final[col].astype('Int64')

            # 处理其他字段的空值（用空字符串替代）
            string_columns = df_ods_final.select_dtypes(include=['object']).columns
            df_ods_final[string_columns] = df_ods_final[string_columns].fillna('')

            # 分批写入
            batch_size = 1000
            total_inserted = 0

            for i in range(0, len(df_ods_final), batch_size):
                batch_df = df_ods_final.iloc[i:i + batch_size]
                batch_df.to_sql(
                    'ods_asl_nodes_snapshot',
                    con=self.engine,
                    if_exists='append',
                    index=False,
                    method='multi'
                )
                total_inserted += len(batch_df)

            self.stats['total_ods_writes'] += 1
            self.last_ods_write = datetime.datetime.now()
            logger.info(f"ODS snapshot written: batch_id={batch_id}, records={len(df_ods_final)}, "
                       f"next write in {self.ods_interval_minutes} minutes")

        except Exception as e:
            logger.error(f"ODS snapshot write failed: {e}")
            raise

    def run_single_cycle(self):
        """运行单次ETL循环"""
        cycle_start = datetime.datetime.now()

        try:
            # 1. 数据提取
            df_nodes, df_map = self.extract_raw_data()

            # 2. 数据转换
            df_now = self.transform_and_standardize(df_nodes, df_map)

            # 3. 异动检测和按需写入
            changes = self.detect_and_save_changes(df_now)

            # 4. 检查是否需要写入ODS（按配置间隔）
            if self.should_write_ods():
                self.write_ods_snapshot(df_now)
                logger.info(f"ODS snapshot completed (interval: {self.ods_interval_minutes} minutes)")

            # 5. 更新统计
            self.stats['successful_cycles'] += 1

            cycle_time = (datetime.datetime.now() - cycle_start).total_seconds()
            logger.info(f"Cycle completed in {cycle_time:.2f}s, changes: {changes}")

            return True

        except Exception as e:
            self.stats['failed_cycles'] += 1
            self.stats['last_error'] = str(e)
            logger.error(f"Cycle failed: {e}")
            return False

        finally:
            self.stats['total_cycles'] += 1

    def run_realtime_loop(self):
        """运行准实时主循环"""
        logger.info(f"Starting realtime ETL loop (1-minute intervals, ODS every {self.ods_interval_minutes} minutes)")

        # 设置信号处理
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, stopping...")
            self.running = False

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        try:
            while self.running:
                loop_start = time.time()

                # 运行单次循环
                success = self.run_single_cycle()

                # 输出统计信息
                if self.stats['total_cycles'] % 10 == 0:  # 每10次输出统计
                    logger.info(f"Stats: Total={self.stats['total_cycles']}, "
                               f"Success={self.stats['successful_cycles']}, "
                               f"Failed={self.stats['failed_cycles']}, "
                               f"StatusChanges={self.stats['total_status_changes']}, "
                               f"GeoMoves={self.stats['total_geo_moves']}, "
                               f"ODSWrites={self.stats['total_ods_writes']}")

                # 计算睡眠时间确保每分钟执行一次
                elapsed = time.time() - loop_start
                sleep_time = max(0, 60 - elapsed)

                if sleep_time > 0:
                    logger.debug(f"Sleeping {sleep_time:.1f}s until next cycle")
                    time.sleep(sleep_time)
                else:
                    logger.warning(f"Cycle took {elapsed:.1f}s, exceeding 60s interval")

        except KeyboardInterrupt:
            logger.info("Received KeyboardInterrupt, stopping gracefully...")
        except Exception as e:
            logger.error(f"Fatal error in main loop: {e}")
            logger.error(traceback.format_exc())
        finally:
            self.running = False
            logger.info("Realtime ETL stopped")
            logger.info(f"Final stats: {self.stats}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='AllStarLink准实时ETL爬虫')
    parser.add_argument('--mode', choices=['single', 'realtime'], default='realtime',
                       help='运行模式：single(单次执行)或realtime(准实时循环)')
    parser.add_argument('--ods-interval', type=int, default=60,
                       help='ODS快照写入间隔（分钟），默认60分钟')

    args = parser.parse_args()

    # 创建ETL处理器
    processor = RealtimeETLProcessor(ods_interval_minutes=args.ods_interval)

    if args.mode == 'single':
        # 单次执行
        logger.info("Running single ETL cycle")
        success = processor.run_single_cycle()
        sys.exit(0 if success else 1)
    else:
        # 准实时循环
        logger.info(f"Starting realtime ETL mode (ODS interval: {args.ods_interval} minutes)")
        processor.run_realtime_loop()


if __name__ == "__main__":
    main()