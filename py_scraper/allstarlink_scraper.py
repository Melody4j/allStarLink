#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AllStarLink节点列表爬虫
爬取https://www.allstarlink.org/nodelist/的节点数据并保存到Excel和MySQL
支持立即爬取和定时爬取
"""

import time
import datetime
import argparse
import schedule
import requests
import pymysql
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# MySQL数据库配置
MYSQL_CONFIG = {
    'host': '121.41.230.15',
    'user': 'root',
    'password': '0595',
    'database': 'allStarLink',
    'charset': 'utf8',
    'cursorclass': pymysql.cursors.DictCursor
}

# API端点
API_URL = "https://www.allstarlink.org/nodelist/nodelist-server.php"
MAP_DATA_URL = "https://stats.allstarlink.org/api/stats/mapData"


def scrape_map_data():
    """爬取地图数据，获取节点的经纬度信息"""
    print("[{}] 开始爬取AllStarLink地图数据...".format(datetime.datetime.now()))
    
    try:
        # 发送请求获取地图数据
        response = requests.get(MAP_DATA_URL, timeout=30)
        response.raise_for_status()
        
        # 解析文本响应，使用制表符分隔
        map_data = response.text
        lines = map_data.strip().split('\n')
        
        # 创建节点ID到经纬度的映射字典
        node_coordinates = {}
        
        # 跳过表头行，从第二行开始处理
        for line in lines[1:]:
            if not line.strip():
                continue
            
            # 分割每行数据，使用制表符作为分隔符
            parts = line.split('\t')
            if len(parts) < 4:
                continue
            
            try:
                node_id = parts[0].strip()
                # 确保node_id是数字
                if not node_id.isdigit():
                    continue
                
                # 第三列是纬度，第四列是经度
                latitude = float(parts[2].strip())
                longitude = float(parts[3].strip())
                
                # 验证经纬度是否在有效范围内
                # 纬度范围：-90 到 90
                # 经度范围：-180 到 180
                if -90 <= latitude <= 90 and -180 <= longitude <= 180:
                    # 保存到字典中
                    node_coordinates[int(node_id)] = {
                        'latitude': latitude,
                        'longitude': longitude
                    }
            except (ValueError, IndexError):
                # 跳过格式不正确的行
                continue
        
        print("[{}] 成功获取 {} 个节点的经纬度数据".format(datetime.datetime.now(), len(node_coordinates)))
        return node_coordinates
    except Exception as e:
        print("[{}] 爬取地图数据错误：{}".format(datetime.datetime.now(), e))
        return {}


def scrape_nodes():
    """爬取节点列表数据"""
    print("[{}] 开始爬取AllStarLink节点列表...".format(datetime.datetime.now()))
    
    try:
        # 爬取地图数据获取经纬度信息
        node_coordinates = scrape_map_data()
        
        # 发送请求获取API数据
        response = requests.get(API_URL, timeout=30)
        response.raise_for_status()
        
        # 解析JSON响应
        data = response.json()
        
        # 检查响应格式
        if not isinstance(data, list):
            print("错误：API返回数据格式不正确")
            return False
        
        print("[{}] 成功获取 {} 个节点数据".format(datetime.datetime.now(), len(data)))
        
        # 定义表头和对应的字段映射
        headers = ['Node #', 'Owner', 'Callsign', 'Freq', 'Tone', 'Location', 'Site', 'Affiliation', 'Last Seen', 'Features']
        field_mapping = {
            'Node #': 'name',
            'Owner': 'User_ID',
            'Callsign': 'callsign',
            'Freq': 'node_frequency',
            'Tone': 'node_tone',
            'Location': 'Location',
            'Site': 'SiteName',
            'Affiliation': 'Affiliation',
            'Last Seen': 'regseconds'
            # Features字段需要动态生成
        }
        
        # 处理节点数据
        processed_nodes = []
        for node in data:
            processed_node = {}
            features = []
            
            # 处理每个字段
            for header, field in field_mapping.items():
                # 处理特殊字段
                if header == 'Last Seen':
                    # 将regseconds转换为可读日期
                    try:
                        regseconds = int(node.get(field, 0))
                        last_seen = datetime.datetime.fromtimestamp(regseconds).strftime('%Y-%m-%d %H:%M:%S')
                        processed_node[header] = last_seen
                    except:
                        processed_node[header] = node.get(field, '')
                else:
                    processed_node[header] = node.get(field, '')
            
            # 生成Features内容
            # 检查webtransceiver功能
            if node.get('access_webtransceiver', '0') == '1':
                features.append('Webtransceiver')
            # 检查telephoneportal功能
            if node.get('access_telephoneportal', '0') == '1':
                features.append('Telephone Portal')
            
            # 将功能列表合并为字符串
            processed_node['Features'] = ', '.join(features) if features else ''
            
            # 添加经纬度信息
            node_id = int(processed_node['Node #'])
            if node_id in node_coordinates:
                processed_node['Latitude'] = node_coordinates[node_id]['latitude']
                processed_node['Longitude'] = node_coordinates[node_id]['longitude']
            else:
                processed_node['Latitude'] = None
                processed_node['Longitude'] = None
            
            processed_nodes.append(processed_node)
        
        if not processed_nodes:
            print("错误：未提取到有效节点数据")
            return False
        
        print("[{}] 成功处理 {} 个节点数据".format(datetime.datetime.now(), len(processed_nodes)))
        
        # 保存到数据库
        db_result = save_to_database(processed_nodes)
        
        # 返回总体结果
        return db_result
        
    except requests.exceptions.RequestException as e:
        print("请求错误：{}".format(e))
        return False
    except ValueError as e:
        print("JSON解析错误：{}".format(e))
        # 保存响应内容到文件以便分析
        with open('debug_api_response.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
        print("API响应已保存到 debug_api_response.html")
        return False
    except Exception as e:
        print("爬取错误：{}".format(e))
        # 保存异常信息
        with open('debug_error.txt', 'w', encoding='utf-8') as f:
            f.write(str(e))
        return False


def create_db_connection():
    """创建数据库连接"""
    try:
        connection = pymysql.connect(**MYSQL_CONFIG)
        print("[{}] 成功连接到MySQL数据库".format(datetime.datetime.now()))
        return connection
    except Exception as e:
        print("[{}] 数据库连接错误：{}".format(datetime.datetime.now(), e))
        return None


def save_to_database(nodes):
    """保存数据到MySQL数据库"""
    # 创建数据库连接
    connection = create_db_connection()
    if not connection:
        return False
    
    try:
        # 插入数据
        with connection.cursor() as cursor:
            # 准备插入SQL语句（使用INSERT IGNORE INTO处理重复数据）
            insert_sql = """
            INSERT IGNORE INTO nodes (
                node_id, owner, callsign, frequency, tone, 
                location, site, affiliation, last_seen, features, 
                latitude, longitude, is_active
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            """
            
            # 准备数据
            data_to_insert = []
            for node in nodes:
                # 根据经纬度是否为空设置is_active字段
                # 经纬度为空：不在线，is_active = 0
                # 经纬度不为空：在线，is_active = 1
                latitude = node['Latitude']
                longitude = node['Longitude']
                is_active = 1 if (latitude is not None and longitude is not None) else 0
                
                data_to_insert.append((
                    int(node['Node #']),
                    node['Owner'],
                    node['Callsign'],
                    node['Freq'],
                    node['Tone'],
                    node['Location'],
                    node['Site'],
                    node['Affiliation'],
                    node['Last Seen'],
                    node['Features'],
                    latitude,
                    longitude,
                    is_active
                ))
            
            # 批量插入数据
            cursor.executemany(insert_sql, data_to_insert)
            connection.commit()
            
            print("[{}] 成功将 {} 条节点数据保存到数据库".format(datetime.datetime.now(), len(data_to_insert)))
            return True
            
    except Exception as e:
        print("[{}] 保存数据库错误：{}".format(datetime.datetime.now(), e))
        return False
    finally:
        # 关闭连接
        if connection:
            connection.close()
            print("[{}] 数据库连接已关闭".format(datetime.datetime.now()))


def run_schedule(interval_minutes):
    """运行定时任务"""
    print("[{}] 定时爬取已启动，每隔 {} 分钟执行一次".format(datetime.datetime.now(), interval_minutes))
    
    # 设置定时任务
    schedule.every(interval_minutes).minutes.do(scrape_nodes)
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[{}] 定时爬取已停止".format(datetime.datetime.now()))


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='AllStarLink节点列表爬虫')
    parser.add_argument('--mode', choices=['now', 'schedule'], default='now',
                      help='运行模式：now(立即爬取)或schedule(定时爬取)')
    parser.add_argument('--interval', type=int, default=60,
                      help='定时爬取间隔（分钟），默认60分钟')
    
    args = parser.parse_args()
    
    if args.mode == 'now':
        # 立即爬取
        scrape_nodes()
    else:
        # 定时爬取
        run_schedule(args.interval)


if __name__ == "__main__":
    main()
