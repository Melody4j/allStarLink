#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AllStarLink数仓ETL爬虫
实现ODS-DWD-DIM三层数据仓库架构
"""

import time
import datetime
import argparse
import schedule
import requests
import pandas as pd
import numpy as np
import re
from sqlalchemy import create_engine, text
from sqlalchemy.dialects.mysql import insert
import logging

# 配置日志 - 修复Windows中文乱码问题
import sys
import locale

# 设置控制台编码
if sys.platform == "win32":
    # Windows平台设置UTF-8编码
    sys.stdout.reconfigure(encoding='utf-8', errors='ignore')
    sys.stderr.reconfigure(encoding='utf-8', errors='ignore')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
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

# 数据库连接字符串
DATABASE_URL = f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}/{DB_CONFIG['database']}?charset={DB_CONFIG['charset']}"


class AllStarLinkETL:
    def __init__(self):
        self.engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=3600)
        self.batch_id = datetime.datetime.now().strftime('%Y%m%d%H%M')

    def extract_data(self):
        """抽取数据层：从API获取节点数据和地图数据"""
        logger.info(f"[{self.batch_id}] Starting data extraction...")

        try:
            # 抓取节点列表数据
            logger.info("Fetching node list data...")
            response_nodes = requests.get(API_URL, timeout=30)
            response_nodes.raise_for_status()
            nodes_data = response_nodes.json()

            # 转换为DataFrame
            df_all = pd.DataFrame(nodes_data)
            logger.info(f"Retrieved {len(df_all)} node records")

            # 抓取地图数据
            logger.info("Fetching map data...")
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

            df_online = pd.DataFrame(map_records)
            logger.info(f"Retrieved {len(df_online)} online nodes with geo data")

            return df_all, df_online

        except Exception as e:
            logger.error(f"Data extraction failed: {e}")
            raise

    def get_continent_country(self, lat, lon):
        """根据经纬度获取洲和国家信息（优化版本）"""
        if pd.isna(lat) or pd.isna(lon) or (lat == 0.0 and lon == 0.0):
            return 'Unknown', 'Unknown'

        try:
            # 精确的地理区域判断
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

    def clean_frequency(self, freq):
        """清理频率字段，仅保留数字"""
        if pd.isna(freq):
            return None

        freq_str = str(freq)
        # 提取数字和小数点
        cleaned = re.sub(r'[^\d.]', '', freq_str)

        try:
            return float(cleaned) if cleaned else None
        except ValueError:
            return None

    def transform_data(self, df_all, df_online):
        """转换数据层：数据清洗、增强、标准化"""
        logger.info(f"[{self.batch_id}] Starting data transformation...")

        # 1. 数据整合：左连接
        # 先重命名df_all中的name字段为node_id
        df_all_renamed = df_all.rename(columns={'name': 'node_id'})
        df_all_renamed['node_id'] = df_all_renamed['node_id'].astype(int)
        df_merged = df_all_renamed.merge(df_online, on='node_id', how='left')

        # 2. 设置is_active标志
        df_merged['is_active'] = (~df_merged['latitude'].isna()).astype(int)

        # 3. 向量化地理增强
        logger.info("Enhancing geographical data...")
        geo_data = df_merged[['latitude', 'longitude']].apply(
            lambda row: self.get_continent_country(row['latitude'], row['longitude']),
            axis=1, result_type='expand'
        )
        df_merged[['continent', 'country']] = geo_data

        # 4. 向量化组织分类
        logger.info("Classifying organization types...")
        df_merged['affiliation_type'] = df_merged.apply(
            lambda row: self.classify_affiliation_type(row['Affiliation'], row['callsign']),
            axis=1
        )

        # 5. 频率字段清理
        df_merged['frequency_clean'] = df_merged['node_frequency'].apply(self.clean_frequency)

        # 6. 时间字段处理
        df_merged['last_seen_dt'] = pd.to_datetime(df_merged['regseconds'], unit='s', errors='coerce')

        # 7. 字段映射和重命名
        df_final = df_merged.rename(columns={
            'User_ID': 'owner',
            'node_frequency': 'frequency',
            'node_tone': 'tone',
            'Location': 'location',
            'SiteName': 'site',
            'Affiliation': 'affiliation',
            'last_seen_dt': 'last_seen',
            'access_webtransceiver': 'webtransceiver',
            'access_telephoneportal': 'telephoneportal'
        })

        # 8. Features字段生成
        def generate_features(row):
            features = []
            if row.get('webtransceiver') == '1':
                features.append('Webtransceiver')
            if row.get('telephoneportal') == '1':
                features.append('Telephone Portal')
            return ', '.join(features)

        df_final['features'] = df_final.apply(generate_features, axis=1)

        # 9. 选择最终字段
        final_columns = [
            'node_id', 'owner', 'callsign', 'frequency', 'tone', 'location',
            'site', 'affiliation', 'last_seen', 'features', 'latitude',
            'longitude', 'is_active', 'country', 'continent', 'affiliation_type'
        ]

        df_final = df_final[final_columns].copy()

        logger.info(f"Data transformation completed, processed {len(df_final)} records")
        return df_final

    def load_to_ods(self, df):
        """加载到ODS层"""
        logger.info(f"[{self.batch_id}] Loading data to ODS layer...")

        try:
            # 准备ODS数据
            df_ods = df.copy()
            df_ods['batch_id'] = self.batch_id
            df_ods['created_at'] = datetime.datetime.now()
            df_ods['updated_at'] = datetime.datetime.now()

            # 根据实际ODS表结构选择和重排字段
            # 注意：不包含'id'字段，因为它是AUTO_INCREMENT
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
                'created_at': 'created_at',
                'updated_at': 'updated_at'
            }

            # 确保字段顺序与表结构匹配
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
                        df_ods_final[col] = df_ods_final[col].astype('Int64')  # 可处理NULL的整数类型

            # 处理其他字段的空值（用空字符串替代）
            string_columns = df_ods_final.select_dtypes(include=['object']).columns
            df_ods_final[string_columns] = df_ods_final[string_columns].fillna('')

            # 分批插入数据，避免内存问题
            batch_size = 1000
            total_inserted = 0

            for i in range(0, len(df_ods_final), batch_size):
                batch_df = df_ods_final.iloc[i:i + batch_size]

                # 使用更安全的插入方式
                batch_df.to_sql(
                    'ods_asl_nodes_snapshot',
                    con=self.engine,
                    if_exists='append',
                    index=False,
                    method='multi'
                )

                total_inserted += len(batch_df)
                logger.info(f"Inserted to ODS: {total_inserted}/{len(df_ods_final)} records")

            logger.info(f"Successfully loaded {len(df_ods_final)} records to ODS layer")
            return True

        except Exception as e:
            logger.error(f"ODS layer loading failed: {e}")
            # 输出详细错误信息用于调试
            logger.error(f"DataFrame columns: {df.columns.tolist()}")
            if 'df_ods_final' in locals():
                logger.error(f"ODS final columns: {df_ods_final.columns.tolist()}")
                logger.error(f"ODS final shape: {df_ods_final.shape}")
            raise

    def process_dwd_events(self, df_current):
        """处理DWD层事件"""
        logger.info(f"[{self.batch_id}] Processing DWD events...")

        try:
            # 读取DIM表的当前状态（包含经纬度）
            query_dim = """
            SELECT node_id, is_active, latitude, longitude
            FROM dim_nodes
            """
            df_dim_previous = pd.read_sql(query_dim, con=self.engine)

            if df_dim_previous.empty:
                logger.info("DIM table is empty, skipping event generation")
                return True

            # 合并当前数据和DIM历史数据进行比较
            df_comparison = df_current[['node_id', 'is_active', 'latitude', 'longitude']].merge(
                df_dim_previous[['node_id', 'is_active', 'latitude', 'longitude']],
                on='node_id',
                how='inner',
                suffixes=('_new', '_old')
            )

            events = []
            event_time = datetime.datetime.now()

            # 1. 状态变化事件（向量化处理）
            status_changes = df_comparison[
                df_comparison['is_active_new'] != df_comparison['is_active_old']
            ]

            for _, row in status_changes.iterrows():
                events.append({
                    'node_id': row['node_id'],
                    'event_type': 'status_change',
                    'attr_name': 'is_active',
                    'old_value': str(row['is_active_old']),
                    'new_value': str(row['is_active_new']),
                    'event_time': event_time
                })

            # 2. 地理位移事件（向量化处理）
            # 计算坐标差异
            df_comparison['lat_new_num'] = pd.to_numeric(df_comparison['latitude_new'], errors='coerce')
            df_comparison['lon_new_num'] = pd.to_numeric(df_comparison['longitude_new'], errors='coerce')
            df_comparison['lat_old_num'] = pd.to_numeric(df_comparison['latitude_old'], errors='coerce')
            df_comparison['lon_old_num'] = pd.to_numeric(df_comparison['longitude_old'], errors='coerce')

            df_comparison['lat_diff'] = abs(df_comparison['lat_new_num'] - df_comparison['lat_old_num'])
            df_comparison['lon_diff'] = abs(df_comparison['lon_new_num'] - df_comparison['lon_old_num'])

            # 地理位移事件条件
            geo_moves = df_comparison[
                ((df_comparison['lat_diff'] > 0.005) | (df_comparison['lon_diff'] > 0.005)) &
                (~df_comparison['lat_new_num'].isna()) &
                (~df_comparison['lon_new_num'].isna()) &
                (~df_comparison['lat_old_num'].isna()) &
                (~df_comparison['lon_old_num'].isna()) &
                (~((df_comparison['lat_new_num'] == 0.0) & (df_comparison['lon_new_num'] == 0.0))) &
                (~((df_comparison['lat_old_num'] == 0.0) & (df_comparison['lon_old_num'] == 0.0)))
            ]

            for _, row in geo_moves.iterrows():
                old_coord = f"{row['latitude_old']},{row['longitude_old']}"
                new_coord = f"{row['latitude_new']},{row['longitude_new']}"
                events.append({
                    'node_id': row['node_id'],
                    'event_type': 'geo_move',
                    'attr_name': 'coordinates',
                    'old_value': old_coord,
                    'new_value': new_coord,
                    'event_time': event_time
                })

            # 批量插入事件
            if events:
                df_events = pd.DataFrame(events)
                df_events.to_sql(
                    'dwd_node_events_fact',
                    con=self.engine,
                    if_exists='append',
                    index=False,
                    method='multi',
                    chunksize=1000
                )
                logger.info(f"Generated and inserted {len(events)} DWD events")
            else:
                logger.info("No event changes in this batch")

            return True

        except Exception as e:
            logger.error(f"DWD event processing failed: {e}")
            raise

    def calculate_node_metrics(self, df):
        """计算节点指标"""
        # 节点等级计算（基于历史活跃度）
        df['node_rank'] = 'Active'  # 简化逻辑，可以根据历史数据计算

        # 移动属性判断（基于历史位置变化）
        df['mobility_type'] = 'Fixed'  # 简化逻辑，可以根据历史轨迹判断

        # 首次入网时间（需要查询历史数据）
        df['first_seen_at'] = df['last_seen']  # 简化处理

        # 初始化is_mobile字段（后续可通过DWD事件历史判定）
        df['is_mobile'] = 0  # 默认为固定节点

        return df

    def upsert_dim_nodes(self, df):
        """更新DIM层节点表"""
        logger.info(f"[{self.batch_id}] Updating DIM layer...")

        try:
            # 添加维度字段
            df_dim = self.calculate_node_metrics(df.copy())

            # 准备DIM表字段（包含新增的经纬度和移动属性字段）
            dim_columns = [
                'node_id', 'callsign', 'owner', 'affiliation', 'affiliation_type',
                'country', 'continent', 'is_active', 'last_seen', 'node_rank',
                'mobility_type', 'first_seen_at', 'latitude', 'longitude', 'is_mobile'
            ]

            df_dim_final = df_dim[dim_columns].copy()
            df_dim_final['update_time'] = datetime.datetime.now()

            # 使用pandas和SQLAlchemy的更安全方式进行upsert
            # 分批处理避免内存问题
            batch_size = 1000
            total_updated = 0

            for i in range(0, len(df_dim_final), batch_size):
                batch_df = df_dim_final.iloc[i:i + batch_size]

                # 使用replace方法实现upsert（MySQL特定）
                batch_df.to_sql(
                    'dim_nodes',
                    con=self.engine,
                    if_exists='append',
                    index=False,
                    method=self._upsert_method
                )
                total_updated += len(batch_df)
                logger.info(f"Updated DIM: {total_updated}/{len(df_dim_final)} records")

            logger.info(f"Successfully updated DIM layer with {len(df_dim_final)} records")
            return True

        except Exception as e:
            logger.error(f"DIM layer update failed: {e}")
            raise

    def _upsert_method(self, pd_table, conn, keys, data_iter):
        """自定义upsert方法用于MySQL ON DUPLICATE KEY UPDATE"""
        from sqlalchemy.dialects.mysql import insert

        data = [dict(zip(keys, row)) for row in data_iter]

        stmt = insert(pd_table.table).values(data)
        update_dict = {c.name: c for c in stmt.inserted if c.name != 'node_id'}

        on_duplicate_key_stmt = stmt.on_duplicate_key_update(update_dict)
        result = conn.execute(on_duplicate_key_stmt)
        return result.rowcount

    def run_etl_pipeline(self):
        """运行完整的ETL流水线"""
        try:
            logger.info(f"Starting ETL pipeline, Batch ID: {self.batch_id}")

            # 1. Extract - 数据抽取
            df_all, df_online = self.extract_data()

            # 2. Transform - 数据转换
            df_transformed = self.transform_data(df_all, df_online)

            # 3. Load - 数据加载
            # 3.1 加载到ODS层
            self.load_to_ods(df_transformed)

            # 3.2 处理DWD事件
            self.process_dwd_events(df_transformed)

            # 3.3 更新DIM层
            self.upsert_dim_nodes(df_transformed)

            logger.info(f"ETL pipeline completed successfully, Batch ID: {self.batch_id}")
            return True

        except Exception as e:
            logger.error(f"ETL pipeline execution failed: {e}")
            return False


def run_schedule(interval_minutes):
    """运行定时任务"""
    logger.info(f"定时ETL任务启动，间隔 {interval_minutes} 分钟")

    def job():
        etl = AllStarLinkETL()
        etl.run_etl_pipeline()

    schedule.every(interval_minutes).minutes.do(job)

    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("定时任务已停止")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='AllStarLink数仓ETL爬虫')
    parser.add_argument('--mode', choices=['now', 'schedule'], default='now',
                      help='运行模式：now(立即执行)或schedule(定时执行)')
    parser.add_argument('--interval', type=int, default=60,
                      help='定时执行间隔（分钟），默认60分钟')

    args = parser.parse_args()

    if args.mode == 'now':
        # 立即执行
        etl = AllStarLinkETL()
        success = etl.run_etl_pipeline()
        if success:
            logger.info("ETL task completed successfully")
        else:
            logger.error("ETL task execution failed")
    else:
        # 定时执行
        run_schedule(args.interval)


if __name__ == "__main__":
    main()