# 新版爬虫架构说明

本文档以 `src/link_scraper` 当前代码为准，聚焦新版爬虫的项目结构、关键模块职责、执行流程以及相关 API 返回数据说明。

## 1. 项目概览

新版爬虫是一个异步拓扑抓取程序，核心目标是：

- 从 AllStarLink API 获取在线节点列表和节点详情
- 使用 Redis 优先级队列调度节点抓取顺序
- 将节点及其连接关系写入 Neo4j
- 将节点当前状态和 ODS 明细写入 MySQL

当前主入口为：

- `src/link_scraper/main.py`

核心流程分为两段：

1. `SnapshotScanner` 扫描在线节点列表，生成抓取任务
2. `APIWorker` 消费任务，抓取节点详情并落库

## 2. 项目结构

### 2.1 目录结构

```text
src/link_scraper/
├─ main.py
├─ config/
│  ├─ settings.py
│  └─ constants.py
├─ database/
│  ├─ base.py
│  ├─ mysql_manager.py
│  └─ neo4j_manager.py
├─ models/
│  ├─ node.py
│  ├─ connection.py
│  └─ ods_node_detail.py
├─ scrapers/
│  ├─ snapshot_scanner.py
│  ├─ api_worker.py
│  └─ node_parser.py
├─ task_queue/
│  └─ priority_queue.py
└─ utils/
   ├─ batch_manager.py
   ├─ rate_limiter.py
   ├─ logger.py
   ├─ helpers.py
   └─ helpers_new.py
```

### 2.2 模块职责

#### `main.py`

负责：

- 加载配置
- 初始化 Redis、Neo4j、MySQL
- 初始化速率限制器和批次号管理器
- 创建 `SnapshotScanner` 和 `APIWorker`
- 根据 Redis 队列状态触发新一轮快照扫描

#### `scrapers/snapshot_scanner.py`

负责：

- 请求在线节点列表接口
- 解析节点 ID 和连接数
- 批量更新 `dim_nodes.current_link_count`
- 将高优先级节点放入 Redis 队列

#### `scrapers/api_worker.py`

负责：

- 从 Redis 队列取节点 ID
- 调用节点详情接口
- 调用 `NodeParser` 解析主节点、子节点、连接关系
- 更新 Neo4j 节点和关系
- 更新 MySQL `dim_nodes`
- 写入 MySQL `ods_nodes_details`

#### `scrapers/node_parser.py`

负责：

- 解析主节点详情
- 解析连接子节点
- 解析连接关系方向和状态
- 提取业务字段、位置字段、硬件类型、节点类型等信息

#### `database/neo4j_manager.py`

负责：

- 初始化 Neo4j 唯一约束
- 按 `unique_id` 更新节点
- 更新 `CONNECTED_TO` 关系
- 查询指定批次拓扑
- 删除指定节点

#### `database/mysql_manager.py`

负责：

- 更新 `dim_nodes`
- 插入 `ods_nodes_details`
- 执行简单 SQL 查询

#### `task_queue/priority_queue.py`

负责：

- Redis ZSET 优先级队列
- Redis SET 去重
- 批量入队
- 批量锁控制

#### `utils/batch_manager.py`

负责：

- 生成批次号
- 从 Redis/MySQL 恢复当前批次号
- 将批次号写入 Redis

## 3. 关键执行流程

### 3.1 应用启动流程

`main.py` 启动阶段顺序如下：

1. 调用 `Settings.load()` 读取配置
2. 初始化 Redis 客户端
3. 初始化 Redis 优先级队列
4. 初始化 Neo4j 连接和唯一约束
5. 初始化 MySQL 连接
6. 初始化 `RateLimiter`
7. 初始化 `BatchManager`
8. 初始化 `SnapshotScanner`
9. 初始化 `APIWorker`
10. 将当前批次号设置到 `APIWorker`

### 3.2 主调度流程

`Neo4jScraperApp.start()` 的核心逻辑是：

