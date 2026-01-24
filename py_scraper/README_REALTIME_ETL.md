# AllStarLink 准实时ETL爬虫使用指南

## 概述

这是一个实现"每分钟爬取、内存对比异动、按需写入数据库"的准实时ETL流程的Python爬虫，专为AllStarLink节点数据设计。

## 系统架构

### 数据仓库分层

1. **ODS层 (ods_asl_nodes_snapshot)**: 全量快照表，按指定间隔写入
2. **DWD层 (dwd_node_even
3. ts_fact)**: 事件事实表，仅在节点状态/位置变化时即时写入
3. **DIM层 (dim_nodes)**: 实体维度表，实时Upsert最新属性

### 核心特性

- **内存状态缓存**: 使用`df_last`变量保存上一次的数据状态
- **向量化异动检测**: 使用pandas向量化操作进行高效的数据比对
- **按需写入**: 只有在检测到变化时才写入DWD和DIM表
- **可配置ODS间隔**: ODS写入时间可通过参数配置
- **异常安全**: 爬虫失败时不会清空内存缓存

## 安装依赖

```bash
pip install pandas numpy sqlalchemy pymysql requests
```

## 使用方法

### 1. 单次执行模式

```bash
python allstarlink_realtime_etl.py --mode single
```

### 2. 准实时循环模式（推荐）

```bash
# 默认每60分钟写入一次ODS
python allstarlink_realtime_etl.py --mode realtime

# 自定义ODS写入间隔为30分钟
python allstarlink_realtime_etl.py --mode realtime --ods-interval 30

# 每2小时写入一次ODS
python allstarlink_realtime_etl.py --mode realtime --ods-interval 120
```

### 3. 参数说明

| 参数 | 描述 | 默认值 | 示例 |
|------|------|--------|------|
| `--mode` | 运行模式：single(单次) 或 realtime(循环) | realtime | `--mode realtime` |
| `--ods-interval` | ODS快照写入间隔（分钟） | 60 | `--ods-interval 30` |

## 核心逻辑说明

### 异动检测机制

1. **状态变化检测**: 识别`is_active`字段的变化
2. **地理位移检测**: 当经纬度变化超过0.005度时视为位移
3. **新增节点检测**: 识别新出现的节点

### 数据写入策略

```python
# 伪代码示例
if 首次运行:
    初始化内存缓存(df_last)
    全量写入DIM表
else:
    # 向量化比对
    df_comparison = pd.merge(df_now, df_last, on='node_id', ...)

    # 检测变化
    status_changes = 检测状态变化(df_comparison)
    geo_moves = 检测地理位移(df_comparison)
    new_nodes = 检测新增节点(df_comparison)

    # 按需写入
    if 有变化:
        写入DWD事件表(变化详情)
        更新DIM表(变化节点)

    # 定时归档
    if 达到ODS间隔时间:
        写入ODS快照表(全量数据)

# 更新内存缓存
df_last = df_now
```

## 监控和日志

### 日志级别

- **INFO**: 正常运行信息，包括统计数据
- **DEBUG**: 详细调试信息
- **ERROR**: 错误信息和异常堆栈

### 统计信息

脚本会定期输出统计信息：

```
Stats: Total=100, Success=98, Failed=2, StatusChanges=15, GeoMoves=3, ODSWrites=5
```

- `Total`: 总执行次数
- `Success`: 成功次数
- `Failed`: 失败次数
- `StatusChanges`: 累计状态变化数
- `GeoMoves`: 累计地理位移数
- `ODSWrites`: ODS写入次数

## 数据库表结构

### ODS表 (ods_asl_nodes_snapshot)

