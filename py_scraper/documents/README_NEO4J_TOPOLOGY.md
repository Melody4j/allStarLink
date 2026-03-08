
# AllStarLink Neo4j拓扑数据爬虫使用指南

## 概述

这是一个实现快照扫描器、优先级调度器和异步工作者解耦架构的Python异步爬虫框架，用于构建AllStarLink全球用户画像，并将拓扑数据存储到Neo4j图数据库中。

## 系统架构

### 组件架构

系统分为三个解耦的组件，通过Redis优先级队列进行通信：

1. **快照扫描器 (Snapshot Scanner)**
   - 频率：每5分钟运行一次
   - 目标：抓取 http://stats.allstarlink.org/api/stats/nodeList
   - 逻辑：提取所有在线节点ID及其连接数
   - 产出：根据连接数计算优先级，将节点ID推送至Redis优先级队列

2. **优先级调度器 (Priority Logic)**
   - High (Score: 100): 连接数 > 5 的Hub节点
   - Normal (Score: 50): 连接数1-4的活跃节点
   - Low (Score: 10): 在线但无连接的边缘节点
   - Cleanup: 若快照显示节点下线，立即在Neo4j中执行SET n.active = false并从队列剔除

3. **异步工作者 (API Worker)**
   - 速率限制：严格遵守30 requests/min（单IP）
   - 逻辑：从Redis取出高优先级节点，调用/api/stats/{id}
   - 写入：更新MySQL dim_nodes（最新快照）和Neo4j（拓扑关系）

## Neo4j关系维护策略

为了解决"节点爬取时差"导致的拓扑失真，实现了以下逻辑：

- **Merge模式**：使用MERGE (src)-[r:CONNECTED_TO]->(dst)
- **时间戳属性**：每个关系必须包含last_updated属性
- **失效清理**：每次写入新关系时，对比nodes字符串。若旧关系不再出现在新字符串中，或last_updated超过15分钟未更新，则删除或禁用该关系

## 技术栈

- Python 3.10+ (asyncio)
- aiohttp (异步请求)
- redis-py (队列管理)
- neo4j (官方驱动)
- BeautifulSoup4 (解析HTML)
- SQLAlchemy (MySQL数据库操作)

## 安装依赖

```bash
pip install -r requirements.txt
```

requirements.txt内容：
```
aiohttp>=3.8.0
beautifulsoup4>=4.11.0
redis>=4.3.0
neo4j>=5.0.0
sqlalchemy>=2.0.0
pymysql>=1.0.0
```

## 配置说明

### 数据库配置

#### Neo4j配置
```python
NEO4J_CONFIG = {
    'uri': 'bolt://121.41.230.15:7687',
    'user': 'neo4j',
    'password': '0595'
}
```

#### Redis配置
```python
REDIS_CONFIG = {
    'host': '121.41.230.15',
    'port': 6379,
    'password': '0595',
    'db': 0
}
```

#### MySQL配置
```python
mysql_config = {
    'host': '121.41.230.15',
    'user': 'root',
    'password': '0595',
    'database': 'allStarLink',
    'charset': 'utf8mb4'
}
```

### API配置
```python
API_CONFIG = {
    'base_url': 'https://stats.allstarlink.org/api/stats',
    'node_list_url': 'http://stats.allstarlink.org/api/stats/nodeList',
    'rate_limit': 30,  # 每分钟30个请求
    'rate_limit_window': 60,  # 时间窗口60秒
    'max_retries': 3,  # 最大重试次数
    'retry_backoff': 2,  # 指数退避因子
    '429_cooldown': 3600  # HTTP 429冷却时间（秒）
}
```

## 使用方法

### 启动爬虫

```bash
cd py_scraper
python neo4j_topology_scraper.py
```

### 主要功能模块

#### 1. Redis优先级队列管理

```python
# 入队
await priority_queue.enqueue(node_id, priority)

# 出队
node_id = await priority_queue.dequeue()

# 获取队列大小
queue_size = await priority_queue.get_queue_size()

# 移除节点
await priority_queue.remove_node(node_id)

# 检查节点是否在队列中
is_in_queue = await priority_queue.is_in_queue(node_id)
```

#### 2. Neo4j数据库操作

```python
# 更新节点数据
await neo4j_manager.update_node(node_data)

# 更新拓扑关系
await neo4j_manager.update_topology(node_id, linked_nodes, connection_modes)

# 设置节点为不活跃状态
await neo4j_manager.set_node_inactive(node_id)
```

#### 3. 核心Cypher查询语句

**更新节点数据：**
```cypher
MERGE (n:Node {node_id: $node_id})
SET n += $properties
```