1. 启动 `APIWorker.start()` 作为后台任务
2. 持续检查 Redis 队列大小
3. 如果队列为空：
   - 清空旧任务集合
   - 触发一次 `SnapshotScanner.scan_and_update()`
   - 读取新的批次号并设置到 `APIWorker`
   - 睡眠 1800 秒
4. 如果队列不为空：
   - 睡眠 10 秒后继续检查

当前程序不是固定按时间扫全量，而是“队列清空后再触发下一轮快照扫描”。

### 3.3 快照扫描流程

`SnapshotScanner.scan_and_update()` 流程如下：

1. 从 `BatchManager` 获取或生成新的批次号
2. 创建 `aiohttp.ClientSession`
3. 请求 `node_list_url`
4. 从返回的 DataTables 风格 JSON 中提取：
   - `node_id`
   - `link_count`
5. 批量更新 MySQL `dim_nodes`：
   - `current_link_count`
   - `last_seen`
   - `is_active`
6. 过滤出 `link_count > 1` 的节点
7. 通过 `RedisPriorityQueue.batch_enqueue()` 批量入队

### 3.4 当前优先级规则

当前优先级分数直接使用连接数：

- `priority = link_count`

连接数越大，出队优先级越高。

### 3.5 节点详情抓取流程

`APIWorker.process_queue()` 流程如下：

1. 检查速率限制器是否允许发起请求
2. 从 Redis 队列中取一个节点 ID
3. 在最小/最大延迟之间随机睡眠
4. 请求 `base_url/{node_id}`
5. 成功后进入 `_update_databases()`

### 3.6 重试与限流

节点详情请求具备以下机制：

- 速率限制：`RateLimiter`
- 最大重试次数：`api.max_retries`
- 指数退避：`retry_backoff ** attempt`
- HTTP 429 冷却：`cooldown_429`

### 3.7 落库流程

`APIWorker._update_databases()` 的执行顺序如下：

1. 校验 `stats` 是否存在
2. 使用 `NodeParser.parse_node()` 解析主节点
3. 给主节点设置 `batch_no`
4. 更新主节点 Neo4j 节点
5. 读取 `linkedNodes`
6. 逐个解析子节点并先写入 Neo4j
7. 解析连接关系
8. 写入 Neo4j `CONNECTED_TO` 关系
9. 再次更新子节点 Neo4j，使用保留统计字段的策略
10. 更新主节点 MySQL `dim_nodes`
11. 更新子节点 MySQL `dim_nodes`，但不更新 `current_link_count`
12. 构建 `OdsNodeDetail`
13. 写入 MySQL `ods_nodes_details`

## 4. API 返回数据讲解

### 4.1 在线节点列表接口

当前代码使用的接口：

- `http://stats.allstarlink.org/api/stats/nodeList`

请求方式：

- `POST`

当前代码假定返回 JSON 中包含 `data` 数组，且每一行是一个列表。

代码实际只使用：

- 第一列中的节点链接或节点文本
- 最后一列的连接数

#### 4.1.1 提取方式

从每一行数据中：

1. 从第一列字符串中用正则匹配 `/stats/(\d+)`
2. 如果匹配失败，则退化为取第一个空格前文本
3. 最后一列如果是数字，则作为 `link_count`

最终转换为：

```json
{
  "node_id": 2105,
  "link_count": 5
}
```

### 4.2 节点详情接口

当前代码使用的接口：

- `https://stats.allstarlink.org/api/stats/{node_id}`

返回数据中，代码重点关注以下结构：