```sql
CREATE TABLE ods_asl_nodes_snapshot (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    batch_id VARCHAR(20),
    node_id INT,
    owner VARCHAR(255),
    callsign VARCHAR(50),
    frequency VARCHAR(50),
    tone VARCHAR(50),
    location VARCHAR(255),
    site VARCHAR(255),
    affiliation VARCHAR(255),
    last_seen DATETIME,
    latitude DECIMAL(10,7),
    longitude DECIMAL(10,7),
    is_active TINYINT(1),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### DWD事件表 (dwd_node_events_fact)

```sql
CREATE TABLE dwd_node_events_fact (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    node_id INT,
    event_type VARCHAR(50),
    attr_name VARCHAR(50),
    old_value TEXT,
    new_value TEXT,
    event_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### DIM维度表 (dim_nodes)

```sql
CREATE TABLE dim_nodes (
    node_id INT PRIMARY KEY,
    owner VARCHAR(255),
    callsign VARCHAR(50),
    frequency VARCHAR(50),
    tone VARCHAR(50),
    location VARCHAR(255),
    site VARCHAR(255),
    affiliation VARCHAR(255),
    last_seen DATETIME,
    latitude DECIMAL(10,7),
    longitude DECIMAL(10,7),
    is_active TINYINT(1),
    update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

## 配置文件

可以修改`realtime_etl_config.py`来调整各种配置：

```python
# 数据库配置
DB_CONFIG = {
    'host': '121.41.230.15',
    'user': 'root',
    'password': '0595',
    'database': 'allStarLink'
}

# ETL配置
ETL_CONFIG = {
    'geo_move_threshold': 0.005,  # 地理位移阈值
    'batch_size': 1000,           # 批处理大小
    'default_ods_interval_minutes': 60  # 默认ODS间隔
}
```

## 性能优化

### 向量化处理

脚本使用pandas向量化操作处理2万+节点数据，避免使用`iterrows()`循环：

```python
# ✅ 推荐：向量化操作
status_change_mask = (
    (df_comparison['_merge'] == 'both') &
    (df_comparison['is_active_now'] != df_comparison['is_active_last'])
)
df_status_changes = df_comparison[status_change_mask]

# ❌ 避免：循环操作
for _, row in df.iterrows():  # 慢
    # 处理每一行
```

### 数据库连接池

使用SQLAlchemy连接池管理数据库连接：

```python
self.engine = create_engine(
    DATABASE_URL,
    pool_size=5,           # 连接池大小
    max_overflow=10,       # 最大溢出连接
    pool_recycle=3600      # 连接回收时间
)
```

## 故障处理

### 常见问题

1. **数据库连接失败**
   - 检查数据库配置
   - 确认网络连通性
   - 验证用户权限

2. **API请求失败**
   - 检查网络连接
   - 验证API端点可用性
   - 调整请求超时时间

3. **内存不足**
   - 增加系统内存
   - 调整批处理大小
   - 优化数据处理逻辑

### 异常安全

脚本具有异常安全机制：

- 爬虫失败时不会清空`df_last`缓存
- 数据库写入失败时会记录错误但继续运行
- 支持优雅停止（Ctrl+C）

## 运行建议

### 生产环境部署

1. **使用systemd服务**:
```ini
[Unit]
Description=AllStarLink Realtime ETL
After=network.target

[Service]
Type=simple
User=etl
WorkingDirectory=/path/to/scraper
ExecStart=/usr/bin/python3 allstarlink_realtime_etl.py --mode realtime --ods-interval 60
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

2. **监控和告警**:
   - 监控进程状态
   - 设置数据库连接告警
   - 监控ETL执行统计

3. **日志管理**:
   - 配置日志轮转
   - 集中化日志收集
   - 设置错误日志告警

## 扩展功能

### 自定义事件类型

可以在`detect_and_save_changes`函数中添加新的事件检测逻辑：

```python
# 示例：检测频率变化
freq_change_mask = (
    (df_comparison['_merge'] == 'both') &
    (df_comparison['frequency_now'] != df_comparison['frequency_last'])
)
```

### 数据增强

可以在`transform_and_standardize`函数中添加数据增强逻辑：

```python
# 示例：添加地理编码
df['country'] = df.apply(lambda row: geocode_country(row['latitude'], row['longitude']), axis=1)
```

## 技术支持

如有问题或建议，请查看：

1. 脚本日志输出
2. 数据库错误日志
3. 系统资源使用情况
4. 网络连接状态