**更新拓扑关系：**
```cypher
MERGE (src:Node {node_id: $src_id})
MERGE (dst:Node {node_id: $dst_id})
MERGE (src)-[r:CONNECTED_TO]->(dst)
SET r.status = $status,
    r.direction = $direction,
    r.last_updated = $last_updated,
    r.active = $active
```

**清理失效关系：**
```cypher
MATCH (src:Node {node_id: $src_id})-[r:CONNECTED_TO]->(dst:Node)
SET r.active = false
```

## 主调度循环

主调度循环通过asyncio同时运行快照扫描器和异步工作者：

```python
async def main():
    # 初始化Redis连接
    redis_client = redis.Redis(
        host=REDIS_CONFIG['host'],
        port=REDIS_CONFIG['port'],
        password=REDIS_CONFIG['password'],
        db=REDIS_CONFIG['db']
    )

    # 初始化Neo4j管理器
    neo4j_manager = Neo4jManager(NEO4J_CONFIG)
    await neo4j_manager.initialize_constraints()

    # 初始化MySQL配置
    mysql_config = {
        'host': '121.41.230.15',
        'user': 'root',
        'password': '0595',
        'database': 'allStarLink',
        'charset': 'utf8mb4'
    }

    try:
        # 创建并启动快照扫描器
        snapshot_scanner = SnapshotScanner(redis_client, neo4j_manager)
        scanner_task = asyncio.create_task(snapshot_scanner.start())

        # 创建并启动异步工作者
        api_worker = APIWorker(redis_client, neo4j_manager, mysql_config)
        worker_task = asyncio.create_task(api_worker.start())

        # 等待任务完成
        await asyncio.gather(scanner_task, worker_task)
    finally:
        # 清理资源
        await redis_client.close()
        await neo4j_manager.close()
```

## 速率限制处理

系统实现了严格的速率限制，确保不超过每分钟30个请求的限制：

```python
class RateLimiter:
    """速率限制器"""

    def __init__(self, max_requests: int, time_window: int):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []

    async def can_make_request(self) -> bool:
        """检查是否可以发起请求"""
        now = time.time()

        # 移除时间窗口外的请求记录
        self.requests = [t for t in self.requests if now - t < self.time_window]

        # 检查是否超过速率限制
        if len(self.requests) >= self.max_requests:
            return False

        # 记录本次请求
        self.requests.append(now)
        return True
```

## 异常处理和重试机制

系统实现了完善的异常处理和重试机制：

1. **HTTP 429处理**：触发速率限制时冷却3600秒
2. **指数退避重试**：请求失败时使用指数退避策略重试
3. **熔断保护**：连续失败时暂停请求，避免雪崩效应
4. **日志记录**：所有操作都有详细的中文日志记录

## 数据模型

### Neo4j节点属性

#### 基本属性

- `node_id`: 节点ID（唯一标识）
- `callsign`: 呼号
- `last_seen`: 最后更新时间
- `active`: 是否活跃
- `updated_at`: 更新时间

#### 地理位置属性

- `lat`: 纬度
- `lon`: 经度
- `location_desc`: 业务信息描述（从node_tone解析，如域名或URL）

#### 节点类型属性

- `node_type`: 节点类型
  - `Hub`: 枢纽节点（从node_frequency解析，包含HUB/SYSTEM/NETWORK等关键词）
  - `Repeater`: 中继节点（从node_frequency解析，包含数字+频率特征，如444.900）
  - `Unknown`: 未知类型

- `node_rank`: 节点等级
  - `Core`: 核心节点（Hub节点）
  - `Normal`: 普通节点

#### 硬件画像属性

- `hardware_type`: 硬件类型（从server.SiteName解析）
  - `Personal Station`: 个人站（包含Shack/Home/Residence关键词）
  - `Infrastructure`: 基础设施（包含Hub/Network/Data Center/Rack关键词）
  - `Embedded Node`: 嵌入式节点（包含Pi/OrangePi/ClearNode/ARM/RASPBERRY PI关键词）
  - `Unknown`: 未知类型

#### 技术参数属性

- `tone`: 技术参数（从node_tone解析，如CTCSS/DCS值110.9）
- `features`: 节点特性列表（从node_frequency解析，如"PRIDE Multi-mode HUB"）

#### 运行统计属性

- `apprptuptime`: 本次在线时长（秒），从API获取，更新到MySQL数据库
- `total_keyups`: 累计按下PTT次数
- `total_tx_time`: 累计发射时长（秒）
- `connections`: 连接数（从linkedNodes长度计算）

#### 拓扑关系属性

- `linked_nodes`: 连接的节点列表（从stats.data.linkedNodes获取）
- `connection_modes`: 连接模式字符串（从stats.data.nodes获取，如"T520580,T56001"）