```json
{
  "stats": {
    "data": {
      "apprptuptime": "240706",
      "totalkeyups": "21",
      "totaltxtime": "92",
      "apprptvers": "3.7.1",
      "timeouts": "0",
      "seqno": "9645",
      "totalexecdcommands": "0",
      "nodes": "T520580,T56001,T61672",
      "linkedNodes": []
    },
    "user_node": {
      "name": 2105,
      "callsign": "KJ7OMO",
      "node_frequency": "PRIDE Multi-mode HUB",
      "node_tone": "kimberlychase.com",
      "ipaddr": "209.222.4.140",
      "is_nnx": "No",
      "access_webtransceiver": "1",
      "access_telephoneportal": "1",
      "access_functionlist": "0",
      "access_reverseautopatch": "1",
      "server": {
        "Server_Name": "2105-PRIDE-HUB",
        "SiteName": "Pride Radio Network Hub",
        "Affiliation": "Pride Radio Network",
        "Latitude": "40.5545",
        "Logitude": "-74.4601",
        "Location": "Cloud 69",
        "udpport": 4569
      }
    }
  }
}
```

### 4.3 主节点数据说明

主节点数据主要来自：

- `stats.user_node`
- `stats.user_node.server`
- `stats.data`

代码直接使用的字段包括：

来自 `stats.user_node`：

- `name`
- `callsign`
- `node_frequency`
- `node_tone`
- `User_ID`
- `ipaddr`
- `is_nnx`
- `access_webtransceiver`
- `access_telephoneportal`
- `access_functionlist`
- `access_reverseautopatch`

来自 `stats.user_node.server`：

- `Affiliation`
- `Server_Name`
- `SiteName`
- `Latitude`
- `Logitude`
- `Location`
- `udpport`

来自 `stats.data`：

- `apprptuptime`
- `totalkeyups`
- `totaltxtime`
- `seqno`
- `timeouts`
- `totalexecdcommands`
- `apprptvers`
- `nodes`
- `linkedNodes`

### 4.4 子节点数据说明

子节点数据来自：

- `stats.data.linkedNodes`

当前代码对 `linkedNodes` 的处理策略是：

- 解析出节点 ID、呼号、位置、硬件类型等基础信息
- 如果缺少完整统计信息，则不伪造真实统计值

因此当前代码中，子节点占位节点可能具有以下特征：

- `apprptuptime = null`
- `total_keyups = null`
- `total_tx_time = null`
- `connections = null`

只有当该节点后续被当作主节点抓取时，才会补全真实统计数据。

### 4.5 连接模式字段 `stats.data.nodes`

`stats.data.nodes` 是一个字符串，例如：

```text
T520580,T56001,T61672
```

每一段前缀代表连接方向：

- `T` -> `Transceive`
- `R` -> `RX Only`
- `L` -> `Local`
- `P` -> `Permanent`

当前代码使用 `NodeParser._parse_connection_modes()` 将其解析成字典映射。

## 5. 当前代码的重要行为说明

### 5.1 批次号机制

批次号格式：

- `yyyymmddHH + 6位序号`

示例：

- `2026031314000068`

作用：

- 区分同一节点在不同抓取批次中的实例
- 作为 Neo4j `unique_id` 的组成部分
- 写入 ODS 明细表

### 5.2 子节点占位策略

当前代码允许先创建子节点占位节点，再等待其自身被主节点抓取时补全数据。

这意味着：

- 图中可能已经存在某节点和大量关系
- 但该节点统计字段仍为空

这不是抓取错误，而是当前设计下的中间状态。

### 5.3 当前不再使用的逻辑

旧版 `SnapshotScanner` 中的 `_cleanup_offline_nodes()` 离线清理逻辑已经删除，不再属于当前主流程。

## 6. 建议阅读顺序

如果要快速理解当前代码，建议按这个顺序阅读：

1. `src/link_scraper/main.py`
2. `src/link_scraper/scrapers/snapshot_scanner.py`
3. `src/link_scraper/scrapers/api_worker.py`
4. `src/link_scraper/scrapers/node_parser.py`
5. `src/link_scraper/database/neo4j_manager.py`
6. `src/link_scraper/database/mysql_manager.py`
7. `src/link_scraper/task_queue/priority_queue.py`
8. `src/link_scraper/utils/batch_manager.py`

