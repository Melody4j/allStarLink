# 新版爬虫架构说明

本文档以 `src/link_scraper` 当前代码为准，描述 2026-03-13 完成本轮重构后的真实架构。

当前项目范围明确如下：

- 当前生产主线只关注 `AllStarLink`
- 第二数据源只保留 adapter 骨架，不做真实采集
- 当前代码已经完成结构化重构、单元测试补齐和一轮真实环境联调

## 1. 当前主入口

主入口：

- `src/link_scraper/main.py`

主入口当前负责：

- 加载配置
- 初始化 Redis、MySQL、Neo4j
- 初始化批次号管理与限流器
- 通过 source factory 构建数据源组件
- 组装扫描器、服务层、仓储层、Worker
- 驱动“快照扫描 -> 队列消费 -> 落库”主流程

## 2. 当前目录结构

```text
src/link_scraper/
├─ main.py
├─ config/
│  ├─ constants.py
│  └─ settings.py
├─ database/
│  ├─ base.py
│  ├─ mysql_manager.py
│  ├─ neo4j_manager.py
│  └─ __init__.py
├─ domain/
│  ├─ models.py
│  └─ __init__.py
├─ repositories/
│  ├─ records.py
│  ├─ mappers.py
│  ├─ graph_repository.py
│  ├─ dim_node_repository.py
│  ├─ ods_repository.py
│  └─ __init__.py
├─ scrapers/
│  ├─ snapshot_scanner.py
│  ├─ node_ingestion_worker.py
│  └─ __init__.py
├─ services/
│  ├─ fetch_service.py
│  ├─ parse_service.py
│  ├─ sync_service.py
│  ├─ ods_service.py
│  └─ __init__.py
├─ sources/
│  ├─ base.py
│  ├─ factory.py
│  ├─ allstarlink/
│  │  ├─ client.py
│  │  ├─ parser.py
│  │  ├─ mapper.py
│  │  └─ __init__.py
│  ├─ other_source/            # 仅保留 Phase 4 骨架
│  └─ __init__.py
├─ task_queue/
│  └─ priority_queue.py
└─ utils/
   ├─ batch_manager.py
   ├─ logger.py
   ├─ rate_limiter.py
   └─ helpers.py
```

## 3. 当前分层结构

本轮重构后，主流程已经从早期的：

```text
worker -> parser -> manager
```

演进为：

```text
worker -> services -> repositories -> managers
                    ^
                    |
                 sources
```

各层职责如下。

### 3.1 Source Adapter 层

目录：

- `src/link_scraper/sources/base.py`
- `src/link_scraper/sources/factory.py`
- `src/link_scraper/sources/allstarlink/`

职责：

- 隔离 AllStarLink 的接口契约
- 提供统一的 client / parser / mapper 抽象
- 让主流程不再依赖 AllStarLink 的原始 JSON 细节

当前状态：

- `AllStarLink` 已经完整接入 adapter 边界
- `other_source` 只保留骨架，不参与当前生产流程

### 3.2 领域模型层

目录：

- `src/link_scraper/domain/models.py`

职责：

- 承接 source mapper 输出的统一语义模型
- 提供 source 无关的节点、连接、聚合结果表达

当前核心模型：

- `CanonicalNode`
- `CanonicalConnection`
- `CanonicalNodeBundle`

### 3.3 服务层

目录：

- `src/link_scraper/services/fetch_service.py`
- `src/link_scraper/services/parse_service.py`
- `src/link_scraper/services/sync_service.py`
- `src/link_scraper/services/ods_service.py`

职责：

- `NodeFetchService`：节点详情抓取
- `NodeParseService`：把 source 结果映射为统一领域对象
- `NodeSyncService`：协调图节点、关系、维表更新
- `OdsWriteService`：构建并写入 ODS 明细

### 3.4 仓储层

目录：

- `src/link_scraper/repositories/records.py`
- `src/link_scraper/repositories/mappers.py`
- `src/link_scraper/repositories/graph_repository.py`
- `src/link_scraper/repositories/dim_node_repository.py`
- `src/link_scraper/repositories/ods_repository.py`

职责：

- 定义持久化 record
- 将 canonical model 映射到图/维表/ODS 的存储对象
- 为服务层屏蔽底层 manager 的技术细节

### 3.5 存储管理层

目录：

- `src/link_scraper/database/mysql_manager.py`
- `src/link_scraper/database/neo4j_manager.py`

当前主用命名：

- `RelationalStorageManager`
- `GraphStorageManager`

职责：

- 维护数据库连接与底层执行
- 承接 repository 的写入请求
- 承接基于 record 的写入输入

### 3.6 Worker 与扫描层

目录：

- `src/link_scraper/scrapers/snapshot_scanner.py`
- `src/link_scraper/scrapers/node_ingestion_worker.py`

