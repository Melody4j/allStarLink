# ODS节点详情表实现进度文档

## 任务概述

新增一个插入节点详细信息ODS表的模块，在对单个节点的处理中，将爬取到的数据插入到ods_nodes_details表中。

## 实施进度

### 1. 数据模型创建 ✅

**文件**: `src/neo4j_scraper/models/ods_node_detail.py`

**内容**:
- 创建了`OdsNodeDetail`数据类，对应数据库表`ods_nodes_details`
- 实现了`to_dict()`方法，将对象转换为字典
- 实现了`validate()`方法，验证数据有效性
- 实现了`from_node_data()`类方法，从API节点数据创建ODS节点详情对象

**字段映射**:
- `node_id`: 节点ID（主键）
- `node_type`: 节点类型（默认为'ALLSTARLINK'）
- `callsign`: 节点呼号
- `frequency`: 工作频率
- `tone`: 节点亚音
- `affiliation`: 所属组织
- `site_name`: 物理站点名称
- `is_active`: 是否在线
- `last_seen`: 最后一次在线时间
- `latitude`: 纬度
- `longitude`: 经度
- `app_version`: ASL软件版本
- `ip`: IP地址
- `timezone_offset`: 时区偏移量
- `is_nnx`: 是否使用NNX协议
- `total_keyups`: 本次在线累积PTT次数
- `total_tx_time`: 本次在线累积发射时长
- `access_webtransceiver`: 是否支持网页收发
- `access_telephoneportal`: 是否支持电话网关接入
- `access_functionlist`: 是否支持远程功能列表查询
- `access_reverseautopatch`: 是否允许反向自动拨号
- `seqno`: 上报序号
- `timeout`: 发射限时中断次数
- `apprptuptime`: 本次在线时长
- `total_execd_commands`: 本次在线执行命令行次数
- `max_uptime`: 历史最大连续在线时长
- `current_link_count`: 当前实时连接数
- `linked_nodes`: 连接节点详情（JSON格式）
- `links`: 节点之间的连接方式（JSON格式）
- `port`: 节点服务器端口

### 2. MySQL数据库操作 ✅

**文件**: `src/neo4j_scraper/database/mysql_manager.py`

**修改内容**:
- 导入了`OdsNodeDetail`模型
- 添加了`insert_ods_node_detail()`方法，用于插入ODS节点详情到MySQL
- 使用UPSERT语法（INSERT ... ON DUPLICATE KEY UPDATE）确保数据更新
- 添加了详细的日志记录（成功和失败情况）

**方法签名**:
```python
async def insert_ods_node_detail(self, ods_detail: OdsNodeDetail) -> None
```

### 3. 爬虫集成 ✅

**文件**: `src/neo4j_scraper/scrapers/api_worker.py`

**修改内容**:
- 导入了`OdsNodeDetail`模型
- 在`_update_databases()`方法中添加了插入ODS节点详情的逻辑
- 在更新dim_nodes表后，创建ODS节点详情对象并插入数据库
- 添加了详细的日志记录（debug和info级别）
- 添加了异常处理，确保ODS插入失败不影响主流程

**数据流程**:
1. 从API获取节点数据
2. 解析节点数据
3. 更新Neo4j数据库
4. 更新MySQL dim_nodes表
5. **新增**：创建ODS节点详情对象并插入MySQL ods_nodes_details表

**日志输出**:
- DEBUG: "API工作者: 开始插入节点 {node_id} 的ODS详情..."
- INFO: "API工作者: 成功插入节点 {node_id} 的ODS详情"
- ERROR: "API工作者: 插入节点 {node_id} 的ODS详情失败 - {error}"（如果失败）

## 数据来源

根据`README_NEO4J_TOPOLOGY.md`文档，节点数据来源于AllStarLink API：

**API端点**: `GET /api/stats/{node_id}`

**数据路径**:
- 节点基本信息: `stats.user_node`
- 服务器信息: `stats.user_node.server`
- 连接节点: `stats.data.linkedNodes`
- 运行统计数据: `stats.data`

## 字段映射说明

### 从API到ODS表的映射

| API字段路径 | ODS表字段 | 说明 |
|------------|-----------|------|
| stats.user_node.name | node_id | 节点ID |
| - | node_type | 固定为'ALLSTARLINK' |
| stats.user_node.callsign | callsign | 呼号 |
| stats.user_node.node_frequency | frequency | 工作频率 |
| stats.user_node.node_tone | tone | 节点亚音 |
| stats.user_node.server.Affiliation | affiliation | 所属组织 |
| stats.user_node.server.SiteName | site_name | 站点名称 |
| - | is_active | 固定为True（在线节点） |
| - | last_seen | 当前时间 |
| stats.user_node.server.Latitude | latitude | 纬度 |
| stats.user_node.server.Logitude | longitude | 经度 |
| stats.data.apprptvers | app_version | ASL版本 |
| stats.user_node.ipaddr | ip | IP地址 |
| - | timezone_offset | 暂无数据 |
| stats.user_node.is_nnx | is_nnx | 是否使用NNX |
| stats.data.totalkeyups | total_keyups | PTT次数 |
| stats.data.totaltxtime | total_tx_time | 发射时长 |
| stats.user_node.access_webtransceiver | access_webtransceiver | 网页收发 |
| stats.user_node.access_telephoneportal | access_telephoneportal | 电话网关 |
| stats.user_node.access_functionlist | access_functionlist | 功能列表 |
| stats.user_node.access_reverseautopatch | access_reverseautopatch | 反向拨号 |
| stats.data.seqno | seqno | 序号 |
| stats.data.timeouts | timeout | 超时次数 |
| stats.data.apprptuptime | apprptuptime | 在线时长 |
| stats.data.totalexecdcommands | total_execd_commands | 执行命令数 |
| - | max_uptime | 暂无数据 |
| stats.data.linkedNodes.length | current_link_count | 连接数 |
| stats.data.linkedNodes | linked_nodes | 连接节点详情 |
| - | links | 连接方式 |
| stats.user_node.server.udpport / user_node.port | port | 端口 |

## 日志记录

所有MySQL操作都有详细的日志记录：

- **成功日志**: 记录节点ID和操作状态
- **失败日志**: 记录节点ID和异常信息
- **验证失败**: 记录节点ID和验证失败原因

## 注意事项

1. **数据验证**: 在插入前会验证数据有效性，无效数据会被跳过
2. **异常处理**: ODS插入失败不会影响主流程（Neo4j和dim_nodes更新）
3. **连接管理**: 每次插入都会创建新的MySQL连接，使用后立即关闭
4. **UPSERT操作**: 使用ON DUPLICATE KEY UPDATE确保数据更新而非重复插入
5. **JSON字段**: linked_nodes和links字段以JSON格式存储

## 测试建议

1. 验证单个节点数据是否正确插入
2. 检查所有字段是否正确映射
3. 验证UPSERT操作是否正常工作
4. 测试异常情况下的错误处理
5. 检查日志输出是否完整

## 后续优化

1. **批量插入**: 考虑实现批量插入以提高性能
2. **连接池**: 复用MySQL连接池而不是每次创建新连接
3. **max_uptime**: 实现历史最大在线时长的计算逻辑
4. **timezone_offset**: 从API或其他来源获取时区信息
5. **links**: 完善连接方式数据的收集

## 完成状态

✅ 数据模型创建
✅ MySQL数据库操作实现
✅ 爬虫集成
✅ 日志记录
✅ 异常处理
✅ 数据验证
⏳ 批量插入优化（待实现）
⏳ 连接池优化（待实现）
⏳ 历史数据计算（待实现）
