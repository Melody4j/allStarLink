#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试numpy字符串类型清理功能
"""

import pandas as pd
import numpy as np
from allstarlink_realtime_etl import RealtimeETLProcessor

def test_clean_dataframe_dtypes():
    """测试DataFrame类型清理"""
    
    # 创建包含numpy字符串的DataFrame
    print("创建测试DataFrame...")
    df = pd.DataFrame({
        'node_id': [1001, 1002, 1003],
        'callsign': np.array(['N5XYZ', 'W4ABC', 'K7DEF'], dtype='object'),
        'owner': ['Alice', 'Bob', 'Charlie'],
        'country': np.array(['US', 'US', 'CA'], dtype=np.str_),  # numpy字符串
        'frequency': [146.520, 147.000, 146.610],
    })
    
    print("\n原始DataFrame数据类型:")
    print(df.dtypes)
    print("\n原始DataFrame内容:")
    print(df)
    
    # 初始化处理器
    processor = RealtimeETLProcessor()
    
    # 清理数据类型
    print("\n清理DataFrame...")
    df_clean = processor._clean_dataframe_dtypes(df)
    
    print("\n清理后DataFrame数据类型:")
    print(df_clean.dtypes)
    print("\n清理后DataFrame内容:")
    print(df_clean)
    
    # 验证所有object列都是Python str
    print("\n验证清理结果...")
    for col in df_clean.select_dtypes(include=['object']).columns:
        for val in df_clean[col]:
            if pd.notna(val):
                if not isinstance(val, str):
                    print(f"❌ 列{col}中值{val}不是Python str类型，类型为: {type(val)}")
                else:
                    print(f"✓ 列{col}中值{val}是Python str类型")
    
    print("\n✅ 测试完成!")

if __name__ == "__main__":
    test_clean_dataframe_dtypes()