当前主用命名：

- `SnapshotScanner`
- `NodeIngestionWorker`

职责：

- `SnapshotScanner` 负责在线节点快照扫描、MySQL 连接数更新、批量入队
- `NodeIngestionWorker` 负责消费 Redis 队列并编排服务调用

## 4. 当前主流程

### 4.1 启动流程

`main.py` 当前启动顺序如下：

1. `Settings.load()` 读取配置
2. 初始化 Redis 客户端与优先级队列
3. 初始化 `GraphStorageManager`
4. 初始化 `RelationalStorageManager`
5. 初始化 `RateLimiter`
6. 初始化 `BatchManager`
7. 通过 `build_source_components()` 构造 source client / parser / mapper
8. 初始化 `SnapshotScanner`
9. 初始化 repositories
10. 初始化 `NodeFetchService` / `NodeParseService` / `NodeSyncService` / `OdsWriteService`
11. 初始化 `NodeIngestionWorker`

### 4.2 运行流程

当前仍然采用“队列清空后再触发新扫描”的调度策略：

1. 后台启动 `NodeIngestionWorker.start()`
2. 主循环检查 Redis 队列大小
3. 队列为空时触发 `SnapshotScanner.scan_and_update()`
4. 快照扫描完成后，Worker 继续消费队列
5. 队列再次清空后，进入下一轮扫描

### 4.3 快照扫描流程

`SnapshotScanner.scan_and_update()` 当前真实流程：

1. 获取或生成新的 `batch_no`
2. 通过 source client 获取节点列表
3. 通过 source mapper 提取 `node_id + link_count`
4. 批量更新 `dim_nodes.current_link_count / last_seen / is_active`
5. 将 `link_count > 1` 的节点按优先级批量入 Redis

当前优先级规则：

- `priority = link_count`

### 4.4 队列消费流程

`NodeIngestionWorker.process_queue()` 当前真实流程：

1. 速率限制校验
2. 从 Redis 队列取一个节点 ID
3. 随机延迟
4. 调 `NodeFetchService` 拉取详情
5. 调 `NodeParseService` 生成 `CanonicalNodeBundle`
6. 调 `NodeSyncService` 写入 Neo4j 和 `dim_nodes`
7. 调 `OdsWriteService` 写入 `ods_nodes_details`

## 5. 当前关键设计说明

### 5.1 当前只对 AllStarLink 做真实实现

虽然主流程已经支持 `SOURCE_NAME` 和 source factory，但当前有效实现仍然只有：

- `allstarlink`

`other_source` 只是骨架目录，用于验证 Phase 4 的接入边界已经具备。

### 5.2 兼容层已移除

截至当前代码版本，以下兼容层已经从主线代码中移除：

- `models/` 下旧模型
- `scrapers/node_parser.py` 兼容包装层
- `APIWorker` / `MySQLManager` / `Neo4jManager` 旧命名别名

当前主流程已统一使用新命名与 canonical / record 模型。

### 5.3 Neo4j 仍采用批次实例化

Neo4j 唯一标识仍然是：

```text
unique_id = "{node_id}_{batch_no}"
```

这意味着拓扑图仍然是按批次隔离的快照图，而不是单节点滚动覆盖图。

### 5.4 子节点仍采用“先占位，后补全”策略

当前子节点如果缺失统计数据：

- 会写 `null`
- 不会伪造 `0`

当该节点后续被当作主节点抓取时，再补齐真实统计信息。

## 6. 联调结论

截至 2026-03-13，已经完成一轮真实依赖联调验证。

已验证通过的内容：

- 初始化 Redis / MySQL / Neo4j / source
- 执行一次快照扫描
- 节点批量入队
- 消费队列中的节点详情任务

联调过程中还修复了两个真实问题：

1. `SnapshotScanner` 批量更新 SQL 中使用了错误变量
2. `RelationalStorageManager.execute_query()` 对 DML 语句返回值判断不正确

## 7. 当前建议阅读顺序

如果要理解当前代码，建议按以下顺序阅读：

1. `src/link_scraper/main.py`
2. `src/link_scraper/sources/base.py`
3. `src/link_scraper/sources/factory.py`
4. `src/link_scraper/sources/allstarlink/`
5. `src/link_scraper/domain/models.py`
6. `src/link_scraper/repositories/`
7. `src/link_scraper/services/`
8. `src/link_scraper/scrapers/snapshot_scanner.py`
9. `src/link_scraper/scrapers/node_ingestion_worker.py`
10. `src/link_scraper/database/`

## 8. 当前剩余工作

当前结构性重构已经基本完成，剩余重点是：

1. 显式建模节点完整度状态
2. 视需要增加更多集成测试
3. 如果未来确定第二数据源，再把 `other_source` 从骨架推进为真实实现
