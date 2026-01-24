#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AllStarLink ETL测试脚本
用于验证ETL流水线各个环节的功能
"""

import sys
import pandas as pd
import numpy as np
from allstarlink_etl_scraper import AllStarLinkETL
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_geographic_classification():
    """测试地理分类功能"""
    print("\n=== 测试地理分类功能 ===")

    etl = AllStarLinkETL()

    # 测试用例
    test_coordinates = [
        (40.7128, -74.0060, "New York, USA"),
        (51.5074, -0.1278, "London, UK"),
        (35.6762, 139.6503, "Tokyo, Japan"),
        (39.9042, 116.4074, "Beijing, China"),
        (-33.8688, 151.2093, "Sydney, Australia"),
        (0.0, 0.0, "Invalid coordinates"),
        (None, None, "None coordinates")
    ]

    for lat, lon, description in test_coordinates:
        continent, country = etl.get_continent_country(lat, lon)
        print(f"{description}: {continent}, {country}")


def test_affiliation_classification():
    """测试组织类型分类功能"""
    print("\n=== 测试组织类型分类功能 ===")

    etl = AllStarLinkETL()

    # 测试用例
    test_cases = [
        ("K1ABC", "K1ABC", "完全匹配呼号"),
        ("Amateur Radio Club", "K1ABC", "业余无线电俱乐部"),
        ("WX5XYZ Network", "K1ABC", "网络系统"),
        ("test.org", "K1ABC", "组织域名"),
        ("147.520", "K1ABC", "频率值"),
        ("John Smith", "K1ABC", "个人姓名"),
        (None, "K1ABC", "空值"),
        ("Emergency Communications Group", "W1AW", "应急通信组织")
    ]

    for affiliation, callsign, description in test_cases:
        result = etl.classify_affiliation_type(affiliation, callsign)
        print(f"{description}: '{affiliation}' -> {result}")


def test_frequency_cleaning():
    """测试频率清理功能"""
    print("\n=== 测试频率清理功能 ===")

    etl = AllStarLinkETL()

    # 测试用例
    test_frequencies = [
        "147.520",
        "147.520 MHz",
        "440.125+",
        "28.400 USB",
        "abc.def",
        "",
        None,
        "1296.100-"
    ]

    for freq in test_frequencies:
        cleaned = etl.clean_frequency(freq)
        print(f"'{freq}' -> {cleaned}")


def test_data_transformation():
    """测试数据转换功能"""
    print("\n=== 测试数据转换功能 ===")

    # 创建模拟数据
    df_all = pd.DataFrame({
        'name': ['1001', '1002', '1003'],
        'User_ID': ['User1', 'User2', 'User3'],
        'callsign': ['K1ABC', 'W2DEF', 'VE3GHI'],
        'node_frequency': ['147.520', '440.125 MHz', '28.400'],
        'node_tone': ['88.5', '100.0', '136.5'],
        'Location': ['New York', 'Toronto', 'London'],
        'SiteName': ['Site1', 'Site2', 'Site3'],
        'Affiliation': ['Radio Club', 'W2DEF', 'test.org'],
        'regseconds': [1640995200, 1640995300, 1640995400],
        'access_webtransceiver': ['1', '0', '1'],
        'access_telephoneportal': ['0', '1', '1']
    })

    df_online = pd.DataFrame({
        'node_id': [1001, 1003],
        'latitude': [40.7128, 51.5074],
        'longitude': [-74.0060, -0.1278]
    })

    try:
        etl = AllStarLinkETL()
        df_transformed = etl.transform_data(df_all, df_online)

        print("转换后的数据结构:")
        print(df_transformed.columns.tolist())
        print(f"\n转换后数据行数: {len(df_transformed)}")

        print("\n前3行数据预览:")
        print(df_transformed.head(3).to_string())

        print("\nis_active统计:")
        print(df_transformed['is_active'].value_counts())

        print("\naffiliation_type统计:")
        print(df_transformed['affiliation_type'].value_counts())

    except Exception as e:
        logger.error(f"数据转换测试失败: {e}")
        return False

    return True


def test_database_connection():
    """测试数据库连接"""
    print("\n=== 测试数据库连接 ===")

    try:
        etl = AllStarLinkETL()

        # 尝试查询数据库
        with etl.engine.connect() as conn:
            result = conn.execute("SELECT 1 as test")
            test_value = result.fetchone()[0]

        if test_value == 1:
            print("✓ 数据库连接成功")
            return True
        else:
            print("✗ 数据库连接异常")
            return False

    except Exception as e:
        logger.error(f"数据库连接失败: {e}")
        print("✗ 数据库连接失败")
        print("请检查数据库配置和网络连接")
        return False


def test_table_structure():
    """测试表结构"""
    print("\n=== 测试表结构 ===")

    try:
        etl = AllStarLinkETL()

        tables_to_check = [
            'ods_asl_nodes_snapshot',
            'dwd_node_events_fact',
            'dim_nodes'
        ]

        for table_name in tables_to_check:
            query = f"SHOW TABLES LIKE '{table_name}'"
            with etl.engine.connect() as conn:
                result = conn.execute(query)
                if result.fetchone():
                    print(f"✓ 表 {table_name} 存在")
                else:
                    print(f"✗ 表 {table_name} 不存在")
                    return False

        return True

    except Exception as e:
        logger.error(f"表结构检查失败: {e}")
        return False


def run_full_test():
    """运行完整测试套件"""
    print("开始AllStarLink ETL测试套件...")

    tests = [
        ("数据库连接", test_database_connection),
        ("表结构检查", test_table_structure),
        ("地理分类", test_geographic_classification),
        ("组织类型分类", test_affiliation_classification),
        ("频率清理", test_frequency_cleaning),
        ("数据转换", test_data_transformation)
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            if test_func():
                print(f"✓ {test_name} 测试通过")
                passed += 1
            else:
                print(f"✗ {test_name} 测试失败")
                failed += 1
        except Exception as e:
            logger.error(f"{test_name} 测试异常: {e}")
            print(f"✗ {test_name} 测试异常")
            failed += 1

    print(f"\n=== 测试结果总结 ===")
    print(f"通过: {passed}")
    print(f"失败: {failed}")
    print(f"总计: {passed + failed}")

    if failed == 0:
        print("🎉 所有测试通过！ETL系统准备就绪。")
        return True
    else:
        print("⚠️  部分测试失败，请检查配置和环境。")
        return False


if __name__ == "__main__":
    success = run_full_test()
    sys.exit(0 if success else 1)