#### 数据来源属性

- `source`: 节点来源标识
  - `allstarlink`: AllStarLink节点
  - `other`: 其他电台节点

### Neo4j关系属性

#### CONNECTED_TO关系

- `status`: 连接状态
  - `Active`: 活跃连接
  - `Inactive`: 非活跃连接

- `direction`: 连接模式（从connection_modes解析）
  - `Transceive`: 双向收发（前缀T）
  - `RX Only`: 仅接收（前缀R）
  - `Local`: 本地链路（前缀L）
  - `Permanent`: 永久连接（前缀P）
  - `Unknown`: 未知模式

- `last_updated`: 最后更新时间
- `active`: 关系是否活跃（true/false）

## API数据解析

### API响应结构

```
GET /api/stats/{node_id}
```

#### 主节点数据结构

```json
{
  "stats": {
    "id": 1677,
    "node": 2105,
    "data": {
      "apprptuptime": "240706",
      "totalexecdcommands": "0",
      "totalkeyups": "21",
      "totaltxtime": "92",
      "apprptvers": "3.7.1",
      "timeouts": "0",
      "links": ["520580", "56001", "61672", "1001", "1000"],
      "keyed": false,
      "time": "1772346664",
      "seqno": "9645",
      "nodes": "T520580,T56001,T61672,T1001,T1000",
      "totalkerchunks": "0",
      "keytime": "98285",
      "linkedNodes": [
        {
          "name": "1000"
        },
        {
          "name": "1001"
        },
        {
          "Node_ID": 65481,
          "User_ID": "KJ7OMO",
          "Status": "Active",
          "name": 520580,
          "ipaddr": "172.119.144.212",
          "port": 4569,
          "regseconds": 1772346455,
          "iptime": "2026-02-11 23:58:58",
          "node_frequency": "444.900 (+)",
          "node_tone": "110.9",
          "node_remotebase": false,
          "node_freqagile": "0",
          "callsign": "KJ7OMO",
          "access_reverseautopatch": "1",
          "access_telephoneportal": "1",
          "access_webtransceiver": "1",
          "access_functionlist": "0",
          "is_nnx": "Yes",
          "server": {
            "Server_ID": 24818,
            "User_ID": "KJ7OMO",
            "Server_Name": "520580-Repeater",
            "Affiliation": "Pride Radio Network",
            "SiteName": "Raspberry Pi",
            "Logitude": "-114.5991",
            "Latitude": "32.6686",
            "Location": "Yuma, AZ",
            "TimeZone": null,
            "udpport": 4570,
            "proxy_ip": null
          }
        }
      ]
    },
    "created_at": "2021-03-22T01:21:43.000000Z",
    "updated_at": "2026-03-01T06:31:04.000000Z",
    "user_node": {
      "Node_ID": 53867,
      "User_ID": "KJ7OMO",
      "Status": "Active",
      "name": 2105,
      "ipaddr": "209.222.4.140",
      "port": 4569,
      "regseconds": 1771123903,
      "iptime": "2025-01-08 10:02:31",
      "node_frequency": "PRIDE Multi-mode HUB",
      "node_tone": "kimberlychase.com",
      "node_remotebase": false,
      "node_freqagile": "0",
      "callsign": "KJ7OMO",
      "access_reverseautopatch": "1",
      "access_telephoneportal": "1",
      "access_webtransceiver": "1",
      "access_functionlist": "0",
      "is_nnx": "No",
      "server": {
        "Server_ID": 33234,
        "User_ID": "KJ7OMO",
        "Server_Name": "2105-PRIDE-HUB",
        "Affiliation": "Pride Radio Network",
        "SiteName": "Pride Radio Network Hub",
        "Logitude": "-74.4601",
        "Latitude": "40.5545",
        "Location": "Cloud 69",
        "TimeZone": null,
        "udpport": 4569,
        "proxy_ip": null
      }
    }
  },
  "node": {
    "Node_ID": 53867,
    "User_ID": "KJ7OMO",
    "Status": "Active",
    "name": 2105,
    ...
  },
  "keyups": [],
  "time": 5.878925323486328
}
```

### JSON字段解析

#### stats字段

- `id`: 统计记录ID
- `node`: 节点ID（整数）
- `created_at`: 创建时间
- `updated_at`: 更新时间

#### stats.data字段（运行统计数据）

- `apprptuptime`: 运行时间
- `totalkeyups`: 累计按下PTT次数
- `totaltxtime`: 累计发射时长（秒）
- `nodes`: 连接模式字符串（如"T520580,T56001"）
- `linkedNodes`: 连接的节点列表

#### stats.data.linkedNodes字段（连接节点数据）

每个连接节点包含以下字段：

- `name`: 节点ID（真正的节点标识）
- `Node_ID`: 数据库自增ID（仅AllStarLink节点有此字段）
- `User_ID`: 用户ID
- `Status`: 状态（Active/Inactive）
- `ipaddr`: IP地址
- `port`: 端口
- `node_frequency`: 节点频率
  - 包含数字+频率特征（如444.900）→ 解析为Repeater类型
  - 包含文本描述（如HUB/SYSTEM/NETWORK）→ 解析为Hub类型
- `node_tone`: 节点音调
  - 纯数字（如110.9）→ 解析为tone技术参数
  - 域名或URL（如kimberlychase.com）→ 解析为location_desc业务信息
- `callsign`: 呼号
- `server`: 服务器信息（仅AllStarLink节点有此字段）

#### stats.data.linkedNodes.server字段（服务器信息）

- `Server_ID`: 服务器ID
- `User_ID`: 用户ID
- `Server_Name`: 服务器名称
- `Affiliation`: 所属组织
- `SiteName`: 站点名称
  - 包含Shack/Home/Residence → 解析为Personal Station
  - 包含Hub/Network/Data Center/Rack → 解析为Infrastructure
  - 包含Pi/OrangePi/ClearNode/ARM/RASPBERRY PI → 解析为Embedded Node
- `Latitude`: 纬度
- `Logitude`: 经度
- `Location`: 位置描述
- `TimeZone`: 时区

#### stats.user_node字段（主节点数据）

主节点数据结构类似于`linkedNodes`中的节点，包含完整的节点信息和服务器信息。

- `name`: 节点ID
- `node_frequency`: 节点频率
- `node_tone`: 节点音调
- `callsign`: 呼号
- `server`: 服务器信息

### 数据解析流程

#### 主节点数据解析

1. 从`stats.user_node`获取主节点数据
2. 从`stats.user_node.server`获取服务器数据
3. 从`stats.data.linkedNodes`获取连接的节点列表
4. 解析`node_frequency` → 确定`node_type`（Hub/Repeater）
5. 解析`node_tone` → 确定`tone`或`location_desc`
6. 解析`server.SiteName` → 确定`hardware_type`
7. 计算`connections = len(linkedNodes)`

#### 连接节点数据解析

1. 遍历`stats.data.linkedNodes`中的每个节点
2. 判断节点来源（通过`Node_ID`字段判断是否为AllStarLink节点）
3. 如果是AllStarLink节点：
   - 解析`node_frequency` → 确定`node_type`
   - 解析`node_tone` → 确定`tone`或`location_desc`
   - 解析`server.SiteName` → 确定`hardware_type`
4. 如果是其他电台节点：
   - 使用默认数据结构
   - `source`标记为`other`

### 连接模式解析

`connection_modes`字符串格式：`T520580,T56001,T61672,T1001,T1000`

- 前缀`T`: Transceive（双向收发）
- 前缀`R`: RX Only（仅接收）
- 前缀`L`: Local（本地链路）
- 前缀`P`: Permanent（永久连接）

解析逻辑：
1. 按逗号分割字符串
2. 提取每个元素的前缀和节点ID
3. 将节点ID映射到对应的连接模式

## 监控和日志

系统提供详细的日志记录：

- INFO级别：正常运行信息
- DEBUG级别：详细调试信息
- ERROR级别：错误信息和异常堆栈

## 故障排除

### 常见问题

1. **数据库连接失败**
   - 检查数据库配置参数
   - 确认网络连接正常

2. **API请求超时**
   - 增加timeout参数
   - 检查网络状况

3. **速率限制触发**
   - 系统会自动冷却3600秒
   - 可以调整API_CONFIG中的rate_limit参数

4. **Redis连接失败**
   - 检查Redis服务是否运行
   - 确认Redis配置参数

## 扩展功能

### 自定义事件类型

可以在APIWorker类中添加新的事件检测逻辑：

```python
async def _fetch_node_data(self, node_id: int) -> Optional[Dict]:
    # 示例：检测频率变化
    # 在这里添加自定义逻辑
```

### 数据增强

可以在_parse_node_data方法中添加数据增强逻辑：

```python
def _parse_node_data(self, data: Dict) -> Dict:
    # 示例：添加地理编码
    # 在这里添加自定义逻辑
```

## 性能优化建议

1. **调整并发数**：根据服务器性能调整API工作者数量
2. **优化数据库连接池**：调整连接池大小以适应负载
3. **使用缓存**：对频繁访问的数据实现缓存
4. **批量处理**：对数据库操作实现批量处理

## 版本历史

- v1.0: 初始版本，实现基本的拓扑数据爬取功能
